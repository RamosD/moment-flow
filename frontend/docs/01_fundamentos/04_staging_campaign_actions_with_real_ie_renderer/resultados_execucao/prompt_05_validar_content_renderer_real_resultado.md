# Prompt 05 — Validar Content Renderer real

**Data:** 2026-07-01
**Fase:** `04_staging_campaign_actions_with_real_ie_renderer` (STG-CA-005, Incremento 2)
**Âmbito:** exercitar o Content Renderer real (8202) via Backend Core; job → render → callback → output. Sem alteração de código de produto.
**Estado de execução:** `executado`

---

## 1. Resumo objectivo

O Content Renderer real foi exercitado **end-to-end** para os três fluxos, com jobs reais, callbacks e outputs em storage local:

| Fluxo | job_type | provider | job status | artefacto | estado final artefacto |
|---|---|---|---|---|---|
| report | `report_generation` | report_renderer | **completed** | Report | **completed** (PDF, storage_asset) |
| media kit | `media_kit_generation` | report_renderer | **completed** | MediaKit | **generated** (PDF, storage_asset) |
| content pack | `content_generation` | content_renderer | **completed** | ContentPackRequest | **completed** (2 ContentOutputs, assets) |

Confirmado que **não** ficaram apenas em `queued`: houve chamada real BC→CR (`POST /jobs/` → 202), render, **callback** CR→BC e evolução para estados terminais reais. Cenário CR indisponível tratado com erro controlado. Frontend nunca chamou 8202. Nenhum token em logs/relatório.

---

## 2. Pré-condições / configuração

- Criado `content_renderer/.env` com o **mesmo** `INTERNAL_API_TOKEN` do Backend Core (verificado igual); CR reiniciado — arrancou com `insecure_mode: false` (auth interna real activa, já não em modo inseguro).
- `backend_core/.env`: `EXTERNAL_JOBS_DRY_RUN=false` (jobs reais), `EXTERNAL_JOBS_ENABLED=true`; Backend Core reiniciado.
- Health confirmado:
  - CR: `GET http://localhost:8202/health` → 200 `{"service":"content_renderer","version":"0.1.0"}`
  - Backend Core → Renderer: `CONTENT_RENDERER_BASE_URL=http://localhost:8202`, `REPORT_RENDERER_BASE_URL=http://localhost:8202`.

---

## 3. Jobs criados (job_id / request_id)

| Fluxo | job_id | request_id | rota chamada |
|---|---|---|---|
| report_generation | `b8c20aaa-cf86-4cea-b4cc-670994be333b` | `0172d9d3c99d460c837ea2d73c19cd7c` | `POST http://localhost:8202/jobs/` → 202 |
| media_kit_generation | `17aeb503-31fc-478f-92cf-eb0908209698` | `f6f07fb5b7c245ce82ed84b23cd5bbc0` | `POST http://localhost:8202/jobs/` → 202 |
| content_generation | `fbee9bcb-bf07-4cff-a451-3a4a63c1e38d` | `2c9f9420f00b43928334dd5c801768dc` | `POST http://localhost:8202/jobs/` → 202 |

`external_job_id` não é usado neste renderer (o CR responde 202 e correlaciona por `job_id`/`request_id`).

Artefactos de origem (fluxo de duas escritas):
- Report `b59e56cb-…`, MediaKit `95bb4d78-…`, ContentPackRequest `faba9d6c-…` (cada um linka o job via `metadata.external_job_id`).

---

## 4. Estados (ciclo de vida do job)

`queued` → `submitted` (202 do CR) → *(render em background no CR)* → **callback** → `completed`.

Evidência (logs Backend Core):
```
event=job_created   ... status=queued    job_type=report_generation
internal_call start ... url=http://localhost:8202/jobs/
internal_call ok    ... status=202
event=job_submitted ... status=submitted
event=callback_received  ... status=submitted
event=callback_processed ... status=completed
POST /api/v1/internal/jobs/callback/ HTTP/1.1 200
```

---

## 5. Callback vs polling

**Callback** (não polling), confirmado nos dois lados:
- CR: `callback.started` → `callback.attempt_started` (`callback_url=http://localhost:8100/api/v1/internal/jobs/callback/`, attempt 1/3) → `callback.completed http_status:200 attempts:1`.
- Backend Core: `POST /api/v1/internal/jobs/callback/ 200`, `callback_received` → `callback_processed status=completed`.

O CR responde `202 Accepted` imediatamente e entrega o resultado por callback autenticado com `X-Internal-Token` (retry exponencial disponível, não necessário — 1 tentativa bastou).

---

## 6. Outputs e storage local

Ficheiros reais gerados em `content_renderer/storage/workspaces/{ws}/jobs/{job_id}/`:
```
.../jobs/b8c20aaa-…/report.pdf        (report_generation)
.../jobs/17aeb503-…/media_kit.pdf     (media_kit_generation)
.../jobs/fbee9bcb-…/output_001.png    (content_generation)
.../jobs/fbee9bcb-…/output_002.png    (content_generation)
```

Assets persistidos no Backend Core (ex.: report):
- `storage_provider=local`, `storage_key=workspaces/{ws}/jobs/{job_id}/report.pdf`, `mime=application/pdf`, `size=1141 bytes`, `fallback_html=false` (PDF real via pdf-lib).

Servidos em dev por `GET http://localhost:8202/files/{storage_key}` (`LOCAL_STORAGE_PUBLIC_BASE_URL`). O campo `public_url` no Asset do Backend Core não é populado nesta fase (o ficheiro é acessível pelo file server dev do CR) — limitação menor documentada.

ContentOutputs (content_generation): 2 outputs (`report`, `media_kit`), ambos `completed`, cada um com storage_asset.

---

## 7. related_* coerente

| CampaignAction (Prompt 04) / artefacto | related | estado |
|---|---|---|
| Report → `related_report` | consistente | Report agora `completed` |
| MediaKit → `related_media_kit` | consistente | MediaKit agora `generated` |
| ContentPackRequest → `related_content_pack_request` | consistente | Request `completed` + ContentOutputs |

As relações `related_*` mantêm-se coerentes; o avanço do render não quebra os vínculos.

---

## 8. Erros testados — Renderer indisponível

Parado o CR (8202), criado um report:
```
POST /reports/  → HTTP 201  (report persistido; sem rollback destrutivo)
report.status   = queued     (honesto — sem output, storage_asset=None)
job.status      = failed
job.error_message = "External service is unavailable."
stacktrace?     = não
```
O Backend Core degrada com estado honesto: o artefacto é preservado (`queued`), o job fica `failed` com mensagem controlada, sem stacktrace sensível e sem retry destrutivo. CR reiniciado a seguir — voltou a `completed` nos fluxos normais.

---

## 9. Evidência de que o frontend não chamou o Renderer

- Grep runtime `frontend/src`: **sem** `localhost:8202`, `:8202`, `/jobs/`, `content_renderer`. As únicas ocorrências de token são o comentário em `client.ts` (*"never sends X-Internal-Token"*) e a constante defensiva em `security.ts` (usada para **remover** o header).
- Toda a mediação é Backend Core → CR (logs mostram `internal_call ... url=http://localhost:8202/jobs/` originado no Backend Core, nunca no browser).

---

## 10. Segurança (logs)

Grep dos logs do Backend Core e do Content Renderer por `internal.?token|x-internal-token|secret|authorization|password` → **sem correspondências**. Os logs só contêm `job_id`, `request_id`, `workspace_id`, `job_type`, `status`, `http_status`, `duration`, `file_size_bytes`. O `X-Internal-Token` viaja apenas em headers e nunca é registado.

---

## 11. Validações executadas

| Validação | Resultado |
|---|---|
| CR health (8202) | ✅ 200 |
| Job real BC→CR (`POST /jobs/` 202) × 3 | ✅ |
| Render real (PDF/PNG em storage) | ✅ report.pdf, media_kit.pdf, 2× output.png |
| Callback CR→BC (200) × 3 | ✅ |
| Estados → `completed` (job + artefacto) | ✅ |
| Renderer indisponível → erro controlado | ✅ job `failed`, artefacto `queued`, sem stacktrace |
| Frontend não chama 8202 | ✅ grep limpo |
| Sem tokens em logs | ✅ grep limpo |
| `npm test` (Content Renderer) | ✅ **136 passed (13 files)**, 11.5s |
| Serviços finais (8100/8201/8202/5200) | ✅ todos 200 |

---

## 12. Limitações

| Limitação | Impacto |
|---|---|
| Campanha de teste "fraca" (sem track/sections) → render com `sections:0`, PDFs pequenos (~1.1 KB) | Baixo. Fluxo real validado; conteúdo mínimo. Para outputs ricos, criar dados dev com secções/stats. |
| `Asset.public_url` não populado no Backend Core (ficheiro acessível via file server dev do CR) | Baixo. Documentado; URL pública canónica é uma pendência de contrato para produção. |
| Storage é local (`content_renderer/storage`), não object storage | Esperado nesta fase (S3/R2 é migração futura). |
| Validação visual no browser não executada | Diferida para STG-CA-009. |

---

## 13. Ficheiros alterados

| Ficheiro | Operação |
|---|---|
| `content_renderer/.env` | **criado** — token partilhado + config dev (não commit; `.gitignore`) |
| `backend_core/.env` | **alterado** — `EXTERNAL_JOBS_DRY_RUN=false` |
| `frontend/docs/.../resultados_execucao/prompt_05_...resultado.md` | **criado** (este relatório) |
| `backend_core/db.sqlite3` + `content_renderer/storage/` | artefactos/jobs/outputs reais criados via fluxo real |

Nenhum código de produto foi alterado. Nenhum segredo consta deste relatório.

---

## 14. Próximo passo recomendado

Avançar para **STG-CA-006 (observabilidade mínima)** e **STG-CA-007 (erros reais entre serviços)**:
1. Confirmar `request_id`/`job_id` em todos os fluxos e o healthcheck agregado `GET /api/v1/system/health/dependencies/` (staff).
2. Testar token interno inválido, timeout e callback inválido (se seguro), confirmando erros controlados.
3. Depois, STG-CA-008 (segurança frontend) e STG-CA-009 (smoke visual no browser).

> Serviços a correr em background no fim desta iteração: Backend Core (8100), Intelligence Engine (8201), Content Renderer (8202, token real), Frontend (5200).
