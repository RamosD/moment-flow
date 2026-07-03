# =============================================================================
# staging-local-apps-down.ps1 — Pára os serviços aplicacionais arrancados por
# staging-local-apps-up.ps1 (STG-LOCAL-006).
#
# Só pára processos cujo PID está registado em .local-runtime\pids\<serviço>.pid
# — nunca "o que estiver a ocupar a porta". Isto é deliberado: matar um
# processo desconhecido só porque ocupa a porta certa já se revelou perigoso
# nesta fase (podia ser trabalho do operador). Se o PID guardado já não
# corresponder a um processo vivo, o ficheiro .pid é apenas removido.
#
# Não mexe na infraestrutura Docker (PostgreSQL/MinIO) — usar
# staging-local-infra-down.ps1 para isso.
#
# Uso:
#   pwsh -ExecutionPolicy Bypass -File scripts\staging-local-apps-down.ps1
#   pwsh -ExecutionPolicy Bypass -File scripts\staging-local-apps-down.ps1 -Services frontend
# =============================================================================
param(
    [ValidateSet('backend_core', 'intelligence_engine', 'content_renderer', 'frontend')]
    [string[]]$Services = @('backend_core', 'intelligence_engine', 'content_renderer', 'frontend')
)

. (Join-Path $PSScriptRoot 'lib\staging-local-common.ps1')

$runtime = Get-RuntimeDir

Write-Output '== staging-local-apps-down =='

foreach ($name in $Services) {
    $pidFile = Join-Path $runtime "pids\$name.pid"
    if (-not (Test-Path $pidFile)) {
        Write-Output "$name — sem PID registado (não foi arrancado por staging-local-apps-up.ps1, ou já parado)."
        continue
    }
    $procId = Get-Content $pidFile -ErrorAction SilentlyContinue
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc) {
        # Pára a árvore inteira, não só o PID guardado — necessário para
        # content_renderer/frontend, arrancados via npx.cmd/pnpm.cmd (o PID
        # guardado é o do wrapper cmd.exe, não o do Node.js real que serve a
        # porta; ver Stop-ProcessTree em lib\staging-local-common.ps1).
        $stopped = Stop-ProcessTree -ProcessId $procId
        Write-Output "$name — PID $procId parado (árvore: $($stopped -join ', '))."
    } else {
        Write-Output "$name — PID $procId já não estava vivo (processo terminou entretanto)."
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

Write-Output ''
Write-Output 'Concluído. A infraestrutura (PostgreSQL/MinIO) continua a correr — usar staging-local-infra-down.ps1 separadamente, se pretendido.'
