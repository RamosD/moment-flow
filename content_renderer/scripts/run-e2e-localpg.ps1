# =============================================================================
# E2E harness against an ALREADY-RUNNING local PostgreSQL (no Docker) — R-HARD-002/003.
#
# Use this when Docker is unavailable but a local PostgreSQL cluster is reachable
# (e.g. a throwaway cluster created with the bundled PostgreSQL `initdb`/`pg_ctl`).
# It migrates + seeds (idempotent), boots the renderer (:8002) and Django (:8000)
# with the SAME internal token, runs the E2E driver and collects evidence.
#
# DB_* come from the environment, with DEV defaults (NOT secrets). Set them to
# point at your cluster. libpq (for psycopg) is taken from the PostgreSQL bin.
#
# Usage:
#   pwsh -ExecutionPolicy Bypass -File scripts\run-e2e-localpg.ps1
# =============================================================================
param(
  [switch]$KeepUp,
  # Django port — overridable so the harness can dodge a port already in use.
  [int]$DjangoPort = 8000
)
$ErrorActionPreference = 'Continue'

$pgBin       = if ($env:PG_BIN) { $env:PG_BIN } else { 'C:\Program Files\PostgreSQL\18\bin' }
$rendererDir = 'D:\Workspace\ChartRex\momentflow\content_renderer'
$backendDir  = 'D:\Workspace\ChartRex\momentflow\backend_core'
$py          = Join-Path $backendDir 'venv\Scripts\python.exe'

# libpq (psycopg) needs the PostgreSQL bin on PATH.
$env:PATH = "$pgBin;$env:PATH"

# DB config (dev defaults — match the running cluster).
if (-not $env:DB_ENGINE)   { $env:DB_ENGINE   = 'postgres' }
if (-not $env:DB_NAME)     { $env:DB_NAME     = 'chartrex_e2e' }
if (-not $env:DB_USER)     { $env:DB_USER     = 'postgres' }
if (-not $env:DB_PASSWORD) { $env:DB_PASSWORD = 'e2e_dev_only' }
if (-not $env:DB_HOST)     { $env:DB_HOST     = 'localhost' }
if (-not $env:DB_PORT)     { $env:DB_PORT     = '55432' }

$token   = if ($env:INTERNAL_API_TOKEN) { $env:INTERNAL_API_TOKEN } else { 'e2e-token-' + ([guid]::NewGuid().ToString('N').Substring(0, 10)) }
$storage = Join-Path $env:TEMP ('cr-e2e-' + [guid]::NewGuid().ToString('N').Substring(0, 6))
New-Item -ItemType Directory -Force -Path $storage | Out-Null
$logDir = Join-Path $rendererDir ('e2e-logs\' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$rOut = Join-Path $logDir 'renderer.out'; $rErr = Join-Path $logDir 'renderer.err'
$dOut = Join-Path $logDir 'django.out';   $dErr = Join-Path $logDir 'django.err'

$env:INTERNAL_API_TOKEN        = $token
$env:PORT                      = '8002'
$env:NODE_ENV                  = 'development'
$env:LOG_LEVEL                 = 'warn'
$env:STORAGE_PROVIDER          = 'local'
$env:LOCAL_STORAGE_ROOT        = $storage
$env:CONTENT_RENDERER_BASE_URL = 'http://localhost:8002'
$env:REPORT_RENDERER_BASE_URL  = 'http://localhost:8002'
# The seeded jobs' callback_url is built from BACKEND_PUBLIC_BASE_URL, so it must
# point at THIS harness's Django (DjangoPort), never a stray server.
$env:BACKEND_PUBLIC_BASE_URL   = "http://localhost:$DjangoPort"
$env:EXTERNAL_JOBS_ENABLED     = 'true'
$env:EXTERNAL_JOBS_DRY_RUN     = 'false'

$renderer = $null; $django = $null
function Wait-Up($url, $sec) {
  $d = (Get-Date).AddSeconds($sec)
  while ((Get-Date) -lt $d) {
    try { $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3; if ($r.StatusCode -ge 200) { return $true } }
    catch { if ($_.Exception.Response.StatusCode.value__ -ge 200) { return $true } }
    Start-Sleep -Milliseconds 500
  }
  return $false
}

try {
  Write-Output 'Applying migrations + seeds (idempotent)...'
  & $py (Join-Path $backendDir 'manage.py') migrate --noinput 2>&1 | Tee-Object -FilePath (Join-Path $logDir 'migrate.log') | Out-Null
  foreach ($s in @('seed_rbac', 'seed_billing', 'seed_content')) {
    & $py (Join-Path $backendDir 'manage.py') $s 2>&1 | Tee-Object -FilePath (Join-Path $logDir "$s.log") | Out-Null
  }

  $renderer = Start-Process -FilePath 'node' -ArgumentList 'dist/server.js' `
    -WorkingDirectory $rendererDir -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $rOut -RedirectStandardError $rErr
  $django = Start-Process -FilePath $py -ArgumentList 'manage.py', 'runserver', "$DjangoPort", '--noreload' `
    -WorkingDirectory $backendDir -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $dOut -RedirectStandardError $dErr

  $rUp = Wait-Up 'http://localhost:8002/health' 30
  $dUp = Wait-Up "http://localhost:$DjangoPort/api/v1/schema/" 60
  Write-Output "renderer_up=$rUp django_up=$dUp"

  if ($rUp -and $dUp) {
    $env:BACKEND_CORE_DIR  = $backendDir
    $env:RENDERER_JOBS_URL = 'http://localhost:8002/jobs/'
    Write-Output '----- E2E RESULTS -----'
    & $py (Join-Path $rendererDir 'scripts\e2e_backend_core.py') 2>&1 | Tee-Object -FilePath (Join-Path $logDir 'e2e_results.json')
    Write-Output '----- END E2E RESULTS -----'
  } else {
    Write-Output '----- renderer.err -----'; Get-Content $rErr -Tail 20 -ErrorAction SilentlyContinue
    Write-Output '----- django.err -----';   Get-Content $dErr -Tail 40 -ErrorAction SilentlyContinue
  }
  Write-Output "evidence_dir=$logDir"
}
catch { Write-Output "E2E ERROR: $($_.Exception.Message)" }
finally {
  if (-not $KeepUp) {
    foreach ($p in @($renderer, $django)) {
      if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
    }
    Remove-Item $storage -Recurse -Force -ErrorAction SilentlyContinue
  }
  Write-Output 'DONE'
}
