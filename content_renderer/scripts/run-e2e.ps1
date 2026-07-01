# Orchestrate a real two-service E2E: renderer (:8002) + Django backend_core (:8000).
# Boots both, waits for readiness, runs the E2E driver, then tears down.
#
# NOTE (R-HARD-002): this legacy variant uses the backend's DEFAULT database
# (SQLite), which cannot share committed rows across processes — the renderer's
# (separate-process) callback gets a 404 resolving the job. For a reliable
# MULTI-PROCESS loop use the PostgreSQL harness instead:
#     scripts\run-e2e-postgres.ps1
$ErrorActionPreference = 'Continue'

$rendererDir = 'D:\Workspace\ChartRex\momentflow\content_renderer'
$backendDir  = 'D:\Workspace\ChartRex\momentflow\backend_core'
$py          = Join-Path $backendDir 'venv\Scripts\python.exe'
$token       = 'e2e-token-' + ([guid]::NewGuid().ToString('N').Substring(0, 10))
$storage     = Join-Path $env:TEMP ('cr-e2e-' + [guid]::NewGuid().ToString('N').Substring(0, 6))
New-Item -ItemType Directory -Force -Path $storage | Out-Null

$logDir = Join-Path $env:TEMP ('cr-e2e-logs-' + [guid]::NewGuid().ToString('N').Substring(0, 6))
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$rOut = Join-Path $logDir 'renderer.out'; $rErr = Join-Path $logDir 'renderer.err'
$dOut = Join-Path $logDir 'django.out';   $dErr = Join-Path $logDir 'django.err'

# Shared + per-service env (each process reads what it needs).
$env:INTERNAL_API_TOKEN        = $token
$env:PORT                      = '8002'
$env:NODE_ENV                  = 'development'
$env:LOG_LEVEL                 = 'warn'
$env:LOCAL_STORAGE_ROOT        = $storage
$env:CONTENT_RENDERER_BASE_URL = 'http://localhost:8002'
$env:REPORT_RENDERER_BASE_URL  = 'http://localhost:8002'
$env:BACKEND_PUBLIC_BASE_URL   = 'http://localhost:8000'
$env:EXTERNAL_JOBS_ENABLED     = 'true'
$env:EXTERNAL_JOBS_DRY_RUN     = 'false'

$renderer = Start-Process -FilePath 'node' -ArgumentList 'dist/server.js' `
  -WorkingDirectory $rendererDir -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput $rOut -RedirectStandardError $rErr
$django = Start-Process -FilePath $py -ArgumentList 'manage.py', 'runserver', '8000', '--noreload' `
  -WorkingDirectory $backendDir -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput $dOut -RedirectStandardError $dErr

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

$rUp = Wait-Up 'http://localhost:8002/health' 30
$dUp = Wait-Up 'http://localhost:8000/api/v1/schema/' 45
Write-Output "renderer_up=$rUp django_up=$dUp"

if ($rUp -and $dUp) {
  $env:BACKEND_CORE_DIR  = $backendDir
  $env:RENDERER_JOBS_URL = 'http://localhost:8002/jobs/'
  Write-Output '----- E2E RESULTS -----'
  & $py (Join-Path $rendererDir 'scripts\e2e_backend_core.py')
  Write-Output '----- END E2E RESULTS -----'
  Write-Output '----- renderer.out (tail) -----'; Get-Content $rOut -Tail 12 -ErrorAction SilentlyContinue
} else {
  Write-Output '----- renderer.err -----'; Get-Content $rErr -Tail 20 -ErrorAction SilentlyContinue
  Write-Output '----- django.err -----';   Get-Content $dErr -Tail 30 -ErrorAction SilentlyContinue
}

# Teardown.
foreach ($p in @($renderer, $django)) {
  if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
}
Remove-Item $storage -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $logDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Output 'e2e-done'
