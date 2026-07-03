# =============================================================================
# staging-local-common.ps1 — Funções partilhadas pelos scripts staging-local-*.
#
# Não é executável directamente — é importado (dot-sourced) pelos outros
# scripts em scripts\staging-local-*.ps1 (STG-LOCAL-006).
#
# Nenhuma função aqui imprime valores de secrets — Import-DotEnvFile só
# reporta NOMES de variável carregadas, nunca valores.
# =============================================================================

function Get-RepoRoot {
    # Este ficheiro vive em <repo>\scripts\lib\, por isso sobe dois níveis.
    return (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
}

<#
.SYNOPSIS
Carrega um ficheiro .env (KEY=VALUE por linha) para $env: do processo actual.

.DESCRIPTION
Réplica em PowerShell do padrão `set -a && . ./ficheiro && set +a` já usado
manualmente nesta fase (Prompts 03-05). Ignora linhas vazias e comentários
(`#`). Não sobrepõe uma variável já definida no ambiente do processo, salvo
-Force. Nunca imprime valores — só o nome da variável e o ficheiro de
origem, quando -Verbose está activo.
#>
function Import-DotEnvFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [switch]$Required,
        [switch]$Force
    )
    if (-not (Test-Path $Path)) {
        if ($Required) {
            throw "Ficheiro de ambiente obrigatório não encontrado: $Path"
        }
        Write-Verbose "Ficheiro de ambiente opcional ausente, a ignorar: $Path"
        return
    }
    $loaded = @()
    foreach ($line in Get-Content -Path $Path) {
        $trimmed = $line.Trim()
        if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { continue }
        $eq = $trimmed.IndexOf('=')
        if ($eq -lt 1) { continue }
        $key = $trimmed.Substring(0, $eq).Trim()
        $value = $trimmed.Substring($eq + 1)
        $alreadySet = [System.Environment]::GetEnvironmentVariable($key)
        if ($alreadySet -and -not $Force) {
            continue
        }
        [System.Environment]::SetEnvironmentVariable($key, $value)
        $loaded += $key
    }
    Write-Verbose "Carregadas $($loaded.Count) variável(is) de $Path (nomes: $($loaded -join ', '))"
}

<#
.SYNOPSIS
Verifica um endpoint HTTP uma única vez, sem lançar excepção.
Devolve um objecto { Ok, StatusCode, Error }.
#>
function Test-HttpOk {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [int]$TimeoutSec = 5
    )
    try {
        # Sem Accept fixo: um "Accept: application/json" quebrava o Vite dev
        # server (devolvia 404 em vez do index.html) — confirmado nesta
        # iteração. Os endpoints de health JSON (Django/FastAPI/Express)
        # respondem JSON independentemente do Accept enviado.
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
        return [pscustomobject]@{ Ok = ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300); StatusCode = $resp.StatusCode; Error = $null }
    } catch {
        $status = $null
        if ($_.Exception.Response) {
            try { $status = [int]$_.Exception.Response.StatusCode } catch {}
        }
        return [pscustomobject]@{ Ok = $false; StatusCode = $status; Error = $_.Exception.Message }
    }
}

<#
.SYNOPSIS
Espera até um endpoint HTTP responder 2xx, ou esgotar o timeout.
#>
function Wait-ForHttpOk {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [int]$TimeoutSec = 30,
        [int]$IntervalMs = 500
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $r = Test-HttpOk -Url $Url -TimeoutSec 3
        if ($r.Ok) { return $true }
        Start-Sleep -Milliseconds $IntervalMs
    }
    return $false
}

<#
.SYNOPSIS
Estado de healthcheck Docker de um container ('healthy'|'unhealthy'|'starting'|
'no-healthcheck'|'not-found').
#>
function Get-ContainerHealth {
    param([Parameter(Mandatory = $true)][string]$ContainerName)
    $exists = docker ps -a --filter "name=^/$ContainerName$" --format '{{.Names}}' 2>$null
    if (-not $exists) { return 'not-found' }
    $health = docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' $ContainerName 2>$null
    if (-not $health) { return 'unknown' }
    return $health.Trim()
}

<#
.SYNOPSIS
Devolve o único PID (int) a ocupar uma porta local, ou $null se nenhum.
#>
function Get-PortOwnerPid {
    param([Parameter(Mandatory = $true)][int]$Port)
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $conns) { return $null }
    $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    if ($pids.Count -ge 1) { return $pids[0] }
    return $null
}

<#
.SYNOPSIS
Pára um processo e TODOS os seus descendentes.

.DESCRIPTION
`Start-Process -FilePath 'npx.cmd'/'pnpm.cmd'` devolve o PID do wrapper
cmd.exe, não o do processo Node.js real que acaba a ocupar a porta —
confirmado nesta iteração: parar só o PID guardado deixava o Node
(neto do processo rastreado) vivo e a servir a porta. Esta função
resolve a árvore inteira (via Win32_Process.ParentProcessId) e pára-a de
fora para dentro (filhos antes do pai, para não perder a referência a meio).
#>
function Stop-ProcessTree {
    param([Parameter(Mandatory = $true)][int]$ProcessId)

    $toStop = New-Object System.Collections.Generic.List[int]
    $frontier = New-Object System.Collections.Generic.Queue[int]
    $frontier.Enqueue($ProcessId)
    while ($frontier.Count -gt 0) {
        $current = $frontier.Dequeue()
        $toStop.Add($current)
        $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $current" -ErrorAction SilentlyContinue
        foreach ($c in $children) { $frontier.Enqueue($c.ProcessId) }
    }
    # Filhos primeiro (ordem inversa à descoberta em largura, aproximação suficiente aqui).
    for ($i = $toStop.Count - 1; $i -ge 0; $i--) {
        Stop-Process -Id $toStop[$i] -Force -ErrorAction SilentlyContinue
    }
    return $toStop
}

function Get-RuntimeDir {
    $dir = Join-Path (Get-RepoRoot) '.local-runtime'
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $dir 'pids') | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $dir 'logs') | Out-Null
    return $dir
}
