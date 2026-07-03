# =============================================================================
# staging-local-infra-down.ps1 — Pára a infraestrutura local (PostgreSQL +
# MinIO) SEM apagar volumes. Os dados persistem para o próximo
# staging-local-infra-up.ps1 (STG-LOCAL-006).
#
# Para apagar dados de propósito, usar staging-local-infra-reset.ps1 — um
# script SEPARADO e destrutivo, nunca este.
#
# Uso:
#   pwsh -ExecutionPolicy Bypass -File scripts\staging-local-infra-down.ps1
# =============================================================================

. (Join-Path $PSScriptRoot 'lib\staging-local-common.ps1')

$ErrorActionPreference = 'Stop'
$root = Get-RepoRoot
$compose = Join-Path $root 'docker-compose.staging.local.yml'
$envFile = Join-Path $root '.env.staging.local'

if (-not (Test-Path $compose)) {
    Write-Error "Compose não encontrado: $compose"
    exit 1
}

Write-Output "== staging-local-infra-down (não destrutivo — volumes preservados) =="

$composeArgs = @('-f', $compose)
if (Test-Path $envFile) { $composeArgs = @('--env-file', $envFile) + $composeArgs }

& docker compose @composeArgs down
$exitCode = $LASTEXITCODE

$pgVol = docker volume ls --filter name=chartrex_staging_postgres_data --format '{{.Name}}' 2>$null
$minioVol = docker volume ls --filter name=chartrex_staging_minio_data --format '{{.Name}}' 2>$null

Write-Output ''
Write-Output "Volume PostgreSQL preservado: $(if ($pgVol) { 'sim (' + $pgVol + ')' } else { 'NÃO ENCONTRADO' })"
Write-Output "Volume MinIO preservado:      $(if ($minioVol) { 'sim (' + $minioVol + ')' } else { 'NÃO ENCONTRADO' })"

if ($exitCode -ne 0) {
    Write-Error "docker compose down terminou com exit $exitCode."
    exit $exitCode
}
if (-not $pgVol -or -not $minioVol) {
    Write-Output ''
    Write-Output 'AVISO — pelo menos um volume esperado não foi encontrado. Se isto foi inesperado, investigar antes de assumir que os dados existem.'
    exit 1
}

Write-Output ''
Write-Output 'OK — containers parados, volumes intactos.'
exit 0
