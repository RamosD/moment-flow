# Relatório de execução — Prompt 07: Campanhas e Objectivos

- **Pipeline / Backlog:** Pipeline 06 — Campanhas (BCORE-601, BCORE-602, BCORE-603)
- **Data:** 2026-06-21
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`

---

## 1. Prompt executado

Implementar `apps.campaigns` com `Campaign`, `CampaignTrack` e `CampaignGoal`,
tenant-scoped e reutilizando as bases do core; validação de workspace (campanha
não referencia artista/música de outro workspace); impedir música duplicada na
campanha; serializers, filters e viewsets; permissões `campaigns:*`; registo no
Admin; e testes de CRUD, permissões, isolamento, constraints e filtros.

## 2. Objectivo

Criar a unidade central de valor do produto — a campanha — ligando catálogo
(artista/música) a objectivos mensuráveis e a múltiplas músicas, preparando o
fluxo campanha → dados → moments → insights → content packs → smart links →
relatórios. A lógica analítica pesada fica fora deste backlog.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/rbac/viewsets.py` | `WorkspaceScopedRBACViewSet` (base reutilizável tenant+RBAC) |
| `apps/campaigns/__init__.py`, `apps/campaigns/apps.py` | App `apps.campaigns` |
| `apps/campaigns/models.py` | `Campaign`, `CampaignTrack`, `CampaignGoal` |
| `apps/campaigns/services.py` | `generate_unique_slug` (por workspace) |
| `apps/campaigns/serializers.py` | Serializers + validação cross-workspace |
| `apps/campaigns/filters.py` | `CampaignFilter`, `CampaignTrackFilter`, `CampaignGoalFilter` |
| `apps/campaigns/views.py` | Viewsets RBAC-gated (`campaigns:*`) |
| `apps/campaigns/urls.py` | Router DRF (campaigns, campaign-tracks, campaign-goals) |
| `apps/campaigns/admin.py` | Admin dos três modelos (filtros + pesquisa) |
| `apps/campaigns/migrations/0001_initial.py` | Migration inicial |
| `apps/campaigns/tests/conftest.py` | Fixtures (rbac, workspaces, artistas/tracks, membros) |
| `apps/campaigns/tests/test_campaigns_api.py` | CRUD, isolamento, constraints, filtros |
| `apps/campaigns/tests/test_permissions.py` | RBAC nos endpoints |
| `docs/.../resultados/prompt_07_campanhas_objectivos.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `config/settings.py` | `"apps.campaigns"` adicionado a `INSTALLED_APPS` |
| `config/urls.py` | `include("apps.campaigns.urls")` montado em `api/v1/` |

## 5. Migrations criadas

```text
apps/campaigns/migrations/0001_initial.py
    + Campaign       (FK artist [CASCADE], track [SET_NULL, nullable];
                      UniqueConstraint workspace+slug; índices workspace+status, artist)
    + CampaignTrack  (FK campaign, track; UniqueConstraint campaign+track)
    + CampaignGoal   (FK campaign; target/current Decimal; índices)
```

`makemigrations --check` confirma **No changes detected**. Nenhuma migration
anterior foi alterada.

## 6. Comandos executados

```powershell
python manage.py makemigrations            # campaigns/0001_initial
python manage.py migrate                   # aplica campaigns.0001
python manage.py check                     # 0 issues
python -m pytest -q                        # 90 passed
ruff check .                               # All checks passed!
python manage.py spectacular --file schema.yml   # 0 errors
```

## 7. Resultado das validações

| Validação | Resultado |
|---|---|
| `makemigrations` / `migrate` | OK — `campaigns.0001_initial` aplicada |
| `manage.py check` | OK — `System check identified no issues (0 silenced)` |
| `makemigrations --check` | OK — `No changes detected` |
| `pytest` | **90 passed** (+12 testes de campanhas) |
| `ruff check .` | OK — `All checks passed!` |
| OpenAPI (`spectacular`) | OK — 0 erros; inclui `/api/v1/campaigns/`, `/api/v1/campaign-tracks/`, `/api/v1/campaign-goals/` |

**Nota benigna:** persiste o `UserWarning` do WhiteNoise sobre `staticfiles/`.

## 8. Decisões tomadas

- **Base reutilizável promovida**: o padrão tenant-scoped + RBAC foi extraído para
  `apps/rbac/viewsets.py` (`WorkspaceScopedRBACViewSet`) e usado pelos três
  viewsets de campanhas. (A app `catalogue` mantém a sua própria cópia local para
  não introduzir refactor de risco; pode adoptar a base no futuro.)
- **Reuso das bases do core**: `Campaign` herda
  `BaseModel + SoftDeleteModel + WorkspaceOwnedModel + CreatedUpdatedByModel`;
  `CampaignTrack` e `CampaignGoal` herdam `BaseModel + WorkspaceOwnedModel` (sem
  soft delete — são sub-recursos geridos pelo ciclo de vida da campanha / status).
- **Integridade cross-workspace**: nos serializers, `artist` e `track` (Campaign),
  `campaign`/`track` (CampaignTrack) e `campaign` (CampaignGoal) têm de pertencer
  ao workspace activo (`X-Workspace-ID`); caso contrário → 400.
- **Sem música duplicada**: `UniqueConstraint(campaign, track)` no modelo; como
  ambos os campos são escrevíveis no serializer, o auto-validador do DRF devolve
  um 400 limpo em duplicados.
- **Permissões**: `campaigns:view/create/update/delete` aplicadas por acção (via
  `required_permissions`) aos três viewsets — sub-recursos (tracks/goals) seguem
  o mesmo conjunto. `viewer` lê mas não escreve; `editor` cria mas não apaga;
  `owner`/`admin` apagam (soft delete da campanha).
- **`target_value`/`current_value`** como `DecimalField` para acomodar metas
  numéricas grandes e métricas fraccionárias (ex.: engagement).

## 9. Pendências

- **Campaign Channels e Timeline** (BCORE-604, P1): não implementados — mantidos
  como pendência conforme a restrição (evitar complicar o escopo).
- **Campaign War Room / analítica** (metrics, moments, insights): fora deste
  backlog (pertencem ao FastAPI).
- **Smart links e content packs**: dependem da campanha mas ficam para as próximas
  pipelines (07 e 08).
- **Consolidação do `WorkspaceScopedRBACViewSet`** no `catalogue`: adiada para
  evitar refactor; o `catalogue` continua com o seu mixin local.
- **`collectstatic`** continua por correr.

## 10. Próximo passo recomendado

Avançar para **Pipeline 07 — Content core** (BCORE-701..705): criar `apps.content`
com `Template`/`TemplateVersion`, `ContentPack`/`ContentPackTemplate`,
`ContentPackRequest` e `ContentOutput`, ligando à campanha (mesmo workspace) e
reutilizando `WorkspaceScopedRBACViewSet` + permissões `content:*`, com o bridge
para o renderer (FastAPI) apenas como contrato/estado (`queued`/callback), sem
renderização real.
