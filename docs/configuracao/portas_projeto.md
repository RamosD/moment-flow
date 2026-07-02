# Mapa Oficial de Portas — MomentFlow / ChartRex

> **Documento normativo.** Todas as configurações activas, scripts e documentação
> operacional do ecossistema devem referenciar exclusivamente as portas abaixo.
>
> **Portas proibidas:** 8000, 8001, 8002, 8003, 1420, 9011, 5173, 5174,
> 8080–8085. Usar `scripts/check-forbidden-ports.ps1` para validar.

---

## Mapa canónico

| Serviço | Protocolo | Porta | Variável / flag |
|---|---|---|---|
| **Frontend Web (Vite dev)** | HTTP | **5200** | `VITE_DEV_PORT=5200` / `vite.config.ts server.port` |
| **Frontend Preview (Vite build)** | HTTP | **5201** | `vite.config.ts preview.port` |
| **Backend Core (Django)** | HTTP | **8100** | `python manage.py runserver 127.0.0.1:8100` |
| **Intelligence Engine (FastAPI/Uvicorn)** | HTTP | **8201** | `uvicorn ... --port 8201` / `INTELLIGENCE_ENGINE_PORT=8201` |
| **Content & Report Renderer (Node/Express)** | HTTP | **8202** | `PORT=8202` |

---

## Variáveis derivadas

```dotenv
# Frontend (frontend/.env.local)
VITE_BACKEND_API_BASE_URL=http://localhost:8100/api/v1

# Backend Core (backend_core/.env)
BACKEND_CORE_PORT=8100
CORS_ALLOWED_ORIGINS=http://localhost:5200,http://127.0.0.1:5200
BACKEND_PUBLIC_BASE_URL=http://localhost:8100
# 127.0.0.1, não "localhost": em Windows, "localhost" resolve para ::1 E
# 127.0.0.1, e o bind por default do uvicorn (só IPv4) não responde em ::1 —
# cada chamada gasta o timeout completo na tentativa IPv6 antes de recuar
# para IPv4, duplicando a latência sempre que o motor está inacessível
# (achado STG-PRE-006, confirmado no healthcheck agregado e nas chamadas
# síncronas reais).
INTELLIGENCE_ENGINE_BASE_URL=http://127.0.0.1:8201
CONTENT_RENDERER_BASE_URL=http://localhost:8202
REPORT_RENDERER_BASE_URL=http://localhost:8202

# Intelligence Engine (intelligence_engine/.env)
INTELLIGENCE_ENGINE_PORT=8201

# Content & Report Renderer (content_renderer/.env)
PORT=8202
BACKEND_CORE_BASE_URL=http://localhost:8100
RENDERER_PUBLIC_BASE_URL=http://localhost:8202
LOCAL_STORAGE_PUBLIC_BASE_URL=http://localhost:8202/files
```

---

## Regras arquitecturais (invioláveis)

1. **O Frontend Web chama apenas o Backend Core** (`:8100/api/v1`). Nunca chama
   Intelligence Engine ou Content Renderer directamente.
2. **O frontend nunca envia `X-Internal-Token`**. Esse header é exclusivo de
   comunicações serviço-a-serviço (Backend Core → IE / Renderer).
3. **Intelligence Engine e Content Renderer são serviços internos** chamados
   pelo Backend Core. Não estão expostos ao frontend nem ao utilizador final.
4. O Content Renderer serve os três tipos de job (`content_generation`,
   `report_generation`, `media_kit_generation`) na **mesma porta 8202**; tanto
   `CONTENT_RENDERER_BASE_URL` como `REPORT_RENDERER_BASE_URL` apontam para
   `:8202`.

---

## Healthchecks de validação

```powershell
# Backend Core (Django) — schema como proxy de liveness
curl http://127.0.0.1:8100/api/v1/schema/

# Intelligence Engine
curl http://127.0.0.1:8201/health

# Content & Report Renderer
curl http://localhost:8202/health

# Healthcheck agregado (staff-only, requer JWT)
curl -H "Authorization: Bearer <ACCESS_TOKEN>" http://127.0.0.1:8100/api/v1/system/health/dependencies/
```

---

## Validação automática

```powershell
# A partir da raiz do repositório:
pwsh -ExecutionPolicy Bypass -File scripts/check-forbidden-ports.ps1
```

O script verifica se algum ficheiro activo (excluindo `node_modules`, `venv`,
`.git`, `resultados_execucao/`, e `resultados/`) contém referências às portas
proibidas e sai com código não-zero se encontrar violações.

---

> Data de criação: 2026-07-01. Actualizar este documento sempre que o mapa de
> portas mudar. Não alterar portas sem actualizar todos os ficheiros listados em
> `scripts/check-forbidden-ports.ps1`.
