# Prompt 05 — Correlation-id ponta-a-ponta — Resultado

**Data:** 2026-07-02
**Fase:** `05_staging_operacionalizacao_pre_producao` (STG-PRE-005)
**Âmbito:** implementar a propagação de um correlation-id único entre Backend Core, Intelligence Engine, CampaignActions, artefactos, jobs, Content Renderer e callbacks. Sem substituir IDs de domínio, sem registar tokens/payload integral.
**Estado de execução:** `executado` — implementação completa (não apenas fundamentos), validada por testes automatizados e por um smoke real ponta-a-ponta com os quatro serviços a correr.

---

## 1. Resumo objectivo

A fase 04 tinha identificado que Intelligence, jobs e callbacks geravam
`request_id`s **independentes** entre si — cada chamada síncrona ao
Intelligence Engine e cada `ExternalJobReference` recebia o seu próprio
`uuid4().hex`, sem qualquer relação com o pedido HTTP que os originou nem
entre si. Implementei um `correlation_id` que nasce uma única vez por pedido
HTTP no Backend Core e flui, sem alteração de comportamento para quem não o
usa, até: o Intelligence Engine, o `CampaignAction`/`Report`/`MediaKit`/
`ContentPackRequest` criado, o `ExternalJobReference` que esse artefacto
dispara, o Content Renderer, e o callback de volta.

**Validação real, não só testes de unidade:** com os quatro serviços a
correr, enviei `X-Request-ID: e2e-smoke-trace-002` numa criação de `Report`
e confirmei — por leitura directa da base de dados e dos logs dos três
serviços — que o mesmo id aparece em: `report.correlation_id`,
`job.request_id`, nos logs do Backend Core (`job_created`,
`internal_call start/ok`, `job_submitted`, `callback_received`,
`callback_processed`) e nos logs do Content Renderer (`job.accepted`,
`render.started`, `report.render_started/finished`, `render.completed`,
`callback.started/completed`). Repeti para `CampaignAction`, `MediaKit` e
`ContentPackRequest` com o mesmo resultado.

Durante a implementação encontrei e corrigi um problema real: os novos
`logger.info(...)` de criação **não apareciam em lado nenhum** até eu
adicionar as respectivas entradas ao dicionário `LOGGING` — sem isso, o
logger de último recurso do Python só deixa passar `WARNING` e acima
(comportamento já documentado no `settings.py` para os loggers existentes,
mas que se repetia para os novos). Corrigido; há agora um teste dedicado que
impede esta regressão de passar despercebida outra vez.

---

## 2. Desenho do correlation-id

### 2.1 Cabeçalho canónico

`X-Request-ID` — já era o cabeçalho usado pelas chamadas Backend Core→
Intelligence Engine e Backend Core→Content Renderer (`clients.py`); não foi
introduzido nenhum cabeçalho novo, conforme pedido pela tarefa 6.

### 2.2 Origem e geração

`apps.core.middleware.CorrelationIdMiddleware` (novo, primeiro middleware a
correr depois do WhiteNoise):

- Se o pedido HTTP trouxer `X-Request-ID` **bem formado** (`^[A-Za-z0-9_-]{1,64}$`),
  reutiliza esse valor — permite que um frontend/proxy futuro proponha o seu
  próprio id.
- Caso contrário (ausente, vazio, ou com caracteres fora do conjunto seguro —
  defesa contra injecção de log/cabeçalho e contra tamanhos de log
  descontrolados), gera um `uuid4().hex` novo.
- Expõe o valor em `request.correlation_id` e devolve-o no cabeçalho de
  resposta `X-Request-ID`.

### 2.3 Estratégia de propagação (nenhum id de domínio substituído)

| Onde | Campo/mecanismo | Novo ou já existia? |
|---|---|---|
| Intelligence Engine (síncrono) | `CampaignIntelligenceService.request_id` (parâmetro já aceite, agora efectivamente ligado ao pedido HTTP via a view) | Já existia o parâmetro; a ligação à view é nova |
| `CampaignAction.correlation_id` | Campo novo (`apps.core.models.CorrelationIdModel`, mixin abstracto reutilizável) | Novo |
| `Report.correlation_id` | Idem | Novo |
| `MediaKit.correlation_id` | Idem | Novo |
| `ContentPackRequest.correlation_id` | Idem | Novo |
| `ExternalJobReference.request_id` | Campo já existente; passa a aceitar um valor explícito (`request_id=` opcional em `create_and_submit_external_job`) em vez de gerar sempre um novo | Comportamento estendido, 100% compatível — omitido continua a gerar como antes |
| Content Renderer | Cabeçalho + corpo `request_id` no envelope de job | Já existia; nenhuma alteração de código do Content Renderer |
| Callback → Backend Core | O `job.request_id` é o mesmo em toda a vida do job | Já existia |

Nenhum id de domínio (`action_id`, `report_id`, `media_kit_id`,
`content_pack_request_id`, `job_id`, `campaign_id`) foi removido, renomeado
ou substituído — o `correlation_id` é sempre um campo adicional.

### 2.4 Regras de segurança respeitadas

- O middleware nunca lê `Authorization` nem `X-Internal-Token` — só o
  cabeçalho de correlação.
- O `correlation_id` é opaco (uuid hex ou string validada por regex
  restritivo) — nunca contém PII nem dados de negócio.
- Nenhum log criado ou alterado nesta iteração regista o payload integral da
  intelligence, tokens, `Authorization` ou `X-Internal-Token` — confirmado
  por grep (ver §7).

---

## 3. Ficheiros alterados/criados

### Backend Core

| Ficheiro | Operação | Nota |
|---|---|---|
| `apps/core/middleware.py` | **criado** | `CorrelationIdMiddleware` |
| `apps/core/models.py` | alterado | `CorrelationIdModel` (mixin abstracto) |
| `apps/core/tests/test_correlation_id_middleware.py` | **criado** | 7 testes (geração, reutilização, ids diferentes por pedido, rejeição de ids malformados) |
| `config/settings.py` | alterado | `CorrelationIdMiddleware` registado em `MIDDLEWARE`; loggers `campaign_actions`, `reports`, `content` adicionados a `LOGGING` |
| `apps/campaign_actions/models.py` | alterado | `CampaignAction` ganha `CorrelationIdModel` |
| `apps/campaign_actions/migrations/0002_campaignaction_correlation_id.py` | **criado** | `AddField`, aditiva |
| `apps/campaign_actions/serializers.py` | alterado | `correlation_id` exposto (read-only) |
| `apps/campaign_actions/views.py` | alterado | `perform_create` regista `correlation_id`; log `campaign_action_created` |
| `apps/campaign_actions/tests/test_api.py` | alterado | +2 testes (com/sem cabeçalho) incl. verificação de log via `caplog` |
| `apps/reports/models.py` | alterado | `Report` e `MediaKit` ganham `CorrelationIdModel` |
| `apps/reports/migrations/0002_mediakit_correlation_id_report_correlation_id.py` | **criado** | `AddField` x2, aditiva |
| `apps/reports/serializers.py` | alterado | `correlation_id` exposto (read-only) nos dois serializers |
| `apps/reports/services.py` | alterado | `submit_report_generation_job`/`submit_media_kit_generation_job` aceitam `correlation_id`, propagam ao job |
| `apps/reports/views.py` | alterado | `perform_create` (Report e MediaKit) regista `correlation_id`; logs `report_created`/`media_kit_created` |
| `apps/reports/tests/test_reports.py` | alterado | +1 teste (propagação + log) |
| `apps/reports/tests/test_media_kits.py` | alterado | +1 teste (propagação + log) |
| `apps/content/models.py` | alterado | `ContentPackRequest` ganha `CorrelationIdModel` |
| `apps/content/migrations/0002_contentpackrequest_correlation_id.py` | **criado** | `AddField`, aditiva |
| `apps/content/serializers.py` | alterado | `correlation_id` exposto (read-only) |
| `apps/content/services.py` | alterado | `create_content_pack_request`/`_submit_content_generation_job` aceitam `correlation_id`, propagam ao job; log `content_pack_request_created` |
| `apps/content/views.py` | alterado | `perform_create` passa `correlation_id` |
| `apps/content/tests/test_requests_outputs.py` | alterado | +1 teste (propagação + log) |
| `apps/integrations_bridge/services.py` | alterado | `create_and_submit_external_job` aceita `request_id=None` opcional (fallback: gera como antes) |
| `apps/integrations_bridge/tests/test_create_submit_job.py` | alterado | +3 testes (reutilização explícita, geração quando omitido, chega ao cliente externo) |
| `apps/integrations_bridge/tests/test_log_correlation.py` | alterado | +3 nomes de logger no teste parametrizado de config; regressão do bug de `LOGGING` coberta |
| `apps/campaigns/views.py` | alterado | acção `intelligence` passa `request_id=request.correlation_id` |
| `apps/campaigns/tests/test_intelligence_api.py` | alterado | `fake_service` actualizado para aceitar `request_id`; teste passa a validar propagação |

### Intelligence Engine

| Ficheiro | Operação | Nota |
|---|---|---|
| `app/api/intelligence.py` | alterado | logging a nível app de `request_id`/`workspace_id` em `intelligence.request_received`/`intelligence.request_completed` (fecha OBS-L01/L02) |
| `tests/test_intelligence_endpoint.py` | alterado | +1 teste (`caplog`, confirma `request_id` nos logs e ausência do token) |

### Content Renderer

**Nenhuma alteração.** Já honrava `X-Request-ID` (entrada/saída) e já
incluía `request_id` no envelope do job e em todos os eventos de log
(`job.accepted`, `render.*`, `callback.*`) — confirmado por leitura de código
e pelo smoke real (ver §6).

---

## 4. Testes

| Suite | Resultado |
|---|---|
| `apps/core/tests/test_correlation_id_middleware.py` (novo) | ✅ 7/7 |
| `apps/campaign_actions/tests/test_api.py` | ✅ 15/15 (2 novos) |
| `apps/reports/tests/test_reports.py` | ✅ 9/9 (1 novo) |
| `apps/reports/tests/test_media_kits.py` | ✅ 8/8 (1 novo) |
| `apps/content/tests/test_requests_outputs.py` | ✅ 7/7 (1 novo) |
| `apps/integrations_bridge/tests/test_create_submit_job.py` | ✅ 13/13 (3 novos) |
| `apps/integrations_bridge/tests/test_log_correlation.py` | ✅ (3 novos nomes de logger no parametrizado) |
| `apps/campaigns/tests/test_intelligence_api.py` + `test_intelligence_integration.py` | ✅ 42/42 (1 corrigido, 0 novos falsos) |
| Intelligence Engine `tests/test_intelligence_endpoint.py` | ✅ 7/7 (1 novo) |
| Intelligence Engine suite completa | ✅ 198/198 |
| Backend Core, apps directamente afectadas (campaign_actions, reports, content, campaigns, integrations_bridge, core) | ✅ 393 passed, 4 failed (as 4 são as mesmas falhas pré-existentes já sinalizadas em `task_e252710e`, Prompt 03 — nenhuma nova) |
| Backend Core, suite completa | Ver §5 |

---

## 5. Suite completa do Backend Core

Executada como diligência extra (não estritamente exigida pela checklist,
que pede só "pytest relevante"). Resultado: **as únicas falhas são as 4
já conhecidas e sinalizadas no Prompt 03** (3 em `test_dependency_health.py`
por causa do literal `"8002"` vs. `"8202"`; 1 em `test_intelligence_payload.py`
por causa de uma data fixa desactualizada) — nenhuma falha nova introduzida
por esta iteração.

---

## 6. Exemplo de fluxo real (ids redigidos apenas onde fazia sentido — os
IDs aqui são de dados de dev/teste, não sensíveis)

```text
Cliente HTTP  →  X-Request-ID: e2e-smoke-trace-002
                 POST /api/v1/reports/  (Backend Core, porta 8100)

Backend Core:
  event=report_created report_id=297bdedb-... correlation_id=e2e-smoke-trace-002
  event=job_created job_id=ac6d5b56-... request_id=e2e-smoke-trace-002
  internal_call start job_id=ac6d5b56-... request_id=e2e-smoke-trace-002
  internal_call ok    job_id=ac6d5b56-... request_id=e2e-smoke-trace-002 status=202
  event=job_submitted job_id=ac6d5b56-... request_id=e2e-smoke-trace-002

Content Renderer (porta 8202):
  job.accepted        job_id=ac6d5b56-... request_id=e2e-smoke-trace-002
  job.scheduled        job_id=ac6d5b56-... request_id=e2e-smoke-trace-002
  render.started       job_id=ac6d5b56-... request_id=e2e-smoke-trace-002
  report.render_started/finished  request_id=e2e-smoke-trace-002
  render.completed     request_id=e2e-smoke-trace-002
  callback.started/completed      request_id=e2e-smoke-trace-002

Backend Core (callback):
  event=callback_received  job_id=ac6d5b56-... request_id=e2e-smoke-trace-002
  event=callback_processed job_id=ac6d5b56-... request_id=e2e-smoke-trace-002 status=completed

Confirmado por leitura directa da BD:
  Report.correlation_id       == "e2e-smoke-trace-002"
  ExternalJobReference.request_id == "e2e-smoke-trace-002"
```

Repetido com sucesso equivalente para `CampaignAction` (`campaign_action_created`),
`MediaKit` (`media_kit_created`) e `ContentPackRequest`
(`content_pack_request_created`), e para a chamada síncrona ao Intelligence
Engine (`intelligence.request_received`/`intelligence.request_completed`,
logados no próprio Intelligence Engine com o mesmo id).

---

## 7. Greps de segurança executados

| Padrão | Ficheiros verificados | Resultado |
|---|---|---|
| `INTERNAL_API_TOKEN=`, `SECRET_KEY=`, `PASSWORD=`, `AWS_SECRET`, `ACCESS_KEY=`, `PRIVATE_KEY=`, `Bearer <token real>`, `x-internal-token: <valor>` | Todos os ficheiros alterados/criados nesta iteração | ✅ 0 ocorrências reais (só placeholders herdados de iterações anteriores, já validados) |
| `X-Internal-Token`/`Authorization` nos logs reais do smoke (Backend Core, Intelligence Engine, Content Renderer) | Ficheiros de log do smoke real (§6) | ✅ 0 ocorrências |
| Payload integral da intelligence nos novos logs | `intelligence.py` (IE), `campaigns/views.py` (BC) | ✅ só `request_id`/`workspace_id`, nunca `data`/`analysis`/`recommendations` |
| `scripts/check-forbidden-ports.ps1` | Repositório | ✅ OK |

---

## 8. Lacunas restantes

- **Agregação/retenção centralizada de logs** continua inexistente (fora do
  escopo desta iteração e desta fase, ver arquitectura §11).
- **Frontend não lê nem envia `X-Request-ID`** — não é necessário para o
  objectivo desta fase (correlação é uma preocupação de observabilidade
  backend-a-backend), mas fica registado como possível extensão futura se
  algum dia for útil correlacionar cliques do browser com operações
  server-side. `CORS_EXPOSE_HEADERS` não foi alterado (o cabeçalho de
  resposta `X-Request-ID` já está lá, só não é exposto a `fetch()` no
  browser via CORS — decisão deliberada de não expandir o contrato do
  frontend sem necessidade concreta).
- **Endpoints individuais do Intelligence Engine** (`/analysis`, `/scoring`,
  `/recommendations`, `/moments`) não ganharam logging de `request_id` —
  só o endpoint composto `/intelligence/campaign`, que é o único
  efectivamente chamado pelo Backend Core hoje. Registar nos outros só faz
  sentido se/quando passarem a ser chamados directamente.
- **`recommendation_ref`** continua posicional (limitação da fase 04, fora
  do escopo desta tarefa).

Nenhuma destas lacunas foi deixada por a implementação ser "demasiado
grande" — a implementação ficou completa dentro do âmbito pedido; estas são
extensões conscientemente fora do âmbito, não trabalho por fazer.

---

## 9. Riscos

| Risco | Severidade | Estado |
|---|---|---|
| Novos logs de criação silenciosamente não emitidos por falta de config `LOGGING` | Alto (encontrado e corrigido nesta própria iteração) | **Mitigado** — corrigido + teste de regressão dedicado |
| `X-Request-ID` malformado/malicioso injectado por um cliente | Baixo | **Mitigado** — validado por regex restritivo (`[A-Za-z0-9_-]{1,64}`); qualquer coisa fora disso gera um id novo em vez de propagar o valor do cliente |
| Migrations aditivas (4 novos campos `correlation_id` + `public_url` já existente) aumentarem ligeiramente o tamanho das tabelas | Muito baixo | Aceitável; campos `blank=True`, sem impacto funcional |
| Correlation-id não chegar a cenários fora de pedidos HTTP (comandos de gestão, retries) | Baixo, intencional | Esses casos continuam a gerar um id novo tal como antes — comportamento inalterado e documentado |

---

## 10. Próximo passo recomendado

Avançar para **Prompt 06 (STG-PRE-006 — Health e logs)**: validar o
healthcheck agregado com utilizador staff em runtime, confirmar cobertura
de DB/IE/Content Renderer/storage, e consolidar os sinais operacionais
(IE down, Renderer down, callback failed) à luz do correlation-id agora
disponível — os logs de falha podem agora ser correlacionados com a mesma
precisão que os de sucesso.
