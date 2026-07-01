# Pipeline: Frontend Foundation & Campaign War Room MVP

## Prompt 01 (opus) — Analisar setup, contratos e arquitectura alvo

```prompt
Objectivo:
Inspeccionar o projecto frontend, o Backend Core e os contratos necessários para preparar uma implementação segura da fase Frontend Foundation & Campaign War Room MVP.

Contexto obrigatório:
- Componente alvo: frontend
- Backlog da fase: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados
- O frontend já existe e foi criado com React, Vite, TypeScript, ESLint e pnpm.
- O Backend Core é a única API que o frontend deve consumir.
- O frontend não deve chamar directamente:
  - intelligence_engine
  - content_renderer
- O frontend nunca deve conter nem enviar X-Internal-Token.

Instruções:
- Lê o backlog completo antes de alterar ficheiros.
- Inspecciona frontend/package.json.
- Inspecciona a estrutura actual do frontend/src.
- Inspecciona tsconfig, vite config, eslint config e ficheiros de entrada.
- Confirma se os scripts existem e funcionam ou estão preparados:
  - pnpm dev
  - pnpm build
  - pnpm lint
- Inspecciona a documentação disponível do Backend Core.
- Inspecciona o schema OpenAPI do Backend Core se estiver disponível no repositório.
- Confirma as rotas reais ou prováveis de:
  - auth;
  - token refresh;
  - workspaces;
  - campaigns;
  - campaign detail;
  - campaign intelligence;
  - health dependencies.
- Confirma o formato esperado do endpoint:
  POST /api/v1/campaigns/{id}/intelligence/
- Confirma requisitos de headers:
  - Authorization: Bearer <access_token>
  - X-Workspace-ID: <workspace_id>
  - Content-Type: application/json
- Confirma que X-Internal-Token é segredo interno e nunca deve existir no frontend.
- Identifica lacunas de contrato.
- Identifica dependências a instalar, mas não instales ainda.
- Identifica riscos:
  - acoplamento directo ao IE/Renderer;
  - auth incompleto;
  - workspace mal modelado;
  - contratos incertos;
  - estrutura frontend fraca;
  - dependências incompatíveis com React/Vite/TypeScript actuais.
- Define plano técnico dos prompts seguintes.
- Não alterar runtime neste prompt, salvo criação do relatório.
- Cria o relatório em:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_01_analise_setup_contratos_arquitectura.md

Critérios de aceitação:
- Relatório de análise criado.
- Estrutura actual do frontend documentada.
- Rotas reais confirmadas ou marcadas como pendentes.
- Contratos críticos identificados.
- Dependências recomendadas listadas.
- Riscos registados.
- Plano de execução definido.
- Nenhum runtime alterado sem necessidade.
```

## Prompt 02 (opus) — Criar foundation estrutural do frontend

```prompt
Objectivo:
Criar a estrutura modular e escalável do frontend, preparando o projecto para crescer por camadas, entidades, features, widgets e pages.

Contexto obrigatório:
- Componente alvo: frontend
- Backlog da fase: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados
- Relatório anterior:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_01_analise_setup_contratos_arquitectura.md

Instruções:
- Lê o backlog e o relatório do Prompt 01.
- Cria uma estrutura modular em src, alinhada com a arquitectura alvo.
- Estrutura sugerida:
  src/app
  src/app/providers
  src/app/router
  src/app/layouts
  src/app/config
  src/shared
  src/shared/api
  src/shared/ui
  src/shared/lib
  src/shared/hooks
  src/shared/types
  src/shared/constants
  src/shared/styles
  src/entities
  src/entities/campaign
  src/entities/artist
  src/entities/track
  src/entities/workspace
  src/entities/user
  src/entities/content-output
  src/entities/report
  src/entities/media-kit
  src/features
  src/features/auth
  src/features/workspace-switching
  src/features/campaign-intelligence
  src/features/campaign-actions
  src/features/asset-generation-status
  src/features/report-status
  src/widgets
  src/widgets/app-shell
  src/widgets/campaign-header
  src/widgets/campaign-score-card
  src/widgets/campaign-recommendations-panel
  src/widgets/campaign-moments-panel
  src/widgets/campaign-assets-panel
  src/widgets/campaign-reports-panel
  src/pages
  src/pages/dashboard
  src/pages/campaigns
  src/pages/campaign-detail
  src/pages/campaign-war-room
  src/pages/not-found
- Criar ficheiros index.ts apenas onde ajudam a manter imports limpos.
- Criar App root limpo.
- Criar estilos globais base.
- Criar design tokens mínimos:
  - spacing;
  - radius;
  - colors;
  - typography;
  - shadows.
- Configurar aliases de import se fizer sentido e se não complicar a configuração.
- Se configurar aliases, actualizar TypeScript e Vite de forma consistente.
- Não instalar dependências ainda, salvo se estritamente necessário.
- Não implementar War Room ainda.
- Não criar uma pasta src/components gigante.
- Garantir que pnpm build passa.
- Garantir que pnpm lint passa ou documentar limitação.
- Criar documentação curta da estrutura, se fizer sentido.
- Cria o relatório em:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_02_foundation_estrutural_frontend.md

Critérios de aceitação:
- Estrutura modular existe.
- App arranca/renderiza sem erro.
- Build passa.
- Lint passa ou limitação fica documentada.
- Não há imports circulares óbvios.
- Não há src/components gigante.
- Arquitectura inicial está documentada no relatório.
```

## Prompt 03 (opus) — Configurar API client e ambiente

```prompt
Objectivo:
Criar a camada central de comunicação com o Backend Core, com configuração por ambiente, headers controlados, normalização de erros e proibição explícita de segredos internos no frontend.

Contexto obrigatório:
- Componente alvo: frontend
- Backlog da fase: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados
- O frontend deve chamar apenas o Backend Core.
- O frontend nunca deve usar X-Internal-Token.
- Base URL esperada:
  VITE_BACKEND_API_BASE_URL

Instruções:
- Lê o backlog e relatórios anteriores.
- Criar leitura de configuração em src/app/config ou src/shared/config, conforme a estrutura criada.
- Criar suporte a:
  VITE_BACKEND_API_BASE_URL
- Criar validação simples de configuração:
  - base URL ausente;
  - base URL inválida;
  - fallback dev, se fizer sentido.
- Criar API client central em src/shared/api.
- Implementar helpers:
  - get;
  - post;
  - patch;
  - delete, se necessário.
- Suportar Authorization Bearer token através de função/provider injectável, não hardcoded.
- Suportar X-Workspace-ID através de função/provider injectável, não hardcoded.
- Garantir que Content-Type application/json é enviado quando aplicável.
- Garantir que X-Internal-Token nunca é enviado.
- Criar normalização de erros HTTP:
  - ApiError;
  - UnauthorizedError;
  - ForbiddenError;
  - NotFoundError;
  - ValidationError;
  - ServiceUnavailableError;
  - NetworkError.
- Tratar 401, 403, 404, 422, 500, 502, 503 e network error.
- Não logar tokens.
- Criar tipos base para responses paginadas, se o Backend Core usa paginação.
- Criar testes se já houver framework de testes.
- Se não houver framework de testes, documentar limitação.
- Garantir build/lint.
- Cria o relatório em:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_03_api_client_ambiente.md

Critérios de aceitação:
- API client central existe.
- Base URL vem de env.
- Authorization header é suportado.
- X-Workspace-ID é suportado.
- X-Internal-Token não existe no frontend.
- Erros HTTP são normalizados.
- Build passa.
- Lint passa ou limitação documentada.
- Relatório lista ficheiros alterados, decisões e limitações.
```

## Prompt 04 (opus) — Configurar routing, query client e providers

```prompt
Objectivo:
Instalar e configurar routing, server state e providers globais da aplicação.

Contexto obrigatório:
- Componente alvo: frontend
- Backlog da fase: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados
- API client já criado no Prompt 03.

Instruções:
- Lê o backlog e relatórios anteriores.
- Confirmar compatibilidade das versões antes de instalar dependências.
- Instalar:
  - react-router-dom
  - @tanstack/react-query
- Criar AppProviders.
- Criar QueryClient com defaults adequados:
  - retry conservador;
  - staleTime razoável;
  - tratamento de erro sem logs sensíveis.
- Criar router em src/app/router.
- Criar layout principal inicial.
- Criar rotas:
  - /
  - /campaigns
  - /campaigns/:campaignId
  - /campaigns/:campaignId/war-room
  - /settings
  - *
- Criar páginas placeholder se ainda não existirem.
- Criar AuthProvider inicial.
- Criar WorkspaceProvider inicial.
- Criar hooks:
  - useAuth;
  - useWorkspace.
- Se fizer sentido, criar ApiProvider ou ligar API client aos providers.
- Garantir que as rotas renderizam.
- Garantir que build/lint passam.
- Não implementar fluxo completo de auth ainda.
- Não implementar War Room real ainda.
- Cria o relatório em:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_04_routing_query_providers.md

Critérios de aceitação:
- react-router-dom instalado e configurado.
- @tanstack/react-query instalado e configurado.
- AppProviders existe.
- Routing funciona.
- QueryClientProvider configurado.
- AuthProvider inicial existe.
- WorkspaceProvider inicial existe.
- Rotas básicas renderizam.
- Build/lint passam ou limitações ficam documentadas.
```

## Prompt 05 (opus) — Criar UI foundation e estados transversais

```prompt
Objectivo:
Criar componentes UI base e estados transversais reutilizáveis para suportar o MVP sem criar um design system pesado.

Contexto obrigatório:
- Componente alvo: frontend
- Backlog da fase: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados
- Estrutura modular e providers já criados.

Instruções:
- Lê o backlog e relatórios anteriores.
- Criar componentes em src/shared/ui.
- Componentes mínimos:
  - Button;
  - Card;
  - Badge;
  - Alert;
  - PageHeader;
  - Section;
  - LoadingState;
  - EmptyState;
  - ErrorState;
  - Skeleton;
  - Tabs ou Nav simples, se necessário.
- Criar estilos consistentes usando a abordagem escolhida no Prompt 02.
- Criar variantes simples:
  - primary;
  - secondary;
  - ghost;
  - danger;
  - success;
  - warning;
  - neutral.
- Criar padrões de erro:
  - erro de rede;
  - erro 401;
  - erro 403;
  - erro 404;
  - serviço indisponível;
  - estado vazio.
- Evitar dependências visuais pesadas.
- Não introduzir UI framework grande sem aprovação explícita.
- Criar uma página ou área de validação simples usando os componentes, se útil.
- Garantir acessibilidade básica:
  - botões com type;
  - estados disabled;
  - labels quando aplicável;
  - contraste razoável.
- Garantir build/lint.
- Cria o relatório em:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_05_ui_foundation_estados.md

Critérios de aceitação:
- Componentes UI base existem.
- Estados loading/error/empty existem.
- Componentes são reutilizáveis.
- Não há design system pesado.
- Build passa.
- Lint passa ou limitação documentada.
```

## Prompt 06 (opus) — Criar entidades e tipos de domínio

```prompt
Objectivo:
Criar os tipos TypeScript centrais de domínio, alinhados aos contratos do Backend Core e preparados para a Campaign War Room.

Contexto obrigatório:
- Componente alvo: frontend
- Backlog da fase: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados
- O Backend Core é a fonte de verdade dos contratos.
- O frontend deve evitar inventar campos como obrigatórios quando o contrato ainda estiver incerto.

Instruções:
- Lê o backlog e relatórios anteriores.
- Consulta schema OpenAPI ou documentação do Backend Core, se disponível.
- Criar tipos TypeScript em entities/*.
- Entidades mínimas:
  - Campaign;
  - Workspace;
  - User;
  - Artist;
  - Track;
  - CampaignIntelligence;
  - CampaignAnalysis;
  - CampaignScores;
  - CampaignMoment;
  - CampaignRecommendation;
  - ContentOutput;
  - Report;
  - MediaKit.
- Criar tipos para responses:
  - ListResponse ou PaginatedResponse;
  - DetailResponse, se aplicável;
  - ApiErrorResponse, se aplicável.
- Alinhar nomes com o Backend Core.
- Campos incertos devem ser opcionais.
- Criar mappers simples apenas se necessário.
- Avaliar instalação de zod.
- Instalar zod apenas se for usado de forma clara nesta fase.
- Se usar Zod, criar schemas apenas para responses críticas, sem exagerar.
- Garantir que os tipos de intelligence cobrem:
  - analysis;
  - scores;
  - grade;
  - moments;
  - recommendations;
  - summary;
  - explanations;
  - warnings;
  - metadata;
  - generated_at.
- Garantir build/lint.
- Cria o relatório em:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_06_entidades_tipos_dominio.md

Critérios de aceitação:
- Tipos centrais existem.
- Tipos de Campaign Intelligence cobrem os blocos principais.
- Campos incertos são opcionais.
- Build passa.
- Lint passa ou limitação documentada.
- Relatório lista decisões de modelação e lacunas de contrato.
```

## Prompt 07 (opus) — Implementar auth/session foundation

```prompt
Objectivo:
Implementar a fundação de autenticação/sessão suficiente para consumir o Backend Core durante o MVP, mantendo o Backend Core como fonte da verdade de segurança.

Contexto obrigatório:
- Componente alvo: frontend
- Backlog da fase: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados
- API client e providers já existem.
- Não implementar RBAC completo no frontend.
- Nunca usar X-Internal-Token.

Instruções:
- Lê o backlog e relatórios anteriores.
- Confirmar endpoints reais de auth no Backend Core:
  - token;
  - refresh, se existir;
  - current user/me, se existir.
- Criar serviço/hook de login se endpoint existir.
- Criar estado de sessão:
  - loading;
  - authenticated;
  - unauthenticated.
- Criar armazenamento de access token simples.
- Se refresh token existir e o contrato for claro, suportar refresh.
- Se refresh não estiver claro, documentar limitação e não inventar comportamento complexo.
- Criar logout.
- Criar ProtectedRoute.
- Criar página de login simples se necessário.
- Ligar API client ao access token.
- Garantir que token não é logado.
- Não implementar permissões de negócio no frontend como fonte da verdade.
- Criar tratamento mínimo de 401.
- Garantir build/lint.
- Cria o relatório em:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_07_auth_session_foundation.md

Critérios de aceitação:
- Fluxo básico de sessão existe.
- Login existe se endpoint real existir.
- Logout limpa sessão.
- ProtectedRoute funciona.
- API client recebe token.
- 401 é tratado.
- Tokens não são logados.
- Build/lint passam ou limitações ficam documentadas.
- Limitações de auth ficam documentadas.
```

## Prompt 08 (opus) — Implementar workspace foundation

```prompt
Objectivo:
Implementar a fundação de workspace para que o frontend trabalhe sempre com um workspace activo e envie X-Workspace-ID nas chamadas ao Backend Core.

Contexto obrigatório:
- Componente alvo: frontend
- Backlog da fase: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados
- Auth/session foundation já existe.
- API client suporta X-Workspace-ID.
- Backend Core é a fonte da verdade de membership/permissões.

Instruções:
- Lê o backlog e relatórios anteriores.
- Confirmar endpoint real de workspaces.
- Criar serviço/hook para listar workspaces.
- Criar WorkspaceProvider real ou completar o provider inicial.
- Criar selector de workspace activo.
- Persistir workspace activo localmente se fizer sentido.
- Injectar X-Workspace-ID no API client.
- Ao trocar workspace, invalidar queries relevantes do TanStack Query.
- Criar estado quando:
  - workspaces estão a carregar;
  - não há workspace;
  - erro ao carregar workspaces;
  - workspace seleccionado já não existe.
- Criar selector simples no App Shell.
- Não duplicar permissões de negócio no frontend.
- Garantir build/lint.
- Cria o relatório em:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_08_workspace_foundation.md

Critérios de aceitação:
- Workspace activo existe.
- X-Workspace-ID é enviado nas chamadas.
- Selector de workspace existe.
- Troca de workspace invalida queries relevantes.
- Estado sem workspace é tratado.
- Build/lint passam ou limitações ficam documentadas.
```

## Prompt 09 (opus) — Implementar páginas base de campanhas

```prompt
Objectivo:
Criar as páginas base de campanhas: listagem, detalhe simples e navegação para Campaign War Room.

Contexto obrigatório:
- Componente alvo: frontend
- Backlog da fase: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados
- API client, auth, workspace e UI foundation já existem.

Instruções:
- Lê o backlog e relatórios anteriores.
- Confirmar endpoint real de listagem de campanhas.
- Confirmar endpoint real de detalhe de campanha.
- Criar API/hook em entities/campaign ou feature adequada:
  - useCampaigns;
  - useCampaign.
- Usar TanStack Query.
- Incluir workspace activo no query key.
- Criar página /campaigns.
- Criar página /campaigns/:campaignId.
- Criar navegação para /campaigns/:campaignId/war-room.
- Mostrar:
  - loading;
  - error;
  - empty;
  - forbidden;
  - service unavailable.
- Usar componentes UI base.
- Não implementar edição completa de campanha nesta fase.
- Não implementar criação completa de campanha nesta fase.
- Se endpoints reais estiverem ausentes, criar camada preparada e documentar dependência, mas não deixar runtime normal dependente de mocks falsos.
- Garantir build/lint.
- Cria o relatório em:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_09_paginas_base_campanhas.md

Critérios de aceitação:
- Lista de campanhas renderiza com dados reais quando Backend Core está disponível.
- Detalhe simples renderiza.
- Estados loading/error/empty existem.
- Navegação para War Room existe.
- Workspace é respeitado.
- Build/lint passam ou limitações ficam documentadas.
```

## Prompt 10 (opus) — Implementar Campaign Intelligence feature

```prompt
Objectivo:
Criar feature dedicada para consumir e apresentar a intelligence de uma campanha através do Backend Core.

Contexto obrigatório:
- Componente alvo: frontend
- Backlog da fase: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados
- Endpoint alvo:
  POST /api/v1/campaigns/{id}/intelligence/
- O frontend deve chamar apenas o Backend Core.
- Não chamar intelligence_engine directamente.

Instruções:
- Lê o backlog e relatórios anteriores.
- Criar feature:
  src/features/campaign-intelligence
- Criar hook:
  useCampaignIntelligence
- Consumir POST /api/v1/campaigns/{id}/intelligence/.
- Usar TanStack Query ou mutation/query conforme decisão técnica:
  - POST pode ser usado com useQuery se for idempotente para leitura operacional;
  - documentar a decisão.
- Query key deve incluir:
  - workspaceId;
  - campaignId.
- Tratar:
  - loading;
  - success;
  - empty/insufficient data;
  - 401;
  - 403;
  - 404;
  - 422;
  - 502;
  - 503;
  - network error.
- Tratar source:
  - engine;
  - dry_run.
- Criar componentes:
  - IntelligenceSummary;
  - GradeBadge;
  - ScoreGrid;
  - RecommendationsList;
  - RecommendationItem;
  - MomentsList;
  - MomentItem;
  - WarningsPanel;
  - ExplanationsPanel.
- Mostrar warnings de forma visível, sem assustar o utilizador.
- Mostrar explanations de forma opcional/colapsável, se fizer sentido.
- Não calcular scores no frontend.
- Não transformar recommendations em acções automáticas nesta fase.
- Garantir build/lint.
- Cria o relatório em:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_10_campaign_intelligence_feature.md

Critérios de aceitação:
- Endpoint de intelligence é consumido via Backend Core.
- Não há chamada directa ao Intelligence Engine.
- Scores são apresentados.
- Grade é apresentada.
- Moments são apresentados.
- Recommendations são apresentadas.
- Warnings/explanations são visíveis.
- Erros 502/503 têm UI própria.
- Build/lint passam ou limitações ficam documentadas.
```

## Prompt 11 (opus) — Implementar Campaign War Room MVP

```prompt
Objectivo:
Compor a primeira experiência real de produto do frontend: Campaign War Room MVP.

Contexto obrigatório:
- Componente alvo: frontend
- Backlog da fase: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados
- Campaign Intelligence feature já criada.
- Páginas base de campanhas já existem.

Instruções:
- Lê o backlog e relatórios anteriores.
- Criar página:
  /campaigns/:campaignId/war-room
- Criar ou completar widgets:
  - campaign-header;
  - campaign-score-card;
  - campaign-recommendations-panel;
  - campaign-moments-panel;
  - campaign-assets-panel;
  - campaign-reports-panel.
- A War Room deve mostrar:
  - breadcrumb/navegação;
  - Campaign Header;
  - Intelligence Summary;
  - Grade;
  - Priority/Scores;
  - Recommendations Panel;
  - Moments Panel;
  - Warnings/Explanations;
  - área de assets/content outputs;
  - área de reports/media kits;
  - estados loading/error/empty.
- Criar layout responsivo simples.
- Usar componentes shared/ui.
- Não chamar IE nem Renderer directamente.
- Não implementar geração real de assets nesta fase.
- Não implementar edição completa de campanha.
- Garantir que a página continua útil mesmo quando intelligence devolve warnings ou insufficient data.
- Garantir build/lint.
- Cria o relatório em:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_11_campaign_war_room_mvp.md

Critérios de aceitação:
- War Room renderiza para uma campanha.
- War Room consome dados reais do Backend Core quando disponível.
- War Room mostra intelligence de forma clara.
- War Room tem painéis principais.
- War Room não depende de IE/Renderer directos.
- Loading/error/empty states funcionam.
- Build/lint passam ou limitações ficam documentadas.
```

## Prompt 12 (opus) — Implementar painéis de assets, reports e media kits

```prompt
Objectivo:
Adicionar à War Room uma visão inicial dos outputs relacionados com a campanha: content outputs, reports e media kits.

Contexto obrigatório:
- Componente alvo: frontend
- Backlog da fase: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados
- War Room MVP já existe.
- Frontend não deve chamar Content Renderer directamente.

Instruções:
- Lê o backlog e relatórios anteriores.
- Confirmar se o Backend Core expõe content outputs por campanha.
- Confirmar se reports/media kits aparecem no campaign detail ou endpoint próprio.
- Criar tipos e hooks necessários:
  - useCampaignContentOutputs;
  - useCampaignReports;
  - useCampaignMediaKits;
  apenas se houver endpoints ou dados reais disponíveis.
- Criar ou completar:
  - CampaignAssetsPanel;
  - CampaignReportsPanel;
  - CampaignMediaKitsPanel.
- Se endpoints ainda não existirem, criar placeholders honestos:
  - "Dados ainda não expostos pelo Backend Core";
  - "A integração com Renderer existe, mas esta UI ainda depende de endpoint de consulta".
- Não usar mocks falsos em runtime normal.
- Não chamar renderer directamente.
- Mostrar status dos outputs se existir:
  - queued;
  - processing;
  - completed;
  - failed;
  - unknown.
- Garantir loading/error/empty states.
- Garantir build/lint.
- Cria o relatório em:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_12_paineis_assets_reports_media_kits.md

Critérios de aceitação:
- War Room tem área para assets/reports/media kits.
- Dados reais são usados se endpoints existirem.
- Se endpoints não existirem, placeholders honestos indicam dependência do Backend Core.
- Não há chamada directa ao Renderer.
- Build/lint passam ou limitações ficam documentadas.
```

## Prompt 13 (opus) — Criar tratamento transversal de erros e sessão expirada

```prompt
Objectivo:
Criar tratamento transversal e consistente para erros comuns de API, sessão expirada, permissões e serviços indisponíveis.

Contexto obrigatório:
- Componente alvo: frontend
- Backlog da fase: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados
- API client, auth, workspace, pages e War Room já existem.

Instruções:
- Lê o backlog e relatórios anteriores.
- Rever API client e normalização de erros.
- Rever uso de ErrorState nas páginas.
- Criar tratamento transversal para:
  - 401 unauthenticated;
  - 403 forbidden;
  - 404 not found;
  - 422 validation;
  - 500 server error;
  - 502 upstream error;
  - 503 service unavailable;
  - network error;
  - backend unavailable;
  - workspace missing.
- Criar componentes se ainda faltarem:
  - PermissionDenied;
  - NotFoundState;
  - ServiceUnavailable;
  - SessionExpired;
  - WorkspaceRequiredState.
- Em 401, encaminhar para login ou mostrar sessão expirada, conforme o auth implementado.
- Em 403, mostrar permissão insuficiente.
- Em 502/503, explicar que o serviço está temporariamente indisponível.
- Nunca mostrar tokens.
- Nunca mostrar stack trace crua ao utilizador.
- Garantir que War Room e páginas de campanhas usam estes padrões.
- Garantir build/lint.
- Cria o relatório em:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_13_tratamento_erros_sessao.md

Critérios de aceitação:
- Erros comuns têm UI adequada.
- 401/403/404/422/502/503 são distinguíveis.
- Sessão expirada é tratada.
- Workspace ausente é tratado.
- Tokens e detalhes sensíveis não aparecem.
- Build/lint passam ou limitações ficam documentadas.
```

## Prompt 14 (sonnet) — Documentar arquitectura frontend

```prompt
Objectivo:
Criar documentação da arquitectura frontend, padrões, decisões e regras de evolução.

Contexto obrigatório:
- Componente alvo: frontend
- Backlog da fase: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados
- Documento a criar:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\arquitectura_frontend.md

Instruções:
- Lê o backlog e todos os relatórios anteriores desta fase.
- Inspecciona a estrutura final do frontend.
- Cria arquitectura_frontend.md.
- O documento deve ser prático, directo e útil para próximos prompts/IA local.
- Incluir:
  - stack;
  - scripts;
  - estrutura de pastas;
  - regras de dependência;
  - API client;
  - auth/session;
  - workspace;
  - routing;
  - server state com TanStack Query;
  - UI foundation;
  - Campaign War Room;
  - tratamento de erros;
  - decisões tomadas;
  - limitações;
  - o que não fazer.
- Explicar claramente:
  - frontend chama apenas Backend Core;
  - frontend não chama IE;
  - frontend não chama Renderer;
  - X-Internal-Token nunca pertence ao frontend.
- Explicar como adicionar uma nova feature.
- Explicar como adicionar uma nova entidade.
- Explicar como criar nova página.
- Não incluir secrets.
- Cria relatório em:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_14_documentacao_arquitectura_frontend.md

Critérios de aceitação:
- arquitectura_frontend.md existe.
- Documento explica a estrutura.
- Documento explica como evoluir o frontend.
- Documento explica regra de não chamar IE/Renderer directamente.
- Documento não contém secrets.
- Relatório lista ficheiros criados/alterados, decisões e próximo passo recomendado.
```

## Prompt 15 (sonnet) — Validar fase e criar estado final

```prompt
Objectivo:
Fechar a fase Frontend Foundation & Campaign War Room MVP com validações, documentação de estado e relatório honesto.

Contexto obrigatório:
- Componente alvo: frontend
- Backlog da fase: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados
- Documento de arquitectura esperado:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\arquitectura_frontend.md
- Documento de estado a criar:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\estado_frontend_foundation_campaign_war_room.md
- Relatório final a criar:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_15_estado_final_frontend_foundation_campaign_war_room.md

Instruções:
- Lê o backlog.
- Lê todos os relatórios desta fase.
- Revê a arquitectura frontend implementada.
- Revê os ficheiros principais alterados.
- Executa validações relevantes:
  - pnpm build;
  - pnpm lint;
  - testes, se existirem;
  - pnpm dev ou validação de arranque local, se possível.
- Validar navegação básica, se possível.
- Validar consumo do Backend Core, se o ambiente permitir.
- Não inventes resultados.
- Se Backend Core não estiver disponível, documentar limitação.
- Verificar que o frontend não contém:
  - X-Internal-Token;
  - INTERNAL_API_TOKEN;
  - secrets reais;
  - chamadas directas ao Intelligence Engine;
  - chamadas directas ao Content Renderer.
- Corrigir apenas falhas directamente relacionadas com esta fase.
- Não fazer refactors fora do escopo.
- Criar estado_frontend_foundation_campaign_war_room.md com:
  - resumo executivo;
  - escopo entregue;
  - estrutura criada;
  - dependências instaladas;
  - rotas;
  - auth/session;
  - workspace;
  - API client;
  - War Room;
  - validações executadas;
  - limitações;
  - riscos em aberto;
  - pronto/não pronto para piloto;
  - pronto/não pronto para produção;
  - próximos passos.
- Criar relatório final em:
  frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_15_estado_final_frontend_foundation_campaign_war_room.md

Critérios de aceitação:
- pnpm build passa ou falha fica documentada.
- pnpm lint passa ou falha fica documentada.
- App arranca ou limitação fica documentada.
- War Room existe ou lacuna fica documentada.
- Não há X-Internal-Token no frontend.
- Não há secrets reais.
- Não há chamadas directas ao IE/Renderer.
- Documento de estado final existe.
- Relatório final existe.
- Estado final é honesto.
- Próximo passo recomendado está claro.
```
