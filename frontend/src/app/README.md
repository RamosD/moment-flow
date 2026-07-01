# `app/` — Application wiring

Top of the dependency graph. Composes everything else and owns global setup.

- `config/` — static app metadata (`APP_CONFIG`). Runtime env config arrives with the API client (FE-003).
- `providers/` — global React providers (QueryClient, Auth, Workspace, Router). Added in FE-004. _(placeholder)_
- `router/` — route tree and route guards. Added in FE-004. _(placeholder)_
- `layouts/` — page frames. `RootLayout` is the minimal app frame; it will host react-router's `<Outlet />` once routing lands.

May import from any lower layer.
