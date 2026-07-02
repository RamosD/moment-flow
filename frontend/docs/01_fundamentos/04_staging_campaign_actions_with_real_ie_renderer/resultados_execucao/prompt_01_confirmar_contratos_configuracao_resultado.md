# Prompt 01 — Confirmar contratos, configuração, endpoints, healthchecks e fluxos reais

**Data:** 2026-07-01
**Fase:** `04_staging_campaign_actions_with_real_ie_renderer` (STG-CA-001, Incremento 0)
**Âmbito:** inspecção leve — nenhuma lógica funcional de produto alterada, nenhum serviço arrancado.
**Estado de execução:** `executado`

---

## 1. Resumo objectivo

Confirmados, por leitura de código real, os contratos e a configuração entre **Backend Core (Django, 8100)**, **Intelligence Engine (FastAPI, 8201)** e **Content Renderer (Node/Express, 8202)**.

Conclusões principais:

1. A variável **exacta** de dry-run da intelligence é **`INTELLIGENCE_ENGINE_DRY_RUN`** (path síncrono). O pipeline de renderer é governado por uma variável **independente**, **`EXTERNAL_JOBS_DRY_RUN`**.
2. No `.env` actual do Backend Core, **ambas estão `true`** — têm de passar a `false` para esta fase.
3. **Bloqueador crítico:** `INTERNAL_API_TOKEN` (e `INTELLIGENCE_ENGINE_INTERNAL_TOKEN`) estão **vazios** no Backend Core, e o IE e o CR **não têm `.env`** (só `.env.example`). Com o token vazio, tanto a chamada Django→IE como o callback CR→Django são **rejeitadas com 403**. É preciso um token partilhado não-vazio nos três serviços antes de qualquer validação real.
4. O Renderer é exercitado por **report, media kit e content pack** (os três apontam para `8202`). O modelo é **callback**, não polling.
5. A fronteira do frontend está **intacta** (só chama Backend Core; sem 8201/8202; sem `X-Internal-Token`).
6. `python manage.py check` → **0 issues**.

---

## 2. Mapa real de variáveis (Backend Core)

Fonte: `backend_core/config/settings.py`. Valores runtime lidos de `backend_core/.env` (segredos mascarados).

| Variável | Default (settings.py) | Valor runtime (`.env`) | Notas |
|---|---|---|---|
| `INTELLIGENCE_ENGINE_BASE_URL` | `http://localhost:8201` | `http://localhost:8201` | IE canónico |
| `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` | `10` | (default) | round-trip síncrono |
| `INTELLIGENCE_ENGINE_ENABLED` | `True` | `true` | se False → 503 |
| **`INTELLIGENCE_ENGINE_DRY_RUN`** | `False` | **`true`** ⚠️ | **flip para `false` nesta fase** |
| `INTELLIGENCE_ENGINE_MAX_RETRIES` | `1` | (default) | só falhas transitórias (timeout/unreachable/5xx) |
| `INTELLIGENCE_ENGINE_RETRY_BACKOFF_SECONDS` | `0.5` | (default) | backoff linear |
| `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` | `=INTERNAL_API_TOKEN` | **EMPTY** ⚠️ | reusa o token partilhado |
| `INTERNAL_API_TOKEN` | `""` | **EMPTY** ⚠️ | segredo service-to-service |
| `CONTENT_RENDERER_BASE_URL` | `http://localhost:8202` | `http://localhost:8202` | provider `content_renderer` |
| `CONTENT_RENDERER_TIMEOUT_SECONDS` | `30` | (default) | |
| `REPORT_RENDERER_BASE_URL` | `http://localhost:8202` | `http://localhost:8202` | provider `report_renderer` (mesma porta) |
| `REPORT_RENDERER_TIMEOUT_SECONDS` | `30` | (default) | |
| `BACKEND_PUBLIC_BASE_URL` | `http://localhost:8100` | `http://localhost:8100` | base do callback URL |
| `INTERNAL_CALLBACK_PATH` | `/api/v1/internal/jobs/callback/` | `/api/v1/internal/jobs/callback/` | callback que o CR chama |
| `EXTERNAL_JOBS_ENABLED` | `True` | `true` | se False → job fica `queued` |
| **`EXTERNAL_JOBS_DRY_RUN`** | `False` | **`true`** ⚠️ | **flip para `false` nesta fase** (governa o renderer) |
| `HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS` | `2.0` | (default) | probe agregado |
| `CORS_ALLOWED_ORIGINS` | `…:5200` | `http://localhost:5200,http://127.0.0.1:5200` | ok |

**Guarda de arranque:** `settings.py` recusa arrancar (`ImproperlyConfigured`) se `DEBUG=False` + IE `ENABLED` + não-`DRY_RUN` + token vazio. Como `DEBUG=True` em dev, o Django arranca à mesma — mas a chamada real ao IE falhará em runtime (ver §9).

### Intelligence Engine (`intelligence_engine/.env.example`)
| Variável | Default | Notas |
|---|---|---|
| `INTELLIGENCE_ENGINE_PORT` | `8201` | porta canónica |
| `APP_ENV` | `development` | fora de prod monta rotas de debug |
| `SERVICE_NAME` / `SERVICE_VERSION` | `intelligence_engine` / `0.1.0` | expostos no `/health` |
| `INTERNAL_API_TOKEN` | `""` (vazio) | dev permite vazio, **mas** aí todo o endpoint protegido devolve 403 |

### Content Renderer (`content_renderer/.env.example`)
| Variável | Default | Notas |
|---|---|---|
| `PORT` | `8202` | porta canónica |
| `NODE_ENV` | `development` | `/files/*` só em não-prod |
| `INTERNAL_API_TOKEN` | `""` | tem de coincidir com o do Backend Core |
| `ALLOW_INSECURE_EMPTY_TOKEN` | `false` | se `true` + token vazio → auth interna desligada (só dev) |
| `RENDERER_PUBLIC_BASE_URL` | `http://localhost:8202` | |
| `BACKEND_CORE_BASE_URL` | `http://localhost:8100` | usado nos callbacks |
| `STORAGE_PROVIDER` | `local` | única implementação nesta fase |
| `LOCAL_STORAGE_ROOT` | `./storage` | armazenamento local (MVP) |
| `LOCAL_STORAGE_PUBLIC_BASE_URL` | `http://localhost:8202/files` | serve ficheiros locais (dev) |
| `CALLBACK_TIMEOUT_SECONDS` | `20` | por tentativa |
| `CALLBACK_MAX_ATTEMPTS` / `..._BASE_DELAY_MS` / `..._MAX_DELAY_MS` | `3` / `500` / `5000` | retry exponencial |
| `RENDER_TIMEOUT_SECONDS` | `30` | por render |
| `REPORT_OUTPUT_FORMAT` | `auto` | pdf→fallback html |

---

## 3. Endpoints reais identificados

### Backend Core (Django, 8100)
| Método / Path | Auth | Papel |
|---|---|---|
| `POST /api/v1/campaigns/{id}/intelligence/` | JWT + capability `campaigns:view` | War Room → chamada **síncrona** ao IE (`campaigns/views.py` action `intelligence`) |
| `POST /api/v1/internal/jobs/callback/` | `X-Internal-Token` (`IsInternalService`) | callback dos renderers/IE para actualizar `ExternalJobReference` |
| `GET /api/v1/system/health/dependencies/` | JWT + `IsAdminUser` (staff) | health agregado de IE + CR + DB (URLs reduzidas a `configured`/`not_configured`) |
| `GET/POST /api/v1/campaign-actions/` (+ `mark-reviewed/`, `dismiss/`, `cancel/`, `complete/`) | JWT | contrato persistente de CampaignAction (fase 03) |
| `POST /api/v1/reports/` | JWT | cria Report → dispara `report_generation` |
| `POST /api/v1/media-kits/` | JWT | cria MediaKit → dispara `media_kit_generation` |
| `POST /api/v1/content-pack-requests/` | JWT | cria ContentPackRequest → dispara `content_generation` |

### Intelligence Engine (FastAPI, 8201)
| Método / Path | Auth | Papel |
|---|---|---|
| `GET /health` | pública | liveness `{status, service, version, timestamp}` |
| `POST /intelligence/campaign` | `X-Internal-Token` (`require_internal_token`) | **endpoint real chamado pelo Backend Core** (path `CAMPAIGN_INTELLIGENCE_PATH`) — diagnóstico composto síncrono |
| `POST /analysis`, `/scoring`, `/recommendations`, `/moments` | token | contratos individuais (não usados pelo path síncrono da War Room) |
| rotas `internal_debug` | token | só fora de produção |

### Content Renderer (Node/Express, 8202)
| Método / Path | Auth | Papel |
|---|---|---|
| `GET /health` | pública | liveness `{status, service, version, uptime_seconds, timestamp}` |
| `POST /jobs` | `X-Internal-Token` (`internalAuth`) | **intake de jobs** chamado pelo Backend Core (`SUBMIT_PATH="/jobs/"`) |
| `GET /files/*` | dev-only, storage local | serve artefactos renderizados localmente |

---

## 4. Healthchecks identificados

- **IE:** `GET http://localhost:8201/health` → `{"status":"ok", ...}` (público, sem token).
- **CR:** `GET http://localhost:8202/health` → `{"status":"ok", ...}` (público, sem token).
- **Agregado (Backend Core):** `GET /api/v1/system/health/dependencies/` (staff) — sonda o `/health` público de IE e CR (timeout `HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS=2.0s`, **sem** enviar token) + `SELECT 1` à DB. Estados por-dependência: `ok|degraded|unavailable|misconfigured|unknown`; overall: `ok|degraded|unavailable`. Devolve sempre HTTP 200.

---

## 5. dry_run: variável e estado esperado

| Path | Variável | Estado actual | Estado esperado (fase 04) |
|---|---|---|---|
| Intelligence síncrona (War Room) | **`INTELLIGENCE_ENGINE_DRY_RUN`** | `true` | **`false`** |
| — (gate on/off) | `INTELLIGENCE_ENGINE_ENABLED` | `true` | `true` |
| Renderer / jobs assíncronos | **`EXTERNAL_JOBS_DRY_RUN`** | `true` | **`false`** |
| — (gate on/off) | `EXTERNAL_JOBS_ENABLED` | `true` | `true` |

Notas de comportamento (código real):
- `INTELLIGENCE_ENGINE_DRY_RUN=true` → `CampaignIntelligenceService` devolve stub determinístico `source=dry_run, grade=unknown, recommendations=[]` (sem HTTP). Confirmado no relatório da fase 03.
- `EXTERNAL_JOBS_DRY_RUN=true` → `_submit_job` marca o job como `submitted` com `response_payload={"dry_run":true}` **sem** chamada HTTP; nunca chega callback nem output real.
- As duas flags são **independentes** por design (o path síncrono de insights é separado do pipeline `/jobs/` + callback).

---

## 6. Fluxos Renderer identificados

Mapeamento `job_type → provider` (`integrations_bridge/registry.py`):

| Action (frontend) | Artefacto (1º POST) | `job_type` | Provider | Base URL |
|---|---|---|---|---|
| `report_request` | `POST /reports/` | `report_generation` | `report_renderer` | `8202` |
| `media_kit_request` | `POST /media-kits/` | `media_kit_generation` | `report_renderer` | `8202` |
| `content_pack` | `POST /content-pack-requests/` | `content_generation` | `content_renderer` | `8202` |

- **O Renderer (8202) é exercitado por report, media kit e content pack.** `content_output` (`ContentOutput`) é produzido **pelo callback** de `content_generation`, não é um action-type de entrada.
- O CR suporta exactamente estes três `job_type` (`SUPPORTED_JOB_TYPES` em `job.types.ts`); um `job_type` desconhecido é recusado com 400 e **sem** callback.
- **Callback, não polling.** Sequência CR: `POST /jobs` → `202 Accepted` imediato → render em background (`setImmediate`, bounded por `RENDER_TIMEOUT_SECONDS`) → `POST` ao `callback_url` (`/api/v1/internal/jobs/callback/`) com retry exponencial. Não há polling em lado nenhum.
- `result` no callback: `content_generation` → `result.outputs[]`; `report/media_kit` → `result.asset`.

### request_id / job_id
- **Síncrono (IE):** `request_id` (uuid hex) gerado no serviço; viaja em `X-Request-ID`. **Sem** `job_id` (path síncrono não usa `ExternalJobReference`).
- **Assíncrono (renderer):** `ExternalJobReference.id` = `job_id`; `request_id` próprio por job. Headers `X-Job-ID`, `X-Request-ID`, `X-Workspace-ID`, `X-Internal-Token`. Envelope inclui `job_id`, `request_id`, `workspace_id`, `callback_url`, `entity`, `payload_version`, `payload`. O CR pode devolver `external_job_id`.

---

## 7. Estados esperados

**`ExternalJobReference.Status`:** `queued`, `submitted`, `running`, `completed`, `partially_completed`, `failed`, `cancelled`, `expired`, `timeout`.
- Terminais: `completed`, `partially_completed`, `failed`, `cancelled`, `expired`.
- Retryáveis: `failed`, `timeout`, `cancelled`, `expired`.
- Submissão real bem-sucedida → `submitted`; via callback → `running`/`completed`/`partially_completed`/`failed`. O CR envia `completed | partially_completed | failed`.

**Estados dos artefactos próprios:**
| Entidade | Estados | Nascimento | Callback |
|---|---|---|---|
| `Report` | `queued`, `processing`, `completed`, `failed`, `archived` | (via POST) | → `completed`/`failed` (`reports/callbacks.py`) |
| `MediaKit` | `draft`, `generated`, `published`, `archived` | `draft` | → `generated` (sem `failed`; falha registada em metadata) |
| `ContentPackRequest` | `draft`, `queued`, `processing`, `partially_completed`, `completed`, `failed`, `cancelled`, `expired` | criado `queued` | tratado em `content/callbacks.py` |

**`CampaignAction.status`** (contrato fase 03, lifecycle próprio): `pending`, `in_progress`, `completed`, `failed`, `dismissed`, `cancelled`. Não é alterado directamente pelos callbacks do renderer nesta fase; liga-se ao artefacto via `related_*`.

Estados a esperar na validação (STG-CA-005): `queued`/`draft` (criação) → `submitted` (job) → `processing`/`running` → `completed`/`generated`/`failed`.

---

## 8. Ficheiros inspeccionados

Backlog / docs:
- `04_.../01_backlog.md`, `04_.../02_prompts_staging.md`
- `03_.../estado_campaign_actions_backend_integration.md`
- `03_.../arquitectura_campaign_actions_backend_integration.md`
- `03_.../resultados_execucao/prompt_16_...resultado.md`

Backend Core:
- `config/settings.py`, `config/urls.py`
- `apps/integrations_bridge/`: `clients.py`, `intelligence.py`, `intelligence_sync.py`, `health.py`, `services.py`, `registry.py`, `callbacks.py`, `models.py`, `views.py`, `urls.py`, `permissions.py`
- `apps/campaigns/`: `intelligence_service.py`, `urls.py`, `views.py` (grep)
- `apps/reports/`: `services.py`, `callbacks.py` (grep), `models.py` (grep)
- `apps/content/`: `services.py`, `models.py`
- `backend_core/.env` (flags; segredos mascarados)

Intelligence Engine: `app/main.py`, `app/api/intelligence.py`, `app/api/health.py`, `app/core/config.py`, `.env.example`.

Content Renderer: `src/http/routes.ts`, `src/http/middleware.ts`, `src/jobs/job.types.ts`, `src/jobs/job.service.ts`, `src/callbacks/callback.client.ts`, `.env.example`, `.env.e2e.example`.

Frontend: grep de fronteira em `frontend/src`.

---

## 9. Ficheiros alterados

Apenas este relatório (**criado**):
`frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_01_confirmar_contratos_configuracao_resultado.md`

Nenhuma lógica de produto, settings ou `.env` foi alterada.

---

## 10. Validações executadas

| Validação | Resultado |
|---|---|
| `python manage.py check` (venv Backend Core) | ✅ `System check identified no issues (0 silenced).` |
| Grep de fronteira frontend (`8201`/`8202`/`X-Internal-Token`/`INTERNAL_API_TOKEN`) | ✅ Limpo — só README/comentário documentando a proibição em `frontend/src/README.md` e `frontend/src/shared/api/client.ts` |
| E2E / browser | Não executados (fora do âmbito deste prompt) |

---

## 11. Riscos e decisões pendentes

| ID | Risco / Decisão | Sev. | Nota |
|---|---|---|---|
| P01-R01 | **`INTERNAL_API_TOKEN` vazio nos 3 serviços.** Com token vazio: IE devolve 403 a `/intelligence/campaign` (→ `IntelligenceUpstreamError` → **502** na War Room); e o Django recusa o callback CR→BC (`IsInternalService` → **403**), deixando o job em `submitted` sem output. | **Crítico** | Definir **o mesmo** token não-vazio em `backend_core/.env`, `intelligence_engine/.env` e `content_renderer/.env` antes da validação real (STG-CA-002/003/005). Nunca commitar valores. |
| P01-R02 | **IE e CR não têm `.env`** (só `.env.example`). | Alto | Criar `.env` a partir dos exemplos. Para o CR em dev sem token seria preciso `ALLOW_INSECURE_EMPTY_TOKEN=true` — **mas isso não resolve** o callback (o Django continua a exigir token); logo, preferir token real partilhado. |
| P01-R03 | `INTELLIGENCE_ENGINE_DRY_RUN=true` e `EXTERNAL_JOBS_DRY_RUN=true` no `.env` actual. | Alto | Passar ambas a `false` (STG-CA-003 e STG-CA-005). São flags **distintas**. |
| P01-R04 | Diferença dry_run vs IE real pode quebrar o snapshot (payload real vs stub). | Alto | Validar `recommendation_snapshot` com recommendations reais (STG-R03). |
| P01-R05 | Possível mismatch de trailing slash: BC usa `SUBMIT_PATH="/jobs/"`, rota CR é `POST /jobs`. | Baixo | Express (routing não-estrito) trata `/jobs` e `/jobs/` como equivalentes; confirmar com um smoke real de job. |
| P01-R06 | MediaKit não tem estado `failed` (falha vai para metadata). | Baixo | Ao validar falhas do renderer, verificar metadata do MediaKit em vez de status. |
| P01-R07 | DB é SQLite dev (não staging alvo). | Médio | Declarar ambiente e limites no fecho (STG-R09). |
| P01-R08 | Guarda de arranque IE só actua com `DEBUG=False`; em dev token vazio deixa o Django arrancar mas falha em runtime. | Médio | Não confiar no arranque como prova; validar chamada real ao IE. |

Fronteira arquitectural (confirmada intacta): o frontend só chama Backend Core; sem URLs 8201/8202 no runtime; nunca envia `X-Internal-Token`.

---

## 12. Próximo passo recomendado

Avançar para **STG-CA-002 (arrancar serviços em portas canónicas)**, precedido da preparação de configuração:

1. Criar `intelligence_engine/.env` e `content_renderer/.env` a partir dos `.env.example`.
2. Definir **um** `INTERNAL_API_TOKEN` partilhado (mesmo valor) nos três serviços — `backend_core/.env`, `intelligence_engine/.env`, `content_renderer/.env`.
3. No `backend_core/.env`, passar `INTELLIGENCE_ENGINE_DRY_RUN=false` e `EXTERNAL_JOBS_DRY_RUN=false`.
4. Arrancar IE (`8201`) e CR (`8202`) e confirmar os `/health` públicos + o agregado `/api/v1/system/health/dependencies/` (staff).
5. Só depois executar STG-CA-003 (War Room com IE real).
