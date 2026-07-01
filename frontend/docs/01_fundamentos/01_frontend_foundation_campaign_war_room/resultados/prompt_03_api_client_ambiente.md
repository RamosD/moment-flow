# FE-003 — API client e configuração de ambiente

**Fase:** Frontend Foundation & Campaign War Room MVP
**Componente alvo:** `frontend`
**Data:** 2026-06-26
**Tipo:** Implementação da camada de comunicação (`shared/api`) + config de ambiente (`shared/config`)

---

## 0. Sumário executivo

- Criada a **camada central de comunicação com o Backend Core** em `src/shared/api`, com client factory + instância singleton, e a **configuração de ambiente** em `src/shared/config`.
- **Base URL vem de `VITE_BACKEND_API_BASE_URL`**, com validação (ausente / inválida) e **fallback de dev** (`http://localhost:8000/api/v1`) apenas em modo desenvolvimento.
- **Headers controlados e injectáveis**: `Authorization: Bearer <token>` e `X-Workspace-ID` lidos em runtime via **providers injectáveis** (registry em `shared/api/providers.ts`), nunca hardcoded. `Content-Type: application/json` enviado quando há corpo.
- **`X-Internal-Token` é explicitamente bloqueado**: o client tem uma guarda que remove qualquer tentativa de o definir. Não existe nenhum caminho para o enviar.
- **Normalização de erros HTTP** completa: `ApiError` + 6 subclasses (`Unauthorized/Forbidden/NotFound/Validation/ServiceUnavailable/Network`), cobrindo 400, 401, 403, 404, 422, 500, 502, 503 e erros de rede.
- **Tipo de paginação DRF** (`Paginated<T>`) criado.
- **`pnpm build` e `pnpm lint` passam** (exit 0, 0 avisos).
- **Sem framework de testes** → limitação documentada (§7).

---

## 1. Decisão de arquitectura: config em `shared`, não `app`

O backlog dava a opção `src/app/config` **ou** `src/shared/config`. Escolhi **`shared/config`** por uma razão de arquitectura:

> A regra de dependência (documentada em FE-002) diz que **`shared` não pode importar de `app`**. Como o API client vive em `shared/api` e precisa da base URL, a config de ambiente **tem de estar em `shared`**, senão `shared/api` importaria de `app/config` e violaria a camada.

`app/config` continua a existir, mas só para **metadados estáticos** (`APP_CONFIG`). A config de **runtime/ambiente** fica em `shared/config`.

---

## 2. Configuração de ambiente — `shared/config/env.ts`

- Lê `import.meta.env.VITE_BACKEND_API_BASE_URL` (tipado em `src/vite-env.d.ts`).
- **Validação simples:**
  - **Ausente** + `DEV` → `console.warn` + fallback `http://localhost:8000/api/v1`.
  - **Ausente** + `PROD` → lança `EnvConfigError` (falha cedo, sem URL inventada em produção).
  - **Inválida** (não é `http(s)` URL válida) → lança `EnvConfigError`.
- Normaliza removendo a barra final, para junção de paths previsível.
- Exporta `ENV = { apiBaseUrl, isDev, isProd }`.

O fallback de dev nunca envolve segredos (é só uma URL pública), por isso o `console.warn` é seguro.

`.env.example` criado na raiz do `frontend/` com `VITE_BACKEND_API_BASE_URL` e um aviso explícito de **nunca** colocar `X-Internal-Token`. `.gitignore` reforçado para ignorar `.env`/`.env.*` mantendo `.env.example` versionado.

---

## 3. API client — `shared/api`

### 3.1 Ficheiros

| Ficheiro | Responsabilidade |
| --- | --- |
| `client.ts` | Client factory (`createApiClient`) + singleton `apiClient`; build de URL/headers; fetch; parsing; mapeamento de erros |
| `errors.ts` | Hierarquia de erros normalizados |
| `providers.ts` | Registry injectável de token + workspace id |
| `types.ts` | `Paginated<T>`, `RequestOptions`, `TokenProvider`, `WorkspaceProvider` |
| `index.ts` | API pública (barril) da camada |

### 3.2 Helpers

`get`, `post`, `patch`, `delete` — todos genéricos (`<T>`) e a devolver `Promise<T>`:

```ts
apiClient.get<Paginated<Campaign>>('/campaigns/', { params: { status: 'active' } })
apiClient.post<CampaignIntelligenceResponse>(`/campaigns/${id}/intelligence/`)
apiClient.patch<Campaign>(`/campaigns/${id}/`, { name })
apiClient.delete<void>(`/campaigns/${id}/`)
```

`RequestOptions`: `params` (query string, ignora null/undefined), `headers` (custom, sanitizados), `signal` (AbortSignal — cancelamento/timeout e compatível com TanStack Query), `auth` (a `false` salta o `Authorization`, p.ex. login/refresh).

### 3.3 Headers controlados e injectáveis

- **`Authorization: Bearer <token>`** — só quando há token **e** `auth !== false`. O token vem de `getAuthToken()` (provider injectável). Nunca hardcoded.
- **`X-Workspace-ID`** — quando há workspace activo, via `getWorkspaceId()` (provider injectável).
- **`Content-Type: application/json`** — definido **só quando há corpo** (POST/PATCH com body). `Accept: application/json` sempre.
- Injecção sem violar camadas: `providers.ts` mantém getters mutáveis; o `AuthProvider` (FE-007) e o `WorkspaceProvider` (FE-008) chamam `setTokenProvider`/`setWorkspaceProvider`. O singleton `apiClient` lê através de `readToken`/`readWorkspaceId`. Assim `shared` não depende de `app`/`features`.

### 3.4 Proibição de `X-Internal-Token`

- Constante `INTERNAL_TOKEN_HEADER = 'x-internal-token'`.
- `sanitizeCustomHeaders()` percorre os headers custom e **descarta** qualquer chave que (case-insensitive) seja `x-internal-token`, com `console.warn` em DEV (sem expor valores).
- O client **nunca** define este header por si. Auditoria (`grep -rni "internal.token\|x-internal" src`) confirma: as únicas ocorrências são **documentação** e a **guarda que bloqueia** — nenhuma o envia.

### 3.5 Segurança de logging

- Não há `console.log` de headers, tokens ou Authorization em lado nenhum.
- Os objectos de erro **não** incluem os headers do pedido (só status, code, body de resposta, requestId). Tokens nunca entram em mensagens de erro.

---

## 4. Normalização de erros — `errors.ts`

Todos derivam de `ApiError` (permite `catch (e) { if (e instanceof ApiError) … }`).

| Classe | Status | Origem |
| --- | --- | --- |
| `ValidationError` | 400, 422 | inclui `fieldErrors: Record<string,string[]>` (parse best-effort do corpo DRF) |
| `UnauthorizedError` | 401 | token ausente/expirado/inválido |
| `ForbiddenError` | 403 | sem permissão / workspace errado |
| `NotFoundError` | 404 | recurso inexistente no workspace |
| `ServiceUnavailableError` | 502, 503 | engine/upstream indisponível (retryable) |
| `ApiError` (genérico) | 500, 504, outros | erro de servidor não mapeado |
| `NetworkError` | 0 | fetch falhou (offline/DNS/CORS); request nunca completou |

Detalhes capturados quando presentes: `code` (DRF `code`), `details` (corpo parseado), `requestId` (header `X-Request-ID` ou `request_id` do corpo), `fieldErrors`. Mensagem extraída de `detail`/`message`/`statusText`.

**Cancelamento:** `AbortError` é re-lançado intacto (não vira `NetworkError`), para o TanStack Query distinguir cancelamento de falha real.

**Parsing de corpo:** trata `204 No Content` e corpo vazio (→ `undefined`), JSON quando `Content-Type: application/json`, texto caso contrário.

---

## 5. Paginação

`Paginated<T>` reflecte o envelope DRF confirmado no Prompt 01:

```ts
interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
```

Usado a partir de FE-009 (`useCampaigns`) e FE-008 (`useWorkspaces`).

---

## 6. Validações executadas

| Verificação | Comando | Resultado |
| --- | --- | --- |
| Lint | `pnpm lint` | ✅ exit 0 — 0 erros, 0 avisos |
| Typecheck + build | `pnpm build` | ✅ exit 0 |
| Auditoria `X-Internal-Token` | `grep -rni` em `src` | ✅ só docs + guarda; nenhum envio |

> Nota: o bundle continua com 21 módulos porque a camada `api` ainda não é importada por código de UI (será consumida a partir de FE-007+); ainda assim é **type-checked** por `tsc -b` (que passou). O `dist/` de validação foi removido.

---

## 7. Testes — limitação documentada

**Não existe framework de testes** no projecto (sem Vitest/Testing Library), conforme decisão FE-PDEC-004 (adiar testes nesta fase; build/lint são o mínimo obrigatório).

- **Limitação:** o API client e a normalização de erros **não têm testes unitários** neste momento.
- **Mitigação:** código escrito de forma testável — `createApiClient(options)` aceita `getAuthToken`/`getWorkspaceId` injectáveis, o que permite testar sem estado global quando o Vitest for adicionado.
- **Recomendação futura:** adicionar Vitest + cobrir: mapeamento de status→erro, sanitização de `X-Internal-Token`, presença/ausência de `Authorization`/`X-Workspace-ID`, parsing de 204/JSON/erro DRF, `NetworkError` vs `AbortError`.

---

## 8. Critérios de aceitação — verificação

| Critério (FE-003) | Estado |
| --- | --- |
| API client central existe | ✅ `shared/api` |
| Base URL vem de env | ✅ `VITE_BACKEND_API_BASE_URL` (`shared/config/env.ts`) |
| Authorization header é suportado | ✅ injectável via provider |
| X-Workspace-ID é suportado | ✅ injectável via provider |
| X-Internal-Token não existe no frontend | ✅ bloqueado por guarda; auditado |
| Erros HTTP são normalizados | ✅ `ApiError` + 6 subclasses; 400/401/403/404/422/500/502/503/network |
| Build passa | ✅ |
| Lint passa ou limitação documentada | ✅ passa sem avisos |
| Relatório lista ficheiros, decisões e limitações | ✅ este documento |

---

## 9. Ficheiros criados/alterados

**Novos:**
- `src/vite-env.d.ts` — tipagem de `import.meta.env` (VITE_BACKEND_API_BASE_URL)
- `src/shared/config/env.ts`, `src/shared/config/index.ts`
- `src/shared/api/client.ts`, `errors.ts`, `providers.ts`, `types.ts`, `index.ts`
- `frontend/.env.example`

**Alterados:**
- `frontend/.gitignore` — ignorar `.env`/`.env.*` mantendo `.env.example`

**Removidos:**
- `src/shared/api/.gitkeep` (a slice passou a ter conteúdo real)

---

## 10. Notas para os prompts seguintes

- **FE-004**: o `AppProviders` deve, ao iniciar, registar os providers de auth/workspace via `setTokenProvider`/`setWorkspaceProvider` (mesmo que devolvam `null` inicialmente). Usar o singleton `apiClient` nos hooks de query.
- **FE-006**: tipar `results` de `Paginated<T>` com as entidades reais (Campaign, Workspace…).
- **FE-007/FE-008**: ligar token e workspace id reais aos providers; o `auth: false` em `RequestOptions` serve para login/refresh.
- **FE-013**: o tratamento transversal de UI já tem os tipos de erro prontos para distinguir 401/403/404/422/503/network.
