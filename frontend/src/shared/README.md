# `shared/` — Reusable building blocks

The lowest layer. Must not import from `entities`, `features`, `widgets`,
`pages` or `app`.

- `api/` — Backend Core HTTP client, error normalization, headers (`Authorization`, `X-Workspace-ID`). The **single network boundary**. Added in FE-003. _(placeholder)_
- `ui/` — presentational primitives (Button, Card, Badge, Alert, states…). Added in FE-005. _(placeholder)_
- `lib/` — pure helpers/utilities. _(placeholder)_
- `hooks/` — generic, domain-agnostic React hooks. _(placeholder)_
- `types/` — cross-cutting TypeScript types. _(placeholder)_
- `constants/` — app-wide constants. _(placeholder)_
- `styles/` — global stylesheet + design tokens (`tokens.css`, `reset.css`, `global.css`, `index.css`).
