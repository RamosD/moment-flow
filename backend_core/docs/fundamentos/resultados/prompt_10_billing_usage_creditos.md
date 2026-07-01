# Relatório de execução — Prompt 10: Billing, Usage e Créditos

- **Pipeline / Backlog:** Pipeline 09 — Billing, usage e créditos (BCORE-901, 902, 903, 904, 905, 906)
- **Data:** 2026-06-21
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`

---

## 1. Prompt executado

Implementar a fundação de billing: criar `apps.billing` com `Plan`, `PlanFeature`,
`Subscription`, `UsageEvent`, `CreditLedgerEntry` e `BillingWebhookEvent`; serviços
de subscrição, features/limites, usage idempotente e ledger de créditos
(`grant`/`reserve`/`consume`/`release`/`refund`); seed de planos e features
iniciais; *quota enforcement* integrado em fluxos existentes (artista, track,
campanha, smart link, content pack request); skeleton de webhook Stripe protegido
por assinatura e idempotente por `provider_event_id`; endpoints de consulta
(plano activo, uso do período, saldo de créditos); registo no Admin; e testes de
planos, subscriptions, usage idempotente, créditos, quotas e webhook duplicado.

## 2. Objectivo

Medir uso desde cedo e controlar limites por workspace com estrutura **segura e
idempotente**. Billing é responsabilidade principal do Django. Não se implementa
checkout Stripe completo — apenas o skeleton seguro. Garantir que não se cobra
duas vezes em *retries* (usage e créditos idempotentes; webhook deduplicado).

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/billing/__init__.py`, `apps/billing/apps.py` | App `apps.billing` |
| `apps/billing/models.py` | `Plan`, `PlanFeature`, `Subscription`, `UsageEvent`, `CreditLedgerEntry`, `BillingWebhookEvent` |
| `apps/billing/exceptions.py` | `QuotaExceeded`, `InsufficientCredits` (APIException 402) |
| `apps/billing/services.py` | Subscrições, features/limites, usage idempotente, ledger de créditos, `check_workspace_limit` |
| `apps/billing/seeds.py` | Catálogo de 7 planos e 9 features (idempotente) |
| `apps/billing/serializers.py` | Serializers read-only (plan, feature, subscription, usage, ledger) |
| `apps/billing/views.py` | `PlanViewSet` + endpoints de subscrição/uso/créditos + `StripeWebhookView` |
| `apps/billing/urls.py` | Router DRF (`/plans/`) + rotas `/billing/*` |
| `apps/billing/webhooks.py` | Verificação HMAC de assinatura Stripe + processamento idempotente |
| `apps/billing/admin.py` | Admin (usage/créditos/webhooks read-only) |
| `apps/billing/migrations/0001_initial.py` | Migration inicial |
| `apps/billing/management/commands/seed_billing.py` | Comando `seed_billing` |
| `apps/billing/tests/conftest.py` | Fixtures (rbac, billing, workspaces, subscribe) |
| `apps/billing/tests/test_plans.py` | Seed de planos/features + API pública de planos |
| `apps/billing/tests/test_subscriptions.py` | `get_active_subscription`, features, limites, endpoint |
| `apps/billing/tests/test_usage.py` | Usage idempotente + endpoint de uso do período |
| `apps/billing/tests/test_credits.py` | Ciclo de créditos + idempotência + endpoint de saldo |
| `apps/billing/tests/test_quotas.py` | `check_workspace_limit` + bloqueio por API + créditos em content pack |
| `apps/billing/tests/test_webhooks.py` | Webhook duplicado, assinatura válida/inválida, sync de subscrição |
| `docs/.../resultados/prompt_10_billing_usage_creditos.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `config/settings.py` | `"apps.billing"` em `INSTALLED_APPS`; bloco `STRIPE_WEBHOOK_SECRET`/`STRIPE_API_KEY` (via ambiente, sem segredos) |
| `config/urls.py` | Rotas de billing montadas em `api/v1/` |
| `.env.example` | Variáveis `STRIPE_WEBHOOK_SECRET`, `STRIPE_API_KEY` (vazias) |
| `apps/catalogue/views.py` | `artists_limit`/`tracks_limit` + usage `artist_created`/`track_created` na criação |
| `apps/campaigns/views.py` | `campaigns_limit` + usage `campaign_created` na criação |
| `apps/links/views.py` | `smart_links_limit` + usage `smart_link_created` na criação |
| `apps/content/services.py` | `content_packs_per_month` + reserva de créditos + usage `content_pack_requested` |

## 5. Migrations criadas

```text
apps/billing/migrations/0001_initial.py
    + Plan (plan_key unique; índice status+is_public)
    + PlanFeature (unique plan+feature_key)
    + Subscription (workspace FK; unique provider+provider_subscription_id; índice workspace+status)
    + UsageEvent (unique workspace+idempotency_key; índices workspace+event_type / workspace+billing_period)
    + CreditLedgerEntry (unique workspace+idempotency_key; índice workspace+transaction_type)
    + BillingWebhookEvent (unique provider+provider_event_id; índices provider+event_type / status)
```

`makemigrations --check --dry-run` confirma **No changes detected**; nenhuma
migration anterior foi alterada.

## 6. Comandos executados

```powershell
python manage.py makemigrations billing      # billing/0001_initial
python manage.py migrate                      # aplica billing.0001
python manage.py seed_billing                 # 7 planos, 63 features
python manage.py check                        # 0 issues
python manage.py makemigrations --check --dry-run   # No changes detected
python -m pytest -q                           # 159 passed
ruff check .                                  # All checks passed!
python manage.py spectacular --file schema.yml      # 0 errors
```

## 7. Resultado das validações

| Validação | Resultado |
|---|---|
| `makemigrations` / `migrate` | OK — `billing.0001_initial` aplicada |
| `seed_billing` | OK — **7 planos, 63 features** |
| `manage.py check` | OK — `System check identified no issues (0 silenced)` |
| `makemigrations --check` | OK — `No changes detected` |
| `pytest` | **159 passed** (116 anteriores + **43 de billing**) — 0 regressões |
| `ruff check .` | OK — `All checks passed!` |
| OpenAPI (`spectacular`) | OK — **0 erros** (2 warnings benignos: hint do `PublicSmartLinkSerializer` e colisão de enums `status`) |

**Nota benigna:** persiste o `UserWarning` do WhiteNoise sobre `staticfiles/`.

## 8. Decisões tomadas

- **Modelo de saldo (single available balance):** o saldo disponível é
  `sum(amount)` do ledger e é reconstituível. Convenção de sinais: `grant`,
  `purchase`, `refund`, `release` somam; `reserve`, `consume`, `expiration`
  subtraem; `adjustment` é assinado pelo chamador. `balance_after` desnormaliza o
  saldo para leituras baratas.
- **Reserve → settle:** `reserve_credits` retira do disponível (segura os
  créditos). No sucesso, `consume_credits(..., settle_reserved=True)` finaliza com
  *delta zero* (os créditos já saíram na reserva) — evitando dupla cobrança; na
  falha, `release_reserved_credits` devolve-os. `consume` directo (sem reserva)
  subtrai do disponível.
- **Idempotência em todo o lado:** `UsageEvent` e `CreditLedgerEntry` são únicos
  por `(workspace, idempotency_key)`; `record_usage_event` e cada operação de
  crédito devolvem `(obj, created)` e fazem *short-circuit* em replays
  (`IntegrityError` tratado). `BillingWebhookEvent` é único por
  `(provider, provider_event_id)` — retries Stripe nunca reprocessam.
- **Quota *fail-open* sem plano:** `check_workspace_limit` só bloqueia quando há
  subscrição activa com limite numérico definido. Sem plano, feature indefinida ou
  limite ilimitado (`limit_value=None`) → não bloqueia, cumprindo "não bloquear
  fluxos existentes sem mensagens claras". Quando bloqueia, devolve **402** com
  mensagem que indica feature, plano e contagem (`x/limit`).
- **Limites por contagem vs por mês:** `artists/tracks/campaigns/smart_links_limit`
  contam entidades vivas (excluindo arquivadas); `content_packs_per_month` e
  `reports_per_month` contam `UsageEvent` no `billing_period` corrente.
- **Content pack request:** valida quota mensal, regista usage idempotente e, se o
  pack declarar `metadata.credit_cost > 0`, **reserva créditos** à cabeça
  (transacção atómica — falha → rollback, sem request órfão nem dupla cobrança).
  Packs sem custo declarado seguem em frente (integração parcial documentada).
- **Stripe skeleton sem dependência:** verificação de assinatura HMAC-SHA256 em
  *stdlib* (sem instalar `stripe`), seguindo o esquema `"{t}.{payload}"`. Com
  `STRIPE_WEBHOOK_SECRET` definido, assinatura inválida → 400; sem secret, o evento
  é aceite e guardado mas marcado `signature_verified: false` (limitação
  documentada). Sem segredos no código (lidos do ambiente).
- **Admin:** `Plan`/`PlanFeature`/`Subscription` editáveis; `UsageEvent`,
  `CreditLedgerEntry` e `BillingWebhookEvent` são **read-only** (append-only,
  trilho de auditoria fiável).

## 9. Pendências

- **Checkout Stripe completo** (sessions, customer/price mapping, portal): fora do
  escopo por restrição — só skeleton.
- **Mapa Stripe → workspace:** o `_sync_subscription_from_event` só actualiza uma
  `Subscription` já existente por `provider_subscription_id`; criar subscrições a
  partir de `checkout.session.completed` exige guardar `customer_id`/metadata de
  ligação (a fazer quando houver Stripe real).
- **`storage_gb`:** definido como feature/limite mas **não há contador de uso de
  storage** (sem pipeline de assets reais ainda) — não é aplicado na criação.
- **Overage automático:** intencionalmente **não** implementado (restrição).
- **Reservas órfãs / expiração:** não há *job* a libertar reservas antigas nem a
  aplicar `expiration` — o tipo de transacção existe mas o agendamento fica para
  depois.
- **Usage em `smart_link_clicked`:** o endpoint público regista o clique mas ainda
  não emite `UsageEvent` (decisão de manter o caminho público leve); pode ligar-se
  num passo futuro.
- **`collectstatic`** continua por correr (warning benigno do WhiteNoise).

## 10. Próximo passo recomendado

Avançar para **Pipeline 10 — Reports, Media Kits e Notifications**
(BCORE-1001..1102), criando `apps.reports` e `apps.notifications` e ligando a
geração de relatórios/media kits aos meters já existentes
(`report_generated`/`media_kit_generated`) e a `check_workspace_limit`
(`reports_per_month`). Em paralelo, quando houver configuração Stripe real,
evoluir o skeleton de webhook para criar/sincronizar subscrições a partir de
`checkout.session.completed` e `customer.subscription.*`.
