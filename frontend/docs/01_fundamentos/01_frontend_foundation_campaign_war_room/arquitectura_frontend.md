# Arquitectura do Frontend — MomentFlow/ChartRex

**Âmbito:** `frontend/`
**Fase:** Frontend Foundation & Campaign War Room MVP (FE-001 a FE-015)
**Estado:** fundação implementada, piloto técnico controlado — **não production-ready**
**Última actualização:** 2026-06-26

Este documento é a referência prática para qualquer pessoa (ou IA local) que continue a desenvolver o frontend. Não substitui o backlog (`01_backlog.md`) nem os relatórios em `resultados/`; consolida o que foi efectivamente construído e como evoluir sem violar as regras da fase.

---

## 1. Regra fundamental do ecossistema

```text
backend_core        → fronteira de produto, auth, workspace, permissões, orquestração
intelligence_engine  → calcula scores/moments/recommendations (FastAPI)
content_renderer     → gera assets/reports/media kits
frontend             → orquestra a experiência do utilizador
```

Fluxo obrigatório:

```text
Frontend → Backend Core → Intelligence Engine
Frontend → Backend Core → Content Renderer
```

**O frontend nunca chama directamente `intelligence_engine` nem `content_renderer`.** Toda a comunicação de rede do frontend passa por **uma única porta**: `src/shared/api/client.ts`, que aponta exclusivamente para `VITE_BACKEND_API_BASE_URL` (o Backend Core). Não existe, em nenhum ficheiro do frontend, configuração de base URL para o Intelligence Engine ou para o Content Renderer — e não deve passar a existir.

**`X-Internal-Token` nunca pertence ao frontend.** É um segredo de comunicação serviço-a-serviço (Backend Core ↔ Intelligence Engine / Content Renderer) e nunca deve estar no browser. O cliente HTTP central (`sanitizeCustomHeaders` em `client.ts`) **bloqueia activamente** qualquer tentativa de definir este header, mesmo que alguém o adicione por engano numa chamada futura — em dev emite um `console.warn`, em qualquer ambiente o header é descartado antes do `fetch`. Qualquer alteração ao API client deve preservar este bloqueio.

Se uma feature futura parecer precisar de chamar o Intelligence Engine ou o Content Renderer directamente, **a resposta correcta é criar/estender um endpoint no Backend Core**, nunca apontar o frontend para esses serviços.

---

## 2. Stack

```text
React 19.2.x + React DOM 19.2.x
TypeScript ~6.0.2 (strict)
Vite ^8.1.0
react-router-dom ^7.18.0 (createBrowserRouter / RouterProvider)
@tanstack/react-query ^5.101.1
ESLint ^10.5 + typescript-eslint ^8.61 + eslint-plugin-react-hooks/react-refresh
pnpm (packageManager fixado em package.json)
CSS Modules + design tokens (sem Tailwind, sem styled-components)
```

Não instalados nesta fase (decisão deliberada, ver §11): `zod`, `react-hook-form`, `zustand`, `date-fns`, `tailwindcss`, framework de testes. Apenas instalar quando houver necessidade concreta — confirmar sempre compatibilidade com o stack acima antes de adicionar dependências (React 19 / TS 6 / Vite 8 são recentes e quebram pacotes desactualizados).

### Scripts (`package.json`)

```bash
pnpm dev       # vite — servidor de desenvolvimento
pnpm build     # tsc -b && vite build — type-check + build de produção
pnpm lint      # eslint .
pnpm preview   # vite preview — serve o build de produção localmente
```

`pnpm build` e `pnpm lint` devem passar **sempre** antes de considerar uma alteração concluída. Se algo não passar, documentar a limitação explicitamente no relatório do prompt — nunca declarar sucesso sem evidência.

---

## 3. Estrutura de pastas

```text
src/
  app/
    config/        # app.config.ts — constantes de app (não segredos)
    layouts/        # RootLayout (shell + <Outlet/>)
    providers/      # AppProviders (compõe Query+Auth+Workspace+Router), queryClient
    router/          # routes.tsx (árvore de rotas), AppRouter, router singleton

  shared/
    api/            # client.ts, providers.ts, errors.ts, types.ts — ÚNICA porta de rede
    config/          # env.ts (VITE_BACKEND_API_BASE_URL)
    lib/              # utilitários puros (cx, …)
    types/            # tipos transversais (PaginatedResponse, Metadata, scalars)
    ui/                # Button, Card, Badge, Alert, PageHeader, Section, Skeleton,
                        # states/ (LoadingState, EmptyState, ErrorState, FeedbackBlock,
                        #          SessionExpired, PermissionDenied, NotFoundState,
                        #          ServiceUnavailable, WorkspaceRequiredState)
    styles/            # tokens.css, reset.css, global.css
    constants/, hooks/ # vazios (.gitkeep) — preencher só quando necessário

  entities/
    campaign/          # model, campaign-api, intelligence (tipos), query-keys, hooks
    content-output/    # model, content-output-api, useCampaignContentOutputs
    report/             # model, report-api, useCampaignReports
    media-kit/          # model, media-kit-api, useCampaignMediaKits
    workspace/, user/, artist/, track/  # tipos de domínio (consumo parcial nesta fase)

  features/
    auth/                       # AuthProvider, ProtectedRoute, auth-api, token-storage
    workspace-switching/        # WorkspaceProvider, WorkspaceSwitcher, workspace-api
    campaign-intelligence/      # hook + todos os painéis de intelligence
    campaign-actions/, asset-generation-status/, report-status/  # placeholders (.gitkeep)

  widgets/
    campaign-header/
    campaign-score-card/
    campaign-moments-panel/
    campaign-recommendations-panel/
    campaign-assets-panel/
    campaign-reports-panel/
    campaign-media-kits-panel/
    app-shell/   # placeholder (.gitkeep) — shell vive em app/layouts por agora

  pages/
    dashboard/, campaigns/, campaign-detail/, campaign-war-room/,
    login/, settings/, not-found/, ui-kit/ (demo interna dos componentes shared/ui)

  main.tsx, App.tsx, vite-env.d.ts
```

Cada pasta de feature/entidade/página/widget segue o padrão: ficheiro(s) de implementação + `index.ts` de barrel export. Importa-se sempre pelo barrel (`@/features/auth`, não `@/features/auth/AuthProvider`).

Alias de import: `@/*` → `./src/*` (configurado em `tsconfig.app.json` `paths` e em `vite.config.ts` `resolve.alias`, ambos sem `baseUrl` — TS 6 marca `baseUrl` standalone como deprecated).

---

## 4. Regras de dependência (FSD)

```text
app       → shared, entities, features, widgets, pages
pages     → shared, entities, features, widgets
widgets   → shared, entities, features
features  → shared, entities
entities  → shared
shared    → (nada acima; só pacotes externos)
```

**Regra prática que resolve 90% dos casos:** uma camada inferior nunca importa de uma camada superior — passa-se a informação **por props**, nunca por import ascendente. Exemplos já em uso no código:

- `entities/campaign/useCampaign.ts` recebe `workspaceId` como **parâmetro**, em vez de importar `useWorkspace` de `features/workspace-switching` (isso violaria `entities → features`).
- `features/campaign-intelligence/CampaignIntelligencePanel.tsx` recebe `workspaceId` e `campaignId` como props da página, não os lê de contexto directamente.
- `shared/api/providers.ts` expõe um **registo de funções injectáveis** (`setTokenProvider`, `setWorkspaceProvider`, `setUnauthorizedHandler`) que `shared/api/client.ts` lê em tempo de pedido. `features/auth` e `features/workspace-switching` registam-se nesse registo no boot. Isto permite que `shared` (que não pode importar `features`) ainda assim use auth/workspace em tempo de execução, sem inverter a regra de dependência.

Antes de adicionar um import, perguntar: "esta camada pode depender daquela, segundo a tabela acima?" Se não, passar dados por props ou usar o padrão de provider injectável.

### Proibições activas (verificadas nesta fase)

- Sem `src/components` genérico — UI base vive em `shared/ui`, UI de domínio em `widgets`/`features`.
- Sem chamadas de API dentro de componentes visuais — todo o acesso à rede passa por `*-api.ts` em `entities/*` ou `features/*`, consumido via hooks do TanStack Query.
- Sem estado global "para tudo" — server state vive no `QueryClient`; estado de sessão/workspace vive em contextos React dedicados (`AuthContext`, `WorkspaceContext`); não há Redux/Zustand.
- Sem mocks falsos em runtime normal — quando faltam dados reais, os componentes mostram `EmptyState`/placeholders honestos, nunca dados inventados.

---

## 5. API client (`shared/api`)

`src/shared/api/client.ts` é a **única fronteira de rede** do frontend.

```ts
import { apiClient } from '@/shared/api'

apiClient.get<T>(path, options?)
apiClient.post<T>(path, body?, options?)
apiClient.patch<T>(path, body?, options?)
apiClient.delete<T>(path, options?)
```

Comportamento por pedido:

1. `Accept: application/json` sempre; `Content-Type: application/json` quando há corpo.
2. `Authorization: Bearer <token>` injectado a partir do `tokenProvider` registado (a menos que `options.auth === false`, usado por login/refresh).
3. `X-Workspace-ID` injectado a partir do `workspaceProvider` registado, quando existir um workspace activo.
4. Headers customizados são aceites, **mas `X-Internal-Token` é sempre descartado** (`sanitizeCustomHeaders`).
5. Erros HTTP são mapeados para uma hierarquia tipada (`shared/api/errors.ts`):

```text
ApiError (base)
 ├─ ValidationError      400 / 422  (+ fieldErrors quando o backend devolve por campo)
 ├─ UnauthorizedError    401
 ├─ ForbiddenError       403
 ├─ NotFoundError        404
 ├─ ServiceUnavailableError  502 / 503
 └─ NetworkError         falha de fetch (sem resposta HTTP — backend inalcançável)
```

6. Um 401 numa chamada **autenticada** (`options.auth !== false`) dispara `notifyUnauthorized()` — o handler global registado pelo `AuthProvider`, que limpa a sessão. Chamadas de login/refresh usam `auth: false` de propósito, para que uma credencial inválida não dispare um "logout global".
7. `createApiClient(options)` é a factory; `apiClient` é o singleton de produção, com `baseUrl: ENV.apiBaseUrl` e os providers de auth/workspace já ligados. Usar sempre o singleton — só usar a factory directamente em testes.

Nunca:
- adicionar `X-Internal-Token` ou qualquer outro segredo de serviço-a-serviço;
- fazer `fetch` directo num componente — passar sempre por `apiClient` via um `*-api.ts`;
- apontar `baseUrl` para outro serviço além do Backend Core.

---

## 6. Configuração de ambiente

`src/shared/config/env.ts` lê `VITE_BACKEND_API_BASE_URL` (ex.: `http://localhost:8000/api/v1`).

- Em dev, se a variável não existir, cai para `http://localhost:8000/api/v1` com um `console.warn` (não é segredo, é só conveniência local).
- Em produção, a ausência da variável **lança erro no boot** (`EnvConfigError`) — falha alto e explícito em vez de apontar silenciosamente para `undefined`.
- Valida que o valor é um URL `http(s)` válido.
- `ENV.isDev` / `ENV.isProd` vêm de `import.meta.env.DEV/PROD`.

Não existe (e não deve existir) configuração de ambiente para Intelligence Engine ou Content Renderer no frontend.

---

## 7. Auth / sessão (`features/auth`)

- **Access token**: vive apenas em memória (`useRef` dentro do `AuthProvider`), nunca em `localStorage`/`sessionStorage`. Exposto ao API client via `setTokenProvider`.
- **Refresh token**: persistido em `localStorage` (`token-storage.ts`, chave `mf.refresh_token`) para restaurar a sessão após reload.
  - **Limitação aceite e documentada (FE-PDEC-003)**: um refresh token em `localStorage` é legível por qualquer script (exposto a XSS). Aceitável para um piloto técnico controlado; para produção, mover para cookie `httpOnly` + `Secure` + `SameSite` emitido pelo Backend Core.
- **Boot**: se existir refresh token guardado, o estado inicial é `loading` e tenta-se `refreshAccessToken`; sem refresh token, o estado inicial já é `unauthenticated` (sem round-trip desnecessário).
- **Estados**: `AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'`, mais a flag `sessionExpired` (true quando a sessão foi terminada por um 401, para distinguir de um logout normal ou de credenciais inválidas no login).
- **`ProtectedRoute`**: envolve toda a árvore de rotas excepto `/login`; redirecciona para `/login` quando `unauthenticated`.
- **Logout**: limpa o ref do access token, remove o refresh token, e repõe `unauthenticated` — não marca `sessionExpired` (é uma acção do utilizador, não uma expiração).
- **401 global**: o cliente HTTP chama `notifyUnauthorized()` → `AuthProvider` marca `sessionExpired = true` e limpa a sessão → `ProtectedRoute` redirecciona → `LoginPage` mostra "Your session has expired. Please sign in again."
- **Sem RBAC no frontend**: o Backend Core continua a ser a única fonte da verdade sobre permissões. O frontend só reage ao que o backend devolve (401/403); nunca decide sozinho se um utilizador pode ou não fazer algo.

---

## 8. Workspace (`features/workspace-switching`)

- `WorkspaceProvider` carrega os workspaces do utilizador autenticado (`useWorkspaces`), resolve o workspace activo (preferência guardada em `localStorage`, com fallback para o primeiro da lista) e expõe o id ao API client via `setWorkspaceProvider` — daí vem o header `X-Workspace-ID` em todas as chamadas autenticadas.
- `setWorkspaceId(id)` actualiza a preferência, persiste-a, e **invalida todas as queries que não sejam a própria lista de workspaces** (`predicate: q.queryKey[0] !== 'workspaces'`), forçando refetch de tudo o resto sob o novo workspace.
- Estados (`WorkspaceStatus`): `unauthenticated | loading | error | empty | ready`. Páginas que dependem de workspace devem tratar `workspaceId === null` com `<WorkspaceRequiredState />` (ver §10).
- `WorkspaceSwitcher` no app shell mostra o workspace activo e permite trocar.

**Convenção para hooks de entidade**: aceitam `workspaceId: string | null` como parâmetro explícito (nunca importam `useWorkspace` directamente, para não violar `entities → features`). A query fica `enabled: Boolean(workspaceId && ...)` para não disparar pedidos sem workspace.

---

## 9. Routing (`app/router`)

`createBrowserRouter` com árvore aninhada (`routes.tsx`):

```text
/login                                    — público
/  (ProtectedRoute → RootLayout)
  ├─ /                                    — DashboardPage
  ├─ /campaigns                           — CampaignsPage
  ├─ /campaigns/:campaignId               — CampaignDetailPage
  ├─ /campaigns/:campaignId/war-room       — CampaignWarRoomPage
  ├─ /settings                            — SettingsPage
  ├─ /ui-kit                               — UiKitPage (demo dos componentes shared/ui)
  └─ *                                     — NotFoundPage
```

`RootLayout` renderiza o shell (nav + `WorkspaceSwitcher` + `<Outlet/>`). Adicionar uma rota nova = adicionar uma entrada em `routes.tsx` dentro (ou fora, se pública) do bloco `ProtectedRoute`.

---

## 10. Server state — TanStack Query

`app/providers/queryClient.ts` define o `QueryClient` único da app:

- `retry`: nunca repete 4xx (`shouldRetry` verifica `error instanceof ApiError && status 400-499 → false`); 5xx/rede repetem até 2 vezes.
- `staleTime: 30_000` (30s) — evita refetch excessivo durante navegação normal.
- `gcTime: 5 * 60_000` (5 min).
- `refetchOnWindowFocus: false`.
- `onError` do `QueryCache` regista só `status` + `code` em dev — **nunca** o token, header `Authorization` ou URL completo.

**Convenções de uso:**
- Toda a leitura de dados do Backend Core passa por `useQuery` (mesmo o endpoint de intelligence, que é `POST` mas semanticamente uma leitura sem persistência — decisão documentada no prompt FE-010).
- Chave de query: `[entidade, workspaceId, ...resto]`, sempre com `workspaceId` primeiro, para permitir invalidação por workspace (ver `entities/campaign/query-keys.ts` como referência).
- Hooks de entidade ficam em `entities/<entidade>/use<Entidade>.ts`, devolvendo o resultado de `useQuery` directamente (sem embrulhar em mais estado).
- Mutações (quando existirem) devem usar `useMutation` com `retry: false` (já é o default global).

---

## 11. UI foundation (`shared/ui`)

Componentes base (CSS Modules, sem framework visual pesado):

```text
Button, Card, Badge, Alert, PageHeader, Section, Skeleton
```

Estados transversais em `shared/ui/states/`:

```text
LoadingState                — spinner/skeleton + label
EmptyState                  — título + descrição, sem dados (não é erro)
ErrorState                  — despachante (ver abaixo)
FeedbackBlock               — bloco base reutilizável (ícone + título + descrição + acções)
SessionExpired              — 401: sessão terminada
PermissionDenied            — 403: sem permissão no workspace actual
NotFoundState                — 404: recurso inexistente
ServiceUnavailable           — 502/503: serviço temporariamente indisponível (+ Retry)
WorkspaceRequiredState       — sem workspace activo selecionado
```

### `ErrorState` como despachante (FE-013)

`<ErrorState error={error} onRetry={...} />` inspecciona o tipo do erro e escolhe automaticamente o componente certo, **sem que cada página precise de lógica própria**:

```text
error instanceof UnauthorizedError        → <SessionExpired />
error instanceof ForbiddenError           → <PermissionDenied />
error instanceof NotFoundError            → <NotFoundState />
error instanceof ServiceUnavailableError  → <ServiceUnavailable onRetry={onRetry} />
outro (NetworkError, 422, 500, …)         → bloco genérico com copy normalizada + Retry
```

O despacho automático só acontece quando o chamador **não** sobrepõe `title`/`description` — passar esses props continua a permitir um `ErrorState` totalmente customizado quando necessário.

**Regras de privacidade que qualquer alteração a estes componentes deve preservar:**
- nunca renderizar `error.stack` ou o erro em bruto;
- nunca renderizar tokens, headers ou a URL completa do pedido;
- a copy é sempre fixa/normalizada (`error-presets.ts` / componentes dedicados), nunca o `error.message` cru exceto para `ValidationError` (mensagem do backend já pensada para o utilizador).

`Page demo`: `pages/ui-kit/UiKitPage.tsx` mostra todos os componentes de `shared/ui` lado a lado — usar como referência visual e para validar novos componentes.

---

## 12. Campaign War Room

`pages/campaign-war-room/CampaignWarRoomPage.tsx` é a composição central da fase:

```text
Breadcrumb
CampaignHeader              (widgets/campaign-header)        — usa useCampaign
IntelligenceSummary + WarningsPanel  (features/campaign-intelligence) — usa useCampaignIntelligence
  ├─ CampaignScoreCard       (widgets/campaign-score-card)
  ├─ CampaignMomentsPanel    (widgets/campaign-moments-panel)
  └─ CampaignRecommendationsPanel (widgets/campaign-recommendations-panel)
ExplanationsPanel
CampaignAssetsPanel | CampaignReportsPanel | CampaignMediaKitsPanel  (widgets/*)
```

Princípios já implementados:
- A página **nunca fica completamente bloqueada** por uma falha parcial: se `campaignQuery` falhar, mostra `ErrorState` para a página toda; se só `intelligenceQuery` falhar, o header e os painéis de outputs continuam visíveis — só a secção de intelligence mostra o erro.
- `result.scores`/`moments`/`recommendations` do Intelligence Engine são **tipados de forma defensiva** (`entities/campaign/intelligence.ts`): todos os campos opcionais + index signature, porque o schema OpenAPI os define como objectos/arrays livres (`items: {}`). Os componentes usam helpers de fallback (`intelligence-format.ts`) para extrair título/label de forma resiliente — nunca assumir uma forma fixa.
- Assets/Reports/Media Kits (`widgets/campaign-*-panel`) consomem entidades dedicadas (`entities/content-output`, `entities/report`, `entities/media-kit`) que já existem no Backend Core; quando os dados estiverem vazios, mostram `EmptyState` honesto — nunca dados inventados.
- Toda a chamada de rede desta página passa pelo Backend Core; o endpoint de intelligence é `POST /api/v1/campaigns/{id}/intelligence/` — não existe nenhum caminho directo para o Intelligence Engine ou o Content Renderer.

---

## 13. Tratamento de erros (transversal)

Mapeamento completo, ponta a ponta:

| Caso | Onde é detectado | UI resultante |
| --- | --- | --- |
| 401 (sessão) | `client.ts` → `notifyUnauthorized()` → `AuthProvider` | redirect para `/login` + "Your session has expired." |
| 401 (login inválido) | `auth-api.ts` (chamada com `auth:false`, não dispara o handler global) | `Alert` de erro na própria página de login |
| 403 | `ErrorState` despacha | `PermissionDenied` — "Access denied" |
| 404 | `ErrorState` despacha | `NotFoundState` |
| 422 / 400 | `ValidationError` (com `fieldErrors`) | bloco genérico com a mensagem do backend |
| 500 | `ApiError` genérico | bloco genérico "Something went wrong" |
| 502 / 503 | `ServiceUnavailableError` | `ServiceUnavailable` + botão Retry |
| erro de rede / backend inalcançável | `NetworkError` (fetch lança antes de haver resposta) | bloco genérico "Connection problem" |
| workspace ausente | `workspaceId === null` verificado em cada página/feature | `WorkspaceRequiredState` |

Todas as páginas e a War Room já passam o `error` do respectivo hook para `<ErrorState error={...} onRetry={...} />` — qualquer página nova que siga o mesmo padrão herda automaticamente este comportamento, sem código extra.

---

## 14. Como evoluir o frontend

### 14.1 Adicionar uma nova entidade

1. Confirmar o contrato real no schema OpenAPI do Backend Core (nunca assumir).
2. Criar `entities/<nome>/model.ts` com o tipo TypeScript (campos incertos → opcionais).
3. Criar `entities/<nome>/<nome>-api.ts` com funções que chamam `apiClient` (nunca `fetch` directo).
4. Criar `entities/<nome>/use<Nome>.ts` com `useQuery`, recebendo `workspaceId` (e outros ids relevantes) como parâmetro.
5. Criar `entities/<nome>/index.ts` a exportar tudo o que for público.
6. `entities` só pode importar de `shared`.

### 14.2 Adicionar uma nova feature

1. Criar `features/<nome>/` com a lógica de domínio (hooks, formatação, sub-componentes).
2. Pode importar de `entities/*` e `shared/*`; nunca de `widgets`/`pages`/`app`.
3. Se precisar de dados de auth/workspace, recebê-los como **props** vindas da página que a usa (não importar `features/auth`/`features/workspace-switching` cruzado entre features, salvo casos já estabelecidos como `workspace-switching` consumir `auth` — verificar a tabela de dependências antes).
4. Expor um componente "panel" de alto nível através do `index.ts` da feature, para a página/widget compor.
5. Tratar sempre `loading`/`error`/`empty` com os componentes de `shared/ui` (`LoadingState`/`ErrorState`/`EmptyState`/estados dedicados) — não inventar UI de erro ad-hoc.

### 14.3 Criar uma nova página

1. Criar `pages/<nome>/<Nome>Page.tsx` (+ `.module.css` + `index.ts`).
2. Compor a página a partir de `widgets`/`features`/`entities`/`shared` — a página em si deve ter pouca lógica própria (orquestração, não implementação).
3. Adicionar a rota em `app/router/routes.tsx`, dentro do bloco `ProtectedRoute` salvo se for pública.
4. Tratar explicitamente: sem workspace (`WorkspaceRequiredState`), loading, erro (`ErrorState`), vazio (`EmptyState`).
5. Confirmar `pnpm build` e `pnpm lint` antes de considerar concluído.

---

## 15. Decisões tomadas

| Decisão | Resolução | Porquê |
| --- | --- | --- |
| Styling | CSS Modules + design tokens | Simples, sem dependência pesada; suficiente para o MVP (FE-PDEC-001) |
| Auth | Auth real contra o Backend Core (JWT access+refresh) | Endpoints já existiam e estavam confirmados no schema (FE-PDEC-002) |
| Persistência de token | Access token em memória; refresh token em `localStorage` | Compromisso aceite para piloto técnico — ver limitação no §7 (FE-PDEC-003) |
| Testes automatizados | Não instalados nesta fase | Sem valor imediato comprovado; build+lint são o mínimo obrigatório (FE-PDEC-004) |
| Tipos gerados a partir de OpenAPI | Manuais nesta fase | Schema do Intelligence Engine ainda instável para `moments`/`scores`/`recommendations` (FE-PDEC-005) |
| Endpoint de intelligence (`POST`) | Consumido com `useQuery`, não `useMutation` | Semanticamente uma leitura (sem corpo, sem persistência), apesar do verbo POST |
| `ErrorState` | Despachante automático por tipo de erro (FE-013) | Evita repetir lógica de erro em cada página; páginas existentes herdam sem alteração |

---

## 16. Limitações conhecidas (honestas)

- **Refresh token em `localStorage`** — exposto a XSS; aceitável só para piloto controlado (ver §7).
- **Sem refresh-and-retry transparente**: um 401 termina a sessão directamente; não há retry automático da chamada original após renovar o token.
- **Tipos de intelligence são best-effort**: `result.analysis`, `result.scores`, `result.moments`, `result.recommendations` vêm de um schema livre (`items: {}` no OpenAPI) — os tipos TypeScript são optimistas, não garantidos; os componentes renderizam defensivamente.
- **Sem testes automatizados** (unit/integration/E2E) — só `pnpm build` (type-check) e `pnpm lint` validam o código nesta fase.
- **Sem RBAC frontend** — o frontend reage a 401/403 do backend, mas não decide visibilidade de funcionalidades com base em permissões antecipadamente.
- **Sem internacionalização** — toda a UI está em inglês.
- **Sem observabilidade/tracking de erros** em produção (ex.: Sentry) — apenas `console.error` em dev.
- **Não é production-ready**: falta UX refinada, testes E2E, tratamento completo de refresh, deploy, gestão segura de ambiente, validação cross-browser, performance budget (ver backlog §15.2).

---

## 17. O que não fazer

```text
Não chamar intelligence_engine directamente do frontend.
Não chamar content_renderer directamente do frontend.
Não enviar X-Internal-Token a partir do browser.
Não fazer fetch directo dentro de componentes visuais — passar sempre por shared/api.
Não importar de uma camada superior numa camada inferior (ver tabela §4).
Não criar um src/components genérico — usar shared/ui, widgets, features.
Não guardar server state em estado global local — usar TanStack Query.
Não usar dados mock/falsos em runtime normal — usar EmptyState honesto.
Não implementar RBAC, geração de assets, cálculo de scores ou detecção de moments no frontend.
Não mostrar tokens, headers de auth ou stack traces na UI ou em logs de produção.
Não declarar build/lint a passar sem correr os comandos e confirmar exit 0.
Não declarar "production-ready" sem evidência — esta fase é um piloto técnico controlado.
```
