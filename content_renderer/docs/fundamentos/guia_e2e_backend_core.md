# Guia de Teste E2E — Content Renderer ↔ Backend Core (Django)

Este guia descreve como validar o ciclo completo **job externo → render → callback
→ Asset/Output/Report/MediaKit** entre o `content_renderer` (Node, porta 8202) e o
`backend_core` (Django, porta 8100).

> **Regra:** o renderer apenas gera activos e reporta o resultado técnico. O Django
> governa o produto (entidades, estado, billing, Asset). Não se altera o
> `backend_core` para este teste.

---

## 1. Pré-requisitos

- `content_renderer` compilado: `npm run build` (gera `dist/`).
- `backend_core` com o seu `venv` e migrations aplicadas (`python manage.py migrate`)
  e seeds (`seed_rbac`, `seed_billing`, `seed_content`).
- **O mesmo `INTERNAL_API_TOKEN` nos dois serviços.**

---

## 2. Configuração (variáveis de ambiente)

**Renderer (`content_renderer`):**

```text
PORT=8202
NODE_ENV=development
INTERNAL_API_TOKEN=<token-partilhado>
BACKEND_CORE_BASE_URL=http://localhost:8100
LOCAL_STORAGE_ROOT=<pasta-local>
```

**Backend Core (`backend_core`):**

```text
INTERNAL_API_TOKEN=<token-partilhado>          # igual ao renderer
BACKEND_PUBLIC_BASE_URL=http://localhost:8100
CONTENT_RENDERER_BASE_URL=http://localhost:8202
REPORT_RENDERER_BASE_URL=http://localhost:8202 # report e media kit também no renderer único
INTERNAL_CALLBACK_PATH=/api/v1/internal/jobs/callback/
EXTERNAL_JOBS_ENABLED=true
EXTERNAL_JOBS_DRY_RUN=false
```

> O Backend mapeia `report_generation`/`media_kit_generation` para o provider
> `report_renderer`; como o renderer único serve os três tipos, aponta-se
> `REPORT_RENDERER_BASE_URL` para `http://localhost:8202`.

---

## 3. Contratos confirmados (após inspecção do `backend_core`)

| Item | Valor |
|---|---|
| Endpoint de submissão no renderer | `POST /jobs/` |
| Endpoint de callback no Django | `POST /api/v1/internal/jobs/callback/` |
| Headers (Django → renderer) | `X-Internal-Token`, `X-Workspace-ID`, `X-Job-ID`, `X-Request-ID`, `Content-Type` |
| Envelope | `job_id`, `workspace_id`, `request_id`, `job_type`, `callback_url`, `entity{type,id}`, `payload_version`, `payload` |
| Callback content | `result.outputs[]` (cada output com `asset`) |
| Callback report/media-kit | **`result.asset`** (bloco único) + `result.metadata` |
| `asset.storage_provider` | `"local"` é válido (`Asset.StorageProvider.LOCAL`) |

Estes contratos são exercitados pelos testes de integração do `backend_core`
(`apps/integrations_bridge`, `apps/content`, `apps/reports`; **134 passed** na
validação mais recente — R-HARD-003) com um renderer simulado, e pelos **136
testes** do renderer (`npm test`, R-HARD-001..007).

---

## 4. Método automatizado (script)

```powershell
# A partir de content_renderer/ (com dist/ compilado):
powershell -ExecutionPolicy Bypass -File scripts\run-e2e.ps1
```

O `run-e2e.ps1`:

1. arranca o renderer (`node dist/server.js`, :8202) e o Django (`runserver`, :8100)
   com o mesmo token e as URLs acima;
2. espera ambos ficarem `up` (`/health` e `/api/v1/schema/`);
3. corre `scripts/e2e_backend_core.py` (venv do backend), que para report e media
   kit: cria a entidade, gera o `ExternalJobReference` (envelope real) e **POSTa o
   envelope ao renderer real**; o renderer renderiza um PDF real e tenta o callback;
4. imprime o resultado e desliga os serviços.

**Resultado observado (evidência):** o renderer aceita os payloads reais do Django
e **renderiza com sucesso** (`renderer_result_status: "completed"`, `render_error:
null`, PDF real). Ver caveats em §6 sobre o passo de escrita no Django.

---

## 5. Método manual (fluxo de produto via API) — checklist

Este é o fluxo **de produção** (o próprio servidor Django cria o job e recebe o
callback no mesmo processo). Com os dois serviços a correr:

### 5.1 content_generation
1. Autenticar: `POST /api/v1/auth/token/` `{email,password}` → `access`.
2. Garantir workspace activo (header `X-Workspace-ID`), artista, track, campanha.
3. `POST /api/v1/content-pack-requests/` (JWT + `X-Workspace-ID`, RBAC
   `content:generate`) com um `content_pack` semeado.
4. Verificar: `ExternalJobReference` criado (`content_generation`, `submitted`).
5. Verificar no renderer: job recebido, PNG(s) gerado(s) em
   `LOCAL_STORAGE_ROOT/workspaces/<ws>/jobs/<job>/`.
6. Verificar callback `completed` → `ContentPackRequest` completed, `ContentOutput`(s)
   e `Asset`(s) criados; `Notification content_ready`; `AuditEvent content_pack.completed`.

   > Nota: o Django resolve o `Template` de cada output por `template_key`/`template_id`
   > ou, em fallback, por `output_type` ligado ao `content_pack` (pack_templates).

### 5.2 report_generation
1. `POST /api/v1/reports/` `{report_type,title}` (JWT + `X-Workspace-ID`).
2. Verificar `ExternalJobReference` (`report_generation`, `submitted`).
3. Renderer gera **PDF** (ou HTML fallback) em storage local.
4. Callback `completed` (com `result.asset`) → `Asset` (`report_pdf`),
   `Report.storage_asset` ligado, `Report` `completed`, `Notification report_ready`,
   `AuditEvent report.completed`.

### 5.3 media_kit_generation
1. `POST /api/v1/media-kits/` `{artist,title}` (JWT + `X-Workspace-ID`).
2. Verificar `ExternalJobReference` (`media_kit_generation`, `submitted`).
3. Renderer gera ficheiro (PDF/HTML).
4. Callback `completed` (com `result.asset`) → `Asset` (`media_kit_asset`),
   `MediaKit.storage_asset` ligado, `MediaKit` `generated`, `Notification
   media_kit_ready`, `AuditEvent media_kit.completed`.

### Verificação (Django shell)
```python
from apps.reports.models import Report
r = Report.objects.latest("created_at")
print(r.status, r.storage_asset_id, r.storage_asset.file_name, r.storage_asset.mime_type)
```

---

## 6. Caveats de ambiente (descobertos no teste)

Estes pontos são **limitações do ambiente/harness local**, não do contrato nem do
renderer:

1. **SQLite + processos separados:** semear o job num processo separado e fazer o
   callback chegar a um servidor Django já a correr falha (`404` no lookup do job),
   porque um servidor SQLite em execução não vê linhas commitadas por outro
   processo iniciado depois. **Em produção não ocorre:** o próprio servidor cria o
   job e recebe o callback no mesmo processo (fluxo §5). Recomendação para E2E
   robusto: **PostgreSQL** (`DB_ENGINE=postgres`).
2. **Callback síncrono vs submit do Django:** o renderer envia o callback *antes* de
   responder 202. No fluxo real do Django (submit síncrono) isto pode sobrepor o
   estado do `ExternalJobReference` (o produto — Asset/Report — fica correcto). A
   recomendação do backlog (CR-203) é **callback em background leve** (responder 202
   primeiro, callback depois) — melhoria recomendada para produção.
3. **Renderer único para os 3 tipos:** apontar `REPORT_RENDERER_BASE_URL` para :8202.

---

## 7. Correcções de contrato aplicadas ao renderer (necessárias para integrar)

- **`result.asset` para report/media-kit:** o handler do Django lê `result.asset`
  (não `result.outputs[]`). O renderer passou a enviar `{ asset, metadata }` nesses
  callbacks. (`callbacks/callback.payload.ts`)
- **Tolerância a `null`:** o Django envia `null` para blocos ausentes
  (`campaign`/`artist`/`track`/`period_*`) e `smart_link_stats` como **array**; os
  schemas de report/media-kit passaram a `.nullish()` e aceitam array-ou-objecto.
  (`renderers/reports/report.model.ts`, `renderers/media-kits/media-kit.model.ts`)

---

## 8. Harness E2E com PostgreSQL (R-HARD-002) — recomendado

O caveat 6.1 (SQLite multi-processo → `404` no callback) resolve-se usando
**PostgreSQL**, que partilha linhas commitadas entre processos. O `backend_core`
já suporta Postgres nativamente (`DB_ENGINE=postgres` + `DB_*`; `psycopg` 3 já
instalado) — **não é preciso alterar o backend_core**.

### 8.1 Pré-requisitos

- **Docker Desktop em execução** (engine ligado), com `docker compose`.
- `content_renderer` compilado: `npm run build` (gera `dist/`).
- `backend_core` com o seu `venv` (migrations/seeds são aplicadas pelo harness).
- Mesmo `INTERNAL_API_TOKEN` nos dois serviços (o harness trata disto).

### 8.2 Variáveis (dev only — **não** são secrets)

Definidas em [`docker-compose.e2e.yml`](../../docker-compose.e2e.yml) e
[`.env.e2e.example`](../../.env.e2e.example); sobreponíveis por ambiente:

| Variável | Default | Notas |
|---|---|---|
| `DB_ENGINE` | `postgres` | activa o ramo Postgres no `settings.py`. |
| `DB_NAME` | `chartrex_e2e` | base efémera (tmpfs). |
| `DB_USER` | `chartrex_e2e` | utilizador de desenvolvimento. |
| `DB_PASSWORD` | `chartrex_e2e_dev_only` | **password de dev**, não é secret. |
| `DB_HOST` / `DB_PORT` | `localhost` / `55432` | `55432` evita conflito com um Postgres local. |
| `INTERNAL_API_TOKEN` | efémero gerado | partilhado renderer ↔ Django. |

### 8.3 Comandos

```powershell
# A partir de content_renderer/ (com dist/ compilado e Docker a correr):
powershell -ExecutionPolicy Bypass -File scripts\run-e2e-postgres.ps1

# Deixar serviços + Postgres a correr para inspecção manual:
powershell -ExecutionPolicy Bypass -File scripts\run-e2e-postgres.ps1 -KeepUp
```

O `run-e2e-postgres.ps1`: sobe Postgres (compose), espera `healthy`, aplica
`migrate` + seeds (`seed_rbac`, `seed_billing`, `seed_content`), arranca renderer
(:8002) e Django (:8000) com o mesmo token e `DB_*`, faz readiness checks, corre
`scripts/e2e_backend_core.py` e recolhe evidências, e por fim faz _teardown_.

> O driver `e2e_backend_core.py` faz **polling** do estado da entidade após o
> `POST /jobs` (o callback é agora em **background** — R-HARD-001 — e chega depois
> do 202).

### 8.4 Evidências esperadas

- `postgres_healthy=True`, `renderer_up=True`, `django_up=True`.
- `e2e-logs/<timestamp>/e2e_results.json` com, por cenário,
  `renderer_result_status: "completed"`, `render_error: null`, `*_status` final
  (`completed`/`generated`) e `asset` com `storage_provider/storage_key/checksum`.
- Logs `migrate.log`, `seed_*.log`, `renderer.out`, `django.out` na pasta de
  evidências (git-ignorada).

### 8.5 Limpeza

- Sem `-KeepUp`: o harness pára os processos e faz `docker compose -f
  docker-compose.e2e.yml down -v` (a base é tmpfs → desaparece; **não** há dados
  reais). A pasta `e2e-logs/` é mantida para inspecção (git-ignorada).
- Manual: `docker compose -f docker-compose.e2e.yml down -v`.

### 8.6 Troubleshooting

| Sintoma | Causa / acção |
|---|---|
| `unable to get image ... dockerDesktopLinuxEngine ... cannot find the file` | **Docker Desktop não está a correr.** Inicia o Docker Desktop e repete. |
| `postgres_healthy=False` | Container não ficou `healthy` em 60s; ver `docker logs chartrex_e2e_postgres`. Porta 55432 ocupada? Ajusta `DB_PORT`. |
| `manage.py migrate failed` | `venv` do backend incompleto ou `DB_*` errado; confirma `psycopg` instalado e o Postgres acessível em `localhost:55432`. |
| `renderer_up=False` | `dist/` não compilado (`npm run build`) ou porta 8002 ocupada. |
| `django_up=False` | porta 8000 ocupada ou erro no arranque; ver `e2e-logs/.../django.err`. |
| callback `404` | Em Postgres não deve ocorrer; se ocorrer, confirma que renderer e Django usam o **mesmo** `DB_*` e token, **e que não há outro servidor a ocupar a porta 8000** (ver §10). |

---

## 9. Harness sem Docker (cluster PostgreSQL local) — R-HARD-003

Quando o engine do Docker não está disponível mas existe o PostgreSQL instalado
(binários `initdb`/`pg_ctl`/`psql`), pode criar-se um **cluster descartável**:

```powershell
$bin = "C:\Program Files\PostgreSQL\18\bin"
$pgdata = Join-Path $env:TEMP "cr-e2e-pg"
& "$bin\initdb.exe" -D $pgdata -U postgres --auth-host=trust --auth-local=trust
& "$bin\pg_ctl.exe" -D $pgdata -o "-p 55432" -l "$env:TEMP\pg.log" start
# --auth=trust acima ⇒ a password não é verificada; PGPASSWORD é apenas um
# valor local não-secreto exigido pelo cliente psql, sem efeito de autenticação real.
$env:PGPASSWORD='trust-mode-unused'; & "$bin\psql.exe" -h localhost -p 55432 -U postgres -d postgres -c "create database chartrex_e2e;"
# psycopg precisa do libpq do PostgreSQL no PATH:
$env:PATH = "$bin;$env:PATH"
# Correr o harness contra o cluster (Django em porta livre p/ evitar conflitos):
pwsh -File scripts\run-e2e-localpg.ps1 -DjangoPort 8010
# Teardown:
& "$bin\pg_ctl.exe" -D $pgdata -m fast stop ; Remove-Item $pgdata -Recurse -Force
```

`scripts/run-e2e-localpg.ps1` migra + seed (idempotente), arranca renderer
(:8002) e Django (:`DjangoPort`) e corre o driver. O driver
(`e2e_backend_core.py`) cobre: **content** (completed + idempotência), **report**
(completed + failed) e **media kit** (completed + failed).

---

## 10. Resultado da validação (R-HARD-003) — 2026-06-23

Loop **Django → Renderer → Django** validado com **PostgreSQL** (cluster local,
porta 55432; Django em 8010; renderer em 8002). Evidência (`e2e_results.json`):

| Cenário | HTTP | Estado Django | Asset | `ok` |
|---|---|---|---|---|
| content_generation **completed** | 202 | `ContentPackRequest=completed`, job `completed`, **3 ContentOutput** | **3 Asset** (PNG, checksum) | ✅ |
| content_generation **idempotência** (re-entrega) | 202 | sem novas linhas | mesmos 3 asset ids | ✅ |
| report_generation **completed** | 202 | `Report=completed`, job `completed` | `report.pdf` ligado | ✅ |
| report_generation **failed** (payload inválido) | 202 | `Report=failed`, job `failed` | nenhum | ✅ |
| media_kit_generation **completed** | 202 | `MediaKit=generated`, job `completed` | `media_kit.pdf` ligado | ✅ |
| media_kit_generation **failed** (payload inválido) | 202 | `MediaKit=draft` (consistente), job `failed` | nenhum | ✅ |

`content_generation` **partially_completed/failed** não é reproduzível pelo loop
real via payload (o renderer é resiliente: template/formato desconhecidos caem em
fallback, logo um job de content produz sempre um output `completed`). O
tratamento desses estados no Django está coberto pelo `pytest`
(`apps/content/tests/test_content_callback.py`: `TestPartiallyCompleted`,
`TestFailed`, `TestIdempotency`) e a emissão pelo renderer pelos testes Vitest.

> **Lição (gotcha):** um servidor Django **antigo** deixado a correr na porta
> 8000 (com SQLite) interceptou os callbacks e devolveu `404` (job inexistente
> nessa BD). Correr o Django do harness numa **porta livre** (`-DjangoPort 8010`)
> e/ou garantir que a 8000 está livre resolve. O `404` do callback não era do
> contrato — era a porta errada.
