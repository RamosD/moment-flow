# Prompt 16 — Validação E2E Real com Portas Padronizadas

**Data:** 2026-07-01  
**Fase:** `03_campaign_actions_backend_integration`  
**Executor:** Claude Sonnet 4.6 (QA técnico + tech lead frontend/backend + guardião de integração E2E)  
**Estado de execução:** `executado_parcialmente` — validação API real completa; validação visual no browser bloqueada por limitação ambiental

---

## 1. Portas usadas

| Serviço | Porta | Método de confirmação |
|---|---|---|
| Backend Core (Django) | **8100** | HTTP 200, WSGIServer/0.2 CPython/3.13.2 |
| Frontend Web (Vite) | **5200** | HTTP 200, text/html, 615 bytes |
| Intelligence Engine | 8201 | Não arrancado; dry_run mode activo |
| Content Renderer | 8202 | Não usado nesta validação |

---

## 2. Confirmação dos serviços correctos

### Backend Core

```text
GET http://localhost:8100/api/v1/schema/  → HTTP 200  Content-Type: application/vnd.oai.openapi
GET http://localhost:8100/api/v1/docs/   → HTTP 200
GET http://localhost:8100/admin/         → HTTP 200  Server: WSGIServer/0.2 CPython/3.13.2
```

Django confirmado — não é FastAPI/uvicorn. Server header confirma Django WSGI.

### Frontend

```text
GET http://localhost:5200/  → HTTP 200  Content-Type: text/html  615 bytes
```

Vite a servir o bundle React correcto na porta canónica. `vite.config.ts` confirma `port: 5200, strictPort: true`.

### Portas antigas

Nenhum dos serviços responde em 8000, 5173 ou outras portas proibidas — confirmado por timeout nas sondas iniciais.

---

## 3. Configuração de portas validada

| Variável | Valor activo | Fonte |
|---|---|---|
| `VITE_BACKEND_API_BASE_URL` | `http://localhost:8100/api/v1` | `frontend/.env.local` |
| Vite `server.port` | `5200` + `strictPort: true` | `vite.config.ts` |
| Vite `preview.port` | `5201` + `strictPort: true` | `vite.config.ts` |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5200,http://127.0.0.1:5200` | `backend_core/.env` + `settings.py` |
| `INTELLIGENCE_ENGINE_BASE_URL` | `http://localhost:8201` | `backend_core/.env` |
| `CONTENT_RENDERER_BASE_URL` | `http://localhost:8202` | `backend_core/.env` |
| `REPORT_RENDERER_BASE_URL` | `http://localhost:8202` | `backend_core/.env` |
| `DEV_FALLBACK_API_BASE_URL` | `http://localhost:8100/api/v1` | `frontend/src/shared/config/env.ts:13` |

---

## 4. Dados dev usados

| Entidade | Identificador |
|---|---|
| Utilizador | `ca014-dev@example.local` (password temporária definida via Django shell; não armazenada) |
| Workspace | `46ca02a0-edcf-4835-8878-a6ff24b41598` — "CA014 Dev Workspace" |
| Campaign | `30930999-5cd3-47d8-afb0-2c218084ed7d` — "CA014 Test Campaign" (status=active) |
| Artist | `915a6fdc-270f-42fa-86ea-ef2ccd70746b` |
| Content Packs | 4 packs disponíveis (key=auto_media_kit e outros) |
| DB | SQLite local (`backend_core/db.sqlite3`, 1.2MB) |

Migração aplicada: `campaign_actions.0001_initial` (tabela estava em falta; aplicada antes dos testes).

---

## 5. Matriz de validação API

### 5.1 Autenticação e War Room

| Verificação | Resultado | Detalhe |
|---|---|---|
| `POST /auth/token/` | ✅ | JWT access token devolvido |
| `GET /auth/me/` | ✅ | `email=ca014-dev@example.local` |
| `GET /campaigns/{id}/` | ✅ | `name=CA014 Test Campaign, status=active` |
| `POST /campaigns/{id}/intelligence/` | ✅ | `source=dry_run, status=completed, grade=unknown` |
| `GET /workspaces/` | ✅ | `count=1` |
| `GET /campaigns/` | ✅ | `count=1` |

### 5.2 Read path — CampaignActionsPanel

| Verificação | Resultado | Detalhe |
|---|---|---|
| `GET /campaign-actions/?campaign=…` | ✅ | Endpoint responde, paginado |
| Empty state honesto | ✅ | `count=0` antes de criar actions |
| Todos os campos obrigatórios na resposta | ✅ | `action_type, status, priority, source, recommendation_ref, recommendation_snapshot, related_*, created_at, updated_at, completed_at, cancelled_at, dismiss_reason` |
| Todos os 4 `related_*` presentes | ✅ | `related_report, related_media_kit, related_content_pack_request, related_content_output` |
| Paginação | ✅ | `page_size=3` → 3 results, next/previous links |
| Ordering estável | ✅ | Dois GETs consecutivos retornam mesma ordem |
| Não usa `/content-pack-requests/`, `/reports/`, `/media-kits/` para agregar | ✅ | Apenas `/campaign-actions/` consultado |

### 5.3 Create path — tipos sem artefacto

| Tipo | Resultado | Campos confirmados |
|---|---|---|
| `manual_task` | ✅ | `id=a5fa052e`, `status=pending`, `recommendation_ref=e2e-ref-001`, `source=recommendation`, `priority=high`, snapshot persistido |
| `mark_reviewed` | ✅ | `id=20894245`, `status=completed`, `completed_at=2026-07-01 22:08:12` |
| `dismiss` (com motivo) | ✅ | `id=0b4ad6b0`, `status=dismissed`, `dismiss_reason=Not relevant to current campaign phase` |

### 5.4 Create path — tipos com artefacto

| Tipo | Resultado | Artefacto | Related FK |
|---|---|---|---|
| `report_request` | ✅ | `POST /reports/` → `id=daa36897, status=queued` | `related_report=daa36897` presente no painel |
| `media_kit_request` | ✅ | `POST /media-kits/` → `id=771baa32, status=draft` | `related_media_kit=771baa32` presente no painel |
| `content_pack` | ✅ | `POST /content-pack-requests/` → `id=6af761e9, status=queued` | `related_content_pack_request=6af761e9` presente no painel |

Fluxo confirmado: artefacto criado primeiro → CampaignAction criada com `related_*` → IDs distintos ✅

### 5.5 Múltiplas actions por recommendation

| Verificação | Resultado | Detalhe |
|---|---|---|
| `ref=e2e-ref-multi` tem `manual_task` | ✅ | `id=3f020397` |
| `ref=e2e-ref-multi` tem `report_request` | ✅ | `id=c331c6d8` |
| Um tipo não bloqueia o outro | ✅ | Ambos criados com sucesso |

### 5.6 Deduplicação

| Verificação | Resultado | Detalhe |
|---|---|---|
| Duplicado activo do mesmo tipo+ref | ✅ Rejeitado | HTTP 400: `"recommendation_ref": ["An active action of this type already exists for this recommendation."]` |
| Campo de erro em snake_case | ✅ | `recommendation_ref` (não camelCase) |

### 5.7 Lifecycle

| Verificação | Resultado | Detalhe |
|---|---|---|
| `POST /campaign-actions/{id}/complete/` | ✅ | `status=completed, completed_at=2026-07-01 22:09:44` |
| `POST /campaign-actions/{id}/cancel/` | ✅ | `status=cancelled, cancelled_at=2026-07-01 22:09:48` |
| `complete` idempotente (completed→completed) | ✅ | Por design (`validate_status_transition` linha 58) |
| Terminal real: `cancel` em `completed` | ✅ Rejeitado | HTTP 400: `"Transition from completed to cancelled is not allowed."` |
| `dismiss` sem motivo via `/dismiss/` | ✅ Rejeitado | HTTP 400 campo `dismiss_reason` |

### 5.8 Erros reais

| Cenário | HTTP | Campo/Detalhe |
|---|---|---|
| 400 — `dismiss` sem motivo no create | ✅ 400 | `dismiss_reason: "This field is required for dismissed actions."` |
| 400 — campos obrigatórios em falta | ✅ 400 | `action_type, title` em snake_case |
| 400 — duplicado activo | ✅ 400 | `recommendation_ref: [...]` |
| 400 — transição terminal inválida | ✅ 400 | `status: "Transition from completed to cancelled is not allowed."` |
| 401 — sem token | ✅ 401 | — |
| 403 — action de outro workspace | ✅ 403 | `detail: "Workspace not found or access denied."` |
| 404 — action inexistente | ✅ 404 | — |
| Cross-workspace list filtrada | ✅ | Lista vazia (não revela dados de outro workspace) |

### 5.9 Reload/persistência

GET repetido após criação de 8 actions confirma todos os ids, tipos, status e `related_*` correctos. Ordering estável entre requests consecutivos.

---

## 6. Validação de segurança (greps runtime)

| Padrão | Resultado |
|---|---|
| `X-Internal-Token` | CLEAN — apenas em comentários e README (proibição explícita) |
| `INTERNAL_API_TOKEN` | CLEAN — apenas na denylist do snapshot (`recommendation-snapshot.ts`) |
| `private_key` | CLEAN — apenas na denylist do snapshot |
| `intelligence_engine` | CLEAN — sem referências runtime |
| `content_renderer` | CLEAN — sem referências runtime |
| `localhost:8201` | CLEAN |
| `localhost:8202` | CLEAN |
| `localhost:8000` | CLEAN |
| `localhost:5173` | CLEAN |
| `localhost:8080-8085` | CLEAN |
| `Bearer` hardcoded | CLEAN — apenas dinâmico no client central |
| `api_key =` | CLEAN |

**Confirmações de arquitectura:**
- `src/shared/api/client.ts` declara explicitamente: *"never sends `X-Internal-Token` — that header is a service-to-service secret and must not exist in the browser"*
- `src/shared/config/env.ts` declara: *"There is intentionally no configuration here for the Intelligence Engine or the Content Renderer, and no internal secrets."*
- Frontend aponta exclusivamente para `http://localhost:8100/api/v1`

---

## 7. Validações técnicas

| Validação | Resultado |
|---|---|
| `pnpm test` | ✅ 14/14 passed |
| `pnpm lint` | ✅ 0 errors |
| `pnpm build` | ✅ 249 modules, 2.94s |
| `python manage.py check` | ✅ 0 issues |
| `pytest apps/campaign_actions/` | ✅ 56/56 passed (147s) |

---

## 8. Validação no browser (visual)

**Estado: BLOQUEADO POR AMBIENTE**

A ferramenta `computer-use` (necessária para controlar o browser no ambiente de CI/automação) falhou com timeout de 300s em `request_access`. Este é o mesmo tipo de bloqueio ambiental que ocorreu no Prompt 13 (`EPERM`, browser inacessível). Não é uma falha do produto ou do código.

O frontend em `http://localhost:5200/` confirmou HTTP 200 com content-type `text/html`. O serviço está a correr correctamente. A navegação visual (login form, War Room, CampaignActionsPanel, dialogs, Network tab do DevTools) não foi possível automatizar.

**Recomendação:** smoke test visual manual de 10 minutos antes do primeiro piloto com utilizadores reais.

---

## 9. Ficheiros criados/alterados

| Ficheiro | Operação |
|---|---|
| `frontend/docs/.../estado_campaign_actions_backend_integration.md` | **ACTUALIZADO** — estado, validação real, prontidão |
| `frontend/docs/.../resultados_execucao/prompt_16_...resultado.md` | **CRIADO** (este ficheiro) |
| `backend_core/db.sqlite3` | Migração `campaign_actions.0001_initial` aplicada; 8 CampaignActions inseridas |

---

## 10. Limitações e riscos em aberto

| Limitação | Impacto |
|---|---|
| Validação visual no browser não executada | Risco baixo-médio: APIs confirmadas; UI pode ter regressões visuais não detectadas |
| Intelligence Engine em dry_run | War Room devolve `source=dry_run, grade=unknown`; recomendações reais requerem IE real em 8201 |
| Content Renderer não testado | Relatórios e media kits ficam em `status=queued`; render não avança sem CR real |
| RBAC com roles diferentes não testado | Viewer pode ver affordances e receber 403 autoritativo (dívida conhecida) |
| Dados de validação deixados no SQLite | 8 CampaignActions, 2 Reports, 1 MediaKit, 1 ContentPackRequest no DB dev — não há problema para dev local |

---

## 11. Conclusão

### Pronto para piloto técnico controlado?

**Sim, com ressalva.**

Todos os critérios mínimos definidos no `estado_campaign_actions_backend_integration.md` foram satisfeitos:
1. Django correcto em `localhost:8100` ✅
2. Base dev acessível e dados mínimos ✅
3. Todos os create paths exercitados via API real ✅
4. Reload/persistência, deduplicação e múltiplos tipos confirmados ✅
5. 400/401/403/404/cross-workspace reais confirmados ✅
6. Build completo executado ✅

**Ressalva:** recomenda-se um smoke test visual manual de 10 minutos (login → War Room → CampaignActionsPanel → criar uma action) antes de qualquer piloto com utilizadores reais, dado que a navegação no browser não foi automáticas por limitação ambiental.

### Pronto para produção?

**Não.** Além das ressalvas do piloto, faltam: staging, E2E repetível e automático, validação cross-browser, observabilidade, revisão RBAC/UX, IE/CR reais em staging, e aprovação operacional.
