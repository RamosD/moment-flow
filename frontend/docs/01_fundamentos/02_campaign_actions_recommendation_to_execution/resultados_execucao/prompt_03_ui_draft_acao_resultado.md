# Prompt 03 — UI mínima + draft de acção a partir de recommendation

## 2026-06-30

### Estado da execução

Concluído.

### Resumo objectivo

Criados os componentes UI mínimos em `shared/ui` necessários para um futuro fluxo
de criação de acção (Dialog, ConfirmDialog, Select, Textarea, FormField,
InlineFieldError), e a lógica defensiva em `features/campaign-actions` que
transforma uma `CampaignRecommendation` (contrato best-effort, ver
`entities/campaign/intelligence.ts`) num `RecommendationActionDraft` —
sem qualquer submissão ao Backend Core. Não foi usado o browser, conforme
instrução explícita desta iteração.

### Ficheiros criados/alterados

**`shared/ui` — componentes base (cada um com `.tsx` + `.module.css` + `index.ts`):**
- `shared/ui/Dialog/` — wrapper sobre o elemento nativo `<dialog>`. Gestão de
  foco, fecho com Escape (`onCancel`) e fecho por clique no backdrop são
  obtidos nativamente do browser, sem `createPortal` nem biblioteca de
  focus-trap (nenhum uso de `createPortal` existe no resto do repositório).
  `aria-labelledby`/`aria-describedby` ligados a `useId()`.
- `shared/ui/ConfirmDialog/` — composição sobre `Dialog`, com botões
  Cancel/Confirm e estado `busy` ("Working…").
- `shared/ui/Select/` — wrapper sobre `<select>` nativo, `SelectOption {
  value, label, disabled? }`, placeholder opcional.
- `shared/ui/Textarea/` — wrapper estilizado sobre `<textarea>` nativo.
- `shared/ui/FormField/` — agrupa `<label htmlFor>` + control + hint/erro,
  generalizando o padrão já usado em `LoginPage`.
- `shared/ui/InlineFieldError/` — `<span role="alert">` condicional.
- **Editado** `shared/ui/index.ts` — adicionados os exports dos 6 componentes
  acima (Dialog, ConfirmDialog, Select, Textarea, FormField,
  InlineFieldError), preservando todos os exports existentes.

Todos os componentes usam CSS Modules + os tokens de
`shared/styles/tokens.css` (sem valores hard-coded) e o helper `cx()`
existente — nenhuma biblioteca de UI nova foi instalada.

**`features/campaign-actions/` — lógica de draft (pasta antes só continha `.gitkeep`, agora removido):**
- `recommendation-action-draft.ts` — `RecommendationActionDraft` interface
  (`recommendationRef`, `title`, `description`, `priority`, `confidence`,
  `suggestedActionType`, `source`) e `buildRecommendationActionDraft(campaignId,
  recommendation, index)`. Extrai `title` de `title → label → action`;
  `description` de `description → reason`; `priority` (string ou number, sem
  normalizar); `confidence` (apenas se numérico); deriva `recommendationRef`
  via `deriveRecommendationRef` (entity, prompt 02); sugere
  `suggestedActionType` por correspondência de palavras-chave
  (`report`, `media[_-]?kit`, `content`/`asset`) restrita aos 3 tipos
  realmente suportados — nunca sugere um tipo sem contrato real. Tolera
  `recommendation === undefined` e qualquer campo em falta; nunca lança
  excepção.
- `useRecommendationActionDraft.ts` — hook `useMemo` fino sobre o builder;
  devolve `null` enquanto não há `campaignId` (todos os endpoints suportados
  são scoped a campanha).
- `action-type-options.ts` — `ACTION_TYPE_OPTIONS` (todos os tipos, com os
  não suportados marcados `disabled: true` e rótulo "(unavailable)" — nunca
  escondidos, para manter a UI honesta) e `SUPPORTED_ACTION_TYPE_OPTIONS`
  (apenas os 3 tipos reais), ambos derivados de
  `CAMPAIGN_ACTION_CAPABILITIES` (única fonte de verdade, prompt 02).
- `index.ts` — barrel exportando o acima.

### Nota sobre limitação de id de recommendation

As recomendações do Intelligence Engine não têm `id` garantido (endpoint
`POST /campaigns/{id}/intelligence/` é recalculado em cada chamada, sem
persistência — ver prompt 01). `buildRecommendationActionDraft` lida com isto
delegando em `deriveRecommendationRef` (entity `campaign-action`), que cai
para uma chave posicional + slug de conteúdo quando `recommendation.id` está
ausente. Esta documentação já existe no JSDoc de
`entities/campaign-action/recommendation-ref.ts`; este prompt não duplicou a
lógica, apenas a reutilizou a partir da feature.

### Decisão técnica — narrowing para `deriveRecommendationRef`

`CampaignRecommendation` (entity `campaign`) declara apenas alguns campos
(`id`, `type`, `title`, `description`, `priority`, `action`) e tem assinatura
de índice `[key: string]: unknown` para o resto (ex.: `label`, `reason`,
`confidence`). Para chamar `deriveRecommendationRef`, que espera
`RecommendationLike` (campos tipados como `string | undefined`), construiu-se
`toRecommendationLike()` em `recommendation-action-draft.ts` que narrows
explicitamente cada campo (em particular `label`, lido via `unknown` e
validado com `asString()`), em vez de passar o objecto `CampaignRecommendation`
directamente — o `tsc -b` confirmou que esta construção compila sem erros.

### Validações executadas e resultado

- `pnpm lint` → passou sem erros nem avisos (`eslint .`, sem output).
- `pnpm build` → passou (`tsc -b && vite build`, 201 módulos transformados,
  build em ~3.49s). Sem erros de tipo.
- Sem uso de browser/dev server, conforme instrução explícita desta iteração
  ("Não usar browser por defeito"). Os componentes `shared/ui` ainda não
  estão integrados em nenhuma página, pelo que não há ainda uma superfície
  visual a validar.

### Pendências/riscos/próximo passo

- **Fora de âmbito deste prompt (por instrução explícita)**: qualquer
  submissão ao backend. Nenhuma chamada de rede foi feita ou implementada
  além do código de entidade já existente do prompt 02.
- Próximos passos identificados no backlog (não iniciados): CA-006
  (adicionar affordance de acção a `RecommendationItem`, usando
  `useRecommendationActionDraft`), CA-007 (modal "Create Action" real, usando
  `Dialog`/`Select`/`Textarea`/`FormField` agora criados + `useCreateCampaignAction`
  do prompt 02), CA-008 (painel de Campaign Actions no War Room).
- Risco a vigiar em CA-007: o draft sugere `suggestedActionType` por
  palavras-chave — é apenas uma sugestão pré-preenchida, o utilizador deve
  poder sempre escolher manualmente entre `SUPPORTED_ACTION_TYPE_OPTIONS`.
- Quando a UI de criação for construída, `content_pack` exige escolher um
  `contentPackId` do catálogo (não derivável da recommendation) — a futura
  modal terá de obter essa lista via endpoint de catálogo existente (fora do
  âmbito deste prompt).
