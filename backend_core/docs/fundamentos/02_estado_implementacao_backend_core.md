# Estado de Implementação — Backend Core Django/DRF

- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`
- **Data:** 2026-06-22
- **Backlog de referência:** [`01_backlog_backend_core_django.md`](01_backlog_backend_core_django.md)
- **Stack:** Django 6.0.6 · DRF 3.17 · SimpleJWT · drf-spectacular · Python 3.13.2

Este documento descreve o estado consolidado do backend core no momento do
hardening final (antes de avançar para frontend, FastAPI Intelligence Engine ou
Content Renderer).

---

## 1. Funcionalidades implementadas

O MVP técnico do backend core (secção 25 do backlog) está coberto:

- **Identidade & auth:** `User` customizado por email, `UserManager`, JWT
  (obtain / refresh / verify), endpoint `/me` (leitura e actualização de perfil).
- **Multi-tenancy:** `Workspace` + `WorkspaceMember`; workspace activo resolvido
  pelo header `X-Workspace-ID`; querysets de entidades de cliente filtram por
  `workspace`; isolamento testado A↔B.
- **RBAC:** `Role`, `Permission`, `RolePermission`; roles de sistema e por
  workspace; guards DRF (`IsWorkspaceMember`, `HasWorkspacePermission`) com
  permissões declaradas por acção; seed `seed_rbac`.
- **Core/base:** modelos abstractos `UUIDModel`, `TimeStampedModel`,
  `SoftDeleteModel` (manager que esconde soft-deleted), `WorkspaceOwnedModel`,
  `CreatedUpdatedByModel`; `Asset` genérico; paginação padrão (page_size 25).
- **Catálogo:** `Artist`, `Track`, `TrackPlatformLink` (validação leve de URL/ID
  YouTube; unicidade de `platform + external_id` por workspace).
- **Campanhas:** `Campaign`, `CampaignTrack`, `CampaignGoal` com enums de tipo e
  estado e validação de coerência de workspace.
- **Content core:** `Template`/`TemplateVersion`, `ContentPack`/
  `ContentPackTemplate` (catálogo global ou por workspace, read-only),
  `ContentPackRequest`, `ContentOutput`; service `create_content_pack_request`
  cria pedido em `queued` (placeholder, sem renderização); seed `seed_content`.
- **Smart links:** `SmartLink`, `SmartLinkDestination`, `SmartLinkClick`; página
  pública `/l/<slug>/` que regista clique e redirecciona (apenas links `active`);
  acção `stats`.
- **Billing:** `Plan`/`PlanFeature`, `Subscription`, `UsageEvent` (idempotente),
  `CreditLedgerEntry` (ledger append-only com `balance_after`), `BillingWebhookEvent`;
  services de subscription/feature/limite, grant/reserve/consume/release/refund de
  créditos, enforcement de quotas; skeleton de webhook Stripe com verificação de
  assinatura e deduplicação; seed `seed_billing`.
- **Reports & media kits:** `Report`/`ReportSection`, `MediaKit`/`MediaKitItem`
  como entidades core (sem renderer avançado).
- **Notificações:** `Notification` in-app com acção *mark as read*.
- **Auditoria:** `AuditEvent` imutável + service; admin read-only.
- **Integrations bridge:** `ExternalJobReference` + callback interno
  `internal/jobs/callback/` autenticado por `X-Internal-Token` (idempotente, com
  guarda de estados terminais).
- **API & OpenAPI:** rotas versionadas em `/api/v1/`, Swagger e Redoc; schema
  gerado sem erros.
- **Admin:** entidades principais registadas com filtros/search; audit read-only.
- **Qualidade:** factories `factory-boy`, suite de regressão transversal.

---

## 2. Endpoints principais

| Prefixo | Recurso | Auth |
|---|---|---|
| `/api/v1/auth/token/`, `token/refresh/`, `token/verify/`, `me/` | JWT + perfil | JWT (excepto obtain) |
| `/api/v1/workspaces/`, `/workspace-members/` | Workspaces e membros | JWT (+ membership) |
| `/api/v1/assets/` | Assets | JWT + `X-Workspace-ID` |
| `/api/v1/artists/`, `/tracks/`, `/track-platform-links/` | Catálogo | JWT + workspace + RBAC |
| `/api/v1/campaigns/`, `/campaign-tracks/`, `/campaign-goals/` | Campanhas | JWT + workspace + RBAC |
| `/api/v1/templates/`, `/template-versions/`, `/content-packs/`, `/content-pack-templates/`, `/content-pack-requests/`, `/content-outputs/` | Content | JWT + workspace + RBAC |
| `/api/v1/smart-links/` (+`/stats/`), `/smart-link-destinations/`, `/smart-link-clicks/` | Smart links | JWT + workspace + RBAC |
| `/l/<slug>/` | Resolução pública + tracking | Pública (sem auth) |
| `/api/v1/plans/`, `/billing/subscription/`, `/billing/usage/`, `/billing/credits/` | Billing | JWT + workspace |
| `/api/v1/billing/webhooks/stripe/` | Webhook Stripe | Assinatura Stripe |
| `/api/v1/reports/`, `/report-sections/`, `/media-kits/`, `/media-kit-items/` | Reports/Media kits | JWT + workspace + RBAC |
| `/api/v1/notifications/` | Notificações | JWT + workspace |
| `/internal/jobs/callback/` | Callback de job externo | `X-Internal-Token` |
| `/api/v1/schema/`, `/docs/`, `/redoc/` | OpenAPI | — |

---

## 3. Apps criadas

Fundação: `core`, `accounts`, `workspaces`, `rbac`, `audit`.
Produto: `catalogue`, `campaigns`, `content`, `links`, `reports`, `notifications`.
Comercial: `billing`.
Integração: `integrations_bridge`.

Todas registadas em `INSTALLED_APPS`; todos os models principais usam UUID PK +
timestamps; entidades tenant-aware herdam `WorkspaceOwnedModel`. `Plan`,
`PlanFeature`, `BillingWebhookEvent` são intencionalmente globais; `Role`,
`Template`, `ContentPack` têm `workspace` nullable (global ou por workspace).

---

## 4. Validações executadas (hardening)

| Validação | Comando | Resultado |
|---|---|---|
| System check | `python manage.py check` | ✅ 0 issues |
| Migrations em falta | `python manage.py makemigrations --check --dry-run` | ✅ No changes detected |
| Schema OpenAPI | `python manage.py spectacular --file schema.yml` | ✅ Gerado sem erros |
| Testes | `pytest` | ✅ **235 passed** (160 warnings benignos) |
| Lint | `ruff check .` | ✅ All checks passed |

Verificações manuais adicionais:

- Entidades tenant-aware filtram por `workspace` nos querysets (mixins
  `WorkspaceScopedRBACMixin` / `WorkspaceScopedRBACViewSet` /
  `GlobalOrWorkspaceReadViewSet`). ✅
- Endpoints sensíveis exigem `IsAuthenticated` + RBAC; público apenas em
  `/l/<slug>/`; interno apenas via `X-Internal-Token` (comparação constante). ✅
- Usage events e audit events ligados aos fluxos críticos (criação de
  artist/track/campaign/smart_link/content_pack, membros, créditos, plano). ✅
- Webhook Stripe e callback interno são idempotentes. ✅

---

## 5. Pendências

Itens **P1/futuros** do backlog, deliberadamente fora deste hardening:

- **Accounts:** password reset / verificação de email (BCORE-103) — estrutura
  preparada, fluxo de envio de email não implementado.
- **Workspaces:** `WorkspaceSettings` / `WorkspaceBranding` (BCORE-204) — ainda não
  implementados.
- **Catálogo:** `Label` / `LabelArtist` (BCORE-504, P1).
- **Campanhas:** `CampaignChannel` / `CampaignTimelineItem` (BCORE-604, P1).
- **Content:** callback/bridge de geração para o renderer real (BCORE-705) —
  mock local em `queued`; rendering real é do Content Renderer.
- **Billing:** Stripe checkout real e mapeamento customer→workspace (o webhook
  skeleton só actualiza subscriptions já existentes por `provider_subscription_id`).
- **Notificações:** `NotificationPreference` (BCORE-1102, P1).
- **Static:** `collectstatic` não corrido em dev — origem do warning benigno do
  WhiteNoise nos testes (sem impacto funcional).

---

## 6. Riscos

- **Mistura Django ↔ motor analítico** — mitigado: nenhuma lógica de
  métricas/moments/insights no Django; fronteira em `integrations_bridge`.
- **Multi-tenancy inconsistente** — mitigado: `workspace` obrigatório, querysets
  filtrados, permission classes, testes cross-workspace.
- **Billing mal acoplado** — mitigado: usage/créditos idempotentes, ledger
  append-only, reserve/consume/refund, auditoria.
- **Webhook Stripe sem secret** — quando `STRIPE_WEBHOOK_SECRET` está vazio os
  eventos são aceites mas não verificados (`signature_verified: false`).
  Limitação documentada; **definir o secret antes de produção**.
- **`INTERNAL_API_TOKEN` vazio** — callbacks internos são todos rejeitados (default
  seguro); definir antes de ligar FastAPI/renderer/workers.

---

## 7. Próximo passo recomendado

O backend core está consistente, testado e documentado — pronto para servir de
base. Próximos passos sugeridos, por ordem:

1. **Definir segredos de ambiente** (`SECRET_KEY`, `INTERNAL_API_TOKEN`,
   `STRIPE_WEBHOOK_SECRET`) num `.env` real antes de qualquer integração.
2. **Avançar para o FastAPI Intelligence Engine / Content Renderer**, consumindo
   os contratos da `integrations_bridge` (criar `ExternalJobReference` e reportar
   estado via `internal/jobs/callback/`).
3. **Frontend (Next.js)** contra a API `/api/v1/` usando o schema OpenAPI.
4. Endereçar pendências P1 (labels/rosters, campaign channels, notification
   preferences, workspace branding) conforme prioridade de produto.
