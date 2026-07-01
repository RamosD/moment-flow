# FE-012 — Painéis de assets, reports e media kits

**Fase:** Frontend Foundation & Campaign War Room MVP
**Componente alvo:** `frontend`
**Data:** 2026-06-26
**Tipo:** Painéis de outputs da War Room (content outputs / reports / media kits) com dados reais

---

## 0. Sumário executivo

- **Os três endpoints existem** no Backend Core e suportam filtro **`?campaign={id}`** → **dados reais são usados** (não são placeholders).
- Criados hooks **`useCampaignContentOutputs`**, **`useCampaignReports`**, **`useCampaignMediaKits`** (TanStack Query, key com `workspaceId + campaignId`).
- Completados/criados os widgets **`CampaignAssetsPanel`** (content outputs), **`CampaignReportsPanel`** (reports) e **`CampaignMediaKitsPanel`** (media kits, **novo**), integrados na War Room.
- **Status dos outputs** apresentado com Badge colorido (queued/processing/completed/failed/… → cor; `unknown` quando ausente).
- **Loading / error / empty** em cada painel; **só Backend Core** — nenhuma chamada directa ao Content Renderer; sem geração de assets.
- **Verificado em browser** (rede stubbed): dados reais, empty e error (503 → "Service unavailable") nos painéis.
- **`pnpm build` e `pnpm lint` passam** (exit 0, 0 avisos).

---

## 1. Confirmação de contrato

| Endpoint | Filtro | Resposta | Header |
| --- | --- | --- | --- |
| `GET /api/v1/content-outputs/` | `?campaign={id}` (+ `status`, `output_type`, `page_size`…) | `PaginatedContentOutputList` | `X-Workspace-ID` (obrigatório) |
| `GET /api/v1/reports/` | `?campaign={id}` (+ `status`, `report_type`…) | `PaginatedReportList` | `X-Workspace-ID` |
| `GET /api/v1/media-kits/` | `?campaign={id}` (+ `status`…) | `PaginatedMediaKitList` | `X-Workspace-ID` |

Conclusão: **content outputs, reports e media kits por campanha são expostos pelo Backend Core** via endpoints próprios (não vêm no campaign detail). Logo, **dados reais** — não foram necessários placeholders de "dados ainda não expostos". As entidades (`ContentOutput`, `Report`, `MediaKit`) já existiam do FE-006.

---

## 2. Camada de dados (entities)

| Entidade | Ficheiros novos | Hook |
| --- | --- | --- |
| `content-output` | `content-output-api.ts`, `useCampaignContentOutputs.ts` | `useCampaignContentOutputs(workspaceId, campaignId)` |
| `report` | `report-api.ts`, `useCampaignReports.ts` | `useCampaignReports(workspaceId, campaignId)` |
| `media-kit` | `media-kit-api.ts`, `useCampaignMediaKits.ts` | `useCampaignMediaKits(workspaceId, campaignId)` |

- Query keys: `['content-outputs'|'reports'|'media-kits', workspaceId, 'by-campaign', campaignId]` → cache por workspace+campanha; invalidados na troca de workspace (predicate do FE-008).
- `enabled: !!workspaceId && !!campaignId`; `select → results`. **Só Backend Core** (`apiClient`).
- Camadas respeitadas: hooks em `entities/*` recebem `workspaceId`/`campaignId` por argumento (sem `entity → feature`).

---

## 3. Widgets

| Widget | Dados | Conteúdo do item | Status |
| --- | --- | --- | --- |
| `CampaignAssetsPanel` | content outputs | título (`title`/`output_type`) + `output_type · format` | Badge `status` |
| `CampaignReportsPanel` | reports | `title` + `report_type` | Badge `status` |
| `CampaignMediaKitsPanel` *(novo)* | media kits | `title` + `N items` | Badge `status` |

- Cada widget chama o seu hook (props `workspaceId`/`campaignId` vindas da página) e trata **loading / error / empty / lista**.
- Lista partilha estilos via `shared/styles/output-list.module.css` (reutilizado pelos 3, sem duplicação).
- **Status → cor** via novo helper **`statusToBadgeVariant`** em `shared/ui` (queued→neutral, processing/rendering/…→warning, completed/generated/published→success, failed/cancelled/expired→danger, etc.; ausente → `unknown` neutral).

---

## 4. War Room

A página `CampaignWarRoomPage` passou a renderizar os três painéis num grid responsivo (`repeat(auto-fit, minmax(280px, 1fr))`), passando `workspaceId` + `campaignId`:
```
[outputsGrid] [Content outputs] [Reports] [Media kits]
```
Mantêm-se independentes da intelligence — renderizam mesmo que a intelligence falhe (resiliência do FE-011 preservada).

---

## 5. Restrições respeitadas

- **Nenhuma chamada directa ao Content Renderer** — a única origem de rede é o `apiClient` (Backend Core). Os painéis são **read-only** (consulta), sem geração de assets.
- **Sem mocks falsos em runtime** — dados reais dos endpoints; empty states honestos quando não há dados.

---

## 6. Verificação em browser (rede stubbed — sem backend)

Login → workspace → War Room, com `apiClient`/hooks reais e endpoints stubbed:

| Verificação | Resultado |
| --- | --- |
| Content outputs com **dados reais** | ✅ "IG Launch" (completed), "tiktok_video" (processing) |
| Reports com **dados reais** | ✅ "Weekly Recap" / "Campaign Report" / queued |
| Media kits com **dados reais** | ✅ "Press Kit" / "3 items" / published |
| Status badges (completed/processing/queued/published) | ✅ |
| **Empty** (content outputs / media kits) | ✅ "No content outputs yet" / "No media kits yet" |
| **Error** (reports 503) | ✅ "Service unavailable" + **Try again** |

### Achado de ambiente (importante)
O browser do preview reporta `navigator.onLine === false`. Como o TanStack Query usa `networkMode: 'online'` por omissão, **as retentativas de erros 5xx ficam pausadas** (`fetchStatus: 'paused'`) e o painel fica em "loading" sem chegar ao `ErrorState`. **É artefacto do ambiente, não bug da app** — respostas 200 (sem retry) renderizam bem. Forçando `onlineManager.setOnline(true)` + `dispatchEvent(new Event('online'))`, a retentativa retoma e o erro **503 → "Service unavailable" + Try again** renderiza correctamente (verificado). Em browser real online, o comportamento é normal. (Guardado em memória para futura verificação.)

> Notas: a screenshot tool manteve timeouts de infra (validação por DOM). Navegação via `router.navigate()`.

---

## 7. Validações

| Verificação | Comando | Resultado |
| --- | --- | --- |
| Lint | `pnpm lint` | ✅ exit 0 — 0 avisos |
| Build | `pnpm build` | ✅ exit 0 |
| Fluxo real (stubbed) | preview + DOM | ✅ §6 |

> `dist/` removido.

---

## 8. Critérios de aceitação — verificação

| Critério (FE-012) | Estado |
| --- | --- |
| War Room tem área para assets/reports/media kits | ✅ 3 painéis |
| Dados reais usados se endpoints existirem | ✅ endpoints existem → dados reais |
| Placeholders honestos se não existirem | N/A (endpoints existem) — empty states honestos |
| Não há chamada directa ao Renderer | ✅ só `apiClient` |
| Build/lint passam ou limitações documentadas | ✅ ambos passam |

---

## 9. Ficheiros criados/alterados

**Novos (entities):** `content-output/{content-output-api.ts,useCampaignContentOutputs.ts}`, `report/{report-api.ts,useCampaignReports.ts}`, `media-kit/{media-kit-api.ts,useCampaignMediaKits.ts}` (+ index actualizados).
**Novos (shared):** `shared/ui/statusVariant.ts` (+ export), `shared/styles/output-list.module.css`.
**Novo widget:** `widgets/campaign-media-kits-panel/{CampaignMediaKitsPanel.tsx,index.ts}`.
**Reescritos:** `widgets/campaign-assets-panel/CampaignAssetsPanel.tsx`, `widgets/campaign-reports-panel/CampaignReportsPanel.tsx` (placeholders → dados reais).
**Alterados:** `pages/campaign-war-room/CampaignWarRoomPage.tsx` (+ `.module.css`) — 3 painéis com props.

---

## 10. Notas para os prompts seguintes

- **FE-013:** tratamento transversal (sessão expirada, PermissionDenied/ServiceUnavailable dedicados). O `statusToBadgeVariant` e o `ErrorState` já cobrem grande parte.
- **Detalhe de output:** abrir um content output / report / media kit (download/preview) depende de endpoints de detalhe/export (`/content-outputs/{id}/export/` existe) — fora do escopo desta fase.
- **Filtros:** os endpoints suportam `status`/`output_type`/`report_type` — UI de filtros numa fase posterior.
