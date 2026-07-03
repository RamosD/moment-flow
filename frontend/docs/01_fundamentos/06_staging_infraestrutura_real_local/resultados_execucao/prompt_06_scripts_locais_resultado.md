# Prompt 06 — Criar scripts locais — Resultado

**Data:** 2026-07-03
**Fase:** `06_staging_infraestrutura_real_local` (STG-LOCAL-006)
**Âmbito:** criar scripts repetíveis para arrancar, validar, parar e (em
separado) resetar a stack staging local. Sem alterar produto.
**Estado de execução:** `executado` — 6 scripts PowerShell + 1 biblioteca
partilhada criados, todos validados por execução real (não só leitura de
código), incluindo dois bugs reais encontrados e corrigidos durante a
própria validação (ver §6).

---

## 1. Inspecção de scripts existentes

`find` confirmou apenas dois precedentes no repositório: `scripts/check-
forbidden-ports.ps1` (raiz — usado como referência de convenção: cabeçalho
`# ===`, `$root = Split-Path -Parent $PSScriptRoot`, `exit 0`/`exit 1`
explícitos) e três scripts `content_renderer/scripts/run-e2e-*.ps1`
(usados como referência de estilo: `Start-Process -PassThru`, redirecção
de output para logs, função `Wait-Up`/polling HTTP). Os scripts desta
iteração seguem a mesma convenção de cabeçalho e vivem em `scripts/`
(raiz), ao lado de `check-forbidden-ports.ps1` — não dentro de um serviço
específico, porque orquestram a stack inteira.

## 2. Scripts criados

| Script | Objectivo | Destrutivo? |
|---|---|---|
| `scripts/lib/staging-local-common.ps1` | Biblioteca partilhada (dot-sourced, não executável sozinha): `Import-DotEnvFile`, `Test-HttpOk`, `Wait-ForHttpOk`, `Get-ContainerHealth`, `Get-PortOwnerPid`, `Stop-ProcessTree`, `Get-RuntimeDir` | N/A |
| `scripts/staging-local-infra-up.ps1` | Sobe PostgreSQL + MinIO via `docker compose --env-file .env.staging.local`, aguarda healthchecks, confirma `minio-bucket-init` terminou com sucesso | Não |
| `scripts/staging-local-infra-down.ps1` | Pára os containers, confirma que os dois volumes continuam a existir depois | **Não** — nunca `-v` |
| `scripts/staging-local-infra-reset.ps1` | Apaga containers **e volumes** (`down -v`) | **Sim** — exige `-IAmSure` + confirmação escrita `"apagar"` (ou `-Force` para uso não-interactivo consciente) |
| `scripts/staging-local-apps-up.ps1` | Arranca Frontend/Backend Core/Intelligence Engine/Content Renderer como processos locais, um a um, cada um com o seu `.env.staging.local` carregado e healthcheck HTTP à espera | Não |
| `scripts/staging-local-apps-down.ps1` | Pára só os processos rastreados por `apps-up.ps1` (via PID + árvore completa), nunca "o que estiver na porta" | Não |
| `scripts/staging-local-health.ps1` | Verifica os 8 alvos pedidos, confirmando a **identidade** de cada resposta (não só HTTP 2xx) | Não |

Nomenclatura: prefixo `staging-local-` consistente em todos, um verbo claro
por ficheiro (`infra-up`/`infra-down`/`infra-reset`/`apps-up`/`apps-down`/
`health`) — nenhum nome ambíguo, nenhum script faz duas coisas.

## 3. Comandos validados (execução real, não simulada)

```powershell
# 1. Infra a partir de um estado parado
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-infra-down.ps1
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-infra-up.ps1

# 2. Health com infra em cima, apps ainda parados
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-health.ps1

# 3. Apps a arrancar (todos os 4)
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-apps-up.ps1

# 4. Health com tudo em cima, incluindo o healthcheck staff-only
$env:STAGING_STAFF_ACCESS_TOKEN = '<jwt de um utilizador is_staff=True>'
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-health.ps1 -RequireApps

# 5. Apps a parar
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-apps-down.ps1

# 6. Reset — só o bloqueio de segurança testado, NUNCA confirmado
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-infra-reset.ps1   # sem -IAmSure
```

Todos os 6 corridos com sucesso na sequência acima, incluindo dois ciclos
completos de `apps-up`→`apps-down` (o segundo já com as correcções do §6
aplicadas).

## 4. Healthchecks (resultado real da execução)

Com infra em cima e apps parados:

```text
PostgreSQL (container)              OK      healthy
MinIO (container)                   OK      healthy
Backend Core /live/                 DOWN    não respondeu (serviço opcional, processo local)
Backend Core /ready/                SKIPPED live já falhou
Backend Core /dependencies/ (staff) SKIPPED STAGING_STAFF_ACCESS_TOKEN não definido, ou /live/ já falhou
Intelligence Engine /health         DOWN    não respondeu (serviço opcional, processo local)
Content Renderer /health            DOWN    não respondeu (serviço opcional, processo local)
Frontend (Vite dev)                 DOWN    não respondeu (serviço opcional, processo local)
RESULTADO: OK
```

Com infra + todos os 4 apps em cima, e um `STAGING_STAFF_ACCESS_TOKEN` real
(concedi `is_staff=True` temporariamente ao utilizador de E2E só para este
teste, revertido logo a seguir):

```text
PostgreSQL (container)              OK      healthy
MinIO (container)                   OK      healthy
Backend Core /live/                 OK      service=backend_core
Backend Core /ready/                OK      http=200
Backend Core /dependencies/ (staff) OK      db=ok ie=ok cr=ok
Intelligence Engine /health         OK      service=intelligence_engine
Content Renderer /health            OK      service=content_renderer
Frontend (Vite dev)                 OK      marcador esperado encontrado
RESULTADO: OK
```

Confirmando o critério de rejeição "Health que passa com serviço errado":
o script **lê o corpo da resposta** de cada endpoint (`service=...`) antes
de reportar `OK` — não se contenta com HTTP 2xx sozinho, precisamente para
nunca repetir o falso-positivo já visto nos Prompts 03/04 desta fase
(processo órfão a responder na porta certa, serviço errado).

## 5. Reset destrutivo

Testado **só** o bloqueio de segurança, nunca a confirmação real (regra
explícita do prompt: "Não executar reset destrutivo sem autorização"):

```text
$ pwsh -ExecutionPolicy Bypass -File scripts\staging-local-infra-reset.ps1
== staging-local-infra-reset — RESET DESTRUTIVO ==
Isto vai apagar PERMANENTEMENTE os volumes chartrex_staging_postgres_data e chartrex_staging_minio_data.
...
Bloqueado: é necessário o switch -IAmSure para sequer considerar este script. Nada foi alterado.
exitcode=1
```

Confirmado por `docker volume ls` imediatamente a seguir: os dois volumes
continuam intactos. O caminho de confirmação real (`-IAmSure` +
escrever `"apagar"`) foi validado só por leitura de código e pelo parser
de sintaxe — nunca invocado.

## 6. Achados reais durante a validação (dois bugs próprios, corrigidos)

### 6.1 `Accept: application/json` quebrava o healthcheck do Frontend

`Test-HttpOk` (biblioteca partilhada) enviava sempre `Accept:
application/json`. Os endpoints JSON (Django/FastAPI/Express) ignoram o
`Accept` e respondem sempre JSON, mas o **Vite dev server devolvia `404`**
a um pedido com esse header em vez do `index.html`. Descoberto ao ver
`staging-local-health.ps1` reportar `Frontend DOWN` apesar de um `curl`
directo (sem esse header) devolver `200`. **Corrigido**: removido o header
`Accept` fixo de `Test-HttpOk` — nenhum dos quatro serviços exige um
`Accept` específico para o seu healthcheck.

### 6.2 `staging-local-apps-down.ps1` não parava o Node.js real por trás de `npx.cmd`/`pnpm.cmd`

`Start-Process -FilePath 'npx.cmd'`/`'pnpm.cmd'` devolve o PID do
**wrapper cmd.exe**, não o do processo Node.js que acaba a servir a porta.
`Stop-Process` no PID guardado matava só o wrapper — confirmado ao ver, a
seguir a `apps-down.ps1`, que as portas 8202 (Content Renderer) e 5200
(Frontend) continuavam `Listen`, ocupadas por PIDs diferentes dos
rastreados. **Corrigido**: nova função `Stop-ProcessTree` na biblioteca
partilhada, que resolve toda a árvore de processos (via
`Win32_Process.ParentProcessId`) e pára-a de fora para dentro. Revalidado:
segundo ciclo `apps-up`→`apps-down` deixou as 4 portas
(8100/8201/8202/5200) completamente livres, confirmado por
`Get-NetTCPConnection`.

### 6.3 (achado secundário, corrigido no mesmo momento) Vite liga-se só a `::1` sem `--host`

Ao investigar o 404 do §6.1, descobri que o Vite dev server, sem `--host`
explícito, se liga só a `::1` (IPv6) nesta máquina — o mesmo tipo de
ambiguidade IPv4/IPv6 já documentado neste projecto para o Intelligence
Engine (`docs/configuracao/portas_projeto.md`). `staging-local-apps-up.ps1`
já arranca o Vite com `--host 127.0.0.1` para evitar que o script (ou
qualquer operador a testar `127.0.0.1:5200`) nunca alcance o serviço.

**Nenhum destes três achados envolveu alteração a código de produto** —
os três estão confinados aos scripts desta iteração.

## 7. Ficheiros criados/alterados

| Ficheiro | Operação |
|---|---|
| `scripts/lib/staging-local-common.ps1` | **criado** |
| `scripts/staging-local-infra-up.ps1` | **criado** |
| `scripts/staging-local-infra-down.ps1` | **criado** |
| `scripts/staging-local-infra-reset.ps1` | **criado** |
| `scripts/staging-local-apps-up.ps1` | **criado** |
| `scripts/staging-local-apps-down.ps1` | **criado** |
| `scripts/staging-local-health.ps1` | **criado** (+ 1 correcção pós-validação, §6.1) |
| `.gitignore` (raiz) | alterado — `.local-runtime/` (PIDs/logs dos scripts) adicionado |
| `frontend/docs/.../06_staging_infraestrutura_real_local/runbook_staging_local.md` | **criado** — runbook inicial/parcial (infra, secrets, scripts; quality gate/E2E/segurança/observabilidade ficam para os Prompts 07–10) |
| `frontend/docs/.../resultados_execucao/prompt_06_scripts_locais_resultado.md` | **criado** (este relatório) |

Nenhum ficheiro de código de produto foi tocado.

## 8. Validações executadas

| Validação | Resultado |
|---|---|
| `[System.Management.Automation.Language.Parser]::ParseFile` nos 7 ficheiros `.ps1` | ✅ 0 erros de sintaxe (validado duas vezes — antes e depois das correcções do §6) |
| `staging-local-infra-down.ps1` → `staging-local-infra-up.ps1` (ciclo real) | ✅ PostgreSQL/MinIO `healthy`, bucket confirmado |
| `staging-local-health.ps1` (infra only) | ✅ resultado correcto — infra OK, apps DOWN, exit 0 |
| `staging-local-apps-up.ps1` (4 serviços) — 1ª tentativa | ⚠️ 2/4 healthy, 2/4 timeout aparente (na verdade já estavam de pé — falso-negativo do próprio script de teste, ver §6.1) |
| `staging-local-apps-up.ps1` (4 serviços) — 2ª tentativa, pós-correcção | ✅ 4/4 healthy na primeira tentativa |
| `staging-local-health.ps1 -RequireApps` (tudo em cima, com token staff) | ✅ 8/8 `OK`, exit 0 |
| `staging-local-apps-down.ps1` — 1ª tentativa | ⚠️ portas 8202/5200 continuaram ocupadas (bug §6.2) |
| `staging-local-apps-down.ps1` — 2ª tentativa, pós-correcção | ✅ 4/4 portas livres, confirmado por `Get-NetTCPConnection` |
| `staging-local-infra-reset.ps1` sem `-IAmSure` | ✅ bloqueado, exit 1, volumes intactos (confirmado por `docker volume ls`) |
| `scripts/check-forbidden-ports.ps1` | ✅ OK |
| Grep de `password\|secret\|token\|api_key\|private_key` (case-insensitive) nos 7 scripts | ✅ só nomes de variável/comentários a explicar que nunca são impressos (`STAGING_STAFF_ACCESS_TOKEN` é um JWT de acesso passado por variável de ambiente pelo operador, nunca hardcoded no script) |
| Mesmo grep no runbook novo | ✅ idem |
| `git check-ignore -q .local-runtime` | ✅ ignorado |

## 9. Limitações

- `staging-local-apps-up.ps1` não valida que o `venv`/`node_modules` de
  cada serviço está instalado antes de tentar arrancar (falha com uma
  mensagem do próprio processo, não uma verificação prévia dedicada).
- O caminho de confirmação real do reset destrutivo (`-IAmSure` + escrever
  `"apagar"`) não foi exercido end-to-end nesta iteração — só o bloqueio.
  Fica para quando um reset real for genuinamente necessário (ex.:
  STG-LOCAL-012, fecho da fase).
- `staging-local-health.ps1` não valida MinIO ao nível aplicacional (só o
  healthcheck do container) — não confirma, por exemplo, que o bucket
  ainda existe ou que as credenciais configuradas nos serviços continuam
  válidas. Isso está mais próximo do âmbito de STG-LOCAL-010
  (observabilidade).
- `staging-local-apps-up.ps1` assume PowerShell 7+ (`pwsh`) e Windows
  (caminhos `venv\Scripts\python.exe`, `.cmd`) — não portátil para
  Linux/macOS tal como está; consistente com o resto do repositório, que já
  assume Windows nesta fase.

## 10. Riscos

| Risco | Situação após este prompt |
|---|---|
| LOCAL-R07 — E2E instável por ordem de arranque incorrecta | Mitigado pela ordem documentada e pelos healthchecks explícitos antes de avançar |
| Processos órfãos de sessões anteriores a mascarar resultados (risco descoberto nos Prompts 03/04, não no backlog original) | **Mitigado estruturalmente**: `apps-up.ps1` nunca arranca por cima de uma porta já ocupada por um processo não-gerido (avisa e salta); `apps-down.ps1` só pára o que arrancou, por PID + árvore completa |
| Reset destrutivo accionado por engano | Mitigado por dois níveis de confirmação (`-IAmSure` + texto exacto), scripts fisicamente separados |
| `.local-runtime/` (PIDs/logs) acumular ficheiros ao longo do tempo | Baixo — só texto, sem dados sensíveis (logs podem conter tokens se um serviço os imprimir por bug próprio; nenhum dos 4 serviços desta stack faz isso, confirmado nos Prompts 04/05) |

## 11. Próximo passo recomendado

Avançar para **STG-LOCAL-007** (Prompt 07 do pipeline): criar um quality
gate local que corra `python manage.py check`, as suites `pytest`/`vitest`,
lint/build do frontend, `check-forbidden-ports.ps1` e greps de secrets num
único comando reutilizável — usando, quando fizer sentido, os scripts desta
iteração (`staging-local-infra-up.ps1`, `staging-local-health.ps1`) como
pré-condição para o modo opcional com E2E.
