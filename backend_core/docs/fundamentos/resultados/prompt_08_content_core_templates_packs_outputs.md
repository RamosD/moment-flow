# Relatório de execução — Prompt 08: Content Core (Templates, Packs, Outputs)

- **Pipeline / Backlog:** Pipeline 07 — Content core (BCORE-701, 702, 703, 704, 705)
- **Data:** 2026-06-21
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`

---

## 1. Prompt executado

Implementar `apps.content` com `Template`, `TemplateVersion`, `ContentPack`,
`ContentPackTemplate`, `ContentPackRequest` e `ContentOutput` **sem renderização
real**; serializers, filters e viewsets; permissões `content:view/generate/export`;
seed de templates e packs iniciais; serviço `create_content_pack_request` que cria
o pedido em `queued`; registo no Admin; e testes de catálogo, packs, request,
output placeholder, permissões e isolamento por workspace.

## 2. Objectivo

Criar a estrutura core que permite **pedir geração, acompanhar estados e guardar
outputs placeholder**. A renderização real (imagens, vídeo, PDF, carrosséis)
ficará a cargo do Content Renderer / FastAPI; aqui só existem entidades de produto
e o seam de orquestração.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/content/__init__.py`, `apps/content/apps.py` | App `apps.content` |
| `apps/content/models.py` | 6 modelos (catálogo global/workspace + lifecycle) |
| `apps/content/seeds.py` | `seed_content` idempotente (templates + packs) |
| `apps/content/services.py` | `create_content_pack_request` (valida + cria `queued`) |
| `apps/content/serializers.py` | Serializers + validação cross-workspace/global |
| `apps/content/filters.py` | FilterSets de template, pack, request, output |
| `apps/content/views.py` | Viewsets (catálogo read-only global+workspace; request/output) |
| `apps/content/urls.py` | Router DRF (6 recursos) |
| `apps/content/admin.py` | Admin dos 6 modelos (+ inlines de versão e pack-template) |
| `apps/content/management/commands/seed_content.py` | Comando `seed_content` |
| `apps/content/migrations/0001_initial.py` | Migration inicial |
| `apps/content/tests/conftest.py` | Fixtures (seed rbac+content, workspaces, campanhas) |
| `apps/content/tests/test_catalogue.py` | Listagem, global vs workspace |
| `apps/content/tests/test_requests_outputs.py` | Request `queued`, output, export, isolamento |
| `apps/content/tests/test_permissions.py` | RBAC (`content:*`) |
| `docs/.../resultados/prompt_08_content_core_templates_packs_outputs.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `config/settings.py` | `"apps.content"` adicionado a `INSTALLED_APPS` |
| `config/urls.py` | `include("apps.content.urls")` montado em `api/v1/` |

## 5. Migrations criadas

```text
apps/content/migrations/0001_initial.py
    + Template, TemplateVersion (unique template+version)
    + ContentPack, ContentPackTemplate (unique pack+template+output_type)
    + ContentPackRequest (FK campaign/pack; usage_event_id placeholder)
    + ContentOutput (FK campaign/template; visibility; usage_event_id placeholder)
```

`makemigrations --check` confirma **No changes detected**; nenhuma migration
anterior foi alterada.

## 6. Comandos executados

```powershell
python manage.py makemigrations            # content/0001_initial
python manage.py migrate                   # aplica content.0001
python manage.py seed_content              # 6 templates, 4 packs (idempotente)
python manage.py check                     # 0 issues
python -m pytest -q                        # 103 passed
ruff check .                               # All checks passed!
python manage.py spectacular --file schema.yml   # 0 errors
```

## 7. Resultado das validações

| Validação | Resultado |
|---|---|
| `makemigrations` / `migrate` | OK — `content.0001_initial` aplicada |
| `seed_content` (idempotente) | OK — 6 templates / 6 versões / 4 packs / 9 pack-templates estáveis em re-execução |
| `manage.py check` | OK — `System check identified no issues (0 silenced)` |
| `makemigrations --check` | OK — `No changes detected` |
| `pytest` | **103 passed** (+13 de content) |
| `ruff check .` | OK — `All checks passed!` |
| OpenAPI (`spectacular`) | OK — 0 erros; 13 paths de content (6 recursos + acção `export`) |

**Nota benigna:** persiste o `UserWarning` do WhiteNoise sobre `staticfiles/`.

## 8. Decisões tomadas

- **Catálogo global ou por workspace**: `Template` e `ContentPack` têm `workspace`
  nullable; os viewsets de catálogo são **read-only** e devolvem
  `workspace IS NULL OR workspace == activo` (`GlobalOrWorkspaceReadViewSet`).
  A gestão faz-se via Admin/seed (não há permissão de criação de templates no
  conjunto base — apenas `content:view/generate/export`).
- **Lifecycle tenant-owned**: `ContentPackRequest` e `ContentOutput` herdam
  `WorkspaceOwnedModel` e usam o `WorkspaceScopedRBACViewSet` partilhado.
- **Serviço de orquestração**: `create_content_pack_request` valida workspace,
  campanha (e track/artist), pack activo e global/do-workspace, e cria o pedido em
  `queued`. É o **seam** para o renderer externo (sem chamadas reais).
- **Output placeholder + export**: `ContentOutput` existe como entidade core
  (criável via API em `queued`); a acção `export` (`content:export`) devolve um
  payload placeholder — **nenhuma renderização** é feita.
- **Hook de billing**: como a app `billing` ainda não existe, `usage_event_id` é um
  `UUIDField` nullable (placeholder documentado) em `ContentPackRequest` e
  `ContentOutput`; será ligado ao usage event quando o billing existir.
- **Permissões**: `content:view` (catálogo + leitura de requests/outputs),
  `content:generate` (criar request/output), `content:export` (export). `viewer`
  vê o catálogo mas não gera; `editor`/`manager`/`owner` geram.
- **Integridade cross-workspace** validada nos serializers (campaign/track/artist/
  storage_asset do workspace activo; template/pack global ou do workspace).

## 9. Pendências

- **Renderer real (BCORE-705)**: implementado apenas o contrato/estado
  (`queued` + acção `export` placeholder + callback futuro). A renderização e o
  callback interno de actualização de estado ficam para o Content Renderer/FastAPI.
- **Billing**: `usage_event_id` é placeholder; falta ligar ao `UsageEvent`/créditos
  (Pipeline 09).
- **Criação/gestão de templates e packs por workspace via API**: não exposta
  (apenas Admin/seed) — exigiria um conjunto de permissões `content:manage`.
- **`collectstatic`** continua por correr.

## 10. Próximo passo recomendado

Avançar para **Pipeline 08 — Smart Links** (BCORE-801/802/803): criar `apps.links`
com `SmartLink`, `SmartLinkDestination` e `SmartLinkClick`, ligados à campanha
(mesmo workspace), reutilizando `WorkspaceScopedRBACViewSet` + permissões
`links:*`, com a página pública/endpoint de resolução e registo de cliques. Em
alternativa, **Pipeline 09 — Billing** (BCORE-901..905) para concretizar o hook
`usage_event_id` (usage events + créditos + quotas) que este prompt deixou
preparado.
