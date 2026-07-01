# `entities/` — Domain models

One folder per business entity. Each holds its TypeScript types (aligned to the
Backend Core OpenAPI schema) and, later, its API access + mappers.

Slices: `campaign`, `artist`, `track`, `workspace`, `user`, `content-output`,
`report`, `media-kit`. Types are implemented in FE-006.

May import only from `shared`. Entities must not depend on each other's UI or on
higher layers.
