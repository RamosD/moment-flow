# Pipeline: Integração Backend Core com FastAPI e Renderer

## Prompt 01 (opus) — Configurar integrações, cliente interno e service registry

```prompt
Objetivo:
Implementar a base de configuração e comunicação interna entre o Backend Core Django/DRF e os serviços técnicos externos futuros: FastAPI Intelligence Engine, Content Renderer, Report Renderer e Video Renderer futuro.

Contexto:
O backlog de referência obrigatório está em:
docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md

O backend core já tem fundação SaaS implementada: accounts, workspaces, RBAC, core assets, catalogue, campaigns, content, links, billing, reports, notifications, audit, integrations_bridge, OpenAPI, Admin e testes.

A regra arquitectural obrigatória é:
Django governa o produto.
FastAPI calcula e executa.
Renderer gera activos.

Nesta fase, o Django não deve implementar métricas, moments, insights, renderização real, Remotion, FFmpeg ou chamadas reais obrigatórias. Deve apenas preparar a orquestração segura.

Instruções:
- Lê o backlog em docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md antes de alterar ficheiros.
- Inspecciona o estado actual de apps.integrations_bridge, config/settings.py, .env.example, apps.audit, apps.billing, apps.content e apps.reports.
- Adiciona ao .env.example as variáveis necessárias:
  - BACKEND_PUBLIC_BASE_URL;
  - INTELLIGENCE_ENGINE_BASE_URL;
  - INTELLIGENCE_ENGINE_TIMEOUT_SECONDS;
  - CONTENT_RENDERER_BASE_URL;
  - CONTENT_RENDERER_TIMEOUT_SECONDS;
  - REPORT_RENDERER_BASE_URL;
  - REPORT_RENDERER_TIMEOUT_SECONDS;
  - INTERNAL_CALLBACK_PATH;
  - EXTERNAL_JOBS_ENABLED;
  - EXTERNAL_JOBS_DRY_RUN.
- Adiciona estas settings em config/settings.py usando python-decouple, sem segredos hardcoded.
- Mantém INTERNAL_API_TOKEN já existente e não exponhas o seu valor em logs, schema ou relatórios.
- Cria em apps.integrations_bridge um cliente HTTP interno reutilizável para serviços técnicos.
- O cliente deve enviar headers internos:
  - X-Internal-Token;
  - X-Workspace-ID;
  - X-Job-ID;
  - X-Request-ID;
  - Content-Type: application/json.
- O cliente deve tratar:
  - sucesso;
  - timeout;
  - erro HTTP;
  - serviço indisponível;
  - JSON inválido.
- Cria um service registry simples para resolver provider/base_url/timeout por job_type.
- Job types iniciais:
  - content_generation;
  - content_preview;
  - report_generation;
  - media_kit_generation;
  - metrics_collection;
  - moment_detection;
  - insight_generation;
  - recommendation_generation.
- O registry deve resolver:
  - content_generation e content_preview para content_renderer;
  - report_generation e media_kit_generation para report_renderer;
  - metrics_collection, moment_detection, insight_generation e recommendation_generation para intelligence_engine.
- Se EXTERNAL_JOBS_DRY_RUN=true, não deve chamar serviço externo real.
- Se EXTERNAL_JOBS_ENABLED=false, deve manter comportamento seguro e sem chamada externa.
- Cria testes unitários para settings, registry, headers do cliente, dry-run, timeout e erro HTTP.
- Não faças refactors grandes fora de integrations_bridge/settings.
- No final, cria a pasta docs\backend_core\integracoes\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\integracoes\resultados\prompt_01_settings_cliente_registry.md.

Restrições:
- Não implementar renderer real.
- Não implementar FastAPI.
- Não criar Celery.
- Não criar métricas reais.
- Não mover responsabilidades analíticas para Django.
- Não expor tokens em logs ou schema.
- Não quebrar testes existentes.

Validações:
- Executa python manage.py check.
- Executa python manage.py makemigrations --check, se aplicável.
- Executa pytest.
- Executa ruff check ., se disponível.
- Executa python manage.py spectacular --file schema.yml, se disponível.

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Variáveis adicionadas.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- .env.example documenta as variáveis de integração.
- settings carregam sem segredos hardcoded.
- cliente interno envia headers obrigatórios.
- service registry resolve provider por job_type.
- dry-run evita chamada externa.
- timeouts e erros HTTP são tratados.
- Testes passam.
- Relatório criado em docs\backend_core\integracoes\resultados\prompt_01_settings_cliente_registry.md.
```

## Prompt 02 (opus) — Evoluir ExternalJobReference e submissão idempotente de jobs

```prompt
Objetivo:
Evoluir ExternalJobReference e criar um serviço único para criar e submeter jobs externos de forma idempotente, rastreável e segura.

Contexto:
O backlog de referência obrigatório está em:
docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md

O Prompt 01 deve ter criado settings de integração, cliente interno e service registry. O backend já tem apps.integrations_bridge com ExternalJobReference e callback interno básico.

A regra arquitectural mantém-se:
Django orquestra e guarda estado.
FastAPI/Renderer executam trabalho técnico.

Instruções:
- Lê o backlog em docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md.
- Inspecciona apps.integrations_bridge.models, services, serializers, views, admin e testes.
- Revê o modelo ExternalJobReference actual.
- Adiciona campos apenas se estiverem em falta:
  - submitted_at;
  - started_at;
  - callback_received_at;
  - request_payload;
  - response_payload;
  - callback_payload;
  - request_id;
  - idempotency_key;
  - retry_count.
- Adiciona ou ajusta estados necessários:
  - queued;
  - submitted;
  - running;
  - completed;
  - partially_completed;
  - failed;
  - cancelled;
  - expired;
  - timeout.
- Garante migration segura, sem perda de dados existentes.
- Actualiza Admin para mostrar e filtrar job_type, provider, status, workspace, external_job_id, related_entity_id, request_id e retry_count.
- Cria ou actualiza serializers internos se necessário.
- Implementa create_and_submit_external_job em apps.integrations_bridge.services.
- A função deve receber:
  - workspace;
  - job_type;
  - provider opcional;
  - related_entity_type;
  - related_entity_id;
  - requested_by;
  - payload;
  - idempotency_key opcional.
- A função deve:
  - criar ExternalJobReference antes de qualquer chamada externa;
  - guardar request_payload;
  - gerar request_id;
  - resolver provider via service registry se não for fornecido;
  - se EXTERNAL_JOBS_ENABLED=false, manter job em queued e não chamar externo;
  - se EXTERNAL_JOBS_DRY_RUN=true, simular submissão e marcar submitted;
  - se activo, chamar serviço externo usando o cliente interno;
  - guardar response_payload;
  - actualizar status para submitted quando aplicável;
  - em caso de timeout, marcar timeout ou failed com erro claro;
  - em caso de erro externo, manter rastreabilidade em error_message/response_payload;
  - criar audit event de submissão quando possível.
- Implementa idempotência:
  - idempotency_key por job_type + entidade;
  - pedido repetido deve devolver job não-terminal existente;
  - retry explícito deve ser possível apenas para failed/timeout/cancelled;
  - retry não deve sobrescrever job antigo de forma destrutiva.
- Cria testes para:
  - criação de job;
  - dry-run;
  - external jobs disabled;
  - submissão com cliente mockado;
  - timeout;
  - erro HTTP;
  - idempotência;
  - retry explícito;
  - Admin/queryset básico.
- No final, cria a pasta docs\backend_core\integracoes\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\integracoes\resultados\prompt_02_external_job_reference_submission.md.

Restrições:
- Não implementar ainda handlers específicos de callback.
- Não ligar ainda ContentPackRequest, Report ou MediaKit ao serviço.
- Não chamar serviços reais em testes.
- Não criar lógica analítica ou renderer.
- Não quebrar o callback interno existente.
- Não expor INTERNAL_API_TOKEN.

Validações:
- Executa python manage.py makemigrations.
- Executa python manage.py migrate.
- Executa python manage.py check.
- Executa python manage.py makemigrations --check, se aplicável.
- Executa pytest.
- Executa ruff check ., se disponível.
- Executa python manage.py spectacular --file schema.yml, se disponível.

Conteúdo mínimo do relatório:
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
- ExternalJobReference suporta payloads, request_id, idempotency_key e retry_count.
- create_and_submit_external_job existe e é testado.
- Job é criado antes da chamada externa.
- Dry-run funciona.
- External jobs disabled não quebra fluxos.
- Pedidos repetidos não criam jobs duplicados.
- Retry explícito funciona de forma controlada.
- Testes passam.
- Relatório criado em docs\backend_core\integracoes\resultados\prompt_02_external_job_reference_submission.md.
```

## Prompt 03 (opus) — Implementar callback dispatcher e idempotência de callbacks

```prompt
Objetivo:
Normalizar o callback interno, implementar dispatcher por job_type e garantir idempotência de callbacks.

Contexto:
O backlog de referência obrigatório está em:
docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md

O Prompt 02 deve ter evoluído ExternalJobReference e create_and_submit_external_job. O callback interno já existe, protegido por X-Internal-Token e INTERNAL_API_TOKEN.

Esta fase deve preparar os handlers, mas ainda sem ligar fluxos completos de content/report/media kit.

Instruções:
- Lê o backlog em docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md.
- Inspecciona apps.integrations_bridge.views, serializers, services, permissions, models e testes.
- Normaliza o serializer de callback interno.
- O callback deve validar:
  - job_id;
  - workspace_id;
  - status;
  - entity.type;
  - entity.id;
  - result;
  - error;
  - metadata.
- O callback deve rejeitar:
  - token ausente;
  - token errado;
  - INTERNAL_API_TOKEN vazio;
  - job inexistente;
  - workspace incompatível;
  - entity.type incompatível com related_entity_type;
  - entity.id incompatível com related_entity_id;
  - payload inválido.
- Guarda callback_payload e callback_received_at.
- Implementa callback_dispatcher.
- Implementa handlers iniciais:
  - handle_content_generation_callback;
  - handle_report_generation_callback;
  - handle_media_kit_generation_callback;
  - handle_metrics_collection_callback placeholder;
  - handle_moment_detection_callback placeholder;
  - handle_insight_generation_callback placeholder;
  - handle_recommendation_generation_callback placeholder.
- Nesta fase, os handlers de content/report/media kit podem apenas actualizar o job e devolver estrutura controlada; a actualização de entidades de produto será feita nos prompts seguintes.
- Handlers placeholder de métricas/moments/insights devem guardar callback_payload e registar audit simples, sem implementar cálculo.
- Implementa idempotência:
  - callback completed repetido deve devolver 200 sem repetir efeitos;
  - callback failed repetido deve devolver 200 sem repetir efeitos;
  - callback incompatível em job terminal deve devolver 409 ou no-op documentado;
  - job desconhecido deve devolver 404;
  - payload inválido deve devolver 400.
- Cria testes para todos os casos críticos:
  - sem token;
  - token errado;
  - token vazio configurado;
  - callback válido;
  - workspace errado;
  - entity errada;
  - callback duplicado;
  - job terminal;
  - job_type desconhecido;
  - placeholders de metrics/moment/insight.
- No final, cria a pasta docs\backend_core\integracoes\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\integracoes\resultados\prompt_03_callback_dispatcher_idempotencia.md.

Restrições:
- Não criar outputs reais ainda.
- Não criar assets a partir de callbacks nesta fase.
- Não consumir/libertar créditos nesta fase.
- Não implementar lógica de métricas, moments ou insights.
- Não chamar serviços externos.
- Não expor tokens em logs/schema.

Validações:
- Executa python manage.py check.
- Executa python manage.py makemigrations --check, se aplicável.
- Executa pytest.
- Executa ruff check ., se disponível.
- Executa python manage.py spectacular --file schema.yml, se disponível.

Conteúdo mínimo do relatório:
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
- Callback interno está normalizado.
- Dispatcher encaminha por job_type.
- Callbacks duplicados são idempotentes.
- Workspace e entity são validados.
- Placeholders técnicos não executam lógica analítica.
- Testes de segurança e idempotência passam.
- Relatório criado em docs\backend_core\integracoes\resultados\prompt_03_callback_dispatcher_idempotencia.md.
```

## Prompt 04 (opus) — Ligar ContentPackRequest ao Renderer job

```prompt
Objetivo:
Ligar o fluxo de ContentPackRequest à criação e submissão de ExternalJobReference do tipo content_generation.

Contexto:
O backlog de referência obrigatório está em:
docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md

O backend core já tem apps.content com ContentPackRequest e ContentOutput, apps.billing com créditos/usage, apps.integrations_bridge com ExternalJobReference e create_and_submit_external_job, e apps.audit.

A renderização real não deve ser implementada. Este prompt apenas cria o pedido de job externo e o payload para o renderer.

Instruções:
- Lê o backlog em docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md.
- Inspecciona apps.content.services, apps.content.models, apps.content.serializers, apps.billing.services, apps.integrations_bridge.services e apps.audit.
- Actualiza create_content_pack_request para criar ExternalJobReference do tipo content_generation depois de validar workspace, RBAC, campanha, pack, quotas e créditos.
- Garante que o fluxo continua transaccional no que for seguro:
  - se a criação do ContentPackRequest falhar, não criar job;
  - se a criação do job falhar antes de submissão, o estado deve ser rastreável;
  - se a submissão externa falhar, não perder o request.
- Define idempotency_key para o job, por exemplo:
  content_generation:<content_pack_request_id>
- Cria build_content_generation_payload.
- O payload deve conter:
  - payload_version;
  - job_id;
  - request_id;
  - workspace_id;
  - callback_url;
  - entity.type = content_pack_request;
  - entity.id;
  - campaign;
  - artist;
  - track, se existir;
  - content_pack;
  - templates activos do pack;
  - expected_outputs;
  - branding básico, se existir;
  - smart_link opcional, se houver relação disponível;
  - billing_context;
  - metadata não sensível.
- Não incluir segredos, tokens, passwords ou dados privados desnecessários.
- Se EXTERNAL_JOBS_ENABLED=false ou dry-run, o fluxo deve continuar previsível.
- Actualiza estados:
  - ContentPackRequest pode ficar queued/submitted conforme padrão existente;
  - ExternalJobReference deve reflectir queued/submitted/dry-run.
- Regista audit event content_pack.job_submitted quando o job for criado/submetido.
- Adiciona testes para:
  - pedido cria ContentPackRequest;
  - pedido cria ExternalJobReference;
  - payload é JSON serializável;
  - payload contém templates esperados;
  - idempotência evita jobs duplicados;
  - dry-run funciona;
  - falha de submissão é rastreável;
  - workspace isolation;
  - créditos continuam reservados conforme lógica existente.
- No final, cria a pasta docs\backend_core\integracoes\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\integracoes\resultados\prompt_04_content_request_renderer_job.md.

Restrições:
- Não implementar callback completed de content_generation ainda.
- Não criar Asset real neste prompt.
- Não gerar ficheiros.
- Não implementar renderer.
- Não alterar billing sem necessidade.
- Não quebrar testes existentes.

Validações:
- Executa python manage.py check.
- Executa python manage.py makemigrations --check, se aplicável.
- Executa pytest.
- Executa ruff check ., se disponível.
- Executa python manage.py spectacular --file schema.yml, se disponível.

Conteúdo mínimo do relatório:
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
- ContentPackRequest cria ExternalJobReference content_generation.
- Payload de content_generation está definido e testado.
- Job tem idempotency_key.
- Dry-run funciona.
- Falha de submissão é rastreável.
- Audit é criado.
- Testes passam.
- Relatório criado em docs\backend_core\integracoes\resultados\prompt_04_content_request_renderer_job.md.
```

## Prompt 05 (opus) — Implementar callback de Content Generation

```prompt
Objetivo:
Implementar o handler real de callback para content_generation, actualizando ContentPackRequest, ContentOutput, Asset, créditos, usage, notification e audit.

Contexto:
O backlog de referência obrigatório está em:
docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md

O Prompt 04 deve ter ligado ContentPackRequest à criação de ExternalJobReference. O Prompt 03 deve ter criado dispatcher e handler inicial. Agora o callback completed/failed de content_generation deve produzir efeitos de produto no Django.

Instruções:
- Lê o backlog em docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md.
- Inspecciona apps.integrations_bridge callback dispatcher, apps.content models/services, apps.core.Asset, apps.billing services, apps.notifications services e apps.audit services.
- Implementa handle_content_generation_callback de forma completa.
- Define e documenta o shape esperado de result para content_generation.
- O result completed deve suportar lista de outputs, por exemplo:
  - output_type;
  - format;
  - status;
  - title;
  - caption;
  - cta;
  - template_key/template_id, se disponível;
  - asset metadata:
    - storage_provider;
    - bucket;
    - storage_key;
    - file_name;
    - mime_type;
    - file_size_bytes;
    - width;
    - height;
    - duration_seconds;
    - checksum;
  - metadata.
- Em completed:
  - actualizar ExternalJobReference para completed;
  - actualizar ContentPackRequest para completed ou partially_completed;
  - criar ou actualizar ContentOutput;
  - criar Asset para ficheiros gerados;
  - ligar ContentOutput.storage_asset;
  - criar UsageEvent content_pack_generated, se aplicável;
  - confirmar consumo de créditos reservados, se aplicável;
  - criar Notification content_pack_ready;
  - registar AuditEvent content_pack.completed.
- Em failed:
  - actualizar ExternalJobReference para failed;
  - actualizar ContentPackRequest para failed;
  - marcar outputs relacionados como failed quando aplicável;
  - libertar ou reembolsar créditos reservados;
  - criar Notification content_pack_failed;
  - registar AuditEvent content_pack.failed.
- Suportar partially_completed:
  - outputs com sucesso ficam completed;
  - outputs falhados ficam failed;
  - ContentPackRequest fica partially_completed;
  - documentar regra de créditos.
- Regra inicial de créditos:
  - se pelo menos um output obrigatório foi gerado, consumir créditos reservados;
  - se todos os outputs obrigatórios falharem, libertar créditos;
  - se não for possível identificar obrigatórios, consumir apenas em completed e libertar em failed.
- Garantir idempotência:
  - callback repetido não cria Asset duplicado;
  - callback repetido não cria Notification duplicada;
  - callback repetido não consome créditos duas vezes;
  - callback repetido não cria UsageEvent duplicado.
- Usar idempotency_key em usage, créditos e notifications quando possível.
- Criar testes end-to-end:
  - request → job → callback completed → outputs/assets/notification/credits;
  - callback failed → request failed/credits libertados/notification;
  - callback repeated;
  - partially_completed;
  - workspace errado rejeitado;
  - entity errada rejeitada.
- No final, cria a pasta docs\backend_core\integracoes\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\integracoes\resultados\prompt_05_callback_content_generation.md.

Restrições:
- Não implementar renderer.
- Não gerar ficheiros reais.
- Não chamar serviço externo real.
- Não implementar métricas ou insights.
- Não relaxar idempotência para fazer testes passar.
- Não expor dados sensíveis em logs.

Validações:
- Executa python manage.py check.
- Executa python manage.py makemigrations --check, se aplicável.
- Executa pytest.
- Executa ruff check ., se disponível.
- Executa python manage.py spectacular --file schema.yml, se disponível.

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Comandos executados.
- Resultado das validações.
- Decisões tomadas.
- Regra de créditos em partial success.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Callback completed cria ou actualiza ContentOutput e Asset.
- ContentPackRequest muda para completed ou partially_completed.
- Callback failed liberta/reembolsa créditos.
- Notifications são criadas.
- Audit é criado.
- Callback duplicado é idempotente.
- Testes end-to-end passam.
- Relatório criado em docs\backend_core\integracoes\resultados\prompt_05_callback_content_generation.md.
```

## Prompt 06 (opus) — Ligar Reports e Media Kits a jobs externos

```prompt
Objetivo:
Ligar os fluxos de criação de Report e MediaKit à criação e submissão de ExternalJobReference para report_generation e media_kit_generation.

Contexto:
O backlog de referência obrigatório está em:
docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md

O backend core já possui apps.reports, apps.billing, apps.integrations_bridge, apps.audit e apps.notifications. A geração real de PDF/HTML/ZIP/media kit fica para renderer externo.

Instruções:
- Lê o backlog em docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md.
- Inspecciona apps.reports.views, serializers, services e models.
- Ao criar Report:
  - validar workspace e RBAC reports:generate;
  - validar quota reports_per_month se já existir;
  - criar Report em queued;
  - criar UsageEvent report_requested ou manter report_generated conforme padrão actual, documentando a decisão;
  - criar ExternalJobReference job_type report_generation;
  - submeter via create_and_submit_external_job;
  - guardar request_payload;
  - registar audit report.job_submitted.
- Criar build_report_generation_payload com:
  - payload_version;
  - job_id;
  - request_id;
  - workspace_id;
  - callback_url;
  - entity.type = report;
  - entity.id;
  - report_type;
  - period_start;
  - period_end;
  - campaign;
  - artist;
  - track;
  - sections esperadas;
  - outputs relacionados, se existirem;
  - smart link stats básicos, se disponíveis;
  - branding básico, se disponível.
- Ao criar MediaKit:
  - validar workspace e RBAC reports:generate;
  - criar MediaKit em draft/queued conforme modelo;
  - criar ExternalJobReference job_type media_kit_generation;
  - submeter via create_and_submit_external_job;
  - registar audit media_kit.job_submitted.
- Criar build_media_kit_generation_payload com:
  - payload_version;
  - job_id;
  - request_id;
  - workspace_id;
  - callback_url;
  - entity.type = media_kit;
  - entity.id;
  - artist;
  - campaign opcional;
  - track opcional;
  - items;
  - assets;
  - smart links;
  - branding.
- Garantir idempotência por entidade:
  - report_generation:<report_id>;
  - media_kit_generation:<media_kit_id>.
- Criar testes para:
  - criar Report cria ExternalJobReference;
  - payload de report é JSON serializável;
  - criar MediaKit cria ExternalJobReference;
  - payload de media kit é JSON serializável;
  - dry-run;
  - falha de submissão rastreável;
  - quota/usage;
  - workspace isolation.
- No final, cria a pasta docs\backend_core\integracoes\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\integracoes\resultados\prompt_06_report_media_kit_jobs.md.

Restrições:
- Não implementar callback completed/failed neste prompt.
- Não gerar PDF real.
- Não gerar media kit real.
- Não implementar renderer.
- Não alterar o modelo de billing sem necessidade.
- Não implementar página pública.

Validações:
- Executa python manage.py check.
- Executa python manage.py makemigrations --check, se aplicável.
- Executa pytest.
- Executa ruff check ., se disponível.
- Executa python manage.py spectacular --file schema.yml, se disponível.

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Comandos executados.
- Resultado das validações.
- Decisão sobre usage report_requested/report_generated.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Report cria ExternalJobReference report_generation.
- MediaKit cria ExternalJobReference media_kit_generation.
- Payloads são versionados e JSON serializáveis.
- Dry-run funciona.
- Falha externa é rastreável.
- Testes passam.
- Relatório criado em docs\backend_core\integracoes\resultados\prompt_06_report_media_kit_jobs.md.
```

## Prompt 07 (opus) — Implementar callbacks de Reports e Media Kits

```prompt
Objetivo:
Implementar handlers de callback para report_generation e media_kit_generation, actualizando Report, MediaKit, Asset, notifications e audit.

Contexto:
O backlog de referência obrigatório está em:
docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md

O Prompt 06 deve ter ligado Report e MediaKit a ExternalJobReference. Agora os callbacks devem completar o ciclo de geração.

Instruções:
- Lê o backlog em docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md.
- Inspecciona apps.integrations_bridge dispatcher, apps.reports models/services, apps.core.Asset, apps.notifications services, apps.audit services e apps.billing.
- Implementa handle_report_generation_callback.
- Em callback report_generation completed:
  - criar Asset do tipo report_pdf ou report_html conforme payload;
  - ligar Report.storage_asset;
  - marcar Report completed;
  - guardar metadata relevante;
  - criar Notification report_ready;
  - registar AuditEvent report.completed.
- Em callback report_generation failed:
  - marcar Report failed;
  - guardar error_message ou metadata de erro;
  - criar Notification report_failed;
  - registar AuditEvent report.failed.
- Implementa handle_media_kit_generation_callback.
- Em callback media_kit_generation completed:
  - criar Asset do tipo media_kit_asset ou report_pdf conforme modelo existente;
  - ligar MediaKit.storage_asset;
  - marcar MediaKit generated;
  - guardar metadata relevante;
  - criar Notification media_kit_ready;
  - registar AuditEvent media_kit.completed.
- Em callback media_kit_generation failed:
  - marcar MediaKit failed se o status existir;
  - se o modelo não suportar failed, guardar erro em metadata e documentar decisão;
  - criar Notification media_kit_failed;
  - registar AuditEvent media_kit.failed.
- Garantir idempotência:
  - callback duplicado não cria asset duplicado;
  - callback duplicado não cria notification duplicada;
  - callback duplicado não altera estado terminal indevidamente.
- Definir shape esperado de result para report/media kit:
  - asset metadata;
  - title opcional;
  - format;
  - storage_provider;
  - storage_key;
  - mime_type;
  - file_size_bytes;
  - checksum;
  - metadata.
- Criar testes:
  - report completed;
  - report failed;
  - report callback duplicado;
  - media kit completed;
  - media kit failed;
  - media kit callback duplicado;
  - workspace/entity mismatch;
  - payload inválido.
- No final, cria a pasta docs\backend_core\integracoes\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\integracoes\resultados\prompt_07_callbacks_reports_media_kits.md.

Restrições:
- Não gerar PDF real.
- Não gerar ficheiro real.
- Não implementar renderer.
- Não criar página pública.
- Não implementar envio de email.
- Não relaxar validações de callback.

Validações:
- Executa python manage.py check.
- Executa python manage.py makemigrations --check, se aplicável.
- Executa pytest.
- Executa ruff check ., se disponível.
- Executa python manage.py spectacular --file schema.yml, se disponível.

Conteúdo mínimo do relatório:
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
- Report completed tem storage_asset.
- Report failed guarda erro.
- MediaKit generated tem storage_asset.
- Falha de MediaKit é rastreável.
- Notifications são criadas.
- Audit é criado.
- Callbacks duplicados são idempotentes.
- Testes passam.
- Relatório criado em docs\backend_core\integracoes\resultados\prompt_07_callbacks_reports_media_kits.md.
```

## Prompt 08 (opus) — Preparar contratos placeholder para Intelligence Engine

```prompt
Objetivo:
Preparar contratos e handlers placeholder para integração futura com FastAPI Intelligence Engine, sem implementar lógica analítica no Django.

Contexto:
O backlog de referência obrigatório está em:
docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md

FastAPI Intelligence Engine será responsável por metrics_collection, moment_detection, insight_generation e recommendation_generation. O Django deve apenas criar ExternalJobReference, montar payloads e guardar callbacks.

Instruções:
- Lê o backlog em docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md.
- Inspecciona apps.catalogue, apps.campaigns, apps.integrations_bridge e apps.audit.
- Cria builders de payload para:
  - metrics_collection;
  - moment_detection;
  - insight_generation;
  - recommendation_generation.
- Payload metrics_collection deve conter:
  - payload_version;
  - job_id;
  - request_id;
  - workspace_id;
  - callback_url;
  - campaign_id;
  - track_id;
  - platform_links;
  - requested_by;
  - metadata.
- Payload moment_detection deve conter:
  - workspace_id;
  - campaign_id;
  - track_id;
  - metrics_context opcional;
  - callback_url.
- Payload insight_generation deve conter:
  - workspace_id;
  - campaign_id;
  - track_id;
  - moments_context opcional;
  - callback_url.
- Payload recommendation_generation deve conter:
  - workspace_id;
  - campaign_id;
  - track_id;
  - insights_context opcional;
  - callback_url.
- Cria services para abrir jobs técnicos:
  - request_metrics_collection;
  - request_moment_detection;
  - request_insight_generation;
  - request_recommendation_generation.
- Estes services devem criar ExternalJobReference e submeter via create_and_submit_external_job.
- Se serviço não estiver configurado, manter job queued ou simular dry-run conforme settings.
- Implementa handlers placeholder que:
  - validam callback;
  - guardam callback_payload;
  - actualizam ExternalJobReference;
  - registam audit event técnico;
  - não criam modelos de métricas, moments ou insights ainda, salvo se já existirem.
- Opcionalmente, criar notification técnica apenas para admins se isso já estiver simples; se não, documentar pendência.
- Criar testes para:
  - criar job metrics_collection;
  - payload inclui TrackPlatformLinks;
  - dry-run;
  - callback metrics_collection;
  - callback moment_detection;
  - callback insight_generation;
  - callback recommendation_generation;
  - garantia de que Django não calcula métricas/moments/insights.
- No final, cria a pasta docs\backend_core\integracoes\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\integracoes\resultados\prompt_08_contratos_intelligence_engine.md.

Restrições:
- Não chamar YouTube API.
- Não recolher métricas reais.
- Não criar engine de moments.
- Não gerar insights reais.
- Não gerar recommendations reais.
- Não criar modelos técnicos complexos fora do escopo.
- Não mover responsabilidades do FastAPI para Django.

Validações:
- Executa python manage.py check.
- Executa python manage.py makemigrations --check, se aplicável.
- Executa pytest.
- Executa ruff check ., se disponível.
- Executa python manage.py spectacular --file schema.yml, se disponível.

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Comandos executados.
- Resultado das validações.
- Contratos definidos.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Django consegue criar jobs técnicos para Intelligence Engine.
- Payload metrics_collection inclui platform links.
- Callback técnico é aceite e guardado.
- Não há lógica analítica em Django.
- Testes passam.
- Relatório criado em docs\backend_core\integracoes\resultados\prompt_08_contratos_intelligence_engine.md.
```

## Prompt 09 (sonnet) — Reforçar segurança, retries, logs e Admin de jobs

```prompt
Objetivo:
Reforçar segurança, resiliência, logs estruturados, retry controlado e Admin de ExternalJobReference.

Contexto:
O backlog de referência obrigatório está em:
docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md

Os prompts anteriores criaram settings, cliente interno, job submission, callbacks, content/report/media kit integration e placeholders para Intelligence Engine. Agora é necessário endurecer a operação.

Instruções:
- Lê o backlog em docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md.
- Inspecciona apps.integrations_bridge, apps.audit, apps.notifications e Admin.
- Reforça segurança dos callbacks:
  - token vazio rejeita tudo;
  - token errado rejeita;
  - workspace_id obrigatório;
  - workspace_id deve bater com job.workspace;
  - entity.type deve bater com job.related_entity_type;
  - entity.id deve bater com job.related_entity_id;
  - status deve ser permitido;
  - logs não podem conter token.
- Implementa ou consolida retry_external_job:
  - permitido apenas para jobs failed, timeout, cancelled ou expired;
  - não permitido para queued/submitted/running/completed sem decisão explícita;
  - retry deve incrementar retry_count ou criar nova submissão controlada conforme decisão documentada;
  - retry deve manter rastreabilidade do job anterior;
  - retry deve respeitar idempotência.
- Implementa logs estruturados nos pontos críticos:
  - criação de job;
  - submissão;
  - falha de submissão;
  - callback recebido;
  - callback rejeitado;
  - callback concluído;
  - retry.
- Logs devem incluir:
  - workspace_id;
  - job_id;
  - job_type;
  - provider;
  - status;
  - request_id.
- Logs não devem incluir:
  - INTERNAL_API_TOKEN;
  - payloads sensíveis completos;
  - secrets.
- Melhora Admin de ExternalJobReference:
  - filtros por job_type, provider, status, workspace;
  - search por external_job_id, related_entity_id, request_id;
  - readonly_fields para payloads e timestamps críticos;
  - ordenação por requested_at ou created_at;
  - acções administrativas seguras apenas se fizer sentido.
- Cria testes para:
  - callback sem token;
  - callback com token errado;
  - callback com token vazio configurado;
  - workspace errado;
  - entity errada;
  - retry permitido;
  - retry bloqueado;
  - logs sem token, se testável;
  - Admin básico.
- No final, cria a pasta docs\backend_core\integracoes\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\integracoes\resultados\prompt_09_seguranca_retries_logs_admin.md.

Restrições:
- Não implementar features de produto novas.
- Não implementar FastAPI.
- Não implementar renderer.
- Não relaxar validações por conveniência.
- Não expor payloads sensíveis.
- Não alterar contratos públicos sem necessidade.

Validações:
- Executa python manage.py check.
- Executa python manage.py makemigrations --check, se aplicável.
- Executa pytest.
- Executa ruff check ., se disponível.
- Executa python manage.py spectacular --file schema.yml, se disponível.

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Comandos executados.
- Resultado das validações.
- Regras de retry definidas.
- Regras de logging definidas.
- Pendências.
- Próximo passo recomendado.

Critérios de aceitação:
- Segurança de callback está reforçada.
- Retry controlado existe e é testado.
- Logs estruturados não expõem tokens.
- Admin de jobs permite investigação operacional.
- Testes passam.
- Relatório criado em docs\backend_core\integracoes\resultados\prompt_09_seguranca_retries_logs_admin.md.
```

## Prompt 10 (sonnet) — Testes end-to-end, hardening e documentação da integração

```prompt
Objetivo:
Criar testes end-to-end dos fluxos de integração, consolidar hardening e documentar o estado final da integração Backend Core ↔ FastAPI/Renderer.

Contexto:
O backlog de referência obrigatório está em:
docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md

Os prompts anteriores devem ter implementado a orquestração de jobs externos, callbacks, integração com content/report/media kit, placeholders técnicos, segurança, retries, logs e Admin.

Instruções:
- Lê o backlog em docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md.
- Inspecciona todo o fluxo de apps.integrations_bridge, apps.content, apps.reports, apps.billing, apps.notifications, apps.audit e tests.
- Cria ou reforça testes end-to-end para Content Pack:
  - criar workspace;
  - criar utilizador/membership/RBAC;
  - criar artista;
  - criar track;
  - criar campanha;
  - criar content pack request;
  - verificar ExternalJobReference;
  - simular callback completed;
  - verificar ContentOutput;
  - verificar Asset;
  - verificar créditos;
  - verificar UsageEvent;
  - verificar Notification;
  - verificar AuditEvent;
  - repetir callback e provar idempotência;
  - simular failed e provar libertação/reembolso de créditos.
- Cria ou reforça testes end-to-end para Report:
  - criar report;
  - verificar job;
  - simular callback completed;
  - verificar Report completed;
  - verificar Asset;
  - verificar Notification;
  - repetir callback.
- Cria ou reforça testes end-to-end para MediaKit:
  - criar media kit;
  - verificar job;
  - simular callback completed;
  - verificar MediaKit generated;
  - verificar Asset;
  - verificar Notification.
- Cria testes de segurança de callbacks:
  - sem token;
  - token errado;
  - workspace errado;
  - entity errada;
  - payload inválido;
  - job terminal.
- Cria testes de dry-run e external jobs disabled.
- Executa coverage se estiver configurado.
- Actualiza ou cria documentação:
  - docs\backend_core\integracoes\02_estado_integracao_fastapi_renderer.md.
- A documentação deve conter:
  - funcionalidades implementadas;
  - fluxos suportados;
  - contratos de payload;
  - contratos de callback;
  - settings necessárias;
  - endpoints internos;
  - segurança;
  - exemplos textuais de payload sem secrets;
  - pendências;
  - próximo passo recomendado.
- Actualiza README do backend_core se necessário, apenas com notas de integração.
- Gera ou actualiza schema.yml se esse já for o padrão do projecto.
- No final, cria a pasta docs\backend_core\integracoes\resultados se não existir.
- No final, grava o relatório desta execução em docs\backend_core\integracoes\resultados\prompt_10_testes_hardening_documentacao.md.

Restrições:
- Não implementar novas features funcionais.
- Não criar FastAPI real.
- Não criar renderer real.
- Não mover lógica técnica para Django.
- Não apagar testes existentes.
- Não esconder falhas de teste.
- Não expor secrets em documentação.

Validações:
- Executa python manage.py check.
- Executa python manage.py makemigrations --check, se aplicável.
- Executa python manage.py spectacular --file schema.yml, se disponível.
- Executa pytest.
- Executa coverage run -m pytest e coverage report, se coverage estiver configurado.
- Executa ruff check ., se disponível.

Conteúdo mínimo do relatório:
- Prompt executado.
- Objectivo.
- Ficheiros criados.
- Ficheiros alterados.
- Comandos executados.
- Resultado das validações.
- Cobertura, se executada.
- Fluxos end-to-end validados.
- Pendências.
- Riscos.
- Próximo passo recomendado.

Critérios de aceitação:
- Teste end-to-end de Content Pack passa.
- Teste end-to-end de Report passa.
- Teste end-to-end de MediaKit passa.
- Testes de segurança de callback passam.
- Dry-run e external jobs disabled estão testados.
- Documentação de estado da integração existe.
- schema.yml é gerado sem erro, se aplicável.
- pytest e ruff passam.
- Relatório criado em docs\backend_core\integracoes\resultados\prompt_10_testes_hardening_documentacao.md.
```
