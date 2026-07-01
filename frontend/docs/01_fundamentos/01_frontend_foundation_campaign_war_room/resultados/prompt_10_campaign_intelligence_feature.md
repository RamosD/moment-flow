# FE-010 — Campaign Intelligence feature

**Fase:** Frontend Foundation & Campaign War Room MVP
**Componente alvo:** `frontend`
**Data:** 2026-06-26
**Tipo:** Feature `campaign-intelligence` (hook + componentes + orquestrador)

---

## 0. Sumário executivo

- Criada a feature **`src/features/campaign-intelligence`**: hook **`useCampaignIntelligence`** + 9 componentes + um orquestrador (`CampaignIntelligencePanel`).
- Consome **`POST /api/v1/campaigns/{id}/intelligence/`** (sem body) **apenas via Backend Core** (`apiClient`). **Nenhuma chamada directa ao Intelligence Engine.**
- **Decisão técnica:** POST exposto com **`useQuery`** (é semanticamente uma leitura — enrichment read-only, sem persistência); query key inclui **workspaceId + campaignId**.
- Trata **todos os estados**: loading, success, empty/insufficient, 401/403/404/422/502/503/network — com **UI própria para 502/503** ("Service unavailable").
- Trata **source**: `engine` ("Live engine") e `dry_run` ("Dry run").
- **Warnings** visíveis mas calmos; **explanations** colapsáveis. **Não** calcula scores; **não** transforma recommendations em acções.
- **Verificado em browser** (rede stubbed): todos os blocos renderizam; dry_run e 503 confirmados.
- **`pnpm build` e `pnpm lint` passam** (exit 0, 0 avisos).

---

## 1. Endpoint e decisão técnica

| Item | Valor |
| --- | --- |
| Endpoint | `POST /api/v1/campaigns/{id}/intelligence/` |
| Request body | **nenhum** |
| Headers | `Authorization: Bearer` + `X-Workspace-ID` (injectados) |
| Resposta | `200` `CampaignIntelligenceResponse` |
| Consumo | `apiClient.post(...)` → **só Backend Core** |

**`useQuery` vs `useMutation`:** apesar de ser HTTP POST, o endpoint é descrito como *read-only enrichment (no persistence)* e não tem body — semanticamente é uma **leitura**. A War Room quer o resultado **no mount, cacheado, com retry em 5xx transitório e refrescável** → `useQuery` é a escolha certa. `staleTime: 2min` evita re-disparar o engine a cada navegação. (Documentado no hook.)

Query key: `['campaign-intelligence', workspaceId, campaignId]` → cache por workspace+campanha; invalidado na troca de workspace (predicate do FE-008 abrange tudo excepto `'workspaces'`).

---

## 2. Estrutura da feature

| Ficheiro | Papel |
| --- | --- |
| `intelligence-api.ts` | `fetchCampaignIntelligence(campaignId)` (POST, sem body) |
| `useCampaignIntelligence.ts` | Query hook + `intelligenceKeys` |
| `intelligence-format.ts` | Helpers defensivos (humanizeKey, gradeVariant, noteToMessage, momentTitle, etc.) |
| `IntelligenceSummary.tsx` | Source (engine/dry_run) + engine + summary + generated_at |
| `GradeBadge.tsx` | Grade como Badge colorido |
| `ScoreGrid.tsx` | Grelha de scores (só primitivos; nested ignorado) |
| `MomentsList.tsx` / `MomentItem.tsx` | Lista de moments |
| `RecommendationsList.tsx` / `RecommendationItem.tsx` | Lista de recommendations |
| `WarningsPanel.tsx` | Warnings (Alert "warning" calmo) |
| `ExplanationsPanel.tsx` | Explanations (`<details>` colapsável) |
| `CampaignIntelligencePanel.tsx` | Orquestrador: hook + estados + composição |
| `index.ts` | API pública |

### Decisão de camadas
O orquestrador recebe **`workspaceId` por prop** (passado pela página War Room via `useWorkspace()`), em vez de importar a feature de workspace — mantém **features → entities + shared** (sem feature→feature). Padrão consistente com FE-009.

---

## 3. Render defensivo (lacuna de contrato G1/G2 do FE-006)

`moments`/`recommendations` são arrays **não-tipados** e `analysis`/`scores` objectos livres. A UI lida com isso:

- **Títulos** por fallback: `title → label → name → type → 'Moment'/'Recommendation'`.
- **Priority** aceita número (`Priority 2`) ou string (`high`).
- **ScoreGrid** mostra só valores **primitivos** (number/string/boolean); objectos aninhados são **ignorados** (não polui a grelha). Números float → 2 casas; boolean → Yes/No.
- **Notes** (warnings/explanations): mensagem por fallback `message → detail → text → title → description → code`.
- Campos em falta nunca quebram o render (tudo opcional + `readString`).

**Não há cálculo de scores no frontend** — só apresentação. **Recommendations não viram acções** (display-only).

---

## 4. Estados tratados

| Estado | UI |
| --- | --- |
| sem workspace | `EmptyState` "No workspace selected" |
| loading | `LoadingState` "Analyzing campaign…" |
| 401 | `ErrorState` → "Session expired" (+ logout global via FE-007) |
| 403 | `ErrorState` → "Access denied" |
| 404 | `ErrorState` → "Not found" |
| 422 | `ErrorState` → "Invalid request" |
| **502/503** | `ErrorState` → **"Service unavailable"** + Try again |
| network | `ErrorState` → "Connection problem" |
| empty/insufficient | summary + warnings + `EmptyState` "Not enough data yet" + explanations |
| success | summary + warnings + grade/scores + moments + recommendations + explanations |

`ErrorState error={error}` deriva a copy via `resolveErrorPreset` (FE-005), por isso 502/503 têm UI própria sem código extra. Retry via `refetch()`.

### Source
- `engine` → Badge **"Live engine"** (success).
- `dry_run` → Badge **"Dry run"** (info) — sinaliza que não são dados de produção, sem alarmar.

---

## 5. Verificação em browser (rede stubbed — sem backend)

Login → workspace → War Room, com `apiClient`/hooks **reais** e `POST /intelligence/` stubbed:

| Verificação | Resultado |
| --- | --- |
| `/campaigns/c1/war-room` consome intelligence | ✅ painel completo renderizado |
| Source **engine** | ✅ "Live engine momentflow-ie · v1.2.0" |
| Summary | ✅ texto apresentado |
| **Warnings** visíveis | ✅ "1 thing to keep in mind — Engagement data is 24h delayed." |
| **Grade** | ✅ "Overall grade B" |
| **Scores** | ✅ Momentum 0.82, Reach 1234, Engagement Rate 0.07, Trending Yes; **nested object ignorado** |
| **Moments** | ✅ "Playlist spike" (Priority 1) + desc; "Blog mention" (high) |
| **Recommendations** | ✅ "Boost paid social" (Priority 2); "Pitch to radio" (fallback de `action`) |
| **Explanations** colapsável | ✅ "Why these results? (1)" |
| Source **dry_run** (c2) | ✅ Badge "Dry run", grade A; moments/recs vazios → mensagens honestas |
| **503** (c3) | ✅ "Service unavailable… Please try again shortly." + **Try again** |
| Erros runtime na consola | ✅ apenas logs **sanitizados** de query 503 (`status=503 code=-`, sem token) |

> Navegação fiável via `router.navigate()` (instância real do router). A screenshot tool manteve-se instável (infra) — validação por inspecção de DOM/consola.

---

## 6. Validações

| Verificação | Comando | Resultado |
| --- | --- | --- |
| Lint | `pnpm lint` | ✅ exit 0 — 0 avisos |
| Build | `pnpm build` | ✅ exit 0 — 154 módulos |
| Fluxo real (stubbed) | preview + DOM/console | ✅ §5 |

> Nota build: corrigido um `TS2345` em `ScoreGrid` — o type-guard precisava de ser um **predicado de tuplo** (`(entry): entry is [string, string|number|boolean]`) para narrow do valor destruturado. `dist/` removido.

---

## 7. Critérios de aceitação — verificação

| Critério (FE-010) | Estado |
| --- | --- |
| Endpoint consumido via Backend Core | ✅ `apiClient.post` |
| Não há chamada directa ao Intelligence Engine | ✅ só Backend Core |
| Scores apresentados | ✅ ScoreGrid |
| Grade apresentada | ✅ GradeBadge |
| Moments apresentados | ✅ MomentsList |
| Recommendations apresentadas | ✅ RecommendationsList |
| Warnings/explanations visíveis | ✅ WarningsPanel + ExplanationsPanel |
| Erros 502/503 com UI própria | ✅ "Service unavailable" + retry |
| Build/lint passam ou limitações documentadas | ✅ ambos passam |

---

## 8. Ficheiros criados/alterados

**Novos (`features/campaign-intelligence`):** `intelligence-api.ts`, `useCampaignIntelligence.ts`, `intelligence-format.ts`, `intelligence.module.css`, `IntelligenceSummary.tsx`, `GradeBadge.tsx`, `ScoreGrid.tsx`, `MomentsList.tsx`, `MomentItem.tsx`, `RecommendationsList.tsx`, `RecommendationItem.tsx`, `WarningsPanel.tsx`, `ExplanationsPanel.tsx`, `CampaignIntelligencePanel.tsx`, `index.ts`.
**Alterado:** `pages/campaign-war-room/CampaignWarRoomPage.tsx` (renderiza o `CampaignIntelligencePanel`).
**Removido:** `features/campaign-intelligence/.gitkeep`.

---

## 9. Notas para os prompts seguintes

- **FE-011 (War Room MVP):** o `CampaignIntelligencePanel` já está integrado na página; falta expandir o layout à volta — Campaign Header (dados de `useCampaign`), e placeholders para Content Outputs / Reports / Media Kits. Os componentes individuais estão exportados para composição mais fina, se desejado.
- **FE-012:** assets/reports/media kits têm endpoints próprios filtráveis por `campaign` (confirmar no schema).
- **Contrato real do engine:** quando moments/recommendations estabilizarem, apertar os tipos (G1) e ajustar os fallbacks de título/priority.
- **Refresh manual:** o `ErrorState` já dá retry; pode-se adicionar um botão "Refresh" no header da War Room ligado a `refetch` numa fase posterior.
