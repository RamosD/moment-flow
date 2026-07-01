# Pipeline: Campaign Actions Backend Integration

## Prompt 01 (opus) — Congelar decisões de rollout

```prompt
Iteração 01

Objectivo:
Fechar as decisões de rollout da fase `03_campaign_actions_backend_integration` antes de alterar código frontend, garantindo que a migração para `/api/v1/campaign-actions/` não apaga histórico, não cria dual-read indefinido e não introduz comportamento ambíguo.

Contexto:
- Backlog: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao
- Backend CampaignAction API persistente já foi implementada no Backend Core.
- O frontend actual ainda representa CampaignAction como projecção best-effort sobre:
  - content-pack-requests;
  - reports;
  - media-kits.
- Esta fase deve migrar para a API real:
  - GET/POST/PATCH /api/v1/campaign-actions/
  - POST /api/v1/campaign-actions/{id}/mark-reviewed/
  - POST /api/v1/campaign-actions/{id}/dismiss/
  - POST /api/v1/campaign-actions/{id}/cancel/
  - POST /api/v1/campaign-actions/{id}/complete/

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog completo.
- Lê a documentação backend da CampaignAction API, se existir:
  backend_core\docs\campaign_actions\arquitectura_campaign_actions_backend.md
  backend_core\docs\campaign_actions\estado_campaign_actions_backend.md
- Lê o estado final da fase frontend anterior:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\estado_campaign_actions_recommendation_to_execution.md
- Inspecciona a implementação actual do frontend em:
  - src/entities/campaign-action/
  - src/features/campaign-actions/
  - src/widgets/campaign-actions-panel/
  - src/pages/campaign-war-room/
- Não alterar código runtime neste prompt.
- Criar a pasta de resultados se não existir.
- Fechar e documentar as decisões abaixo:

DEC-01 — Histórico e backfill:
- Escolher uma opção:
  A. backfill backend;
  B. corte temporal explícito;
  C. compatibilidade temporária com feature flag.
- Se não houver instrução contrária, adoptar corte temporal explícito como decisão inicial:
  - Campaign Actions Panel passa a mostrar apenas CampaignActions reais;
  - artefactos antigos continuam visíveis nos painéis próprios;
  - não implementar dual-read indefinido.
- Documentar impacto e riscos.

DEC-02 — Ordem das duas escritas:
- Adoptar artefacto primeiro, CampaignAction depois.
- Se o artefacto for criado e CampaignAction falhar:
  - não repetir automaticamente o POST do artefacto;
  - permitir retry apenas do registo/link CampaignAction;
  - refetch por recommendation_ref + action_type antes de repetir.

DEC-03 — Reviewed / Dismiss:
- Para recommendation sem CampaignAction:
  - mark reviewed cria CampaignAction action_type=mark_reviewed;
  - dismiss cria CampaignAction action_type=dismiss com dismiss_reason.
- Para CampaignAction existente:
  - usar endpoints semânticos sobre o id da action.
- Não persistir review/dismiss em metadata de artefactos.

DEC-04 — Múltiplas actions por recommendation:
- Permitir múltiplas CampaignActions por recommendation.
- Deduplicar apenas por recommendation_ref + action_type, alinhado com o backend.
- Não manter o comportamento antigo de “primeiro match bloqueia todos os tipos”.

Resultado esperado:
- Documento curto com decisões fechadas.
- Indicação clara do impacto sobre read path, create path, matching, reviewed/dismiss e histórico.
- Nenhuma alteração runtime.

Validações:
- Não usar browser.
- Não arrancar servidores.
- Não executar build/lint se nenhum código runtime foi alterado.
- Verificar que o relatório não contém secrets.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_01_congelar_decisoes_rollout_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução: executado, executado_parcialmente, bloqueado, falhado ou sem_alteracoes;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 02 (opus) — Remodelar entity CampaignAction

```prompt
Iteração 02

Objectivo:
Remodelar `entities/campaign-action` para representar o contrato persistente real da API `/api/v1/campaign-actions/`, substituindo o modelo de projecção best-effort sobre artefactos.

Contexto:
- Backlog: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao
- Relatório anterior:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_01_congelar_decisoes_rollout_resultado.md
- Entity actual:
  src/entities/campaign-action/

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e o relatório do Prompt 01.
- Inspecciona a API backend implementada e documentação disponível.
- Remodelar `entities/campaign-action` para o contrato real.
- A entity deve deixar de representar:
  - id do artefacto como id da action;
  - artifactKind como campo canónico;
  - rawStatus como campo canónico;
  - status unknown como valor persistente;
  - agregação de reports/media-kits/content-pack-requests.
- Representar campos reais da API:
  - id;
  - workspace;
  - campaign;
  - recommendation_ref;
  - recommendation_snapshot;
  - title;
  - description;
  - action_type;
  - status;
  - priority;
  - source;
  - dismiss_reason;
  - metadata;
  - related_content_pack_request;
  - related_content_output;
  - related_report;
  - related_media_kit;
  - created_by;
  - completed_at;
  - cancelled_at;
  - created_at;
  - updated_at.
- Usar enums exactos:
  - action_type: content_pack, report_request, media_kit_request, manual_task, mark_reviewed, dismiss;
  - status: pending, in_progress, completed, failed, dismissed, cancelled;
  - priority: low, medium, high, urgent;
  - source: recommendation, manual.
- Manter asset_request fora do union persistível.
- Criar DTO snake_case e mapper explícito se o frontend usar model camelCase.
- Se o projecto preferir manter snake_case nas entities, seguir o padrão existente.
- Criar payloads:
  - CreateCampaignActionPayload;
  - UpdateCampaignActionPayload;
  - DismissCampaignActionPayload;
  - CampaignActionTransitionPayload, se útil.
- Campos imutáveis não devem aparecer em update payload:
  - campaign;
  - recommendation_ref;
  - recommendation_snapshot;
  - action_type;
  - source.
- Campos read-only não devem aparecer em create/update payload:
  - id;
  - workspace;
  - created_by;
  - completed_at;
  - cancelled_at;
  - created_at;
  - updated_at.
- Actualizar labels/badges/helpers para os novos enums.
- Não implementar chamadas de API neste prompt, salvo ajustes mínimos necessários para o build.
- Não alterar UI de War Room ainda.
- Não alterar IE/Renderer.
- Não usar browser.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
- Se falhar por referências ainda dependentes do modelo antigo, ajustar compatibilidade mínima ou exports temporários, sem manter semântica falsa.
- Se ambiente falhar, registar pendência sem troubleshooting prolongado.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_02_remodelar_entity_campaign_action_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 03 (opus) — Implementar API e hooks directos

```prompt
Iteração 03

Objectivo:
Implementar a camada de API e hooks para consumir directamente `/api/v1/campaign-actions/`, removendo da entity a agregação antiga de artefactos.

Contexto:
- Backlog: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao
- Relatórios anteriores:
  - prompt_01_congelar_decisoes_rollout_resultado.md
  - prompt_02_remodelar_entity_campaign_action_resultado.md

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- Actualizar `campaign-action-api.ts` para chamar apenas endpoints reais:
  - GET /campaign-actions/
  - GET /campaign-actions/{id}/
  - POST /campaign-actions/
  - PATCH /campaign-actions/{id}/
  - POST /campaign-actions/{id}/mark-reviewed/
  - POST /campaign-actions/{id}/dismiss/
  - POST /campaign-actions/{id}/cancel/
  - POST /campaign-actions/{id}/complete/
- Remover da entity a responsabilidade de chamar:
  - /content-pack-requests/
  - /reports/
  - /media-kits/
- Manter esses endpoints apenas nas respectivas entities, se já existirem, ou criar entities mínimas em prompts posteriores.
- Implementar hooks:
  - useCampaignActions;
  - useCampaignAction;
  - useCreateCampaignAction;
  - useUpdateCampaignAction;
  - useCampaignActionTransition.
- Implementar filtros reais:
  - campaign;
  - status;
  - action_type;
  - recommendation_ref;
  - source;
  - created_by.
- Respeitar envelope paginado do Backend Core.
- Query keys devem incluir:
  - workspaceId;
  - campaignId;
  - filtros;
  - page/page_size quando aplicável.
- Mutations devem invalidar:
  - lista por campaign;
  - detalhe da action;
  - queries exactas por recommendation_ref quando existirem.
- Mapear 400 do backend para ValidationError, mantendo tolerância existente a 422 se o cliente já a suporta.
- Garantir que headers continuam a vir apenas do apiClient central.
- Não enviar workspace no body.
- Não aceitar nem enviar X-Internal-Token.
- Não alterar UI ainda, salvo o mínimo para compilar.
- Não usar browser.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
- Executar greps:
  - X-Internal-Token;
  - INTERNAL_API_TOKEN;
  - intelligence_engine;
  - content_renderer;
  - localhost:8201;
  - localhost:8202.
- Se ambiente falhar, registar pendência sem troubleshooting prolongado.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_03_api_hooks_directos_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 04 (opus) — Migrar read path do painel

```prompt
Iteração 04

Objectivo:
Migrar o `CampaignActionsPanel` e o read path da War Room para consumir CampaignActions persistentes via `/campaign-actions/`, sem agregar artefactos antigos.

Contexto:
- Backlog: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao
- Relatórios anteriores:
  - prompt_01_congelar_decisoes_rollout_resultado.md
  - prompt_02_remodelar_entity_campaign_action_resultado.md
  - prompt_03_api_hooks_directos_resultado.md

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- Actualizar `CampaignActionsPanel` para consumir a query nova por campaign.
- O painel deve mostrar CampaignAction persistente, não artefacto projectado.
- Mostrar:
  - title;
  - action_type;
  - status;
  - priority;
  - source;
  - created_at;
  - completed_at;
  - cancelled_at;
  - dismiss_reason quando relevante;
  - related_* quando existir.
- Remover copy que sugira “operational artifacts” como fonte primária.
- Aplicar decisão de histórico do Prompt 01:
  - se corte temporal explícito foi escolhido, não fazer dual-read;
  - se outra decisão foi escolhida, implementar apenas o que foi documentado.
- Não inferir relações por metadata.
- Manter loading/error/empty state.
- Garantir que falha da CampaignAction API não quebra:
  - Campaign Header;
  - Intelligence;
  - Content Outputs;
  - Reports;
  - Media Kits.
- Actualizar `CampaignWarRoomPage` para fornecer dados novos.
- Não mexer ainda no create dialog, salvo adaptação mínima para compilar.
- Não usar browser por defeito.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
- Se houver UI alterada mas browser não for indispensável, documentar que validação visual fica para prompt final.
- Se ambiente falhar, registar pendência sem troubleshooting prolongado.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_04_migrar_read_path_painel_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 05 (opus) — Tratar paginação e matching exacto

```prompt
Iteração 05

Objectivo:
Garantir que a paginação da CampaignAction API não causa truncamento silencioso nem falso “não existe action”, especialmente no matching por recommendation_ref.

Contexto:
- Backlog: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao
- Relatórios anteriores da fase.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- Inspeccionar o formato paginado real já usado pelo frontend noutros endpoints.
- Garantir que `useCampaignActions` respeita:
  - count;
  - next;
  - previous;
  - results;
  - page;
  - page_size, se aplicável.
- Decidir implementação mínima:
  - page_size=100 para listagem inicial, se aceitável para MVP;
  - ou paginação visível;
  - ou infinite query.
- Não assumir que a primeira página contém todas as actions.
- Para matching por recommendation_ref:
  - implementar query exacta por campaign + recommendation_ref quando necessário;
  - não concluir “sem action” se a lista parcial não carregou todas as páginas;
  - preparar query key específica.
- Preservar ordering default `-created_at`.
- Evitar regressão visual no painel.
- Não usar browser por defeito.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
- Validar por inspecção que não há truncamento silencioso por slice hardcoded.
- Se ambiente falhar, registar pendência.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_05_paginacao_matching_exacto_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 06 (opus) — Criar snapshot seguro

```prompt
Iteração 06

Objectivo:
Criar builder seguro de `recommendation_snapshot` e normalização de `recommendation_ref`/priority para payloads reais de CampaignAction.

Contexto:
- Backlog: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao
- Relatórios anteriores da fase.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- Inspeccionar a estrutura real de CampaignRecommendation no frontend.
- Manter derivação defensiva de recommendation_ref:
  - preferir id da recommendation quando existir;
  - fallback para campaignId + índice + title/action/type;
  - garantir limite máximo de 512 caracteres.
- Criar builder allowlist para recommendation_snapshot.
- Incluir apenas campos seguros e úteis:
  - id;
  - title;
  - label;
  - action;
  - type;
  - description;
  - reason;
  - priority;
  - confidence.
- Não copiar o objecto integral de intelligence.
- Excluir recursivamente chaves sensíveis conhecidas:
  - token;
  - access_token;
  - refresh_token;
  - api_key;
  - password;
  - secret;
  - authorization;
  - private_key;
  - client_secret;
  - internal_api_token;
  - X-Internal-Token.
- Garantir que snapshot é object não vazio para todos os tipos excepto manual_task.
- Garantir tamanho defensivo inferior a 65 536 bytes.
- Normalizar priority para:
  - low;
  - medium;
  - high;
  - urgent.
- Definir default documentado, preferencialmente medium.
- Remover uso de priority livre em metadata para novas CampaignActions.
- Não alterar create dialog ainda, salvo integração do builder se for simples e segura.
- Não usar browser.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
- Se houver test runner, criar testes unitários para snapshot/priority; se não houver, documentar pendência para prompt de testes.
- Grep para garantir que snapshot não serializa recommendation inteira por padrão.
- Se ambiente falhar, registar pendência.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_06_snapshot_seguro_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 07 (opus) — Adaptar Create Action Dialog

```prompt
Iteração 07

Objectivo:
Adaptar o `CreateActionFromRecommendationDialog` para criar CampaignAction persistente, mantendo a criação de artefactos existentes quando aplicável.

Contexto:
- Backlog: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao
- Relatórios anteriores da fase.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- Actualizar action type options:
  - content_pack;
  - report_request;
  - media_kit_request;
  - manual_task;
  - mark_reviewed, se tratado noutro fluxo;
  - dismiss, se tratado noutro fluxo;
  - asset_request deve continuar ausente ou disabled como futuro.
- Adaptar o diálogo para usar campos top-level:
  - title;
  - description;
  - priority;
  - source;
  - recommendation_ref;
  - recommendation_snapshot.
- Trocar priority livre por Select do enum:
  - low;
  - medium;
  - high;
  - urgent.
- Para manual_task:
  - criar apenas CampaignAction.
- Para content_pack/report/media_kit:
  - preparar chamada para orquestração do Prompt 08;
  - não deixar o dialog chamar directamente APIs proprietárias dentro da entity campaign-action.
- Adaptar field errors para nomes reais snake_case:
  - recommendation_ref;
  - recommendation_snapshot;
  - related_report;
  - related_media_kit;
  - related_content_pack_request;
  - dismiss_reason;
  - priority.
- Prevenir double submit.
- Em caso de erro 400 de duplicado, mostrar mensagem clara e preparar refetch.
- Não usar metadata como substituto de campos canónicos.
- Não usar browser por defeito.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
- Se o fluxo ainda depender do Prompt 08 para submit completo, manter estado honesto e documentar.
- Se ambiente falhar, registar pendência.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_07_adaptar_create_action_dialog_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 08 (opus) — Orquestrar artefacto e CampaignAction

```prompt
Iteração 08

Objectivo:
Implementar a orquestração real em duas etapas para criar artefacto proprietário e depois criar CampaignAction com a FK `related_*` correspondente, tratando sucesso parcial sem duplicar artefactos.

Contexto:
- Backlog: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao
- Relatórios anteriores da fase.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- Criar ou adaptar camada de feature:
  - features/campaign-actions/useCreateActionFromRecommendation.ts
- POST proprietários devem viver nas respectivas entities:
  - content-pack-requests;
  - reports;
  - media-kits.
- Se essas functions ainda estiverem em campaign-action-api.ts, mover ou duplicar temporariamente com plano de limpeza documentado.
- Fluxo obrigatório:
  1. criar artefacto quando action_type for content_pack/report_request/media_kit_request;
  2. criar CampaignAction com related_content_pack_request/related_report/related_media_kit;
  3. invalidar queries do artefacto e de CampaignAction.
- Para manual_task:
  - criar CampaignAction sem artefacto.
- Para mark_reviewed/dismiss:
  - não criar artefacto.
- Tratar sucesso parcial:
  - se artefacto foi criado e CampaignAction falhou, não repetir POST do artefacto automaticamente;
  - expor estado de erro com informação suficiente para retry apenas da CampaignAction;
  - antes de repetir, refetch por campaign + recommendation_ref + action_type.
- Garantir campaign/workspace iguais em ambos os passos.
- Não tentar rollback destrutivo de artefactos.
- Não chamar IE/Renderer.
- Não usar X-Internal-Token.
- Não usar browser por defeito.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
- Se possível, validar por testes unitários ou por inspecção que não há retry cego do artefacto.
- Se ambiente falhar, registar pendência.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_08_orquestrar_artefacto_campaign_action_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 09 (opus) — Refazer matching por recommendation

```prompt
Iteração 09

Objectivo:
Refazer o matching entre recommendation e CampaignActions persistentes, suportando múltiplas actions por recommendation e deduplicação por action_type.

Contexto:
- Backlog: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao
- Relatórios anteriores da fase.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- Actualizar:
  - recommendation-action-match;
  - RecommendationActionState;
  - CreateActionFromRecommendationButton;
  - RecommendationsList integration, se necessário.
- Usar `recommendation_ref` top-level da CampaignAction.
- Agrupar todas as actions por recommendation_ref.
- Não assumir match único.
- Uma recommendation pode ter actions diferentes:
  - content_pack;
  - report_request;
  - media_kit_request;
  - manual_task;
  - mark_reviewed;
  - dismiss.
- Deduplicar/desactivar apenas o mesmo action_type quando existir action activa:
  - pending;
  - in_progress;
  - completed.
- Permitir retry/criação nova quando action anterior estiver:
  - failed;
  - dismissed;
  - cancelled.
- Mostrar estados:
  - pending;
  - in_progress;
  - completed;
  - failed;
  - cancelled;
  - dismissed;
  - reviewed.
- Mostrar reviewed quando action_type=mark_reviewed e status=completed.
- Mostrar dismissed separadamente de cancelled.
- Ao receber erro 400 de duplicado:
  - refetch exacto por recommendation_ref + action_type;
  - convergir UI para a action existente.
- Não inferir relação por metadata.
- Não bloquear todos os tipos só porque um tipo já existe.
- Não usar browser por defeito.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
- Se houver test runner, criar testes unitários para matching.
- Se não houver, documentar pendência para Prompt 12.
- Se ambiente falhar, registar pendência.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_09_matching_recommendation_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 10 (sonnet) — Activar reviewed e dismiss

```prompt
Iteração 10

Objectivo:
Activar Mark Reviewed e Dismiss no frontend usando CampaignAction persistente, sem persistência local falsa e sem metadata de artefactos.

Contexto:
- Backlog: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao
- Relatórios anteriores da fase.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- Adicionar affordances por recommendation:
  - Mark reviewed;
  - Dismiss.
- Mark reviewed:
  - se não existir CampaignAction do tipo mark_reviewed activa, criar CampaignAction com action_type=mark_reviewed;
  - backend deve devolver status completed.
- Dismiss:
  - pedir dismiss_reason obrigatório;
  - criar CampaignAction com action_type=dismiss;
  - backend deve devolver status dismissed.
- Se houver CampaignAction existente e a operação semântica fizer sentido sobre id:
  - usar endpoint correspondente apenas quando a semântica estiver clara.
- Não criar action fictícia só para depois chamar endpoint semântico.
- Não persistir reviewed/dismissed em local state, localStorage ou metadata de artefacto.
- Tratar:
  - 400 dismiss sem motivo;
  - 400 duplicado activo;
  - 401;
  - 403;
  - 404.
- Invalidar CampaignAction list e queries exactas por recommendation_ref.
- Mostrar reviewed e dismissed após reload.
- Não usar browser por defeito.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
- Se houver test runner, cobrir reviewed/dismiss.
- Se não houver, documentar pendência.
- Se ambiente falhar, registar pendência.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_10_reviewed_dismiss_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 11 (sonnet) — Lifecycle e artefactos relacionados

```prompt
Iteração 11

Objectivo:
Expor operações de lifecycle e relações formais com artefactos no Campaign Actions Panel, respeitando a matriz de transições do backend.

Contexto:
- Backlog: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao
- Relatórios anteriores da fase.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- No Campaign Actions Panel, adicionar ou ajustar:
  - complete;
  - cancel;
  - dismiss, se aplicável a action existente;
  - PATCH de campos editáveis, se já houver UI para isso;
  - visualização de completed_at;
  - visualização de cancelled_at;
  - visualização de dismiss_reason.
- Esconder/desactivar transições impossíveis em estados terminais:
  - completed;
  - failed;
  - dismissed;
  - cancelled.
- Não implementar reopen.
- Retry de failed deve criar nova CampaignAction segundo decisão UX documentada; não reabrir a antiga.
- Mostrar artefactos relacionados:
  - related_content_pack_request;
  - related_content_output;
  - related_report;
  - related_media_kit.
- Não inferir relações por metadata.
- Se for permitido ligar artefacto existente por PATCH:
  - selector deve ser limitado à campaign actual;
  - não misturar workspaces/campaigns;
  - aceitar que backend é autoridade final.
- Tratar FK null, caso artefacto tenha sido apagado.
- Não usar browser por defeito.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
- Se houver test runner, cobrir pelo menos helpers de transição.
- Se ambiente falhar, registar pendência.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_11_lifecycle_artefactos_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 12 (opus) — Segurança, erros e testes

```prompt
Iteração 12

Objectivo:
Endurecer segurança, tratamento de erros e cobertura automatizada da adaptação Campaign Actions Backend Integration.

Contexto:
- Backlog: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao
- Relatórios anteriores da fase.
- O backlog regista que o frontend não tinha test runner automatizado. Se isso ainda for verdade, introduzir tooling leve apenas se for seguro e isolado.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- Rever:
  - API client;
  - campaign-action entity;
  - create flow;
  - matching;
  - reviewed/dismiss;
  - lifecycle;
  - panel;
  - War Room integration.
- Confirmar erros:
  - 400 validation;
  - 401 session;
  - 403 permission;
  - 404 not found/cross-workspace;
  - network error;
  - service unavailable, se aplicável.
- Confirmar que 403 não é mostrado como 404.
- Confirmar que 404 não revela dados cross-workspace.
- Confirmar que workspace nunca é enviado no body.
- Confirmar que frontend não envia:
  - X-Internal-Token;
  - INTERNAL_API_TOKEN.
- Executar greps:
  - X-Internal-Token;
  - INTERNAL_API_TOKEN;
  - intelligence_engine;
  - content_renderer;
  - localhost:8201;
  - localhost:8202;
  - Bearer hardcoded;
  - api_key;
  - password;
  - private_key.
- Se não existir test runner:
  - avaliar introdução de Vitest em alteração isolada;
  - se for simples e compatível, adicionar;
  - se for arriscado, não adicionar e documentar pendência.
- Testes desejados, se houver runner:
  - DTO/model mapping;
  - labels/status/type;
  - snapshot allowlist;
  - priority normalisation;
  - payload create/update;
  - semantic action payloads;
  - matching com múltiplas actions;
  - duplicado activo;
  - reviewed/dismissed;
  - partial success da orquestração.
- Não usar browser por defeito.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
  - testes, se existirem ou forem adicionados.
- Se ambiente falhar, registar pendência sem troubleshooting prolongado.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_12_seguranca_erros_testes_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 13 (opus) — Validar integração real

```prompt
Iteração 13

Objectivo:
Validar a integração real frontend ↔ Backend Core da nova CampaignAction API, com browser permitido, sem mocks runtime e sem declarar sucesso se o ambiente não permitir.

Contexto:
- Backlog: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao
- Relatórios anteriores da fase.
- Este prompt permite browser/validação visual porque a alteração afecta UI/UX e fluxo end-to-end.
- Portas esperadas:
  - Backend Core: localhost:8100
  - Frontend Vite: localhost:5200

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- Confirmar Backend Core real em localhost:8100:
  - GET /api/v1/schema/ 200;
  - GET /api/v1/docs/ 200;
  - /admin/ existe;
  - serviço não é FastAPI/uvicorn errado.
- Confirmar frontend em localhost:5200.
- Confirmar:
  - VITE_BACKEND_API_BASE_URL=http://localhost:8100/api/v1.
- Garantir dados dev mínimos:
  - user;
  - workspace;
  - campaign;
  - recommendations visíveis ou condição dev documentada;
  - pelo menos um content pack activo, se for validar content_pack.
- Validar no browser quando possível:
  - login;
  - workspace;
  - campaigns;
  - War Room;
  - CampaignActionsPanel lendo /campaign-actions/;
  - criar manual task;
  - mark reviewed;
  - dismiss com motivo;
  - criar report action;
  - criar media kit action;
  - criar content pack action, se houver catálogo;
  - ver related_* no painel;
  - reload e persistência;
  - deduplicação por ref + action_type;
  - múltiplas actions de tipos diferentes na mesma recommendation.
- Validar via Network/API que:
  - GET /campaign-actions/ é usado;
  - não há GET agregado antigo a alimentar o CampaignActionsPanel;
  - POST /campaign-actions/ é usado nas criações bem-sucedidas;
  - endpoints proprietários são chamados apenas para criar artefactos, não para representar a action.
- Validar erros:
  - 400 duplicado;
  - 400 dismiss sem motivo;
  - 401;
  - 403, se fácil;
  - 404;
  - cross-workspace se possível sem complexidade excessiva.
- Não expor tokens ou passwords no relatório.
- Se browser/Chrome extension/Vite/Python/spawn falhar por limitação ambiental:
  - registar validação como pendente;
  - não fazer troubleshooting prolongado;
  - continuar com evidência API possível.

Validações técnicas:
- Executar:
  - pnpm lint
  - pnpm build
  - testes, se existirem.
- Se backend for usado e houver alteração backend, executar:
  - python manage.py check.
- Executar greps de segurança.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_13_validar_integracao_real_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 14 (sonnet) — Limpar legado e documentar

```prompt
Iteração 14

Objectivo:
Remover legado da projecção best-effort quando o cutover estiver validado, actualizar documentação e deixar o estado da fase honesto.

Contexto:
- Backlog: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao
- Relatórios anteriores da fase.
- Só executar limpeza definitiva se os prompts anteriores confirmaram que o read path e create path novos estão funcionais ou que a decisão de rollout permite o corte.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e todos os relatórios anteriores.
- Confirmar decisão de histórico do Prompt 01.
- Se o corte temporal explícito estiver activo:
  - remover projecções antigas que alimentavam CampaignActionsPanel;
  - remover RAW_STATUS_MAP, rawStatus e artifactKind se já não forem usados;
  - remover metadata conventions como fonte de action;
  - manter apenas metadata como dado auxiliar, não contrato.
- Se compatibilidade temporária foi decidida:
  - garantir feature flag, owner e data de remoção documentados;
  - não remover código necessário ainda;
  - marcar dívida explicitamente.
- Actualizar ou criar:
  - frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\arquitectura_campaign_actions_backend_integration.md
  - frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\estado_campaign_actions_backend_integration.md
- Documentar:
  - escopo entregue;
  - contrato usado;
  - decisões de rollout;
  - histórico/backfill/cutover;
  - read path;
  - create path;
  - snapshot seguro;
  - reviewed/dismiss;
  - lifecycle;
  - related artefacts;
  - testes;
  - validação real;
  - limitações;
  - pronto/não pronto para piloto;
  - pronto/não pronto para produção.
- Não declarar produção-ready.
- Não usar browser.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
  - testes, se existirem.
- Verificar que docs não contêm tokens reais.
- Verificar greps de segurança.
- Se ambiente falhar, registar pendência.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_14_limpar_legado_documentar_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 15 (sonnet) — Fechar estado final

```prompt
Iteração 15

Objectivo:
Fechar a fase `03_campaign_actions_backend_integration` com relatório final consolidado, estado honesto e próximos passos claros.

Contexto:
- Backlog: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao
- Documentos esperados:
  - frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\arquitectura_campaign_actions_backend_integration.md
  - frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\estado_campaign_actions_backend_integration.md
- Relatórios anteriores da fase.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e todos os relatórios da fase.
- Lê a arquitectura e o estado gerados no Prompt 14.
- Inspecciona o código final.
- Criar ou actualizar:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_15_estado_final_resultado.md
- Garantir que o estado final indica claramente:
  - implementado e validado;
  - implementado mas não validado por ambiente;
  - não implementado;
  - pendente para backend;
  - pendente para produto.
- Confirmar:
  - CampaignActionsPanel lê /campaign-actions/;
  - toda criação bem-sucedida persiste CampaignAction;
  - manual task funciona, se implementado;
  - mark reviewed funciona;
  - dismiss funciona;
  - artefactos novos ficam ligados por related_*;
  - recommendation_snapshot é mínimo e seguro;
  - deduplicação converge com backend;
  - paginação não perde actions;
  - destino do histórico antigo está resolvido;
  - lint/build/testes passaram ou pendências estão documentadas;
  - sem chamadas directas a IE/Renderer;
  - sem X-Internal-Token.
- Não declarar produção-ready sem evidência.
- Se validação real ficou pendente, o estado deve reflectir isso e não declarar fase totalmente concluída.
- Não alterar runtime salvo documentação.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
  - testes, se existirem.
- Verificar que documentos não contêm tokens reais.
- Executar greps de segurança.
- Não usar browser.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\resultados_execucao\prompt_15_estado_final_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```
