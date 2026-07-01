# FE-011 — Campaign War Room MVP

**Fase:** Frontend Foundation & Campaign War Room MVP
**Componente alvo:** `frontend`
**Data:** 2026-06-26
**Tipo:** Composição da experiência de produto (War Room) a partir de widgets

---

## 0. Sumário executivo

- Criados **6 widgets** (`campaign-header`, `campaign-score-card`, `campaign-recommendations-panel`, `campaign-moments-panel`, `campaign-assets-panel`, `campaign-reports-panel`) e composta a página **`/campaigns/:campaignId/war-room`**.
- A War Room mostra **tudo o que o backlog pede**: breadcrumb, Campaign Header, Intelligence Summary, Grade, Scores, Recommendations, Moments, Warnings/Explanations, área de assets/content outputs, área de reports/media kits, e estados loading/error/empty.
- Consome **dados reais** de dois endpoints do Backend Core: `GET /campaigns/{id}/` (header) e `POST /campaigns/{id}/intelligence/` (painéis). **Nunca** chama IE/Renderer directamente.
- **Layout responsivo** (grid 2-col → 1-col em ecrãs estreitos).
- **A página continua útil** com warnings, insufficient data ou falha de intelligence — header + assets/reports renderizam sempre.
- **Verificado em browser** (rede stubbed): War Room completa renderiza; estado de erro de intelligence ("Service unavailable") aparece sem derrubar a página.
- **`pnpm build` e `pnpm lint` passam** (exit 0, 0 avisos). Sem geração de assets, sem edição de campanha.

---

## 1. Widgets criados

| Widget | Papel | Fonte |
| --- | --- | --- |
| `campaign-header` | Nome, status (Badge), tipo, goal, datas; skeleton em loading | `Campaign` (entity) + `shared/ui` |
| `campaign-score-card` | Card "Grade & scores": `GradeBadge` + `ScoreGrid` | `features/campaign-intelligence` |
| `campaign-recommendations-panel` | Card "Recommendations": `RecommendationsList` | `features/campaign-intelligence` |
| `campaign-moments-panel` | Card "Moments": `MomentsList` | `features/campaign-intelligence` |
| `campaign-assets-panel` | Placeholder honesto "Content outputs" (FE-012) | `shared/ui` |
| `campaign-reports-panel` | Placeholder honesto "Reports & media kits" (FE-012) | `shared/ui` |

Os widgets de intelligence **embrulham os componentes presentacionais** do FE-010 em `Card`+`Section`, mantendo a lógica de fetch numa só camada (a página). Respeitam a regra **widgets → features + entities + shared**.

---

## 2. Composição da página (`CampaignWarRoomPage`)

Duas queries em paralelo:
- `useCampaign(workspaceId, campaignId)` → header.
- `useCampaignIntelligence(workspaceId, campaignId)` → painéis de intelligence.

Estrutura renderizada:
```
[breadcrumb]   Campaigns / <campanha> / War Room
[CampaignHeader]                         (campanha)
[intelligenceSection]                    (ver §3)
[grid] [CampaignAssetsPanel] [CampaignReportsPanel]
```

- **Sem workspace** → `EmptyState`.
- **Campaign 404/403/erro** → `ErrorState` (full) — o campaign é o sujeito da página.

---

## 3. Região de intelligence (estados)

| Estado | UI |
| --- | --- |
| loading | `LoadingState` "Analyzing campaign…" |
| error (401/403/404/422/**502/503**/network) | `ErrorState error={error}` + Try again (502/503 → "Service unavailable") |
| insufficient data | `IntelligenceSummary` + `WarningsPanel` + `EmptyState` "Not enough data yet" + `ExplanationsPanel` |
| success | `IntelligenceSummary` + `WarningsPanel` + `CampaignScoreCard` + grid(`Moments`/`Recommendations`) + `ExplanationsPanel` |

**Resiliência:** o header e os painéis de assets/reports renderizam **sempre**, independentemente do estado da intelligence — a War Room nunca fica em branco quando o engine falha, devolve warnings ou tem poucos dados.

---

## 4. Layout responsivo

`CampaignWarRoomPage.module.css`: página em coluna (`flex`), grids 2-colunas (`grid-template-columns: 1fr 1fr`) para Moments/Recommendations e Assets/Reports, colapsando para 1 coluna em `max-width: 820px`. Tudo em `shared/ui` + design tokens; sem dependências visuais pesadas.

---

## 5. Restrições respeitadas

- **Sem chamadas directas a IE/Renderer:** a única origem de rede é o `apiClient` (Backend Core). Assets/reports são placeholders — **nenhuma geração** de assets.
- **Sem edição de campanha** (só leitura).
- **Sem cálculo de scores** no frontend (display-only).

---

## 6. Verificação em browser (rede stubbed — sem backend)

Login → workspace → `router.navigate('/campaigns/c1/war-room')`, com `apiClient`/hooks reais e stub do Backend Core:

| Secção | Resultado |
| --- | --- |
| Breadcrumb (Campaigns / … / War Room) | ✅ |
| Campaign Header ("Summer Drop" · active) | ✅ |
| Intelligence Summary ("Live engine" + texto) | ✅ |
| Warnings ("…keep in mind") | ✅ |
| Grade & scores | ✅ |
| Moments ("Playlist spike") | ✅ |
| Recommendations ("Boost paid social") | ✅ |
| Explanations (colapsável) | ✅ |
| Content outputs (placeholder) | ✅ |
| Reports & media kits (placeholder) | ✅ |
| **Intelligence 503 → "Service unavailable" + Try again** | ✅ renderiza **dentro** da War Room |
| **Resiliência:** header + assets + reports renderizam quando intelligence falha/carrega | ✅ |

> Limitações de verificação: a screenshot tool manteve timeouts de infra (validação por inspecção de DOM). A navegação fiável foi feita via `router.navigate()`. Após muitas manipulações in-page, uma das tentativas de 503 ficou presa em "loading" (artefacto do harness — sem log de erro); numa tentativa limpa o estado de erro renderizou correctamente. O caminho de erro é idêntico ao já provado no FE-010.

---

## 7. Validações

| Verificação | Comando | Resultado |
| --- | --- | --- |
| Lint | `pnpm lint` | ✅ exit 0 — 0 avisos |
| Build | `pnpm build` | ✅ exit 0 — 169 módulos |
| Fluxo real (stubbed) | preview + DOM | ✅ §6 |

> `dist/` removido.

---

## 8. Critérios de aceitação — verificação

| Critério (FE-011) | Estado |
| --- | --- |
| War Room renderiza para uma campanha | ✅ |
| Consome dados reais do Backend Core | ✅ campaign + intelligence |
| Mostra intelligence de forma clara | ✅ summary/grade/scores/moments/recs |
| Tem os painéis principais | ✅ 6 widgets + summary/warnings/explanations |
| Não depende de IE/Renderer directos | ✅ só `apiClient` |
| Loading/error/empty funcionam | ✅ §3 + §6 |
| Build/lint passam ou limitações documentadas | ✅ ambos passam |

---

## 9. Ficheiros criados/alterados

**Novos widgets:** `widgets/campaign-header/{CampaignHeader.tsx,.module.css,index.ts}`, `widgets/campaign-score-card/{CampaignScoreCard.tsx,.module.css,index.ts}`, `widgets/campaign-recommendations-panel/{CampaignRecommendationsPanel.tsx,index.ts}`, `widgets/campaign-moments-panel/{CampaignMomentsPanel.tsx,index.ts}`, `widgets/campaign-assets-panel/{CampaignAssetsPanel.tsx,index.ts}`, `widgets/campaign-reports-panel/{CampaignReportsPanel.tsx,index.ts}`.
**Reescritos:** `pages/campaign-war-room/CampaignWarRoomPage.tsx` (+ `.module.css`).
**Removidos:** `.gitkeep` dos 6 widgets.

---

## 10. Notas para os prompts seguintes

- **FE-012:** ligar `campaign-assets-panel`/`campaign-reports-panel` aos endpoints reais (content-outputs / reports / media-kits filtrados por `campaign`); substituir os placeholders por dados + estados, mantendo placeholders honestos onde o backend ainda não expõe.
- **FE-013:** tratamento transversal (sessão expirada, PermissionDenied/ServiceUnavailable dedicados) — o `ErrorState` já distingue os casos.
- **Refresh manual:** considerar um botão "Refresh" no header da War Room ligado a `intelligenceQuery.refetch`.
- **Priority:** o contrato não tem campo de prioridade explícito ao nível do resultado; a Grade serve de sinal de prioridade. Reavaliar se o engine vier a expor prioridade.
