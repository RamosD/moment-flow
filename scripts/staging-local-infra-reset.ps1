# =============================================================================
# staging-local-infra-reset.ps1 — RESET DESTRUTIVO da infraestrutura local.
#
# ⚠️  APAGA TODOS OS DADOS de PostgreSQL e MinIO desta stack local (todos os
#     workspaces, campanhas, artefactos, objectos no bucket de staging).
#     NÃO HÁ DESFAZER. Não é o mesmo que staging-local-infra-down.ps1 (que
#     preserva os volumes) — este script existe SEPARADAMENTE de propósito,
#     para que parar a stack nunca apague dados por acidente.
#
# Exige DUAS confirmações explícitas antes de agir:
#   1. o switch -IAmSure;
#   2. escrever literalmente "apagar" quando pedido interactivamente
#      (salvo -Force, para uso não-interactivo consciente, ex.: CI local).
#
# Uso:
#   pwsh -ExecutionPolicy Bypass -File scripts\staging-local-infra-reset.ps1 -IAmSure
# =============================================================================
param(
    [switch]$IAmSure,
    [switch]$Force
)

. (Join-Path $PSScriptRoot 'lib\staging-local-common.ps1')

$ErrorActionPreference = 'Stop'
$root = Get-RepoRoot
$compose = Join-Path $root 'docker-compose.staging.local.yml'
$envFile = Join-Path $root '.env.staging.local'

Write-Output '== staging-local-infra-reset — RESET DESTRUTIVO =='
Write-Output 'Isto vai apagar PERMANENTEMENTE os volumes chartrex_staging_postgres_data e chartrex_staging_minio_data.'
Write-Output 'Todos os dados de PostgreSQL e todos os objectos do bucket MinIO desta stack local serão perdidos.'
Write-Output ''

if (-not $IAmSure) {
    Write-Error 'Bloqueado: é necessário o switch -IAmSure para sequer considerar este script. Nada foi alterado.'
    exit 1
}

if (-not $Force) {
    $answer = Read-Host 'Escreva exactamente "apagar" para confirmar a perda permanente de dados (qualquer outra resposta cancela)'
    if ($answer -ne 'apagar') {
        Write-Output 'Cancelado pelo operador. Nada foi alterado.'
        exit 1
    }
}

Write-Output ''
Write-Output 'Confirmado. A remover containers, rede e volumes...'

$composeArgs = @('-f', $compose)
if (Test-Path $envFile) { $composeArgs = @('--env-file', $envFile) + $composeArgs }

& docker compose @composeArgs down -v
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Error "docker compose down -v terminou com exit $exitCode."
    exit $exitCode
}

Write-Output ''
Write-Output 'OK — infraestrutura e dados removidos. Correr staging-local-infra-up.ps1 para recriar (dados novos, vazios).'
exit 0
