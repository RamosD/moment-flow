# BC-IE-004 — Builder do data bundle de campanha

> **Tipo:** implementação de adapter/builder + testes unitários.
> **Fase:** `integracao_intelligence_engine` — tarefa **BC-IE-004**.
> **Data:** 2026-06-25.
> **Âmbito:** apenas o builder no `backend_core`. **Não** chama o Intelligence
> Engine (BC-IE-005). **Não** foram tocados `intelligence_engine` nem
> `content_renderer`.
> **Base:** [`prompt_01`](prompt_01_analise_plano_integracao.md),
> [`prompt_03`](prompt_03_client_sincrono_intelligence_engine.md).

---

## 0. Sumário executivo

- Criado `CampaignIntelligencePayloadBuilder` (+ função
  `build_campaign_intelligence_payload`) em `apps/campaigns/intelligence_payload.py`.
- Monta o envelope do contrato §7: `payload_version="1.0"`, `workspace_id`,
  `request_id`, `entity` (campaign), `context.reference_date`, e o bloco `data`.
- Recolhe dados reais de **campaigns, catalogue, links, content, reports** via
  queries eficientes (`.values()` + um `aggregate` para cliques) — **sem N+1**
  (provado por teste com muitas linhas relacionadas).
- Serialização **JSON-safe**: UUID→`str`, date/datetime→ISO, Decimal→`float`,
  nulos preservados; o payload completo passa em `json.dumps`.
- **Workspace mismatch** validado no construtor (`WorkspaceMismatchError`).
- Dados ausentes geram payload válido (listas vazias, `track=None`, stats a zero)
  — nunca erro inesperado.
- **13 testes novos**; suite de campaigns **25 passed**; ruff e `manage.py check`
  limpos.

---

## 1. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| [`apps/campaigns/intelligence_payload.py`](../../../../../apps/campaigns/intelligence_payload.py) | **Novo.** Builder, helpers JSON-safe, `WorkspaceMismatchError`, factory function |
| [`apps/campaigns/tests/test_intelligence_payload.py`](../../../../../apps/campaigns/tests/test_intelligence_payload.py) | **Novo.** 13 testes (envelope, campanha rica, N+1, dados esparsos, isolamento, validação) |

> Nenhum ficheiro existente foi alterado. Os modelos de `links`/`content`/
> `reports` são importados **lazy** dentro dos métodos (padrão já usado em
> `integrations_bridge/intelligence.py`), evitando ciclos de import.

---

## 2. Decisões de mapeamento (modelo → contrato §7.1)

| Campo do bundle | Origem | Fonte / notas |
|---|---|---|
| `campaign` | `Campaign` | `id, name, campaign_type, status, start_date(ISO), end_date(ISO), primary_goal` |
| `artist` | `campaign.artist` | `id, name, primary_genre, status`; `None` se ausente (FK é obrigatório, mas defensivo) |
| `track` | `campaign.track` | `id, title, release_date(ISO), track_type, status`; **`None`** quando a campanha não tem track |
| `smart_link_stats` | `SmartLinkClick` + `SmartLink` | `total_clicks` (lifetime), `clicks_last_7_days`, `clicks_last_30_days` (janelas `[ref-N, ref]`), `active_links` (status=`active`, exclui soft-deleted) |
| `content_outputs` | `campaign.content_outputs` | `[{id, output_type, status, created_at(ISO)}]`, top `MAX_ITEMS` por `-created_at` |
| `previous_reports` | `campaign.reports` (`Report`) | `[{id, report_type, status, period_end(ISO)}]` — **chave canónica que o IE lê** |
| `reports` | (alias) | mesma lista que `previous_reports` (ver §2.1) |
| `media_kits` | `campaign.media_kits` (`MediaKit`) | `[{id, status}]` |
| `goals` | `campaign.goals` (`CampaignGoal`) | `[{goal_type, status, target_value(float), current_value(float), unit, deadline(ISO)}]` |

### 2.1 Discrepância `reports` vs `previous_reports` (resolvida)
O backlog §7.3 escreve `data.reports`; o **contrato §7.1 (autoritativo) lê
`previous_reports`** (discrepância já sinalizada no prompt_01 §5.1). Para garantir
compatibilidade com o que o IE **efectivamente consome** *e* satisfazer a redacção
do backlog/prompt, o builder emite **ambas** as chaves apontando para a mesma
lista. O `data` do IE é permissivo (`extra="allow"`), pelo que a chave extra não
quebra o contrato. `previous_reports` é a canónica; `reports` é alias documentado.

### 2.2 Janelas temporais de cliques
`reference_date` (default hoje, UTC) ancora as janelas: `clicks_last_7_days` =
cliques com `clicked_at__date ∈ [ref-7, ref]`; `clicks_last_30_days` = `[ref-30,
ref]`; `total_clicks` = lifetime. Tudo num **único** `aggregate` com `Count(...,
filter=Q(...))`. Determinístico e alinhado com o contrato §7 (recência ancorada
no `reference_date`).

### 2.3 Limite de tamanho
Cada lista é limitada a `MAX_ITEMS = 50` (ordenada por `-created_at`) para manter
o payload limitado em campanhas movimentadas. Decisão documentada; ajustável.

---

## 3. JSON-safe & robustez

- Helpers `_iso` (date/datetime→ISO), `_id` (UUID→str), `_num` (Decimal→float);
  nulos preservados como `None`.
- Enums/choices (`status`, `campaign_type`, `report_type`, …) já são strings
  armazenadas — passam directas.
- `enum`/`Decimal`/`date`/`UUID` confirmados serializáveis: cada teste relevante
  faz `json.dumps(payload)`.

---

## 4. Performance (sem N+1)

Por construção, o builder emite um número **constante** de queries,
independente do volume de dados relacionados:

```
artist (lazy)  + track (lazy)  + clicks(aggregate) + active_links(count)
+ content_outputs + reports + media_kits + goals  ≈ 8 queries
```

Cada colecção usa **uma** query `.values()` (sem instanciar modelos nem disparar
acessos por linha). O teste `test_no_n_plus_one_with_many_related_rows` cria 5+
linhas de cada entidade e afirma `django_assert_max_num_queries(9)` — provando
que o custo não cresce com o número de linhas. Callers podem
`select_related("artist", "track")` para poupar 2 queries.

---

## 5. Testes (13 novos)

| Classe | Casos |
|---|---|
| `TestEnvelope` | top-level (version/workspace_id/entity/context/data keys); `request_id` gerado e respeitado; `reference_date` default = hoje; alias `reports == previous_reports` |
| `TestRichCampaign` | todas as secções preenchidas + JSON-safe (stats 3/1/2, active_links exclui paused); **N+1 bound** com muitas linhas |
| `TestSparseData` | campanha mínima sem track/relacionados; sem smart links; sem content outputs; sem reports/media kits |
| `TestIsolationAndValidation` | **workspace mismatch** levanta `WorkspaceMismatchError`; dados de outra campanha (mesmo workspace) **não** vazam |

Cobre os 6 cenários exigidos pelo prompt + isolamento por campanha + geração/
respeito de `request_id` + serialização.

---

## 6. Validações executadas

| Verificação | Comando | Resultado |
|---|---|---|
| Testes do builder | `pytest apps/campaigns/tests/test_intelligence_payload.py` | **13 passed** |
| Suite de campaigns | `pytest apps/campaigns/` | **25 passed** |
| Lint | `ruff check apps/campaigns/intelligence_payload.py …/test_intelligence_payload.py` | **All checks passed** |
| Django system check | `manage.py check` | **0 issues** |

> Warnings são pré-existentes (`No directory at: staticfiles/`).

---

## 7. Conformidade com os critérios de aceitação

- [x] Builder gera payload compatível com o contrato do IE (envelope §7 + `data` §7.1).
- [x] Inclui `payload_version` 1.0, `workspace_id`, `request_id` e `entity` campaign.
- [x] Dados ausentes tratados sem falha (listas vazias, `track=None`, stats a zero).
- [x] Datas/UUIDs/enums/Decimal JSON-safe (`json.dumps` em testes).
- [x] Workspace mismatch tratado de forma segura (`WorkspaceMismatchError`).
- [x] Testes unitários passam (13).
- [x] Validações executadas (ruff, suite, check).
- [x] Relatório com ficheiros, decisões de mapeamento, testes, pendências e próximo passo.

---

## 8. Pendências / notas para fases seguintes

- **`reference_date` via request** (PD-6): hoje é "hoje" por omissão; o endpoint
  (BC-IE-006) pode permitir override por body.
- **`ENABLED`/`DRY_RUN`**: continuam responsabilidade do service (BC-IE-005); o
  builder é puro e não os consulta.
- **`select_related` no service**: o `CampaignIntelligenceService` deve carregar a
  campanha com `select_related("artist", "track")` para poupar 2 queries.
- **`MAX_ITEMS=50`**: rever se o produto precisar de mais histórico no payload.

---

## 9. Próximo passo recomendado

Avançar para **BC-IE-005 — serviço de domínio** (`CampaignIntelligenceService`):
orquestra `build_campaign_intelligence_payload` + `IntelligenceEngineClient`,
honra `INTELLIGENCE_ENGINE_ENABLED` (curto-circuito) e
`INTELLIGENCE_ENGINE_DRY_RUN` (stub determinístico), carrega a campanha com
`select_related("artist","track")`, trata timeout/5xx com degradação controlada,
carimba `generated_at` do lado Django, **sem** persistir snapshot — com testes de
client mockado (reutilizando o `opener` do BC-IE-003).
