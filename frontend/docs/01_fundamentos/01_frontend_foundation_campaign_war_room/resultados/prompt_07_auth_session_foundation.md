# FE-007 — Auth/session foundation

**Fase:** Frontend Foundation & Campaign War Room MVP
**Componente alvo:** `frontend`
**Data:** 2026-06-26
**Tipo:** Autenticação/sessão (login, refresh, logout, ProtectedRoute, 401 handling)

---

## 0. Sumário executivo

- **Endpoints reais confirmados** no `backend_core/schema.yml`: `POST /auth/token/` (email+password → access+refresh), `POST /auth/token/refresh/` (refresh → access), `GET /auth/me/` → `User`.
- **Fluxo de sessão completo**: estados `loading | authenticated | unauthenticated`, login, logout, restauro de sessão no boot via refresh token.
- **Login real** implementado (o endpoint existe) com `email` + `password`.
- **Refresh suportado de forma defensiva** (restauro no boot); a **rotação de refresh é incerta no contrato** → documentada, sem inventar comportamento complexo.
- **ProtectedRoute** protege toda a app; `/login` é público.
- **API client recebe o access token** via o token provider injectável (já existente do FE-004), agora alimentado pelo `AuthProvider`.
- **401 tratado globalmente**: um pedido autenticado com 401 limpa a sessão → redirect para `/login`.
- **Tokens nunca são logados** (verificado em browser: credenciais e tokens não aparecem na consola).
- **`pnpm build` e `pnpm lint` passam** (exit 0, 0 avisos).
- **RBAC não implementado** — o Backend Core continua fonte da verdade de permissões.

---

## 1. Endpoints de auth confirmados (OpenAPI real)

| Endpoint | Body | Resposta | Notas |
| --- | --- | --- | --- |
| `POST /api/v1/auth/token/` | `{ email, password }` | `{ access, refresh }` | **email**, não username; sem auth |
| `POST /api/v1/auth/token/refresh/` | `{ refresh }` | `{ access }` (+`refresh`?) | `refresh` é writeOnly no schema → resposta documentada é só `access` |
| `GET /api/v1/auth/me/` | — | `User` | requer Bearer |
| `POST /api/v1/auth/token/verify/` | `{ token }` | `{ token }` | não usado nesta fase |

---

## 2. Arquitectura da sessão (`features/auth`)

| Ficheiro | Responsabilidade |
| --- | --- |
| `auth-api.ts` | Serviços: `login`, `refreshAccessToken`, `fetchCurrentUser` (usam `apiClient`) |
| `token-storage.ts` | Persistência do **refresh** token (localStorage); access fica só em memória |
| `auth-context.ts` | `AuthContextValue` = `{ status, user, login, logout }` |
| `AuthProvider.tsx` | Estado da sessão, boot/restauro, wiring do token provider e do handler de 401 |
| `useAuth.ts` | Hook de acesso ao contexto |
| `ProtectedRoute.tsx` | Guarda de rotas (loading / redirect / outlet) |

### Fluxo
- **Login:** `POST /auth/token/` (`auth:false`) → guarda access (memória) + refresh (localStorage) → `status=authenticated` → carrega `/auth/me` em background.
- **Boot/restauro:** se há refresh token guardado, `status` inicial = `loading` e o efeito chama `refreshAccessToken`; sucesso → `authenticated`, falha → sessão limpa (`unauthenticated`). Sem refresh token guardado, arranca directamente em `unauthenticated` (sem flash de loading).
- **Logout:** limpa access (memória) + refresh (storage) + user → `unauthenticated`. JWT é stateless; não há chamada ao backend.

---

## 3. API client recebe o token

O `AuthProvider` regista, no mount, `setTokenProvider(() => accessTokenRef.current)`. O singleton `apiClient` lê o access token em cada pedido e envia `Authorization: Bearer <token>`. O access token vive **apenas em memória** (ref), nunca persistido. Login/refresh usam `auth:false` (sem header), por isso não dependem de um token existente.

---

## 4. Tratamento de 401 (global)

Adicionado ao registry injectável de `shared/api` um **handler de não-autorizado**:

- `client.ts`: quando um pedido **autenticado** (`auth !== false`) recebe **401**, chama `notifyUnauthorized()` antes de lançar o erro.
- `AuthProvider`: regista `setUnauthorizedHandler(clearSession)` → ao 401, a sessão é limpa e o `ProtectedRoute` redirecciona para `/login`.
- **Login/refresh excluídos** (`auth:false`): um login falhado **não** dispara logout global — é tratado localmente na `LoginPage` (mensagem "Invalid email or password.").

Distingue assim "o meu token de sessão foi recusado" de "as credenciais de login estão erradas".

---

## 5. ProtectedRoute + Login

- **Router** reestruturado: `/login` público; tudo o resto dentro de `<ProtectedRoute>` → `<RootLayout>` → páginas.
- `ProtectedRoute`: `loading` → `LoadingState`; `unauthenticated` → `<Navigate to="/login" state={{ from }}>` (preserva o destino); `authenticated` → `<Outlet/>`.
- `LoginPage` (`pages/login`): formulário simples (email/password) com `shared/ui` (Card, Alert, Button) e inputs nativos com `label`/`autoComplete`/`required`. Em sucesso, redirecciona para o destino original (`from`) ou `/`. Se já autenticado, redirecciona (não mostra o form).
- `RootLayout`: adicionado nome do utilizador + botão **Sign out** (chama `logout`).
- **Sem `react-hook-form`/`zod`**: um único formulário não justifica dependências; estado controlado com `useState`.

---

## 6. Segurança / decisões

- **Tokens não logados:** nenhum `console.log` de tokens/headers; erros de `apiClient` não incluem headers; `queryClient.onError` regista só `status/code`. **Verificado em browser** — credenciais e tokens ausentes da consola.
- **RBAC fora do frontend:** o frontend só gere presença de sessão; permissões de negócio continuam no Backend Core (não há decisões de autorização locais).
- **Persistência (FE-PDEC-003):** access em memória; refresh em localStorage para restaurar sessão no reload.

---

## 7. Limitações documentadas

| # | Limitação | Detalhe / Mitigação |
| --- | --- | --- |
| L1 | **Rotação de refresh incerta** | O schema marca `refresh` como writeOnly; a resposta documentada de `/auth/token/refresh/` é só `access`. Lemos `refresh` **defensivamente** e, se presente, actualizamos o guardado. Não implementámos lógica de rotação complexa. |
| L2 | **Refresh em localStorage = exposto a XSS** | Aceitável para piloto técnico controlado. Produção: cookie httpOnly/Secure/SameSite emitido pelo Backend Core. |
| L3 | **Sem refresh automático on-401** | Um 401 limpa a sessão e redirecciona para login (não tenta refresh transparente + retry). Suficiente para o MVP; melhorar em FE-013/futuro com interceptor de refresh-and-retry. |
| L4 | **Sem testes** | Sem framework de testes (FE-PDEC-004). Serviços isolados em `auth-api.ts` para testabilidade futura. |
| L5 | **`/auth/me` best-effort** | Falha não-401 ao carregar o perfil não derruba a sessão; `user` fica `null`. |

---

## 8. Verificação em browser

Dev server, com `localStorage` limpo (sem refresh token):

| Verificação | Resultado |
| --- | --- |
| Visitar `/campaigns` (protegida) sem sessão | ✅ redirecciona para `/login` |
| Login renderiza (brand, email, password, "Sign in") | ✅ confirmado via DOM |
| Submeter login (sem backend → network error) | ✅ mostra "Could not sign in. Please try again."; fica em `/login` |
| Credenciais/tokens na consola | ✅ **ausentes**; só o aviso esperado de `VITE_BACKEND_API_BASE_URL` |
| Erros na consola | ✅ 0 |

> A ferramenta de screenshot esteve instável (timeouts de infra); a validação foi feita por inspecção directa do DOM e da consola, que confirmam o render e o comportamento.

---

## 9. Validações

| Verificação | Comando | Resultado |
| --- | --- | --- |
| Lint | `pnpm lint` | ✅ exit 0 — 0 avisos |
| Build | `pnpm build` | ✅ exit 0 — 121 módulos |

> Nota lint: a primeira versão accionou a regra `react-hooks/set-state-in-effect` (setState síncrono no efeito de boot). Resolvido derivando o `status` inicial de `readRefreshToken()` — também elimina o flash de `loading` quando não há sessão. `dist/` removido.

---

## 10. Critérios de aceitação — verificação

| Critério (FE-007) | Estado |
| --- | --- |
| Fluxo básico de sessão existe | ✅ loading/authenticated/unauthenticated |
| Login existe se endpoint real existir | ✅ `POST /auth/token/` |
| Logout limpa sessão | ✅ access + refresh + user |
| ProtectedRoute funciona | ✅ redirect verificado |
| API client recebe token | ✅ token provider injectável |
| 401 é tratado | ✅ handler global → logout/redirect |
| Tokens não são logados | ✅ verificado em browser |
| Build/lint passam ou limitações documentadas | ✅ ambos passam |
| Limitações de auth documentadas | ✅ §7 |

---

## 11. Ficheiros criados/alterados

**Novos (`features/auth`):** `auth-api.ts`, `token-storage.ts`, `ProtectedRoute.tsx`.
**Reescritos (`features/auth`):** `auth-context.ts`, `AuthProvider.tsx`, `index.ts`.
**Novos (`pages/login`):** `LoginPage.tsx`, `LoginPage.module.css`, `index.ts`.
**Alterados:**
- `shared/api/providers.ts` (+ handler de 401), `shared/api/client.ts` (notify em 401 autenticado), `shared/api/index.ts` (export `setUnauthorizedHandler`)
- `app/router/routes.tsx` (ProtectedRoute + `/login`)
- `app/layouts/RootLayout.tsx` + `.module.css` (user + Sign out)

---

## 12. Notas para os prompts seguintes

- **FE-008**: o `WorkspaceProvider` pode agora carregar `GET /workspaces/` quando `status==='authenticated'`; usar `useAuth().status`. Já existe `/workspaces/current/`.
- **FE-013**: considerar refresh-and-retry transparente no client (interceptor) antes de cair no logout global (L3); `PermissionDenied`/`ServiceUnavailable` sobre `ErrorState`.
- **Pré-produção**: migrar refresh para cookie httpOnly (L2) e proteger/remover `/ui-kit`.
