# FE-002 — Foundation estrutural do frontend

**Fase:** Frontend Foundation & Campaign War Room MVP
**Componente alvo:** `frontend`
**Data:** 2026-06-26
**Tipo:** Implementação de estrutura (foundation modular) + design tokens + aliases

---

## 0. Sumário executivo

- Criada a **estrutura modular Feature-Sliced** completa em `src/` (camadas `app`, `shared`, `entities`, `features`, `widgets`, `pages`), alinhada com a arquitectura alvo do backlog (§6) e o plano do Prompt 01.
- **Aliases de import `@/` → `src/`** configurados de forma consistente em TypeScript e Vite. Imports limpos, sem `../../..`.
- **Design tokens mínimos** (spacing, radius, colors, typography, shadows) + reset + estilos globais base, em `shared/styles`, via variáveis CSS.
- **App root limpo**: removido todo o template do Vite (logos, contador, `App.css`, `index.css`, assets) e substituído por um `RootLayout` mínimo.
- **`pnpm build` passa** (`tsc -b && vite build`, exit 0) e **`pnpm lint` passa** (0 erros, 0 avisos).
- **Sem `src/components` gigante**, sem imports circulares. War Room **não** implementada (conforme instrução).
- **Nenhuma dependência instalada** (não foi necessário).

---

## 1. Estrutura criada

```
src/
├── README.md                         # mapa de camadas + regras de dependência
├── main.tsx                          # entry: importa estilos globais + App
├── App.tsx                           # root limpo (RootLayout + placeholder)
│
├── app/                              # wiring de topo
│   ├── README.md
│   ├── config/
│   │   ├── app.config.ts             # APP_CONFIG (metadados estáticos)
│   │   └── index.ts
│   ├── layouts/
│   │   ├── RootLayout.tsx            # frame mínimo da app
│   │   ├── RootLayout.module.css
│   │   └── index.ts
│   ├── providers/ (.gitkeep)         # FE-004
│   └── router/    (.gitkeep)         # FE-004
│
├── shared/                           # blocos reutilizáveis (camada base)
│   ├── README.md
│   ├── styles/
│   │   ├── tokens.css                # design tokens (CSS vars)
│   │   ├── reset.css                 # reset moderno mínimo
│   │   ├── global.css                # estilos base de elementos
│   │   └── index.css                 # entry (importa os 3)
│   ├── api/ ui/ lib/ hooks/ types/ constants/   (.gitkeep)
│
├── entities/  (README + 8 slices .gitkeep)
│   └── campaign · artist · track · workspace · user · content-output · report · media-kit
│
├── features/  (README + 6 slices .gitkeep)
│   └── auth · workspace-switching · campaign-intelligence · campaign-actions · asset-generation-status · report-status
│
├── widgets/   (README + 7 slices .gitkeep)
│   └── app-shell · campaign-header · campaign-score-card · campaign-recommendations-panel · campaign-moments-panel · campaign-assets-panel · campaign-reports-panel
│
└── pages/     (README + 5 slices)
    ├── not-found/   NotFoundPage.tsx + .module.css + index.ts   (implementada)
    └── dashboard · campaigns · campaign-detail · campaign-war-room   (.gitkeep, FE-009/FE-011)
```

### Critério de placeholders
- Slices ainda não implementadas têm `.gitkeep` (existem na árvore, prontas a receber código nas fases seguintes).
- `index.ts` (barril) criado **apenas** onde já há API pública real: `app/config`, `app/layouts`, `pages/not-found`. Não foram criados barris vazios.
- Cada camada tem um `README.md` curto com o propósito e a regra de dependência — satisfaz o requisito de documentação curta da estrutura.

---

## 2. Aliases de import

Decisão do Prompt 01 aplicada: alias `@/` → `src/`.

- **`vite.config.ts`** — `resolve.alias['@'] = fileURLToPath(new URL('./src', import.meta.url))` (ESM, sem `__dirname`).
- **`tsconfig.app.json`** — `"paths": { "@/*": ["./src/*"] }`.

> **Nota técnica (TS 6):** a primeira tentativa usou `baseUrl: "."`, mas o TypeScript 6 emitiu `TS5101: Option 'baseUrl' is deprecated`. Com `moduleResolution: "bundler"`, `paths` funciona **sem** `baseUrl` (resolvido relativamente ao `tsconfig`), pelo que `baseUrl` foi removido. Build e resolução confirmados a funcionar — alinha com o risco FE-RSK-008 (stack bleeding-edge).

Exemplos em uso real: `main.tsx` importa `@/shared/styles/index.css` e `@/App.tsx`; `App.tsx` importa `@/app/layouts` e `@/app/config`; `RootLayout` importa `@/app/config`.

---

## 3. Design tokens e estilos globais

`shared/styles/tokens.css` define em `:root` (categorias pedidas no backlog):

| Categoria | Tokens |
| --- | --- |
| **Spacing** | `--space-0..8` (escala base 4px) |
| **Radius** | `--radius-sm/md/lg/xl/full` |
| **Colors** | primitivos (`--color-slate-*`, `--color-brand-*`, success/warning/danger/info) + **semânticos** (`--color-bg`, `--color-surface`, `--color-border`, `--color-text`, `--color-primary`, …) |
| **Typography** | `--font-sans/mono`, `--font-size-xs..2xl`, `--font-weight-*`, `--line-height-*` |
| **Shadows** | `--shadow-sm/md/lg` |
| Layout (extra) | `--layout-max-width`, `--header-height` |

- `reset.css`: reset moderno mínimo (box-sizing, margens, media block, herança de fontes em inputs).
- `global.css`: estilo base de elementos (body, headings, links, code, `:focus-visible`) — **só** via `var(--token)`.
- `index.css`: entry com ordem correcta `tokens → reset → global`, importado uma vez em `main.tsx`.

Componentes usam **CSS Modules** (`*.module.css`) — ver `RootLayout.module.css`, `NotFoundPage.module.css`. Decisão FE-PDEC-001 (CSS Modules + tokens, sem Tailwind) materializada.

---

## 4. App root e layout

- **`App.tsx`**: limpo de todo o template Vite; renderiza `RootLayout` com um bloco placeholder. Será embrulhado por providers e substituído/composto pelo router em FE-004.
- **`RootLayout`**: frame mínimo (top bar com nome do produto + área central com `max-width`). Recebe `children: ReactNode` por agora; será adaptado para o `<Outlet />` do react-router em FE-004 (anotado em comentário no ficheiro).
- **Removido**: `src/App.css`, `src/index.css`, `src/assets/{react.svg,vite.svg,hero.png}` e a pasta `assets/` (todos resíduos de template, sem uso). `index.html` e `public/` mantidos intactos.

---

## 5. Regras de dependência (documentadas em `src/README.md`)

```
app      → shared, entities, features, widgets, pages
pages    → shared, entities, features, widgets
widgets  → shared, entities, features
features → shared, entities
entities → shared
shared   → (nada acima)
```

Reforçado também: **única fronteira de rede = `shared/api`**, só Backend Core; nunca IE/Renderer directos; nunca `X-Internal-Token`.

---

## 6. Validações executadas

| Verificação | Comando | Resultado |
| --- | --- | --- |
| Lint | `pnpm lint` | ✅ exit 0 — 0 erros, 0 avisos |
| Typecheck + build | `pnpm build` (`tsc -b && vite build`) | ✅ exit 0 — 21 módulos, `dist` gerado (e depois removido) |
| Alias `@/` em build | (via `vite build`) | ✅ resolve correctamente |
| Imports circulares | inspecção manual + build | ✅ nenhum (dependências só descem de camada) |
| `src/components` gigante | inspecção | ✅ não existe |

> O `dist/` gerado pela validação foi removido (artefacto de build, já ignorado pelo ESLint via `globalIgnores(['dist'])`).

---

## 7. Critérios de aceitação — verificação

| Critério (FE-002) | Estado |
| --- | --- |
| Estrutura modular existe | ✅ §1 |
| App arranca/renderiza sem erro | ✅ build OK; App+RootLayout renderizam o placeholder |
| Build passa | ✅ §6 |
| Lint passa ou limitação documentada | ✅ passa sem avisos |
| Não há imports circulares óbvios | ✅ §6 |
| Não há `src/components` gigante | ✅ §6 |
| Arquitectura inicial documentada | ✅ READMEs por camada + este relatório |

---

## 8. Notas para os prompts seguintes

- **FE-003**: criar `shared/api` (client + erros + headers) e leitura de `VITE_BACKEND_API_BASE_URL`; adicionar `.env.example`. A pasta `app/config` já existe para acomodar a config de ambiente.
- **FE-004**: preencher `app/providers` e `app/router`; trocar `RootLayout` `children` por `<Outlet />`; montar rotas (`/`, `/campaigns`, `/campaigns/:id`, `/campaigns/:id/war-room`, `/settings`, `*` → `NotFoundPage`).
- **Convenção de barris**: continuar a criar `index.ts` só quando a slice tiver API pública real (evita barris vazios e potenciais avisos de `react-refresh`).
- **Limpeza fora de âmbito**: a pasta vazia `frontend1/` (raiz do repo) continua por remover — assinalada no Prompt 01, fora do âmbito deste prompt.

---

## 9. Ficheiros alterados/criados

**Configuração:** `vite.config.ts` (alias), `tsconfig.app.json` (paths).
**Removidos:** `src/App.css`, `src/index.css`, `src/assets/*`.
**Reescritos:** `src/App.tsx`, `src/main.tsx`.
**Novos (conteúdo):** `src/README.md`; `app/README.md`, `app/config/{app.config.ts,index.ts}`, `app/layouts/{RootLayout.tsx,RootLayout.module.css,index.ts}`; `shared/README.md`, `shared/styles/{tokens,reset,global,index}.css`; `entities/README.md`, `features/README.md`, `widgets/README.md`, `pages/README.md`; `pages/not-found/{NotFoundPage.tsx,NotFoundPage.module.css,index.ts}`.
**Placeholders:** `.gitkeep` em todas as slices ainda não implementadas.
