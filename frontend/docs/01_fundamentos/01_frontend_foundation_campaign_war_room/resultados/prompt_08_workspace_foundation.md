# FE-008 — Workspace foundation

**Fase:** Frontend Foundation & Campaign War Room MVP
**Componente alvo:** `frontend`
**Data:** 2026-06-26
**Tipo:** Fundação de workspace (listagem, selecção, `X-Workspace-ID`, invalidação de queries)

---

## 0. Sumário executivo

- **Endpoint confirmado** no `backend_core/schema.yml`: `GET /api/v1/workspaces/` → `PaginatedWorkspaceList`, **só JWT** (listagem não requer `X-Workspace-ID`). Existe também `GET /workspaces/current/` (resolve via header).
- **`WorkspaceProvider` completado**: carrega os workspaces (quando autenticado via TanStack Query), resolve um workspace activo (preferência persistida, com fallback para o primeiro), e expõe o id ao API client como **`X-Workspace-ID`**.
- **Selector de workspace** (`WorkspaceSwitcher`) no app shell (RootLayout), com estados loading / empty / error / ready.
- **Troca de workspace invalida queries scoped** (todas excepto a lista de workspaces) → refetch sob o novo workspace.
- **Estados tratados:** unauthenticated, loading, error, empty e "selecção já não existe" (reconciliação com fallback).
- **`X-Workspace-ID` verificado em browser** (deterministicamente, via o `apiClient` real): header enviado, sem `X-Internal-Token`.
- **`pnpm build` e `pnpm lint` passam** (exit 0, 0 avisos).
- Membership/permissões **não duplicadas** — Backend Core continua fonte da verdade.

---

## 1. Endpoint confirmado

| Endpoint | Auth | Resposta | Notas |
| --- | --- | --- | --- |
| `GET /api/v1/workspaces/` | JWT | `PaginatedWorkspaceList` | listagem scoped às memberships activas; params `page`, `page_size`, `search`, `ordering`; **sem** `X-Workspace-ID` |
| `GET /api/v1/workspaces/current/` | JWT + `X-Workspace-ID` | `Workspace` | resolve o workspace activo a partir do header |

Usámos a **listagem** para popular o switcher (`page_size=100`, suficiente — um utilizador pertence a poucos workspaces).

---

## 2. Arquitectura (`features/workspace-switching`)

| Ficheiro | Responsabilidade |
| --- | --- |
| `workspace-api.ts` | `fetchWorkspaces()` (usa `apiClient`) |
| `useWorkspaces.ts` | Query TanStack (`WORKSPACES_QUERY_KEY`), `enabled` por autenticação, `select → results` |
| `workspace-context.ts` | `WorkspaceContextValue` + `WorkspaceStatus` + chave de storage |
| `WorkspaceProvider.tsx` | Carrega, reconcilia activo, injecta header, invalida queries na troca |
| `useWorkspace.ts` | Hook de acesso ao contexto |
| `WorkspaceSwitcher.tsx` | Selector no app shell, com estados |

### Resolução do workspace activo
- `preferredId` (escolha do utilizador) seeded de `localStorage`.
- `activeWorkspace = workspaces.find(id===preferredId) ?? workspaces[0]` → se o id guardado **já não existe**, cai para o primeiro (e re-persiste).
- Um efeito sincroniza o **ref** lido pelo API client + `localStorage` com o id resolvido (escreve só ref/storage, **sem setState** → cumpre `react-hooks/set-state-in-effect`).

---

## 3. `X-Workspace-ID` no API client

O `WorkspaceProvider` regista no mount `setWorkspaceProvider(() => workspaceRef.current)`. O `apiClient` (FE-003) constrói o header `X-Workspace-ID` a partir desse getter em cada pedido. O access token (FE-007) e o workspace id são injectados pelo mesmo mecanismo de providers injectáveis — `shared` não depende de `app`/`features`.

### Verificação determinística (browser, sem backend)
Via `import('/src/shared/api/index.ts')` + spy de `fetch`, exercitando o `apiClient` real:

```
setWorkspaceProvider(() => 'ws-test-123'); setTokenProvider(() => 'tok-abc');
await apiClient.get('/campaigns/')
→ headers = { accept, authorization: "Bearer tok-abc", x-workspace-id: "ws-test-123" }
→ x-internal-token: ausente ✓
→ url: http://localhost:8000/api/v1/campaigns/
```

Prova que `X-Workspace-ID` é enviado e que `X-Internal-Token` nunca aparece.

---

## 4. Invalidação de queries na troca

`setWorkspaceId(id)`:
1. actualiza `workspaceRef.current = id` (header passa a usar o novo id **antes** de qualquer refetch);
2. persiste em `localStorage`;
3. `setPreferredId(id)` (re-render);
4. `queryClient.invalidateQueries({ predicate: q => q.queryKey[0] !== 'workspaces' })` → refetch de todos os dados scoped ao workspace, **excepto** a própria lista de workspaces (que é independente do workspace activo).

---

## 5. Estados de workspace

| Estado | Quando | UI no switcher |
| --- | --- | --- |
| `unauthenticated` | sem sessão | switcher oculto (não há fetch) |
| `loading` | a carregar workspaces | "Loading workspaces…" |
| `error` | fetch falhou | "Couldn't load workspaces" + **Retry** |
| `empty` | utilizador sem workspaces | "No workspace" |
| `ready` | há workspaces + activo | `<select>` com os nomes |
| *(selecção inexistente)* | id guardado não está na lista | reconciliação silenciosa → fallback para o primeiro + re-persist |

---

## 6. Decisões / limitações

- **Não duplicar permissões:** o frontend só escolhe o workspace activo e envia o header; membership e permissões são validadas pelo Backend Core (FE-RSK não violado).
- **`<select>` nativo** para o switcher — acessível (`aria-label`), sem dependências de UI pesadas.
- **Verificação E2E limitada pelo ambiente:** sem backend disponível, não é possível atingir o estado `authenticated` pela app e observar o switcher populado/loading/error com dados reais. A injecção de `X-Workspace-ID` foi, ainda assim, **verificada deterministicamente** (§3); os estados do switcher estão cobertos por código e por build/lint. Validação com dados reais fica para a fase com Backend Core a correr.
- **`workspaces/current/`** não é usado nesta fase (a lista já dá tudo o que o switcher precisa); fica disponível para validação futura do header.

---

## 7. Validações

| Verificação | Comando / método | Resultado |
| --- | --- | --- |
| Lint | `pnpm lint` | ✅ exit 0 — 0 avisos |
| Build | `pnpm build` | ✅ exit 0 — 132 módulos |
| `X-Workspace-ID` enviado | browser, fetch spy sobre `apiClient` real | ✅ presente; `X-Internal-Token` ausente |
| App boota sem erros | preview + console | ✅ 0 erros |

> `dist/` removido após validação.

---

## 8. Critérios de aceitação — verificação

| Critério (FE-008) | Estado |
| --- | --- |
| Workspace activo existe | ✅ resolvido (preferência + fallback) |
| X-Workspace-ID é enviado nas chamadas | ✅ verificado em browser |
| Selector de workspace existe | ✅ `WorkspaceSwitcher` no shell |
| Troca de workspace invalida queries relevantes | ✅ `invalidateQueries` (exclui a lista) |
| Estado sem workspace é tratado | ✅ unauthenticated/loading/error/empty + reconciliação |
| Build/lint passam ou limitações documentadas | ✅ ambos passam |

---

## 9. Ficheiros criados/alterados

**Novos (`features/workspace-switching`):** `workspace-api.ts`, `useWorkspaces.ts`, `WorkspaceSwitcher.tsx`, `WorkspaceSwitcher.module.css`.
**Reescritos:** `workspace-context.ts`, `WorkspaceProvider.tsx`, `index.ts`.
**Alterados:** `app/layouts/RootLayout.tsx` (render do `WorkspaceSwitcher`).

---

## 10. Notas para os prompts seguintes

- **FE-009/010/011**: os hooks de campanha/intelligence herdam automaticamente `X-Workspace-ID`. Os seus query keys devem incluir o `workspaceId` (ou ser invalidados na troca — já tratado pelo predicate). Recomenda-se incluir `workspaceId` na queryKey para cache correcto por workspace.
- **Estado `empty`/`error` de workspace**: páginas que dependem de um workspace activo devem considerar bloquear/avisar quando `status !== 'ready'`.
- **Validação com backend**: confirmar `X-Workspace-ID` end-to-end e o comportamento de `403` quando o workspace não pertence ao utilizador (tratado globalmente como `ForbiddenError`).
