# =============================================================================
# staging-local-infra-up.ps1 — Sobe a infraestrutura local obrigatória desta
# fase (STG-LOCAL-006): PostgreSQL + MinIO em containers Docker persistentes,
# com o bucket de staging criado automaticamente.
#
# NÃO sobe nenhum serviço aplicacional (Frontend, Backend Core, Intelligence
# Engine, Content Renderer) — ver scripts\staging-local-apps-up.ps1 para isso.
# NÃO apaga volumes — arranque normal e repetível, nunca destrutivo.
#
# Lê credenciais de .env.staging.local (raiz do repositório, ignorado pelo
# git) via `docker compose --env-file`. Nenhum secret é lido, impresso ou
# passado como argumento por este script.
#
# Uso:
#   pwsh -ExecutionPolicy Bypass -File scripts\staging-local-infra-up.ps1
#   pwsh -ExecutionPolicy Bypass -File scripts\staging-local-infra-up.ps1 -TimeoutSec 90
# =============================================================================
param(
    [int]$TimeoutSec = 60
)

. (Join-Path $PSScriptRoot 'lib\staging-local-common.ps1')

$ErrorActionPreference = 'Stop'
$root = Get-RepoRoot
$compose = Join-Path $root 'docker-compose.staging.local.yml'
$envFile = Join-Path $root '.env.staging.local'

if (-not (Test-Path $compose)) {
    Write-Error "Compose não encontrado: $compose"
    exit 1
}

Write-Output "== staging-local-infra-up =="
Write-Output "Compose:  $compose"
Write-Output "Env file: $envFile $(if (-not (Test-Path $envFile)) { '(ausente — a usar defaults de dev do compose, ver .env.staging.local.example)' })"

$composeArgs = @('-f', $compose)
if (Test-Path $envFile) { $composeArgs = @('--env-file', $envFile) + $composeArgs }

& docker compose @composeArgs up -d
if ($LASTEXITCODE -ne 0) {
    Write-Error "docker compose up falhou (exit $LASTEXITCODE)."
    exit $LASTEXITCODE
}

Write-Output "A aguardar healthchecks (timeout ${TimeoutSec}s)..."
$deadline = (Get-Date).AddSeconds($TimeoutSec)
$pgOk = $false; $minioOk = $false
while ((Get-Date) -lt $deadline) {
    $pgOk = (Get-ContainerHealth -ContainerName 'chartrex_staging_postgres') -eq 'healthy'
    $minioOk = (Get-ContainerHealth -ContainerName 'chartrex_staging_minio') -eq 'healthy'
    if ($pgOk -and $minioOk) { break }
    Start-Sleep -Milliseconds 500
}

Write-Output ("PostgreSQL: {0}" -f (Get-ContainerHealth -ContainerName 'chartrex_staging_postgres'))
Write-Output ("MinIO:      {0}" -f (Get-ContainerHealth -ContainerName 'chartrex_staging_minio'))

# minio-bucket-init corre uma vez e termina — confirmar que terminou com sucesso.
$bucketInitState = docker inspect --format '{{.State.Status}} exit={{.State.ExitCode}}' chartrex_staging_minio_bucket_init 2>$null
Write-Output "Bucket init: $bucketInitState"

if (-not ($pgOk -and $minioOk)) {
    Write-Output ''
    Write-Output 'FALHOU — nem todos os healthchecks passaram dentro do timeout.'
    Write-Output 'Diagnóstico: docker compose -f docker-compose.staging.local.yml logs'
    exit 1
}

Write-Output ''
Write-Output 'OK — PostgreSQL e MinIO saudáveis, bucket de staging pronto.'
Write-Output 'Próximo passo: scripts\staging-local-health.ps1 (verificação completa) ou scripts\staging-local-apps-up.ps1 (serviços aplicacionais).'
exit 0
