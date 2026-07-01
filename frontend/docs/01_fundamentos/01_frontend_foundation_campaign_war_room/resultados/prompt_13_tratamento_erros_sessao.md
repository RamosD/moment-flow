# FE-013 — Tratamento transversal de erros e sessão expirada

**Fase:** Frontend Foundation & Campaign War Room MVP
**Componente alvo:** `frontend`
**Data:** 2026-06-26
**Tipo:** Padrões transversais de erro/sessão/permissões/serviço indisponível

---

## 0. Sumário executivo

- Criados componentes de estado **dedicados e semânticos**: `SessionExpired`, `PermissionDenied`, `NotFoundState`, `ServiceUnavailable`, `WorkspaceRequiredState` (+ `FeedbackBlock` reutilizável).
- O **`ErrorState` passou a despachar** automaticamente por tipo de erro: 401 → SessionExpired, 403 → PermissionDenied, 404 → NotFoundState, 502/503 → ServiceUnavailable; restantes (rede/422/500) → bloco genérico com copy normalizada. **Todas as páginas existentes** que já usavam `<ErrorState error={…}/>` ganham este comportamento sem alteração.
- **Sessão expirada (401)** tratada de ponta a ponta: o handler global limpa a sessão **e marca `sessionExpired`**, o `ProtectedRoute` redirecciona para `/login`, e o login mostra **"Your session has expired."**.
- **Workspace ausente** tratado com `WorkspaceRequiredState` nas 4 superfícies (campanhas, detalhe, War Room, intelligence).
- **Nunca mostra tokens nem stack traces** — copy fixa/normalizada; logs de query sanitizados.
- **Verificado em browser**: 403, 404, sessão expirada e workspace ausente distinguíveis e correctos.
- **`pnpm build` e `pnpm lint` passam** (exit 0, 0 avisos).

---

## 1. Revisão do existente

| Camada | Estado antes do FE-013 |
| --- | --- |
| API client | Normalização completa (`ApiError` + subclasses) — 400/401/403/404/422/500/502/503/network. **OK** |
| 401 global | Handler injectável → `clearSession` → redirect (FE-007). **Melhorado** (ver §4) |
| `ErrorState` | Copy por `resolveErrorPreset` (distinguível). **Refactorizado** para delegar a componentes dedicados |
| Logging | `queryClient.onError` regista só `status/code` (sem token). **OK** |

---

## 2. Componentes criados (`shared/ui/states`)

| Componente | Caso | Tom | Copy |
| --- | --- | --- | --- |
| `SessionExpired` | 401 | danger | "Session expired" / "…sign in again." |
| `PermissionDenied` | 403 | danger | "Access denied" / "…no permission in the current workspace." |
| `NotFoundState` | 404 | neutral (`?`) | "Not found" / "…does not exist or is not available here." |
| `ServiceUnavailable` | 502/503 | warning | "Service unavailable" / "…temporarily unavailable. Try again." + Retry |
| `WorkspaceRequiredState` | workspace ausente | neutral | "No workspace selected" / "Choose a workspace from the top bar." |
| `FeedbackBlock` (base) | — | neutral/danger/warning | bloco reutilizável (ícone + título + descrição + acções) |

- **Acções por render-prop** (`onRetry`/`action`) → `shared/ui` sem dependência de router.
- `FeedbackBlock` usa `role="alert"` (danger) ou `role="status"` (restantes) para acessibilidade.

---

## 3. `ErrorState` como despachante transversal

```
error 401  → <SessionExpired />
error 403  → <PermissionDenied />
error 404  → <NotFoundState />
error 502/503 → <ServiceUnavailable onRetry=… />
network / 422 / 500 / desconhecido → bloco genérico (preset copy) + Retry
```

- Só despacha quando o chamador **não** sobrepõe `title`/`description` (mantém retro-compatibilidade com usos custom).
- Mapeamento de status já vinha do client: **502 e 503 → `ServiceUnavailableError`**; **500 → `ApiError` genérico** ("Something went wrong"); **network/backend unavailable → `NetworkError`** ("Connection problem… could not reach the server").

Resultado: **401/403/404/422/502/503 são visualmente distinguíveis** em toda a app, sem código por página.

---

## 4. Sessão expirada (401)

- `AuthProvider` ganhou estado **`sessionExpired`** e um handler dedicado:
  - **handler global de 401** (`setUnauthorizedHandler`) → `setSessionExpired(true)` + `clearSession()`.
  - `logout()` e falha de boot → `clearSession()` **sem** marcar expiry (não é expiração).
  - `login()` com sucesso → `setSessionExpired(false)`.
- `ProtectedRoute` redirecciona para `/login` quando `unauthenticated`.
- `LoginPage` mostra um `Alert` **"Your session has expired. Please sign in again."** quando `sessionExpired` (e não há erro de submissão).

Distingue assim **sessão expirada** (notice azul) de **credenciais inválidas** (alerta vermelho) e de **login normal**.

---

## 5. Privacidade / segurança

- **Sem tokens**: a copy é fixa; os componentes não recebem nem mostram tokens; `ApiError` não transporta headers; `onError` regista só `status/code`.
- **Sem stack traces**: nunca se renderiza `error.stack` nem o objecto cru; `resolveErrorPreset` devolve apenas mensagens humanas. `ValidationError` usa `error.message` (texto do backend), sem internals.

---

## 6. Integração nas páginas

`WorkspaceRequiredState` substituiu os `EmptyState "No workspace selected"` em:
`CampaignsPage`, `CampaignDetailPage`, `CampaignWarRoomPage`, `CampaignIntelligencePanel`.
Todas as páginas/War Room já passavam `error` ao `ErrorState` (FE-009/10/11/12), por isso herdam automaticamente o despacho 401/403/404/502/503.

---

## 7. Verificação em browser (rede stubbed)

| Cenário | Resultado |
| --- | --- |
| 403 (detalhe de campanha) | ✅ "Access denied — …no permission in the current workspace." |
| 404 (detalhe de campanha) | ✅ "Not found — …does not exist or is not available here." (ícone `?`) |
| **401 → sessão expirada** | ✅ redirecciona para `/login` + notice "Your session has expired." + botão Sign in |
| **Workspace ausente** | ✅ "No workspace selected — Choose a workspace from the top bar." (+ switcher "No workspace") |
| 502/503 | ✅ "Service unavailable" + Try again (despacho do `ErrorState`; provado em FE-010/11/12) |
| Tokens/stack na UI ou consola | ✅ ausentes |

> Notas: a screenshot tool manteve timeouts (validação por DOM). 4xx (403/404/401) surgem de imediato (sem retry). O ambiente do preview reporta `navigator.onLine=false` (ver memória), pelo que 5xx exigem `onlineManager.setOnline(true)` para retomar a retentativa — artefacto de ambiente, não da app.

---

## 8. Validações

| Verificação | Comando | Resultado |
| --- | --- | --- |
| Lint | `pnpm lint` | ✅ exit 0 — 0 avisos |
| Build | `pnpm build` | ✅ exit 0 |
| Cenários | preview + DOM | ✅ §7 |

> `dist/` removido.

---

## 9. Critérios de aceitação — verificação

| Critério (FE-013) | Estado |
| --- | --- |
| Erros comuns têm UI adequada | ✅ 401/403/404/422/500/502/503/network/workspace |
| 401/403/404/422/502/503 são distinguíveis | ✅ componentes/copy dedicados |
| Sessão expirada é tratada | ✅ redirect + notice |
| Workspace ausente é tratado | ✅ `WorkspaceRequiredState` |
| Tokens e detalhes sensíveis não aparecem | ✅ copy fixa; logs sanitizados |
| Build/lint passam ou limitações documentadas | ✅ ambos passam |

---

## 10. Ficheiros criados/alterados

**Novos (`shared/ui/states`):** `FeedbackBlock.tsx`, `dedicated.tsx` (SessionExpired, PermissionDenied, NotFoundState, ServiceUnavailable, WorkspaceRequiredState).
**Alterados (`shared/ui`):** `states/ErrorState.tsx` (despacho + usa `FeedbackBlock`), `states/index.ts`, `index.ts`, `states/states.module.css` (`.iconWarning`).
**Alterados (auth):** `features/auth/auth-context.ts` (+`sessionExpired`), `features/auth/AuthProvider.tsx` (handler de 401 + flag), `pages/login/LoginPage.tsx` (notice).
**Alterados (workspace ausente):** `pages/campaigns/CampaignsPage.tsx`, `pages/campaign-detail/CampaignDetailPage.tsx`, `pages/campaign-war-room/CampaignWarRoomPage.tsx`, `features/campaign-intelligence/CampaignIntelligencePanel.tsx`.

---

## 11. Notas para os prompts seguintes

- **FE-014 (documentação):** documentar o padrão de erros (ErrorState despachante + componentes dedicados + sessão expirada).
- **Futuro:** refresh-and-retry transparente no client antes do logout em 401 (hoje 401 → logout directo); `networkMode` poderá ser ajustado se necessário para ambientes offline-tolerant.
- **`ValidationError`:** para formulários, mapear `fieldErrors` a campos específicos (fora do escopo desta fase — não há forms de edição).
