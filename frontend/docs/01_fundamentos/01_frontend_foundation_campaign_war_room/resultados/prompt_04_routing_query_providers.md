# FE-004 — Routing, server state e providers globais

**Fase:** Frontend Foundation & Campaign War Room MVP
**Componente alvo:** `frontend`
**Data:** 2026-06-26
**Tipo:** Instalação de dependências + providers globais + router + páginas placeholder

---

## 0. Sumário executivo

- **Compatibilidade confirmada antes de instalar** (FE-RSK-008): `react-router-dom@7.18.0` (peer `react >=18`) e `@tanstack/react-query@5.101.1` (peer `^18 || ^19`) — ambos compatíveis com React 19.2. Instalados **um de cada vez**, com `tsc -b` a passar entre cada.
- Criado **`AppProviders`** compondo `QueryClientProvider → AuthProvider → WorkspaceProvider`.
- **`QueryClient`** com defaults adequados: retry conservador (nunca em 4xx), `staleTime` 30s, sem refetch on focus, e `onError` que regista **resumo sem dados sensíveis**.
- **Router** (`createBrowserRouter`) com as 6 rotas pedidas; `RootLayout` passou a usar `<Outlet />` + navegação.
- **AuthProvider** e **WorkspaceProvider** iniciais + hooks **`useAuth`** e **`useWorkspace`**. Ligam-se ao API client via os providers injectáveis do FE-003 (`setTokenProvider`/`setWorkspaceProvider`).
- **Render verificado em browser** (preview): Dashboard e rota aninhada `/campaigns/:id/war-room` renderizam, param lido, nav activa correcta, **0 erros na consola**.
- **`pnpm build` e `pnpm lint` passam** (exit 0, 0 avisos).
- Fluxo completo de auth e War Room real **não** implementados (conforme instrução).

---

## 1. Dependências instaladas

| Pacote | Versão | Peer deps | Compatível c/ stack |
| --- | --- | --- | --- |
| `react-router-dom` | 7.18.0 | `react >=18`, `react-dom >=18` | ✅ React 19.2 |
| `@tanstack/react-query` | 5.101.1 | `react ^18 || ^19` | ✅ React 19.2 |

Procedimento (mitiga FE-RSK-008): instalar isolado → `pnpm exec tsc -b` (exit 0) → instalar o seguinte → `tsc -b` (exit 0) → `lint` + `build` finais. Nenhum conflito de peer dependencies.

---

## 2. Server state — `app/providers/queryClient.ts`

`QueryClient` com `defaultOptions`:

| Opção | Valor | Razão |
| --- | --- | --- |
| `queries.retry` | função `shouldRetry` | **Nunca** repete erros 4xx (`ApiError.status` 400–499); repete 5xx/rede até 2× |
| `queries.staleTime` | `30_000` (30s) | Evita refetch storms durante navegação |
| `queries.gcTime` | `5 * 60_000` (5min) | Retenção de cache razoável |
| `queries.refetchOnWindowFocus` | `false` | Evita refetch agressivo no MVP |
| `mutations.retry` | `false` | Mutações (ex.: intelligence POST) não devem repetir cegamente |

**Erro sem logs sensíveis:** `QueryCache.onError` regista, **só em DEV**, um resumo `status=… code=…` + `message`. Como `ApiError` nunca transporta token/headers (FE-003), o log é seguro. Em produção não regista nada.

---

## 3. Providers globais

### 3.1 `AppProviders` (`app/providers/AppProviders.tsx`)
Composição única:
```
QueryClientProvider (queryClient)
  └─ AuthProvider
       └─ WorkspaceProvider
            └─ children
```

### 3.2 `AuthProvider` inicial (`features/auth`)
- Mantém `accessToken` em **memória** (state + ref).
- **Regista o token provider uma vez** no mount: `setTokenProvider(() => tokenRef.current)` → o `apiClient` passa a enviar `Authorization: Bearer` assim que houver token.
- Expõe `useAuth(): { status, accessToken, setAccessToken, clearAuth }`. `status` derivado: `authenticated` se há token, senão `unauthenticated` (`loading` reservado para o refresh do FE-007).
- **Não** implementa login/refresh (FE-007). Só a infra-estrutura.
- Ficheiros separados (`auth-context.ts` / `AuthProvider.tsx` / `useAuth.ts`) para não disparar avisos de `react-refresh` (componente isolado do contexto/hook).

### 3.3 `WorkspaceProvider` inicial (`features/workspace-switching`)
- Mantém `workspaceId`, **persistido em `localStorage`** (`mf.active_workspace_id`), com leitura inicial e escrita protegidas por try/catch.
- **Regista o workspace provider** no mount: `setWorkspaceProvider(() => workspaceRef.current)` → `apiClient` envia `X-Workspace-ID` quando há workspace activo.
- Expõe `useWorkspace(): { workspaceId, setWorkspaceId }`.
- **Não** carrega lista de workspaces nem mostra switcher (FE-008). Só selecção + persistência + plumbing.

### 3.4 ApiProvider?
Decisão: **não criar `ApiProvider`**. O API client já é um singleton (`apiClient`) que lê credenciais via o registry injectável. Auth/Workspace providers fazem a injecção via `setTokenProvider`/`setWorkspaceProvider` — mais simples e sem prop-drilling do client. (Hook `useApiClient` pode ser adicionado depois se necessário; não é preciso agora.)

---

## 4. Routing — `app/router`

`createBrowserRouter` (data router idiomático do react-router v7). `RootLayout` é o elemento raiz e renderiza a rota activa via `<Outlet />`.

| Rota | Elemento |
| --- | --- |
| `/` (index) | `DashboardPage` |
| `/campaigns` | `CampaignsPage` |
| `/campaigns/:campaignId` | `CampaignDetailPage` |
| `/campaigns/:campaignId/war-room` | `CampaignWarRoomPage` |
| `/settings` | `SettingsPage` |
| `*` | `NotFoundPage` |

Ficheiros: `routes.tsx` (árvore + `export const router`), `AppRouter.tsx` (`<RouterProvider router={router} />`), `index.ts`. `App.tsx` reduzido a `AppProviders > AppRouter`.

`RootLayout` ganhou navegação (`NavLink` Dashboard/Campaigns/Settings) com estado activo via `aria-current` + tokens; CSS Module actualizado.

### Páginas placeholder
Criadas (honestas, sem dados falsos): `dashboard`, `campaigns`, `campaign-detail` (lê `useParams().campaignId` + `Link` relativo para `war-room`), `campaign-war-room`, `settings`. `not-found` já existia (FE-002). Cada uma com `index.ts`.

---

## 5. Verificação de render (browser)

Servido o dev server via preview e validado:

| Verificação | Resultado |
| --- | --- |
| `/` (Dashboard) renderiza | ✅ tokens, layout e nav aplicados; "Dashboard" activo |
| Navegação para `/campaigns/abc-123/war-room` | ✅ renderiza; **param lido** (`Campaign ID: abc-123`); nav "Campaigns" activa |
| SPA fallback (curl `/campaigns/abc/war-room`) | ✅ HTTP 200 |
| Consola — erros | ✅ **0 erros** |
| Consola — avisos | ⚠️ apenas o aviso **esperado** de fallback `VITE_BACKEND_API_BASE_URL` (FE-003), por não haver `.env.local` |

---

## 6. Validações

| Verificação | Comando | Resultado |
| --- | --- | --- |
| Typecheck após cada install | `pnpm exec tsc -b` | ✅ exit 0 (×2) |
| Lint | `pnpm lint` | ✅ exit 0 — 0 avisos |
| Build | `pnpm build` | ✅ exit 0 — 82 módulos |
| Render em browser | preview + screenshot + console | ✅ §5 |

> O `dist/` de validação foi removido. O `.claude/launch.json` (config do dev server `frontend`) foi criado para o preview e fica disponível para uso futuro.

---

## 7. Critérios de aceitação — verificação

| Critério (FE-004) | Estado |
| --- | --- |
| react-router-dom instalado e configurado | ✅ 7.18.0 + router |
| @tanstack/react-query instalado e configurado | ✅ 5.101.1 + QueryClient |
| AppProviders existe | ✅ |
| Routing funciona | ✅ render verificado em browser |
| QueryClientProvider configurado | ✅ defaults conservadores |
| AuthProvider inicial existe | ✅ + `useAuth` |
| WorkspaceProvider inicial existe | ✅ + `useWorkspace` |
| Rotas básicas renderizam | ✅ §5 |
| Build/lint passam ou limitações documentadas | ✅ ambos passam |

---

## 8. Ficheiros criados/alterados

**Dependências:** `package.json` / `pnpm-lock.yaml` (+ react-router-dom, +@tanstack/react-query).

**Novos:**
- `app/providers/{queryClient.ts, AppProviders.tsx, index.ts}`
- `app/router/{routes.tsx, AppRouter.tsx, index.ts}`
- `features/auth/{auth-context.ts, AuthProvider.tsx, useAuth.ts, index.ts}`
- `features/workspace-switching/{workspace-context.ts, WorkspaceProvider.tsx, useWorkspace.ts, index.ts}`
- `pages/dashboard`, `pages/campaigns`, `pages/campaign-detail`, `pages/campaign-war-room`, `pages/settings` (cada `*.tsx` + `index.ts`)
- `.claude/launch.json` (config do dev server para preview)

**Alterados:**
- `App.tsx` (composição root), `app/layouts/RootLayout.tsx` (+ `Outlet` + nav), `RootLayout.module.css` (+ estilos de nav)

**Removidos:** `.gitkeep` das slices agora preenchidas (`app/providers`, `app/router`, `features/auth`, `features/workspace-switching`, `pages/{dashboard,campaigns,campaign-detail,campaign-war-room}`).

---

## 9. Notas para os prompts seguintes

- **FE-005**: as páginas placeholder devem passar a usar os componentes de `shared/ui` (PageHeader, Card, estados). Já há onde os aplicar.
- **FE-007**: implementar login (`POST /auth/token/` com `auth:false`), refresh e `ProtectedRoute` (envolver rotas no router); usar `setAccessToken`/`clearAuth` já existentes; preencher `status: 'loading'` durante o refresh inicial.
- **FE-008**: carregar `GET /workspaces/`, popular o switcher no `RootLayout`/app-shell, e **invalidar queries** (`queryClient.invalidateQueries`) ao trocar de workspace.
- **Aviso de fallback**: definir `VITE_BACKEND_API_BASE_URL` em `.env.local` silencia o aviso de dev; é comportamento intencional do FE-003.
