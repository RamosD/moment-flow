# Relatório de execução — Prompt 13: API Routing, OpenAPI e Admin

- **Pipeline / Backlog:** Pipeline 12 (parcial) — BCORE-1401 (API routing), BCORE-1501 (Django Admin), DoD "OpenAPI não quebra"
- **Data:** 2026-06-21
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`

---

## 1. Prompt executado

Rever e consolidar o routing da API v1, a documentação OpenAPI e a configuração do
Django Admin para todas as apps implementadas. Garantir endpoints versionados sob
`/api/v1/`, rotas/routers para todos os domínios, ViewSets com serializer +
queryset filtrado por workspace + permissões + filtros, Admin completo (incl.
`AuditEvent` read-only e campos críticos de billing read-only), e um schema
OpenAPI que gera sem erros nem warnings.

## 2. Objectivo

Após implementar as apps principais, expor endpoints consistentes em `/api/v1/` e
documentação OpenAPI fiável, com o Django Admin como backoffice inicial. Esta foi
uma passagem de **revisão/consolidação** — sem novas features de domínio, sem
alterar models, corrigindo apenas inconsistências simples detectadas.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `docs/.../resultados/prompt_13_api_routing_openapi_admin.md` | Este relatório |

(Nenhum ficheiro de código novo — tarefa de consolidação.)

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `apps/links/serializers.py` | `@extend_schema_field(...)` em `PublicSmartLinkSerializer.get_destinations` — tipa o campo `destinations` no schema (era "unable to resolve type hint") |
| `config/settings.py` | `SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"]` para 3 enums sem nome estável (status de content, status de external job, platform de smart link) |

## 5. Migrations criadas

Nenhuma. Não houve alterações a models (restrição "não alterar models sem
necessidade real"). `makemigrations --check --dry-run` → **No changes detected**.

## 6. Comandos executados

```powershell
python manage.py check                              # 0 issues
python manage.py spectacular --file schema.yml       # 0 warnings, 0 errors
python manage.py makemigrations --check --dry-run     # No changes detected
python -m pytest -q                                 # 198 passed
ruff check .                                        # All checks passed!
```

## 7. Resultado das validações

| Validação | Resultado |
|---|---|
| `manage.py check` | OK — `System check identified no issues (0 silenced)` |
| OpenAPI (`spectacular`) | OK — **0 warnings, 0 errors** (eram 3 warnings antes) |
| `makemigrations --check` | OK — `No changes detected` |
| `pytest` | **198 passed** — 0 regressões |
| `ruff check .` | OK — `All checks passed!` |

**Nota benigna:** persiste apenas o `UserWarning` do WhiteNoise sobre `staticfiles/`.

## 8. Revisão efectuada (sem alterações necessárias)

### 8.1 Routing `/api/v1/` — completo e versionado

Todos os domínios pedidos têm rota/router e estão sob `/api/v1/`:

| Domínio | Rota |
|---|---|
| auth | `/api/v1/auth/token/`, `/token/refresh/`, `/token/verify/`, `/me/` |
| workspaces / members | `/api/v1/workspaces/`, `/workspace-members/` |
| artists / tracks / platform links | `/api/v1/artists/`, `/tracks/`, `/track-platform-links/` |
| campaigns / tracks / goals | `/api/v1/campaigns/`, `/campaign-tracks/`, `/campaign-goals/` |
| templates / packs / requests / outputs | `/api/v1/templates/`, `/template-versions/`, `/content-packs/`, `/content-pack-templates/`, `/content-pack-requests/`, `/content-outputs/` |
| smart links | `/api/v1/smart-links/`, `/smart-link-destinations/`, `/smart-link-clicks/` (+ público `/l/<slug>/`) |
| reports / media kits | `/api/v1/reports/`, `/report-sections/`, `/media-kits/`, `/media-kit-items/` |
| billing | `/api/v1/plans/`, `/billing/subscription/`, `/billing/usage/`, `/billing/credits/`, `/billing/webhooks/stripe/` |
| notifications | `/api/v1/notifications/` (+ acções `read`, `read-all`) |
| integrations bridge (interno) | `/api/v1/internal/jobs/callback/` |
| assets (core) | `/api/v1/assets/` |
| schema / docs | `/api/v1/schema/`, `/api/v1/docs/` (Swagger), `/api/v1/redoc/` |

### 8.2 ViewSets — serializer, scoping, permissões e filtros

Verificado que cada ViewSet de tenant usa o scoping por workspace
(`WorkspaceScopedRBACViewSet` / mixins equivalentes), `permission_classes` com
`IsAuthenticated` + (`HasWorkspacePermission` | `IsWorkspaceMember`),
`serializer_class`, e `filterset_*` / `search_fields` / `ordering_fields`
adequados. Casos especiais confirmados: `PlanViewSet` (catálogo público
read-only, sem workspace), endpoints de billing por `billing:view`,
`NotificationViewSet` por membership, e `ExternalJobCallbackView` apenas por
`X-Internal-Token` (interno, não público).

### 8.3 Admin — completo e seguro

Todas as entidades principais estão registadas com `list_display`,
`search_fields`, `list_filter`, `readonly_fields` e `ordering`. Read-only
garantido onde é crítico:

- **`AuditEvent`** — totalmente read-only (`has_add/change/delete = False`).
- **Billing append-only** — `UsageEvent`, `CreditLedgerEntry`,
  `BillingWebhookEvent` totalmente read-only; `Plan`/`PlanFeature`/`Subscription`
  editáveis com `id`/timestamps read-only.
- **`SmartLinkClick`** — read-only (nasce no endpoint público).
- Soft-delete: admins de entidades soft-deletáveis mostram registos apagados
  (`all_objects`) com `deleted_at` read-only.

## 9. Problemas corrigidos

1. **`destinations` sem tipo no schema** (`PublicSmartLinkSerializer`): o
   `SerializerMethodField` resolvia para `string`. Anotado com
   `@extend_schema_field(PublicSmartLinkDestinationSerializer(many=True))` → agora
   tipado como array de objectos de destino.
2. **Nomes de enum instáveis no schema** (3 colisões `…Fa2Enum` / `…8e3Enum` /
   `…5e6Enum`): fixados via `ENUM_NAME_OVERRIDES` com nomes estáveis e
   significativos —
   `ContentCatalogueStatusEnum` (status partilhado por Template/TemplateVersion/
   ContentPack), `ExternalJobStatusEnum` (status do `ExternalJobReference`,
   exposto pelo serializer de callback) e `SmartLinkPlatformEnum`
   (platform de `SmartLinkDestination`). Correspondência por conjunto de valores;
   uma futura mudança de model degrada para o nome automático (nunca um erro).

Resultado: schema OpenAPI passou de **3 warnings → 0 warnings / 0 errors**.

## 10. Segredos / tokens no schema

Confirmado que **nenhum segredo é exposto**: `STRIPE_WEBHOOK_SECRET`,
`STRIPE_API_KEY` e `INTERNAL_API_TOKEN` vivem apenas em settings/ambiente; nenhum
serializer ou model os expõe. No schema, `X-Internal-Token` aparece apenas como
**nome** de header (parâmetro necessário), e `STRIPE_WEBHOOK_SECRET` apenas como
referência textual num docstring — nunca valores.

## 11. Pendências

- **`provider_subscription_id` (Subscription) editável no Admin:** mantido
  editável de propósito (subscrições manuais precisam de o definir); os registos
  financeiros verdadeiramente imutáveis (ledger/usage/webhooks) já são read-only.
- **`spectacular --validate` em CI:** o schema gera limpo; falta automatizar a
  geração/validação do `schema.yml` num passo de CI e versioná-lo.
- **Namespacing de routers:** os `app_name` existem mas as rotas convivem sob o
  mesmo prefixo `api/v1/` por basenames únicos — suficiente; um router central
  agrupado é opcional.
- **Warning do WhiteNoise (`staticfiles/`):** resolve-se com `collectstatic`
  (fora do escopo desta passagem).

## 12. Próximo passo recomendado

Avançar para **Pipeline 12 — Testes, hardening e documentação** (BCORE-1601+):
`factory-boy` factories, testes transversais de multi-tenancy e RBAC por role,
`coverage`, e um passo de CI que corre `check` + `spectacular` + `pytest` + `ruff`
e versiona o `schema.yml` gerado. Em paralelo, fechar o ciclo de orquestração
billing → integrations_bridge → reports/notifications (gerar `ExternalJobReference`
nos fluxos de geração e emitir notificações no callback).
