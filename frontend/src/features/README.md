# `features/` — User-facing use cases

A feature is a slice of interactive behaviour (a thing the user does), with its
hooks, components and logic.

Slices: `auth`, `workspace-switching`, `campaign-intelligence`,
`campaign-actions`, `asset-generation-status`, `report-status`. Implemented from
FE-007 onward.

May import from `entities` and `shared` only.
