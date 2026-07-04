# Prompt 01 — Estabilizar E2E local (STG-HARD-001) — Resultado

**Data:** 2026-07-03
**Fase:** `07_staging_local_hardening` (STG-HARD-001)
**Âmbito:** investigar e reduzir o flake do E2E observado no fecho da fase
06 (diálogo de criação de media kit preso em "Creating…"), sem remover
cobertura, sem sleeps cegos, sem retries a esconder falhas.
**Estado de execução:** `executado` — causa mais provável identificada por
leitura de código (não conjectura), waits melhorados com base em sinais
reais (resposta HTTP, não fecho do diálogo), e **validado limpo em 7
execuções consecutivas de 12/12** ao longo desta fase. Este relatório
ficou por escrever no momento em que o trabalho foi feito (início da
fase) — é materializado agora, no fecho, com toda a evidência já
acumulada nas iterações seguintes, sem inventar nada de novo.

---

## 1. Causa mais provável (leitura de código, não suposição)

O teste original só esperava o **fecho do diálogo**
(`await expect(dialog).toBeHidden()`) depois de clicar em "Create campaign
action". Para os três tipos de acção com artefacto
(`report_request`/`media_kit_request`/`content_pack`), esse clique
despoleta **dois** pedidos HTTP sequenciais no Backend Core:

1. `POST /reports/` (ou `/media-kits/`, `/content-pack-requests/`) — que,
   por sua vez, **submete sincronamente** um job ao Content Renderer
   (`create_and_submit_external_job`,
   `backend_core/apps/integrations_bridge/services.py`), dentro do mesmo
   ciclo pedido/resposta Django. Este passo está sujeito a
   `REPORT_RENDERER_TIMEOUT_SECONDS`/`CONTENT_RENDERER_TIMEOUT_SECONDS`
   (30s por defeito).
2. `POST /campaign-actions/` — regista a acção persistente.

O `expect(dialog).toBeHidden()` da suite original tinha o timeout **default
de 10s** do Playwright — bem mais curto que os até ~30s que o primeiro
pedido pode legitimamente demorar se o Content Renderer estiver
momentaneamente lento a aceitar o job (não a processá-lo — só a
aceitação). O flake do fecho da fase 06 (media kit preso >10s, API directa
a responder em 0.2s segundos depois) é consistente com contenção pontual
de recursos numa sessão já muito longa, exactamente onde o default de 10s
tinha menos margem.

## 2. Alteração aplicada

`frontend/e2e/main-flow.spec.ts` — `trackedPost()` + `ARTIFACT_POST_PATH`:
em vez de confiar só no fecho do diálogo, o teste regista os listeners de
`page.waitForResponse()` para o(s) pedido(s) HTTP reais **antes** do
clique (nunca depois — para nunca perder uma resposta que chegue
imediatamente), com um timeout alargado e explícito só para os passos com
artefacto (`ARTIFACT_NETWORK_TIMEOUT_MS = 35_000`, cobrindo o pior caso
dos 30s do Content Renderer com margem). `manual_task` (sem artefacto)
mantém o timeout default do Playwright, inalterado.

```ts
async function trackedPost(page: Page, pathSuffix: string): Promise<TrackedRequest> {
  const response = await page.waitForResponse(
    (candidate) => candidate.request().method() === 'POST' && candidate.url().includes(pathSuffix),
    { timeout: ARTIFACT_NETWORK_TIMEOUT_MS },
  )
  return { url: response.url(), status: response.status(), requestId: ..., durationMs: ... }
}
```

Em caso de falha, uma anotação de diagnóstico (`test.info().annotations`)
regista os pedidos já observados e o `X-Request-ID` para correlação —
precursor directo do que STG-HARD-007 depois generalizou
(`frontend/e2e/diagnostics.ts`).

**O que não foi feito, deliberadamente** (critérios de rejeição do
backlog): nenhum sleep cego, nenhum aumento do timeout **global** do
Playwright (`playwright.config.ts` continua com `expect.timeout: 10_000`
inalterado — só os passos com artefacto têm um timeout de rede dedicado,
mais alto, e justificado por um limite real do sistema, não por
tentativa-e-erro), nenhum retry a esconder falhas, nenhum passo de
cobertura removido (media kit continua totalmente coberto).

## 3. Validação — 7 execuções limpas ao longo da fase

| # | Iteração/contexto | Resultado | Tempo |
|---|---|---|---|
| 1 | STG-HARD-007 (diagnóstico E2E) | 12/12 `PASS` | 25.5s |
| 2 | STG-HARD-007 | 12/12 `PASS` | 29.6s |
| 3 | STG-HARD-007 | 12/12 `PASS` | 22.6s |
| 4 | STG-HARD-007 (depois de reverter uma falha controlada) | 12/12 `PASS` | 15.8s |
| 5 | STG-HARD-007 (idem) | 12/12 `PASS` | 19.5s |
| 6 | STG-HARD-004/009 (via `quality-gate.ps1 -WithE2E`, sessão `pwsh` nova) | 12/12 `PASS` | 18.4s |
| 7 | STG-HARD-010 (fecho da fase, confirmação final) | 12/12 `PASS` | 19.8s |

**Zero flakes reproduzidos em 7 tentativas**, incluindo o mesmo passo de
media kit que falhou na fase 06 (sempre concluído em menos de 2.4s em
todas as 7 execuções). Não se declara "impossível de voltar a acontecer"
— declara-se "não reproduzido, com uma causa mais provável identificada e
tratada com um sinal real, não com tolerância cega".

## 4. Ficheiros alterados

| Ficheiro | Operação |
|---|---|
| `frontend/e2e/main-flow.spec.ts` | `trackedPost()`, `ARTIFACT_POST_PATH`, `ARTIFACT_NETWORK_TIMEOUT_MS`, anotações de diagnóstico em `createActionFromFirstRecommendation()` |
| `frontend/docs/.../06_staging_infraestrutura_real_local/runbook_staging_local.md` | §12 actualizado (nota "Actualização fase 07, STG-HARD-001") |
| `frontend/docs/.../07_staging_local_hardening/resultados_execucao/prompt_01_estabilizar_e2e_local_resultado.md` | **criado** (este relatório, materializado no fecho — ver preâmbulo) |

## 5. Critérios de aceitação — verificação

- ✅ E2E passa em múltiplas execuções consecutivas (7/7, ver §3).
- ✅ Media kit, report, content pack e manual task continuam cobertos —
  nenhum passo removido.
- ✅ Network apenas Backend Core continua validada (teste inalterado,
  reconfirmado em todas as 7 execuções).
- ✅ Nenhum sleep arbitrário introduzido como solução principal.
- ✅ Nenhum timeout global aumentado sem diagnóstico — só um timeout de
  rede específico, dimensionado contra um limite real de sistema
  (`REPORT_RENDERER_TIMEOUT_SECONDS`/`CONTENT_RENDERER_TIMEOUT_SECONDS`).

Nenhum critério de rejeição ocorreu.

## 6. Riscos remanescentes

| Risco | Severidade | Nota |
|---|---|---|
| O flake original nunca foi reproduzido de propósito (só observado uma vez, na fase 06) | Baixo | 7 execuções limpas depois da correcção é uma amostra razoável, não uma prova formal de que a causa raiz era exactamente esta; continua a ser a explicação mais provável, com evidência de código a suportá-la |
| `ARTIFACT_NETWORK_TIMEOUT_MS` (35s) ainda pode, em teoria, ser insuficiente numa máquina muito mais lenta | Muito baixo | Dimensionado com margem sobre o limite real de 30s do sistema; se voltar a falhar, o diagnóstico (STG-HARD-007) já mostra o tempo exacto decorrido para decidir se o limite precisa de revisão |

## 7. Próximo passo recomendado

Nenhuma acção pendente — este item fica encerrado com evidência
acumulada ao longo de toda a fase 07. Continuar a monitorizar em
execuções futuras do E2E (já facilitado pelo diagnóstico do STG-HARD-007).
