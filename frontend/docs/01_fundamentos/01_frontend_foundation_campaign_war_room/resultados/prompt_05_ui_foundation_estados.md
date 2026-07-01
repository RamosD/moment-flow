# FE-005 — UI foundation e estados transversais

**Fase:** Frontend Foundation & Campaign War Room MVP
**Componente alvo:** `frontend`
**Data:** 2026-06-26
**Tipo:** Componentes UI base (`shared/ui`) + estados loading/error/empty + página de validação

---

## 0. Sumário executivo

- Criados **11 componentes UI base** em `src/shared/ui`, com **CSS Modules + design tokens** (abordagem do Prompt 02), **sem qualquer dependência visual nova** (sem Tailwind, sem UI framework, sem `clsx` — usei um utilitário `cx` local de 3 linhas).
- **Estados transversais** loading / empty / error implementados, com **mapeamento de erros da API** para os padrões pedidos: rede, 401, 403, 404, serviço indisponível e validação.
- **Variantes** completas: Button (`primary/secondary/ghost/danger/success/warning/neutral`), Badge/Alert com tons semânticos.
- **Acessibilidade básica**: `type="button"` por omissão, `disabled` nativo, `role`/`aria-live` nos estados e alerts, `aria-hidden` em elementos decorativos, `prefers-reduced-motion` nas animações.
- Componentes **reutilizados nas páginas iniciais** (Dashboard, Campaigns, Campaign Detail, War Room, Settings) + **página de validação** `/ui-kit` (style guide vivo, não ligada à navegação).
- **Render verificado em browser** (buttons, badges, cards, skeleton, alerts, loading/empty, 5 padrões de erro) — **0 erros na consola**.
- **`pnpm build` e `pnpm lint` passam** (exit 0, 0 avisos).

---

## 1. Decisão: sem dependências visuais novas

O backlog recomendava `clsx`/`lucide-react`, mas a instrução é evitar peso visual. Decisões:

- **`clsx` → não instalado.** Criei `shared/lib/cx.ts` (combina classes, ignora falsy). Trivial e sem dependência.
- **`lucide-react` → não instalado.** Ícones decorativos resolvidos com glifos simples (`—`, `!`) + `aria-hidden`. Evita ~1MB de pacote de ícones no MVP.
- **Styling:** CSS Modules por componente + tokens CSS (FE-PDEC-001). Nenhum design system pesado.

> Mantém FE-RSK-006 (overengineering visual) sob controlo: zero novas dependências neste prompt.

---

## 2. Componentes criados (`shared/ui`)

| Componente | Ficheiros | Variantes / API principal |
| --- | --- | --- |
| **Button** | `Button/` | `variant`: primary, secondary, ghost, danger, success, warning, neutral · `size`: sm/md · `fullWidth` · `type` default `button` |
| **Card** | `Card/` | `padding`: sm/md/lg · superfície neutra |
| **Badge** | `Badge/` | `variant`: neutral, primary, success, warning, danger, info |
| **Alert** | `Alert/` | `variant`: info, success, warning, danger · `title` · `role` automático |
| **PageHeader** | `PageHeader/` | `title`, `description`, `actions` |
| **Section** | `Section/` | `title`, `description`, `actions`, `children` |
| **Skeleton** | `Skeleton/` | `width`/`height`/`radius` · shimmer · decorativo |
| **LoadingState** | `states/` | `label` · spinner + `role="status"` |
| **EmptyState** | `states/` | `title`, `description`, `action`, `icon` |
| **ErrorState** | `states/` | `error` (auto-copy) ou `title`/`description` · `onRetry` · `action` |

Cada componente tem barril próprio; `shared/ui/index.ts` reexporta a API pública (componentes + tipos). **Tabs/Nav simples não foi criado** — a navegação já existe no `RootLayout` (FE-004) e não há necessidade de tabs nesta fase (o backlog marca-o como "se necessário").

---

## 3. Estados e padrões de erro

`states/error-presets.ts` centraliza `resolveErrorPreset(error)`, que mapeia os erros normalizados do FE-003 para copy consistente e não-técnica (nunca expõe tokens nem stack traces):

| Erro (instanceof) | Título | Mensagem |
| --- | --- | --- |
| `NetworkError` | Connection problem | "could not reach the server…" |
| `UnauthorizedError` (401) | Session expired | "session is no longer valid…" |
| `ForbiddenError` (403) | Access denied | "do not have permission…" |
| `NotFoundError` (404) | Not found | "does not exist or is not available…" |
| `ServiceUnavailableError` (502/503) | Service unavailable | "temporarily unavailable…" |
| `ValidationError` (400/422) | Invalid request | mensagem do servidor |
| `ApiError` / desconhecido | Something went wrong | genérico |

`ErrorState` aceita `error` (deriva copy via preset) **ou** `title`/`description` explícitos, mais `onRetry` (render do botão "Try again") e `action` (ex.: "Sign in"). Mantém-se **livre de dependências de router/query** — o retry é injectado por callback, pronto para o tratamento transversal do FE-013.

---

## 4. Acessibilidade básica

- **Button:** `type="button"` por omissão (nunca submete sem querer); `disabled` nativo (comportamento + estilo via `:disabled`).
- **Alert:** `role="alert"` para danger/warning (assertivo), `role="status"` para info/success (polido).
- **LoadingState:** `role="status"` + `aria-live="polite"` + label textual; spinner `aria-hidden`.
- **Skeleton / ícones decorativos:** `aria-hidden="true"`.
- **Contraste:** tons semânticos com pares fundo/texto de contraste razoável (ex.: danger `#fee2e2`/`#b91c1c`).
- **Motion:** `@media (prefers-reduced-motion: reduce)` desliga/abranda shimmer e spinner.

---

## 5. Reutilização nas páginas + validação

- **Páginas iniciais refeitas** para usar os primitivos:
  - Dashboard → `PageHeader` (+ `Button`) + `Card`
  - Campaigns → `PageHeader` + `EmptyState`
  - Campaign Detail → `PageHeader` (+ `Button`) + `Card` + `Badge`
  - War Room → `PageHeader` + `Badge` + `Alert`
  - Settings → `PageHeader` + `Card`
- **Página de validação `/ui-kit`** (`pages/ui-kit`): style guide vivo com todos os componentes, variantes, estados e os 5 padrões de erro. **Não ligada à navegação** (acessível só por URL) — serve de referência de desenvolvimento.
- Corrigido durante a implementação um `as-child` inválido no Dashboard (geraria `<a>` dentro de `<button>`); substituído por `useNavigate` + `Button`.

---

## 6. Verificação em browser

Servido o dev server e validado em `/ui-kit` e `/`:

| Verificação | Resultado |
| --- | --- |
| Buttons (7 variantes + sm/md + disabled) | ✅ render correcto |
| Badges (6 variantes) | ✅ |
| Card + Skeleton (shimmer) | ✅ |
| Alerts (4 variantes) | ✅ |
| LoadingState (spinner) + EmptyState (com acção) | ✅ |
| Error patterns (network/401/403/404/503) com copy derivada + retry | ✅ |
| Dashboard refeito (PageHeader+Card+Button) | ✅ |
| Consola — erros | ✅ **0 erros** |

---

## 7. Validações

| Verificação | Comando | Resultado |
| --- | --- | --- |
| Lint | `pnpm lint` | ✅ exit 0 — 0 avisos |
| Build | `pnpm build` | ✅ exit 0 — 115 módulos |
| Render em browser | preview + screenshots + console | ✅ §6 |

> CSS final do bundle ~10kB (gzip 2.7kB) — leve, confirmando "sem design system pesado". `dist/` de validação removido.

---

## 8. Critérios de aceitação — verificação

| Critério (FE-005) | Estado |
| --- | --- |
| Componentes UI base existem | ✅ 10 componentes (Tabs/Nav dispensado, justificado) |
| Estados loading/error/empty existem | ✅ + presets de erro |
| Componentes são reutilizáveis | ✅ usados em 5 páginas + `/ui-kit` |
| Não há design system pesado | ✅ CSS Modules + tokens; 0 deps novas |
| Build passa | ✅ |
| Lint passa ou limitação documentada | ✅ passa sem avisos |

---

## 9. Ficheiros criados/alterados

**Novos (`shared/`):**
- `shared/lib/{cx.ts, index.ts}`
- `shared/ui/Button/`, `Card/`, `Badge/`, `Alert/`, `PageHeader/`, `Section/`, `Skeleton/` (cada `*.tsx` + `*.module.css` + `index.ts`)
- `shared/ui/states/{LoadingState.tsx, EmptyState.tsx, ErrorState.tsx, error-presets.ts, states.module.css, index.ts}`
- `shared/ui/index.ts`

**Novos (`pages/`):** `pages/ui-kit/{UiKitPage.tsx, UiKitPage.module.css, index.ts}`

**Alterados:**
- `app/router/routes.tsx` (+ rota `/ui-kit`)
- `pages/dashboard`, `pages/campaigns`, `pages/campaign-detail`, `pages/campaign-war-room`, `pages/settings` (refeitos com primitivos)

**Removidos:** `shared/ui/.gitkeep`

---

## 10. Notas para os prompts seguintes

- **FE-006**: entidades/tipos de domínio podem usar `Badge`/`Card` para apresentação (ex.: grade badge mapeada para variante).
- **FE-009/FE-010/FE-011**: usar `LoadingState`/`ErrorState error={error}`/`EmptyState` directamente nos hooks de query — o mapeamento de 401/403/404/503/rede já está pronto.
- **FE-013**: `resolveErrorPreset` + `ErrorState` são a base do tratamento transversal; `PermissionDenied`/`ServiceUnavailable` podem ser wrappers finos sobre `ErrorState`.
- A página `/ui-kit` pode ser removida ou protegida antes de produção (é uma superfície de desenvolvimento).
