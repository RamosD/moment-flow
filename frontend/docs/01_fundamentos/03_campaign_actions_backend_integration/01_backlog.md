# Backlog — Campaign Actions Backend Integration

> Fase: `03_campaign_actions_backend_integration`  
> Estado: planeada  
> Data da análise: 2026-07-01  
> Dependência backend: CampaignAction API persistente da Iteração 01

## 1. Objectivo

Adaptar a Campaign War Room para consumir a entidade persistente
`CampaignAction` exposta pelo Backend Core em `/api/v1/campaign-actions/`,
substituindo conscientemente a projecção best-effort actual sobre content pack
requests, reports e media kits.

A fase deve preservar a regra arquitectural:

```text
Frontend -> Backend Core
```

O frontend não chama Intelligence Engine ou renderers directamente e nunca
envia `X-Internal-Token`.

Este documento define trabalho futuro. Não autoriza nem contém implementação
runtime.

## 2. Fontes de verdade usadas

- contrato e implementação reais em `backend_core/apps/campaign_actions/`;
- `backend_core/docs/campaign_actions/arquitectura_campaign_actions_backend.md`;
- validação HTTP real registada no Prompt 09 backend;
- implementação actual em `src/entities/campaign-action/`;
- feature actual em `src/features/campaign-actions/`;
- `CampaignActionsPanel` e composição actual da Campaign War Room;
- documentação da fase
  `02_campaign_actions_recommendation_to_execution`.

## 3. Estado real de partida no frontend

### 3.1 A CampaignAction actual não é uma entidade backend

O tipo actual é uma projecção criada no browser. O seu `id` é o id do artefacto
subjacente, não o id de uma CampaignAction:

```text
ContentPackRequest -> CampaignAction projectada
Report             -> CampaignAction projectada
MediaKit            -> CampaignAction projectada
```

`fetchCampaignActions` faz três GET em paralelo:

```text
/content-pack-requests/?campaign=...
/reports/?campaign=...
/media-kits/?campaign=...
```

O resultado usa `Promise.allSettled`, agrega no máximo 50 itens de cada endpoint
e normaliza três contratos diferentes numa lista única.

### 3.2 Criação actual

`CreateActionFromRecommendationDialog` não cria uma CampaignAction. O mutation
despacha directamente para um dos endpoints proprietários:

| Tipo visual | Endpoint actual |
| --- | --- |
| `content_pack` | `POST /content-pack-requests/` |
| `report_request` | `POST /reports/` |
| `media_kit_request` | `POST /media-kits/` |

Title, description, priority, source e recommendation ref são parcialmente
guardados em `metadata` do artefacto. Não existe actualmente uma segunda escrita
para `/campaign-actions/`.

### 3.3 Correlação e deduplicação actuais

O frontend deriva `recommendation_ref` a partir de recommendation id ou de:

```text
campaignId + índice + title/action/type
```

Essa ref é escrita em `artifact.metadata.recommendation_ref`. A leitura volta a
extraí-la de metadata. `matchRecommendationAction` usa o primeiro match por ref
e substitui todo o botão de criação por dois badges.

Consequências actuais:

- o matching é best-effort;
- uma mudança de índice/conteúdo pode produzir outra ref;
- artefactos criados fora desta convenção não são correlacionados;
- qualquer match bloqueia visualmente todos os novos tipos de acção para a
  recommendation;
- não existe protecção transaccional contra concorrência ou duplo clique;
- o backend antigo não garantia deduplicação.

### 3.4 Status actual

O frontend converte os estados nativos dos três artefactos para:

```text
pending | in_progress | completed | failed | cancelled | dismissed | unknown
```

`rawStatus` preserva o estado do artefacto. Não existe lifecycle próprio da
acção. `dismissed` é actualmente inalcançável e é apresentado como cancelled no
estado agregado da recommendation.

### 3.5 Capabilities actualmente desactivadas

`CAMPAIGN_ACTION_CAPABILITIES` marca como não suportados:

- `manual_task`;
- `asset_request`;
- `mark_reviewed`;
- `dismiss`.

O diálogo usa apenas `SUPPORTED_ACTION_TYPE_OPTIONS`, pelo que esses tipos são
omitidos. A documentação anterior justificava correctamente a limitação pela
ausência de uma entidade persistente, mas essa premissa deixou de ser verdadeira
para todos excepto `asset_request`.

### 3.6 Ausência de testes frontend automatizados

O projecto não tem test runner nem ficheiros `*.test.*`/`*.spec.*`. As validações
actuais são lint, TypeScript/build e smoke tests manuais/reais. A adaptação mexe
em deduplicação, mapping e orquestração multi-request; a ausência de testes deve
ser tratada como risco, não omitida do plano.

## 4. Contrato novo confirmado

### 4.1 Identidade e campos

`CampaignAction` tem id UUID e lifecycle próprios. A resposta pública usa
snake_case e inclui:

```text
id
workspace
campaign
recommendation_ref
recommendation_snapshot
title
description
action_type
status
priority
source
dismiss_reason
metadata
related_content_pack_request
related_content_output
related_report
related_media_kit
created_by
completed_at
cancelled_at
created_at
updated_at
```

Valores reais:

```text
action_type:
  content_pack | report_request | media_kit_request | manual_task |
  mark_reviewed | dismiss

status:
  pending | in_progress | completed | failed | dismissed | cancelled

priority:
  low | medium | high | urgent

source:
  recommendation | manual
```

`asset_request` não está implementado. `content_output` é uma relação possível
de `content_pack`, não um action type.

### 4.2 Endpoints

```text
GET   /api/v1/campaign-actions/
POST  /api/v1/campaign-actions/
GET   /api/v1/campaign-actions/{id}/
PATCH /api/v1/campaign-actions/{id}/

POST  /api/v1/campaign-actions/{id}/mark-reviewed/
POST  /api/v1/campaign-actions/{id}/dismiss/
POST  /api/v1/campaign-actions/{id}/cancel/
POST  /api/v1/campaign-actions/{id}/complete/
```

PUT e DELETE não são suportados.

### 4.3 Scoping, permissions e paginação

- JWT e `X-Workspace-ID` são obrigatórios;
- list/detail requerem `campaigns:view`;
- create/PATCH/actions semânticas requerem `campaigns:update`;
- detail cross-workspace devolve 404;
- campaign/artefacto cross-workspace ou cross-campaign devolve 400 de campo;
- lista é paginada: 25 por omissão, `page_size`, máximo 100;
- ordering default: `-created_at`.

Filtros exactos:

```text
campaign | status | action_type | recommendation_ref | source | created_by
```

### 4.4 Recommendations

`recommendation_ref` passou a ser campo persistente, opaco e imutável. Continua
a não ser FK nem id garantido do Intelligence Engine. A derivação defensiva do
frontend continua necessária quando a intelligence não fornece id estável.

`recommendation_snapshot`:

- é obrigatório e não vazio excepto para `manual_task`;
- tem de ser object JSON;
- é imutável;
- tem limite de 65 536 bytes;
- rejeita chaves sensíveis;
- deve ser allowlist mínima, não cópia integral da resposta de intelligence.

### 4.5 Anti-duplicação

O backend rejeita duplicado activo pela chave:

```text
workspace + campaign + recommendation_ref + action_type
```

para status `pending`, `in_progress` ou `completed`. A resposta é 400 no campo
`recommendation_ref`; a constraint de base de dados é a defesa concorrente.

A regra é por action type. Uma recommendation pode legitimamente ter mais do
que uma CampaignAction de tipos diferentes. Actions failed, dismissed ou
cancelled não bloqueiam uma nova action com a mesma chave.

### 4.6 Artefactos relacionados

CampaignAction não cria artefactos automaticamente. O fluxo é:

```text
1. criar artefacto no endpoint proprietário;
2. criar/actualizar CampaignAction com a FK related_*.
```

Compatibilidade:

| Action type | Relações aceites |
| --- | --- |
| `content_pack` | `related_content_pack_request`, `related_content_output` |
| `report_request` | `related_report` |
| `media_kit_request` | `related_media_kit` |
| `manual_task` | nenhuma |
| `mark_reviewed` | nenhuma |
| `dismiss` | nenhuma |

## 5. Comparação directa

| Tema | Frontend actual | Contrato alvo |
| --- | --- | --- |
| Identidade | id do artefacto | id próprio CampaignAction |
| Lista | agrega 3 endpoints | GET único `/campaign-actions/` |
| Paginação | 50 por endpoint, silenciosa | envelope global, máximo 100 |
| Tipo | `type` limitado a 3 criáveis | `action_type`, 6 tipos |
| Artefacto | `artifactKind` implícito | quatro FKs `related_*` |
| Campaign | `campaignId` projectado | `campaign` |
| Status | normalizado do artefacto + `rawStatus` | status próprio e exacto |
| Priority | string livre em metadata | enum top-level |
| Source | inferido de metadata/ref | campo top-level imutável |
| Recommendation ref | metadata do artefacto | campo top-level imutável |
| Snapshot | inexistente | object allowlisted obrigatório |
| Description | metadata do artefacto | campo top-level |
| Deduplicação | primeiro match no browser | regra por ref + action type no backend |
| Reviewed/dismiss | indisponíveis | persistentes |
| Manual task | indisponível | suportada |
| Update | PATCH ao artefacto | PATCH à CampaignAction |
| Lifecycle | depende do artefacto | matriz de transições própria |
| Scoping | cliente partilhado | mesmo cliente, RBAC adicional confirmado |

## 6. Arquitectura frontend alvo

### 6.1 Camada entity

`entities/campaign-action` deve passar a representar exclusivamente o contrato
persistente. Não deve continuar a esconder GET/POST/PATCH de reports, media kits
ou content pack requests.

Estrutura provável:

```text
src/entities/campaign-action/
  model.ts
  campaign-action-api.ts
  campaign-action-mapper.ts       # apenas se o projecto optar por UI camelCase
  query-keys.ts
  useCampaignActions.ts
  useCampaignAction.ts
  useCreateCampaignAction.ts
  useUpdateCampaignAction.ts
  useCampaignActionTransition.ts
  recommendation-ref.ts
  index.ts
```

Há duas opções coerentes para nomes:

1. manter o model em snake_case, como outras entities já fazem; ou
2. declarar DTO snake_case e mapear explicitamente para um model camelCase.

Não é aceitável manter o model camelCase actual fingindo que `artifactKind`,
`rawStatus` e `campaignId` vêm da nova API.

### 6.2 Orquestração de use case

A criação a partir de recommendation é um use case, não uma responsabilidade da
entity CampaignAction. Deve existir uma camada de feature que coordene:

```text
recommendation draft
  -> criar artefacto quando aplicável
  -> criar CampaignAction com related_*
  -> invalidar queries certas
  -> representar sucesso total ou parcial
```

Nome provável:

```text
features/campaign-actions/useCreateActionFromRecommendation.ts
```

Os POST proprietários devem viver nas entities dos respectivos artefactos, não
em `campaign-action-api.ts`.

### 6.3 Read path

`CampaignActionsPanel` e `RecommendationActionState` devem partilhar a mesma
query `/campaign-actions/?campaign=...`. Reports/media kits/content outputs
continuam com queries independentes para os seus painéis.

## 7. Decisões obrigatórias antes do cutover

### DEC-01 — Histórico e backfill

Ao mudar a lista para `/campaign-actions/`, artefactos históricos que só têm
`metadata.recommendation_ref` deixam de aparecer no Campaign Actions Panel.

Escolher antes do rollout:

- **A — backfill backend:** recomendado quando o histórico precisa de ser
  preservado;
- **B — corte temporal explícito:** o painel novo mostra apenas CampaignActions
  criadas após a activação;
- **C — compatibilidade temporária:** merge da API nova com a projecção antiga,
  protegido por feature flag, deduplicado e com data de remoção.

C é a opção mais cara e arriscada. Não adoptar dual-read indefinido.

### DEC-02 — Ordem das duas escritas para artefactos

O contrato recomenda artefacto primeiro, CampaignAction depois. Esta fase deve
seguir essa ordem e definir recuperação de sucesso parcial:

- se o artefacto for criado e CampaignAction falhar, não criar outro artefacto
  num retry cego;
- refetch por `recommendation_ref` + `action_type` antes de repetir;
- apresentar o artefacto já criado e permitir repetir apenas o registo/link;
- não tentar rollback destrutivo de artefactos sem endpoint/contrato próprio.

### DEC-03 — Semântica de reviewed e dismiss

Para uma recommendation ainda sem CampaignAction:

- Mark reviewed cria `action_type=mark_reviewed`; o backend cria-a completed;
- Dismiss cria `action_type=dismiss` com `dismiss_reason`; o backend cria-a
  dismissed.

Para uma CampaignAction já existente, as operations semânticas actuam sobre o
id da action. Não criar uma action fictícia para depois chamar a operação.

### DEC-04 — Múltiplas actions por recommendation

O frontend não deve continuar a assumir um único match. Deve modelar
`CampaignAction[]` por recommendation. O backend permite tipos diferentes e
retries após estados não activos.

## 8. Backlog incremental

### FE-CAI-001 — Congelar contrato e rollout

**Objectivo:** transformar DEC-01 a DEC-04 em decisões executáveis antes de
alterar queries.

Tarefas:

- confirmar OpenAPI usado pela equipa;
- escolher backfill, corte temporal ou compatibilidade temporária;
- definir feature flag/cutover se necessário;
- definir comportamento de partial success no fluxo artefacto -> action;
- confirmar copy para reviewed, dismissed e actions terminais;
- registar que `asset_request` continua futuro e sem execução automática.

Critérios de aceitação:

- decisões documentadas;
- owner e data de remoção definidos para qualquer compatibilidade temporária;
- nenhum histórico desaparece acidentalmente.

Dependências: nenhuma. Bloqueia FE-CAI-005 e rollout de escrita.

### FE-CAI-002 — Remodelar entity CampaignAction

**Objectivo:** substituir o tipo de projecção pelo contrato persistente real.

Tarefas:

- criar DTO/model para todos os campos públicos;
- usar enums exactos de action type, status, priority e source;
- remover `artifactKind`, `rawStatus` e status `unknown` do contrato canónico;
- substituir `type`, `campaignId`, `createdAt` pelos campos reais ou mapper
  explícito;
- modelar FKs relacionadas nullable;
- modelar create/update payloads e campos read-only/imutáveis;
- manter `asset_request` fora do union persistível;
- actualizar labels/badges sem normalização de status de artefactos.

Critérios de aceitação:

- tipos não inventam campos;
- TypeScript impede PUT/DELETE e alteração de campos imutáveis nos payloads;
- `dismiss_reason` e timestamps terminais estão representados.

Dependências: FE-CAI-001 apenas para decisões de naming/rollout.

### FE-CAI-003 — Implementar API e hooks directos

**Objectivo:** fazer a entity chamar apenas `/campaign-actions/`.

Tarefas:

- GET list paginada com filtros;
- GET detail;
- POST create;
- PATCH parcial;
- POST mark-reviewed/dismiss/cancel/complete;
- criar query keys com workspace + campaign + filtros;
- invalidar list/detail após mutations;
- preservar `AbortSignal` se o padrão do cliente for evoluído para o suportar;
- mapear erros 400 existentes para `ValidationError`;
- remover `Promise.allSettled` dos três endpoints da entity.

Critérios de aceitação:

- um GET substitui as três listagens agregadas;
- headers continuam fornecidos apenas pelo `apiClient` central;
- 401/403/404/400 são apresentados pelo sistema de erros existente;
- nenhum header interno é aceite ou enviado.

Dependências: FE-CAI-002.

### FE-CAI-004 — Tratar paginação sem truncar silenciosamente

**Objectivo:** respeitar o envelope paginado do Backend Core.

Tarefas:

- decidir entre paginação visível, infinite query ou carregamento explícito de
  páginas;
- não assumir que `page_size=100` contém toda a campanha;
- preservar ordenação `-created_at`;
- garantir que matching de recommendations conhece páginas ainda não carregadas;
- evitar concluir “não existe action” enquanto a pesquisa exacta por
  `recommendation_ref` não tiver sido feita.

Critérios de aceitação:

- painel não perde actions depois da primeira página;
- deduplicação não depende de uma lista parcial;
- loading/error de páginas adicionais é explícito.

Dependências: FE-CAI-003.

### FE-CAI-005 — Cortar o read path do CampaignActionsPanel

**Objectivo:** apresentar CampaignActions persistentes.

Tarefas:

- consumir a query nova por campaign;
- actualizar copy de “operational artifacts” para acções persistentes;
- mostrar title, action type, status, priority, source e created_at;
- mostrar completed_at/cancelled_at/dismiss_reason quando relevantes;
- indicar artefactos relacionados sem inferir relação por metadata;
- manter loading/error/empty state;
- aplicar a decisão de histórico de FE-CAI-001;
- remover projecção/normalização antiga quando o cutover terminar.

Critérios de aceitação:

- ids mostrados são CampaignAction ids;
- painel não agrega reports/media kits/content pack requests;
- falha da API não afecta os restantes painéis da War Room.

Dependências: FE-CAI-001, FE-CAI-003 e FE-CAI-004.

### FE-CAI-006 — Construir recommendation snapshot seguro

**Objectivo:** enviar contexto histórico mínimo e válido.

Tarefas:

- manter derivação defensiva de `recommendation_ref`;
- criar builder allowlist para title, label, action, type, description, reason,
  priority, confidence e id quando seguro;
- nunca copiar o objecto integral de intelligence;
- garantir object não vazio para todos os tipos excepto manual task;
- normalizar priority para `low|medium|high|urgent`, com default documentado;
- limitar/refusar snapshot demasiado grande antes do POST;
- excluir recursivamente chaves sensíveis conhecidas;
- manter recommendation ref abaixo de 512 caracteres.

Critérios de aceitação:

- payload passa as validações reais do serializer;
- snapshot não contém tokens, authorization, passwords, secrets ou private keys;
- priority livre antiga deixa de ser escrita em metadata.

Dependências: FE-CAI-002.

### FE-CAI-007 — Adaptar CreateActionFromRecommendationDialog

**Objectivo:** criar CampaignAction persistente sem perder a criação de
artefactos já existente.

Tarefas:

- usar title, description, priority e source como campos top-level;
- incluir recommendation ref e snapshot;
- oferecer content pack, report, media kit e manual task;
- manter `asset_request` ausente ou disabled com copy de futuro;
- trocar priority livre por select do enum;
- para manual task, criar apenas CampaignAction;
- para tipos com artefacto, delegar na orquestração FE-CAI-008;
- apresentar field errors usando nomes snake_case reais;
- prevenir double submit, mas tratar o backend como autoridade de deduplicação;
- actualizar copy: CampaignAction não gera artefacto por si só.

Critérios de aceitação:

- POST novo é sempre efectuado para uma criação bem-sucedida;
- manual task passa a funcionar;
- metadata não substitui campos canónicos;
- sucesso actualiza panel e recommendation state.

Dependências: FE-CAI-003 e FE-CAI-006.

### FE-CAI-008 — Orquestrar artefacto e related FK

**Objectivo:** preservar ownership dos endpoints proprietários e formalizar a
relação.

Tarefas:

- extrair POST de report/media kit/content pack request para as respectivas
  entities;
- criar o artefacto primeiro;
- criar CampaignAction com a FK `related_*` correspondente;
- invalidar queries do artefacto e da action;
- representar sucesso parcial sem retry cego;
- permitir completar apenas o segundo passo quando o artefacto já existe;
- garantir campaign/workspace iguais em ambos os passos;
- não criar artefactos para manual/reviewed/dismiss;
- não automatizar Content Renderer, IE ou jobs internos.

Critérios de aceitação:

- cada action de artefacto guarda a FK correcta;
- nenhum POST duplicado é escondido após falha parcial;
- erros cross-workspace/cross-campaign aparecem no campo relacionado;
- `CampaignAction` e artefacto mantêm ids distintos.

Dependências: FE-CAI-007.

### FE-CAI-009 — Refazer matching e RecommendationActionState

**Objectivo:** usar a relação persistente sem impor cardinalidade falsa.

Tarefas:

- ler `recommendation_ref` top-level;
- pesquisar por filtro exacto quando necessário;
- agrupar todas as actions da recommendation;
- distinguir pending, in progress, completed, failed, cancelled, dismissed e
  mark reviewed;
- mostrar reviewed quando `action_type=mark_reviewed` completed;
- mostrar dismissed separadamente de cancelled;
- não esconder todos os tipos porque existe uma action de outro tipo;
- desactivar apenas duplicado activo da mesma ref + action type;
- ao receber 400 de duplicado, refetch e convergir a UI;
- definir apresentação de retries/histórico terminal.

Critérios de aceitação:

- duas actions de tipos diferentes são representáveis;
- concorrência entre tabs não cria estado visual incoerente;
- decisões reviewed/dismissed são visíveis após recálculo da intelligence.

Dependências: FE-CAI-003, FE-CAI-004 e FE-CAI-006.

### FE-CAI-010 — Implementar Mark reviewed e Dismiss

**Objectivo:** activar capabilities antes indisponíveis.

Tarefas:

- adicionar menu/affordances por recommendation;
- Mark reviewed: criar action `mark_reviewed` com snapshot/ref;
- Dismiss: pedir motivo obrigatório e criar action `dismiss`;
- apresentar erros de duplicação/validação;
- confirmar antes de dismiss quando o padrão UX o exigir;
- invalidar CampaignAction list e matching exacto;
- não persistir review state local ou em metadata de artefacto.

Critérios de aceitação:

- ambos sobrevivem a reload;
- dismiss sem motivo é bloqueado localmente e pelo backend;
- estado visual distingue reviewed de dismissed.

Dependências: FE-CAI-006 e FE-CAI-009.

### FE-CAI-011 — Operações de lifecycle no painel

**Objectivo:** permitir updates coerentes com a matriz backend.

Tarefas:

- PATCH para title, description, priority, metadata e `in_progress`;
- usar endpoints semânticos para complete, cancel e dismiss;
- usar mark-reviewed apenas quando a semântica da action o justificar;
- esconder/desactivar transições impossíveis em estados terminais;
- não implementar reopen;
- retry de failed cria nova action segundo decisão UX;
- mostrar completed_at e cancelled_at vindos do servidor.

Critérios de aceitação:

- UI nunca inventa timestamps;
- erro 400 de transição não deixa optimistic state preso;
- terminal continua terminal após reload.

Dependências: FE-CAI-003 e FE-CAI-005.

### FE-CAI-012 — Mostrar e associar artefactos relacionados

**Objectivo:** tornar as FKs formais úteis na War Room.

Tarefas:

- resolver links/detail para request, output, report e media kit;
- mostrar relação no panel e RecommendationActionState quando útil;
- permitir ligar artefacto existente por PATCH, com selector limitado à campaign;
- suportar ContentOutput apenas como relação de `content_pack`;
- impedir combinações incompatíveis na UI, mantendo validação backend;
- tratar FK `null` após remoção do artefacto.

Critérios de aceitação:

- nenhuma relação é inferida por metadata;
- selectors não misturam workspaces/campaigns;
- 400 cross-scope é apresentado sem revelar dados estrangeiros.

Dependências: FE-CAI-003, FE-CAI-005 e APIs de artefactos.

### FE-CAI-013 — RBAC, erros e segurança

**Objectivo:** adaptar o UX às permissions reais sem duplicar autoridade.

Tarefas:

- viewer pode listar mas recebe UI read-only quando a capability local existir;
- backend continua fonte da verdade para `campaigns:update`;
- tratar 400, 401, 403 e 404 com presets existentes;
- não tratar 422 como resposta esperada principal, embora o cliente possa
  continuar tolerante;
- garantir que workspace nunca é enviado no body;
- manter guard contra `X-Internal-Token`;
- grep de URLs/portas internas e secrets;
- não registar snapshot/payload integral em logs.

Critérios de aceitação:

- sem fuga cross-workspace;
- 403 não é apresentado como “não existe” e 404 não revela outro workspace;
- relatórios e logs não contêm credentials ou snapshots integrais.

Dependências: transversal.

### FE-CAI-014 — Testes automatizados da adaptação

**Objectivo:** cobrir mapping e orquestração de maior risco.

Tarefas:

- decidir e adicionar test runner leve, provavelmente Vitest, em item isolado;
- testar DTO/model e status/type labels;
- testar snapshot allowlist e priority normalisation;
- testar list/pagination/filters;
- testar payloads create/update/semantic actions;
- testar matching com múltiplas actions e duplicado activo por tipo;
- testar reviewed/dismissed;
- testar success partial da orquestração em duas etapas;
- testar 400/401/403/404;
- evitar testes dependentes de ordenação sem ordering explícito.

Critérios de aceitação:

- testes críticos automatizados passam;
- `pnpm lint` e `pnpm build` passam;
- a introdução de tooling não fica escondida dentro de uma alteração funcional.

Dependências: pode começar em FE-CAI-002 e acompanhar cada incremento.

### FE-CAI-015 — Limpeza, documentação e validação real

**Objectivo:** remover o modo legado e provar o novo contrato.

Tarefas:

- remover projecções, `RAW_STATUS_MAP`, `rawStatus`, `artifactKind` e metadata
  conventions quando já não houver compatibilidade activa;
- actualizar arquitectura/estado frontend;
- executar lint, build e testes;
- validar com Backend Core real: login, workspace, list/create/detail/PATCH,
  filtros, manual task, artefacto relacionado, mark reviewed e dismiss;
- validar 401/403/404/400 e cross-workspace;
- validar UI da War Room sem browser apenas se possível; browser fica para fase
  própria quando autorizado;
- documentar decisão/backfill efectivamente aplicado.

Critérios de aceitação:

- nenhum GET agregado antigo alimenta CampaignActionsPanel;
- nenhuma criação escreve recommendation ref apenas em metadata;
- validação real e limitações ficam registadas;
- feature flag temporária removida ou com owner/data de remoção.

Dependências: todos os itens de rollout.

## 9. Ordem recomendada

```text
Incremento 0 — decisões
  FE-CAI-001

Incremento 1 — contrato/read path
  FE-CAI-002 -> FE-CAI-003 -> FE-CAI-004 -> FE-CAI-005

Incremento 2 — criação persistente
  FE-CAI-006 -> FE-CAI-007 -> FE-CAI-008

Incremento 3 — recommendation state e decisões
  FE-CAI-009 -> FE-CAI-010

Incremento 4 — lifecycle e relações
  FE-CAI-011 -> FE-CAI-012

Transversal
  FE-CAI-013 + FE-CAI-014

Fecho
  FE-CAI-015
```

Cada incremento deve manter build utilizável. Não remover o read path antigo
antes de aplicar DEC-01.

## 10. Ficheiros prováveis a alterar na fase futura

### Existentes

```text
src/entities/campaign-action/model.ts
src/entities/campaign-action/campaign-action-api.ts
src/entities/campaign-action/helpers.ts
src/entities/campaign-action/query-keys.ts
src/entities/campaign-action/useCampaignActions.ts
src/entities/campaign-action/useCreateCampaignAction.ts
src/entities/campaign-action/useUpdateCampaignAction.ts
src/entities/campaign-action/recommendation-ref.ts
src/entities/campaign-action/index.ts

src/features/campaign-actions/action-type-options.ts
src/features/campaign-actions/recommendation-action-draft.ts
src/features/campaign-actions/recommendation-action-match.ts
src/features/campaign-actions/CreateActionFromRecommendationButton.tsx
src/features/campaign-actions/CreateActionFromRecommendationDialog.tsx
src/features/campaign-actions/RecommendationActionState.tsx
src/features/campaign-actions/campaign-actions.module.css

src/widgets/campaign-actions-panel/CampaignActionsPanel.tsx
src/widgets/campaign-actions-panel/CampaignActionsPanel.module.css
src/pages/campaign-war-room/CampaignWarRoomPage.tsx
```

APIs/entities de reports, media kits, content pack requests e content outputs
podem precisar de funções de create/detail para retirar essa responsabilidade de
`campaign-action-api.ts`.

### Prováveis novos ficheiros

```text
src/entities/campaign-action/campaign-action-mapper.ts
src/entities/campaign-action/useCampaignAction.ts
src/entities/campaign-action/useCampaignActionTransition.ts
src/features/campaign-actions/useCreateActionFromRecommendation.ts
src/features/campaign-actions/recommendation-snapshot.ts
src/features/campaign-actions/DismissRecommendationDialog.tsx
```

Os nomes finais devem seguir a convenção real no momento da implementação.

## 11. Riscos

| ID | Risco | Impacto | Mitigação |
| --- | --- | --- | --- |
| FE-CAI-R01 | Histórico antigo desaparece no cutover | Alto | DEC-01 antes do read cutover |
| FE-CAI-R02 | Artefacto criado e action falha | Alto | partial-success explícito; retry só do link/action |
| FE-CAI-R03 | Action criada mas status do artefacto diverge | Médio | mostrar estados separados; não inferir sincronização |
| FE-CAI-R04 | Lista paginada causa falso “não existe” | Alto | filtro exacto por ref e paginação real |
| FE-CAI-R05 | Ref derivada muda após recálculo | Alto | preferir id da recommendation; snapshot; documentar natureza opaca |
| FE-CAI-R06 | UI bloqueia tipos legítimos por match único | Médio | modelar múltiplas actions e dedup por tipo |
| FE-CAI-R07 | Priority livre gera 400 | Médio | normalização + select enum |
| FE-CAI-R08 | Snapshot inclui dados sensíveis | Crítico | allowlist, limite e testes |
| FE-CAI-R09 | Viewer vê affordance de escrita | Médio | capability UX + 403 autoritativo |
| FE-CAI-R10 | Dual-read permanece indefinidamente | Alto | feature flag com owner/data de remoção |
| FE-CAI-R11 | Falta de testes causa regressão silenciosa | Alto | FE-CAI-014 incremental |
| FE-CAI-R12 | Frontend assume que POST action cria artefacto | Alto | orquestração explícita e copy correcta |

## 12. Fora do escopo desta fase

- alterações no Backend Core, Intelligence Engine ou renderers;
- `asset_request` automático;
- workflow engine, scheduler, WebSockets ou Kanban completo;
- sincronização automática de status action/artefacto;
- backfill executado pelo browser;
- criação ou rollback destrutivo de artefactos sem contrato;
- envio de secrets ou internal tokens;
- frontend como fonte da verdade de RBAC/transições;
- assumir que recommendation ref é id persistente do Intelligence Engine.

## 13. Definição de concluído da futura fase

A integração só fica concluída quando:

- CampaignActionsPanel lê `/campaign-actions/`;
- toda criação bem-sucedida persiste CampaignAction;
- manual task, mark reviewed e dismiss funcionam e sobrevivem a reload;
- artefactos novos ficam ligados por `related_*`;
- recommendation snapshot é mínimo e seguro;
- deduplicação por ref + action type converge com o backend;
- paginação não perde actions;
- o destino do histórico antigo está resolvido;
- lint, build, testes e smoke HTTP real passam;
- não existem chamadas directas a IE/Renderer nem `X-Internal-Token`;
- limitações remanescentes estão documentadas sem as apresentar como feature.
