# Relatório de execução — Prompt 09: Smart Links e Tracking

- **Pipeline / Backlog:** Pipeline 08 — Smart Links (BCORE-801, 802, 803)
- **Data:** 2026-06-21
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`

---

## 1. Prompt executado

Implementar `apps.links` com `SmartLink`, `SmartLinkDestination` e
`SmartLinkClick`; serializers, filters e viewsets; endpoint público de resolução
por slug que regista clique e redirecciona (ou devolve payload de destinos);
endpoint de estatísticas simples; associação opcional de `content_output` no
clique; permissões `links:*`; registo no Admin; e testes de criação, destinos,
tracking, link pausado, isolamento e estatísticas.

## 2. Objectivo

Ligar conteúdos, campanhas e medição de impacto. O Django é dono funcional de
smart links, destinos e tracking base. Privacidade preservada (sem IP em claro).

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/links/__init__.py`, `apps/links/apps.py` | App `apps.links` |
| `apps/links/models.py` | `SmartLink`, `SmartLinkDestination`, `SmartLinkClick` |
| `apps/links/utils.py` | Hashing de IP/UA (salted), parsing leve de device/browser |
| `apps/links/services.py` | `generate_unique_slug` (global) |
| `apps/links/serializers.py` | Serializers internos + serializers públicos |
| `apps/links/filters.py` | FilterSets de link, destino e clique |
| `apps/links/views.py` | Viewsets RBAC + acção `stats` + `PublicSmartLinkView` |
| `apps/links/urls.py` | Router DRF + `public_urlpatterns` (`/l/<slug>/`) |
| `apps/links/admin.py` | Admin (clicks read-only) |
| `apps/links/migrations/0001_initial.py` | Migration inicial |
| `apps/links/tests/conftest.py` | Fixtures (rbac, workspaces, campanhas, links) |
| `apps/links/tests/test_smart_links_api.py` | CRUD, destinos, isolamento, permissões, stats |
| `apps/links/tests/test_public_resolution.py` | Resolução pública, redirect, pausado, privacidade |
| `docs/.../resultados/prompt_09_smart_links_tracking.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `config/settings.py` | `"apps.links"` adicionado a `INSTALLED_APPS` |
| `config/urls.py` | Router em `api/v1/` + endpoint público `/l/<slug>/` na raiz |

## 5. Migrations criadas

```text
apps/links/migrations/0001_initial.py
    + SmartLink (slug unique global; índice workspace+status; soft delete)
    + SmartLinkDestination (FK smart_link; índice smart_link+is_active)
    + SmartLinkClick (FK smart_link/destination/content_output/campaign/track;
      utm_*, country, device_type, browser, ip_hash, user_agent_hash)
```

`makemigrations --check` confirma **No changes detected**; nenhuma migration
anterior foi alterada.

## 6. Comandos executados

```powershell
python manage.py makemigrations            # links/0001_initial
python manage.py migrate                   # aplica links.0001
python manage.py check                     # 0 issues
python -m pytest -q                        # 116 passed
ruff check .                               # All checks passed!
python manage.py spectacular --file schema.yml   # 0 errors
```

## 7. Resultado das validações

| Validação | Resultado |
|---|---|
| `makemigrations` / `migrate` | OK — `links.0001_initial` aplicada |
| `manage.py check` | OK — `System check identified no issues (0 silenced)` |
| `makemigrations --check` | OK — `No changes detected` |
| `pytest` | **116 passed** (+13 de links) |
| `ruff check .` | OK — `All checks passed!` |
| OpenAPI (`spectacular`) | OK — 0 erros (2 warnings benignos: colisão de nomes de enum `status` e o público `/l/`) |

**Nota benigna:** persiste o `UserWarning` do WhiteNoise sobre `staticfiles/`.

## 8. Decisões tomadas

- **Slug global**: `SmartLink.slug` é único globalmente (a URL pública `/l/<slug>/`
  não tem contexto de workspace); gerado de forma única via `generate_unique_slug`.
- **Endpoint público (`PublicSmartLinkView`, AllowAny)**: só resolve links
  `active` (caso contrário 404 — pausado/expirado nunca redirecciona). Com
  `?destination=<id>` ou `?platform=<key>` regista clique e devolve **302**; sem
  escolha explícita regista clique (destino nulo) e devolve **payload** dos
  destinos activos — nunca escolhe arbitrariamente.
- **Privacidade**: o IP nunca é guardado em claro — `ip_hash` e `user_agent_hash`
  são SHA-256 *salted* com a `SECRET_KEY`; `country` fica vazio (sem GeoIP);
  `device_type`/`browser` por heurística leve. Sem pixels, cookies ou retargeting.
- **`content_output` no clique**: lido de `?content_output=<uuid>` ou de
  `utm_content` quando for UUID, validado contra o workspace do link.
- **Estatísticas**: acção `stats` (`links:view`) devolve total de cliques, cliques
  por destino e cliques por dia (`TruncDate`) — analytics propositadamente básico.
- **RBAC**: `links:view/create/update/delete` por acção (reuso do
  `WorkspaceScopedRBACViewSet`); `SmartLinkClick` exposto apenas leitura
  (`links:view`), já que os cliques nascem no endpoint público.
- **Admin**: cliques são read-only (`has_add/change_permission=False`).

## 9. Pendências

- **Domínio customizado** e **página pública completa (frontend)**: fora do escopo
  por restrição — o backend devolve payload/redirect, sem UI.
- **GeoIP (`country`)**: por preencher (precisa de base GeoIP/serviço externo).
- **Analytics avançado** (cohorts, séries temporais ricas): fora do escopo.
- **`collectstatic`** continua por correr.

## 10. Próximo passo recomendado

Avançar para **Pipeline 09 — Billing, usage e créditos** (BCORE-901..905): criar
`apps.billing` com `Plan`/`PlanFeature`, `Subscription`, `UsageEvent`,
`CreditLedgerEntry` e *quota enforcement*, concretizando o hook `usage_event_id`
deixado em `content` (e podendo registar `usage` em eventos como
`smart_link_created`/`smart_link_clicked`). Em alternativa, **Pipeline 10 —
Reports/Media Kits/Notifications** se a prioridade for fechar o ciclo de produto
antes da monetização.
