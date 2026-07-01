# `src/` — Frontend architecture (Feature-Sliced layers)

The frontend is organized into **layers**. Imports may only flow **downward**.
Higher layers compose lower ones; lower layers never know about higher ones.

```
app       → top-level wiring: providers, router, layouts, config
pages     → route screens; compose widgets + features + entities + shared
widgets   → self-contained UI blocks (panels, headers); compose features/entities/shared
features  → user-facing interactions/use cases; compose entities + shared
entities  → domain models, types, and their API access; compose shared
shared    → framework-agnostic building blocks (api client, ui, lib, types…)
```

## Dependency rule

| Layer    | May import from                              |
| -------- | -------------------------------------------- |
| app      | shared, entities, features, widgets, pages   |
| pages    | shared, entities, features, widgets          |
| widgets  | shared, entities, features                   |
| features | shared, entities                             |
| entities | shared                                        |
| shared   | (nothing above it)                           |

## Conventions

- **Path alias:** import with `@/…` (maps to `src/…`). No deep relative `../../..`.
- **Barrels:** add an `index.ts` only where it keeps imports clean (public API of a slice). Empty/placeholder slices carry a `.gitkeep` until implemented.
- **Styling:** CSS Modules (`*.module.css`) per component + global design tokens in `shared/styles`. No raw color/spacing literals — use `var(--token)`.
- **Network boundary:** the **only** place that talks to the network is `shared/api`, and it targets **Backend Core only**. Never call the Intelligence Engine or Content Renderer directly. Never send `X-Internal-Token`.
- No giant `src/components` folder — UI primitives live in `shared/ui`, composed blocks in `widgets`.
