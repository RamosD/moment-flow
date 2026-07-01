# =============================================================================
# E2E harness on PostgreSQL (R-HARD-002).
#
# Reliable MULTI-PROCESS loop: brings up an ephemeral PostgreSQL (Docker),
# points backend_core at it, migrates + seeds, boots the renderer (:8202) and
# Django (:8100) with the SAME internal token, waits for readiness, runs the E2E
# driver, collects evidence, then tears everything down.
#
# Why PostgreSQL: SQLite cannot share committed rows across processes, so the
# renderer's (separate-process) callback gets a 404 resolving the job. PostgreSQL
# is the recommended base for multi-process E2E.
#
# Credentials are EXPLICIT DEV VALUES (see docker-compose.e2e.yml / .env.e2e.example),
# not secrets. Override via environment or a local .env.e2e.
#
# Usage (from content_renderer/, with dist/ built via `npm run build`):
#   powershell -ExecutionPolicy Bypass -File scripts\run-e2e-postgres.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\run-e2e-postgres.ps1 -KeepUp
# =============================================================================
param(
  # Leave Postgres + services running after the driver (for manual inspection).
  [switch]$KeepUp
)

$ErrorActionPreference = 'Continue'

$rendererDir = 'D:\Workspace\ChartRex\momentflow\content_renderer'
$backendDir  = 'D:\Workspace\ChartRex\momentflow\backend_core'
$py          = Join-Path $backendDir 'venv\Scripts\python.exe'
$compose     = Join-Path $rendererDir 'docker-compose.e2e.yml'

# --- Config (dev-only defaults; override via environment) ---------------------
$token   = if ($env:INTERNAL_API_TOKEN -and $env:INTERNAL_API_TOKEN -ne 'e2e-shared-token-change-me') {
  $env:INTERNAL_API_TOKEN
} else {
  'e2e-token-' + ([guid]::NewGuid().ToString('N').Substring(0, 10))
}
$dbName  = if ($env:DB_NAME) { $env:DB_NAME } else { 'chartrex_e2e' }
$dbUser  = if ($env:DB_USER) { $env:DB_USER } else { 'chartrex_e2e' }
$dbPass  = if ($env:DB_PASSWORD) { $env:DB_PASSWORD } else { 'chartrex_e2e_dev_only' }
$dbPort  = if ($env:DB_PORT) { $env:DB_PORT } else { '55432' }

# Evidence/logs are kept (git-ignored) so a run can be inspected afterwards.
$logDir = Join-Path $rendererDir ('e2e-logs\' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$rOut = Join-Path $logDir 'renderer.out'; $rErr = Join-Path $logDir 'renderer.err'
$dOut = Join-Path $logDir 'django.out';   $dErr = Join-Path $logDir 'django.err'
$storage = Join-Path $env:TEMP ('cr-e2e-' + [guid]::NewGuid().ToString('N').Substring(0, 6))
New-Item -ItemType Directory -Force -Path $storage | Out-Null

$renderer = $null; $django = $null

function Wait-Up($url, $timeoutSec) {
  $deadline = (Get-Date).AddSeconds($timeoutSec)
  while ((Get-Date) -lt $deadline) {
    try {
      $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
      if ($r.StatusCode -ge 200) { return $true }
    } catch {
      if ($_.Exception.Response.StatusCode.value__ -ge 200) { return $true }
    }
    Start-Sleep -Milliseconds 500
  }
  return $false
}

try {
  Write-Output "===== E2E PostgreSQL harness ====="

  # 1) Bring up PostgreSQL. Pass DB_* so compose interpolation matches Django.
  $env:DB_NAME = $dbName; $env:DB_USER = $dbUser; $env:DB_PASSWORD = $dbPass; $env:DB_PORT = $dbPort
  Write-Output 'Starting PostgreSQL (docker compose)...'
  & docker compose -f $compose up -d
  if ($LASTEXITCODE -ne 0) { throw 'docker compose up failed (is Docker running?)' }

  # 2) Wait until the container reports healthy.
  $pgReady = $false
  $deadline = (Get-Date).AddSeconds(60)
  while ((Get-Date) -lt $deadline) {
    $health = (& docker inspect --format '{{.State.Health.Status}}' chartrex_e2e_postgres 2>$null)
    if ($health -eq 'healthy') { $pgReady = $true; break }
    Start-Sleep -Milliseconds 1000
  }
  Write-Output "postgres_healthy=$pgReady"
  if (-not $pgReady) { throw 'PostgreSQL did not become healthy in time.' }

  # 3) Point Django at PostgreSQL and use the shared token for all processes.
  $env:DB_ENGINE          = 'postgres'
  $env:DB_HOST            = 'localhost'
  $env:INTERNAL_API_TOKEN = $token
  $env:PORT               = '8202'
  $env:NODE_ENV           = 'development'
  $env:LOG_LEVEL          = 'warn'
  $env:STORAGE_PROVIDER   = 'local'
  $env:LOCAL_STORAGE_ROOT = $storage
  $env:CONTENT_RENDERER_BASE_URL = 'http://localhost:8202'
  $env:REPORT_RENDERER_BASE_URL  = 'http://localhost:8202'
  $env:BACKEND_PUBLIC_BASE_URL   = 'http://localhost:8100'
  $env:EXTERNAL_JOBS_ENABLED     = 'true'
  $env:EXTERNAL_JOBS_DRY_RUN     = 'false'

  # 4) Migrate + seed the fresh database.
  Write-Output 'Applying migrations...'
  & $py (Join-Path $backendDir 'manage.py') migrate --noinput 2>&1 | Tee-Object -FilePath (Join-Path $logDir 'migrate.log')
  if ($LASTEXITCODE -ne 0) { throw 'manage.py migrate failed.' }

  Write-Output 'Seeding (rbac, billing, content)...'
  foreach ($seed in @('seed_rbac', 'seed_billing', 'seed_content')) {
    & $py (Join-Path $backendDir 'manage.py') $seed 2>&1 | Tee-Object -FilePath (Join-Path $logDir "$seed.log")
  }

  # 5) Boot renderer + Django (children inherit the env set above).
  $renderer = Start-Process -FilePath 'node' -ArgumentList 'dist/server.js' `
    -WorkingDirectory $rendererDir -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $rOut -RedirectStandardError $rErr
  $django = Start-Process -FilePath $py -ArgumentList 'manage.py', 'runserver', '8100', '--noreload' `
    -WorkingDirectory $backendDir -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $dOut -RedirectStandardError $dErr

  $rUp = Wait-Up 'http://localhost:8202/health' 30
  $dUp = Wait-Up 'http://localhost:8100/api/v1/schema/' 45
  Write-Output "renderer_up=$rUp django_up=$dUp"

  # 6) Run the E2E driver and capture evidence.
  if ($rUp -and $dUp) {
    $env:BACKEND_CORE_DIR  = $backendDir
    $env:RENDERER_JOBS_URL = 'http://localhost:8202/jobs/'
    Write-Output '----- E2E RESULTS -----'
    & $py (Join-Path $rendererDir 'scripts\e2e_backend_core.py') 2>&1 | Tee-Object -FilePath (Join-Path $logDir 'e2e_results.json')
    Write-Output '----- END E2E RESULTS -----'
  } else {
    Write-Output '----- renderer.err -----'; Get-Content $rErr -Tail 20 -ErrorAction SilentlyContinue
    Write-Output '----- django.err -----';   Get-Content $dErr -Tail 30 -ErrorAction SilentlyContinue
  }
  Write-Output "evidence_dir=$logDir"
}
catch {
  Write-Output "E2E ERROR: $($_.Exception.Message)"
}
finally {
  if (-not $KeepUp) {
    foreach ($p in @($renderer, $django)) {
      if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
    }
    & docker compose -f $compose down -v 2>&1 | Out-Null
    Remove-Item $storage -Recurse -Force -ErrorAction SilentlyContinue
    Write-Output 'e2e-postgres-done (services + Postgres torn down)'
  } else {
    Write-Output "e2e-postgres-done (-KeepUp: services + Postgres LEFT RUNNING; evidence in $logDir)"
  }
}
