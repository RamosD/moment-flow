# Pipeline: Content e Report Renderer

## Prompt 01 (opus) — Criar fundação do serviço renderer

```prompt
Objetivo:
Criar a fundação técnica do serviço Content/Report Renderer, responsável por receber jobs do Backend Core Django, gerar activos mínimos e devolver callback ao Django.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\01_backlog_content_report_renderer.md

Este serviço deve ser separado do backend_core Django. O Django governa produto, permissões, billing, estado e callbacks. O renderer apenas gera activos.

Localização esperada do serviço:
content_renderer

Pasta obrigatória para relatórios de execução:
docs\fundamentos\resultados

Instruções:
- Lê o backlog em docs\fundamentos\01_backlog_content_report_renderer.md antes de alterar ficheiros.
- Inspecciona a estrutura actual do repositório para confirmar se a pasta content_renderer já existe.
- Se não existir, cria a pasta content_renderer.
- Inicializa um projecto Node.js com TypeScript.
- Configura package.json com scripts:
  - dev;
  - build;
  - start;
  - test;
  - lint, se aplicável.
- Configura tsconfig.json.
- Cria estrutura src/ com:
  - app.ts;
  - server.ts;
  - config/env.ts;
  - http/routes.ts;
  - http/middleware.ts;
  - jobs/job.schema.ts;
  - jobs/job.types.ts;
  - jobs/job.controller.ts;
  - jobs/job.service.ts;
  - renderers/content;
  - renderers/reports;
  - renderers/media-kits;
  - templates/registry.ts;
  - storage/local-storage.ts;
  - callbacks/callback.client.ts;
  - logging/logger.ts;
  - errors/errors.ts.
- Cria endpoint GET /health.
- Cria .env.example com variáveis mínimas:
  - PORT=8002;
  - NODE_ENV=development;
  - INTERNAL_API_TOKEN=;
  - RENDERER_PUBLIC_BASE_URL=http://localhost:8002;
  - BACKEND_CORE_BASE_URL=http://localhost:8000;
  - LOCAL_STORAGE_ROOT=./storage;
  - LOCAL_STORAGE_PUBLIC_BASE_URL=http://localhost:8002/files;
  - MAX_JOB_PAYLOAD_BYTES=1048576;
  - CALLBACK_TIMEOUT_SECONDS=20;
  - RENDER_TIMEOUT_SECONDS=30.
- Cria loader de ambiente em src/config/env.ts.
- Valida variáveis obrigatórias.
- Em production, rejeita INTERNAL_API_TOKEN vazio.
- Em development, permite token vazio apenas se explicitamente documentado como modo inseguro local.
- Cria logger estruturado inicial.
- Garante que o logger nunca imprime INTERNAL_API_TOKEN.
- Cria README.md inicial do content_renderer com instalação, scripts, .env e healthcheck.
- Cria testes mínimos para:
  - healthcheck;
  - env loader;
  - production rejeita token vazio;
  - logger não expõe token, se testável.
- No final, cria a pasta docs\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\fundamentos\resultados\prompt_01_fundacao_servico_renderer.md.

Restrições:
- Não implementar ainda POST /jobs.
- Não implementar renderização real ainda.
- Não implementar callback real ainda.
- Não implementar vídeo, Remotion ou FFmpeg.
- Não adicionar dependências pesadas sem necessidade.
- Não criar autenticação própria, users, RBAC ou billing no renderer.

Validações:
- Executa npm install, se o projecto for criado.
- Executa npm run build.
- Executa npm test, se configurado.
- Executa npm run lint, se configurado.
- Executa o serviço localmente ou valida que o endpoint /health está implementado.

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Dependências instaladas.
- Scripts disponíveis.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- content_renderer existe.
- TypeScript está configurado.
- Serviço arranca localmente.
- /health devolve 200.
- .env.example existe.
- README.md inicial existe.
- Testes mínimos passam.
- Relatório criado em docs\fundamentos\resultados\prompt_01_fundacao_servico_renderer.md.
```

## Prompt 02 (opus) — Implementar segurança, schemas e endpoint de jobs

```prompt
Objetivo:
Implementar a camada HTTP de recepção de jobs, com autenticação interna, validação de headers, validação de envelope e dispatcher por job_type.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\01_backlog_content_report_renderer.md

O Prompt 01 deve ter criado a fundação do serviço content_renderer, com TypeScript, healthcheck, env loader, logger e estrutura base.

O renderer deve receber jobs do Backend Core Django e nunca decidir permissões, billing ou regras de produto.

Pasta obrigatória para relatórios:
docs\fundamentos\resultados

Instruções:
- Lê o backlog em docs\fundamentos\01_backlog_content_report_renderer.md.
- Inspecciona a estrutura actual do content_renderer.
- Implementa middleware de autenticação interna:
  - validar header X-Internal-Token;
  - usar comparação segura;
  - rejeitar token ausente;
  - rejeitar token errado;
  - rejeitar token vazio em production;
  - não expor token em logs ou respostas.
- Implementa validação de headers:
  - X-Workspace-ID;
  - X-Job-ID;
  - X-Request-ID.
- Compara headers com o body:
  - X-Workspace-ID deve bater com body.workspace_id;
  - X-Job-ID deve bater com body.job_id;
  - X-Request-ID deve bater com body.request_id ou gerar erro controlado conforme decisão documentada.
- Cria schema Zod para envelope de job:
  - job_id;
  - workspace_id;
  - request_id;
  - job_type;
  - callback_url;
  - entity.type;
  - entity.id;
  - payload_version;
  - payload.
- Limita tamanho do payload conforme MAX_JOB_PAYLOAD_BYTES, se aplicável ao framework usado.
- Implementa POST /jobs.
- O endpoint deve:
  - aplicar autenticação interna;
  - validar headers;
  - validar schema;
  - chamar dispatcher;
  - devolver 202 quando o job for aceite;
  - devolver 400 para payload inválido;
  - devolver 403 para token inválido.
- Implementa dispatcher por job_type:
  - content_generation;
  - report_generation;
  - media_kit_generation.
- Para já, os handlers podem ser placeholders controlados que devolvem accepted ou simulated result, sem render real.
- Job type desconhecido deve gerar erro controlado e callback failed ou resposta 400 conforme decisão documentada.
- Cria tipos TypeScript para:
  - JobEnvelope;
  - JobType;
  - JobEntity;
  - CallbackPayload;
  - RenderResult;
  - RenderError.
- Cria testes para:
  - POST /jobs sem token;
  - POST /jobs com token errado;
  - POST /jobs com token correcto;
  - payload inválido;
  - workspace mismatch;
  - job mismatch;
  - job_type desconhecido;
  - content_generation aceite;
  - report_generation aceite;
  - media_kit_generation aceite.
- No final, cria a pasta docs\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\fundamentos\resultados\prompt_02_seguranca_schema_jobs.md.

Restrições:
- Não implementar renderização real ainda.
- Não guardar ficheiros ainda.
- Não enviar callback real ainda, salvo placeholder testável.
- Não implementar fila complexa.
- Não criar base de dados.
- Não expor INTERNAL_API_TOKEN.

Validações:
- Executa npm run build.
- Executa npm test.
- Executa npm run lint, se configurado.
- Testa manualmente ou por teste automatizado POST /jobs.

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Schemas criados.
- Endpoints criados.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- POST /jobs existe.
- Auth interna funciona.
- Headers são validados.
- Envelope é validado.
- Dispatcher reconhece os três job types do MVP.
- Job inválido falha de forma controlada.
- Testes passam.
- Relatório criado em docs\fundamentos\resultados\prompt_02_seguranca_schema_jobs.md.
```

## Prompt 03 (opus) — Implementar storage local e callback client

```prompt
Objetivo:
Implementar storage local para ficheiros renderizados e client de callback para comunicar resultados ao Backend Core Django.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\01_backlog_content_report_renderer.md

O Prompt 02 deve ter criado POST /jobs, autenticação interna, validação de envelope e dispatcher por job_type.

O renderer deve guardar ficheiros localmente no MVP e devolver ao Django apenas metadata compatível com Asset.

Pasta obrigatória para relatórios:
docs\fundamentos\resultados

Instruções:
- Lê o backlog em docs\fundamentos\01_backlog_content_report_renderer.md.
- Inspecciona storage/local-storage.ts, callbacks/callback.client.ts, job types e env.
- Implementa storage local em src/storage/local-storage.ts.
- O storage deve:
  - criar pasta por workspace;
  - criar pasta por job;
  - guardar buffer em disco;
  - gerar storage_key estável;
  - calcular checksum;
  - calcular file_size_bytes;
  - inferir ou receber mime_type;
  - devolver metadata compatível com Django Asset.
- Estrutura sugerida:
  storage/workspaces/<workspace_id>/jobs/<job_id>/<file_name>
- Metadata mínima:
  - storage_provider=local;
  - bucket="";
  - storage_key;
  - file_name;
  - mime_type;
  - file_size_bytes;
  - width, quando aplicável;
  - height, quando aplicável;
  - duration_seconds=null;
  - checksum;
  - public_url, opcional em metadata.
- Implementa endpoint /files/* para servir ficheiros locais em development.
- Bloqueia path traversal.
- Documenta que /files é apenas para desenvolvimento.
- Implementa callback client.
- O callback client deve:
  - enviar POST para callback_url recebido no job;
  - enviar X-Internal-Token;
  - enviar Content-Type application/json;
  - enviar payload completed;
  - enviar payload failed;
  - aplicar timeout CALLBACK_TIMEOUT_SECONDS;
  - logar status;
  - não logar token.
- Payload completed deve seguir o contrato do Django:
  - job_id;
  - workspace_id;
  - status;
  - entity;
  - result;
  - error=null;
  - metadata com renderer e renderer_version.
- Payload failed deve seguir o contrato:
  - job_id;
  - workspace_id;
  - status=failed;
  - entity;
  - result=null;
  - error com code, message e details;
  - metadata.
- Cria erros normalizados:
  - invalid_payload;
  - unsupported_job_type;
  - unsupported_template;
  - render_failed;
  - storage_failed;
  - callback_failed;
  - timeout.
- Cria testes para:
  - guardar ficheiro;
  - metadata correcta;
  - checksum;
  - path traversal bloqueado;
  - /files serve ficheiro válido;
  - callback completed enviado;
  - callback failed enviado;
  - callback timeout tratado;
  - token não aparece em logs.
- No final, cria a pasta docs\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\fundamentos\resultados\prompt_03_storage_callback_client.md.

Restrições:
- Não implementar renderização real ainda.
- Não implementar S3/R2.
- Não implementar CDN.
- Não implementar retry complexo de callback.
- Não expor token.
- Não criar base de dados.

Validações:
- Executa npm run build.
- Executa npm test.
- Executa npm run lint, se configurado.

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Storage implementado.
- Callback client implementado.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Storage local grava ficheiros.
- Metadata é compatível com Django Asset.
- /files funciona em development.
- Path traversal é bloqueado.
- Callback completed funciona.
- Callback failed funciona.
- Testes passam.
- Relatório criado em docs\fundamentos\resultados\prompt_03_storage_callback_client.md.
```

## Prompt 04 (opus) — Implementar template engine e render SVG/PNG

```prompt
Objetivo:
Implementar o template engine mínimo e a renderização inicial de imagens estáticas via SVG convertido para PNG.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\01_backlog_content_report_renderer.md

O Prompt 03 deve ter criado storage local e callback client. Agora o renderer deve começar a gerar imagens reais, mas ainda sem editor visual, sem vídeo e sem browser pesado.

Pasta obrigatória para relatórios:
docs\fundamentos\resultados

Instruções:
- Lê o backlog em docs\fundamentos\01_backlog_content_report_renderer.md.
- Inspecciona templates/registry.ts, renderers/content e storage.
- Implementa registry de templates em src/templates/registry.ts.
- Templates iniciais:
  - generic_post;
  - generic_story;
  - milestone_card;
  - weekly_growth_card;
  - release_card;
  - report_cover;
  - media_kit_cover.
- O registry deve:
  - resolver template_key;
  - devolver fallback para template desconhecido;
  - suportar metadados de formato e dimensão.
- Implementa renderer SVG simples.
- O SVG deve suportar:
  - title;
  - subtitle;
  - artist name;
  - track title;
  - campaign name;
  - metric/milestone quando existir;
  - brand color simples;
  - fundo simples.
- Converte SVG para PNG usando Sharp ou biblioteca equivalente.
- Suporta dimensões:
  - post_1_1: 1080x1080;
  - post_4_5: 1080x1350;
  - story_9_16: 1080x1920;
  - thumbnail_16_9: 1280x720.
- Formato desconhecido deve usar fallback seguro.
- Garante que o render não depende de browser.
- Cria funções reutilizáveis:
  - buildSvg;
  - renderSvgToPng;
  - resolveOutputDimensions;
  - sanitizeTextForSvg.
- Sanitiza texto para evitar SVG inválido.
- Cria testes para:
  - template_key válido;
  - fallback de template desconhecido;
  - SVG gerado contém título;
  - texto é sanitizado;
  - PNG é gerado;
  - dimensões correctas para cada formato;
  - formato desconhecido usa fallback.
- No final, cria a pasta docs\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\fundamentos\resultados\prompt_04_template_engine_svg_png.md.

Restrições:
- Não implementar editor visual.
- Não implementar HTML screenshot.
- Não implementar Playwright nesta fase, salvo se já existir e for necessário.
- Não implementar PDF ainda.
- Não implementar vídeo.
- Não usar assets externos remotos.
- Não gerar conteúdo com IA.

Validações:
- Executa npm run build.
- Executa npm test.
- Executa npm run lint, se configurado.

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Templates suportados.
- Formatos suportados.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Registry de templates existe.
- SVG é gerado.
- PNG é gerado.
- Dimensões estão correctas.
- Template desconhecido usa fallback.
- Testes passam.
- Relatório criado em docs\fundamentos\resultados\prompt_04_template_engine_svg_png.md.
```

## Prompt 05 (opus) — Implementar content_generation

```prompt
Objetivo:
Implementar o renderer real mínimo para jobs content_generation, gerando outputs PNG e enviando callback completed, failed ou partially_completed ao Backend Core Django.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\01_backlog_content_report_renderer.md

O Prompt 04 deve ter criado template engine e render SVG/PNG. O Prompt 03 deve ter criado storage local e callback client. Agora o serviço deve fechar o ciclo de content_generation.

Pasta obrigatória para relatórios:
docs\fundamentos\resultados

Instruções:
- Lê o backlog em docs\fundamentos\01_backlog_content_report_renderer.md.
- Inspecciona job dispatcher, storage, callback client, templates e renderers/content.
- Implementa renderers/content/content-generation.renderer.ts.
- O renderer deve ler do payload:
  - campaign;
  - artist;
  - track;
  - content_pack;
  - templates;
  - expected_outputs;
  - branding;
  - smart_link;
  - billing_context;
  - metadata.
- Para cada expected_output:
  - seleccionar template pelo template_key quando existir;
  - usar fallback quando necessário;
  - resolver formato/dimensão;
  - gerar SVG;
  - converter para PNG;
  - guardar no storage local;
  - devolver metadata de asset.
- O result.outputs deve seguir o contrato esperado pelo Django:
  - output_type;
  - format;
  - status;
  - title;
  - caption;
  - cta;
  - required;
  - template_key;
  - asset;
  - metadata.
- Suportar packs iniciais:
  - release_pack;
  - milestone_pack;
  - weekly_growth_pack;
  - monthly_recap_pack;
  - auto_media_kit como fallback simples, se vier como content pack.
- Se nenhum expected_output vier no payload, gerar pelo menos um output fallback.
- Implementar regra de status geral:
  - completed se todos os outputs obrigatórios forem gerados;
  - partially_completed se alguns outputs falharem mas pelo menos um obrigatório ou útil for gerado;
  - failed se todos falharem.
- Enviar callback completed/partially_completed/failed ao Django.
- Em erro parcial, incluir outputs failed com metadata de erro segura.
- Integrar o renderer no dispatcher de content_generation.
- Criar testes para:
  - content_generation gera pelo menos um PNG;
  - release_pack gera output;
  - milestone_pack gera output;
  - weekly_growth_pack gera output;
  - pack desconhecido usa fallback;
  - expected_outputs vazio gera fallback;
  - partial success;
  - failed envia callback failed;
  - callback completed contém asset metadata compatível com Django;
  - ficheiro existe no storage local.
- No final, cria a pasta docs\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\fundamentos\resultados\prompt_05_content_generation.md.

Restrições:
- Não implementar PDF neste prompt.
- Não implementar vídeo.
- Não chamar Backend Core real nos testes; usar mock de callback.
- Não implementar editor visual.
- Não implementar IA generativa.
- Não alterar contrato do Django sem necessidade.

Validações:
- Executa npm run build.
- Executa npm test.
- Executa npm run lint, se configurado.
- Executa teste manual ou automatizado POST /jobs content_generation.

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Packs suportados.
- Outputs gerados.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- content_generation gera PNG real.
- Ficheiro é guardado no storage local.
- Callback completed é enviado.
- Callback failed é enviado quando aplicável.
- Partial success é suportado.
- Metadata é compatível com Django Asset.
- Testes passam.
- Relatório criado em docs\fundamentos\resultados\prompt_05_content_generation.md.
```

## Prompt 06 (opus) — Implementar report_generation

```prompt
Objetivo:
Implementar o renderer real mínimo para jobs report_generation, gerando PDF simples ou fallback HTML e enviando callback ao Backend Core Django.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\01_backlog_content_report_renderer.md

O Prompt 05 deve ter implementado content_generation. Agora o serviço deve suportar geração de reports simples.

Pasta obrigatória para relatórios:
docs\fundamentos\resultados

Instruções:
- Lê o backlog em docs\fundamentos\01_backlog_content_report_renderer.md.
- Inspecciona renderers/reports, storage, callback client e dispatcher.
- Implementa renderers/reports/report-generation.renderer.ts.
- O renderer deve ler payload de report:
  - report_type;
  - title;
  - period_start;
  - period_end;
  - campaign;
  - artist;
  - track;
  - sections;
  - outputs relacionados, se vierem;
  - smart link stats, se vierem;
  - branding, se vier.
- Gerar documento simples com:
  - capa;
  - título;
  - período;
  - artista;
  - campanha;
  - música;
  - secções;
  - estatísticas básicas, se disponíveis;
  - data de geração.
- Implementar geração de PDF se a biblioteca escolhida estiver disponível e for simples.
- Se PDF com dependência pesada dificultar o ambiente local, implementar fallback HTML:
  - guardar .html;
  - mime_type text/html;
  - metadata indicando fallback_html=true.
- O callback completed deve devolver result.asset com metadata:
  - storage_provider;
  - bucket;
  - storage_key;
  - file_name;
  - mime_type;
  - file_size_bytes;
  - checksum;
  - metadata.
- Em erro, enviar callback failed com erro normalizado.
- Integrar no dispatcher de report_generation.
- Criar testes para:
  - report_generation gera PDF ou HTML;
  - ficheiro é guardado;
  - asset metadata é compatível com Django;
  - callback completed é enviado;
  - fallback HTML funciona, se aplicável;
  - callback failed em erro;
  - payload inválido falha.
- No final, cria a pasta docs\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\fundamentos\resultados\prompt_06_report_generation.md.

Restrições:
- Não implementar gráficos avançados.
- Não implementar BI real.
- Não chamar FastAPI.
- Não gerar métricas.
- Não implementar página pública.
- Não usar Playwright se criar complexidade excessiva.
- Não alterar content_generation salvo necessidade mínima.

Validações:
- Executa npm run build.
- Executa npm test.
- Executa npm run lint, se configurado.
- Executa teste manual ou automatizado POST /jobs report_generation.

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Tipo de output gerado, PDF ou HTML.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- report_generation gera ficheiro real.
- Asset metadata tem mime_type correcto.
- Callback completed é enviado.
- Callback failed funciona.
- Django consegue consumir a metadata recebida.
- Testes passam.
- Relatório criado em docs\fundamentos\resultados\prompt_06_report_generation.md.
```

## Prompt 07 (opus) — Implementar media_kit_generation

```prompt
Objetivo:
Implementar o renderer real mínimo para jobs media_kit_generation, gerando PDF ou HTML simples de media kit e enviando callback ao Backend Core Django.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\01_backlog_content_report_renderer.md

O Prompt 06 deve ter implementado report_generation. Agora o serviço deve suportar media kits simples para artista/campanha.

Pasta obrigatória para relatórios:
docs\fundamentos\resultados

Instruções:
- Lê o backlog em docs\fundamentos\01_backlog_content_report_renderer.md.
- Inspecciona renderers/media-kits, storage, callback client e dispatcher.
- Implementa renderers/media-kits/media-kit-generation.renderer.ts.
- O renderer deve ler payload:
  - artist;
  - campaign opcional;
  - track opcional;
  - items;
  - assets;
  - smart links;
  - branding;
  - metadata.
- Gerar media kit simples com:
  - capa;
  - nome do artista;
  - bio curta, se vier;
  - música/campanha, se vier;
  - destaques;
  - links;
  - contactos/press, se vierem;
  - assets listados, se vierem.
- Reutilizar a estratégia de PDF ou fallback HTML definida no report_generation.
- Guardar ficheiro no storage local.
- Enviar callback completed com result.asset.
- Enviar callback failed em erro.
- Integrar no dispatcher de media_kit_generation.
- Criar testes para:
  - media_kit_generation gera ficheiro;
  - metadata é compatível com Django Asset;
  - callback completed é enviado;
  - callback failed em erro;
  - payload mínimo funciona;
  - payload com items funciona;
  - ficheiro existe no storage.
- No final, cria a pasta docs\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\fundamentos\resultados\prompt_07_media_kit_generation.md.

Restrições:
- Não implementar página pública.
- Não implementar editor visual.
- Não implementar upload externo.
- Não implementar vídeo.
- Não implementar scraping de dados do artista.
- Não chamar APIs externas.
- Não alterar report_generation sem necessidade.

Validações:
- Executa npm run build.
- Executa npm test.
- Executa npm run lint, se configurado.
- Executa teste manual ou automatizado POST /jobs media_kit_generation.

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Tipo de output gerado.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- media_kit_generation gera ficheiro real.
- Ficheiro é guardado.
- Callback completed é enviado.
- Callback failed funciona.
- Metadata é compatível com Django.
- Testes passam.
- Relatório criado em docs\fundamentos\resultados\prompt_07_media_kit_generation.md.
```

## Prompt 08 (sonnet) — Normalizar erros, partial success e hardening

```prompt
Objetivo:
Consolidar tratamento de erros, partial success, timeouts, logs e robustez operacional do Content/Report Renderer.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\01_backlog_content_report_renderer.md

Os prompts anteriores devem ter implementado content_generation, report_generation e media_kit_generation. Agora é necessário endurecer o serviço antes de testar com o Backend Core real.

Pasta obrigatória para relatórios:
docs\fundamentos\resultados

Instruções:
- Lê o backlog em docs\fundamentos\01_backlog_content_report_renderer.md.
- Inspecciona errors, job dispatcher, callback client, content renderer, report renderer, media kit renderer, storage e logger.
- Normaliza erros de render com códigos:
  - invalid_payload;
  - unsupported_job_type;
  - unsupported_template;
  - render_failed;
  - storage_failed;
  - callback_failed;
  - timeout.
- Garante que todos os erros enviados no callback failed têm:
  - code;
  - message;
  - details seguro.
- Garante que detalhes não expõem:
  - INTERNAL_API_TOKEN;
  - paths sensíveis completos quando não necessário;
  - payload completo;
  - secrets.
- Reforça partial success de content_generation:
  - outputs renderizados com sucesso ficam completed;
  - outputs falhados ficam failed;
  - status geral é completed, partially_completed ou failed conforme regra;
  - outputs failed aparecem no result.outputs com metadata segura.
- Reforça timeouts:
  - RENDER_TIMEOUT_SECONDS para render;
  - CALLBACK_TIMEOUT_SECONDS para callback;
  - erro timeout normalizado.
- Reforça logs:
  - job accepted;
  - render started;
  - render completed;
  - render failed;
  - callback started;
  - callback completed;
  - callback failed;
  - incluir job_id, workspace_id, request_id, job_type;
  - não incluir token.
- Verifica que path traversal continua bloqueado.
- Verifica que job_type desconhecido falha de forma controlada.
- Cria ou ajusta testes para:
  - erro de template;
  - erro de storage;
  - erro de callback;
  - partial success;
  - timeout simulado;
  - logs sem token;
  - payload inválido;
  - unsupported job type;
  - path traversal.
- No final, cria a pasta docs\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\fundamentos\resultados\prompt_08_erros_partial_hardening.md.

Restrições:
- Não implementar novas features visuais.
- Não implementar vídeo.
- Não criar fila complexa.
- Não alterar contratos sem necessidade.
- Não relaxar segurança para passar testes.
- Não expor secrets.

Validações:
- Executa npm run build.
- Executa npm test.
- Executa npm run lint, se configurado.
- Executa testes E2E internos do renderer.

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Erros normalizados.
- Regras de partial success.
- Comandos executados.
- Resultado das validações.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Erros são normalizados.
- Callback failed usa contrato correcto.
- Partial success funciona.
- Timeouts são tratados.
- Logs não expõem token.
- Testes passam.
- Relatório criado em docs\fundamentos\resultados\prompt_08_erros_partial_hardening.md.
```

## Prompt 09 (opus) — Validar integração E2E com Backend Core

```prompt
Objetivo:
Validar o Content/Report Renderer contra o Backend Core Django real, fechando o ciclo job externo → render → callback → Asset/Output/Report/MediaKit no Django.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\01_backlog_content_report_renderer.md

O Backend Core já implementa ExternalJobReference, callbacks internos, ContentPackRequest, ContentOutput, Report, MediaKit, Asset, Billing, Notifications e Audit.

O renderer já deve suportar content_generation, report_generation e media_kit_generation.

Pasta obrigatória para relatórios:
docs\fundamentos\resultados

Instruções:
- Lê o backlog em docs\fundamentos\01_backlog_content_report_renderer.md.
- Inspecciona README do backend_core e documentação de integração existente se estiver disponível:
  - docs\backend_core\integracoes\02_estado_integracao_fastapi_renderer.md.
- Não alteres o backend_core salvo se for indispensável e documentado.
- Configura teste manual ou automatizado com dois serviços:
  - backend_core em localhost:8000;
  - content_renderer em localhost:8002.
- Garante que INTERNAL_API_TOKEN é igual nos dois serviços.
- Garante que o Django tem:
  - CONTENT_RENDERER_BASE_URL=http://localhost:8002;
  - EXTERNAL_JOBS_ENABLED=true;
  - EXTERNAL_JOBS_DRY_RUN=false.
- Garante que o renderer tem:
  - BACKEND_CORE_BASE_URL=http://localhost:8000;
  - INTERNAL_API_TOKEN igual ao Django;
  - LOCAL_STORAGE_ROOT configurado.
- Cria um guia ou script de teste E2E local, conforme for mais adequado.
- Cenário content_generation:
  - criar ou usar workspace;
  - criar artista;
  - criar track;
  - criar campanha;
  - criar content pack request no Django;
  - verificar que Django cria ExternalJobReference;
  - verificar que renderer recebe job;
  - verificar que renderer gera PNG;
  - verificar callback para Django;
  - verificar ContentOutput criado;
  - verificar Asset criado;
  - verificar Notification/Audit, se consultável.
- Cenário report_generation:
  - criar report no Django;
  - verificar job;
  - verificar renderer gera PDF ou HTML;
  - verificar callback;
  - verificar Report completed;
  - verificar Asset ligado.
- Cenário media_kit_generation:
  - criar media kit no Django;
  - verificar job;
  - verificar renderer gera ficheiro;
  - verificar callback;
  - verificar MediaKit generated;
  - verificar Asset ligado.
- Se não for possível executar integração real por limitação do ambiente, criar documentação exacta e checklist operacional com comandos e resultados esperados.
- Cria testes automatizados sempre que viável, mas não bloqueies se depender de serviços em execução manual.
- Actualiza README com secção de integração com Backend Core.
- No final, cria a pasta docs\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\fundamentos\resultados\prompt_09_validacao_e2e_backend_core.md.

Restrições:
- Não implementar novas features.
- Não alterar contratos já validados sem necessidade.
- Não desactivar autenticação interna.
- Não usar EXTERNAL_JOBS_DRY_RUN=true para o teste real final, salvo se documentado como fallback.
- Não expor tokens nos relatórios.
- Não substituir testes unitários por validação manual.

Validações:
- Executa npm run build.
- Executa npm test.
- Executa npm run lint, se configurado.
- Executa validação E2E local ou documenta impedimento técnico.
- Se possível, executa comandos relevantes do backend_core:
  - python manage.py check;
  - pytest de integração relevante.

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Configuração usada.
- Cenários executados.
- Evidências de content_generation.
- Evidências de report_generation.
- Evidências de media_kit_generation.
- Comandos executados.
- Resultado das validações.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- content_generation integra com Django real ou checklist é documentada.
- report_generation integra com Django real ou checklist é documentada.
- media_kit_generation integra com Django real ou checklist é documentada.
- README documenta integração.
- Testes do renderer continuam a passar.
- Relatório criado em docs\fundamentos\resultados\prompt_09_validacao_e2e_backend_core.md.
```

## Prompt 10 (sonnet) — Documentação final e estado de implementação

```prompt
Objetivo:
Consolidar documentação final, estado de implementação, pendências e próximos passos do Content/Report Renderer.

Contexto:
O backlog de referência obrigatório está em:
docs\fundamentos\01_backlog_content_report_renderer.md

Os prompts anteriores devem ter implementado o renderer mínimo, testes, callbacks e validação E2E com Backend Core ou checklist operacional.

Pasta obrigatória para relatórios:
docs\fundamentos\resultados

Instruções:
- Lê o backlog em docs\fundamentos\01_backlog_content_report_renderer.md.
- Revê toda a implementação do content_renderer.
- Revê relatórios em docs\fundamentos\resultados.
- Actualiza README.md do content_renderer com:
  - objectivo do serviço;
  - stack;
  - arquitectura;
  - instalação;
  - .env;
  - scripts;
  - como correr em dev;
  - como correr build;
  - como correr tests;
  - endpoint GET /health;
  - endpoint POST /jobs;
  - headers obrigatórios;
  - contrato de job;
  - contrato de callback;
  - exemplo textual de content_generation;
  - exemplo textual de report_generation;
  - exemplo textual de media_kit_generation;
  - storage local;
  - limitações;
  - troubleshooting;
  - integração com backend_core.
- Cria ou actualiza:
  docs\fundamentos\02_estado_content_report_renderer.md
- O documento de estado deve conter:
  - features implementadas;
  - endpoints;
  - templates suportados;
  - formatos suportados;
  - jobs suportados;
  - jobs não suportados;
  - formato de storage;
  - contratos de payload;
  - contratos de callback;
  - validações executadas;
  - pendências;
  - riscos;
  - próximo passo recomendado.
- Confirma que não há tokens ou secrets na documentação.
- Confirma que .env.example não contém valores reais sensíveis.
- Confirma que os relatórios de execução existem.
- Executa validações finais.
- Se houver coverage configurado, executa coverage.
- No final, cria a pasta docs\fundamentos\resultados se não existir.
- No final, grava o relatório desta execução em docs\fundamentos\resultados\prompt_10_documentacao_estado_final.md.

Restrições:
- Não implementar novas features.
- Não alterar contratos sem necessidade.
- Não adicionar dependências.
- Não esconder falhas de validação.
- Não expor secrets.
- Não apagar relatórios anteriores.

Validações:
- Executa npm run build.
- Executa npm test.
- Executa npm run lint, se configurado.
- Executa coverage, se configurado.
- Valida que README e 02_estado_content_report_renderer.md existem.

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Documentos actualizados.
- Comandos executados.
- Resultado das validações.
- Coverage, se executado.
- Pendências finais.
- Riscos.
- Próximo passo recomendado.

Critérios de aceitação:
- README final existe e está útil.
- docs\fundamentos\02_estado_content_report_renderer.md existe.
- Documentação não expõe secrets.
- Testes passam.
- Build passa.
- Pendências estão claras.
- Relatório criado em docs\fundamentos\resultados\prompt_10_documentacao_estado_final.md.
```
