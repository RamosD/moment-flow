# Relatório de execução — Prompt 07: Moment detection MVP

Implementação do `POST /moments/detect` (IE-007) com detecção **determinística**
e **explicável** dos oito momentos MVP. O detector é um *sensor* sobre o data
bundle de campanha: identifica oportunidades simples que justificam uma acção.
Sem IA generativa, sem scraping, sem chamadas externas, sem persistência.

## Contexto consultado (sem alterações)

- `backend_core/apps/campaigns/models.py` — `Campaign.CampaignType`
  (`single_release`, `weekly_growth_campaign`, `milestone_campaign`,
  `media_campaign`, …), `Status` e `CampaignGoal`
  (`goal_type=milestone`/`status=achieved`).
- `backend_core/apps/links/models.py` — sinais de smart link (clicks/active
  links) para `weekly_growth`, `low_engagement`, `smart_link_activity`.
- `backend_core/apps/content/models.py` — `ContentOutput.Status.COMPLETED`
  (`content_gap`).
- `backend_core/apps/reports/models.py` — `Report.Status.COMPLETED` e
  `MediaKit.Status` (`generated`/`published`) para `report_due` e
  `media_kit_missing`.
- `backend_core/apps/catalogue` — `Track.release_date` para `release_window`.

Nenhum ficheiro do Backend Core foi alterado.

## Decisões de desenho

1. **Detector como sensor de sinais (baixo acoplamento).** O `MomentDetector`
   lê o data bundle directamente com predicados próprios e pequenos; **não**
   chama o scoring nem o recommendation engine. Mantém-se consistente com eles
   reutilizando os **mesmos limiares** (janela de lançamento, recência de
   report, limiares de cliques) e mapeando cada momento para uma acção que o
   recommendation engine sabe cumprir.
2. **Compatibilidade de acções garantida.** `RECOMMENDED_ACTION` mapeia cada
   `MomentType` para um `ActionType` do recommendation engine; um teste estático
   verifica que todos os valores pertencem ao vocabulário `ActionType`, e um
   teste dinâmico verifica que cada momento emitido respeita isto.
3. **Determinismo.** Regras temporais ancoradas a `context.reference_date` (sem
   relógio); confianças fixas por sinal (nunca aleatórias); ordenação estável
   por (severidade, −confiança, tipo); `metadata.generated_at` a `null`.
4. **Explicabilidade em duas camadas.** Cada momento traz uma `Explanation` com
   o código do sinal detectado (ex.: `release_window_detected`,
   `milestone_detected`); o envelope fica com `explanations: []` (a justificação
   vive em cada momento). Estendi o schema `Moment` com `explanations`
   (retrocompatível, default vazio) para cumprir o requisito do prompt.
5. **Dados insuficientes → lista vazia + warning.** Bundle vazio →
   `moments: []` e `Warning` `insufficient_data`, com `status=completed` (não é
   erro). Payloads malformados → `422` (nunca `500`).
6. **Anti-ruído deliberado.** `weekly_growth` suprime `smart_link_activity` (já
   captura a actividade forte); `content_gap` distingue ausência total (high/
   medium consoante `active`) de conteúdo apenas antigo (low).

## Regras de detecção implementadas

| Momento | Gatilho | Severidade | Confiança | Acção recomendada |
| --- | --- | --- | --- | --- |
| `release_window` | faixa a ±14d da referência (±3d → imminent) | high/medium | 0.90/0.80 | `create_release_post` |
| `weekly_growth` | `weekly_growth_campaign` ou `clicks_last_7_days ≥ 20` | medium | 0.75/0.65 | `create_weekly_growth_post` |
| `milestone_reached` | goal milestone achieved / `milestone_campaign` / `total_clicks ≥ 1000` | high/high/medium | 0.85/0.80/0.65 | `create_milestone_post` |
| `low_engagement` | smart link presente sem actividade | high (active)/medium | 0.75 | `improve_smart_link` |
| `content_gap` | sem conteúdo completo / só conteúdo antigo | high·medium/low | 0.80/0.60 | `create_release_post` |
| `report_due` | sem report recente + substância | medium | 0.70 | `create_report` |
| `media_kit_missing` | sem media kit utilizável (não draft) | high (media_campaign)/medium | 0.70 | `create_media_kit` |
| `smart_link_activity` | actividade de smart link (weekly não disparou) | low | 0.70 | `create_story` |

Limiares documentados como constantes: `RELEASE_WINDOW_DAYS=14`,
`RELEASE_IMMINENT_DAYS=3`, `RECENT_CONTENT_WINDOW_DAYS=14`,
`REPORT_DUE_AFTER_DAYS=30`, `MILESTONE_CLICKS_THRESHOLD=1000`,
`WEEKLY_GROWTH_CLICKS_THRESHOLD=20`.

## Ficheiros criados/alterados

### Criados

```text
app/services/moment_detector.py        # MomentDetector + regras de detecção
tests/test_moment_detector.py          # 24 testes unitários do detector
tests/test_moments_endpoint.py         # 6 testes HTTP do endpoint
docs/gestao/fundamentos/resultados/prompt_07_moment_detection.md
```

### Alterados

```text
app/api/moments.py                # 501 stub → chamada ao MomentDetector; IMPLEMENTED_ERROR_RESPONSES
app/schemas/moments.py            # + explanations por Moment
tests/test_contract_endpoints.py  # /moments/detect movido para IMPLEMENTED (só /intelligence/campaign fica stub)
README.md                         # estado IE-007, tabela de endpoints, secção do endpoint, regras, exemplos, estrutura, próximos passos
```

Nada em `backend_core` foi alterado.

## Comandos executados

```bash
cd intelligence_engine
venv/Scripts/python.exe -m pytest -q                  # 182 passed
venv/Scripts/python.exe -m ruff check .               # All checks passed!
venv/Scripts/python.exe -m ruff format app/services/moment_detector.py \
    app/api/moments.py app/schemas/moments.py \
    tests/test_moment_detector.py tests/test_moments_endpoint.py
# Smoke real via app factory (TestClient + token), campanha single_release na janela:
#   200, ordenado por severidade → release_window(high,0.9), content_gap(high,0.8),
#   media_kit_missing(medium,0.7), report_due(medium,0.7), milestone_reached(medium,0.65),
#   weekly_growth(medium,0.65); smart_link_activity suprimido (weekly disparou).
```

## Resultados

- **pytest**: `182 passed` (era 152; +30 — detector (24) e endpoint HTTP (6);
  os testes de contrato parametrizados mantêm o total, apenas mudam de bucket).
  1 warning conhecido (`httpx`/`starlette.testclient`, não bloqueante).
- **ruff check .**: `All checks passed!`.
- **ruff format**: aplicado aos ficheiros do detector/testes; restantes já
  formatados.
- **Cobertura por tipo de momento** (um teste focado cada): `release_window`
  (imminent/far/fora de janela), `weekly_growth` (tipo/sinal), `milestone_reached`
  (goal/cliques), `low_engagement`, `content_gap` (ausência/antigo/limpo por
  conteúdo recente), `report_due` (devido/limpo por report recente),
  `media_kit_missing` (media_campaign/limpo por media kit), `smart_link_activity`.
- **Garantias transversais**: cada momento tem `type`, `severity`, `confidence∈
  [0,1]`, `summary`, `recommended_action` e `explanations`; ordenação por
  severidade verificada; `recommended_action` sempre compatível com o
  recommendation engine (estático + dinâmico).
- **Dados insuficientes**: bundle vazio → `moments: []` + warning
  `insufficient_data`, sem `500`.
- **Robustez**: contadores negativos → warning `negative_smart_link_stats`;
  `reference_date` inválido → warning `invalid_reference_date`; tipos malformados
  → `422 invalid_payload`; entity type desconhecido → `422`; sem token → `403`.
- **Determinismo**: verificado ao nível do detector (`model_dump()`) e via HTTP.

## Pendências

- Motor ainda por implementar: endpoint composto (IE-008) — continua a devolver
  `501 not_implemented`.
- O detector reusa limiares partilhados (release window, report, milestone,
  weekly) por duplicação documentada de constantes em cada serviço; uma fase
  futura pode centralizá-los num módulo de configuração comum se a calibração
  passar a ser frequente (risco IE-RSK-002).
- Severidades/confianças são MVP, não calibradas com dados reais; mitigadas pela
  explicabilidade (cada momento expõe o sinal) e por estarem centralizadas como
  constantes.
- `app/api/internal_debug.py` mantém-se (suporta testes de auth); remover quando
  deixar de ser necessário.
- Warning de depreciação `httpx`/`starlette.testclient` — não bloqueante.

## Próximo passo recomendado

Avançar para **IE-008 — Endpoint composto**: implementar o
`IntelligenceOrchestrator` por trás de `POST /intelligence/campaign`, executando
e agregando numa só chamada a análise (IE-004), o scoring (IE-005), os momentos
(IE-007) e as recomendações (IE-006), com `summary` executivo, `explanations`
consolidadas e `warnings` de dados insuficientes — garantindo que uma falha
parcial controlada não gera `500` indevido, mantendo a disciplina determinística
e explicável.
