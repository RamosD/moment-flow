# Runbook — Staging Pré-Produção (MomentFlow / ChartRex)

> Fase: `05_staging_operacionalizacao_pre_producao` (STG-PRE-010)
> Âmbito: **staging pré-produção / staging técnico**. Este documento **não**
> descreve produção — não há SLA, alta disponibilidade, rotação automática de
> secrets nem aprovação operacional aqui (ver `arquitectura_staging_pre_producao.md`
> §1 para a distinção formal entre os quatro níveis de ambiente).
> Nenhum comando abaixo desactiva autenticação interna, RBAC ou validação de
> token — se um passo pedir isso, é um sinal de configuração errada, não uma
> instrução válida deste runbook.

---

## 0. Antes de começar

- Este runbook assume que já leu (ou tem à mão) `arquitectura_staging_pre_producao.md`
  e `docs/configuracao/portas_projeto.md` — as portas e regras arquitecturais
  aqui **não são redefinidas**, só aplicadas.
- Todos os comandos abaixo usam **placeholders** (`<...>`). Nenhum valor real
  de secret aparece neste ficheiro. Se alguma vez colar aqui um valor real por
  engano, remova-o antes de commitar.
- **Staging pré-produção real** (host remoto, PostgreSQL dedicado, object
  storage) ainda não está provisionado — ver §11 de
  `arquitectura_staging_pre_producao.md` (decisões pendentes: topologia de DB
  persistente, provider de storage, mecanismo de secrets, esquema de hosts).
  Este runbook cobre o que **já existe e é reproduzível hoje** (staging
  técnico, localhost, quatro serviços reais) e assinala explicitamente onde
  esse ambiente ainda não é staging pré-produção formal.

---

## 1. Pré-requisitos

| Componente | Requisito |
|---|---|
| Python | 3.13+ com um venv por serviço Python (`backend_core/venv`, `intelligence_engine/venv`) |
| Node.js | versão compatível com `content_renderer` e `frontend` (ver `package.json` de cada um); `pnpm` para o frontend |
| Base de dados | SQLite (default, ficheiro local) ou PostgreSQL 16+ se `DB_ENGINE=postgres` |
| Browsers (E2E) | Playwright + Chromium instalado (`npx playwright install chromium`) — só necessário para correr o E2E (Prompt 09) |
| Rede local | Portas 5200, 8100, 8201, 8202 livres (ver §2) |

Nenhum destes pré-requisitos assume produção — todos correm numa única
máquina de staging técnico.

---

## 2. Portas canónicas (fonte de verdade: `docs/configuracao/portas_projeto.md`)

| Serviço | Porta | Variável |
|---|---|---|
| Frontend Web (dev) | **5200** | `VITE_DEV_PORT` (implícito em `vite.config.ts`) |
| Frontend Preview (build) | **5201** | `vite.config.ts preview.port` |
| Backend Core (Django) | **8100** | arranque explícito: `runserver 127.0.0.1:8100` |
| Intelligence Engine (FastAPI) | **8201** | `INTELLIGENCE_ENGINE_PORT` |
| Content & Report Renderer (Node) | **8202** | `PORT` |

**Portas proibidas, nunca usar:** 8000, 8001, 8002, 8003, 1420, 9011, 5173,
5174, 8080–8085. Validar com:

```powershell
pwsh -ExecutionPolicy Bypass -File scripts/check-forbidden-ports.ps1
```

**Regra inviolável:** o Frontend só fala com o Backend Core (`:8100/api/v1`).
Nunca chama Intelligence Engine (`:8201`) nem Content Renderer (`:8202`)
directamente, e nunca envia `X-Internal-Token` — esse cabeçalho é exclusivo de
comunicação serviço-a-serviço.

---

## 3. Variáveis obrigatórias por serviço

Cada serviço tem o seu `.env.example` (copiar para `.env`, nunca commitar o
`.env` real). Lista das variáveis que **têm de estar definidas** para o
serviço arrancar de forma útil — os valores abaixo são placeholders, não
valores reais.

### 3.1 Backend Core (`backend_core/.env`)

```dotenv
SECRET_KEY=<secret-forte-unico-por-ambiente>
DEBUG=False                          # True só em dev local
ALLOWED_HOSTS=<hosts-do-ambiente>
CORS_ALLOWED_ORIGINS=<origem-do-frontend>

# Base de dados — NÃO existe suporte a DATABASE_URL neste projecto (nem
# dj-database-url nem django-environ nas dependências). Usar sempre as
# variáveis discretas abaixo.
DB_ENGINE=postgres                   # sqlite só em dev local
DB_NAME=<nome-da-base>
DB_USER=<utilizador>
DB_PASSWORD=<password>               # nunca o placeholder do .env.example
DB_HOST=<host-da-base>
DB_PORT=5432

INTERNAL_API_TOKEN=<token-partilhado-com-IE-e-Renderer>

INTELLIGENCE_ENGINE_BASE_URL=http://<host-ie>:8201   # 127.0.0.1, nunca "localhost", se local (ver nota de latência §7.2)
INTELLIGENCE_ENGINE_ENABLED=true
INTELLIGENCE_ENGINE_DRY_RUN=false    # true só esconde a falta de IE; nunca em staging válido

CONTENT_RENDERER_BASE_URL=http://<host-renderer>:8202
REPORT_RENDERER_BASE_URL=http://<host-renderer>:8202
EXTERNAL_JOBS_ENABLED=true
EXTERNAL_JOBS_DRY_RUN=false
```

### 3.2 Intelligence Engine (`intelligence_engine/.env`)

```dotenv
INTELLIGENCE_ENGINE_PORT=8201
APP_ENV=production                   # ou "development" em staging técnico
INTERNAL_API_TOKEN=<mesmo-token-do-Backend-Core>
```

### 3.3 Content Renderer (`content_renderer/.env`)

```dotenv
PORT=8202
NODE_ENV=production                  # ou "development" em staging técnico
INTERNAL_API_TOKEN=<mesmo-token-do-Backend-Core>
ALLOW_INSECURE_EMPTY_TOKEN=false     # NUNCA true em staging — ver §3.4
RENDERER_PUBLIC_BASE_URL=http://<host-renderer>:8202
BACKEND_CORE_BASE_URL=http://<host-backend>:8100
STORAGE_PROVIDER=local               # único implementado hoje; ver arquitectura §6
LOCAL_STORAGE_ROOT=<caminho-persistente>
LOCAL_STORAGE_PUBLIC_BASE_URL=http://<host-renderer>:8202/files
```

### 3.4 Frontend (`frontend/.env.local`)

```dotenv
VITE_BACKEND_API_BASE_URL=http://<host-backend>:8100/api/v1
```

O frontend **nunca** deve ter `INTERNAL_API_TOKEN`, `X-Internal-Token`, nem
URLs de IE/Renderer em nenhum `.env`.

---

## 4. Secrets obrigatórios (sem valores)

| Secret | Serviços que o usam | Regra |
|---|---|---|
| `INTERNAL_API_TOKEN` | Backend Core, Intelligence Engine, Content Renderer | **Idêntico nos três**; nunca em log/body/query; comparação em tempo constante já implementada (não alterar) |
| `SECRET_KEY` | Backend Core | Único e forte por ambiente; nunca o valor de dev |
| `DB_PASSWORD` | Backend Core | Nunca hardcoded, nunca em connection string documentada |
| Credenciais de storage | Content Renderer / Backend Core | Só relevante quando um provider de object storage for escolhido (ainda pendente — ver arquitectura §11) |
| `STRIPE_WEBHOOK_SECRET` / `STRIPE_API_KEY` | Backend Core (billing) | Fora do âmbito operacional deste runbook |
| `E2E_PASSWORD` | Harness E2E (Prompt 09, dev/CI only) | Nunca hardcoded; exportado no ambiente antes de correr `pnpm test:e2e` |

**Nunca fazer, em nenhuma circunstância de staging:**
- `ALLOW_INSECURE_EMPTY_TOKEN=true` no Content Renderer — desactiva
  autenticação interna por completo. É uma flag exclusiva de dev local,
  rejeitada em produção pelo próprio serviço; **nunca deve aparecer** num
  `.env` de staging.
- Deixar `INTERNAL_API_TOKEN` vazio com `DEBUG=False` — o Backend Core recusa
  arrancar nessas condições (guarda já existente, não contornar).
- Commitar qualquer `.env` real — só `.env.example` fica versionado
  (`.gitignore` cobre `.env`/`.env.*` nos quatro serviços).

---

## 5. Ordem de arranque

```text
1. Base de dados (se PostgreSQL — arrancar/confirmar disponível antes do Backend Core)
2. Backend Core          (depende da BD)
3. Intelligence Engine   (independente; sem BD própria)
4. Content Renderer      (independente; sem BD própria)
5. Frontend              (depende só do Backend Core estar de pé)
```

IE e Content Renderer podem arrancar em qualquer ordem entre si — nenhum
depende do outro. O frontend deve ser o último (senão mostra erros de rede
transitórios até o Backend Core responder).

---

## 6. Comandos por componente

### 6.1 Backend Core

```powershell
cd backend_core
python -m venv venv                      # uma vez
venv\Scripts\activate
pip install -r requirements.txt          # ou requirements com [binary] do psycopg em Windows, ver §9.1
python manage.py migrate
python manage.py seed_rbac               # roles/permissions do sistema (idempotente)
python manage.py seed_content            # templates + content packs de sistema (idempotente)
python manage.py check                   # deve devolver "0 issues"
python manage.py runserver 127.0.0.1:8100
```

`seed_billing` (planos) é opcional consoante o que o ambiente precisar de
exercitar; `seed_rbac`/`seed_content` são pré-requisitos mínimos para
qualquer fluxo de CampaignActions funcionar (roles + content packs).

### 6.2 Intelligence Engine

```powershell
cd intelligence_engine
python -m venv venv                      # uma vez
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8201
```

### 6.3 Content Renderer

```powershell
cd content_renderer
npm install                              # uma vez
npm run build
npm start                                # produção (dist/server.js)
# ou, em staging técnico/dev:
npm run dev                              # tsx watch, recarga automática
```

### 6.4 Frontend

```powershell
cd frontend
pnpm install                             # uma vez
pnpm build                               # valida tsc -b + vite build
pnpm dev                                 # porta 5200 (strictPort)
# ou, para servir o build:
pnpm preview                             # porta 5201
```

---

## 7. Healthchecks

### 7.1 Comandos directos

```powershell
# Backend Core — liveness pura (público, sem dependências verificadas)
curl http://127.0.0.1:8100/api/v1/system/health/live/

# Backend Core — readiness (público; só a base de dados; 200 ok / 503 unavailable)
curl http://127.0.0.1:8100/api/v1/system/health/ready/

# Backend Core — agregado (staff-only, requer JWT de um utilizador is_staff=True)
curl -H "Authorization: Bearer <ACCESS_TOKEN>" http://127.0.0.1:8100/api/v1/system/health/dependencies/

# Intelligence Engine — liveness (público)
curl http://127.0.0.1:8201/health

# Content Renderer — liveness (público)
curl http://127.0.0.1:8202/health
```

O endpoint agregado devolve `ok` / `degraded` / `unavailable` /
`misconfigured` / `unknown` por dependência (DB, IE, Content Renderer/Report
Renderer) — nunca lança excepção, nunca expõe URLs completas ou secrets.

**Não confundir liveness com readiness** (STG-PRE-006): liveness nunca falha
por uma dependência estar em baixo; readiness só cobre a base de dados —
IE/Renderer ficam deliberadamente fora da readiness porque a maior parte da
API continua a funcionar sem eles (o detalhe fica no endpoint agregado).

### 7.2 Nota de latência (Windows)

Usar sempre `127.0.0.1`, nunca `localhost`, em
`INTELLIGENCE_ENGINE_BASE_URL`. Em Windows, `localhost` resolve para `::1` E
`127.0.0.1`, e o `uvicorn` (bind IPv4 por default) não responde em `::1` —
cada chamada esgota o timeout completo na tentativa IPv6 antes de recuar,
duplicando a latência sempre que o motor está lento ou em baixo (achado
STG-PRE-006, confirmado: `duration_ms` caiu de ~2000ms para ~40ms após a
correcção).

---

## 8. Smoke API

```powershell
# Login (obtém tokens JWT)
curl -X POST http://127.0.0.1:8100/api/v1/auth/token/ `
  -H "Content-Type: application/json" `
  -d '{"email": "<utilizador>", "password": "<password>"}'

# Perfil autenticado
curl http://127.0.0.1:8100/api/v1/auth/me/ -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### 8.1 Smoke operacional dedicado (zero-setup, sem tocar na BD)

```powershell
cd backend_core
venv\Scripts\activate

# Backend Core -> Intelligence Engine (chamada síncrona real)
python manage.py smoke_intelligence_engine

# Backend Core -> Content Renderer (health + submissão de 1 job real)
python manage.py smoke_content_renderer
python manage.py smoke_content_renderer --health-only   # só GET /health, sem disparar render
python manage.py smoke_content_renderer --job-type report_generation
```

Estes dois comandos nunca imprimem o token (só `configured`/`not_configured`)
e não escrevem nada na base de dados do Backend Core — são o primeiro passo
de diagnóstico antes de qualquer smoke via browser. Ver também
`backend_core/docs/fundamentos/03_observabilidade_staging_ecossistema/smoke_content_renderer.md`
para o checklist completo do Content Renderer.

---

## 9. Smoke browser

1. Arrancar os quatro serviços pela ordem da §5.
2. Confirmar os healthchecks da §7.
3. Preparar um utilizador de staging com workspace/artist/campaign (via
   `python manage.py seed_e2e_run --run-id=<qualquer-coisa>` com
   `E2E_PASSWORD` exportado — ver §10 — ou dados de staging já existentes).
4. No browser: login → abrir a campanha → **Open War Room** → confirmar que
   aparecem recomendações (ou o estado honesto "Not enough data yet"/erro, se
   a Intelligence estiver indisponível) → criar uma acção a partir de uma
   recomendação → confirmar que aparece em **Campaign Actions** → recarregar
   a página e confirmar que persiste.
5. Confirmar na aba de Network do browser que **só** aparecem pedidos para o
   host do Backend Core (`:8100`) e para os assets do próprio frontend
   (`:5200`/`:5201`) — nunca `:8201` nem `:8202`.

---

## 10. E2E automatizado (Prompt 09)

```powershell
cd frontend
npx playwright install chromium          # uma vez por máquina
$env:E2E_PASSWORD = "<password-efemera-so-para-este-run>"
pnpm test:e2e
```

Pré-condições (documentadas em
`resultados_execucao/prompt_09_e2e_automatizado_resultado.md`):

- Backend Core, Intelligence Engine e Content Renderer têm de estar
  **genuinamente a correr** — o harness não os arranca.
- A Intelligence Engine tem de estar **acessível e fora de dry-run**
  (`INTELLIGENCE_ENGINE_DRY_RUN=false`) — em dry-run, `recommendations` vem
  sempre vazio e o cenário não consegue criar nenhuma CampaignAction (não há
  affordance de criação independente de uma recomendação na UI).
- `E2E_PASSWORD` tem de estar exportado no ambiente que corre o Playwright —
  o comando `seed_e2e_run` recusa-se a arrancar sem ele (`CommandError`).

Cada corrida usa um `run-id` novo (namespace isolado, sem limpeza manual
necessária); ver §12 para limpar os dados de execuções antigas.

---

## 11. Troubleshooting

### 11.1 Base de dados

| Sintoma | Diagnóstico | Acção |
|---|---|---|
| `django.db.utils.OperationalError` no arranque | BD não alcançável ou credenciais erradas | Confirmar `DB_HOST`/`DB_PORT` alcançáveis (`telnet`/`Test-NetConnection`); confirmar `DB_USER`/`DB_PASSWORD` |
| `ImportError: no pq wrapper available` (Windows) | `psycopg` puro sem `libpq` de sistema | Instalar `psycopg[binary]` na venv local (achado STG-PRE-002); não alterar `requirements.txt` a menos que o alvo de produção também precise |
| Migrations pendentes (`python manage.py showmigrations` mostra `[ ]`) | BD desactualizada face ao código | `python manage.py migrate`; nunca editar uma migration já aplicada em staging |
| `/api/v1/system/health/ready/` devolve 503 | BD inacessível neste momento | Ver logs do Backend Core; confirmar a BD está de pé antes de reiniciar o processo |

### 11.2 Intelligence Engine

| Sintoma | Diagnóstico | Acção |
|---|---|---|
| Chamada síncrona devolve 503 ao utilizador | IE inacessível, timeout ou 5xx | `curl http://<host-ie>:8201/health`; `python manage.py smoke_intelligence_engine` |
| Chamada devolve 502 | IE respondeu 4xx (ex.: token errado) ou corpo inusável | Confirmar `INTERNAL_API_TOKEN` idêntico entre Backend Core e IE |
| Latência alta mesmo com IE de pé | `INTELLIGENCE_ENGINE_BASE_URL` usa `localhost` em vez de `127.0.0.1` (Windows) | Corrigir para `127.0.0.1` — ver §7.2 |
| Recomendações sempre vazias | `INTELLIGENCE_ENGINE_DRY_RUN=true` | Confirmar a variável; dry-run devolve sempre `recommendations: []` por desenho |
| IE recusa arrancar | `INTERNAL_API_TOKEN` vazio com `APP_ENV=production` | Definir o token (guarda de arranque, não contornar) |

### 11.3 Content Renderer

| Sintoma | Diagnóstico | Acção |
|---|---|---|
| Job fica `queued`/`draft` para sempre, job diz `failed` | Renderer inacessível na submissão (nunca recebeu o job) | Desde o Prompt 07, o artefacto já reflecte a falha automaticamente (`Report`→`failed`, `MediaKit`→metadata, `ContentPackRequest`→`failed`+créditos libertados); confirmar `CONTENT_RENDERER_BASE_URL`/`REPORT_RENDERER_BASE_URL` e `curl http://<host-renderer>:8202/health` |
| Renderer recusa arrancar | Token vazio sem `ALLOW_INSECURE_EMPTY_TOKEN=true` | **Não activar essa flag em staging** — definir `INTERNAL_API_TOKEN` correctamente |
| `smoke_content_renderer` reporta 403 na submissão | Token não coincide com o Backend Core | Alinhar `INTERNAL_API_TOKEN` nos dois serviços |

### 11.4 Callbacks

| Sintoma | Diagnóstico | Acção |
|---|---|---|
| Callback do Renderer devolve 403 no Backend Core | `IsInternalService` rejeitou — token errado/ausente no `X-Internal-Token` do callback | Confirmar `INTERNAL_API_TOKEN` idêntico; nunca "resolver" isto ocultando `IsInternalService` |
| Callback nunca chega | Renderer não alcança `BACKEND_CORE_BASE_URL`, ou `INTERNAL_CALLBACK_PATH` errado | Confirmar rede/URL; o Renderer só faz retry em falhas transitórias (nunca em 4xx) |
| `job failed`, artefacto sem explicação visível | Ver Prompt 07 — `related_artifact_status` no `CampaignActionSerializer` e mensagens em `CampaignReportsPanel`/`CampaignMediaKitsPanel` já expõem `metadata.error` | Confirmar que a UI está actualizada (Prompt 07/08 aplicados) |

### 11.5 Storage / asset sem `public_url`

| Sintoma | Diagnóstico | Acção |
|---|---|---|
| `Asset.public_url` vazio após um job `completed` | O Content Renderer não enviou `asset.public_url` no callback | Confirmar `LOCAL_STORAGE_PUBLIC_BASE_URL` configurado (provider `local`); se um provider real estiver em uso, confirmar que a implementação preenche o campo |
| Ficheiro inacessível pelo `public_url` | `LOCAL_STORAGE_ROOT` não persistente entre reinícios, ou storage local apagado | Usar um caminho persistente para `LOCAL_STORAGE_ROOT`; object storage real remove esta limitação (ainda pendente — ver arquitectura §11) |

### 11.6 Auth / RBAC

| Sintoma | Diagnóstico | Acção |
|---|---|---|
| 401 em qualquer pedido autenticado | Sessão expirada ou token de acesso inválido | Reautenticar (`/auth/token/`); o frontend já trata isto como "Session expired" honesto |
| 403 ao criar/editar recursos | Utilizador sem a permissão RBAC exigida pela view (`HasWorkspacePermission`) | Confirmar `role_key` do `WorkspaceMember`; **não** contornar no frontend — o backend é sempre a autoridade (STG-PRE-008) |
| 404 num recurso doutro workspace | Comportamento correcto e intencional — 404 genérico em vez de 403, para não revelar existência cross-workspace | Não é um bug; não "corrigir" para 403 |
| `X-Workspace-ID` em falta | View exige o header | Confirmar que o cliente envia o header em todos os pedidos workspace-scoped |

### 11.7 CORS

| Sintoma | Diagnóstico | Acção |
|---|---|---|
| Browser bloqueia pedidos ao Backend Core (erro de CORS na consola) | Origem do frontend não está em `CORS_ALLOWED_ORIGINS` | Adicionar a origem exacta (protocolo+host+porta) do frontend de staging a `CORS_ALLOWED_ORIGINS` no `.env` do Backend Core e reiniciar |
| Pedido funciona via `curl` mas falha no browser | Confirma que é CORS, não rede | Ver cabeçalho `Access-Control-Allow-Origin` na resposta; nunca usar `*` em staging com credenciais |

### 11.8 DB migration

| Sintoma | Diagnóstico | Acção |
|---|---|---|
| `django.db.utils.ProgrammingError: relation does not exist` | Migrations não aplicadas neste ambiente | `python manage.py migrate` antes de qualquer outro passo |
| Migration falha a meio | Alteração incompatível com dados existentes | Nunca forçar em staging com dados reais sem um plano de rollback/backup — ver arquitectura §5 (topologia de staging persistente ainda pendente) |

---

## 12. Limpeza de dados dev/staging

- **Dados de smoke/E2E são sempre namespaced** (prefixo `e2e-<run-id>`,
  `E2E Workspace <run-id>`, ou o padrão adoptado pelo CA-014/`STG09 smoke`
  usado nas fases anteriores) — nunca partilham workspace com dados reais.
- Para remover um namespace de teste específico (via Django shell, nunca em
  produção):

```python
from django.contrib.auth import get_user_model
from apps.workspaces.models import Workspace

User = get_user_model()
user = User.objects.filter(email="e2e-<run-id>@example.local").first()
if user:
    Workspace.objects.filter(created_by=user).delete()  # cascata remove artefactos/campanhas
    user.delete()
```

- **Nunca** correr `flush`/`migrate zero` num ambiente com dados reais de
  staging sem um backup confirmado — este runbook não cobre produção e não
  assume que staging pré-produção seja descartável por omissão.
- Storage local (`LOCAL_STORAGE_ROOT`) acumula ficheiros de teste — limpar
  periodicamente o directório em staging técnico; não relevante quando um
  object storage real com política de retenção estiver em uso.

---

## 13. Paragem segura

```text
1. Frontend            (parar primeiro — deixa de aceitar novas interacções)
2. Content Renderer    (deixa jobs em curso terminarem ou falharem via timeout próprio antes de parar, se possível)
3. Intelligence Engine (stateless — seguro parar a qualquer momento)
4. Backend Core        (último — garante que callbacks pendentes ainda são aceites o máximo de tempo possível)
5. Base de dados       (só parar depois do Backend Core; nunca parar a BD com o Backend Core ainda a correr)
```

Nenhum destes serviços precisa de um sinal especial de "drain" — todos são
seguros de terminar com `Ctrl+C`/`SIGTERM`. Um job de renderer interrompido a
meio fica no pior caso `submitted`/`running` sem callback — visível no
healthcheck agregado e no estado do artefacto; não há corrupção de dados.

---

## 14. Checklist de validação rápida

- [ ] `scripts/check-forbidden-ports.ps1` sem violações.
- [ ] `python manage.py check` — 0 problemas.
- [ ] `python manage.py migrate` — sem pendências (`showmigrations` limpo).
- [ ] `GET /api/v1/system/health/live/` → 200.
- [ ] `GET /api/v1/system/health/ready/` → 200.
- [ ] `GET /api/v1/system/health/dependencies/` (staff) → `ok` em DB, IE, Content/Report Renderer.
- [ ] `python manage.py smoke_intelligence_engine` → sucesso.
- [ ] `python manage.py smoke_content_renderer` → 202 aceite.
- [ ] Smoke browser (login → War Room → criar acção → reload) — secção 9.
- [ ] `pnpm test:e2e` verde (se o ambiente permitir IE real — secção 10).
- [ ] Grep de secrets no runbook e nos `.env.example` — 0 valores reais.
- [ ] Nenhum `ALLOW_INSECURE_EMPTY_TOKEN=true` em nenhum `.env` deste ambiente.

---

## 15. Matriz de sintomas (referência rápida)

| Sintoma | Causa mais provável | Secção |
|---|---|---|
| IE down | `INTELLIGENCE_ENGINE_BASE_URL` inacessível; processo parado | §11.2 |
| Renderer down | `CONTENT_RENDERER_BASE_URL`/`REPORT_RENDERER_BASE_URL` inacessível; processo parado | §11.3 |
| Callback 403 | `INTERNAL_API_TOKEN` não coincide entre Renderer e Backend Core | §11.4 |
| Job failed | Renderer inacessível na submissão ou callback reportou falha; artefacto já reflecte isto (Prompt 07) | §11.3, §11.4 |
| Asset sem `public_url` | Renderer não enviou o campo no callback, ou storage local não persistente | §11.5 |
| 403 no frontend | RBAC do utilizador não tem a permissão exigida — comportamento correcto, backend é autoridade | §11.6 |
| CORS | Origem do frontend ausente de `CORS_ALLOWED_ORIGINS` | §11.7 |
| DB migration | Migrations pendentes ou incompatíveis | §11.8, §11.1 |

---

## 16. Critérios de pronto / não pronto

**Pronto para piloto técnico staging** (nível já alcançado, fase 04):
todos os itens da checklist §14 relativos a health/smoke passam, com os
quatro serviços em `localhost`, SQLite e storage local.

**Pronto para staging pré-produção formal** — só quando, além da checklist
§14:
- [ ] BD alvo é PostgreSQL **persistente** (não um container descartável) — ainda pendente (arquitectura §11).
- [ ] Object storage real substitui `STORAGE_PROVIDER=local` — nenhum provider escolhido ainda (arquitectura §11).
- [ ] Secrets vêm de um mecanismo controlado (secret store ou variáveis de CI/deploy), não de um `.env` copiado manualmente — ainda pendente, sem CI/CD neste repositório.
- [ ] Esquema de hosts definido (máquina única com portas distintas vs. hosts separados) — ainda pendente.
- [ ] `pnpm test:e2e` corre como gate automático (CI) — ainda não existe CI.

**Nunca declarar produção** a partir deste runbook — produção exige SLA,
alta disponibilidade, alertas e rotação automática de secrets, nenhum dos
quais este documento cobre ou pretende cobrir.

---

## 17. Referências

- `arquitectura_staging_pre_producao.md` — arquitectura alvo completa (níveis de ambiente, componentes, fluxos, decisões pendentes).
- `docs/configuracao/portas_projeto.md` — mapa oficial de portas.
- `resultados_execucao/prompt_02_db_staging_resultado.md` — validação técnica PostgreSQL.
- `resultados_execucao/prompt_03_object_storage_resultado.md` — `Asset.public_url` e interface `StorageProvider`.
- `resultados_execucao/prompt_04_gestao_segredos_resultado.md` — inventário e rotação de secrets.
- `resultados_execucao/prompt_05_correlation_id_resultado.md` — correlation-id ponta-a-ponta.
- `resultados_execucao/prompt_06_health_logs_resultado.md` — health agregado, liveness/readiness.
- `resultados_execucao/prompt_07_estados_operacionais_resultado.md` — estados de artefacto/job, `related_artifact_status`.
- `resultados_execucao/prompt_08_rbac_ux_resultado.md` — contrato RBAC, UX de erro honesta.
- `resultados_execucao/prompt_09_e2e_automatizado_resultado.md` — E2E Playwright, `seed_e2e_run`.
- `backend_core/docs/fundamentos/03_observabilidade_staging_ecossistema/smoke_content_renderer.md` — checklist detalhado do Content Renderer.
