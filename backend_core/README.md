# ChartRex / MomentFlow — Backend Core

Backend Core em **Django 6 / Django REST Framework** que governa a camada SaaS da
plataforma ChartRex / MomentFlow: autenticação, multi-tenancy, RBAC, catálogo
musical, campanhas, content core, smart links, billing/usage/créditos, reports,
media kits, notificações, auditoria e a ponte de integração para serviços
externos.

> **Regra de fronteira:** *Django governa o produto; FastAPI calcula e executa.*
> O backend core guarda entidades, estados e contratos. Não implementa recolha de
> métricas, detecção de moments, insights, nem renderização real de imagem/vídeo.
> Ver [Fronteira Django vs FastAPI](#fronteira-django-vs-fastapi).

---

## Visão geral

- **Stack:** Django 6.0, DRF 3.17, SimpleJWT, django-filter, drf-spectacular,
  django-cors-headers, WhiteNoise, python-decouple, psycopg.
- **Identidade:** `User` customizado (login por email), JWT.
- **Multi-tenant:** workspace activo resolvido pelo header `X-Workspace-ID`;
  todas as entidades de cliente filtram por `workspace`.
- **RBAC:** roles/permissions por workspace, aplicadas via permission classes DRF.
- **Billing:** usage events e credit ledger idempotentes, quotas por plano.
- **Auditoria:** `AuditEvent` imutável ligado aos fluxos críticos.
- **API:** versionada em `/api/v1/`, documentada por OpenAPI (Swagger + Redoc).
- **Qualidade:** pytest (235 testes), ruff, coverage.

---

## Requisitos

- **Python 3.13** (testado em 3.13.2).
- **pip** + `venv`.
- **SQLite** (default, sem configuração) ou **PostgreSQL 14+** (opcional, via
  `DB_ENGINE=postgres`).
- Windows / macOS / Linux. Os exemplos abaixo usam PowerShell (Windows); em
  bash/zsh ajustar o caminho do venv (`venv/bin/...`).

---

## Configuração de `.env`

Os settings são lidos do ambiente com `python-decouple` e têm defaults seguros
para desenvolvimento local, por isso **o `.env` é opcional para arrancar em
SQLite**. Para um ambiente reproduzível, copiar o exemplo:

```powershell
Copy-Item .env.example .env
```

Variáveis suportadas (ver `.env.example`):

| Variável | Default | Notas |
|---|---|---|
| `SECRET_KEY` | dev inseguro | **Obrigatório definir em produção.** |
| `DEBUG` | `True` | `False` em produção. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | CSV. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5200,...` | CSV (origem do frontend). |
| `DB_ENGINE` | `sqlite` | `postgres` para usar PostgreSQL. |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | — | Só quando `DB_ENGINE=postgres`. |
| `ACCESS_TOKEN_LIFETIME_MINUTES` | `60` | JWT access. |
| `REFRESH_TOKEN_LIFETIME_DAYS` | `7` | JWT refresh. |
| `STRIPE_WEBHOOK_SECRET` | vazio | Verifica assinatura do webhook quando definido. |
| `STRIPE_API_KEY` | vazio | Skeleton; sem checkout real. |
| `INTERNAL_API_TOKEN` | vazio | Token partilhado para callbacks internos (`X-Internal-Token`). Vazio = todos os callbacks internos são rejeitados. |

> **Segredos:** nunca commitar o `.env` real (está no `.gitignore`). Não há
> segredos hardcoded em `config/settings.py`.

---

## Instalação

```powershell
# 1. criar e activar o ambiente virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. instalar dependências
pip install -r requirements.txt

# 3. (opcional) criar o .env
Copy-Item .env.example .env
```

---

## Migrations

```powershell
python manage.py migrate                 # aplicar migrations
python manage.py makemigrations          # gerar novas migrations (quando se alteram models)
python manage.py makemigrations --check --dry-run   # CI: falha se faltarem migrations
```

---

## Seed (dados iniciais)

Comandos de seed idempotentes para os catálogos de sistema:

```powershell
python manage.py seed_rbac       # roles de sistema + permissions base
python manage.py seed_billing    # planos iniciais + plan features
python manage.py seed_content    # templates e content packs iniciais
```

Criar um superuser para o Django Admin (`/admin/`):

```powershell
python manage.py createsuperuser
```

---

## Runserver

```powershell
python manage.py runserver 127.0.0.1:8100
```

Pontos úteis:

- Admin / backoffice: `http://127.0.0.1:8100/admin/`
- Swagger UI: `http://127.0.0.1:8100/api/v1/docs/`
- Redoc: `http://127.0.0.1:8100/api/v1/redoc/`

---

## Testes

```powershell
pytest                           # suite completa (apps + tests transversais)
pytest -q                        # saída resumida
pytest apps/billing              # testes de uma app
coverage run -m pytest           # com cobertura
coverage report                  # relatório de cobertura
```

---

## Ruff (lint)

```powershell
ruff check .                     # lint
ruff check . --fix               # lint + correcções automáticas seguras
ruff format .                    # formatação
```

---

## OpenAPI

```powershell
python manage.py spectacular --file schema.yml   # gerar o schema OpenAPI
```

O schema também é servido em runtime:

- JSON/YAML: `/api/v1/schema/`
- Swagger UI: `/api/v1/docs/`
- Redoc: `/api/v1/redoc/`

---

## Endpoints principais

Todas as rotas autenticadas exigem JWT (`Authorization: Bearer <token>`); as
rotas de produto exigem também o header `X-Workspace-ID` (workspace activo onde o
utilizador é membro activo).

| Prefixo | Recurso |
|---|---|
| `/api/v1/auth/token/`, `token/refresh/`, `token/verify/`, `me/` | Autenticação JWT e perfil |
| `/api/v1/workspaces/`, `/workspace-members/` | Workspaces e membros |
| `/api/v1/assets/` | Assets (ficheiros/metadados) |
| `/api/v1/artists/`, `/tracks/`, `/track-platform-links/` | Catálogo musical |
| `/api/v1/campaigns/`, `/campaign-tracks/`, `/campaign-goals/` | Campanhas |
| `/api/v1/campaigns/{id}/intelligence/` (`POST`) | Intelligence de campanha (chamada síncrona ao FastAPI Intelligence Engine) |
| `/api/v1/templates/`, `/template-versions/`, `/content-packs/`, `/content-pack-templates/`, `/content-pack-requests/`, `/content-outputs/` | Content core |
| `/api/v1/smart-links/` (+ `/stats/`), `/smart-link-destinations/`, `/smart-link-clicks/` | Smart links |
| `/l/<slug>/` | Resolução pública de smart link + tracking de cliques (sem auth) |
| `/api/v1/plans/`, `/billing/subscription/`, `/billing/usage/`, `/billing/credits/`, `/billing/webhooks/stripe/` | Billing |
| `/api/v1/reports/`, `/report-sections/`, `/media-kits/`, `/media-kit-items/` | Reports e media kits |
| `/api/v1/notifications/` | Notificações in-app |
| `/internal/jobs/callback/` | Callback interno de jobs externos (`X-Internal-Token`, sem JWT) |
| `/api/v1/system/health/dependencies/` (`GET`) | Healthcheck agregado das dependências técnicas (Intelligence Engine, Content Renderer, base de dados). **Staff-only** (`IsAdminUser`); devolve sempre 200 com `status` por dependência e geral, sem expor tokens nem URLs completas |
| `/api/v1/schema/`, `/api/v1/docs/`, `/api/v1/redoc/` | OpenAPI |

---

## Fronteira Django vs FastAPI

Este backend é deliberadamente o **plano de produto**, não o plano analítico.

**Pertence ao Django (este repositório):**

- Identidade, autenticação e RBAC.
- Workspaces e isolamento multi-tenant.
- Entidades de produto: artistas, tracks, campanhas, content packs/outputs,
  smart links, reports, media kits.
- Billing: planos, subscriptions, usage events, credit ledger, quotas.
- Auditoria e backoffice (Django Admin).
- **Contratos** com serviços externos: `ExternalJobReference` e o callback
  interno `internal/jobs/callback/`.

**Não pertence ao Django (FastAPI Intelligence Engine / Content Renderer /
workers):**

- Recolha técnica de métricas (YouTube, etc.) e processamento de snapshots.
- Cálculo de growth spike, detecção de moments, insights e recomendações.
- Renderização real de imagem/vídeo (FFmpeg, Remotion), PDF avançado.
- Integrações externas pesadas, scraping, ML, benchmarking de cohorts.

A ligação a jobs pesados (renderer/workers) faz-se pela app `integrations_bridge`:
o Django cria uma referência de job e expõe um callback autenticado por
`X-Internal-Token` para o serviço externo reportar o estado. O Django **nunca**
executa o trabalho técnico — apenas regista estado e orquestra.

A ligação ao **Intelligence Engine** é diferente e mais simples: é uma chamada
**síncrona** dentro do próprio request HTTP do utilizador (sem
`ExternalJobReference`, sem callback, sem job assíncrono) — ver a secção
seguinte e o estado detalhado em
[`docs/backend_core/fundamentos/integracao_intelligence_engine/estado_integracao_intelligence_engine.md`](docs/backend_core/fundamentos/integracao_intelligence_engine/estado_integracao_intelligence_engine.md).

### Notas de integração (jobs externos — renderer/workers)

- Content Pack / Report / Media Kit abrem um `ExternalJobReference` e submetem-no
  ao renderer; o callback completed/failed cria `Asset`, actualiza estado, trata
  créditos, emite notification e audit.
- Controla-se por ambiente: `EXTERNAL_JOBS_ENABLED=false` mantém o job em `queued`
  (sem chamada); `EXTERNAL_JOBS_DRY_RUN=true` simula a submissão. Em local, com
  FastAPI/renderer ainda inexistentes, usar **dry-run**.
- Contratos de payload/callback, settings e segurança detalhados em
  [`docs/backend_core/integracoes/02_estado_integracao_fastapi_renderer.md`](docs/backend_core/integracoes/02_estado_integracao_fastapi_renderer.md).

### Notas de integração (Intelligence Engine — síncrono)

- `POST /api/v1/campaigns/{id}/intelligence/` chama o serviço
  `CampaignIntelligenceService` (`apps/campaigns/intelligence_service.py`), que
  monta o payload com `CampaignIntelligencePayloadBuilder`
  (`apps/campaigns/intelligence_payload.py`) e chama o FastAPI Intelligence
  Engine via `IntelligenceEngineClient` (`apps/integrations_bridge/intelligence_sync.py`).
- Controla-se por `INTELLIGENCE_ENGINE_ENABLED`/`INTELLIGENCE_ENGINE_DRY_RUN`
  (independentes dos `EXTERNAL_JOBS_*` acima — caminhos isolados de propósito).
- Estado completo, arquitectura, settings, testes e pendências em
  [`docs/backend_core/fundamentos/integracao_intelligence_engine/estado_integracao_intelligence_engine.md`](docs/backend_core/fundamentos/integracao_intelligence_engine/estado_integracao_intelligence_engine.md).

---

## Estrutura do projecto

```text
backend_core/
  config/            settings, urls, asgi, wsgi
  apps/
    core/            base models (UUID/timestamps/soft-delete), Asset, paginação
    accounts/        User customizado, JWT, /me
    workspaces/      Workspace, WorkspaceMember, resolução de X-Workspace-ID
    rbac/            Role, Permission, guards DRF, seed_rbac
    catalogue/       Artist, Track, TrackPlatformLink
    campaigns/       Campaign, CampaignTrack, CampaignGoal
    content/         Template(Version), ContentPack(Template), Request, Output, seed_content
    links/           SmartLink, Destination, Click, página pública
    billing/         Plan(Feature), Subscription, UsageEvent, CreditLedger, Stripe skeleton, seed_billing
    reports/         Report(Section), MediaKit(Item)
    notifications/   Notification
    audit/           AuditEvent (imutável) + service
    integrations_bridge/  ExternalJobReference + callback interno
  tests/             suite transversal (multi-tenancy, RBAC, billing, ...)
```

Estado de implementação detalhado:
[`docs/backend_core/fundamentos/02_estado_implementacao_backend_core.md`](docs/backend_core/fundamentos/02_estado_implementacao_backend_core.md).
