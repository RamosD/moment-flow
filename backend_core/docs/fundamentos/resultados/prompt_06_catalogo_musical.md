# Relatório de execução — Prompt 06: Catálogo Musical

- **Pipeline / Backlog:** Pipeline 05 — Catálogo musical (BCORE-501, BCORE-502, BCORE-503)
- **Data:** 2026-06-21
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`

---

## 1. Prompt executado

Implementar `apps.catalogue` com `Artist`, `Track` e `TrackPlatformLink`,
tenant-scoped e reutilizando as bases abstractas do core; validação leve de URL
YouTube com extracção de `video_id`; constraints anti-cross-workspace; serializers,
filters e viewsets; permissões por role (`artists:*`, `tracks:*`); registo no
Admin; e testes de CRUD, permissões, isolamento, slug único por workspace e
extracção do YouTube.

## 2. Objectivo

Criar a base do catálogo musical (artistas, músicas e links de plataforma) que
suportará campanhas, smart links, content packs e relatórios. O Django guarda
links e metadata base; a validação técnica profunda e as métricas pertencem ao
FastAPI.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/catalogue/__init__.py`, `apps/catalogue/apps.py` | App `apps.catalogue` |
| `apps/catalogue/models.py` | `Artist`, `Track`, `TrackPlatformLink` (enums, constraints) |
| `apps/catalogue/utils.py` | `extract_youtube_video_id`, `is_youtube_url` |
| `apps/catalogue/services.py` | `generate_unique_slug` (por workspace) |
| `apps/catalogue/serializers.py` | Serializers + validação cross-workspace + YouTube |
| `apps/catalogue/filters.py` | `ArtistFilter`, `TrackFilter`, `TrackPlatformLinkFilter` |
| `apps/catalogue/views.py` | Viewsets (`WorkspaceScopedRBACMixin`) RBAC-gated |
| `apps/catalogue/urls.py` | Router DRF (`artists`, `tracks`, `track-platform-links`) |
| `apps/catalogue/admin.py` | Admin dos três modelos (filtros + pesquisa) |
| `apps/catalogue/migrations/0001_initial.py` | Migration inicial |
| `apps/catalogue/tests/conftest.py` | Fixtures (rbac, workspaces, membros, clients) |
| `apps/catalogue/tests/test_youtube_utils.py` | Unit tests da extracção YouTube |
| `apps/catalogue/tests/test_catalogue_api.py` | CRUD, slug, isolamento, YouTube |
| `apps/catalogue/tests/test_permissions.py` | RBAC nos endpoints |
| `docs/.../resultados/prompt_06_catalogo_musical.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `config/settings.py` | `"apps.catalogue"` adicionado a `INSTALLED_APPS` |
| `config/urls.py` | `include("apps.catalogue.urls")` montado em `api/v1/` |

## 5. Migrations criadas

```text
apps/catalogue/migrations/0001_initial.py
    + Artist  (UniqueConstraint workspace+slug, índice workspace+status)
    + Track   (FK artist, UniqueConstraint workspace+slug, índices)
    + TrackPlatformLink  (FK track, UniqueConstraint condicional
      workspace+platform+external_id quando external_id != "")
```

`makemigrations --check` confirma **No changes detected**. Nenhuma migration
anterior foi alterada.

## 6. Comandos executados

```powershell
python manage.py makemigrations            # catalogue/0001_initial
python manage.py migrate                   # aplica catalogue.0001
python manage.py check                     # 0 issues
python -m pytest -q                        # 78 passed
ruff check .                               # All checks passed!
python manage.py spectacular --file schema.yml   # 0 errors
```

## 7. Resultado das validações

| Validação | Resultado |
|---|---|
| `makemigrations` / `migrate` | OK — `catalogue.0001_initial` aplicada |
| `manage.py check` | OK — `System check identified no issues (0 silenced)` |
| `makemigrations --check` | OK — `No changes detected` |
| `pytest` | **78 passed** (+23 testes de catálogo) |
| `ruff check .` | OK — `All checks passed!` |
| OpenAPI (`spectacular`) | OK — 0 erros; inclui `/api/v1/artists/`, `/api/v1/tracks/`, `/api/v1/track-platform-links/` |

**Nota benigna:** persiste o `UserWarning` do WhiteNoise sobre `staticfiles/`.

## 8. Decisões tomadas

- **Reutilização das bases do core**: `Artist`/`Track` herdam
  `BaseModel + SoftDeleteModel + WorkspaceOwnedModel + CreatedUpdatedByModel`;
  `TrackPlatformLink` herda `BaseModel + WorkspaceOwnedModel` (sem soft delete —
  o ciclo de vida é dado pelo `status`, que inclui `removed`).
- **Imagens via `core.Asset`**: `Artist.image_asset` e `Track.cover_asset` são FKs
  a `core.Asset`, validando o contrato do prompt anterior.
- **Slug único por workspace**: gerado de `name`/`title` no `perform_create`,
  verificado contra `all_objects` (constraint cobre soft-deleted). Mesmo slug é
  permitido em workspaces diferentes.
- **Integridade cross-workspace**: validada nos serializers — `artist`,
  `cover_asset`, `image_asset` e `track` têm de pertencer ao workspace activo
  (`X-Workspace-ID`); caso contrário → 400.
- **YouTube leve**: `extract_youtube_video_id` reconhece `watch?v=`, `youtu.be/`,
  `/shorts/`, `/embed/`, `/v/`, `/live/` e valida o id de 11 caracteres. Para
  `platform=youtube`, o `external_id` é extraído automaticamente; URL não
  reconhecida → 400. **Sem** chamadas à YouTube API nem recolha de métricas.
- **Unicidade do link**: a `UniqueConstraint` condicional não é bem modelada pelo
  auto-validador do DRF (forçava `external_id` obrigatório antes da extracção),
  por isso foi desligada (`Meta.validators = []`) e substituída por uma
  verificação explícita em `validate()` (400 limpo) — a constraint da BD continua
  como rede de segurança.
- **Mixin reutilizável**: `WorkspaceScopedRBACMixin` concentra resolução do
  workspace + RBAC por acção (`required_permissions`) + queryset scoped, evitando
  hardcode de permissões nas views.

## 9. Pendências

- **Labels e rosters** (BCORE-504): não implementados (P1, fora deste prompt).
- **Validação/normalização de outras plataformas** (Spotify, Apple, etc.): apenas
  persistência; a validação profunda pertence ao FastAPI.
- **`last_validated_at` / `validation_error`**: campos presentes mas só serão
  preenchidos quando existir o serviço de validação técnica (FastAPI bridge).
- **`collectstatic`** continua por correr.

## 10. Próximo passo recomendado

Avançar para **Pipeline 06 — Campanhas** (BCORE-601/602/603): criar
`apps.campaigns` com `Campaign`, `CampaignTrack` e `CampaignGoal`, referenciando
`Artist`/`Track` do catálogo (validando o mesmo workspace), reutilizando as bases
do core, os guards de RBAC (`campaigns:*`) e a paginação/filtros padrão. A campanha
é a unidade central de valor e liga catálogo, content packs e smart links.
