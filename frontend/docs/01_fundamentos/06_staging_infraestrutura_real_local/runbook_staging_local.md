# Runbook — Staging Local Formal (MomentFlow / ChartRex)

> Fase: `06_staging_infraestrutura_real_local` (STG-LOCAL-012, fecho)
> Estado deste documento: **consolidado e fechado** — cobre tudo o que
> esta fase implementou e validou: infraestrutura Docker, secrets locais,
> scripts, migrations, seeds, storage MinIO, quality gate, segurança
> operacional, observabilidade **e E2E real (12/12 testes, executado no
> fecho da fase)** — ver §12. Validação por um terceiro sem contexto
> prévio continua pendente (§20) — não bloqueante, registado sem mascarar.
> Não descreve produção. Não descreve cloud. Sem secrets reais.

---

## 0. Antes de começar

Esta stack corre **inteiramente na máquina local**. PostgreSQL e MinIO são
containers Docker persistentes; Frontend, Backend Core, Intelligence Engine
e Content Renderer são processos locais (não containerizados nesta fase —
ver `arquitectura_staging_local.md` §6.2 para a justificação).

Este runbook assume que o leitor não tem contexto prévio da fase — cada
comando é dado por extenso, com o caminho relativo à raiz do repositório.

## 1. Pré-requisitos

- **Docker Desktop** instalado e a correr — confirmar com `docker info`
  (sem erro) antes de continuar. Se Docker não estiver disponível, esta
  fase **não pode ser validada como staging local formal** — não substituir
  por SQLite/filesystem para "passar" (ver §14, matriz de sintomas).
- **PowerShell 7+** (`pwsh`) — todos os scripts desta fase são `.ps1`.
- Ambientes de cada serviço já preparados:
  - `backend_core/venv/` e `intelligence_engine/venv/` (Python, `pip install -r requirements.txt`);
  - `content_renderer/node_modules/` e `frontend/node_modules/` (`npm install`/`pnpm install`).
- Ficheiros `*.env.staging.local` já criados (ver §4) — sem eles, os
  serviços aplicacionais arrancam com os defaults de dev do respectivo
  `.env.example`, que não apontam para o PostgreSQL/MinIO do container.

## 2. Portas canónicas

Fonte de verdade: [`docs/configuracao/portas_projeto.md`](../../../../docs/configuracao/portas_projeto.md).
**Portas proibidas** (nunca usar): 8000, 8001, 8002, 8003, 1420, 9011,
5173, 5174, 8080–8085 — validado por `scripts/check-forbidden-ports.ps1`.

| Serviço | Porta | Tipo |
|---|---|---|
| Frontend Web (Vite dev) | 5200 | processo local |
| Backend Core | 8100 | processo local |
| Intelligence Engine | 8201 | processo local |
| Content Renderer | 8202 | processo local |
| PostgreSQL | 5432 (default; ver nota de override) | container |
| MinIO S3 API | 9000 | container |
| MinIO Console | 9001 | container |

**Nota de override real:** nesta máquina de referência, um serviço Windows
nativo (`postgresql-x64-18`) já ocupa `127.0.0.1:5432`, pelo que o
container publica em `5433` via `.env.staging.local` → `POSTGRES_PORT=5433`
(achado real, ver `resultados_execucao/prompt_03_postgresql_local_resultado.md`
§10). Confirmar `POSTGRES_PORT`/`MINIO_API_PORT`/`MINIO_CONSOLE_PORT` no
`.env.staging.local` local antes de assumir os valores default.

**Todos os containers publicam em `127.0.0.1` explicitamente**, não
`0.0.0.0` — corrigido no STG-LOCAL-009 depois de se confirmar que o
default do Docker expunha PostgreSQL e MinIO a qualquer máquina na mesma
rede local, não só esta (ver §13).

## 3. Docker — infraestrutura (PostgreSQL + MinIO)

`docker-compose.staging.local.yml` (raiz do repositório) define **só** as
duas dependências que esta fase exige como containers locais persistentes:

| Serviço | Imagem | Persistência |
|---|---|---|
| `postgres` | `postgres:16-alpine` | Volume nomeado `chartrex_staging_postgres_data` |
| `minio` | `minio/minio:latest` | Volume nomeado `chartrex_staging_minio_data` |
| `minio-bucket-init` | `minio/mc:latest` | Serviço auxiliar de execução única — cria o bucket `chartrex-staging` e aplica a política de leitura anónima (só `s3:GetObject`, sem listagem — ver §13) |

Frontend, Backend Core, Intelligence Engine e Content Renderer **não**
estão neste compose — continuam processos locais (decisão da arquitectura
desta fase, não uma limitação técnica).

## 4. Env local / secrets

Um `.env.staging.local` por sítio, sempre ignorado pelo git
(`.gitignore`: `.env`, `.env.*`, exceptos os `*.example` explicitamente
negados):

| Ficheiro | Contém |
|---|---|
| `.env.staging.local` (raiz) | Credenciais do PostgreSQL/MinIO do compose — inclui `MINIO_ROOT_USER`/`PASSWORD` (só administração) **e**, desde STG-HARD-003, `MINIO_RENDERER_USER`/`PASSWORD` (utilizador de serviço do Content Renderer, policy mínima) |
| `backend_core/.env.staging.local` | `DB_*`, `INTERNAL_API_TOKEN`, `E2E_PASSWORD` |
| `intelligence_engine/.env.staging.local` | `INTERNAL_API_TOKEN` |
| `content_renderer/.env.staging.local` | `INTERNAL_API_TOKEN`, `STORAGE_*` |
| `frontend/` | Nenhum — o frontend não tem secrets (nem deve ter — nunca criar `VITE_INTERNAL_API_TOKEN` nem equivalente) |

`INTERNAL_API_TOKEN` tem de ser **byte-a-byte idêntico** nos três
ficheiros de serviço. Ver
`resultados_execucao/prompt_05_secrets_locais_resultado.md` para o
inventário completo e o procedimento de rotação testado.

**`ALLOW_INSECURE_EMPTY_TOKEN` nunca é uma opção válida de staging local**
— é uma *flag* exclusiva de desenvolvimento sem stack (Content Renderer),
confirmada `false`/ausente em todos os `.env.staging.local` desta fase.
Activá-la para "resolver" um problema de token dessincronizado esconde o
problema em vez de o corrigir — nunca fazer isto.

Os scripts desta fase (`scripts/staging-local-apps-up.ps1`) carregam
automaticamente o `.env.staging.local` de cada serviço via
`Import-DotEnvFile` (`scripts/lib/staging-local-common.ps1`) — não é
preciso `source` manual quando se usa os scripts.

## 5. Scripts disponíveis

Todos em `scripts/`, todos PowerShell, todos idempotentes:

| Script | Faz | Destrutivo? |
|---|---|---|
| `staging-local-infra-up.ps1` | Sobe PostgreSQL + MinIO (containers), aguarda healthchecks, confirma bucket criado | Não |
| `staging-local-infra-down.ps1` | Pára os containers, **preserva os volumes** | Não |
| `staging-local-infra-reset.ps1` | Apaga containers **e volumes** (todos os dados) | **Sim — ver §17, separado de propósito** |
| `staging-local-apps-up.ps1` | Arranca Frontend/Backend Core/Intelligence Engine/Content Renderer como processos locais, um a um, com healthcheck | Não |
| `staging-local-apps-down.ps1` | Pára só os processos arrancados por `apps-up.ps1` (por PID rastreado, árvore completa) | Não |
| `staging-local-health.ps1` | Verifica infraestrutura + serviços aplicacionais activos, confirmando a **identidade** de cada resposta, não só o HTTP 2xx | Não |
| `staging-local-quality-gate.ps1` | Corre todas as suites de validação (§11) num único comando | Não |
| `cleanup-e2e-run.ps1` (STG-HARD-006) | Apaga PostgreSQL + MinIO de **um único `--run-id`** (ver §17.1) | Sim, mas **escopo estrito ao run-id** — nunca um reset completo |

`scripts/lib/staging-local-common.ps1` não é executável directamente — é
importado pelos scripts acima.

## 6. Start infra

```powershell
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-infra-up.ps1
```

Sobe PostgreSQL e MinIO, aguarda os healthchecks Docker (`healthy`), e
confirma que o serviço `minio-bucket-init` terminou com sucesso
(`exit=0`). Falha com uma mensagem clara se algum healthcheck não passar
dentro do timeout — nunca declara sucesso sem confirmar.

## 7. Start apps

```powershell
# Todos os 4 serviços
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-apps-up.ps1

# Só um subconjunto
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-apps-up.ps1 -Services backend_core,content_renderer
```

Cada serviço só arranca se a porta-alvo estiver livre — se já estiver
ocupada por um processo não gerido por este script, o arranque desse
serviço é **saltado com aviso**, nunca força o encerramento de um processo
desconhecido (podia ser trabalho do operador). PIDs ficam registados em
`.local-runtime\pids\<serviço>.pid` para que `apps-down.ps1` saiba
exactamente o que parar.

## 8. Healthchecks

```powershell
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-health.ps1
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-health.ps1 -RequireApps
```

Verifica, por esta ordem: container PostgreSQL, container MinIO, Backend
Core `/live/`, `/ready/`, `/dependencies/` (staff-only — só corre se
`$env:STAGING_STAFF_ACCESS_TOKEN` estiver definido; ausente ⇒ `SKIPPED`,
nunca `FAIL`), Intelligence Engine `/health`, Content Renderer `/health`,
Frontend (Vite dev, verifica marcadores do `index.html` deste projecto no
corpo da resposta).

**Cada verificação confirma a identidade do serviço, não só HTTP 2xx** —
lição desta fase (Prompts 03/04): processos órfãos de sessões anteriores já
responderam com sucesso na porta certa, pertencendo ao serviço errado. Por
isso o script lê o corpo da resposta (`service=backend_core`, etc.) antes
de reportar `OK`.

Exit code `0` se a infraestrutura estiver saudável **e** nenhum serviço
aplicacional activo respondeu com identidade errada. `-RequireApps` torna
os 4 serviços aplicacionais obrigatórios.

## 9. Migrations

```powershell
cd backend_core
# Carregar o .env.staging.local com a mesma função que os scripts usam:
. ..\scripts\lib\staging-local-common.ps1
Import-DotEnvFile -Path .env.staging.local
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py showmigrations
venv\Scripts\python.exe manage.py migrate
```

Validado com sucesso real nesta fase: 32 migrations aplicadas contra o
PostgreSQL do container, 0 erros
(`resultados_execucao/prompt_03_postgresql_local_resultado.md` §3). Nunca
usar `DB_ENGINE=sqlite` para "resolver" uma falha de migration em staging
local — isso invalida a fase (critério de rejeição do backlog).

## 10. Seeds

```powershell
venv\Scripts\python.exe manage.py seed_rbac
venv\Scripts\python.exe manage.py seed_billing
venv\Scripts\python.exe manage.py seed_content
$env:E2E_PASSWORD = '<definido pelo operador, nunca hardcoded>'
venv\Scripts\python.exe manage.py seed_e2e_run --run-id <id-unico>
```

Os três primeiros são idempotentes (podem ser re-corridos sem duplicar
dados). `seed_e2e_run` cria um utilizador/workspace/artista/campanha
namespaced pelo `--run-id` — exige `E2E_PASSWORD` no ambiente, nunca o
inventa nem o aceita como argumento (ficaria no histórico do shell).

## 11. Storage MinIO

O Content Renderer usa `STORAGE_PROVIDER=s3` (S3-compatible, validado
contra o MinIO local — não `minio` como nome de provider, porque reaproveita
o valor de enum `Asset.StorageProvider.S3` já existente no Backend Core,
sem exigir alteração ao Django). Variáveis em
`content_renderer/.env.staging.local`: `STORAGE_ENDPOINT`,
`STORAGE_BUCKET`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`,
`STORAGE_FORCE_PATH_STYLE=true`.

O provider `local` (filesystem) **continua o default de desenvolvimento**
— `STORAGE_PROVIDER=s3` é uma escolha explícita para esta fase, não uma
substituição obrigatória do modo dev.

**Contrato validado de facto** (`resultados_execucao/prompt_04_minio_storage_resultado.md`,
revalidado com as credenciais não-root em
`resultados_execucao/prompt_03_minio_credenciais_nao_root_resultado.md`):
upload real dos três tipos de artefacto (`report.pdf`, `media_kit.pdf`,
outputs de content pack), `Asset.storage_provider="s3"`,
`Asset.storage_key`, e **`Asset.public_url` preenchido e efectivamente
descarregável** (`http://127.0.0.1:9000/chartrex-staging/workspaces/<ws>/jobs/<job>/<ficheiro>`,
`200`, ficheiro real confirmado por assinatura de bytes).

**Credenciais do Content Renderer (STG-HARD-003):** `STORAGE_ACCESS_KEY` /
`STORAGE_SECRET_KEY` são `MINIO_RENDERER_USER` / `MINIO_RENDERER_PASSWORD`
(`.env.staging.local` na raiz), **não** `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`.
O utilizador `chartrex_renderer` tem uma policy mínima
(`chartrex-renderer-policy`): apenas `s3:PutObject` + `s3:GetObject`,
limitados ao bucket `chartrex-staging` — sem `s3:ListBucket`, sem
`s3:DeleteObject`, sem nenhuma acção administrativa. Root fica reservado
para administração (comandos `mc admin ...` abaixo, e o próprio
`minio-bucket-init`, que cria/actualiza o utilizador e a policy de forma
idempotente a cada arranque da infraestrutura).

Verificar objectos e credenciais manualmente (usar sempre o alias `root`
para `mc admin`/`mc ls` — o utilizador `chartrex_renderer` não consegue
nem uma coisa nem outra, por desenho):

```powershell
# Root — administração (listar objectos, inspeccionar utilizadores/policies).
docker run --rm --network chartrex_staging_local --entrypoint sh minio/mc:latest -c "mc alias set root http://minio:9000 <MINIO_ROOT_USER> <MINIO_ROOT_PASSWORD> && mc ls --recursive root/chartrex-staging"
docker run --rm --network chartrex_staging_local --entrypoint sh minio/mc:latest -c "mc alias set root http://minio:9000 <MINIO_ROOT_USER> <MINIO_ROOT_PASSWORD> && mc admin user info root chartrex_renderer && mc admin policy info root chartrex-renderer-policy"

# chartrex_renderer — deve FALHAR nestas duas operações (prova de que a policy é mínima):
docker run --rm --network chartrex_staging_local --entrypoint sh minio/mc:latest -c "mc alias set svc http://minio:9000 <MINIO_RENDERER_USER> <MINIO_RENDERER_PASSWORD> && mc ls svc/chartrex-staging"        # esperado: Access Denied
docker run --rm --network chartrex_staging_local --entrypoint sh minio/mc:latest -c "mc alias set svc http://minio:9000 <MINIO_RENDERER_USER> <MINIO_RENDERER_PASSWORD> && mc admin user list svc"              # esperado: Access Denied
```

## 12. E2E

```powershell
$env:E2E_PASSWORD = '<definido pelo operador>'
cd frontend
pnpm test:e2e
```

**Ou, via o quality gate** (recomendado — já valida as pré-condições
antes de correr):

```powershell
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-quality-gate.ps1 -WithE2E
```

✅ **Executado de facto no fecho da fase (STG-LOCAL-012)**:
`pnpm test:e2e` correu contra a stack totalmente activa (PostgreSQL,
MinIO, Intelligence Engine real, Content Renderer real, Frontend real,
sem dry-run). **12/12 testes passaram**, incluindo o teste dedicado que
confirma via captura real de rede do browser (`page.on('request')`, não
análise estática) que o frontend nunca chamou as portas `8201`/`8202`.
Artefactos confirmados no bucket MinIO (`report.pdf`, `media_kit.pdf`, 2×
outputs de content pack) e `Asset.public_url` preenchido para os 4.

**Achado honesto**: a primeira tentativa teve **1 falha** (timeout de 10s
a aguardar o fecho do diálogo de criação de media kit) — investigado,
confirmado **não-reprodutível** numa segunda execução imediata a seguir
(12/12 limpo, o mesmo passo em 1.9s). Ver
`resultados_execucao/prompt_12_fecho_staging_local_resultado.md` §4 para o
registo original desta execução, e
`resultados_execucao/prompt_08_e2e_local_resultado.md` para o relatório
autónomo (**retroactivo** — a execução aconteceu de facto durante o
Prompt 12, não numa iteração dedicada ao Prompt 08; o relatório retroactivo
só reorganiza essa mesma evidência sob o número de prompt correcto, sem
nova execução). Não classificado como bug de produto — consistente com
contenção de recursos pontual numa sessão longa, não um problema de lógica
(a chamada API directa equivalente respondeu em 0.2s quando testada
isoladamente no mesmo momento).

**Actualização (fase 07, STG-HARD-001):** os passos de criação de acção com
artefacto (`report_request`/`media_kit_request`/`content_pack`) passaram a
esperar a resposta HTTP real (`page.waitForResponse`) em vez de só o fecho
do diálogo — ver `frontend/e2e/main-flow.spec.ts`. O relatório dedicado a
essa investigação (STG-HARD-001) ainda está pendente à parte; esta secção
regista apenas o resultado prático observado durante a validação desta
iteração de diagnóstico (STG-HARD-007): **5 execuções consecutivas, 12/12
`PASS` em todas**, sem nenhum flake observado.

## 12.1 Diagnóstico de falhas E2E (STG-HARD-007)

Quando um passo E2E falha, além do erro do próprio `expect`, ficam
disponíveis (sem precisar de repetir a execução):

| Artefacto | Onde | O que mostra |
|---|---|---|
| Screenshot | `frontend/test-results/<teste>/test-failed-1.png` | Estado visual do browser no momento da falha |
| Trace | `frontend/test-results/<teste>/trace.zip` | DOM, rede, consola, passo-a-passo — abrir com `pnpm exec playwright show-trace <caminho>` |
| Error context | `frontend/test-results/<teste>/error-context.md` | Resumo da falha em Markdown (gerado pelo Playwright) |
| Diagnóstico do teste | Aba **Attachments** do trace viewer, item `e2e-diagnostics` | JSON com `run_id`, `X-Request-ID`s observados durante o teste, `workspace_id`/`campaign_id`, contagem de pedidos por endpoint — ver `frontend/e2e/diagnostics.ts` |
| Relatório navegável | `frontend/playwright-report/index.html` (`pnpm exec playwright show-report`) | A mesma informação acima, numa UI, sem `show-trace` manual |
| Contexto da execução | stdout do `pnpm test:e2e` (reporter `list`) | Uma linha `[e2e] run_id=... workspace=...`, impressa no arranque de cada execução |
| Logs locais correlacionáveis | `.local-runtime/logs/{backend_core.err,intelligence_engine.out,content_renderer.out,frontend.out}.log` | Grep pelo `run_id` ou por qualquer `X-Request-ID` da tabela `e2e-diagnostics` acima — os mesmos 4 ficheiros já documentados em §14 |

**Correlação prática**: um `X-Request-ID` observado no attachment
`e2e-diagnostics` aparece nos 3 serviços (Backend Core, Intelligence
Engine, Content Renderer) exactamente como descrito em §14
("Correlation-id ponta-a-ponta") — o mecanismo não é novo, só passou a
estar automaticamente recolhido e anexado ao teste que falhou, em vez de
exigir um grep manual reactivo.

**Segurança dos artefactos (validado nesta iteração)**:
- `frontend/e2e/global-teardown.ts` redige, em todo `trace.zip` retido, o
  cabeçalho `Authorization`/`Cookie`/`Set-Cookie`/`X-Internal-Token` (troca
  o valor por `[REDACTED]`) e o corpo completo dos pedidos/respostas de
  login/refresh (`/auth/token/`, `/auth/token/refresh/`) — sem isto, a
  captura de rede nativa do Playwright grava o JWT em claro em **todos** os
  pedidos autenticados, e o `E2E_PASSWORD` em claro no pedido de login;
  ambos foram confirmados presentes antes desta correcção (achado real
  desta iteração) e confirmados ausentes depois, por grep dedicado sobre o
  `trace.zip` descomprimido.
- Corre sempre (`globalTeardown`, garantido pelo Playwright mesmo que
  testes falhem), sem depender de `test:e2e` ser invocado de uma forma
  específica — funciona igual a partir do quality gate (`-WithE2E`) ou
  directamente.
- O attachment `e2e-diagnostics` nunca inclui `E2E_PASSWORD`/
  `INTERNAL_API_TOKEN` — só ids (`run_id`, `X-Request-ID`, `workspace_id`,
  `campaign_id`) e contagens de pedidos por endpoint.
- Os excertos de log anexados (`collectLogExcerpts` em `diagnostics.ts`)
  aplicam uma segunda camada de redacção defensiva sobre as mesmas 4
  variáveis, mesmo os serviços já nunca as escrevendo por desenho (ver §14).

**Nunca usar isto como substituto dos asserts** — o teste continua a falhar
exactamente da mesma forma (mesma mensagem, mesmo `expect`); estes
artefactos só encurtam o tempo até perceber *porquê*.

## 13. Segurança

Resumo operacional (detalhe completo:
`resultados_execucao/prompt_09_seguranca_local_resultado.md`):

- **Frontend isolado** — bundle sem URLs de IE (`:8201`)/Content Renderer
  (`:8202`), sem valores de `INTERNAL_API_TOKEN`; único `apiClient` aponta
  só ao Backend Core (`:8100/api/v1`); `X-Internal-Token` é activamente
  bloqueado antes de sair do browser (`shared/api/security.ts`).
- **Backend Core**: `/live/`/`/ready/` públicos; `/dependencies/`
  staff-only (`401` sem auth, `403` para não-staff, `200` para staff).
- **Intelligence Engine / Content Renderer**: `/health` público; endpoints
  internos exigem `X-Internal-Token` correcto (`403` para ausente/errado).
  `ALLOW_INSECURE_EMPTY_TOKEN` nunca activo (ver §4).
- **MinIO** — **dois achados reais corrigidos nesta fase**:
  1. A política `mc anonymous set download` (usada inicialmente)
     concede `s3:ListBucket`, não só `s3:GetObject` como o nome sugere —
     permitia listar publicamente todas as chaves do bucket. Corrigida
     para uma política JSON própria, só `s3:GetObject` — listagem agora
     `403`, download continua `200`.
  2. PostgreSQL e MinIO publicavam em `0.0.0.0` (alcançáveis por qualquer
     máquina na mesma rede local). Corrigido para `127.0.0.1` explícito
     nas três portas (§2).
- **CORS**: `CORS_ALLOWED_ORIGINS` restrito a `localhost:5200`/
  `127.0.0.1:5200`, testado ao vivo — origem não confiável correctamente
  rejeitada (sem `Access-Control-Allow-Origin` na resposta).

Nenhuma destas verificações foi feita por pentest agressivo — só pedidos
HTTP directos e inspecção de código/configuração.

## 14. Observabilidade

Resumo operacional (detalhe completo:
`resultados_execucao/prompt_10_observabilidade_local_resultado.md`):

### Onde ver logs

| Serviço | Ficheiro (via `apps-up.ps1`) | Nota |
|---|---|---|
| Backend Core | `.local-runtime\logs\backend_core.err.log` | ⚠️ **o Django `runserver` escreve os seus logs em STDERR, não STDOUT** — `backend_core.out.log` fica sempre vazio por desenho do próprio Django. Consultar sempre o `.err.log`. |
| Intelligence Engine | `.local-runtime\logs\intelligence_engine.out.log` | JSON estruturado, uma linha por evento |
| Content Renderer | `.local-runtime\logs\content_renderer.out.log` | JSON estruturado, uma linha por evento |
| Frontend (Vite) | `.local-runtime\logs\frontend.out.log` | Só arranque/HMR |
| PostgreSQL | `docker logs chartrex_staging_postgres` | Sem ficheiro adicional nesta fase |
| MinIO | `docker logs chartrex_staging_minio` | idem |

**Retenção:** manual, sem rotação automática — ficheiros substituídos a
cada arranque via `apps-up.ps1`; limpeza manual com
`Remove-Item .local-runtime\logs\*.log -Force`.

### Correlation-id ponta-a-ponta

Um `X-Request-ID` enviado pelo cliente propaga-se por todo o fluxo:
Backend Core → Intelligence Engine (síncrono) → `ExternalJobReference`/
Content Renderer (assíncrono, `job.*`/`render.*`/`callback.*`) → callback
de volta ao Backend Core. **Validado com um fluxo real completo**: o
mesmo id apareceu em 27 linhas do Backend Core, 2 da Intelligence Engine,
27+ do Content Renderer, sem perda em nenhum ponto.

```powershell
Select-String -Path .local-runtime\logs\backend_core.err.log -Pattern '<o-meu-id>'
Select-String -Path .local-runtime\logs\intelligence_engine.out.log -Pattern '<o-meu-id>'
Select-String -Path .local-runtime\logs\content_renderer.out.log -Pattern '<o-meu-id>'
```

### Diagnosticar MinIO

```powershell
docker compose -f docker-compose.staging.local.yml ps minio
docker logs chartrex_staging_minio --tail 50
docker run --rm --network chartrex_staging_local --entrypoint sh minio/mc:latest -c "mc alias set local http://minio:9000 <user> <password> && mc anonymous get-json local/chartrex-staging"
```

### Diagnosticar PostgreSQL

```powershell
docker compose -f docker-compose.staging.local.yml ps postgres
docker logs chartrex_staging_postgres --tail 50
docker exec chartrex_staging_postgres pg_isready -U <user> -d <db>
```

**Actualizado (STG-HARD-002, fase 07):** o achado original desta secção —
"`/ready/` já falha rápido, mas um pedido normal não tem protecção
equivalente" — estava **parcialmente incorrecto**: medido de facto (fase
07), `/ready/` também ficava pendurado (~130s) quando o PostgreSQL estava
em baixo, porque `_check_database()` nunca teve nenhum timeout próprio —
`HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS` só protege as sondas HTTP ao
Intelligence Engine/Content Renderer, nunca a base de dados. Corrigido
adicionando `DB_CONNECT_TIMEOUT_SECONDS` (default `5`, só para
`DB_ENGINE=postgres`) a `OPTIONS.connect_timeout` em
`backend_core/config/settings.py` — ver
`resultados_execucao/prompt_02_timeout_postgresql_resultado.md` para as
medições completas antes/depois. Com o PostgreSQL em baixo:

- `/ready/` falha em **~5.1–5.3s** (bounded, medido, `503`).
- Um pedido normal cuja primeira interacção com a BD é a query em si (ex.:
  `POST /api/v1/auth/token/`) falha em **~31s** — muito melhor que os
  minutos anteriores, mas mais lento que `/ready/`. Causa identificada: com
  `DEBUG=True` (staging local), uma excepção não tratada aciona a página de
  erro técnica do Django, que reavalia os *context processors* de
  `TEMPLATES` (incluindo `django.contrib.auth.context_processors.auth`),
  cada um tentando a sua própria ligação (cada uma já bounded a `~5s`, mas
  em série). Confirmado isoladamente: uma query ORM directa, fora do
  caminho HTTP/DEBUG, fica bounded a `~5.07s`, igual ao `/ready/` — o
  `connect_timeout` em si funciona correctamente; o tempo extra é
  exclusivo da renderização de erro em modo `DEBUG`. Não corrigido nesta
  iteração (fora do âmbito estreito de STG-HARD-002; ver relatório
  §"Riscos remanescentes").

Se um pedido parecer "pendurado", testar `/ready/` primeiro — continua a
ser o sinal mais rápido, mesmo não sendo mais o único protegido.

## 15. Quality gate local

```powershell
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-quality-gate.ps1
```

Corre num único comando: `manage.py check` + `pytest` (Backend Core),
`pytest` (Intelligence Engine), typecheck+lint+`vitest` (Content
Renderer), testes+lint+build (Frontend), `check-forbidden-ports.ps1`, grep
de segredos sobre `git ls-files`. **Não depende da stack Docker desta
fase** — corre contra a configuração de dev normal de cada serviço,
precisamente para ser reutilizável por uma CI futura sem alterações.

Última execução completa real: **9/9 etapas `PASS`**, ~16m35s
(`resultados_execucao/prompt_07_quality_gate_local_resultado.md` §4).
`-Only <nomes>` para subconjuntos; `-WithE2E` para o modo opcional (§12).

## 16. Paragem (não destrutiva)

```powershell
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-apps-down.ps1
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-infra-down.ps1
```

Ordem inversa ao arranque. Os volumes do PostgreSQL/MinIO **não são
apagados** por nenhum destes dois scripts.

## 17. Reset destrutivo

```powershell
# ⚠️ APAGA TODOS OS DADOS de PostgreSQL e MinIO desta stack local. Sem desfazer.
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-infra-reset.ps1 -IAmSure
# (pede confirmação interactiva: escrever "apagar")
```

**Nunca embutido em `infra-down.ps1`** — é um script separado
(`staging-local-infra-reset.ps1`), que exige o switch `-IAmSure` **e** uma
confirmação escrita antes de tocar em qualquer volume. Sem `-IAmSure`, o
script bloqueia imediatamente e não altera nada (validado — ver
`resultados_execucao/prompt_06_scripts_locais_resultado.md` §5).

## 17.1 Cleanup por run-id (STG-HARD-006, não destrutivo)

**Diferente do reset acima** — este NÃO apaga tudo, só o que pertence a um
único `--run-id` (o mesmo token passado a `seed_e2e_run`, incluindo o das
sessões E2E via `global-setup.ts`). Útil depois de sessões repetidas de
E2E/smoke, sem esperar por um reset completo.

```powershell
# Pré-visualizar (Postgres: contagens; MinIO: nº de objectos) — não apaga nada:
pwsh -ExecutionPolicy Bypass -File scripts\cleanup-e2e-run.ps1 -RunId <run-id> -DryRun

# Limpar de facto (pede para escrever o run-id de volta, para confirmar):
pwsh -ExecutionPolicy Bypass -File scripts\cleanup-e2e-run.ps1 -RunId <run-id>

# Não-interactivo (scripts/CI local) — salta a confirmação:
pwsh -ExecutionPolicy Bypass -File scripts\cleanup-e2e-run.ps1 -RunId <run-id> -Force
```

Como funciona: `manage.py cleanup_e2e_run` resolve o workspace/utilizador
exactos do run-id (pelo email `e2e-{run_id}@example.local` e pelo nome do
workspace `E2E Workspace {run_id}` — os mesmos que `seed_e2e_run` cria) e
apaga em cascata só o que lhes pertence (campanhas, artistas, tracks, acções,
reports, media kits, content pack requests/outputs, assets). `ExternalJobReference`
e `AuditEvent` são apagados explicitamente à parte, porque apontam para
`workspace` com `on_delete=SET_NULL` — um simples apagar do workspace deixá-los-ia
orfãos (linha mantida, FK a `null`), não removidos. O script depois remove os
objectos MinIO sob `workspaces/<workspace_id>/` (o mesmo layout de chaves do
Content Renderer), usando credenciais **root** — o utilizador de serviço
`chartrex_renderer` (STG-HARD-003) não tem `s3:ListBucket` nem
`s3:DeleteObject`, de propósito.

- Um `--run-id` que não corresponda a nada **não é um erro** — é idempotente
  (nada a fazer, exit 0).
- Um `--run-id` vazio/só espaços é sempre bloqueado.
- Nunca apaga RBAC global (`Permission`/`Role` de sistema) nem dados de
  conteúdo partilhados (`Template`/`ContentPack`/`ContentPackTemplate`) —
  nenhum destes tem FK para `workspace`.
- Validado (`resultados_execucao/prompt_04_cleanup_run_id_resultado.md`):
  dois run-ids distintos, dry-run, limpeza real de um, confirmação de que o
  outro fica intacto (PostgreSQL e MinIO), reseed limpo do run-id limpo.

## 18. Troubleshooting (achados reais desta fase)

| Sintoma | Causa provável | Resolução |
|---|---|---|
| `password authentication failed` ao ligar ao PostgreSQL | Outro PostgreSQL local (nativo, não Docker) a ocupar a porta 5432 | Confirmar `POSTGRES_PORT` em `.env.staging.local`; `Get-NetTCPConnection -LocalPort 5432` para identificar o processo concorrente |
| Login/smoke API falha com "No active account" apesar da password estar certa | Um processo `runserver`/`uvicorn`/`node` órfão de uma sessão anterior ainda ocupa a porta | `Get-NetTCPConnection -LocalPort <porta>` → confirmar um único PID; parar os antigos antes de arrancar de novo (`apps-up`/`apps-down` já mitigam isto) |
| Frontend (Vite) inacessível em `127.0.0.1:5200` mas "acessível" em `localhost:5200` | Vite, sem `--host` explícito, liga-se só a `::1` (IPv6) nesta máquina | `staging-local-apps-up.ps1` já arranca o Vite com `--host 127.0.0.1` |
| `staging-local-apps-down.ps1` pára o script mas a porta continua ocupada | Serviços arrancados via `npx.cmd`/`pnpm.cmd` geram um processo Node.js filho; parar só o PID do wrapper não o mata | `Stop-ProcessTree` (na lib) pára a árvore completa |
| `database "test_..." is being accessed by other users` ao correr `pytest` | Uma execução anterior de `pytest` ficou órfã (`idle in transaction`) | `pg_terminate_backend` + `DROP DATABASE test_...` antes de repetir |
| Chamada de intelligence devolve `503` | Intelligence Engine em baixo | Log: `WARNING ... intelligence_call unavailable`; `curl http://127.0.0.1:8201/health`; reiniciar com `apps-up.ps1 -Services intelligence_engine` |
| Report/MediaKit/ContentPack `status=failed`, `metadata.error="External service is unavailable."` | Content Renderer em baixo | Log Backend Core: `WARNING ... job_submission_failed`; `curl http://127.0.0.1:8202/health`; reiniciar com `apps-up.ps1 -Services content_renderer` |
| Report/MediaKit `status=failed` mas o job foi aceite (`202`) | MinIO em baixo durante o render | Log Content Renderer: `render.completed status=failed`; `docker compose ps minio`; `docker compose start minio` |
| Pedido a endpoint que lê a BD fica pendurado sem resposta | PostgreSQL em baixo — **corrigido (STG-HARD-002, fase 07)**: `DB_CONNECT_TIMEOUT_SECONDS` (default `5`) limita a ligação; `/ready/` falha em `~5s`, um endpoint normal em `~31s` (ver §14) | Testar `/ready/` primeiro (mais rápido); `docker compose start postgres`; se persistir >31s, é uma regressão, reportar |
| Callback com `403 Invalid or missing internal token` | `X-Internal-Token` errado/ausente | Esperado e seguro — log `WARNING ... callback_rejected reason=invalid_token`, token nunca aparece no log; confirmar sincronização entre os 3 serviços |

## 19. Matriz de sintomas (referência rápida, pedida pelo backlog)

| Sintoma | Causa mais provável | Secção |
|---|---|---|
| Docker indisponível | Docker Desktop não instalado/não a correr | §1 — bloqueio explícito, não contornar com SQLite |
| Porta 5432 ocupada | Instância PostgreSQL nativa/outra já a usar a porta | §2 — override `POSTGRES_PORT` em `.env.staging.local` |
| Porta 9000/9001 ocupada | Outro serviço local já a usar a porta | §2 — override `MINIO_API_PORT`/`MINIO_CONSOLE_PORT` |
| DB migration falha | Migrations pendentes/incompatíveis, ou ligação à BD indisponível | §9, §18 |
| MinIO health falha | Container parado, ou volume corrompido | §18; `docker compose ps minio`, `docker logs chartrex_staging_minio` |
| Bucket ausente | `minio-bucket-init` não correu ou falhou | §6 — confirmar `exit=0`; re-correr `docker compose run --rm minio-bucket-init` |
| `Asset.public_url` vazio | Content Renderer não enviou o campo no callback, ou o provider está mal configurado (`STORAGE_PROVIDER` errado) | §11 |
| Callback `403` | `INTERNAL_API_TOKEN` dessincronizado entre serviços | §4, §13, §18 |
| IE down | Processo Intelligence Engine parado | §18 |
| Renderer down | Processo Content Renderer parado | §18 |
| Frontend chama porta errada | `VITE_BACKEND_API_BASE_URL` mal configurado, ou código a violar a fronteira "só Backend Core" | §13 — nunca deve acontecer por desenho; se acontecer, é uma regressão de código, reportar |
| E2E sem recommendations | `INTELLIGENCE_ENGINE_DRY_RUN=true` (dry-run devolve sempre `recommendations: []` por desenho) | §12 — confirmar `DRY_RUN=false` para E2E real |

## 20. Validação por terceiro

**Pendente — sem mascarar.** Esta fase, até este prompt (STG-LOCAL-011),
não teve nenhum técnico independente a seguir este runbook do zero, numa
máquina sem contexto prévio. Não se declara "validado por terceiro" porque
isso não aconteceu. Fica registado como pendência explícita para antes de
qualquer fecho formal desta fase (STG-LOCAL-012) declarar prontidão sem
qualificação.

## 21. Limitações conhecidas

- **Validação por terceiro não feita** — ver §20.
- E2E real teve 1 flake não-reprodutível numa primeira tentativa (§12) —
  monitorizar em execuções futuras; não bloqueante (confirmado limpo em
  retry imediato).
- Sem agregação central de logs entre serviços (§14) — aceitável para
  staging local de um único operador, não para produção.
- **Corrigido (STG-HARD-002, fase 07):** ligações Django→PostgreSQL
  "normais" agora têm `DB_CONNECT_TIMEOUT_SECONDS` (default `5`, só
  `DB_ENGINE=postgres`) — ver §14. Risco residual conhecido, não corrigido:
  o caminho de erro HTTP de um endpoint normal (não o `/ready/`) fica
  bounded a `~31s`, não `~5s`, por causa da página de erro técnica do
  Django em `DEBUG=True` (ver §14 para a causa exacta); aceitável para
  staging local, mas a confirmar se compensa reduzir antes de qualquer
  staging não-local.
- **Corrigido (STG-HARD-003, fase 07):** o Content Renderer já não usa a
  conta "root" do MinIO. Usa um utilizador de serviço dedicado
  (`MINIO_RENDERER_USER`, default `chartrex_renderer`), criado
  idempotentemente pelo `minio-bucket-init`, com uma policy mínima
  (`s3:PutObject` + `s3:GetObject`, limitada ao bucket de staging — sem
  `s3:ListBucket`, sem `s3:DeleteObject`, sem nenhuma acção `admin:*`). Root
  fica reservado para administração local (`mc admin ...`, o próprio
  `minio-bucket-init`). Ver §11 e
  `resultados_execucao/prompt_03_minio_credenciais_nao_root_resultado.md`
  para a policy completa e as validações de permissões.

## 22. Referências

- Arquitectura: [`arquitectura_staging_local.md`](arquitectura_staging_local.md)
- Backlog: [`01_backlog.md`](01_backlog.md)
- Compose de infraestrutura: `docker-compose.staging.local.yml`
- Scripts: `scripts/staging-local-*.ps1`, `scripts/lib/staging-local-common.ps1`
- Relatórios de execução: `resultados_execucao/prompt_01_*` a `prompt_12_*`
  (`prompt_08_e2e_local_resultado.md` é um relatório **retroactivo** — a
  execução real ocorreu durante o Prompt 12, ver esse ficheiro para a nota
  de retroactividade completa)
- Fase 05 (runbook anterior, staging pré-produção não-local): `frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/runbook_staging_pre_producao.md`
