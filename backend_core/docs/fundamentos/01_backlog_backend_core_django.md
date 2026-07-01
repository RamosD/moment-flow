# Backlog: Backend Core Django/DRF

# ChartRex / MomentFlow — Backend Core

## 1. Objectivo do documento

Este documento define o backlog técnico do **Backend Core em Django/DRF** para a plataforma ChartRex / MomentFlow.

O backend core é responsável pela camada SaaS, produto, permissões, catálogo, campanhas, smart links, billing, quotas, usage, auditoria e backoffice.

Este backlog assume que o projecto Django já foi criado em:

```text
D:\Workspace\ChartRex\momentflow\backend_core
```

E que já existem:

```text
manage.py
config/
venv/
```

Também assume que já foram instaladas as bibliotecas principais:

```text
Django
djangorestframework
django-filter
drf-spectacular
django-cors-headers
psycopg
pytest
pytest-django
factory-boy
coverage
ruff
djangorestframework-simplejwt
python-decouple
whitenoise
```

Este documento não é uma especificação genérica. É um backlog executável para orientar uma IA local ou developer na implementação incremental do backend core.

---

## 2. Fronteira do Backend Core

## 2.1 Responsabilidades do Django/DRF

O backend core em Django/DRF é responsável por:

```text
autenticação;
utilizadores;
workspaces;
multi-tenancy;
RBAC;
permissões;
convites;
artistas;
labels;
músicas;
campanhas;
objectivos de campanha;
smart links;
páginas públicas de smart links;
content packs como entidades de produto;
outputs como entidades de produto;
assets;
billing;
planos;
quotas;
créditos;
usage events;
watermark rules;
relatórios como entidade core;
media kits como entidade core;
notificações base;
audit logs;
Django Admin;
APIs REST administrativas e de produto;
contratos de integração com FastAPI/renderer.
```

Regra principal:

> Django governa o produto.

---

## 2.2 Responsabilidades que não pertencem ao Django nesta fase

Não implementar no backend core Django:

```text
recolha técnica de métricas YouTube;
processamento pesado de snapshots;
cálculo de growth spike;
detecção algorítmica de moments;
engine de insights;
engine de recomendações analíticas;
renderização real de imagens;
renderização de vídeo;
FFmpeg;
Remotion;
workers técnicos de métricas;
integrações externas pesadas;
scraping;
machine learning;
cohort benchmarking avançado.
```

Esses domínios pertencem a futuros componentes:

```text
FastAPI Intelligence Engine;
Content Renderer;
Workers técnicos;
serviços de integração.
```

O Django pode, no entanto, manter entidades core, estados, referências e contratos necessários para orquestrar esses serviços.

---

## 3. Princípios técnicos

A implementação deve seguir estes princípios:

```text
multi-tenant desde o primeiro commit;
workspace_id obrigatório nas entidades de cliente;
Custom User desde o início;
Django como autoridade de identidade e permissões;
DRF para APIs;
SimpleJWT para autenticação;
drf-spectacular para OpenAPI;
django-filter para filtros;
pytest para testes;
factory-boy para fixtures;
ruff para qualidade;
python-decouple para configuração;
whitenoise para static files;
Django Admin como backoffice inicial;
usage events desde cedo;
audit logs desde cedo;
soft delete em entidades de negócio críticas;
UUID como chave primária nas entidades principais;
não misturar responsabilidades do FastAPI dentro do Django.
```

---

## 4. Estado actual do projecto

O projecto já tem:

```text
venv criado;
Django instalado;
project config criado;
DRF instalado;
django-filter instalado;
drf-spectacular instalado;
django-cors-headers instalado;
psycopg instalado;
pytest stack instalada;
SimpleJWT instalado;
python-decouple instalado;
whitenoise instalado.
```

Logo, este backlog começa a partir da consolidação da estrutura e implementação das apps.

---

## 5. Estrutura recomendada do projecto

Estrutura alvo:

```text
backend_core/
  manage.py
  requirements.txt
  .env
  .env.example
  pytest.ini
  pyproject.toml

  config/
    __init__.py
    settings.py
    urls.py
    asgi.py
    wsgi.py

  apps/
    __init__.py

    core/
      __init__.py
      apps.py
      models.py
      admin.py
      permissions.py
      pagination.py
      exceptions.py
      mixins.py
      utils.py

    accounts/
      __init__.py
      apps.py
      models.py
      admin.py
      serializers.py
      views.py
      urls.py
      managers.py
      permissions.py
      tests/

    workspaces/
      __init__.py
      apps.py
      models.py
      admin.py
      serializers.py
      views.py
      urls.py
      services.py
      selectors.py
      permissions.py
      tests/

    rbac/
      __init__.py
      apps.py
      models.py
      admin.py
      services.py
      permissions.py
      tests/

    catalogue/
      __init__.py
      apps.py
      models.py
      admin.py
      serializers.py
      views.py
      urls.py
      filters.py
      tests/

    campaigns/
      __init__.py
      apps.py
      models.py
      admin.py
      serializers.py
      views.py
      urls.py
      filters.py
      tests/

    content/
      __init__.py
      apps.py
      models.py
      admin.py
      serializers.py
      views.py
      urls.py
      filters.py
      services.py
      tests/

    links/
      __init__.py
      apps.py
      models.py
      admin.py
      serializers.py
      views.py
      urls.py
      filters.py
      services.py
      tests/

    billing/
      __init__.py
      apps.py
      models.py
      admin.py
      serializers.py
      views.py
      urls.py
      services.py
      selectors.py
      tests/

    reports/
      __init__.py
      apps.py
      models.py
      admin.py
      serializers.py
      views.py
      urls.py
      tests/

    audit/
      __init__.py
      apps.py
      models.py
      admin.py
      services.py
      middleware.py
      tests/

    notifications/
      __init__.py
      apps.py
      models.py
      admin.py
      serializers.py
      views.py
      urls.py
      tests/

    integrations_bridge/
      __init__.py
      apps.py
      models.py
      services.py
      tests/

  tests/
    conftest.py
    factories/
```

---

## 6. Apps Django recomendadas

## 6.1 Apps de fundação

```text
apps.core
apps.accounts
apps.workspaces
apps.rbac
apps.audit
```

## 6.2 Apps de produto

```text
apps.catalogue
apps.campaigns
apps.content
apps.links
apps.reports
apps.notifications
```

## 6.3 Apps comerciais

```text
apps.billing
```

## 6.4 Apps de integração futura

```text
apps.integrations_bridge
```

A app `integrations_bridge` não deve implementar a lógica técnica do FastAPI. Deve apenas guardar contratos, estados, callbacks e configurações necessárias para orquestrar serviços externos.

---

# 7. Configuração base

## BCORE-001 — Consolidar settings base

### Objectivo

Preparar `config/settings.py` para desenvolvimento limpo, variáveis de ambiente, DRF, JWT, CORS, OpenAPI, static files e apps locais.

### Tarefas

```text
Criar .env.
Criar .env.example.
Configurar python-decouple.
Configurar SECRET_KEY via ambiente.
Configurar DEBUG via ambiente.
Configurar ALLOWED_HOSTS.
Configurar DATABASE_URL ou variáveis separadas para PostgreSQL.
Configurar INSTALLED_APPS com third-party apps.
Configurar MIDDLEWARE com CORS e WhiteNoise.
Configurar REST_FRAMEWORK.
Configurar SimpleJWT.
Configurar drf-spectacular.
Configurar CORS_ALLOWED_ORIGINS.
Configurar STATIC_URL e STATIC_ROOT.
Configurar DEFAULT_AUTO_FIELD.
Configurar LANGUAGE_CODE e TIME_ZONE.
```

### Apps third-party esperadas

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "drf_spectacular",
    "corsheaders",

    "apps.core",
    "apps.accounts",
    "apps.workspaces",
    "apps.rbac",
    "apps.catalogue",
    "apps.campaigns",
    "apps.content",
    "apps.links",
    "apps.billing",
    "apps.reports",
    "apps.audit",
    "apps.notifications",
    "apps.integrations_bridge",
]
```

### Critérios de aceitação

```text
Django arranca sem erro.
settings não contém segredos hardcoded.
DRF usa JWT por padrão.
OpenAPI está configurado.
CORS está configurado.
WhiteNoise está activo.
Todas as apps locais são carregadas.
```

---

## BCORE-002 — Criar ficheiros de qualidade e testes

### Objectivo

Preparar base de testes e qualidade.

### Tarefas

```text
Criar pytest.ini.
Criar pyproject.toml com configuração do ruff.
Criar coverage config, se aplicável.
Criar tests/conftest.py.
Criar tests/factories/.
Criar requirements.txt com pip freeze.
Criar comando documentado para correr testes.
Criar comando documentado para ruff.
```

### Critérios de aceitação

```text
pytest executa.
ruff check executa.
coverage pode ser executado.
requirements.txt existe.
```

---

# 8. Épico 1 — Accounts e autenticação

## Objectivo

Implementar utilizador customizado, autenticação JWT e endpoints base de conta.

---

## BCORE-101 — Criar Custom User

### Objectivo

Criar modelo de utilizador customizado baseado em email.

### Tarefas

```text
Criar apps.accounts.
Criar User customizado.
Usar email como USERNAME_FIELD.
Criar UserManager.
Adicionar campos full_name, display_name, avatar_url, preferred_language, timezone, email_verified_at.
Configurar AUTH_USER_MODEL.
Registar User no Django Admin.
Criar migration inicial.
Criar testes do UserManager.
```

### Critérios de aceitação

```text
AUTH_USER_MODEL aponta para accounts.User.
Superuser pode ser criado por createsuperuser.
Login por email funciona.
Admin lista utilizadores.
Testes passam.
```

---

## BCORE-102 — Autenticação JWT

### Objectivo

Expor endpoints de autenticação JWT.

### Tarefas

```text
Configurar SimpleJWT.
Criar endpoints token obtain e refresh.
Criar endpoint /api/auth/me/.
Criar serializer de perfil do utilizador.
Criar endpoint para actualizar perfil.
Criar endpoint de logout lógico, se aplicável.
Documentar endpoints no Swagger.
```

### Critérios de aceitação

```text
Utilizador obtém access token.
Utilizador actualiza token com refresh.
Endpoint /me retorna dados do utilizador autenticado.
Endpoint /me rejeita utilizador anónimo.
Swagger mostra endpoints.
```

---

## BCORE-103 — Password reset e verificação futura

### Objectivo

Preparar estrutura para recuperação de password e verificação de email.

### Tarefas

```text
Criar modelos PasswordResetToken e EmailVerificationToken ou usar fluxo compatível com Django.
Criar serviços para gerar token com hash.
Criar endpoints request-reset e confirm-reset.
Criar placeholders para envio de email.
Criar testes.
```

### Critérios de aceitação

```text
Pedido de reset cria token seguro.
Token expira.
Token usado não pode ser reutilizado.
Password é alterada com token válido.
```

---

# 9. Épico 2 — Workspaces e multi-tenancy

## Objectivo

Criar a fundação SaaS multi-tenant.

---

## BCORE-201 — Criar Workspace

### Objectivo

Implementar a entidade central de tenant.

### Tarefas

```text
Criar app workspaces.
Criar modelo Workspace.
Campos: id UUID, name, slug, workspace_type, country, market, default_language, timezone, status, created_by, metadata, timestamps, deleted_at.
Criar enum de workspace_type.
Criar enum de status.
Registar no Admin.
Criar serializers.
Criar viewsets.
Criar filtros.
Criar testes.
```

### Critérios de aceitação

```text
Utilizador autenticado cria workspace.
Slug é único.
Workspace tem estado active/trial/suspended/cancelled/archived.
Workspace aparece no Admin.
API filtra workspaces do utilizador.
```

---

## BCORE-202 — Workspace Members

### Objectivo

Permitir membros por workspace.

### Tarefas

```text
Criar modelo WorkspaceMember.
Relacionar workspace, user e role.
Campos: status, invited_by, joined_at, timestamps.
Criar estados invited, active, suspended, removed.
Criar endpoint para listar membros.
Criar endpoint para adicionar membro existente.
Criar endpoint para remover membro.
Criar endpoint para alterar role.
Criar testes de isolamento.
```

### Critérios de aceitação

```text
Um utilizador pode pertencer a vários workspaces.
Um workspace pode ter vários membros.
Não é possível duplicar user no mesmo workspace.
Membro removido perde acesso.
```

---

## BCORE-203 — Workspace Context

### Objectivo

Criar mecanismo consistente para resolver workspace activo.

### Tarefas

```text
Definir estratégia de workspace activo via header X-Workspace-ID.
Criar permission/mixin para validar membership.
Criar base queryset filtrado por workspace.
Criar helper get_current_workspace.
Criar testes para acesso cross-workspace.
```

### Critérios de aceitação

```text
Requests com workspace inválido são rejeitados.
Utilizador não acede dados de workspace onde não é membro.
Querysets de entidades tenant-aware filtram por workspace.
Testes provam isolamento.
```

---

## BCORE-204 — Workspace Settings e Branding

### Objectivo

Preparar configurações e branding base por workspace.

### Tarefas

```text
Criar WorkspaceSettings.
Criar WorkspaceBranding.
Campos de branding: logo_asset, primary_color, secondary_color, font_family, brand_voice, watermark_enabled, custom_domain.
Criar endpoints de leitura/actualização.
Criar permissões para alteração.
Registar no Admin.
```

### Critérios de aceitação

```text
Workspace tem settings.
Workspace tem branding.
Apenas admin/owner altera branding.
Branding pode ser usado por content outputs futuramente.
```

---

# 10. Épico 3 — RBAC e permissões

## Objectivo

Implementar permissões por workspace e roles.

---

## BCORE-301 — Roles e Permissions

### Objectivo

Criar catálogo de roles e permissions.

### Tarefas

```text
Criar app rbac.
Criar modelo Role.
Criar modelo Permission.
Criar modelo RolePermission.
Criar roles de sistema: owner, admin, manager, editor, viewer, billing_admin, api_user.
Criar permissions base.
Criar seed command para roles/permissions.
Registar no Admin.
```

### Permissões base

```text
workspace:manage
members:invite
members:manage
artists:view
artists:create
artists:update
artists:delete
tracks:view
tracks:create
tracks:update
tracks:delete
campaigns:view
campaigns:create
campaigns:update
campaigns:delete
content:view
content:generate
content:export
links:view
links:create
links:update
links:delete
reports:view
reports:generate
billing:view
billing:manage
branding:manage
api_keys:manage
```

### Critérios de aceitação

```text
Roles são criadas por seed command.
Permissions são criadas por seed command.
Role tem várias permissions.
WorkspaceMember aponta para role.
```

---

## BCORE-302 — Permission Guards

### Objectivo

Criar permissões DRF reutilizáveis.

### Tarefas

```text
Criar permission class IsWorkspaceMember.
Criar permission class HasWorkspacePermission.
Criar mixin RequiredWorkspacePermissionMixin.
Criar util user_has_permission.
Criar testes por role.
```

### Critérios de aceitação

```text
Viewer não cria campanha.
Editor cria conteúdo.
Billing admin acede billing.
Utilizador fora do workspace é bloqueado.
```

---

# 11. Épico 4 — Core utilities

## Objectivo

Criar bases transversais para models, soft delete, timestamps, ownership, assets e paginação.

---

## BCORE-401 — Base Models

### Objectivo

Criar modelos abstractos reutilizáveis.

### Tarefas

```text
Criar UUIDModel.
Criar TimeStampedModel.
Criar SoftDeleteModel.
Criar WorkspaceOwnedModel.
Criar CreatedUpdatedByModel.
Criar StatusModel, se útil.
Criar managers para soft delete.
Criar testes.
```

### Critérios de aceitação

```text
Entidades principais usam UUID.
Timestamps são automáticos.
Soft delete funciona.
Queryset padrão exclui deleted_at, quando aplicável.
```

---

## BCORE-402 — Assets

### Objectivo

Criar entidade genérica para ficheiros e assets.

### Tarefas

```text
Criar modelo Asset em apps.core.
Campos: workspace, asset_type, storage_provider, bucket, storage_key, file_name, mime_type, file_size_bytes, width, height, duration_seconds, checksum, created_by, metadata, deleted_at.
Criar serializer.
Criar viewset básico.
Criar Admin.
```

### Critérios de aceitação

```text
Asset pertence a workspace.
Asset pode representar logo, capa, output, PDF ou imagem.
API lista assets do workspace.
Admin permite consultar assets.
```

---

## BCORE-403 — Paginação e filtros padrão

### Objectivo

Uniformizar APIs.

### Tarefas

```text
Criar paginação padrão.
Configurar page_size.
Criar filtros por status, created_at, updated_at.
Criar ordering padrão.
Criar respostas de erro consistentes.
```

### Critérios de aceitação

```text
Viewsets principais paginam.
Filtros básicos funcionam.
Ordering funciona.
```

---

# 12. Épico 5 — Catálogo musical

## Objectivo

Implementar artistas, labels, músicas e links de plataforma.

---

## BCORE-501 — Artists

### Objectivo

Criar gestão de artistas.

### Tarefas

```text
Criar app catalogue.
Criar modelo Artist.
Campos: workspace, name, slug, country, market, primary_genre, language, bio_short, bio_long, image_asset, status, metadata.
Criar serializer.
Criar viewset.
Criar filtros.
Criar Admin.
Criar testes.
```

### Critérios de aceitação

```text
Utilizador cria artista no workspace.
Artista não aparece noutro workspace.
Slug é único por workspace.
Artista pode ser arquivado.
```

---

## BCORE-502 — Tracks

### Objectivo

Criar gestão de músicas/faixas monitorizáveis.

### Tarefas

```text
Criar modelo Track.
Campos: workspace, artist, title, slug, release_date, track_type, primary_genre, language, market, cover_asset, status, metadata.
Criar enum track_type.
Criar enum status.
Criar serializer.
Criar viewset.
Criar filtros por artist, status, release_date.
Criar Admin.
Criar testes.
```

### Critérios de aceitação

```text
Utilizador cria música associada a artista do mesmo workspace.
Música não pode referenciar artista de outro workspace.
Música pode ter estado draft/scheduled/released/monitoring/paused/archived.
```

---

## BCORE-503 — Track Platform Links

### Objectivo

Permitir links por plataforma.

### Tarefas

```text
Criar modelo TrackPlatformLink.
Campos: workspace, track, platform, external_id, url, canonical_url, status, last_validated_at, validation_error, metadata.
Criar enum platform.
Criar enum status.
Criar serializer.
Criar viewset.
Criar validação simples de URL YouTube.
Extrair video_id de YouTube de forma básica.
Criar testes.
```

### Critérios de aceitação

```text
Utilizador adiciona link YouTube a uma música.
Sistema guarda external_id quando possível.
Link pertence ao mesmo workspace da música.
Não permite duplicar platform + external_id no mesmo workspace.
```

### Nota

A validação técnica profunda e recolha de métricas pertencem ao FastAPI. Nesta fase, Django faz apenas validação leve e persistência.

---

## BCORE-504 — Labels e Rosters

### Objectivo

Preparar gestão B2B de labels e rosters.

### Prioridade

P1. Pode entrar depois do MVP inicial.

### Tarefas

```text
Criar modelo Label.
Criar modelo LabelArtist.
Criar serializers.
Criar viewsets.
Criar filtros.
Criar Admin.
Criar testes.
```

### Critérios de aceitação

```text
Workspace cria label.
Label associa artistas.
Relação tem tipo: signed, distributed, managed, partner, historical.
```

---

# 13. Épico 6 — Campanhas

## Objectivo

Implementar campanha como unidade principal de valor.

---

## BCORE-601 — Campaigns

### Objectivo

Criar gestão de campanhas.

### Tarefas

```text
Criar app campaigns.
Criar modelo Campaign.
Campos: workspace, artist, track nullable, name, slug, campaign_type, status, start_date, end_date, primary_goal, description, metadata.
Criar enum campaign_type.
Criar enum status.
Criar serializer.
Criar viewset.
Criar filtros por artist, track, status, campaign_type.
Criar Admin.
Criar testes.
```

### Critérios de aceitação

```text
Utilizador cria campanha.
Campanha pertence a workspace.
Campanha referencia artista/música do mesmo workspace.
Campanha pode ser draft/scheduled/active/paused/completed/archived.
```

---

## BCORE-602 — Campaign Tracks

### Objectivo

Permitir campanhas com múltiplas músicas.

### Tarefas

```text
Criar modelo CampaignTrack.
Campos: workspace, campaign, track, role, metadata.
Criar serializer.
Criar endpoints para adicionar/remover tracks.
Criar testes.
```

### Critérios de aceitação

```text
Campanha pode ter várias músicas.
Não duplica mesma música na mesma campanha.
Todas as músicas pertencem ao mesmo workspace.
```

---

## BCORE-603 — Campaign Goals

### Objectivo

Permitir objectivos de campanha.

### Tarefas

```text
Criar modelo CampaignGoal.
Campos: workspace, campaign, goal_type, target_value, current_value, unit, deadline, status, metadata.
Criar serializer.
Criar viewset nested ou endpoint por campaign.
Criar Admin.
Criar testes.
```

### Critérios de aceitação

```text
Campanha tem objectivos.
Objectivo tem tipo views/clicks/content_outputs/milestone/reports/custom.
Objectivo pode ser active/achieved/missed/cancelled.
```

---

## BCORE-604 — Campaign Channels e Timeline

### Objectivo

Preparar canais e actividade da campanha.

### Prioridade

P1.

### Tarefas

```text
Criar CampaignChannel.
Criar CampaignTimelineItem.
Criar endpoints.
Criar Admin.
Criar testes.
```

### Critérios de aceitação

```text
Campanha tem canais alvo.
Timeline regista eventos funcionais.
```

---

# 14. Épico 7 — Content core

## Objectivo

Criar entidades core para templates, content packs, requests e outputs, sem implementar renderização real.

---

## BCORE-701 — Templates e versões

### Objectivo

Criar catálogo de templates.

### Tarefas

```text
Criar app content.
Criar modelo Template.
Criar modelo TemplateVersion.
Campos: template_key, name, description, template_type, status, is_premium, is_system, workspace nullable, metadata.
TemplateVersion: version, renderer_type, manifest, required_props, supported_formats, status.
Criar serializers.
Criar viewsets.
Criar filtros.
Criar Admin.
Criar seed de templates iniciais.
Criar testes.
```

### Critérios de aceitação

```text
Template global pode ser listado.
Template por workspace só aparece ao workspace.
Template activo tem versão activa.
TemplateVersion guarda manifest.
```

---

## BCORE-702 — Content Packs

### Objectivo

Criar catálogo de packs comerciais.

### Tarefas

```text
Criar modelo ContentPack.
Criar modelo ContentPackTemplate.
Campos: pack_key, name, description, pack_type, status, is_premium, workspace nullable, metadata.
Relacionar pack a templates.
Criar serializers.
Criar viewsets.
Criar Admin.
Criar seed de packs iniciais.
```

### Packs iniciais

```text
release_pack
milestone_pack
weekly_growth_pack
monthly_recap_pack
auto_media_kit
```

### Critérios de aceitação

```text
Pack activo é listado.
Pack mostra templates incluídos.
Pack pode ser global ou por workspace.
```

---

## BCORE-703 — Content Pack Requests

### Objectivo

Criar pedido de geração de pack.

### Tarefas

```text
Criar modelo ContentPackRequest.
Campos: workspace, campaign, track nullable, artist nullable, content_pack, requested_by, status, requested_at, completed_at, failed_at, error_message, usage_event nullable, metadata.
Criar serializer.
Criar viewset.
Criar endpoint request generation.
Validar permissões.
Validar plano/créditos via billing service placeholder.
Criar testes.
```

### Critérios de aceitação

```text
Utilizador cria pedido de content pack.
Pedido fica queued ou draft conforme fluxo.
Pedido valida campaign do mesmo workspace.
Pedido pode ser completed/failed/cancelled.
```

---

## BCORE-704 — Content Outputs

### Objectivo

Criar entidade de output gerado.

### Tarefas

```text
Criar modelo ContentOutput.
Campos: workspace, campaign, track nullable, artist nullable, content_pack_request nullable, template, template_version, output_type, format, status, title, caption, cta, storage_asset, public_visibility, created_by, expires_at, usage_event nullable, metadata.
Criar serializer.
Criar viewset.
Criar filtros por campaign, track, output_type, status.
Criar Admin.
Criar testes.
```

### Critérios de aceitação

```text
Output pertence ao workspace.
Output referencia campaign.
Output pode referenciar pack request.
Output aparece na biblioteca de outputs.
Output pode estar queued/processing/completed/failed/cancelled/expired/archived.
```

---

## BCORE-705 — Bridge para renderer futuro

### Objectivo

Preparar contrato sem renderizar de facto.

### Tarefas

```text
Criar service create_content_generation_request.
Criar payload interno de geração.
Criar interface para chamada futura ao Content Renderer/FastAPI.
Criar mock local que cria output em estado queued.
Criar callback endpoint interno para actualizar output.
Criar testes.
```

### Critérios de aceitação

```text
Django consegue criar request de geração.
Request cria ContentPackRequest.
Request cria ContentOutput placeholder, se aplicável.
Callback interno actualiza status.
Nenhuma renderização real é implementada.
```

---

# 15. Épico 8 — Smart Links

## Objectivo

Implementar smart links, destinos, tracking de cliques e página pública base.

---

## BCORE-801 — Smart Links

### Objectivo

Criar smart links por campanha.

### Tarefas

```text
Criar app links.
Criar modelo SmartLink.
Campos: workspace, campaign, track nullable, artist nullable, slug, title, description, status, branding_enabled, created_by, metadata.
Criar serializer.
Criar viewset.
Criar filtros.
Criar Admin.
Criar testes.
```

### Critérios de aceitação

```text
Utilizador cria smart link.
Slug é único.
Smart link pertence à campanha do workspace.
Smart link pode ser draft/active/paused/expired/archived.
```

---

## BCORE-802 — Smart Link Destinations

### Objectivo

Permitir múltiplos destinos.

### Tarefas

```text
Criar modelo SmartLinkDestination.
Campos: workspace, smart_link, platform, label, url, sort_order, is_active, metadata.
Criar endpoints nested.
Criar validações.
Criar testes.
```

### Critérios de aceitação

```text
Smart link tem destinos.
Destinos têm ordem.
Destino pode ser activado/desactivado.
```

---

## BCORE-803 — Página pública e tracking

### Objectivo

Criar página pública ou endpoint base para smart link.

### Tarefas

```text
Criar endpoint público /l/<slug>/ ou API equivalente.
Criar endpoint para resolver smart link.
Criar modelo SmartLinkClick.
Campos: workspace, smart_link, destination nullable, content_output nullable, campaign, track nullable, clicked_at, referrer, utm_source, utm_medium, utm_campaign, utm_content, country, device_type, browser, ip_hash, user_agent_hash, metadata.
Registar clique antes de redireccionar.
Criar estatísticas simples.
Criar testes.
```

### Critérios de aceitação

```text
Link público activo é resolvido.
Clique é registado.
Destino recebe redirect.
Smart link pausado não redirecciona.
Estatísticas por smart link são consultáveis.
```

---

# 16. Épico 9 — Billing, planos, quotas e créditos

## Objectivo

Criar fundação de monetização e controlo de uso.

---

## BCORE-901 — Plans e Plan Features

### Objectivo

Criar planos e features.

### Tarefas

```text
Criar app billing.
Criar modelo Plan.
Criar modelo PlanFeature.
Criar seed de planos iniciais.
Criar serializers.
Criar viewsets read-only.
Criar Admin.
Criar testes.
```

### Planos iniciais

```text
trial
artist_starter
artist_growth
manager
label_agency
white_label
enterprise
```

### Critérios de aceitação

```text
Planos são criados por seed.
Features têm limit_value e is_enabled.
Admin pode gerir planos.
API lista planos públicos.
```

---

## BCORE-902 — Subscriptions

### Objectivo

Associar plano ao workspace.

### Tarefas

```text
Criar modelo Subscription.
Campos: workspace, plan, provider, provider_subscription_id, status, current_period_start, current_period_end, trial_start, trial_end, cancel_at_period_end, metadata.
Criar service get_active_subscription.
Criar service workspace_has_feature.
Criar service get_plan_limit.
Criar Admin.
Criar testes.
```

### Critérios de aceitação

```text
Workspace tem subscrição activa ou trial.
Sistema consulta features do plano.
Sistema consulta limites do plano.
```

---

## BCORE-903 — Usage Events

### Objectivo

Registar uso da plataforma.

### Tarefas

```text
Criar modelo UsageEvent.
Campos: workspace, event_type, quantity, unit, related_entity_type, related_entity_id, cost_units, billing_period, idempotency_key, metadata.
Criar service record_usage_event.
Garantir idempotência.
Criar Admin.
Criar testes.
```

### Eventos iniciais

```text
artist_created
track_created
track_monitored
campaign_created
content_pack_requested
content_pack_generated
content_output_created
smart_link_created
smart_link_clicked
report_generated
media_kit_generated
```

### Critérios de aceitação

```text
Usage event é registado.
Evento duplicado com mesma idempotency_key não duplica.
Usage pode ser consultado por workspace e período.
```

---

## BCORE-904 — Credit Ledger

### Objectivo

Criar livro de créditos.

### Tarefas

```text
Criar modelo CreditLedgerEntry.
Campos: workspace, transaction_type, amount, balance_after, reason, related_entity_type, related_entity_id, idempotency_key, metadata.
Criar service grant_credits.
Criar service reserve_credits.
Criar service consume_credits.
Criar service release_reserved_credits.
Criar service refund_credits.
Criar testes.
```

### Critérios de aceitação

```text
Créditos são concedidos.
Créditos são consumidos.
Saldo é reconstituível.
Falha técnica pode gerar refund.
Consumo duplicado é evitado.
```

---

## BCORE-905 — Quota Enforcement

### Objectivo

Bloquear acções fora do plano.

### Tarefas

```text
Criar service check_workspace_limit.
Criar validação de limite de artistas.
Criar validação de limite de músicas.
Criar validação de limite de campanhas activas.
Criar validação de limite de smart links.
Criar validação de créditos para content packs.
Criar mensagens de erro claras.
Criar testes.
```

### Critérios de aceitação

```text
Workspace sem créditos não gera content pack.
Workspace no limite não cria nova campanha activa.
Mensagem de erro indica limite e plano.
```

---

## BCORE-906 — Stripe skeleton

### Objectivo

Preparar integração com Stripe sem bloquear o core.

### Tarefas

```text
Criar modelo BillingWebhookEvent.
Criar endpoint para webhook Stripe.
Validar assinatura por configuração.
Guardar provider_event_id.
Garantir idempotência.
Tratar eventos principais em modo inicial.
Criar placeholders para checkout.
Criar testes de webhook duplicado.
```

### Eventos mínimos

```text
checkout.session.completed
customer.subscription.created
customer.subscription.updated
customer.subscription.deleted
invoice.payment_succeeded
invoice.payment_failed
```

### Critérios de aceitação

```text
Webhook é recebido.
Evento é guardado.
Evento duplicado não reprocessa.
Subscription é actualizada quando aplicável.
```

---

# 17. Épico 10 — Reports e Media Kits core

## Objectivo

Criar entidades core de relatórios e media kits, sem implementar renderer avançado.

---

## BCORE-1001 — Reports

### Objectivo

Criar histórico e pedidos de relatórios.

### Tarefas

```text
Criar app reports.
Criar modelo Report.
Campos: workspace, campaign nullable, artist nullable, track nullable, report_type, title, period_start, period_end, status, requested_by, storage_asset, metadata.
Criar modelo ReportSection.
Criar serializers.
Criar viewsets.
Criar Admin.
Criar testes.
```

### Critérios de aceitação

```text
Utilizador cria pedido de relatório.
Relatório tem estado queued/processing/completed/failed/archived.
Relatório pertence a workspace.
```

---

## BCORE-1002 — Media Kits

### Objectivo

Criar entidade de media kit.

### Tarefas

```text
Criar modelo MediaKit.
Criar modelo MediaKitItem.
Criar serializers.
Criar viewsets.
Criar Admin.
Criar testes.
```

### Critérios de aceitação

```text
Media kit pertence a artista.
Media kit pode estar draft/generated/published/archived.
Media kit pode incluir itens.
```

---

# 18. Épico 11 — Notifications

## Objectivo

Criar base para notificações in-app e digest futuro.

---

## BCORE-1101 — Notifications base

### Objectivo

Implementar notificações internas.

### Tarefas

```text
Criar app notifications.
Criar modelo Notification.
Campos: workspace, user nullable, notification_type, title, message, related_entity_type, related_entity_id, status, read_at, metadata.
Criar serializer.
Criar viewset.
Criar endpoint mark as read.
Criar Admin.
Criar testes.
```

### Critérios de aceitação

```text
Sistema cria notificação.
Utilizador lista notificações do workspace.
Utilizador marca como lida.
```

---

## BCORE-1102 — Notification Preferences

### Objectivo

Preparar preferências por utilizador.

### Prioridade

P1.

### Tarefas

```text
Criar modelo NotificationPreference.
Criar endpoints.
Criar testes.
```

---

# 19. Épico 12 — Audit logs

## Objectivo

Garantir rastreabilidade de acções críticas.

---

## BCORE-1201 — Audit Events

### Objectivo

Criar auditoria funcional.

### Tarefas

```text
Criar app audit.
Criar modelo AuditEvent.
Campos: workspace nullable, actor_user nullable, actor_type, action, entity_type, entity_id, before_data, after_data, ip_address_hash, user_agent_hash, metadata.
Criar service record_audit_event.
Criar Admin read-only.
Criar testes.
```

### Acções auditáveis iniciais

```text
workspace.created
member.added
member.role_changed
artist.created
track.created
campaign.created
content_pack.requested
smart_link.created
billing.plan_changed
credits.granted
credits.consumed
```

### Critérios de aceitação

```text
Acções críticas geram audit event.
Admin consulta audit events.
Audit event não é editável pelo Admin.
```

---

# 20. Épico 13 — Integrations bridge

## Objectivo

Criar pontos de contrato para FastAPI e serviços técnicos futuros.

---

## BCORE-1301 — Technical Job References

### Objectivo

Permitir que Django acompanhe requests técnicos sem implementar lógica técnica.

### Tarefas

```text
Criar app integrations_bridge.
Criar modelo ExternalJobReference.
Campos: workspace, job_type, provider, external_job_id, related_entity_type, related_entity_id, status, requested_by, requested_at, completed_at, failed_at, error_message, metadata.
Criar service create_external_job_reference.
Criar callback endpoint interno.
Criar testes.
```

### Tipos de job

```text
metrics_collection
moment_detection
content_generation
report_generation
media_kit_generation
video_rendering
```

### Critérios de aceitação

```text
Django cria referência de job externo.
Callback actualiza estado.
Job externo fica associado a entidade de produto.
```

---

## BCORE-1302 — Internal API Auth

### Objectivo

Preparar autenticação para chamadas internas entre Django e FastAPI/renderer.

### Tarefas

```text
Definir INTERNAL_API_TOKEN via .env.
Criar permission para endpoints internos.
Criar header X-Internal-Token.
Criar testes.
```

### Critérios de aceitação

```text
Endpoint interno rejeita chamada sem token.
Endpoint interno aceita chamada com token válido.
```

---

# 21. Épico 14 — APIs, routers e OpenAPI

## Objectivo

Organizar endpoints REST e documentação.

---

## BCORE-1401 — API routing

### Objectivo

Criar estrutura limpa de URLs.

### Tarefas

```text
Criar api/v1/ como prefixo.
Organizar routers por app.
Adicionar endpoints auth.
Adicionar schema OpenAPI.
Adicionar Swagger UI.
Adicionar Redoc, se útil.
```

### Estrutura esperada

```text
/api/v1/auth/
/api/v1/workspaces/
/api/v1/members/
/api/v1/artists/
/api/v1/tracks/
/api/v1/campaigns/
/api/v1/templates/
/api/v1/content-packs/
/api/v1/content-pack-requests/
/api/v1/outputs/
/api/v1/smart-links/
/api/v1/reports/
/api/v1/media-kits/
/api/v1/billing/
/api/v1/notifications/
/api/v1/schema/
/api/v1/docs/
```

### Critérios de aceitação

```text
Endpoints estão versionados.
Swagger abre.
Schema OpenAPI é gerado.
Rotas seguem padrão consistente.
```

---

# 22. Épico 15 — Django Admin / Backoffice

## Objectivo

Garantir operação interna mínima através do Django Admin.

---

## BCORE-1501 — Admin por domínio

### Objectivo

Registar entidades principais no Admin.

### Tarefas

```text
Configurar Admin para User.
Configurar Admin para Workspace.
Configurar Admin para WorkspaceMember.
Configurar Admin para Role e Permission.
Configurar Admin para Artist, Track, Campaign.
Configurar Admin para ContentPack, ContentOutput.
Configurar Admin para SmartLink.
Configurar Admin para Plan, Subscription, UsageEvent, CreditLedger.
Configurar Admin para Reports.
Configurar Admin para AuditEvent read-only.
Adicionar search_fields.
Adicionar list_filter.
Adicionar readonly_fields.
Adicionar ordering.
```

### Critérios de aceitação

```text
Admin permite consultar entidades.
Admin tem filtros úteis.
Audit events são read-only.
Usage e credits são consultáveis.
```

---

# 23. Épico 16 — Testes e qualidade

## Objectivo

Garantir que o backend core não evolui com regressões graves.

---

## BCORE-1601 — Factories

### Objectivo

Criar factories para testes.

### Tarefas

```text
Criar UserFactory.
Criar WorkspaceFactory.
Criar WorkspaceMemberFactory.
Criar ArtistFactory.
Criar TrackFactory.
Criar CampaignFactory.
Criar SmartLinkFactory.
Criar PlanFactory.
Criar SubscriptionFactory.
Criar ContentPackFactory.
```

### Critérios de aceitação

```text
Factories criam dados válidos.
Factories respeitam workspace.
```

---

## BCORE-1602 — Testes de multi-tenancy

### Objectivo

Impedir vazamento de dados entre workspaces.

### Tarefas

```text
Testar artists por workspace.
Testar tracks por workspace.
Testar campaigns por workspace.
Testar smart links por workspace.
Testar outputs por workspace.
Testar billing por workspace.
```

### Critérios de aceitação

```text
Utilizador de workspace A não lê dados do workspace B.
Utilizador de workspace A não altera dados do workspace B.
```

---

## BCORE-1603 — Testes de RBAC

### Objectivo

Garantir permissões.

### Tarefas

```text
Testar viewer.
Testar editor.
Testar manager.
Testar billing_admin.
Testar admin.
Testar owner.
```

### Critérios de aceitação

```text
Cada role só executa acções permitidas.
```

---

## BCORE-1604 — Testes de billing

### Objectivo

Garantir usage, créditos e limites.

### Tarefas

```text
Testar criação de usage event.
Testar idempotência.
Testar grant de créditos.
Testar consumo.
Testar refund.
Testar limite de campanhas.
Testar limite de tracks.
Testar bloqueio sem créditos.
```

---

# 24. Ordem recomendada de implementação

A ordem de execução deve ser:

```text
1. BCORE-001 — Settings base
2. BCORE-002 — Testes e qualidade
3. BCORE-101 — Custom User
4. BCORE-102 — JWT auth
5. BCORE-201 — Workspace
6. BCORE-202 — Workspace Members
7. BCORE-301 — Roles e Permissions
8. BCORE-302 — Permission Guards
9. BCORE-401 — Base Models
10. BCORE-402 — Assets
11. BCORE-501 — Artists
12. BCORE-502 — Tracks
13. BCORE-503 — Track Platform Links
14. BCORE-601 — Campaigns
15. BCORE-602 — Campaign Tracks
16. BCORE-603 — Campaign Goals
17. BCORE-701 — Templates
18. BCORE-702 — Content Packs
19. BCORE-703 — Content Pack Requests
20. BCORE-704 — Content Outputs
21. BCORE-801 — Smart Links
22. BCORE-802 — Smart Link Destinations
23. BCORE-803 — Smart Link Tracking
24. BCORE-901 — Plans
25. BCORE-902 — Subscriptions
26. BCORE-903 — Usage Events
27. BCORE-904 — Credit Ledger
28. BCORE-905 — Quota Enforcement
29. BCORE-906 — Stripe skeleton
30. BCORE-1001 — Reports
31. BCORE-1002 — Media Kits
32. BCORE-1101 — Notifications
33. BCORE-1201 — Audit Events
34. BCORE-1301 — External Job References
35. BCORE-1401 — API routing
36. BCORE-1501 — Django Admin
37. BCORE-1601+ — Testes finais e hardening
```

---

# 25. MVP técnico do Backend Core

O MVP técnico do backend core está pronto quando permitir:

```text
criar utilizador;
autenticar via JWT;
criar workspace;
adicionar membro;
atribuir role;
validar permissões;
criar artista;
criar música;
adicionar link YouTube;
criar campanha;
criar objectivo;
criar content pack request;
criar content output placeholder;
criar smart link;
adicionar destinos;
registar clique;
criar plano;
associar subscription a workspace;
registar usage event;
conceder e consumir créditos;
bloquear acção por limite;
registar audit event;
consultar entidades no Django Admin;
expor OpenAPI.
```

---

# 26. Fora do escopo deste backlog

Não implementar neste backlog:

```text
frontend Next.js;
FastAPI Intelligence Engine;
recolha real de métricas YouTube em produção;
detecção algorítmica avançada de moments;
renderização real de posts;
renderização real de vídeo;
PDF renderer avançado;
Stripe Checkout completo em produção, salvo skeleton;
email provider real;
S3/R2 real completo, salvo modelo/contrato;
API pública B2B completa;
white-label completo;
SSO;
Kubernetes;
CI/CD produção completo.
```

---

# 27. Riscos principais

## 27.1 Misturar Django com motor analítico

### Risco

O backend core começar a implementar regras de metrics/moments que pertencem ao FastAPI.

### Mitigação

```text
Django guarda estado e entidades de produto.
FastAPI calcula e executa.
Criar integrations_bridge para fronteira.
```

---

## 27.2 Multi-tenancy inconsistente

### Risco

Vazamento de dados entre workspaces.

### Mitigação

```text
workspace_id obrigatório;
querysets filtrados;
testes cross-workspace;
permission classes;
audit logs.
```

---

## 27.3 Billing mal acoplado

### Risco

Gerar outputs sem usage event ou consumir créditos em duplicado.

### Mitigação

```text
usage events idempotentes;
credit ledger;
reservation/consume/refund;
testes de billing;
audit logs.
```

---

## 27.4 Models grandes demais no início

### Risco

Criar complexidade excessiva antes de validar produto.

### Mitigação

```text
implementar campos essenciais;
usar metadata JSONB para flexibilidade controlada;
deixar features P1/P2 para depois;
não implementar white-label completo agora.
```

---

## 27.5 Admin sem controlo

### Risco

Admin permitir alterações perigosas sem auditoria.

### Mitigação

```text
AuditEvent read-only;
campos críticos readonly;
acções sensíveis auditadas;
evitar deletes físicos.
```

---

# 28. Definition of Done

Uma tarefa deste backlog só deve ser considerada concluída quando:

```text
models implementados;
migrations criadas;
serializers criados, se aplicável;
viewsets/endpoints criados, se aplicável;
permissions aplicadas;
querysets filtram por workspace;
admin configurado;
testes mínimos implementados;
pytest passa;
ruff passa;
OpenAPI não quebra;
documentação breve actualizada;
não há segredos hardcoded;
não há responsabilidade FastAPI implementada indevidamente no Django.
```

---

# 29. Comandos úteis esperados

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
pytest
coverage run -m pytest
coverage report
ruff check .
python manage.py spectacular --file schema.yml
```

---

# 30. Próximo passo após este backlog

Depois de validar este backlog, o próximo passo deve ser gerar uma pipeline de prompts para IA local implementar o backend core por fases.

Pipeline recomendada:

```text
Pipeline 01 — Configuração base e qualidade
Pipeline 02 — Custom User e autenticação JWT
Pipeline 03 — Workspaces e multi-tenancy
Pipeline 04 — RBAC e permissions
Pipeline 05 — Catálogo musical
Pipeline 06 — Campanhas
Pipeline 07 — Content core
Pipeline 08 — Smart links
Pipeline 09 — Billing, usage e créditos
Pipeline 10 — Reports, media kits e notifications
Pipeline 11 — Audit, admin e integrations bridge
Pipeline 12 — Testes, hardening e documentação
```

O objectivo é evitar um prompt gigante e permitir validação incremental.
