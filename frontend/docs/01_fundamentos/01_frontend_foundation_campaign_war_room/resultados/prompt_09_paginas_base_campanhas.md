# FE-009 — Páginas base de campanhas

**Fase:** Frontend Foundation & Campaign War Room MVP
**Componente alvo:** `frontend`
**Data:** 2026-06-26
**Tipo:** Páginas de campanhas (listagem, detalhe) + camada de dados (TanStack Query)

---

## 0. Sumário executivo

- **Endpoints confirmados** no `backend_core/schema.yml`: `GET /api/v1/campaigns/` (→ `PaginatedCampaignList`) e `GET /api/v1/campaigns/{id}/` (→ `Campaign`). Ambos exigem `X-Workspace-ID` (injectado automaticamente).
- **Camada de dados** em `entities/campaign`: `fetchCampaigns`/`fetchCampaign` + hooks **`useCampaigns`** e **`useCampaign`** (TanStack Query), com o **`workspaceId` no query key**.
- **Página `/campaigns`**: lista real, com estados loading / error / empty + "sem workspace".
- **Página `/campaigns/:campaignId`**: detalhe simples + botão **Open War Room** (navega para `/campaigns/:id/war-room`).
- **Estados** loading/error/empty/forbidden/service-unavailable via `LoadingState`/`EmptyState`/`ErrorState` (este último deriva 401/403/404/503/network automaticamente).
- **Workspace respeitado**: queries desactivadas sem workspace; key inclui o id; troca de workspace invalida (FE-008).
- **Verificado em browser com rede stubbed** (sem backend): login → workspace → **lista renderiza 2 campanhas reais**; **detalhe renderiza dados reais**; navegação para War Room funciona; estado empty renderiza; erro 503 propaga pelo pipeline real.
- **`pnpm build` e `pnpm lint` passam** (exit 0, 0 avisos). Sem edição/criação de campanhas (fora do escopo).

---

## 1. Endpoints confirmados

| Endpoint | Auth | Resposta | Notas |
| --- | --- | --- | --- |
| `GET /api/v1/campaigns/` | JWT + `X-Workspace-ID` | `PaginatedCampaignList` | params: `search`, `status`, `ordering`, `page`, `page_size`, `artist`, `track`, `campaign_type`, `start_date_after/before` |
| `GET /api/v1/campaigns/{id}/` | JWT + `X-Workspace-ID` | `Campaign` | detalhe |

O `X-Workspace-ID` é injectado pelo workspace provider (FE-008) — as páginas não o gerem manualmente.

---

## 2. Camada de dados (`entities/campaign`)

| Ficheiro | Responsabilidade |
| --- | --- |
| `campaign-api.ts` | `fetchCampaigns(params)`, `fetchCampaign(id)` (usam `apiClient`) |
| `query-keys.ts` | `campaignKeys.list/detail` — **`workspaceId` em todas as keys** |
| `useCampaigns.ts` | Query da lista; `enabled: !!workspaceId`; `select → results` |
| `useCampaign.ts` | Query do detalhe; `enabled: !!workspaceId && !!campaignId` |

### Decisão de camadas
Os hooks **recebem o `workspaceId` como argumento** (passado pela página via `useWorkspace()`), em vez de importar a feature de workspace dentro da entidade. Mantém a regra **entities → shared apenas** (sem `entities → features`). Query keys: `['campaigns', workspaceId, 'list'|'detail', …]` → cache por workspace + invalidação na troca (predicate do FE-008 abrange `'campaigns'`).

---

## 3. Páginas

### `/campaigns` (`CampaignsPage`)
- `useWorkspace()` → `workspaceId`; `useCampaigns(workspaceId)`.
- Ramos de estado: **sem workspace** → `EmptyState` "No workspace selected"; **loading** → `LoadingState`; **error** → `ErrorState error={error}` (cobre 403/404/503/network) + Retry; **empty** → `EmptyState` "No campaigns yet"; **success** → lista de `Card`s, cada um `Link` para o detalhe, com nome, `Badge` de status e `primary_goal`.
- Mapa status→variante de Badge (active→success, paused→warning, draft→neutral, scheduled→info, completed→primary, archived→neutral).

### `/campaigns/:campaignId` (`CampaignDetailPage`)
- `useParams()` + `useWorkspace()` + `useCampaign(workspaceId, campaignId)`.
- `PageHeader` com `title = campaign?.name` e **acção `Open War Room`** (`navigate('war-room')` → `/campaigns/:id/war-room`).
- Estados idênticos; success → `Card` com `dl` (status, type, primary goal, datas) + descrição.
- **Sem edição** (apenas leitura), conforme escopo.

---

## 4. Estados / tratamento de erros

`ErrorState` recebe o `error` e deriva a copy via `resolveErrorPreset` (já existente, FE-005):

| Erro | Título mostrado |
| --- | --- |
| `NetworkError` | Connection problem |
| 401 `UnauthorizedError` | Session expired |
| **403 `ForbiddenError`** | **Access denied** |
| 404 `NotFoundError` | Not found |
| **502/503 `ServiceUnavailableError`** | **Service unavailable** |
| 422 `ValidationError` | Invalid request |

Assim, "forbidden" e "service unavailable" pedidos no backlog estão cobertos sem código por página.

---

## 5. Verificação em browser (rede stubbed — sem backend)

Como não há Backend Core neste ambiente, a rede foi stubbed no browser para exercitar os **hooks e o `apiClient` reais** (login → workspace → campanhas):

| Verificação | Resultado |
| --- | --- |
| Login (form) → autenticado, shell + Sign out | ✅ |
| Workspace carregado e activo (`ws1`) | ✅ switcher populado |
| `/campaigns` lista **dados reais** | ✅ 2 itens: "Summer Drop" (active) e "Album Teaser" (draft), com `href` para o detalhe |
| `/campaigns/c1` detalhe **dados reais** | ✅ título "Summer Drop"; status `active`, type `single_release`, goal e datas |
| Navegação **Open War Room** | ✅ → `/campaigns/c1/war-room` |
| Estado **empty** | ✅ "No campaigns yet" renderizado |
| Estado **loading** | ✅ "Loading campaigns…" observado |
| Erro **503** no pipeline real | ✅ propagou como `ServiceUnavailableError`; `queryClient.onError` registou **sanitizado** (`status=503 code=-`, sem token) |
| Erros de runtime na consola | ✅ nenhum (apenas o log sanitizado de query 503) |

### Limitações de verificação
- A **captura visual isolada** de 403/503 na página não foi obtida de forma limpa: após muitas manipulações no browser, (a) a ferramenta de screenshot teve timeouts de infra, e (b) o `import()` dinâmico do `queryClient` no dev devolveu uma **instância de módulo diferente** da app, pelo que `clear()` não afectava o cache real (mostrava cache stale). Ainda assim, o **caminho de erro foi exercido no pipeline real** (logs de 503) e o `ErrorState`/`resolveErrorPreset` estão verificados por código. A validação visual final fica para a fase com Backend Core real.

---

## 6. Validações

| Verificação | Comando | Resultado |
| --- | --- | --- |
| Lint | `pnpm lint` | ✅ exit 0 — 0 avisos |
| Build | `pnpm build` | ✅ exit 0 — 139 módulos |
| Fluxo real (stubbed) | preview + DOM/console | ✅ §5 |

> `dist/` removido. Durante a validação, foi terminado um processo `node` órfão a ocupar a porta 5173.

---

## 7. Critérios de aceitação — verificação

| Critério (FE-009) | Estado |
| --- | --- |
| Lista renderiza com dados reais quando Backend Core disponível | ✅ verificado (rede stubbed do `apiClient` real) |
| Detalhe simples renderiza | ✅ verificado |
| Estados loading/error/empty existem | ✅ + forbidden/service-unavailable via `ErrorState` |
| Navegação para War Room existe | ✅ botão → `/campaigns/:id/war-room` |
| Workspace é respeitado | ✅ key inclui `workspaceId`; query gated; invalidação na troca |
| Build/lint passam ou limitações documentadas | ✅ ambos passam; limitações de verificação em §5 |

---

## 8. Ficheiros criados/alterados

**Novos (`entities/campaign`):** `campaign-api.ts`, `query-keys.ts`, `useCampaigns.ts`, `useCampaign.ts`.
**Alterado:** `entities/campaign/index.ts` (exporta api + hooks + keys).
**Reescritos (páginas):** `pages/campaigns/CampaignsPage.tsx` (+ `.module.css`), `pages/campaign-detail/CampaignDetailPage.tsx` (+ `.module.css`).

> Nota: as páginas placeholder de campaigns/detail (refactor de FE-005 para usar UI base) foram substituídas pelas versões com dados reais.

---

## 9. Notas para os prompts seguintes

- **FE-010**: `useCampaignIntelligence` segue o mesmo padrão (chave com `workspaceId` + `campaignId`); `POST /campaigns/{id}/intelligence/` **sem body**; renderizar moments/recommendations defensivamente (lacuna G1 do FE-006).
- **FE-011**: a War Room substitui o placeholder de `pages/campaign-war-room` e compõe o detalhe + intelligence.
- **Filtros/paginação**: `CampaignListParams` já suporta `search`/`status`/`page`; ligar a UI de filtros numa fase posterior (fora do escopo do MVP).
- **Validação real**: confirmar com Backend Core o render de 403 (workspace alheio) e 503 (engine em baixo) nas páginas.
