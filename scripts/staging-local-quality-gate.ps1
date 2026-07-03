# =============================================================================
# staging-local-quality-gate.ps1 — Quality gate local, executável manualmente
# hoje e reutilizável por CI no futuro (STG-LOCAL-007).
#
# Corre, por esta ordem, contra a configuração de DEV normal de cada
# serviço (backend_core/.env, etc. — NÃO exige a stack Docker desta fase
# nem .env.staging.local; um runner de CI também não os teria):
#   1. python manage.py check           (Backend Core)
#   2. pytest                           (Backend Core, suite completa)
#   3. pytest                           (Intelligence Engine, suite completa)
#   4. tsc --noEmit + eslint + vitest   (Content Renderer)
#   5. npm test                         (Frontend, unidade)
#   6. eslint                           (Frontend, lint)
#   7. tsc -b && vite build             (Frontend, build)
#   8. scripts\check-forbidden-ports.ps1
#   9. grep de secrets em `git ls-files`
#
# Modo opcional com E2E (-WithE2E): exige a stack staging local ACTIVA
# (containers + 4 processos aplicacionais — ver staging-local-health.ps1) e
# E2E_PASSWORD definido no ambiente. NÃO corre por defeito — correr sem
# -WithE2E nunca depende de Docker nem de nenhum processo local a mais.
#
# Nunca mascara falhas: cada etapa reporta PASS/FAIL/SKIP explicitamente, o
# exit code final é não-zero se qualquer etapa obrigatória falhar, e a
# saída completa de cada comando falhado é reencaminhada para o ecrã (não
# engolida). Nenhuma etapa usa skip/xfail para "passar" artificialmente.
#
# Uso:
#   pwsh -ExecutionPolicy Bypass -File scripts\staging-local-quality-gate.ps1
#   pwsh -ExecutionPolicy Bypass -File scripts\staging-local-quality-gate.ps1 -WithE2E
#   pwsh -ExecutionPolicy Bypass -File scripts\staging-local-quality-gate.ps1 -Only backend_core,frontend_lint
# =============================================================================
param(
    [switch]$WithE2E,
    [string[]]$Only
)

. (Join-Path $PSScriptRoot 'lib\staging-local-common.ps1')

# Invocar via `pwsh -File ... -Only a,b` (processo aninhado, como fazem os
# outros scripts staging-local-*) nem sempre faz o PowerShell separar a
# lista em elementos — confirmado nesta iteração. Repartir explicitamente
# por vírgula torna -Only robusto seja qual for o caminho de invocação.
if ($Only) {
    $Only = $Only | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
}

$root = Get-RepoRoot
$results = New-Object System.Collections.Generic.List[object]

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList
    )
    if ($Only -and ($Only -notcontains $Name)) {
        Write-Output "[SKIP] $Name (fora de -Only)"
        $results.Add([pscustomobject]@{ Name = $Name; Status = 'SKIP'; Seconds = 0 })
        return
    }
    Write-Output ''
    Write-Output "== $Name =="
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    Push-Location $WorkingDirectory
    try {
        & $FilePath @ArgumentList
        $exit = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    $sw.Stop()
    $elapsed = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    if ($exit -eq 0) {
        Write-Output "[PASS] $Name (${elapsed}s)"
        $results.Add([pscustomobject]@{ Name = $Name; Status = 'PASS'; Seconds = $elapsed })
    } else {
        Write-Output "[FAIL] $Name — exit $exit (${elapsed}s). Ver output acima — nada foi escondido."
        $results.Add([pscustomobject]@{ Name = $Name; Status = 'FAIL'; Seconds = $elapsed })
    }
}

Write-Output '========================================================'
Write-Output ' staging-local-quality-gate'
Write-Output '========================================================'
$gateStart = [System.Diagnostics.Stopwatch]::StartNew()

# --- 1/2. Backend Core ---
$bcDir = Join-Path $root 'backend_core'
$bcPy = Join-Path $bcDir 'venv\Scripts\python.exe'
Invoke-Step -Name 'backend_core_check' -WorkingDirectory $bcDir -FilePath $bcPy -ArgumentList @('manage.py', 'check')
Invoke-Step -Name 'backend_core_pytest' -WorkingDirectory $bcDir -FilePath $bcPy -ArgumentList @('-m', 'pytest', '-q')

# --- 3. Intelligence Engine ---
$ieDir = Join-Path $root 'intelligence_engine'
$iePy = Join-Path $ieDir 'venv\Scripts\python.exe'
Invoke-Step -Name 'intelligence_engine_pytest' -WorkingDirectory $ieDir -FilePath $iePy -ArgumentList @('-m', 'pytest', '-q')

# --- 4. Content Renderer (typecheck + lint + tests — âmbito alargado
#         deliberadamente face à lista mínima do prompt, porque as três
#         validações já correm juntas em todos os fechos anteriores desta
#         fase; ver relatório §2 para a justificação) ---
$crDir = Join-Path $root 'content_renderer'
Invoke-Step -Name 'content_renderer_typecheck' -WorkingDirectory $crDir -FilePath 'npx.cmd' -ArgumentList @('tsc', '--noEmit')
Invoke-Step -Name 'content_renderer_lint' -WorkingDirectory $crDir -FilePath 'npx.cmd' -ArgumentList @('eslint', '.')
Invoke-Step -Name 'content_renderer_test' -WorkingDirectory $crDir -FilePath 'npx.cmd' -ArgumentList @('vitest', 'run')

# --- 5/6/7. Frontend ---
$feDir = Join-Path $root 'frontend'
Invoke-Step -Name 'frontend_test' -WorkingDirectory $feDir -FilePath 'pnpm.cmd' -ArgumentList @('test')
Invoke-Step -Name 'frontend_lint' -WorkingDirectory $feDir -FilePath 'pnpm.cmd' -ArgumentList @('lint')
Invoke-Step -Name 'frontend_build' -WorkingDirectory $feDir -FilePath 'pnpm.cmd' -ArgumentList @('build')

# --- 8. Portas proibidas ---
Invoke-Step -Name 'forbidden_ports' -WorkingDirectory $root -FilePath 'pwsh' -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $root 'scripts\check-forbidden-ports.ps1'))

# --- 9. Grep de secrets em git ls-files ---
# Só ficheiros TRACKED pelo git (nunca .env reais, sempre ignorados —
# ver STG-LOCAL-005). Nunca imprime o VALOR encontrado, só ficheiro:linha,
# para que este próprio script nunca se torne um sítio que imprime um
# segredo real, mesmo no caso (inesperado) de um ter sido commitado.
# Padrões claramente seguros (placeholders já documentados nesta fase e
# na fase 05) são excluídos para reduzir ruído; qualquer outro valor
# não-trivial faz esta etapa FALHAR.
if (-not $Only -or ($Only -contains 'secrets_grep')) {
    Write-Output ''
    Write-Output '== secrets_grep =='
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    # (?<![A-Za-z0-9_]) evita apanhar STRIPE_ dentro de HTTP_STRIPE_SIGNATURE=,
    # etc. — a chave tem de começar um identificador novo, não ser sufixo de
    # outro. O valor pára em espaço, backtick, pipe (tabelas markdown),
    # vírgula ou parêntese/aspa de fecho — para não engolir texto explicativo
    # a seguir a um exemplo. Uma aspa logo a seguir ao "=" (ex.: TOKEN="")
    # não casa nada em [^\s`|,)"']+, o que já trata "" e '' como vazio/seguro.
    # O valor é OU um placeholder <...> completo (pode conter espaços/vírgulas,
    # ex.: <definido, oculto>), OU um token sem espaços — tentado nesta ordem.
    $pattern = '(?<![A-Za-z0-9_])(INTERNAL_API_TOKEN|SECRET_KEY|DB_PASSWORD|MINIO_ROOT_PASSWORD|STORAGE_ACCESS_KEY|STORAGE_SECRET_KEY|E2E_PASSWORD|STRIPE_[A-Z_]+)=(<[^`|"''<>]*>|[^\s`|;)"'']+)'
    $safeMarker = '(?i)(change.?me|placeholder|example|dev.?only|local.?only|unused|deadbeef|test|smoke|token|^<.*>$|^postgres$|^\*+$)'
    $suspicious = New-Object System.Collections.Generic.List[string]
    $trackedFiles = & git -C $root ls-files
    foreach ($relPath in $trackedFiles) {
        $full = Join-Path $root $relPath
        if (-not (Test-Path $full -PathType Leaf)) { continue }
        try {
            $lines = Select-String -Path $full -Pattern $pattern -AllMatches -ErrorAction SilentlyContinue
        } catch { continue }
        foreach ($m in $lines) {
            foreach ($match in $m.Matches) {
                $value = $match.Groups[2].Value.Trim('`', '"', "'")
                if ($value -ne '' -and $value -notmatch $safeMarker) {
                    $suspicious.Add("${relPath}:$($m.LineNumber)")
                }
            }
        }
    }
    $sw.Stop()
    $elapsed = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    if ($suspicious.Count -eq 0) {
        Write-Output "[PASS] secrets_grep — $($trackedFiles.Count) ficheiros verificados, 0 suspeitos (${elapsed}s)."
        $results.Add([pscustomobject]@{ Name = 'secrets_grep'; Status = 'PASS'; Seconds = $elapsed })
    } else {
        Write-Output "[FAIL] secrets_grep — $($suspicious.Count) ocorrência(s) suspeita(s) (só ficheiro:linha, nunca o valor):"
        $suspicious | ForEach-Object { Write-Output "  $_" }
        $results.Add([pscustomobject]@{ Name = 'secrets_grep'; Status = 'FAIL'; Seconds = $elapsed })
    }
} else {
    Write-Output '[SKIP] secrets_grep (fora de -Only)'
    $results.Add([pscustomobject]@{ Name = 'secrets_grep'; Status = 'SKIP'; Seconds = 0 })
}

# --- Opcional: E2E contra a stack staging local activa ---
if ($WithE2E) {
    Write-Output ''
    Write-Output '== e2e (opcional, -WithE2E) =='
    $healthScript = Join-Path $root 'scripts\staging-local-health.ps1'
    $health = & pwsh -NoProfile -ExecutionPolicy Bypass -File $healthScript -RequireApps
    $healthExit = $LASTEXITCODE
    if ($healthExit -ne 0) {
        Write-Output '[FAIL] e2e — stack staging local não está totalmente activa (staging-local-health.ps1 -RequireApps falhou).'
        Write-Output '       Arrancar com staging-local-infra-up.ps1 + staging-local-apps-up.ps1 antes de pedir -WithE2E.'
        $results.Add([pscustomobject]@{ Name = 'e2e'; Status = 'FAIL'; Seconds = 0 })
    } elseif (-not $env:E2E_PASSWORD) {
        Write-Output '[FAIL] e2e — E2E_PASSWORD não está definido no ambiente. Exportar antes de correr com -WithE2E.'
        $results.Add([pscustomobject]@{ Name = 'e2e'; Status = 'FAIL'; Seconds = 0 })
    } else {
        Invoke-Step -Name 'e2e' -WorkingDirectory $feDir -FilePath 'pnpm.cmd' -ArgumentList @('test:e2e')
    }
} else {
    Write-Output ''
    Write-Output '[SKIP] e2e — não pedido (usar -WithE2E com a stack local activa e E2E_PASSWORD definido).'
    $results.Add([pscustomobject]@{ Name = 'e2e'; Status = 'SKIP'; Seconds = 0 })
}

$gateStart.Stop()
Write-Output ''
Write-Output '========================================================'
Write-Output ' RESUMO'
Write-Output '========================================================'
$results | Format-Table -Property Name, Status, Seconds -AutoSize | Out-String | Write-Output
Write-Output "Duração total: $([math]::Round($gateStart.Elapsed.TotalSeconds, 1))s"

$failed = $results | Where-Object { $_.Status -eq 'FAIL' }
if ($failed.Count -gt 0) {
    Write-Output ''
    Write-Output "RESULTADO: FALHOU — $($failed.Count) etapa(s) falharam: $(($failed | ForEach-Object { $_.Name }) -join ', ')"
    exit 1
}
Write-Output ''
Write-Output 'RESULTADO: OK — todas as etapas executadas passaram.'
exit 0
