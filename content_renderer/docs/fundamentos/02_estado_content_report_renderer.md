# Estado de Implementação — Content / Report Renderer

- **Serviço:** `content_renderer`
- **Localização:** `D:\Workspace\ChartRex\momentflow\content_renderer`
- **Versão:** `0.1.0`
- **Data:** 2026-06-24
- **Backlog de referência:** [`01_backlog_content_report_renderer.md`](01_backlog_content_report_renderer.md) (MVP) e [`03_backlog_hardening_pos_mvp_renderer.md`](03_backlog_hardening_pos_mvp_renderer.md) (hardening pós-MVP)
- **Regra arquitectural:** *Django governa o produto; o renderer apenas gera activos e reporta o resultado técnico.*

Este documento consolida o estado da implementação após os Pipelines 01–10 (MVP)
e o backlog de hardening pós-MVP **R-HARD-001..008** (callback em background,
retry, echo de template, storage provider, E2E PostgreSQL, validação real do
loop, coverage e esta documentação final).

---

## 1. Features implementadas

- **Fundação:** app Express pura/testável, `server.ts`, configuração validada por
  ambiente (`config/env.ts`), logger estruturado JSON com **redacção de segredos**.
- **Segurança/contrato HTTP:** middleware de autenticação interna
  (`X-Internal-Token`, comparação em tempo constante), validação de consistência
  de headers vs body, schema Zod do envelope, limite de tamanho de payload.
- **Endpoints:** `GET /health`, `POST /jobs`, `GET /files/*` (dev only).
- **Template engine:** registry de templates → SVG (string) → **PNG** via Sharp
  (sem browser), sanitização de texto/cor, 4 formatos com fallback.
- **Storage local:** layout por workspace/job, checksum SHA-256, mime inferido,
  metadata compatível com `Asset` do Django; bloqueio de _path traversal_.
- **Abstracção de storage (R-HARD-005):** interface `StorageProvider` (name,
  buildStorageKey, saveBuffer) + `LocalStorageProvider` (root, resolveWithinRoot,
  getPublicUrl); factory `createStorageProvider(config, logger)` selecciona por
  `STORAGE_PROVIDER` (só `local`; desconhecido falha no arranque). `RenderContext`
  depende de `StorageProvider`, não de `LocalStorage` concreto; contrato de `Asset`
  inalterado; `/files` registado só para provider local em dev. S3/R2 = futuro.
- **content_generation:** leitura de payload (campaign, artist, track,
  content_pack, templates, expected_outputs, branding, smart_link, billing_context,
  metadata); selecção de template por `template_key` com fallback; packs iniciais;
  **partial success**; outputs com metadata de `Asset`.
- **Echo de template (R-HARD-004):** cada output devolve `template_key` (usado) e,
  quando recebido, `template_id` no topo, mais `requested_template_key`,
  `requested_template_id`, `resolved_template_key`, `used_fallback_template`,
  `used_fallback_format`, `dimension`, `width`, `height` em `metadata`. `template_id`
  **nunca** é inventado (o registry não tem ids); campos novos são aditivos
  (retrocompatíveis) e a `metadata` não inclui segredos.
- **report_generation:** validação de payload, modelo de report, **PDF** (`pdf-lib`)
  com fallback **HTML** (`fallback_html`), storage + callback.
- **media_kit_generation:** validação (nome de artista), modelo, **PDF**/HTML
  reutilizando o toolkit partilhado (`renderers/shared`).
- **Execução em background leve (R-HARD-001):** `POST /jobs` separa recepção
  (`acceptJob`, valida `job_type` e regista `job.accepted`), agendamento
  (`scheduleJobExecution` → `setImmediate`, regista `job.scheduled`) e execução
  (`executeJob`: render → storage → callback). O **202** é devolvido de imediato,
  **sem** esperar pelo callback e **sem** `result` no corpo (entregue só via
  callback). Rede de segurança global no background: erro inesperado é capturado,
  logado (`job.execution_failed`), tenta callback `failed` _best-effort_ e nunca
  derruba o processo. Sem fila externa (sem BullMQ/Redis/RabbitMQ/Kafka).
- **Dispatcher + callback:** encaminhamento por `job_type`, **timeout de render**
  (`RENDER_TIMEOUT_SECONDS`) + **timeout de callback** (`CALLBACK_TIMEOUT_SECONDS`),
  callback `completed`/`partially_completed`/`failed`, logs de ciclo de vida
  (`job.accepted`, `job.scheduled`, `render.started/completed/failed`,
  `callback.started/completed/failed`, `job.execution_failed`).
- **Retry de callback com backoff (R-HARD-006):** até `CALLBACK_MAX_ATTEMPTS`
  tentativas com backoff exponencial (`CALLBACK_RETRY_BASE_DELAY_MS` →
  `CALLBACK_RETRY_MAX_DELAY_MS`). **Retry** em network error/timeout/HTTP
  500/502/503/504; **sem** retry em 4xx (400/401/403/404/409/422) — 4xx nunca é
  mascarado como sucesso. O cliente **não lança** (devolve `{ ok, statusCode,
  attempts }`) e mantém a falha não-fatal; logs por tentativa
  (`callback.attempt_started/attempt_failed/retry_scheduled/completed/
  delivery_failed`) sem token. Tempo total limitado (sem loop infinito).
- **Hardening:** erros normalizados, `error.details` redigidos (defesa em
  profundidade), logs sem token, path traversal bloqueado, job_type desconhecido
  controlado.

---

## 2. Endpoints

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| `GET` | `/health` | — | Liveness probe (200). |
| `POST` | `/jobs` | `X-Internal-Token` | Intake de jobs do Django (também aceita `/jobs/`). |
| `GET` | `/files/*` | — (dev only) | Serve ficheiros locais; bloqueia path traversal; **não** registado em production. |

---

## 3. Templates suportados

`generic_post`, `generic_story`, `milestone_card`, `weekly_growth_card`,
`release_card`, `report_cover`, `media_kit_cover`. Template desconhecido →
fallback `generic_post`.

---

## 4. Formatos suportados

| Formato | Dimensão |
|---|---|
| `post_1_1` | 1080×1080 |
| `post_4_5` | 1080×1350 |
| `story_9_16` | 1080×1920 |
| `thumbnail_16_9` | 1280×720 |

Formato desconhecido/ausente → fallback `post_1_1`. Outputs de documento: **PDF**
(`application/pdf`) ou **HTML** (`text/html`, fallback).

---

## 5. Jobs suportados

| `job_type` | Output | Provider no Django |
|---|---|---|
| `content_generation` | PNG(s) | `content_renderer` |
| `report_generation` | PDF/HTML | `report_renderer` |
| `media_kit_generation` | PDF/HTML | `report_renderer` |

Packs de content: `release_pack`, `milestone_pack`, `weekly_growth_pack`,
`monthly_recap_pack`, `auto_media_kit` (fallback simples); pack desconhecido ou
sem `expected_outputs` → 1 output fallback.

### Jobs NÃO suportados (devolvem `400 unsupported_job_type`)

`content_preview`, `video_rendering`, `metrics_collection`, `moment_detection`,
`insight_generation`, `recommendation_generation`.

---

## 6. Formato de storage

```text
<LOCAL_STORAGE_ROOT>/workspaces/<workspace_id>/jobs/<job_id>/<file_name>
```

Metadata devolvida (compatível com Django `Asset`): `storage_provider="local"`,
`bucket=""`, `storage_key`, `file_name`, `mime_type`, `file_size_bytes`,
`width`/`height`, `duration_seconds`, `checksum` (SHA-256), `public_url` (dev).
Apenas desenvolvimento; produção usará S3/R2 com o mesmo contrato.

---

## 7. Contratos de payload (entrada)

Envelope (`POST /jobs`):

```json
{
  "job_id": "...", "workspace_id": "...", "request_id": "...",
  "job_type": "content_generation",
  "callback_url": "http://localhost:8100/api/v1/internal/jobs/callback/",
  "entity": { "type": "content_pack_request", "id": "..." },
  "payload_version": "1.0",
  "payload": { }
}
```

- **content:** `campaign`, `artist`, `track`, `content_pack`, `templates`,
  `expected_outputs`, `branding`, `smart_link`, `billing_context`, `metadata`.
- **report:** `report_type`, `title`, `period_start/end`, `campaign`, `artist`,
  `track`, `sections`, `smart_link_stats`, `branding` (blocos ausentes podem vir
  `null`; `smart_link_stats` pode vir array).
- **media kit:** `artist` (com `name`), `campaign?`, `track?`, `items`, `assets`,
  `smart_links`, `branding`, `metadata`.

---

## 8. Contratos de callback (saída)

**Sucesso:** `status` `completed`/`partially_completed`, `error: null`,
`metadata.renderer`/`renderer_version`.

- **content:** `result.outputs[]` — cada output com
  `output_type/format/status/title/caption/cta/required/template_key/template_id?/asset/metadata`
  (metadata inclui `requested_template_key`, `requested_template_id?`,
  `resolved_template_key`, `used_fallback_template`, `used_fallback_format`,
  `dimension`, `width`, `height`).
- **report/media kit:** `result.asset` (bloco único) + `result.metadata`.

**Falha:** `status: "failed"`, `result: null`,
`error: { code, message, details }` (details redigidos).

Códigos de erro: `invalid_payload`, `unsupported_job_type`, `unsupported_template`,
`render_failed`, `storage_failed`, `callback_failed`, `timeout`.

Regra de partial success (content): `completed` se nenhum output falhou;
`partially_completed` se ≥1 gerado e ≥1 falhado; `failed` se nenhum gerado.

---

## 9. Validações executadas

| Validação | Resultado |
|---|---|
| `npm run build` (tsc) | ✅ Sem erros |
| `npm test` (vitest) | ✅ **136 testes**, 13 ficheiros (após R-HARD-001/006/004/005) |
| `npm run lint` (eslint) | ✅ Sem erros |
| `npm run test:coverage` (R-HARD-007) | ✅ Configurado (`@vitest/coverage-v8`); thresholds mín. lines 70/funcs 65/branches 55/statements 70; real: stmts 91.9%, branches 79.32%, funcs 95.89%, lines 91.86% |
| Backend `manage.py check` | ✅ `0 issues` |
| Backend `pytest` integração (bridge/content/reports) | ✅ **134 passed** (callbacks content/report/media-kit) |
| Backend `manage.py check` (R-HARD-003) | ✅ `0 issues` |
| **E2E real PostgreSQL** (R-HARD-003) | ✅ loop completo: content/report/media-kit `completed` criam Asset via callback; failed consistentes; idempotência confirmada |

Relatórios por pipeline em [`resultados/`](resultados/) (prompts 01–10).

---

## 10. Pendências

- ✅ **Callback em background leve** (R-HARD-001) — **concluído**: 202 imediato +
  execução em background (`setImmediate`), com rede de segurança global.
- ✅ **Retry de callback com backoff** (R-HARD-006) — **concluído**: até
  `CALLBACK_MAX_ATTEMPTS` com backoff exponencial; sem retry em 4xx.
- ✅ **Echo de `template_key`/`template_id`** (R-HARD-004) — **concluído**: outputs
  de content devolvem template usado/pedido + metadados de resolução.
- ✅ **Interface de storage** (R-HARD-005) — **concluído**: `StorageProvider` +
  factory; renderers desacoplados do `LocalStorage` concreto.
- ✅ **Harness E2E com PostgreSQL** (R-HARD-002) — **concluído**:
  `docker-compose.e2e.yml` + `scripts/run-e2e-postgres.ps1` (Docker) e
  `scripts/run-e2e-localpg.ps1` (cluster local, sem Docker) + `.env.e2e.example`.
- ✅ **Loop real Django → Renderer → Django** (R-HARD-003) — **validado com
  PostgreSQL** (evidência em [`guia_e2e_backend_core.md`](guia_e2e_backend_core.md) §10):
  content/report/media-kit `completed` criam **Asset** via callback; report/media-kit
  `failed` ficam consistentes; **idempotência** confirmada (re-entrega não duplica).
  content `partially_completed`/`failed` cobertos por `pytest` (o renderer é
  resiliente e não os produz via payload). Backend `pytest` relevante: **134 passed**.
- ✅ **Coverage Vitest** (R-HARD-007) — **concluído**: `@vitest/coverage-v8`
  configurado em `vitest.config.ts`; `npm run test:coverage` gera relatório
  texto/HTML/lcov em `coverage/` (git-ignorado); thresholds mínimos definidos
  (lines 70, functions 65, branches 55, statements 70) — cobertura real
  ultrapassa todos (ver [relatório](resultados/prompt_hardening_07_coverage_vitest.md)).
- **Storage S3/R2** implementando `StorageProvider`, mantendo o contrato de `Asset`.

### 10.1 Pendências remanescentes (fora do âmbito do backlog R-HARD-001..008)

Itens explicitamente fora do âmbito desta fase de hardening (ver
[backlog §5](03_backlog_hardening_pos_mvp_renderer.md)), que **não bloqueiam**
o uso actual em integração controlada mas faltam para produção plena ou são
decisões de produto futuras:

| Item | Estado | Nota |
|---|---|---|
| **Storage S3/R2 real** | Não implementado | Interface `StorageProvider` pronta (R-HARD-005); falta o provider concreto (SDK, credenciais, bucket). |
| **Observabilidade** (métricas, tracing, dashboards) | Não implementado | Logs estruturados sem secrets existem; sem exportação Prometheus/OpenTelemetry nem tracing distribuído. |
| **Métricas operacionais** (latência render/callback, taxa de erro) | Não implementado | Extracção manual a partir dos logs por evento; sem agregação/alerting automatizado. |
| **Fila persistente** (BullMQ/Redis/RabbitMQ/Kafka) | Deliberadamente fora do âmbito | Background é `setImmediate` *in-process* (R-HARD-001); um *restart* entre o 202 e o callback perde o trabalho em curso. Reavaliar conforme volume. |
| **Templates visuais avançados** (layout rico, logos/imagens, editor) | Não implementado | Geração actual (SVG→PNG via Sharp, PDF via `pdf-lib`) é deliberadamente simples; sem vídeo (Remotion/FFmpeg) nem IA generativa. |
| **Frontend** | Não implementado | Fora do âmbito deste serviço (renderer headless, consumido só pelo Django). |
| **FastAPI Intelligence Engine** | Não implementado | Não existe neste repositório; próximo passo do produto (backlog §11), independente deste serviço. |

---

## 11. Riscos

| Risco | Mitigação |
|---|---|
| Acoplamento ao payload do Django | `payload_version`, validação Zod, leitura defensiva (`null`/tipos), sem importar modelos Django. |
| Corrida com o estado do `ExternalJobReference` | ✅ Mitigado: 202 imediato + callback em background leve (R-HARD-001) — o callback deixa de competir com o submit síncrono do Django. |
| Erro silencioso no background | Rede de segurança global (`job.execution_failed`), logs estruturados e callback `failed` _best-effort_; testes de falha cobrem o cenário. |
| Retry duplicar callback / efeitos colaterais | Retry só em transientes (network/timeout/5xx) e nunca em 4xx; entrega bem-sucedida pára o retry. Depende da **idempotência** do callback no Django (RSK-HARD-002). |
| Storage local não é produção | Abstracção `StorageProvider` + factory (R-HARD-005); trocar por S3/R2 é adicionar um provider sem mudar renderers nem o contrato de `Asset`. |
| Falha de callback | Timeout + **retry com backoff** (R-HARD-006) + log estruturado; ficheiro permanece no storage (não-fatal). |
| Dependência de PDF | `pdf-lib` (pure JS) com import dinâmico + fallback HTML. |
| Exposição de segredos | Token nunca logado; `error.details` redigidos; `.env.example` sem valores reais. |

---

## 12. Próximo passo recomendado

1. ✅ **Callback em background leve** (R-HARD-001) — concluído.
2. ✅ **Retry simples de callback com backoff** (R-HARD-006) — concluído.
3. ✅ **Echo de `template_key`/`template_id`** no `content_generation` (R-HARD-004) — concluído.
4. ✅ **Interface de storage para S3/R2** (R-HARD-005) — concluído (`StorageProvider` + factory).
5. ✅ **Harness E2E com PostgreSQL** (R-HARD-002) — concluído (Docker + cluster local).
6. ✅ **Loop real** Django → Renderer → Django (R-HARD-003) — validado com PostgreSQL.
7. ✅ **Coverage Vitest** (R-HARD-007) — concluído (`@vitest/coverage-v8`, thresholds mínimos definidos, cobertura real acima de todos).
8. ✅ **Documentação final pós-hardening** (R-HARD-008) — concluído: README, este
   documento e o guia E2E reflectem o estado real; pendências remanescentes
   explícitas em [§10.1](#101-pendências-remanescentes-fora-do-âmbito-do-backlog-r-hard-001008);
   ver [relatório](resultados/prompt_hardening_08_documentacao_final.md).
9. Migrar o **storage para S3/R2** preservando o contrato de `Asset`.

**Backlog R-HARD-001..008 concluído.** Estado da fase (conforme
[backlog §10](03_backlog_hardening_pos_mvp_renderer.md)): pronto para ambiente
de integração — **sim**; pronto para piloto técnico — **sim**; pronto para
produção — **ainda não** (depende de S3/R2 real, observabilidade e política
operacional — ver §10.1). Próxima decisão de produto (fora deste serviço):
avançar para o **FastAPI Intelligence Engine** (backlog §11), já que o loop
Django ↔ Renderer está validado com PostgreSQL.
