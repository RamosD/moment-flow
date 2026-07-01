# Prompt 05 — Painel Campaign Actions + associação ao estado das acções

> Fase: `02_campaign_actions_recommendation_to_execution`
> Backlog de referência: `01_backlog.md` (CA-008, CA-009)
> Relatórios anteriores: prompt_01, prompt_02, prompt_03, prompt_04

---

## Execução 2026-06-30 (Iteração 01)

### Estado da execução

**Concluído** (painel completado para cumprir todos os campos exigidos; associação
recommendation→acção mantida e documentada; lint e build verdes; sem mocks runtime;
sem browser, conforme instrução).

### Resumo objectivo

O widget `campaign-actions-panel` e a associação visual recommendation→acção já
tinham sido introduzidos no prompt_04 (CA-006/007/008/009). Esta iteração **completou
o painel** para cumprir exactamente a lista de campos e estados pedida neste prompt,
fechando 3 lacunas concretas:

1. **priority** — não era mostrado. O backend dos 3 endpoints reais não tem coluna
   `priority`; ela é gravada (convenção do frontend) em `metadata.action_priority`
   no momento da criação. Foi adicionada à projecção da entity e passa a aparecer
   na linha de meta do painel.
2. **relação com recommendation** — clarificada: a origem "From recommendation" é
   definida exactamente quando existe um `recommendation_ref` (best-effort) no
   `metadata`, sendo essa a relação real possível (não há FK no backend).
3. **workspace ausente** — o painel mostrava "Loading actions…" indefinidamente
   quando `workspaceId`/`campaignId` faltavam (a query fica `disabled` e nunca sai
   de `isPending`). Agora há um estado honesto antes da verificação de loading.

Continua a ser uma **projecção** read-only sobre os 3 artefactos reais
(content-pack-requests / reports / media-kits) filtrados por campanha — não existe
endpoint `campaign-actions` no Backend Core.

### Campos e estados exigidos vs implementado

| Exigido | Estado | Onde |
|---|---|---|
| título | ✅ | `itemTitle` |
| tipo | ✅ | `campaignActionTypeLabel` na meta |
| status | ✅ | `Badge` (variant por `campaignActionStatusVariant`) |
| **priority** | ✅ (novo) | `metadata.action_priority` → meta `Priority: X` |
| source | ✅ | "From recommendation" / "Manual" na meta |
| data de criação | ✅ | `formatDate(createdAt)` |
| **relação com recommendation** | ✅ (best-effort) | source = recommendation ⇔ `recommendation_ref` presente |
| loading | ✅ | `LoadingState` |
| error | ✅ | `ErrorState` |
| empty | ✅ | `EmptyState` ("No actions yet") |
| **workspace ausente** | ✅ (novo) | guard antes do loading |
| sem permissão (403) | ✅ | `ErrorState` → `PermissionDenied` |
| serviço indisponível (502/503) | ✅ | `ErrorState` → `ServiceUnavailable` |

### Decisões técnicas e limitações documentadas

- **priority como projecção da entity, não leitura crua no widget**: adicionado
  `priority: string | null` a `CampaignAction` e projectado de
  `metadata.action_priority` nas três funções de projecção. Mantém a regra de
  camadas (o widget não mete a mão no bag de metadata cru; a entity projecta).
  Documentado no tipo que **não é uma coluna do backend**.
- **Associação recommendation→acção é best-effort** (CA-009 / CA-RSK-002): só
  existe via `recommendation_ref` derivado e gravado em `metadata` — não há
  relação relacional no Backend Core. Detecta apenas acções criadas por este
  frontend; o ref pode mudar se a recommendation mudar de título/posição entre
  recálculos da intelligence (recommendations não são persistidas). Já documentado
  em `features/campaign-actions/recommendation-action-match.ts` (matching) e na
  entity. A duplicação óbvia continua evitada: o botão "Create action" é
  substituído pelo estado quando já existe acção associada (lógica do prompt_04).
- **Resiliência (não quebrar outros painéis)**: `fetchCampaignActions` usa
  `Promise.allSettled` sobre os 3 endpoints — uma falha parcial (ex.: 403 só em
  reports) não apaga o painel; só lança erro se **todos** falharem. O painel é
  renderizado como bloco independente na War Room: uma falha em actions não afecta
  intelligence, scores, moments, recommendations, outputs, reports nem media kits
  (cada um tem o seu próprio estado de erro).

### Ficheiros alterados
- `entities/campaign-action/model.ts` — novo campo `priority: string | null` em
  `CampaignAction` (com nota de que é convenção de metadata, não coluna backend).
- `entities/campaign-action/campaign-action-api.ts` — `priority` projectado de
  `metadata.action_priority` nas 3 projecções (content-pack / report / media-kit).
- `widgets/campaign-actions-panel/CampaignActionsPanel.tsx` — priority na meta;
  guard honesto para `workspace/campaign` ausente; comentário a clarificar a
  relação source⇔recommendation_ref.

### Ficheiros relevantes já existentes (do prompt_04, não recriados)
- `widgets/campaign-actions-panel/CampaignActionsPanel.{tsx,module.css}`, `index.ts`.
- `entities/campaign-action/useCampaignActions.ts` (query scoped por workspace+campaign).
- `features/campaign-actions/recommendation-action-match.ts` (matching + estado).
- Integração na War Room (`pages/campaign-war-room/CampaignWarRoomPage.tsx`).

### Validações executadas e resultado
- ✅ `pnpm lint` → `eslint .` sem erros nem avisos.
- ✅ `pnpm build` → `tsc -b && vite build`, 230 módulos, sem erros de tipo.
- ✅ Sem chamadas a IE/Renderer; sem `X-Internal-Token` (inalterado; toda a rede
  passa por `apiClient` → Backend Core).
- ➖ Browser — **não usado**, conforme instrução ("Não usar browser por defeito").

### Pendências, riscos e próximo passo recomendado
- **CA-014 (validação integrada real)**: o painel não foi exercitado contra um
  Backend Core real a correr nem em browser (estados de loading/error/permission
  validados por inspecção de código e tipos, não em runtime).
- **Risco CA-RSK-002 (limitação documentada)**: associação recommendation→acção
  best-effort via metadata; sem garantia de persistência relacional no backend.
- **CA-010 (mark reviewed/dismiss)**: continua indisponível por ausência de
  contrato — não persistir estado falso.
- **CA-011 (ligar acções a outputs existentes)**: não abordado; só possível via
  metadata hoje.
- **CA-013 (doc de arquitectura)** e **CA-015 (relatório final da fase)**: por fazer.
- Nota de produto (CA-PDEC-002/006): rastreabilidade firme de acções exigiria
  backlog complementar no Backend Core (entidade `CampaignAction` persistente).
