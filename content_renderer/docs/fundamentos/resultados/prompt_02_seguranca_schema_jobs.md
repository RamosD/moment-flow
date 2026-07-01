# Relatório de Execução — Prompt 02: Segurança, Schema e Endpoint de Jobs

- **Data:** 2026-06-22
- **Pipeline:** 02 — Segurança, schema e endpoint de jobs
- **Épico/Tarefas do backlog:** CR-101 (auth interna), CR-102 (validação de headers), CR-103 (schema de envelope), CR-201 (POST /jobs), CR-202 (dispatcher)
- **Serviço:** `content_renderer`
- **Localização:** `D:\Workspace\ChartRex\momentflow\content_renderer`

---

## 1. Prompt executado

Implementar a camada HTTP de recepção de jobs do `content_renderer`:
autenticação interna por `X-Internal-Token` (comparação segura, sem expor o
token), validação dos headers `X-Workspace-ID` / `X-Job-ID` / `X-Request-ID` e
respectiva consistência com o body, validação do envelope com Zod, endpoint
`POST /jobs` e dispatcher por `job_type` (`content_generation`,
`report_generation`, `media_kit_generation`). Os handlers de render são
**placeholders controlados** que devolvem um resultado simulado — **sem**
renderização real, storage ou callback real. Inclui testes e relatório.

Backlog de referência: `docs/fundamentos/01_backlog_content_report_renderer.md`.

---

## 2. Objectivo

Fechar o contrato de recepção de jobs entre o Backend Core (Django) e o
renderer: autenticar a chamada interna, rejeitar de forma controlada pedidos
inválidos (403/400) e aceitar pedidos válidos (202), encaminhando-os para o
renderer correcto — mantendo a regra de que o renderer **nunca** decide
permissões, billing ou regras de produto.

---

## 3. Ficheiros criados

- `tests/jobs.test.ts` — testes do endpoint `POST /jobs` (auth, validação, dispatcher).
- `docs/fundamentos/resultados/prompt_02_seguranca_schema_jobs.md` — este relatório.

---

## 4. Ficheiros alterados

| Ficheiro | Alteração |
| -------- | --------- |
| `src/http/middleware.ts` | Novo `internalAuth` (comparação constante via SHA-256 + `timingSafeEqual`, bypass só em insecure mode) e `enforceJobHeaderConsistency` (headers vs body). |
| `src/jobs/job.controller.ts` | Implementado `receiveJob`: schema → headers → dispatch → **202**. |
| `src/jobs/job.service.ts` | Dispatcher passa a devolver `RenderResult`; docstring actualizada. |
| `src/jobs/job.schema.ts` | `ParseResult` passou a união discriminada (`success: true \| false`). |
| `src/jobs/job.types.ts` | Adicionados `JobType`, `RenderError`, `RenderResult`; `CallbackPayload.error` usa `RenderError`. |
| `src/renderers/renderer.types.ts` | `Renderer` devolve `RenderResult`. |
| `src/renderers/content/index.ts` | Placeholder devolve resultado simulado (`output_type: post`). |
| `src/renderers/reports/index.ts` | Placeholder devolve resultado simulado (`output_type: report`). |
| `src/renderers/media-kits/index.ts` | Placeholder devolve resultado simulado (`output_type: media_kit`). |
| `src/errors/errors.ts` | `UnsupportedJobTypeError` 422 → **400**; `toAppError` mapeia erros do body-parser (JSON malformado → 400, payload grande → 413). |
| `src/http/routes.ts` | Regista `POST /jobs` (auth + controller); `RouteDeps` recebe `logger` e `jobController`. |
| `src/app.ts` | Compõe o grafo de dependências (`jobService` → `jobController`) e injecta no router. |
| `README.md` | Documentado `POST /jobs` (headers, body, respostas, exemplo 202) e limitações actualizadas. |

> Nenhum ficheiro pré-existente fora do `src/`, `tests/` e `README.md` foi alterado.

---

## 5. Schemas criados / aplicados

- **`jobEnvelopeSchema`** (Zod, `.strict()`) — valida `job_id`, `workspace_id`,
  `request_id`, `job_type`, `callback_url` (URL), `entity.{type,id}`,
  `payload_version`, `payload` (objecto). Criado no Pipeline 01, **agora aplicado**
  no endpoint via `parseJobEnvelope`.
- **`jobEntitySchema`** (Zod, `.strict()`) — `type` + `id` não vazios.
- **`ParseResult<T>`** — agora união discriminada, permitindo _narrowing_ seguro
  no controller (erro só existe no ramo `success: false`).

Tipos TypeScript do domínio cobertos: `JobEnvelope`, `JobType`, `JobEntity`,
`CallbackPayload`, `RenderResult`, `RenderError` (+ `RenderOutput`, `JobResult`,
`AssetMetadata`, `JobStatus`).

---

## 6. Endpoints criados

| Método | Rota      | Auth | Descrição |
| ------ | --------- | ---- | --------- |
| `POST` | `/jobs`   | sim  | Recepção de jobs: auth → schema → headers → dispatch → 202. |
| `GET`  | `/health` | não  | (Pipeline 01) liveness probe. |

**Pipeline de validação do `POST /jobs`:**

1. `internalAuth` — `X-Internal-Token` (403 se ausente/errado).
2. Schema Zod do envelope (400 `invalid_payload`).
3. Consistência de headers vs body (400 `bad_request` em workspace/job).
4. Dispatcher por `job_type` (400 `unsupported_job_type` se desconhecido).
5. **202 `accepted`** com `result` simulado.

---

## 7. Comandos executados

```bash
# Validações
npm run build      # tsc
npm run lint       # eslint .
npm test           # vitest run

# Smoke test manual (servidor com token local)
INTERNAL_API_TOKEN=local-dev-token NODE_ENV=development PORT=8002 node dist/server.js
# 1) sem token            -> 403
# 2) content_generation   -> 202 (result simulado)
# 3) workspace mismatch   -> 400 bad_request
# 4) job_type desconhecido -> 400 unsupported_job_type
```

---

## 8. Resultado das validações

| Validação | Resultado |
| --------- | --------- |
| `npm run build` (tsc) | ✅ Sem erros |
| `npm run lint` (eslint) | ✅ Sem erros |
| `npm test` (vitest) | ✅ 4 ficheiros, **24 testes** (10 novos para `POST /jobs`) |
| Smoke `POST /jobs` sem token | ✅ **403** `unauthorized` |
| Smoke `POST /jobs` válido | ✅ **202** `accepted` + result simulado |
| Smoke workspace mismatch | ✅ **400** `bad_request` |
| Smoke `job_type` desconhecido | ✅ **400** `unsupported_job_type` |
| Token nos logs/respostas | ✅ Nunca aparece (auth loga apenas `reason: missing_token`/`invalid_token`) |

Testes de `POST /jobs` (todos a passar):
sem token (403), token errado (403), token correcto (202), payload inválido
(400), workspace mismatch (400), job mismatch (400), `job_type` desconhecido
(400), `content_generation` (202), `report_generation` (202),
`media_kit_generation` (202).

Exemplo de resposta 202 (resultado **simulado**):

```json
{"status":"accepted","job_id":"job-1","workspace_id":"ws-1","job_type":"content_generation","entity":{"type":"content_pack_request","id":"ent-1"},"result":{"status":"completed","outputs":[{"output_type":"post","format":"png","status":"completed","metadata":{"simulated":true}}]},"metadata":{"renderer":"content_renderer","renderer_version":"0.1.0","simulated":true}}
```

---

## 9. Decisões tomadas

1. **Comparação segura do token:** `X-Internal-Token` é comparado em tempo
   constante via digests SHA-256 + `crypto.timingSafeEqual` (length-safe). O
   token nunca é logado nem incluído em respostas.
2. **Insecure local mode:** quando `INTERNAL_API_TOKEN` está vazio (apenas
   possível em `development` com `ALLOW_INSECURE_EMPTY_TOKEN=true`, ou em `test`),
   a auth é **bypassed** com warning, coerente com o modo documentado no
   Pipeline 01. Em `production` o token vazio nem sequer arranca.
3. **Mismatch de headers:** `X-Workspace-ID` e `X-Job-ID` divergentes do body →
   **400** (`bad_request`). `X-Request-ID` divergente → **warning controlado**
   (o body é autoritativo), conforme a opção permitida pelo backlog (secção 8) —
   evita rejeitar jobs por uma divergência não crítica de correlação.
4. **`job_type` desconhecido → 400** (`unsupported_job_type`), em vez de aceitar
   e enviar callback `failed`: o job é recusado à entrada, por isso não há o que
   reportar via callback nesta fase.
5. **Execução síncrona com resultado simulado:** o dispatcher corre de forma
   síncrona e devolve `RenderResult` simulado no corpo do **202**. Isto mantém o
   contrato estável; o 202 + background leve + callback real entram no Pipeline 03.
6. **Erros do body-parser normalizados:** JSON malformado → **400**
   (`invalid_payload`), payload acima de `MAX_JOB_PAYLOAD_BYTES` → **413**,
   evitando 500 genéricos. O limite de tamanho já é aplicado por `express.json`.
7. **Envelope `.strict()`:** mantém-se a rejeição de campos desconhecidos para
   detectar cedo divergências de contrato; a evolução far-se-á via
   `payload_version`.

---

## 10. Pendências

- **Callback real** ao Django (`callback.client.ts` continua placeholder) — Pipeline 03.
- **Execução em background** (resposta 202 + `setImmediate`/promise) e envio de
  callback `completed`/`failed` — Pipeline 03 (CR-203 / CR-503).
- **Storage local real** (escrita, checksum, mime, metadata de Asset) — Pipeline 03.
- **Renderização real** (SVG → PNG / PDF) e templates — Pipelines 04+.
- **Partial success** em `content_generation` — Pipeline 08 (CR-802).
- O `result` devolvido é **simulado** (`simulated: true`), sem assets reais.

---

## 11. Próximo passo recomendado

Avançar para o **Pipeline 03 — Storage local e callback client**:

1. Implementar `storage/local-storage.ts` (escrita em disco por
   workspace/job, `storage_key` estável, checksum, `file_size_bytes`, mime) e o
   servidor local de ficheiros `GET /files/*` com protecção contra path traversal.
2. Implementar `callbacks/callback.client.ts` (POST ao `callback_url` com
   `X-Internal-Token`, timeout `CALLBACK_TIMEOUT_SECONDS`, retry simples, sem
   expor o token) e testes com mock HTTP.
3. Ajustar `POST /jobs` para responder **202** e despachar em **background leve**,
   enviando callback `completed`/`failed` após o render (CR-203).

Critério de pronto do próximo passo: um job aceite gera ficheiro no storage
local e o renderer envia um callback (mockado nos testes) com a metadata de
asset compatível com o Django.
