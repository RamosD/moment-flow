# Prompt 02 — Arrancar e validar serviços nas portas canónicas

**Data:** 2026-07-01
**Fase:** `04_staging_campaign_actions_with_real_ie_renderer` (STG-CA-002, Incremento 0)
**Âmbito:** arranque e validação de portas/healthchecks. Sem alteração de lógica de produto.
**Estado de execução:** `executado`

---

## 1. Resumo objectivo

Os quatro serviços canónicos estão **de pé e confirmados como o serviço correcto** em cada porta:

| Serviço | Porta | Estado | Prova |
|---|---|---|---|
| Frontend Web (Vite) | **5200** | ✅ já a correr | `GET /` → 200, `strictPort:true` |
| Backend Core (Django) | **8100** | ✅ já a correr | Server `WSGIServer/0.2 CPython/3.13.2`, schema `application/vnd.oai.openapi` |
| Intelligence Engine (FastAPI) | **8201** | ✅ arrancado agora | `/health` → `{"service":"intelligence_engine"}` |
| Content Renderer (Node/Express) | **8202** | ✅ arrancado agora | `/health` → `{"service":"content_renderer"}` |

Backend Core e Frontend **já estavam a correr** nas portas canónicas correctas (não foram reiniciados, para não colidir com `strictPort`). IE e CR foram arrancados nesta iteração.

Nenhum ficheiro de configuração foi alterado — IE e CR foram arrancados com variáveis **inline** (ver §5).

---

## 2. Serviços arrancados / confirmados

### Já a correr (confirmados, não reiniciados)
- **Backend Core (8100)** — pid python 3740. Confirmado Django (não o uvicorn alheio da :8000).
- **Frontend (5200)** — pid node 20968.

### Arrancados nesta iteração
- **Intelligence Engine (8201)** — pid python 41120, uvicorn `app.main:app`, `app_env=development`.
- **Content Renderer (8202)** — pid node 42112, `tsx watch src/server.ts`.

---

## 3. Portas usadas

| Porta | Estado | Processo | Serviço |
|---|---|---|---|
| 5200 | LISTEN | node (20968) | Frontend Web ✅ |
| 8100 | LISTEN | python (3740) | Backend Core Django ✅ |
| 8201 | LISTEN | python (41120) | Intelligence Engine ✅ |
| 8202 | LISTEN | node (42112) | Content Renderer ✅ |
| 8000 | LISTEN | python (32536) | **uvicorn alheio** — NÃO é o Backend Core (ver §7) |
| 5173 | LISTEN | node (11732) | processo node alheio (porta Vite antiga) |

---

## 4. Healthchecks (endpoints reais do Prompt 01)

| Serviço | Endpoint | Resultado |
|---|---|---|
| IE | `GET http://localhost:8201/health` | 200 · `{"status":"ok","service":"intelligence_engine","version":"0.1.0",...}` |
| CR | `GET http://localhost:8202/health` | 200 · `{"status":"ok","service":"content_renderer","version":"0.1.0","uptime_seconds":29,...}` |
| BC | `GET http://localhost:8100/api/v1/schema/` | 200 · `Content-Type: application/vnd.oai.openapi` |
| BC | `GET http://localhost:8100/api/v1/docs/` | 200 · `text/html` |
| BC | `GET http://localhost:8100/admin/` | 302 → login (comportamento Django esperado) |
| FE | `GET http://localhost:5200/` | 200 |

O healthcheck agregado (`GET /api/v1/system/health/dependencies/`, staff-only) não foi exercido aqui por exigir JWT de staff; fica para uma iteração com autenticação (STG-CA-006).

---

## 5. Comandos executados

```bash
# Intelligence Engine (8201) — background
cd intelligence_engine
APP_ENV=development LOG_LEVEL=INFO ./venv/Scripts/python.exe \
  -m uvicorn app.main:app --host 127.0.0.1 --port 8201

# Content Renderer (8202) — background (variáveis inline; sem alterar .env)
cd content_renderer
NODE_ENV=development ALLOW_INSECURE_EMPTY_TOKEN=true PORT=8202 \
  RENDERER_PUBLIC_BASE_URL=http://localhost:8202 \
  BACKEND_CORE_BASE_URL=http://localhost:8100 \
  npm run dev
```

Validações:
```bash
python manage.py check                                  # Backend Core (venv)
pnpm lint                                               # frontend
pnpm build                                              # frontend
pwsh -File scripts/check-forbidden-ports.ps1
# + probes HTTP dos 4 healthchecks
```

**Nota:** o CR foi arrancado em **modo inseguro** (`ALLOW_INSECURE_EMPTY_TOKEN=true`) porque o loader do env recusa arrancar em `development` com `INTERNAL_API_TOKEN` vazio. Isto é suficiente para o `/health` (público), mas **não** habilita o fluxo autenticado IE/callback — ver §8.

---

## 6. Confirmações de configuração

### Backend Core aponta para os serviços correctos (`backend_core/.env`)
```
INTELLIGENCE_ENGINE_BASE_URL=http://localhost:8201
CONTENT_RENDERER_BASE_URL=http://localhost:8202
REPORT_RENDERER_BASE_URL=http://localhost:8202
```

### Frontend sem config de IE/Renderer (`frontend/.env.local`)
```
VITE_BACKEND_API_BASE_URL=http://localhost:8100/api/v1
```
Grep por `INTELLIGENCE_ENGINE_BASE_URL` / `CONTENT_RENDERER_BASE_URL` / `INTERNAL_API_TOKEN` / `8201` / `8202` nos `.env*` do frontend → **NONE (good)**.

### Vite `strictPort` (`vite.config.ts`)
```
server:  { port: 5200, strictPort: true }
preview: { port: 5201, strictPort: true }
```

---

## 7. Evidência de que cada serviço é o correcto

- **8100 = Django** (não FastAPI): `Server: WSGIServer/0.2 CPython/3.13.2`; `/api/v1/schema/` devolve `application/vnd.oai.openapi`; `/admin/` redirecciona (302) para login.
- **8000 = uvicorn alheio** (NÃO validar contra): `Server: uvicorn`, `Content-Type: application/json`, `GET /api/v1/schema/` → **404**. Não é o Backend Core. Correctamente ignorado (mesmo serviço alheio do histórico do Prompt 13).
- **8201 = Intelligence Engine**: corpo do `/health` traz `"service":"intelligence_engine"`.
- **8202 = Content Renderer**: corpo do `/health` traz `"service":"content_renderer"`.

Cada porta foi validada pelo conteúdo/headers do serviço, não apenas pelo código HTTP.

---

## 8. Validações executadas

| Validação | Resultado |
|---|---|
| `python manage.py check` | ✅ `System check identified no issues (0 silenced).` |
| `pnpm lint` (frontend) | ✅ `eslint .` sem erros |
| `pnpm build` (frontend) | ✅ 249 módulos, `built in 2.71s` |
| `scripts/check-forbidden-ports.ps1` | ✅ `OK — nenhuma porta proibida encontrada em ficheiros activos` |
| Healthchecks HTTP (4 serviços) | ✅ todos 200 |

---

## 9. Bloqueios

Nenhum bloqueio de arranque. Observações/pendências:

| ID | Item | Sev. | Nota |
|---|---|---|---|
| P02-O01 | Portas antigas **8000** (uvicorn) e **5173** (node) ocupadas por processos **alheios** | Baixo | Não são serviços deste projecto nem referenciados em config activa (`check-forbidden-ports` passa). Os nossos 4 serviços estão nas portas canónicas. Recomenda-se parar esses processos alheios para evitar confusão futura. |
| P02-O02 | CR a correr em `ALLOW_INSECURE_EMPTY_TOKEN=true`; IE com token vazio | **Alto (herdado, P01-R01)** | Suficiente para healthchecks, **insuficiente** para o fluxo real: IE devolverá 403 a `/intelligence/campaign`; callback CR→Django será rejeitado (403). Antes de STG-CA-003/005 é preciso um `INTERNAL_API_TOKEN` partilhado não-vazio nos três serviços (e reiniciá-los). |
| P02-O03 | `INTELLIGENCE_ENGINE_DRY_RUN=true` e `EXTERNAL_JOBS_DRY_RUN=true` no BC | **Alto (herdado)** | Continuam por desactivar (âmbito do STG-CA-003/005). O Django em execução ainda está em dry-run. |

---

## 10. Ficheiros alterados

Apenas este relatório (**criado**):
`frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_02_arrancar_servicos_portas_canonicas_resultado.md`

Nenhum `.env`, settings ou código de produto foi alterado (IE/CR arrancados com variáveis inline).

---

## 11. Próximo passo recomendado

Avançar para **STG-CA-003 (War Room com Intelligence Engine real)**, precedido da resolução da pendência de token/dry-run (P02-O02/O03):

1. Definir **um** `INTERNAL_API_TOKEN` partilhado (mesmo valor) em `backend_core/.env`, `intelligence_engine/.env` e `content_renderer/.env`.
2. No `backend_core/.env`, `INTELLIGENCE_ENGINE_DRY_RUN=false` (e, para STG-CA-005, `EXTERNAL_JOBS_DRY_RUN=false`).
3. **Reiniciar** Backend Core, IE e CR para aplicar token/dry-run (o Django actual em 8100 foi arrancado externamente em modo dry-run).
4. Executar `POST /api/v1/campaigns/{id}/intelligence/` e confirmar `source=engine` (não `dry_run`) com recommendations reais.

> Os serviços IE (8201) e CR (8202) ficaram a correr em background no fim desta iteração.
