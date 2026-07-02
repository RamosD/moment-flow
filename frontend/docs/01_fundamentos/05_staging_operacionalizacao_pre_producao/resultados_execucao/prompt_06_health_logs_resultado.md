# Prompt 06 — Health e logs — Resultado

**Data:** 2026-07-02
**Fase:** `05_staging_operacionalizacao_pre_producao` (STG-PRE-006)
**Âmbito:** validar e endurecer healthchecks, readiness, logs estruturados e sinais de falha. Sem tornar o health agregado público, sem mascarar dependências, sem observabilidade pesada desnecessária.
**Estado de execução:** `executado` — validação real (não só mocks) com os três serviços a correr, mais um achado de latência real corrigido e dois endpoints novos (liveness/readiness) implementados.

---

## 1. Resumo objectivo

Validei os quatro healthchecks existentes (IE, Content Renderer, agregado do
Backend Core, e o proxy de schema) com um **utilizador staff real** e os
três serviços genuinamente em execução — a fase 04 tinha deixado isto como
"parcial" (só testado com mocks). Confirmei que o agregado cobre DB, IE e
Content Renderer/Report Renderer correctamente (`ok`/`degraded`/`unavailable`
conforme o estado real), nunca devolve 500, e nunca expõe segredos.

Identifiquei que **não existia nenhum endpoint de liveness/readiness
dedicado e público** no Backend Core — só o agregado (staff-only, pesado
para um probe de infraestrutura) e o `/api/v1/schema/` como proxy
improvisado. Implementei dois endpoints novos, mínimos e públicos
(`/api/v1/system/health/live/` e `/api/v1/system/health/ready/`), ao mesmo
nível de segurança dos `/health` do IE e do Content Renderer.

**Achado real e corrigido durante a validação:** em Windows, o valor por
omissão `INTELLIGENCE_ENGINE_BASE_URL=http://localhost:8201` fazia toda
chamada ao IE (agregado **e** chamadas síncronas reais de intelligence)
gastar sistematicamente **~2 segundos extra**, e o dobro quando o IE estava
mesmo em baixo — porque `localhost` resolve para `::1` **e** `127.0.0.1`, e
o `uvicorn` só escuta em IPv4. Cada chamada esgotava o timeout completo na
tentativa IPv6 antes de recuar para IPv4. Corrigido: o default passou a
`127.0.0.1`. Validado antes/depois: `duration_ms` do IE no agregado caiu de
~2000ms para ~40ms.

Também corrigi, como parte directa desta validação, os **3 testes do
healthcheck agregado que já estavam a falhar** (achado de uma iteração
anterior, `task_e252710e`) — usavam literais de porta desactualizados
(`"8001"`/`"8002"` em vez de `"8201"`/`"8202"`), pelo que a condição de
simulação de falha nunca disparava.

---

## 2. Endpoints validados

| Endpoint | Método de validação | Resultado |
|---|---|---|
| `GET /health` (Intelligence Engine) | HTTP real, `curl` | ✅ `200`, `{"status":"ok","service":"intelligence_engine","version":"0.1.0","timestamp":...}` |
| `GET /health` (Content Renderer) | HTTP real, `curl` | ✅ `200`, `{"status":"ok","service":"content_renderer","uptime_seconds":...}` |
| `GET /api/v1/system/health/dependencies/` (Backend Core) | HTTP real, **utilizador staff real** (`is_staff=True` temporário no user de dev, revertido no fim), JWT real, três serviços reais a correr | ✅ `200`, `status=ok`, os três `dependencies` (`intelligence_engine`, `content_renderer`, `database`) todos `ok` |
| `GET /api/v1/system/health/dependencies/` com IE parado de propósito | HTTP real, IE parado | ✅ `200`, `status=degraded`, `intelligence_engine.status=unavailable`, `detail=timeout`; `content_renderer`/`database` continuam `ok` |
| `GET /api/v1/system/health/live/` (**novo**) | HTTP real, sem autenticação | ✅ `200`, `{"status":"ok","service":"backend_core"}` |
| `GET /api/v1/system/health/ready/` (**novo**) | HTTP real, sem autenticação | ✅ `200` com DB up; `503` simulado em teste com DB down |
| `GET /api/v1/schema/` (proxy de liveness) | HTTP real | ✅ `200`, mantido sem alteração (compatibilidade) |

**Autenticação do health agregado confirmada:** `IsAdminUser` (staff-only).
Sem autenticação → `401`; autenticado mas não-staff → `403`; staff → `200`.
Os dois endpoints novos são deliberadamente **públicos** (`AllowAny`),
espelhando o `/health` do IE e do Content Renderer — nunca expõem estado de
IE/Renderer, só `ok`/`unavailable` de si próprios.

---

## 3. Resultados por dependência

| Dependência | Estado normal | Estado simulado (real, não mock) | Detail |
|---|---|---|---|
| Intelligence Engine | `ok`, `duration_ms≈40` (após correcção) | `unavailable`, `detail=timeout` (processo parado) | `duration_ms` antes de corrigir o achado de latência: ~2000-4000ms |
| Content Renderer / Report Renderer | `ok`, `duration_ms≈10-20` | Não testado no agregado nesta iteração (já validado em fases anteriores); testado sim o fluxo de job (ver §5) | Um único processo serve `content_generation`/`report_generation`/`media_kit_generation` — coberto por uma só entrada `content_renderer` no agregado (decisão "renderer único" da fase 03, ainda válida) |
| Base de dados | `ok`, `duration_ms≈0` (SQLite local) | `unavailable` (via mock — não recriei um cenário real de DB indisponível, ver §7) | `SELECT 1` trivial |
| Storage | **Não coberto pelo healthcheck** | N/A | Storage `local` não tem endpoint de saúde próprio nem dependência de rede — nada de útil a sondar sem um provider real (ver arquitectura §6, STG-PRE-003) |

---

## 4. Liveness vs. readiness (implementado)

| Aspecto | Antes | Depois (STG-PRE-006) |
|---|---|---|
| Liveness dedicada | Não existia (só `/api/v1/schema/` como proxy) | `GET /api/v1/system/health/live/`, público, não verifica nada |
| Readiness dedicada | Não existia | `GET /api/v1/system/health/ready/`, público, só DB; `200`/`503` |
| Diagnóstico operacional detalhado | `/api/v1/system/health/dependencies/`, staff-only | Inalterado — continua a única fonte de detalhe por dependência |

**Decisão de desenho (documentada, não escondida em código):** a readiness
**não** inclui IE/Content Renderer. Razão: são chamadas por-pedido, já
tratadas com erros claros (502/503) nos endpoints que as usam; incluir o seu
estado marcaria todo o serviço como "not ready" sempre que um deles caísse,
o que seria falso — a maior parte da API do Backend Core não depende deles.
Isto respeita explicitamente a regra "não confundir readiness com liveness"
e "não declarar readiness se só liveness passou" — a readiness aqui
**verifica algo real** (a base de dados), não é uma cópia da liveness.

`Asset`/`ContentPackRequest`/etc. — nenhuma alteração de contrato público
além da adição pura destes dois endpoints novos (aditivo, sem tocar em
nenhum endpoint existente).

---

## 5. Logs estruturados validados (com os três serviços reais)

| Evento | Confirmado? | Evidência |
|---|---|---|
| `intelligence.request_received` / `intelligence.request_completed` (IE) | ✅ | Já validado no Prompt 05; log a nível app com `request_id` |
| `event=report_created` (BC) | ✅ | `reports.views event=report_created report_id=... correlation_id=...` |
| `event=job_created` (BC) | ✅ | `integrations_bridge event=job_created ... status=queued request_id=...` |
| `event=job_submitted` (BC) | ✅ | `integrations_bridge event=job_submitted ... status=submitted request_id=...` |
| `event=callback_received` (BC) | ✅ | `integrations_bridge event=callback_received ... request_id=...` |
| `event=callback_processed` (BC) | ✅ | `integrations_bridge event=callback_processed ... status=completed request_id=...` |
| `event=job_submission_failed` / job failed (BC) | ✅ | `integrations_bridge event=job_submission_failed ... status=failed request_id=...` (Content Renderer parado de propósito) |
| `event=campaign_action_created` (BC) | ✅ | Já validado no Prompt 05 |
| `event=health_check overall=...` (BC) | ✅ | `integrations_bridge event=health_check overall=degraded intelligence_engine=unavailable content_renderer=ok database=ok` |

Todos os eventos partilham o mesmo `request_id`/`correlation_id` por
operação (herança directa do Prompt 05) — confirmando que a observabilidade
de falha tem a mesma qualidade de rastreio que a de sucesso.

---

## 6. Sinais operacionais confirmados (reais, não simulados só em teste)

| Sinal | Como foi validado | Resultado |
|---|---|---|
| **Erro IE down** | IE parado de propósito; chamada síncrona real `POST /campaigns/{id}/intelligence/` | `503` honesto (`"Campaign intelligence is temporarily unavailable."`), sem stacktrace; log `intelligence_call unavailable` + `error_type=IntelligenceEngineUnavailable` |
| **Erro Renderer down** | Content Renderer parado de propósito; `POST /reports/` real | `201` (o Report em si é sempre criado), mas fica `status=queued` honesto; `ExternalJobReference.status=failed`; log `event=job_submission_failed` |
| **Callback failed** | Coberto pelo cenário acima — a submissão falha antes de haver callback a processar (nunca há callback para um job que nem chegou a ser aceite) | Comportamento correcto: sem callback simulado nem falso sucesso |
| **DB unavailable** | Simulado **só via mock** (`monkeypatch` em `_check_database`) — não recriei uma falha real de SQLite/Postgres, ver §7 | `503` no `/ready/`, `unavailable` no agregado — testes automatizados cobrem isto |
| **Storage unavailable** | Não aplicável — storage `local` é filesystem, sem "serviço" a cair; nenhum provider de rede está em uso ainda (STG-PRE-003) | Documentado como N/A, não escondido |

---

## 7. Achado e correcção: latência do Intelligence Engine em Windows

**Diagnóstico:** `curl` directo a `http://127.0.0.1:8201/health` respondia em
~3ms; o mesmo `curl` a `http://localhost:8201/health` demorava **~2.1s**.
Confirmado com `socket.create_connection(('::1', 8201))` → timeout (nada
escuta em IPv6), enquanto o Content Renderer (Node, escuta dual-stack por
omissão) não sofre do mesmo problema. `urllib`/Python tenta os endereços
devolvidos por `getaddrinfo("localhost")` sequencialmente — a tentativa IPv6
falhada consome o timeout completo antes de recuar para IPv4.

**Impacto real (não só cosmético do healthcheck):** o mesmo atraso afecta a
chamada síncrona real do Backend Core ao Intelligence Engine
(`CampaignIntelligenceService`) sempre que o IE está em baixo — duplicando a
latência que um utilizador real experimentaria numa falha de IE.

**Correcção aplicada:**
- `backend_core/config/settings.py`: default de `INTELLIGENCE_ENGINE_BASE_URL`
  passou de `http://localhost:8201` para `http://127.0.0.1:8201` (comentário
  explicativo adicionado).
- `backend_core/.env.example`: mesmo valor, mesmo comentário.
- `docs/configuracao/portas_projeto.md`: actualizado (documento normativo).
- `backend_core/.env` (não versionado, ambiente de dev real): actualizado
  manualmente para validar a correcção em runtime.

**Validado antes/depois:**
| Cenário | Antes | Depois |
|---|---|---|
| Agregado, IE saudável | `duration_ms≈2000-2100` | `duration_ms≈40` |
| Agregado, endpoint completo | `real 2.1s` | `real 0.14s` |
| Chamada síncrona real `POST .../intelligence/` | não medido antes da correcção (mas sujeito ao mesmo mecanismo) | `real 0.16s` |

Não alterei `CONTENT_RENDERER_BASE_URL`/`REPORT_RENDERER_BASE_URL` — o
Content Renderer não sofre deste problema (confirmado por teste directo de
socket IPv6).

---

## 8. Ficheiros alterados/criados

| Ficheiro | Operação | Nota |
|---|---|---|
| `backend_core/apps/integrations_bridge/health.py` | alterado | `liveness_report()` e `readiness_report()` (novos, DB-only) |
| `backend_core/apps/integrations_bridge/views.py` | alterado | `SystemLivenessView`, `SystemReadinessView` (novos, `AllowAny`) |
| `backend_core/apps/integrations_bridge/urls.py` | alterado | rotas `/system/health/live/` e `/system/health/ready/` |
| `backend_core/apps/integrations_bridge/tests/test_dependency_health.py` | alterado | 3 testes corrigidos (literais de porta → `settings.*_BASE_URL`); +9 testes novos (liveness/readiness) |
| `backend_core/config/settings.py` | alterado | default de `INTELLIGENCE_ENGINE_BASE_URL` → `127.0.0.1` |
| `backend_core/.env.example` | alterado | mesmo default + comentário explicativo |
| `docs/configuracao/portas_projeto.md` | alterado | mesmo default + nota do achado |
| `backend_core/.env` (não versionado) | alterado | mesmo default, para validar em runtime real |
| `frontend/docs/.../arquitectura_staging_pre_producao.md` | alterado | §9/§9.1 (liveness/readiness, achado de latência) e §10 (limites) |

Nenhum endpoint público existente foi removido ou teve o contrato alterado —
só adições.

---

## 9. Validações executadas

| Validação | Resultado |
|---|---|
| `python manage.py check` | ✅ 0 issues |
| `pytest apps/integrations_bridge` | ✅ 176/176 |
| `pytest apps/integrations_bridge apps/campaigns apps/core` | ✅ 273 passed, 1 failed (o único restante, `test_intelligence_payload.py`, já reportado numa tarefa separada `task_1d40d090`, sem relação com health/logs) |
| Healthchecks HTTP reais dos 3 serviços | ✅ (§2) |
| Health agregado com JWT staff real | ✅ (§2) — `is_staff` foi activado temporariamente no utilizador de dev `ca014-dev@example.local` só para esta validação e **revertido no fim** (`is_staff=False`), para não interferir com testes de RBAC de prompts futuros (STG-PRE-008) |
| Smoke de falha controlada (IE down, Renderer down) | ✅ real, não simulado (§6/§7) |
| Greps de logs (`X-Internal-Token`, `Authorization`, `Bearer`, `password`, `private_key`, `api_key`) em todos os logs reais desta sessão | ✅ 0 ocorrências |
| Greps de segredos nos ficheiros alterados | ✅ 0 ocorrências reais (só placeholders já validados em prompts anteriores) |
| `scripts/check-forbidden-ports.ps1` | ✅ OK |

---

## 10. Lacunas de observabilidade restantes

- **Agregação/retenção central de logs** continua inexistente — cada serviço
  só escreve para o seu próprio stdout/consola (decisão pendente, fora do
  escopo desta fase — ver arquitectura §11).
- **Storage não tem healthcheck** — aceitável hoje (storage `local`, sem
  dependência de rede a sondar); passa a ser relevante quando um provider
  real for escolhido (STG-PRE-003).
- **DB unavailable só simulado via mock**, não recriado de facto (parar um
  servidor PostgreSQL real seria mais representativo, mas arriscado/
  desnecessário para SQLite local — não há "servidor" a parar). O
  comportamento do código (`_check_database` nunca levanta excepção) já dá
  confiança suficiente; os testes cobrem o caminho de falha.
- **Latência residual de ~2s por tentativa em conexões IPv4 recusadas** neste
  Windows específico (observada quando o Content Renderer estava
  completamente parado) — parece ser uma característica do stack de
  rede/firewall desta máquina, não do código; não investigada mais a fundo
  por estar fora do controlo do repositório. Vale a pena revisitar se o
  mesmo padrão aparecer numa staging real (Linux).

---

## 11. Riscos

| Risco | Severidade | Estado |
|---|---|---|
| Latência dobrada em chamadas reais ao IE quando este está em baixo (Windows) | Alto (antes de corrigido) | **Mitigado** — default corrigido, validado em runtime |
| Testes do healthcheck agregado silenciosamente não exercitavam o caminho de falha | Alto (já presente antes desta fase) | **Mitigado** — corrigido e reforçado (URLs derivadas de `settings`, não literais) |
| Readiness a confundir-se com liveness ou a marcar "not ready" por dependências opcionais | Médio | **Mitigado** — desenho explícito e documentado (§4) |
| Falta de agregação central de logs dificultar diagnóstico em staging real com múltiplos hosts | Médio | Presente, fora do escopo desta fase |

---

## 12. Próximo passo recomendado

Avançar para **Prompt 07 (STG-PRE-007 — Alinhar estados de artefacto e
job)**: mapear as transições de `Report`/`MediaKit`/`ContentPackRequest`/
`ContentOutput`/`ExternalJobReference` e decidir como tornar mais explícita
a divergência já observada nesta e nas fases anteriores (artefacto `queued`/
`draft` honesto quando o job falha) — os logs e o correlation-id agora
disponíveis tornam este mapeamento mais fácil de confirmar empiricamente.
