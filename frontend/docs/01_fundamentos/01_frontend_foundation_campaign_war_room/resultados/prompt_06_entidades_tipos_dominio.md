# FE-006 — Entidades e tipos de domínio

**Fase:** Frontend Foundation & Campaign War Room MVP
**Componente alvo:** `frontend`
**Data:** 2026-06-26
**Tipo:** Tipos TypeScript de domínio (`entities/*`) alinhados ao OpenAPI do Backend Core

---

## 0. Sumário executivo

- **Fonte de verdade encontrada e usada:** `backend_core/schema.yml` (OpenAPI 3.0.3, drf-spectacular, ~9300 linhas). Os tipos foram derivados **directamente do schema real**, não de suposições.
- Criadas as **13 entidades** pedidas em `src/entities/*` + tipos de resposta em `src/shared/types`.
- **Tipos de Campaign Intelligence** cobrem todos os blocos: analysis, scores, grade, moments, recommendations, summary, explanations, warnings, metadata, generated_at.
- **Campos incertos = opcionais**, alinhados ao array `required` de cada schema; `nullable` → `| null`.
- **Lacuna de contrato registada:** `result.moments` e `result.recommendations` são **arrays não-tipados** (`items: {}`) e `analysis`/`scores` são objectos livres — modelados como best-effort (tudo opcional + index signature).
- **Zod não instalado** (decisão justificada, FE-PDEC-005). Sem mappers (tipos 1:1 com o JSON, snake_case mantido).
- **`pnpm build` e `pnpm lint` passam** (exit 0, 0 avisos).

---

## 1. Fonte de verdade: OpenAPI real

Ao contrário do que o Prompt 01 assumiu (rotas "prováveis"), o schema OpenAPI **existe** no repositório: `backend_core/schema.yml`. Confirmações relevantes:

- Wrapper de paginação DRF = exactamente `{ count, next, previous, results }` → coincide com o `Paginated<T>` criado no FE-003.
- **Todas as FKs são strings UUID**, não objectos aninhados (ex.: `Campaign.artist` é um uuid, não um `Artist`). Listas/detalhes **não** expandem relações.
- `POST /api/v1/campaigns/{id}/intelligence/`: **sem request body**, header `X-Workspace-ID` obrigatório + JWT, resposta **200** `CampaignIntelligenceResponse`.
- Auth usa **email** + password (não username).

(Factos guardados em memória para os próximos prompts.)

---

## 2. Entidades criadas (`entities/*`)

| Entidade | Ficheiro | Enums (union types) |
| --- | --- | --- |
| **Workspace** | `workspace/model.ts` | `WorkspaceType` (8), `WorkspaceStatus` (5) |
| **User** | `user/model.ts` | — (read-only) |
| **Artist** | `artist/model.ts` | `ArtistStatus` (3) |
| **Track** | `track/model.ts` | `TrackType` (7), `TrackStatus` (6) |
| **Campaign** | `campaign/model.ts` | `CampaignType` (9), `CampaignStatus` (6) |
| **CampaignIntelligence** + análise/scores/moments/recommendations | `campaign/intelligence.ts` | `IntelligenceSource` (engine/dry_run) |
| **ContentOutput** | `content-output/model.ts` | `ContentOutputStatus` (10), `PublicVisibility` (4) |
| **Report** | `report/model.ts` | `ReportType` (7), `ReportStatus` (5) |
| **MediaKit** + **MediaKitItem** | `media-kit/model.ts` | `MediaKitStatus` (4), `MediaKitItemType` (9), `PublicVisibility` (4) |

Cada entidade tem `index.ts` com `export type * from './model'`. Enums modelados como **string literal unions** (TS `enum` é proibido por `erasableSyntaxOnly`; unions são também mais leves e serializáveis).

### Localização dos tipos de intelligence
Os tipos `CampaignIntelligence`, `CampaignIntelligenceResult`, `CampaignAnalysis`, `CampaignScores`, `CampaignMoment`, `CampaignRecommendation` ficam em **`entities/campaign/intelligence.ts`** (domínio da campanha), em vez de uma entidade nova — respeita a estrutura definida no FE-002 e mantém-nos importáveis pela feature `campaign-intelligence`.

---

## 3. Cobertura de Campaign Intelligence

`CampaignIntelligence` (alias `CampaignIntelligenceResponse`) cobre os 10 blocos pedidos:

| Bloco | Tipo | Obrigatório? |
| --- | --- | --- |
| status | `string` | ✅ |
| source | `'engine' \| 'dry_run'` | ✅ |
| engine / engine_version | `string` | ✅ |
| request_id / workspace_id / campaign_id | `string` | ✅ |
| **result.analysis** | `CampaignAnalysis` (`Record<string, unknown>`) | opcional |
| **result.scores** | `CampaignScores` (`Record<string, unknown>`) | opcional |
| **result.grade** | `string \| null` | opcional |
| **result.moments** | `CampaignMoment[]` (best-effort) | opcional |
| **result.recommendations** | `CampaignRecommendation[]` (best-effort) | opcional |
| **result.summary** | `string` | opcional |
| explanations / warnings | `IntelligenceNote[]` (`Record<string,unknown>[]`) | opcional |
| metadata | `Metadata` | opcional |
| generated_at | `string` | ✅ |

---

## 4. Tipos de resposta (`shared/types`)

| Tipo | Definição | Nota |
| --- | --- | --- |
| `PaginatedResponse<T>` | alias de `Paginated<T>` (FE-003) | DRF `{count,next,previous,results}` |
| `DetailResponse<T>` | `T` | endpoints de detalhe devolvem a entidade directa |
| `ApiErrorResponse` | `{ detail?, code?, [field]: unknown }` | corpo de erro DRF (validação inclusa) |

Scalars (`shared/types/scalars.ts`): `UUID`, `ISODateString`, `ISODateTimeString`, `Metadata` — documentam os `format` do OpenAPI sem custo runtime.

---

## 5. Decisões de modelação

1. **Opcionalidade guiada pelo `required` do schema.** Campos no array `required` → obrigatórios; restantes → `?`. `nullable: true` → `| null`. Evita inventar campos como obrigatórios (FE-RSK-004).
2. **snake_case mantido.** Os tipos espelham exactamente o JSON da API → **sem mappers** nem camada de transformação no MVP. (Reavaliar se/quando a UI precisar de normalização.)
3. **FKs como `UUID`**, não objectos — fiel ao contrato. A War Room que precise de dados do artista/track fará fetch próprio ou dependerá de expansão futura do backend (lacuna §7).
4. **`PublicVisibility` duplicado** em `content-output` e `media-kit` (4 literais cada) para respeitar a regra de camadas (entities → shared apenas; sem import entity↔entity). Custo: drift potencial mínimo; documentado nos ficheiros.
5. **Moments/recommendations best-effort**: tudo opcional + `[key: string]: unknown`. A UI deve renderizar defensivamente.

---

## 6. Avaliação de Zod — não instalado

Decisão: **não instalar Zod nesta fase** (alinha FE-PDEC-005).

- **Porquê:** os blocos mais críticos da intelligence (`analysis`, `scores`, `moments`, `recommendations`) são **livres/não-tipados no próprio contrato**. Schemas Zod sobre dados não estabilizados seriam adivinhação de alta manutenção e dariam falsa sensação de segurança.
- **Alternativa adoptada:** tipos manuais derivados do OpenAPI (a verdadeira fonte de verdade) + render defensivo na War Room.
- **Caminho futuro:** quando o contrato do engine estabilizar, avaliar geração automática de tipos a partir do `schema.yml` (ex.: `openapi-typescript`) e/ou Zod só para a resposta de intelligence.

**Sem framework de testes** (FE-PDEC-004) → sem testes de tipos; `tsc -b` é a validação.

---

## 7. Lacunas de contrato registadas

| # | Lacuna | Impacto | Mitigação |
| --- | --- | --- | --- |
| G1 | `result.moments` / `result.recommendations` são `items: {}` (sem shape) | Alto p/ War Room | Tipos best-effort opcionais; render defensivo; confirmar shape real com a equipa do engine |
| G2 | `result.analysis` / `result.scores` são objectos livres | Médio | `Record<string, unknown>`; UI itera/normaliza com cuidado |
| G3 | FKs não expandidas (só UUID) | Médio | War Room faz fetch de campaign + (futuro) artist/track; ou pedir expansão ao backend |
| G4 | `generated_at` é `string` (sem `format: date-time`) | Baixo | Tratar como string; parse tolerante na UI |
| G5 | `metadata: {}` e `explanations`/`warnings` sem shape | Baixo | `Record<string,unknown>` / arrays de objectos livres |

---

## 8. Validações

| Verificação | Comando | Resultado |
| --- | --- | --- |
| Lint | `pnpm lint` | ✅ exit 0 — 0 avisos |
| Typecheck + build | `pnpm build` | ✅ exit 0 — 115 módulos (tipos são apagados; `tsc -b` valida todos os ficheiros de `entities`) |

> O bundle mantém-se em 115 módulos porque tipos não geram runtime. `dist/` removido. Não houve verificação em browser por serem alterações puramente de tipos (não observáveis).

---

## 9. Critérios de aceitação — verificação

| Critério (FE-006) | Estado |
| --- | --- |
| Tipos centrais existem | ✅ 13 entidades + responses |
| Tipos de Campaign Intelligence cobrem os blocos principais | ✅ §3 (10 blocos) |
| Campos incertos são opcionais | ✅ guiados pelo `required` do schema |
| Build passa | ✅ |
| Lint passa ou limitação documentada | ✅ passa sem avisos |
| Relatório lista decisões de modelação e lacunas | ✅ §5 + §7 |

---

## 10. Ficheiros criados/alterados

**Novos (`shared/types`):** `scalars.ts`, `responses.ts`, `index.ts`.
**Novos (`entities`):**
- `campaign/{model.ts, intelligence.ts, index.ts}`
- `artist/`, `track/`, `workspace/`, `user/`, `content-output/`, `report/`, `media-kit/` (cada `model.ts` + `index.ts`); `media-kit/model.ts` inclui `MediaKitItem`.

**Removidos:** `.gitkeep` das 8 entidades + `shared/types/.gitkeep`.

**Memória:** registado `backend-core-openapi-source-of-truth` (localização do `schema.yml` + factos-chave de contrato).

---

## 11. Notas para os prompts seguintes

- **FE-007 (auth):** tipos de token — `POST /auth/token/` recebe `{email, password}` → `{access, refresh}`; `/auth/token/refresh/` recebe `{refresh}` → `{access, refresh}`; `/auth/me/` devolve `User`. Definir em `features/auth` (não em entities).
- **FE-008 (workspace):** `GET /workspaces/` → `PaginatedResponse<Workspace>`; existe `GET /workspaces/current/`.
- **FE-009:** `GET /campaigns/` → `PaginatedResponse<Campaign>`; `GET /campaigns/{id}/` → `Campaign`.
- **FE-010/011:** `POST /campaigns/{id}/intelligence/` (**sem body**) → `CampaignIntelligence`; renderizar moments/recommendations defensivamente (G1).
- **FE-012:** content outputs / reports / media kits têm endpoints próprios filtráveis por `campaign` — confirmar parâmetros de filtro no schema antes de implementar.
