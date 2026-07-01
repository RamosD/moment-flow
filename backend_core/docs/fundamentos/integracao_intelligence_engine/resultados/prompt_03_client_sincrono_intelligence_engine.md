# BC-IE-003 — Client síncrono para o Intelligence Engine

> **Tipo:** implementação de client interno (transporte + normalização + testes).
> **Fase:** `integracao_intelligence_engine` — tarefa **BC-IE-003**.
> **Data:** 2026-06-25.
> **Âmbito:** apenas o client síncrono no `backend_core`. **Não** foi implementado
> o payload builder (BC-IE-004) nem o endpoint API (BC-IE-006). **Não** foram
> tocados `intelligence_engine` nem `content_renderer`.
> **Base:** [`prompt_01`](prompt_01_analise_plano_integracao.md) e
> [`prompt_02`](prompt_02_settings_intelligence_engine.md).

---

## 0. Sumário executivo

- Criado `IntelligenceEngineClient` (módulo
  `apps/integrations_bridge/intelligence_sync.py`), uma camada fina **sobre o
  `InternalServiceClient` existente** — sem novas dependências, sem duplicar
  transporte.
- Método explícito `post_campaign_intelligence(payload, *, workspace_id,
  request_id)` → `POST /intelligence/campaign`, com os headers internos
  (`X-Internal-Token`, `X-Workspace-ID`, `X-Request-ID`) e o timeout configurado.
- Lê as settings do IE: `BASE_URL`, `TIMEOUT_SECONDS` e
  `INTERNAL_TOKEN` (via factory `build_intelligence_engine_client`).
- Normaliza o envelope de resposta do IE e mapeia **todos** os modos de falha em
  **erros tipados**: timeout, indisponível, 4xx, 5xx, JSON inválido, corpo não-
  objecto e status inesperado.
- **Token nunca é logado nem aparece em mensagens de erro** (verificado por
  testes).
- `ENABLED`/`DRY_RUN` **não** são consultados nesta camada — ficam centralizados
  no service (BC-IE-005), seguindo o padrão do projecto (decisão §3.2).
- **20 testes novos** (mock HTTP), **118 testes** da bridge a passar; ruff e
  `manage.py check` limpos.

---

## 1. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| [`apps/integrations_bridge/intelligence_sync.py`](../../../../../apps/integrations_bridge/intelligence_sync.py) | **Novo.** `IntelligenceEngineClient`, `IntelligenceResult`, erros tipados, factory |
| [`apps/integrations_bridge/tests/test_intelligence_sync.py`](../../../../../apps/integrations_bridge/tests/test_intelligence_sync.py) | **Novo.** 20 testes (sucesso, protocolo, HTTP, transporte, segurança, factory) |

> Nenhum ficheiro existente foi alterado. `clients.py`, `registry.py`,
> `services.py` e `intelligence.py` (caminho assíncrono) ficaram **intactos**.

---

## 2. Comportamento implementado

### 2.1 Reutilização vs novo client
O `InternalServiceClient` já trata transporte JSON-sobre-`urllib`, headers
internos, logging token-free e excepções tipadas de transporte
(`InternalClientTimeout`, `InternalServiceUnavailable`, `InternalHTTPError`,
`InvalidJSONResponse`). É **reutilizado tal como está** (composição). O novo
`IntelligenceEngineClient` só acrescenta:
1. o **endpoint nomeado** `/intelligence/campaign` (vs `/jobs/` do assíncrono);
2. a **normalização** do envelope de resposta do IE;
3. **erros tipados específicos** do IE para decisões de mapeamento/retry a
   jusante.

### 2.2 Método público
```python
client.post_campaign_intelligence(payload, *, workspace_id, request_id) -> IntelligenceResult
```
- `payload`: o envelope já montado (o builder é a BC-IE-004; aqui é só um `dict`).
- Headers enviados (pelo client interno): `X-Internal-Token`, `X-Workspace-ID`,
  `X-Request-ID`, `Content-Type`. `X-Job-ID` vai vazio (opcional/ignorado no
  síncrono — contrato §6).
- Timeout: `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` (aplicado no `post_json`).

### 2.3 Resultado normalizado (`IntelligenceResult`)
Dataclass com `status, engine, engine_version, request_id, workspace_id, result,
explanations, warnings, metadata, raw`. `result` é o bloco `{analysis, scores,
grade, moments, recommendations, summary}`; `raw` guarda o envelope completo
(forward-compat). `metadata.generated_at` é `null` por desenho do IE — o
carimbo é responsabilidade do service (BC-IE-005).

### 2.4 Mapa de tratamento de respostas

| Situação | Origem | Erro/retorno do client | Retry (BC-IE-007) |
|---|---|---|---|
| 200 `status=completed` | sucesso | `IntelligenceResult` | — |
| 200 `status` ≠ completed | corpo inesperado | `IntelligenceEngineProtocolError` | não |
| 200 corpo não-objecto | corpo inesperado | `IntelligenceEngineProtocolError` | não |
| JSON inválido | `InvalidJSONResponse` | `IntelligenceEngineProtocolError` | não |
| 400 / 422 | `InternalHTTPError` | `IntelligenceEngineResponseError` (`is_client_error`) | **não** |
| 403 | `InternalHTTPError` | `IntelligenceEngineResponseError` (`error_code=unauthorized_internal_request`) | **não** |
| 5xx | `InternalHTTPError` | `IntelligenceEngineResponseError` (`is_server_error`) | sim (cauteloso) |
| timeout | `InternalClientTimeout` | `IntelligenceEngineTimeout` | sim |
| indisponível / sem base_url | `InternalServiceUnavailable` | `IntelligenceEngineUnavailable` | sim |

`IntelligenceEngineResponseError` expõe `status_code`, `error_code`,
`is_client_error`/`is_server_error` — dá ao service (BC-IE-005) e à política de
retry (BC-IE-007) toda a informação para decidir, **sem** guardar o corpo bruto.

### 2.5 Segurança e logs
- Logger dedicado `integrations_bridge.intelligence`. Linhas `key=value` com
  `request_id`, `workspace_id`, `status`/`status_code`/`error_code`. **Nunca**
  token, headers ou payload/corpo.
- `_parse_error_body` extrai apenas `error.code`/`error.message` do envelope do
  IE (best-effort, nunca levanta, nunca devolve o corpo bruto). O IE não devolve
  stack trace no corpo (contrato §8.2) e o token só viaja em headers.

### 2.6 Decisão sobre `ENABLED`/`DRY_RUN` (§3.2)
**Não** são consultados no client. No projecto, os switches do caminho
assíncrono (`EXTERNAL_JOBS_*`) são honrados em `services._submit_job`, **não** em
`clients.py`. Para manter a simetria e um client puro/testável, `INTELLIGENCE_
ENGINE_ENABLED` (curto-circuito) e `INTELLIGENCE_ENGINE_DRY_RUN` (stub
determinístico) serão tratados no `CampaignIntelligenceService` (BC-IE-005). O
client mantém-se uma camada de transporte+normalização. Há um guard defensivo:
`base_url` vazio → `IntelligenceEngineUnavailable`.

---

## 3. Decisões

| ID | Decisão |
|---|---|
| §3.1 | Reutilizar `InternalServiceClient` por composição; novo wrapper só para endpoint nomeado + normalização |
| §3.2 | `ENABLED`/`DRY_RUN` ficam no service (BC-IE-005), não no client (alinhado com `_submit_job`) |
| §3.3 | Nome da classe `IntelligenceEngineClient` (como sugerido no prompt); módulo `intelligence_sync.py` para não colidir com `intelligence.py` (builders assíncronos) |
| §3.4 | Erros tipados ricos (`...ResponseError` com `status_code`/`error_code`) para suportar a política de retry da BC-IE-007 sem reabrir esta camada |
| §3.5 | Token lido de `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` (que por sua vez faz fallback para `INTERNAL_API_TOKEN`, BC-IE-002) |

---

## 4. Testes (20 novos)

| Grupo | Casos |
|---|---|
| `TestSuccess` | resultado normalizado; headers + path correctos; timeout aplicado; warnings/scores `unknown` passam |
| `TestProtocolErrors` | JSON inválido; status inesperado; corpo não-objecto |
| `TestHTTPErrors` | 403, 422, 400, 500, e 5xx com corpo não-parseável (fallback `http_error`) |
| `TestTransportFailures` | timeout; indisponível; `base_url` vazio |
| `TestSecurityAndLogging` | token ausente dos logs (sucesso e erro); token ausente da mensagem de erro; `request_id`/`workspace_id` presentes nos logs |
| `TestFactory` | `build_intelligence_engine_client` lê `BASE_URL`/`TIMEOUT`/`INTERNAL_TOKEN` e envia o token correcto |

Transporte injectado via `opener` (sem HTTP real); erros HTTP simulados com
`urllib.error.HTTPError` + `io.BytesIO` para fornecer corpo de envelope de erro.

---

## 5. Validações executadas

| Verificação | Comando | Resultado |
|---|---|---|
| Testes do client | `pytest apps/integrations_bridge/tests/test_intelligence_sync.py` | **20 passed** |
| Suite da bridge | `pytest apps/integrations_bridge/` | **118 passed** |
| Lint | `ruff check apps/integrations_bridge/` | **All checks passed** |
| Django system check | `manage.py check` | **0 issues** |

> Warnings são pré-existentes (`No directory at: staticfiles/`), não introduzidos
> por esta fase.

---

## 6. Conformidade com os critérios de aceitação

- [x] Client síncrono para `POST /intelligence/campaign` (`post_campaign_intelligence`).
- [x] Headers internos enviados (X-Internal-Token, X-Workspace-ID, X-Request-ID) — testado.
- [x] Timeout aplicado (`INTELLIGENCE_ENGINE_TIMEOUT_SECONDS`) — testado.
- [x] 4xx, 5xx, timeout e JSON inválido tratados de forma previsível (erros tipados).
- [x] Token não aparece em logs nem em mensagens de erro — testado.
- [x] Testes do client passam (20).
- [x] Validações executadas (ruff, suite da bridge, check).
- [x] Relatório com ficheiros, comportamento, testes, pendências e próximo passo.

---

## 7. Pendências / notas para fases seguintes

- **`ENABLED`/`DRY_RUN`** a implementar no service (BC-IE-005): curto-circuito
  quando desligado; stub determinístico documentado em dry-run.
- **Default de teste dry-run** (nota da BC-IE-002): ao escrever os testes do
  service, considerar forçar `INTELLIGENCE_ENGINE_DRY_RUN=True` por omissão para
  garantir zero HTTP real, à semelhança do `conftest.py` raiz para `EXTERNAL_JOBS_*`.
- **Política de retry** (BC-IE-007): o client já distingue
  `is_client_error`/`is_server_error`/timeout/unavailable; a decisão de
  *quantas* tentativas fica para o service/política.
- **Mapeamento HTTP→resposta do utilizador** (BC-IE-006): traduzir os erros
  tipados em respostas seguras (sem detalhes internos).

---

## 8. Próximo passo recomendado

Avançar para **BC-IE-004 — payload builder**: criar
`CampaignIntelligencePayloadBuilder` (em `apps/campaigns`) que monta o envelope
(`payload_version`, `workspace_id`, `request_id`, `entity`, `context.reference_
date`, `data`) a partir dos modelos reais (campaign, artist, track,
smart_link_stats, content_outputs, **`previous_reports`** — ver discrepância §5.1
do prompt_01 —, media_kits, goals), JSON-safe e sem N+1, com testes de campanha
rica/mínima/sem relacionados. O envelope produzido alimenta directamente o
`post_campaign_intelligence` deste client.
