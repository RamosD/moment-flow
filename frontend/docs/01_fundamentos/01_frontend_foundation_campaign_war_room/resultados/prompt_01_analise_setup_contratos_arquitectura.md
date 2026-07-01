# FE-001 — Análise de setup, contratos e arquitectura alvo

**Fase:** Frontend Foundation & Campaign War Room MVP
**Componente alvo:** `frontend`
**Data:** 2026-06-26
**Tipo:** Relatório de análise (sem alteração de runtime, salvo este documento e a criação da pasta `resultados/`)

---

## 0. Sumário executivo

- O frontend é um scaffold Vite + React 19 + TypeScript 6 **limpo** (template inicial), sem router, sem camada de API, sem estrutura modular. Ponto de partida saudável: `pnpm lint` e `tsc -b` passam sem erros.
- O **Backend Core expõe um schema OpenAPI real e versionado** (`backend_core/schema.yml`, 9319 linhas). **Todas** as rotas críticas do backlog foram **confirmadas** no schema e no código Django — nenhuma fica como "provável".
- O endpoint central da War Room — `POST /api/v1/campaigns/{id}/intelligence/` — está confirmado, mas com **dois desvios relevantes face ao backlog**: responde **HTTP 200** (não 201) e o **corpo do POST é vazio** (`request=None`).
- A resposta de intelligence tem **envelope bem definido**, mas o **miolo (`result.analysis`, `result.scores`, `result.moments`, `result.recommendations`) é fracamente tipado** no schema (objectos/arrays genéricos). Isto obriga a tipagem defensiva no frontend (campos opcionais / validação tolerante).
- `X-Internal-Token` **confirmado como segredo serviço-a-serviço**: aparece apenas em `apps/integrations_bridge/*` (Backend Core ↔ IE/Renderer). **Nunca** deve existir no frontend. ✅
- **CORS já está preparado** para o dev server do Vite (`http://localhost:5173`). Integração local frontend↔backend é viável sem alterações no backend.
- Stack do frontend é **bleeding-edge** (React 19.2, Vite 8, TS 6, ESLint 10, @types/node 24). É o maior risco técnico — instalar dependências uma a uma e validar `lint`/`tsc` a cada passo.

---

## 1. Estado actual do frontend

### 1.1 Localização e estrutura

```
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json            (referências para app + node)
├── tsconfig.app.json
├── tsconfig.node.json
├── eslint.config.js         (flat config)
├── public/
└── src/
    ├── main.tsx             (createRoot + StrictMode → <App/>)
    ├── App.tsx              (template Vite/React: logos, contador)
    ├── App.css
    ├── index.css
    └── assets/              (hero.png, react.svg, vite.svg)
```

> Nota: existe uma pasta `frontend1/` **vazia** na raiz do repositório (provável engano de scaffolding). Não é usada; recomenda-se removê-la fora desta fase.

### 1.2 Dependências instaladas (`frontend/package.json`)

| Pacote | Versão | Observação |
| --- | --- | --- |
| react / react-dom | ^19.2.7 | React 19 (nova era de tipos, `ReactNode`, etc.) |
| vite | ^8.1.0 | Vite 8 (recente) |
| @vitejs/plugin-react | ^6.0.2 | resolvido p/ 6.0.3 em node_modules |
| typescript | ~6.0.2 | **TS 6** — muito recente |
| typescript-eslint | ^8.61.0 | resolvido p/ 8.62 |
| eslint | ^10.5.0 | ESLint 10, flat config |
| eslint-plugin-react-hooks | ^7.1.1 | |
| eslint-plugin-react-refresh | ^0.5.3 | |
| @types/node | ^24.13.2 | Node types 24 |
| @types/react / @types/react-dom | ^19.2.x | |
| globals | ^17.6.0 | |

Gestor de pacotes: **pnpm 11.9.0** (fixado em `packageManager`).

### 1.3 Configuração

- **`tsconfig.app.json`**: `target ES2023`, `module esnext`, `moduleResolution: bundler`, `verbatimModuleSyntax: true`, `noUnusedLocals/Parameters: true`, `erasableSyntaxOnly: true`, `noEmit: true`, `jsx: react-jsx`. **Sem `baseUrl`/`paths`** → não há aliases de import configurados.
- **`vite.config.ts`**: mínimo, só `react()`. **Sem `resolve.alias`, sem `server.proxy`, sem config de env.**
- **`eslint.config.js`**: flat config com `js.recommended` + `typescript-eslint.recommended` + `react-hooks` + `react-refresh`. Globals `browser`.
- **Sem framework de testes** (sem Vitest/Testing Library). Confirma FE-PDEC-004 como pendente.
- **Sem ficheiro `.env`/`.env.example`** nem leitura de `VITE_*`.

### 1.4 Scripts — confirmação

| Script | Comando | Estado |
| --- | --- | --- |
| `pnpm dev` | `vite` | Presente (não executado para não abrir servidor; config válida) |
| `pnpm build` | `tsc -b && vite build` | Presente. **`tsc -b` validado (exit 0)**; `vite build` não corrido para não gerar `dist/` |
| `pnpm lint` | `eslint .` | **Executado: passa sem erros/avisos** ✅ |
| `pnpm preview` | `vite preview` | Presente |

**Verificações executadas neste prompt (read-only):**
- `pnpm lint` → **0 problemas**.
- `pnpm exec tsc -b` → **exit 0** (typecheck limpo; `noEmit` activo, não gera artefactos).

Conclusão: o scaffold está funcional e saudável. Build/lint passam na base.

---

## 2. Backend Core — fonte de verdade dos contratos

O Backend Core é uma aplicação **Django + DRF** com:
- Autenticação **JWT (SimpleJWT)**, login **por email** (modelo de utilizador sem username).
- Multi-tenancy por **workspace** via header **`X-Workspace-ID`** (validado por `WorkspaceScopedRBACViewSet` + RBAC por permissões).
- **Schema OpenAPI** gerado por `drf-spectacular`, disponível em:
  - `GET /api/v1/schema/` (YAML/JSON)
  - `GET /api/v1/docs/` (Swagger UI)
  - `GET /api/v1/redoc/` (ReDoc)
  - Cópia em repositório: **`backend_core/schema.yml`**.

### 2.1 Configuração relevante (confirmada em `config/settings.py`)

- `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES = [JWTAuthentication]`, `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]`.
- `SIMPLE_JWT`: `ACCESS_TOKEN_LIFETIME` default **60 min**, `REFRESH_TOKEN_LIFETIME` default **7 dias**.
- Paginação default: `PAGE_SIZE = 25` (`StandardResultsSetPagination`).
- **CORS** (`CORS_ALLOWED_ORIGINS`) default: `http://localhost:5173,http://127.0.0.1:5173` → **alinha com o dev server do Vite**. ✅

---

## 3. Rotas confirmadas (não "prováveis")

Todas verificadas em `backend_core/schema.yml` + `config/urls.py` + `apps/*/views.py`.

| Necessidade (backlog) | Rota real | Método | Auth | `X-Workspace-ID` | Estado |
| --- | --- | --- | --- | --- | --- |
| Login / token | `/api/v1/auth/token/` | POST | — (público) | não | ✅ Confirmado |
| Refresh token | `/api/v1/auth/token/refresh/` | POST | — | não | ✅ Confirmado |
| Verify token | `/api/v1/auth/token/verify/` | POST | — | não | ✅ Confirmado (bónus) |
| Utilizador autenticado | `/api/v1/auth/me/` | GET/PUT/PATCH | jwt | não | ✅ Confirmado (bónus) |
| Listar workspaces | `/api/v1/workspaces/` | GET | jwt | **não** | ✅ Confirmado |
| Workspace activo | `/api/v1/workspaces/current/` | GET | jwt | **sim** | ✅ Confirmado (bónus) |
| Detalhe workspace | `/api/v1/workspaces/{id}/` | GET | jwt | não | ✅ Confirmado |
| Listar campanhas | `/api/v1/campaigns/` | GET | jwt | **sim** | ✅ Confirmado |
| Detalhe campanha | `/api/v1/campaigns/{id}/` | GET | jwt | **sim** | ✅ Confirmado |
| **Intelligence** | `/api/v1/campaigns/{id}/intelligence/` | **POST** | jwt | **sim** | ✅ Confirmado (ver §4) |
| Health dependências | `/api/v1/system/health/dependencies/` | GET | jwt (**staff only**) | não | ⚠️ Confirmado, mas restrito a staff |
| Content outputs | `/api/v1/content-outputs/` (+ `/{id}/`, `/{id}/export/`) | GET/POST | jwt | sim | ✅ Existe (FE-012) |
| Reports | `/api/v1/reports/` (+ `report-sections`) | GET/… | jwt | sim | ✅ Existe (FE-012) |
| Media kits | `/api/v1/media-kits/` (+ `media-kit-items`) | GET/… | jwt | sim | ✅ Existe (FE-012) |

Outras rotas presentes e úteis em fases futuras: `artists`, `tracks`, `track-platform-links`, `campaign-tracks`, `campaign-goals`, `templates`, `content-packs`, `smart-links`, `billing/*`, `notifications`, `workspace-members`.

---

## 4. Contrato do endpoint central da War Room

`POST /api/v1/campaigns/{id}/intelligence/`

### 4.1 Pedido

- **Método:** `POST`.
- **Corpo:** **vazio** (`request=None` no `@extend_schema`; o endpoint reconstrói o bundle a partir da campanha). Enviar `{}` ou corpo vazio.
- **Headers obrigatórios:**
  - `Authorization: Bearer <access_token>`
  - `X-Workspace-ID: <workspace_uuid>`
  - `Content-Type: application/json`
- **Permissão:** `campaigns:view` (read-only enrichment; não persiste nada).

### 4.2 Resposta — **HTTP 200** (⚠️ não 201)

Schema `CampaignIntelligenceResponse` (envelope estável):

```jsonc
{
  "status": "string",                 // ex.: completed
  "source": "engine" | "dry_run",     // SourceEnum
  "engine": "string",
  "engine_version": "string",
  "request_id": "string",
  "workspace_id": "string",
  "campaign_id": "string",
  "result": {                         // CampaignIntelligenceResult
    "analysis": { /* objecto genérico (additionalProperties) */ },
    "scores":   { /* objecto genérico (additionalProperties) */ },
    "grade":    "string | null",
    "moments":  [ /* array não tipado (items: {}) */ ],
    "recommendations": [ /* array não tipado (items: {}) */ ],
    "summary":  "string"
  },
  "explanations": [ { /* objectos genéricos */ } ],
  "warnings":     [ { /* objectos genéricos */ } ],
  "metadata":     { /* objecto genérico */ },
  "generated_at": "string"
}
```

**Obrigatórios** (schema `required`): `status, source, engine, engine_version, request_id, workspace_id, campaign_id, result, generated_at`. Dentro de `result`, nenhum subcampo é marcado `required` → tratar todos como opcionais.

### 4.3 Erros do endpoint (confirmados em `apps/campaigns/views.py`)

| HTTP | `code` | Significado | Tratamento FE |
| --- | --- | --- | --- |
| 404 | — | Campanha não existe **neste workspace** (ou soft-deleted) | NotFound / "campanha não encontrada" |
| 503 | `intelligence_unavailable` | Engine temporariamente indisponível (retryable) | ServiceUnavailable + opção retry |
| 503 | `intelligence_disabled` | Intelligence desligada por config | ServiceUnavailable (mensagem distinta) |
| 502 | `intelligence_upstream_error` | Engine respondeu erro não exponível | Erro upstream genérico |
| 401 | — | Token ausente/inválido | Redireccionar p/ login |
| 403 | — | Sem permissão / workspace errado | PermissionDenied |

> `source: "dry_run"` indica que o backend devolveu resultado simulado (engine não chamado realmente). O frontend deve **mostrar esse estado honestamente** (badge/aviso) — alinha com FE-RSK-010.

---

## 5. Contratos de domínio adicionais (confirmados)

### 5.1 Auth
- `TokenObtainPair` (request): `email` + `password` (writeOnly) → (response) `access` + `refresh`.
- `TokenRefresh`: `refresh` (writeOnly) → `access`.
- `User` (`/auth/me/`): `id, email, full_name, display_name, avatar_url, preferred_language, timezone, is_email_verified, is_active, is_staff, date_joined, last_login, email_verified_at`.

### 5.2 Campaign (`Campaign`)
`id (uuid), workspace (uuid, RO), artist (uuid, req), track (uuid|null), name, slug (RO), campaign_type (enum), status (enum), start_date|null, end_date|null, primary_goal, description, created_by (uuid|null, RO), metadata, created_at, updated_at`.

- `CampaignStatusEnum`: `draft|scheduled|active|paused|completed|archived`.
- `CampaignTypeEnum`: `single_release|music_video_release|album_release|milestone_campaign|comeback_campaign|weekly_growth_campaign|catalogue_push|media_campaign|custom`.
- Listagem é **paginada** (`PaginatedCampaignList`: `count, next, previous, results[]`) e filtrável por `status, campaign_type, artist, track, search, ordering, page, page_size, start_date_after/before`.

### 5.3 Workspace (`Workspace`)
`id (uuid), name, slug (RO), workspace_type (enum), country, market, default_language, timezone, status (enum, RO), created_by (uuid|null, RO)`.
- Listagem paginada (`PaginatedWorkspaceList`), **scoped às memberships activas do utilizador** (não precisa de header).

### 5.4 Outputs (FE-012)
- `ContentOutput` tem FK `campaign` → é possível **filtrar content-outputs por campanha**.
- Relação `reports`/`media-kits` ↔ campanha **não está garantida no schema** (precisa de confirmação de query params no FE-012). Usar placeholders honestos se não houver filtro por campanha.

---

## 6. Segurança — `X-Internal-Token`

**Confirmado**: `X-Internal-Token` é segredo de comunicação **serviço-a-serviço**. Aparece **apenas** em:
- `apps/integrations_bridge/clients.py`, `health.py`, `intelligence_sync.py`, `logging_utils.py`
- e respectivos testes / comando de smoke.

Ou seja: é o Backend Core que assina os pedidos ao Intelligence Engine / Content Renderer. **Não há nenhum caminho legítimo para o frontend conhecê-lo ou enviá-lo.**

**Regra para o frontend (a aplicar e a testar/grep nas fases seguintes):**
- O API client **só** monta `Authorization`, `X-Workspace-ID`, `Content-Type`.
- Adicionar um teste/grep de CI ou script que falha se `X-Internal-Token`/`INTERNAL_TOKEN` aparecer em `frontend/src`. (FE-RSK-003)

---

## 7. Lacunas de contrato / incertezas

| # | Lacuna | Impacto | Acção |
| --- | --- | --- | --- |
| C-01 | `result.analysis`/`scores` são objectos genéricos; `moments`/`recommendations` são arrays sem item-schema | Alto | Tipar defensivamente (`Record<string, unknown>` + tipos parciais conhecidos opcionais). Validação **tolerante** (Zod `.passthrough()` / `.catchall`). Documentar campos como incertos (FE-006/FE-010). |
| C-02 | Intelligence devolve **200, não 201**; corpo do POST **vazio** | Médio | Ajustar client/hook: aceitar 200; POST sem body. |
| C-03 | `health/dependencies` é **staff-only** + resposta `object` genérica | Médio | Não depender dele para utilizadores normais; usar só em vista de diagnóstico/staff. Tratar 403 silenciosamente. |
| C-04 | **Sem endpoint de logout** no schema (sem blacklist visível) | Baixo | Logout é **client-side** (descartar tokens + limpar query cache). Documentar como limitação. |
| C-05 | Relação reports/media-kits ↔ campanha não confirmada | Médio | FE-012: confirmar query params; senão placeholders honestos. |
| C-06 | Intelligence **não persiste** (recalcula a cada POST) | Baixo | TanStack Query: tratar como mutation ou query com `staleTime` curto; sem assumir cache no servidor. |
| C-07 | Forma exacta dos erros DRF (corpo do 4xx/5xx) não detalhada no schema | Médio | Assumir formato DRF padrão (`{detail, code}` / `{campo: [erros]}`); normalizar defensivamente (FE-003/FE-013). |

---

## 8. Dependências recomendadas (a instalar nos prompts seguintes — **não instalar agora**)

Compatibilidade avaliada face a **React 19 / Vite 8 / TS 6 / ESLint 10**. `skipLibCheck: true` mitiga incompatibilidades de tipos de libs.

### 8.1 Núcleo (FE-003/FE-004) — recomendadas
| Pacote | Versão alvo | Justificação / compat |
| --- | --- | --- |
| `react-router-dom` | v7.x | Compatível com React 19; ESM. Routing das rotas do backlog. |
| `@tanstack/react-query` | v5.x | Suporta React 19; server-state (regra: não guardar server state em estado global local). |
| `zod` | v3.x (ou v4 estável) | Validação tolerante das respostas de intelligence. |
| `react-hook-form` | v7.x | Suporta React 19; formulário de login. |
| `@hookform/resolvers` | compatível c/ zod escolhido | Ligação zod↔RHF. |
| `clsx` | latest | Composição de classes. |
| `lucide-react` | latest | Ícones; suporta React 19. |

### 8.2 Opcionais (instalar só se necessário)
| Pacote | Quando |
| --- | --- |
| `zustand` | Só para estado de UI cliente (ex.: workspace activo) se Context+localStorage não chegar. **Preferir Context nesta fase.** |
| `date-fns` | Formatação de datas (`start_date`, `generated_at`). |
| `tailwindcss` + `class-variance-authority` | Só se a equipa decidir Tailwind (FE-PDEC-001). |

### 8.3 Regras de instalação (mitiga FE-RSK-008)
1. Instalar **um pacote (ou par) de cada vez** com `pnpm add`.
2. Após cada instalação: correr `pnpm lint` **e** `pnpm exec tsc -b`.
3. Se um peer dependency exigir React/Vite/TS diferente, **não forçar** — registar e escolher versão compatível.
4. Manter `pnpm-lock.yaml` versionado.

---

## 9. Decisões propostas (resolver as pendências do backlog)

| Decisão | Recomendação |
| --- | --- |
| **FE-PDEC-001** Tailwind vs CSS | **CSS Modules + design tokens** (variáveis CSS globais: spacing/radius/colors/typography/shadows). Evita overhead de Tailwind no MVP. |
| **FE-PDEC-002** Auth real vs dev | **Auth real** — endpoints `auth/token/*` existem e estão confirmados. Ecrã de login email+password. |
| **FE-PDEC-003** Persistência do token | Access token em **memória** (state do AuthProvider) + refresh token em `localStorage` para sobreviver a reload, com refresh on-401. Aceitável para piloto; documentar trade-off XSS. Nunca logar tokens. |
| **FE-PDEC-004** Test framework | **Adiar** Vitest para esta fase (build/lint são o mínimo). Deixar gancho documentado. |
| **FE-PDEC-005** Gerar types do OpenAPI | **Manual** nesta fase (miolo de intelligence é instável). Reavaliar geração automática depois. |
| **Path aliases** | Adicionar `@/* → src/*` em `tsconfig.app.json` (`paths`) + `vite.config.ts` (`resolve.alias`). Facilita arquitectura por camadas. |

---

## 10. Arquitectura alvo (resumo a implementar em FE-002)

Estrutura Feature-Sliced (conforme backlog §6): `app/`, `shared/`, `entities/`, `features/`, `widgets/`, `pages/`. Regras de dependência unidireccionais (`shared` não importa nada acima; `app` no topo).

**Regra inviolável de fronteira:** o **único** ponto de saída de rede é `shared/api` (API client), apontando **só** para `VITE_BACKEND_API_BASE_URL` (Backend Core). Nenhum módulo chama IE/Renderer. (FE-RSK-002)

---

## 11. Riscos registados

| ID | Risco | Estado / evidência | Mitigação nesta pipeline |
| --- | --- | --- | --- |
| FE-RSK-002 | Acoplamento directo a IE/Renderer | Mitigável: backend é a fronteira; CORS aponta ao :8000 | API client único → só Backend Core; revisão em FE-003/FE-010 |
| FE-RSK-003 | `X-Internal-Token` no browser | Confirmado interno (só `integrations_bridge`) | Client nunca o monta; grep/teste de guarda |
| FE-RSK-004 | Contratos reais ≠ assumidos | **Mitigado** — schema real confirmado; desvios catalogados (§4.2, §7) | Tipos derivados do `schema.yml`; campos incertos opcionais |
| FE-RSK-005 | Auth/workspace subestimados | Auth e workspace bem definidos no backend | AuthProvider + WorkspaceProvider desde FE-004/FE-007/FE-008 |
| FE-RSK-008 | Versões bleeding-edge (React 19/Vite 8/TS 6/ESLint 10) | **Risco principal** | Instalação incremental + `lint`/`tsc` a cada passo (§8.3) |
| FE-RSK-001 | Frontend vira protótipo desorganizado | Scaffold ainda é template | Foundation modular (FE-002) antes da War Room |
| FE-RSK-006 | Overengineering visual | — | CSS tokens, design system mínimo |
| FE-RSK-007 | War Room sem dados de assets/reports | Relação reports↔campanha incerta (C-05) | Placeholders honestos + documentar dependência |
| FE-RSK-009 | 502/503 não tratados | Endpoint devolve 502/503 reais (§4.3) | Tratamento transversal de erros (FE-013) |
| FE-RSK-010 | Declarar piloto sem validar real | `source: dry_run` existe | Distinguir engine vs dry_run na UI; estado final honesto |

---

## 12. Plano técnico dos prompts seguintes

| Prompt | Entregável | Contratos/decisões a usar |
| --- | --- | --- |
| **FE-002** Foundation estrutural | Camadas FSD, design tokens, layout base, App root limpo, **aliases `@/`** | §9 (aliases), §10 |
| **FE-003** API client + ambiente | `.env.example` (`VITE_BACKEND_API_BASE_URL=http://localhost:8000/api/v1`); client com `Authorization`/`X-Workspace-ID`/`Content-Type`; normalização de erros DRF; tipos de erro (Api/Unauthorized/Forbidden/NotFound/Validation/ServiceUnavailable); **guarda anti-`X-Internal-Token`** | §2.1, §4.1, §6, C-07 |
| **FE-004** Routing + Query + Providers | `react-router-dom` v7, `@tanstack/react-query` v5; rotas `/`, `/campaigns`, `/campaigns/:id`, `/campaigns/:id/war-room`, `/settings`, `*`; AuthProvider/WorkspaceProvider | §8.1 |
| **FE-005** UI foundation | Button/Card/Badge/Alert/PageHeader/Section/Loading/Empty/Error/Skeleton (CSS Modules) | FE-PDEC-001 |
| **FE-006** Entidades/tipos | Tipos de `Campaign`, `Workspace`, `User`, `CampaignIntelligence*` alinhados ao schema; **miolo de intelligence opcional**; Zod tolerante p/ resposta de intelligence | §5, C-01 |
| **FE-007** Auth/session | Login email+password → `auth/token/`; refresh via `auth/token/refresh/`; `auth/me/`; ProtectedRoute; logout client-side | §5.1, FE-PDEC-002/003, C-04 |
| **FE-008** Workspace | `useWorkspaces` (`/workspaces/`), selecção activa, injecção de `X-Workspace-ID`, `workspaces/current/`, invalidação de queries ao trocar | §5.3 |
| **FE-009** Páginas campanhas | `useCampaigns` (paginado/filtros), `useCampaign`; lista + detalhe + link War Room; loading/error/empty | §5.2 |
| **FE-010** Campaign Intelligence | `useCampaignIntelligence` → **POST sem body, aceitar 200**, `source dry_run`, warnings/explanations; componentes IntelligenceSummary/GradeBadge/ScoreGrid/RecommendationsList/MomentsList/WarningsPanel/ExplanationsPanel | §4 |
| **FE-011** War Room MVP | Composição da página `/campaigns/:id/war-room` com header + intelligence + estados | §4, §8 do backlog |
| **FE-012** Assets/Reports/Media Kits | `content-outputs?campaign=…`; reports/media-kits — **confirmar filtro por campanha**, senão placeholders | §5.4, C-05 |
| **FE-013** Erros transversais | 401→login, 403→PermissionDenied, 404, 422, 502/503→ServiceUnavailable, network; sem tokens em mensagens | §4.3, C-07 |
| **FE-014** Documentação arquitectura | `arquitectura_frontend.md` | tudo acima |
| **FE-015** Validação final | `pnpm build`/`lint` (+ dev se possível); estado honesto; relatório final | §1.4 |

---

## 13. Critérios de aceitação — verificação

| Critério (FE-001) | Estado |
| --- | --- |
| Relatório de análise criado | ✅ Este documento |
| Estrutura actual do frontend documentada | ✅ §1 |
| Rotas reais confirmadas ou marcadas como pendentes | ✅ §3 (todas confirmadas; restritas/incertas marcadas) |
| Contratos críticos identificados | ✅ §4, §5 |
| Dependências recomendadas listadas | ✅ §8 |
| Riscos registados | ✅ §11 |
| Plano de execução definido | ✅ §12 |
| Nenhum runtime alterado sem necessidade | ✅ Só criada a pasta `resultados/` e este `.md`; `lint`/`tsc` correram read-only |

---

## 14. Anexos — fontes inspeccionadas

- `frontend/package.json`, `vite.config.ts`, `tsconfig*.json`, `eslint.config.js`, `src/{main,App}.tsx`
- `backend_core/config/urls.py`, `backend_core/config/settings.py`
- `backend_core/schema.yml` (OpenAPI; secções auth, workspaces, campaigns, intelligence, health, schemas)
- `backend_core/apps/campaigns/views.py` (endpoint de intelligence e códigos de erro)
- `backend_core/apps/integrations_bridge/*` (confirmação de `X-Internal-Token` como segredo interno)
- Execução: `pnpm --version` (11.9.0), `pnpm lint` (0 erros), `pnpm exec tsc -b` (exit 0)
