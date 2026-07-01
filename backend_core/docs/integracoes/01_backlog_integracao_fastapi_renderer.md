Segue o conteúdo completo para `docs\backend_core\integracoes\01_backlog_integracao_fastapi_renderer.md`.

# Backlog: Integração Backend Core com FastAPI e Renderer

# ChartRex / MomentFlow — Integrações Técnicas

## 1. Objectivo do documento

Este documento define o backlog técnico para integrar o **Backend Core Django/DRF** com os futuros serviços técnicos externos da plataforma:

```text
FastAPI Intelligence Engine;
Content Renderer;
Report / Media Kit Renderer;
Video Renderer futuro;
workers técnicos futuros.
```

O backend core Django já contém a fundação SaaS e de produto:

```text
accounts;
workspaces;
RBAC;
core assets;
catalogue;
campaigns;
content core;
smart links;
billing;
reports;
media kits;
notifications;
audit;
integrations_bridge;
OpenAPI;
Admin;
testes e hardening.
```

Este backlog foca a próxima etapa:

> Fechar o ciclo de orquestração entre Django, FastAPI/Renderer, callbacks, estados, billing, notifications e audit logs.

---

## 2. Tese arquitectural

A regra central mantém-se:

```text
Django governa o produto.
FastAPI calcula e executa.
Renderer gera activos.
```

Isto significa:

```text
Django:
  decide se o utilizador pode pedir uma acção;
  valida plano, créditos e permissões;
  cria entidades de produto;
  cria ExternalJobReference;
  envia pedido ao serviço técnico;
  recebe callback;
  actualiza estados;
  regista usage/audit;
  emite notification.

FastAPI Intelligence Engine:
  recolhe métricas;
  calcula snapshots/deltas;
  detecta moments;
  gera insights;
  recomenda content packs;
  devolve resultados técnicos.

Content Renderer:
  gera imagens, cards, stories, carrosséis;
  gera previews;
  gera ZIPs;
  gera PDFs;
  gera media kits;
  actualiza outputs via callback.

Video Renderer futuro:
  gera reels, shorts e vídeos;
  usa fila separada;
  consome créditos superiores;
  envia callback.
```

O Django não deve passar a fazer cálculos pesados nem renderizações.

---

## 3. Estado actual assumido

Este backlog assume que já existem no Backend Core:

```text
apps.integrations_bridge.ExternalJobReference;
callback interno autenticado por X-Internal-Token;
INTERNAL_API_TOKEN via ambiente;
apps.content.ContentPackRequest;
apps.content.ContentOutput;
apps.reports.Report;
apps.reports.MediaKit;
apps.notifications.Notification;
apps.billing.UsageEvent;
apps.billing.CreditLedgerEntry;
apps.audit.AuditEvent;
apps.core.Asset;
```

Também assume que já existem estados funcionais suficientes para:

```text
queued;
processing;
completed;
failed;
cancelled;
partially_completed;
```

A tarefa agora é **ligar estes blocos de ponta a ponta**.

---

## 4. Fronteira de responsabilidades

## 4.1 Django / Backend Core

O Django é responsável por:

```text
validar autenticação;
validar workspace;
validar RBAC;
validar plano;
validar créditos;
validar quotas;
criar pedido de geração;
criar ExternalJobReference;
chamar serviço técnico externo;
receber callback;
validar callback;
actualizar ContentPackRequest;
actualizar ContentOutput;
actualizar Report;
actualizar MediaKit;
criar Asset;
registar usage;
actualizar créditos;
registar audit;
emitir notification;
expor estado ao frontend.
```

---

## 4.2 FastAPI Intelligence Engine

O FastAPI é responsável por:

```text
validar payload técnico;
executar recolha de métricas;
criar snapshots técnicos;
calcular deltas;
detectar moments;
gerar insights;
gerar recommendations;
devolver resultados estruturados;
notificar Django por callback.
```

O FastAPI não deve ser dono de:

```text
utilizadores;
workspaces;
RBAC;
billing;
créditos;
subscriptions;
catálogo comercial;
planos;
smart links;
Django Admin.
```

---

## 4.3 Content Renderer

O Content Renderer é responsável por:

```text
receber payload de render;
validar template manifest;
gerar preview;
gerar PNG;
gerar JPG;
gerar WebP;
gerar PDF;
gerar ZIP;
guardar ficheiro, se tiver acesso a storage;
ou devolver metadata para Django criar Asset;
enviar callback de conclusão ou falha.
```

O Renderer não decide se o utilizador pode gerar conteúdo. Essa decisão é do Django.

---

## 4.4 Video Renderer futuro

O Video Renderer deve ser tratado como serviço separado ou fila separada.

Não implementar nesta fase, mas preparar contratos para:

```text
video_rendering;
reel;
short;
mp4;
thumbnail;
long_running_job;
higher_credit_cost;
timeout maior;
progress callback futuro.
```

---

# 5. Princípios de integração

As integrações devem seguir estes princípios:

```text
Django cria e controla o ciclo de vida do job;
todo pedido externo deve ter ExternalJobReference;
todo callback deve ser autenticado;
todo callback deve ser idempotente;
todo job deve estar associado a workspace;
todo job deve estar associado a uma entidade de produto;
todo erro externo deve ficar rastreável;
todo output gerado deve criar ou actualizar Asset;
toda geração com custo deve estar ligada a usage/créditos;
falha técnica não deve consumir crédito final indevidamente;
callbacks não podem alterar entidades de outro workspace;
payloads devem ser versionados;
timeouts devem ser explícitos;
não bloquear request HTTP do utilizador com processamento longo;
Django deve tolerar serviço externo temporariamente indisponível.
```

---

# 6. Variáveis de ambiente recomendadas

Adicionar ao `.env.example` e settings:

```text
INTERNAL_API_TOKEN=
BACKEND_PUBLIC_BASE_URL=http://localhost:8100

INTELLIGENCE_ENGINE_BASE_URL=http://localhost:8201
INTELLIGENCE_ENGINE_TIMEOUT_SECONDS=20

CONTENT_RENDERER_BASE_URL=http://localhost:8202
CONTENT_RENDERER_TIMEOUT_SECONDS=30

REPORT_RENDERER_BASE_URL=http://localhost:8202
REPORT_RENDERER_TIMEOUT_SECONDS=30

INTERNAL_CALLBACK_PATH=/api/v1/internal/jobs/callback/

EXTERNAL_JOBS_ENABLED=true
EXTERNAL_JOBS_DRY_RUN=false
```

Em ambiente local, é aceitável usar `EXTERNAL_JOBS_DRY_RUN=true` enquanto FastAPI/Renderer ainda não existirem.

---

# 7. Headers internos obrigatórios

Todas as chamadas internas devem usar:

```text
X-Internal-Token: <INTERNAL_API_TOKEN>
X-Workspace-ID: <workspace_id>
X-Job-ID: <external_job_reference_id>
X-Request-ID: <uuid>
Content-Type: application/json
```

Regras:

```text
X-Internal-Token é obrigatório para callbacks.
X-Workspace-ID ajuda validação e rastreabilidade.
X-Job-ID liga pedido técnico à ExternalJobReference.
X-Request-ID permite tracing e idempotência.
```

---

# 8. Estados de job

Estados recomendados para `ExternalJobReference`:

```text
queued;
submitted;
running;
completed;
partially_completed;
failed;
cancelled;
expired;
timeout.
```

Se o modelo actual tiver menos estados, evoluir com migration controlada.

---

# 9. Tipos de job

Tipos suportados nesta fase:

```text
content_generation;
content_preview;
report_generation;
media_kit_generation;
metrics_collection;
moment_detection;
insight_generation;
recommendation_generation;
```

Tipos futuros:

```text
video_rendering;
bulk_export;
cohort_benchmarking;
api_sync;
```

---

# 10. Contrato base de ExternalJobReference

Cada job externo deve guardar:

```text
workspace;
job_type;
provider;
external_job_id;
related_entity_type;
related_entity_id;
status;
requested_by;
requested_at;
submitted_at;
started_at;
completed_at;
failed_at;
error_message;
request_payload;
response_payload;
callback_payload;
metadata.
```

Se o modelo actual não tiver todos os campos, este backlog deve evoluí-lo com cuidado.

Campos mínimos obrigatórios para já:

```text
workspace;
job_type;
provider;
external_job_id;
related_entity_type;
related_entity_id;
status;
requested_by;
requested_at;
completed_at;
failed_at;
error_message;
metadata.
```

---

# 11. Contrato base de pedido externo

Formato conceptual para pedidos enviados pelo Django:

```text
{
  "job_id": "<external_job_reference_id>",
  "workspace_id": "<workspace_id>",
  "request_id": "<uuid>",
  "job_type": "<content_generation|report_generation|...>",
  "callback_url": "<backend_public_base_url>/api/v1/internal/jobs/callback/",
  "entity": {
    "type": "<content_pack_request|report|media_kit|...>",
    "id": "<uuid>"
  },
  "payload_version": "1.0",
  "payload": {}
}
```

Regras:

```text
payload_version é obrigatório;
callback_url é obrigatório;
entity.type e entity.id são obrigatórios;
workspace_id é obrigatório;
job_id é obrigatório;
request_id é obrigatório;
payload deve ser serializável em JSON.
```

---

# 12. Contrato base de callback

Formato conceptual para callback recebido pelo Django:

```text
{
  "job_id": "<external_job_reference_id>",
  "external_job_id": "<id do serviço externo, se existir>",
  "workspace_id": "<workspace_id>",
  "status": "completed",
  "entity": {
    "type": "content_pack_request",
    "id": "<uuid>"
  },
  "result": {},
  "error": null,
  "metadata": {}
}
```

Para falha:

```text
{
  "job_id": "<external_job_reference_id>",
  "workspace_id": "<workspace_id>",
  "status": "failed",
  "entity": {
    "type": "content_pack_request",
    "id": "<uuid>"
  },
  "result": null,
  "error": {
    "code": "renderer_error",
    "message": "Falha ao gerar output.",
    "details": {}
  },
  "metadata": {}
}
```

Regras:

```text
callback sem token interno deve ser rejeitado;
callback de job inexistente devolve 404;
callback de workspace incompatível devolve 403 ou 400;
callback repetido deve ser idempotente;
callback sobre job terminal não deve duplicar efeitos;
callback failed deve libertar créditos reservados quando aplicável;
callback completed deve confirmar consumo quando aplicável;
callback deve criar audit event.
```

---

# 13. Fluxos principais

## 13.1 Fluxo de geração de Content Pack

```text
Utilizador pede Content Pack
  ↓
Django valida JWT
  ↓
Django valida X-Workspace-ID
  ↓
Django valida RBAC content:generate
  ↓
Django valida plano/quotas/créditos
  ↓
Django cria ContentPackRequest em queued
  ↓
Django reserva créditos, se aplicável
  ↓
Django cria UsageEvent content_pack_requested
  ↓
Django cria ExternalJobReference content_generation
  ↓
Django envia payload ao Content Renderer
  ↓
Renderer processa
  ↓
Renderer chama callback interno
  ↓
Django actualiza ContentPackRequest
  ↓
Django cria/actualiza ContentOutput
  ↓
Django cria Assets
  ↓
Django confirma consumo de créditos
  ↓
Django cria notification
  ↓
Django regista audit
```

---

## 13.2 Fluxo de falha de Content Pack

```text
Renderer falha
  ↓
Renderer chama callback failed
  ↓
Django marca ExternalJobReference failed
  ↓
Django marca ContentPackRequest failed ou partially_completed
  ↓
Django marca outputs afectados como failed
  ↓
Django liberta ou reembolsa créditos reservados
  ↓
Django cria notification de falha
  ↓
Django regista audit
```

---

## 13.3 Fluxo de Report Generation

```text
Utilizador pede Report
  ↓
Django valida reports:generate
  ↓
Django valida reports_per_month
  ↓
Django cria Report queued
  ↓
Django cria UsageEvent report_generated ou report_requested
  ↓
Django cria ExternalJobReference report_generation
  ↓
Django envia payload ao Report Renderer
  ↓
Renderer gera PDF/HTML/asset
  ↓
Renderer chama callback
  ↓
Django actualiza Report completed
  ↓
Django cria Asset report_pdf
  ↓
Django cria notification report_ready
  ↓
Django regista audit
```

---

## 13.4 Fluxo de Media Kit Generation

```text
Utilizador pede Media Kit
  ↓
Django valida reports:generate
  ↓
Django cria MediaKit draft/queued
  ↓
Django cria ExternalJobReference media_kit_generation
  ↓
Renderer gera media kit
  ↓
Callback interno
  ↓
Django actualiza MediaKit generated/published
  ↓
Django cria Asset
  ↓
Django cria notification media_kit_ready
```

---

## 13.5 Fluxo de Metrics Collection futuro

```text
Django agenda ou solicita recolha
  ↓
Django cria ExternalJobReference metrics_collection
  ↓
FastAPI recolhe métricas
  ↓
FastAPI devolve snapshots/deltas via callback
  ↓
Django guarda estado mínimo ou encaminha para app técnica futura
  ↓
Django expõe resumo à War Room
```

Nota:

> Nesta fase, o Django não deve implementar o motor de métricas. Apenas preparar o contrato e a orquestração.

---

# 14. Backlog por épicos

---

# Épico INT-01 — Configuração de integrações externas

## INT-001 — Adicionar settings de integração

### Objectivo

Adicionar configurações de URL, timeout, dry-run e callback base para FastAPI/Renderer.

### Tarefas

```text
Adicionar variáveis ao .env.example.
Adicionar settings em config/settings.py.
Criar helpers para obter URLs de serviço.
Criar validação simples de configuração.
Adicionar BACKEND_PUBLIC_BASE_URL.
Adicionar EXTERNAL_JOBS_ENABLED.
Adicionar EXTERNAL_JOBS_DRY_RUN.
Adicionar timeouts por serviço.
```

### Critérios de aceitação

```text
settings carregam sem segredos hardcoded;
.env.example documenta variáveis;
Django funciona mesmo sem serviços externos activos;
dry-run pode ser activado por ambiente;
manage.py check passa.
```

---

## INT-002 — Criar cliente HTTP interno base

### Objectivo

Criar cliente reutilizável para chamadas internas aos serviços técnicos.

### Tarefas

```text
Criar apps.integrations_bridge.clients.py.
Criar InternalServiceClient.
Suportar base_url, timeout, headers internos.
Enviar X-Internal-Token.
Enviar X-Workspace-ID.
Enviar X-Job-ID.
Enviar X-Request-ID.
Tratar timeout.
Tratar erro HTTP.
Tratar serviço indisponível.
Normalizar resposta.
Criar testes com mocks.
```

### Critérios de aceitação

```text
cliente envia headers internos;
timeout é aplicado;
erro externo é transformado em erro controlado;
logs não expõem tokens;
testes cobrem sucesso, timeout e erro HTTP.
```

---

## INT-003 — Criar service registry simples

### Objectivo

Centralizar endpoints dos serviços técnicos.

### Serviços

```text
intelligence_engine;
content_renderer;
report_renderer;
video_renderer_future.
```

### Tarefas

```text
Criar registry em integrations_bridge.
Resolver URL por provider/job_type.
Validar se serviço está configurado.
Suportar dry-run.
Criar testes.
```

### Critérios de aceitação

```text
job_type content_generation resolve para content_renderer;
job_type report_generation resolve para report_renderer;
job_type metrics_collection resolve para intelligence_engine;
configuração ausente gera erro controlado;
dry-run não chama serviço externo.
```

---

# Épico INT-02 — Evolução de ExternalJobReference

## INT-101 — Rever e evoluir modelo de ExternalJobReference

### Objectivo

Garantir que ExternalJobReference suporta payload, resposta, callback, timestamps e idempotência.

### Tarefas

```text
Rever modelo actual.
Adicionar campos apenas se estiverem em falta:
  submitted_at;
  started_at;
  callback_received_at;
  request_payload;
  response_payload;
  callback_payload;
  request_id;
  idempotency_key.
Adicionar índices úteis.
Criar migration.
Actualizar Admin.
Actualizar serializers internos, se existirem.
Actualizar testes.
```

### Critérios de aceitação

```text
ExternalJobReference guarda request_payload;
guarda response_payload;
guarda callback_payload;
guarda request_id;
tem timestamps de ciclo de vida;
migrations aplicam sem perda de dados;
testes passam.
```

---

## INT-102 — Normalizar criação de job externo

### Objectivo

Criar serviço único para abrir jobs externos.

### Tarefas

```text
Criar função create_and_submit_external_job.
Receber workspace, job_type, provider, related_entity, requested_by, payload.
Criar ExternalJobReference em queued.
Se dry-run: marcar submitted sem chamar externo ou simular resposta.
Se external jobs desactivado: manter queued e devolver pendência.
Se activo: chamar serviço externo.
Actualizar status para submitted.
Guardar request_payload e response_payload.
Registar audit event.
Tratar falha de submissão.
```

### Critérios de aceitação

```text
job é criado antes da chamada externa;
falha de chamada não apaga job;
status reflecte resultado da submissão;
payload fica guardado;
audit é criado;
testes cobrem active, dry-run e falha.
```

---

## INT-103 — Idempotência de submissão

### Objectivo

Evitar criar múltiplos jobs externos para o mesmo pedido de produto.

### Tarefas

```text
Definir idempotency_key por entidade e job_type.
Exemplo: content_generation:<content_pack_request_id>.
Antes de criar job, verificar job não-terminal existente.
Se existir, devolver job existente.
Se terminal failed e retry explícito, criar novo job com retry_count.
Adicionar retry_count, se necessário.
Criar testes.
```

### Critérios de aceitação

```text
pedidos repetidos não criam jobs duplicados;
retry explícito é suportado;
jobs terminais não são sobrescritos indevidamente;
testes passam.
```

---

# Épico INT-03 — Callback interno robusto

## INT-201 — Normalizar callback payload

### Objectivo

Tornar o callback interno genérico e seguro.

### Tarefas

```text
Rever endpoint interno actual.
Criar serializer de callback genérico.
Validar job_id.
Validar workspace_id.
Validar status.
Validar entity.type.
Validar entity.id.
Validar result/error.
Guardar callback_payload.
Actualizar callback_received_at.
```

### Critérios de aceitação

```text
callback inválido devolve 400;
token ausente devolve 403;
job inexistente devolve 404;
workspace incompatível é rejeitado;
callback válido actualiza job.
```

---

## INT-202 — Implementar dispatcher de callback por job_type

### Objectivo

Encaminhar callbacks para handlers específicos.

### Tarefas

```text
Criar callback_dispatcher.
Criar handlers:
  handle_content_generation_callback;
  handle_report_generation_callback;
  handle_media_kit_generation_callback;
  handle_metrics_collection_callback placeholder;
  handle_moment_detection_callback placeholder.
Dispatcher chama handler por job_type.
Handler desconhecido marca erro controlado.
Criar testes.
```

### Critérios de aceitação

```text
callback content_generation chama handler certo;
callback report_generation chama handler certo;
job_type desconhecido não quebra endpoint;
callback idempotente não duplica efeitos.
```

---

## INT-203 — Garantir callbacks idempotentes

### Objectivo

Evitar duplicação de outputs, assets, créditos e notifications.

### Tarefas

```text
Se job já completed e callback completed chegar novamente, devolver 200 sem repetir efeitos.
Se job já failed e callback failed chegar novamente, devolver 200 sem repetir efeitos.
Se job terminal receber estado incompatível, devolver 409 ou no-op documentado.
Usar idempotency_key em assets/usage/credits/notifications quando aplicável.
Criar testes.
```

### Critérios de aceitação

```text
callback duplicado não cria Asset duplicado;
não cria Notification duplicada;
não consome créditos duas vezes;
não altera estado terminal indevidamente;
testes passam.
```

---

# Épico INT-04 — Integração de Content Generation

## INT-301 — Ligar ContentPackRequest a ExternalJobReference

### Objectivo

Quando um content pack for pedido, criar job externo de geração.

### Tarefas

```text
Actualizar create_content_pack_request.
Após criar request e validar créditos, criar ExternalJobReference content_generation.
Montar payload para Content Renderer.
Chamar create_and_submit_external_job.
Guardar relação job ↔ ContentPackRequest.
Criar audit event content_pack.job_submitted.
Se submissão falhar, manter request queued ou marcar failed conforme regra definida.
Criar testes.
```

### Critérios de aceitação

```text
ContentPackRequest cria ExternalJobReference;
job_type é content_generation;
related_entity aponta para ContentPackRequest;
payload contém workspace, campaign, pack, templates e callback_url;
falha externa é rastreável;
testes passam.
```

---

## INT-302 — Definir payload de content generation

### Objectivo

Definir payload mínimo para o renderer gerar outputs.

### Payload deve conter

```text
workspace;
branding;
campaign;
artist;
track;
content_pack;
templates;
outputs_expected;
smart_link opcional;
copies/cta opcionais;
callback_url;
billing_context;
```

### Tarefas

```text
Criar builder build_content_generation_payload.
Incluir dados mínimos da campanha.
Incluir dados do artista.
Incluir dados da música.
Incluir templates activos do pack.
Incluir brand settings se existirem.
Incluir créditos reservados ou usage context se existir.
Não incluir segredos.
Criar testes de payload.
```

### Critérios de aceitação

```text
payload é JSON serializável;
payload tem versão;
payload não contém campos sensíveis;
payload inclui templates esperados;
payload inclui callback_url;
testes passam.
```

---

## INT-303 — Handler de callback de content generation

### Objectivo

Actualizar ContentPackRequest, ContentOutput e Asset quando o renderer concluir.

### Callback completed deve permitir

```text
actualizar ContentPackRequest para completed ou partially_completed;
criar ou actualizar ContentOutput;
criar Asset para cada ficheiro gerado;
ligar output a storage_asset;
confirmar consumo de créditos reservados;
criar UsageEvent content_pack_generated;
criar Notification content_pack_ready;
registar AuditEvent content_pack.completed.
```

### Callback failed deve permitir

```text
marcar request failed;
marcar outputs failed, se existirem;
libertar créditos reservados;
criar Notification content_pack_failed;
registar AuditEvent content_pack.failed.
```

### Critérios de aceitação

```text
callback completed cria outputs;
assets são criados com workspace correcto;
request fica completed;
créditos não são cobrados duas vezes;
callback failed liberta créditos;
notification é criada;
testes passam.
```

---

## INT-304 — Suportar resultado parcial

### Objectivo

Permitir que alguns outputs sejam gerados e outros falhem.

### Tarefas

```text
Definir status partially_completed.
Handler deve criar outputs completed e failed conforme result.
ContentPackRequest fica partially_completed.
Créditos devem seguir regra clara:
  opção A: consumir total se pack teve sucesso parcial;
  opção B: consumir proporcionalmente;
  opção C: manter simples e consumir total apenas se outputs mínimos foram gerados.
Documentar decisão.
Criar testes.
```

### Recomendação inicial

```text
Para MVP, consumir créditos se pelo menos um output obrigatório foi gerado.
Se todos os obrigatórios falharem, libertar créditos.
```

### Critérios de aceitação

```text
resultado parcial não quebra;
outputs falhados ficam visíveis;
request fica partially_completed;
regra de crédito está documentada;
testes passam.
```

---

# Épico INT-05 — Integração de Report e Media Kit Generation

## INT-401 — Ligar Report a ExternalJobReference

### Objectivo

Quando um report for pedido, criar job externo de report_generation.

### Tarefas

```text
Actualizar fluxo de criação de Report.
Validar reports:generate.
Validar quota reports_per_month.
Criar UsageEvent report_requested ou report_generated conforme regra actual.
Criar ExternalJobReference report_generation.
Montar payload para report renderer.
Submeter job.
Criar audit event report.job_submitted.
Criar testes.
```

### Critérios de aceitação

```text
Report cria ExternalJobReference;
payload contém campaign/artist/track/período/secções;
report fica queued/submitted;
falha externa é rastreável;
testes passam.
```

---

## INT-402 — Handler de callback de report_generation

### Objectivo

Actualizar Report quando o PDF/HTML estiver pronto.

### Callback completed deve

```text
criar Asset report_pdf ou report_html;
ligar Report.storage_asset;
marcar Report completed;
criar Notification report_ready;
registar AuditEvent report.completed.
```

### Callback failed deve

```text
marcar Report failed;
guardar error_message;
criar Notification report_failed;
registar AuditEvent report.failed.
```

### Critérios de aceitação

```text
Report completed tem storage_asset;
Report failed tem error_message;
notification é criada;
callback duplicado não duplica asset;
testes passam.
```

---

## INT-403 — Ligar MediaKit a ExternalJobReference

### Objectivo

Criar job externo para media_kit_generation.

### Tarefas

```text
Actualizar fluxo de criação de MediaKit.
Montar payload com artist, track, campaign, métricas disponíveis, links e assets.
Criar ExternalJobReference media_kit_generation.
Submeter job.
Criar audit event media_kit.job_submitted.
Criar testes.
```

### Critérios de aceitação

```text
MediaKit cria ExternalJobReference;
payload contém artist e itens;
MediaKit fica draft/queued;
job é submetido ou fica queued em dry-run;
testes passam.
```

---

## INT-404 — Handler de callback de media_kit_generation

### Objectivo

Actualizar MediaKit quando o renderer concluir.

### Callback completed deve

```text
criar Asset media_kit_asset;
ligar MediaKit.storage_asset;
marcar MediaKit generated;
criar Notification media_kit_ready;
registar AuditEvent media_kit.completed.
```

### Callback failed deve

```text
marcar MediaKit failed ou draft com erro, conforme modelo;
guardar error_message em metadata se não houver campo;
criar Notification media_kit_failed;
registar AuditEvent media_kit.failed.
```

### Critérios de aceitação

```text
MediaKit generated tem asset;
falha é rastreável;
notification é criada;
testes passam.
```

---

# Épico INT-06 — Integração futura com Intelligence Engine

## INT-501 — Definir contratos para metrics_collection

### Objectivo

Preparar contrato para recolha de métricas sem implementar motor analítico no Django.

### Tarefas

```text
Definir payload metrics_collection.
Incluir workspace_id.
Incluir campaign_id.
Incluir track_id.
Incluir platform links.
Incluir callback_url.
Criar builder de payload.
Criar ExternalJobReference metrics_collection.
Não chamar serviço se não estiver configurado.
Criar testes de dry-run.
```

### Critérios de aceitação

```text
Django consegue criar job metrics_collection;
payload inclui track_platform_links;
não há recolha real em Django;
job fica queued/submitted conforme configuração.
```

---

## INT-502 — Definir callback de metrics_collection

### Objectivo

Preparar recebimento de resultados técnicos de métricas.

### Tarefas

```text
Criar handler placeholder para metrics_collection.
Validar payload recebido.
Guardar callback_payload no job.
Não criar ainda models técnicos de métricas se não existirem.
Criar audit event metrics_collection.completed.
Opcional: criar notification técnica apenas para admins.
```

### Critérios de aceitação

```text
callback metrics_collection é aceite;
payload fica guardado;
Django não tenta calcular metrics;
testes passam.
```

---

## INT-503 — Definir contratos para moment_detection e insight_generation

### Objectivo

Preparar contratos para fases seguintes.

### Tarefas

```text
Definir payload moment_detection.
Definir payload insight_generation.
Definir callback shape.
Documentar campos mínimos.
Criar handlers placeholder.
Criar testes básicos de callback.
```

### Critérios de aceitação

```text
job_type é reconhecido;
callback é guardado;
sem lógica analítica em Django;
documentação actualizada.
```

---

# Épico INT-07 — Segurança, observabilidade e resiliência

## INT-601 — Segurança de chamadas internas

### Objectivo

Reforçar autenticação e validação de integrações internas.

### Tarefas

```text
Garantir comparação constante do token interno.
Garantir que token vazio rejeita tudo.
Garantir que callbacks sem workspace_id são rejeitados.
Garantir que workspace_id do callback bate com job.workspace.
Garantir que entity.id bate com related_entity_id.
Garantir logs sem segredos.
Criar testes de segurança.
```

### Critérios de aceitação

```text
callback sem token é 403;
callback com token errado é 403;
callback com workspace errado é rejeitado;
callback com entity errada é rejeitado;
logs não mostram token.
```

---

## INT-602 — Timeouts e retries controlados

### Objectivo

Evitar requests presos e permitir retry manual.

### Tarefas

```text
Definir timeout por serviço.
Guardar erro de timeout no job.
Criar endpoint ou service retry_external_job.
Permitir retry apenas em failed/timeout.
Incrementar retry_count se existir.
Não duplicar jobs sem intenção explícita.
Criar testes.
```

### Critérios de aceitação

```text
timeout marca job como failed ou timeout;
retry explícito cria nova submissão controlada;
não há duplicação acidental;
testes passam.
```

---

## INT-603 — Logs estruturados

### Objectivo

Melhorar rastreabilidade de integrações.

### Tarefas

```text
Adicionar logs com workspace_id, job_id, job_type, provider, status.
Não logar payloads sensíveis completos.
Logar submissão.
Logar callback.
Logar falha.
Criar padrão de logger por app.
```

### Critérios de aceitação

```text
logs permitem seguir job;
tokens não aparecem nos logs;
erros externos ficam rastreáveis.
```

---

## INT-604 — Dashboard administrativo de jobs

### Objectivo

Melhorar visibilidade no Django Admin.

### Tarefas

```text
Melhorar Admin de ExternalJobReference.
Adicionar filtros por job_type, provider, status, workspace.
Adicionar search por external_job_id, related_entity_id.
Adicionar readonly_fields para payloads e timestamps críticos.
Adicionar acção admin para marcar failed/cancelled apenas se seguro.
```

### Critérios de aceitação

```text
Admin permite investigar jobs;
payloads são consultáveis;
campos críticos não são editados indevidamente.
```

---

# Épico INT-08 — Testes transversais de integração

## INT-701 — Testar ciclo completo de Content Pack

### Objectivo

Garantir ciclo pedido → job → callback → outputs.

### Cenário

```text
Criar workspace;
criar artista;
criar track;
criar campanha;
criar pack;
pedir content pack;
criar ExternalJobReference;
simular callback completed;
verificar outputs;
verificar assets;
verificar créditos;
verificar notification;
verificar audit.
```

### Critérios de aceitação

```text
teste end-to-end passa;
não há duplicação em callback repetido;
falha liberta créditos;
workspace isolation é mantido.
```

---

## INT-702 — Testar ciclo completo de Report

### Objectivo

Garantir ciclo report → job → callback → asset → notification.

### Critérios de aceitação

```text
Report fica queued após pedido;
job é criado;
callback completed cria asset;
Report fica completed;
notification report_ready existe;
callback duplicado é idempotente.
```

---

## INT-703 — Testar ciclo completo de Media Kit

### Objectivo

Garantir ciclo media kit → job → callback → asset.

### Critérios de aceitação

```text
MediaKit cria job;
callback completed cria asset;
MediaKit fica generated;
notification existe;
falha é tratada.
```

---

## INT-704 — Testar segurança de callbacks

### Objectivo

Garantir que callbacks internos não abrem vulnerabilidades.

### Critérios de aceitação

```text
sem token: rejeitado;
token errado: rejeitado;
workspace errado: rejeitado;
entity errada: rejeitada;
job terminal: não duplica efeitos;
payload inválido: 400.
```

---

# 15. Ordem recomendada de implementação

A ordem recomendada é:

```text
1. INT-001 — Settings de integração
2. INT-002 — Cliente HTTP interno
3. INT-003 — Service registry
4. INT-101 — Evoluir ExternalJobReference
5. INT-102 — create_and_submit_external_job
6. INT-103 — Idempotência de submissão
7. INT-201 — Callback payload normalizado
8. INT-202 — Callback dispatcher
9. INT-203 — Callback idempotente
10. INT-301 — ContentPackRequest → ExternalJobReference
11. INT-302 — Payload de content generation
12. INT-303 — Callback de content generation
13. INT-304 — Resultado parcial
14. INT-401 — Report → ExternalJobReference
15. INT-402 — Callback de report_generation
16. INT-403 — MediaKit → ExternalJobReference
17. INT-404 — Callback de media_kit_generation
18. INT-501 — Contrato metrics_collection
19. INT-502 — Callback metrics_collection placeholder
20. INT-503 — Contratos moment/insight placeholders
21. INT-601 — Segurança de chamadas internas
22. INT-602 — Timeouts e retries
23. INT-603 — Logs estruturados
24. INT-604 — Admin de jobs
25. INT-701 a INT-704 — Testes end-to-end
```

---

# 16. MVP desta fase de integração

O MVP desta fase fica pronto quando existir:

```text
ContentPackRequest cria ExternalJobReference;
Django consegue submeter job ao renderer ou dry-run;
callback completed cria ContentOutput e Asset;
callback failed actualiza erro e liberta créditos;
Report cria job e recebe callback completed;
MediaKit cria job e recebe callback completed;
notifications são emitidas;
audit logs são emitidos;
callbacks são idempotentes;
callbacks são autenticados;
testes end-to-end passam.
```

---

# 17. Fora do escopo desta fase

Não implementar ainda:

```text
FastAPI Intelligence Engine completo;
Content Renderer real completo;
Remotion;
FFmpeg;
YouTube API real;
métricas reais;
moment detection real;
insight engine real;
frontend;
public media kit page;
domínio customizado;
storage S3/R2 real completo, salvo se já existir;
Celery obrigatório;
Kubernetes;
CI/CD produção.
```

É aceitável implementar **dry-run** ou **mock external service** para validar contratos.

---

# 18. Critérios técnicos de pronto

Cada item deste backlog só fica pronto quando:

```text
migrations criadas, se houver models;
settings documentados no .env.example;
serviços têm testes;
callbacks têm testes;
idempotência testada;
workspace isolation testado;
RBAC respeitado nos endpoints de pedido;
callback interno protegido por token;
tokens não aparecem em logs;
usage/créditos tratados correctamente;
audit gerado nos fluxos críticos;
notification gerada quando aplicável;
OpenAPI não quebra;
pytest passa;
ruff passa;
makemigrations --check passa.
```

---

# 19. Riscos

## 19.1 Duplicação de efeitos em callback

### Risco

Callback repetido criar outputs, assets, notifications ou consumo de créditos em duplicado.

### Mitigação

```text
callbacks idempotentes;
idempotency_key;
verificar job terminal;
unique constraints quando aplicável;
testes de replay.
```

---

## 19.2 Django assumir lógica técnica

### Risco

O Django começar a implementar métricas, moments ou renderização.

### Mitigação

```text
Django só orquestra;
FastAPI calcula;
Renderer gera;
payloads e callbacks bem definidos;
handlers placeholder para métricas.
```

---

## 19.3 Perda de créditos em falha técnica

### Risco

Falha do renderer consumir créditos indevidamente.

### Mitigação

```text
reserve antes;
consume só no sucesso;
release/refund na falha;
testes de falha.
```

---

## 19.4 Segurança fraca nos callbacks

### Risco

Serviço externo ou atacante actualizar entidades indevidamente.

### Mitigação

```text
X-Internal-Token obrigatório;
workspace_id validado;
entity.id validado;
job_id validado;
token vazio rejeita tudo;
logs sem token.
```

---

## 19.5 Acoplamento prematuro ao renderer real

### Risco

Bloquear backend à espera do renderer.

### Mitigação

```text
dry-run;
mock client;
contratos versionados;
ExternalJobReference como fronteira;
testes com callbacks simulados.
```

---

# 20. Próximo passo após este backlog

Depois de validar este backlog, o próximo passo será gerar uma pipeline de prompts para IA local executar a integração por fases.

Pipeline recomendada:

```text
Pipeline 01 — Settings, cliente interno e service registry
Pipeline 02 — Evolução de ExternalJobReference
Pipeline 03 — Callback dispatcher e idempotência
Pipeline 04 — ContentPackRequest → Renderer job
Pipeline 05 — Callback de Content Generation
Pipeline 06 — Report e MediaKit jobs
Pipeline 07 — Callbacks de Report e MediaKit
Pipeline 08 — Contratos placeholder para Intelligence Engine
Pipeline 09 — Segurança, retries, logs e Admin
Pipeline 10 — Testes end-to-end e hardening
```

O resultado esperado desta fase é:

> O Backend Core deixa de apenas criar entidades e passa a orquestrar jobs externos de forma segura, idempotente e rastreável, sem violar a fronteira entre Django, FastAPI e Renderer.
