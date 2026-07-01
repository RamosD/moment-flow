# Relatório de execução — Prompt 05: Core, Assets e Padrões transversais

- **Pipeline / Backlog:** BCORE-401 (Base Models), BCORE-402 (Assets), BCORE-403 (Paginação/filtros)
- **Data:** 2026-06-21
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`

---

## 1. Prompt executado

Criar utilitários transversais em `apps.core`: modelos abstractos reutilizáveis
(`UUIDModel`, `TimeStampedModel`, `SoftDeleteModel`, `WorkspaceOwnedModel`,
`CreatedUpdatedByModel`), o modelo concreto `Asset` (referência genérica a ficheiro
por workspace), serializer/viewset com isolamento por workspace e
`IsWorkspaceMember`, paginação padrão no core configurada no DRF, registo do
`Asset` no Admin e testes de isolamento.

## 2. Objectivo

Consolidar a fundação técnica multi-tenant: entidades de cliente passam a poder
reutilizar bases abstractas (UUID, timestamps, soft delete, ownership por
workspace, autoria), e os ficheiros (logos, capas, outputs, PDFs) passam a ser
referenciados por uma entidade `Asset` — sem implementar storage real.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/core/pagination.py` | `StandardResultsSetPagination` (page_size 25, máx 100) |
| `apps/core/serializers.py` | `AssetSerializer` (workspace/created_by server-managed) |
| `apps/core/views.py` | `AssetViewSet` (scoped por X-Workspace-ID, soft delete) |
| `apps/core/urls.py` | Router DRF (`assets`) |
| `apps/core/admin.py` | `AssetAdmin` (inclui soft-deleted via `all_objects`) |
| `apps/core/migrations/0001_initial.py` | Migration inicial (modelo `Asset`) |
| `apps/core/tests/conftest.py` | Fixtures (`user_a/b`, `workspace_a/b`, `client_a/b`) |
| `apps/core/tests/test_assets.py` | Criação, isolamento por workspace, soft delete, filtro |
| `docs/.../resultados/prompt_05_core_assets_padroes.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `apps/core/models.py` | Novos `WorkspaceOwnedModel`, `CreatedUpdatedByModel` e modelo concreto `Asset` |
| `config/settings.py` | `REST_FRAMEWORK`: `DEFAULT_PAGINATION_CLASS` + `PAGE_SIZE = 25` |
| `config/urls.py` | `include("apps.core.urls")` montado em `api/v1/` |

## 5. Migrations criadas

```text
apps/core/migrations/0001_initial.py
    + Create model Asset  (UUID PK, timestamps, deleted_at, workspace FK,
      created_by/updated_by FKs, asset_type, storage_*, file_*, dimensões,
      checksum, metadata, índice (workspace, asset_type))
```

`makemigrations --check` confirma **No changes detected**. Nenhuma migration
anterior (accounts/workspaces/rbac) foi alterada.

## 6. Comandos executados

```powershell
python manage.py makemigrations            # core/0001_initial (Asset)
python manage.py migrate                   # aplica core.0001
python manage.py check                     # 0 issues
python -m pytest -q                        # 55 passed
ruff check .                               # All checks passed!
python manage.py spectacular --file schema.yml   # 0 errors
```

## 7. Resultado das validações

| Validação | Resultado |
|---|---|
| `makemigrations` / `migrate` | OK — `core.0001_initial` aplicada |
| `manage.py check` | OK — `System check identified no issues (0 silenced)` |
| `makemigrations --check` | OK — `No changes detected` |
| `pytest` | **55 passed** (+8 testes de Asset face ao prompt anterior) |
| `ruff check .` | OK — `All checks passed!` |
| OpenAPI (`spectacular`) | OK — 0 erros; inclui `/api/v1/assets/` e `/api/v1/assets/{id}/` |

**Nota benigna:** mantém-se o `UserWarning` do WhiteNoise sobre `staticfiles/`.

## 8. Decisões tomadas

- **Bases abstractas reutilizáveis**: além das já existentes (`UUIDModel`,
  `TimeStampedModel`, `SoftDeleteModel`, `BaseModel`), foram adicionadas
  `WorkspaceOwnedModel` (FK `workspace` obrigatória) e `CreatedUpdatedByModel`
  (`created_by`/`updated_by`). Para evitar colisões de reverse accessors em
  modelos abstractos, os `related_name` usam os placeholders
  `%(app_label)s_%(class)s_*`.
- **`Asset` compõe todas as bases**: `Asset(BaseModel, SoftDeleteModel,
  WorkspaceOwnedModel, CreatedUpdatedByModel)` — prova de reutilização. Mantém
  `base_manager_name = "all_objects"` (consistente com a estratégia de soft
  delete) e um índice `(workspace, asset_type)`.
- **Isolamento por workspace**: o `AssetViewSet` resolve o workspace activo via
  `X-Workspace-ID` (`IsWorkspaceMember`), filtra o queryset por esse workspace e
  define `workspace`/`created_by` no servidor. Aceder a asset de outro workspace
  resulta em 404 (fora do queryset) ou 403 (sem membership).
- **Paginação padrão** (`StandardResultsSetPagination`) aplicada globalmente; os
  testes de listagem existentes já eram robustos ao formato paginado.
- **Soft delete na API**: `DELETE` chama `instance.soft_delete()` (204); o asset
  deixa de aparecer no manager por defeito mas permanece em `all_objects` (e no
  Admin).
- **Sem refactor arriscado**: as entidades existentes (`Workspace`,
  `WorkspaceMember`, RBAC) **não** foram migradas para as novas bases abstractas,
  para não alterar `related_name`/migrations já estáveis. Ficam como pendência
  controlada (ver §9).
- **Utilitários de resposta/erro**: deliberadamente **não** adicionados — um
  envelope global de erros alteraria contratos de resposta já testados; o ganho
  não justificava o risco nesta fase.

## 9. Pendências

- **RBAC de assets**: não existe um conjunto `assets:*` no catálogo base, por isso
  qualquer membro activo do workspace pode gerir assets desse workspace
  (isolamento garantido; granularidade por role fica para quando o domínio o
  exigir).
- **Storage real (S3/R2)**: não implementado, por restrição — `Asset` é uma
  entidade de metadados/contrato (`storage_provider` default `local`).
- **Refactor das entidades existentes** para `WorkspaceOwnedModel`/
  `CreatedUpdatedByModel`: adiado para evitar migrations de risco; as novas apps
  de produto devem nascer já sobre estas bases.
- **Envelope de respostas/erros consistente**: não adicionado (opcional).
- **`collectstatic`** continua por correr (apenas relevante em produção).

## 10. Próximo passo recomendado

Avançar para **Pipeline 05 — Catálogo musical** (BCORE-501/502/503): criar
`apps.catalogue` com `Artist`, `Track` e `TrackPlatformLink`, nascendo já sobre
`BaseModel + SoftDeleteModel + WorkspaceOwnedModel + CreatedUpdatedByModel`,
protegidos pelos guards de RBAC (`artists:*`, `tracks:*`) e com paginação/filtros
padrão. As imagens (foto de artista, capa) devem referenciar `core.Asset` via FK
(`image_asset`, `cover_asset`), validando o contrato criado neste prompt.
