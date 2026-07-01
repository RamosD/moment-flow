# Estado da Integração — Backend Core ↔ FastAPI / Renderer

- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`
- **Data:** 2026-06-22
- **Backlog de referência:** [`01_backlog_integracao_fastapi_renderer.md`](01_backlog_integracao_fastapi_renderer.md)
- **Regra arquitectural:** *Django governa o produto; FastAPI calcula e executa; Renderer gera activos.*

Este documento descreve o estado consolidado da fase de integração (Pipelines
01–10). O Django **orquestra** jobs externos e transforma callbacks em estado de
produto; **não** recolhe métricas, não detecta moments, não gera insights nem
renderiza ficheiros.

---

## 1. Funcionalidades implementadas

- **Configuração de integração** (`config/settings.py`, `.env.example`): URLs e
  timeouts por serviço, callback path, switches `EXTERNAL_JOBS_ENABLED` /
  `EXTERNAL_JOBS_DRY_RUN`, token interno.
- **Cliente HTTP interno** (`clients.py`): stdlib `urllib`, headers internos
  obrigatórios, erros tipados (timeout/HTTP/indisponível/JSON inválido), token
  nunca logado.
- **Service registry** (`registry.py`): resolve `job_type → provider → base_url/
  timeout`; switches enabled/dry-run; `callback_url()`.
- **`ExternalJobReference`**: payloads (request/response/callback), `request_id`,
  `idempotency_key`, `retry_count`, timestamps de ciclo de vida, estados
  (`queued/submitted/running/completed/partially_completed/failed/cancelled/
  expired/timeout`).
- **Submissão** (`create_and_submit_external_job`): cria o job antes de chamar,
  idempotente, dry-run/disabled, resiliente a falhas (job marcado failed/timeout).
- **Retry controlado** (`retry_external_job`): só de `failed/timeout/cancelled/
  expired`; cria novo job com `retry_count+1` e `retried_from`.
- **Callback interno**: normalizado, autenticado, idempotente, com dispatcher por
  `job_type`.
- **Integração de produto**:
  - Content Pack → `content_generation` (job + callback que cria `ContentOutput`/
    `Asset`, consome/liberta créditos, usage, notification, audit; suporta
    `partially_completed`).
  - Report → `report_generation` (job + callback que cria `Asset` report_pdf,
    liga `Report.storage_asset`, notification, audit).
  - Media Kit → `media_kit_generation` (job + callback que cria `Asset`
    media_kit_asset, marca `generated`, notification, audit).
- **Contratos do Intelligence Engine** (placeholders): builders + services para
  `metrics_collection`, `moment_detection`, `insight_generation`,
  `recommendation_generation`; handlers de callback guardam o resultado **sem**
  cálculo.
- **Hardening**: segurança de callback reforçada, logs estruturados sem token,
  Admin operacional de jobs.
- **Testes**: end-to-end (Content Pack / Report / Media Kit), segurança de
  callback, dry-run/disabled, idempotência, isolamento de workspace.

---

## 2. Fluxos suportados

### 2.1 Content Pack
```
POST /api/v1/content-pack-requests/ (JWT + X-Workspace-ID + RBAC content:generate)
  → valida workspace/campaign/pack/quota; reserva créditos (se pack tem custo)
  → cria ContentPackRequest (queued) + UsageEvent content_pack_requested
  → cria ExternalJobReference content_generation + submete (dry-run/real)
  → audit content_pack.job_submitted
Renderer → POST /api/v1/internal/jobs/callback/ (X-Internal-Token)
  completed → ContentOutput(s) + Asset(s); consume créditos; UsageEvent
              content_pack_generated; Notification content_ready; audit
              content_pack.completed (ou partially_completed)
  failed    → request failed; liberta créditos; Notification; audit content_pack.failed
```

### 2.2 Report
```
POST /api/v1/reports/  → Report queued + UsageEvent report_generated
  → ExternalJobReference report_generation + submete; audit report.job_submitted
callback completed → Asset report_pdf; Report.storage_asset; Report completed;
                     Notification report_ready; audit report.completed
callback failed    → Report failed (erro em metadata); Notification; audit report.failed
```

### 2.3 Media Kit
```
POST /api/v1/media-kits/ → MediaKit draft
  → ExternalJobReference media_kit_generation + submete; audit media_kit.job_submitted
callback completed → Asset media_kit_asset; MediaKit.storage_asset; MediaKit generated;
                     Notification media_kit_ready; audit media_kit.completed
callback failed    → erro em MediaKit.metadata (sem estado failed); Notification; audit
```

### 2.4 Intelligence Engine (placeholder)
```
request_metrics_collection / request_moment_detection / request_insight_generation /
request_recommendation_generation → ExternalJobReference + submete (dry-run-friendly)
callback → guarda callback_payload, transita o job, audit <job_type>.callback_received
           (Django NÃO calcula nada)
```

---

## 3. Contrato de payload (pedido)

O builder de cada domínio devolve o **payload de domínio**; o envelope acrescenta
os campos de transporte. Estrutura final enviada ao serviço externo:

```json
{
  "job_id": "<external_job_reference_id>",
  "workspace_id": "<workspace_id>",
  "request_id": "<uuid>",
  "job_type": "content_generation",
  "callback_url": "http://localhost:8100/api/v1/internal/jobs/callback/",
  "entity": { "type": "content_pack_request", "id": "<uuid>" },
  "payload_version": "1.0",
  "payload": {
    "campaign": { "id": "...", "name": "...", "slug": "..." },
    "artist": { "id": "...", "name": "..." },
    "track": { "id": "...", "title": "..." },
    "content_pack": { "pack_key": "release_pack", "name": "..." },
    "templates": [ { "template_key": "system_post", "output_type": "post", "format": "png" } ],
    "expected_outputs": [ { "output_type": "post", "format": "png", "required": true } ],
    "branding": { "workspace_name": "..." },
    "smart_link": null,
    "billing_context": { "credit_cost": "5", "credits_reserved": true },
    "metadata": {}
  }
}
```

`metrics_collection` (domínio) inclui `platform_links` derivados de
`TrackPlatformLink`:
```json
{
  "payload_version": "1.0", "workspace_id": "...", "campaign_id": "...",
  "track_id": "...", "requested_by": "...",
  "platform_links": [
    { "platform": "youtube", "external_id": "vid123",
      "url": "https://www.youtube.com/watch?v=vid123", "status": "valid" }
  ],
  "metadata": {}
}
```

> Os payloads **nunca** contêm tokens, passwords nem dados sensíveis.

---

## 4. Contrato de callback

```json
{
  "job_id": "<external_job_reference_id>",
  "external_job_id": "<id do serviço externo, opcional>",
  "workspace_id": "<workspace_id>",            // OBRIGATÓRIO
  "status": "completed",                         // ou partially_completed/failed/...
  "entity": { "type": "content_pack_request", "id": "<uuid>" },  // opcional, validado
  "result": { "outputs": [ /* ou asset para report/media kit */ ] },
  "error": { "code": "renderer_error", "message": "..." },        // em falha
  "metadata": {}
}
```

`result` de content (completed/partially): lista `outputs[]` com
`output_type/format/status/title/caption/cta/required/template_key/asset/metadata`.
`result` de report/media kit (completed): bloco `asset`
(`storage_provider/bucket/storage_key/file_name/mime_type/file_size_bytes/
checksum/format/title`).

---

## 5. Settings necessárias

```text
INTERNAL_API_TOKEN=                # secret; vazio → todos os callbacks rejeitados
BACKEND_PUBLIC_BASE_URL=http://localhost:8100
INTELLIGENCE_ENGINE_BASE_URL=http://localhost:8201
INTELLIGENCE_ENGINE_TIMEOUT_SECONDS=20
CONTENT_RENDERER_BASE_URL=http://localhost:8202
CONTENT_RENDERER_TIMEOUT_SECONDS=30
REPORT_RENDERER_BASE_URL=http://localhost:8202
REPORT_RENDERER_TIMEOUT_SECONDS=30
INTERNAL_CALLBACK_PATH=/api/v1/internal/jobs/callback/
EXTERNAL_JOBS_ENABLED=true
EXTERNAL_JOBS_DRY_RUN=false         # true em local enquanto FastAPI/renderer não existem
```

Mapeamento de provider: `content_generation`/`content_preview` →
`content_renderer`; `report_generation`/`media_kit_generation` →
`report_renderer`; `metrics_collection`/`moment_detection`/`insight_generation`/
`recommendation_generation` → `intelligence_engine`.

---

## 6. Endpoints internos

| Endpoint | Método | Auth | Descrição |
|---|---|---|---|
| `/api/v1/internal/jobs/callback/` | POST | `X-Internal-Token` | Callback de jobs externos (único endpoint interno) |

Os serviços de submissão (`create_and_submit_external_job`, `request_*`) são
chamados **internamente** pelos fluxos de produto / por código futuro; não há
endpoint público para abrir jobs técnicos.

---

## 7. Segurança

- **Autenticação** dos callbacks por `X-Internal-Token` comparado em tempo
  constante (`hmac.compare_digest`). Token vazio/errado/ausente → **403**.
- **`workspace_id` obrigatório** e validado contra `job.workspace` → **400** se
  ausente ou divergente.
- **`entity.type`/`entity.id`** (quando presentes) validados contra o job → **400**.
- **Idempotência:** callback repetido no mesmo estado → 200 no-op; job terminal
  com estado diferente → 409; efeitos chaveados (usage/créditos/assets/
  notifications) nunca duplicam.
- **Créditos:** reserva antes; consume só em sucesso; release/refund em falha.
- **Logs estruturados sem segredos:** `workspace_id/job_id/job_type/provider/
  status/request_id`; nunca token nem payloads completos.

---

## 8. Exemplos textuais (sem secrets)

**Submissão de content pack (envelope):** ver secção 3.

**Callback completed (content):**
```json
{
  "job_id": "f1e2...", "workspace_id": "a1b2...", "status": "completed",
  "entity": { "type": "content_pack_request", "id": "c3d4..." },
  "result": { "outputs": [
    { "output_type": "post", "format": "png", "status": "completed",
      "template_key": "system_post",
      "asset": { "storage_provider": "s3", "storage_key": "outputs/post.png",
                 "file_name": "post.png", "mime_type": "image/png",
                 "file_size_bytes": 12345, "checksum": "deadbeef" } }
  ] }
}
```

**Callback failed (report):**
```json
{
  "job_id": "f1e2...", "workspace_id": "a1b2...", "status": "failed",
  "entity": { "type": "report", "id": "r5s6..." },
  "error": { "code": "renderer_error", "message": "Falha ao gerar PDF." }
}
```

> Nenhum exemplo contém `X-Internal-Token` (esse viaja apenas no header, nunca no
> corpo nem em logs).

---

## 9. Pendências

- **FastAPI Intelligence Engine** e **Content/Report Renderer** reais (fora de
  escopo desta fase — contratos prontos, dry-run no Django).
- **Modelos técnicos** (snapshots/moments/insights/recommendations) — pertencem ao
  FastAPI; o Django apenas guarda `callback_payload`.
- **Notificação técnica para admins** em callbacks de Intelligence Engine
  (opcional, não implementada).
- **Wiring de produto** para disparar `request_metrics_collection` etc. (quando o
  motor existir).
- **`LOGGING` formal** em settings (handlers/formatters por ambiente).
- **`content_preview`** tem handler próprio (apenas transita o job); efeitos de
  preview a definir quando o renderer existir.

---

## 10. Próximo passo recomendado

Avançar para o **FastAPI Intelligence Engine** e o **Content/Report Renderer**
reais, consumindo estes contratos: receber o envelope em `/jobs/`, processar e
chamar `POST /api/v1/internal/jobs/callback/` com `X-Internal-Token` e
`workspace_id`. Do lado do Django, ligar `request_metrics_collection` &
companhia aos fluxos de produto (War Room / monitorização) e adicionar os modelos
técnicos de leitura quando o motor devolver resultados estáveis.
