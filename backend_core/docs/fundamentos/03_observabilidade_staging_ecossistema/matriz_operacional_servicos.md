# Matriz Operacional dos Serviços — MomentFlow / ChartRex

> Documento de referência central da fase **Observabilidade e Staging Técnico do
> Ecossistema** (OBS-STG-002). Reúne, num só lugar, portas, comandos, healthchecks,
> variáveis, dependências, secrets e modos de arranque (local / staging técnico)
> dos serviços do ecossistema.
>
> Fonte: [`01_backlog.md`](01_backlog.md) e
> [`resultados/prompt_01_analise_estado_operacional.md`](resultados/prompt_01_analise_estado_operacional.md).
> Data: 2026-06-25. **Nenhum valor real de segredo aparece neste documento** — só
> placeholders.

---

## 0. Convenções

- 🔒 = **secret / sensível**: nunca versionar, nunca logar, nunca colocar em docs.
  Representado sempre por placeholder (ex.: `<INTERNAL_API_TOKEN>`).
- ⚙️ = configuração não-secreta (URL, porta, timeout, flag).
- **Modo local** = desenvolvimento numa máquina, SQLite por default, tudo em
  `localhost`, tokens podem ser placeholders de dev.
- **Modo staging técnico** = os três serviços a correr de forma reproduzível
  (idealmente PostgreSQL), com o **mesmo** `INTERNAL_API_TOKEN` em todos, URLs
  explícitas e `DRY_RUN=false`. Não é produção (ver §10).
- "por confirmar" = valor não verificável só por inspecção estática; segue sempre
  de **como validar**.

---

## 1. Referência rápida (todos os serviços)

| Serviço | Directório | Porta default | Healthcheck | Comando de arranque | DB própria |
|---|---|---|---|---|---|
| `backend_core` (Django) | `backend_core/` | **8100** | `GET /api/v1/system/health/dependencies/` (agregado, **staff-only**) | `python manage.py runserver 127.0.0.1:8100` | Sim (SQLite/PostgreSQL) |
| `intelligence_engine` (FastAPI) | `intelligence_engine/` | **8201** | `GET /health` (público) | `uvicorn app.main:app --port 8201` | Não (stateless) |
| `content_renderer` (Express/TS) | `content_renderer/` | **8202** | `GET /health` (público) | `npm run dev` ou `npm start` | Não (storage local) |
| `report_renderer` (lógico) | = `content_renderer/` | **8202** (mesmo processo) | `GET /health` | (mesmo processo do renderer) | Não |
| PostgreSQL (staging/E2E) | `content_renderer/docker-compose.e2e.yml` | **55432→5432** (E2E) / 5432 (local) | `pg_isready` / `docker inspect … Health` | `docker compose -f docker-compose.e2e.yml up -d` | — |

> ℹ️ **Renderer único (G9, resolvido):** o `content_renderer` serve
> `content_generation`, `report_generation` e `media_kit_generation` na mesma
> porta **8202**. Tanto `CONTENT_RENDERER_BASE_URL` como `REPORT_RENDERER_BASE_URL`
> apontam para `:8202` — os defaults no `config/settings.py` já reflectem isto.
> **Como validar:** `curl http://localhost:8202/health` responde.

---

## 2. `backend_core` — Django / DRF (orquestrador)

| Campo | Valor |
|---|---|
| **Descrição** | Plano de produto SaaS: auth/JWT, multi-tenancy, RBAC, catálogo, campanhas, content, smart links, billing, reports, media kits, auditoria. Orquestra os serviços técnicos (IE síncrono; renderer via jobs+callback). |
| **Directório** | `backend_core/` |
| **Stack** | Django 6 / DRF 3.17, Python 3.13, SimpleJWT, drf-spectacular, WhiteNoise, python-decouple, psycopg |
| **Porta default** | **8100** (`runserver 127.0.0.1:8100`) |
| **Instalação/preparação** | `python -m venv venv` → `.\venv\Scripts\Activate.ps1` → `pip install -r requirements.txt` → (opcional) `Copy-Item .env.example .env` → `python manage.py migrate` → seeds (`seed_rbac`, `seed_billing`, `seed_content`) → (opcional) `createsuperuser` |
| **Comando de arranque** | `python manage.py runserver 127.0.0.1:8100` (→ `http://127.0.0.1:8100/`) |
| **Healthcheck** | **Agregado:** `GET /api/v1/system/health/dependencies/` (OBS-STG-003) — **staff-only** (`IsAdminUser`), sonda IE + renderer (`/health` público, sem token) + base de dados; devolve sempre **200** com `status` geral (`ok\|degraded\|unavailable`) e por dependência (`ok\|degraded\|unavailable\|misconfigured\|unknown`) + `duration_ms`; URLs reduzidas a `configured`/`not_configured`. Timeout: `HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS` (default 2s). Proxy de readiness sem auth (até existir liveness próprio): `GET /api/v1/schema/`. |
| **Logs relevantes** | Loggers `campaigns.intelligence`, `integrations_bridge` (inclui `event=health_check overall=…`), `integrations_bridge.client`, `integrations_bridge.intelligence` (formato `key=value`). `config/settings.py` define agora `LOGGING` (OBS-STG-006): consola estruturada, nível `LOG_LEVEL` (default INFO) para `integrations_bridge*` e `campaigns.intelligence`. Os logs de job incluem `external_job_id` (correlação de callbacks). Tokens nunca logados (redacção + `_FORBIDDEN_KEYS`). |

### 2.1 Variáveis — `backend_core`

**Obrigatórias em staging/produção** (em local há defaults seguros):

| Variável | Tipo | Default | Notas |
|---|---|---|---|
| `SECRET_KEY` | 🔒 | dev inseguro | Forte e único em staging/produção. |
| `INTERNAL_API_TOKEN` | 🔒 | vazio | Segredo partilhado dos callbacks internos e (por default) das chamadas ao IE. **Tem de ser idêntico** ao do IE e do renderer. Vazio ⇒ callbacks internos rejeitados. |
| `ALLOWED_HOSTS` | ⚙️ | `localhost,127.0.0.1` | CSV; ajustar ao host de staging. |
| `DEBUG` | ⚙️ | `True` | `False` em staging/produção (activa guardas — ver §5/§9). |

**Opcionais / com default:**

| Variável | Tipo | Default | Notas |
|---|---|---|---|
| `CORS_ALLOWED_ORIGINS` | ⚙️ | `http://localhost:5200,…` | Origem do frontend. |
| `DB_ENGINE` | ⚙️ | `sqlite` | `postgres` para multi-processo fiável (ver §6). |
| `DB_NAME` / `DB_USER` / `DB_HOST` / `DB_PORT` | ⚙️ | — | Só com `DB_ENGINE=postgres`. |
| `DB_PASSWORD` | 🔒 | — | Só com PostgreSQL. |
| `ACCESS_TOKEN_LIFETIME_MINUTES` / `REFRESH_TOKEN_LIFETIME_DAYS` | ⚙️ | `60` / `7` | JWT. |
| `BACKEND_PUBLIC_BASE_URL` | ⚙️ | `http://localhost:8100` | Base do `callback_url` enviado ao renderer. |
| `INTELLIGENCE_ENGINE_BASE_URL` | ⚙️ | `http://localhost:8201` | Alvo do client síncrono IE. |
| `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` | ⚙️ | `10` | Timeout do client IE. |
| `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` | 🔒 | vazio → reutiliza `INTERNAL_API_TOKEN` | Token `X-Internal-Token` para o IE. |
| `INTELLIGENCE_ENGINE_ENABLED` | ⚙️ | `True` | `False` ⇒ 503 `intelligence_disabled`. |
| `INTELLIGENCE_ENGINE_DRY_RUN` | ⚙️ | `False` | `True` ⇒ stub sem HTTP. **Smoke real exige `False`.** |
| `INTELLIGENCE_ENGINE_MAX_RETRIES` / `..._RETRY_BACKOFF_SECONDS` | ⚙️ | `1` / `0.5` | Retry só de transitórios. |
| `CONTENT_RENDERER_BASE_URL` / `..._TIMEOUT_SECONDS` | ⚙️ | `http://localhost:8202` / `30` | `content_generation`. |
| `REPORT_RENDERER_BASE_URL` / `..._TIMEOUT_SECONDS` | ⚙️ | `http://localhost:8202` / `30` | renderer único — aponta ao mesmo serviço que `CONTENT_RENDERER_BASE_URL`. |
| `INTERNAL_CALLBACK_PATH` | ⚙️ | `/api/v1/internal/jobs/callback/` | Combinado com `BACKEND_PUBLIC_BASE_URL`. |
| `EXTERNAL_JOBS_ENABLED` | ⚙️ | `True` | `False` ⇒ jobs ficam `queued`. |
| `EXTERNAL_JOBS_DRY_RUN` | ⚙️ | `False` | `True` ⇒ submissão simulada. **Smoke real exige `False`.** |
| `HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS` | ⚙️ | `2.0` | Timeout (fail-fast) do healthcheck agregado ao sondar IE/renderer `/health`. Sem token. |
| `STRIPE_WEBHOOK_SECRET` / `STRIPE_API_KEY` | 🔒 | vazio | Billing skeleton; fora do escopo desta fase. |

**Secrets (`backend_core`):** `SECRET_KEY`, `INTERNAL_API_TOKEN`,
`INTELLIGENCE_ENGINE_INTERNAL_TOKEN`, `DB_PASSWORD`, `STRIPE_*`. Exemplo de `.env`
(placeholders):

```dotenv
SECRET_KEY=<SECRET_KEY>
INTERNAL_API_TOKEN=<INTERNAL_API_TOKEN>
# INTELLIGENCE_ENGINE_INTERNAL_TOKEN=<INTELLIGENCE_ENGINE_INTERNAL_TOKEN>  # opcional; vazio reutiliza o de cima
DB_PASSWORD=<DB_PASSWORD>
```

### 2.2 Dependências — `backend_core`

- **Base de dados** própria (SQLite local / PostgreSQL staging).
- **Intelligence Engine** (`:8201`) — chamada síncrona dentro do request.
- **Content Renderer** (`:8202`) — submissão de jobs + recepção de callback.
- É o **único ponto de orquestração**; recebe callbacks de volta do renderer.

---

## 3. `intelligence_engine` — FastAPI (stateless)

| Campo | Valor |
|---|---|
| **Descrição** | Calcula análise, scores/grade, momentos e recomendações de campanha (heurístico, determinístico, explicável). Sem persistência, sem chamar outros serviços. |
| **Directório** | `intelligence_engine/` |
| **Stack** | FastAPI 0.138 + Uvicorn, Pydantic 2 / pydantic-settings, Python 3.13 |
| **Porta default** | **8201** (configura por `INTELLIGENCE_ENGINE_PORT=8201` no `.env.example`; a porta efectiva vem do CLI `--port 8201`; o Backend Core assume `:8201` por default) |
| **Instalação/preparação** | `python -m venv venv` → `venv\Scripts\python.exe -m pip install -r requirements.txt` → (opcional) `cp .env.example .env` |
| **Comando de arranque** | `venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8201` (em staging, sem `--reload` e com `--host 0.0.0.0` conforme necessário — **por confirmar** o host de staging; validar com `curl http://<host>:8201/health`) |
| **Healthcheck** | `GET /health` — **público, sem auth**. Resposta: `{ status:"ok", service, version, timestamp }`. *Liveness* apenas (serviço stateless, sem dependências). |
| **Logs relevantes** | Logger JSON estruturado (UTC) com redacção de chaves sensíveis; loggers do Uvicorn unificados no mesmo formato. Nível por `LOG_LEVEL`. |

### 3.1 Variáveis — `intelligence_engine`

| Variável | Tipo | Obrig.? | Default | Notas |
|---|---|---|---|---|
| `INTERNAL_API_TOKEN` | 🔒 | **Sim em `production`** | vazio | Em `production` vazio ⇒ `config_error` no arranque. Em dev/test vazio ⇒ endpoints protegidos rejeitam tudo (não é bypass). **Tem de igualar** o do Backend Core. |
| `APP_ENV` | ⚙️ | Não | `development` | `production` desliga rotas de diagnóstico e endurece config. |
| `SERVICE_NAME` | ⚙️ | Não | `intelligence_engine` | Devolvido em `/health`. |
| `SERVICE_VERSION` | ⚙️ | Não | `0.1.0` | Devolvido em `/health`. |
| `LOG_LEVEL` | ⚙️ | Não | `INFO` | Nível do logger estruturado. |

**Secrets (`intelligence_engine`):** apenas `INTERNAL_API_TOKEN`.

```dotenv
APP_ENV=development
INTERNAL_API_TOKEN=<INTERNAL_API_TOKEN>   # mesmo valor do Backend Core e do Renderer
```

### 3.2 Dependências — `intelligence_engine`

- **Nenhuma** dependência de saída (não chama Backend Core, renderer nem DB).
- É **chamado pelo** Backend Core em `POST /intelligence/campaign` (e nos
  endpoints `analysis/scoring/recommendations/moments`).

---

## 4. `content_renderer` — Express / TypeScript

| Campo | Valor |
|---|---|
| **Descrição** | Recebe jobs do Backend Core, gera activos (PNG/PDF/HTML), guarda em storage local (MVP) e devolve o resultado via callback interno autenticado. Serve os três tipos de job. |
| **Directório** | `content_renderer/` |
| **Stack** | Node ≥18.18 + TypeScript, Express 5, Zod, Sharp (SVG→PNG), pdf-lib, logger JSON próprio |
| **Porta default** | **8202** (env `PORT`) |
| **Instalação/preparação** | `npm install` → `cp .env.example .env` (Windows: `Copy-Item .env.example .env`) → (para `npm start`) `npm run build` |
| **Comando de arranque** | `npm run dev` (watch, `tsx`) **ou** `npm run build` + `npm start` (`node dist/server.js`) |
| **Healthcheck** | `GET /health` — **público, sem auth**. Resposta: `{ status:"ok", service, version, uptime_seconds, timestamp }`. *Liveness*; não reporta storage nem callback. |
| **Logs relevantes** | Logger JSON estruturado com redacção recursiva (`token|secret|password|authorization|api_key|credential`). Eventos de ciclo de vida de job e de callback (`job.accepted`, `job.scheduled`, `callback.*`). Nível por `LOG_LEVEL`. |

### 4.1 Variáveis — `content_renderer`

| Variável | Tipo | Obrig.? | Default | Notas |
|---|---|---|---|---|
| `INTERNAL_API_TOKEN` | 🔒 | **Sim** (salvo dev inseguro) | vazio | **Tem de igualar** o do Backend Core. Vazio rejeitado em prod/dev salvo `ALLOW_INSECURE_EMPTY_TOKEN=true`. |
| `ALLOW_INSECURE_EMPTY_TOKEN` | ⚙️ | Não | `false` | Só dev: permite token vazio (auth desligada). Rejeitado em produção. |
| `PORT` | ⚙️ | Não | `8202` | Porta HTTP. |
| `NODE_ENV` | ⚙️ | Não | `development` | `production` desactiva `GET /files/*`. |
| `RENDERER_PUBLIC_BASE_URL` | ⚙️ | Não | `http://localhost:8202` | URL público do renderer. |
| `BACKEND_CORE_BASE_URL` | ⚙️ | Não | `http://localhost:8100` | Alvo dos callbacks. |
| `STORAGE_PROVIDER` | ⚙️ | Não | `local` | Só `local` implementado; valor desconhecido ⇒ falha no arranque. |
| `LOCAL_STORAGE_ROOT` | ⚙️ | Não | `./storage` | Storage MVP (não produção). |
| `LOCAL_STORAGE_PUBLIC_BASE_URL` | ⚙️ | Não | `http://localhost:8202/files` | URL de ficheiros locais (dev). |
| `MAX_JOB_PAYLOAD_BYTES` | ⚙️ | Não | `1048576` | 413 acima do limite. |
| `CALLBACK_TIMEOUT_SECONDS` | ⚙️ | Não | `20` | Timeout do callback (por tentativa). |
| `CALLBACK_MAX_ATTEMPTS` | ⚙️ | Não | `3` | `1` desliga retry. |
| `CALLBACK_RETRY_BASE_DELAY_MS` / `CALLBACK_RETRY_MAX_DELAY_MS` | ⚙️ | Não | `500` / `5000` | Backoff exponencial; sem retry em 4xx. |
| `RENDER_TIMEOUT_SECONDS` | ⚙️ | Não | `30` | Timeout de um render. |
| `REPORT_OUTPUT_FORMAT` | ⚙️ | Não | `auto` | `auto\|pdf\|html`. |
| `LOG_LEVEL` | ⚙️ | Não | `info` | Nível do logger. |

**Secrets (`content_renderer`):** apenas `INTERNAL_API_TOKEN`.

```dotenv
PORT=8202
NODE_ENV=development
INTERNAL_API_TOKEN=<INTERNAL_API_TOKEN>   # mesmo valor do Backend Core e do IE
# ALLOW_INSECURE_EMPTY_TOKEN=true  # só dev, se quiseres arrancar sem token
```

### 4.2 Dependências — `content_renderer`

- **Backend Core** (`:8100`) — **apenas para o callback** (`POST <callback_url>`).
- Storage **local** (filesystem) — não depende de S3/R2 nesta fase.
- É **chamado pelo** Backend Core em `POST /jobs` (responde 202; render + callback
  em background).
- **Loop fiável exige PostgreSQL** no Backend Core (ver §6).

---

## 5. Identidade e secrets — registo consolidado

| Secret (placeholder) | Onde é definido | Como é usado | Regras |
|---|---|---|---|
| `<INTERNAL_API_TOKEN>` | `backend_core`, `intelligence_engine`, `content_renderer` | Header `X-Internal-Token` entre serviços | **Idêntico nos três.** Só em header; nunca em corpo/query/log. |
| `<INTELLIGENCE_ENGINE_INTERNAL_TOKEN>` | `backend_core` (opcional) | Token específico para o IE | Vazio ⇒ reutiliza `<INTERNAL_API_TOKEN>`. |
| `<SECRET_KEY>` | `backend_core` | Assinatura Django/JWT | Forte/único em staging/produção. |
| `<DB_PASSWORD>` | `backend_core` (PostgreSQL) | Ligação à DB | Só com `DB_ENGINE=postgres`. |
| `<STRIPE_WEBHOOK_SECRET>` / `<STRIPE_API_KEY>` | `backend_core` | Billing (skeleton) | Fora do escopo desta fase. |

**Regra de ouro:** estes valores **nunca** entram em ficheiros versionados
(`.env` está git-ignored; só `.env.example` é committed, sempre vazio/placeholder),
nem em logs (redacção activa nos três serviços), nem neste documento.

**Guardas de arranque fail-fast (já existentes):**
- Django recusa arrancar se `DEBUG=False` + IE `ENABLED` + `DRY_RUN=False` + token vazio.
- IE recusa arrancar se `INTERNAL_API_TOKEN` vazio em `production`.
- Renderer recusa arrancar com token vazio salvo `ALLOW_INSECURE_EMPTY_TOKEN=true` (dev).

---

## 6. Base de dados

| Campo | Valor |
|---|---|
| **Quem usa** | Apenas o `backend_core`. IE e renderer **não** têm base de dados. |
| **Local (default)** | SQLite — `backend_core/db.sqlite3` (sem configuração). |
| **Staging/E2E** | PostgreSQL (`DB_ENGINE=postgres`). Harness de E2E: `postgres:16-alpine` via `content_renderer/docker-compose.e2e.yml`, porta host **55432→5432**, dados em **tmpfs** (descartável). |
| **Porquê PostgreSQL** | O callback do renderer corre noutro processo; SQLite não partilha linhas commitadas entre processos ⇒ callback dá 404. PostgreSQL é a base recomendada para o **loop multi-processo**. |
| **Healthcheck** | `pg_isready -U <DB_USER> -d <DB_NAME>` (usado pelo compose); `docker inspect --format '{{.State.Health.Status}}' chartrex_e2e_postgres` reporta `healthy`. |
| **Preparação** | `python manage.py migrate` + seeds (`seed_rbac`, `seed_billing`, `seed_content`). |
| **Secrets** | `<DB_PASSWORD>`. Valores do harness E2E (`chartrex_e2e_dev_only`, etc.) são **dev explícitos, não secretos**, e descartáveis. |

---

## 7. Dependências internas e externas (grafo)

```text
                 Cliente HTTP (JWT + X-Workspace-ID)
                              │
                              ▼
                  ┌─────────────────────────┐
                  │   backend_core  :8100    │  ◄── orquestrador + DB
                  └───────────┬──────────────┘
            síncrono          │            jobs (/jobs/)
   X-Internal-Token           │            X-Internal-Token
                  ┌───────────┴───────────┐
                  ▼                       ▼
       intelligence_engine        content_renderer
              :8201                     :8202
       GET /health                GET /health
       POST /intelligence/...     POST /jobs (202) → render → storage local
       (stateless, sem deps)            │ callback X-Internal-Token
                                        ▼
                       POST /api/v1/internal/jobs/callback/ → backend_core
                                        │
                                        ▼
                          PostgreSQL / SQLite (do backend_core)
```

| Dependência | Tipo | Direcção | Protocolo / auth |
|---|---|---|---|
| backend_core → intelligence_engine | Interna | síncrona (request do utilizador) | HTTP + `X-Internal-Token` |
| backend_core → content_renderer | Interna | submissão de job | HTTP `POST /jobs` + `X-Internal-Token` |
| content_renderer → backend_core | Interna | callback | HTTP `POST /…/callback/` + `X-Internal-Token` |
| backend_core → base de dados | Interna | persistência | SQLite (local) / PostgreSQL (staging) |
| (futuro) renderer → S3/R2 | Externa | storage | **fora do escopo** (hoje storage local) |

**Dependências externas relevantes hoje:** nenhuma obrigatória para o staging
técnico (sem S3/R2, sem Stripe real, sem APIs de terceiros). Docker é dependência
**operacional** apenas para o harness PostgreSQL do renderer (existe alternativa
`run-e2e-localpg.ps1` sem Docker).

---

## 8. Ordem de arranque recomendada

1. **Base de dados** (se PostgreSQL): `docker compose -f content_renderer/docker-compose.e2e.yml up -d` (ou cluster local) → esperar `healthy`.
2. **backend_core:** `migrate` + seeds → `runserver` (8100).
3. **intelligence_engine:** `uvicorn app.main:app --port 8201`.
4. **content_renderer:** `npm run dev` (ou `build`+`start`) (8202).
5. **Validar healthchecks:** `curl :8201/health`, `curl :8202/health`, Django via `:8100/api/v1/schema/` (até existir o agregado de OBS-STG-003).

> O **mesmo `<INTERNAL_API_TOKEN>`** tem de estar definido nos três processos
> antes do arranque, senão as chamadas internas dão 403.

---

## 9. Modo local vs Modo staging técnico

| Aspecto | Modo local | Modo staging técnico |
|---|---|---|
| `DEBUG` (Django) | `True` | `False` (activa guardas) |
| Base de dados | SQLite (default) | PostgreSQL (`DB_ENGINE=postgres`) |
| `INTERNAL_API_TOKEN` | placeholder de dev (igual nos 3) | segredo real, igual nos 3, fora de versionamento |
| `INTELLIGENCE_ENGINE_DRY_RUN` | pode ser `True` (sem IE a correr) | `False` (loop real) |
| `EXTERNAL_JOBS_DRY_RUN` | pode ser `True` (sem renderer) | `False` (loop real) |
| `APP_ENV` (IE) | `development` | `production` (exige token não-vazio) |
| `NODE_ENV` (renderer) | `development` (serve `/files`) | `production` (sem `/files`) |
| URLs | `localhost` | hosts explícitos (**por confirmar** o esquema de hosts de staging) |
| Storage renderer | local (`./storage`) | local (MVP) — S3/R2 ainda **fora do escopo** |

---

## 10. Prontidão (resumo; detalhe em OBS-STG-009)

- **Piloto técnico controlado:** possível — loops BC↔IE e BC↔Renderer já validados.
- **Produção:** **não** — faltam observabilidade real, logs centralizados/alertas,
  S3/R2, calibração de scores e staging contínuo. Esta fase entrega apenas a
  camada **mínima** de operação (healthchecks, smoke tests, runbook, troubleshooting,
  logs mínimos).

---

## 11. Itens "por confirmar"

| Item | Estado | Como validar |
|---|---|---|
| Porta do renderer (content e report) | Padronizado em 8202 | `curl http://localhost:8202/health` responde. `CONTENT_RENDERER_BASE_URL` e `REPORT_RENDERER_BASE_URL` apontam ambas para `:8202` (ver §1). |
| Host/bind do IE e do renderer em staging | por confirmar | Definir `--host` (uvicorn) e bind do Node conforme o ambiente; validar com `curl http://<host>:<porta>/health`. |
| Healthcheck dedicado do Backend Core | ✅ implementado (OBS-STG-003) | `GET /api/v1/system/health/dependencies/` (staff-only). Validar com JWT de utilizador `is_staff`; sem auth → 401, não-staff → 403. Liveness próprio (sem auth) continua por adicionar — entretanto `GET /api/v1/schema/` serve de proxy. |
| `LOGGING` do Django (visibilidade de INFO) | ✅ implementado (OBS-STG-006) | `config/settings.py` define `LOGGING` (consola, `LOG_LEVEL` default INFO). Validar com `python manage.py shell -c "import logging; print(logging.getLogger('integrations_bridge').getEffectiveLevel())"` → `20`. |

---

## 12. Referências

- Backlog da fase: [`01_backlog.md`](01_backlog.md)
- Análise do estado operacional: [`resultados/prompt_01_analise_estado_operacional.md`](resultados/prompt_01_analise_estado_operacional.md)
- Smoke test Backend Core ↔ Intelligence Engine: [`smoke_intelligence_engine.md`](smoke_intelligence_engine.md)
- Smoke test / checklist Backend Core ↔ Content Renderer: [`smoke_content_renderer.md`](smoke_content_renderer.md)
- Runbook de arranque local/staging: [`runbook_arranque_staging.md`](runbook_arranque_staging.md)
- Checklist de troubleshooting: [`checklist_troubleshooting.md`](checklist_troubleshooting.md)
- Painel de prontidão operacional: [`painel_prontidao_operacional.md`](painel_prontidao_operacional.md)
- Estado final da fase: [`estado_observabilidade_staging_ecossistema.md`](estado_observabilidade_staging_ecossistema.md)
- Estado IE↔BC: [`../integracao_intelligence_engine/estado_integracao_intelligence_engine.md`](../integracao_intelligence_engine/estado_integracao_intelligence_engine.md)
- READMEs: `backend_core/README.md`, `intelligence_engine/README.md`, `content_renderer/README.md`
- Harness E2E do renderer: `content_renderer/scripts/run-e2e-postgres.ps1`, `content_renderer/scripts/e2e_backend_core.py`, `content_renderer/docker-compose.e2e.yml`
