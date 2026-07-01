# Relatório de Execução — Hardening 01: Callback em background leve (R-HARD-001)

- **Serviço:** `content_renderer`
- **Data:** 2026-06-23
- **Backlog de referência:** [`03_backlog_hardening_pos_mvp_renderer.md`](../03_backlog_hardening_pos_mvp_renderer.md) → **R-HARD-001**

---

## 1. Prompt executado

Implementar o callback em background leve no `content_renderer`, separando a
recepção HTTP do job da execução render/storage/callback. O `POST /jobs` deve
aceitar o job, responder **202 rapidamente** e executar render/callback em
background leve (`setImmediate`/`Promise`), sem fila complexa
(sem BullMQ/Redis/RabbitMQ/Kafka), com tratamento global de erros, logs
estruturados sem secrets e testes do fluxo assíncrono.

## 2. Objectivo

Remover a corrida entre o callback do renderer e o estado do
`ExternalJobReference` no Django, devolvendo o `202` antes do callback e movendo
render → storage → callback para um _tick_ de background leve, com garantia de
que um erro em background **nunca** derruba o processo.

## 3. Ficheiros criados

| Ficheiro | Propósito |
|---|---|
| `tests/helpers.ts` | Helpers de teste partilhados: `createDeferred`, `waitUntil` (espera determinística pelo background). |
| `tests/background.test.ts` | Testes do fluxo de background (R-HARD-001): 202 antes do callback, callback `completed`/`failed` em background, callback que falha é não-fatal, rede de segurança global, logs sem token. |
| `docs/fundamentos/resultados/prompt_hardening_01_callback_background.md` | Este relatório. |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `src/jobs/job.service.ts` | Substitui `processJob` por **`acceptJob`** (gate síncrono + `job.accepted`), **`scheduleJobExecution`** (`job.scheduled` + `setImmediate`) e **`executeJob`** (render→storage→callback). Adiciona `runInBackground` (rede de segurança global → `job.execution_failed` + callback `failed` _best-effort_) e `JobExecutionContext`. |
| `src/jobs/job.controller.ts` | `POST /jobs` agora faz `acceptJob` + `scheduleJobExecution` e responde **202 sem `result`** (apenas _acknowledgement_). |
| `tests/jobs.test.ts` | Secção "dispatcher" reescrita para background: 202 + `waitUntil` sobre o callback gravado; deixa de ler `res.body.result`. |
| `tests/content-generation.test.ts` | Integração POST /jobs: `waitUntil(calls)` antes das asserções; remove `res.body.result`. |
| `tests/report-generation.test.ts` | Idem. |
| `tests/media-kit-generation.test.ts` | Idem. |
| `tests/hardening.test.ts` | `processJob`→`executeJob`; teste de `job_type` não suportado passa a usar `acceptJob` (síncrono); teste de ciclo de vida espera o background e valida `job.scheduled` + `request_id`. |
| `README.md` | Nova secção "Execução em background leve", diagrama, corpo do 202, limitações e próximos passos. |
| `docs/fundamentos/02_estado_content_report_renderer.md` | Estado, validações (109 testes), pendências, riscos e próximo passo. |

## 5. Desenho da execução em background

```text
POST /jobs
  → auth (X-Internal-Token, middleware)
  → parseJobEnvelope (Zod)
  → enforceJobHeaderConsistency
  → jobService.acceptJob(envelope)            # síncrono
        ├─ valida job_type (desconhecido → throw UnsupportedJobTypeError → 400, SEM callback)
        ├─ log job.accepted
        └─ devolve JobExecutionContext (logger filho com job_id/workspace_id/request_id/job_type)
  → jobService.scheduleJobExecution(envelope, context)
        ├─ log job.scheduled
        └─ setImmediate(() => runInBackground(envelope, context))   # background leve
  → res.status(202).json({ status: 'accepted', ... })   # RESPONDE JÁ (sem result)

· · · · · · · · · · · · · · · · · · background tick · · · · · · · · · · · · · · · ·
runInBackground:
  try executeJob(envelope, context):
        ├─ log render.started
        ├─ withTimeout(renderer(...), RENDER_TIMEOUT_SECONDS)
        │      ├─ ok  → log render.completed → deliverCallback(completed/partially)
        │      └─ throw/timeout → log render.failed → deliverCallback(failed, erro normalizado)
        └─ deliverCallback:
              log callback.started → callbackClient.send
                 ├─ ok    → log callback.completed
                 └─ throw → log callback.failed   (NÃO-FATAL)
  catch (erro inesperado):                         # rede de segurança global
        ├─ log job.execution_failed
        └─ deliverCallback(failed) best-effort     # nunca relança / nunca derruba o processo
```

Mecanismo de background: **`setImmediate`** (Node.js nativo). **Sem** fila
externa, **sem** Redis/BullMQ/RabbitMQ/Kafka, **sem** base de dados de jobs.

## 6. Alterações ao fluxo POST /jobs

- **Antes:** `POST /jobs` corria render + storage + callback de forma síncrona e
  devolvia o `result` no corpo do `202` (o callback era enviado **antes** da
  resposta → corria com o submit síncrono do Django).
- **Depois:** `POST /jobs` valida, **aceita** (`acceptJob`), **agenda**
  (`scheduleJobExecution`) e responde `202` **imediatamente**. O corpo do `202`
  é apenas `{ status: 'accepted', job_id, workspace_id, job_type, entity,
  metadata }` — **sem `result`**. Render/storage/callback correm em background.
- **`job_type` não suportado** continua a ser **400** (`unsupported_job_type`),
  decidido **antes** do `202`, sem callback.
- **Contrato do callback inalterado** (mesma forma `completed`/
  `partially_completed`/`failed`, mesmos campos de `result`/`error`/`metadata`).

## 7. Testes criados/alterados

**Novos (`tests/background.test.ts`):**
- `responds 202 BEFORE the callback is delivered` — callback bloqueado num _gate_;
  o `202` regressa com o callback ainda pendente.
- `delivers a completed callback in the background` — `calls.length === 0` no
  momento do 202; callback `completed` chega depois.
- `delivers a failed callback in the background when the render fails` — storage
  a falhar → callback `failed` (`render_failed`).
- `does not crash the process when the callback delivery throws` — callback
  lança; é logado `callback.failed`, **sem** `job.execution_failed`, e um segundo
  job continua a ser aceite (processo vivo).
- `logs job.execution_failed and stays alive on an unexpected background error` —
  _sink_ de log a falhar em `render.failed` escapa ao `try/catch` de render e é
  apanhado pela rede de segurança global; valida `job.execution_failed`, callback
  `failed` _best-effort_ e ausência do token nos logs.

**Alterados:** `tests/jobs.test.ts`, `tests/content-generation.test.ts`,
`tests/report-generation.test.ts`, `tests/media-kit-generation.test.ts`,
`tests/hardening.test.ts` — adaptados ao callback assíncrono (`waitUntil`,
remoção de `res.body.result`, `acceptJob`/`executeJob`, `job.scheduled`).

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
| `npm test` | ✅ **109 testes** em **13 ficheiros** (104 → 109; +5 do fluxo de background) |

Critérios de aceitação R-HARD-001:

- ✅ `POST /jobs` devolve `202` sem esperar pelo callback.
- ✅ Callback continua a ser enviado (em background).
- ✅ Erro no render gera callback `failed`.
- ✅ Erro no callback é logado e não derruba o processo.
- ✅ Erro inesperado em background é capturado/logado (`job.execution_failed`).
- ✅ Logs incluem `job_id`/`workspace_id`/`request_id`/`job_type` e **não**
  incluem `INTERNAL_API_TOKEN`/payload completo/secrets.
- ✅ Build, lint e testes passam.
- ✅ Compatibilidade mantida com `content_generation`, `report_generation` e
  `media_kit_generation`.

## 10. Riscos remanescentes

- **Callback `failed` duplicado pela rede de segurança:** em cenários de _bug_
  genuíno em que algo falhe **depois** de um callback de sucesso já ter sido
  entregue, a rede de segurança pode tentar um callback `failed` adicional.
  Mitigação: o callback do Django deve ser **idempotente** (RSK-HARD-002). Nos
  caminhos realistas testados não há duplicação (a falha ocorre antes do envio).
- **Sem retry de callback:** falha temporária do Django ainda só é logada
  (tentativa única) — endereçado em **R-HARD-006**.
- **Background _in-process_:** um _restart_/_crash_ do processo entre o `202` e o
  callback perde o trabalho em curso (sem persistência de jobs — fora do âmbito).
- **`withTimeout` não cancela** o render subjacente (apenas limita a espera); um
  render _runaway_ continua a consumir recursos até terminar.

## 11. Próximo passo recomendado

Avançar para **R-HARD-006 — Retry simples de callback com backoff** (próximo na
ordem do backlog), reforçando a resiliência quando o Backend Core está
temporariamente indisponível, sem introduzir fila persistente nem _dead-letter_.
