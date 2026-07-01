# Pipeline: Hardening Pós-MVP do Content/Report Renderer

## Prompt 01 (opus) — Callback em background leve

```prompt
Objetivo:
Implementar o callback em background leve no content_renderer, separando a recepção HTTP do job da execução render/storage/callback.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md

O renderer já está funcional como MVP:
- recebe POST /jobs;
- valida X-Internal-Token;
- valida headers e envelope;
- gera PNG para content_generation;
- gera PDF/HTML para report_generation;
- gera PDF/HTML para media_kit_generation;
- guarda assets em storage local;
- envia callbacks;
- tem build, lint e testes a passar.

Problema a resolver:
Actualmente o fluxo pode executar render/callback de forma demasiado síncrona, criando risco de corrida com o estado do ExternalJobReference no Django. O POST /jobs deve aceitar o job, responder 202 rapidamente e executar o render/callback em background leve.

Instruções:
- Lê primeiro o backlog:
  docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md
- Inspecciona a implementação actual de:
  - src/jobs/job.controller.ts
  - src/jobs/job.service.ts
  - src/callbacks/callback.client.ts
  - src/callbacks/callback.payload.ts
  - src/renderers/*
  - tests/*
- Implementa uma separação clara entre:
  - recepção do job;
  - agendamento da execução;
  - execução render/storage/callback.
- Cria uma função ou módulo equivalente a:
  - scheduleJobExecution(envelope, context)
  - executeJob(envelope, context)
- O POST /jobs deve:
  - validar token;
  - validar headers;
  - validar envelope;
  - registar job.accepted;
  - agendar execução em background leve;
  - responder 202 sem esperar pelo callback.
- Usa background leve:
  - setImmediate;
  - queueMicrotask;
  - Promise.resolve().then(...);
  - ou mecanismo equivalente simples em Node.js.
- Não introduzir BullMQ, Redis, RabbitMQ, Kafka ou fila complexa.
- Garante que erro em background:
  - é capturado;
  - gera callback failed sempre que possível;
  - é logado;
  - não derruba o processo.
- Garante logs estruturados:
  - job.accepted;
  - job.scheduled;
  - render.started;
  - render.completed;
  - render.failed;
  - callback.started;
  - callback.completed;
  - callback.failed.
- Garante que os logs incluem:
  - job_id;
  - workspace_id;
  - request_id;
  - job_type.
- Garante que os logs não incluem:
  - INTERNAL_API_TOKEN;
  - payload completo;
  - secrets.
- Actualiza testes existentes que assumem callback síncrono.
- Cria novos testes para:
  - POST /jobs devolve 202 antes do callback;
  - callback completed é enviado em background;
  - callback failed é enviado em erro de render;
  - erro no callback não derruba o processo;
  - erro inesperado em background é logado;
  - logs não expõem token.
- Mantém compatibilidade com content_generation, report_generation e media_kit_generation.
- Actualiza README.md com a nova semântica de execução.
- Actualiza docs\fundamentos\02_estado_content_report_renderer.md.
- Cria relatório de execução em:
  docs\fundamentos\resultados\prompt_hardening_01_callback_background.md

Restrições:
- Não implementar fila complexa.
- Não alterar contratos de payload/callback sem necessidade.
- Não implementar novas features visuais.
- Não alterar lógica de billing/RBAC/Django.
- Não chamar Backend Core real nos testes unitários.
- Não expor tokens nos logs ou relatórios.

Validações obrigatórias:
- npm run build
- npm run lint
- npm test

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Desenho da execução em background.
- Alterações ao fluxo POST /jobs.
- Testes criados/alterados.
- Comandos executados.
- Resultados.
- Riscos remanescentes.
- Próximo passo recomendado.

Critérios de aceitação:
- POST /jobs responde 202 rapidamente.
- Render/callback executa em background leve.
- Callback completed continua funcional.
- Callback failed continua funcional.
- Erro em background não derruba o processo.
- Logs são rastreáveis e sem secrets.
- Build passa.
- Lint passa.
- Testes passam.
```

## Prompt 02 (opus) — Retry simples de callback com backoff

```prompt
Objetivo:
Implementar retry simples de callback com backoff, aumentando a resiliência quando o Backend Core Django estiver temporariamente indisponível.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md

O Prompt 01 deve ter implementado callback em background leve.

Problema a resolver:
O callback client actualmente faz tentativa única com timeout. Em falhas temporárias, o renderer deve tentar novamente de forma controlada, sem bloquear indefinidamente e sem duplicar efeitos indevidos.

Instruções:
- Lê primeiro o backlog:
  docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md
- Inspecciona:
  - src/callbacks/callback.client.ts
  - src/config/env.ts
  - src/errors/errors.ts
  - src/jobs/job.service.ts
  - tests/callback.test.ts
  - tests/hardening.test.ts
- Adiciona variáveis de ambiente:
  - CALLBACK_MAX_ATTEMPTS=3
  - CALLBACK_RETRY_BASE_DELAY_MS=500
  - CALLBACK_RETRY_MAX_DELAY_MS=5000
- Actualiza .env.example.
- Actualiza loader de ambiente com validação:
  - max attempts >= 1;
  - base delay >= 0;
  - max delay >= base delay;
  - valores inválidos falham com erro claro.
- Implementa backoff simples.
- Regras de retry:
  - retry em network error;
  - retry em timeout;
  - retry em HTTP 502, 503, 504;
  - opcionalmente retry em 500;
  - não retry em 400, 401, 403, 404, 409, 422.
- Cada tentativa deve logar:
  - callback.attempt_started;
  - callback.attempt_failed;
  - callback.retry_scheduled;
  - callback.completed;
  - callback.delivery_failed.
- Logs devem incluir:
  - job_id, se disponível;
  - workspace_id, se disponível;
  - request_id, se disponível;
  - attempt;
  - max_attempts;
  - http_status, quando existir.
- Logs não devem incluir:
  - X-Internal-Token;
  - payload completo;
  - secrets.
- Garante que o callback client devolve informação suficiente para o JobService logar o resultado.
- Mantém callback failed não-fatal em relação ao processo.
- Cria testes para:
  - sucesso na primeira tentativa;
  - sucesso após falha temporária;
  - timeout com retry;
  - 503 com retry;
  - 400 sem retry;
  - 403 sem retry;
  - max attempts esgotado;
  - token ausente nos logs;
  - env inválida falha.
- Actualiza README.md.
- Actualiza docs\fundamentos\02_estado_content_report_renderer.md.
- Cria relatório de execução em:
  docs\fundamentos\resultados\prompt_hardening_02_callback_retry.md

Restrições:
- Não implementar fila persistente.
- Não implementar dead-letter queue.
- Não implementar Redis.
- Não alterar o contrato do callback.
- Não expor token em logs.
- Não transformar retry em loop infinito.
- Não mascarar 4xx como sucesso.

Validações obrigatórias:
- npm run build
- npm run lint
- npm test

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Regras de retry.
- Env vars adicionadas.
- Testes criados/alterados.
- Comandos executados.
- Resultados.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Callback retry funciona em falha temporária.
- 4xx não gera retry indevido.
- Timeout gera retry até ao limite.
- Max attempts é respeitado.
- Logs mostram tentativas sem secrets.
- Build passa.
- Lint passa.
- Testes passam.
```

## Prompt 03 (opus) — Echo de template_key/template_id no content_generation

```prompt
Objetivo:
Garantir que o content_generation devolve template_key/template_id e metadados de resolução de template de forma explícita e compatível com o Backend Core Django.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md

O renderer já gera outputs reais de content_generation. Esta tarefa melhora o contrato de retorno para facilitar a associação dos outputs aos templates no Django.

Instruções:
- Lê primeiro o backlog:
  docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md
- Inspecciona:
  - src/renderers/content/content-generation.renderer.ts
  - src/templates/registry.ts
  - src/jobs/job.types.ts
  - src/callbacks/callback.payload.ts
  - tests/content-generation.test.ts
- Inspecciona, se disponível no repositório, o contrato do Backend Core para:
  - ContentOutput;
  - ContentTemplate;
  - callback de content_generation;
  - criação de Asset;
  - criação de ContentOutput.
- Confirma se o Django já aceita campos extra em result.outputs[].metadata.
- Sem quebrar compatibilidade, garante que cada output de content_generation inclui:
  - template_key;
  - template_id, se recebido no payload;
  - requested_template_key;
  - requested_template_id, se recebido no payload;
  - resolved_template_key;
  - used_fallback_template;
  - used_fallback_format;
  - dimension;
  - width;
  - height.
- Regras:
  - template_key no topo do output deve representar o template realmente usado ou o melhor valor compatível com o Django;
  - metadata.requested_template_key deve preservar o pedido original;
  - metadata.resolved_template_key deve indicar o template resolvido pelo registry;
  - metadata.used_fallback_template deve ser true quando o template pedido não existir;
  - template_id só deve ser devolvido se tiver vindo no payload ou expected_output.
- Não inventar template_id.
- Se expected_outputs tiverem template_id, preservar.
- Se expected_outputs tiverem template_key, preservar como requested_template_key.
- Criar testes para:
  - output preserva template_key válido;
  - output preserva template_id enviado;
  - fallback de template desconhecido fica explícito;
  - fallback de formato desconhecido fica explícito;
  - callback mantém compatibilidade;
  - outputs sem template_id continuam válidos;
  - metadata não contém dados sensíveis.
- Actualiza README.md com o contrato de output de content_generation.
- Actualiza docs\fundamentos\02_estado_content_report_renderer.md.
- Cria relatório de execução em:
  docs\fundamentos\resultados\prompt_hardening_03_template_echo.md

Restrições:
- Não alterar geração visual.
- Não criar novos templates.
- Não alterar modelos Django.
- Não inventar template_id.
- Não quebrar payloads antigos.
- Não alterar report_generation/media_kit_generation sem necessidade.

Validações obrigatórias:
- npm run build
- npm run lint
- npm test

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Campos adicionados ao output.
- Compatibilidade com Django.
- Testes criados/alterados.
- Comandos executados.
- Resultados.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- content_generation devolve template_key usado.
- content_generation preserva template_id quando recebido.
- fallback de template fica explícito.
- fallback de formato fica explícito.
- Callback continua compatível com Django.
- Build passa.
- Lint passa.
- Testes passam.
```

## Prompt 04 (opus) — Abstrair storage provider e preparar S3/R2

```prompt
Objetivo:
Preparar a interface de storage do content_renderer para futura migração para S3/R2, mantendo LocalStorage funcional e sem mudar o contrato de Asset.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md

O renderer usa storage local como MVP. Esta tarefa não deve implementar S3/R2 completo; deve apenas criar uma abstracção limpa para que os renderers não dependam directamente da implementação local.

Instruções:
- Lê primeiro o backlog:
  docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md
- Inspecciona:
  - src/storage/local-storage.ts
  - src/renderers/renderer.types.ts
  - src/renderers/content/*
  - src/renderers/reports/*
  - src/renderers/media-kits/*
  - src/app.ts
  - src/config/env.ts
  - tests/storage.test.ts
- Criar ou consolidar uma interface StorageProvider.
- A interface deve suportar, no mínimo:
  - saveBuffer(input): Promise<AssetMetadata>
  - resolveWithinRoot, apenas se aplicável ao local provider;
  - getPublicUrl, se já existir lógica equivalente.
- Centralizar tipos:
  - SaveBufferInput;
  - AssetMetadata;
  - StorageProvider;
  - StorageProviderName.
- Adaptar LocalStorage para implementar StorageProvider.
- Adicionar env:
  - STORAGE_PROVIDER=local
- Validar provider:
  - local é aceite;
  - provider desconhecido falha no arranque com erro claro.
- Criar factory:
  - createStorageProvider(config, logger)
- Garantir que RenderContext depende de StorageProvider e não de LocalStorage concreto.
- Garantir que todos os renderers continuam a funcionar sem alteração de contrato.
- Manter endpoint /files apenas para local storage em development.
- Documentar que S3/R2 será implementação futura.
- Não implementar ainda credenciais reais AWS/R2, salvo stubs não usados e claramente documentados.
- Criar testes para:
  - LocalStorage implementa StorageProvider;
  - createStorageProvider(local) funciona;
  - provider inválido falha;
  - renderers continuam a guardar assets;
  - endpoint /files continua a funcionar em local;
  - contrato de Asset permanece igual.
- Actualizar README.md.
- Actualizar docs\fundamentos\02_estado_content_report_renderer.md.
- Cria relatório de execução em:
  docs\fundamentos\resultados\prompt_hardening_04_storage_provider.md

Restrições:
- Não migrar realmente para S3/R2.
- Não adicionar SDK AWS/R2 nesta fase, salvo se for indispensável e justificado.
- Não alterar contrato de Asset.
- Não remover storage local.
- Não quebrar endpoint /files em desenvolvimento.
- Não expor caminhos sensíveis ou secrets.

Validações obrigatórias:
- npm run build
- npm run lint
- npm test

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Nova interface de storage.
- Factory de storage.
- Compatibilidade com LocalStorage.
- Testes criados/alterados.
- Comandos executados.
- Resultados.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Renderers dependem de StorageProvider.
- LocalStorage continua funcional.
- STORAGE_PROVIDER=local funciona.
- Provider inválido falha com erro claro.
- Contrato de Asset não muda.
- Endpoint /files continua funcional em development.
- Build passa.
- Lint passa.
- Testes passam.
```

## Prompt 05 (opus) — Harness E2E com PostgreSQL

```prompt
Objetivo:
Criar um harness E2E com PostgreSQL para validar o content_renderer contra o Backend Core Django em ambiente multi-processo fiável.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md

A validação anterior mostrou limitações com SQLite em cenário multi-processo. Esta tarefa deve preparar um ambiente E2E com PostgreSQL, sem alterar indevidamente o backend_core.

Instruções:
- Lê primeiro o backlog:
  docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md
- Lê também:
  docs\fundamentos\guia_e2e_backend_core.md
  docs\fundamentos\02_estado_content_report_renderer.md
- Inspecciona scripts já existentes:
  - scripts/e2e_backend_core.py
  - scripts/run-e2e.ps1
- Inspecciona README.md.
- Inspecciona, se disponível:
  - backend_core README;
  - settings/env do backend_core;
  - variáveis DB existentes;
  - comandos de migração/teste.
- Criar ou actualizar um harness E2E com PostgreSQL.
- Opções aceitáveis:
  - docker-compose.e2e.yml com PostgreSQL;
  - script PowerShell que sobe PostgreSQL via Docker;
  - documentação operacional clara se Docker não estiver disponível.
- Não hardcodar passwords reais.
- Usar valores de desenvolvimento explícitos e seguros.
- Criar .env.e2e.example, se fizer sentido.
- O harness deve conseguir:
  - subir PostgreSQL;
  - configurar backend_core para usar PostgreSQL;
  - aplicar migrações;
  - subir backend_core em localhost:8100;
  - subir content_renderer em localhost:8202;
  - garantir INTERNAL_API_TOKEN igual nos dois;
  - correr readiness checks;
  - executar script E2E;
  - recolher logs/evidências;
  - encerrar serviços.
- Actualizar scripts existentes em vez de duplicar sem necessidade.
- Criar documentação com:
  - pré-requisitos;
  - variáveis;
  - comandos;
  - troubleshooting;
  - limpeza;
  - evidências esperadas.
- Não é obrigatório que o teste E2E fique 100% verde neste prompt, mas o ambiente deve ficar preparado e os impedimentos devem ser documentados com precisão.
- Cria relatório de execução em:
  docs\fundamentos\resultados\prompt_hardening_05_e2e_postgres_harness.md

Restrições:
- Não alterar regras de produto do backend_core.
- Não commitar secrets.
- Não depender de SQLite para o teste final.
- Não apagar dados reais.
- Não modificar backend_core sem necessidade; se alterar, documentar exactamente.
- Não mascarar falhas de ambiente como sucesso.

Validações obrigatórias:
- npm run build
- npm run lint
- npm test
- python manage.py check, se backend_core estiver disponível
- pytest relevante do backend_core, se ambiente permitir
- comando de smoke do harness E2E, se ambiente permitir

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Estratégia PostgreSQL escolhida.
- Variáveis necessárias.
- Comandos executados.
- Resultado dos comandos.
- Impedimentos, se existirem.
- Próximo passo recomendado.

Critérios de aceitação:
- Harness E2E com PostgreSQL existe ou está documentado de forma executável.
- PostgreSQL é a base recomendada para E2E multi-processo.
- Scripts/documentação indicam como subir backend_core e renderer.
- Não há secrets reais.
- Build/lint/testes do renderer continuam verdes.
- Relatório criado.
```

## Prompt 06 (opus) — Validar loop real Django → Renderer → Django

```prompt
Objetivo:
Executar e validar o loop real Django → Renderer → Django com PostgreSQL, confirmando a criação/actualização de Asset, ContentOutput, Report e MediaKit via callback.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md

O Prompt 05 deve ter criado o harness E2E com PostgreSQL ou uma checklist operacional executável.

Esta tarefa é a validação funcional da integração, não apenas preparação de ambiente.

Instruções:
- Lê primeiro o backlog:
  docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md
- Lê:
  docs\fundamentos\guia_e2e_backend_core.md
  docs\fundamentos\02_estado_content_report_renderer.md
  relatório do Prompt 05.
- Usa PostgreSQL, não SQLite, para o E2E principal.
- Sobe backend_core e content_renderer com o mesmo INTERNAL_API_TOKEN.
- Confirma que EXTERNAL_JOBS_ENABLED=true e EXTERNAL_JOBS_DRY_RUN=false no backend.
- Executa cenários:

Cenário 1 — content_generation completed:
- criar dados mínimos no Django;
- gerar job real;
- renderer gera PNG;
- callback chega ao Django;
- ExternalJobReference fica completed;
- ContentOutput é criado;
- Asset é criado;
- metadata de Asset está correcta.

Cenário 2 — content_generation partially_completed:
- criar payload com pelo menos um output válido e um output que falhe de forma controlada;
- validar callback partially_completed;
- validar outputs completed e failed;
- validar estado no Django.

Cenário 3 — content_generation failed:
- forçar erro controlado;
- validar callback failed;
- validar que o estado no Django não fica inconsistente.

Cenário 4 — report_generation completed:
- criar Report real;
- renderer gera PDF/HTML;
- callback chega;
- Report fica completed;
- Asset é ligado.

Cenário 5 — report_generation failed:
- payload inválido ou erro controlado;
- callback failed;
- estado reflectido no Django.

Cenário 6 — media_kit_generation completed:
- criar MediaKit real;
- renderer gera PDF/HTML;
- callback chega;
- MediaKit fica generated/completed;
- Asset é ligado.

Cenário 7 — media_kit_generation failed:
- payload inválido ou erro controlado;
- callback failed;
- estado reflectido no Django.

Cenário 8 — idempotência:
- reenviar callback completed ou repetir entrega;
- confirmar que não duplica assets/output indevidamente;
- confirmar comportamento esperado do Backend Core.

- Registar evidências:
  - comandos;
  - HTTP status;
  - IDs dos jobs;
  - estados finais;
  - assets criados;
  - logs relevantes;
  - falhas encontradas.
- Actualizar:
  docs\fundamentos\guia_e2e_backend_core.md
  docs\fundamentos\02_estado_content_report_renderer.md
- Cria relatório de execução em:
  docs\fundamentos\resultados\prompt_hardening_06_loop_real_django_renderer.md

Restrições:
- Não declarar E2E verde sem evidência.
- Não inventar resultados.
- Não usar SQLite para o resultado principal.
- Não apagar dados não relacionados.
- Não expor tokens.
- Não alterar backend_core para “forçar passar” sem documentar.

Validações obrigatórias:
- npm run build
- npm run lint
- npm test
- python manage.py check
- pytest relevante do backend_core
- E2E real com PostgreSQL ou impedimento documentado

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ambiente usado.
- Dados criados.
- Cenários executados.
- Evidências por cenário.
- Resultado final.
- Falhas e causas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Loop Django → Renderer → Django validado com PostgreSQL.
- Asset criado via callback em pelo menos content/report/media kit.
- Estados finais confirmados no Django.
- Idempotência validada.
- Falhas controladas não deixam estado inconsistente.
- Relatório criado com evidências.
```

## Prompt 07 (sonnet) — Adicionar coverage Vitest

```prompt
Objetivo:
Adicionar coverage ao projecto content_renderer com Vitest, criando uma métrica inicial de qualidade para controlar regressões futuras.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md

O relatório final anterior indicou que coverage não estava configurado. Esta tarefa deve configurar coverage sem alterar funcionalidades.

Instruções:
- Lê primeiro o backlog:
  docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md
- Inspecciona:
  - package.json
  - vitest.config.ts
  - tests/*
  - README.md
- Instala provider de coverage adequado:
  - @vitest/coverage-v8
- Adiciona script:
  - npm run test:coverage
- Configura vitest.config.ts para coverage.
- Definir thresholds iniciais realistas:
  - lines: 70
  - functions: 65
  - branches: 55
  - statements: 70
- Se os thresholds forem agressivos face à cobertura real, ajustar para valores conservadores e documentar.
- Excluir de coverage, se fizer sentido:
  - dist;
  - node_modules;
  - coverage;
  - scripts;
  - ficheiros de configuração;
  - tipos puros, se aplicável.
- Executar coverage.
- Registar resultado real no relatório.
- Actualizar README.md com:
  - comando de coverage;
  - interpretação básica;
  - localização do relatório.
- Actualizar docs\fundamentos\02_estado_content_report_renderer.md.
- Cria relatório de execução em:
  docs\fundamentos\resultados\prompt_hardening_07_coverage_vitest.md

Restrições:
- Não alterar funcionalidades.
- Não reduzir qualidade dos testes para aumentar coverage artificialmente.
- Não inventar percentagens.
- Não falhar o pipeline por thresholds impossíveis sem documentar.
- Não remover testes existentes.

Validações obrigatórias:
- npm run build
- npm run lint
- npm test
- npm run test:coverage

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Provider instalado.
- Thresholds definidos.
- Resultado real de coverage.
- Comandos executados.
- Resultados.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- npm run test:coverage existe.
- Coverage executa.
- Relatório coverage é gerado.
- Thresholds iniciais estão configurados.
- Build passa.
- Lint passa.
- Testes passam.
```

## Prompt 08 (sonnet) — Documentação final pós-hardening

```prompt
Objetivo:
Actualizar a documentação final do content_renderer após o hardening pós-MVP, reflectindo o estado real da implementação, validações, pendências e próximos passos.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md

Os prompts anteriores devem ter tratado:
- callback em background leve;
- retry de callback;
- echo de template_key/template_id;
- storage provider abstraction;
- E2E PostgreSQL;
- validação real Django → Renderer → Django;
- coverage Vitest.

Instruções:
- Lê primeiro o backlog:
  docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md
- Lê todos os relatórios criados nesta fase:
  docs\fundamentos\resultados\prompt_hardening_01_callback_background.md
  docs\fundamentos\resultados\prompt_hardening_02_callback_retry.md
  docs\fundamentos\resultados\prompt_hardening_03_template_echo.md
  docs\fundamentos\resultados\prompt_hardening_04_storage_provider.md
  docs\fundamentos\resultados\prompt_hardening_05_e2e_postgres_harness.md
  docs\fundamentos\resultados\prompt_hardening_06_loop_real_django_renderer.md
  docs\fundamentos\resultados\prompt_hardening_07_coverage_vitest.md
- Actualizar README.md com:
  - estado actual;
  - arquitectura;
  - variáveis de ambiente novas;
  - callback em background;
  - retry de callback;
  - storage provider;
  - endpoint /files em local;
  - contratos de job/callback actualizados;
  - exemplos actualizados de content_generation;
  - template_key/template_id no output;
  - E2E com PostgreSQL;
  - coverage;
  - troubleshooting.
- Actualizar:
  docs\fundamentos\02_estado_content_report_renderer.md
- Actualizar:
  docs\fundamentos\guia_e2e_backend_core.md
- Criar secção de pendências remanescentes:
  - S3/R2 real;
  - observabilidade;
  - métricas operacionais;
  - fila persistente, se for futura;
  - templates visuais avançados;
  - frontend;
  - FastAPI Intelligence Engine.
- Confirmar ausência de secrets em:
  - README.md;
  - .env.example;
  - docs/fundamentos/*.md;
  - relatórios desta fase.
- Não apagar relatórios anteriores.
- Não esconder falhas do E2E; se algum cenário ficou pendente, documentar claramente.
- Criar relatório final em:
  docs\fundamentos\resultados\prompt_hardening_08_documentacao_final.md

Restrições:
- Não implementar novas features.
- Não alterar código sem necessidade documental.
- Não apagar histórico.
- Não inventar resultados.
- Não declarar produção-ready se ainda existirem pendências de produção.
- Não expor tokens, passwords ou secrets.

Validações obrigatórias:
- npm run build
- npm run lint
- npm test
- npm run test:coverage, se configurado
- verificação manual de documentação sem secrets

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Documentos lidos.
- Ficheiros alterados.
- Estado final pós-hardening.
- Pendências resolvidas.
- Pendências remanescentes.
- Validações executadas.
- Resultado de coverage, se disponível.
- Confirmação de ausência de secrets.
- Próximo passo recomendado.

Critérios de aceitação:
- README.md reflecte o estado real.
- 02_estado_content_report_renderer.md reflecte o estado real.
- guia E2E está actualizado.
- Pendências antigas foram resolvidas ou mantidas com justificação.
- Não há secrets reais na documentação.
- Build passa.
- Lint passa.
- Testes passam.
- Relatório final criado.
```
