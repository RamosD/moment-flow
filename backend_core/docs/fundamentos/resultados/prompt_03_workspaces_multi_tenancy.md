# Relatório de execução — Prompt 03: Workspaces e Multi-tenancy

- **Pipeline / Backlog:** Pipeline 03 — Workspaces e multi-tenancy (BCORE-201, BCORE-202, BCORE-203; + base BCORE-401 parcial)
- **Data:** 2026-06-21
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`

---

## 1. Prompt executado

Implementar `apps.workspaces` com os modelos `Workspace` (UUID, name, slug,
workspace_type, country, market, default_language, timezone, status, created_by,
timestamps, deleted_at, metadata) e `WorkspaceMember` (workspace, user, role
textual temporário, status, invited_by, joined_at, timestamps, unique
workspace+user). Criar serializers/viewsets, criação de workspace pelo utilizador
autenticado com atribuição automática de membro **owner activo**, mecanismo de
resolução do workspace activo via header **X-Workspace-ID** com bloqueio de
acesso a quem não é membro activo, registo no Admin, endpoints em
`/api/v1/workspaces/` e `/api/v1/workspace-members/`, e testes de multi-tenancy.

## 2. Objectivo

Estabelecer a fundação SaaS multi-tenant: todas as entidades de cliente passarão
a pertencer a um workspace; um utilizador pode pertencer a vários workspaces; e o
isolamento entre tenants é garantido por membership + header `X-Workspace-ID`,
sem workspace global implícito e sem acesso cross-workspace.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/workspaces/__init__.py` | Pacote da app |
| `apps/workspaces/apps.py` | `WorkspacesConfig` (`name = "apps.workspaces"`) |
| `apps/workspaces/models.py` | `Workspace` + `WorkspaceMember` (enums, unique constraint) |
| `apps/workspaces/services.py` | `create_workspace` (owner automático), `generate_unique_slug` |
| `apps/workspaces/permissions.py` | `resolve_active_workspace`, `get_current_workspace`, `IsWorkspaceMember` |
| `apps/workspaces/serializers.py` | `WorkspaceSerializer`, `WorkspaceMemberSerializer` |
| `apps/workspaces/views.py` | `WorkspaceViewSet` (+ acção `current`), `WorkspaceMemberViewSet` |
| `apps/workspaces/urls.py` | Router DRF (`workspaces`, `workspace-members`) |
| `apps/workspaces/admin.py` | `WorkspaceAdmin`, `WorkspaceMemberAdmin` |
| `apps/workspaces/migrations/__init__.py` | Pacote de migrations |
| `apps/workspaces/migrations/0001_initial.py` | Migration inicial (Workspace, WorkspaceMember) |
| `apps/workspaces/tests/__init__.py` | Pacote de testes |
| `apps/workspaces/tests/conftest.py` | Fixtures (`user_a`, `user_b`, `client_a`, `client_b`) |
| `apps/workspaces/tests/test_workspaces_api.py` | Criação, isolamento e header X-Workspace-ID |
| `apps/workspaces/tests/test_models.py` | Owner automático, unicidade, soft delete |
| `docs/.../resultados/prompt_03_workspaces_multi_tenancy.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `apps/core/models.py` | Adicionados `SoftDeleteQuerySet`, `SoftDeleteManager`, `SoftDeleteModel` (mixin `deleted_at` + soft delete) |
| `config/settings.py` | `"apps.workspaces"` adicionado a `INSTALLED_APPS` |
| `config/urls.py` | `include("apps.workspaces.urls")` montado em `api/v1/` |

## 5. Migrations criadas

```text
apps/workspaces/migrations/0001_initial.py
    + Create model Workspace
    + Create model WorkspaceMember   (UniqueConstraint workspace+user)
```

`apps.core` **não** gera migration nova: `SoftDeleteModel` é abstracto.

## 6. Comandos executados

```powershell
python manage.py makemigrations            # workspaces/0001_initial
python manage.py migrate                   # aplica workspaces.0001_initial
python manage.py check                     # 0 issues
python -m pytest -q                        # 29 passed
ruff check .                               # All checks passed!
python manage.py spectacular --file schema.yml   # 0 errors, inclui endpoints
```

## 7. Resultado das validações

| Validação | Resultado |
|---|---|
| `makemigrations` / `migrate` | OK — `workspaces.0001_initial` aplicada |
| `manage.py check` | OK — `System check identified no issues (0 silenced)` |
| `pytest` | **29 passed** (3 core + 12 accounts + 14 workspaces) |
| `ruff check .` | OK — `All checks passed!` |
| OpenAPI (`spectacular`) | OK — 0 erros; inclui `/api/v1/workspaces/`, `/api/v1/workspaces/{id}/`, `/api/v1/workspaces/current/`, `/api/v1/workspace-members/`, `/api/v1/workspace-members/{id}/` |

**Nota benigna:** mantém-se o `UserWarning: No directory at ...\staticfiles\`
(WhiteNoise) durante o `pytest`; desaparece após `collectstatic`.

## 8. Decisões tomadas

- **`SoftDeleteModel` em `apps.core`** (antecipação de BCORE-401): `deleted_at`,
  `objects` esconde soft-deleted, `all_objects` devolve tudo, e
  `base_manager_name = "all_objects"` para não truncar lookups por FK reversa. O
  Admin usa `all_objects` para mostrar registos apagados.
- **`Workspace(BaseModel, SoftDeleteModel)`**: UUID PK + timestamps + soft delete.
  `status` default `trial`; tipos e estados via `TextChoices`.
- **Slug automático e único**: gerado de `name` (`slugify`), com sufixo
  incremental verificado contra `all_objects` (a unique constraint da BD abrange
  também os soft-deleted). `slug` é read-only na API.
- **Owner automático**: `create_workspace` corre em `transaction.atomic` e cria o
  `WorkspaceMember` do criador com `role="owner"`, `status="active"`,
  `joined_at=now()`, `invited_by=self`.
- **`WorkspaceMember.role` é texto temporário** (default `"viewer"`, constante
  `ROLE_OWNER`); será convertido para FK a `apps.rbac.Role` na fase de RBAC.
  Unicidade garantida por `UniqueConstraint(workspace, user)`.
- **Multi-tenancy via `X-Workspace-ID`**: `resolve_active_workspace` devolve 400
  para header ausente/malformado e 403 para workspace inexistente **ou** sem
  membership activo (sem distinguir, para não revelar existência). Exposto e
  testável em `GET /api/v1/workspaces/current/` (permission `IsWorkspaceMember`).
- **Isolamento estrito**: `WorkspaceViewSet.get_queryset` filtra pelos memberships
  activos do requester; aceder a workspace alheio devolve 404 (fora do queryset).
  `WorkspaceMemberViewSet` confina operações aos workspaces do requester.
- **OpenAPI limpo**: `queryset = ...none()` + guarda `swagger_fake_view` nos
  viewsets para tipar o parâmetro `id` e evitar introspecção com `AnonymousUser`.

## 9. Pendências

- **RBAC real** (Pipeline 04): `role` ainda é texto; falta `Role`/`Permission`/
  `RolePermission`, seed de roles de sistema e guards `HasWorkspacePermission`.
  Enquanto isso, qualquer membro activo pode gerir membros (sem verificação de
  papel) — a ser restringido na fase de RBAC.
- **BCORE-204** (WorkspaceSettings/Branding) não implementado.
- **Convites por email reais** não implementados (apenas `invited_by`).
- **Paginação e filtros padrão** (BCORE-403) ainda não configurados; os testes
  são robustos a respostas paginadas ou em lista.
- **`collectstatic`** ainda não corrido (apenas relevante para produção).

## 10. Próximo passo recomendado

Avançar para **Pipeline 04 — RBAC e permissões** (BCORE-301/302): criar
`apps.rbac` com `Role`, `Permission`, `RolePermission`, seed das roles de sistema
(owner, admin, manager, editor, viewer, billing_admin, api_user) e das permissions
base; converter `WorkspaceMember.role` de texto para FK a `Role` (com migration de
dados); e implementar os guards reutilizáveis `IsWorkspaceMember` (mover/partilhar
com workspaces) e `HasWorkspacePermission`, com testes por role. Isto fecha a
fundação de identidade + tenancy + autorização antes de iniciar o catálogo
musical (Pipeline 05).
