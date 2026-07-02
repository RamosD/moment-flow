
# Pipeline: Staging Campaign Actions with Real IE and Renderer

## Prompt 01 (opus) — Confirmar contratos e configuração real

```prompt
Iteração 1

Objectivo:
Confirmar contratos, variáveis de ambiente, endpoints, healthchecks e fluxos reais entre Backend Core, Intelligence Engine e Content Renderer antes de arrancar a validação staging.

Contexto:
- Fase: 04_staging_campaign_actions_with_real_ie_renderer
- Backlog:
  frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/01_backlog.md
- Pasta de resultados:
  frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/
- Fase anterior:
  frontend/docs/01_fundamentos/03_campaign_actions_backend_integration/
- Portas canónicas:
  - Frontend Web: http://localhost:5200
  - Backend Core: http://localhost:8100
  - Intelligence Engine: http://localhost:8201
  - Content Renderer: http://localhost:8202

Regras:
- Não alterar lógica funcional de produto neste prompt.
- Não arrancar serviços ainda, salvo inspecção leve se já estiverem a correr.
- Não usar mocks para declarar validação real.
- Não expor tokens, passwords ou secrets no relatório.
- O frontend deve continuar a chamar apenas Backend Core.
- O frontend nunca deve chamar IE ou Renderer directamente.
- O frontend nunca deve enviar X-Internal-Token.

Fonte de verdade:
1. instruções explícitas e recentes do utilizador;
2. código actual do repositório;
3. contratos reais, settings, clients, payloads e testes;
4. backlog desta fase;
5. documentação da fase anterior;
6. documentação de portas.

Tarefas:
1. Ler o backlog completo da fase 04.
2. Ler documentos finais da fase 03:
   - estado_campaign_actions_backend_integration.md
   - arquitectura_campaign_actions_backend_integration.md
   - prompt_16_validacao_e2e_real_portas_padronizadas_resultado.md
3. Inspeccionar Backend Core:
   - settings;
   - clients de Intelligence Engine;
   - clients de Content Renderer;
   - variáveis de dry_run;
   - tokens internos service-to-service;
   - timeouts;
   - callbacks;
   - polling;
   - request_id/job_id;
   - endpoints de reports, media kits, content pack requests e content outputs.
4. Inspeccionar Intelligence Engine:
   - porta;
   - healthcheck;
   - endpoint real chamado pelo Backend Core;
   - payload esperado;
   - resposta real;
   - modo dry_run;
   - logs.
5. Inspeccionar Content Renderer:
   - porta;
   - healthcheck;
   - endpoints de job/render;
   - callback para Backend Core;
   - storage local;
   - estados de job;
   - output URLs.
6. Confirmar o nome exacto da variável de dry_run da intelligence.
7. Confirmar se o Renderer é exercitado por:
   - report;
   - media kit;
   - content pack;
   - content output;
   - ou outro fluxo real.
8. Confirmar se o Content Renderer usa callback, polling ou ambos.
9. Confirmar quais estados devem ser esperados:
   - queued;
   - processing;
   - completed;
   - failed;
   - draft;
   - ou equivalentes reais.
10. Registar riscos e decisões pendentes.

Validações:
- Executar apenas comandos seguros de inspecção.
- Executar `python manage.py check` se não exigir serviços externos.
- Não executar E2E.
- Não usar browser.

Registo de execução:
Criar ou actualizar:
frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_01_confirmar_contratos_configuracao_resultado.md

O relatório deve incluir:
- estado da execução: executado, executado_parcialmente, bloqueado, falhado ou sem_alteracoes;
- resumo objectivo;
- mapa real de variáveis;
- endpoints reais identificados;
- healthchecks identificados;
- dry_run: variável e estado esperado;
- fluxos Renderer identificados;
- ficheiros inspeccionados;
- ficheiros alterados, se algum;
- validações executadas;
- riscos;
- próximo passo recomendado.
```

## Prompt 02 (opus) — Arrancar serviços em portas canónicas

```prompt
Iteração 2

Objectivo:
Arrancar e validar os quatro serviços principais nas portas canónicas, garantindo que cada porta corresponde ao serviço correcto.

Contexto:
- Backlog:
  frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/01_backlog.md
- Relatório anterior:
  frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_01_confirmar_contratos_configuracao_resultado.md
- Portas:
  - Frontend Web: http://localhost:5200
  - Backend Core: http://localhost:8100
  - Intelligence Engine: http://localhost:8201
  - Content Renderer: http://localhost:8202

Regras:
- Não validar contra serviço errado.
- Não usar portas antigas como default activo.
- Não fazer troubleshooting prolongado de ambiente.
- Se uma porta estiver ocupada por serviço errado, parar e registar bloqueio.
- Não expor secrets.

Tarefas:
1. Confirmar portas livres ou ocupadas pelo serviço correcto:
   - 5200;
   - 8100;
   - 8201;
   - 8202.
2. Arrancar Backend Core em:
   python manage.py runserver 127.0.0.1:8100
3. Confirmar Backend Core:
   - GET http://localhost:8100/api/v1/schema/ = 200;
   - GET http://localhost:8100/api/v1/docs/ = 200;
   - GET http://localhost:8100/admin/ existe;
   - server header ou conteúdo indica Django, não FastAPI/uvicorn errado.
4. Arrancar Frontend Web em:
   pnpm dev -- --host 127.0.0.1 --port 5200
5. Confirmar Frontend:
   - GET http://localhost:5200/ = 200;
   - Vite usa strictPort;
   - VITE_BACKEND_API_BASE_URL aponta para http://localhost:8100/api/v1.
6. Arrancar Intelligence Engine real em:
   http://localhost:8201
7. Confirmar healthcheck do IE:
   - usar endpoint real identificado no Prompt 01.
8. Arrancar Content Renderer em:
   http://localhost:8202
9. Confirmar healthcheck do Renderer:
   - usar endpoint real identificado no Prompt 01.
10. Confirmar que Backend Core aponta para:
   - INTELLIGENCE_ENGINE_BASE_URL=http://localhost:8201
   - CONTENT_RENDERER_BASE_URL=http://localhost:8202
   - REPORT_RENDERER_BASE_URL=http://localhost:8202
11. Confirmar que o frontend não tem configs para IE/Renderer.
12. Confirmar que não há serviços activos nas portas antigas relevantes.

Validações:
- python manage.py check
- pnpm lint
- pnpm build, se viável
- scripts/check-forbidden-ports.ps1, se existir
- healthchecks HTTP dos quatro serviços

Registo de execução:
Criar ou actualizar:
frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_02_arrancar_servicos_portas_canonicas_resultado.md

O relatório deve incluir:
- estado da execução;
- serviços arrancados;
- portas usadas;
- healthchecks;
- comandos executados;
- bloqueios;
- evidência de que cada serviço é o correcto;
- ficheiros alterados, se algum;
- próximo passo recomendado.
```

## Prompt 03 (opus) — Validar War Room com Intelligence Engine real

```prompt
Iteração 3

Objectivo:
Validar que a War Room recebe intelligence real através do Backend Core, com dry_run desactivado e sem chamada directa do frontend ao Intelligence Engine.

Contexto:
- Backlog:
  frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/01_backlog.md
- Relatórios anteriores:
  - prompt_01_confirmar_contratos_configuracao_resultado.md
  - prompt_02_arrancar_servicos_portas_canonicas_resultado.md

Regras:
- Não usar dry_run para declarar intelligence real.
- Não chamar Intelligence Engine directamente a partir do frontend.
- Não colocar tokens internos no browser.
- Não usar mocks runtime.
- Se IE real não gerar recommendations suficientes, registar limitação e não inventar sucesso.

Tarefas:
1. Confirmar que o Backend Core está configurado com dry_run desactivado.
2. Confirmar IE health em 8201.
3. Confirmar Backend Core em 8100.
4. Confirmar dados dev/staging mínimos:
   - user;
   - workspace;
   - campaign;
   - artist;
   - dados suficientes para intelligence real.
5. Executar via Backend Core:
   POST /api/v1/campaigns/{id}/intelligence/
6. Confirmar que a resposta não é dry_run.
7. Confirmar:
   - source real;
   - status completed ou equivalente;
   - grade/score real quando aplicável;
   - recommendations reais;
   - recommendation fields usados pelo frontend;
   - request_id nos logs.
8. Confirmar no frontend/War Room:
   - recommendations aparecem;
   - estado visual não depende de dry_run;
   - erros IE são isolados.
9. Testar cenário IE indisponível, se simples e seguro:
   - Backend Core deve devolver erro controlado;
   - frontend deve mostrar erro honesto;
   - sem stacktrace sensível.

Validações:
- HTTP real via Backend Core.
- Browser se disponível.
- Grep no frontend para garantir ausência de localhost:8201.
- Logs sem tokens/secrets.

Registo de execução:
Criar ou actualizar:
frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_03_validar_war_room_ie_real_resultado.md

O relatório deve incluir:
- estado da execução;
- dry_run activo/inactivo;
- payload resumido, sem dados sensíveis;
- resposta IE via Backend Core;
- número e tipo de recommendations;
- evidência frontend, se browser usado;
- erros testados;
- logs relevantes sem secrets;
- limitações;
- próximo passo recomendado.
```

## Prompt 04 (opus) — Criar CampaignActions a partir de recommendations reais

```prompt
Iteração 4

Objectivo:
Validar que recommendations reais do Intelligence Engine podem ser convertidas em CampaignActions persistentes.

Contexto:
- Backlog:
  frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/01_backlog.md
- Relatórios anteriores:
  - prompt_01
  - prompt_02
  - prompt_03

Regras:
- Usar recommendations reais vindas da War Room/Backend Core/IE real.
- Não criar actions com refs artificiais para declarar sucesso desta fase, salvo como preparação auxiliar claramente identificada.
- Não copiar payload integral da intelligence para recommendation_snapshot.
- Não usar metadata como fonte canónica.
- Não usar X-Internal-Token no frontend.

Tarefas:
1. Obter recommendations reais na War Room.
2. Escolher pelo menos uma recommendation accionável.
3. Validar recommendation_ref:
   - preferir id real se existir;
   - fallback defensivo documentado, se necessário.
4. Criar manual_task a partir de recommendation real.
5. Criar mark_reviewed a partir de recommendation real.
6. Criar dismiss com motivo a partir de recommendation real.
7. Criar report_request a partir de recommendation real.
8. Criar media_kit_request a partir de recommendation real.
9. Criar content_pack a partir de recommendation real, se houver content pack activo.
10. Confirmar:
   - CampaignAction id próprio;
   - recommendation_ref persistido;
   - recommendation_snapshot mínimo e seguro;
   - action_type correcto;
   - status correcto;
   - priority enum;
   - source=recommendation;
   - related_* quando aplicável.
11. Confirmar reload/persistência.
12. Confirmar múltiplas actions de tipos diferentes na mesma recommendation.
13. Confirmar deduplicação por recommendation_ref + action_type.
14. Confirmar que failed/dismissed/cancelled permitem nova tentativa conforme contrato.

Validações:
- API real.
- Browser se disponível.
- Network deve mostrar frontend -> Backend Core apenas.
- pnpm test/lint/build se o código for alterado.
- python manage.py check se backend for alterado.

Registo de execução:
Criar ou actualizar:
frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_04_campaign_actions_recommendations_reais_resultado.md

O relatório deve incluir:
- estado da execução;
- recommendations usadas;
- actions criadas;
- endpoints chamados;
- payloads resumidos sem secrets;
- related_*;
- deduplicação;
- reload/persistência;
- limitações;
- próximo passo recomendado.
```

## Prompt 05 (opus) — Validar Content Renderer real

```prompt
Iteração 5

Objectivo:
Validar que os artefactos criados por CampaignActions exercitam o Content Renderer real em 8202 e produzem job/output/estado observável.

Contexto:
- Backlog:
  frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/01_backlog.md
- Relatórios anteriores:
  - prompt_01
  - prompt_02
  - prompt_03
  - prompt_04

Regras:
- Não declarar Renderer real validado se apenas artefactos ficarem queued sem chamada ao Renderer.
- Não chamar Renderer directamente a partir do frontend.
- O Backend Core é o único mediador entre frontend e Renderer.
- Não expor internal tokens em logs ou relatórios.
- Não fazer rollback destrutivo de artefactos.

Tarefas:
1. Confirmar Content Renderer health em 8202.
2. Confirmar Backend Core configurado para Renderer em 8202.
3. Criar report action:
   - POST /reports/;
   - POST /campaign-actions/ com related_report;
   - confirmar se Renderer recebe job real.
4. Criar media kit action:
   - POST /media-kits/;
   - POST /campaign-actions/ com related_media_kit;
   - confirmar se Renderer recebe job real.
5. Criar content pack action:
   - POST /content-pack-requests/;
   - POST /campaign-actions/ com related_content_pack_request;
   - confirmar se Renderer recebe job real ou se há etapa posterior necessária.
6. Validar:
   - job_id;
   - request_id;
   - status queued/processing/completed/failed;
   - callback ou polling;
   - output URL ou storage local, quando aplicável;
   - related_* continua coerente.
7. Confirmar que o frontend não chama 8202.
8. Testar Renderer indisponível, se simples e seguro:
   - erro controlado;
   - sem stacktrace sensível;
   - CampaignAction/artefacto fica em estado honesto.

Validações:
- HTTP real via Backend Core.
- Logs Backend Core.
- Logs Renderer.
- Greps de segurança.
- Testes existentes do Renderer, se rápidos:
  npm test
  ou comando real do componente.

Registo de execução:
Criar ou actualizar:
frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_05_validar_content_renderer_real_resultado.md

O relatório deve incluir:
- estado da execução;
- health Renderer;
- jobs criados;
- job_id/request_id;
- outputs;
- estados;
- callbacks/polling;
- erros;
- evidência de que frontend não chamou Renderer;
- limitações;
- próximo passo recomendado.
```

## Prompt 06 (opus) — Validar observabilidade mínima

```prompt
Iteração 6

Objectivo:
Validar observabilidade mínima da cadeia Frontend -> Backend Core -> IE/Renderer, com request_id/job_id e sem exposição de secrets.

Contexto:
- Backlog:
  frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/01_backlog.md
- Relatórios anteriores da fase.

Regras:
- Não colar tokens, passwords, authorization headers ou internal tokens no relatório.
- Não registar payload integral da intelligence.
- Não registar snapshot completo se contiver dados sensíveis.
- Não mascarar falhas de rastreabilidade.

Tarefas:
1. Confirmar request_id no Backend Core para:
   - intelligence request;
   - create CampaignAction;
   - report/media kit/content pack request;
   - renderer job/callback.
2. Confirmar job_id no Renderer quando aplicável.
3. Confirmar logs IE:
   - request recebido;
   - processamento;
   - resposta;
   - sem tokens.
4. Confirmar logs Renderer:
   - job recebido;
   - status;
   - callback/polling;
   - sem tokens.
5. Confirmar correlação mínima:
   - campaign id;
   - action id;
   - artifact id;
   - job id;
   - request id.
6. Confirmar erros 502/503 com mensagens seguras.
7. Confirmar que X-Internal-Token não aparece em logs.
8. Confirmar que snapshots/logs não copiam payload integral do IE.

Validações:
- Inspecção de logs.
- Greps por:
  - X-Internal-Token;
  - Authorization;
  - Bearer;
  - INTERNAL_API_TOKEN;
  - password;
  - private_key;
  - api_key.
- Não usar browser salvo se necessário para gerar fluxo.

Registo de execução:
Criar ou actualizar:
frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_06_observabilidade_minima_resultado.md

O relatório deve incluir:
- estado da execução;
- ids rastreados;
- amostras redigidas de logs;
- lacunas;
- riscos;
- próximo passo recomendado.
```

## Prompt 07 (opus) — Validar erros reais entre serviços

```prompt
Iteração 7

Objectivo:
Validar comportamento real de falhas controladas entre Backend Core, Intelligence Engine e Content Renderer.

Contexto:
- Backlog:
  frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/01_backlog.md
- Relatórios anteriores da fase.

Regras:
- Testar falhas apenas quando for seguro e reversível.
- Não corromper dados.
- Não expor stacktrace sensível ao frontend.
- Não expor secrets.
- Não fazer troubleshooting prolongado.
- Não forçar cenários destrutivos.

Tarefas:
1. Testar IE indisponível:
   - parar IE ou apontar temporariamente para porta inválida, se seguro;
   - chamar intelligence via Backend Core;
   - confirmar 502/503 ou erro controlado;
   - confirmar UI honesta.
2. Testar Renderer indisponível:
   - parar Renderer ou apontar temporariamente para porta inválida, se seguro;
   - criar artefacto que exige Renderer;
   - confirmar estado/erro controlado.
3. Testar timeout, se houver configuração simples.
4. Testar payload inválido para IE/Renderer, se houver endpoint seguro.
5. Testar token interno inválido apenas se for seguro e sem expor valor.
6. Confirmar que CampaignAction/artefacto não fica em estado falso de sucesso.
7. Confirmar que não há retry destrutivo.
8. Restaurar configuração original no fim.

Validações:
- API real.
- Browser opcional.
- Logs redigidos.
- Greps de segurança.
- python manage.py check após restaurar configs, se alteradas.

Registo de execução:
Criar ou actualizar:
frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_07_erros_reais_entre_servicos_resultado.md

O relatório deve incluir:
- estado da execução;
- cenários testados;
- resultados HTTP;
- comportamento UI/API;
- logs redigidos;
- configurações alteradas/restauradas;
- riscos;
- próximo passo recomendado.
```

## Prompt 08 (sonnet) — Validar segurança frontend e Network

```prompt
Iteração 8

Objectivo:
Confirmar que, mesmo com IE e Renderer reais activos, o frontend continua isolado e chama exclusivamente o Backend Core.

Contexto:
- Backlog:
  frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/01_backlog.md
- Relatórios anteriores da fase.

Regras:
- Frontend chama apenas http://localhost:8100/api/v1.
- Frontend não chama 8201.
- Frontend não chama 8202.
- Frontend não envia X-Internal-Token.
- Frontend não contém secrets internos.
- Não declarar segurança validada sem greps e/ou Network.

Tarefas:
1. Inspeccionar .env.local frontend.
2. Inspeccionar env.ts/config frontend.
3. Inspeccionar api client.
4. Executar greps em frontend/src:
   - X-Internal-Token;
   - INTERNAL_API_TOKEN;
   - INTELLIGENCE_ENGINE_BASE_URL;
   - CONTENT_RENDERER_BASE_URL;
   - REPORT_RENDERER_BASE_URL;
   - localhost:8201;
   - localhost:8202;
   - intelligence_engine;
   - content_renderer;
   - Bearer hardcoded;
   - api_key;
   - private_key;
   - password.
5. No browser/Network, se disponível:
   - executar War Room;
   - criar actions;
   - confirmar requests apenas para 8100.
6. Confirmar que `X-Internal-Token` aparece apenas em guard/teste/documentação de proibição.
7. Confirmar que Authorization é apenas Bearer dinâmico no client central.
8. Confirmar que não há portas antigas em runtime.

Validações:
- pnpm test
- pnpm lint
- pnpm build
- scripts/check-forbidden-ports.ps1, se existir

Registo de execução:
Criar ou actualizar:
frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_08_seguranca_frontend_network_resultado.md

O relatório deve incluir:
- estado da execução;
- greps;
- evidência Network, se disponível;
- violações encontradas/corrigidas;
- limitações;
- próximo passo recomendado.
```

## Prompt 09 (opus) — Smoke visual staging

```prompt
Iteração 9

Objectivo:
Executar smoke visual staging no browser, clicando o fluxo principal da War Room com IE real e Renderer real.

Contexto:
- Backlog:
  frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/01_backlog.md
- Relatórios anteriores da fase.
- Este prompt permite browser e validação visual.

Regras:
- Não usar mocks runtime.
- Não usar dry_run para declarar sucesso.
- Não usar IE/Renderer directos no frontend.
- Não declarar smoke visual se apenas API foi validada.
- Se o browser estiver bloqueado por ambiente, registar bloqueio e não declarar sucesso visual.

Tarefas:
1. Abrir http://localhost:5200.
2. Fazer login real.
3. Seleccionar workspace.
4. Abrir campaign.
5. Abrir War Room.
6. Executar ou refrescar intelligence real.
7. Confirmar recommendations reais visíveis.
8. Criar manual task.
9. Criar report action.
10. Criar media kit action.
11. Criar content pack action, se houver catálogo activo.
12. Executar Mark reviewed.
13. Executar Dismiss com motivo.
14. Confirmar CampaignActionsPanel:
   - actions aparecem;
   - statuses coerentes;
   - related_* aparecem;
   - timestamps aparecem quando aplicável;
   - paginação funciona, se houver volume.
15. Recarregar página.
16. Confirmar persistência visual.
17. Confirmar que layout, botões, dialogs e mensagens não têm regressões óbvias.
18. Confirmar Network:
   - frontend chama 8100;
   - não chama 8201/8202.

Validações:
- Browser real.
- Network.
- API quando necessário.
- Screenshots opcionais se a ferramenta suportar, sem capturar secrets.

Registo de execução:
Criar ou actualizar:
frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_09_smoke_visual_staging_resultado.md

O relatório deve incluir:
- estado da execução;
- passos clicados;
- resultado por passo;
- screenshots/evidência textual, se possível;
- Network observado;
- falhas visuais;
- limitações;
- pronto/não pronto para fecho.
```

## Prompt 10 (sonnet) — Fechar estado de staging

```prompt
Iteração 10

Objectivo:
Fechar a fase `04_staging_campaign_actions_with_real_ie_renderer` com estado honesto, documentação consolidada e decisão de prontidão.

Contexto:
- Backlog:
  frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/01_backlog.md
- Pasta de resultados:
  frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/
- Relatórios anteriores:
  - prompt_01 a prompt_09
- Documentos a criar ou actualizar:
  frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/arquitectura_staging_ie_renderer.md
  frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/estado_staging_ie_renderer.md

Regras:
- Não declarar produção-ready.
- Não declarar staging real se IE ficou em dry_run.
- Não declarar Renderer real validado se ele não recebeu job/output real.
- Separar claramente:
  - implementado;
  - validado API;
  - validado browser;
  - bloqueado por ambiente;
  - pendente para produção.
- Não expor secrets.

Tarefas:
1. Ler backlog da fase.
2. Ler todos os relatórios de execução da fase.
3. Inspeccionar documentos da fase anterior se necessário.
4. Criar/actualizar arquitectura_staging_ie_renderer.md com:
   - desenho dos quatro serviços;
   - portas;
   - fluxo Frontend -> Backend Core -> IE/Renderer;
   - regras de segurança;
   - lifecycle de CampaignAction;
   - related artefacts;
   - observabilidade.
5. Criar/actualizar estado_staging_ie_renderer.md com:
   - resumo executivo;
   - validações concluídas;
   - validações bloqueadas;
   - evidências;
   - riscos;
   - limitações;
   - decisão de prontidão.
6. Criar relatório final:
   frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_10_estado_final_staging_resultado.md
7. Declarar uma das opções:
   - pronto_para_piloto_tecnico_staging;
   - executado_parcialmente;
   - bloqueado;
   - nao_pronto.
8. Indicar próximos passos:
   - staging formal;
   - observabilidade;
   - RBAC/UX;
   - E2E automatizado;
   - preparação para produção, se aplicável.

Validações:
- pnpm test
- pnpm lint
- pnpm build
- python manage.py check
- testes relevantes IE/Renderer, se rápidos
- greps de segurança
- check-forbidden-ports, se existir
- verificar docs sem secrets

Registo de execução:
Criar ou actualizar:
frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_10_estado_final_staging_resultado.md

O relatório deve incluir:
- estado final;
- evidência consolidada;
- ficheiros criados/alterados;
- validações executadas;
- limitações;
- riscos;
- decisão de prontidão;
- próximos passos.
```
