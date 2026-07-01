# BC-IE-006 — Endpoint API de intelligence de campanha

> **Tipo:** implementação de endpoint API + serializer + OpenAPI + testes.
> **Fase:** `integracao_intelligence_engine` — tarefa **BC-IE-006**.
> **Data:** 2026-06-25.
> **Âmbito:** apenas o endpoint no `backend_core`. **Não** foram tocados
> `intelligence_engine` nem `content_renderer`.
> **Base:** [`prompt_05` (serviço)](prompt_05_service_campaign_intelligence.md).

---

## 0. Sumário executivo

- Adicionada a action `intelligence` ao `CampaignViewSet`:
  **`POST /api/v1/campaigns/{id}/intelligence/`**.
- Reutiliza o `WorkspaceScopedRBACViewSet`: autenticação JWT, isolamento por
  workspace (`get_object()` scoped) e RBAC (`campaigns:view`).
- Chama `get_campaign_intelligence(...)` e devolve a resposta normalizada
  (analysis, scores, grade, moments, recommendations, summary + explanations,
  warnings, metadata, generated_at, source).
- Mapeia as excepções do serviço para HTTP seguro: 404 / 502 / 503, sem expor
  token, stack trace ou corpo do IE.
- Serializer de resposta para OpenAPI + `schema.yml` regenerado.
- **11 testes de API novos**; suite completa **439 passed**; ruff e
  `manage.py check` limpos.

---

## 1. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| [`apps/campaigns/views.py`](../../../../../apps/campaigns/views.py) | Action `intelligence`; excepções DRF `IntelligenceUnavailable` (503) e `IntelligenceUpstreamFailure` (502); entrada `"intelligence": ["campaigns:view"]` em `_CAMPAIGN_PERMS` |
| [`apps/campaigns/serializers.py`](../../../../../apps/campaigns/serializers.py) | `CampaignIntelligenceResponseSerializer` + `CampaignIntelligenceResultSerializer` (documentação/schema) |
| [`apps/campaigns/tests/test_intelligence_api.py`](../../../../../apps/campaigns/tests/test_intelligence_api.py) | **Novo.** 11 testes de API |
| [`schema.yml`](../../../../../schema.yml) | Regenerado (inclui o novo path + componentes) |

---

## 2. Rota e decisões

### 2.1 Abordagem: `@action` no ViewSet (POST)
Seguindo o padrão já usado em `content/views.py` e `links/views.py`, a forma mais
consistente é uma `@action(detail=True, methods=["post"], url_path="intelligence")`
no `CampaignViewSet`. **POST** porque dispara cálculo remoto, pode vir a aceitar
contexto (PD-6) e não deve ser cacheado (backlog PDEC-001).

### 2.2 Segurança herdada (sem reinventar)
`get_object()` usa o queryset do `WorkspaceScopedRBACViewSet`, **filtrado pelo
workspace activo** → campanha de outro workspace (ou soft-deleted) é **404** (não
vaza existência). `HasWorkspacePermission` + `required_permissions["intelligence"]
= ["campaigns:view"]` garante RBAC; `IsAuthenticated` garante autenticação.

### 2.3 RBAC: reutilizar `campaigns:view`
Intelligence é enriquecimento de leitura de uma campanha → gated por
`campaigns:view` (sem novas permissões/seeds). Uma permissão dedicada
(`campaigns:intelligence`) fica como evolução futura.

### 2.4 Mapeamento de erros (serviço → HTTP)

| Excepção do serviço | HTTP | `code` |
|---|---|---|
| `CampaignNotFoundError` | 404 | `not_found` (DRF `NotFound`) |
| `IntelligenceDisabledError` | 503 | `intelligence_disabled` |
| `IntelligenceUnavailableError` | 503 | `intelligence_unavailable` |
| `IntelligenceUpstreamError` | 502 | `intelligence_upstream_error` |
| (autenticação ausente) | 401 | — |
| (sem `campaigns:view`) | 403 | — |
| (header `X-Workspace-ID` ausente/inválido) | 400 | — |

As respostas usam `default_detail` genéricos — **não** expõem token, stack trace
nem o corpo do IE.

### 2.5 Resposta de sucesso
`Response(outcome.as_dict())`: `status, source, engine, engine_version,
request_id, workspace_id, campaign_id, result{analysis, scores, grade, moments,
recommendations, summary}, explanations, warnings, metadata, generated_at`.

---

## 3. OpenAPI

`schema.yml` regenerado com `manage.py spectacular --file schema.yml` (sem
warnings). Novo path `/api/v1/campaigns/{id}/intelligence/`
(`operationId: api_v1_campaigns_intelligence_create`) e os componentes
`CampaignIntelligenceResponse`/`CampaignIntelligenceResult`.

---

## 4. Testes (11 novos)

| Classe | Casos |
|---|---|
| `TestSuccess` | sucesso (monkeypatch) com todos os blocos do IE + passagem de workspace/campaign/user; dry-run real (sem HTTP) com blocos presentes |
| `TestAccessControl` | 401 sem auth; 403 sem `campaigns:view` (billing_admin); 400 sem header de workspace; 404 campanha inexistente; 404 cross-workspace |
| `TestEngineFailures` | 503 IE desligado (path real); 503 unavailable; 502 upstream; 404 not-found do serviço |

---

## 5. Validações executadas

| Verificação | Comando | Resultado |
|---|---|---|
| Testes de API | `pytest apps/campaigns/tests/test_intelligence_api.py` | **11 passed** |
| Suite de campaigns | `pytest apps/campaigns/` | **54 passed** |
| Suite completa | `pytest -q` | **439 passed** |
| Lint | `ruff check apps/campaigns/` | **All checks passed** |
| Django system check | `manage.py check` | **0 issues** |
| OpenAPI | `manage.py spectacular --file schema.yml` | gerado sem warnings |

---

## 6. Conformidade com os critérios de aceitação

- [x] Endpoint existe e está protegido (auth + RBAC + workspace).
- [x] Utilizador sem permissão não acede (403).
- [x] Campanha fora do workspace não é exposta (404).
- [x] Endpoint chama o serviço (`get_campaign_intelligence`).
- [x] Resposta de sucesso contém os blocos principais do IE.
- [x] Erros previsíveis e testados (401/403/400/404/502/503).
- [x] OpenAPI/schema actualizado.
- [x] Testes de API passam (11); suite completa 439 passed.
- [x] Relatório com ficheiros, rota, decisões, testes, pendências e próximo passo.

---

## 7. Pendências / notas

- **`reference_date` por body (PD-6):** hoje o endpoint usa `request=None`; o
  override por contexto fica para evolução futura.
- **Timeout/retry/fallback (BC-IE-007):** consolidar política operacional.
- **Snapshot (PDEC-002):** continua fora do MVP.

---

## 8. Próximo passo recomendado

**BC-IE-007** — consolidar timeout, política de retry mínima e fallback
controlado para todos os modos de falha, com logs úteis sem secrets e testes de
falha dedicados.
