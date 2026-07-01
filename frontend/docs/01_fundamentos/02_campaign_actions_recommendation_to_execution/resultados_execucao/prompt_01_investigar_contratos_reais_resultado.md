# Resultado — Prompt 01: Investigar contratos reais (CA-001)

> Fase: `02_campaign_actions_recommendation_to_execution`
> Backlog de referência: `01_backlog.md` (CA-001)

---

## Execução 2026-06-30 (Iteração 01)

### Estado da execução
**executado** (investigação concluída; nenhum código runtime alterado)

### Resumo objectivo

**Conclusão: Resultado B — Backend Core suporta PARCIALMENTE.**

O Backend Core **não** expõe nenhuma entidade nem endpoint "Campaign Action" / "Task" / "Action Item",
e **não persiste recommendations**. Porém **expõe endpoints reais de execução**
(content-pack-requests, content-outputs, reports, media-kits) que podem ser criados a partir
do contexto de uma campanha. Logo:

- O ciclo `recommendation → gerar artefacto de execução` é **parcialmente implementável de forma real**
  (content pack / report / media kit ligados à campanha).
- O conceito de **Campaign Action como entidade persistente rastreável** (status próprio, recommendation_ref,
  mark_reviewed/dismiss) **não tem suporte no Backend Core** e exigiria backlog complementar.

Recomendação imediata: **não** implementar uma entidade `campaign-action` falsa no frontend.
Implementar apenas o que mapeia a contratos reais e marcar honestamente o resto como indisponível.

---

### Evidências recolhidas (fonte: código real do repositório)

#### 1. Endpoints existentes (`backend_core/schema.yml`, 9319 linhas, OpenAPI)

Apps montadas em `backend_core/config/urls.py`:
`accounts(auth)`, `workspaces`, `core`, `catalogue`, `campaigns`, `content`, `links`,
`billing`, `reports`, `notifications`, `integrations_bridge`.

| Conceito do backlog | Endpoint real | Métodos | Existe? |
|---|---|---|---|
| **Campaign Actions** | — | — | ❌ **Não existe** |
| **Tasks / Action Items** | — | — | ❌ **Não existe** |
| **Recommendations (persistidas)** | — | — | ❌ Não persistidas (ver ponto 2) |
| Intelligence (gera recommendations) | `POST /api/v1/campaigns/{id}/intelligence/` | POST | ✅ (recalculado, sem persistência) |
| **Content packs** | `GET /api/v1/content-packs/` (+ `/{id}/`) | GET (read-only) | ✅ catálogo, só leitura |
| **Content pack requests** (≈ generation job) | `GET,POST /api/v1/content-pack-requests/` | GET, POST | ✅ **criável** |
| **Content outputs** | `GET,POST,PATCH /api/v1/content-outputs/` | GET, POST, PATCH | ✅ **criável/editável** |
| **Reports** | `GET,POST,PATCH /api/v1/reports/` (+ `report-sections`) | GET, POST, PATCH | ✅ **criável/editável** |
| **Media kits** | `GET,POST,PATCH /api/v1/media-kits/` (+ `media-kit-items`) | GET, POST, PATCH | ✅ **criável/editável** |
| **Generation jobs** (dedicado) | — | — | ❌ Não dedicado; ContentPackRequest cumpre papel via `status` |
| Callback de jobs (interno) | `POST /api/v1/internal/jobs/callback/` | POST | ⚠️ **Interno (X-Internal-Token) — proibido ao frontend** |
| **Audit / Event logs** | — | — | ❌ App `audit` existe mas **não está montada em urls** (sem API pública) |
| Notifications | `GET /api/v1/notifications/` (+ read/read-all) | GET, POST | ✅ (não é action) |

> Confirmação de ausência: nenhuma rota `campaign-actions`, `actions`, `tasks` ou `action-items`
> na lista completa de paths do `schema.yml`. Nenhuma `class *Action* / *Task*` em qualquer
> `apps/*/models.py` (única ocorrência de "Action"/"Task" é `TransactionType` em billing, irrelevante).

#### 2. Intelligence / Recommendations — recalculadas, NÃO persistidas

`schema.yml` (linha ~1525), descrição do endpoint:
> "Builds the campaign data bundle and calls the Intelligence Engine synchronously, returning
> analysis, scores, grade, moments, recommendations and summary. **Read-only enrichment (no persistence).**"

`apps/campaigns/serializers.py` — `CampaignIntelligenceResultSerializer`:
- `recommendations = serializers.ListField(required=False)` — **lista livre, sem shape fixo, sem `id`**.

Consequências confirmadas (resolve decisões pendentes do backlog):
- **CA-PDEC-001**: Campaign Actions **não** existem no Backend Core.
- **CA-PDEC-003**: Recommendations **não têm `id` estável** persistido → obrigatório `recommendation_ref` defensivo
  (derivado de `campaignId + índice + title/action/type`), tal como o backlog antecipa (CA-RSK-002).
- **CA-PDEC-005**: `mark_reviewed` / `dismiss` **não podem persistir** estado no backend
  (não há entidade onde gravar) → não persistir estado falso.

#### 3. Endpoints de execução — capacidades reais (o que É possível)

- `ContentPackRequest` (`apps/content/models.py:212`): FK `campaign` (obrigatório, CASCADE),
  `content_pack` (obrigatório), `track`/`artist` opcionais, `metadata` **JSON gravável**,
  workflow de `status` (draft→queued→…→completed/failed) gerido pelo backend.
  - Serializer (`apps/content/serializers.py:125`): campos graváveis no POST =
    `campaign, track, artist, content_pack, metadata`. `status`, `requested_by`, timestamps são **read-only**.
  - Filtro: `ContentPackRequestFilter.fields = ["campaign", "content_pack", "status"]` → **filtrável por campanha**.
- `ContentOutput` (`models.py:285`): FK `campaign`, FK opcional `content_pack_request`, `status`/`visibility`.
  Filtro por `campaign`. POST + PATCH.
- `Report` / `MediaKit` (`apps/reports/models.py:19/133`): ambos `WorkspaceOwnedModel`, FK `campaign`,
  filtro `campaign` exact. POST + PATCH.

> **Importante**: nenhum destes models tem FK/campo `recommendation`. A única forma de associar uma
> recommendation a um artefacto é via o campo `metadata` (JSON livre) — associação **não-relacional,
> não-consultável como contrato**, e apenas em ContentPackRequest/ContentOutput (não confirmado em Report/MediaKit;
> verificar serializers de reports antes de assumir `metadata` gravável lá).

#### 4. Permissões e erros

- Viewsets de execução usam `WorkspaceScopedRBACViewSet` + JWT (`jwtAuth`) e exigem header `X-Workspace-ID`.
  Erros esperados: **401** (sessão/JWT inválido), **403** (sem permissão RBAC no workspace),
  **404** (campanha/recurso fora do workspace), **422/400** (validação — ex.: campanha de outro workspace,
  via `validate_campaign`/`_ensure_same_workspace`), **502/503** (intelligence indisponível —
  `IntelligenceUnavailable` / `IntelligenceUpstreamFailure` em `apps/campaigns/views.py`).
- Catálogo (`content-packs`, `templates`) é **read-only** (`GlobalOrWorkspaceReadViewSet`).

---

### Mapa Action Type (MVP backlog) → suporte real

| `action_type` (CA-003) | Suporte Backend Core | Como |
|---|---|---|
| `content_pack` | ✅ **Real** | `POST /content-pack-requests/` (campaign + content_pack + metadata) |
| `report_request` | ✅ **Real** | `POST /reports/` (campaign) |
| `media_kit_request` | ✅ **Real** | `POST /media-kits/` (campaign) |
| `manual_task` | ❌ **Sem suporte** | Não há entidade task/action |
| `asset_request` | ❌ **Sem suporte** | Não há endpoint de asset request genérico |
| `mark_reviewed` | ❌ **Sem suporte** | Recommendation não persistida |
| `dismiss` | ❌ **Sem suporte** | Recommendation não persistida |

---

### Divergências backlog ↔ código (código prevalece)

1. Backlog hipotetiza `GET/POST /api/v1/campaign-actions/` e `POST /campaigns/{id}/actions/` (secção 9.2).
   **Não existem.** Prevalece o código.
2. Backlog lista `content_pack`, `report_request`, `media_kit_request` como tipos de acção.
   Estes mapeiam a endpoints de **execução** diferentes — **não** a uma entidade Action unificada.
   Não há um recurso único que represente "a acção"; há os artefactos gerados.
3. Backlog assume possível relação persistente `recommendation → action`. **Não há suporte relacional**;
   apenas `metadata` JSON livre, sem garantia de contrato.

**Risco de implementação errada**: Médio-Alto se se tentar criar a entidade genérica `campaign-action`.
**Não há bloqueio total** porque os 3 caminhos de execução reais (content pack / report / media kit) permitem
entregar valor sem inventar persistência. Por isso: **não bloquear a fase**, mas **reduzir escopo ao real**.

---

### Decisão recomendada para a fase

**Resultado B (suporte parcial) + necessidade de backlog backend complementar (CA-PDEC-006 = SIM).**

Caminho recomendado para os próximos prompts:
1. **CA-002/CA-003**: NÃO criar entidade `campaign-action` com persistência fictícia.
   Modelar como "**Recommendation Execution**": cada acção é a criação de um artefacto real
   (content-pack-request / report / media-kit). Tipos de UI limitados aos 3 suportados.
2. **CA-006/CA-007**: botão "Create action" abre modal que escolhe apenas entre
   `content_pack` / `report` / `media_kit`. `manual_task`, `asset_request`, `mark_reviewed`, `dismiss`
   → estados **disabled** com copy honesta ("not supported by Backend Core yet").
3. **CA-008 (painel)**: alimentar o painel "Campaign Actions" lendo `content-pack-requests`,
   `reports` e `media-kits` filtrados por `campaign` (agregação no frontend, read-only) —
   é a única fonte real de "acções já criadas".
4. **CA-009 (estado da recommendation)**: associação `recommendation → artefacto` apenas via `metadata`
   (best-effort, não-persistente como contrato) → documentar limitação; usar `recommendation_ref` derivado.
5. **CA-010 (reviewed/dismiss)**: marcar como **indisponível** (não persistir estado falso).
6. **Backlog backend complementar** (recomendado): criar app/endpoint `campaign-actions` com
   FK `campaign` + `recommendation_ref` + `status` + `related_*_id`, se a rastreabilidade for requisito do piloto.

---

### Ficheiros criados ou alterados
- **Criado**: `frontend/docs/01_fundamentos/02_campaign_actions_recommendation_to_execution/resultados_execucao/` (pasta).
- **Criado**: este ficheiro (`prompt_01_investigar_contratos_reais_resultado.md`).
- Nenhum ficheiro de código runtime foi alterado.

### Validações executadas e resultado
- ✅ Não foi usado browser.
- ✅ Não foram executados servidores.
- ✅ Apenas comandos de leitura/inspecção (grep/find/cat/read) sobre `backend_core`.
- ✅ Não foi feito troubleshooting de ambiente.
- ✅ Código priorizado sobre backlog; divergências registadas acima.

### Pendências, riscos e próximo passo recomendado
- **Pendente verificar antes de CA-002**: se o serializer de `Report`/`MediaKit` expõe `metadata` gravável
  (foi confirmado em ContentPackRequest/ContentOutput; reports/media-kits a confirmar).
- **Risco CA-RSK-001 (Alto)** confirmado materializado: não há Campaign Actions API → seguir Resultado B + backlog backend.
- **Risco CA-RSK-002 (Alto)** confirmado: recommendations sem `id` → `recommendation_ref` obrigatório.
- **Próximo passo**: avançar para CA-002 com escopo reduzido ao real (3 tipos de execução), OU,
  se rastreabilidade de acções for requisito firme do piloto, primeiro abrir backlog complementar
  no Backend Core para uma `CampaignAction` persistente. Decisão de produto pendente (CA-PDEC-002/006).
