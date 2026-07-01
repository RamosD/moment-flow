# Prompt 07 — Revisão de erros, permissões e segurança (Campaign Actions)

> Fase: `02_campaign_actions_recommendation_to_execution`
> Backlog de referência: `01_backlog.md` (CA-012)
> Relatórios anteriores: prompt_01 a prompt_06

---

## Execução 2026-06-30 (Iteração 01)

### Estado da execução

**Concluído** (auditoria completa de todos os cenários de erro; 1 correcção aplicada;
greps de segurança limpos; lint e build verdes; sem browser, conforme instrução).

### Resumo objectivo

Revisão completa da experiência de erros, permissões e segurança da feature
Campaign Actions — incluindo `CreateActionFromRecommendationDialog`,
`CampaignActionsPanel`, `CreateActionFromRecommendationButton` e a integração
na `CampaignWarRoomPage`. O objetivo era confirmar que nenhum cenário de falha
quebra a War Room, que todas as respostas HTTP são tratadas correctamente, que
não há exposição de dados sensíveis, e que a fronteira com o Backend Core é
a única fronteira de rede.

**Resultado:** A feature estava correta em todos os cenários críticos excepto um:
a descrição do alert de erro geral para 422 com erros em campos não-visíveis
mostrava o texto HTTP "Unprocessable Content" (texto de status HTTP, não
mensagem para o utilizador). Corrigido.

---

### Auditoria completa de cenários de erro

#### Panel (`CampaignActionsPanel`)

| Cenário | Comportamento | Estado |
|---|---|---|
| 401 sessão expirada | `ErrorState` → `SessionExpired` | ✅ |
| 403 sem permissão | `ErrorState` → `PermissionDenied` | ✅ |
| 403 parcial (1 de 3 endpoints) | `Promise.allSettled` — painel mostra dados parciais, sem erro | ✅ |
| 404 campanha inexistente | `ErrorState` → `NotFoundState` | ✅ |
| 502/503 serviço indisponível | `ErrorState` → `ServiceUnavailable` com retry | ✅ |
| Network error | `ErrorState` → `FeedbackBlock` "Connection problem" | ✅ |
| Workspace / campaignId ausente | `EmptyState` "No workspace selected" (guard antes do loading) | ✅ |
| Todos os 3 endpoints falham | Rethrow do primeiro erro → `ErrorState` | ✅ |
| Backend sem suporte a actions | Degradação honesta — sem mocks, 3 endpoints reais usados | ✅ |

#### Dialog (`CreateActionFromRecommendationDialog`)

| Cenário | Comportamento | Estado |
|---|---|---|
| 401 sessão expirada | `resolveErrorPreset` → Alert "Session expired" + `notifyUnauthorized()` global | ✅ |
| 403 sem permissão | `resolveErrorPreset` → Alert "Access denied" | ✅ |
| 404 campanha/acção inexistente | `resolveErrorPreset` → Alert "Not found" | ✅ |
| 422 — campo visível (title) | Inline field error via `ValidationError.fieldErrors` | ✅ |
| 422 — campo visível (content_pack) | Inline field error via `ValidationError.fieldErrors` | ✅ |
| 422 — campo derivado (artist, campaign) | `visibleFieldErrored = false` → Alert "Invalid request" / "Some of the submitted data was rejected." (**CORRIGIDO**) | ✅ |
| 422 com field errors em campos visíveis | `visibleFieldErrored = true` → `generalError = null` (sem duplicação) | ✅ |
| 502/503 serviço indisponível | `resolveErrorPreset` → Alert "Service unavailable" | ✅ |
| Network error | `resolveErrorPreset` → Alert "Connection problem" | ✅ |
| Close durante loading (busy) | `handleClose` bloqueia — não fecha enquanto `isPending` | ✅ |
| Escape durante loading (busy) | `Dialog.handleCancel` → `handleClose` → bloqueado por `busy` | ✅ |

#### Button (`CreateActionFromRecommendationButton`)

| Cenário | Comportamento | Estado |
|---|---|---|
| `actionsQuery` em loading | `actionsQuery.data = undefined` → `matchRecommendationAction(draft, undefined)` → `null` → mostra "Create action" | ✅ |
| `actionsQuery` com erro | Mesmo que loading → mostra "Create action" (degradação segura, sem crash) | ✅ |
| `campaign` ainda a carregar | `campaign = undefined` → `ready = false` → botão disabled | ✅ |

#### Isolamento da War Room

| Componente | Impacto de falha em `CampaignActionsPanel` | Estado |
|---|---|---|
| Campaign Header | Não afectado — query independente | ✅ |
| Intelligence section | Não afectada — query independente | ✅ |
| Content Outputs panel | Não afectado — query independente | ✅ |
| Reports panel | Não afectado — query independente | ✅ |
| Media Kits panel | Não afectado — query independente | ✅ |

A `CampaignActionsPanel` renderiza o seu `ErrorState` dentro do `Card` — uma falha
limita-se ao painel, não propaga para a página nem para outros painéis.

O `actionsQuery` na página serve apenas para passar `actionsQuery.data` ao botão
por-recommendation. Erro nesta query → `data = undefined` → botão mostra
"Create action" — não quebra nada.

---

### Auditoria de segurança

#### `X-Internal-Token` / tokens internos

| Verificação | Resultado |
|---|---|
| `X-Internal-Token` enviado como header | ❌ Nunca enviado — `client.ts:64` intercepta e descarta qualquer tentativa, com aviso em dev |
| `INTERNAL_API_TOKEN` em `src/` | ❌ Não encontrado |
| `X-Internal-Token` em `src/` | Apenas em `client.ts` (guard defensivo) e comentário de `campaign-action-api.ts` — nunca como header enviado |

#### Chamadas directas a serviços internos

| Verificação | Resultado |
|---|---|
| Referências a `intelligence_engine` em `src/` | ❌ Não encontrado (apenas em `docs/`, que é correcto) |
| Referências a `content_renderer` em `src/` | ❌ Não encontrado |
| Portas internas (`:8001`, `:8002`, etc.) em `src/` | ❌ Não encontrado |
| Toda a rede passa por `apiClient` → Backend Core | ✅ |

#### Environment e secrets

| Verificação | Resultado |
|---|---|
| `.env.example` contém secrets | ❌ Apenas `VITE_BACKEND_API_BASE_URL=http://localhost:8000/api/v1` |
| `.env.example` tem nota de segurança | ✅ "never add X-Internal-Token or any service-to-service secret here" |
| `.env.local` contém secrets | ❌ Apenas `VITE_BACKEND_API_BASE_URL` |
| Stack traces ou tokens em UI de erro | ❌ `resolveErrorPreset` e `ErrorState` nunca expõem stack/tokens |

---

### Ficheiros criados ou alterados

**Alterado:**
- `shared/ui/states/error-presets.ts` — correcção na branch `ValidationError`:
  removida dependência em `error.message` (que podia ser texto HTTP de status
  como "Unprocessable Content"); a descrição é agora sempre
  "Some of the submitted data was rejected." — copy clara, sem jargão técnico.

  ```ts
  // Antes:
  description: error.message || 'Some of the submitted data was rejected.',

  // Depois:
  description: 'Some of the submitted data was rejected.',
  ```

  **Fundamento**: Para 422 com erros apenas em campos derivados (ex.: `artist`,
  `campaign`), `error.message` era preenchido por `extractMessage` com
  `response.statusText` ("Unprocessable Content" / "Unprocessable Entity") porque
  o corpo DRF não tem campo `detail`. O utilizador via "Unprocessable Content" no
  alert — texto HTTP, não user-facing. Os field errors em campos visíveis
  continuam a ser surfaced inline; o alert geral é para os restantes casos.

**Criado:**
- `docs/.../resultados_execucao/prompt_07_erros_seguranca_resultado.md` (este ficheiro).

**Não alterados** (confirmados correctos por auditoria):
- `shared/api/client.ts` — guard de `X-Internal-Token`, `notifyUnauthorized`, mapeamento completo de erros HTTP.
- `shared/api/errors.ts` — hierarquia de erros completa.
- `shared/ui/states/ErrorState.tsx` — routing correcto 401→SessionExpired, 403→PermissionDenied, 404→NotFoundState, 502/503→ServiceUnavailable.
- `entities/campaign-action/campaign-action-api.ts` — `Promise.allSettled` com resiliência parcial.
- `widgets/campaign-actions-panel/CampaignActionsPanel.tsx` — guard workspace + ErrorState por tipo.
- `features/campaign-actions/CreateActionFromRecommendationDialog.tsx` — `visibleFieldErrored` guard correcto.
- `pages/campaign-war-room/CampaignWarRoomPage.tsx` — isolamento de queries independentes.

---

### Validações executadas e resultado

- ✅ `pnpm lint` → `eslint .` sem erros nem avisos.
- ✅ `pnpm build` → `tsc -b && vite build`, 230 módulos, 366ms, sem erros de tipo.
- ✅ Greps de segurança:
  - `X-Internal-Token` / `INTERNAL_TOKEN` — apenas no guard defensivo de `client.ts` e doc de `campaign-action-api.ts`. Nunca enviado.
  - `INTERNAL_API_TOKEN` — não encontrado em `src/`.
  - `intelligence_engine` / `content_renderer` — não encontrado em `src/`.
  - Portas internas — não encontradas em `src/`.
  - `.env.example` / `.env.local` — sem secrets.
- ➖ `python manage.py check` — **não aplicável**: nenhum contrato/código backend foi alterado nesta fase. Todos os prompts foram frontend-only.
- ➖ Browser — **não usado**, conforme instrução.

---

### Pendências, riscos e próximo passo recomendado

- **CA-013 (doc de arquitectura da feature)** — por fazer.
- **CA-014 (validação integrada real)** — bloqueada até iteração com browser habilitado.
- **CA-015 (relatório final da fase)** — por fazer.
- **CA-011 (ligar actions a outputs existentes)** — não abordado; só possível via metadata.
- **Melhoria futura (CA-009/CA-RSK-003)**: quando `actionsQuery` erra, o botão
  mostra "Create action" em vez do estado da acção existente — pode levar a
  duplicação se o utilizador criar nova acção sem saber que já existe uma. Comportamento
  documentado; mitigação completa exige CA-PDEC-006 (entidade persistente no backend).
- **Melhoria futura de mensagens 422**: se no futuro o Backend Core passar a retornar
  `{ "detail": "mensagem_útil" }` em 422, considerar restaurar `error.message` para
  `ValidationError` em `resolveErrorPreset` — actualmente ignorado para evitar
  texto HTTP de status.
