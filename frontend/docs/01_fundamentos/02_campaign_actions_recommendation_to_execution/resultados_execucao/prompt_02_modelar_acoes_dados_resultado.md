# Resultado — Prompt 02: Modelar acções + camada de dados (CA-002 / CA-003)

> Fase: `02_campaign_actions_recommendation_to_execution`
> Backlog de referência: `01_backlog.md` (CA-002, CA-003)
> Depende de: `prompt_01_investigar_contratos_reais_resultado.md` (Resultado B — suporte parcial)

---

## Execução 2026-06-30 (Iteração 01)

### Estado da execução
**executado**

### Resumo objectivo

Com base no Prompt 01 (Resultado B — suporte parcial: **não** existe entidade/endpoint
`campaign-actions`, recommendations **não** persistidas, mas existem 3 endpoints reais de execução),
foi criada a entity `entities/campaign-action` como **projeção frontend + dispatcher de criação**
sobre os contratos reais — **sem persistência falsa e sem inventar endpoints**.

Mapeamento real implementado:

| `CampaignActionType` | Endpoint real | Métodos usados | Campos obrigatórios |
|---|---|---|---|
| `content_pack` | `/content-pack-requests/` | GET, POST | `campaign`, `content_pack` |
| `report_request` | `/reports/` | GET, POST, PATCH | `report_type` (default `campaign_report`), `title` |
| `media_kit_request` | `/media-kits/` | GET, POST, PATCH | `artist`, `title` |
| `manual_task`, `asset_request`, `mark_reviewed`, `dismiss` | — | — | **sem suporte** (capability `supported:false`, copy honesta) |

Decisões de modelação (alinhadas ao código real):

- **Sem entidade unificada inventada**: `CampaignAction` é explicitamente documentado como projeção
  read-only sobre 3 artefactos reais; `id` é o id do artefacto subjacente, não um id de acção dedicado.
- **Pendência do Prompt 01 resolvida**: `metadata` é **gravável** em Report, MediaKit e ContentPackRequest
  (confirmado nos serializers). A ligação `recommendation → acção` é guardada *best-effort* em
  `metadata.recommendation_ref` / `metadata.action_source` / `metadata.action_title` — **convenção
  frontend, não contrato relacional** (documentado no código).
- **RecommendationRef defensivo** (CA-RSK-002 / CA-PDEC-003): recommendations não têm `id` estável →
  chave derivada de `campaignId + índice + title/action/type`, marcada como não-identificador de backend.
- **Update parcial honesto**: só `report_request` e `media_kit_request` expõem PATCH; `content_pack`
  (content-pack-request) é imutável (status read-only) → `updateCampaignAction` lança erro claro em vez
  de fingir sucesso. Capability `updatable` reflecte isto.
- **Listagem resiliente**: `fetchCampaignActions` lê os 3 endpoints em paralelo (`Promise.allSettled`);
  falha de um recurso (ex.: 403) não apaga o painel — só lança erro se **todos** falharem.
- **Arquitectura respeitada**: a entity importa apenas de `@/shared/*` (tipos + `BadgeVariant` type-only);
  **não** importa outras entities (shapes raw locais), **não** importa features, **não** chama IE/Renderer,
  **não** envia `X-Internal-Token` (cliente partilhado bloqueia).
- Query keys incluem `workspaceId` + `campaignId`; mutations invalidam o agregado `campaign-actions` e as
  listas base relevantes (`reports` / `media-kits`) já usadas na War Room.

> Nota: estes são os **primeiros hooks de mutation** do repositório (não existia `useMutation` antes).

### Ficheiros criados ou alterados

Criados (todos em `frontend/src/entities/campaign-action/`):
- `model.ts` — `CampaignAction`, `CampaignActionType`, `SupportedCampaignActionType`,
  `CampaignActionStatus`, `CampaignActionSource`, `CampaignActionArtifactKind`,
  `CAMPAIGN_ACTION_CAPABILITIES`, `isSupportedCampaignActionType`,
  payloads `CreateCampaignActionInput` (union) + `UpdateCampaignActionInput`.
- `recommendation-ref.ts` — `RecommendationRef`, `RecommendationLike`, `deriveRecommendationRef`.
- `helpers.ts` — `normalizeActionStatus`, `campaignActionStatusLabel`,
  `campaignActionStatusVariant`, `campaignActionTypeLabel`.
- `query-keys.ts` — `campaignActionKeys`.
- `campaign-action-api.ts` — projeções + `fetchCampaignActions`, `createCampaignAction` (dispatcher),
  `updateCampaignAction`.
- `useCampaignActions.ts` — query agregada.
- `useCreateCampaignAction.ts` — mutation de criação + invalidações.
- `useUpdateCampaignAction.ts` — mutation de update (report/media-kit) + invalidações.
- `index.ts` — barrel público da entity.

Nenhum ficheiro existente foi alterado; nenhum endpoint inventado; nenhum mock runtime.

### Validações executadas e resultado

| Validação | Comando | Resultado |
|---|---|---|
| Lint | `pnpm lint` (`eslint .`) | ✅ **passou** (sem erros) |
| Type-check + Build | `pnpm build` (`tsc -b && vite build`) | ✅ **passou** (184 módulos, build em ~3.1s) |
| Browser | — | ✅ Não usado (não aplicável; camada de dados sem superfície renderizada) |
| Segurança | revisão manual | ✅ Sem IE/Renderer, sem `X-Internal-Token`, sem chamadas directas a serviços internos |

### Pendências, riscos ou próximo passo recomendado

- **Constrangimentos de criação a tratar na UI (CA-007)**:
  - `media_kit_request` exige `artist` → derivar de `campaign.artist` (disponível no model frontend).
  - `content_pack` exige `content_pack` (id de catálogo) → o diálogo terá de oferecer escolha de
    content pack (`GET /content-packs/`); sem isso, não é criável.
  - `report_request` exige `report_type` → default `campaign_report` aplicado, editável na UI.
- **Risco CA-RSK-003 (duplicação)**: a associação recommendation→acção é só via `metadata` (não-consultável
  como contrato) → o matching em CA-009 será best-effort; documentar limitação. Não há deduplicação no backend.
- **Risco CA-RSK-006 (expectativa de automação)**: criar acção = criar um *pedido*/artefacto (status gerido
  pelo backend), não execução imediata → a copy da UI deve distinguir "create" de "execute".
- **Próximo passo recomendado**: CA-004 (UI base: Dialog/Select/Textarea/FormField) e depois CA-005/CA-006/CA-007
  (draft a partir de recommendation + affordance no RecommendationItem + diálogo Create Action),
  usando `CAMPAIGN_ACTION_CAPABILITIES` para desactivar honestamente os tipos sem suporte.
