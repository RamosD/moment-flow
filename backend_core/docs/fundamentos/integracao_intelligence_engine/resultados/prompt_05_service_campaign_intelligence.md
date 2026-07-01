# BC-IE-005 — Serviço de domínio para intelligence de campanha

> **Tipo:** implementação de serviço de domínio + testes unitários.
> **Fase:** `integracao_intelligence_engine` — tarefa **BC-IE-005**.
> **Data:** 2026-06-25.
> **Âmbito:** apenas o serviço no `backend_core`. **Não** expõe endpoint API
> (BC-IE-006). **Não** persiste snapshots. **Não** foram tocados
> `intelligence_engine` nem `content_renderer`.
> **Base:** [`prompt_03` (client)](prompt_03_client_sincrono_intelligence_engine.md),
> [`prompt_04` (builder)](prompt_04_builder_data_bundle_campaign.md).

---

## 0. Sumário executivo

- Criado `CampaignIntelligenceService` (+ `get_campaign_intelligence`) em
  `apps/campaigns/intelligence_service.py`. Orquestra:
  **carregar campanha (scoped) → validar → builder → client → normalizar**.
- Carrega a campanha **scoped ao workspace** com `select_related("artist",
  "track")`; cross-workspace e soft-deleted colapsam em `CampaignNotFoundError`
  (nunca vaza existência).
- Honra `INTELLIGENCE_ENGINE_ENABLED` (erro controlado) e
  `INTELLIGENCE_ENGINE_DRY_RUN` (stub determinístico, sem chamada) — os switches
  vivem **no serviço**, não no client (decisão §2.1).
- Mapeia **todos** os erros do client em 3 excepções de serviço tipadas
  (disabled / unavailable / upstream) para a camada API traduzir em HTTP seguro.
- Carimba `generated_at` do lado Django; **sem** snapshot (MVP, contrato §11).
- Token nunca é manuseado nem logado aqui. Logs com `request_id`,
  `workspace_id`, `campaign_id`, `status`, `duration_ms`.
- **18 testes novos**; `campaigns`+`integrations_bridge` **161 passed**; ruff e
  `manage.py check` limpos.

---

## 1. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| [`apps/campaigns/intelligence_service.py`](../../../../../apps/campaigns/intelligence_service.py) | **Novo.** `CampaignIntelligenceService`, `CampaignIntelligenceOutcome`, excepções tipadas, stub dry-run, factory function |
| [`apps/campaigns/tests/test_intelligence_service.py`](../../../../../apps/campaigns/tests/test_intelligence_service.py) | **Novo.** 18 testes (sucesso, isolamento, switches, mapeamento de erros, logging) |

> Nenhum ficheiro existente foi alterado. O serviço fica num módulo dedicado
> (a par de `intelligence_payload.py`), separado do `services.py` (slug helper).

---

## 2. Comportamento implementado

### 2.1 Onde vivem os switches (decisão)
`INTELLIGENCE_ENGINE_ENABLED`/`DRY_RUN` são consultados **no serviço**, espelhando
o caminho assíncrono onde `services._submit_job` honra os `EXTERNAL_JOBS_*`. O
client permanece transporte puro (BC-IE-003) e o builder adapter puro (BC-IE-004).

### 2.2 Fluxo (`run()`)
```text
1. _load_campaign(): Campaign.objects.filter(workspace, id).select_related(artist, track).first()
   → None ⇒ CampaignNotFoundError (cobre inexistente, cross-workspace e soft-deleted)
2. ENABLED? não ⇒ IntelligenceDisabledError (controlado; client não é chamado)
3. build_campaign_intelligence_payload(campaign, workspace, request_id, reference_date)
4. DRY_RUN? sim ⇒ stub determinístico (sem chamada)
5. _call_engine(): client.post_campaign_intelligence(payload, workspace_id, request_id)
   → mapeia erros → CampaignIntelligenceOutcome(source="engine", generated_at=agora)
```
O `request_id` é gerado uma vez no serviço e usado **tanto** no envelope (builder)
**como** no header (client), garantindo correlação consistente.

### 2.3 Mapa de erros (client → serviço → HTTP sugerido para BC-IE-006)

| Erro do client | Excepção do serviço | HTTP sugerido | Retry |
|---|---|---|---|
| `IntelligenceEngineTimeout` | `IntelligenceUnavailableError` | 503 | sim |
| `IntelligenceEngineUnavailable` | `IntelligenceUnavailableError` | 503 | sim |
| `ResponseError` 5xx | `IntelligenceUnavailableError` | 503 | sim (cauteloso) |
| `ResponseError` 4xx (403/422/404) | `IntelligenceUpstreamError` | 502 | **não** |
| `IntelligenceEngineProtocolError` | `IntelligenceUpstreamError` | 502 | não |
| (campanha não encontrada) | `CampaignNotFoundError` | 404 | — |
| (IE desligado) | `IntelligenceDisabledError` | 503 | — |

**Racional 4xx→502:** um 403 (token) ou 422 (payload) **não** é culpa do pedido do
utilizador; é um problema de configuração/contrato nosso ou do IE. Não deve
surgir como 4xx para o cliente — daí 502.

### 2.4 Dry-run (resposta previsível e documentada)
Com `INTELLIGENCE_ENGINE_DRY_RUN=True`, o serviço **valida e monta o payload**
(exercita builder + isolamento), **não** chama o IE, e devolve:
```json
{
  "status": "completed", "source": "dry_run",
  "result": {"analysis": {}, "scores": {}, "grade": "unknown",
             "moments": [], "recommendations": [],
             "summary": "Dry-run: Intelligence Engine was not called."},
  "warnings": [{"code": "dry_run", "message": "INTELLIGENCE_ENGINE_DRY_RUN is enabled; no real call was made."}],
  "metadata": {"dry_run": true}
}
```

### 2.5 Resultado (`CampaignIntelligenceOutcome.as_dict()`)
`status, source, engine, engine_version, request_id, workspace_id, campaign_id,
result, explanations, warnings, metadata, generated_at`. `source ∈ {engine,
dry_run}`; `generated_at` carimbado pelo Django (o IE devolve `null`, contrato §8.1).

### 2.6 Persistência
**Nenhuma** (MVP — contrato §11 / PDEC-002). Resposta em tempo real. Sem
`ExternalJobReference`, sem callbacks.

### 2.7 Segurança/observabilidade
O serviço nunca toca no token (está no client/settings). `_log` emite linhas
`key=value` token-free com `event`, `request_id`, `workspace_id`, `campaign_id`,
e `status`/`duration_ms`/`error_code` conforme o evento.

---

## 3. Testes (18 novos)

| Classe | Casos |
|---|---|
| `TestSuccess` | outcome engine; propagação de `request_id`/`workspace_id` (header + payload + entity); shape de `as_dict`; aceita `campaign_id` |
| `TestLoadingAndIsolation` | inexistente → not-found; cross-workspace → not-found; soft-deleted → not-found; sem identificador → `ValueError` |
| `TestSwitches` | desligado → `IntelligenceDisabledError` (sem chamada); dry-run → stub (sem chamada) |
| `TestErrorMapping` | timeout/unavailable/500 → unavailable; 403/422 → upstream; protocol → upstream |
| `TestLogging` | token ausente dos logs; contexto de domínio (`campaign_id`, `event=ok`) presente |

Client **injectado** (stub que devolve `IntelligenceResult` ou levanta os erros
tipados reais do client) → zero HTTP, mapeamento testado fielmente.

---

## 4. Validações executadas

| Verificação | Comando | Resultado |
|---|---|---|
| Testes do serviço | `pytest apps/campaigns/tests/test_intelligence_service.py` | **18 passed** |
| Suites campaigns + bridge | `pytest apps/campaigns/ apps/integrations_bridge/` | **161 passed** |
| Lint | `ruff check apps/campaigns/intelligence_service.py …/test_intelligence_service.py` | **All checks passed** |
| Django system check | `manage.py check` | **0 issues** |

> Warnings pré-existentes (`No directory at: staticfiles/`).

---

## 5. Conformidade com os critérios de aceitação

- [x] Devolve intelligence com sucesso usando builder + client.
- [x] Trata campanha inexistente (`CampaignNotFoundError`).
- [x] Trata workspace inválido (cross-workspace → not-found, sem vazar).
- [x] Trata IE desactivado (`IntelligenceDisabledError`) e dry-run (stub).
- [x] Trata timeout/5xx/4xx/JSON inválido sem crash (excepções tipadas).
- [x] Token não aparece em logs.
- [x] Testes unitários passam (18).
- [x] Validações executadas (ruff, suites, check).
- [x] Relatório com ficheiros, comportamento, testes, pendências e próximo passo.

---

## 6. Pendências / notas para fases seguintes

- **Endpoint API (BC-IE-006):** mapear as excepções do §2.3 para respostas HTTP
  seguras; usar a tabela. Decidir se passa `campaign`/`campaign_id` (o serviço
  re-carrega scoped de qualquer forma, garantindo isolamento).
- **Retry (BC-IE-007):** ainda não implementado (sem retry no MVP). O serviço já
  distingue transitório (unavailable) de definitivo (upstream); a política de
  tentativas entra na BC-IE-007.
- **`reference_date` por request (PD-6):** o serviço aceita `reference_date`; o
  endpoint pode expô-lo via body.
- **Snapshot (PDEC-002):** continua fora do MVP.

---

## 7. Próximo passo recomendado

Avançar para **BC-IE-006 — endpoint API**: adicionar
`@action(detail=True, methods=["post"], url_path="intelligence")` ao
`CampaignViewSet` (`POST /api/v1/campaigns/{id}/intelligence/`), com
`required_permissions["intelligence"] = ["campaigns:view"]`, chamando
`get_campaign_intelligence(workspace=request.workspace, campaign=self.get_object(),
requested_by=request.user)` e traduzindo `CampaignNotFoundError`→404,
`IntelligenceDisabledError`/`IntelligenceUnavailableError`→503,
`IntelligenceUpstreamError`→502, com serializer de resposta e actualização do
OpenAPI, mais testes de API (auth, RBAC, cross-workspace, sucesso, erros).
