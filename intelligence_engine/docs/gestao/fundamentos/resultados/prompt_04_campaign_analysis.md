# Relatório de execução — Prompt 04: Campaign analysis MVP

Implementação do `POST /analysis/campaign` (IE-004) com análise heurística,
**determinística** e **explicável** de campanhas, sobre os schemas definidos
no Prompt 03. Sem IA generativa, sem chamadas externas, sem persistência.

## Contexto consultado (sem alterações)

Reconfirmadas em `backend_core` as entidades e estados que alimentam as
heurísticas (nenhum ficheiro alterado):

- `apps/campaigns/models.py` — `Campaign.Status` (`active`, `draft`, …) usado
  na regra de risco R7.
- `apps/content/models.py` — `ContentOutput.Status.COMPLETED` (R1/R2).
- `apps/reports/models.py` — `Report.Status.COMPLETED` (R5) e
  `MediaKit.Status` (`generated`/`published`, R6).
- `apps/links/models.py` — sinais de smart link (clicks/active links, R3/R4).

## Decisões de desenho

1. **Determinismo via `reference_date` explícito**. A maior ameaça ao
   determinismo eram as regras de "recência". Em vez de ler `datetime.now()`
   (que tornaria o output dependente do momento da execução), o serviço lê
   `context.reference_date` (ISO `YYYY-MM-DD`). Sem ele, as regras de recência
   **degradam para presença** (ex.: "tem content outputs" em vez de "tem
   content outputs recentes"), nunca lendo o relógio. Resultado: o mesmo input
   gera sempre o mesmo output, independentemente de quando corre. Testado
   explicitamente (`test_same_input_produces_identical_output`,
   `test_response_is_deterministic_over_http`).
2. **`generated_at` deixado a `null`**. Para o response ser byte-a-byte
   reprodutível, o `metadata.generated_at` não é preenchido (timestamping é do
   Backend Core); apenas se ecoa `payload_version` (determinístico).
3. **Dados insuficientes ≠ erro**. Bundle vazio → `campaign_health=unknown` +
   warning `insufficient_data`, com `status=completed` (não é um erro HTTP).
   Payloads incompletos/contraditórios geram warnings, nunca 500 (R0/C1–C3).
4. **Ausência de dados vs. ausência de actividade**. Smart link sem
   estatísticas → *warning* `smart_link_stats_missing` (não sabemos), enquanto
   estatísticas presentes mas a zero → *weakness* `smart_link_no_activity`
   (sabemos que não há). Distinção deliberada para não penalizar dados em
   falta.
5. **Saúde derivada de sinais discretos** (não aritmética opaca): `unknown`
   (R0) · `critical` (há risco e nenhum strength) · `warning` (há
   risco/weakness, ou sinais sem tendência positiva) · `good` (strengths, sem
   riscos nem weaknesses). Cada sinal carrega uma `Explanation` com `code`,
   `message` e `weight`, garantindo explicabilidade.
6. **OpenAPI honesto por endpoint**. Adicionado `IMPLEMENTED_ERROR_RESPONSES`
   (403/422) em `app/api/_openapi.py`; o `/analysis/campaign` deixa de
   anunciar o `501` (que já não devolve), mantendo os stubs com o `501`.

## Regras heurísticas implementadas

| Regra | Condição                                          | Efeito / código |
| ----- | -------------------------------------------------- | ---------------- |
| R0    | bundle vazio                                       | `unknown` + warning `insufficient_data` |
| R1    | content outputs `completed` presentes              | strength `has_content_outputs` |
| R1b   | …e recentes (janela 14 dias, se datáveis)          | strength `recent_content_outputs` |
| R2    | sem content outputs `completed`                    | opportunity `content_gap` |
| R3    | smart link com actividade positiva                 | strength `smart_link_activity` |
| R4    | smart link presente mas sem actividade             | weakness `smart_link_no_activity` |
| R4b   | estatísticas de smart link ausentes                | warning `smart_link_stats_missing` |
| R5    | sem report `completed` recente (janela 30 dias)    | opportunity `report_due` |
| R6    | sem media kit `generated`/`published`              | opportunity `media_kit_missing` |
| R7    | campanha `active` sem conteúdo nem tracção          | risk `active_campaign_no_traction` |
| C1    | `end_date < start_date`                            | warning `inconsistent_campaign_dates` |
| C2    | contadores de smart link negativos                 | warning `negative_smart_link_stats` |
| C3    | content output datado após `reference_date`        | warning `future_content_output_date` |

Thresholds documentados como constantes: `RECENT_CONTENT_WINDOW_DAYS=14`,
`REPORT_DUE_AFTER_DAYS=30`.

## Ficheiros criados/alterados

### Criados

```text
app/services/campaign_analysis.py            # CampaignAnalysisService + heurísticas
tests/test_campaign_analysis_service.py      # 26 testes unitários do serviço
tests/test_analysis_endpoint.py              # 6 testes HTTP do endpoint
docs/gestao/fundamentos/resultados/prompt_04_campaign_analysis.md
```

### Alterados

```text
app/api/analysis.py            # 501 stub → chamada ao CampaignAnalysisService
app/api/_openapi.py            # + IMPLEMENTED_ERROR_RESPONSES (403/422)
tests/test_contract_endpoints.py  # /analysis/campaign agora 200 (não 501); 501 só nos stubs
README.md                      # estado IE-004, secção do endpoint, tabela de regras, exemplos, estrutura
```

## Comandos executados

```bash
venv/Scripts/python.exe -m pytest -q          # 91 passed
venv/Scripts/python.exe -m ruff check .       # All checks passed!
venv/Scripts/python.exe -m ruff format app/services/campaign_analysis.py tests/test_*.py

# Smoke test real (Uvicorn + token)
INTERNAL_API_TOKEN=smoke venv/Scripts/python.exe -m uvicorn app.main:app --port 8095
curl -X POST -H "X-Internal-Token: smoke" .../analysis/campaign -d '<good payload>'
```

## Resultados

- **pytest**: `91 passed` (era 61; +30 entre serviço (26) e endpoint HTTP
  (6), menos 2 do contrato reescrito). 1 warning conhecido
  (`httpx`/`starlette.testclient`).
- **ruff check .**: `All checks passed!`.
- **Smoke test real (Uvicorn)**:
  - payload rico (`active`, conteúdo recente, smart link activo, report
    recente, media kit publicado) → `200`, `status=completed`,
    `campaign_health=good`, 3 strengths, 3 explanations.
  - payload mínimo (só envelope) → `200`, `campaign_health=unknown`, warning
    `insufficient_data`.
  - sem token → `403`. Token ausente dos logs (confirmado).
- **Determinismo**: verificado ao nível do serviço e via HTTP (dois pedidos
  idênticos → respostas idênticas, `model_dump()` igual).
- **Sem 500 em dados maus**: datas inconsistentes, contadores negativos,
  `reference_date` inválido e datas no futuro produzem warnings e `200`.

## Pendências

- Motores ainda por implementar: scoring (IE-005), recommendations (IE-006),
  moments (IE-007), endpoint composto (IE-008) — continuam a devolver `501
  not_implemented`.
- `app/api/internal_debug.py` mantém-se (suporta os testes de auth com
  200-on-auth); remover quando deixar de ser necessário.
- As regras heurísticas e os thresholds são deliberadamente simples (MVP);
  futura calibração com dados reais (risco IE-RSK-002 — "scores/saúde
  parecerem objectivos mas serem heurísticos fracos"). A explicabilidade
  (`explanations` com `weight`) mitiga ao tornar cada decisão auditável.
- Warning de depreciação `httpx`/`starlette.testclient` — não bloqueante.

## Próximo passo recomendado

Avançar para **IE-005 — Scoring engine MVP**: implementar `ScoringEngine` por
trás de `POST /scoring/campaign`, derivando `campaign_readiness_score`,
`momentum_score`, `content_opportunity_score`, `risk_score` e `priority_score`
(0–100 ou `null`/unknown) e a `grade`, de forma determinística e explicável,
reaproveitando os sinais já produzidos pela análise de campanha.
