# Arquitectura: Campaign Actions / Recommendation-to-Execution

> Fase: `02_campaign_actions_recommendation_to_execution`
> Data: 2026-06-30
> Estado: implementado (Prompts 01–07 concluídos)

---

## 1. Objectivo da feature

Transformar a Campaign War Room de uma superfície puramente analítica (mostra
o quê fazer) numa superfície de **execução operacional controlada** (permite fazer
e acompanhar o que foi feito).

A tese central:

> Uma recommendation só tem valor real quando pode ser convertida numa acção
> acompanhável.

O utilizador deve conseguir, a partir da War Room:

- ver recommendations com affordance de execução;
- escolher um tipo de acção e confirmar;
- ter a acção registada num artefacto real do Backend Core;
- ver o estado da acção associado à recommendation original;
- ver todas as acções da campanha num painel dedicado.

---

## 2. Fronteira de rede — regra não negociável

```
Browser / React → Backend Core (única fronteira)
```

O frontend **nunca** chama:

- `intelligence_engine` directamente;
- `content_renderer` directamente;
- qualquer serviço interno por porta técnica.

O header `X-Internal-Token` é um segredo de comunicação serviço-a-serviço.
**Nunca pertence ao browser.** O `apiClient` (`shared/api/client.ts`) tem um
guard activo que intercepta e descarta qualquer tentativa de o enviar:

```ts
// shared/api/client.ts
const INTERNAL_TOKEN_HEADER = 'x-internal-token'

function sanitizeCustomHeaders(headers, target): void {
  for (const [key, value] of Object.entries(headers)) {
    if (key.toLowerCase() === INTERNAL_TOKEN_HEADER) {
      // Bloqueado. Nunca enviado.
      continue
    }
    target.set(key, value)
  }
}
```

O `apiClient` singleton usa `ENV.apiBaseUrl` (variável de ambiente
`VITE_BACKEND_API_BASE_URL`) que aponta exclusivamente para o Backend Core.

---

## 3. Contratos reais do Backend Core

### 3.1 Resultado da investigação (CA-001)

O Backend Core **não tem** um endpoint de Campaign Actions, Tasks ou
Action Items. Não existe tabela nem entidade `CampaignAction`.

As recommendations são geradas pelo Intelligence Engine via
`POST /campaigns/{id}/intelligence/` e **não são persistidas** — são
recalculadas a cada chamada.

### 3.2 Endpoints de execução reais

Os três endpoints de execução reais, scoped por campanha:

| Tipo de acção | Endpoint | Método | Campos obrigatórios | PATCH? |
|---|---|---|---|---|
| `content_pack` | `/content-pack-requests/` | POST | `campaign` (UUID), `content_pack` (UUID) | ❌ imutável |
| `report_request` | `/reports/` | POST + PATCH | `campaign` (UUID), `title`, `report_type` | ✅ |
| `media_kit_request` | `/media-kits/` | POST + PATCH | `artist` (UUID), `title` | ✅ |

**Nota sobre `media_kit_request`**: o campo obrigatório no backend é `artist`
(não `campaign`). O `artist` é derivado de `campaign.artist` na criação.

**Nota sobre `content_pack`**: requer o utilizador a seleccionar um pack do
catálogo (`GET /content-packs/?status=active`). Não há título nativo — é
armazenado em `metadata.action_title`.

**Nota sobre `report_request`**: `report_type` tem default `campaign_report`
se omitido no frontend.

### 3.3 Status nativos dos artefactos

Os três artefactos usam vocabulários de status diferentes, todos normalizados
pela entity:

| Artefacto | Status nativos |
|---|---|
| Report | `queued`, `processing`, `completed`, `failed`, `archived` |
| MediaKit | `draft`, `generated`, `published`, `archived` |
| ContentPackRequest | `draft`, `queued`, `processing`, `partially_completed`, `completed`, `failed`, `cancelled`, `expired` |

### 3.4 Catálogo de content packs

Endpoint read-only: `GET /content-packs/?status=active&page_size=100`

Usado apenas quando o utilizador escolhe o tipo `content_pack` no modal.

---

## 4. Lacunas do Backend Core

| Lacuna | Impacto | Mitigação frontend |
|---|---|---|
| Sem entidade `CampaignAction` persistente | Actions são projecções de 3 endpoints distintos | Frontend projecta sobre os 3 endpoints com `Promise.allSettled` |
| Recommendations não persistidas | Sem id estável entre recálculos | `recommendation_ref` derivado (best-effort) |
| Sem FK recommendation → action | Associação não é relacional | `metadata.recommendation_ref` gravado na criação |
| Sem status `reviewed` / `dismissed` em nenhum endpoint | CA-010 (Mark Reviewed/Dismiss) não implementável | Omitido — sem persistência falsa |
| `mark_reviewed` e `dismiss` sem contrato backend | Tipos existem no modelo mas `supported: false` | UI nunca oferece estes tipos na criação |
| `manual_task` e `asset_request` sem contrato | Idem | Idem |
| `ContentPackRequest` sem PATCH | Artefacto imutável após criação | `updateCampaignAction` lança erro explícito para `content_pack` |

---

## 5. Estrutura frontend criada

```
src/
  entities/
    campaign-action/              ← entity CA (CA-002/CA-003)
      model.ts
      campaign-action-api.ts
      recommendation-ref.ts
      helpers.ts
      query-keys.ts
      useCampaignActions.ts
      useCreateCampaignAction.ts
      useUpdateCampaignAction.ts
      index.ts

    content-pack/                 ← entity read-only (catálogo)
      model.ts
      content-pack-api.ts
      useContentPacks.ts
      index.ts

  features/
    campaign-actions/             ← feature CA (CA-005/CA-006/CA-007/CA-009)
      recommendation-action-draft.ts
      useRecommendationActionDraft.ts
      action-type-options.ts
      recommendation-action-match.ts
      RecommendationActionState.tsx
      CreateActionFromRecommendationButton.tsx
      CreateActionFromRecommendationDialog.tsx
      campaign-actions.module.css
      index.ts

  shared/
    ui/
      Input/                      ← componente adicionado (CA-004)
        Input.tsx
        Input.module.css
        index.ts

  widgets/
    campaign-actions-panel/       ← widget CA (CA-008)
      CampaignActionsPanel.tsx
      CampaignActionsPanel.module.css
      index.ts
```

**Ficheiros modificados em features/campaign-intelligence:**
```
features/campaign-intelligence/
  RecommendationItem.tsx          ← slot `action?: ReactNode` adicionado
  RecommendationsList.tsx         ← prop `renderAction` adicionada
  intelligence.module.css         ← `.itemAction` adicionado

widgets/campaign-recommendations-panel/
  CampaignRecommendationsPanel.tsx ← `renderAction` pass-through adicionado

pages/campaign-war-room/
  CampaignWarRoomPage.tsx         ← actionsQuery + renderAction + CampaignActionsPanel
```

---

## 6. Entity `campaign-action`

### 6.1 Modelo — projecção, não entidade real

`CampaignAction` é uma **projecção frontend** sobre os 3 artefactos reais.
Não existe no Backend Core. O `id` de uma `CampaignAction` é o `id` do
artefacto subjacente (content-pack-request / report / media-kit).

```ts
interface CampaignAction {
  id: UUID                          // id do artefacto real
  type: SupportedCampaignActionType // 'content_pack' | 'report_request' | 'media_kit_request'
  artifactKind: CampaignActionArtifactKind
  campaignId: UUID | null
  title: string
  status: CampaignActionStatus      // normalizado (ver helpers)
  rawStatus: string | null          // status nativo original
  source: 'recommendation' | 'manual'
  priority: string | null           // convenção de metadata (não coluna)
  recommendationRef: string | null  // best-effort (não FK relacional)
  createdAt: ISODateTimeString
  updatedAt: ISODateTimeString | null
  metadata: Metadata | null
}
```

### 6.2 Tipos de acção — capabilities

`CAMPAIGN_ACTION_CAPABILITIES` é a **única fonte de verdade** para o que o
Backend Core suporta. Nada na UI deve oferecer uma acção sem verificar aqui
primeiro.

| Tipo | Suportado | Endpoint | PATCH |
|---|---|---|---|
| `content_pack` | ✅ | `/content-pack-requests/` | ❌ |
| `report_request` | ✅ | `/reports/` | ✅ |
| `media_kit_request` | ✅ | `/media-kits/` | ✅ |
| `manual_task` | ❌ | — | — |
| `asset_request` | ❌ | — | — |
| `mark_reviewed` | ❌ | — | — |
| `dismiss` | ❌ | — | — |

### 6.3 Normalização de status

O helper `normalizeActionStatus` mapeia os status nativos dos 3 artefactos
para o vocabulário partilhado `CampaignActionStatus`:

```
draft, queued          → pending
validating, processing, rendering, uploading, partially_completed → in_progress
completed, generated, published → completed
failed                 → failed
cancelled, expired, archived    → cancelled
(outro)                → unknown
```

### 6.4 `fetchCampaignActions` — resiliência por `Promise.allSettled`

```ts
const settled = await Promise.allSettled([
  apiClient.get('/content-pack-requests/', { params }),
  apiClient.get('/reports/', { params }),
  apiClient.get('/media-kits/', { params }),
])
```

- Se 1 ou 2 endpoints falham (ex.: 403 parcial): dados parciais mostrados,
  sem erro visível.
- Se todos falham: rethrow do primeiro erro → painel mostra `ErrorState`.

**Intenção**: uma 403 num recurso não bloqueia os outros. O painel de actions
nunca está completamente em branco por culpa de uma falha parcial.

### 6.5 `recommendation_ref` — convenção de metadata

A única ligação possível entre uma recommendation e o artefacto criado é uma
chave derivada gravada em `metadata` na criação:

```
metadata.recommendation_ref = "<campaignId>:id:<rec.id>"       // quando rec tem id
                             = "<campaignId>:i<idx>:<slug>"     // fallback posicional
metadata.action_source       = "recommendation" | "manual"
metadata.action_title        = título do draft (para content_pack sem título nativo)
metadata.action_description  = descrição opcional
metadata.action_priority     = prioridade opcional
```

**Esta convenção é frontend-only.** O Backend Core não a conhece nem a
valida. Não é uma FK relacional. Funciona apenas para acções criadas por este
frontend usando este fluxo.

### 6.6 `priority` — não é coluna do backend

`CampaignAction.priority` é projectado de `metadata.action_priority`. Os
3 endpoints reais não têm coluna de prioridade. É uma convenção do frontend
gravada na criação e lida na projecção.

---

## 7. Feature `campaign-actions`

### 7.1 `recommendation-action-draft.ts`

Converte uma `CampaignRecommendation` flexível num `RecommendationActionDraft`
consistente. Defensivo — nunca lança se campos faltam.

Campos derivados:
- `title` ← `rec.title ?? rec.label ?? rec.action ?? 'Recommendation'`
- `description` ← `rec.description ?? rec.reason`
- `priority` ← `rec.priority` (normalizado para string)
- `confidence` ← `rec.confidence` (apenas se numérico)
- `suggestedActionType` ← keyword match em `rec.action/type/title/label`
- `recommendationRef` ← `deriveRecommendationRef(campaignId, rec, index)`

### 7.2 `recommendation-action-match.ts`

Verifica se já existe uma `CampaignAction` cujo
`metadata.recommendation_ref` coincide com o ref do draft:

```ts
function matchRecommendationAction(
  draft: RecommendationActionDraft | null,
  actions: CampaignAction[] | undefined,
): CampaignAction | null
```

Limitação documentada: só encontra acções criadas por este frontend usando
esta convenção. Acções criadas por outros meios (API directa, admin, outro
cliente) não são correlacionadas.

### 7.3 `CreateActionFromRecommendationButton`

Affordance por-recommendation. Renderiza um de três estados:

1. **matched** — mostra `RecommendationActionState` (tipo + status); o botão
   desaparece para evitar duplicação óbvia.
2. **ready** — mostra "Create action" (abre o dialog).
3. **not ready** — botão disabled enquanto `campaign` ou `draft` não existem.

Se `actionsQuery` erra ou está a carregar, `actions = undefined` →
`matchRecommendationAction` retorna `null` → estado 2 ou 3 (degradação segura,
sem crash).

### 7.4 `CreateActionFromRecommendationDialog`

Modal de confirmação construído sobre o componente `<Dialog>` nativo
(`<dialog>` HTML).

Fluxo de submit:
1. Validação local (`title` obrigatório; `content_pack` obrigatório quando
   tipo = `content_pack`).
2. `buildInput()` constrói o payload correcto por tipo (switch discriminado).
3. `mutation.mutate(input)` → `useCreateCampaignAction` → `createCampaignAction`.
4. Sucesso → `queryClient.invalidateQueries` + fechar dialog.
5. Erro → `generalError` via `resolveErrorPreset` (ou field errors inline).

Campo `content_pack`: o `Select` de packs só é carregado quando o utilizador
escolhe o tipo `content_pack` — `useContentPacks(workspaceId, actionType === 'content_pack')`.

Campo `priority` e `description`: não são colunas dos endpoints → gravados em
`metadata` (convenção, não contrato).

**Tratamento de erros no dialog:**

| Erro | Comportamento |
|---|---|
| 401 | `notifyUnauthorized()` global + Alert "Session expired" |
| 403 | Alert "Access denied" |
| 404 | Alert "Not found" |
| 422 com erros em campo visível (title, content_pack) | Field error inline; sem alert geral |
| 422 com erros em campo derivado (artist, campaign) | Alert "Invalid request / Some of the submitted data was rejected." |
| 502/503 | Alert "Service unavailable" |
| Network | Alert "Connection problem" |
| busy = true | Escape/backdrop/close bloqueados — `handleClose` guarda `if (busy) return` |

### 7.5 `RecommendationActionState`

Dois badges inline por recommendation convertida:
- `Badge variant="info"` com o tipo da acção (`campaignActionTypeLabel`).
- `Badge variant={statusVariant}` com o status normalizado.

### 7.6 `action-type-options.ts`

`SUPPORTED_ACTION_TYPE_OPTIONS` — apenas os 3 tipos suportados (usado no dialog).

`ACTION_TYPE_OPTIONS` — todos os tipos, com os não-suportados `disabled: true`
e label "(unavailable)" (disponível para surfaces futuras que precisem de mostrar
honestamente o que não está disponível).

---

## 8. Widget `campaign-actions-panel`

`CampaignActionsPanel` agrega os 3 artefactos reais num painel único na War Room.

```
GET /content-pack-requests/?campaign=<id>&page_size=50
GET /reports/?campaign=<id>&page_size=50
GET /media-kits/?campaign=<id>&page_size=50
```

Usa o mesmo `queryKey` que `useCampaignActions` na página — uma única
chamada de rede partilhada por TanStack Query.

**Campos mostrados por acção:**
- título
- tipo (`campaignActionTypeLabel`)
- status (`Badge`)
- source ("From recommendation" | "Manual")
- priority (quando presente em `metadata.action_priority`)
- data de criação (`formatDate`)

**Estados do painel:**

| Condição | Estado |
|---|---|
| `!workspaceId \|\| !campaignId` | `EmptyState` "No workspace selected" |
| `isPending` | `LoadingState` |
| `isError` + 401 | `ErrorState` → `SessionExpired` |
| `isError` + 403 | `ErrorState` → `PermissionDenied` |
| `isError` + 404 | `ErrorState` → `NotFoundState` |
| `isError` + 502/503 | `ErrorState` → `ServiceUnavailable` |
| `isError` + network | `ErrorState` → "Connection problem" |
| `data.length === 0` | `EmptyState` "No actions yet" |
| dados | lista de acções |

---

## 9. Isolamento na War Room

Cada painel da War Room tem queries e estados de erro independentes. Uma falha
no `CampaignActionsPanel` não afecta:

- `CampaignHeader` (query independente em `useCampaign`)
- Intelligence section (query independente em `useCampaignIntelligence`)
- `CampaignReportsPanel`, `CampaignMediaKitsPanel`, `CampaignAssetsPanel`

O `actionsQuery` na página (`CampaignWarRoomPage`) existe apenas para passar
`actionsQuery.data` ao botão por-recommendation. Se errar:
- `data = undefined`
- `matchRecommendationAction(draft, undefined) → null`
- botão mostra "Create action" (degradação segura)

---

## 10. Render-prop para desacoplamento de camadas

A regra de camadas FSD-like proíbe `campaign-intelligence` de importar
`campaign-actions`. Para ligar os dois sem violar a regra:

```
CampaignWarRoomPage
  └─ CampaignRecommendationsPanel
       └─ RecommendationsList
            └─ RecommendationItem
                 └─ {action?: ReactNode}   ← slot injectado pela página
```

A página injeta o `renderAction` prop:

```tsx
renderAction={(recommendation, index) => (
  <CreateActionFromRecommendationButton
    workspaceId={workspaceId}
    campaign={campaignQuery.data}
    recommendation={recommendation}
    index={index}
    actions={actionsQuery.data}
  />
)}
```

`campaign-intelligence` permanece completamente desconhecido de
`campaign-actions`. A ligação só existe na página.

---

## 11. Fluxo recommendation → action

```
1. War Room carrega
   ├─ useCampaignIntelligence → recommendations
   └─ useCampaignActions → acções existentes (3 endpoints em paralelo)

2. Por cada recommendation, a página injeta CreateActionFromRecommendationButton

3. Button:
   ├─ useRecommendationActionDraft → draft (title, description, priority, ref, suggestedType)
   ├─ matchRecommendationAction(draft, actions)
   │    ├─ match encontrado → mostra RecommendationActionState (tipo + status)
   │    └─ sem match → mostra "Create action" (botão)
   └─ onClick "Create action" → abre CreateActionFromRecommendationDialog(open=true)

4. Dialog:
   ├─ Formulário pré-preenchido com dados do draft
   ├─ Utilizador escolhe tipo (content_pack / report_request / media_kit_request)
   ├─ Se content_pack: useContentPacks carrega catálogo (lazy)
   ├─ Utilizador edita título, descrição, priority
   └─ Submit

5. Submit:
   ├─ Validação local (title, content_pack)
   ├─ buildInput() → payload correcto por tipo com metadata (recommendation_ref, source, priority, description)
   ├─ useCreateCampaignAction → createCampaignAction → POST endpoint real
   ├─ Sucesso:
   │    ├─ queryClient.invalidateQueries('campaign-actions')
   │    ├─ queryClient.invalidateQueries('reports' | 'media-kits') se aplicável
   │    └─ dialog fecha
   └─ Erro → alert (ver §7.4)

6. Após invalidação:
   ├─ useCampaignActions refetch → nova acção visível no CampaignActionsPanel
   └─ actionsQuery refetch → matchRecommendationAction encontra a nova acção
                           → botão substituído por RecommendationActionState
```

---

## 12. Mark Reviewed / Dismiss — não implementado

`mark_reviewed` e `dismiss` existem em `CAMPAIGN_ACTION_CAPABILITIES` com
`supported: false` e razões explícitas:

```ts
mark_reviewed: {
  reason: 'Recommendations are recomputed, not persisted; review state cannot be stored.',
},
dismiss: {
  reason: 'Recommendations are recomputed, not persisted; dismissal cannot be stored.',
},
```

O Backend Core não tem:
- status `reviewed` / `dismissed` em nenhum dos 3 artefactos;
- endpoint dedicado para marcar recommendations;
- persistência de recommendations (são recalculadas a cada chamada).

**Decisão (CA-010)**: omitidos. Não há affordance para estes tipos. Não há
persistência falsa. Para implementar no futuro requer backlog no Backend Core
(ver §14 — próximos passos).

---

## 13. Regras de segurança

| Regra | Como é aplicada |
|---|---|
| Nunca chamar IE directamente | `apiClient` aponta apenas para `VITE_BACKEND_API_BASE_URL` (Backend Core) |
| Nunca chamar Renderer directamente | Idem |
| Nunca enviar `X-Internal-Token` | `sanitizeCustomHeaders` em `client.ts` intercepta e descarta |
| Nunca expor stack traces | `resolveErrorPreset` e `ErrorState` devolvem copy segura, nunca `error.stack` |
| Nunca expor tokens em UI | Erros tipados (`ApiError`, subclasses) não carregam headers de autenticação |
| 401 global → logout | `notifyUnauthorized()` notifica o `AuthProvider` registado |
| 403 → permissão insuficiente | `PermissionDenied` screen (não "acesso bloqueado") |
| `workspaceId` ausente | Queries desactivadas; UI mostra estado honesto |
| Sem secrets em `.env.example` | Apenas `VITE_BACKEND_API_BASE_URL`; nota explícita no ficheiro |

---

## 14. O que não fazer

- **Não chamar `intelligence_engine` directamente** — sempre via Backend Core.
- **Não chamar `content_renderer` directamente** — sempre via Backend Core.
- **Não enviar `X-Internal-Token` do browser** — nunca é um header do frontend.
- **Não inventar endpoints** — só usar os 3 confirmados (ver §3.2).
- **Não criar mocks runtime** para fingir persistência de actions, reviews ou
  dismissals sem contrato backend real.
- **Não persistir estado reviewed/dismissed** via metadata workaround —
  as recommendations são transientes e o ref pode mudar entre recálculos.
- **Não passar `content_pack` como tipo numa mutation sem `contentPackId`** —
  o endpoint exige FK `content_pack` obrigatória.
- **Não usar `updateCampaignAction` com `content_pack`** — endpoint sem PATCH;
  a função lança erro explícito para impedir uso acidental.
- **Não construir lógica de negócio dependente de `recommendation_ref`** como
  se fosse um identificador persistente do backend — é uma correlação
  best-effort que pode divergir entre sessões.
- **Não importar `features/campaign-actions` de dentro de
  `features/campaign-intelligence`** — viola regras de camadas; usar render-prop.

---

## 15. Próximos passos

| Item | Descrição | Pré-requisito |
|---|---|---|
| **CA-011** | Ligar acções a outputs existentes | Apenas via metadata hoje; backlog backend para FK |
| **CA-014** | Validação integrada real (browser + Backend Core real) | Iteração com browser habilitado |
| **CA-015** | Relatório final da fase | Após CA-014 |
| **CA-PDEC-006** | Backlog backend: entidade `CampaignAction` persistente | Decisão de produto |
| Mark Reviewed / Dismiss | Requere backend: status `reviewed`/`dismissed` num endpoint, ou entidade de recommendation persistida | CA-PDEC-006 |
| `manual_task` | Requere backend: endpoint de tasks | CA-PDEC-006 |
| `asset_request` | Requere backend: endpoint de asset requests | CA-PDEC-006 |
| Traceabilidade firme rec→action | Requere backend: FK `recommendation_ref` persistida no artefacto, não apenas em `metadata` | CA-PDEC-006 |
| Actualização de status de report/media-kit | `useUpdateCampaignAction` já existe e funciona; falta affordance UI | Decisão UX |

---

## Apêndice A — Ficheiros chave e propósito

| Ficheiro | Propósito |
|---|---|
| `entities/campaign-action/model.ts` | Tipos, CAMPAIGN_ACTION_CAPABILITIES, payloads |
| `entities/campaign-action/campaign-action-api.ts` | fetch/create/update sobre os 3 endpoints reais |
| `entities/campaign-action/recommendation-ref.ts` | Derivação e estrutura do recommendation_ref |
| `entities/campaign-action/helpers.ts` | Labels, status normalization, badge variants |
| `entities/campaign-action/query-keys.ts` | Query keys scoped por workspace+campaign |
| `entities/content-pack/` | Catálogo read-only (`GET /content-packs/`) |
| `features/campaign-actions/recommendation-action-draft.ts` | Draft builder defensivo |
| `features/campaign-actions/recommendation-action-match.ts` | Best-effort match rec→action |
| `features/campaign-actions/action-type-options.ts` | Select options derivadas de CAPABILITIES |
| `features/campaign-actions/CreateActionFromRecommendationDialog.tsx` | Modal de criação real |
| `features/campaign-actions/CreateActionFromRecommendationButton.tsx` | Affordance por-recommendation |
| `features/campaign-actions/RecommendationActionState.tsx` | Badges de tipo+status |
| `widgets/campaign-actions-panel/CampaignActionsPanel.tsx` | Painel agregado na War Room |
| `shared/api/client.ts` | Única fronteira de rede; guard X-Internal-Token |
| `shared/ui/states/error-presets.ts` | Copy segura por tipo de erro |
| `shared/ui/states/ErrorState.tsx` | Router para dedicated screens por erro |

---

## Apêndice B — Decisões de arquitectura e fundamentos

### B.1 Por que três endpoints em vez de um único endpoint de actions?

O Backend Core não tem um endpoint de campaign-actions. A alternativa honesta
é agregar os três endpoints reais que registam execuções numa campanha.
Inventar um endpoint falso ou criar mocks runtime violaria a regra de não
fingir persistência.

### B.2 Por que `Promise.allSettled` e não `Promise.all`?

Com `Promise.all`, uma 403 num único endpoint (ex.: `reports:view` não
concedido) faria a query falhar completamente. Com `Promise.allSettled`, os
resultados de content-pack-requests e media-kits são mostrados mesmo que
reports falhe. O painel só vai a erro quando **todos** falham.

### B.3 Por que render-prop para ligar intelligence a campaign-actions?

As regras de camadas FSD-like proíbem `features/campaign-intelligence` de
importar `features/campaign-actions`. O render-prop inverte a dependência:
`campaign-intelligence` expõe um slot; a página wire-up os dois. Zero
acoplamento entre features.

### B.4 Por que `metadata` para priority/description/recommendation_ref?

Os três endpoints reais não têm colunas para estes campos. Usar `metadata`
(JSONField no Django) é a única forma de persisti-los no backend existente
sem alterações ao schema. É uma convenção do frontend, devidamente
documentada — não um contrato de backend.

### B.5 Por que omitir mark_reviewed/dismiss em vez de mostrar disabled?

Dois motivos: (1) as recommendations são transientes — não há entidade backend
a "marcar"; um botão disabled criaria a expectativa de uma funcionalidade
que não pode ser cumprida nem com workarounds; (2) a omissão é mais honesta
para o piloto técnico do que botões que nunca ficarão disponíveis sem
backlog backend.
