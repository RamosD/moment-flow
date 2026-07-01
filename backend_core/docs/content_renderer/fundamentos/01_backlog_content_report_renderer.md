# Backlog: Content e Report Renderer

# ChartRex / MomentFlow — Content Renderer

## 1. Objectivo do documento

Este documento define o backlog técnico para criar o serviço **Content/Report Renderer** da plataforma ChartRex / MomentFlow.

Este serviço será responsável por receber jobs enviados pelo **Backend Core Django**, gerar activos visuais mínimos e devolver o resultado ao Django via callback interno autenticado.

O objectivo desta fase não é criar um editor visual avançado nem um motor de vídeo. O objectivo é criar um renderer funcional, simples e confiável que prove o ciclo:

```text id="94kb7n"
Django cria pedido
  ↓
Django cria ExternalJobReference
  ↓
Renderer recebe job
  ↓
Renderer gera ficheiros reais
  ↓
Renderer envia callback para Django
  ↓
Django cria Asset / actualiza Output / Report / MediaKit
```

---

## 2. Tese arquitectural

A regra arquitectural mantém-se:

```text id="8o443a"
Django governa o produto.
FastAPI calcula e executa.
Renderer gera activos.
```

Neste contexto:

```text id="x03rin"
Backend Core Django:
  valida utilizador;
  valida workspace;
  valida RBAC;
  valida billing/créditos;
  cria ContentPackRequest;
  cria Report;
  cria MediaKit;
  cria ExternalJobReference;
  envia job;
  recebe callback;
  cria Asset;
  actualiza ContentOutput/Report/MediaKit;
  emite Notification;
  regista Audit.

Content/Report Renderer:
  recebe job;
  valida envelope;
  valida token interno;
  interpreta payload;
  selecciona template;
  gera PNG/JPG/WebP/PDF/ZIP simples;
  guarda ficheiro em storage local inicial;
  devolve metadata via callback;
  não decide permissões;
  não decide billing;
  não cria utilizadores;
  não conhece RBAC.
```

---

## 3. Nome e localização sugerida

Serviço recomendado:

```text id="mtm9z4"
content_renderer
```

Localização sugerida no repositório:

```text id="kqxx19"
D:\Workspace\ChartRex\momentflow\content_renderer
```

Documentação:

```text id="sqn26g"
docs\content_renderer\fundamentos\01_backlog_content_report_renderer.md
docs\content_renderer\fundamentos\resultados
```

---

## 4. Stack técnica recomendada

Para renderer estático e PDF, a opção mais prática é **Node.js + TypeScript**.

Stack recomendada:

```text id="x0hzwu"
Node.js;
TypeScript;
Fastify ou Express;
Zod;
Sharp;
Satori ou SVG manual inicial;
Playwright, apenas se necessário para PDF;
pdf-lib ou Playwright PDF;
Pino ou logger estruturado;
Vitest;
tsx;
dotenv.
```

Alternativa aceitável:

```text id="lffk5d"
Python FastAPI + Pillow + WeasyPrint/ReportLab
```

Mas a recomendação principal é Node.js/TypeScript porque futuras fases de renderização podem evoluir melhor para:

```text id="8f36zv"
Satori;
Sharp;
Playwright;
Remotion;
FFmpeg.
```

---

## 5. Escopo desta fase

Esta fase deve implementar apenas o renderer mínimo funcional.

Inclui:

```text id="y1lm76"
endpoint de healthcheck;
endpoint para receber jobs;
validação de X-Internal-Token;
validação de envelope;
content_generation;
report_generation;
media_kit_generation;
templates simples;
geração de PNG;
geração de JPG ou WebP opcional;
geração de PDF simples;
geração de ZIP simples, opcional;
storage local;
callback para Django;
logs estruturados;
testes;
documentação.
```

---

## 6. Fora do escopo desta fase

Não implementar ainda:

```text id="pvjpdg"
editor visual;
template builder visual;
vídeo;
reels;
shorts;
Remotion;
FFmpeg;
animações;
upload real para S3/R2;
integração com CDN;
login próprio;
RBAC próprio;
billing próprio;
base de dados própria complexa;
fila assíncrona complexa;
Kubernetes;
multi-worker avançado;
renderização baseada em IA generativa;
integração com Canva/CapCut;
publicação automática em redes sociais.
```

---

## 7. Contrato de entrada esperado

O renderer deve receber jobs do Django com um envelope semelhante a:

```text id="a7sspb"
{
  "job_id": "<external_job_reference_id>",
  "workspace_id": "<workspace_id>",
  "request_id": "<request_id>",
  "job_type": "content_generation",
  "callback_url": "http://localhost:8000/api/v1/internal/jobs/callback/",
  "entity": {
    "type": "content_pack_request",
    "id": "<uuid>"
  },
  "payload_version": "1.0",
  "payload": {}
}
```

Campos obrigatórios:

```text id="ni2spr"
job_id;
workspace_id;
request_id;
job_type;
callback_url;
entity.type;
entity.id;
payload_version;
payload.
```

---

## 8. Headers obrigatórios

Todas as chamadas recebidas do Django devem exigir:

```text id="91zwxr"
X-Internal-Token: <INTERNAL_API_TOKEN>
X-Workspace-ID: <workspace_id>
X-Job-ID: <external_job_reference_id>
X-Request-ID: <request_id>
Content-Type: application/json
```

Regras:

```text id="wqt0vj"
sem X-Internal-Token → 403;
token errado → 403;
token vazio no ambiente → rejeitar tudo;
workspace header diferente do body → 400;
job header diferente do body → 400;
request header diferente do body → 400 ou warning controlado;
payload inválido → 400.
```

---

## 9. Contrato de callback para Django

O renderer deve chamar o callback do Django com:

```text id="xfal8z"
POST <callback_url>
X-Internal-Token: <INTERNAL_API_TOKEN>
Content-Type: application/json
```

Payload de sucesso:

```text id="hcy85s"
{
  "job_id": "<external_job_reference_id>",
  "workspace_id": "<workspace_id>",
  "status": "completed",
  "entity": {
    "type": "content_pack_request",
    "id": "<uuid>"
  },
  "result": {
    "outputs": []
  },
  "error": null,
  "metadata": {
    "renderer": "content_renderer",
    "renderer_version": "0.1.0"
  }
}
```

Payload de falha:

```text id="wkmoej"
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
    "code": "render_failed",
    "message": "Falha ao gerar o conteúdo.",
    "details": {}
  },
  "metadata": {
    "renderer": "content_renderer",
    "renderer_version": "0.1.0"
  }
}
```

---

## 10. Tipos de job suportados no MVP

O renderer deve suportar:

```text id="5ruj9x"
content_generation;
report_generation;
media_kit_generation.
```

Não suportar ainda:

```text id="9sx3hl"
content_preview;
video_rendering;
metrics_collection;
moment_detection;
insight_generation;
recommendation_generation.
```

Se receber job type não suportado, deve devolver erro controlado ou callback failed.

---

# 11. Backlog por épicos

---

# Épico CR-01 — Fundação do serviço

## CR-001 — Criar projecto content_renderer

### Objectivo

Criar a estrutura base do serviço de renderização.

### Tarefas

```text id="5v23a5"
Criar pasta content_renderer.
Inicializar projecto Node.js com TypeScript.
Configurar package.json.
Configurar tsconfig.json.
Configurar estrutura src/.
Configurar scripts dev, build, start, test, lint.
Criar .env.example.
Criar README.md inicial.
Criar endpoint /health.
```

### Estrutura sugerida

```text id="4mmdcl"
content_renderer/
  package.json
  tsconfig.json
  .env.example
  README.md

  src/
    app.ts
    server.ts

    config/
      env.ts

    http/
      routes.ts
      middleware.ts

    jobs/
      job.schema.ts
      job.types.ts
      job.controller.ts
      job.service.ts

    renderers/
      content/
      reports/
      media-kits/

    templates/
      registry.ts

    storage/
      local-storage.ts

    callbacks/
      callback.client.ts

    logging/
      logger.ts

    errors/
      errors.ts

  tests/
```

### Critérios de aceitação

```text id="inok0c"
serviço arranca localmente;
endpoint /health devolve 200;
TypeScript compila;
README explica como executar;
.env.example existe.
```

---

## CR-002 — Configuração por ambiente

### Objectivo

Centralizar variáveis de ambiente do renderer.

### Variáveis mínimas

```text id="67kaze"
PORT=8002
NODE_ENV=development
INTERNAL_API_TOKEN=
RENDERER_PUBLIC_BASE_URL=http://localhost:8002
BACKEND_CORE_BASE_URL=http://localhost:8000
LOCAL_STORAGE_ROOT=./storage
LOCAL_STORAGE_PUBLIC_BASE_URL=http://localhost:8002/files
MAX_JOB_PAYLOAD_BYTES=1048576
CALLBACK_TIMEOUT_SECONDS=20
RENDER_TIMEOUT_SECONDS=30
```

### Tarefas

```text id="kr2o28"
Criar loader de env.
Validar env obrigatórias.
Falhar arranque se INTERNAL_API_TOKEN estiver vazio em modo production.
Permitir INTERNAL_API_TOKEN vazio em development apenas se explicitamente autorizado.
Criar testes de configuração.
```

### Critérios de aceitação

```text id="okdjxp"
env é validado no arranque;
produção rejeita token vazio;
desenvolvimento funciona com configuração explícita;
settings não têm segredos hardcoded.
```

---

## CR-003 — Logger estruturado

### Objectivo

Criar logging operacional sem expor segredos.

### Tarefas

```text id="ngn9id"
Configurar logger.
Logar job_id, workspace_id, request_id, job_type e status.
Não logar INTERNAL_API_TOKEN.
Não logar payload completo por defeito.
Logar erros de validação.
Logar render started/completed/failed.
```

### Critérios de aceitação

```text id="2xmhwq"
logs permitem rastrear job;
token não aparece nos logs;
erro inclui contexto suficiente;
testes validam ausência de token quando possível.
```

---

# Épico CR-02 — Segurança e contrato HTTP

## CR-101 — Middleware de autenticação interna

### Objectivo

Validar chamadas internas vindas do Django.

### Tarefas

```text id="gskmmb"
Criar middleware de autenticação.
Validar header X-Internal-Token.
Usar comparação segura.
Rejeitar token ausente.
Rejeitar token errado.
Rejeitar token vazio em production.
Não expor valor do token em erro/log.
```

### Critérios de aceitação

```text id="4xwv94"
sem token devolve 403;
token errado devolve 403;
token correcto permite continuar;
logs não expõem token.
```

---

## CR-102 — Validação de headers de job

### Objectivo

Validar consistência entre headers e body.

### Tarefas

```text id="h98t2d"
Validar X-Workspace-ID.
Validar X-Job-ID.
Validar X-Request-ID.
Comparar headers com body.
Rejeitar mismatch.
Criar erro claro.
Criar testes.
```

### Critérios de aceitação

```text id="67pmr5"
workspace mismatch devolve 400;
job mismatch devolve 400;
request mismatch é tratado conforme decisão;
headers válidos passam.
```

---

## CR-103 — Schema de envelope de job

### Objectivo

Validar o payload de entrada.

### Tarefas

```text id="hyslr0"
Criar job.schema.ts com Zod.
Validar job_id.
Validar workspace_id.
Validar request_id.
Validar job_type.
Validar callback_url.
Validar entity.
Validar payload_version.
Validar payload.
Limitar tamanho do payload.
Criar testes.
```

### Critérios de aceitação

```text id="dz6mti"
payload inválido devolve 400;
job_type não suportado devolve erro controlado;
payload válido é aceite;
schema é reutilizável nos testes.
```

---

# Épico CR-03 — Job receiver e dispatcher

## CR-201 — Endpoint POST /jobs

### Objectivo

Criar endpoint único para receber jobs do Django.

### Tarefas

```text id="chvj9z"
Criar POST /jobs.
Aplicar auth interna.
Aplicar validação de headers.
Aplicar validação de schema.
Chamar dispatcher por job_type.
Responder 202 accepted quando job é aceite.
Enviar callback completed ou failed depois da execução.
```

### Critérios de aceitação

```text id="30fvea"
POST /jobs aceita content_generation válido;
job inválido devolve 400;
token inválido devolve 403;
job aceite devolve 202;
dispatcher é chamado.
```

---

## CR-202 — Dispatcher por job_type

### Objectivo

Encaminhar cada job para o renderer correcto.

### Tarefas

```text id="kdw56f"
Criar job dispatcher.
Suportar content_generation.
Suportar report_generation.
Suportar media_kit_generation.
Job type desconhecido gera erro controlado.
Criar testes.
```

### Critérios de aceitação

```text id="d6bdh5"
content_generation chama renderer de conteúdo;
report_generation chama renderer de report;
media_kit_generation chama renderer de media kit;
job desconhecido falha de forma controlada.
```

---

## CR-203 — Execução síncrona controlada no MVP

### Objectivo

Executar jobs de forma simples no MVP, sem fila complexa.

### Decisão recomendada

No MVP, aceitar execução síncrona curta:

```text id="ozh5sd"
recebe job;
gera ficheiros;
envia callback;
responde 202 ou 200 conforme design.
```

Ou:

```text id="0yd5ed"
responde 202;
executa em background leve com setImmediate/promise;
envia callback.
```

### Recomendação

Usar background leve, sem Celery/BullMQ nesta fase.

### Critérios de aceitação

```text id="m7ra6s"
request HTTP não fica preso por tempo excessivo;
callback é enviado depois do render;
falha no render envia callback failed.
```

---

# Épico CR-04 — Storage local

## CR-301 — Criar storage local

### Objectivo

Guardar ficheiros renderizados localmente no MVP.

### Tarefas

```text id="3yuxam"
Criar storage/local-storage.ts.
Criar pasta por workspace.
Criar pasta por job.
Gerar storage_key estável.
Guardar buffer em disco.
Calcular checksum.
Calcular file_size_bytes.
Inferir mime_type.
Devolver metadata compatível com Django Asset.
```

### Estrutura sugerida

```text id="faj2ts"
storage/
  workspaces/
    <workspace_id>/
      jobs/
        <job_id>/
          output_001.png
          output_002.png
          report.pdf
```

### Critérios de aceitação

```text id="r9tkpe"
ficheiro é guardado;
metadata inclui storage_provider local;
metadata inclui storage_key;
metadata inclui file_name;
metadata inclui mime_type;
metadata inclui file_size_bytes;
metadata inclui checksum.
```

---

## CR-302 — Endpoint público/local de ficheiros

### Objectivo

Expor ficheiros localmente em desenvolvimento.

### Tarefas

```text id="bcgkx3"
Servir /files/* a partir de LOCAL_STORAGE_ROOT.
Impedir path traversal.
Não servir ficheiros fora da pasta storage.
Documentar que isto é apenas desenvolvimento.
```

### Critérios de aceitação

```text id="i5d1zz"
ficheiro gerado pode ser aberto via /files/;
path traversal é bloqueado;
README deixa claro que não é storage de produção.
```

---

# Épico CR-05 — Template engine mínimo

## CR-401 — Criar registry de templates

### Objectivo

Criar catálogo interno de templates simples.

### Tarefas

```text id="13iy0q"
Criar templates/registry.ts.
Mapear template_key para função de render.
Suportar templates vindos do payload.
Fallback para template genérico.
Criar testes.
```

### Templates iniciais

```text id="vg7m0y"
generic_post;
generic_story;
milestone_card;
weekly_growth_card;
release_card;
report_cover;
media_kit_cover.
```

### Critérios de aceitação

```text id="ag7grv"
template_key válido resolve função;
template desconhecido usa fallback;
registry é testado.
```

---

## CR-402 — Renderização por SVG simples

### Objectivo

Gerar imagem inicial sem editor visual.

### Tarefas

```text id="83nzmk"
Criar funções que geram SVG string.
Incluir title.
Incluir subtitle.
Incluir artist name.
Incluir track title.
Incluir metric/milestone quando existir.
Incluir brand color simples.
Converter SVG para PNG com Sharp.
Criar testes.
```

### Critérios de aceitação

```text id="38ihcq"
SVG é gerado;
PNG é gerado;
output tem dimensões correctas;
texto principal aparece no SVG;
render não depende de browser.
```

---

## CR-403 — Dimensões suportadas

### Objectivo

Suportar formatos visuais mínimos.

### Formatos

```text id="5mxa4k"
post_1_1: 1080x1080;
post_4_5: 1080x1350;
story_9_16: 1080x1920;
thumbnail_16_9: 1280x720.
```

### Critérios de aceitação

```text id="8tbcm3"
cada formato gera PNG na dimensão certa;
formato desconhecido usa fallback seguro;
testes verificam dimensões.
```

---

# Épico CR-06 — Content Generation

## CR-501 — Implementar renderer de content_generation

### Objectivo

Gerar outputs reais para ContentPackRequest.

### Tarefas

```text id="e0j3a1"
Criar renderers/content/content-generation.renderer.ts.
Ler payload de campaign, artist, track, content_pack, templates e expected_outputs.
Para cada expected_output, escolher template.
Gerar SVG.
Converter para PNG com Sharp.
Guardar no storage local.
Devolver result.outputs no formato esperado pelo Django.
Suportar completed e partially_completed.
```

### Output esperado

```text id="fqmsg2"
{
  "outputs": [
    {
      "output_type": "post",
      "format": "png",
      "status": "completed",
      "title": "...",
      "caption": "...",
      "cta": "...",
      "required": true,
      "template_key": "...",
      "asset": {
        "storage_provider": "local",
        "bucket": "",
        "storage_key": "...",
        "file_name": "...",
        "mime_type": "image/png",
        "file_size_bytes": 12345,
        "width": 1080,
        "height": 1080,
        "duration_seconds": null,
        "checksum": "..."
      },
      "metadata": {}
    }
  ]
}
```

### Critérios de aceitação

```text id="1hvzze"
content_generation gera pelo menos um PNG;
callback completed é enviado;
Django consegue criar ContentOutput/Asset com metadata recebida;
falha parcial é representada;
testes passam.
```

---

## CR-502 — Suportar packs iniciais

### Objectivo

Gerar outputs mínimos para os packs principais.

### Packs

```text id="eieotj"
release_pack;
milestone_pack;
weekly_growth_pack;
monthly_recap_pack;
auto_media_kit, apenas se vier como content pack simples.
```

### Critérios de aceitação

```text id="9e72pt"
release_pack gera card/post simples;
milestone_pack gera card de milestone;
weekly_growth_pack gera card semanal;
pack desconhecido usa fallback;
testes cobrem pelo menos 3 packs.
```

---

## CR-503 — Callback completed/failed para content_generation

### Objectivo

Enviar callback ao Django depois do render.

### Tarefas

```text id="pcjgen"
Criar callback client.
Enviar X-Internal-Token.
Enviar payload completed.
Enviar payload failed em erro.
Aplicar timeout.
Aplicar retry simples opcional.
Logar callback status.
Não expor token.
Criar testes com mock HTTP.
```

### Critérios de aceitação

```text id="v7jqnr"
callback completed é enviado;
callback failed é enviado em erro;
token não aparece nos logs;
erro de callback é registado.
```

---

# Épico CR-07 — Report Generation

## CR-601 — Implementar report_generation simples

### Objectivo

Gerar PDF simples para reports.

### Tarefas

```text id="3curd2"
Criar renderers/reports/report-generation.renderer.ts.
Ler payload de report.
Gerar HTML ou estrutura PDF simples.
Incluir título.
Incluir período.
Incluir artista/campanha/música.
Incluir secções esperadas.
Incluir estatísticas de smart links se vierem no payload.
Gerar PDF.
Guardar PDF no storage local.
Enviar callback completed.
```

### Critérios de aceitação

```text id="16b0dd"
report_generation gera PDF;
PDF é guardado;
asset metadata tem mime_type application/pdf;
callback completed é enviado;
Django marca Report completed e liga storage_asset.
```

---

## CR-602 — Report fallback em HTML/texto

### Objectivo

Garantir que mesmo sem Playwright pesado há output útil.

### Decisão

Se PDF com Playwright for pesado no ambiente local, permitir fallback:

```text id="mnqfcl"
gerar HTML;
guardar como .html;
enviar mime_type text/html;
Django continua a aceitar como asset.
```

### Critérios de aceitação

```text id="lnrl3w"
se PDF falhar por dependência, fallback HTML funciona;
falha fica registada em metadata;
callback continua completed se fallback for válido.
```

---

# Épico CR-08 — Media Kit Generation

## CR-701 — Implementar media_kit_generation simples

### Objectivo

Gerar media kit mínimo para artista/campanha.

### Tarefas

```text id="urr38t"
Criar renderers/media-kits/media-kit-generation.renderer.ts.
Ler payload de artist, campaign, track, items, smart links e assets.
Gerar PDF simples ou HTML.
Incluir capa.
Incluir bio.
Incluir links.
Incluir destaques.
Incluir secções de contacto/press, se existirem.
Guardar ficheiro.
Enviar callback completed.
```

### Critérios de aceitação

```text id="oe5ftr"
media_kit_generation gera ficheiro;
asset metadata é compatível com Django;
callback completed é enviado;
Django marca MediaKit generated.
```

---

# Épico CR-09 — Erros, fallback e partial success

## CR-801 — Normalizar erros de render

### Objectivo

Devolver erros previsíveis ao Django.

### Códigos sugeridos

```text id="lvux2e"
invalid_payload;
unsupported_job_type;
unsupported_template;
render_failed;
storage_failed;
callback_failed;
timeout.
```

### Critérios de aceitação

```text id="9u6jms"
erro tem code;
erro tem message;
erro tem details seguro;
callback failed usa formato esperado pelo Django.
```

---

## CR-802 — Partial success em content_generation

### Objectivo

Permitir que alguns outputs falhem e outros sejam gerados.

### Tarefas

```text id="4ypc4p"
Renderizar outputs independentemente.
Se output falhar, marcar status failed.
Se pelo menos um output obrigatório for gerado, status partially_completed ou completed conforme regra.
Se todos falharem, callback failed.
Documentar regra.
Criar testes.
```

### Critérios de aceitação

```text id="du0hmf"
falha de um output não quebra todos;
result.outputs inclui completed e failed;
status geral é coerente;
Django trata partial success.
```

---

# Épico CR-10 — Testes

## CR-901 — Testes unitários

### Objectivo

Cobrir validações e renderers.

### Tarefas

```text id="4gnzar"
Testar env loader.
Testar auth middleware.
Testar schema de job.
Testar dispatcher.
Testar template registry.
Testar storage local.
Testar callback client.
Testar render SVG.
```

### Critérios de aceitação

```text id="sracfl"
testes unitários passam;
casos de erro são cobertos;
token não aparece em snapshots/logs.
```

---

## CR-902 — Testes de integração com callback mockado

### Objectivo

Validar job completo sem Django real.

### Tarefas

```text id="6jyfou"
Mockar callback_url.
Enviar POST /jobs content_generation.
Verificar callback completed.
Verificar ficheiro criado.
Verificar metadata.
Testar failed.
Testar unsupported job type.
```

### Critérios de aceitação

```text id="cxh85k"
content_generation E2E passa;
report_generation E2E passa;
media_kit_generation E2E passa;
falha envia callback failed.
```

---

## CR-903 — Teste manual com Backend Core real

### Objectivo

Validar integração real com o Django já implementado.

### Cenário

```text id="jz5w5w"
Subir backend_core em localhost:8000.
Subir content_renderer em localhost:8002.
Configurar INTERNAL_API_TOKEN igual nos dois.
Configurar CONTENT_RENDERER_BASE_URL no Django.
Criar content pack request no Django.
Verificar job submitted.
Verificar renderer recebe job.
Verificar callback.
Verificar ContentOutput/Asset no Django.
```

### Critérios de aceitação

```text id="q9koq2"
Django envia job real;
renderer gera ficheiro;
callback chega ao Django;
Django cria Asset;
Django actualiza ContentOutput/Report/MediaKit.
```

---

# Épico CR-11 — Documentação

## CR-1001 — README do renderer

### Objectivo

Documentar execução local.

### Deve conter

```text id="qlyfha"
objectivo do serviço;
stack;
instalação;
.env;
scripts;
como correr dev;
como correr tests;
contrato POST /jobs;
contrato de callback;
exemplo de content_generation;
exemplo de report_generation;
limitações;
próximos passos.
```

### Critérios de aceitação

```text id="5x5krn"
README permite arrancar o serviço localmente;
exemplos não têm secrets;
contratos estão claros.
```

---

## CR-1002 — Estado de implementação

### Objectivo

Criar documento de estado após implementação.

### Caminho

```text id="0acopt"
docs\content_renderer\fundamentos\02_estado_content_report_renderer.md
```

### Deve conter

```text id="9hm99i"
features implementadas;
endpoints;
templates suportados;
formatos suportados;
jobs suportados;
validações executadas;
pendências;
riscos;
próximo passo.
```

---

# 12. Ordem recomendada de implementação

Ordem sugerida:

```text id="1w73ts"
1. CR-001 — Criar projecto content_renderer
2. CR-002 — Configuração por ambiente
3. CR-003 — Logger estruturado
4. CR-101 — Middleware de autenticação interna
5. CR-102 — Validação de headers
6. CR-103 — Schema de envelope
7. CR-201 — Endpoint POST /jobs
8. CR-202 — Dispatcher
9. CR-301 — Storage local
10. CR-401 — Registry de templates
11. CR-402 — Render SVG
12. CR-403 — Dimensões
13. CR-501 — content_generation
14. CR-503 — callback client
15. CR-502 — packs iniciais
16. CR-601 — report_generation
17. CR-602 — fallback HTML
18. CR-701 — media_kit_generation
19. CR-801 — erros
20. CR-802 — partial success
21. CR-901 — testes unitários
22. CR-902 — testes de integração
23. CR-903 — teste manual com Backend Core
24. CR-1001 — README
25. CR-1002 — Estado de implementação
```

---

# 13. MVP do Content/Report Renderer

O MVP fica pronto quando:

```text id="bu4c5o"
serviço arranca;
POST /jobs recebe content_generation;
renderer gera pelo menos um PNG real;
ficheiro é guardado em storage local;
callback completed chega ao Django;
Django cria Asset;
POST /jobs recebe report_generation;
renderer gera PDF ou HTML;
callback completed actualiza Report;
POST /jobs recebe media_kit_generation;
renderer gera PDF ou HTML;
callback completed actualiza MediaKit;
falhas enviam callback failed;
token interno é validado;
testes passam;
README existe.
```

---

# 14. Riscos

## 14.1 Acoplamento excessivo ao payload do Django

### Risco

Renderer ficar demasiado dependente da estrutura interna do Django.

### Mitigação

```text id="p674rb"
usar payload_version;
validar schema;
manter payload de domínio estável;
não importar modelos Django;
não aceder à base de dados do Django.
```

---

## 14.2 Renderer tentar decidir regras de produto

### Risco

Renderer decidir permissões, plano, créditos ou estado final comercial.

### Mitigação

```text id="hh9lwk"
renderer só gera activos;
Django decide permissões e billing;
callback apenas reporta resultado técnico.
```

---

## 14.3 Dependências pesadas de PDF

### Risco

Playwright dificultar instalação local.

### Mitigação

```text id="hn3c8q"
começar com HTML ou pdf-lib;
usar Playwright só se necessário;
permitir fallback HTML.
```

---

## 14.4 Storage local não servir para produção

### Risco

Storage local não é adequado para ambiente real.

### Mitigação

```text id="4orls4"
usar storage_provider=local no MVP;
manter interface de storage;
trocar depois por S3/R2 sem alterar callback.
```

---

## 14.5 Falha de callback

### Risco

Renderer gera ficheiro mas não consegue notificar Django.

### Mitigação

```text id="syunih"
callback client com timeout;
retry simples;
logs estruturados;
job_id e request_id em logs;
ficheiro permanece no storage local.
```

---

# 15. Critérios técnicos de pronto

Cada tarefa só fica pronta quando:

```text id="4balid"
código implementado;
testes relevantes criados;
lint passa;
typecheck passa;
serviço arranca;
contrato de payload validado;
callback testado;
token não aparece nos logs;
README ou documentação actualizada quando aplicável;
pendências documentadas.
```

---

# 16. Próximo passo após este backlog

Depois deste backlog, o próximo passo será gerar uma pipeline de prompts para a IA local implementar o renderer por fases.

Pipeline sugerida:

```text id="w6cftd"
Pipeline 01 — Fundação do serviço renderer
Pipeline 02 — Segurança, schema e endpoint de jobs
Pipeline 03 — Storage local e callback client
Pipeline 04 — Template engine e render SVG/PNG
Pipeline 05 — Content generation
Pipeline 06 — Report generation
Pipeline 07 — Media kit generation
Pipeline 08 — Erros, partial success e hardening
Pipeline 09 — Testes E2E com Backend Core
Pipeline 10 — Documentação final
```

Resultado esperado:

> O Content/Report Renderer passa a ser o primeiro serviço técnico real a responder aos jobs externos do Django, gerando ficheiros mínimos e fechando o ciclo operacional da plataforma.
