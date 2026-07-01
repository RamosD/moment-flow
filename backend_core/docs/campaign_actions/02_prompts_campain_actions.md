# Pipeline: Backend CampaignAction API

## Prompt 01 (opus) — Investigar padrões backend

```prompt
Iteração 01

Objectivo:
Investigar os padrões actuais do Backend Core para implementar uma API persistente de CampaignAction sem quebrar arquitectura, permissões, contratos existentes ou comportamento validado.

Contexto:
- Backlog: backend_core\docs\campaign_actions\01_backlog.md
- Pasta de resultados: backend_core\docs\campaign_actions\resultados_execucao
- Esta fase nasce da limitação detectada no frontend: Campaign Actions existem apenas como projecção best-effort sobre content-pack-requests, reports e media-kits.
- O objectivo desta fase é criar uma entidade persistente CampaignAction no Backend Core.
- O frontend deve continuar a chamar apenas o Backend Core.
- Não alterar Intelligence Engine nem Content Renderer.
- Não introduzir X-Internal-Token em APIs públicas.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog completo.
- Inspecciona a estrutura actual de backend_core.
- Identifica os padrões existentes para:
  - apps Django;
  - models workspace-scoped;
  - WorkspaceOwnedModel ou equivalente;
  - WorkspaceScopedRBACViewSet ou equivalente;
  - serializers;
  - filters;
  - permissions;
  - routers;
  - schema OpenAPI;
  - testes.
- Inspecciona em detalhe:
  - apps/campaigns;
  - apps/content;
  - apps/reports;
  - apps/workspaces;
  - apps/core;
  - config/urls.py;
  - settings;
  - factories/test utilities, se existirem.
- Confirmar se CampaignAction deve ficar:
  - numa nova app dedicada, por exemplo campaign_actions;
  - ou dentro de apps/campaigns.
- Confirmar como o projecto define:
  - workspace;
  - campaign;
  - user/created_by;
  - metadata JSON;
  - timestamps;
  - filtros por workspace;
  - validação cross-workspace.
- Confirmar se já existe app audit ou events utilizável, mas não integrar nesta iteração.
- Identificar riscos de migração.
- Identificar convenções de nomes, choices/enums, migrations e testes.
- Não alterar código runtime neste prompt.
- Criar a pasta de resultados se não existir.

Resultado esperado:
- Decisão técnica sobre localização da implementação.
- Lista de padrões a seguir.
- Lista de ficheiros prováveis a alterar nos próximos prompts.
- Riscos e bloqueios registados.
- Nenhuma alteração runtime.

Validações:
- Não usar browser.
- Não arrancar servidores, salvo necessidade de leitura leve já existente.
- Não fazer troubleshooting de ambiente.
- Não executar migrations.
- Pode executar comandos de inspecção e testes rápidos apenas se forem úteis e seguros.

Registo de execução:
- Criar ou actualizar:
  backend_core\docs\campaign_actions\resultados_execucao\prompt_01_investigar_padroes_backend_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução: executado, executado_parcialmente, bloqueado, falhado ou sem_alteracoes;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 02 (opus) — Criar modelo CampaignAction

```prompt
Iteração 01

Objectivo:
Criar a entidade persistente CampaignAction e a migration correspondente, respeitando os padrões identificados no Backend Core.

Contexto:
- Backlog: backend_core\docs\campaign_actions\01_backlog.md
- Pasta de resultados: backend_core\docs\campaign_actions\resultados_execucao
- Relatório anterior esperado:
  backend_core\docs\campaign_actions\resultados_execucao\prompt_01_investigar_padroes_backend_resultado.md

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e o relatório do Prompt 01.
- Se o Prompt 01 registou bloqueio real, não avances sem resolver a causa.
- Criar a app/módulo CampaignAction no local decidido no Prompt 01.
- Criar model CampaignAction seguindo os padrões do projecto.
- Campos mínimos esperados:
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
  - created_by, se o padrão do projecto suportar;
  - completed_at;
  - cancelled_at;
  - created_at;
  - updated_at.
- Usar JSONField conforme padrão existente.
- Usar TextChoices ou padrão equivalente para:
  - action_type;
  - status;
  - priority;
  - source.
- Estados mínimos:
  - pending;
  - in_progress;
  - completed;
  - failed;
  - dismissed;
  - cancelled.
- Tipos mínimos:
  - content_pack;
  - report_request;
  - media_kit_request;
  - manual_task;
  - mark_reviewed;
  - dismiss.
- Validar se asset_request deve ficar fora ou como tipo futuro. Se incluído, marcar claramente como futuro/sem execução automática.
- Criar indexes para:
  - workspace + campaign;
  - workspace + campaign + recommendation_ref;
  - status;
  - action_type;
  - created_at.
- Avaliar constraint anti-duplicação:
  - workspace + campaign + recommendation_ref + action_type para estados activos.
- Se a constraint parcial for arriscada ou incompatível com SQLite/dev, documentar e adiar para validação em serializer/service.
- Criar migration.
- Não alterar serializers/viewsets ainda, salvo o mínimo para a app carregar.
- Não alterar frontend.
- Não alterar IE/Renderer.

Validações:
- Executar:
  - python manage.py makemigrations
  - python manage.py migrate
  - python manage.py check
- Se houver testes rápidos existentes relacionados com models/core, executar apenas se forem seguros.
- Se ambiente Python falhar por limitação local, registar como pendente e não fazer troubleshooting prolongado.

Registo de execução:
- Criar ou actualizar:
  backend_core\docs\campaign_actions\resultados_execucao\prompt_02_criar_model_campaign_action_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 03 (opus) — Criar serializers e validações

```prompt
Iteração 01

Objectivo:
Criar serializers seguros para CampaignAction, incluindo validação de workspace, campaign, artefactos relacionados, status e dismiss_reason.

Contexto:
- Backlog: backend_core\docs\campaign_actions\01_backlog.md
- Pasta de resultados: backend_core\docs\campaign_actions\resultados_execucao
- Relatórios anteriores:
  - prompt_01_investigar_padroes_backend_resultado.md
  - prompt_02_criar_model_campaign_action_resultado.md

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e os relatórios anteriores.
- Inspecciona serializers existentes em campaigns, content, reports e workspaces.
- Criar serializers para CampaignAction conforme padrão do projecto.
- Pode ser um serializer único ou serializers separados para read/create/update, conforme padrão existente.
- Garantir campos read-only adequados:
  - id;
  - workspace, se derivado de campaign/workspace activo;
  - created_by;
  - created_at;
  - updated_at;
  - completed_at, quando calculado;
  - cancelled_at, quando calculado.
- Validar que campaign pertence ao workspace activo.
- Validar que related_content_pack_request pertence ao mesmo workspace e campaign.
- Validar que related_content_output pertence ao mesmo workspace e campaign.
- Validar que related_report pertence ao mesmo workspace e campaign.
- Validar que related_media_kit pertence ao mesmo workspace e campaign.
- Validar action_type.
- Validar status.
- Validar dismiss_reason quando:
  - action_type = dismiss;
  - ou status = dismissed.
- Validar recommendation_ref:
  - obrigatório quando action_type não for manual_task;
  - opcional para manual_task, se fizer sentido.
- Validar recommendation_snapshot:
  - aceite como JSON;
  - não obrigatório para manual_task;
  - não expor dados sensíveis.
- Validar metadata como JSON livre, sem assumir schema rígido.
- Se houver regra anti-duplicação não implementada no model, implementar validação de duplicado activo no serializer ou service.
- Não criar viewset ainda, salvo se o padrão exigir import mínimo.
- Não alterar frontend.

Validações:
- Executar:
  - python manage.py check
- Executar testes existentes relevantes, se forem rápidos.
- Se ainda não houver testes, registar pendência para prompt de testes.
- Não usar browser.

Registo de execução:
- Criar ou actualizar:
  backend_core\docs\campaign_actions\resultados_execucao\prompt_03_criar_serializers_validacoes_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 04 (opus) — Criar API e rotas

```prompt
Iteração 01

Objectivo:
Expor a API REST pública autenticada de CampaignAction no Backend Core, com list/create/detail/patch, filtros e workspace scoping.

Contexto:
- Backlog: backend_core\docs\campaign_actions\01_backlog.md
- Pasta de resultados: backend_core\docs\campaign_actions\resultados_execucao
- Relatórios anteriores:
  - prompt_01_investigar_padroes_backend_resultado.md
  - prompt_02_criar_model_campaign_action_resultado.md
  - prompt_03_criar_serializers_validacoes_resultado.md

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- Inspecciona viewsets workspace-scoped existentes.
- Criar CampaignActionViewSet conforme padrão do projecto.
- Registar endpoint:
  - GET /api/v1/campaign-actions/
  - POST /api/v1/campaign-actions/
  - GET /api/v1/campaign-actions/{id}/
  - PATCH /api/v1/campaign-actions/{id}/
- Garantir autenticação JWT conforme padrão.
- Garantir exigência de X-Workspace-ID se esse for o padrão dos endpoints workspace-scoped.
- Garantir filtro por workspace activo.
- Garantir que lista não devolve dados cross-workspace.
- Adicionar filtros:
  - campaign;
  - status;
  - action_type;
  - recommendation_ref;
  - source;
  - created_by, se aplicável.
- Ordenação recomendada:
  - created_at desc.
- Garantir paginação se o projecto usa paginação.
- Garantir integração com schema OpenAPI.
- Não criar endpoints internos.
- Não usar X-Internal-Token.
- Não alterar IE/Renderer.
- Não alterar frontend ainda.

Validações:
- Executar:
  - python manage.py check
- Confirmar, se possível sem arrancar servidor:
  - rotas registadas;
  - schema local gerável, se houver comando existente.
- Se seguro e simples, arrancar Backend Core e confirmar:
  - GET /api/v1/schema/
  - presença de /api/v1/campaign-actions/
- Se ambiente falhar, registar pendência sem troubleshooting prolongado.

Registo de execução:
- Criar ou actualizar:
  backend_core\docs\campaign_actions\resultados_execucao\prompt_04_criar_api_rotas_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 05 (opus) — Implementar transições de estado

```prompt
Iteração 01

Objectivo:
Implementar regras de transição de estado para CampaignAction, incluindo completed_at, cancelled_at, dismiss_reason e operações semânticas quando forem consistentes com o projecto.

Contexto:
- Backlog: backend_core\docs\campaign_actions\01_backlog.md
- Pasta de resultados: backend_core\docs\campaign_actions\resultados_execucao
- Relatórios anteriores da fase.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- Inspecciona padrões existentes para status/transições em content-pack-requests, reports e media-kits.
- Definir transições permitidas, mantendo simplicidade.
- Estados mínimos:
  - pending;
  - in_progress;
  - completed;
  - failed;
  - dismissed;
  - cancelled.
- Implementar validação de status:
  - bloquear status inválido;
  - bloquear transições inválidas, se a regra for segura;
  - exigir dismiss_reason para dismissed;
  - preencher completed_at quando status passar a completed;
  - preencher cancelled_at quando status passar a cancelled;
  - limpar ou preservar timestamps conforme decisão documentada.
- Decidir se usar:
  - PATCH simples;
  - actions custom mark-reviewed, dismiss, cancel, complete.
- Recomendação:
  - usar PATCH para actualizações simples;
  - usar action custom apenas se já for padrão no projecto.
- Se criar actions custom, garantir schema e testes.
- Não criar workflow engine.
- Não automatizar geração de artefactos.
- Não alterar frontend.

Validações:
- Executar:
  - python manage.py check
- Executar testes relevantes existentes, se houver.
- Se houver endpoint funcional, validar via API simples apenas se ambiente estiver disponível.
- Não usar browser.

Registo de execução:
- Criar ou actualizar:
  backend_core\docs\campaign_actions\resultados_execucao\prompt_05_transicoes_estado_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 06 (opus) — Integrar artefactos relacionados

```prompt
Iteração 01

Objectivo:
Garantir que CampaignAction pode apontar formalmente para artefactos reais existentes, com validação de workspace e campaign.

Contexto:
- Backlog: backend_core\docs\campaign_actions\01_backlog.md
- Pasta de resultados: backend_core\docs\campaign_actions\resultados_execucao
- Relatórios anteriores da fase.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- Inspecciona os models/serializers/viewsets de:
  - ContentPackRequest;
  - ContentOutput;
  - Report;
  - MediaKit;
  - Campaign.
- Confirmar os campos reais de campaign/workspace em cada artefacto.
- Garantir que CampaignAction valida:
  - related_content_pack_request pertence à mesma campaign/workspace;
  - related_content_output pertence à mesma campaign/workspace;
  - related_report pertence à mesma campaign/workspace;
  - related_media_kit pertence à mesma campaign/workspace.
- Se algum artefacto não tiver campaign obrigatória ou tiver semântica diferente, ajustar validação ao código real e documentar.
- Garantir que action_type é compatível com related_*:
  - content_pack deve apontar preferencialmente para content_pack_request;
  - report_request deve apontar preferencialmente para report;
  - media_kit_request deve apontar preferencialmente para media_kit.
- Não obrigar related_* no momento de criação, salvo decisão clara.
- Não criar artefactos automaticamente neste prompt.
- Não duplicar responsabilidade dos endpoints existentes.
- Não alterar frontend.

Validações:
- Executar:
  - python manage.py check
- Executar testes existentes relevantes, se houver.
- Criar validações unitárias apenas se a estrutura de testes já estiver clara; caso contrário, deixar para Prompt 07.
- Não usar browser.

Registo de execução:
- Criar ou actualizar:
  backend_core\docs\campaign_actions\resultados_execucao\prompt_06_integrar_artefactos_relacionados_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 07 (opus) — Criar testes backend

```prompt
Iteração 01

Objectivo:
Criar testes backend para cobrir os contratos críticos da API CampaignAction.

Contexto:
- Backlog: backend_core\docs\campaign_actions\01_backlog.md
- Pasta de resultados: backend_core\docs\campaign_actions\resultados_execucao
- Relatórios anteriores da fase.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- Inspecciona a estrutura actual de testes.
- Criar testes seguindo o padrão existente do projecto.
- Cobrir pelo menos:
  - listar actions por workspace;
  - criar action válida;
  - consultar detail;
  - actualizar action;
  - bloquear sem autenticação;
  - bloquear sem X-Workspace-ID, se aplicável;
  - bloquear campaign fora do workspace;
  - bloquear related artefact fora do workspace;
  - bloquear related artefact fora da campaign, se aplicável;
  - validar action_type inválido;
  - validar status inválido;
  - validar dismiss sem motivo;
  - filtrar por campaign;
  - filtrar por recommendation_ref;
  - filtrar por status;
  - filtrar por action_type;
  - impedir duplicação óbvia se regra existir.
- Criar fixtures/factories apenas se seguirem padrão existente.
- Não fazer testes frágeis dependentes de ordem sem ordering explícito.
- Não alterar comportamento runtime fora do necessário para os testes passarem.
- Não alterar frontend.

Validações:
- Executar testes criados.
- Executar suite relevante da app, se viável.
- Executar:
  - python manage.py check
- Se a suite completa for pesada, executar subset relevante e registar.
- Não usar browser.

Registo de execução:
- Criar ou actualizar:
  backend_core\docs\campaign_actions\resultados_execucao\prompt_07_criar_testes_backend_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 08 (sonnet) — Documentar contrato backend

```prompt
Iteração 01

Objectivo:
Documentar a arquitectura e o contrato real da CampaignAction API no Backend Core.

Contexto:
- Backlog: backend_core\docs\campaign_actions\01_backlog.md
- Pasta de resultados: backend_core\docs\campaign_actions\resultados_execucao
- Documento a criar:
  backend_core\docs\campaign_actions\arquitectura_campaign_actions_backend.md
- Relatórios anteriores da fase.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- Inspecciona o código implementado.
- Criar arquitectura_campaign_actions_backend.md.
- O documento deve reflectir o código real, não apenas o plano.
- Incluir:
  - objectivo da CampaignAction API;
  - localização da implementação;
  - model e campos;
  - action types;
  - status;
  - regras de negócio;
  - endpoints reais;
  - payloads principais;
  - filtros;
  - permissões;
  - workspace scoping;
  - validação cross-workspace;
  - relação com recommendations;
  - recommendation_ref;
  - recommendation_snapshot;
  - relação com content-pack-requests, content-outputs, reports e media-kits;
  - mark_reviewed/dismiss/cancel/complete, se implementado;
  - limitações;
  - riscos;
  - como o frontend deve consumir;
  - o que não fazer.
- Confirmar explicitamente:
  - CampaignAction é API pública autenticada do Backend Core;
  - não usa X-Internal-Token;
  - não chama IE/Renderer directamente.
- Não incluir secrets.
- Não alterar runtime.

Validações:
- Verificar que o documento existe.
- Verificar por grep que não contém tokens reais.
- Executar python manage.py check apenas se algum import/runtime foi afectado.
- Não usar browser.

Registo de execução:
- Criar ou actualizar:
  backend_core\docs\campaign_actions\resultados_execucao\prompt_08_documentar_contrato_backend_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 09 (opus) — Validar API real

```prompt
Iteração 01

Objectivo:
Validar a CampaignAction API em execução real no Backend Core, confirmando schema, auth, workspace scoping, criação, listagem, actualização, filtros e erros principais.

Contexto:
- Backlog: backend_core\docs\campaign_actions\01_backlog.md
- Pasta de resultados: backend_core\docs\campaign_actions\resultados_execucao
- Relatórios anteriores da fase.
- Este prompt permite arranque local do Backend Core porque valida integração real da API.
- Não é necessário browser, salvo se indispensável.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e relatórios anteriores.
- Confirmar que a porta 8000 está livre ou ocupada pelo Backend Core correcto.
- Arrancar Backend Core real em:
  - http://localhost:8000
- Confirmar:
  - GET /api/v1/schema/ responde 200;
  - GET /api/v1/docs/ responde 200;
  - /api/v1/campaign-actions/ aparece no schema;
  - /admin/ existe;
  - serviço não é FastAPI/uvicorn errado.
- Garantir dados dev mínimos:
  - utilizador dev;
  - workspace;
  - campaign;
  - related report/media-kit/content-pack-request, se necessário.
- Validar via API real:
  - login;
  - /auth/me;
  - /workspaces/;
  - GET /campaign-actions/;
  - POST /campaign-actions/;
  - GET /campaign-actions/{id}/;
  - PATCH /campaign-actions/{id}/;
  - filtros campaign/status/action_type/recommendation_ref;
  - dismiss ou mark-reviewed, se implementado;
  - validação de related artefacts, se possível.
- Validar erros:
  - 401;
  - 403, se fácil;
  - 404;
  - 400/422 de validação;
  - ausência de X-Workspace-ID, se aplicável;
  - cross-workspace, se possível sem complexidade excessiva.
- Não expor tokens, passwords ou secrets no relatório.
- Não fazer troubleshooting prolongado de ambiente.
- Se ambiente falhar, registar validação como pendente e continuar com evidência possível.

Validações:
- Executar:
  - python manage.py check
- Executar testes relevantes:
  - testes da app CampaignAction;
  - subset de API relevante.
- Confirmar schema.
- Não usar browser por defeito.

Registo de execução:
- Criar ou actualizar:
  backend_core\docs\campaign_actions\resultados_execucao\prompt_09_validar_api_real_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 10 (opus) — Avaliar impacto no frontend

```prompt
Iteração 01

Objectivo:
Comparar a nova CampaignAction API real com a implementação frontend actual e definir o backlog de adaptação frontend, sem implementar essa adaptação nesta fase backend.

Contexto:
- Backlog backend: backend_core\docs\campaign_actions\01_backlog.md
- Pasta de resultados: backend_core\docs\campaign_actions\resultados_execucao
- Frontend actual:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution
- Futura fase frontend sugerida:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê relatórios backend anteriores.
- Inspecciona a implementação frontend actual de campaign-actions.
- Identificar onde o frontend ainda usa:
  - projecção best-effort;
  - content-pack-requests/reports/media-kits agregados como actions;
  - recommendation_ref em metadata;
  - capabilities disabled por falta de CampaignAction API.
- Comparar com o novo contrato /api/v1/campaign-actions/.
- Definir impacto necessário:
  - entity campaign-action;
  - API hooks;
  - CreateActionFromRecommendationDialog;
  - CampaignActionsPanel;
  - RecommendationActionState;
  - reviewed/dismiss;
  - deduplicação;
  - associação related artefacts.
- Criar backlog frontend de adaptação:
  frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
- O backlog deve ser honesto e incremental.
- Não implementar alterações frontend neste prompt.
- Não alterar código runtime, salvo documentação.
- Não usar browser.

Validações:
- Verificar que o backlog frontend foi criado.
- Verificar que não contém secrets.
- Executar python manage.py check apenas se runtime backend tiver sido tocado.
- Não executar build frontend se nenhum código frontend foi alterado.

Registo de execução:
- Criar ou actualizar:
  backend_core\docs\campaign_actions\resultados_execucao\prompt_10_avaliar_impacto_frontend_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 11 (sonnet) — Fechar estado final

```prompt
Iteração 01

Objectivo:
Fechar a fase Backend Core CampaignAction API com estado final honesto, relatório consolidado e próximos passos claros.

Contexto:
- Backlog: backend_core\docs\campaign_actions\01_backlog.md
- Pasta de resultados: backend_core\docs\campaign_actions\resultados_execucao
- Documento de arquitectura:
  backend_core\docs\campaign_actions\arquitectura_campaign_actions_backend.md
- Estado final a criar:
  backend_core\docs\campaign_actions\estado_campaign_actions_backend.md
- Relatórios anteriores da fase.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Instruções:
- Lê o backlog e todos os relatórios desta fase.
- Lê arquitectura_campaign_actions_backend.md.
- Inspecciona o estado real do código.
- Criar estado_campaign_actions_backend.md com:
  - resumo executivo;
  - escopo entregue;
  - localização da implementação;
  - model criado;
  - endpoints criados;
  - migrations;
  - serializers;
  - viewsets;
  - filtros;
  - permissões;
  - regras de negócio;
  - testes;
  - validações executadas;
  - limitações;
  - impacto no frontend;
  - riscos;
  - pronto/não pronto para piloto;
  - pronto/não pronto para produção;
  - próximos passos.
- Criar ou actualizar relatório final:
  backend_core\docs\campaign_actions\resultados_execucao\prompt_11_estado_final_backend_resultado.md
- A conclusão deve distinguir claramente:
  - implementado e validado;
  - implementado mas não validado por ambiente;
  - não implementado;
  - pendente para frontend.
- Não declarar produção-ready sem evidência.
- Não alterar runtime salvo documentação.

Validações:
- Verificar que estado_campaign_actions_backend.md existe.
- Verificar que relatório final existe.
- Executar:
  - python manage.py check
- Executar testes relevantes da fase se forem rápidos.
- Verificar que documentos não contêm tokens reais.
- Não usar browser.

Registo de execução:
- Criar ou actualizar:
  backend_core\docs\campaign_actions\resultados_execucao\prompt_11_estado_final_backend_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```
