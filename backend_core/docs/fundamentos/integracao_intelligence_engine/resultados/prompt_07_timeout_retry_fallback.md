# BC-IE-007 — Timeout, retry e fallback (comportamento operacional)

> **Tipo:** consolidação de comportamento operacional + retry configurável + testes.
> **Fase:** `integracao_intelligence_engine` — tarefa **BC-IE-007**.
> **Data:** 2026-06-25.
> **Âmbito:** apenas o `backend_core`. **Não** foram tocados `intelligence_engine`
> nem `content_renderer`.
> **Base:** client [`prompt_03`](prompt_03_client_sincrono_intelligence_engine.md),
> serviço [`prompt_05`](prompt_05_service_campaign_intelligence.md),
> endpoint [`prompt_06`](prompt_06_endpoint_api_campaign_intelligence.md).

---

## 0. Sumário executivo

- **Timeout** já configurável (`INTELLIGENCE_ENGINE_TIMEOUT_SECONDS`, default 10 s;
  contrato §9.1). Mantido.
- Adicionada **política de retry mínima e configurável** no client (camada de
  transporte): retry **apenas** para falhas transitórias (timeout / unreachable /
  5xx); **nunca** em 4xx nem em resposta inutilizável. Defaults:
  `INTELLIGENCE_ENGINE_MAX_RETRIES=1`, `INTELLIGENCE_ENGINE_RETRY_BACKOFF_SECONDS=0.5`.
- **Fallback controlado** confirmado para os 9 modos de falha (desligado,
  dry-run, timeout, conexão recusada, 5xx, 403, 422, JSON inválido, resposta
  inesperada) → mapeados para 404/502/503 seguros, **sem** expor token, stack
  trace ou corpo do IE.
- **Logs** enriquecidos: o serviço passa a registar `duration_ms` e `error_type`
  também nas falhas (já tinha em sucesso); o client regista cada retry. Nunca o
  token.
- **+8 testes** (7 de retry no client + presença de settings); suites-alvo
  **87 passed**; suite completa verde; ruff e `manage.py check` limpos.

---

## 1. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| [`config/settings.py`](../../../../../config/settings.py) | `INTELLIGENCE_ENGINE_MAX_RETRIES` (1) e `INTELLIGENCE_ENGINE_RETRY_BACKOFF_SECONDS` (0.5) |
| [`.env.example`](../../../../../.env.example) | Documenta as duas variáveis de retry |
| [`apps/integrations_bridge/intelligence_sync.py`](../../../../../apps/integrations_bridge/intelligence_sync.py) | Loop de retry transitório-only em `post_campaign_intelligence`; `_attempt()` extraído; factory lê as settings de retry |
| [`apps/campaigns/intelligence_service.py`](../../../../../apps/campaigns/intelligence_service.py) | `duration_ms` + `error_type` nos logs de falha |
| [`apps/integrations_bridge/tests/test_settings_client_registry.py`](../../../../../apps/integrations_bridge/tests/test_settings_client_registry.py) | Presença das settings de retry |
| [`apps/integrations_bridge/tests/test_intelligence_sync.py`](../../../../../apps/integrations_bridge/tests/test_intelligence_sync.py) | `TestRetry` (7 casos) + factory lê retry |

> O endpoint (`views.py`) **não** precisou de alterações: já mapeava as excepções
> do serviço para HTTP seguro (BC-IE-006). Esta tarefa consolidou-o e testou-o.

---

## 2. Política aplicada

### 2.1 Timeout
`INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` (default **10 s**, configurável por env),
aplicado pelo `InternalServiceClient` em cada tentativa. Curto porque o cálculo
do IE é sub-milissegundo; o tempo de parede é rede/serialização (contrato §9.1).

### 2.2 Retry (mínimo, transitório-only, dentro do request)
Implementado no **client** (a fronteira de transporte), porque retry é fiabilidade
de transporte — distinto das *políticas de produto* (`ENABLED`/`DRY_RUN`), que
ficam no serviço.

| Falha | Retry? | Racional |
|---|---|---|
| `IntelligenceEngineTimeout` | **sim** | transitório; engine idempotente/sem estado (contrato §9.2) |
| `IntelligenceEngineUnavailable` (conexão recusada/sem base_url) | **sim** | transitório |
| `IntelligenceEngineResponseError` 5xx | **sim** | transitório |
| `IntelligenceEngineResponseError` 4xx (403/404/422) | **não** | erro de contrato/config — retry não ajuda |
| `IntelligenceEngineProtocolError` (JSON inválido / status inesperado / corpo não-objecto) | **não** | determinístico — retry não ajuda |

- Tentativas = `MAX_RETRIES + 1`. Backoff **linear curto** (`backoff * tentativa`),
  default 0.5 s. Como corre **dentro do request HTTP do utilizador**, é deliberadamente
  pequeno e limitado (default 1 retry → no máximo +1 tentativa, ~0.5 s).
- **Decisão de default:** `MAX_RETRIES=1` (um retry cauteloso) — alinhado com o
  contrato §9.2/PDEC-004 ("retry simples em falhas transitórias", "evitar retry
  longo durante o request"). Pode ser posto a `0` para latência mínima.
- O construtor do client tem default `max_retries=0` (test-friendly); é a *factory*
  (`build_intelligence_engine_client`) que injecta o default de produção (1) a
  partir das settings.

### 2.3 Fallback controlado (todos os modos de falha)

| Situação | Camada | Excepção do serviço | HTTP | Resposta ao consumidor |
|---|---|---|---|---|
| IE desactivado | serviço | `IntelligenceDisabledError` | **503** | `intelligence_disabled` |
| IE dry-run | serviço | — (stub) | **200** | `source="dry_run"`, warning `dry_run` |
| Timeout | client→serviço | `IntelligenceUnavailableError` | **503** | `intelligence_unavailable` |
| Conexão recusada | client→serviço | `IntelligenceUnavailableError` | **503** | `intelligence_unavailable` |
| 5xx | client→serviço | `IntelligenceUnavailableError` | **503** | `intelligence_unavailable` |
| 403 interno | client→serviço | `IntelligenceUpstreamError` | **502** | `intelligence_upstream_error` |
| 422 invalid_payload | client→serviço | `IntelligenceUpstreamError` | **502** | `intelligence_upstream_error` |
| JSON inválido | client→serviço | `IntelligenceUpstreamError` | **502** | `intelligence_upstream_error` |
| Resposta inesperada (status ≠ completed / corpo não-objecto) | client→serviço | `IntelligenceUpstreamError` | **502** | `intelligence_upstream_error` |

Racional 4xx→502: um 403 (token) ou 422 (payload) é falha de configuração/contrato
nossa, **não** do pedido do utilizador → não deve surgir como 4xx.

### 2.4 Respostas seguras
As respostas usam `default_detail` genéricos das `APIException` (`IntelligenceUnavailable`
503 / `IntelligenceUpstreamFailure` 502 / `NotFound` 404). **Nunca** incluem token,
stack trace nem o corpo/`error_code` do IE. O `error_code` do IE fica apenas nos
**logs** (diagnóstico), não na resposta. Em produção (`DEBUG=False`) o DRF também
não expõe tracebacks.

---

## 3. Observabilidade (logs sem secrets)

| Camada | Logger | Campos |
|---|---|---|
| Client | `integrations_bridge.intelligence` | `event` (start/ok/timeout/unavailable/http_error/invalid_json/unexpected_status/bad_body/**retry**), `request_id`, `workspace_id`, `status`, `error_code`, `attempt`/`of` |
| Serviço | `campaigns.intelligence` | `event` (ok/unavailable/server_error/upstream_error/protocol_error/dry_run/disabled), `request_id`, `workspace_id`, `campaign_id`, `status`, `error_code`, **`error_type`**, **`duration_ms`** |

- `request_id`, `workspace_id`, `campaign_id`, tempo de chamada (`duration_ms`),
  tipo de erro e status da resposta: **todos cobertos**.
- O **token nunca é logado** (o `InternalServiceClient` não o regista; o wrapper e
  o serviço não lhe tocam) — verificado por testes (`test_token_not_in_logs`,
  `test_token_never_logged_on_*`).

---

## 4. Testes

### 4.1 Novos (8)
- `TestRetry` (7): sem retry por omissão (construtor); 5xx retentado N vezes
  então levanta; timeout retentado; unavailable retentado; **sucesso após falha
  transitória**; **4xx não retentado** (1 chamada); **protocol error não
  retentado** (1 chamada). Backoff=0 → testes rápidos.
- Settings: presença de `INTELLIGENCE_ENGINE_MAX_RETRIES`/`..._RETRY_BACKOFF_SECONDS`;
  factory lê-as (`max_retries`/`retry_backoff`).

### 4.2 Reforçados/confirmados (já existentes)
- Client: 403/422/400/500, timeout, unavailable, JSON inválido, status inesperado,
  corpo não-objecto, token ausente de logs/mensagens.
- Serviço: mapeamento timeout/unavailable/5xx→unavailable; 403/422/protocol→upstream;
  token ausente dos logs.
- API: 401/403/400/404/502/503 + sucesso (engine e dry-run).

---

## 5. Validações executadas

| Verificação | Comando | Resultado |
|---|---|---|
| Suites-alvo (client+settings+serviço+API) | `pytest …test_intelligence_sync.py …test_settings_client_registry.py …test_intelligence_service.py …test_intelligence_api.py` | **87 passed** |
| Suite completa | `pytest -q` | **446 passed** (439 + 7 retry) |
| Lint | `ruff check apps/ config/` | **All checks passed** |
| Django system check | `manage.py check` | **0 issues** |

---

## 6. Conformidade com os critérios de aceitação

- [x] Timeout configurável (`INTELLIGENCE_ENGINE_TIMEOUT_SECONDS`).
- [x] 4xx **não** é retentado (testado: 1 chamada).
- [x] Timeout/5xx/unavailable tratados de forma controlada (retry transitório → erro 503).
- [x] Erros devolvidos ao cliente são seguros (sem token/stack/corpo do IE).
- [x] Logs ajudam diagnóstico sem expor secrets (request_id/workspace_id/campaign_id/duration_ms/error_type/status).
- [x] Testes de falha passam.
- [x] Validações executadas (ruff, suites, check).
- [x] Relatório com ficheiros, política, testes, pendências e próximo passo.

---

## 7. Pendências / notas

- **Default de retry (`MAX_RETRIES=1`):** decisão de produto/operacional; pode ser
  `0` para latência mínima ou `2` (limite recomendado pelo contrato §9.2). Fica
  configurável por env.
- **Sem circuit breaker / jitter:** o MVP usa retry linear simples. Backoff
  exponencial/jitter e circuit breaker ficam para observabilidade futura (fora do MVP).
- **Degradação graciosa alternativa:** o endpoint é explícito ("dá-me intelligence"),
  por isso falha com 502/503; se mais tarde o insight for embutido noutra vista,
  pode-se preferir devolver a vista sem o insight (contrato §9.2).

---

## 8. Próximo passo recomendado

**BC-IE-008** — validar a integração com mocks HTTP de ponta a ponta (cobrir
completed/warnings/recommendations/moments/scores=unknown/timeout/403/422/5xx/JSON
inválido; confirmar `request_id`/`workspace_id` propagados e token não logado),
consolidando os testes já existentes do client/serviço/API num conjunto de
integração coerente.
