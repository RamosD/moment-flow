# Relatório de execução — Prompt 04: RBAC e Permissões

- **Pipeline / Backlog:** Pipeline 04 — RBAC e permissões (BCORE-301, BCORE-302)
- **Data:** 2026-06-21
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`

---

## 1. Prompt executado

Implementar `apps.rbac` com `Role`, `Permission` e `RolePermission`; alinhar
`WorkspaceMember.role` (texto temporário) com um FK a `Role`, preservando dados;
seed idempotente das roles de sistema e permissions base; serviços
`user_has_permission`, `get_user_workspace_role`, `require_workspace_permission`;
permission classes DRF `IsWorkspaceMember` e `HasWorkspacePermission`; aplicar
permissões nos endpoints de workspaces/members; registo no Admin; e testes de
RBAC por role.

## 2. Objectivo

Tornar o Django a autoridade de permissões multi-tenant: cada utilizador tem uma
role por workspace (via `WorkspaceMember`), e as acções de escrita/gestão passam
a ser verificáveis por permissão e por workspace, sem hardcode nas views.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/rbac/__init__.py`, `apps/rbac/apps.py` | App `apps.rbac` (`RbacConfig`) |
| `apps/rbac/models.py` | `Permission`, `Role`, `RolePermission` (UUID, constraints) |
| `apps/rbac/seeds.py` | `seed_rbac()` idempotente + matriz role→permissions |
| `apps/rbac/services.py` | `get_user_workspace_role`, `user_has_permission`, `require_workspace_permission` |
| `apps/rbac/permissions.py` | `HasWorkspacePermission` (+ re-export de `IsWorkspaceMember`) |
| `apps/rbac/admin.py` | Admin de `Permission`, `Role` (inline de permissions), `RolePermission` |
| `apps/rbac/management/commands/seed_rbac.py` | Comando `seed_rbac` (idempotente) |
| `apps/rbac/migrations/0001_initial.py` | Migration inicial do RBAC |
| `apps/rbac/tests/conftest.py` | Fixtures (`rbac`, `workspace`, `add_member`, …) |
| `apps/rbac/tests/test_seed.py` | Seed cria tudo e é idempotente |
| `apps/rbac/tests/test_permissions.py` | Permissões por role (serviço) |
| `apps/rbac/tests/test_member_rbac_api.py` | RBAC nos endpoints de membros/workspace |
| `apps/workspaces/migrations/0002_workspacemember_role_fk.py` | Rename `role`→`role_key` + FK `role` + data migration |
| `docs/.../resultados/prompt_04_rbac_permissions.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `config/settings.py` | `"apps.rbac"` adicionado a `INSTALLED_APPS` |
| `apps/workspaces/models.py` | `role` agora é FK a `rbac.Role`; novo `role_key` (texto denormalizado) |
| `apps/workspaces/services.py` | `create_workspace` resolve e atribui a `Role` de owner (+ `role_key`) |
| `apps/workspaces/serializers.py` | `WorkspaceMemberSerializer`: `workspace`/`role` read-only, `role_key` editável |
| `apps/workspaces/views.py` | Membros gated por `members:invite`/`members:manage` (header); workspace `update/destroy` por `workspace:manage` (objecto) |
| `apps/workspaces/admin.py` | `WorkspaceMemberAdmin` mostra `role` + `role_key`; filtro por `role_key` |
| `apps/workspaces/tests/*` | Asserções `role` → `role_key` (modelo mudou) |

## 5. Migrations criadas

```text
apps/rbac/migrations/0001_initial.py
    + Permission, Role, RolePermission, M2M Role.permissions, 3 constraints
apps/workspaces/migrations/0002_workspacemember_role_fk.py
    RenameField role -> role_key
    AlterField role_key (CharField, blank, default "viewer")
    AddField role (FK -> rbac.Role, null)
    RunPython link_roles  (liga membros existentes à system role correspondente)
```

`makemigrations --check` confirma **No changes detected** (modelos e migrations
em sincronia).

## 6. Comandos executados

```powershell
python manage.py makemigrations rbac        # rbac/0001_initial
# (migration de workspaces 0002 escrita à mão; --check confirma sincronia)
python manage.py migrate                    # aplica rbac.0001 e workspaces.0002
python manage.py seed_rbac                  # 28 permissions, 7 roles (7 created)
python manage.py seed_rbac                  # idempotente: (0 created)
python manage.py check                      # 0 issues
python -m pytest -q                         # 47 passed
ruff check .                                # All checks passed!
python manage.py spectacular --file schema.yml   # 0 errors
```

## 7. Resultado das validações

| Validação | Resultado |
|---|---|
| `makemigrations` / `migrate` | OK — `rbac.0001`, `workspaces.0002` aplicadas |
| `seed_rbac` (idempotente) | OK — 1.ª execução 7 roles criadas; 2.ª e 3.ª: 0 criadas |
| `manage.py check` | OK — `System check identified no issues (0 silenced)` |
| `pytest` | **47 passed** (inclui 18 testes de RBAC) |
| `ruff check .` | OK — `All checks passed!` |
| OpenAPI (`spectacular`) | OK — 0 erros |

**Nota benigna:** persiste o `UserWarning` do WhiteNoise sobre `staticfiles/`
durante os testes (desaparece após `collectstatic`).

## 8. Decisões tomadas

- **`Role` com escopo duplo**: roles de sistema (`workspace` NULL, `is_system`)
  e roles por workspace. Unicidade garantida por dois `UniqueConstraint`
  condicionais (`unique_system_role_key`, `unique_workspace_role_key`).
- **Migração segura do `role`**: `RenameField role→role_key` (preserva valor) +
  `AddField role` (FK nullable) + `RunPython` que liga cada membro existente à
  system role correspondente (criando-a se faltar). `role_key` é mantido como
  denormalização/compatibilidade e fallback de resolução.
- **Matriz de permissões** (resumo): `owner` = todas; `admin` = todas excepto
  `workspace:manage` e `billing:manage`; `manager` = produto (view/create/update)
  + `members:invite` + `reports:generate` + `billing:view`; `editor` = produto
  (view/create/update, sem delete, sem membros/billing); `viewer` = apenas `*:view`;
  `billing_admin` = `billing:view`/`billing:manage` (+ `reports:view`); `api_user`
  = acesso programático mínimo.
- **Guards sem hardcode**: `HasWorkspacePermission` lê `required_permissions`
  (dict por acção) ou `get_required_permissions()`; resolve o workspace via
  `X-Workspace-ID` e verifica via `user_has_permission`.
- **Anti-escalada de privilégios**: membros são geridos no contexto do workspace
  do header (queryset restrito a esse workspace), e a mutação do próprio workspace
  é verificada contra o **objecto** (`require_workspace_permission(..., instance,
  "workspace:manage")`), nunca contra o header — evitando que um header de um
  workspace autorize acções noutro.
- **Seed reutilizável**: a lógica vive em `seeds.py` (usada pelo comando e pelos
  testes), com `update_or_create` + reconciliação de `RolePermission` para ser
  idempotente.

## 9. Pendências

- **Roles por workspace (customizadas)**: o modelo suporta-as, mas só são criadas
  roles de sistema; falta UI/endpoints para roles personalizadas.
- **`members:invite` vs `members:manage`**: implementado o essencial; fluxos de
  convite por email reais continuam por fazer (Pipeline futura).
- **Billing endpoints**: a permissão `billing:manage` é verificável, mas a app
  `billing` ainda não existe — a regra é validada a nível de serviço/teste.
- **Paginação/filtros padrão** (BCORE-403) continuam pendentes.
- **`collectstatic`** ainda não corrido.

## 10. Próximo passo recomendado

Avançar para **Pipeline 05 — Catálogo musical** (BCORE-501/502/503): criar
`apps.catalogue` com `Artist`, `Track` e `TrackPlatformLink`, todos
tenant-scoped (FK a `Workspace`) e protegidos pelos guards de RBAC já criados
(`artists:*`, `tracks:*`), reutilizando `HasWorkspacePermission` com
`required_permissions` por acção e o contexto `X-Workspace-ID`. Recomenda-se
introduzir nesta fase a paginação/filtros padrão (BCORE-403), já que os primeiros
list endpoints de produto vão precisar deles.
