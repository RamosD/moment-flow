# Relatório de execução — Prompt 02: Custom User + Autenticação JWT

- **Pipeline / Backlog:** Pipeline 02 — Custom User e autenticação JWT (BCORE-101 + BCORE-102)
- **Data:** 2026-06-21
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`

---

## 1. Prompt executado

Implementar a app `accounts` com Custom User baseado em email (UUID como id,
`email` como `USERNAME_FIELD`, sem `username`), `UserManager` com `create_user`
e `create_superuser`, registo no Django Admin, serializers de perfil, endpoint
`/api/v1/auth/me/` (GET + actualização), e autenticação JWT (token obtain /
refresh) via SimpleJWT, integrada em `/api/v1/auth/`. Garantir schema OpenAPI,
testes e validações.

## 2. Objectivo

Estabelecer a fundação de identidade e autenticação do Backend Core, mantendo a
regra arquitectural **Django governa o produto; FastAPI calcula e executa**. Sem
workspaces, sem password reset (além de estrutura futura), sem `username`.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/accounts/__init__.py` | Pacote da app |
| `apps/accounts/apps.py` | `AccountsConfig` (`name = "apps.accounts"`) |
| `apps/accounts/managers.py` | `UserManager` com `create_user` / `create_superuser` |
| `apps/accounts/models.py` | Custom `User` (UUID PK, email-based) |
| `apps/accounts/admin.py` | `UserAdmin` + forms de criação/edição sem username |
| `apps/accounts/serializers.py` | `UserSerializer`, `UserProfileUpdateSerializer` |
| `apps/accounts/views.py` | `MeView` (`RetrieveUpdateAPIView`, `IsAuthenticated`) |
| `apps/accounts/urls.py` | Rotas `token/`, `token/refresh/`, `token/verify/`, `me/` |
| `apps/accounts/migrations/__init__.py` | Pacote de migrations |
| `apps/accounts/migrations/0001_initial.py` | Migration inicial do User |
| `apps/accounts/tests/__init__.py` | Pacote de testes |
| `apps/accounts/tests/test_user_manager.py` | Testes do `UserManager` e superuser |
| `apps/accounts/tests/test_auth_api.py` | Testes `/me/` (auth e anónimo) e JWT |
| `docs/backend_core/fundamentos/resultados/prompt_02_custom_user_auth_jwt.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `config/settings.py` | `AUTH_USER_MODEL = "accounts.User"`; adicionados `rest_framework_simplejwt`, `apps.accounts` a `INSTALLED_APPS` |
| `config/urls.py` | `include("apps.accounts.urls")` montado em `api/v1/auth/` |

## 5. Migrations criadas

```text
apps/accounts/migrations/0001_initial.py  (+ Create model User)
```

Aplicada juntamente com as migrations base (`contenttypes`, `auth`, `admin`,
`sessions`). A migration `accounts.0001_initial` corre **antes** de
`admin.0001_initial` (dependência do swappable user respeitada).

## 6. Comandos executados

```powershell
python manage.py makemigrations         # cria accounts/0001_initial
python manage.py migrate                # aplica todas as migrations
python manage.py check                  # 0 issues
python manage.py createsuperuser --email superadmin@example.com --noinput  # smoke
python -m pytest -q                     # 15 passed
ruff check .                            # All checks passed!
python manage.py spectacular --file schema.yml   # schema gerado, EXIT 0
```

## 7. Resultado das validações

| Validação | Resultado |
|---|---|
| `manage.py makemigrations` | OK — `accounts/0001_initial.py` |
| `manage.py migrate` | OK — todas as migrations aplicadas |
| `manage.py check` | OK — `System check identified no issues (0 silenced)` |
| `createsuperuser` (email, `--noinput`) | OK — `Superuser created successfully` |
| `pytest` | **15 passed** (3 core + 5 UserManager + 7 auth API) |
| `ruff check .` | OK — `All checks passed!` |
| OpenAPI (`spectacular`) | OK — inclui `/api/v1/auth/{me,token,token/refresh,token/verify}/` |

**Nota benigna:** durante o `pytest` surge `UserWarning: No directory at: ...\staticfiles\`
emitido pelo WhiteNoise porque `STATIC_ROOT` ainda não foi populado. É inofensivo
e desaparece após `python manage.py collectstatic`.

## 8. Decisões tomadas

- **`User` standalone** herdando de `AbstractBaseUser` + `PermissionsMixin` (em
  vez dos mixins de `apps.core`) para evitar conflitos de MRO e manter
  `date_joined`/`last_login` nativos. UUID como PK.
- **Sem `username`:** `USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = []`. Login e
  `createsuperuser` passam a usar email.
- **Admin sem username:** forms `UserCreationForm`/`UserChangeForm` personalizados
  para não depender do `username` do `UserAdmin` base.
- **`/me/` unificado:** `RetrieveUpdateAPIView` — GET devolve o perfil completo
  (`UserSerializer`); PUT/PATCH aceitam apenas campos básicos
  (`UserProfileUpdateSerializer`) e respondem sempre com a representação completa.
- **SimpleJWT padrão:** `TokenObtainPairView` usa o `USERNAME_FIELD`, logo o login
  é feito com `email` + `password`. Adicionado também `token/verify/`.
- **`rest_framework_simplejwt` em `INSTALLED_APPS`** conforme esperado no backlog
  (BCORE-001); não introduz migrations (o blacklist não foi activado).
- **Bug corrigido:** o campo `timezone` sombreava o módulo `django.utils.timezone`
  no corpo da classe; resolvido importando `now` directamente
  (`from django.utils.timezone import now`).
- **Superuser de verificação:** criado `superadmin@example.com` no `db.sqlite3`
  local apenas para validar o critério de aceitação. É descartável — pode ser
  removido/alterado (é um DB de desenvolvimento, fora de controlo de versões).

## 9. Pendências

- **BCORE-103** (password reset / verificação de email): não implementado nesta
  fase, conforme restrições. `email_verified_at` já existe no modelo para suportar
  o fluxo futuro.
- **Logout / blacklist de tokens:** não activado (exigiria
  `rest_framework_simplejwt.token_blacklist` + migrations).
- **Workspaces / multi-tenancy:** fora de escopo deste prompt (Pipeline 03).
- **`collectstatic`** ainda não corrido (apenas relevante para produção/WhiteNoise).

## 10. Próximo passo recomendado

Avançar para **Pipeline 03 — Workspaces e multi-tenancy** (BCORE-201/202/203):
criar `apps.workspaces` com o modelo `Workspace` (UUID, slug único, status),
`WorkspaceMember`, e o mecanismo de workspace activo via header `X-Workspace-ID`,
com testes de isolamento cross-workspace. Em paralelo, consolidar os base models
de `apps.core` (BCORE-401: `SoftDeleteModel`, `WorkspaceOwnedModel`) que as apps
de produto vão reutilizar.
