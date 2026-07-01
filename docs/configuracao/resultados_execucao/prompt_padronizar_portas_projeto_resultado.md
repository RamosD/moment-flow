# Resultado — Padronização de Portas do Projecto

**Data:** 2026-07-01  
**Tarefa:** Padronizar todas as portas do ecossistema MomentFlow / ChartRex, eliminando portas proibidas e estabelecendo um mapa canónico.  
**Executor:** Claude Sonnet 4.6 (solução arquitecto + tech lead + guardião de configuração cross-cutting)

---

## 1. Mapa canónico de portas estabelecido

| Serviço | Porta | Variável principal |
|---|---|---|
| Frontend Web (Vite dev) | **5200** | `VITE_DEV_PORT` |
| Frontend Preview | **5201** | — |
| Backend Core (Django) | **8100** | `BACKEND_CORE_PORT` |
| Intelligence Engine (FastAPI) | **8201** | `INTELLIGENCE_ENGINE_PORT` |
| Content Renderer (FastAPI+Node) | **8202** | `PORT` |

**Portas proibidas removidas:** 8000, 8001, 8002, 8003, 1420, 9011, 5173, 5174, 8080–8085.

Referência canónica: [`docs/configuracao/portas_projeto.md`](../portas_projeto.md).

---

## 2. Regras arquitecturais mantidas (sem alteração)

- O Frontend Web chama apenas o Backend Core (`:8100`). Nunca chama IE ou Content Renderer directamente.
- O frontend nunca envia `X-Internal-Token`.
- Intelligence Engine e Content Renderer são serviços internos chamados pelo Backend Core.
- Nenhuma lógica funcional de produto foi alterada. Escopo restrito a configuração, scripts, documentação e validação de portas.

---

## 3. Alterações aplicadas por componente

### 3.1 Frontend / Vite

| Ficheiro | Alteração |
|---|---|
| `frontend/vite.config.ts` | `server.port: 5200, strictPort: true`; `preview.port: 5201, strictPort: true` |
| `frontend/src/shared/config/env.ts` | Fallback dev: `http://localhost:8100/api/v1` |
| `frontend/src/vite-env.d.ts` | Exemplo comentado: `http://localhost:8100/api/v1` |

### 3.2 Backend Core (Django)

| Ficheiro | Alteração |
|---|---|
| `backend_core/config/settings.py` | `INTELLIGENCE_ENGINE_BASE_URL` default → `http://localhost:8201`; `CONTENT_RENDERER_BASE_URL` e `REPORT_RENDERER_BASE_URL` defaults → `http://localhost:8202`; CORS: `http://localhost:5200` |
| `backend_core/apps/campaigns/tests/test_smoke_intelligence_command.py` | `127.0.0.1:8201` |
| `backend_core/apps/campaigns/tests/test_intelligence_real_loop.py` | `127.0.0.1:8201`; comentários `--port 8201` |
| `backend_core/apps/integrations_bridge/tests/test_settings_client_registry.py` | `http://localhost:8100/` |
| `backend_core/apps/integrations_bridge/tests/test_smoke_content_renderer_command.py` | `127.0.0.1:8202` (CONTENT e REPORT) |

### 3.3 Intelligence Engine (FastAPI)

| Ficheiro | Alteração |
|---|---|
| `intelligence_engine/README.md` | `--port 8201`; `curl http://localhost:8201/health` |
| `intelligence_engine/app/main.py` | Comentário `--port 8201` |
| `intelligence_engine/.env.example` | `INTELLIGENCE_ENGINE_PORT=8201` |

### 3.4 Content Renderer (Node/FastAPI)

| Ficheiro | Alteração |
|---|---|
| `content_renderer/src/config/env.ts` | Defaults: `port=8202`, `rendererPublicBaseUrl=8202`, `backendCoreBaseUrl=8100`, `localStoragePublicBaseUrl=8202/files` |
| `content_renderer/tests/env.test.ts` | Todos os expects: 8202, 8100 |
| `content_renderer/tests/jobs.test.ts` | `callback_url` → `:8100` |
| `content_renderer/tests/storage.test.ts` | `localhost:8202/files` (3 ocorrências) |
| `content_renderer/scripts/run-e2e.ps1` | `PORT=8202`, URLs 8202/8100, healthchecks |
| `content_renderer/scripts/run-e2e-postgres.ps1` | Idem |
| `content_renderer/scripts/run-e2e-localpg.ps1` | `DjangoPort=8100`, `PORT=8202`, URLs |
| `content_renderer/scripts/e2e_backend_core.py` | Comentários e `RENDERER_JOBS_URL` default → 8202/8100 |
| `content_renderer/README.md` | Tabela de config, exemplos, secção de integração |

### 3.5 Documentação operacional

| Ficheiro | Alteração |
|---|---|
| `docs/configuracao/portas_projeto.md` | **CRIADO** — mapa canónico oficial de portas |
| `scripts/check-forbidden-ports.ps1` | **CRIADO** — script de verificação automatizada |
| `backend_core/docs/fundamentos/03_observabilidade_staging_ecossistema/runbook_arranque_staging.md` | Tabela de portas, comandos, healthchecks; G9 resolvido |
| `backend_core/docs/fundamentos/03_observabilidade_staging_ecossistema/matriz_operacional_servicos.md` | Idem |
| `backend_core/docs/fundamentos/03_observabilidade_staging_ecossistema/checklist_troubleshooting.md` | Casos de diagnóstico; portas actualizadas |
| `backend_core/docs/fundamentos/03_observabilidade_staging_ecossistema/smoke_content_renderer.md` | URLs de exemplo → 8202/8100 |
| `backend_core/docs/fundamentos/03_observabilidade_staging_ecossistema/smoke_intelligence_engine.md` | URLs → 8201 |
| `backend_core/docs/fundamentos/03_observabilidade_staging_ecossistema/painel_prontidao_operacional.md` | B7/G9 marcados como **resolvidos** |
| `backend_core/docs/fundamentos/integracao_intelligence_engine/estado_integracao_intelligence_engine.md` | `127.0.0.1:8201`; `--port 8201` |
| `backend_core/docs/integracoes/02_estado_integracao_fastapi_renderer.md` | callback_url 8100; env vars 8201/8202 |
| `backend_core/docs/integracoes/01_backlog_integracao_fastapi_renderer.md` | Env vars actualizados |
| `backend_core/docs/content_renderer/fundamentos/01_backlog_content_report_renderer.md` | callback_url, env vars |
| `backend_core/docs/campaign_actions/01_backlog.md` | `localhost:8100`, `localhost:5200` |
| `backend_core/docs/campaign_actions/02_prompts_campain_actions.md` | 8000→8100 |
| `backend_core/docs/campaign_actions/backend_integrations/01_prompts_backend_integration.md` | 8000→8100, 5173→5200 |
| `backend_core/docs/campaign_actions/estado_campaign_actions_backend.md` | `runserver localhost:8100` |
| `content_renderer/docs/fundamentos/guia_e2e_backend_core.md` | 8202, 8100 em todo o guia |
| `content_renderer/docs/fundamentos/01_backlog_content_report_renderer.md` | callback_url, env vars, cenários |
| `content_renderer/docs/fundamentos/02_estado_content_report_renderer.md` | callback_url → 8100 |
| `content_renderer/docs/fundamentos/02_prompts_report_renderer.md` | `.env.example`, cenários de integração |
| `content_renderer/docs/fundamentos/03_backlog_hardening_pos_mvp_renderer.md` | Cenário de comportamento → 8202/8100 |
| `content_renderer/docs/fundamentos/04_prompts_hardening_pos_mvp_renderer.md` | Instruções de arranque → 8100/8202 |
| `docs_macro/gestao/Execucao e Acompanhamento (Sync)/05 - Matriz de Validação.md` | `REAL_IE_BASE_URL=http://127.0.0.1:8201` |
| `frontend/docs/01_fundamentos/01_frontend_foundation_campaign_war_room/01_backlog.md` | `VITE_BACKEND_API_BASE_URL=http://localhost:8100/api/v1` |
| `frontend/docs/01_fundamentos/01_frontend_foundation_campaign_war_room/arquitectura_frontend.md` | Fallback dev → 8100 |
| `frontend/docs/01_fundamentos/02_campaign_actions_recommendation_to_execution/02_prompts_campaign_actions.md` | 8000→8100, 5173→5200 |
| `frontend/docs/01_fundamentos/03_campaign_actions_backend_integration/estado_campaign_actions_backend_integration.md` | Critério de readiness → `localhost:8100` |

---

## 4. Ficheiros excluídos deliberadamente (evidência histórica)

| Ficheiro | Motivo |
|---|---|
| `resultados_execucao/**` e `resultados/**` | Relatórios de execuções passadas — imutáveis por definição |
| `estado_frontend_foundation_campaign_war_room.md` | FE-016 validou contra localhost:8000 — facto histórico |
| `estado_campaign_actions_backend_integration.md` (linha 106) | Descreve falha de validação passada em porta 8000 — facto histórico |
| URLs tipo `http://intelligence:8001` em testes | Fixtures de mock HTTP; não fazem ligações reais à rede |
| `.claude/launch.json` (`"port": 5173`) | Porta de attach do debugger VS Code — não é a porta de serviço |

---

## 5. Resolução do G9 (REPORT_RENDERER_BASE_URL)

Discrepância histórica: `REPORT_RENDERER_BASE_URL` defaultava para `:8003` no código enquanto o serviço real corria em `:8002`.

**Estado actual:** ambos `CONTENT_RENDERER_BASE_URL` e `REPORT_RENDERER_BASE_URL` defaultam agora para `http://localhost:8202` no código Django (`config/settings.py`). Workaround manual eliminado. Documentado como resolvido em `painel_prontidao_operacional.md` (B7) e `matriz_operacional_servicos.md`.

---

## 6. Validação automatizada

### `scripts/check-forbidden-ports.ps1`

Script criado e executado. **Resultado final: OK — 0 violações encontradas.**

```text
check-forbidden-ports: OK — nenhuma porta proibida encontrada em ficheiros activos.
```

Critérios do script:
- Padrão: `localhost:PORTA_PROIBIDA` e `127.0.0.1:PORTA_PROIBIDA` (não abrange URLs de container)
- Exclusões: `resultados_execucao/`, `resultados/`, `node_modules/`, `venv/`, `.git/`, `dist/`, `coverage/`, ficheiros históricos específicos

### Testes unitários / linting

| Suite | Resultado |
|---|---|
| `pnpm lint` (frontend) | 0 erros |
| `npm test` (content_renderer) | 136/136 passed |
| `python manage.py check` (backend_core) | 0 issues |

---

## 7. Variáveis de ambiente canónicas

```env
# Frontend
VITE_BACKEND_API_BASE_URL=http://localhost:8100/api/v1
VITE_DEV_PORT=5200

# Backend Core
BACKEND_CORE_PORT=8100
CORS_ALLOWED_ORIGINS=http://localhost:5200
INTELLIGENCE_ENGINE_BASE_URL=http://localhost:8201
CONTENT_RENDERER_BASE_URL=http://localhost:8202
REPORT_RENDERER_BASE_URL=http://localhost:8202

# Intelligence Engine
INTELLIGENCE_ENGINE_PORT=8201

# Content Renderer
PORT=8202
BACKEND_CORE_BASE_URL=http://localhost:8100
RENDERER_PUBLIC_BASE_URL=http://localhost:8202
LOCAL_STORAGE_PUBLIC_BASE_URL=http://localhost:8202/files
```

---

## 8. Pendentes (fora do escopo desta tarefa)

| Item | Razão |
|---|---|
| Validação E2E real (3 serviços simultâneos) | Exige ambiente de staging com Backend Core, IE e Renderer a correr; fora do escopo de configuração de portas. |
| Backend Core pytest completo | Suite exige ambiente Django completo (DB, migrações); não executado nesta sessão de configuração. |

---

## 9. Classificação de estado

| Critério | Estado |
|---|---|
| Mapa canónico de portas documentado | **Concluído** |
| Portas proibidas eliminadas de configs e scripts | **Concluído** |
| Portas proibidas eliminadas de docs operacionais e prompts | **Concluído** |
| Script de verificação criado e a passar | **Concluído** |
| Testes unitários a passar | **Concluído** |
| Validação E2E real nas novas portas | **Pendente** (bloqueado por ambiente; não declarado concluído) |
