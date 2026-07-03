# =============================================================================
# staging-local-apps-up.ps1 — Arranca os serviços aplicacionais desta fase
# como processos locais (Frontend, Backend Core, Intelligence Engine,
# Content Renderer) — NÃO containerizados, por decisão da arquitectura desta
# fase (STG-LOCAL-006; ver arquitectura_staging_local.md §6.2).
#
# Cada serviço lê o seu próprio <serviço>\.env.staging.local (ignorado pelo
# git) antes de arrancar. Requer que a infraestrutura (PostgreSQL/MinIO) já
# esteja de pé — correr staging-local-infra-up.ps1 primeiro.
#
# Antes de arrancar cada serviço, confirma que a porta-alvo está livre. Se
# já estiver ocupada por um processo NÃO controlado por este script,
# **não mata esse processo** (podia ser trabalho do operador, ou um processo
# órfão de outra sessão — matar processos desconhecidos às cegas já causou
# falsos-negativos de smoke test nesta fase, ver Prompts 03/04) — em vez
# disso avisa e salta esse serviço.
#
# PIDs ficam guardados em .local-runtime\pids\<serviço>.pid, para que
# staging-local-apps-down.ps1 saiba exactamente o que parar (e só isso).
# Logs ficam em .local-runtime\logs\<serviço>.out.log / .err.log.
#
# Uso:
#   pwsh -ExecutionPolicy Bypass -File scripts\staging-local-apps-up.ps1
#   pwsh -ExecutionPolicy Bypass -File scripts\staging-local-apps-up.ps1 -Services backend_core,content_renderer
# =============================================================================
param(
    [ValidateSet('backend_core', 'intelligence_engine', 'content_renderer', 'frontend')]
    [string[]]$Services = @('backend_core', 'intelligence_engine', 'content_renderer', 'frontend'),
    # 45s por defeito: o Vite pode demorar bem mais do que os ~300ms do seu
    # próprio log "ready" quando precisa de re-optimizar dependências (lockfile
    # mudou) — confirmado nesta iteração a levar >30s de parede antes do
    # primeiro pedido HTTP responder.
    [int]$WaitTimeoutSec = 45
)

. (Join-Path $PSScriptRoot 'lib\staging-local-common.ps1')

$root = Get-RepoRoot
$runtime = Get-RuntimeDir

$defs = @{
    backend_core         = [pscustomobject]@{
        Dir        = Join-Path $root 'backend_core'
        EnvFile    = Join-Path $root 'backend_core\.env.staging.local'
        Exe        = Join-Path $root 'backend_core\venv\Scripts\python.exe'
        Args       = @('manage.py', 'runserver', '127.0.0.1:8100', '--noreload')
        Port       = 8100
        HealthUrl  = 'http://127.0.0.1:8100/api/v1/system/health/live/'
    }
    intelligence_engine  = [pscustomobject]@{
        Dir        = Join-Path $root 'intelligence_engine'
        EnvFile    = Join-Path $root 'intelligence_engine\.env.staging.local'
        Exe        = Join-Path $root 'intelligence_engine\venv\Scripts\python.exe'
        Args       = @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8201')
        Port       = 8201
        HealthUrl  = 'http://127.0.0.1:8201/health'
    }
    content_renderer     = [pscustomobject]@{
        Dir        = Join-Path $root 'content_renderer'
        EnvFile    = Join-Path $root 'content_renderer\.env.staging.local'
        Exe        = 'npx.cmd'
        Args       = @('tsx', 'src/server.ts')
        Port       = 8202
        HealthUrl  = 'http://127.0.0.1:8202/health'
    }
    frontend             = [pscustomobject]@{
        Dir        = Join-Path $root 'frontend'
        EnvFile    = $null
        Exe        = 'pnpm.cmd'
        # --host 127.0.0.1: o Vite, sem --host explícito, liga-se só a ::1
        # nesta máquina (confirmado nesta iteração) — o mesmo tipo de
        # ambiguidade IPv4/IPv6 já documentado para o Intelligence Engine em
        # docs/configuracao/portas_projeto.md. Forçar IPv4 aqui evita que
        # este script (e o healthcheck) fiquem a apontar para um endereço
        # que o browser/curl a testar 127.0.0.1 nunca alcança.
        Args       = @('dev', '--host', '127.0.0.1')
        Port       = 5200
        HealthUrl  = 'http://127.0.0.1:5200/'
    }
}

Write-Output '== staging-local-apps-up =='

foreach ($name in $Services) {
    $d = $defs[$name]
    Write-Output ''
    Write-Output "--- $name ---"

    $existingPid = Get-PortOwnerPid -Port $d.Port
    if ($existingPid) {
        Write-Output "SALTADO — porta $($d.Port) já ocupada pelo PID $existingPid (não gerido por este script). Confirmar manualmente antes de continuar (ver runbook: processos orfãos de sessoes anteriores ja causaram falsos-positivos nesta fase)."
        continue
    }

    if (-not (Test-Path $d.Exe) -and $d.Exe -notmatch '\.cmd$') {
        Write-Output "SALTADO — executável não encontrado: $($d.Exe). Confirmar que o venv/dependências existem."
        continue
    }

    $pidFile = Join-Path $runtime "pids\$name.pid"
    $outLog = Join-Path $runtime "logs\$name.out.log"
    $errLog = Join-Path $runtime "logs\$name.err.log"

    if ($d.EnvFile) {
        Import-DotEnvFile -Path $d.EnvFile -Required:$false
    }

    $proc = Start-Process -FilePath $d.Exe -ArgumentList $d.Args -WorkingDirectory $d.Dir `
        -WindowStyle Hidden -PassThru -RedirectStandardOutput $outLog -RedirectStandardError $errLog
    Set-Content -Path $pidFile -Value $proc.Id

    Write-Output "Arrancado PID $($proc.Id), a aguardar $($d.HealthUrl) (timeout ${WaitTimeoutSec}s)..."
    $up = Wait-ForHttpOk -Url $d.HealthUrl -TimeoutSec $WaitTimeoutSec
    if ($up) {
        Write-Output "OK — $name saudável."
    } else {
        Write-Output "AVISO — $name não respondeu dentro do timeout. Ver logs: $outLog / $errLog"
    }
}

Write-Output ''
Write-Output 'Concluído. Usar scripts\staging-local-health.ps1 para uma verificação completa, ou scripts\staging-local-apps-down.ps1 para parar.'
