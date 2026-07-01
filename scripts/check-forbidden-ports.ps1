# =============================================================================
# check-forbidden-ports.ps1 — Valida que nenhum ficheiro activo do projecto
# referencia as portas proibidas do ecossistema MomentFlow / ChartRex.
#
# Portas proibidas: 8000, 8001, 8002, 8003, 1420, 9011, 5173, 5174, 8080-8085.
# Portas canónicas (ver docs/configuracao/portas_projeto.md):
#   Frontend Web:  5200  | Frontend Preview: 5201
#   Backend Core:  8100  | Intelligence Engine: 8201 | Content Renderer: 8202
#
# Uso (a partir da raiz do repositório):
#   pwsh -ExecutionPolicy Bypass -File scripts\check-forbidden-ports.ps1
#
# Saída: lista de violações encontradas; exit code 0 se limpo, 1 se houver
# violações.
#
# Exclusões (ficheiros que podem referenciar portas antigas como evidência
# histórica, não como configuração activa):
#   - resultados_execucao/  (relatórios históricos de execução)
#   - /resultados/          (idem)
#   - node_modules/
#   - venv/ e .venv/
#   - .git/
#   - __pycache__/
#   - coverage/
#   - dist/
#   - este próprio script (check-forbidden-ports.ps1)
#   - estado_frontend_foundation_campaign_war_room.md  (FE-016 ran against old ports — historical fact)
#   - estado_campaign_actions_backend_integration.md   (describes past failed validation — historical fact)
# =============================================================================

$ErrorActionPreference = 'Continue'

$root = Split-Path -Parent $PSScriptRoot

# Padrão regex das portas proibidas.
# Foca em referências a localhost/127.0.0.1 com a porta proibida, ou atribuições
# de variável PORT=PORTA. Não assinala URLs de container (e.g. http://renderer:8002)
# nem comentários históricos em docs de estado.
$portPattern = '(?:localhost|127\.0\.0\.1):(8000|8001|8002|8003|8080|8081|8082|8083|8084|8085|1420|9011|5173|5174)\b|(?<![:/a-zA-Z])PORT\s*=\s*(8000|8001|8002|8003|8080|8081|8082|8083|8084|8085|1420|9011|5173|5174)\b'

# Extensões a verificar
$extensions = @('*.py', '*.ts', '*.tsx', '*.js', '*.mjs', '*.json', '*.env',
                '*.ps1', '*.sh', '*.md', '*.toml', '*.cfg', '*.ini', '*.yml', '*.yaml')

# Pastas/ficheiros a excluir
$excludeDirs = @(
    'node_modules', 'venv', '.venv', '__pycache__', '.git',
    'coverage', 'dist', 'resultados_execucao', 'resultados',
    'e2e-logs'
)

# Ficheiros específicos com evidências históricas de portas antigas (execuções passadas)
$excludeFiles = @(
    'estado_frontend_foundation_campaign_war_room.md',
    'estado_campaign_actions_backend_integration.md'
)

$violations = [System.Collections.Generic.List[string]]::new()

foreach ($ext in $extensions) {
    $files = Get-ChildItem -Path $root -Filter $ext -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object {
            $path = $_.FullName
            # Excluir este próprio script
            if ($path -eq $PSCommandPath) { return $false }
            # Excluir directorias proibidas
            foreach ($exclude in $excludeDirs) {
                if ($path -match [regex]::Escape([System.IO.Path]::DirectorySeparatorChar + $exclude + [System.IO.Path]::DirectorySeparatorChar) -or
                    $path -match [regex]::Escape([System.IO.Path]::DirectorySeparatorChar + $exclude + '$')) {
                    return $false
                }
            }
            # Excluir ficheiros históricos específicos
            foreach ($excludeFile in $excludeFiles) {
                if ($_.Name -eq $excludeFile) { return $false }
            }
            return $true
        }

    foreach ($file in $files) {
        $lineNum = 0
        Get-Content $file.FullName -ErrorAction SilentlyContinue | ForEach-Object {
            $lineNum++
            if ($_ -match $portPattern) {
                $relative = $file.FullName.Substring($root.Length + 1)
                $violations.Add("${relative}:${lineNum}: $_")
            }
        }
    }
}

if ($violations.Count -eq 0) {
    Write-Output 'check-forbidden-ports: OK — nenhuma porta proibida encontrada em ficheiros activos.'
    exit 0
} else {
    Write-Output "check-forbidden-ports: FALHA — $($violations.Count) referência(s) a portas proibidas encontrada(s):"
    foreach ($v in $violations) {
        Write-Output "  $v"
    }
    Write-Output ''
    Write-Output 'Portas proibidas: 8000, 8001, 8002, 8003, 1420, 9011, 5173, 5174, 8080-8085'
    Write-Output 'Portas canónicas: Backend Core=8100, IE=8201, Renderer=8202, FE=5200, FE Preview=5201'
    Write-Output 'Referência: docs/configuracao/portas_projeto.md'
    exit 1
}
