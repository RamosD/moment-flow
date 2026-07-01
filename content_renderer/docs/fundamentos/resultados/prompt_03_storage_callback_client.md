# Relatório de Execução — Prompt 03: Storage Local e Callback Client

- **Data:** 2026-06-22
- **Pipeline:** 03 — Storage local e callback client
- **Épico/Tarefas do backlog:** CR-301 (storage local), CR-302 (endpoint `/files`), CR-503 (callback client), CR-801 (erros normalizados)
- **Serviço:** `content_renderer`
- **Localização:** `D:\Workspace\ChartRex\momentflow\content_renderer`

---

## 1. Prompt executado

Implementar o **storage local** para ficheiros renderizados (escrita em disco
por workspace/job, `storage_key` estável, checksum, tamanho, mime, metadata
compatível com `Asset` do Django), o endpoint **`GET /files/*`** (apenas dev,
com bloqueio de path traversal) e o **callback client** (POST ao `callback_url`
com `X-Internal-Token`, `Content-Type: application/json`, timeout
`CALLBACK_TIMEOUT_SECONDS`, sem expor o token), incluindo os payloads
`completed`/`failed` segundo o contrato do Django e os erros normalizados.

Backlog de referência: `docs/fundamentos/01_backlog_content_report_renderer.md`.

---

## 2. Objectivo

Dar ao renderer a capacidade de **persistir activos** localmente (MVP) e de
**reportar resultados** ao Backend Core (Django), mantendo a metadata estável e
compatível com `Asset`, sem expor segredos e sem decidir regras de produto.

---

## 3. Ficheiros criados

- `src/http/files.ts` — handler `GET /files/*` (dev only) com bloqueio de path traversal.
- `src/callbacks/callback.payload.ts` — builders dos payloads `completed`/`failed`.
- `tests/storage.test.ts` — testes do storage local.
- `tests/files.test.ts` — testes do servidor `/files`.
- `tests/callback.test.ts` — testes do callback client.
- `docs/fundamentos/resultados/prompt_03_storage_callback_client.md` — este relatório.

---

## 4. Ficheiros alterados

| Ficheiro | Alteração |
| -------- | --------- |
| `src/storage/local-storage.ts` | Implementação real: `saveBuffer` (mkdir + write + checksum + size + mime), `resolveWithinRoot` (anti-traversal), `inferMimeType`, sanitização de segmentos. |
| `src/callbacks/callback.client.ts` | Implementação real: `fetch` POST com `X-Internal-Token`, `AbortSignal.timeout`, log de status sem token, `TimeoutError`/`CallbackFailedError`. |
| `src/errors/errors.ts` | Novas classes: `UnsupportedTemplateError`, `RenderFailedError`, `StorageFailedError`, `CallbackFailedError`, `TimeoutError`. |
| `src/jobs/job.types.ts` | `AssetMetadata.public_url?` (opcional). |
| `src/http/routes.ts` | `RouteDeps.storage`; registo de `GET /files/*` (só quando `NODE_ENV !== production`). |
| `src/app.ts` | Constrói `createLocalStorage` e injecta no router. |
| `README.md` | Secções de storage, `/files` (dev only) e callback; limitações/próximos passos actualizados. |

---

## 5. Storage implementado

**Layout em disco:**

```text
<LOCAL_STORAGE_ROOT>/workspaces/<workspace_id>/jobs/<job_id>/<file_name>
```

**`saveBuffer(input)`** → grava o buffer e devolve `AssetMetadata`:

| Campo | Origem |
| ----- | ------ |
| `storage_provider` | `"local"` |
| `bucket` | `""` |
| `storage_key` | `workspaces/<ws>/jobs/<job>/<file>` (forward slashes, estável) |
| `file_name` | nome do ficheiro |
| `mime_type` | `input.mimeType` ou inferido da extensão |
| `file_size_bytes` | `buffer.length` |
| `width` / `height` | recebidos quando aplicável (senão `null`) |
| `duration_seconds` | `null` |
| `checksum` | SHA-256 hex do conteúdo |
| `public_url` | `LOCAL_STORAGE_PUBLIC_BASE_URL` + `/` + `storage_key` |

**Segurança:**

- `assertSafeSegment` rejeita `workspaceId`/`jobId`/`fileName` com `/`, `\`,
  `..`, `\0` ou vazios → `StorageFailedError`.
- `resolveWithinRoot(rel)` resolve contra a raiz e devolve `null` para traversal
  ou caminhos absolutos que escapem à raiz.

**`GET /files/*` (CR-302):** servido só fora de produção; usa `resolveWithinRoot`
e `res.sendFile`; traversal/ficheiro inexistente → **404**. Documentado como
**apenas desenvolvimento**.

---

## 6. Callback client implementado

`createCallbackClient({ config, logger }).send(callbackUrl, payload)`:

- `POST` ao `callback_url` com headers `X-Internal-Token` e
  `Content-Type: application/json`.
- Timeout via `AbortSignal.timeout(CALLBACK_TIMEOUT_SECONDS * 1000)`.
- Resposta HTTP → `{ ok, statusCode }`; loga `callback.sent` (ok) ou
  `callback.non_ok` (status ≥ 400), **sem** o token.
- Timeout → `TimeoutError` (`code: timeout`); outras falhas → `CallbackFailedError`.
- Sem retry complexo (fora de escopo).

**Payloads (contrato Django, `callback.payload.ts`):**

- `buildCompletedPayload(envelope, result)` → `{ job_id, workspace_id, status,
  entity, result: { outputs }, error: null, metadata: { renderer, renderer_version } }`.
- `buildFailedPayload(envelope, error)` → `{ ..., status: "failed", result: null,
  error: { code, message, details }, metadata }`.

---

## 7. Comandos executados

```bash
npm run build      # tsc
npm run lint       # eslint .
npx vitest run     # testes

# Smoke manual do /files (servidor local)
INTERNAL_API_TOKEN=local-dev-token NODE_ENV=development PORT=8002 \
  LOCAL_STORAGE_ROOT=./storage node dist/server.js
# ficheiro válido            -> 200 image/png (len 7)
# /files/..%2f..%2f..        -> 404 (files.blocked)
# ficheiro inexistente       -> 404
```

---

## 8. Resultado das validações

| Validação | Resultado |
| --------- | --------- |
| `npm run build` (tsc) | ✅ Sem erros |
| `npm run lint` (eslint) | ✅ Sem erros |
| `npx vitest run` | ✅ 7 ficheiros, **37 testes** (13 novos) |
| Smoke `/files` ficheiro válido | ✅ **200** `image/png`, `Content-Length: 7` |
| Smoke `/files` path traversal | ✅ **404** (`files.blocked`) |
| Smoke `/files` ficheiro inexistente | ✅ **404** |
| Token nos logs | ✅ Nunca aparece |

**Novos testes (13):**

- Storage (5): guarda ficheiro + metadata; checksum + `public_url`; mime/width
  explícitos; rejeita traversal no `fileName`; `resolveWithinRoot` bloqueia.
- `/files` (4): serve ficheiro válido; traversal → 404; inexistente → 404; não
  registado em produção.
- Callback (4): `completed` enviado (contrato + token no header); `failed`
  enviado; timeout → `TimeoutError`; token nunca aparece nos logs.

---

## 9. Decisões tomadas

1. **Bloqueio de traversal em camadas:** `assertSafeSegment` na escrita +
   `resolveWithinRoot` na leitura/serviço; ambos com testes. Traversal devolve
   **404** (não revela detalhe de filesystem).
2. **`/files` dev-only por registo condicional:** a rota só é registada quando
   `NODE_ENV !== production`; em produção devolve 404 (notFound), reforçando que
   não é storage de produção.
3. **`public_url` em metadata:** incluído como campo opcional, derivado de
   `LOCAL_STORAGE_PUBLIC_BASE_URL` + `storage_key`, útil em dev e ignorável pelo Django.
4. **Timeout via `AbortSignal.timeout`:** simples e nativo (Node 22); timeout →
   `TimeoutError` (`code: timeout`), demais falhas → `CallbackFailedError`. Sem
   retry/backoff (fora de escopo).
5. **Segurança do token:** enviado apenas no header `X-Internal-Token`; os logs
   contêm só `callback_url`, ids de correlação e `http_status`. O logger redige
   chaves sensíveis como defesa adicional.
6. **Builders de payload separados:** `callback.payload.ts` concentra o contrato
   `completed`/`failed`, reutilizável e testável.
7. **Storage e callback ainda não ligados ao `POST /jobs`:** implementados e
   testados isoladamente; o encadeamento render → storage → callback em background
   (CR-203) fica para o próximo pipeline, evitando flakiness e respeitando “sem
   renderização real ainda”.

---

## 10. Pendências

- **Encadeamento no fluxo de job:** `POST /jobs` responder **202** e, em
  background leve, render → `saveBuffer` → `callback.send(completed/failed)` (CR-203).
- **Renderização real** (SVG → PNG / PDF / HTML) e template engine — Pipelines 04+.
- **Partial success** em `content_generation` — Pipeline 08 (CR-802).
- **Object storage real (S3/R2)** e CDN — fora do MVP.
- O `result` do `POST /jobs` continua **simulado** (`simulated: true`).

---

## 11. Próximo passo recomendado

Avançar para o **Pipeline 04 — Template engine e render SVG/PNG**, e ligar o
ciclo completo:

1. Implementar `templates/registry.ts` (funções de render reais) e a conversão
   SVG → PNG (Sharp), respeitando as dimensões suportadas.
2. Alterar `POST /jobs` para responder **202** e executar em **background leve**
   (`setImmediate`/promise), encadeando render → `storage.saveBuffer` →
   `callbackClient.send` com `completed`/`failed`.
3. Testes E2E: job aceite gera ficheiro real no storage e dispara callback
   (mockado) com a metadata de `Asset`.

Critério de pronto: um `content_generation` válido gera pelo menos um PNG real no
storage local, acessível via `/files`, e o renderer envia um callback `completed`
com a metadata de asset compatível com o Django.
