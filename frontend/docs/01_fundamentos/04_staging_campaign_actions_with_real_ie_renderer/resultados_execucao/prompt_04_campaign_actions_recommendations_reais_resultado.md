# Prompt 04 — CampaignActions a partir de recommendations reais

**Data:** 2026-07-01
**Fase:** `04_staging_campaign_actions_with_real_ie_renderer` (STG-CA-004, Incremento 1)
**Âmbito:** converter recommendations reais do IE em CampaignActions persistentes. Sem alteração de código de produto.
**Estado de execução:** `executado`

---

## 1. Resumo objectivo

Todas as recommendations usadas vieram do **IE real** (`source=engine`). A partir delas foram criadas **8 CampaignActions** cobrindo os **6 action_types** do contrato, mais deduplicação e retry-após-terminal:

- `manual_task`, `mark_reviewed`, `report_request` na **mesma** recommendation (rec0) → múltiplos tipos por recommendation ✅
- `dismiss` + `media_kit_request` na mesma recommendation (rec1) ✅
- `content_pack` na rec2 (com content pack activo) ✅
- Deduplicação `ref + action_type` → **HTTP 400** ✅
- Retry após `cancelled` → nova action do mesmo tipo+ref permitida ✅
- `recommendation_snapshot` mínimo e seguro (allowlist; sem payload integral do IE) ✅
- `source=recommendation`, `related_*` correctos, reload confirma persistência ✅

---

## 2. Recommendations usadas (reais, `source=engine`)

| # | action | priority | confidence | recommendation_ref derivado |
|---|---|---|---|---|
| 0 | `improve_smart_link` | high | 0.7 | `…ed7d:i0:improve-smart-link` |
| 1 | `create_media_kit` | medium | — | `…ed7d:i1:create-media-kit` |
| 2 | `create_release_post` | medium | — | `…ed7d:i2:create-release-post` |

### recommendation_ref (tarefa 3)
As recommendations reais **não têm `id`** (nem `title`/`type`). O ref foi derivado **exactamente como o frontend** (`deriveRecommendationRef`): sem id → `{campaignId}:i{index}:{slug(action)}`. É um **fallback defensivo documentado** (correlação frontend, não identificador persistente do backend). O `id` real seria preferido se existisse — não existe neste IE.

---

## 3. Actions criadas

| # | action_type | rec/ref | CampaignAction id | status | related_* |
|---|---|---|---|---|---|
| a | `manual_task` | rec0 | `10c25899…` | pending | — |
| b | `mark_reviewed` | rec0 | `5c3ae0c2…` | completed | — |
| c | `report_request` | rec0 | `d43a54ad…` | pending | `related_report=bfb89d9b…` |
| e | `dismiss` | rec1 | `341638f3…` | dismissed | — (reason="Not relevant this cycle") |
| f | `media_kit_request` | rec1 | `8704ed82…` | pending | `related_media_kit=64e8b948…` |
| g | `content_pack` | rec2 | `e5595831…` | pending | `related_content_pack_request=a94ade15…` |
| h1 | `manual_task` | retry-ref | `1352dc66…` | cancelled | — |
| h3 | `manual_task` | retry-ref | `db817d16…` | pending | — |

Artefactos proprietários criados primeiro (fluxo de duas escritas):
- `POST /reports/` → `bfb89d9b…` status `queued`
- `POST /media-kits/` → `64e8b948…` status `draft`
- `POST /content-pack-requests/` → `a94ade15…` status `queued`

### Confirmações do contrato (tarefa 10)
- **id próprio** por CampaignAction ✅ (distinto do artefacto)
- **recommendation_ref** persistido ✅
- **recommendation_snapshot** mínimo e seguro ✅ (ver §6)
- **action_type** correcto ✅
- **status** correcto ✅ (mark_reviewed→completed, dismiss→dismissed, restantes→pending)
- **priority** enum ✅ (`high`/`medium` normalizados)
- **source=recommendation** ✅ em todas
- **related_*** presente quando aplicável ✅

---

## 4. Endpoints chamados (todos no Backend Core, `:8100/api/v1`)

```
POST /campaigns/{id}/intelligence/            (obter recommendations reais)
POST /reports/                                 (artefacto report)
POST /media-kits/                              (artefacto media kit)
POST /content-pack-requests/                   (artefacto content pack)
POST /campaign-actions/                        (todas as actions)
POST /campaign-actions/{id}/cancel/            (lifecycle cancel)
GET  /campaign-actions/?campaign={id}          (reload/persistência)
```

O frontend consome exactamente estes endpoints via `apiClient` central (base `http://localhost:8100/api/v1`); nenhuma chamada directa a IE/Renderer, nenhum `X-Internal-Token` (confirmado nos Prompts 01/03 e imutável nesta iteração).

---

## 5. Payloads resumidos (sem secrets)

CampaignAction (ex.: `report_request` rec0):
```json
{
  "campaign": "<campaign_id>",
  "action_type": "report_request",
  "title": "Report from rec0",
  "priority": "high",
  "source": "recommendation",
  "recommendation_ref": "<cid>:i0:improve-smart-link",
  "recommendation_snapshot": { "action": "...", "reason": "...", "priority": "high", "confidence": 0.7 },
  "related_report": "<report_id>"
}
```
- `workspace` **não** é enviado no body (read-only; injectado por `X-Workspace-ID`). Confirmado: a resposta ecoa o workspace correcto sem o cliente o enviar.
- `dismiss` inclui `dismiss_reason`; `mark_reviewed`/`dismiss` **não** enviam `status` (o backend define completed/dismissed).

---

## 6. recommendation_snapshot mínimo e seguro

Snapshot persistido (rec0 report_request):
```json
{"confidence":0.7,"priority":"high","reason":"Smart links are configured but show no activity; improve them.","action":"improve_smart_link"}
```
- Apenas campos da **allowlist** presentes na recommendation (`action`, `reason`, `priority`, `confidence`).
- **Não** contém `explanations`, `moments`, `analysis`, `scores` nem o payload integral do IE — verificado programaticamente (`False`).
- O serializer do backend rejeita chaves sensíveis e impõe limite de 64 KB (defesa adicional).

---

## 7. related_* (tarefa 10)

| CampaignAction | related preenchido | artefacto | estado artefacto |
|---|---|---|---|
| report_request | `related_report` | Report | queued |
| media_kit_request | `related_media_kit` | MediaKit | draft |
| content_pack | `related_content_pack_request` | ContentPackRequest | queued |

Cada relação passou a validação de compatibilidade (`_ALLOWED_RELATED_FIELDS`) e de workspace/campaign.

---

## 8. Deduplicação (tarefa 13)

Segunda `report_request` com o **mesmo** `recommendation_ref` (rec0) + mesmo `action_type`:
```
POST /campaign-actions/ -> HTTP 400
{ "recommendation_ref": ["An active action of this type already exists for this recommendation."] }
```
A deduplicação activa é por `workspace + campaign + recommendation_ref + action_type` nos estados activos (`pending`/`in_progress`/`completed`).

---

## 9. Múltiplos tipos por recommendation (tarefa 12)

- **rec0** (`improve-smart-link`): `manual_task` (pending) + `mark_reviewed` (completed) + `report_request` (pending) → 3 tipos coexistem ✅
- **rec1** (`create-media-kit`): `dismiss` (dismissed) + `media_kit_request` (pending) ✅

Tipos diferentes na mesma recommendation não se bloqueiam entre si.

---

## 10. Retry após estado terminal (tarefa 14)

```
manual_task (ref retry) -> pending
POST /campaign-actions/{id}/cancel/ -> cancelled
manual_task (mesmo ref) -> HTTP 201 (pending)   # permitido: cancelled não é estado activo
```
Confirma que `failed`/`dismissed`/`cancelled` não bloqueiam nova tentativa do mesmo tipo+ref (dedup só considera `pending`/`in_progress`/`completed`).

---

## 11. Reload / persistência (tarefa 11)

`GET /campaign-actions/?campaign={id}&page_size=100` após criação → **count=16** (8 do Prompt 16 + 8 desta iteração). Todas as 8 novas actions presentes com ids próprios, `recommendation_ref`, `source=recommendation`, `status` e `related_*` correctos, ordenação estável. A persistência sobrevive a novo GET (equivalente a reload).

---

## 12. Validações executadas

| Validação | Resultado |
|---|---|
| API real via Backend Core (6 action_types) | ✅ todos criados |
| Snapshot mínimo/seguro (sem payload integral) | ✅ |
| Deduplicação ref+type | ✅ 400 |
| Múltiplos tipos por recommendation | ✅ |
| Retry após cancelled | ✅ |
| Reload/persistência | ✅ count=16 |
| Fronteira frontend → só Backend Core | ✅ (contrato inalterado; apiClient central) |
| `pnpm test/lint/build` | N/A — nenhum código de produto alterado nesta iteração |
| `python manage.py check` | N/A — backend não alterado (só dados criados via API) |

---

## 13. Limitações

| Limitação | Impacto |
|---|---|
| Recommendations reais **sem `id`** → `recommendation_ref` posicional+conteúdo | Médio. Estável por chamada, mas se a ordem/action mudar entre execuções do IE, o ref muda. Aceitável como correlação frontend; documentado. |
| Artefactos ficam em `queued`/`draft` (renderer ainda em `EXTERNAL_JOBS_DRY_RUN=true`) | Esperado — avanço real do job/output é STG-CA-005. |
| Validação visual no browser não executada | Diferida para STG-CA-009. |
| Dados de teste acumulam no SQLite dev (16 actions + artefactos) | Sem impacto em dev local. |

---

## 14. Ficheiros alterados

| Ficheiro | Operação |
|---|---|
| `frontend/docs/.../resultados_execucao/prompt_04_...resultado.md` | **criado** (este relatório) |
| `backend_core/db.sqlite3` | 8 CampaignActions + 1 Report + 1 MediaKit + 1 ContentPackRequest criados via API real |

Nenhum código de produto (frontend ou backend) foi alterado. Nenhum segredo consta deste relatório.

---

## 15. Próximo passo recomendado

Avançar para **STG-CA-005 (Content Renderer real)**:
1. Criar `content_renderer/.env` com o **mesmo** `INTERNAL_API_TOKEN` dos outros serviços e reiniciar o CR (sair do modo `ALLOW_INSECURE_EMPTY_TOKEN`).
2. Desactivar `EXTERNAL_JOBS_DRY_RUN=false` no `backend_core/.env` e reiniciar o Backend Core.
3. Criar report/media kit/content pack e confirmar submissão real do job (`/jobs`), evolução de estados (`queued`→`submitted`→`running`→`completed`), callback CR→Django e `related_*`/output final.

> Serviços a correr em background: Backend Core (8100), IE (8201), Content Renderer (8202, modo inseguro), Frontend (5200).
