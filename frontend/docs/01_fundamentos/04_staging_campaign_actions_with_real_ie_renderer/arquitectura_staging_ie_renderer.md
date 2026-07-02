# Arquitectura — Staging Campaign Actions com IE e Renderer reais

> Fase: `04_staging_campaign_actions_with_real_ie_renderer`
> Estado: consolidado no fecho (STG-CA-010), 2026-07-02
> Fonte: leitura de código real + execução dos Prompts 01–09 desta fase.

Este documento descreve a arquitectura **validada em staging/dev** dos quatro serviços, com Intelligence Engine real (síncrono) e Content Renderer real (assíncrono por callback). Não descreve produção.

---

## 1. Os quatro serviços e portas canónicas

```text
┌─────────────────────┐        ┌──────────────────────┐
│  Frontend Web        │  HTTP  │  Backend Core         │
│  Vite / React        │ ─────▶ │  Django / DRF         │
│  localhost:5200      │  JWT   │  localhost:8100        │
└─────────────────────┘        │  /api/v1              │
        ▲  só fala com 8100     └───────┬───────┬───────┘
        │                               │       │
        │            X-Internal-Token   │       │  X-Internal-Token
        │            (síncrono)         │       │  (assíncrono, /jobs/)
        │                               ▼       ▼
        │                    ┌────────────────┐ ┌────────────────────┐
        │                    │ Intelligence    │ │ Content Renderer    │
        │                    │ Engine (FastAPI)│ │ (Node/Express)      │
        │                    │ localhost:8201  │ │ localhost:8202      │
        │                    └────────────────┘ └─────────┬──────────┘
        │                                                  │ callback
        └──────────────────────────────────────────────────┘
                    (Renderer → Backend Core: POST /api/v1/internal/jobs/callback/)
```

| Serviço | Stack | Porta | Papel |
|---|---|---|---|
| Frontend Web | Vite + React | **5200** (`strictPort`) | UI; fala **exclusivamente** com o Backend Core |
| Backend Core | Django + DRF | **8100** | orquestrador; única fronteira que fala com IE/Renderer |
| Intelligence Engine | FastAPI | **8201** | diagnóstico síncrono de campanha (analysis/scores/grade/moments/recommendations) |
| Content Renderer | Node/Express | **8202** | geração assíncrona de artefactos (report/media kit/content pack) via jobs + callback |

Portas antigas proibidas (validadas ausentes por `scripts/check-forbidden-ports.ps1`): 8000–8003, 8080–8085, 1420, 9011, 5173, 5174.

---

## 2. Fluxo Frontend → Backend Core → IE / Renderer

### 2.1 Intelligence (síncrono — War Room)

```text
Frontend  POST /api/v1/campaigns/{id}/intelligence/     (Authorization: Bearer <jwt>, X-Workspace-ID)
   │
Backend Core (CampaignIntelligenceService)
   │  build payload (workspace, campaign, track, platform_links, contexto)
   │  POST http://localhost:8201/intelligence/campaign   (X-Internal-Token, X-Workspace-ID, X-Request-ID)
   ▼
Intelligence Engine  →  200 { status:completed, engine, engine_version, request_id, result:{analysis,scores,grade,moments,recommendations,summary}, warnings }
   │
Backend Core  →  200 { source:"engine", status, grade, scores, recommendations, generated_at, request_id }
```

- **Síncrono**: request/response inline; **não** usa `ExternalJobReference`, `/jobs/` nem callback.
- `source=engine` (real) vs `source=dry_run` (stub) — governado por `INTELLIGENCE_ENGINE_DRY_RUN`. Nesta fase: **`false`** (IE real).
- Timeout `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS=10`; retry só para transitórios (`MAX_RETRIES=1` → 2 tentativas).

### 2.2 Renderer (assíncrono — artefactos)

```text
Frontend  POST /api/v1/reports/ | /media-kits/ | /content-pack-requests/   (cria o artefacto próprio primeiro)
   │
Backend Core (create_and_submit_external_job)
   │  1) cria ExternalJobReference status=queued  (ANTES de qualquer chamada)
   │  2) POST http://localhost:8202/jobs/  →  202 Accepted  →  status=submitted
   ▼
Content Renderer  (render em background, bounded por RENDER_TIMEOUT_SECONDS)
   │  POST http://localhost:8100/api/v1/internal/jobs/callback/   (X-Internal-Token; retry exponencial)
   ▼
Backend Core (IsInternalService)  →  aplica estado: running / completed / partially_completed / failed
                                   →  actualiza artefacto (Report→completed, MediaKit→generated, ContentPackRequest→completed + ContentOutputs)
```

- **Callback, não polling.** O CR responde 202 imediato e entrega o resultado por callback autenticado.
- Governado por `EXTERNAL_JOBS_DRY_RUN`. Nesta fase: **`false`** (renderer real; PDFs/PNGs reais em storage local).

| Action (UI) | Artefacto (1º POST) | `job_type` | Provider | Base URL |
|---|---|---|---|---|
| `report_request` | `/reports/` | `report_generation` | `report_renderer` | 8202 |
| `media_kit_request` | `/media-kits/` | `media_kit_generation` | `report_renderer` | 8202 |
| `content_pack` | `/content-pack-requests/` | `content_generation` | `content_renderer` | 8202 |

---

## 3. Regras de segurança (fronteira arquitectural)

1. **O Frontend só fala com o Backend Core** (`http://localhost:8100/api/v1`). Um único `fetch()` em todo o `frontend/src` (`shared/api/client.ts`); sem axios/WebSocket/EventSource. Validado ao vivo (Prompt 09): hosts observados só `5200` (assets) + `8100` (API); **zero** 8201/8202.
2. **O `X-Internal-Token` nunca sai do browser.** É um segredo service-to-service. `shared/api/security.ts` **remove** activamente `x-internal-token` (e `authorization`/`x-workspace-id`) de headers custom. O bundle compilado (`dist/`) não contém o token nem URLs internas.
3. **`Authorization` é sempre `Bearer` dinâmico**, injectado por provider em request-time (nunca hardcoded).
4. **O token viaja só em headers**, nunca em payloads nem logs (greps a 0 em BC/IE/CR — Prompts 06/07).
5. **Erros internos não expõem stacktrace nem secrets** (Prompt 07): IE indisponível/timeout/5xx → **503**; IE 4xx (403/422)/body inusável → **502**; renderer em baixo → job `failed` + artefacto em estado honesto.
6. **`.env` do frontend** só tem `VITE_BACKEND_API_BASE_URL`; sem `INTELLIGENCE_ENGINE_BASE_URL`/`CONTENT_RENDERER_BASE_URL`/`INTERNAL_API_TOKEN`.

---

## 4. Lifecycle de CampaignAction

Contrato persistente (fase 03), exercitado com recommendations reais (Prompt 04) e via UI (Prompt 09).

```text
                 create
 recommendation ───────▶ pending ──▶ in_progress ──▶ completed
 (source=engine)           │                          
                           ├──▶ dismissed  (dismiss + dismiss_reason)
                           ├──▶ cancelled
                           └──▶ failed
 mark_reviewed ───────────────────────────────────▶ completed (imediato)
 dismiss ─────────────────────────────────────────▶ dismissed (imediato)
```

- **`action_type`** (6): `manual_task`, `mark_reviewed`, `dismiss`, `report_request`, `media_kit_request`, `content_pack`.
- **`status`**: `pending`, `in_progress`, `completed`, `dismissed`, `cancelled`, `failed`.
- **`source`**: `recommendation` (nesta fase, sempre a partir de intelligence real) ou `manual`.
- **`recommendation_ref`**: id estável quando existe; como o IE real **não** devolve `id`/`title`/`type`, deriva-se posicional+conteúdo `{campaignId}:i{index}:{slug(action)}` (fallback documentado, correlação frontend).
- **`recommendation_snapshot`**: allowlist mínima (`action`, `reason`, `priority`, `confidence`, …) — **nunca** o payload integral do IE; serializer redige chaves sensíveis e limita a 64 KB.
- **Deduplicação**: `workspace + campaign + recommendation_ref + action_type` em estados activos (`pending`/`in_progress`/`completed`) → **HTTP 400** / na UI o botão fica "Active action exists". Estados terminais (`dismissed`/`cancelled`/`failed`) não bloqueiam nova tentativa.
- **Retry de job** (renderer): **nunca automático**; `retry_external_job` cria um **novo** job (preserva o antigo, `retried_from`), só a partir de estado terminal retryável.

---

## 5. Related artefacts

A CampaignAction liga-se ao artefacto próprio por campos `related_*` (validados por workspace/campaign e por compatibilidade de tipo):

| action_type | campo | artefacto | estado inicial | estado após renderer real |
|---|---|---|---|---|
| `report_request` | `related_report` | `Report` | `queued` | `completed` (PDF, storage_asset) |
| `media_kit_request` | `related_media_kit` | `MediaKit` | `draft` | `generated` (PDF) |
| `content_pack` | `related_content_pack_request` | `ContentPackRequest` | `queued` | `completed` (+ `ContentOutput`s) |

Fluxo de duas escritas: o artefacto próprio é criado primeiro, depois a CampaignAction regista o `related_*`. O avanço do render (via callback) não quebra os vínculos (Prompt 05/09).

---

## 6. Observabilidade

- **Síncrono (IE):** `request_id` (uuid hex) gerado no BC; viaja em `X-Request-ID`; correlaciona `intelligence_call start/ok/unavailable/timeout/http_error` + `campaign_id`/`workspace_id`. Sem `job_id`.
- **Assíncrono (renderer):** `ExternalJobReference.id` = `job_id`; `request_id` próprio por job; correlaciona BC↔CR (`job_created → job_submitted → callback_received → callback_processed`; no CR `job.accepted → render → callback.completed`).
- **Sem secrets nos logs:** greps por token/Authorization/Bearer/password/api_key/private_key → 0 (Prompts 06/07). O `X-Internal-Token` só em headers.
- **Sem payload integral do IE nos logs** (greps a 0).
- **Healthchecks:** IE `GET /health`, CR `GET /health` (públicos); agregado `GET /api/v1/system/health/dependencies/` (staff) sonda IE+CR+DB com URLs reduzidas a `configured/not_configured`.
- **Lacuna conhecida (OBS-L01/L02):** não existe correlation-id **único** ponta-a-ponta; a correlação faz-se por `campaign_id` + `workspace_id` (+ `job_id` no renderer). O IE não regista o `request_id` recebido a nível app. A resolver antes de produção.

---

## 7. Configuração de referência (dev/staging)

Backend Core (`backend_core/.env`, valores desta fase):
```env
INTELLIGENCE_ENGINE_BASE_URL=http://localhost:8201
INTELLIGENCE_ENGINE_DRY_RUN=false
INTELLIGENCE_ENGINE_TIMEOUT_SECONDS=10
INTELLIGENCE_ENGINE_MAX_RETRIES=1
CONTENT_RENDERER_BASE_URL=http://localhost:8202
REPORT_RENDERER_BASE_URL=http://localhost:8202
EXTERNAL_JOBS_DRY_RUN=false
INTERNAL_CALLBACK_PATH=/api/v1/internal/jobs/callback/
# INTERNAL_API_TOKEN / INTELLIGENCE_ENGINE_INTERNAL_TOKEN = <segredo partilhado, não commitado>
```
IE (`intelligence_engine/.env`) e CR (`content_renderer/.env`): o **mesmo** `INTERNAL_API_TOKEN` partilhado (não-vazio) que o BC. Frontend (`frontend/.env.local`): só `VITE_BACKEND_API_BASE_URL=http://localhost:8100/api/v1`.

> Nota: o token partilhado é obrigatório e não-vazio; com token vazio o IE devolve 403 (→502) e o callback CR→BC é rejeitado (403). Nunca commitar valores.
