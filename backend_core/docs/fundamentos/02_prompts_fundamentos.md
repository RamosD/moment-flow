# Pipeline: Backend Core Django/DRF — Fundamentos

## Prompt 01 (opus) — Consolidar configuração base e qualidade

```prompt
Objetivo:
Consolidar a fundação técnica do projecto Django existente em backend_core, sem recriar o projecto nem reinstalar Django.

Contexto:
O projecto já existe em D:\Workspace\ChartRex\momentflow\backend_core e já contém manage.py e config/.
As bibliotecas já instaladas incluem Django, djangorestframework, django-filter, drf-spectacular, django-cors-headers, psycopg, pytest, pytest-django, factory-boy, coverage, ruff, djangorestframework-simplejwt, python-decouple e whitenoise.
O backlog de referência obrigatório é: docs\backend_core\fundamentos\01_backlog_backend_core_django.md.
A pasta obrigatória para resultados de execução é: docs\backend_core\fundamentos\resultados.
A regra arquitectural é: Django governa o produto; FastAPI calcula e executa.

Instruções:
- Inspecciona a estrutura actual do projecto.
- Lê o backlog em docs\backend_core\fundamentos\01_backlog_backend_core_django.md antes de alterar ficheiros.
- Não recries o projecto Django.
- Não apagues código existente.
- Consolida config/settings.py para usar python-decouple, DRF, SimpleJWT, django-filter, drf-spectacular, corsheaders e whitenoise.
- Cria ou actualiza .env.example com as variáveis mínimas necessárias.
- Garante que segredos não ficam hardcoded.
- Cria ou actualiza requirements.txt com as dependências instaladas.
- Cria pytest.ini.
- Cria pyproject.toml com configuração mínima para ruff.
- Cria a pasta apps/ com __init__.py, se ainda não existir.
- Cria uma app apps.core com utilitários base mínimos.
- Configura REST_FRAMEWORK com JWTAuthentication, IsAuthenticated por defeito, DjangoFilterBackend, SearchFilter, OrderingFilter e AutoSchema do drf-spectacular.
- Configura SPECTACULAR_SETTINGS com título ChartRex Backend Core API, versão 0.1.0 e descrição curta.
- Configura urls.py com endpoints de schema e documentação OpenAPI.
- Garante que o middleware de CORS fica antes de CommonMiddleware.
- Garante que WhiteNoise está configurado depois de SecurityMiddleware.
- Mantém a configuração simples e funcional para desenvolvimento local.
- No final, cria a pasta docs\backend_core\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\fundamentos\resultados\prompt_01_configuracao_base_qualidade.md.

Restrições:
- Não implementar ainda models de negócio.
- Não implementar ainda autenticação customizada.
- Não implementar ainda apps do domínio.
- Não adicionar dependências novas sem necessidade clara.
- Não configurar Celery, FastAPI, Stripe real ou storage externo nesta fase.

Validações:
- Executa python manage.py check.
- Executa pytest, mesmo que ainda não existam testes relevantes.
- Executa ruff check ., se configurado.
- Se algum comando falhar por causa de configuração do ambiente local, explica a limitação e o que falta.

Conteúdo mínimo do relatório de execução:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- O projecto Django arranca sem erro.
- .env.example existe.
- requirements.txt existe.
- pytest.ini existe.
- pyproject.toml existe.
- DRF, JWT, filtros, CORS, drf-spectacular e WhiteNoise estão configurados.
- /api/v1/schema/ e /api/v1/docs/ ou equivalentes estão disponíveis.
- apps.core existe.
- O relatório de execução foi criado em docs\backend_core\fundamentos\resultados\prompt_01_configuracao_base_qualidade.md.
```

## Prompt 02 (opus) — Implementar Custom User e autenticação JWT

```prompt
Objetivo:
Implementar a app accounts com Custom User baseado em email e autenticação JWT.

Contexto:
Este é o Backend Core Django/DRF do ChartRex. O projecto já foi configurado no prompt anterior.
Django é responsável por autenticação, utilizadores, workspaces, RBAC, billing, catálogo, campanhas, smart links, backoffice e auditoria.
FastAPI não deve ser usado aqui.
O backlog de referência obrigatório é: docs\backend_core\fundamentos\01_backlog_backend_core_django.md.
A pasta obrigatória para resultados de execução é: docs\backend_core\fundamentos\resultados.

Instruções:
- Inspecciona a configuração actual antes de alterar ficheiros.
- Lê o backlog em docs\backend_core\fundamentos\01_backlog_backend_core_django.md antes de alterar ficheiros.
- Cria a app apps.accounts, se ainda não existir.
- Implementa um Custom User com UUID como id, email como USERNAME_FIELD e sem dependência obrigatória de username.
- Campos recomendados: email, full_name, display_name, avatar_url, preferred_language, timezone, email_verified_at, is_active, is_staff, date_joined.
- Cria UserManager com create_user e create_superuser.
- Configura AUTH_USER_MODEL em settings.py.
- Regista o User no Django Admin com list_display, search_fields, list_filter e fieldsets adequados.
- Cria serializers para perfil do utilizador.
- Cria endpoint /api/v1/auth/me/ para obter o utilizador autenticado.
- Cria endpoint para actualizar perfil básico do utilizador autenticado.
- Usa SimpleJWT para token obtain e token refresh.
- Integra as rotas da app accounts em /api/v1/auth/.
- Garante que o schema OpenAPI inclui os endpoints.
- Cria testes para UserManager, criação de superuser, endpoint me autenticado e endpoint me anónimo.
- No final, cria a pasta docs\backend_core\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\fundamentos\resultados\prompt_02_custom_user_auth_jwt.md.

Restrições:
- Não implementar workspaces neste prompt.
- Não implementar password reset ainda, salvo stubs simples se necessário.
- Não usar username como identificador principal.
- Não quebrar a criação de superuser.
- Não implementar lógica de frontend.

Validações:
- Executa python manage.py makemigrations.
- Executa python manage.py migrate.
- Executa python manage.py check.
- Executa pytest.
- Executa ruff check ., se disponível.

Conteúdo mínimo do relatório de execução:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Migrations criadas.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- AUTH_USER_MODEL aponta para accounts.User.
- É possível criar superuser.
- Token JWT pode ser obtido com email/password.
- /api/v1/auth/me/ devolve dados do utilizador autenticado.
- Utilizador anónimo não acede ao endpoint me.
- Testes relevantes passam.
- O relatório de execução foi criado em docs\backend_core\fundamentos\resultados\prompt_02_custom_user_auth_jwt.md.
```

## Prompt 03 (opus) — Implementar Workspaces e multi-tenancy base

```prompt
Objetivo:
Implementar workspaces, membros de workspace e o mecanismo base de multi-tenancy.

Contexto:
ChartRex é uma plataforma SaaS/B2B multi-tenant. Todas as entidades de cliente devem pertencer a um workspace.
O utilizador pode pertencer a vários workspaces.
A resolução do workspace activo deve usar o header X-Workspace-ID.
O backlog de referência obrigatório é: docs\backend_core\fundamentos\01_backlog_backend_core_django.md.
A pasta obrigatória para resultados de execução é: docs\backend_core\fundamentos\resultados.

Instruções:
- Inspecciona a implementação actual de accounts e settings.
- Lê o backlog em docs\backend_core\fundamentos\01_backlog_backend_core_django.md antes de alterar ficheiros.
- Cria a app apps.workspaces, se ainda não existir.
- Implementa o modelo Workspace com UUID, name, slug, workspace_type, country, market, default_language, timezone, status, created_by, timestamps, deleted_at e metadata.
- Tipos de workspace: artist, manager, label, distributor, agency, media, white_label, internal.
- Estados: active, trial, suspended, cancelled, archived.
- Implementa WorkspaceMember com workspace, user, role textual temporário se a app rbac ainda não existir, status, invited_by, joined_at e timestamps.
- Estados de membro: invited, active, suspended, removed.
- Garante unique constraint para workspace + user.
- Cria serializers e viewsets para Workspace e WorkspaceMember.
- Implementa criação de workspace pelo utilizador autenticado.
- Ao criar workspace, o utilizador deve ser automaticamente membro activo com role owner textual temporário.
- Implementa helper, permission ou mixin para resolver o workspace via X-Workspace-ID.
- Implementa validação para bloquear acesso a workspace onde o utilizador não é membro activo.
- Cria endpoints em /api/v1/workspaces/ e /api/v1/workspace-members/ ou estrutura equivalente.
- Regista modelos no Django Admin.
- Cria testes para criação de workspace, membership automático, isolamento entre utilizadores e validação de header X-Workspace-ID.
- No final, cria a pasta docs\backend_core\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\fundamentos\resultados\prompt_03_workspaces_multi_tenancy.md.

Restrições:
- Não implementar RBAC completo ainda.
- Não criar catálogo, campanhas ou billing neste prompt.
- Não assumir workspace global por defeito sem validação.
- Não permitir acesso cross-workspace.
- Não implementar convite por email real ainda.

Validações:
- Executa makemigrations e migrate.
- Executa python manage.py check.
- Executa pytest.
- Executa ruff check ., se disponível.

Conteúdo mínimo do relatório de execução:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Migrations criadas.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Utilizador autenticado cria workspace.
- Criador fica como membro owner activo.
- Utilizador só lista workspaces onde é membro.
- Header X-Workspace-ID inválido ou sem membership é rejeitado nas validações criadas.
- Admin permite consultar workspaces e membros.
- Testes de multi-tenancy base passam.
- O relatório de execução foi criado em docs\backend_core\fundamentos\resultados\prompt_03_workspaces_multi_tenancy.md.
```

## Prompt 04 (opus) — Implementar RBAC e guards de permissões

```prompt
Objetivo:
Implementar a app RBAC com roles, permissions, role_permissions e guards reutilizáveis para APIs multi-tenant.

Contexto:
O Backend Core Django é a autoridade de permissões. Cada utilizador tem uma role por workspace através de WorkspaceMember.
No prompt anterior, WorkspaceMember pode ter role textual temporária. Este prompt deve substituir ou alinhar esse campo com o modelo Role, preservando migrations de forma segura.
O backlog de referência obrigatório é: docs\backend_core\fundamentos\01_backlog_backend_core_django.md.
A pasta obrigatória para resultados de execução é: docs\backend_core\fundamentos\resultados.

Instruções:
- Inspecciona os modelos actuais de workspaces e members.
- Lê o backlog em docs\backend_core\fundamentos\01_backlog_backend_core_django.md antes de alterar ficheiros.
- Cria a app apps.rbac, se ainda não existir.
- Implementa Role com UUID, workspace nullable, key, name, description, is_system, timestamps e metadata.
- Implementa Permission com UUID, key, name, description, domain e timestamps.
- Implementa RolePermission relacionando Role e Permission.
- Ajusta WorkspaceMember para referenciar Role, mantendo compatibilidade com dados existentes se necessário.
- Cria seed command para criar roles e permissions de sistema.
- Roles de sistema: owner, admin, manager, editor, viewer, billing_admin, api_user.
- Permissions base: workspace:manage, members:invite, members:manage, artists:view, artists:create, artists:update, artists:delete, tracks:view, tracks:create, tracks:update, tracks:delete, campaigns:view, campaigns:create, campaigns:update, campaigns:delete, content:view, content:generate, content:export, links:view, links:create, links:update, links:delete, reports:view, reports:generate, billing:view, billing:manage, branding:manage, api_keys:manage.
- Cria serviços user_has_permission, get_user_workspace_role e require_workspace_permission.
- Cria permission classes DRF IsWorkspaceMember e HasWorkspacePermission, ou equivalente reutilizável.
- Actualiza endpoints de workspaces/members para usar permissões adequadas.
- Regista Role, Permission e RolePermission no Admin.
- Cria testes para roles owner, admin, editor, viewer e billing_admin.
- Garante que o seed command é idempotente.
- No final, cria a pasta docs\backend_core\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\fundamentos\resultados\prompt_04_rbac_permissions.md.

Restrições:
- Não implementar ainda catálogo ou campanhas.
- Não hardcodar permissões directamente nas views quando puder usar helpers.
- Não permitir que viewer execute acções de escrita.
- Não permitir gestão de billing por utilizador sem billing:manage.
- Não criar UI.

Validações:
- Executa makemigrations e migrate.
- Executa o seed command de RBAC.
- Executa python manage.py check.
- Executa pytest.
- Executa ruff check ., se disponível.

Conteúdo mínimo do relatório de execução:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Migrations criadas.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Roles e permissions são criadas por comando idempotente.
- WorkspaceMember referencia Role.
- Permissões são verificáveis por workspace.
- Viewer não cria/edita recursos protegidos.
- Owner/Admin gerem membros conforme permissões.
- Testes de RBAC passam.
- O relatório de execução foi criado em docs\backend_core\fundamentos\resultados\prompt_04_rbac_permissions.md.
```

## Prompt 05 (opus) — Implementar core models, assets e padrões transversais

```prompt
Objetivo:
Criar utilitários transversais para modelos, soft delete, timestamps, ownership por workspace, assets, paginação e respostas consistentes.

Contexto:
A plataforma é multi-tenant. Entidades de cliente devem ter workspace_id. Entidades principais devem usar UUID. Outputs, capas, logos, PDFs e imagens devem ser referenciados por uma entidade Asset, mesmo que o storage real ainda seja local ou placeholder.
O backlog de referência obrigatório é: docs\backend_core\fundamentos\01_backlog_backend_core_django.md.
A pasta obrigatória para resultados de execução é: docs\backend_core\fundamentos\resultados.

Instruções:
- Inspecciona apps existentes e padrões já implementados.
- Lê o backlog em docs\backend_core\fundamentos\01_backlog_backend_core_django.md antes de alterar ficheiros.
- Em apps.core, cria modelos abstractos reutilizáveis:
  - UUIDModel;
  - TimeStampedModel;
  - SoftDeleteModel;
  - WorkspaceOwnedModel;
  - CreatedUpdatedByModel, se adequado.
- Implementa managers/querysets para soft delete, se viável sem excesso de complexidade.
- Cria modelo Asset em apps.core com UUID, workspace, asset_type, storage_provider, bucket, storage_key, file_name, mime_type, file_size_bytes, width, height, duration_seconds, checksum, created_by, timestamps, deleted_at e metadata.
- Tipos de asset: artist_photo, cover, logo, template_asset, report_pdf, media_kit_asset, uploaded_image, generated_output, audio_preview, other.
- Cria serializer e viewset básico para Asset com filtro por workspace.
- Aplica IsWorkspaceMember e permissões adequadas.
- Cria paginação padrão no core e configura REST_FRAMEWORK para a usar, se ainda não existir.
- Cria utilitários de respostas/erros apenas se forem claramente úteis e simples.
- Regista Asset no Django Admin.
- Cria testes para Asset e isolamento por workspace.
- Actualiza entidades existentes para reutilizar modelos abstractos apenas se for seguro e sem refactor arriscado. Se não for seguro, documenta a pendência.
- No final, cria a pasta docs\backend_core\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\fundamentos\resultados\prompt_05_core_assets_padroes.md.

Restrições:
- Não alterar drasticamente migrations já criadas sem necessidade.
- Não implementar upload real para S3/R2.
- Não implementar storage externo neste prompt.
- Não criar lógica de renderer.
- Não quebrar accounts, workspaces ou RBAC.

Validações:
- Executa makemigrations e migrate.
- Executa python manage.py check.
- Executa pytest.
- Executa ruff check ., se disponível.

Conteúdo mínimo do relatório de execução:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Migrations criadas.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- apps.core contém modelos abstractos reutilizáveis.
- Asset existe e pertence a workspace.
- API de assets lista apenas assets do workspace.
- Admin permite consultar assets.
- Testes de isolamento passam.
- O relatório de execução foi criado em docs\backend_core\fundamentos\resultados\prompt_05_core_assets_padroes.md.
```

## Prompt 06 (opus) — Implementar catálogo musical

```prompt
Objetivo:
Implementar a app catalogue com artistas, músicas e links de plataforma.

Contexto:
O catálogo musical é a base para campanhas, smart links, content packs, relatórios e futuras métricas. Django é dono do catálogo. A validação técnica profunda de plataformas e recolha de métricas pertencem ao FastAPI, mas o Django deve guardar links e metadata base.
O backlog de referência obrigatório é: docs\backend_core\fundamentos\01_backlog_backend_core_django.md.
A pasta obrigatória para resultados de execução é: docs\backend_core\fundamentos\resultados.

Instruções:
- Inspecciona apps core, workspaces e rbac existentes.
- Lê o backlog em docs\backend_core\fundamentos\01_backlog_backend_core_django.md antes de alterar ficheiros.
- Cria a app apps.catalogue, se ainda não existir.
- Implementa Artist com workspace, name, slug, country, market, primary_genre, language, bio_short, bio_long, image_asset, status, created_by, timestamps, deleted_at e metadata.
- Estados de Artist: active, inactive, archived.
- Implementa Track com workspace, artist, title, slug, release_date, track_type, primary_genre, language, market, cover_asset, status, created_by, timestamps, deleted_at e metadata.
- Tipos de Track: single, music_video, album_track, remix, live, freestyle, other.
- Estados de Track: draft, scheduled, released, monitoring, paused, archived.
- Implementa TrackPlatformLink com workspace, track, platform, external_id, url, canonical_url, status, last_validated_at, validation_error e metadata.
- Plataformas: youtube, spotify, apple_music, deezer, soundcloud, audiomack, boomplay, tiktok, instagram, facebook, custom.
- Estados do link: pending, valid, invalid, private, removed, paused.
- Implementa validação leve para URL YouTube e extracção básica de video_id.
- Garante constraints para impedir artista/música/link de outro workspace.
- Cria serializers, filters e viewsets.
- Aplica permissions por role:
  - artists:view/create/update/delete;
  - tracks:view/create/update/delete.
- Regista modelos no Admin com filtros e pesquisa.
- Cria testes de CRUD, permissões, workspace isolation, slug único por workspace, e validação básica de YouTube.
- No final, cria a pasta docs\backend_core\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\fundamentos\resultados\prompt_06_catalogo_musical.md.

Restrições:
- Não recolher métricas reais.
- Não chamar YouTube API.
- Não implementar labels neste prompt, salvo se já estiver simples e isolado.
- Não implementar campanhas neste prompt.
- Não quebrar RBAC.

Validações:
- Executa makemigrations e migrate.
- Executa python manage.py check.
- Executa pytest.
- Executa ruff check ., se disponível.

Conteúdo mínimo do relatório de execução:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Migrations criadas.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Utilizador cria artista no workspace.
- Utilizador cria música associada a artista do mesmo workspace.
- Utilizador adiciona link YouTube a uma música.
- external_id é extraído quando o link YouTube é reconhecido.
- Dados não cruzam workspaces.
- Permissões são respeitadas.
- Admin permite pesquisar artistas, músicas e links.
- O relatório de execução foi criado em docs\backend_core\fundamentos\resultados\prompt_06_catalogo_musical.md.
```

## Prompt 07 (opus) — Implementar campanhas e objectivos

```prompt
Objetivo:
Implementar a app campaigns com campanhas, campaign tracks e objectivos.

Contexto:
A campanha é a unidade principal de valor do produto. O fluxo central é campanha → dados → moments → insights → content packs → smart links → relatórios.
Django é dono das campanhas e dos objectivos. A lógica analítica pesada fica fora deste backlog.
O backlog de referência obrigatório é: docs\backend_core\fundamentos\01_backlog_backend_core_django.md.
A pasta obrigatória para resultados de execução é: docs\backend_core\fundamentos\resultados.

Instruções:
- Inspecciona a app catalogue existente.
- Lê o backlog em docs\backend_core\fundamentos\01_backlog_backend_core_django.md antes de alterar ficheiros.
- Cria a app apps.campaigns, se ainda não existir.
- Implementa Campaign com workspace, artist, track nullable, name, slug, campaign_type, status, start_date, end_date, primary_goal, description, created_by, timestamps, deleted_at e metadata.
- Tipos de campanha: single_release, music_video_release, album_release, milestone_campaign, comeback_campaign, weekly_growth_campaign, catalogue_push, media_campaign, custom.
- Estados: draft, scheduled, active, paused, completed, archived.
- Implementa CampaignTrack com workspace, campaign, track, role e metadata.
- Roles de CampaignTrack: primary, secondary, reference, catalogue_item.
- Implementa CampaignGoal com workspace, campaign, goal_type, target_value, current_value, unit, deadline, status e metadata.
- Tipos de goal: views, clicks, content_outputs, milestone, reports, engagement, custom.
- Estados de goal: active, achieved, missed, cancelled.
- Cria serializers, filters e viewsets.
- Garante validação de workspace: campanha não pode referenciar artista ou música de outro workspace.
- Garante que CampaignTrack não duplica a mesma música na campanha.
- Aplica permissions campaigns:view/create/update/delete.
- Regista modelos no Admin.
- Cria endpoints adequados para campanhas, campaign tracks e goals.
- Cria testes de CRUD, permissões, workspace isolation, constraints e filtros.
- No final, cria a pasta docs\backend_core\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\fundamentos\resultados\prompt_07_campanhas_objectivos.md.

Restrições:
- Não implementar Campaign War Room completa neste prompt.
- Não implementar metrics, moments ou insights.
- Não implementar smart links neste prompt.
- Não implementar frontend.
- Não criar timeline se isso complicar o escopo; pode ficar como pendência P1.

Validações:
- Executa makemigrations e migrate.
- Executa python manage.py check.
- Executa pytest.
- Executa ruff check ., se disponível.

Conteúdo mínimo do relatório de execução:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Migrations criadas.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Utilizador cria campanha para artista/música do mesmo workspace.
- Campanha suporta estados e tipos definidos.
- Campanha suporta objectivos.
- Campanha pode associar múltiplas músicas via CampaignTrack.
- Não há acesso cross-workspace.
- Permissões de campanha são respeitadas.
- Admin permite pesquisar e filtrar campanhas.
- O relatório de execução foi criado em docs\backend_core\fundamentos\resultados\prompt_07_campanhas_objectivos.md.
```

## Prompt 08 (opus) — Implementar content core, templates, packs e outputs

```prompt
Objetivo:
Implementar a app content com templates, template versions, content packs, content pack requests e content outputs, sem renderização real.

Contexto:
Django governa o catálogo comercial de templates, packs, requests e outputs como entidades de produto. A renderização real de imagens, vídeos, PDFs e carrosséis será feita depois por Content Renderer ou FastAPI.
O objectivo deste prompt é criar a estrutura core que permite pedir geração, acompanhar estados e guardar outputs placeholders.
O backlog de referência obrigatório é: docs\backend_core\fundamentos\01_backlog_backend_core_django.md.
A pasta obrigatória para resultados de execução é: docs\backend_core\fundamentos\resultados.

Instruções:
- Inspecciona apps catalogue, campaigns, billing se existir, e core assets.
- Lê o backlog em docs\backend_core\fundamentos\01_backlog_backend_core_django.md antes de alterar ficheiros.
- Cria a app apps.content, se ainda não existir.
- Implementa Template com workspace nullable, template_key, name, description, template_type, status, is_premium, is_system, created_by, timestamps e metadata.
- Tipos de template: post, story, carousel, carousel_slide, card, thumbnail, report, media_kit, reel, short, widget, embed.
- Estados de template: draft, active, deprecated, archived.
- Implementa TemplateVersion com template, version, renderer_type, manifest, required_props, supported_formats, status, created_by, timestamps e metadata.
- Renderer types: html_svg, satori, sharp, playwright, remotion_still, remotion_video, pdf, html_embed.
- Implementa ContentPack com workspace nullable, pack_key, name, description, pack_type, status, is_premium, timestamps e metadata.
- Pack types: release_pack, milestone_pack, weekly_growth_pack, monthly_recap_pack, comeback_pack, ranking_pack, auto_media_kit, label_reporting_pack.
- Implementa ContentPackTemplate ligando pack a template, output_type, format, required, sort_order e metadata.
- Implementa ContentPackRequest com workspace, campaign, track nullable, artist nullable, content_pack, requested_by, status, requested_at, completed_at, failed_at, error_message, usage_event nullable e metadata.
- Estados de request: draft, queued, processing, partially_completed, completed, failed, cancelled, expired.
- Implementa ContentOutput com workspace, campaign, track nullable, artist nullable, content_pack_request nullable, template, template_version, output_type, format, status, title, caption, cta, storage_asset, public_visibility, created_by, expires_at, usage_event nullable e metadata.
- Estados de output: queued, validating, processing, rendering, uploading, completed, failed, cancelled, expired, archived.
- Visibilidade: private, workspace, public, unlisted.
- Cria serializers, filters e viewsets.
- Aplica permissions content:view, content:generate e content:export.
- Cria seed command para templates e packs iniciais simples:
  - milestone_pack;
  - weekly_growth_pack;
  - release_pack;
  - auto_media_kit.
- Implementa service create_content_pack_request que valida workspace, campaign, pack activo e cria request em queued.
- Implementa output placeholder apenas se fizer sentido. Não renderizar.
- Regista modelos no Admin.
- Cria testes para catálogo de templates, packs, request, output placeholder, permissões e workspace isolation.
- No final, cria a pasta docs\backend_core\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\fundamentos\resultados\prompt_08_content_core_templates_packs_outputs.md.

Restrições:
- Não implementar renderização real.
- Não gerar imagens reais.
- Não chamar FastAPI ainda, salvo interface placeholder clara.
- Não implementar billing profundo neste prompt; se billing ainda não existir, deixar hook/placeholder documentado.
- Não criar editor visual.

Validações:
- Executa makemigrations e migrate.
- Executa seed command criado.
- Executa python manage.py check.
- Executa pytest.
- Executa ruff check ., se disponível.

Conteúdo mínimo do relatório de execução:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Migrations criadas.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Templates e packs são listáveis.
- Template pode ser global ou por workspace.
- ContentPackRequest pode ser criado para uma campanha.
- ContentOutput pode existir como entidade core.
- Permissões são aplicadas.
- Dados ficam isolados por workspace.
- Admin permite gerir templates, packs, requests e outputs.
- O relatório de execução foi criado em docs\backend_core\fundamentos\resultados\prompt_08_content_core_templates_packs_outputs.md.
```

## Prompt 09 (opus) — Implementar Smart Links e tracking básico

```prompt
Objetivo:
Implementar smart links, destinos, página pública/resolução e tracking básico de cliques.

Contexto:
Smart links ligam conteúdos, campanhas e medição de impacto. Django é dono funcional de smart links, destinos e tracking base.
O backlog de referência obrigatório é: docs\backend_core\fundamentos\01_backlog_backend_core_django.md.
A pasta obrigatória para resultados de execução é: docs\backend_core\fundamentos\resultados.

Instruções:
- Inspecciona apps campaigns, catalogue e content.
- Lê o backlog em docs\backend_core\fundamentos\01_backlog_backend_core_django.md antes de alterar ficheiros.
- Cria a app apps.links, se ainda não existir.
- Implementa SmartLink com workspace, campaign, track nullable, artist nullable, slug, title, description, status, branding_enabled, created_by, timestamps, deleted_at e metadata.
- Estados: draft, active, paused, expired, archived.
- Implementa SmartLinkDestination com workspace, smart_link, platform, label, url, sort_order, is_active, timestamps e metadata.
- Plataformas: youtube, spotify, apple_music, deezer, audiomack, soundcloud, boomplay, instagram, tiktok, website, custom.
- Implementa SmartLinkClick com workspace, smart_link, destination nullable, content_output nullable, campaign, track nullable, clicked_at, referrer, utm_source, utm_medium, utm_campaign, utm_content, country, device_type, browser, ip_hash, user_agent_hash e metadata.
- Cria serializers, filters e viewsets para SmartLink e destinos.
- Cria endpoint público para resolver smart link por slug.
- O endpoint público deve registar clique e redireccionar para o destino escolhido ou devolver dados para uma página pública, conforme padrão existente do projecto.
- Se houver múltiplos destinos e não existir escolha explícita, devolver payload com destinos activos em vez de escolher arbitrariamente.
- Cria endpoint de estatísticas simples por smart link: total de cliques, cliques por destino e cliques por dia.
- Permite associar content_output_id nos cliques quando fornecido por query param ou UTM metadata.
- Aplica permissions links:view/create/update/delete.
- Regista modelos no Admin.
- Cria testes para criação, destinos, tracking, link pausado, workspace isolation e estatísticas.
- No final, cria a pasta docs\backend_core\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\fundamentos\resultados\prompt_09_smart_links_tracking.md.

Restrições:
- Não implementar frontend público completo.
- Não implementar analytics avançado.
- Não guardar IP em claro; usar hash ou campo vazio quando não houver estratégia segura.
- Não implementar retargeting, pixels ou cookies avançados.
- Não implementar domínio customizado ainda.

Validações:
- Executa makemigrations e migrate.
- Executa python manage.py check.
- Executa pytest.
- Executa ruff check ., se disponível.

Conteúdo mínimo do relatório de execução:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Migrations criadas.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Utilizador cria smart link associado a campanha.
- Smart link tem múltiplos destinos.
- Link activo pode ser resolvido publicamente.
- Clique é registado.
- Link pausado não redirecciona normalmente.
- Estatísticas básicas são consultáveis.
- Dados respeitam workspace.
- O relatório de execução foi criado em docs\backend_core\fundamentos\resultados\prompt_09_smart_links_tracking.md.
```

## Prompt 10 (opus) — Implementar billing, planos, usage e créditos

```prompt
Objetivo:
Implementar a fundação de billing: planos, features, subscrições, usage events, credit ledger, quotas e skeleton de Stripe.

Contexto:
Billing é responsabilidade principal do Django. O produto deve medir uso desde cedo e controlar limites por workspace.
Não é necessário ter Stripe completo em produção, mas deve existir estrutura segura e idempotente.
O backlog de referência obrigatório é: docs\backend_core\fundamentos\01_backlog_backend_core_django.md.
A pasta obrigatória para resultados de execução é: docs\backend_core\fundamentos\resultados.

Instruções:
- Inspecciona apps workspaces, rbac, content, campaigns e links.
- Lê o backlog em docs\backend_core\fundamentos\01_backlog_backend_core_django.md antes de alterar ficheiros.
- Cria a app apps.billing, se ainda não existir.
- Implementa Plan com plan_key, name, description, billing_interval, base_price, currency, status, is_public, timestamps e metadata.
- Implementa PlanFeature com plan, feature_key, limit_value, limit_unit, is_enabled, timestamps e metadata.
- Implementa Subscription com workspace, plan, provider, provider_subscription_id, status, current_period_start, current_period_end, trial_start, trial_end, cancel_at_period_end, timestamps e metadata.
- Estados de Subscription: trialing, active, past_due, cancelled, unpaid, paused, enterprise_manual.
- Implementa UsageEvent com workspace, event_type, quantity, unit, related_entity_type, related_entity_id, cost_units, billing_period, idempotency_key, created_at e metadata.
- Implementa CreditLedgerEntry com workspace, transaction_type, amount, balance_after, reason, related_entity_type, related_entity_id, idempotency_key, created_at e metadata.
- Tipos de transacção: grant, reserve, consume, release, refund, adjustment, expiration, purchase.
- Implementa serviços:
  - get_active_subscription;
  - workspace_has_feature;
  - get_plan_limit;
  - record_usage_event com idempotência;
  - get_credit_balance;
  - grant_credits;
  - reserve_credits;
  - consume_credits;
  - release_reserved_credits;
  - refund_credits;
  - check_workspace_limit.
- Cria seed command para planos iniciais: trial, artist_starter, artist_growth, manager, label_agency, white_label, enterprise.
- Define features iniciais: artists_limit, tracks_limit, campaigns_limit, content_packs_per_month, smart_links_limit, reports_per_month, storage_gb, watermark_removal, custom_branding.
- Integra validação simples de quotas em fluxos já existentes quando seguro:
  - criar artista;
  - criar track;
  - criar campanha;
  - criar smart link;
  - criar content pack request.
- Implementa BillingWebhookEvent para skeleton Stripe com provider, provider_event_id, event_type, status, received_at, processed_at, payload, error_message e metadata.
- Cria endpoint de webhook Stripe protegido por assinatura se STRIPE_WEBHOOK_SECRET existir. Caso contrário, preparar estrutura e documentar limitação.
- Garante idempotência por provider_event_id.
- Cria endpoints/API para consultar plano activo, uso do período e saldo de créditos do workspace.
- Regista modelos no Admin.
- Cria testes de planos, subscriptions, usage idempotente, créditos, quotas e webhook duplicado.
- No final, cria a pasta docs\backend_core\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\fundamentos\resultados\prompt_10_billing_usage_creditos.md.

Restrições:
- Não implementar checkout completo se não houver configuração Stripe real.
- Não guardar segredos Stripe no código.
- Não cobrar duas vezes em caso de retry.
- Não bloquear fluxos existentes sem mensagens claras.
- Não implementar overage automático.

Validações:
- Executa makemigrations e migrate.
- Executa seed command de planos.
- Executa python manage.py check.
- Executa pytest.
- Executa ruff check ., se disponível.

Conteúdo mínimo do relatório de execução:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Migrations criadas.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Planos e features são criados por seed.
- Workspace pode ter subscription.
- Usage event é idempotente.
- Créditos podem ser concedidos, reservados, consumidos, libertados e reembolsados.
- Limites bloqueiam criação quando excedidos.
- Content pack request valida créditos ou deixa pendência clara se integração ainda estiver parcial.
- Webhook Stripe duplicado não é reprocessado.
- Admin permite consultar billing.
- O relatório de execução foi criado em docs\backend_core\fundamentos\resultados\prompt_10_billing_usage_creditos.md.
```

## Prompt 11 (opus) — Implementar reports, media kits e notifications base

```prompt
Objetivo:
Implementar entidades core para relatórios, media kits e notificações internas, sem renderer avançado.

Contexto:
Relatórios e media kits são críticos para o valor B2B. Django é dono dos pedidos, estados, histórico e permissões. A geração real de PDF/ZIP pode ser feita futuramente por renderer/worker.
O backlog de referência obrigatório é: docs\backend_core\fundamentos\01_backlog_backend_core_django.md.
A pasta obrigatória para resultados de execução é: docs\backend_core\fundamentos\resultados.

Instruções:
- Inspecciona apps campaigns, catalogue, content, links e billing.
- Lê o backlog em docs\backend_core\fundamentos\01_backlog_backend_core_django.md antes de alterar ficheiros.
- Cria a app apps.reports, se ainda não existir.
- Implementa Report com workspace, campaign nullable, artist nullable, track nullable, report_type, title, period_start, period_end, status, requested_by, storage_asset nullable, timestamps e metadata.
- Tipos de report: weekly_report, monthly_report, campaign_report, artist_report, track_report, label_report, catalogue_report.
- Estados: queued, processing, completed, failed, archived.
- Implementa ReportSection com workspace, report, section_key, title, sort_order, content_json, timestamps e metadata.
- Implementa MediaKit com workspace, artist, campaign nullable, track nullable, title, status, public_visibility, storage_asset nullable, created_by, timestamps e metadata.
- Estados de MediaKit: draft, generated, published, archived.
- Implementa MediaKitItem com workspace, media_kit, item_type, title, content, asset nullable, sort_order, timestamps e metadata.
- Cria serializers, filters e viewsets.
- Aplica permissions reports:view e reports:generate.
- Quando um report ou media kit for criado, regista usage event se a app billing já estiver implementada.
- Cria a app apps.notifications, se ainda não existir.
- Implementa Notification com workspace, user nullable, notification_type, title, message, related_entity_type, related_entity_id, status, read_at, timestamps e metadata.
- Estados de Notification: unread, read, dismissed, archived.
- Cria endpoint para listar notificações e marcar como lida.
- Regista tudo no Admin.
- Cria testes de criação, permissões, workspace isolation e usage event quando aplicável.
- No final, cria a pasta docs\backend_core\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\fundamentos\resultados\prompt_11_reports_media_kits_notifications.md.

Restrições:
- Não gerar PDF real.
- Não enviar email real.
- Não implementar digest.
- Não implementar página pública completa de media kit.
- Não implementar renderer.

Validações:
- Executa makemigrations e migrate.
- Executa python manage.py check.
- Executa pytest.
- Executa ruff check ., se disponível.

Conteúdo mínimo do relatório de execução:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Migrations criadas.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Utilizador cria pedido de relatório.
- Relatório tem secções.
- Utilizador cria media kit para artista.
- Media kit tem itens.
- Notificações podem ser criadas, listadas e marcadas como lidas.
- Permissões são respeitadas.
- Dados ficam isolados por workspace.
- Admin permite consultar reports, media kits e notifications.
- O relatório de execução foi criado em docs\backend_core\fundamentos\resultados\prompt_11_reports_media_kits_notifications.md.
```

## Prompt 12 (opus) — Implementar audit logs e integrations bridge

```prompt
Objetivo:
Implementar auditoria funcional e uma ponte de integração para jobs externos futuros com FastAPI/renderer.

Contexto:
Django deve manter rastreabilidade de acções críticas e acompanhar pedidos técnicos externos sem executar lógica pesada.
FastAPI/Renderer serão responsáveis por métricas, moments, insights e renderização real.
O backlog de referência obrigatório é: docs\backend_core\fundamentos\01_backlog_backend_core_django.md.
A pasta obrigatória para resultados de execução é: docs\backend_core\fundamentos\resultados.

Instruções:
- Inspecciona apps existentes e eventos críticos já implementados.
- Lê o backlog em docs\backend_core\fundamentos\01_backlog_backend_core_django.md antes de alterar ficheiros.
- Cria a app apps.audit, se ainda não existir.
- Implementa AuditEvent com workspace nullable, actor_user nullable, actor_type, action, entity_type, entity_id, before_data, after_data, ip_address_hash, user_agent_hash, created_at e metadata.
- Actor types: user, system, admin, api_key, worker.
- Cria service record_audit_event.
- Integra audit logs em acções críticas de forma simples e sem excesso:
  - workspace.created;
  - member.added;
  - member.role_changed;
  - artist.created;
  - track.created;
  - campaign.created;
  - content_pack.requested;
  - smart_link.created;
  - billing.plan_changed quando aplicável;
  - credits.granted;
  - credits.consumed.
- Regista AuditEvent no Admin como read-only.
- Cria a app apps.integrations_bridge, se ainda não existir.
- Implementa ExternalJobReference com workspace nullable, job_type, provider, external_job_id, related_entity_type, related_entity_id, status, requested_by, requested_at, completed_at, failed_at, error_message e metadata.
- Tipos de job: metrics_collection, moment_detection, content_generation, report_generation, media_kit_generation, video_rendering.
- Estados: queued, running, completed, failed, cancelled.
- Cria service create_external_job_reference.
- Cria endpoint interno para callback de job externo.
- Implementa autenticação simples para endpoint interno usando header X-Internal-Token e variável INTERNAL_API_TOKEN.
- Cria testes para audit service, admin read-only, criação de external job reference e callback com/sem token.
- No final, cria a pasta docs\backend_core\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\fundamentos\resultados\prompt_12_audit_integrations_bridge.md.

Restrições:
- Não implementar FastAPI.
- Não chamar serviços externos reais.
- Não implementar Celery neste prompt.
- Não guardar IP em claro; usar hash ou vazio.
- Não tornar audit events editáveis no Admin.

Validações:
- Executa makemigrations e migrate.
- Executa python manage.py check.
- Executa pytest.
- Executa ruff check ., se disponível.

Conteúdo mínimo do relatório de execução:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Migrations criadas.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- AuditEvent existe e é registado em acções críticas seleccionadas.
- AuditEvent é read-only no Admin.
- ExternalJobReference permite acompanhar jobs técnicos futuros.
- Callback interno actualiza estado apenas com token válido.
- Testes relevantes passam.
- O relatório de execução foi criado em docs\backend_core\fundamentos\resultados\prompt_12_audit_integrations_bridge.md.
```

## Prompt 13 (sonnet) — Organizar API routing, OpenAPI e Admin

```prompt
Objetivo:
Rever e consolidar o routing da API v1, documentação OpenAPI e configuração do Django Admin para todas as apps implementadas.

Contexto:
Após implementar as apps principais, o backend deve expor endpoints consistentes em /api/v1/ e documentação OpenAPI. O Django Admin é o backoffice inicial da plataforma.
O backlog de referência obrigatório é: docs\backend_core\fundamentos\01_backlog_backend_core_django.md.
A pasta obrigatória para resultados de execução é: docs\backend_core\fundamentos\resultados.

Instruções:
- Inspecciona config/urls.py e urls das apps.
- Lê o backlog em docs\backend_core\fundamentos\01_backlog_backend_core_django.md antes de alterar ficheiros.
- Garante que os endpoints estão versionados sob /api/v1/.
- Garante rotas ou routers para:
  - auth;
  - workspaces;
  - workspace members;
  - artists;
  - tracks;
  - track platform links;
  - campaigns;
  - campaign goals;
  - templates;
  - content packs;
  - content pack requests;
  - outputs;
  - smart links;
  - reports;
  - media kits;
  - billing;
  - notifications;
  - integrations bridge, apenas endpoints internos;
  - schema e docs.
- Garante que cada ViewSet tem serializer, queryset filtrado por workspace quando aplicável, permissions adequadas e filtros úteis.
- Revê Admin de todas as entidades principais.
- Adiciona list_display, search_fields, list_filter, readonly_fields e ordering onde útil.
- Garante que AuditEvent é read-only.
- Garante que entidades sensíveis de billing têm campos críticos readonly quando apropriado.
- Garante que OpenAPI não quebra por serializers ou endpoints mal definidos.
- Não alterar regras de negócio sem necessidade.
- Corrige inconsistências simples detectadas no routing ou Admin.
- No final, cria a pasta docs\backend_core\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\fundamentos\resultados\prompt_13_api_routing_openapi_admin.md.

Restrições:
- Não criar novas features de domínio.
- Não alterar models sem necessidade real.
- Não implementar frontend.
- Não transformar endpoints internos em públicos.
- Não expor segredos ou tokens no schema.

Validações:
- Executa python manage.py check.
- Executa python manage.py spectacular --file schema.yml, se o comando estiver disponível.
- Executa pytest.
- Executa ruff check ., se disponível.

Conteúdo mínimo do relatório de execução:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Comandos executados.
- Resultado das validações.
- Problemas corrigidos.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- API v1 está organizada.
- Swagger/OpenAPI abre sem erro.
- Admin permite operar entidades principais.
- AuditEvent é read-only.
- Endpoints sensíveis têm permissões.
- O relatório de execução foi criado em docs\backend_core\fundamentos\resultados\prompt_13_api_routing_openapi_admin.md.
```

## Prompt 14 (sonnet) — Criar factories e testes de regressão críticos

```prompt
Objetivo:
Criar factories e reforçar testes críticos de multi-tenancy, RBAC, billing, content requests e smart links.

Contexto:
O backend core já deve ter as apps principais implementadas. Agora é necessário reduzir risco de regressão antes de avançar para integração com FastAPI/renderer ou frontend.
O backlog de referência obrigatório é: docs\backend_core\fundamentos\01_backlog_backend_core_django.md.
A pasta obrigatória para resultados de execução é: docs\backend_core\fundamentos\resultados.

Instruções:
- Inspecciona a estrutura de testes existente.
- Lê o backlog em docs\backend_core\fundamentos\01_backlog_backend_core_django.md antes de alterar ficheiros.
- Cria ou actualiza tests/conftest.py.
- Cria factories com factory-boy para:
  - User;
  - Workspace;
  - Role;
  - Permission;
  - WorkspaceMember;
  - Asset;
  - Artist;
  - Track;
  - TrackPlatformLink;
  - Campaign;
  - CampaignGoal;
  - Template;
  - TemplateVersion;
  - ContentPack;
  - ContentPackRequest;
  - ContentOutput;
  - SmartLink;
  - SmartLinkDestination;
  - Plan;
  - Subscription;
  - UsageEvent;
  - CreditLedgerEntry;
  - Report;
  - MediaKit.
- Cria testes de multi-tenancy para garantir que utilizador do workspace A não lê nem altera dados do workspace B.
- Cria testes de RBAC para viewer, editor, admin, owner e billing_admin.
- Cria testes de billing:
  - usage event idempotente;
  - grant de créditos;
  - reserve/consume;
  - refund;
  - bloqueio por falta de créditos;
  - limite de campanhas ou tracks.
- Cria testes de smart links:
  - criação;
  - destinos;
  - clique registado;
  - link pausado.
- Cria testes de content pack request:
  - criação válida;
  - bloqueio sem permissão;
  - bloqueio por workspace inválido.
- Mantém testes objectivos e rápidos.
- Corrige bugs encontrados que estejam directamente ligados aos testes criados.
- No final, cria a pasta docs\backend_core\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\fundamentos\resultados\prompt_14_factories_testes_regressao.md.

Restrições:
- Não implementar features novas fora dos testes e correcções necessárias.
- Não alterar contratos de API sem necessidade.
- Não remover testes existentes.
- Não relaxar permissões para fazer testes passar.

Validações:
- Executa pytest.
- Executa coverage run -m pytest e coverage report, se coverage estiver configurado.
- Executa ruff check ., se disponível.
- Executa python manage.py check.

Conteúdo mínimo do relatório de execução:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Comandos executados.
- Resultado das validações.
- Bugs encontrados.
- Correcções feitas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Factories principais existem.
- Testes críticos de multi-tenancy passam.
- Testes críticos de RBAC passam.
- Testes críticos de billing passam.
- Testes de smart links e content pack requests passam.
- Bugs relacionados foram corrigidos.
- O relatório de execução foi criado em docs\backend_core\fundamentos\resultados\prompt_14_factories_testes_regressao.md.
```

## Prompt 15 (sonnet) — Hardening final e documentação técnica do backend core

```prompt
Objetivo:
Fazer hardening final do Backend Core Django/DRF e criar documentação técnica mínima para desenvolvimento e operação local.

Contexto:
As apps principais do backend core já devem estar implementadas. Antes de avançar para frontend, FastAPI Intelligence Engine ou Content Renderer, o backend deve estar consistente, testado e documentado.
O backlog de referência obrigatório é: docs\backend_core\fundamentos\01_backlog_backend_core_django.md.
A pasta obrigatória para resultados de execução é: docs\backend_core\fundamentos\resultados.

Instruções:
- Revê a estrutura do projecto e identifica inconsistências óbvias.
- Lê o backlog em docs\backend_core\fundamentos\01_backlog_backend_core_django.md antes de alterar ficheiros.
- Confirma que settings, apps, URLs, Admin, permissions, serializers e tests seguem padrões consistentes.
- Verifica se todas as entidades tenant-aware filtram por workspace.
- Verifica se endpoints sensíveis exigem autenticação e permissões.
- Verifica se models principais usam UUID, timestamps e workspace quando aplicável.
- Verifica se usage events e audit logs estão ligados aos fluxos críticos implementados.
- Verifica se o schema OpenAPI é gerado sem erro.
- Cria ou actualiza README.md do backend_core com:
  - visão curta do backend;
  - requisitos;
  - configuração de .env;
  - comandos de instalação;
  - comandos de migrations;
  - comandos de runserver;
  - comandos de testes;
  - comandos de ruff;
  - comandos de OpenAPI;
  - seed commands existentes;
  - notas sobre fronteira Django vs FastAPI.
- Cria ou actualiza docs\backend_core\fundamentos\02_estado_implementacao_backend_core.md com:
  - funcionalidades implementadas;
  - endpoints principais;
  - apps criadas;
  - validações executadas;
  - pendências;
  - riscos;
  - próximo passo recomendado.
- Corrige apenas problemas pequenos e directamente relacionados com hardening.
- No final, cria a pasta docs\backend_core\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\fundamentos\resultados\prompt_15_hardening_documentacao.md.

Restrições:
- Não implementar novas features.
- Não alterar arquitectura acordada.
- Não mover responsabilidades analíticas para Django.
- Não apagar migrations existentes.
- Não introduzir dependências novas sem necessidade.
- Não fazer refactors grandes.

Validações:
- Executa python manage.py check.
- Executa python manage.py makemigrations --check, se aplicável.
- Executa python manage.py spectacular --file schema.yml, se disponível.
- Executa pytest.
- Executa ruff check ., se disponível.

Conteúdo mínimo do relatório de execução:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Comandos executados.
- Resultado das validações.
- Inconsistências encontradas.
- Correcções feitas.
- Pendências.
- Riscos.
- Próximo passo recomendado.

Critérios de aceitação:
- README.md do backend_core existe e é útil.
- docs\backend_core\fundamentos\02_estado_implementacao_backend_core.md existe.
- Checks principais foram executados ou limitações foram explicadas.
- Inconsistências pequenas foram corrigidas.
- Pendências estão documentadas.
- O relatório de execução foi criado em docs\backend_core\fundamentos\resultados\prompt_15_hardening_documentacao.md.
```
