# Content / Report Renderer

Serviço de renderização da plataforma **ChartRex / MomentFlow**.

Recebe _jobs_ enviados pelo **Backend Core (Django)**, gera activos visuais
mínimos (**PNG / PDF / HTML**) e devolve o resultado ao Django via _callback_
interno autenticado.

> **Separação de responsabilidades**
>
> - O **Django** governa o produto: utilizadores, permissões (RBAC), billing,
>   estado, criação de `ExternalJobReference` e processamento de callbacks.
> - O **Renderer** apenas gera activos e reporta o resultado técnico. Não decide
>   permissões, não conhece billing, não cria utilizadores e não acede à base de
>   dados do Django.

## Estado

Ciclo real ligado de ponta a ponta: `POST /jobs` → **aceitação (202)** →
**execução em background leve** (render → **storage local** → **callback** ao
Django). Jobs suportados:

- **`content_generation`** — PNG(s) via template engine (SVG → PNG/Sharp); packs
  (`release_pack`, `milestone_pack`, `weekly_growth_pack`, `monthly_recap_pack`,
  `auto_media_kit`); _partial success_.
- **`report_generation`** — **PDF** simples (`pdf-lib`) com fallback **HTML**.
- **`media_kit_generation`** — **PDF**/HTML reutilizando a mesma estratégia.

Inclui erros normalizados, timeouts (render + callback), logs estruturados sem
token e integração validada contra os contratos do Backend Core. Estado detalhado:
[`docs/fundamentos/02_estado_content_report_renderer.md`](docs/fundamentos/02_estado_content_report_renderer.md).

---

## Stack

- **Node.js** (>= 18.18) + **TypeScript**
- **Express** — servidor HTTP
- **Zod** — validação do envelope de job e dos payloads de report/media kit
- **Sharp** — rasterização SVG → PNG (libvips, sem browser)
- **pdf-lib** — geração de PDF (pure JS, sem browser/Playwright)
- **dotenv** — carregamento de configuração
- Logger estruturado próprio (JSON, com redacção de segredos)
- **Vitest** + **Supertest** — testes
- **tsx** — execução em desenvolvimento
- **ESLint** (+ typescript-eslint) — linting

---

## Arquitectura

```text
Django (Backend Core)                      content_renderer (este serviço)
─────────────────────                      ──────────────────────────────
cria ExternalJobReference ──POST /jobs/──►  auth (X-Internal-Token)
                                            └► valida envelope (Zod)
                                            └► consistência headers vs body
                                            └► acceptJob (valida job_type)
                          ◄────202 Accepted──┤  (acknowledgement; sem result)
                                            └► scheduleJobExecution (setImmediate)
                                            · · · · · · · · background leve · · · · ·
                                            └► dispatcher por job_type
                                                 ├─ content  → SVG→PNG (Sharp)
                                                 ├─ report   → PDF (pdf-lib)/HTML
                                                 └─ media kit→ PDF (pdf-lib)/HTML
                                            └► storage local (checksum/metadata)
   recebe callback  ◄──POST callback_url──  callback completed/partially/failed
   cria Asset/Output/Report/MediaKit
```

Fluxo no serviço: `server.ts` → `app.ts` (factory Express) → `http/routes.ts`
(auth + `/health` + `/jobs` + `/files`) → `jobs/job.controller.ts` (valida +
`acceptJob` + `scheduleJobExecution` + **202**) → **background leve
(`setImmediate`)** → `jobs/job.service.ts` `executeJob` (dispatcher + timeout +
callback) → `renderers/*` (render real) → `storage/local-storage.ts` →
`callbacks/callback.client.ts`.

### Execução em background leve (R-HARD-001)

O `POST /jobs` **não** espera pelo render nem pelo callback. A recepção é
separada da execução em três passos:

1. **Recepção** — valida token, headers e envelope; `acceptJob` valida o
   `job_type` (desconhecido → **400**, sem callback) e regista `job.accepted`.
2. **Agendamento** — `scheduleJobExecution` regista `job.scheduled` e destaca a
   execução para o próximo _tick_ via `setImmediate` (background leve, **sem**
   fila externa — nada de BullMQ/Redis/RabbitMQ/Kafka).
3. **Execução** — `executeJob` corre render → storage → callback e entrega o
   resultado ao Django. Erros de render geram callback `failed`; falhas de
   entrega do callback são **não-fatais**; qualquer erro inesperado é capturado
   por uma rede de segurança global (`job.execution_failed`), logado, tenta um
   callback `failed` _best-effort_ e **nunca derruba o processo**.

O **202** é apenas um _acknowledgement_ de aceitação — **já não** transporta o
`result` (o resultado é entregue exclusivamente pelo callback). Isto remove a
corrida com o estado do `ExternalJobReference` no Django.

---

## Instalação

```bash
npm install
cp .env.example .env   # depois edita o .env conforme necessário
```

> No Windows (PowerShell): `Copy-Item .env.example .env`

---

## Configuração (.env)

Todas as variáveis estão documentadas em [`.env.example`](.env.example) (sem
valores sensíveis — o `INTERNAL_API_TOKEN` vem vazio).

| Variável                       | Descrição                                                    | Default                        |
| ------------------------------ | ------------------------------------------------------------ | ------------------------------ |
| `PORT`                         | Porta HTTP                                                    | `8002`                         |
| `NODE_ENV`                     | `development` \| `production` \| `test`                      | `development`                  |
| `INTERNAL_API_TOKEN`           | Segredo partilhado com o Django (`X-Internal-Token`)         | _(vazio)_                      |
| `ALLOW_INSECURE_EMPTY_TOKEN`   | Permite token vazio **apenas** em desenvolvimento            | `false`                        |
| `RENDERER_PUBLIC_BASE_URL`     | URL público do renderer                                      | `http://localhost:8002`        |
| `BACKEND_CORE_BASE_URL`        | URL base do Django                                           | `http://localhost:8000`        |
| `STORAGE_PROVIDER`             | Backend de storage: `local` (único implementado; `s3`/`r2` futuros) | `local`                |
| `LOCAL_STORAGE_ROOT`           | Raiz do storage local (MVP, **não** é produção)              | `./storage`                    |
| `LOCAL_STORAGE_PUBLIC_BASE_URL`| URL base dos ficheiros locais (dev)                          | `http://localhost:8002/files`  |
| `MAX_JOB_PAYLOAD_BYTES`        | Tamanho máximo do payload de job (bytes)                     | `1048576`                      |
| `CALLBACK_TIMEOUT_SECONDS`     | Timeout do callback para o Django (por tentativa)            | `20`                           |
| `CALLBACK_MAX_ATTEMPTS`        | Tentativas totais de entrega do callback (`>= 1`; `1` desliga retry) | `3`                   |
| `CALLBACK_RETRY_BASE_DELAY_MS` | Delay base do backoff entre tentativas, em ms (`>= 0`)       | `500`                          |
| `CALLBACK_RETRY_MAX_DELAY_MS`  | Tecto do backoff, em ms (`>= base delay`)                    | `5000`                         |
| `RENDER_TIMEOUT_SECONDS`       | Timeout de um render                                         | `30`                           |
| `REPORT_OUTPUT_FORMAT`         | Formato de report/media kit: `auto` \| `pdf` \| `html`       | `auto`                         |

### Regras do `INTERNAL_API_TOKEN`

- **production** → o token **tem** de estar preenchido. Arranque falha se vazio.
- **development** → token vazio é **rejeitado**, _excepto_ se activares
  explicitamente o modo inseguro local com `ALLOW_INSECURE_EMPTY_TOKEN=true`.
- **test** → token vazio é permitido para a suite de testes correr sem segredos.

O `INTERNAL_API_TOKEN` **nunca** é escrito nos logs: o logger redige
recursivamente chaves sensíveis (`token`, `secret`, `authorization`, `api_key`, …).

---

## Scripts

| Script              | Descrição                                            |
| ------------------- | ---------------------------------------------------- |
| `npm run dev`       | Arranca em modo watch (`tsx`)                        |
| `npm run build`     | Compila TypeScript para `dist/`                      |
| `npm start`         | Corre o build (`node dist/server.js`)                |
| `npm test`          | Corre os testes (`vitest run`)                       |
| `npm run test:watch`| Testes em watch                                      |
| `npm run test:coverage` | Testes + relatório de cobertura (`vitest run --coverage`) |
| `npm run lint`      | ESLint                                               |
| `npm run typecheck` | Verificação de tipos sem emitir (`tsc --noEmit`)     |

---

## Correr localmente

```bash
# desenvolvimento (watch)
npm run dev

# build + start
npm run build
npm start
```

### Testes

```bash
npm test            # vitest run (suite completa)
npm run test:watch  # watch
npm run test:coverage  # suite completa + relatório de cobertura (V8)
```

### Coverage (R-HARD-007)

`npm run test:coverage` corre a suite com o provider **`@vitest/coverage-v8`**
(configurado em `vitest.config.ts`) e gera:

- **texto** no terminal (resumo por ficheiro/pasta);
- **HTML** em `coverage/index.html` (navegável, linha-a-linha);
- **lcov** em `coverage/lcov.info` (para CI/ferramentas externas).

`coverage/` é gerado localmente e está no `.gitignore` (não é versionado).

**Thresholds mínimos** (falham o comando se não cumpridos):

| Métrica | Threshold | Real (2026-06-24) |
| --- | --- | --- |
| Statements | 70% | 91.9% |
| Branches | 55% | 79.32% |
| Functions | 65% | 95.89% |
| Lines | 70% | 91.86% |

Âmbito: `src/**/*.ts`, excluindo `src/server.ts` (entrypoint do processo, não
importado pelos testes — exercitado indirectamente via `app.ts`) e os módulos
puramente de tipos (`job.types.ts`, `renderer.types.ts`, `storage.types.ts`).
Ver relatório completo em
[`docs/fundamentos/resultados/prompt_hardening_07_coverage_vitest.md`](docs/fundamentos/resultados/prompt_hardening_07_coverage_vitest.md).

---

## Estrutura

```text
content_renderer/
  package.json  tsconfig.json  eslint.config.mjs  vitest.config.ts  .env.example  README.md
  scripts/
    run-e2e.ps1            # orquestra E2E renderer + backend_core
    e2e_backend_core.py    # driver E2E (ver guia)
  src/
    app.ts                 # factory da app Express (pura, testável)
    server.ts              # entrypoint: carrega config, faz listen
    constants.ts           # nome/versão do renderer
    config/env.ts          # loader e validação de ambiente
    http/
      routes.ts            # GET /health, POST /jobs, GET /files/*
      middleware.ts        # logging + auth interna + consistência headers + erros
      files.ts             # GET /files/* (dev only) com bloqueio de path traversal
    jobs/
      job.schema.ts        # schema Zod do envelope
      job.types.ts         # tipos do domínio (JobEnvelope, CallbackPayload, …)
      job.controller.ts    # handler POST /jobs (validação + acceptJob + schedule + 202)
      job.service.ts       # acceptJob + scheduleJobExecution + executeJob (dispatcher + timeout + callback)
      with-timeout.ts      # RENDER_TIMEOUT_SECONDS
    renderers/
      renderer.types.ts    # RenderContext (config, logger, storage)
      content/             # content-generation.renderer.ts (SVG→PNG, packs, partial)
      reports/             # report-generation.renderer.ts (+ model/html/pdf)
      media-kits/          # media-kit-generation.renderer.ts (+ model/html/pdf)
      shared/              # pdf-doc.ts, pdf-primitives.ts, html.ts (toolkit partilhado)
    templates/
      registry.ts          # catálogo de templates + renderTemplate (SVG→PNG)
      svg.ts               # buildSvg, renderSvgToPng, sanitizeTextForSvg, sanitizeColor
      dimensions.ts        # formatos suportados + resolveOutputDimensions
    storage/
      storage.types.ts     # StorageProvider/LocalStorageProvider/SaveBufferInput/AssetMetadata
      storage.factory.ts   # createStorageProvider(config, logger) (local; S3/R2 futuro)
      local-storage.ts     # LocalStorageProvider (escrita, checksum, mime, metadata)
    callbacks/
      callback.client.ts   # cliente de callback (POST + token + timeout)
      callback.payload.ts  # builders de payload completed/failed
      render-error.ts      # agregação de erro normalizado por job_type
    logging/logger.ts      # logger estruturado com redacção
    errors/errors.ts       # modelo de erros normalizado
  tests/                   # ficheiros de teste (vitest + supertest) + helpers.ts
```

---

## Endpoint `GET /health`

Liveness probe pública (sem auth).

```bash
curl http://localhost:8002/health
```

```json
{
  "status": "ok",
  "service": "content_renderer",
  "version": "0.1.0",
  "uptime_seconds": 3,
  "timestamp": "2026-06-23T10:00:00.000Z"
}
```

---

## Endpoint `POST /jobs`

Endpoint interno que recebe jobs do Django. Aplica, por esta ordem:
autenticação interna (`X-Internal-Token`) → validação de envelope (Zod) →
consistência de headers vs body → aceitação (`acceptJob`, valida `job_type`) →
agendamento em background leve (`scheduleJobExecution`) → resposta **202**. O
render + storage + callback correm **depois** do 202, em background
(`setImmediate`).

### Headers obrigatórios

| Header             | Obrigatório | Regra                                              |
| ------------------ | ----------- | -------------------------------------------------- |
| `X-Internal-Token` | sim         | Deve igualar `INTERNAL_API_TOKEN` (senão **403**)  |
| `X-Workspace-ID`   | sim         | Deve igualar `body.workspace_id` (senão **400**)   |
| `X-Job-ID`         | sim         | Deve igualar `body.job_id` (senão **400**)         |
| `X-Request-ID`     | recomendado | Se divergir de `body.request_id` → **warning** controlado (body é autoritativo) |
| `Content-Type`     | sim         | `application/json`                                  |

### Contrato de job (envelope)

```json
{
  "job_id": "<external_job_reference_id>",
  "workspace_id": "<workspace_id>",
  "request_id": "<request_id>",
  "job_type": "content_generation",
  "callback_url": "http://localhost:8000/api/v1/internal/jobs/callback/",
  "entity": { "type": "content_pack_request", "id": "<uuid>" },
  "payload_version": "1.0",
  "payload": { }
}
```

Tipos de job suportados: `content_generation`, `report_generation`,
`media_kit_generation`. Qualquer outro → **400** `unsupported_job_type`.

### Respostas

| Situação                                       | Status | `error.code`            |
| ---------------------------------------------- | ------ | ----------------------- |
| Job aceite (render/callback agendados em background) | `202`  | —                  |
| Token ausente/errado                           | `403`  | `unauthorized`          |
| Envelope inválido                              | `400`  | `invalid_payload`       |
| Header workspace/job ≠ body                    | `400`  | `bad_request`           |
| `job_type` não suportado                       | `400`  | `unsupported_job_type`  |
| Payload acima de `MAX_JOB_PAYLOAD_BYTES`       | `413`  | `invalid_payload`       |

O `POST /jobs` aceita o job e responde **202 rapidamente**, **sem esperar** pelo
render/callback. O corpo do 202 é apenas um _acknowledgement_:

```json
{
  "status": "accepted",
  "job_id": "<id>",
  "workspace_id": "<ws>",
  "job_type": "content_generation",
  "entity": { "type": "content_pack_request", "id": "<uuid>" },
  "metadata": { "renderer": "content_renderer", "renderer_version": "0.1.0" }
}
```

O resultado do render **não** vem no 202 — é entregue ao Django **apenas** pelo
callback, executado em background leve (ver
[Execução em background leve](#execução-em-background-leve-r-hard-001)).

---

## Contrato de callback

O renderer chama `POST <callback_url>` com `X-Internal-Token` e
`Content-Type: application/json`.

**Sucesso (`completed` / `partially_completed`):**

```json
{
  "job_id": "<id>",
  "workspace_id": "<ws>",
  "status": "completed",
  "entity": { "type": "content_pack_request", "id": "<uuid>" },
  "result": { "outputs": [ /* content */ ] },
  "error": null,
  "metadata": { "renderer": "content_renderer", "renderer_version": "0.1.0" }
}
```

- **content_generation** → `result.outputs[]` (cada output com `asset`).
- **report_generation / media_kit_generation** → `result.asset` (bloco único) +
  `result.metadata`.

**Falha (`failed`):**

```json
{
  "job_id": "<id>",
  "workspace_id": "<ws>",
  "status": "failed",
  "entity": { "type": "report", "id": "<uuid>" },
  "result": null,
  "error": { "code": "render_failed", "message": "Falha ao gerar o relatório.", "details": {} },
  "metadata": { "renderer": "content_renderer", "renderer_version": "0.1.0" }
}
```

`error.details` é redigido (sem token/segredos/paths sensíveis/payload completo).
Códigos: `invalid_payload`, `unsupported_job_type`, `unsupported_template`,
`render_failed`, `storage_failed`, `callback_failed`, `timeout`.

### Retry de callback com backoff (R-HARD-006)

A entrega do callback é resiliente a indisponibilidade momentânea do Django. O
cliente faz até `CALLBACK_MAX_ATTEMPTS` tentativas com **backoff exponencial**
(`delay = min(CALLBACK_RETRY_MAX_DELAY_MS, CALLBACK_RETRY_BASE_DELAY_MS · 2^(n-1))`):

- **Retry** em: _network error_, _timeout_, e HTTP **500 / 502 / 503 / 504**.
- **Sem retry** em: HTTP **400 / 401 / 403 / 404 / 409 / 422** (qualquer 4xx) — um
  4xx é reportado como não-entrega, **nunca** mascarado como sucesso.
- **2xx** → entregue.

O tempo total é limitado por `tentativas × (timeout + backoff)` — **nunca** um
_loop_ infinito; `send` **não** bloqueia indefinidamente e **não** lança (devolve
sempre `{ ok, statusCode, attempts }`, mantendo a falha de callback **não-fatal**
para o processo).

Logs por entrega (sem token/secrets/payload completo; com `job_id`,
`workspace_id`, `attempt`, `max_attempts` e `http_status` quando existe):
`callback.attempt_started`, `callback.attempt_failed`, `callback.retry_scheduled`,
`callback.completed`, `callback.delivery_failed`. O `JobService` regista ainda, no
log de ciclo de vida do job, `callback.started` e `callback.completed`/
`callback.failed` com `attempts`/`http_status`.

### Metadata de `asset` (compatível com Django `Asset`)

```json
{
  "storage_provider": "local",
  "bucket": "",
  "storage_key": "workspaces/<ws>/jobs/<job>/output_001.png",
  "file_name": "output_001.png",
  "mime_type": "image/png",
  "file_size_bytes": 50858,
  "width": 1080,
  "height": 1080,
  "duration_seconds": null,
  "checksum": "<sha256>"
}
```

---

## Exemplo — `content_generation`

`payload` (excerto):

```json
{
  "campaign": { "name": "Summer Push" },
  "artist": { "name": "Nova" },
  "track": { "title": "Midnight Drive" },
  "content_pack": { "pack_key": "release_pack" },
  "templates": [ { "template_key": "release_card", "output_type": "post", "format": "png" } ],
  "expected_outputs": [ { "output_type": "post", "format": "png", "required": true } ],
  "branding": { "brand_color": "#E17055" },
  "smart_link": { "url": "https://chartrex.link/midnight" }
}
```

`result` no callback:

```json
{
  "outputs": [
    {
      "output_type": "post", "format": "png", "status": "completed",
      "title": "Midnight Drive", "caption": "Summer Push", "cta": "Listen now",
      "required": true, "template_key": "release_card", "template_id": "tmpl-uuid-123",
      "asset": { "storage_provider": "local", "storage_key": "...", "file_name": "output_001.png",
                 "mime_type": "image/png", "file_size_bytes": 50858, "width": 1080, "height": 1080,
                 "duration_seconds": null, "checksum": "..." },
      "metadata": {
        "content_pack": "release_pack",
        "requested_template_key": "release_card", "resolved_template_key": "release_card",
        "requested_template_id": "tmpl-uuid-123",
        "used_fallback_template": false, "used_fallback_format": false,
        "dimension": "post_1_1", "width": 1080, "height": 1080
      }
    }
  ]
}
```

#### Echo de template (R-HARD-004)

Cada output de `content_generation` devolve, de forma explícita e
**retrocompatível** (campos novos são aditivos), informação suficiente para o
Django resolver o `Template`/`ContentOutput`:

| Campo | Local | Significado |
|---|---|---|
| `template_key` | topo do output | template **realmente usado** (resolvido pelo registry; melhor valor compatível com o Django). |
| `template_id` | topo do output | id **ecoado** do pedido (`templates[]` ou `expected_outputs[]`). Só presente quando recebido — **nunca inventado**. |
| `requested_template_key` | `metadata` | `template_key` original do pedido (preservado mesmo se desconhecido). |
| `requested_template_id` | `metadata` | `template_id` original do pedido, se enviado. |
| `resolved_template_key` | `metadata` | template resolvido pelo registry. |
| `used_fallback_template` | `metadata` | `true` quando o `template_key` pedido não existe (fallback `generic_post`). |
| `used_fallback_format` | `metadata` | `true` quando o `format`/`dimension` pedido não existe (fallback `post_1_1`). |
| `dimension` / `width` / `height` | `metadata` | formato resolvido e dimensões em px. |

O renderer **não** tem ids próprios de template, por isso `template_id` só existe
no retorno se vier no pedido. Os mesmos campos de resolução acompanham também os
outputs **falhados** (com `template_key` = valor resolvido). A `metadata` não
inclui token/segredos.

Sem `expected_outputs` nem pack reconhecido, é gerado **1 output fallback**
(`generic_post`). Partial success: outputs gerados ficam `completed`, falhados
`failed` (com `metadata.error` seguro); estado geral `completed` /
`partially_completed` / `failed`.

---

## Exemplo — `report_generation`

`payload` (excerto):

```json
{
  "report_type": "weekly_growth", "title": "Weekly Growth Report",
  "period_start": "2026-06-01", "period_end": "2026-06-07",
  "artist": { "name": "Nova" }, "campaign": { "name": "Summer Push" },
  "sections": [ { "heading": "Highlights", "items": ["+12% streams"] } ],
  "smart_link_stats": { "total_clicks": 1234 }, "branding": { "brand_color": "#0984E3" }
}
```

`result` no callback (bloco único `asset`):

```json
{
  "asset": { "storage_provider": "local", "storage_key": "workspaces/<ws>/jobs/<job>/report.pdf",
             "file_name": "report.pdf", "mime_type": "application/pdf", "format": "pdf",
             "file_size_bytes": 1479, "checksum": "...", "title": "Weekly Growth Report" },
  "metadata": { "report_type": "weekly_growth", "fallback_html": false }
}
```

Sem PDF (ou `REPORT_OUTPUT_FORMAT=html`): `report.html`, `mime_type: text/html`,
`metadata.fallback_html: true`. Payload inválido (sem title/report_type/sections)
→ callback `failed`.

---

## Exemplo — `media_kit_generation`

`payload` (excerto):

```json
{
  "artist": { "name": "Nova", "tagline": "Synthwave from Lisbon", "bio": "...",
              "contact": { "email": "team@nova.fm" } },
  "track": { "title": "Midnight Drive" }, "campaign": { "name": "Summer Push" },
  "items": [ "Featured on New Music Friday", { "title": "1M streams", "description": "first month" } ],
  "assets": [ { "file_name": "press_photo.jpg", "type": "image/jpeg" } ],
  "smart_links": [ { "label": "Listen", "url": "https://chartrex.link/midnight" } ],
  "branding": { "brand_color": "#0984E3" }
}
```

`result` no callback (bloco único `asset`):

```json
{
  "asset": { "storage_provider": "local", "storage_key": "workspaces/<ws>/jobs/<job>/media_kit.pdf",
             "file_name": "media_kit.pdf", "mime_type": "application/pdf", "format": "pdf",
             "file_size_bytes": 1617, "checksum": "...", "title": "Nova — Media Kit" },
  "metadata": { "artist_name": "Nova", "highlight_count": 2, "fallback_html": false }
}
```

Requisito mínimo: **nome do artista**. Sem artista → callback `failed`.

---

## Templates e formatos

Templates (`templates/registry.ts`): `generic_post`, `generic_story`,
`milestone_card`, `weekly_growth_card`, `release_card`, `report_cover`,
`media_kit_cover`. Template desconhecido → fallback `generic_post`.

| Formato          | Dimensão   |
| ---------------- | ---------- |
| `post_1_1`       | 1080×1080  |
| `post_4_5`       | 1080×1350  |
| `story_9_16`     | 1080×1920  |
| `thumbnail_16_9` | 1280×720   |

Formato desconhecido → fallback seguro `post_1_1`.

---

## Storage local e `GET /files/*` (apenas dev)

Os ficheiros são guardados em
`<LOCAL_STORAGE_ROOT>/workspaces/<workspace_id>/jobs/<job_id>/<file_name>` com
metadata compatível com o `Asset` do Django (ver acima).

`GET /files/*` serve esses ficheiros **apenas em desenvolvimento** (não é
registado quando `NODE_ENV=production`). Pedidos com _path traversal_ (`../`,
caminhos absolutos) devolvem **404**. **Não** é storage de produção — em produção
os activos virão de object storage (S3/R2) mantendo o mesmo contrato de `Asset`.

### Abstracção de storage (`StorageProvider`, R-HARD-005)

Os renderers dependem da **interface** `StorageProvider` (em
`storage/storage.types.ts`), não da implementação concreta:

```text
StorageProvider                # name, buildStorageKey, saveBuffer → AssetMetadata
  └─ LocalStorageProvider      # + root, resolveWithinRoot, getPublicUrl (dev /files)
       └─ createLocalStorage   # implementação filesystem (MVP/dev)
```

- A factory `createStorageProvider(config, logger)` escolhe o provider a partir de
  `STORAGE_PROVIDER` (hoje só `local`); um valor desconhecido **falha no arranque**
  com `ConfigError` (validado também no loader de ambiente).
- O `RenderContext.storage` é `StorageProvider` — trocar para **S3/R2** no futuro é
  adicionar um novo provider à factory **sem** tocar nos renderers nem no contrato
  de `Asset`.
- `GET /files/*` só é registado quando o provider é local
  (`isLocalStorageProvider`) e fora de produção. Um provider de object storage
  serve URLs próprias e não expõe `/files`.
- **Esta fase não migra para S3/R2** nem adiciona SDK AWS/R2 — apenas separa a
  interface da implementação local. A implementação S3/R2 é trabalho futuro.

---

## Integração com o Backend Core (Django)

```text
Django cria ExternalJobReference → POST /jobs/ (renderer) → render → storage local
  → POST /api/v1/internal/jobs/callback/ (Django) → Asset + ContentOutput/Report/MediaKit
```

**Mapeamento de jobs:** `content_generation` → `content_renderer` (:8002);
`report_generation` / `media_kit_generation` → provider `report_renderer` no
Django (aponta-se `REPORT_RENDERER_BASE_URL=http://localhost:8002`, pois o renderer
único serve os três tipos).

**Configuração partilhada:** o `INTERNAL_API_TOKEN` tem de ser **igual** nos dois
serviços. No Django: `CONTENT_RENDERER_BASE_URL`/`REPORT_RENDERER_BASE_URL=http://localhost:8002`,
`BACKEND_PUBLIC_BASE_URL=http://localhost:8000`, `EXTERNAL_JOBS_ENABLED=true`,
`EXTERNAL_JOBS_DRY_RUN=false`.

Guia + checklist E2E:
[`docs/fundamentos/guia_e2e_backend_core.md`](docs/fundamentos/guia_e2e_backend_core.md).
Para um loop **multi-processo fiável** use o harness **PostgreSQL** (R-HARD-002):
`docker-compose.e2e.yml` + `scripts/run-e2e-postgres.ps1` (vars dev em
[`.env.e2e.example`](.env.e2e.example), sem secrets); sem Docker, use
`scripts/run-e2e-localpg.ps1` contra um cluster PostgreSQL local. O
`scripts/run-e2e.ps1` (SQLite) fica como variante legada — limitado em
multi-processo (ver guia §6/§8). **Loop validado** (R-HARD-003): content/report/
media-kit `completed` criam Asset via callback, com idempotência (guia §10).

---

## Limitações

- **PDF/HTML simples** — sem gráficos avançados, sem BI, sem layout rico
  (imagens/logos).
- **Sem vídeo** (Remotion/FFmpeg), sem editor visual, sem IA generativa.
- **Storage local** (`/files`) é **apenas** desenvolvimento — não é S3/R2/CDN.
- **Retry de callback** é em memória (sem fila persistente nem _dead-letter_): se
  o processo reiniciar entre tentativas, a entrega em curso perde-se.
- O renderer **não** tem autenticação de utilizadores, RBAC nem billing — isso é
  do Django.

---

## Troubleshooting

| Sintoma | Causa provável / acção |
| ------- | ---------------------- |
| Arranque falha com `ConfigError` de `INTERNAL_API_TOKEN` | Token vazio em production/development. Define `INTERNAL_API_TOKEN` ou, só em dev, `ALLOW_INSECURE_EMPTY_TOKEN=true`. |
| `403 unauthorized` no `POST /jobs` | `X-Internal-Token` ausente ou diferente do `INTERNAL_API_TOKEN`. Confirma o mesmo token nos dois serviços. |
| `400 bad_request` | `X-Workspace-ID`/`X-Job-ID` não coincidem com o body. |
| `400 invalid_payload` | Envelope inválido (Zod). Vê `error.details.issues`. |
| Callback `failed` com `code: invalid_payload` | Payload de report sem `title`/`report_type`/`sections`, ou media kit sem nome de artista. |
| Report/media kit sai em HTML em vez de PDF | `pdf-lib` indisponível ou `REPORT_OUTPUT_FORMAT=html`. `metadata.fallback_html=true`. |
| Callback dá `404` no Django em E2E local com SQLite | Limitação multi-processo do SQLite (servidor não vê linhas commitadas por outro processo). Usar PostgreSQL ou o fluxo de produto via API. Ver o guia E2E. |
| Callback dá `404` mesmo com PostgreSQL | Confirma que **não há outro servidor Django** (de uma sessão anterior) a ocupar a porta esperada — um servidor antigo com outra BD intercepta o callback e devolve `404` (não é falha de contrato). Usa uma porta livre (`-DjangoPort`) e `BACKEND_PUBLIC_BASE_URL` a apontar para ela. Ver guia E2E §10. |
| Harness PostgreSQL (Docker) falha a subir o container | Docker Desktop **engine** não está em execução (CLI instalado ≠ engine ligado). Inicia o Docker Desktop; alternativa sem Docker: harness com cluster PostgreSQL local (`scripts/run-e2e-localpg.ps1`, guia §9). |
| `GET /files/...` dá 404 | Path traversal bloqueado, ficheiro inexistente, ou `NODE_ENV=production` (rota desactivada). |
| Token aparece em logs | Não deveria — o logger redige chaves sensíveis. Reporta como bug. |

---

## Pendências remanescentes

Após o backlog de hardening pós-MVP (R-HARD-001..008), o que **ainda não** está
implementado — fora do âmbito desta fase por desenho (ver
[backlog §5](docs/fundamentos/03_backlog_hardening_pos_mvp_renderer.md)):

| Item | Estado | Nota |
|---|---|---|
| **Storage S3/R2 real** | Não implementado | `StorageProvider` já abstrai a interface (R-HARD-005); falta o provider concreto (SDK, credenciais, bucket) — implementação futura sem tocar nos renderers. |
| **Observabilidade** (métricas, tracing, dashboards) | Não implementado | Logs estruturados existem (sem secrets), mas não há exportação de métricas (Prometheus/OpenTelemetry) nem tracing distribuído. |
| **Métricas operacionais** (latência de render/callback, taxa de erro) | Não implementado | Os logs por evento permitem extracção manual; não há agregação/alerting automatizado. |
| **Fila persistente** (BullMQ/Redis/RabbitMQ/Kafka) | Deliberadamente fora do âmbito | O background é `setImmediate` *in-process*; um *restart* entre o 202 e o callback perde o trabalho em curso. Reavaliar se o volume de jobs justificar. |
| **Templates visuais avançados** (layout rico, logos/imagens, editor) | Não implementado | PNG/PDF actuais são deliberadamente simples (SVG→PNG via Sharp, PDF via `pdf-lib`); sem vídeo (Remotion/FFmpeg) nem IA generativa. |
| **Frontend** | Não implementado | Fora do âmbito deste serviço (renderer headless); consumido apenas pelo Django. |
| **FastAPI Intelligence Engine** | Não implementado | Não existe neste repositório; é o próximo passo do produto recomendado pelo backlog (§11), independente deste serviço. |

Nenhum destes itens bloqueia o uso actual do renderer em ambiente de integração
controlada — bloqueiam apenas **produção** plena (storage real, observabilidade)
ou são **decisões de produto futuras** (frontend, Intelligence Engine, fila).

---

## Próximos passos

1. ✅ **Callback em background leve** (R-HARD-001): 202 imediato + execução em
   background (`setImmediate`), com rede de segurança global. **Concluído.**
2. ✅ **Retry simples de callback com backoff** (R-HARD-006): até
   `CALLBACK_MAX_ATTEMPTS` com backoff exponencial; sem retry em 4xx. **Concluído.**
3. ✅ **Interface de storage** (R-HARD-005): `StorageProvider` + factory; renderers
   desacoplados da implementação local. **Concluído.**
4. ✅ **E2E com PostgreSQL e loop real Django ↔ Renderer** (R-HARD-002/003):
   validado com evidência — Asset criado via callback em content/report/media-kit,
   falhas consistentes, idempotência confirmada. **Concluído** (ver guia E2E §10).
5. ✅ **Coverage Vitest** (R-HARD-007): `npm run test:coverage` com
   `@vitest/coverage-v8` e thresholds mínimos. **Concluído.**
6. **Storage S3/R2** implementando `StorageProvider`, mantendo o contrato de `Asset`.
7. Layout de PDF/imagem mais rico e novos formatos/templates, conforme necessidade.

Backlog de referência:
[`docs/fundamentos/01_backlog_content_report_renderer.md`](docs/fundamentos/01_backlog_content_report_renderer.md).
