# =============================================================================
# cleanup-e2e-run.ps1 — Cleanup SEGURO, por --run-id, de dados de E2E/smoke
# (STG-HARD-006).
#
# NÃO é o reset destrutivo (staging-local-infra-reset.ps1) — esse continua
# separado, exige -IAmSure + escrever "apagar", e apaga TODOS os dados de
# PostgreSQL e MinIO. Este script apaga apenas o que pertence a um único
# --run-id (o mesmo token passado a seed_e2e_run), em dois passos:
#
#   1. PostgreSQL — via `manage.py cleanup_e2e_run` (Django resolve o
#      workspace/utilizador exactos do run-id e apaga em cascata só o que
#      lhes pertence — ver o próprio management command para o porquê de
#      cada modelo).
#   2. MinIO — objectos sob o prefixo `workspaces/<workspace_id>/`, derivado
#      do mesmo layout de chaves que o Content Renderer já usa
#      (`content_renderer/src/storage/s3-storage.ts`), usando as credenciais
#      ROOT do MinIO (o utilizador de serviço do Content Renderer,
#      STG-HARD-003, não tem `s3:ListBucket` nem `s3:DeleteObject` — de
#      propósito, não é ele que faz cleanup).
#
# Um --run-id que não corresponda a nada não é um erro — é idempotente
# (nada a fazer). Um --run-id vazio é sempre bloqueado.
#
# Uso:
#   # Pré-visualizar (Postgres + contagem MinIO), sem apagar nada:
#   pwsh -ExecutionPolicy Bypass -File scripts\cleanup-e2e-run.ps1 -RunId <id> -DryRun
#
#   # Limpar de facto (pede confirmação interactiva — escrever o run-id):
#   pwsh -ExecutionPolicy Bypass -File scripts\cleanup-e2e-run.ps1 -RunId <id>
#
#   # Não-interactivo (CI local/scripts) — salta a confirmação:
#   pwsh -ExecutionPolicy Bypass -File scripts\cleanup-e2e-run.ps1 -RunId <id> -Force
# =============================================================================
param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [switch]$DryRun,
    [switch]$Force
)

. (Join-Path $PSScriptRoot 'lib\staging-local-common.ps1')

$ErrorActionPreference = 'Stop'
$root = Get-RepoRoot

if ([string]::IsNullOrWhiteSpace($RunId)) {
    Write-Error 'Bloqueado: -RunId não pode ser vazio/só espaços. Nada foi alterado.'
    exit 1
}

$backendDir = Join-Path $root 'backend_core'
$pythonExe = Join-Path $backendDir 'venv\Scripts\python.exe'
if (-not (Test-Path $pythonExe)) {
    Write-Error "Interpretador Python não encontrado em $pythonExe. Confirmar o venv do backend_core."
    exit 1
}

Import-DotEnvFile -Path (Join-Path $backendDir '.env.staging.local') -Required:$false

Write-Output "== cleanup-e2e-run — run-id '$RunId' =="
Write-Output ''

# --- 1) Pré-visualização (sempre corre primeiro, mesmo fora de -DryRun) -----
Push-Location $backendDir
try {
    $previewLines = & $pythonExe manage.py cleanup_e2e_run "--run-id=$RunId" --dry-run 2>&1
    $previewExit = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($previewExit -ne 0) {
    Write-Output ($previewLines -join "`n")
    Write-Error "cleanup_e2e_run --dry-run falhou (exit $previewExit). Nada foi alterado."
    exit $previewExit
}

$previewJsonLine = ($previewLines | Select-Object -Last 1)
$preview = $previewJsonLine | ConvertFrom-Json

if (-not $preview.found) {
    Write-Output "Nada encontrado para run-id '$RunId' — já limpo ou nunca seedado. Nada a fazer (Postgres nem MinIO)."
    exit 0
}

Write-Output "PostgreSQL — dados encontrados para run-id '$RunId' (workspace $($preview.workspace_id)):"
$preview.counts.PSObject.Properties | ForEach-Object { Write-Output ("  {0,-22} {1}" -f $_.Name, $_.Value) }
Write-Output ''

# --- MinIO — contagem por prefixo, sempre que possível (mesmo em dry-run) --
$rootEnvFile = Join-Path $root '.env.staging.local'
$minioObjectCount = $null
if ((Test-Path $rootEnvFile) -and $preview.workspace_id) {
    Import-DotEnvFile -Path $rootEnvFile -Required:$false
    $bucket = if ($env:STORAGE_BUCKET) { $env:STORAGE_BUCKET } else { 'chartrex-staging' }
    $prefix = "workspaces/$($preview.workspace_id)/"
    $lsScript = "mc alias set root http://minio:9000 `"`$MINIO_ROOT_USER`" `"`$MINIO_ROOT_PASSWORD`" > /dev/null 2>&1 && mc ls --recursive `"root/$bucket/$prefix`" 2>/dev/null | wc -l"
    try {
        $minioObjectCount = (docker run --rm --network chartrex_staging_local --entrypoint /bin/sh `
            -e MINIO_ROOT_USER=$env:MINIO_ROOT_USER -e MINIO_ROOT_PASSWORD=$env:MINIO_ROOT_PASSWORD `
            minio/mc:latest -c $lsScript 2>$null | Select-Object -Last 1).Trim()
    } catch {
        $minioObjectCount = $null
    }
}
if ($null -ne $minioObjectCount) {
    Write-Output "MinIO — objectos sob workspaces/$($preview.workspace_id)/: $minioObjectCount"
} else {
    Write-Output "MinIO — não foi possível pré-contar objectos (MinIO em baixo, ou sem .env.staging.local na raiz). A limpeza de MinIO, se pedida, tentará mesmo assim e reportará o resultado."
}
Write-Output ''

if ($DryRun) {
    Write-Output 'Dry-run: nada foi alterado (nem PostgreSQL, nem MinIO).'
    exit 0
}

# --- 2) PostgreSQL — apagar de facto (confirmação interactiva no Python, ---
#         salvo -Force) -----------------------------------------------------
$cleanupArgs = @('manage.py', 'cleanup_e2e_run', "--run-id=$RunId")
if ($Force) { $cleanupArgs += '--yes' }

Push-Location $backendDir
try {
    & $pythonExe @cleanupArgs
    $cleanupExit = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($cleanupExit -ne 0) {
    Write-Output ''
    Write-Output "Cancelado ou falhado (exit $cleanupExit) — PostgreSQL não foi alterado (transacção atómica: tudo ou nada). MinIO não foi tocado."
    exit $cleanupExit
}

Write-Output ''
Write-Output 'PostgreSQL limpo com sucesso.'

# --- 3) MinIO — apagar de facto, só se o Postgres confirmou um workspace ---
if (-not $preview.workspace_id) {
    Write-Output 'Sem workspace_id resolvido — a saltar limpeza de MinIO (nada a apagar).'
    exit 0
}

if (-not (Test-Path $rootEnvFile)) {
    Write-Output "AVISO: $rootEnvFile não encontrado — não é possível limpar objectos MinIO automaticamente. Limpar manualmente sob workspaces/$($preview.workspace_id)/ com credenciais root, se necessário."
    exit 0
}

Import-DotEnvFile -Path $rootEnvFile -Required:$true
$bucket = if ($env:STORAGE_BUCKET) { $env:STORAGE_BUCKET } else { 'chartrex-staging' }
$prefix = "workspaces/$($preview.workspace_id)/"
$rmScript = "mc alias set root http://minio:9000 `"`$MINIO_ROOT_USER`" `"`$MINIO_ROOT_PASSWORD`" > /dev/null && mc rm --recursive --force `"root/$bucket/$prefix`""

Write-Output "A remover objectos MinIO sob $prefix ..."
docker run --rm --network chartrex_staging_local --entrypoint /bin/sh `
    -e MINIO_ROOT_USER=$env:MINIO_ROOT_USER -e MINIO_ROOT_PASSWORD=$env:MINIO_ROOT_PASSWORD `
    minio/mc:latest -c $rmScript
$minioExit = $LASTEXITCODE

if ($minioExit -ne 0) {
    Write-Output ''
    Write-Output "AVISO: limpeza de MinIO terminou com exit $minioExit (o bucket pode já não ter objectos sob este prefixo, ou o MinIO está em baixo). PostgreSQL já está limpo — este aviso não é revertível automaticamente; confirmar manualmente com 'mc ls --recursive' se necessário."
    exit 0
}

Write-Output ''
Write-Output "OK — run-id '$RunId' limpo em PostgreSQL e MinIO."
exit 0
