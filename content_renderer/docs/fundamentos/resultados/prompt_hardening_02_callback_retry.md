# Relatório de Execução — Hardening 02: Retry de callback com backoff (R-HARD-006)

- **Serviço:** `content_renderer`
- **Data:** 2026-06-23
- **Backlog de referência:** [`03_backlog_hardening_pos_mvp_renderer.md`](../03_backlog_hardening_pos_mvp_renderer.md) → **R-HARD-006**
- **Pré-requisito:** [Hardening 01 — Callback em background leve](prompt_hardening_01_callback_background.md) (R-HARD-001) ✅

---

## 1. Prompt executado

Implementar retry simples de callback com backoff para aumentar a resiliência
quando o Backend Core (Django) está temporariamente indisponível, sem fila
persistente, sem _dead-letter_, sem Redis, sem alterar o contrato do callback,
sem expor o token e sem transformar o retry num _loop_ infinito nem mascarar 4xx
como sucesso.

## 2. Objectivo

Substituir a tentativa única do callback por **até `CALLBACK_MAX_ATTEMPTS`
tentativas** com **backoff exponencial limitado**, distinguindo falhas
_retryable_ (network/timeout/5xx) de _non-retryable_ (4xx), com logs por tentativa
sem secrets e mantendo a falha de callback **não-fatal** para o processo.

## 3. Ficheiros criados

| Ficheiro | Propósito |
|---|---|
| `docs/fundamentos/resultados/prompt_hardening_02_callback_retry.md` | Este relatório. |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `src/config/env.ts` | Novas vars `CALLBACK_MAX_ATTEMPTS` (>=1), `CALLBACK_RETRY_BASE_DELAY_MS` (>=0), `CALLBACK_RETRY_MAX_DELAY_MS` (>= base). Helper `parseIntegerAtLeast` + validação cruzada (max >= base). Falha _fast_ no arranque com erro claro. |
| `src/callbacks/callback.client.ts` | Reescrito com loop de tentativas + backoff exponencial; classificação retryable/non-retryable; logs `callback.attempt_started/attempt_failed/retry_scheduled/completed/delivery_failed`; **deixa de lançar** — devolve `{ ok, statusCode, attempts }`. |
| `src/jobs/job.service.ts` | `deliverCallback` consome o novo `CallbackResult`: `ok` → `callback.completed`; `!ok` → `callback.failed` (com `attempts`/`http_status`); `catch` defensivo mantido. |
| `.env.example` | Documentação das três vars de retry/backoff. |
| `tests/callback.test.ts` | Reescrito: contrato + política de retry (1ª tentativa, sucesso após transitório, 503/timeout até ao limite, 400/403 sem retry, max attempts, token ausente nos logs). Servidor de teste passa a variar resposta por tentativa. |
| `tests/env.test.ts` | Defaults de retry + 4 casos de env inválida (max<1, não-inteiro, base<0, max<base). |
| `README.md` | Tabela de config + secção "Retry de callback com backoff", limitações e próximos passos. |
| `docs/fundamentos/02_estado_content_report_renderer.md` | Features, validações (120 testes), pendências, riscos e próximo passo. |

## 5. Regras de retry

| Situação | Decisão |
|---|---|
| HTTP 2xx | **Entregue** (`ok: true`), pára. |
| Network error | **Retry** (até ao limite). |
| Timeout (`AbortSignal.timeout` por tentativa) | **Retry** (até ao limite). |
| HTTP 500 / 502 / 503 / 504 | **Retry** (até ao limite). |
| HTTP 400 / 401 / 403 / 404 / 409 / 422 (e restantes 4xx) | **Sem retry** — `ok: false` à 1ª tentativa, nunca mascarado como sucesso. |
| Tentativas esgotadas | `ok: false` com `attempts == CALLBACK_MAX_ATTEMPTS`; log `callback.delivery_failed`. |

- **Backoff:** `delay = min(MAX_DELAY, BASE_DELAY · 2^(n-1))` (exponencial,
  limitado pelo tecto). `BASE_DELAY = 0` ⇒ sem espera.
- **Tempo total limitado:** `≈ attempts × (timeout + backoff)` — **nunca**
  infinito; `send` **não** bloqueia indefinidamente.
- **Não-fatal:** `send` **não lança**; devolve sempre `{ ok, statusCode,
  attempts }`. O `JobService` apenas regista o resultado; os ficheiros
  permanecem no storage.
- **Logs (sem token/secrets/payload completo):** `callback.attempt_started`,
  `callback.attempt_failed`, `callback.retry_scheduled`, `callback.completed`,
  `callback.delivery_failed` — com `job_id`, `workspace_id`, `attempt`,
  `max_attempts` e `http_status` (quando existe). O `request_id` consta dos logs
  de ciclo de vida do `JobService` (`callback.started`/`completed`/`failed`).

## 6. Env vars adicionadas

| Variável | Regra | Default |
|---|---|---|
| `CALLBACK_MAX_ATTEMPTS` | inteiro `>= 1` (`1` desliga retry) | `3` |
| `CALLBACK_RETRY_BASE_DELAY_MS` | inteiro `>= 0` | `500` |
| `CALLBACK_RETRY_MAX_DELAY_MS` | inteiro `>= CALLBACK_RETRY_BASE_DELAY_MS` | `5000` |

Valores inválidos (não-inteiro, abaixo do mínimo, ou `max < base`) fazem o
arranque falhar com `ConfigError` e mensagem clara, indicando a variável.

## 7. Testes criados/alterados

**`tests/callback.test.ts` (reescrito, 10 testes):**
- contrato `completed` (1ª tentativa) → `{ ok: true, statusCode: 200, attempts: 1 }`;
- contrato `failed`;
- sucesso na 1ª tentativa (sem retry);
- sucesso após falha temporária (503 → 200, `attempts: 2`);
- 503 com retry até ao limite (`attempts: 3`, `callback.delivery_failed`);
- timeout com retry (`attempts: 2`, `reason: timeout`);
- 400 sem retry (`attempts: 1`);
- 403 sem retry (`reason: non_retryable_status`, sem `retry_scheduled`);
- `CALLBACK_MAX_ATTEMPTS` respeitado exactamente (`attempts: 4`);
- token ausente nos logs ao longo das tentativas.

**`tests/env.test.ts` (+5 testes):** defaults de retry; `max<1`; não-inteiro;
`base<0`; `max<base`.

## 8. Comandos executados

```bash
npm run build   # tsc -p tsconfig.json
npm run lint    # eslint .
npm test        # vitest run
```

## 9. Resultados

| Validação | Resultado |
|---|---|
| `npm run build` | ✅ Sem erros |
| `npm run lint` | ✅ Sem erros |
| `npm test` | ✅ **120 testes** em **13 ficheiros** (109 → 120; +6 retry, +5 env) |

Critérios de aceitação R-HARD-006:

- ✅ Callback retry funciona em falha temporária (503/timeout → nova tentativa).
- ✅ 4xx não gera retry indevido (400/403 → 1 tentativa).
- ✅ Timeout gera retry até ao limite.
- ✅ `CALLBACK_MAX_ATTEMPTS` é respeitado.
- ✅ Logs mostram tentativas sem secrets (token nunca aparece).
- ✅ Env inválida falha no arranque com erro claro.
- ✅ Build, lint e testes passam.
- ✅ Contrato de callback inalterado; sem fila/Redis/dead-letter.

## 10. Pendências

- **Idempotência no Django:** o retry pode reentregar um callback se a primeira
  resposta se perder após o Django já ter processado — depende da idempotência do
  _endpoint_ de callback (RSK-HARD-002). A validar no E2E (R-HARD-002/003).
- **Retry em memória:** sem fila persistente nem _dead-letter_ — um _restart_ do
  processo entre tentativas perde a entrega em curso (fora do âmbito).
- **`request_id` nos logs do cliente:** o `CallbackPayload` não inclui
  `request_id`, pelo que os logs do cliente correlacionam por `job_id`/
  `workspace_id`; o `request_id` aparece nos logs de ciclo de vida do `JobService`.

## 11. Próximo passo recomendado

Avançar para **R-HARD-004 — Echo de `template_key`/`template_id` no
`content_generation`**, e em seguida o **E2E com PostgreSQL** (R-HARD-002/003)
para validar, com evidência, a idempotência do callback sob retry no _loop_
Django → Renderer → Django.
