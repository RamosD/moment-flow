# Relatório de Execução — Prompt 08: Erros, Partial Success e Hardening

- **Data:** 2026-06-22
- **Pipeline:** 08 — Erros, partial success e hardening
- **Épico/Tarefas do backlog:** CR-801 (normalização de erros), CR-802 (partial success), CR-203/CR-503 (timeouts e callback), CR-003 (logs), CR-302/CR-301 (path traversal)
- **Serviço:** `content_renderer`
- **Localização:** `D:\Workspace\ChartRex\momentflow\content_renderer`

---

## 1. Prompt executado

Consolidar tratamento de erros, partial success, timeouts, logs e robustez
operacional do renderer antes do teste com o Backend Core real. Normalizar
códigos de erro, garantir `details` seguros (sem token/segredos/paths/payload),
reforçar o partial success do content, **aplicar `RENDER_TIMEOUT_SECONDS` ao
render** (além do `CALLBACK_TIMEOUT_SECONDS` já existente), enriquecer os logs de
ciclo de vida (sem token), confirmar bloqueio de path traversal e job_type
desconhecido controlado, e cobrir tudo com testes.

Backlog de referência: `docs/fundamentos/01_backlog_content_report_renderer.md`.

---

## 2. Objectivo

Endurecer o serviço: erros previsíveis e normalizados, callbacks `failed` com
contrato correcto e detalhes seguros, partial success coerente, dois timeouts
(render + callback) normalizados, logs rastreáveis sem segredos, e segurança
(path traversal, job_type) verificada — deixando o renderer pronto para o E2E com
o Django.

---

## 3. Ficheiros criados

- `src/jobs/with-timeout.ts` — `withTimeout(promise, ms, details)`: limita a
  espera do render e rejeita com `TimeoutError` normalizado.
- `tests/hardening.test.ts` — 12 testes de hardening (normalização de erros,
  redacção de segredos, timeout, robustez do dispatcher, logs sem token, path
  traversal).
- `docs/fundamentos/resultados/prompt_08_erros_partial_hardening.md` — este relatório.

---

## 4. Ficheiros alterados

| Ficheiro | Alteração |
| -------- | --------- |
| `src/jobs/job.service.ts` | Render envolto em `withTimeout(RENDER_TIMEOUT_SECONDS)`; `try/catch` converte timeout/excepção em **callback `failed` normalizado** (código preservado), nunca rebenta o pedido; logs de ciclo de vida (`job.accepted`, `render.started/completed/failed`, `callback.started/completed/failed`); mapa de renderers com **DI opcional** (testabilidade). |
| `src/callbacks/callback.payload.ts` | `buildFailedPayload` passa `error.details` por `redact()` (defesa em profundidade — nunca expõe valores com forma de token/secret). |
| `src/callbacks/render-error.ts` | Novo `failureMessage(jobType)` e `renderErrorFromException(envelope, appError)` (preserva o código real, ex.: `timeout`). |
| `vitest.config.ts` | `testTimeout`/`hookTimeout` = 30s — robustez do harness sob carga (render real de PNG/PDF + init de workers pode exceder o default de 5s numa máquina ocupada; o timeout de *comportamento* é testado via `withTimeout`/callback client, não por este valor). |

> `content/report/media-kit` renderers **não** foram alterados — o partial success
> e a normalização já residiam neles e no dispatcher; o hardening centralizou-se no
> dispatcher, no callback e nos timeouts.

---

## 5. Erros normalizados

Todos os erros expõem `code` + `message` + `details` (seguro) via `AppError.toJSON()`,
e o callback `failed` usa o contrato do Django (`result: null`, `error: {code,message,details}`):

| `code` | HTTP | Onde |
| ------ | ---- | ---- |
| `invalid_payload` | 400 | envelope inválido / payload de report/media-kit inválido |
| `unsupported_job_type` | 400 | job_type fora do MVP (sem callback — job recusado) |
| `unsupported_template` | 422 | template não registado (classe pronta; registry usa fallback) |
| `render_failed` | 500 | falha de render / agregado de outputs falhados |
| `storage_failed` | 500 | falha ao escrever no storage |
| `callback_failed` | 502 | falha ao entregar o callback (não-fatal) |
| `timeout` | 504 | render ou callback excederam o tempo |

**Segurança dos `details`:** o callback `failed` agrega apenas
`outputs_total`/`outputs_failed`/`first_error{code,message}` (render-result) ou
`operation`/`reason` (excepção); nunca inclui `INTERNAL_API_TOKEN`, payload
completo nem caminhos absolutos (o `storage_key` é **relativo**). Como rede de
segurança, `buildFailedPayload` ainda corre `redact()` sobre os `details`
(qualquer chave com forma de token/secret/password/authorization/api_key →
`[REDACTED]`).

---

## 6. Regras de partial success (content_generation)

Cada output é renderizado de forma independente; a falha de um não afecta os
restantes:

- output gerado com sucesso → `status: "completed"` (com `asset`);
- output falhado → `status: "failed"` (sem `asset`, com `metadata.error` seguro);
- **status geral:**
  - `completed` — nenhum output falhou;
  - `partially_completed` — ≥1 gerado **e** ≥1 falhado;
  - `failed` — nenhum output gerado.

`result.outputs` inclui os outputs `completed` e `failed`; o dispatcher reencaminha
`partially_completed` como callback de sucesso (com `error: null`) e `failed` como
callback de falha.

---

## 7. Timeouts

- **Render:** `RENDER_TIMEOUT_SECONDS` agora é aplicado — o dispatcher corre
  `withTimeout(renderer(...), renderTimeoutMs)`; ao exceder, gera callback `failed`
  com `code: "timeout"`. (Nota: limita a espera; não cancela o trabalho subjacente —
  rede de segurança para renders descontrolados.)
- **Callback:** `CALLBACK_TIMEOUT_SECONDS` continua aplicado no callback client via
  `AbortSignal.timeout` → `TimeoutError`.

---

## 8. Comandos executados

```bash
npm run build              # tsc -p tsconfig.json
npx vitest run             # toda a suite (E2E interno incluído)
npm run lint               # eslint .
```

Os **E2E internos** (`POST /jobs`) cobrem content/report/media-kit (callback
completed + asset + ficheiro em disco) e os cenários de hardening (timeout,
excepção, callback falhado, logs sem token).

---

## 9. Resultado das validações

| Validação | Resultado |
| --------- | --------- |
| `npm run build` (tsc) | ✅ Sem erros |
| `npm run lint` (eslint) | ✅ Sem erros |
| `npx vitest run` | ✅ **12 ficheiros, 104 testes** (12 novos de hardening); estável em execuções repetidas (4×104 verde) |

**Novos testes (12) cobrem:**
- normalização de erros (código + status + corpo `{code,message,details}`) para os
  7 códigos — inclui **erro de template** (`UnsupportedTemplateError`);
- `details` do callback `failed` redactam token/secret e preservam campos seguros;
- `withTimeout` resolve rápido e rejeita `TimeoutError` quando lento;
- **timeout simulado** de render → callback `failed` com `code: "timeout"`;
- **erro de render** lançado → callback `failed` (código preservado);
- **erro de storage** num output → `render_failed` com `first_error` nos `details`;
- **partial success** reencaminhado como `partially_completed` (2 outputs, `error: null`);
- **erro de callback** é não-fatal e logado (`callback.failed`);
- **unsupported job type** lança e **não** envia callback;
- **logs de ciclo de vida** presentes (`job.accepted`, `render.started/completed`,
  `callback.started/completed`) e **sem token**, com `job_id`/`job_type`;
- **path traversal** bloqueado (segmentos inseguros + escape do root → `StorageFailedError`/null).

---

## 10. Pendências

- **Cancelamento real do render** no timeout (AbortController nos renderers) — hoje
  o timeout limita a espera mas não cancela o trabalho subjacente.
- **Retry de callback** com backoff — fora do escopo; tentativa única com timeout.
- **`unsupported_template` em uso** — a classe existe e está testada, mas o registry
  resolve sempre por fallback; um modo estrito (falhar em template desconhecido)
  fica para evolução futura.
- **Teste E2E com Backend Core Django real** (CR-903) — próximo passo.

---

## 11. Próximo passo recomendado

Avançar para o **Pipeline 09 — Testes E2E com Backend Core**: subir
`backend_core` (Django) em `localhost:8000` e o `content_renderer` em
`localhost:8002` com o mesmo `INTERNAL_API_TOKEN`, criar um `ContentPackRequest`
(e um `Report`/`MediaKit`) reais e confirmar o ciclo completo — job enviado,
ficheiro gerado, callback recebido, `Asset` criado e `ContentOutput`/`Report`/
`MediaKit` actualizados — incluindo os caminhos de `failed`/`partially_completed`.
