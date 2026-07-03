# =============================================================================
# staging-local-health.ps1 — Verifica a stack staging local completa:
# containers de infraestrutura (PostgreSQL, MinIO) e serviços aplicacionais
# (Backend Core, Intelligence Engine, Content Renderer, Frontend), quando
# activos (STG-LOCAL-006).
#
# Cada verificação confirma não só HTTP 2xx, mas que o corpo da resposta
# identifica o SERVIÇO CORRECTO (ver Prompts 03-05 desta fase: processos
# órfãos de sessões anteriores já responderam com sucesso na porta certa
# mas pertenciam ao serviço errado — este script existe para nunca repetir
# esse falso-positivo silenciosamente).
#
# Serviços aplicacionais são OPCIONAIS por desenho desta fase (podem não
# estar a correr) — não estarem activos não é tratado como falha do script,
# é reportado como "down" e reflectido no exit code só se -RequireApps for
# passado explicitamente.
#
# Uso:
#   pwsh -ExecutionPolicy Bypass -File scripts\staging-local-health.ps1
#   pwsh -ExecutionPolicy Bypass -File scripts\staging-local-health.ps1 -RequireApps
#
# Healthcheck agregado staff-only (dependencies) só corre se a variável de
# ambiente STAGING_STAFF_ACCESS_TOKEN estiver definida (um JWT de acesso de
# um utilizador staff, não um secret de configuração — nunca impresso por
# este script). Ausente ⇒ verificação marcada SKIPPED, não FAIL.
# =============================================================================
param(
    [switch]$RequireApps
)

. (Join-Path $PSScriptRoot 'lib\staging-local-common.ps1')

$results = New-Object System.Collections.Generic.List[object]
function Add-Result($Name, $Status, $Detail) {
    $results.Add([pscustomobject]@{ Name = $Name; Status = $Status; Detail = $Detail })
}

Write-Output '== staging-local-health =='

# --- Infraestrutura (obrigatória) ---
$pgHealth = Get-ContainerHealth -ContainerName 'chartrex_staging_postgres'
Add-Result 'PostgreSQL (container)' $(if ($pgHealth -eq 'healthy') { 'OK' } else { 'FAIL' }) $pgHealth

$minioHealth = Get-ContainerHealth -ContainerName 'chartrex_staging_minio'
Add-Result 'MinIO (container)' $(if ($minioHealth -eq 'healthy') { 'OK' } else { 'FAIL' }) $minioHealth

# --- Backend Core ---
$bcLive = Test-HttpOk -Url 'http://127.0.0.1:8100/api/v1/system/health/live/'
$bcLiveOk = $bcLive.Ok -and ($bcLive.StatusCode -eq 200)
if ($bcLiveOk) {
    try {
        $body = Invoke-RestMethod -Uri 'http://127.0.0.1:8100/api/v1/system/health/live/' -TimeoutSec 3
        $bcLiveOk = $body.service -eq 'backend_core'
        Add-Result 'Backend Core /live/' $(if ($bcLiveOk) { 'OK' } else { 'FAIL' }) "service=$($body.service)"
    } catch {
        Add-Result 'Backend Core /live/' 'FAIL' "corpo inesperado: $($_.Exception.Message)"
        $bcLiveOk = $false
    }
} else {
    Add-Result 'Backend Core /live/' 'DOWN' 'não respondeu (serviço opcional, processo local)'
}

if ($bcLiveOk) {
    $bcReady = Test-HttpOk -Url 'http://127.0.0.1:8100/api/v1/system/health/ready/'
    Add-Result 'Backend Core /ready/' $(if ($bcReady.Ok) { 'OK' } else { 'FAIL' }) "http=$($bcReady.StatusCode)"
} else {
    Add-Result 'Backend Core /ready/' 'SKIPPED' 'live já falhou'
}

if ($bcLiveOk -and $env:STAGING_STAFF_ACCESS_TOKEN) {
    try {
        $headers = @{ Authorization = "Bearer $($env:STAGING_STAFF_ACCESS_TOKEN)" }
        $dep = Invoke-RestMethod -Uri 'http://127.0.0.1:8100/api/v1/system/health/dependencies/' -Headers $headers -TimeoutSec 5
        Add-Result 'Backend Core /dependencies/ (staff)' 'OK' "db=$($dep.dependencies.database.status) ie=$($dep.dependencies.intelligence_engine.status) cr=$($dep.dependencies.content_renderer.status)"
    } catch {
        Add-Result 'Backend Core /dependencies/ (staff)' 'FAIL' $_.Exception.Message
    }
} else {
    Add-Result 'Backend Core /dependencies/ (staff)' 'SKIPPED' 'STAGING_STAFF_ACCESS_TOKEN não definido, ou /live/ já falhou'
}

# --- Intelligence Engine ---
$ieHealth = Test-HttpOk -Url 'http://127.0.0.1:8201/health'
if ($ieHealth.Ok) {
    try {
        $body = Invoke-RestMethod -Uri 'http://127.0.0.1:8201/health' -TimeoutSec 3
        $ok = $body.service -eq 'intelligence_engine'
        Add-Result 'Intelligence Engine /health' $(if ($ok) { 'OK' } else { 'FAIL' }) "service=$($body.service)"
    } catch {
        Add-Result 'Intelligence Engine /health' 'FAIL' $_.Exception.Message
    }
} else {
    Add-Result 'Intelligence Engine /health' 'DOWN' 'não respondeu (serviço opcional, processo local)'
}

# --- Content Renderer ---
$crHealth = Test-HttpOk -Url 'http://127.0.0.1:8202/health'
if ($crHealth.Ok) {
    try {
        $body = Invoke-RestMethod -Uri 'http://127.0.0.1:8202/health' -TimeoutSec 3
        $ok = $body.service -eq 'content_renderer'
        Add-Result 'Content Renderer /health' $(if ($ok) { 'OK' } else { 'FAIL' }) "service=$($body.service)"
    } catch {
        Add-Result 'Content Renderer /health' 'FAIL' $_.Exception.Message
    }
} else {
    Add-Result 'Content Renderer /health' 'DOWN' 'não respondeu (serviço opcional, processo local)'
}

# --- Frontend ---
$feHealth = Test-HttpOk -Url 'http://127.0.0.1:5200/'
if ($feHealth.Ok) {
    try {
        $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:5200/' -UseBasicParsing -TimeoutSec 3
        $ok = $resp.Content -match 'id="root"' -and $resp.Content -match 'src/main\.tsx'
        Add-Result 'Frontend (Vite dev)' $(if ($ok) { 'OK' } else { 'FAIL' }) $(if ($ok) { 'marcador esperado encontrado' } else { 'resposta não corresponde ao index.html deste frontend' })
    } catch {
        Add-Result 'Frontend (Vite dev)' 'FAIL' $_.Exception.Message
    }
} else {
    Add-Result 'Frontend (Vite dev)' 'DOWN' 'não respondeu (serviço opcional, processo local)'
}

Write-Output ''
$results | Format-Table -Property Name, Status, Detail -AutoSize | Out-String | Write-Output

$infraOk = ($results | Where-Object { $_.Name -like '*container*' -and $_.Status -ne 'OK' }).Count -eq 0
$appsFailed = ($results | Where-Object { $_.Name -notlike '*container*' -and $_.Status -eq 'FAIL' }).Count -gt 0
$appsDown = ($results | Where-Object { $_.Status -eq 'DOWN' }).Count -gt 0

if (-not $infraOk) {
    Write-Output 'RESULTADO: FALHOU — infraestrutura obrigatória (PostgreSQL/MinIO) não está saudável.'
    exit 1
}
if ($appsFailed) {
    Write-Output 'RESULTADO: FALHOU — pelo menos um serviço aplicacional respondeu, mas com identidade/estado incorrecto (ver FAIL acima).'
    exit 1
}
if ($RequireApps -and $appsDown) {
    Write-Output 'RESULTADO: FALHOU — -RequireApps pedido e pelo menos um serviço aplicacional está DOWN.'
    exit 1
}

Write-Output 'RESULTADO: OK — infraestrutura saudável; serviços aplicacionais correctos (os que estiverem activos identificam-se correctamente).'
exit 0
