# Relatório de execução — Prompt 06: Recommendation engine MVP

Implementação do `POST /recommendations/campaign` (IE-006) com geração
**determinística**, **explicável** e **sem efeitos no produto** de recomendações
de campanha. O motor **só sugere**: nunca cria entidades no Django, nunca chama
o renderer, nunca persiste. Honra a tese arquitectural — *Intelligence
recomenda → Django decide e cria jobs → Renderer gera activos*.

## Contexto consultado (sem alterações)

- `backend_core/apps/content/seeds.py` — catálogo **semeado** real: packs
  `release_pack`, `milestone_pack`, `weekly_growth_pack`, `auto_media_kit` e
  templates `system_post`/`system_story`/`system_carousel`/`system_thumbnail`/
  `system_report`/`system_media_kit`. É a fonte da verdade para
  `suggested_content_pack`/`expected_outputs`, espelhada como constantes no
  motor (sem importar Django) — mitigação directa do risco IE-RSK-005.
- `backend_core/apps/content/models.py` — `ContentPack.PackType`,
  `Template.TemplateType`, `ContentPackTemplate` (mapeamento pack→template→
  output_type/format).
- `backend_core/apps/campaigns/models.py` — `Campaign.CampaignType`
  (`single_release`, `milestone_campaign`, `weekly_growth_campaign`,
  `media_campaign`, …), `Status` e `CampaignGoal` (`goal_type=milestone`,
  `status=achieved`).
- `backend_core/apps/links/models.py` e `apps/reports/models.py` — sinais de
  smart link e estados de report/media kit.
- `content_renderer/src/constants.ts` — confirma que o renderer é dirigido por
  jobs do Django (não há registry de templates a consultar; o renderer não é
  chamado pelo Intelligence). Nenhum ficheiro do renderer foi alterado.

## Decisões de desenho

1. **Só sugere, nunca age.** A `Recommendation` carrega `action`, `priority`,
   `confidence`, `reason`, `suggested_content_pack`/`expected_outputs` e
   `explanations`. Não há qualquer escrita, chamada externa ou persistência —
   o endpoint é uma função pura do payload.
2. **Baixo acoplamento, com reutilização do scoring.** O motor chama o
   `scoring_engine` apenas pelo seu **output público** (`ScoreSet`), que
   orienta a decisão "campanha saudável → `no_action`" e a propagação de avisos
   de consistência. Os gatilhos de conteúdo são lidos directamente do data
   bundle. Não se importam helpers privados do scoring nem da análise. A
   compatibilidade de schemas (todos `CampaignRequest`) permite reconstruir o
   `ScoringRequest` via `model_validate(request.model_dump())` — atravessa o
   contrato público, sem dependência de internals.
3. **Compatibilidade com o produto garantida por construção.** Cada pack e cada
   `template_key` sugeridos pertencem ao catálogo semeado (`SUPPORTED_PACKS`,
   `SUPPORTED_TEMPLATE_KEYS`). Como todas as recomendações MVP são suportáveis,
   não foi necessária a marcação "conceptual"; um teste de invariante verifica
   que nenhuma recomendação referencia algo fora do catálogo.
4. **Determinismo.** Regras temporais ancoradas a `context.reference_date` (sem
   relógio); confianças fixas por regra (nunca aleatórias); ordenação estável
   por (prioridade, −confiança, nome da acção); `metadata.generated_at` a
   `null`. Mesmo input → mesma lista ordenada.
5. **Explicabilidade em duas camadas.** Cada recomendação traz uma
   `Explanation` com o código do gatilho (ex.: `release_window`,
   `milestone_click_threshold`); o envelope traz uma `Explanation`
   `scoring_basis` com os scores que orientaram a decisão.
6. **Dados insuficientes → espera.** Quando o scoring não consegue calcular
   nenhum score, devolve-se uma única recomendação `wait_for_more_data` e um
   `Warning` `insufficient_data`. Avisos de consistência do scoring são
   propagados; payloads malformados são rejeitados com `422` (nunca `500`).
7. **Extensão mínima do contrato.** Adicionado `explanations` (lista) à
   `Recommendation` para a justificação por recomendação que o prompt pede,
   mantendo retrocompatibilidade (campo opcional, default vazio).

## Regras implementadas

| Gatilho | Acção | Prioridade | Confiança | Pack |
| --- | --- | --- | --- | --- |
| Todos os scores `null` | `wait_for_more_data` | low | 0.30 | — |
| Faixa na janela de lançamento (±14d) | `create_release_post` | high | 0.85 | release_pack |
| Campanha de lançamento active/scheduled | `create_release_post` | medium | 0.70 | release_pack |
| Goal milestone achieved | `create_milestone_post` | high | 0.80 | milestone_pack |
| campaign_type milestone_campaign | `create_milestone_post` | high | 0.75 | milestone_pack |
| total_clicks ≥ 1000 | `create_milestone_post` | medium | 0.65 | milestone_pack |
| campaign_type weekly_growth_campaign (active) | `create_weekly_growth_post` | medium | 0.75 | weekly_growth_pack |
| clicks_last_7_days ≥ 20 (active) | `create_weekly_growth_post` | medium | 0.65 | weekly_growth_pack |
| Sem media kit utilizável | `create_media_kit` | high (media_campaign)/medium | 0.70 | auto_media_kit |
| Sem report recente + substância | `create_report` | medium | 0.70 | — (system_report) |
| Active + actividade de smart link | `create_story` | low | 0.60 | — (system_story) |
| Smart link presente mas inactivo | `improve_smart_link` | high (active)/medium | 0.70 | — |
| Nada disparou, dados suficientes | `no_action` | low | 0.50 | — |

Constantes documentadas: `RELEASE_WINDOW_DAYS=14`, `REPORT_DUE_AFTER_DAYS=30`,
`MILESTONE_CLICKS_THRESHOLD=1000`, `WEEKLY_GROWTH_CLICKS_THRESHOLD=20`, mapa
`CONFIDENCE` por regra. O `create_weekly_growth_post` suprime o
`create_story` (o pack semanal já inclui um story), evitando ruído.

## Ficheiros criados/alterados

### Criados

```text
app/services/recommendation_engine.py          # RecommendationEngine + regras
tests/test_recommendation_engine.py            # 22 testes unitários do motor
tests/test_recommendations_endpoint.py         # 6 testes HTTP do endpoint
docs/gestao/fundamentos/resultados/prompt_06_recommendation_engine.md
```

### Alterados

```text
app/api/recommendations.py        # 501 stub → chamada ao RecommendationEngine; IMPLEMENTED_ERROR_RESPONSES
app/schemas/recommendations.py    # + explanations por Recommendation
tests/test_contract_endpoints.py  # /recommendations/campaign movido para IMPLEMENTED
README.md                         # estado IE-006, tabela de endpoints, secção do endpoint, regras, exemplos, estrutura, próximos passos
```

Nada em `backend_core` nem em `content_renderer` foi alterado.

## Comandos executados

```bash
cd intelligence_engine
venv/Scripts/python.exe -m pytest -q                       # 152 passed
venv/Scripts/python.exe -m ruff check .                    # All checks passed!
venv/Scripts/python.exe -m ruff format app/services/recommendation_engine.py \
    app/api/recommendations.py app/schemas/recommendations.py \
    tests/test_recommendation_engine.py tests/test_recommendations_endpoint.py
# Smoke real via app factory (TestClient + token):
#   campanha single_release na janela → 200, 1ª recomendação create_release_post (high),
#   seguida de create_media_kit/create_report/create_milestone_post/create_weekly_growth_post
#   (ordenadas por prioridade, confiança, acção); warnings [].
```

## Resultados

- **pytest**: `152 passed` (era 124; +28 — motor (22) e endpoint HTTP (6); os
  testes de contrato parametrizados mantêm o total, apenas mudam de bucket).
  1 warning conhecido (`httpx`/`starlette.testclient`, não bloqueante).
- **ruff check .**: `All checks passed!`.
- **ruff format**: aplicado aos ficheiros do motor/testes; restantes já
  formatados.
- **Cobertura das recomendações principais** (acceptance):
  - `create_release_post` (janela e tipo de campanha);
  - `create_milestone_post` (goal achieved e limiar de cliques);
  - `create_weekly_growth_post` (tipo e sinal semanal), com supressão de
    `create_story`;
  - `create_media_kit` (incl. `media_campaign` → high; draft não recebe;
    media kit existente não é recomendado);
  - `create_report` (substância presente; report recente limpa a recomendação);
  - `create_story`; `improve_smart_link` (high em campanha active);
  - `wait_for_more_data` (dados insuficientes + warning);
  - `no_action` (campanha saudável → única recomendação).
- **Estrutura e ordenação**: cada recomendação tem `action`, `priority`,
  `confidence∈[0,1]`, `reason` e `explanations`; lista ordenada por prioridade
  (verificado).
- **Compatibilidade com o produto**: invariante testado —
  `suggested_content_pack ∈ SUPPORTED_PACKS ∪ {None}` e cada `template_key ∈
  SUPPORTED_TEMPLATE_KEYS ∪ {None}`.
- **Sem efeitos colaterais**: o motor não importa Django nem o renderer; a
  resposta é função pura do payload (determinismo verificado ao nível do motor
  e via HTTP).
- **Sem 500 em payload inválido**: tipos malformados → `422 invalid_payload`;
  entity type desconhecido → `422`; sem token → `403`.

## Pendências

- Motores ainda por implementar: moments (IE-007) e endpoint composto (IE-008)
  — continuam a devolver `501 not_implemented`.
- O catálogo de packs/templates é espelhado manualmente a partir de
  `backend_core/apps/content/seeds.py`. Se o Backend Core semear novos packs,
  as constantes `SUPPORTED_PACKS`/`SUPPORTED_TEMPLATE_KEYS` e os builders de
  `expected_outputs` devem ser actualizados (ou, no futuro, alimentados por um
  contrato/catálogo partilhado).
- Confianças e limiares são MVP, não calibrados com dados reais (risco
  IE-RSK-002); mitigado pela explicabilidade (cada recomendação expõe o gatilho)
  e por estarem centralizados como constantes.
- `create_report`/`create_story` sugerem `template_key` suportado mas sem
  `suggested_content_pack` (não há pack semeado dedicado a report-only ou
  story-only); o Django decide o meio de cumprimento.
- `app/api/internal_debug.py` mantém-se (suporta testes de auth); remover quando
  deixar de ser necessário.
- Warning de depreciação `httpx`/`starlette.testclient` — não bloqueante.

## Próximo passo recomendado

Avançar para **IE-007 — Moment detection MVP**: implementar `MomentDetector`
por trás de `POST /moments/detect`, detectando momentos simples
(`release_window`, `weekly_growth`, `milestone_reached`, `low_engagement`,
`content_gap`, `report_due`, `media_kit_missing`, `smart_link_activity`) com
`severity`, `confidence`, `summary` e `recommended_action`, reaproveitando os
sinais já produzidos pela análise (IE-004), scoring (IE-005) e recommendations
(IE-006), mantendo a mesma disciplina determinística e explicável.
