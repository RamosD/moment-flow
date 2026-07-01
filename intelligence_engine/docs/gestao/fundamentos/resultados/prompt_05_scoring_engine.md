# Relatório de execução — Prompt 05: Scoring engine MVP

Implementação do `POST /scoring/campaign` (IE-005) com cálculo
**determinístico**, **explicável** e **testável** de cinco scores de campanha,
sobre os schemas definidos no Prompt 03 e reaproveitando os sinais já modelados
no Prompt 04. Sem IA generativa, sem chamadas externas, sem persistência.

## Contexto consultado (sem alterações)

Reconfirmadas em `backend_core` as entidades e estados que alimentam os scores
(nenhum ficheiro alterado):

- `apps/campaigns/models.py` — `Campaign.Status`
  (`draft`/`scheduled`/`active`/`paused`/`completed`/`archived`),
  `start_date`/`end_date`, `primary_goal` e `CampaignGoal` (readiness/risk).
- `apps/content/models.py` — `ContentOutput.Status.COMPLETED` (momentum,
  content gap) e `ContentPack.PackType` (vocabulário já alinhado nos schemas).
- `apps/links/models.py` — sinais de smart link (clicks/active links) para
  momentum e risco.
- `apps/reports/models.py` — `Report.Status.COMPLETED` e `MediaKit.Status`
  (`generated`/`published`) para oportunidade e readiness.

Também reconfirmado o backlog em
[`backlog.md`](../backlog.md) (IE-005, secção 7.3) e o padrão do serviço de
análise ([`campaign_analysis.py`](../../../../app/services/campaign_analysis.py)).

## Decisões de desenho

1. **Score = soma ponderada transparente.** Cada score é
   `round(100 · Σ pesoᵢ · valorᵢ)`, com cada `valorᵢ ∈ [0,1]` e os pesos a
   somarem 1.0. Não há aritmética opaca: cada componente é uma regra nomeada e
   o seu peso está documentado. A `Explanation` de cada score enumera os
   componentes e os seus valores (ex.: `status_known w0.20 v1.00`), tornando o
   número auditável linha a linha.
2. **`null`/unknown só por ausência de dados, nunca por desempenho fraco.**
   Cada score tem uma condição `computável sse` baseada nos seus inputs.
   Quando não é calculável, devolve `null` **e** um `Warning` `<score>_unknown`
   (com `details.score`). Quando é calculável, devolve um inteiro **e** uma
   `Explanation`. Nunca os dois, nunca nenhum — cada score é sempre
   justificado, satisfazendo "cada score deve ter uma explanation ou warning".
3. **Determinismo via `reference_date` explícito** (igual à análise). As regras
   de recência lêem `context.reference_date` (ISO `YYYY-MM-DD`); sem ele,
   degradam para presença em vez de `datetime.now()`. `metadata.generated_at`
   fica `null` para o response ser byte-a-byte reprodutível. Testado ao nível
   do motor e via HTTP.
4. **Dois compostos distintos: prioridade vs. grade.** `priority_score` mede
   *urgência de agir* (o risco aumenta a prioridade); a `grade` deriva de um
   composto separado `overall_standing` que mede *como a campanha está* (o
   risco entra invertido, `100 − risk`). Mantê-los separados evita que uma
   campanha problemática (alto risco/oportunidade, logo alta prioridade) receba
   grade A. Ambos renormalizam os pesos sobre os scores disponíveis, de forma
   documentada.
5. **Ausência de dados ≠ penalização.** Sem `smart_link_stats`, os componentes
   de cliques (momentum) e `link_inactivity` (risco) contribuem 0 em vez de
   penalizarem — não sabemos da tracção, por isso não a inventamos. Contadores
   negativos são tratados como zero (com warning), nunca como actividade.
6. **Pesos como `Explanation.weight`.** O campo `weight` de cada explanation de
   score é o peso desse score na mistura de prioridade (readiness 0.20,
   momentum 0.25, opportunity 0.35, risk 0.20), documentando a sua influência.

## Regras de scoring implementadas

Pesos (cada conjunto soma 1.0) documentados como constantes em
`app/services/scoring_engine.py` e no README.

### `campaign_readiness_score` — computável sse há `campaign`

| Componente | Peso | Vale 1.0 quando |
| --- | ---: | --- |
| `status_known` | 0.20 | status é um estado de ciclo de vida conhecido |
| `artist_present` | 0.15 | há dados de artista |
| `track_present` | 0.15 | há dados de faixa |
| `goal_defined` | 0.15 | `primary_goal` definido ou `goals` listados |
| `schedule_defined` | 0.15 | `start_date` presente |
| `media_kit_ready` | 0.20 | media kit `generated`/`published` |

### `momentum_score` — computável sse há `smart_link_stats` OU `content_outputs`

| Componente | Peso | Valor |
| --- | ---: | --- |
| `clicks_7d` | 0.40 | `saturate(clicks_last_7_days, 100)` |
| `clicks_30d` | 0.25 | `saturate(clicks_last_30_days, 400)` |
| `total_clicks` | 0.15 | `saturate(total_clicks, 2000)` |
| `recent_content` | 0.20 | `saturate(outputs completos recentes, 2)`; sem `reference_date` → 0.5 se há outputs completos |

### `content_opportunity_score` — computável sse há campaign/track/content/reports/media kits

| Componente | Peso | Vale 1.0 quando |
| --- | ---: | --- |
| `content_gap` | 0.35 | sem conteúdo completo (recente → 0.0; antigo → 0.4; recência desconhecida → 0.2) |
| `report_due` | 0.20 | sem report completo recente (janela 30 dias) |
| `media_kit_missing` | 0.20 | sem media kit utilizável |
| `timing_relevance` | 0.25 | janela de lançamento ±14d; senão active=0.6, scheduled=0.5, paused=0.3, outro=0.0 |

### `risk_score` — computável sse há `campaign` OU `smart_link_stats`

| Componente | Peso | Vale 1.0 quando |
| --- | ---: | --- |
| `no_traction` | 0.35 | `active` + sem conteúdo + sem actividade de link |
| `link_inactivity` | 0.20 | stats presentes sem cliques (0.5 se há links mas sem cliques; sem stats → 0.0) |
| `content_gap_active` | 0.15 | `active` sem conteúdo completo |
| `overdue` | 0.15 | `end_date < reference_date` e não `completed`/`archived` |
| `data_quality` | 0.15 | datas inconsistentes ou contadores de link negativos |

### `priority_score` — mistura, computável sse ≥2 dos quatro existem

`content_opportunity 0.35 · momentum 0.25 · risk 0.20 · readiness 0.20`,
renormalizados sobre os disponíveis. O risco **aumenta** a prioridade.

### `grade` — de `overall_standing`

`readiness 0.35 · momentum 0.35 · risk_inverted (100−risk) 0.30`,
renormalizados. Limiares: **A** ≥ 80 · **B** ≥ 65 · **C** ≥ 45 · **D** < 45 ·
**unknown** quando nenhum dos três entra.

Thresholds documentados como constantes: `RECENT_CONTENT_WINDOW_DAYS=14`,
`REPORT_DUE_AFTER_DAYS=30`, `RELEASE_WINDOW_DAYS=14`,
`MOMENTUM_CLICKS_{7D,30D,TOTAL}_SATURATION`,
`MOMENTUM_RECENT_OUTPUTS_SATURATION`.

## Ficheiros criados/alterados

### Criados

```text
app/services/scoring_engine.py               # ScoringEngine + regras/pesos
tests/test_scoring_engine.py                 # 26 testes unitários do motor
tests/test_scoring_endpoint.py               # 7 testes HTTP do endpoint
docs/gestao/fundamentos/resultados/prompt_05_scoring_engine.md
```

### Alterados

```text
app/api/scoring.py                # 501 stub → chamada ao ScoringEngine; IMPLEMENTED_ERROR_RESPONSES
tests/test_contract_endpoints.py  # /scoring/campaign movido de STUBBED para IMPLEMENTED
README.md                         # estado IE-005, tabela de endpoints, secção do endpoint, pesos/regras, exemplos, estrutura, próximos passos
```

Nada em `backend_core` foi alterado.

## Comandos executados

```bash
cd intelligence_engine
venv/Scripts/python.exe -m pytest -q                 # 124 passed
venv/Scripts/python.exe -m ruff check .              # All checks passed!
venv/Scripts/python.exe -m ruff format app/services/scoring_engine.py
# Smoke real via app factory (TestClient + token), payload rico:
#   -> 200, scores {readiness 100, momentum 90, opportunity 25, risk 0, priority 51}, grade A
```

## Resultados

- **pytest**: `124 passed` (era 91; +33 entre motor (26) e endpoint HTTP (7),
  e os parametrizados de contrato passam a contar `/scoring/campaign` como
  implementado). 1 warning conhecido (`httpx`/`starlette.testclient`,
  não bloqueante).
- **ruff check .**: `All checks passed!`.
- **ruff format**: aplicado ao motor; restantes ficheiros já formatados.
- **Cobertura de cenários (acceptance)**:
  - **bons sinais** → todos os scores presentes, readiness/momentum altos,
    risco 0, grade A (`test_good_campaign_*`);
  - **dados fracos** → momentum ≤10, oportunidade ≥80, grade C/D
    (`test_weak_campaign_*`);
  - **dados insuficientes** → cinco scores `null`, grade `unknown`, warnings
    `insufficient_data` + `<score>_unknown` (`test_empty_bundle_*`);
  - **dados parciais** → momentum `null` mas readiness/opportunity/risk/priority
    calculados, sem `insufficient_data` (`test_partial_data_*`);
  - **limites 0 e 100** → readiness, momentum, content_opportunity e risk
    atingem 0 e 100 (seis testes dedicados); `priority` renormaliza e respeita
    limites; `grade` estável por limiar (`test_grade_thresholds_are_stable`).
- **Sem 500 em payload inválido**: tipos malformados (`total_clicks` não
  numérico, `content_outputs` não-lista) → `422 invalid_payload`;
  `reference_date` inválido → `200` + warning; entity type desconhecido →
  `422`. Verificado por `test_malformed_data_types_yield_422_not_500` e
  `test_bad_context_reference_date_is_warned_not_500`.
- **Determinismo**: dois pedidos idênticos → respostas idênticas, ao nível do
  motor (`model_dump()`) e via HTTP.
- **Auth**: `/scoring/campaign` rejeita token ausente/errado (`403`); token
  nunca aparece em respostas nem logs (herda `require_internal_token`).

## Pendências

- Motores ainda por implementar: recommendations (IE-006), moments (IE-007),
  endpoint composto (IE-008) — continuam a devolver `501 not_implemented`.
- Os pesos e thresholds são deliberadamente simples (MVP) e ainda não
  calibrados com dados reais (risco IE-RSK-002 — "scores parecerem objectivos
  mas serem heurísticos fracos"). Mitigado pela explicabilidade: cada score
  expõe os seus componentes e pesos, e cada decisão é auditável e ajustável
  num único sítio (constantes no topo de `scoring_engine.py`).
- `app/api/internal_debug.py` mantém-se (suporta testes de auth); remover
  quando deixar de ser necessário.
- `recent_content`/`content_gap` degradam para presença sem `reference_date`;
  para máxima fidelidade temporal, o Backend Core deve enviar sempre
  `context.reference_date`.
- Warning de depreciação `httpx`/`starlette.testclient` — não bloqueante.

## Próximo passo recomendado

Avançar para **IE-006 — Recommendation engine MVP**: implementar
`RecommendationEngine` por trás de `POST /recommendations/campaign`, mapeando os
scores (e, mais tarde, os moments) para acções de campanha
(`create_release_post`, `create_media_kit`, `improve_smart_link`,
`wait_for_more_data`, …) com `priority`, `confidence`, `reason` e, quando
aplicável, `suggested_content_pack`/`expected_outputs` — reaproveitando os
sinais já produzidos pela análise (IE-004) e pelo scoring (IE-005), mantendo a
mesma disciplina determinística e explicável.
