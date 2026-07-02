# Prompt 07 — Estados operacionais (artefacto/job/CampaignAction) — Resultado

**Data:** 2026-07-02
**Fase:** `05_staging_operacionalizacao_pre_producao` (STG-PRE-007)
**Âmbito:** alinhar estados de `Report`/`MediaKit`/`ContentPackRequest`/`ContentOutput`/`ExternalJobReference`/`CampaignAction` para que uma falha do renderer seja sempre visível — nunca um falso sucesso, nunca uma espera infinita silenciosa.
**Estado de execução:** `executado` — encontrada e corrigida uma divergência real (não hipotética) de produção: falhas de submissão síncrona do job (renderer inacessível no momento do pedido) deixavam o artefacto preso no estado inicial para sempre, e um segundo bug real de sobrescrita de dados foi descoberto e corrigido enquanto validava a correcção.

---

## 1. Resumo objectivo

A fase 04 já tinha documentado que uma falha reportada pelo *callback* do
renderer é tratada correctamente: `Report`→`failed`, `MediaKit`→continua
`draft` mas com `metadata.generation_status="failed"`, `ContentPackRequest`→
`failed`+créditos libertados. O que a fase 04 **não cobriu** é o caminho mais
comum de indisponibilidade em staging: o renderer estar em baixo **no
momento da submissão do job**, antes de qualquer callback existir.

Inspeccionando `integrations_bridge/services.py`, confirmei que esse caminho
(`_mark_failed`/`_mark_timeout`, chamados a partir de `_submit_job` quando o
`InternalServiceClient` levanta `InternalClientError`/`InternalClientTimeout`)
só transitava o `ExternalJobReference` para `failed`/`timeout` — **nunca**
chamava o dispatcher de callback nem os handlers do `reports`/`content`. Como
o renderer nunca chegou a receber o job, nenhum callback real chegaria alguma
vez para o resgatar. Resultado real, reproduzido com um cliente HTTP mockado
a levantar `InternalServiceUnavailable`:

- `Report` ficava `queued` para sempre, com o job já `failed`;
- `MediaKit` ficava `draft` para sempre, **sem sequer o rasto em metadata**
  que a falha via callback já produzia (pior que o caso já conhecido da
  fase 04);
- `ContentPackRequest` ficava `queued` para sempre — e os créditos reservados
  **nunca eram libertados** (fuga de crédito real, não só um problema de UX).

## 2. Decisão tomada

Reutilizar exactamente o mesmo handler que já trata a falha via callback
(`apply_report_generation_callback`, `apply_media_kit_generation_callback`,
`apply_content_generation_callback`) também a partir do caminho de falha de
submissão síncrona — em vez de inventar um segundo caminho de "falha". Isto
mantém as duas fontes de falha (callback real vs. submissão nunca chegou ao
destino) a produzir exactamente o mesmo resultado no artefacto, sem duplicar
lógica de notificação/auditoria/crédito.

Deliberadamente **não alterado**:
- o lifecycle do `CampaignAction` (continua inteiramente independente do
  artefacto — ver secção 4);
- o enum `MediaKit.Status` (continua sem `FAILED` próprio; a falha continua
  em `metadata`, agora alcançável também pelo caminho de submissão).

## 3. Matriz de estados (antes → depois desta correcção)

| Fluxo | Cenário | `ExternalJobReference` | Artefacto — antes | Artefacto — depois |
|---|---|---|---|---|
| `report_generation` | Renderer inacessível na submissão | `failed`/`timeout` | `queued` (para sempre) | `failed` + `metadata.error` |
| `report_generation` | Callback `completed` | `completed` | `completed` + asset | *(sem alteração)* |
| `report_generation` | Callback `failed` | `failed` | `failed` + `metadata.error` | *(sem alteração)* |
| `media_kit_generation` | Renderer inacessível na submissão | `failed`/`timeout` | `draft`, sem rasto algum | `draft` + `metadata.generation_status="failed"` + `metadata.error` |
| `media_kit_generation` | Callback `failed` | `failed` | `draft` + metadata | *(sem alteração)* |
| `content_generation` | Renderer inacessível na submissão | `failed`/`timeout` | `queued` (para sempre), créditos presos | `failed` + `error_message` + créditos libertados |
| `content_generation` | Callback `completed`/`partially_completed`/`failed` | idem | outputs/créditos/notificação correctos | *(sem alteração)* |
| Retry (`retry_external_job`) | Job antigo `failed`/`timeout`/`cancelled`/`expired` | novo job (job antigo preservado) | inalterado pelo retry em si | inalterado — se o novo job falhar de novo na submissão, aplica-se a mesma correcção (idempotente: `_notify_once` e `idempotency_key` de crédito impedem duplicação) |
| `CampaignAction` | Qualquer um dos acima | — | `pending`/`in_progress` continuam **independentes** do artefacto | agora diagnosticável via `related_artifact_status` (API), sem alterar o lifecycle |

`ContentOutput` não tem uma divergência própria nesta iteração: já era
marcado `failed` em massa por `_handle_failed` quando o job falha via
callback; esse caminho não foi tocado.

## 4. Divergência que fica documentada, não corrigida (por desenho)

**`CampaignAction pending`/`in_progress` com artefacto `failed`** continua
possível e é **intencional nesta fase**: o backlog proíbe alterar o
lifecycle do `CampaignAction` sem uma decisão explícita de produto (ex.:
deveria uma falha do artefacto transitar automaticamente o `CampaignAction`
para `failed`? Deveria isso ser uma acção manual do utilizador a partir do
badge de estado?). Isso é uma decisão de produto, não uma correcção técnica —
fica registada como próximo passo (secção 6).

O que mudou é que essa divergência deixou de ser **invisível**: adicionei um
campo só de leitura, `related_artifact_status`, ao
`CampaignActionSerializer` (`{"type": "report"|"media_kit"|
"content_pack_request", "status": "<status real do artefacto>"}` — para
`MediaKit` deriva `"failed"` de `metadata.generation_status` quando presente,
já que o modelo não tem esse estado próprio). O `CampaignActionsPanel.tsx`
mostra-o como um segundo badge ao lado do estado da própria acção, sem tocar
em nenhuma transição existente.

## 5. Bug real encontrado durante a validação (não hipotético)

Ao validar a correcção acima com um teste que criava um `Report`/`MediaKit`/
`ContentPackRequest` real, submetia o job com o cliente HTTP mockado a falhar,
e verificava o estado final: **o artefacto continuava sem a informação de
falha**, apesar do handler ser chamado com sucesso (confirmado com prints de
depuração isolando a chamada). Causa raiz: `_submit_external_job`
(`reports/services.py`) e `_submit_content_generation_job`
(`content/services.py`) guardam uma referência ao objecto **antes** de
submeter o job e, já depois de `create_and_submit_external_job` devolver,
fazem `entity.metadata = {**(entity.metadata or {}), "external_job_id": ...}`
+ `entity.save(...)` usando essa cópia **em memória desactualizada** — que
não sabe nada da escrita que a nova propagação de falha acabou de fazer numa
instância diferente do mesmo registo. Esse `save()` **reescrevia** a
metadata, apagando `generation_status`/`error` que tinham acabado de ser
gravados.

Corrigido com um `entity.refresh_from_db()` imediatamente antes desse merge
final, nos dois pontos. Isto tem um benefício adicional: a mesma instância
`entity`/`report`/`media_kit`/`request` é a que a view devolve na resposta
HTTP (`perform_create` → `serializer.save()` → mesmo objecto reserializado);
sem o refresh, um pedido `POST /reports/` que falhasse a submissão de forma
síncrona devolveria `status: "queued"` ao cliente, quando a base de dados já
diz `"failed"`.

## 6. Ficheiros alterados

Backend:
- `backend_core/apps/integrations_bridge/services.py` — `_propagate_submission_failure` + `_entity_failure_handlers`, chamados a partir de `_mark_failed`/`_mark_timeout`.
- `backend_core/apps/reports/services.py` — `entity.refresh_from_db()` antes do merge final de metadata em `_submit_external_job`.
- `backend_core/apps/content/services.py` — mesma correcção em `_submit_content_generation_job`.
- `backend_core/apps/campaign_actions/serializers.py` — campo `related_artifact_status` (+ helper `_related_artifact_status`).
- `backend_core/apps/campaign_actions/views.py` — `select_related` no `get_queryset` para o novo campo não custar N+1 queries.

Testes:
- `backend_core/apps/reports/tests/test_report_media_kit_jobs.py` — estendido `test_report_submission_failure_is_traceable`; adicionado `test_media_kit_submission_failure_is_traceable`.
- `backend_core/apps/content/tests/test_content_generation_job.py` — estendido `test_client_failure_marks_job_failed_and_links`.
- `backend_core/apps/campaign_actions/tests/test_api.py` — nova classe `TestRelatedArtifactStatus` (3 testes).

Frontend:
- `frontend/src/entities/campaign-action/model.ts` — tipo `RelatedArtifactStatus` + campo em `CampaignAction`.
- `frontend/src/entities/campaign-action/helpers.ts` — `relatedArtifactStatusLabel`/`relatedArtifactStatusVariant`.
- `frontend/src/entities/campaign-action/index.ts` — export dos novos helpers.
- `frontend/src/widgets/campaign-actions-panel/CampaignActionsPanel.tsx` — badge do estado do artefacto relacionado.
- `frontend/tests/campaign-actions.test.mjs` — teste unitário dos novos helpers.

## 7. Validações

- `python manage.py check` — 0 problemas.
- `pytest apps/integrations_bridge apps/reports apps/content apps/campaign_actions` — 308 passed.
- `pytest` (suite completa do backend_core) — 594 passed, 1 failed, 3 skipped
  (12m17s). O único falhado, `test_intelligence_payload.py::
  TestRichCampaign::test_all_sections_populated_and_json_safe`, é uma
  falha **pré-existente e não relacionada** (usa uma data fixa
  `2026-06-25` desactualizada face ao relógio real) já rastreada em tarefa
  própria (`task_1d40d090`, aberta na fase anterior) — confirma zero
  regressões desta correcção. Os 3 `skipped` exigem o Intelligence Engine
  real a correr (`RUN_REAL_IE=1`), não relacionados com esta fase.
- `pnpm`/`npx tsc -b` (build) — sem erros.
- `npx eslint .` — sem avisos/erros.
- `npm test` (frontend) — 15/15 passed (14 pré-existentes + 1 novo).
- Nenhum falso sucesso introduzido: a correcção só marca artefactos como `failed`, nunca `completed`/`generated` sem output real.
- Nenhuma alteração de retry: `retry_external_job` não foi tocado; o comportamento idempotente de crédito/notificação (`idempotency_key`, `_notify_once`) já existente absorve uma segunda falha na mesma entidade sem duplicar efeitos.

## 8. Riscos

- **`related_artifact_status` é derivado, não persistido** — reflecte sempre o valor mais recente na leitura (correcto), mas não gera evento de auditoria próprio; é só um espelho de leitura.
- **MediaKit continua sem estado `FAILED` próprio** — a heurística (`metadata.generation_status == "failed"` ⇒ reportar `"failed"`) é uma convenção acordada nas fases 04/05, não um valor de enum garantido pelo schema; um consumidor externo que ignore metadata não vê a falha através do campo `status` puro do MediaKit.
- **CampaignAction ainda pode ficar `pending` indefinidamente com artefacto `failed`** — decisão de produto pendente (secção 4), não um bug.
- **`entity.refresh_from_db()` acrescenta uma query por submissão de job** — custo desprezável (uma criação de Report/MediaKit/ContentPackRequest já faz várias queries), mas vale registar para quem otimizar este caminho no futuro.

## 9. Próximo passo recomendado

1. Decisão de produto explícita (fora desta fase técnica): o `CampaignAction`
   deve reagir automaticamente a um artefacto `failed` (ex.: auto-transição
   para `failed`, ou um CTA de "Retry" na UI que dispare
   `retry_external_job`)? Isto é o STG-PRE-007 remanescente que o backlog
   já assinalava como decisão de produto, não técnica.
2. Se o produto decidir que `MediaKit` precisa de um estado `FAILED` real
   (não só metadata), abrir isso como um item de backlog técnico próprio —
   requer migration + auditoria de todos os consumidores do enum
   (frontend `MediaKitStatus`, filtros, dashboards).
3. Seguir para STG-PRE-008 (RBAC/UX mínimo) conforme a ordem recomendada do
   backlog da fase.
