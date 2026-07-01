# Runbook — Arranque local/staging do ecossistema MomentFlow/ChartRex

> Guia prático e executável para arrancar, validar e parar os três serviços
> (`backend_core`, `intelligence_engine`, `content_renderer`) em **local** ou em
> **staging técnico** (OBS-STG-007).
>
> Fonte: [`01_backlog.md`](01_backlog.md) §8/§9 e
> [`matriz_operacional_servicos.md`](matriz_operacional_servicos.md) (referência
> completa de portas/variáveis/dependências — este runbook não a repete, só a
> operacionaliza). Comandos em **PowerShell** (Windows). Caminhos relativos à raiz
> do repositório.
>
> **Nenhum valor real de secret aparece neste documento** — apenas placeholders
> (`<DEV_TOKEN>`, `<INTERNAL_API_TOKEN>`, …) ou valores de dev explicitamente
> descartáveis.

---

## 1. Pré-requisitos

| Requisito | Versão / nota |
|---|---|
| Python | 3.13 (backend_core, intelligence_engine) |
| Node.js | ≥ 18.18 (content_renderer) |
| PostgreSQL | 16 (**só** necessário para o loop completo Renderer→callback multi-processo — ver §7 e §4.3); via Docker (`docker compose`) ou instalação local |
| Docker | Opcional — só se usares o harness E2E via `docker-compose.e2e.yml` |
| PowerShell | 7+ recomendado (`pwsh`); os comandos abaixo também funcionam em Windows PowerShell 5.1 |
| `curl` | Disponível por default no Windows 10/11; usado para validar healthchecks |

**Antes de arrancar qualquer serviço:** decide um `<INTERNAL_API_TOKEN>` de dev
(qualquer string não-vazia, ex.: `dev-local-token-only`) e usa **o mesmo valor
nos três serviços**. Sem isto, todas as chamadas internas dão `403`.

---

## 2. Directórios e portas (referência rápida)

| Serviço | Directório | Porta default | Healthcheck |
|---|---|---|---|
| `backend_core` | `backend_core/` | **8100** | `GET /api/v1/system/health/dependencies/` (staff-only, agregado) |
| `intelligence_engine` | `intelligence_engine/` | **8201** | `GET /health` (público) |
| `content_renderer` | `content_renderer/` | **8202** | `GET /health` (público) |
| PostgreSQL (loop completo) | `content_renderer/docker-compose.e2e.yml` | **55432→5432** | `pg_isready` |

> ℹ️ **Renderer único (G9, resolvido):** o `content_renderer` serve
> `content_generation`, `report_generation` e `media_kit_generation` na mesma
> porta **8202**. Tanto `CONTENT_RENDERER_BASE_URL` como `REPORT_RENDERER_BASE_URL`
> apontam para `:8202` — os defaults no `config/settings.py` já reflectem isto.
> **Como validar:** `curl http://localhost:8202/health` responde.

---

## 3. Variáveis de ambiente mínimas

Detalhe completo (tipos, defaults, secrets) em
[`matriz_operacional_servicos.md`](matriz_operacional_servicos.md) §2–§5. Aqui só
o necessário para arrancar em modo local com o loop real activo.

### 3.1 `backend_core/.env`

```dotenv
SECRET_KEY=<SECRET_KEY>
INTERNAL_API_TOKEN=<DEV_TOKEN>
DEBUG=True

INTELLIGENCE_ENGINE_BASE_URL=http://127.0.0.1:8201
INTELLIGENCE_ENGINE_ENABLED=True
INTELLIGENCE_ENGINE_DRY_RUN=False

CONTENT_RENDERER_BASE_URL=http://localhost:8202
REPORT_RENDERER_BASE_URL=http://localhost:8202
BACKEND_PUBLIC_BASE_URL=http://localhost:8100
EXTERNAL_JOBS_ENABLED=True
EXTERNAL_JOBS_DRY_RUN=False

HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS=2.0
```

### 3.2 `intelligence_engine/.env`

```dotenv
APP_ENV=development
INTERNAL_API_TOKEN=<DEV_TOKEN>
```

### 3.3 `content_renderer/.env`

```dotenv
PORT=8202
NODE_ENV=development
INTERNAL_API_TOKEN=<DEV_TOKEN>
BACKEND_CORE_BASE_URL=http://localhost:8100
```

> `<DEV_TOKEN>` tem de ser **literalmente o mesmo valor** nos três ficheiros.

---

## 4. Ordem de arranque recomendada

```text
1. (opcional) PostgreSQL — só se quiseres o loop completo do renderer
2. backend_core (migrate + seeds + runserver)         :8100
3. intelligence_engine (uvicorn)                       :8201
4. content_renderer (npm run dev / build+start)        :8202
5. Validar os três healthchecks
6. Correr os smoke tests
```

Cada serviço corre num terminal/processo próprio — usa **4 terminais
separados** (DB opcional + 3 serviços).

### 4.1 Arrancar `backend_core`

```powershell
cd backend_core
python -m venv venv          # só na 1.ª vez
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env  # depois edita .env conforme §3.1
python manage.py migrate
python manage.py seed_rbac
python manage.py seed_billing
python manage.py seed_content
# opcional: utilizador staff para o healthcheck agregado
python manage.py createsuperuser
python manage.py runserver
```

Fica disponível em `http://127.0.0.1:8100/`.

### 4.2 Arrancar `intelligence_engine`

```powershell
cd intelligence_engine
python -m venv venv          # só na 1.ª vez
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env  # depois edita .env conforme §3.2
$env:INTERNAL_API_TOKEN="<DEV_TOKEN>"; $env:APP_ENV="development"
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8201
```

> Em staging, remove `--reload` e confirma o `--host` adequado ao ambiente
> (**confirmar no ambiente**: validar com `curl http://<host>:8201/health`).

### 4.3 Arrancar `content_renderer`

```powershell
cd content_renderer
npm install                  # só na 1.ª vez
Copy-Item .env.example .env  # depois edita .env conforme §3.3
$env:INTERNAL_API_TOKEN="<DEV_TOKEN>"; $env:PORT="8202"; $env:NODE_ENV="development"
npm run dev
# alternativa (build de produção):
# npm run build; npm start
```

Fica disponível em `http://localhost:8202/`.

> **Loop completo com callback** (Renderer → Backend Core) exige que o
> `backend_core` use **PostgreSQL**, não SQLite — o callback corre noutro
> processo e o SQLite não vê linhas committed por outro processo (dá `404` no
> callback). Para isso, sobe o PostgreSQL efémero do harness antes do passo 4.1:
>
> ```powershell
> cd content_renderer
> docker compose -f docker-compose.e2e.yml up -d
> docker inspect --format '{{.State.Health.Status}}' chartrex_e2e_postgres   # esperar "healthy"
> ```
>
> e configura `backend_core/.env` com `DB_ENGINE=postgres` + `DB_HOST`/`DB_PORT`/
> `DB_NAME`/`DB_USER`/`DB_PASSWORD` apontando para esse PostgreSQL (porta host
> **55432**). Para arranque local simples (sem validar o callback ponta-a-ponta),
> SQLite (default) é suficiente.

---

## 5. Validar `GET /health` de cada serviço

```powershell
curl http://127.0.0.1:8201/health      # intelligence_engine — esperar {"status":"ok",...}
curl http://localhost:8202/health      # content_renderer    — esperar {"status":"ok",...}
```

Ambos são **públicos, sem token**. O `backend_core` não tem `/health` próprio
ainda (proxy de readiness sem auth — ver item "por confirmar" na matriz); usa
`GET /api/v1/schema/` como proxy de liveness:

```powershell
curl http://127.0.0.1:8100/api/v1/schema/   # 200 ⇒ Django está de pé
```

---

## 6. Executar o healthcheck agregado

Endpoint **staff-only** (`IsAdminUser`) que sonda IE + renderer + base de dados
num único pedido, sempre com `200`:

```powershell
# 1. obter um access token JWT de um utilizador is_staff=True
#    (ex.: via POST /api/v1/auth/login/ com as credenciais do superuser criado em 4.1)
# 2. chamar o endpoint agregado
curl -H "Authorization: Bearer <ACCESS_TOKEN>" http://127.0.0.1:8100/api/v1/system/health/dependencies/
```

Resposta esperada (exemplo, todos os serviços de pé):

```json
{
  "status": "ok",
  "service": "backend_core",
  "checked_at": "...",
  "dependencies": {
    "intelligence_engine": {"status": "ok", "url": "configured", "duration_ms": 12},
    "content_renderer": {"status": "ok", "url": "configured", "duration_ms": 18},
    "database": {"status": "ok", "duration_ms": 2}
  }
}
```

- Sem `Authorization` → `401`. Utilizador não-staff → `403`.
- Falha de uma dependência → `status` geral `degraded`/`unavailable`, **nunca**
  `500`.
- Timeout configurável por `HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS` (default
  `2.0`s).

---

## 7. Executar o smoke test do Intelligence Engine

Documentação completa: [`smoke_intelligence_engine.md`](smoke_intelligence_engine.md).
Forma rápida (sem base de dados):

```powershell
cd backend_core
$env:INTELLIGENCE_ENGINE_BASE_URL="http://127.0.0.1:8201"
$env:INTELLIGENCE_ENGINE_INTERNAL_TOKEN="<DEV_TOKEN>"
$env:INTELLIGENCE_ENGINE_ENABLED="true"; $env:INTELLIGENCE_ENGINE_DRY_RUN="false"
.\venv\Scripts\python.exe manage.py smoke_intelligence_engine
```

Sucesso esperado: linha `smoke_ie ok {...}` com as 6 chaves (`analysis`, `scores`,
`grade`, `moments`, `recommendations`, `summary`). Token nunca aparece na saída.
Loop completo (com base de dados, opt-in `pytest`):

```powershell
$env:RUN_REAL_IE="1"; $env:REAL_IE_BASE_URL="http://127.0.0.1:8201"; $env:REAL_IE_TOKEN="<DEV_TOKEN>"
.\venv\Scripts\python.exe -m pytest apps/campaigns/tests/test_intelligence_real_loop.py -q
```

---

## 8. Executar o smoke test do Content Renderer

Documentação completa: [`smoke_content_renderer.md`](smoke_content_renderer.md).
Camada 1 — perna de saída, sem base de dados (confirma `/health` + token +
aceitação `202`):

```powershell
cd backend_core
$env:INTERNAL_API_TOKEN="<DEV_TOKEN>"
$env:CONTENT_RENDERER_BASE_URL="http://localhost:8202"
.\venv\Scripts\python.exe manage.py smoke_content_renderer --health-only
.\venv\Scripts\python.exe manage.py smoke_content_renderer
```

Camada 2 — loop completo com callback (exige PostgreSQL, ver §4.3):

```powershell
cd content_renderer
npm run build
powershell -ExecutionPolicy Bypass -File scripts\run-e2e-postgres.ps1
```

---

## 9. Parar os serviços

| Serviço | Como parar |
|---|---|
| `backend_core` (`runserver`) | `Ctrl+C` no terminal onde corre |
| `intelligence_engine` (`uvicorn`) | `Ctrl+C` no terminal onde corre |
| `content_renderer` (`npm run dev`/`start`) | `Ctrl+C` no terminal onde corre |
| PostgreSQL do harness E2E | `docker compose -f content_renderer/docker-compose.e2e.yml down` (remove o container; dados em tmpfs, perdem-se sempre) |

> Se algum processo ficar "preso" numa porta (ex.: terminal fechado sem
> `Ctrl+C`), ver §11 "Porta ocupada".

---

## 10. Limpar artefactos locais

| Artefacto | Comando |
|---|---|
| Base de dados SQLite do `backend_core` | `Remove-Item backend_core\db.sqlite3` (recriar com `migrate`+seeds) |
| Storage local do renderer (ficheiros gerados) | `Remove-Item -Recurse content_renderer\storage\*` (caminho conforme `LOCAL_STORAGE_ROOT`) |
| Evidência do harness E2E | `content_renderer\e2e-logs\<timestamp>\` — apagar manualmente se não for necessária |
| PostgreSQL efémero do harness | `docker compose -f content_renderer/docker-compose.e2e.yml down -v` (tmpfs; sem volume persistente a remover na prática) |
| Ambientes virtuais Python / `node_modules` | Normalmente não é necessário limpar; só em caso de reinstalação completa (`Remove-Item -Recurse venv` / `node_modules`) |

---

## 11. Problemas comuns

| Sintoma | Causa provável | Acção |
|---|---|---|
| `403` em qualquer chamada interna | `INTERNAL_API_TOKEN` diferente entre os serviços | Confirmar que os três `.env`/variáveis de ambiente têm **exactamente** o mesmo valor |
| `INTELLIGENCE_ENGINE_BASE_URL`/`CONTENT_RENDERER_BASE_URL` aponta para porta errada | Defaults não ajustados ao ambiente | Confirmar com `curl` directo a essa porta/`/health` |
| Callback do renderer dá `404` no Django | `backend_core` a usar SQLite com callback cross-processo | Usar PostgreSQL (§4.3) para o loop completo; para smoke rápido (sem callback), Camada 1 do §8 é suficiente |
| Healthcheck agregado devolve `401`/`403` | Sem JWT ou utilizador não `is_staff` | Obter token de um utilizador `is_staff=True` (`createsuperuser` em §4.1) |
| Porta ocupada (`8100`/`8201`/`8202`) | Processo anterior não terminado | Windows: `Get-NetTCPConnection -LocalPort 8100 \| Select-Object OwningProcess` → `Stop-Process -Id <PID>` |
| `smoke_intelligence_engine` falha com "Cannot run … config" | `INTELLIGENCE_ENGINE_ENABLED=False` ou `DRY_RUN=True` ou token/URL vazios | Ajustar `.env`/variáveis conforme §7; smoke real exige `ENABLED=True` e `DRY_RUN=False` |
| `smoke_content_renderer` falha com "unavailable" | Renderer não está a correr ou porta errada | `curl http://localhost:8202/health`; confirmar `CONTENT_RENDERER_BASE_URL` |
| IE recusa arrancar em `production` | `INTERNAL_API_TOKEN` vazio com `APP_ENV=production` | Definir o token antes de mudar `APP_ENV` para `production` |
| Renderer recusa arrancar | Token vazio sem `ALLOW_INSECURE_EMPTY_TOKEN=true` | Definir `INTERNAL_API_TOKEN` (recomendado) ou, só em dev, `ALLOW_INSECURE_EMPTY_TOKEN=true` |
| Django recusa arrancar (`DEBUG=False`) | Guarda fail-fast: IE `ENABLED`+`DRY_RUN=False`+token vazio | Definir `INTELLIGENCE_ENGINE_INTERNAL_TOKEN`/`INTERNAL_API_TOKEN` antes de desligar `DEBUG` |

Diagnóstico mais detalhado e accionável (sintomas → causa → comandos) está em
[`checklist_troubleshooting.md`](checklist_troubleshooting.md) (OBS-STG-008, se
já existir).

---

## 12. Referências

- Matriz operacional completa: [`matriz_operacional_servicos.md`](matriz_operacional_servicos.md)
- Smoke IE: [`smoke_intelligence_engine.md`](smoke_intelligence_engine.md)
- Smoke Renderer: [`smoke_content_renderer.md`](smoke_content_renderer.md)
- Backlog da fase: [`01_backlog.md`](01_backlog.md)
- Harness E2E do renderer: `content_renderer/scripts/run-e2e-postgres.ps1`,
  `content_renderer/scripts/run-e2e-localpg.ps1`, `content_renderer/docker-compose.e2e.yml`
