# Prompt 05 — Diagnóstico de falhas E2E — Resultado

**Data:** 2026-07-03
**Fase:** `07_staging_local_hardening` (STG-HARD-007)
**Âmbito:** melhorar a capacidade de diagnosticar falhas E2E — run-id,
correlation-id, screenshots, traces, logs relevantes, caminhos dos
artefactos — sem reduzir cobertura e sem expor secrets.
**Estado de execução:** `executado` — instrumentação adicionada e validada
com uma falha controlada real (screenshot/trace/diagnóstico confirmados),
E2E revalidado limpo 5× depois de reverter a falha controlada. **Uma
violação real de segurança foi encontrada e corrigida durante esta mesma
iteração**: a captura de rede nativa do Playwright gravava o JWT
`Authorization: Bearer` e o `E2E_PASSWORD` em claro dentro de `trace.zip`
— ver §3.

---

## 1. Estado anterior (confirmado por leitura de código, não suposição)

`frontend/playwright.config.ts`, antes desta iteração, já tinha:
- `trace: 'retain-on-failure'` — trace só guardado quando um teste falha;
- `screenshot: 'only-on-failure'` — screenshot só na falha;
- `reporter: [['list']]` — só terminal, sem relatório navegável persistente.

Ou seja, screenshot e trace **já existiam** (não foi preciso activá-los);
faltava (a) um relatório fácil de abrir sem `show-trace` manual, (b)
contexto explícito do teste (run-id, endpoints, contagens) anexado à falha,
e (c) — descoberto **durante** esta iteração — uma auditoria real de que o
trace não continha segredos.

## 2. Melhorias implementadas

### 2.1 `frontend/e2e/diagnostics.ts` (novo)

- `collectLogExcerpts({ ids, tailLines })` — lê os 4 logs locais já
  documentados no runbook (`backend_core.err.log`,
  `intelligence_engine.out.log`, `content_renderer.out.log`,
  `frontend.out.log`), filtra pelas linhas que mencionam qualquer id
  passado (run-id ou `X-Request-ID`), com *fallback* para as últimas 40
  linhas quando nada corresponde — nunca lança excepção (ficheiro em falta
  vira um marcador claro, não um erro).
- Segunda camada de redacção defensiva (`SECRET_PATTERNS`) sobre os
  próprios excertos de log, mesmo os serviços já nunca escreverem estes
  valores por desenho (`backend_core/apps/core/middleware.py`,
  `integrations_bridge/clients.py`) — nunca confiar numa só camada.
- `attachDiagnostics(testInfo, { runId, ids, extra })` — agrega tudo num
  único `testInfo.attach('e2e-diagnostics', ...)` JSON.

### 2.2 `frontend/e2e/main-flow.spec.ts` (instrumentado)

- **Contexto da execução impresso uma vez, no arranque** (`beforeAll`):
  `run_id`, `workspace`/`campaign` (últimos 8 caracteres, não o UUID
  completo — sem razão funcional para imprimir mais que isso numa linha de
  log), `email`. Nunca a password.
- **Correlation ids acumulados** durante toda a suite (`correlationIds`,
  extraído de `X-Request-ID` nas respostas já capturadas por `trackedPost`,
  mecanismo introduzido em STG-HARD-001).
- **Endpoints usados**: `endpointHits` (`Map<"MÉTODO pathname", contagem>`),
  alimentado pelo mesmo listener `page.on('request')` que já validava
  "Network apenas Backend Core" — nunca a query string nem o corpo.
- **Número de acções encontradas**: anotado (`test.info().annotations`)
  *antes* do `expect(matches).toHaveCount(6)`, para que o valor real fique
  visível mesmo que a asserção falhe.
- **`test.afterEach`**: se o teste não terminou no estado esperado,
  chama `attachDiagnostics` com o run-id, todos os correlation ids
  observados até esse ponto, e o resumo de endpoints — nunca corre em
  testes que passaram.

### 2.3 `playwright.config.ts`

- `reporter: [['list'], ['html', { open: 'never' }]]` — relatório
  navegável (`playwright-report/index.html`, `pnpm exec playwright
  show-report`) além do terminal; `open: 'never'` para nunca abrir um
  browser automaticamente (relevante para `-WithE2E` no quality gate).
  Confirmado que o quality gate só verifica o exit code do processo
  (`scripts/staging-local-quality-gate.ps1` linha ~187), nunca faz parsing
  do stdout — adicionar um reporter não o afecta.
- `globalTeardown: './e2e/global-teardown.ts'` — ver §3.

## 3. Achado real de segurança (encontrado e corrigido nesta iteração)

Ao simular uma falha controlada (§4) e fazer o grep obrigatório sobre os
artefactos gerados, **o `trace.zip` continha, em claro**:
- o cabeçalho `Authorization: Bearer <JWT completo>` em **todos** os
  pedidos autenticados (62 ocorrências numa única execução);
- o corpo do pedido de login (`POST /api/v1/auth/token/`):
  `{"email":"e2e-...@example.local","password":"<E2E_PASSWORD em claro>"}`;
- o corpo da resposta de login/refresh (tokens de acesso/refresh emitidos).

**Causa:** comportamento nativo do Playwright — `trace: 'retain-on-failure'`
grava a rede completa vista pelo browser via CDP, sem nenhuma opção
incorporada de redacção de cabeçalhos/corpos (confirmado: não existe
nenhuma flag `redact`/`sanitize` nos tipos do `@playwright/test`/
`playwright-core` instalados). Não é um bug deste projecto nem desta
iteração — é o próprio mecanismo de trace a fazer exactamente o que
promete (gravar tudo), e nada no código desta suite nunca imprime estes
valores directamente.

**Correcção:** `frontend/e2e/global-teardown.ts` (novo), registado como
`globalTeardown` do Playwright (corre sempre, sucesso ou falha, garantido
pelo próprio Playwright). Para cada `trace.zip` retido sob
`test-results/`:
1. Reescreve cada ficheiro `*.network` (o log de rede dentro do trace),
   trocando o valor de qualquer cabeçalho `Authorization`/`Cookie`/
   `Set-Cookie`/`X-Internal-Token` (case-insensitive) por `[REDACTED]`.
2. Identifica, pelos mesmos ficheiros `*.network`, os hashes de recurso
   (`_sha1`) dos corpos de pedido/resposta de `/auth/token/` e
   `/auth/token/refresh/` — e substitui o conteúdo desses recursos
   (`resources/<hash>`) por um marcador `"[REDACTED — auth request/response
   body, STG-HARD-007]"`, por inteiro (mais robusto que tentar analisar
   campo a campo).
3. Reescreve o `.zip` no mesmo caminho (`adm-zip`, nova dependência de
   desenvolvimento, mínima e sem bindings nativos).

Nunca lança: uma falha de redacção é avisada explicitamente no output
(`console.warn`), nunca escondida nem silenciosamente ignorada — quem vir
o aviso sabe que deve tratar esse trace específico como potencialmente
inseguro.

## 4. Falha controlada (simulada, revertida) — validação real

Alterada temporariamente uma linha (`toHaveCount(6)` → `toHaveCount(999)`)
no teste `CampaignActionsPanel lists every action...`, correndo a suite
completa duas vezes (antes e depois de adicionar o reporter `html`),
depois **revertida** e a suite re-confirmada limpa. Nenhum dado de
produção/cloud envolvido — apenas o workspace/campanha efémeros desta
própria execução (namespaced por `E2E_RUN_ID`, como sempre).

| Validação | Resultado |
|---|---|
| Falha ocorre exactamente como esperado (`Expected: 999, Received: 6`) | ✅ |
| `screenshot` gerado (`test-failed-1.png`) | ✅ |
| `trace.zip` gerado | ✅ |
| `error-context.md` gerado | ✅ |
| Attachment `e2e-diagnostics` presente no trace, com `run_id`, 7 `correlation_ids`, `workspace_id`, `campaign_id`, `endpoint_hits` | ✅ (confirmado via `test.trace`, evento `"name":"e2e-diagnostics","contentType":"application/json"`) |
| `playwright-report/index.html` gerado | ✅ |
| Testes seguintes (`reload`, `network check`) marcados "did not run" (modo `serial`) | ✅ — comportamento esperado, não um bug |
| **Antes da correcção**: grep por `Bearer [A-Za-z0-9._-]{10,}` / `"password":"..."` no trace descomprimido | ❌ **encontrado** (achado real, §3) |
| **Depois da correcção**: mesmo grep, trace da execução seguinte | ✅ **0 ocorrências** |
| Reversão da falha controlada + 2 execuções limpas a seguir | ✅ 12/12 em ambas |

## 5. Execuções reais do E2E nesta iteração

| # | Contexto | Resultado | Tempo |
|---|---|---|---|
| 1 | Limpa (antes da falha controlada) | 12/12 `PASS` | 25.5s |
| 2 | Limpa | 12/12 `PASS` | 29.6s |
| 3 | Limpa | 12/12 `PASS` | 22.6s |
| 4 | Falha controlada (validação artefactos, pré-correcção do achado §3) | 1 falhou (esperado), 2 não correram (`serial`), 9 passaram | 25.4s |
| 5 | Falha controlada (revalidação pós-correcção do achado §3, com reporter `html`) | idem | 26.2s |
| 6 | Limpa (revertida) | 12/12 `PASS` | 15.8s |
| 7 | Limpa | 12/12 `PASS` | 19.5s |

**5 execuções limpas, 12/12 em todas, zero flakes** — consistente com a
melhoria de espera introduzida em STG-HARD-001 (relatório dedicado ainda
pendente, referenciado no runbook §12).

## 6. Validações de segurança e qualidade

| Validação | Resultado |
|---|---|
| Grep `INTERNAL_API_TOKEN=`/`E2E_PASSWORD=`/`Bearer <token>` em `frontend/e2e/*.ts`, `playwright.config.ts` | ✅ 0 ocorrências |
| Grep dos mesmos padrões em `test-results/` (screenshots, error-context, `.last-run.json`) | ✅ 0 ocorrências |
| Grep dos mesmos padrões em **todos** os `trace.zip` descomprimidos (`Bearer`/`"password":"..."`) | ✅ 0 ocorrências (pós-correcção) |
| `npx tsc -p tsconfig.e2e.json --noEmit` | ✅ sem erros |
| `npx eslint e2e/` | ✅ sem avisos/erros |
| `pnpm lint` (frontend completo) | ✅ |
| `pnpm build` | ✅ `built in 4.33s` |
| `pnpm test` (vitest unitário) | ✅ 15/15 |
| `scripts/staging-local-health.ps1 -RequireApps` | ✅ 8/8 `OK`/`SKIPPED` |
| `scripts/check-forbidden-ports.ps1` | ✅ `OK` |

## 7. Ficheiros criados/alterados

| Ficheiro | Operação |
|---|---|
| `frontend/e2e/diagnostics.ts` | **criado** |
| `frontend/e2e/global-teardown.ts` | **criado** |
| `frontend/e2e/main-flow.spec.ts` | Instrumentado: contexto impresso, `correlationIds`, `endpointHits`, `afterEach` de diagnóstico, contagem de acções anotada |
| `frontend/playwright.config.ts` | `reporter` com `html`; `globalTeardown` |
| `frontend/package.json`, `frontend/pnpm-lock.yaml` | `adm-zip` + `@types/adm-zip` (devDependencies, para a redacção do trace) |
| `frontend/docs/.../06_staging_infraestrutura_real_local/runbook_staging_local.md` | Nova secção **§12.1** (diagnóstico de falhas E2E); §12 actualizada com nota honesta sobre o achado de segurança e as 5 execuções limpas desta iteração |
| `frontend/docs/.../07_staging_local_hardening/resultados_execucao/prompt_05_diagnostico_e2e_resultado.md` | **criado** (este relatório) |

## 8. Critérios de aceitação — verificação

- ✅ Falhas E2E deixam evidência accionável (screenshot, trace,
  error-context, diagnóstico JSON com ids).
- ✅ Artefactos são localizáveis por run-id/teste (nome de directório por
  teste; `run_id` impresso e anexado).
- ✅ Logs são correlacionáveis (`X-Request-ID` partilhado Backend
  Core/Intelligence Engine/Content Renderer, já validado em STG-LOCAL-010,
  agora automaticamente recolhido).
- ✅ Nenhum secret aparece em artefactos — confirmado por grep dedicado,
  **depois de corrigir um achado real** (não escondido, documentado em
  detalhe no §3).
- ✅ E2E continua a passar — 5/5 execuções limpas, 12/12 cada.
- ✅ Runbook explica como diagnosticar falhas (§12.1).
- ✅ Network apenas Backend Core continua validada (teste inalterado,
  `endpointHits` é um complemento, não substituição).
- ✅ Quality gate não quebra — `pnpm lint`/`pnpm build`/`pnpm test`
  confirmados; a etapa `e2e` do quality gate só olha ao exit code.

Nenhum critério de rejeição ocorreu: nenhum secret ficou em artefactos
(depois da correcção), screenshots/traces continuam a ser evidência, não
substituto de asserts (a falha controlada continuou a falhar exactamente
da mesma forma), Network continua validada, nada depende de cloud, logs
continuam com referência clara (run-id/correlation-id), quality gate
inalterado.

## 9. Limitações / riscos remanescentes

| Item | Severidade | Nota |
|---|---|---|
| `adm-zip` é uma nova dependência de desenvolvimento | Baixo | Mínima, sem bindings nativos, usada só no `globalTeardown`; alternativa seria orquestração via shell (`Compress-Archive`/`unzip`), mais frágil entre SOs |
| A redacção é um passo de pós-processamento, não uma prevenção na origem | Baixo-Médio | O Playwright não oferece (nesta versão) uma opção nativa para excluir cabeçalhos/corpos sensíveis da captura de rede do trace; esta é a mitigação disponível, e corre sempre, de forma garantida, sobre 100% dos traces retidos |
| Se `global-teardown.ts` falhar a redigir um trace específico, esse trace fica sinalizado por aviso mas **não é apagado automaticamente** | Baixo | Decisão consciente — apagar silenciosamente esconderia a falha; o aviso explícito é a divulgação correcta |
| O relatório `e2e-diagnostics` só é anexado em `afterEach` quando o teste falha — passos que passam não geram este anexo (por desenho, para não poluir execuções limpas) | Nenhum | Consistente com "não usar diagnóstico como substituto de asserts" |
| STG-HARD-001 (relatório dedicado ao flake original) continua pendente à parte | — | Fora do âmbito desta iteração; esta iteração só regista o resultado prático (5/5 limpo) como contexto |

## 10. Próximo passo recomendado

1. Fechar o relatório pendente de **STG-HARD-001** (E2E flake), reutilizando
   as 5 execuções limpas já registadas aqui como evidência adicional.
2. Seguir para **STG-HARD-009/010** (revalidação de segurança e fecho de
   hardening) quando as restantes tarefas do backlog de fase 07 estiverem
   fechadas.
3. Considerar, se este padrão de redacção de trace se mostrar útil,
   reutilizá-lo como um pequeno utilitário partilhável caso outro projecto
   desta organização venha a precisar do mesmo (não decidido aqui, só
   registado como possibilidade).
