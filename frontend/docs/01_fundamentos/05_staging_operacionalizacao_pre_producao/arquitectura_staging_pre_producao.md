# Arquitectura Alvo — Staging Pré-Produção

> Fase: `05_staging_operacionalizacao_pre_producao` (STG-PRE-001)
> Estado: documento alvo (arquitectura desejada), não estado final da fase
> Data: 2026-07-02
> Fonte: [`01_backlog.md`](01_backlog.md), documentos finais da fase 04
> (`arquitectura_staging_ie_renderer.md`, `estado_staging_ie_renderer.md`,
> `resultados_execucao/prompt_10_estado_final_staging_resultado.md`),
> [`docs/configuracao/portas_projeto.md`](../../../../docs/configuracao/portas_projeto.md),
> `.env.example` dos quatro serviços, `backend_core/config/settings.py`,
> `backend_core/apps/integrations_bridge/health.py`,
> `backend_core/docs/fundamentos/03_observabilidade_staging_ecossistema/matriz_operacional_servicos.md`.

Este documento descreve a arquitectura **alvo** para transformar o piloto
técnico staging (fase 04) num ambiente de **staging pré-produção** formal.
Não descreve produção e não introduz nova funcionalidade de produto — é um
documento de operacionalização.

---

## 1. Os quatro níveis de ambiente

É essencial não confundir estes quatro níveis. Esta fase (05) tem como alvo o
nível **staging pré-produção**; o nível **produção** fica fora de escopo.

| Nível | Descrição | DB | Storage | Secrets | Estado nesta fase |
|---|---|---|---|---|---|
| **Dev local** | Uma máquina de developer, tudo em `localhost`, arranque manual | SQLite | filesystem local do Content Renderer | placeholders de dev partilhados manualmente | **existente** (fases 01–04) |
| **Staging técnico** | Os quatro serviços a correr de forma reproduzível, ainda em `localhost`/máquina única, IE e Renderer reais (sem dry-run) | SQLite (fase 04) ou PostgreSQL local | filesystem local | mesmo token partilhado, ainda gerido manualmente | **validado** (fase 04 — `pronto_para_piloto_tecnico_staging`) |
| **Staging pré-produção** (alvo desta fase) | Ambiente reproduzível, isolado, com DB e storage não-locais, secrets geridos fora de `.env` manual, observabilidade e runbook | PostgreSQL dedicado (não SQLite) | object storage (provider a decidir) | secret store ou variáveis de CI/deploy, nunca hardcoded | **alvo — a construir pelos Prompts 02–11** |
| **Produção** | Ambiente com SLA, alta disponibilidade, alertas, rotação de secrets automatizada, aprovação operacional | PostgreSQL gerido/produção | object storage de produção | secret manager de produção | **fora de escopo** |

A tese da fase (backlog §2) resume o critério de passagem staging técnico →
staging pré-produção: *um fluxo funcional validado em dev só passa a ser
candidato a pré-produção quando é reproduzível, observável, seguro,
recuperável e independente de SQLite/storage local.*

---

## 2. Componentes e responsabilidades

| Componente | Stack | Papel | Fica igual nesta fase? |
|---|---|---|---|
| **Frontend Web** | Vite + React | UI; fala **exclusivamente** com o Backend Core | Sim — nenhuma alteração de fronteira |
| **Backend Core** | Django + DRF | Orquestrador; única fronteira que fala com IE/Renderer; dono do domínio de produto (auth, RBAC, campanhas, CampaignActions, artefactos, jobs) | Ganha DB alvo, secrets geridos, correlation-id, health mais rico |
| **Intelligence Engine** | FastAPI (stateless) | Diagnóstico síncrono de campanha (scores/grade/moments/recommendations); sem persistência, sem chamar outros serviços | Ganha registo de `request_id` a nível app |
| **Content Renderer** | Node/Express | Geração assíncrona de artefactos (report/media kit/content pack) via jobs + callback | Ganha object storage e `public_url`/`signed_url` estável |
| **Base de dados** | SQLite (dev) / PostgreSQL (alvo) | Persistência exclusiva do Backend Core; IE e Renderer não têm DB própria | Migra de SQLite para PostgreSQL nesta fase (STG-PRE-002) |
| **Object storage** | Filesystem local (actual) / provider a decidir | Persistência dos outputs do Content Renderer (PDF/PNG/HTML) | Introduzido nesta fase (STG-PRE-003) — decisão pendente |
| **Jobs / callbacks** | `ExternalJobReference` (Backend Core) ↔ `/jobs/` + callback (Content Renderer) | Ponte assíncrona entre a criação do artefacto e o resultado do render | Sem alteração de contrato; ganha correlation-id |

**Regra inviolável, sem excepção nesta fase:** o Frontend Web só fala com o
Backend Core (`:8100/api/v1`). Nunca chama Intelligence Engine nem Content
Renderer directamente, e nunca envia `X-Internal-Token` — esse cabeçalho é
exclusivo de comunicação serviço-a-serviço (Backend Core → IE / Renderer, e
Content Renderer → Backend Core no callback).

---

## 3. Portas canónicas e URLs

Fonte de verdade: [`docs/configuracao/portas_projeto.md`](../../../../docs/configuracao/portas_projeto.md).
As portas **não mudam** entre dev local, staging técnico e staging
pré-produção — mudam os *hosts* e o modo de arranque.

| Serviço | Porta | URL interna (staging pré-produção) | URL externa/pública |
|---|---|---|---|
| Frontend Web (dev/preview) | 5200 / 5201 | — | única entrada do utilizador |
| Backend Core | 8100 | `http://<host-backend>:8100/api/v1` | mesma, exposta ao frontend |
| Intelligence Engine | 8201 | `http://<host-ie>:8201` | **nunca exposta** ao frontend/utilizador |
| Content Renderer | 8202 | `http://<host-renderer>:8202` | **nunca exposta** ao frontend/utilizador; expõe apenas o endpoint de callback ao Backend Core |

**Portas proibidas** (validadas por `scripts/check-forbidden-ports.ps1`):
8000, 8001, 8002, 8003, 1420, 9011, 5173, 5174, 8080–8085. Este documento não
introduz nem referencia nenhuma como default activo.

Em staging pré-produção, `<host-backend>`, `<host-ie>`, `<host-renderer>`
deixam de ser implicitamente `localhost` — mas o esquema exacto de hosts
(máquinas separadas, containers, um único host com portas distintas) é uma
**decisão pendente** (§7).

---

## 4. Fluxos

### 4.1 Frontend → Backend Core

```text
Frontend (5200)  --HTTP, Authorization: Bearer <jwt>, X-Workspace-ID-->  Backend Core (8100) /api/v1/*
```

- Único `fetch()` no frontend (`shared/api/client.ts`); sem axios/WebSocket/EventSource.
- `X-Internal-Token` é removido activamente de qualquer header custom antes de sair do browser (`shared/api/security.ts`).
- Inalterado nesta fase.

### 4.2 Backend Core → Intelligence Engine (síncrono)

```text
Backend Core  --POST /intelligence/campaign, X-Internal-Token, X-Request-ID-->  Intelligence Engine (8201)
Backend Core  <--200 { status, engine, result:{...}, request_id }--  Intelligence Engine
```

- Síncrono, dentro do request do utilizador; não usa `ExternalJobReference` nem `/jobs/`.
- Governado por `INTELLIGENCE_ENGINE_ENABLED` / `INTELLIGENCE_ENGINE_DRY_RUN`. Em staging pré-produção: `ENABLED=true`, `DRY_RUN=false`.
- Timeout `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS`; retry só para falhas transitórias (`MAX_RETRIES`).
- **Alvo desta fase:** o IE passa a registar o `request_id` recebido a nível app (lacuna OBS-L01/L02 da fase 04) — ver STG-PRE-005.

### 4.3 Backend Core → Content Renderer (assíncrono, jobs)

```text
Frontend  --cria artefacto próprio (Report/MediaKit/ContentPackRequest)-->  Backend Core
Backend Core  --1) cria ExternalJobReference status=queued-->  (persistência local, antes de qualquer chamada)
Backend Core  --2) POST /jobs/, X-Internal-Token-->  Content Renderer (8202)  --202 Accepted-->  Backend Core (status=submitted)
```

- Governado por `EXTERNAL_JOBS_ENABLED` / `EXTERNAL_JOBS_DRY_RUN`. Em staging pré-produção: `ENABLED=true`, `DRY_RUN=false`.
- O job é persistido **antes** da chamada HTTP — nunca há chamada sem registo correspondente.

### 4.4 Callback Content Renderer → Backend Core

```text
Content Renderer  --render em background (RENDER_TIMEOUT_SECONDS)-->  grava output no storage alvo
Content Renderer  --POST /api/v1/internal/jobs/callback/, X-Internal-Token, retry exponencial-->  Backend Core
Backend Core (IsInternalService)  --aplica running/completed/partially_completed/failed-->  actualiza artefacto + Asset
```

- Retry do callback só em falhas transitórias (rede, timeout, 5xx); nunca em 4xx.
- **Alvo desta fase:** o output passa a residir em object storage (não filesystem local do Renderer) e o `Asset.public_url`/`signed_url` passa a ser persistido pelo Backend Core (lacuna conhecida da fase 04) — ver STG-PRE-003.

---

## 5. Base de dados

| Aspecto | Dev local / staging técnico (actual) | Staging pré-produção (alvo) |
|---|---|---|
| Engine | SQLite (`DB_ENGINE=sqlite`, default) | PostgreSQL (`DB_ENGINE=postgres`) — já suportado em `config/settings.py` |
| Quem usa | Só o Backend Core; IE e Renderer não têm DB própria | Igual |
| Porquê mudar | O callback do renderer corre noutro processo; SQLite não partilha linhas commitadas entre processos → callback pode dar 404 em cenários multi-processo | PostgreSQL suporta o loop multi-processo de forma fiável |
| Configuração | Defaults inseguros só válidos em dev (`DB_PASSWORD=postgres` no `.env.example` é placeholder, nunca usar em staging) | `DATABASE_URL` ou `DB_NAME`/`DB_USER`/`DB_HOST`/`DB_PORT`/`DB_PASSWORD` via secret store |
| Precedente já validado | `content_renderer/docker-compose.e2e.yml` já usa `postgres:16-alpine` para o harness E2E (dados em tmpfs, descartáveis) | Extensão do mesmo padrão para staging persistente (dados **não** descartáveis) |

Migrations, seed mínimo e validação por API contra o DB alvo são tratados em
STG-PRE-002 (Prompt 02), não neste documento.

---

## 6. Storage

| Aspecto | Dev local / staging técnico (actual) | Staging pré-produção (alvo) |
|---|---|---|
| Provider | `STORAGE_PROVIDER=local` (único implementado; `content_renderer/src/storage/storage.types.ts` valida contra uma lista fechada — hoje só `['local']`) | Provider de object storage — **decisão ainda pendente** (§11); nenhum provider foi escolhido nem inventado nesta fase |
| Abstracção | Já existe uma interface `StorageProvider` (`saveBuffer`, `buildStorageKey`, `name`) com uma única implementação (`local-storage.ts`); um provider S3/R2/MinIO seria uma **nova implementação da mesma interface**, sem tocar nos renderers nem no contrato de callback | Igual — a interface já é adequada; só falta a implementação do provider escolhido |
| Onde vive | `LOCAL_STORAGE_ROOT=./storage` no Content Renderer | Bucket/container remoto |
| Acesso ao ficheiro | `LOCAL_STORAGE_PUBLIC_BASE_URL=http://localhost:8202/files` (o Content Renderer serve os ficheiros directamente) | URL do provider (`public_url` ou `signed_url`, conforme contrato de §6.1) |
| `Asset.public_url` no Backend Core | **Populado desde o Prompt 03 (STG-PRE-003)** — campo `public_url` adicionado ao modelo `Asset` (migration `core.0002_asset_public_url`) e persistido a partir de `asset_data.public_url` no callback (`reports/callbacks.py`, `content/callbacks.py`); exposto em `GET /api/v1/assets/{id}/`. Continua vazio apenas se o Content Renderer não o enviar. | Igual — o campo é agnóstico de provider; um provider real só precisa de preencher `public_url` (ou, no futuro, `signed_url`) na resposta do callback |
| Modo local de desenvolvimento | Inalterado — `LOCAL_STORAGE_PUBLIC_BASE_URL` continua a alimentar `public_url` tal como antes | Deve continuar a funcionar sem regressão (compatibilidade obrigatória, validada no Prompt 03) |

### 6.1 Contrato de asset URL (definido no Prompt 03)

| Campo | Onde vive | Estado |
|---|---|---|
| `storage_key` | `Asset.storage_key` (Backend Core) e `AssetMetadata.storage_key` (Content Renderer) | Já estável — gerado por `buildStorageKey(workspaceId, jobId, fileName)`, portável entre providers |
| `public_url` | `Asset.public_url` (Backend Core, novo nesta fase) e `AssetMetadata.public_url` (Content Renderer, já existia) | **Resolvido nesta fase** para qualquer provider que preencha o campo; hoje só o provider `local` o preenche |
| `signed_url` | Não existe nenhum campo dedicado | **Não implementado.** Só necessário se o provider escolhido usar bucket privado com expiração; ficaria noutro campo (não reutilizar `public_url` para URLs que expiram) — decisão adiada até haver provider |
| Regra de expiração | N/A | Não definida — depende da escolha entre acesso público permanente vs. `signed_url` temporário |
| Acesso público ou privado | Público (storage local serve qualquer pedido dentro da raiz) | **Decisão pendente**, ligada à escolha do provider (§11) |

**O que ficou provider-agnóstico e já funciona hoje:** o Backend Core já
aceita e persiste `public_url` vindo de qualquer `storage_provider`
(`local`, `s3`, `r2`, `gcs` — `Asset.StorageProvider` já tem as 4 opções)
sem alteração adicional de código quando um provider real for escolhido; o
trabalho que falta é inteiramente do lado do Content Renderer (implementar
a interface `StorageProvider` para o provider escolhido).

---

## 7. Secrets

| Secret | Onde é usado | Regra |
|---|---|---|
| `INTERNAL_API_TOKEN` | Backend Core, Intelligence Engine, Content Renderer | Deve ser **idêntico** nos três serviços; viaja só em header `X-Internal-Token`; nunca em body/query/log |
| `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` | Backend Core (opcional) | Ausente/omitido ⇒ reutiliza `INTERNAL_API_TOKEN` (ver nota de robustez abaixo) |
| `SECRET_KEY` | Backend Core (Django) | Forte e único em staging/produção; nunca o valor de dev |
| `DB_PASSWORD` | Backend Core (só com `DB_ENGINE=postgres`) | Nunca hardcoded; nunca em connection string documentada |
| Credenciais de storage (futuras) | Content Renderer / Backend Core, conforme o provider escolhido | A definir com o provider (STG-PRE-003, ainda sem provider escolhido) |
| `STRIPE_WEBHOOK_SECRET` / `STRIPE_API_KEY` | Backend Core (billing, skeleton) | Fora do escopo desta fase |

**Estado actual (dev/staging técnico):** todos os secrets vivem em `.env`
local, não commitado (`.gitignore` cobre `.env`/`.env.*` em todos os quatro
serviços — corrigido no Prompt 04 para `backend_core` e `intelligence_engine`,
que só cobriam `.env` exacto — mantendo só `.env.example` versionado com
placeholders vazios/genéricos). Este mecanismo é adequado para dev, **não**
para staging pré-produção formal — falta um mecanismo de fornecimento
controlado (secret store, variáveis de CI/deploy). Ver
`resultados_execucao/prompt_04_gestao_segredos_resultado.md` para o
inventário completo, o mecanismo recomendado (nenhuma decisão de
infraestrutura tomada — não existe ainda CI/CD neste repositório) e o guia de
rotação.

**Guardas de arranque já existentes** (fail-fast, não alterar):
- Backend Core recusa arrancar se `DEBUG=False` + IE `ENABLED` + `DRY_RUN=False` + token vazio.
- Intelligence Engine recusa arrancar se `INTERNAL_API_TOKEN` vazio em `APP_ENV=production`.
- Content Renderer recusa arrancar com token vazio, salvo `ALLOW_INSECURE_EMPTY_TOKEN=true` — **flag exclusiva de dev, nunca usar em staging pré-produção**.
- **Comparação de token é sempre em tempo constante** nos três serviços (`hmac.compare_digest` no Backend Core e no Intelligence Engine, `timingSafeEqual` no Content Renderer) — confirmado por leitura de código no Prompt 04, não alterado.

**Correcção de robustez (Prompt 04):** `INTELLIGENCE_ENGINE_INTERNAL_TOKEN`
tinha um efeito perigoso do `python-decouple` — se a chave estivesse
**presente mas vazia** no `.env` (`INTELLIGENCE_ENGINE_INTERNAL_TOKEN=`), o
decouple devolvia a string vazia literal em vez de aplicar o default
(reutilizar `INTERNAL_API_TOKEN`), deixando o Backend Core a enviar um token
vazio ao Intelligence Engine sem qualquer aviso. Corrigido em
`config/settings.py` (`config(..., default="") or INTERNAL_API_TOKEN`) para
que qualquer valor vazio — chave ausente ou presente-e-vazia — resulte
sempre na reutilização do token partilhado. Ver relatório do Prompt 04 para o
incidente que revelou este problema.

**Frontend:** `.env.example` só contém `VITE_BACKEND_API_BASE_URL`. Nunca deve
conter `INTERNAL_API_TOKEN`, `X-Internal-Token`, URLs internas de IE/Renderer,
nem credenciais de DB/storage.

---

## 8. Logs e observabilidade

| Aspecto | Estado |
|---|---|
| Logs estruturados Backend Core | `LOGGING` em `config/settings.py`: loggers `integrations_bridge`, `campaigns.intelligence`, e (desde o Prompt 05) `campaign_actions`, `reports`, `content` — todos na consola, nível `LOG_LEVEL` |
| Logs Intelligence Engine | Logger JSON estruturado próprio, com redacção de chaves sensíveis; desde o Prompt 05 regista `request_id`/`workspace_id` a nível app em `POST /intelligence/campaign` (`intelligence.request_received`/`intelligence.request_completed`) |
| Logs Content Renderer | Logger JSON com redacção recursiva (`token\|secret\|password\|authorization\|api_key\|credential`); já incluía `request_id` por job (inalterado) |
| **Correlation-id ponta-a-ponta** | **Resolvido no Prompt 05 (STG-PRE-005)** — ver §8.1 |
| Secrets em logs | Greps a 0 nos três serviços, revalidados no Prompt 05 após as alterações de logging | Manter a 0; qualquer alteração de logging deve re-validar com grep |
| Estratégia de agregação/retenção | **Não existe** (logs só em consola/stdout de cada processo) | **Decisão pendente** (§11) — fora do alcance desta fase |

### 8.1 Correlation-id (STG-PRE-005)

Um `request.correlation_id` nasce no Backend Core, em
`apps.core.middleware.CorrelationIdMiddleware` (primeiro middleware depois do
WhiteNoise), a partir do cabeçalho `X-Request-ID` (reutilizado se presente e
bem-formado — `[A-Za-z0-9_-]{1,64}`; gerado via `uuid4().hex` caso contrário)
e devolvido no cabeçalho de resposta com o mesmo nome. Esse valor é a mesma
identidade que flui por:

- **Intelligence Engine (síncrono):** `CampaignIntelligenceService.request_id`
  → corpo/cabeçalho `X-Request-ID` da chamada → agora também registado a
  nível app no Intelligence Engine (fechando a lacuna OBS-L01/L02 da fase 04).
- **`CampaignAction.correlation_id`** (campo novo) — populado em
  `perform_create`, devolvido na resposta da API.
- **`Report.correlation_id` / `MediaKit.correlation_id` /
  `ContentPackRequest.correlation_id`** (campos novos, mesmo mecanismo).
- **`ExternalJobReference.request_id`** (campo já existente) — deixa de ser
  gerado de forma independente por job; quando a criação vem de um pedido
  HTTP, herda o mesmo `correlation_id`, o que o liga directamente ao
  Report/MediaKit/ContentPackRequest que o criou. Continua a ser gerado
  automaticamente quando não há id explícito (retries, comandos de gestão) —
  compatibilidade total, nada quebra.
- **Content Renderer** — recebe o mesmo valor no cabeçalho `X-Request-ID` e
  no corpo (`envelope.request_id`); já tinha esta capacidade antes desta
  fase (nenhuma alteração de código do Content Renderer foi necessária).
- **Callback Content Renderer → Backend Core** — o job (e portanto o
  `request_id`) é o mesmo; os logs de `callback_received`/`callback_processed`
  no Backend Core continuam a incluir `request_id`.

`correlation_id` **complementa** os ids de domínio — nunca substitui
`action_id`/`report_id`/`media_kit_id`/`content_pack_request_id`/`job_id`/
`campaign_id`, que continuam a ser as chaves primárias de cada entidade.

Uma operação completa pode ser seguida assim (ids reais, exemplo redigido):

```text
X-Request-ID: e2e-smoke-trace-002
  → CampaignAction ou Report criado com correlation_id=e2e-smoke-trace-002
  → ExternalJobReference criado com request_id=e2e-smoke-trace-002
  → Backend Core loga: job_created / internal_call start / job_submitted
      (todos com request_id=e2e-smoke-trace-002)
  → Content Renderer loga: job.accepted / render.started / render.completed /
      callback.started / callback.completed
      (todos com request_id=e2e-smoke-trace-002)
  → Backend Core loga: callback_received / callback_processed
      (request_id=e2e-smoke-trace-002)
```

**Nota de robustez descoberta durante a implementação:** os novos loggers
(`campaign_actions.views`, `reports.views`, `content.services`) só passaram a
emitir de facto depois de serem adicionados ao dicionário `LOGGING` — sem essa
entrada, o logger de último recurso do Python só deixa passar `WARNING` e
acima, e os `logger.info(...)` de criação ficavam silenciosamente sem efeito.
Corrigido; há um teste dedicado (`test_loggers_emit_info`) que impede esta
regressão específica de voltar a acontecer sem ser notada.

---

## 9. Healthchecks

| Endpoint | Serviço | Autenticação | Cobre |
|---|---|---|---|
| `GET /health` | Intelligence Engine | Público | Liveness apenas (stateless, sem dependências) |
| `GET /health` | Content Renderer | Público | Liveness apenas (não reporta storage nem callback) |
| `GET /api/v1/system/health/dependencies/` | Backend Core | **Staff-only** (`IsAdminUser`) | Agregado: sonda IE + Content Renderer (via `/health` público, sem token) + DB (`SELECT 1`); nunca lança excepção, devolve sempre 200 com `status` por dependência (`ok\|degraded\|unavailable\|misconfigured\|unknown`) |
| `GET /api/v1/system/health/live/` (**novo, STG-PRE-006**) | Backend Core | Público | Liveness pura — nenhuma dependência verificada, espelha o `/health` do IE/CR |
| `GET /api/v1/system/health/ready/` (**novo, STG-PRE-006**) | Backend Core | Público | Readiness mínima — só a base de dados (`200` ok / `503` unavailable); **não** reflecte IE/Renderer de propósito (ver §9.1) |
| `GET /api/v1/schema/` | Backend Core | Público | Continua disponível como proxy adicional de liveness (compatibilidade; não removido) |

O healthcheck agregado (`backend_core/apps/integrations_bridge/health.py`) foi
**validado com utilizador staff real em runtime** no Prompt 06 (não apenas
mocks) — ver `resultados_execucao/prompt_06_health_logs_resultado.md`. Não
introduz nem expõe URLs completas ou secrets — reduz a `configured`/`not_configured`.

### 9.1 Liveness vs. readiness (STG-PRE-006)

Antes desta iteração, o Backend Core não tinha nenhum endpoint dedicado de
liveness/readiness — só o agregado (staff-only, pesado, pensado para
diagnóstico operacional) e o `/api/v1/schema/` como proxy improvisado. Foram
adicionados dois endpoints **públicos e mínimos**, ao mesmo nível de
segurança do `/health` do IE e do Content Renderer:

- **Liveness** (`/live/`): não verifica nada — só confirma que o processo
  responde. Nunca deve reportar falha só porque uma dependência está em baixo.
- **Readiness** (`/ready/`): verifica **só a base de dados**. IE e Content
  Renderer ficam deliberadamente fora — são chamadas por-pedido já tratadas
  com erros claros (502/503) nos endpoints que as usam; incluir o seu estado
  na readiness marcaria o serviço inteiro como "not ready" sempre que um
  deles estivesse em baixo, o que não é verdade (a maior parte da API
  continua a funcionar sem IE/Renderer). O detalhe operacional de IE/Renderer
  continua exclusivo do endpoint agregado staff-only.

**Achado relevante descoberto durante a validação real:** em Windows, o
default `INTELLIGENCE_ENGINE_BASE_URL=http://localhost:8201` fazia o
healthcheck agregado (e as chamadas síncronas reais ao IE) demorarem
sistematicamente **~2 segundos extra por chamada** — e o dobro (~4s) quando o
IE estava mesmo em baixo — porque `localhost` resolve para `::1` e
`127.0.0.1`, e o `uvicorn` só escuta em IPv4; cada chamada esgotava o timeout
completo na tentativa IPv6 antes de recuar para IPv4. Corrigido nesta
iteração: o default passou a `http://127.0.0.1:8201` (`config/settings.py`,
`.env.example`, `docs/configuracao/portas_projeto.md`), eliminando a
ambiguidade. Validado: `duration_ms` do IE no healthcheck caiu de ~2000ms
para ~40ms.

---

## 10. Limites conhecidos (herdados da fase 04, ainda por resolver)

- **DB validado tecnicamente contra PostgreSQL 16 no Prompt 02** (migrations, seed, CRUD via API, `pytest apps/campaign_actions` 56/56 — ver `resultados_execucao/prompt_02_db_staging_resultado.md`), mas o **ambiente de staging persistente ainda não foi cortado para PostgreSQL** — o Backend Core de staging técnico continua a arrancar em SQLite por default (`DB_ENGINE=sqlite`); a validação usou uma instância PostgreSQL descartável (container efémero), não uma instância de staging permanente.
- **Object storage continua `local` até se escolher e implementar um provider real (STG-PRE-003 fecha só a plumbing de `public_url`, não a escolha de provider)** — ver `resultados_execucao/prompt_03_object_storage_resultado.md`. `signed_url` continua por definir (depende do provider).
- **Secrets: inventário, `.gitignore` e rotação fechados no Prompt 04** (ver `resultados_execucao/prompt_04_gestao_segredos_resultado.md`), mas o mecanismo de fornecimento continua `.env` manual — não há secret store nem CI/CD; decisão de infraestrutura ainda pendente (§11).
- **Correlation-id único ponta-a-ponta resolvido no Prompt 05** (ver §8.1 e `resultados_execucao/prompt_05_correlation_id_resultado.md`) — uma operação é rastreável BC→IE→CampaignAction→Artefacto→Job→Renderer→Callback via o mesmo id.
- **Health agregado validado com staff real, liveness/readiness dedicados criados no Prompt 06** (ver §9/§9.1 e `resultados_execucao/prompt_06_health_logs_resultado.md`) — inclui a correcção do achado de latência IPv6/`localhost` do Intelligence Engine. Continua sem storage no healthcheck (só `local`, sem dependência externa a sondar) e sem agregação/retenção central de logs (fora do escopo desta fase).
- `Asset.public_url` **já é populado desde o Prompt 03** quando o Content Renderer o envia (hoje sempre, via storage `local`); deixa de ser uma limitação de esquema, mas continua vazio se algum provider futuro não o preencher.
- `recommendation_ref` é posicional (o IE real não devolve `id`) — fora do escopo desta fase.
- `MediaKit` não tem estado `failed` próprio — tratado em STG-PRE-007.
- RBAC/UX mínimo (capabilities, mensagens de erro) — tratado em STG-PRE-008.
- E2E ainda é smoke manual, não automatizado — tratado em STG-PRE-009.
- Nenhum destes limites é resolvido por este documento; são o mapa do que falta.

---

## 11. Decisões pendentes

Estas decisões **não são tomadas neste documento** — ficam registadas para
que não sejam decididas implicitamente num `.env` local:

| Decisão | Opções em consideração | Onde se decide |
|---|---|---|
| **DB alvo de staging** | **PostgreSQL confirmado e validado tecnicamente (Prompt 02, `resultados_execucao/prompt_02_db_staging_resultado.md`)** — migrations, seed e CRUD via API passam; falta ainda decidir a topologia da instância **persistente** de staging (dedicada vs. partilhada, gestão de backups, host) — a validação usou um container descartável | STG-PRE-002 (técnico fechado) / topologia persistente ainda por decidir |
| **Provider de object storage** | S3, R2, MinIO ou equivalente — **continua nenhum escolhido** (deliberadamente, ver `resultados_execucao/prompt_03_object_storage_resultado.md`); `content_renderer` só tem `local` implementado, mas a interface `StorageProvider` já está pronta para receber uma nova implementação sem tocar nos renderers | STG-PRE-003 (interface/contrato fechados; escolha do provider continua pendente) |
| **Mecanismo de secrets** | Inventário e recomendação documentados no Prompt 04 (`resultados_execucao/prompt_04_gestao_segredos_resultado.md`); **continua sem infraestrutura escolhida/provisionada** — não existe CI/CD neste repositório (sem `.github/workflows` nem equivalente), pelo que a escolha entre secret store dedicado, variáveis de CI/deploy ou outro mecanismo fica para quando a plataforma de deploy de staging for decidida | STG-PRE-004 (inventário/rotação/gitignore fechados; mecanismo de fornecimento continua pendente) |
| **`public_url` vs `signed_url`** | **`public_url` resolvido** (campo `Asset.public_url`, Prompt 03) para qualquer provider que o preencha; `signed_url` continua por definir — só relevante se o provider escolhido usar bucket privado com expiração | `public_url`: STG-PRE-003 (fechado) / `signed_url`: por decidir junto com o provider |
| **Estratégia de logs (agregação/retenção)** | Ainda não há ferramenta de agregação; logs só em stdout por processo | STG-PRE-006 (parcialmente), fora de escopo total desta fase |
| **Ferramenta E2E** | Playwright é a opção preferencial mencionada no backlog; nenhuma ferramenta instalada ainda | STG-PRE-009 |
| **Esquema de hosts em staging pré-produção** | Máquina única com portas distintas vs. hosts/containers separados — nenhum definido | Fora do escopo explícito do backlog actual; a esclarecer antes do runbook (STG-PRE-010) |

---

## 12. Referências

- Backlog desta fase: [`01_backlog.md`](01_backlog.md)
- Pipeline de prompts: [`02_prompts_staging_operacionalizacao.md`](02_prompts_staging_operacionalizacao.md)
- Fase 04 — estado: `frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/estado_staging_ie_renderer.md`
- Fase 04 — arquitectura: `frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/arquitectura_staging_ie_renderer.md`
- Fase 04 — fecho: `frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_10_estado_final_staging_resultado.md`
- Mapa de portas: `docs/configuracao/portas_projeto.md`
- Matriz operacional (fase 03, ainda válida para portas/env/dependências): `backend_core/docs/fundamentos/03_observabilidade_staging_ecossistema/matriz_operacional_servicos.md`
- Healthcheck agregado: `backend_core/apps/integrations_bridge/health.py`
- `.env.example` de cada serviço: `backend_core/.env.example`, `intelligence_engine/.env.example`, `content_renderer/.env.example`, `frontend/.env.example`
