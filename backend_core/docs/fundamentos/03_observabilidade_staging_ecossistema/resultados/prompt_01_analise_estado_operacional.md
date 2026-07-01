# OBS-STG-001 — Análise do estado operacional actual dos três serviços

> Relatório de análise (somente leitura). **Nenhum código de runtime foi alterado**
> nesta etapa — o único artefacto criado é este relatório.
>
> Fase: **Observabilidade e Staging Técnico do Ecossistema**.
> Backlog: [`01_backlog.md`](../01_backlog.md).
> Data: 2026-06-25.
> Modelo recomendado para este prompt (backlog §15): opus.

---

## 1. Objectivo e âmbito desta análise

Inspeccionar o estado operacional actual de `backend_core`, `intelligence_engine`
e `content_renderer` para preparar, com segurança, a execução da fase de
observabilidade mínima (healthchecks, smoke tests, runbook, troubleshooting,
logs mínimos e prontidão operacional). Esta análise:

- **não** altera runtime;
- **não** transforma o projecto numa stack de observabilidade completa;
- identifica o que já existe, o que falta e os riscos, e propõe um plano curto
  para os prompts OBS-STG-002 a OBS-STG-010.

### 1.1 Ficheiros e artefactos inspeccionados

| Área | Ficheiros lidos |
|---|---|
| Backlog da fase | `…/03_observabilidade_staging_ecossistema/01_backlog.md`; `02_prompts_observabilidade.md` (**vazio** — 1 linha) |
| Estado IE↔BC | `…/integracao_intelligence_engine/estado_integracao_intelligence_engine.md` |
| READMEs | `backend_core/README.md`, `intelligence_engine/README.md`, `content_renderer/README.md` |
| Backend Core (config) | `config/urls.py`, `config/settings.py`, `.env.example` |
| Backend Core (integração IE) | `apps/campaigns/intelligence_service.py`, `apps/integrations_bridge/intelligence_sync.py`, `apps/integrations_bridge/clients.py` |
| Backend Core (jobs externos) | `apps/integrations_bridge/services.py`, `apps/integrations_bridge/views.py`, `apps/integrations_bridge/urls.py`, `apps/integrations_bridge/logging_utils.py` |
| Backend Core (testes opt-in) | `apps/campaigns/tests/test_intelligence_real_loop.py` |
| Intelligence Engine | `app/api/health.py`, `.env.example` |
| Content Renderer | `src/http/routes.ts`, `src/logging/logger.ts`, `.env.example`, `.env.e2e.example` |
| Content Renderer (E2E) | `scripts/run-e2e-postgres.ps1`, `scripts/e2e_backend_core.py` (e referências a `run-e2e.ps1`, `run-e2e-localpg.ps1`) |

> Documentação final do IE (`docs/gestao/fundamentos/estado_fastapi_intelligence_engine.md`)
> e do renderer (`docs/fundamentos/02_estado_content_report_renderer.md`) são
> referenciadas pelos respectivos READMEs; o estado relevante foi extraído via
> READMEs + código, suficiente para esta análise operacional.

---

## 2. Matriz operacional preliminar (insumo para OBS-STG-002)

| Serviço | Stack | Porta default | Healthcheck | Auth interna | Comando de arranque |
|---|---|---|---|---|---|
| `backend_core` | Django 6 / DRF (Python 3.13) | **8000** | **Inexistente** (ver §3) | JWT (produto) + `X-Internal-Token` (callbacks) | `python manage.py runserver` |
| `intelligence_engine` | FastAPI / Uvicorn (Python 3.13) | **8001** | `GET /health` (público) | `X-Internal-Token` em todos os endpoints excepto `/health` | `uvicorn app.main:app --port 8001` |
| `content_renderer` | Node ≥18 / Express / TypeScript | **8002** | `GET /health` (público) | `X-Internal-Token` em `/jobs` | `npm run dev` (ou `npm run build && npm start`) |
| `report_renderer` (lógico) | = content_renderer | **8003 na config / 8002 na prática** | `GET /health` | `X-Internal-Token` | (mesmo processo do content_renderer) |
| PostgreSQL (E2E) | Docker | **55432** (E2E) / 5432 (local) | `docker inspect … Health.Status` | — | `docker compose -f docker-compose.e2e.yml up -d` |

> **Nota de porta (gap de configuração):** `REPORT_RENDERER_BASE_URL` tem default
> `http://localhost:8003` em `config/settings.py`, mas o renderer único serve os
> três tipos de job numa só porta (8002). O harness E2E aponta
> `REPORT_RENDERER_BASE_URL=http://localhost:8002`. Em staging tem de se apontar
> explicitamente o report renderer para **8002** (ou subir um segundo processo em
> 8003). Documentar isto no runbook (OBS-STG-007) para evitar callbacks/submissões
> para uma porta inexistente.

---

## 3. Healthchecks existentes

### 3.1 Intelligence Engine — `GET /health` (existe)

- Ficheiro: `intelligence_engine/app/api/health.py`.
- **Público, sem auth** (`/health` nunca exige `X-Internal-Token`).
- Resposta: `{ "status": "ok", "service", "version", "timestamp" }` (UTC ISO).
- É uma *liveness probe*: não testa dependências (o IE não tem dependências
  externas nem base de dados — é stateless e determinístico).

### 3.2 Content Renderer — `GET /health` (existe)

- Ficheiro: `content_renderer/src/http/routes.ts`.
- **Público, sem auth.**
- Resposta: `{ "status": "ok", "service", "version", "uptime_seconds", "timestamp" }`.
- Também *liveness*; não reporta estado de storage nem de callback.

### 3.3 Backend Core — **sem healthcheck** (lacuna central)

- `config/urls.py` **não regista** nenhuma rota de health/liveness/readiness.
- `grep health` no código do Backend Core só encontra ocorrências em **testes** e
  **documentação** — não há view.
- Não existe healthcheck de base de dados próprio nem healthcheck agregado das
  dependências técnicas (IE / renderer).
- **Consequência:** hoje, "está tudo de pé?" só se responde indo a cada serviço à
  mão. Esta é exactamente a lacuna que **OBS-STG-003** vai cobrir (endpoint
  agregado no Backend Core que consulta `GET /health` do IE e do renderer com
  timeout curto e devolve `ok|degraded|unavailable` por dependência).

---

## 4. Variáveis de ambiente críticas

Legenda: 🔒 = **secret, nunca versionar nem logar** · ⚙️ = config não-secreta.

### 4.1 Backend Core (`.env.example` / `config/settings.py`)

| Variável | Tipo | Default | Relevância operacional |
|---|---|---|---|
| `INTERNAL_API_TOKEN` | 🔒 | vazio | Segredo partilhado dos callbacks internos e (por default) das chamadas ao IE. Vazio ⇒ callbacks internos rejeitados. |
| `SECRET_KEY` | 🔒 | dev inseguro | Obrigatório forte em produção. |
| `STRIPE_WEBHOOK_SECRET` / `STRIPE_API_KEY` | 🔒 | vazio | Billing skeleton; fora do escopo desta fase. |
| `DEBUG` | ⚙️ | `True` | `False` activa guardas de produção (ver §5). |
| `ALLOWED_HOSTS` / `CORS_ALLOWED_ORIGINS` | ⚙️ | localhost | Necessário rever em staging. |
| `DB_ENGINE` (+ `DB_NAME/USER/PASSWORD/HOST/PORT`) | ⚙️/🔒 | `sqlite` | `postgres` necessário para o **loop multi-processo** do renderer (SQLite não partilha linhas entre processos — ver §7). `DB_PASSWORD` é 🔒. |
| `BACKEND_PUBLIC_BASE_URL` | ⚙️ | `http://localhost:8000` | Base do `callback_url` enviado ao renderer. |
| `INTELLIGENCE_ENGINE_BASE_URL` | ⚙️ | `http://localhost:8001` | Alvo do client síncrono. |
| `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` | ⚙️ | `10` | Timeout do client IE. |
| `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` | 🔒 | vazio → reutiliza `INTERNAL_API_TOKEN` | Token `X-Internal-Token` para o IE. |
| `INTELLIGENCE_ENGINE_ENABLED` | ⚙️ | `True` | `False` ⇒ serviço devolve 503 (`intelligence_disabled`). |
| `INTELLIGENCE_ENGINE_DRY_RUN` | ⚙️ | `False` | `True` ⇒ stub determinístico, sem HTTP. **Smoke real exige `False`.** |
| `INTELLIGENCE_ENGINE_MAX_RETRIES` / `..._RETRY_BACKOFF_SECONDS` | ⚙️ | `1` / `0.5` | Retry só de falhas transitórias (timeout/inacessível/5xx). |
| `CONTENT_RENDERER_BASE_URL` / `..._TIMEOUT_SECONDS` | ⚙️ | `:8002` / `30` | Alvo de `content_generation`. |
| `REPORT_RENDERER_BASE_URL` / `..._TIMEOUT_SECONDS` | ⚙️ | `:8003` / `30` | ⚠️ ver nota de porta em §2. |
| `INTERNAL_CALLBACK_PATH` | ⚙️ | `/api/v1/internal/jobs/callback/` | Combinado com `BACKEND_PUBLIC_BASE_URL`. |
| `EXTERNAL_JOBS_ENABLED` | ⚙️ | `True` | `False` ⇒ jobs ficam `queued` (sem chamada). |
| `EXTERNAL_JOBS_DRY_RUN` | ⚙️ | `False` | `True` ⇒ submissão simulada. **Smoke real do renderer exige `False`.** |

### 4.2 Intelligence Engine (`.env.example`)

| Variável | Tipo | Default | Notas |
|---|---|---|---|
| `INTERNAL_API_TOKEN` | 🔒 | vazio | Em `production` **tem** de ser não-vazio (senão `config_error` no arranque). Em dev/test vazio ⇒ todos os endpoints protegidos rejeitam (não é bypass). |
| `APP_ENV` | ⚙️ | `development` | `production` desliga rotas de diagnóstico e endurece config. |
| `SERVICE_NAME` / `SERVICE_VERSION` | ⚙️ | `intelligence_engine` / `0.1.0` | Devolvidos em `/health`. |
| `LOG_LEVEL` | ⚙️ | `INFO` | Logger JSON estruturado. |
| (porta) | ⚙️ | — | **Não há `PORT`**; a porta vem do CLI `uvicorn --port 8001`. |

### 4.3 Content Renderer (`.env.example`)

| Variável | Tipo | Default | Notas |
|---|---|---|---|
| `INTERNAL_API_TOKEN` | 🔒 | vazio | **Tem** de igualar o do Django. Em `production` não pode ser vazio. |
| `ALLOW_INSECURE_EMPTY_TOKEN` | ⚙️ | `false` | Só dev: permite arrancar com token vazio (auth desligada). Rejeitado em produção. |
| `PORT` | ⚙️ | `8002` | Porta HTTP. |
| `NODE_ENV` | ⚙️ | `development` | `production` desactiva `GET /files/*`. |
| `RENDERER_PUBLIC_BASE_URL` | ⚙️ | `:8002` | URL público. |
| `BACKEND_CORE_BASE_URL` | ⚙️ | `:8000` | Alvo dos callbacks. |
| `STORAGE_PROVIDER` | ⚙️ | `local` | Só `local` implementado; valor desconhecido ⇒ falha no arranque. |
| `LOCAL_STORAGE_ROOT` / `LOCAL_STORAGE_PUBLIC_BASE_URL` | ⚙️ | `./storage` / `:8002/files` | Storage MVP (não produção). |
| `MAX_JOB_PAYLOAD_BYTES` | ⚙️ | `1048576` | Limite de payload (413 acima). |
| `CALLBACK_TIMEOUT_SECONDS` / `CALLBACK_MAX_ATTEMPTS` / `CALLBACK_RETRY_BASE_DELAY_MS` / `CALLBACK_RETRY_MAX_DELAY_MS` | ⚙️ | `20` / `3` / `500` / `5000` | Retry de callback com backoff (sem retry em 4xx). |
| `RENDER_TIMEOUT_SECONDS` | ⚙️ | `30` | Timeout de um render. |
| `REPORT_OUTPUT_FORMAT` | ⚙️ | `auto` | `auto\|pdf\|html`. |

### 4.4 Harness E2E (`.env.e2e.example`)

Valores **dev explícitos, não secretos**: `INTERNAL_API_TOKEN=e2e-shared-token-change-me`
(o harness gera um token efémero se ficar no placeholder), `DB_*` para o PostgreSQL
do `docker-compose.e2e.yml` (`DB_PORT=55432`, `DB_PASSWORD=chartrex_e2e_dev_only`).
`.env.e2e` é git-ignored; só o `.example` é versionado.

---

## 5. Tokens internos necessários e guardas de segurança

- **Um único segredo partilhado** (`INTERNAL_API_TOKEN`) tem de ser **idêntico**
  nos três serviços. O Django também o reutiliza, por default, como token do IE
  (`INTELLIGENCE_ENGINE_INTERNAL_TOKEN` vazio → cai no `INTERNAL_API_TOKEN`).
- Viaja **apenas** no header `X-Internal-Token`; nunca em corpo, query, log ou
  mensagem de erro. Comparação em tempo constante no IE (`hmac.compare_digest`).
- **Guardas de arranque (fail-fast) já existentes:**
  - **Django:** `config/settings._require_secure_intelligence_engine_config` —
    se `DEBUG=False` **e** `INTELLIGENCE_ENGINE_ENABLED=True` **e**
    `INTELLIGENCE_ENGINE_DRY_RUN=False` **e** token resolvido vazio ⇒
    `ImproperlyConfigured` (recusa arrancar).
  - **IE:** `INTERNAL_API_TOKEN` vazio em `production` ⇒ `config_error` no arranque.
  - **Renderer:** token vazio rejeitado em `production`/`development` salvo
    `ALLOW_INSECURE_EMPTY_TOKEN=true` (apenas dev).
- **Redacção de logs** em todos os serviços:
  - Django bridge (`logging_utils._FORBIDDEN_KEYS`): `token`, `internal_token`,
    `x_internal_token`, `secret`, `password` são descartadas mesmo se passadas
    como extra.
  - IE e renderer: redacção recursiva por padrão de chave
    (`token|secret|password|authorization|api_key|credential`).

---

## 6. Scripts e comandos existentes

### 6.1 Arranque

| Serviço | Comando |
|---|---|
| Backend Core | `python manage.py runserver` (8000); migrations: `migrate`; seeds: `seed_rbac`, `seed_billing`, `seed_content`; superuser: `createsuperuser` |
| Intelligence Engine | `venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8001` |
| Content Renderer | `npm run dev` (watch) **ou** `npm run build` + `npm start` |

**Management commands existentes** (Backend Core): apenas `seed_rbac`,
`seed_billing`, `seed_content`. **Não há** management command de health nem de
smoke test — confirma a necessidade de OBS-STG-003/004/005.

### 6.2 Testes e validação

| Comando | Serviço | Notas |
|---|---|---|
| `pytest` (`-q`) | Backend Core | 459 passed, 3 skipped no fecho do IE↔BC (os 3 skips = loop real opt-in). |
| `ruff check .` / `ruff format .` | Backend Core / IE | Lint. |
| `python manage.py check` | Backend Core | System check. |
| `python manage.py spectacular --file schema.yml` | Backend Core | Schema OpenAPI. |
| `pytest -v` | IE | 197 testes. |
| `npm test` / `npm run test:coverage` / `npm run lint` / `npm run typecheck` | Renderer | Vitest + thresholds de coverage. |

### 6.3 Scripts E2E do renderer (`content_renderer/scripts/`)

| Script | Papel |
|---|---|
| `run-e2e-postgres.ps1` | Harness **multi-processo fiável**: sobe PostgreSQL efémero (Docker), migra+seed, arranca renderer (8002) e Django (8000) com o **mesmo token**, espera readiness (`/health` do renderer; `/api/v1/schema/` do Django), corre o driver, recolhe evidência e faz teardown. Suporta `-KeepUp`. |
| `run-e2e-localpg.ps1` | Variante sem Docker, contra um cluster PostgreSQL local. |
| `run-e2e.ps1` | Variante legada (SQLite) — limitada em multi-processo. |
| `e2e_backend_core.py` | Driver: usa o ORM do Django, semeia jobs em DRY-RUN (commit do `ExternalJobReference`), faz de *submitter* (POST do envelope ao renderer), e valida o callback real → criação de `Asset`. Cobre cenários content/report/media-kit, **falhas controladas** e **idempotência**. Devolve JSON com `ok` por cenário. |

> Estes scripts são a base concreta para **OBS-STG-005** (smoke renderer): já
> existe um loop real verificável; falta consolidá-lo como smoke opt-in
> documentado e tratar explicitamente o caso "renderer desligado".

---

## 7. Testes E2E / smoke / opt-in já existentes

| Activo | Localização | Tipo | Como activar |
|---|---|---|---|
| Loop real BC→IE | `apps/campaigns/tests/test_intelligence_real_loop.py` | **Opt-in** (`pytest.mark.skipif` por `RUN_REAL_IE`) | `RUN_REAL_IE=1 REAL_IE_BASE_URL=… REAL_IE_TOKEN=…` com o IE a correr |
| Loop real BC↔Renderer | `content_renderer/scripts/run-e2e-postgres.ps1` + `e2e_backend_core.py` | Harness multi-processo | `powershell -File scripts\run-e2e-postgres.ps1` |
| Sucesso real BC→IE | `test_real_loop_returns_intelligence` | valida `source=engine`, `status=completed`, 6 chaves (`analysis/scores/grade/moments/recommendations/summary`), **token ausente do log** | (idem opt-in) |
| Falha controlada BC→IE | `test_real_loop_unavailable_is_controlled` | porta fechada ⇒ `IntelligenceUnavailableError` | (idem opt-in) |
| Endpoint HTTP real BC→IE | `test_real_loop_via_django_http_endpoint` | `POST /api/v1/campaigns/{id}/intelligence/` com auth+RBAC reais ⇒ 200 | (idem opt-in) |

**Leitura para a fase:** o BC→IE já tem um teste opt-in que é praticamente um
smoke test (reutilizável em OBS-STG-004). O BC↔Renderer tem um harness completo
mas pesado (Docker/PostgreSQL); OBS-STG-005 deve **documentar/consolidar** este
loop como checklist executável e/ou smoke opt-in mais leve, sem reescrever o
renderer.

---

## 8. Padrões de logging e correlação (insumo para OBS-STG-006)

### 8.1 Loggers existentes no Backend Core

| Logger | Origem | Formato | Campos emitidos |
|---|---|---|---|
| `campaigns.intelligence` | `intelligence_service._log` | `key=value` | `event`, `request_id`, `workspace_id`, `campaign_id` + extras: `status`, **`duration_ms`**, `error_type`, `error_code` |
| `integrations_bridge.intelligence` | `intelligence_sync` | `key=value` | `request_id`, `workspace_id`, `status`, `error_code`, `attempt` |
| `integrations_bridge.client` | `clients.InternalServiceClient` | `key=value` | `job_id`, `request_id`, `url`, `status` |
| `integrations_bridge` | `logging_utils.log_job_event` + callback view | `key=value` | `event`, `workspace_id`, `job_id`, `job_type`, `provider`, `status`, `request_id` + extras |

### 8.2 Cobertura por campo pedido pelo backlog

| Campo | Estado actual |
|---|---|
| `request_id` | ✅ amplamente presente (IE sync, client, intelligence service) |
| `workspace_id` | ✅ no intelligence service/client e em `job_log_fields`; ❌ **ausente** no `InternalServiceClient` de baixo nível (só `job_id`+`request_id`) |
| `campaign_id` | ⚠️ **só** em `campaigns.intelligence` (fluxo IE); ausente no fluxo de jobs/renderer |
| `job_id` | ✅ em `job_log_fields` e `InternalServiceClient` |
| `provider` | ⚠️ **só** em `job_log_fields` (fluxo de jobs); ausente no fluxo IE |
| `duration_ms` | ⚠️ **só** em `campaigns.intelligence._call_engine`; ❌ ausente na submissão de jobs e no callback |
| `status` | ✅ presente nos vários fluxos |
| `error_type` | ⚠️ presente como extra em `campaigns.intelligence`; ❌ não normalizado nos restantes |
| `external_job_id` | ❌ existe no modelo, mas **não** nos `job_log_fields` default (gap citado pelo próprio OBS-STG-006) |

### 8.3 Lacunas estruturais de logging (importantes)

1. **`config/settings.py` não define `LOGGING`.** Sem `LOGGING` dict, os logs de
   nível **INFO** dos loggers de aplicação (`intelligence_call start/ok`,
   `internal_call ok`, `job_*`) podem **não aparecer** (o root logger default do
   Python só emite ≥ WARNING via *last-resort handler*). Risco directo para
   "correlacionar logs por request_id". **OBS-STG-006** deve incluir um `LOGGING`
   mínimo (handler de consola + nível para os loggers `campaigns.*` /
   `integrations_bridge.*`).
2. **Heterogeneidade de formato:** Backend Core emite `key=value` em texto; IE e
   renderer emitem **JSON**. Correlacionar por `request_id` entre serviços exige
   parsing de dois formatos. Para o âmbito mínimo desta fase, basta garantir que o
   `request_id` (e `job_id`) é **propagado e impresso** em ambos — o renderer já
   recebe `X-Request-ID`/`request_id` no envelope; o Django gera `request_id` por
   job/chamada IE.
3. **Fluxo de jobs sem `duration_ms`/`error_type` normalizados** — dificulta medir
   latência e taxa de erro por provider sem ler o código.

---

## 9. Dependências entre serviços

```text
Cliente HTTP (JWT + X-Workspace-ID)
        │
        ▼
   backend_core (Django :8000) ── orquestra tudo
        │  síncrono (X-Internal-Token)          │  jobs (X-Internal-Token, /jobs/)
        ▼                                        ▼
 intelligence_engine (:8001)            content_renderer (:8002)
   GET /health, POST /intelligence/...    GET /health, POST /jobs
        │ (sem dependências)                    │ render → storage local
        ▼                                        ▼ callback X-Internal-Token
   (stateless)                           POST /api/v1/internal/jobs/callback/ → backend_core
                                                 │
                                                 ▼
                                          PostgreSQL/SQLite (do backend_core)
```

- O **Backend Core** é o ponto de orquestração e o único com base de dados.
- O **IE** é stateless e sem dependências (não chama ninguém).
- O **Renderer** depende do Backend Core **apenas para o callback**; o storage é
  local (MVP).
- O loop do renderer **exige PostgreSQL** para ser fiável em multi-processo
  (SQLite não partilha linhas commitadas entre processos → callback dá 404).

---

## 10. Lacunas operacionais (gaps de diagnóstico)

| # | Lacuna | Impacto | Prompt que resolve |
|---|---|---|---|
| G1 | Backend Core **sem healthcheck** (liveness, readiness e agregado de dependências) | Não há resposta rápida a "está tudo de pé?" | OBS-STG-003 |
| G2 | **Sem matriz operacional** central (portas/healthchecks/vars/comandos) | Arranque e diagnóstico dependem de conhecimento tácito | OBS-STG-002 |
| G3 | Smoke test BC→IE existe como teste opt-in, mas **não está documentado como comando operacional** | Operador não sabe como validar o loop IE | OBS-STG-004 |
| G4 | Smoke BC↔Renderer só via harness pesado (Docker/PostgreSQL); **sem checklist leve** nem tratamento documentado de "renderer desligado" | Validação do loop renderer é cara | OBS-STG-005 |
| G5 | **Sem `LOGGING` em settings.py**; INFO pode não surgir; `request_id`/`job_id`/`duration_ms`/`error_type` não uniformes | Correlação e diagnóstico frágeis | OBS-STG-006 |
| G6 | **Sem runbook** de arranque local/staging (ordem, portas, vars, paragem) | Onboarding e staging manuais e propensos a erro | OBS-STG-007 |
| G7 | **Sem checklist de troubleshooting** accionável (403/422/500/timeout/porta ocupada/DB down) | Falhas comuns exigem ler código | OBS-STG-008 |
| G8 | **Sem painel de prontidão** que separe piloto vs produção | Risco de confundir "pronto para piloto" com "pronto para produção" | OBS-STG-009 |
| G9 | Discrepância `REPORT_RENDERER_BASE_URL` (8003 default vs 8002 real) | Submissões/callbacks para porta inexistente | OBS-STG-002/007 (documentar) |
| G10 | `external_job_id` ausente dos logs default | Dificulta cruzar o id interno do renderer com o job Django | OBS-STG-006 |

---

## 11. Riscos registados

Reforçam os riscos do backlog (§10, OBS-RSK-001..008), com a leitura concreta
desta análise:

| ID | Risco | Estado / mitigação observada |
|---|---|---|
| OBS-RSK-001 | Transformar a fase numa stack de observabilidade completa | Manter MVP; **não** introduzir Prometheus/OTel/ELK (fora do escopo §4.2). |
| OBS-RSK-002 | Expor tokens em logs/docs | **Já mitigado** por redacção nos três serviços; manter `grep` de secrets nos novos docs/scripts. Não usar tokens reais nos exemplos (usar placeholders tipo `real-loop-token-123` atados a 127.0.0.1). |
| OBS-RSK-003 | Smoke tests frágeis por dados locais | Reutilizar factories/opt-in (BC→IE) e o driver com entidades criadas on-the-fly (renderer); manter comandos opt-in/checklist. |
| OBS-RSK-004 | Healthcheck agregado com falsos negativos por timeout agressivo | Timeout **curto mas configurável**; estado `degraded` em vez de falha total (a desenhar em OBS-STG-003). |
| OBS-RSK-005 | Healthcheck detalhado expor info sensível | Endpoint agregado deve ser **protegido** se expuser detalhe (decisão OBS-PDEC-001); nunca incluir token/URLs sensíveis em excesso. |
| OBS-RSK-006 | Logs insuficientes | Resolver G5/G10 em OBS-STG-006: `LOGGING` mínimo + campos uniformes. |
| OBS-RSK-007 | Validação real não executável no ambiente | BC→IE e BC↔Renderer **são** executáveis localmente, mas exigem processos externos (e Docker/PostgreSQL no renderer). Documentar limitação + checklist (OBS-STG-007/008). |
| OBS-RSK-008 | Confundir piloto com produção | Painel (OBS-STG-009) deve separar explicitamente; o estado IE↔BC já diz **piloto: sim / produção: não**. |
| **Novo** OBS-RSK-009 | Discrepância de porta do report renderer (G9) | Documentar e/ou corrigir default em OBS-STG-002/007. |

---

## 12. Plano técnico curto e executável (OBS-STG-002 → 010)

Ordem do backlog §12, com o foco concreto extraído desta análise. Modelos
sugeridos pelo backlog: 02–06 opus, 07–10 sonnet.

1. **OBS-STG-002 — Matriz operacional** (`matriz_operacional_servicos.md`).
   Consolidar §2/§4/§9 deste relatório; marcar secrets (🔒); **registar a
   discrepância de porta do report renderer (G9)**. *Doc apenas.*
2. **OBS-STG-003 — Healthcheck agregado no Backend Core.**
   Novo endpoint (ex.: `GET /api/v1/system/health/external-services/`), **protegido**
   (OBS-PDEC-001), que consulta `GET /health` do IE e do renderer com **timeout
   curto configurável**; normaliza `ok|degraded|unavailable|misconfigured|unknown`
   por dependência, com `duration_ms`; falha de uma dependência → `degraded`,
   **nunca 500**. Testes com mocks (ok/degraded/timeout/misconfigured). *Toca runtime.*
3. **OBS-STG-004 — Smoke BC→IE.** Reutilizar `test_intelligence_real_loop.py`
   (opt-in `RUN_REAL_IE`) e/ou criar management command opt-in (OBS-PDEC-002);
   validar `ENABLED/DRY_RUN=false`/token/`BASE_URL`; confirmar as 6 chaves e
   **ausência de token nos logs**; documentar o caso "IE desligado". *Doc + opt-in.*
4. **OBS-STG-005 — Smoke BC↔Renderer.** Consolidar `run-e2e-postgres.ps1` +
   `e2e_backend_core.py` como smoke documentado; checklist executável; tratar
   "renderer desligado"; validar health/token/job/202/callback/`ExternalJobReference`/
   asset. **Sem alterar o renderer.** *Doc + script.*
5. **OBS-STG-006 — Correlação de logs.** Adicionar `LOGGING` mínimo em settings
   (consola + níveis para `campaigns.*`/`integrations_bridge.*`); uniformizar
   `request_id`/`workspace_id`/`campaign_id`/`job_id`/`external_job_id`/`provider`/
   `duration_ms`/`status`/`error_type` nos fluxos IE e jobs/callback; testes de
   ausência de token. *Toca runtime (logs).*
6. **OBS-STG-007 — Runbook** (`runbook_arranque_staging.md`): pré-requisitos,
   portas, ordem de arranque, vars, arranque/paragem dos três serviços,
   verificação de healthchecks, execução de smoke tests, limpeza de artefactos.
   Incluir a nota de porta do report renderer. *Doc apenas.*
7. **OBS-STG-008 — Checklist de troubleshooting** (`checklist_troubleshooting.md`):
   IE indisponível/403/422/500, renderer indisponível/sem callback/callback 404,
   token desalinhado, URL errada, timeout, payload inválido, RBAC, porta ocupada,
   DB indisponível — cada um com sintoma, causa provável, acção e comando de
   verificação. Reaproveitar o "Troubleshooting" do README do renderer. *Doc apenas.*
8. **OBS-STG-009 — Painel de prontidão** (`painel_prontidao_operacional.md`):
   estado de serviços/healthchecks/smoke/logs/secrets/blockers; decisão explícita
   **piloto vs produção**. *Doc apenas.*
9. **OBS-STG-010 — Validação final e estado da fase.** Correr `pytest`,
   `manage.py check`, lint, healthcheck agregado, smoke IE e renderer **se o
   ambiente permitir** (não inventar resultados); criar
   `estado_observabilidade_staging_ecossistema.md` e
   `resultados/prompt_final_observabilidade_staging.md`. *Doc + validação.*

---

## 13. Decisões pendentes (recomendações desta análise)

| Decisão (backlog §11) | Recomendação |
|---|---|
| OBS-PDEC-001 — health agregado público ou protegido | **Protegido** (expõe estado de dependências internas). |
| OBS-PDEC-002 — management command vs teste opt-in | **Teste opt-in primeiro** (já existe para IE); management command só se útil para operação manual. |
| OBS-PDEC-003 — consultar IE/renderer em tempo real | **Sim**, com timeout curto e `degraded` em falha. |
| OBS-PDEC-004 — métricas: logs ou endpoint | **Logs estruturados + painel textual**; endpoint de métricas fica para fase posterior. |

---

## 14. Conclusão e estado de prontidão

- Os **três serviços estão funcionais**; IE↔BC e BC↔Renderer já foram validados
  com loops reais (o IE↔BC encerrado com 459 passed/3 skipped; o renderer com
  harness PostgreSQL e idempotência confirmada).
- A **lacuna operacional central** é a ausência de healthcheck (e de healthcheck
  agregado) no Backend Core, somada à falta de `LOGGING` configurado, runbook e
  troubleshooting — exactamente o que esta fase endereça.
- **Segurança de secrets** está em bom estado de partida (redacção nos três
  serviços + guardas de arranque); manter a disciplina de não introduzir tokens
  reais em docs/scripts novos.
- **Veredicto de partida (a confirmar no OBS-STG-009):** *pronto para piloto
  técnico controlado* com as ressalvas acima; **não** pronto para produção
  (faltam observabilidade real, staging contínuo, S3/R2, calibração).

---

## 15. Conformidade com os critérios de aceitação (OBS-STG-001)

| Critério | Estado |
|---|---|
| Plano técnico criado | ✅ §12 |
| Healthchecks existentes identificados | ✅ §3 (IE e renderer existem; Backend Core não tem) |
| Variáveis de ambiente críticas identificadas | ✅ §4 (com marcação de secrets) |
| Scripts/comandos existentes identificados | ✅ §6 |
| Lacunas operacionais listadas | ✅ §10 |
| Riscos registados | ✅ §11 |
| Relatório criado em `resultados/` | ✅ este ficheiro |
| Nenhum runtime alterado sem necessidade | ✅ apenas este relatório foi criado |
