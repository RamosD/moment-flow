# Prompt 04 — Fluxo principal recommendation-to-action na War Room

> Fase: `02_campaign_actions_recommendation_to_execution`
> Backlog de referência: `01_backlog.md` (CA-006, CA-007, CA-008, CA-009, CA-012)
> Relatórios anteriores: prompt_01, prompt_02, prompt_03

---

## Execução 2026-06-30 (Iteração 01)

### Estado da execução

**Concluído** (fluxo principal recommendation → action implementado com contratos
reais; lint e build verdes; sem mocks runtime; sem browser, conforme instrução).

### Resumo objectivo

Implementado o ciclo mínimo de execução na War Room usando **apenas os 3 endpoints
reais** do Backend Core (confirmados no prompt_01): `POST /reports/`,
`POST /media-kits/`, `POST /content-pack-requests/`. Cada recommendation passa a ter
uma affordance "Create action" que abre um modal de confirmação, submete um payload
real, trata loading/sucesso/erro (401/403/404/422/502/503) e invalida as queries
relevantes. Foi adicionado o painel "Campaign Actions" na War Room (projecção
agregada dos 3 artefactos por campanha) e o estado de execução por recommendation
(badge "convertida") para evitar duplicação óbvia.

Como o Backend Core **não** tem entidade Campaign Action nem relação persistente
recommendation→action, a associação é best-effort via `recommendation_ref` gravado
em `metadata` (convenção do frontend, não contrato relacional) — limitação
documentada abaixo e em código.

### Mapeamento ao backlog

| Item | Estado | Nota |
|---|---|---|
| CA-006 — affordance no RecommendationItem | ✅ | Slot `action` injectado pela página; intelligence feature mantém-se desacoplada |
| CA-007 — modal "Create Action" | ✅ | `CreateActionFromRecommendationDialog`, payload real, 422 por campo |
| CA-008 — painel Campaign Actions | ✅ | `widgets/campaign-actions-panel`, agrega 3 endpoints, loading/error/empty |
| CA-009 — estado da recommendation | ✅ (best-effort) | Match por `recommendation_ref`; limitação documentada |
| CA-012 — permissões e erros | ✅ | `resolveErrorPreset` + field errors; sem stack/tokens |
| CA-010 — mark reviewed/dismiss | ⛔ Indisponível | Sem suporte backend (recommendation não persistida) — não implementado, sem persistência falsa |
| CA-011 — ligação a outputs existentes | ⏳ Fora deste prompt | A relação só existe via metadata; deixado para iteração futura |

### Decisões técnicas

- **Camadas respeitadas**: a feature `campaign-actions` importa apenas `shared` +
  `entities`. Não importa `campaign-intelligence`. A ligação visual é feita via
  render-prop: a página injecta `renderAction(recommendation, index)` em
  `CampaignRecommendationsPanel` → `RecommendationsList` → `RecommendationItem`
  (slot `action: ReactNode`). Assim a intelligence feature continua sem conhecer
  campaign-actions.
- **content_pack exige escolher um pack do catálogo** (`content_pack` é FK
  obrigatória e não é derivável da recommendation). Criada entity read-only
  `entities/content-pack` (`GET /content-packs/?status=active`) para alimentar um
  `Select` no modal. `report_request` e `media_kit_request` derivam os campos
  obrigatórios (`campaign`, `artist`, `title`) directamente da campanha.
- **Sem duplicação (CA-009)**: se já existir uma action cujo
  `metadata.recommendation_ref` é igual ao ref derivado da recommendation, a UI
  mostra o estado (tipo + status) em vez do botão "Create action".
- **Erros**: 422 com `fieldErrors` mapeados por campo (`title`, `content_pack`);
  qualquer outro erro (incl. 401/403/404/502/503/network, ou 422 em campos
  derivados) é mostrado num `Alert` via `resolveErrorPreset` — nunca silencioso,
  nunca expõe stack/tokens.
- **priority/description** não são colunas reais nos 3 endpoints → gravados em
  `metadata` (`action_priority`, `action_description`), de forma honesta.

### Ficheiros criados

**Entity `entities/content-pack/` (catálogo read-only):**
- `model.ts` — tipo `ContentPack` (subset renderizável).
- `content-pack-api.ts` — `fetchContentPacks()` (`GET /content-packs/`).
- `useContentPacks.ts` — hook + `contentPackKeys` (enabled sob demanda).
- `index.ts`.

**`shared/ui/Input/` (campo de texto, faltava — necessário ao formulário):**
- `Input.tsx`, `Input.module.css`, `index.ts`. Export adicionado em
  `shared/ui/index.ts`.

**Feature `features/campaign-actions/`:**
- `recommendation-action-match.ts` — `matchRecommendationAction`,
  `recommendationExecutionState`, tipo `RecommendationExecutionState`.
- `RecommendationActionState.tsx` — badge de estado (tipo + status).
- `CreateActionFromRecommendationDialog.tsx` — modal de criação real.
- `CreateActionFromRecommendationButton.tsx` — affordance por recommendation.
- `campaign-actions.module.css`.

**Widget `widgets/campaign-actions-panel/`:**
- `CampaignActionsPanel.tsx`, `CampaignActionsPanel.module.css`, `index.ts`.

### Ficheiros alterados
- `features/campaign-actions/index.ts` — exports dos novos módulos.
- `features/campaign-intelligence/RecommendationItem.tsx` — slot opcional `action`.
- `features/campaign-intelligence/RecommendationsList.tsx` — prop `renderAction`.
- `features/campaign-intelligence/intelligence.module.css` — `.itemAction`.
- `widgets/campaign-recommendations-panel/CampaignRecommendationsPanel.tsx` —
  pass-through de `renderAction`.
- `pages/campaign-war-room/CampaignWarRoomPage.tsx` — `useCampaignActions`,
  `renderAction` com `CreateActionFromRecommendationButton`, e
  `CampaignActionsPanel` no layout.

### Validações executadas e resultado
- ✅ `pnpm lint` → `eslint .` sem erros nem avisos.
- ✅ `pnpm build` → `tsc -b && vite build`, 230 módulos transformados, build em
  ~3.5s, sem erros de tipo.
- ✅ Greps de segurança:
  - `internal-token` aparece **apenas** no guard de `shared/api/client.ts` e em
    docs/comentários — nunca como header enviado.
  - Sem referências a `intelligence_engine` / `content_renderer` / portas de
    serviços internos em `src/`. Todas as chamadas passam por `apiClient`
    (Backend Core).
- ➖ `python manage.py check` — **não aplicável**: não foi alterado nenhum
  contrato/código backend nesta iteração.
- ➖ Browser — **não usado**, conforme instrução ("Não usar browser por defeito").
  A validação visual interactiva fica como pendência (CA-014).

### Pendências, riscos e próximo passo recomendado

- **CA-014 (validação integrada real) pendente**: o fluxo não foi exercitado contra
  um Backend Core real a correr nem em browser. Recomenda-se validar login →
  workspace → campaign → War Room → criar action real (especialmente o caminho
  `content_pack`, dependente do catálogo) numa iteração dedicada.
- **Risco CA-RSK-002/CA-009 (limitação documentada)**: a associação
  recommendation→action é **best-effort**, baseada em `recommendation_ref`
  gravado em `metadata` (não há FK no backend). Só detecta actions criadas por
  este frontend; o ref derivado pode mudar se a recommendation mudar de
  título/posição entre cálculos da intelligence (recommendations são recalculadas,
  não persistidas). Documentado em `recommendation-action-match.ts`.
- **CA-010 (mark reviewed/dismiss)** continua **indisponível** por ausência de
  contrato backend — não persistir estado falso.
- **CA-011 (ligar actions a outputs existentes)** não abordado neste prompt; a
  única ligação possível hoje é via metadata.
- **CA-013 (documento de arquitectura da feature)** e **CA-015 (relatório final da
  fase)** continuam por fazer.
- Nota de produto (CA-PDEC-002/006): se a rastreabilidade de acções for requisito
  firme do piloto, recomenda-se backlog complementar no Backend Core para uma
  entidade `CampaignAction` persistente (FK campaign + recommendation_ref +
  status + related_*_id).
