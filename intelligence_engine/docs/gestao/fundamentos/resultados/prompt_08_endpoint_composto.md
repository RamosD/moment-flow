# Relatório de execução — Prompt 08: Endpoint composto

Implementação do `POST /intelligence/campaign` (IE-008): um endpoint composto
que **orquestra** os quatro motores já existentes e agrega o diagnóstico numa
única resposta coerente, **determinística** e **explicável**. Sem reimplementar
lógica, sem chamadas ao Backend Core ou ao renderer, sem persistência.

## Contexto consultado (sem alterações)

- `app/schemas/intelligence.py` — o contrato agregado `IntelligenceResult`
  (`analysis`, `scores`, `grade`, `moments`, `recommendations`, `summary`) já
  estava definido (IE-003); este prompt preencheu o motor por trás dele.
- Motores reutilizados (IE-004 → IE-007): `campaign_analysis_service`,
  `scoring_engine`, `moment_detector`, `recommendation_engine`.
- `backend_core` e `content_renderer` — apenas para confirmar coerência de
  contratos (o endpoint composto não os chama). Nenhum ficheiro alterado.

## Decisões de desenho

1. **Orquestração, não reimplementação.** O `IntelligenceOrchestrator` não
   possui lógica de scoring/detecção própria: chama os serviços stateless
   existentes pelos seus contratos públicos e cose os resultados. Cada serviço
   continua testável isoladamente (um teste compara os scores do composto com os
   do `scoring_engine` chamado directamente — devem ser idênticos).
2. **Reutilização via contrato, não internals.** Os quatro sub-pedidos
   (`CampaignAnalysisRequest`, `ScoringRequest`, `MomentsRequest`,
   `RecommendationsRequest`) são reconstruídos por `model_validate` a partir de
   um único `request.model_dump()` — todos são `CampaignRequest` com a mesma
   forma. Baixo acoplamento: depende apenas dos schemas públicos.
3. **Resiliência por etapa (sem 500 indevido).** Cada motor corre dentro de
   `_safe`: uma falha previsível numa etapa (excepção inesperada sobre input já
   validado) é convertida num warning `<etapa>_unavailable` e a secção fica no
   valor por omissão — nunca um `500` para o diagnóstico inteiro. A validação de
   payload continua a montante (FastAPI → `422` normalizado), por isso payloads
   malformados continuam a ser rejeitados de forma normalizada.
4. **Consolidação determinística.** As `explanations` e `warnings` de nível de
   envelope de cada etapa são reunidas em ordem fixa (analysis → scoring →
   moments → recommendations) e **deduplicadas por `code`** (primeira ocorrência
   vence), produzindo listas determinísticas e sem ruído (ex.: um único
   `insufficient_data` em vez de quatro). As `explanations` por recomendação e
   por momento permanecem dentro dos respectivos objectos em `result`.
5. **Summary executivo determinístico.** Uma frase com `campaign_health`,
   `grade`, os cinco scores (ou `n/a`) e as contagens de moments/recommendations
   (com a acção de topo). Sem relógio; `metadata.generated_at` a `null`.

## Comportamento implementado

- Executa **analysis + scoring + moment detection + recommendations** numa só
  chamada e agrega `analysis`, `scores`, `grade`, `moments`, `recommendations`,
  `summary`, `explanations` consolidadas, `warnings` consolidados e `metadata`.
- **Dados insuficientes**: `campaign_health=unknown`, scores `null`,
  `grade=unknown`, `moments: []`, uma recomendação `wait_for_more_data` e um
  único `insufficient_data` consolidado — `status=completed`, sem erro.
- **Falha parcial**: etapa que rebenta → warning `<etapa>_unavailable` + secção
  por omissão; as outras etapas continuam.
- **Determinístico**: mesmo input → resposta idêntica (verificado no motor e via
  HTTP).

## Ficheiros criados/alterados

### Criados

```text
app/services/intelligence_orchestrator.py      # IntelligenceOrchestrator
tests/test_intelligence_orchestrator.py        # 9 testes unitários do orquestrador
tests/test_intelligence_endpoint.py            # 6 testes HTTP do endpoint composto
docs/gestao/fundamentos/resultados/prompt_08_endpoint_composto.md
```

### Alterados

```text
app/api/intelligence.py           # 501 stub → chamada ao IntelligenceOrchestrator; IMPLEMENTED_ERROR_RESPONSES
tests/test_contract_endpoints.py  # /intelligence/campaign agora IMPLEMENTED; removido o teste de stub 501 (já não há stubs)
README.md                         # estado IE-008, tabela de endpoints, secção do endpoint composto + exemplo, estrutura, próximos passos, nota sobre not_implemented sem uso
```

Nada em `backend_core` nem em `content_renderer` foi alterado.

## Comandos executados

```bash
cd intelligence_engine
venv/Scripts/python.exe -m pytest -q                  # 197 passed
venv/Scripts/python.exe -m ruff check .               # All checks passed!
# Smoke real via app factory (TestClient + token), campanha single_release na janela:
#   200, health=good, grade=A,
#   scores {readiness 100, momentum 50, opportunity 45, risk 0, priority 48},
#   moments [release_window, report_due, milestone_reached, weekly_growth],
#   recs [create_release_post, create_report, create_milestone_post, create_weekly_growth_post],
#   explanations consolidadas (analysis + scoring + scoring_basis); warnings [].
```

## Resultados

- **pytest**: `197 passed` (era 182; +15 — orquestrador (9) e endpoint HTTP (6);
  o total de testes de contrato mantém-se, com `/intelligence/campaign` a passar
  de stub para implementado). 1 warning conhecido
  (`httpx`/`starlette.testclient`, não bloqueante).
- **ruff check .**: `All checks passed!`.
- **Agregação verificada**: a resposta inclui `analysis`, `scores`, `grade`,
  `moments`, `recommendations` e `summary`; `explanations`/`warnings`
  consolidados ao nível do envelope.
- **Consolidação**: bundle vazio → `insufficient_data` aparece uma única vez
  (deduplicado por `code`); as explanations juntam códigos de análise
  (`has_content_outputs`/`content_gap`…), de scoring (por score + `grade`) e de
  recomendações (`scoring_basis`).
- **Isolamento preservado**: os scores do composto são idênticos aos do
  `scoring_engine` chamado directamente.
- **Resiliência**: com o `scoring_engine.score` forçado a rebentar
  (monkeypatch), o endpoint devolve `200` com warning `scoring_unavailable` e a
  secção de scores por omissão; as restantes etapas continuam.
- **Erros de payload**: tipos malformados → `422 invalid_payload`; entity type
  desconhecido → `422`; sem token → `403`. Nunca `500` indevido.

## Pendências

- **Redundância menor de scoring**: o `recommendation_engine` chama o
  `scoring_engine` internamente, pelo que o scoring corre duas vezes por pedido
  composto (uma standalone, outra dentro das recomendações). É barato (sem I/O) e
  preserva o isolamento dos serviços; uma optimização futura poderia injectar os
  scores já calculados se o custo passar a importar.
- O código de erro `not_implemented` (501) deixou de ser usado por qualquer
  endpoint; mantém-se definido como código de ciclo de vida para futuros stubs.
- `app/api/internal_debug.py` mantém-se (suporta testes de auth); remover quando
  deixar de ser necessário.
- Calibração de pesos/limiares/severidades continua a ser MVP (risco IE-RSK-002);
  mitigada pela explicabilidade e pela centralização em constantes.
- Warning de depreciação `httpx`/`starlette.testclient` — não bloqueante.

## Próximo passo recomendado

Os motores MVP estão completos (IE-004 → IE-008). A seguir, fora do código de
runtime:

- **IE-009 — Contrato Backend Core ↔ Intelligence Engine**: documentar os
  payloads enviados pelo Django, headers, timeouts, códigos de erro, exemplos de
  request/response e a decisão síncrono vs `ExternalJobReference` (recomendação
  inicial: síncrono para `analysis`/`scoring`/`recommendations`/`moments`/
  `intelligence`; job externo só para análises pesadas futuras).
- **IE-010 — Testes, qualidade e documentação final**: fecho da fase, documento
  de estado (`docs/fundamentos/05_estado_intelligence_engine.md`), confirmação de
  ausência de secrets e indicação pronto/não-pronto para integração.
