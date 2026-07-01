# Pipeline: Campaign Actions Recommendation-to-Execution

## Prompt 01 (opus) — Investigar contratos reais

```prompt
Iteração 01

Objectivo:
Investigar os contratos reais existentes no repositório para saber se a fase Campaign Actions / Recommendation-to-Execution pode ser implementada com persistência real ou se depende de backlog complementar no Backend Core.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Contexto:
- Backlog: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao
- A fase anterior Frontend Foundation & Campaign War Room MVP está fechada e validada com Backend Core real.
- O frontend deve continuar a chamar apenas o Backend Core.
- O frontend não deve chamar directamente intelligence_engine nem content_renderer.
- O frontend nunca deve enviar X-Internal-Token.

Instruções:
- Lê o backlog completo.
- Lê a documentação da arquitectura frontend existente, se existir.
- Lê o estado final da fase anterior.
- Inspecciona o Backend Core:
  - schema OpenAPI;
  - urls;
  - viewsets;
  - serializers;
  - models;
  - permissões;
  - filtros;
  - testes existentes.
- Procura suporte real para:
  - campaign actions;
  - actions;
  - tasks;
  - action items;
  - recommendations;
  - content packs;
  - content outputs;
  - reports;
  - media kits;
  - generation jobs;
  - audit/event logs.
- Confirma se existem endpoints reais para:
  - listar acções por campanha;
  - criar acção;
  - actualizar estado de acção;
  - associar acção a recommendation;
  - marcar recommendation como reviewed/dismissed;
  - criar content pack/report/media kit a partir de uma recommendation.
- Confirma payloads, responses, permissões e erros possíveis.
- Confirma se a intelligence/recommendations são persistidas ou apenas recalculadas.
- Se houver divergência entre backlog e código, prioriza o código e regista a divergência.
- Se a divergência criar risco real de implementação errada, não implementes nada e regista bloqueio.
- Não alteres código runtime neste prompt.
- Cria a pasta de resultados se não existir.

Resultado esperado:
- Um relatório curto que conclua claramente uma de três opções:
  - Backend Core suporta Campaign Actions reais;
  - Backend Core suporta parcialmente;
  - Backend Core não suporta e será necessário backlog complementar.

Validações:
- Não usar browser.
- Não executar servidores.
- Executar apenas comandos de leitura/inspecção se necessário.
- Não fazer troubleshooting de ambiente.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao\prompt_01_investigar_contratos_reais_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução: executado, executado_parcialmente, bloqueado, falhado ou sem_alteracoes;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 02 (opus) — Modelar acções e camada de dados

```prompt
Iteração 01

Objectivo:
Criar a modelação frontend e a camada de dados para Campaign Actions, apenas se os contratos reais do Backend Core suportarem a funcionalidade. Se não suportarem, preparar estado indisponível honesto sem persistência falsa.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Contexto:
- Backlog: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao
- Relatório anterior esperado:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao\prompt_01_investigar_contratos_reais_resultado.md

Instruções:
- Lê o backlog e o relatório do Prompt 01.
- Se o Prompt 01 concluiu bloqueio por ausência de contrato essencial, não inventes endpoints.
- Se houver contrato real:
  - criar ou completar entity campaign-action;
  - criar tipos alinhados ao Backend Core real;
  - criar CampaignAction;
  - criar CampaignActionStatus;
  - criar CampaignActionType;
  - criar CampaignActionSource;
  - criar RecommendationRef;
  - criar payloads de create/update conforme o contrato real;
  - criar helpers de label/status/badge.
- Criar camada de API apenas para endpoints reais:
  - listagem por campanha;
  - criação;
  - update/status, se existir.
- Criar hooks com TanStack Query:
  - useCampaignActions;
  - useCreateCampaignAction;
  - useUpdateCampaignAction, se suportado.
- Query keys devem incluir workspaceId e campaignId quando aplicável.
- Invalidar queries relevantes após criação/actualização.
- Se o backend não suportar persistência:
  - criar apenas tipos internos para ActionIntent/Draft;
  - não criar chamadas falsas;
  - preparar export claro de capacidade indisponível.
- Respeitar a arquitectura existente:
  - entities não devem importar features;
  - shared não deve importar camadas superiores.
- Não chamar IE/Renderer.
- Não usar X-Internal-Token.
- Não usar browser.

Validações:
- Executar no frontend:
  - pnpm lint
  - pnpm build
- Se npm/pnpm/Vite falhar por limitação de ambiente, registar validação como pendente e não fazer troubleshooting de ambiente.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao\prompt_02_modelar_acoes_dados_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 03 (sonnet) — Criar UI base e draft de acção

```prompt
Iteração 01

Objectivo:
Criar os componentes UI mínimos e a lógica defensiva para transformar uma recommendation flexível num draft de acção, sem criar ainda o fluxo completo de submissão.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Contexto:
- Backlog: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao
- Relatórios anteriores:
  - prompt_01_investigar_contratos_reais_resultado.md
  - prompt_02_modelar_acoes_dados_resultado.md

Instruções:
- Lê o backlog e os relatórios anteriores.
- Inspecciona os componentes existentes em shared/ui.
- Criar apenas os componentes necessários para esta fase, por exemplo:
  - Dialog ou Modal;
  - Select;
  - Textarea;
  - FormField;
  - InlineFieldError;
  - ConfirmDialog, se necessário.
- Manter CSS Modules + design tokens.
- Não instalar UI framework pesado.
- Não criar design system grande.
- Garantir acessibilidade básica:
  - label;
  - foco;
  - aria quando aplicável;
  - botão cancel/confirm;
  - fechar modal por acção clara.
- Criar helper/hook para draft de acção a partir de recommendation:
  - extrair title/action/label;
  - extrair description/reason;
  - extrair priority/confidence;
  - gerar recommendation_ref defensivo;
  - sugerir action_type quando possível;
  - tolerar campos ausentes;
  - não assumir shape fixo.
- Se recommendations não tiverem id persistente, documentar limitação no código/comentário curto quando necessário e no resultado.
- Não fazer submissão ao backend neste prompt, salvo se já existir código trivial e seguro que faça parte do draft.
- Não usar browser por defeito.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
- Se o ambiente falhar, registar pendência sem troubleshooting de ambiente.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao\prompt_03_ui_draft_acao_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 04 (opus) — Implementar criação de acção na War Room

```prompt
Iteração 01

Objectivo:
Implementar o fluxo principal recommendation-to-action na War Room, usando apenas contratos reais do Backend Core. Se o backend não suportar Campaign Actions, implementar estado indisponível honesto sem persistência falsa.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Contexto:
- Backlog: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao
- Relatórios anteriores:
  - prompt_01_investigar_contratos_reais_resultado.md
  - prompt_02_modelar_acoes_dados_resultado.md
  - prompt_03_ui_draft_acao_resultado.md

Instruções:
- Lê o backlog e os relatórios anteriores.
- Inspecciona a implementação actual da Campaign War Room e da Campaign Intelligence feature.
- Adicionar affordance de execução nas recommendations:
  - botão Create action, Convert to action ou equivalente;
  - estado disabled se backend não suportar actions;
  - copy honesta quando indisponível.
- Criar ou completar feature campaign-actions:
  - CreateActionFromRecommendationButton;
  - CreateActionFromRecommendationDialog;
  - RecommendationActionState;
  - helpers necessários.
- Se houver endpoint real:
  - submeter payload real;
  - tratar loading;
  - tratar sucesso;
  - tratar 401/403/404/422/502/503;
  - invalidar campaign actions e dados relacionados;
  - evitar duplicação óbvia se já existir associação.
- Se não houver endpoint real:
  - não criar mocks runtime;
  - não simular sucesso;
  - mostrar funcionalidade indisponível com explicação clara.
- Não alterar contratos backend sem necessidade.
- Não chamar IE/Renderer directamente.
- Não expor X-Internal-Token.
- Não usar browser por defeito.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
- Se houver alteração backend necessária e directamente relacionada, executar:
  - python manage.py check
- Se ambiente falhar, registar pendência sem troubleshooting de ambiente.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao\prompt_04_criar_acao_war_room_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 05 (opus) — Implementar painel Campaign Actions

```prompt
Iteração 01

Objectivo:
Criar o painel Campaign Actions na War Room e associar visualmente recommendations ao estado das acções, usando persistência real quando existir.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Contexto:
- Backlog: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao
- Relatórios anteriores da fase.

Instruções:
- Lê o backlog e os relatórios anteriores.
- Criar widget campaign-actions-panel.
- Se existir endpoint real:
  - listar acções da campanha;
  - mostrar título;
  - tipo;
  - status;
  - priority;
  - source;
  - data de criação;
  - relação com recommendation quando existir.
- Tratar:
  - loading;
  - error;
  - empty;
  - workspace ausente;
  - sem permissão;
  - serviço indisponível.
- Se não existir endpoint real:
  - mostrar painel com estado honesto de indisponibilidade;
  - não usar mocks runtime;
  - não mostrar dados falsos.
- Associar recommendation ao estado da acção quando possível:
  - usar recommendation_ref real;
  - se não houver id persistente, usar chave derivada defensiva apenas para UI;
  - documentar limitações;
  - evitar duplicação óbvia.
- Integrar o painel na War Room sem quebrar os painéis existentes.
- Garantir que falha em actions não quebra intelligence, outputs, reports ou media kits.
- Não chamar IE/Renderer.
- Não usar browser por defeito.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
- Se ambiente falhar, registar pendência sem troubleshooting de ambiente.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao\prompt_05_painel_campaign_actions_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 06 (sonnet) — Implementar reviewed e dismissed

```prompt
Iteração 01

Objectivo:
Implementar suporte a Mark Reviewed e Dismiss apenas se houver suporte real no Backend Core. Caso contrário, documentar lacuna e manter UI honesta.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Contexto:
- Backlog: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao
- Relatórios anteriores da fase.

Instruções:
- Lê o backlog e relatórios anteriores.
- Confirmar novamente se o Backend Core suporta:
  - reviewed;
  - dismissed;
  - motivo de dismiss;
  - update de status;
  - criação de action com tipo mark_reviewed ou dismiss.
- Se suportar:
  - adicionar acções UI para reviewed/dismiss;
  - pedir motivo no dismiss, se contrato suportar;
  - submeter payload real;
  - invalidar queries;
  - actualizar estado visual da recommendation.
- Se não suportar:
  - não persistir estado falso;
  - mostrar a opção indisponível ou omitir a acção;
  - registar lacuna no resultado.
- Tratar 401/403/404/422/502/503.
- Não usar browser por defeito.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
- Se ambiente falhar, registar pendência sem troubleshooting de ambiente.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao\prompt_06_reviewed_dismissed_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 07 (sonnet) — Endurecer erros e segurança

```prompt
Iteração 01

Objectivo:
Rever a experiência de erros, permissões e segurança da feature Campaign Actions, garantindo que a War Room não quebra e que não há exposição de dados sensíveis.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Contexto:
- Backlog: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao
- Relatórios anteriores da fase.

Instruções:
- Lê o backlog e relatórios anteriores.
- Rever a feature campaign-actions, widget campaign-actions-panel e integração com RecommendationItem.
- Confirmar tratamento de:
  - 401 sessão expirada;
  - 403 sem permissão;
  - 404 campanha/acção inexistente;
  - 422 validação;
  - 502/503 serviço indisponível;
  - network error;
  - workspace ausente;
  - backend sem suporte para actions.
- Reusar ErrorState e componentes dedicados existentes.
- Garantir que 422 mostra field errors quando aplicável.
- Garantir que falha em actions não quebra:
  - Campaign Header;
  - Intelligence;
  - Content Outputs;
  - Reports;
  - Media Kits.
- Executar greps no frontend para confirmar:
  - X-Internal-Token não é enviado;
  - INTERNAL_API_TOKEN não aparece em runtime frontend;
  - sem chamadas directas a intelligence_engine;
  - sem chamadas directas a content_renderer;
  - sem URLs directas para portas internas dos serviços técnicos;
  - sem secrets reais em src, docs da fase e .env.example.
- Corrigir apenas problemas directamente relacionados.
- Não usar browser por defeito.

Validações:
- Executar:
  - pnpm lint
  - pnpm build
- Se backend foi alterado em prompts anteriores, executar:
  - python manage.py check
- Se ambiente falhar, registar pendência sem troubleshooting de ambiente.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao\prompt_07_erros_seguranca_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 08 (sonnet) — Documentar arquitectura da feature

```prompt
Iteração 01

Objectivo:
Documentar a arquitectura real da feature Campaign Actions / Recommendation-to-Execution, reflectindo o código implementado e as lacunas reais.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Contexto:
- Backlog: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao
- Documento a criar:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\arquitectura_campaign_actions.md
- Relatórios anteriores da fase.

Instruções:
- Lê o backlog e os relatórios anteriores.
- Inspecciona o código final da feature.
- Criar arquitectura_campaign_actions.md.
- O documento deve reflectir o que foi realmente implementado, não apenas o plano.
- Incluir:
  - objectivo da feature;
  - contratos reais usados;
  - endpoints reais;
  - lacunas backend;
  - estrutura frontend criada;
  - entity campaign-action ou alternativa implementada;
  - feature campaign-actions;
  - widget campaign-actions-panel;
  - fluxo recommendation → action;
  - reviewed/dismissed, se existir;
  - tratamento de erros;
  - regras de segurança;
  - o que não fazer;
  - próximos passos.
- Explicar claramente:
  - frontend chama apenas Backend Core;
  - frontend não chama IE;
  - frontend não chama Renderer;
  - X-Internal-Token nunca pertence ao frontend.
- Não incluir secrets.
- Não usar browser.
- Não alterar código runtime.

Validações:
- Verificar que o documento existe.
- Verificar por leitura/grep que não contém tokens reais.
- Não é obrigatório executar build/lint se não houve alteração de código.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao\prompt_08_documentar_arquitectura_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 09 (opus) — Validar integração real

```prompt
Iteração 01

Objectivo:
Validar a feature Campaign Actions / Recommendation-to-Execution contra o Backend Core real, sem mocks runtime, e corrigir apenas falhas directamente relacionadas.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Contexto:
- Backlog: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao
- Relatórios anteriores da fase.
- Não usar browser por defeito em prompts anteriores; neste prompt a validação visual/browser é permitida porque a alteração é UI/UX e integração real.

Instruções:
- Lê o backlog, arquitectura da feature e relatórios anteriores.
- Confirmar Backend Core real em localhost:8100.
- Confirmar frontend em localhost:5200.
- Confirmar VITE_BACKEND_API_BASE_URL=http://localhost:8100/api/v1.
- Fazer login real com utilizador dev/local.
- Seleccionar workspace real.
- Abrir campanha real.
- Abrir War Room.
- Validar:
  - recommendations renderizam;
  - botões de acção aparecem ou estado indisponível honesto aparece;
  - criação real de action funciona, se backend suportar;
  - Campaign Actions Panel lista dados reais, se backend suportar;
  - recommendation mostra estado coerente;
  - reviewed/dismissed funciona, se suportado;
  - outputs/reports/media kits continuam independentes;
  - erros são tratados.
- Se backend não suportar actions:
  - confirmar visualmente que a UI não finge persistência;
  - confirmar mensagem honesta de indisponibilidade;
  - documentar que a fase fica parcialmente aceite como preparação/descoberta.
- Não usar mocks para declarar sucesso.
- Não expor tokens.
- Corrigir apenas falhas directamente relacionadas com esta validação.
- Se browser, Vite, Python, npm, spawn ou ferramenta local falhar por limitação de ambiente:
  - registar validação como pendente;
  - não fazer troubleshooting de ambiente;
  - continuar com o resultado possível.

Validações técnicas:
- Executar:
  - pnpm lint
  - pnpm build
- Se backend foi alterado:
  - python manage.py check
- Executar greps de segurança relevantes.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao\prompt_09_validar_integracao_real_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```

## Prompt 10 (sonnet) — Fechar estado final

```prompt
Iteração 01

Objectivo:
Fechar a fase Campaign Actions / Recommendation-to-Execution com relatório final e estado honesto, sem declarar produção-ready sem evidência.

Fonte de verdade:
1. instruções explícitas e mais recentes do utilizador;
2. código actual do repositório;
3. contratos actuais, tipos, payloads, testes e comportamento existente;
4. backlog referenciado;
5. documentação auxiliar.

Contexto:
- Backlog: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\01_backlog.md
- Pasta de resultados: frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao
- Relatórios anteriores da fase.
- Documento de arquitectura:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\arquitectura_campaign_actions.md
- Estado final a criar:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\estado_campaign_actions_recommendation_to_execution.md
- Relatório final a criar:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao\prompt_10_estado_final_resultado.md

Instruções:
- Lê o backlog e todos os relatórios desta fase.
- Lê a arquitectura da feature.
- Inspecciona o estado real do código.
- Criar estado_campaign_actions_recommendation_to_execution.md com:
  - resumo executivo;
  - escopo entregue;
  - contratos usados;
  - funcionalidades implementadas;
  - funcionalidades não implementadas;
  - lacunas backend;
  - validações executadas;
  - riscos;
  - pronto/não pronto para piloto;
  - pronto/não pronto para produção;
  - próximos passos.
- Criar relatório final em prompt_10_estado_final_resultado.md.
- A conclusão deve distinguir claramente:
  - funcionalidade real com backend;
  - funcionalidade preparada mas indisponível por falta de backend;
  - validação pendente por ambiente.
- Se Campaign Actions reais não existirem no Backend Core, não declarar Recommendation-to-Execution funcional.
- Se a fase ficou apenas preparada, recomendar backlog complementar Backend Core.
- Não usar browser.
- Não alterar código runtime salvo documentação.

Validações:
- Verificar que os documentos finais existem.
- Executar pnpm lint e pnpm build apenas se houve alteração de código neste prompt.
- Verificar que documentos não contêm tokens reais.
- Se validações anteriores falharam ou ficaram pendentes, reflectir isso no estado final.

Registo de execução:
- Criar ou actualizar:
  frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados_execucao\prompt_10_estado_final_resultado.md
- Se o ficheiro já existir, preservar conteúdo anterior e acrescentar nova secção no fim com data/hora.
- Incluir obrigatoriamente:
  - estado da execução;
  - resumo objectivo;
  - ficheiros criados ou alterados;
  - validações executadas e resultado;
  - pendências, riscos ou próximo passo recomendado.
```
