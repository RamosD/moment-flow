# Backlog: Frontend Foundation & Campaign War Room MVP

# MomentFlow / ChartRex — Frontend Foundation & Campaign War Room MVP

## 1. Objectivo do documento

Este documento define o backlog técnico e funcional da primeira fase do frontend do MomentFlow/ChartRex.

A pasta `frontend/` já foi criada e o projecto React/Vite/TypeScript já foi inicializado.

O objectivo desta fase é criar uma fundação de frontend robusta, modular e escalável, e entregar a primeira experiência de produto útil: **Campaign War Room MVP**.

A regra principal é:

```text
Frontend MVP pequeno.
Arquitectura do frontend robusta desde o início.
```

---

## 2. Estado de partida

## 2.1 Projecto frontend existente

O projecto frontend já existe com React, Vite, TypeScript, ESLint e pnpm.

`frontend/package.json` actual:

```json
{
  "name": "frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.2.7",
    "react-dom": "^19.2.7"
  },
  "devDependencies": {
    "@eslint/js": "^10.0.1",
    "@types/node": "^24.13.2",
    "@types/react": "^19.2.17",
    "@types/react-dom": "^19.2.3",
    "@vitejs/plugin-react": "^6.0.2",
    "eslint": "^10.5.0",
    "eslint-plugin-react-hooks": "^7.1.1",
    "eslint-plugin-react-refresh": "^0.5.3",
    "globals": "^17.6.0",
    "typescript": "~6.0.2",
    "typescript-eslint": "^8.61.0",
    "vite": "^8.1.0"
  },
  "packageManager": "pnpm@11.9.0+sha512.bd682d5d03fe525ef7c9fd6780c6884d1e756ac4c9c9fe00c538782824310dcf90e3ddc4f53835f06dfaebd5085e41855e0bcbb3b60de2ac5bbab89e5036f03b"
}
```

## 2.2 Estado do ecossistema

O frontend deve nascer assumindo que existem três componentes técnicos:

```text
backend_core
intelligence_engine
content_renderer
```

Mas o frontend **não deve chamar directamente** o `intelligence_engine` nem o `content_renderer`.

Fluxo correcto:

```text
Frontend → Backend Core → Intelligence Engine
Frontend → Backend Core → Content Renderer
```

O Backend Core é a fronteira de produto, segurança, workspace, permissões e orquestração.

---

# 3. Tese arquitectural

A tese global mantém-se:

```text
Django governa o produto.
FastAPI Intelligence calcula e recomenda.
Content Renderer gera activos.
Frontend orquestra a experiência do utilizador.
```

## 3.1 Responsabilidade do frontend

O frontend é responsável por:

```text
- experiência de utilizador;
- navegação;
- composição visual;
- consumo das APIs do Backend Core;
- estados de loading/error/empty;
- visualização de campanhas;
- visualização de intelligence;
- visualização de scores;
- visualização de moments;
- visualização de recommendations;
- iniciação de acções pelo utilizador;
- apresentação do estado de assets/reports/media kits;
- respeitar auth/workspace/permissões vindas do Backend Core.
```

## 3.2 O frontend não deve

```text
- chamar directamente o Intelligence Engine;
- chamar directamente o Content Renderer;
- decidir permissões de negócio sozinho;
- guardar server state em estado global local;
- duplicar regras de negócio do Django;
- gerar assets;
- calcular scores;
- detectar moments;
- persistir estado de produto;
- assumir produção-ready antes de validação.
```

---

# 4. Escopo da fase

## 4.1 Incluído

Esta fase inclui:

```text
- estrutura modular escalável do frontend;
- routing base;
- app shell;
- providers globais;
- API client;
- configuração de ambiente;
- auth/session foundation;
- workspace context foundation;
- design system mínimo;
- componentes UI base;
- estados loading/error/empty;
- tipos TypeScript para contratos consumidos;
- páginas iniciais de campaigns;
- Campaign War Room MVP;
- consumo do endpoint de intelligence do Backend Core;
- visualização de scores, grade, moments e recommendations;
- documentação da arquitectura frontend;
- validação build/lint;
- relatório final de estado.
```

## 4.2 Fora do escopo

Não implementar nesta fase:

```text
- Next.js;
- SSR;
- landing pages públicas;
- SEO;
- billing UI;
- edição completa de campanhas;
- criação completa de campanhas;
- upload de media;
- geração real de assets a partir do frontend;
- dashboards avançados;
- gráficos complexos;
- design system enterprise completo;
- internacionalização avançada;
- testes E2E completos com Playwright/Cypress;
- consumo directo de Intelligence Engine;
- consumo directo de Content Renderer;
- mobile app nativa;
- deploy produção.
```

---

# 5. Stack alvo

## 5.1 Stack já existente

```text
React
React DOM
TypeScript
Vite
ESLint
pnpm
```

## 5.2 Dependências recomendadas para esta fase

A IA local deve confirmar compatibilidade antes de instalar.

```text
react-router-dom
@tanstack/react-query
zod
react-hook-form
@hookform/resolvers
clsx
lucide-react
```

## 5.3 Dependências opcionais

Instalar apenas se forem realmente necessárias nesta fase:

```text
zustand
date-fns
tailwindcss
class-variance-authority
```

## 5.4 Recomendação de styling

Para esta fase, usar abordagem simples e consistente.

Opções aceitáveis:

```text
CSS Modules
ou
CSS global organizado por design tokens
ou
Tailwind CSS, se a equipa já preferir
```

A IA local deve inspeccionar o projecto antes de escolher. Não introduzir uma stack visual pesada sem necessidade.

---

# 6. Estrutura arquitectural recomendada

A estrutura deve seguir uma arquitectura por camadas e features.

Estrutura alvo sugerida:

```text
frontend/
  src/
    app/
      providers/
      router/
      layouts/
      config/

    shared/
      api/
      ui/
      lib/
      hooks/
      types/
      constants/
      styles/

    entities/
      campaign/
      artist/
      track/
      workspace/
      user/
      content-output/
      report/
      media-kit/

    features/
      auth/
      workspace-switching/
      campaign-intelligence/
      campaign-actions/
      asset-generation-status/
      report-status/

    widgets/
      app-shell/
      campaign-header/
      campaign-score-card/
      campaign-recommendations-panel/
      campaign-moments-panel/
      campaign-assets-panel/
      campaign-reports-panel/

    pages/
      dashboard/
      campaigns/
      campaign-detail/
      campaign-war-room/
      not-found/

    main.tsx
```

## 6.1 Regras de dependência

```text
app pode importar shared, entities, features, widgets e pages.
pages podem importar widgets, features, entities e shared.
widgets podem importar features, entities e shared.
features podem importar entities e shared.
entities podem importar shared.
shared não deve importar app, pages, widgets, features ou entities.
```

## 6.2 Proibição

Evitar:

```text
src/components gigante;
API calls dentro de componentes visuais;
tipos espalhados sem domínio;
estado global para tudo;
imports circulares;
features acopladas a rotas;
chamadas directas a serviços técnicos internos.
```

---

# 7. Contratos de API esperados

## 7.1 Backend Core como única API do frontend

O frontend deve consumir apenas o Backend Core.

Base URL por ambiente:

```text
VITE_BACKEND_API_BASE_URL
```

Exemplo:

```text
VITE_BACKEND_API_BASE_URL=http://localhost:8100/api/v1
```

## 7.2 Headers esperados

O frontend deve estar preparado para enviar:

```text
Authorization: Bearer <access_token>
X-Workspace-ID: <workspace_id>
Content-Type: application/json
```

O frontend **não** deve enviar:

```text
X-Internal-Token
```

`X-Internal-Token` é segredo de comunicação serviço-a-serviço e nunca deve existir no frontend.

## 7.3 Endpoints esperados

A IA local deve confirmar rotas reais no Backend Core antes de implementar.

Endpoints prováveis:

```text
POST /api/v1/auth/token/
POST /api/v1/auth/token/refresh/
GET /api/v1/workspaces/
GET /api/v1/campaigns/
GET /api/v1/campaigns/{id}/
POST /api/v1/campaigns/{id}/intelligence/
GET /api/v1/system/health/dependencies/
```

## 7.4 Endpoint central da War Room

```text
POST /api/v1/campaigns/{id}/intelligence/
```

Resposta esperada inclui:

```text
status
source
engine
engine_version
request_id
workspace_id
campaign_id
result.analysis
result.scores
result.grade
result.moments
result.recommendations
result.summary
explanations
warnings
metadata
generated_at
```

---

# 8. UX alvo — Campaign War Room MVP

## 8.1 Objectivo da War Room

A War Room deve responder rapidamente:

```text
Como está esta campanha?
Qual é a prioridade?
Que sinais foram detectados?
O que devo fazer a seguir?
Que assets/reports/media kits já existem ou faltam?
```

## 8.2 Layout inicial

```text
Campaign War Room
  ├── App Shell
  ├── Breadcrumb / navegação
  ├── Campaign Header
  ├── Intelligence Summary
  ├── Grade / Priority / Scores
  ├── Recommendations Panel
  ├── Moments Panel
  ├── Assets / Content Outputs Panel
  ├── Reports / Media Kits Panel
  ├── Warnings / Explanations
  └── Estados loading/error/empty
```

## 8.3 MVP visual mínimo

O MVP deve ser funcional sem depender de design avançado.

Componentes mínimos:

```text
Card
Button
Badge
Alert
Skeleton/Loading
EmptyState
ErrorState
PageHeader
Section
ScoreCard
RecommendationItem
MomentItem
```

---

# 9. Backlog técnico

---

# FE-001 — Analisar setup actual, contratos e arquitectura alvo

## Objectivo

Inspeccionar o projecto `frontend/`, o Backend Core e os contratos necessários para definir um plano de implementação seguro.

## Tarefas

```text
Ler este backlog.
Inspeccionar frontend/package.json.
Inspeccionar src actual.
Inspeccionar tsconfig, vite config e eslint config.
Confirmar se React/Vite estão funcionais.
Confirmar scripts disponíveis:
- pnpm dev;
- pnpm build;
- pnpm lint.

Inspeccionar documentação do Backend Core.
Confirmar rotas reais:
- auth;
- workspaces;
- campaigns;
- campaign detail;
- campaign intelligence.

Inspeccionar schema OpenAPI se existir.
Confirmar formato real do endpoint:
POST /api/v1/campaigns/{id}/intelligence/

Confirmar requisitos de auth e workspace.
Identificar lacunas.
Definir plano de implementação dos próximos prompts.
Não alterar runtime salvo relatório.
```

## Critérios de aceitação

```text
Relatório de análise criado.
Rotas reais confirmadas ou marcadas como pendentes.
Estrutura actual do frontend documentada.
Dependências necessárias identificadas.
Riscos listados.
Plano de execução definido.
```

---

# FE-002 — Criar foundation estrutural do frontend

## Objectivo

Criar a estrutura modular escalável do frontend sem ainda implementar a War Room completa.

## Tarefas

```text
Criar estrutura src/app.
Criar estrutura src/shared.
Criar estrutura src/entities.
Criar estrutura src/features.
Criar estrutura src/widgets.
Criar estrutura src/pages.
Criar ficheiros index quando úteis.
Configurar aliases de import se fizer sentido.
Actualizar tsconfig/vite config se necessário.
Criar estilos globais base.
Criar design tokens mínimos:
- spacing;
- radius;
- colors;
- typography;
- shadows.

Criar layout base.
Criar App root limpo.
Garantir que build continua a passar.
```

## Critérios de aceitação

```text
Estrutura modular existe.
App arranca sem erro.
Build passa.
Lint passa ou limitações documentadas.
Não há imports circulares óbvios.
Arquitectura documentada.
```

---

# FE-003 — Configurar API client e ambiente

## Objectivo

Criar camada de comunicação com o Backend Core, centralizada, tipada e segura.

## Tarefas

```text
Criar leitura de VITE_BACKEND_API_BASE_URL.
Criar validação simples de configuração.
Criar API client base.
Criar normalização de erros HTTP.
Criar suporte a Authorization Bearer token.
Criar suporte a X-Workspace-ID.
Criar helpers:
- get;
- post;
- patch;
- delete, se necessário.

Garantir que X-Internal-Token nunca existe no frontend.
Criar tipos de erro:
- ApiError;
- UnauthorizedError;
- ForbiddenError;
- NotFoundError;
- ValidationError;
- ServiceUnavailableError.

Criar testes se houver setup de testes.
Se não houver framework de testes, documentar limitação.
```

## Critérios de aceitação

```text
API client central existe.
Base URL vem de env.
Auth header é suportado.
Workspace header é suportado.
Erros HTTP são normalizados.
Nenhum segredo interno é exposto.
Build/lint passam.
```

---

# FE-004 — Instalar e configurar routing, query client e providers

## Objectivo

Criar os providers globais da aplicação: routing, server state, auth/session foundation e workspace foundation.

## Tarefas

```text
Instalar react-router-dom.
Instalar @tanstack/react-query.
Criar AppProviders.
Criar RouterProvider ou router equivalente.
Criar QueryClient com defaults adequados.
Criar AuthProvider inicial.
Criar WorkspaceProvider inicial.
Criar hooks:
- useAuth;
- useWorkspace;
- useApiClient, se fizer sentido.

Criar rotas:
- /
- /campaigns
- /campaigns/:campaignId
- /campaigns/:campaignId/war-room
- /settings, placeholder
- *
```

## Critérios de aceitação

```text
Routing funciona.
QueryClientProvider configurado.
AuthProvider inicial existe.
WorkspaceProvider inicial existe.
Rotas básicas renderizam.
Build/lint passam.
```

---

# FE-005 — Criar UI foundation e estados transversais

## Objectivo

Criar componentes UI base e padrões de estado reutilizáveis para evitar duplicação visual.

## Componentes mínimos

```text
Button
Card
Badge
Alert
PageHeader
Section
LoadingState
EmptyState
ErrorState
Skeleton
Tabs ou Nav simples, se necessário
```

## Tarefas

```text
Criar componentes em shared/ui.
Criar estilos consistentes.
Criar variantes simples.
Criar página demo interna ou usar páginas existentes para validar.
Criar padrões de erro:
- erro de rede;
- erro 401;
- erro 403;
- erro 404;
- serviço indisponível;
- estado vazio.

Evitar design system pesado.
```

## Critérios de aceitação

```text
Componentes UI base existem.
Estados loading/error/empty existem.
Componentes são reutilizados nas páginas iniciais.
Build/lint passam.
```

---

# FE-006 — Criar entidades e tipos de domínio

## Objectivo

Criar os tipos TypeScript centrais para campanhas, workspaces, intelligence e assets, alinhados ao Backend Core.

## Entidades mínimas

```text
Campaign
Workspace
User
Artist
Track
CampaignIntelligence
CampaignAnalysis
CampaignScores
CampaignMoment
CampaignRecommendation
ContentOutput
Report
MediaKit
```

## Tarefas

```text
Criar types em entities/*.
Criar types para responses.
Criar mappers mínimos se necessário.
Criar guards ou schemas Zod para responses críticas, se fizer sentido.
Alinhar nomes com Backend Core.
Evitar overengineering.
Documentar campos incertos como opcionais.
```

## Critérios de aceitação

```text
Tipos centrais existem.
Tipos da intelligence cobrem analysis, scores, moments, recommendations e summary.
Campos incertos são opcionais.
Build/lint passam.
```

---

# FE-007 — Implementar auth/session foundation

## Objectivo

Criar fundação de autenticação suficiente para consumir o Backend Core durante o MVP.

## Tarefas

```text
Confirmar endpoints reais de auth.
Criar serviço de login se endpoint existir.
Criar armazenamento de access token de forma simples.
Criar refresh token apenas se já existir contrato claro.
Criar logout.
Criar estado authenticated/unauthenticated/loading.
Criar ProtectedRoute.
Criar ecrã de login simples se necessário.
Garantir que token não é logado.
Não implementar RBAC completo no frontend.
Backend continua fonte da verdade de permissões.
```

## Critérios de aceitação

```text
Fluxo básico de sessão existe.
ProtectedRoute funciona.
API client recebe token.
Logout limpa sessão.
Build/lint passam.
Limitações de auth estão documentadas.
```

---

# FE-008 — Implementar workspace foundation

## Objectivo

Criar contexto de workspace para que as chamadas ao Backend Core incluam `X-Workspace-ID`.

## Tarefas

```text
Confirmar endpoint real de workspaces.
Criar listagem/carregamento de workspaces.
Criar selecção de workspace activo.
Persistir workspace activo localmente, se fizer sentido.
Injectar X-Workspace-ID no API client.
Criar estado quando não há workspace.
Criar selector simples de workspace no App Shell.
Garantir que troca de workspace invalida queries relevantes.
```

## Critérios de aceitação

```text
Workspace activo existe.
X-Workspace-ID é enviado nas chamadas.
Selector de workspace existe.
Sem workspace, a app mostra estado adequado.
Build/lint passam.
```

---

# FE-009 — Implementar páginas base de campanhas

## Objectivo

Criar as primeiras páginas de campanhas: listagem, detalhe simples e navegação para War Room.

## Tarefas

```text
Confirmar endpoint real de listagem de campanhas.
Confirmar endpoint real de detalhe de campanha.
Criar hooks com TanStack Query:
- useCampaigns;
- useCampaign;
- useCampaignIntelligence, se já necessário.

Criar página /campaigns.
Criar página /campaigns/:campaignId.
Criar link para /campaigns/:campaignId/war-room.
Mostrar loading/error/empty.
Usar componentes UI base.
Não implementar edição completa de campanha nesta fase.
```

## Critérios de aceitação

```text
Lista de campanhas renderiza.
Detalhe simples renderiza.
Estados loading/error/empty tratados.
Navegação para War Room existe.
Build/lint passam.
```

---

# FE-010 — Implementar Campaign Intelligence feature

## Objectivo

Criar feature dedicada para consumir e apresentar a intelligence de uma campanha.

## Tarefas

```text
Criar feature campaign-intelligence.
Criar hook useCampaignIntelligence.
Consumir POST /api/v1/campaigns/{id}/intelligence/.
Tratar loading.
Tratar erro 401/403/404/502/503.
Tratar status completed.
Tratar source engine/dry_run.
Tratar warnings.
Tratar explanations.
Criar componentes:
- IntelligenceSummary;
- GradeBadge;
- ScoreGrid;
- RecommendationsList;
- MomentsList;
- WarningsPanel;
- ExplanationsPanel.
```

## Critérios de aceitação

```text
Endpoint de intelligence é consumido via Backend Core.
Não há chamada directa ao Intelligence Engine.
Scores são apresentados.
Moments são apresentados.
Recommendations são apresentadas.
Warnings/explanations são visíveis.
Build/lint passam.
```

---

# FE-011 — Implementar Campaign War Room MVP

## Objectivo

Compor a primeira experiência de produto real: War Room da campanha.

## Tarefas

```text
Criar página /campaigns/:campaignId/war-room.
Integrar Campaign Header.
Integrar Intelligence Summary.
Integrar Grade/Priority/Scores.
Integrar Recommendations Panel.
Integrar Moments Panel.
Integrar Warnings/Explanations.
Integrar placeholders para:
- Content Outputs;
- Reports;
- Media Kits;
- Asset generation status.

Criar layout responsivo simples.
Garantir boa experiência em loading.
Garantir boa experiência em erro.
Garantir empty states.
```

## Critérios de aceitação

```text
War Room renderiza para uma campanha.
War Room consome dados reais do Backend Core.
War Room mostra intelligence de forma clara.
War Room não depende de IE/Renderer directos.
Build/lint passam.
```

---

# FE-012 — Implementar painéis de assets, reports e media kits

## Objectivo

Adicionar à War Room uma visão inicial dos outputs relacionados com a campanha.

## Tarefas

```text
Confirmar se o Backend Core já expõe content outputs por campanha.
Confirmar se reports/media kits aparecem no campaign detail ou endpoint próprio.
Criar tipos e hooks necessários.
Criar CampaignAssetsPanel.
Criar CampaignReportsPanel.
Criar CampaignMediaKitsPanel.
Se endpoints ainda não existirem, criar placeholders honestos e documentar dependência.
Não chamar renderer directamente.
```

## Critérios de aceitação

```text
War Room tem área para assets/reports/media kits.
Dados reais são usados se endpoints existirem.
Se endpoints não existirem, placeholders indicam dependência de backend.
Build/lint passam.
```

---

# FE-013 — Criar tratamento transversal de erros e sessão expirada

## Objectivo

Melhorar robustez do frontend em erros comuns.

## Casos a tratar

```text
401 unauthenticated
403 forbidden
404 not found
422 validation
502 upstream error
503 service unavailable
network error
backend unavailable
workspace missing
```

## Tarefas

```text
Centralizar parsing de erros.
Criar mensagens amigáveis e técnicas o suficiente para operação.
Criar fallback visual.
Criar redireccionamento para login em 401, se aplicável.
Criar componente PermissionDenied.
Criar componente ServiceUnavailable.
Garantir que erros não mostram tokens.
```

## Critérios de aceitação

```text
Erros comuns têm UI adequada.
401/403/404/503 são distinguíveis.
Tokens não aparecem.
Build/lint passam.
```

---

# FE-014 — Documentar arquitectura frontend

## Objectivo

Criar documentação da arquitectura, padrões e decisões do frontend.

## Documento sugerido

```text
frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\arquitectura_frontend.md
```

## Conteúdo mínimo

```text
Stack.
Estrutura de pastas.
Regras de dependência.
API client.
Auth.
Workspace.
Routing.
Server state.
UI foundation.
Campaign War Room.
Decisões tomadas.
O que não fazer.
```

## Critérios de aceitação

```text
Documento de arquitectura existe.
Explica a estrutura.
Explica como adicionar nova feature.
Explica a regra de não chamar IE/Renderer directamente.
Não contém secrets.
```

---

# FE-015 — Validação final e estado da fase

## Objectivo

Fechar a fase com validações, documentação final e estado honesto.

## Tarefas

```text
Executar pnpm build.
Executar pnpm lint.
Executar testes, se existirem.
Executar pnpm dev ou validar arranque local, se possível.
Validar navegação básica.
Validar consumo do Backend Core, se ambiente permitir.
Não inventar resultados.
Criar documento de estado:
frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\estado_frontend_foundation_campaign_war_room.md

Criar relatório final em:
frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\resultados\prompt_final_frontend_foundation_campaign_war_room.md
```

## Critérios de aceitação

```text
Build passa ou falhas ficam documentadas.
Lint passa ou falhas ficam documentadas.
App arranca ou limitação fica documentada.
War Room está implementada ou lacunas ficam documentadas.
Documentação final existe.
Estado final é honesto.
Próximo passo recomendado está claro.
```

---

# 10. Critérios de aceitação da fase

A fase fica concluída quando:

```text
Estrutura frontend modular existe.
API client central existe.
Routing existe.
Providers globais existem.
Auth foundation existe.
Workspace foundation existe.
UI foundation existe.
Campaign pages existem.
Campaign War Room MVP existe.
Campaign Intelligence feature consome Backend Core.
Não há chamadas directas ao IE/Renderer.
Build passa.
Lint passa.
Documentação de arquitectura existe.
Documento de estado final existe.
```

---

# 11. Critérios de não aceitação

A fase não deve ser aceite se:

```text
Frontend chama directamente o Intelligence Engine.
Frontend chama directamente o Content Renderer.
X-Internal-Token aparece no frontend.
API calls ficam espalhadas em componentes visuais.
Tudo fica dentro de src/components.
Não há separação por features/entities/shared.
Server state é guardado em estado global local sem necessidade.
War Room depende de mocks em runtime normal.
Build não passa sem justificação.
Lint não passa sem justificação.
Documentação final declara produção-ready sem evidência.
```

---

# 12. Riscos

| ID         | Risco                                                          | Impacto | Mitigação                                                                                  |
| ---------- | -------------------------------------------------------------- | ------: | ------------------------------------------------------------------------------------------ |
| FE-RSK-001 | Frontend nascer como protótipo desorganizado.                  |    Alto | Criar foundation modular antes da War Room.                                                |
| FE-RSK-002 | Acoplamento directo ao IE/Renderer.                            | Crítico | API client aponta apenas ao Backend Core.                                                  |
| FE-RSK-003 | X-Internal-Token ir parar ao browser.                          | Crítico | Proibir e testar/grep.                                                                     |
| FE-RSK-004 | Contratos reais do Backend Core diferirem do assumido.         |    Alto | Prompt inicial deve confirmar OpenAPI/rotas reais.                                         |
| FE-RSK-005 | Auth/workspace subestimados.                                   |    Alto | Criar providers desde início.                                                              |
| FE-RSK-006 | Overengineering visual atrasar MVP.                            |   Médio | Design system mínimo, não enterprise.                                                      |
| FE-RSK-007 | War Room sem valor por falta de dados de assets/reports.       |   Médio | Usar placeholders honestos e documentar dependências.                                      |
| FE-RSK-008 | Versões recentes de React/Vite/TS causarem incompatibilidades. |   Médio | Não instalar dependências sem confirmar compatibilidade; validar build/lint em cada etapa. |
| FE-RSK-009 | Erros 502/503 do ecossistema não tratados na UI.               |   Médio | Criar tratamento transversal de erros.                                                     |
| FE-RSK-010 | Frontend declarar piloto sem validar com Backend Core real.    |   Médio | Validação final deve distinguir mockado vs real.                                           |

---

# 13. Decisões pendentes

## FE-PDEC-001 — Usar Tailwind ou CSS simples?

```text
Estado: pendente
Recomendação: começar com CSS simples/design tokens, salvo preferência explícita da equipa.
```

## FE-PDEC-002 — Auth real ou auth dev temporário?

```text
Estado: pendente
Recomendação: usar auth real se endpoints já existirem; caso contrário, criar dev auth claramente isolado e documentado.
```

## FE-PDEC-003 — Persistência do token

```text
Estado: pendente
Recomendação: começar simples, mas evitar expor secrets internos. Avaliar localStorage vs memória conforme o contrato actual.
```

## FE-PDEC-004 — Test framework

```text
Estado: pendente
Recomendação: só adicionar Vitest/Testing Library se houver valor imediato nesta fase; build/lint são mínimos obrigatórios.
```

## FE-PDEC-005 — Gerar types a partir de OpenAPI?

```text
Estado: pendente
Recomendação: manual nesta fase se o schema ainda estiver instável; avaliar geração automática depois.
```

---

# 14. Ordem recomendada de execução

```text
1. FE-001 — Analisar setup actual, contratos e arquitectura alvo
2. FE-002 — Criar foundation estrutural do frontend
3. FE-003 — Configurar API client e ambiente
4. FE-004 — Instalar e configurar routing, query client e providers
5. FE-005 — Criar UI foundation e estados transversais
6. FE-006 — Criar entidades e tipos de domínio
7. FE-007 — Implementar auth/session foundation
8. FE-008 — Implementar workspace foundation
9. FE-009 — Implementar páginas base de campanhas
10. FE-010 — Implementar Campaign Intelligence feature
11. FE-011 — Implementar Campaign War Room MVP
12. FE-012 — Implementar painéis de assets, reports e media kits
13. FE-013 — Criar tratamento transversal de erros e sessão expirada
14. FE-014 — Documentar arquitectura frontend
15. FE-015 — Validação final e estado da fase
```

---

# 15. Relação com fases futuras

## 15.1 Próxima fase provável

Depois desta fase, a próxima fase deve ser escolhida entre:

```text
- Campaign actions;
- geração de content packs a partir de recomendações;
- reports/media kits UI completa;
- dashboard executivo;
- hardening visual;
- testes E2E;
- deploy staging do frontend.
```

## 15.2 Produção

Esta fase não torna o frontend production-ready.

Para produção ainda serão necessários:

```text
- UX refinada;
- testes E2E;
- tratamento completo de auth/refresh;
- observabilidade frontend;
- tracking de erros;
- feature flags maduras;
- deploy;
- gestão segura de ambiente;
- validação cross-browser;
- performance budget.
```

---

# 16. Resultado esperado

Ao concluir esta fase, o projecto deve passar de:

```text
Sem frontend de produto
```

para:

```text
Frontend foundation robusta + primeira Campaign War Room funcional
```

Estado esperado:

```text
Pronto para piloto técnico controlado: sim
Pronto para produção: não
```

---

# 17. Próximo passo após este backlog

Criar uma pipeline de prompts compatível com o Assistente Desktop para executar esta fase.

Ficheiro sugerido:

```text
frontend\docs\01_fundamentos\01_frontend_foundation_campaign_war_room\02_pipeline.md
```

Recomendação de modelos:

```text
Prompts 01–13: opus
Prompts 14–15: sonnet
```

Justificação:

```text
A fase exige arquitectura frontend, contratos, auth, workspace, server state, War Room e integração real.
A documentação e validação final podem ser feitas com sonnet.
```
