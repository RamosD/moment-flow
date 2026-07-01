# Painel de prontidão operacional — Ecossistema MomentFlow/ChartRex

> Visão objectiva e honesta do estado operacional ao fecho da fase
> **Observabilidade e Staging Técnico do Ecossistema** (OBS-STG-009).
>
> Estados usados: **ok** · **parcial** · **pendente** · **bloqueado** · **não
> aplicável**. Nenhuma validação não executada é apresentada como concluída —
> onde não houve execução real nesta fase, está marcado **"não executada"**
> explicitamente. **Nenhum valor real de secret** aparece neste documento.
>
> Fonte: [`01_backlog.md`](01_backlog.md),
> [`matriz_operacional_servicos.md`](matriz_operacional_servicos.md),
> [`runbook_arranque_staging.md`](runbook_arranque_staging.md),
> [`checklist_troubleshooting.md`](checklist_troubleshooting.md) e os
> relatórios `resultados/prompt_01`…`prompt_08`.
> Data: 2026-06-25.

---

## 1. Estado dos serviços

| Serviço | Estado | Evidência |
|---|---|---|
| `backend_core` | **ok** (funcional) | Suite de testes própria a passar (ver §3); endpoint agregado e management commands operacionais (código + testes, sem mocks no nível de teste de aceitação descritos abaixo). |
| `intelligence_engine` | **ok** (funcional, validado por loop real anterior) | Integração síncrona validada em fase anterior (`estado_integracao_intelligence_engine.md`, fora desta fase) — `RUN_REAL_IE=1` confirma `source=engine`/`status=completed`/6 chaves quando o IE está a correr (OBS-STG-004). |
| `content_renderer` | **ok** (funcional, validado por harness E2E anterior) | Harness `run-e2e-postgres.ps1` + `e2e_backend_core.py` (pré-existente, não recriado nesta fase) valida job→202→render→callback→asset com idempotência. |
| Execução simultânea dos três serviços **nesta sessão** | **não executada** | Nenhum processo (`runserver`/`uvicorn`/`npm run dev`) foi efectivamente arrancado durante OBS-STG-001…008; todas as evidências de loop real citadas são de validações anteriores a esta fase ou descritas nos guias como passos a executar manualmente (runbook §5–§8). |

---

## 2. Estado dos healthchecks

| Item | Estado | Evidência |
|---|---|---|
| `intelligence_engine` `GET /health` | **ok** | Endpoint público existente, confirmado por inspecção de código (`app/api/health.py`) em OBS-STG-001. **Não chamado ao vivo** nesta fase. |
| `content_renderer` `GET /health` | **ok** | Endpoint público existente, confirmado por inspecção de código (`src/http/routes.ts`) em OBS-STG-001. **Não chamado ao vivo** nesta fase. |
| `backend_core` — healthcheck agregado | **ok** (implementado e testado) | `GET /api/v1/system/health/dependencies/` (OBS-STG-003); 20 testes unitários/integração com mocks cobrindo ok/degraded/unavailable/misconfigured/timeout/resposta inválida/401/403/200 — **todos passados** (`pytest apps/integrations_bridge/tests/test_dependency_health.py -q` → 20 passed). Chamada real contra o IE/renderer **vivos** não foi executada nesta fase (validação automatizada é com mocks, não end-to-end). |
| `backend_core` — liveness próprio (sem auth) | **pendente** | Não existe `/health` público no `backend_core`; usa-se `GET /api/v1/schema/` como proxy documentado (runbook §5). Item já registado como pendência em OBS-STG-003/007. |

---

## 3. Estado dos smoke tests

| Item | Estado | Evidência |
|---|---|---|
| Smoke BC↔IE — existência e documentação | **ok** | Management command `smoke_intelligence_engine` (OBS-STG-004) + teste opt-in pré-existente `test_intelligence_real_loop.py`; documentado em [`smoke_intelligence_engine.md`](smoke_intelligence_engine.md). |
| Smoke BC↔IE — execução real nesta fase | **não executada** | Os testes do command em si (validação de config, mocks de cliente) passaram (`pytest apps/campaigns/tests/test_smoke_intelligence_command.py -q`); a chamada real ao IE **a correr** (`RUN_REAL_IE=1`) não foi disparada durante esta fase — os 3 testes opt-in aparecem como `skipped` em todas as execuções de suite completa registadas (ex.: prompt_06: "243 passed, 3 skipped"). |
| Smoke BC↔Renderer — existência e documentação | **ok** | Management command `smoke_content_renderer` (OBS-STG-005, perna de saída) + harness E2E pré-existente (`run-e2e-postgres.ps1`) documentado como Camada 2; documentado em [`smoke_content_renderer.md`](smoke_content_renderer.md). |
| Smoke BC↔Renderer — execução real nesta fase | **não executada** | Os testes do command (`test_smoke_content_renderer_command.py`, mocks) passaram; o harness E2E real (que exige Docker/PostgreSQL e os processos a correr) **não foi executado** durante OBS-STG-001…008. |
| Tratamento de falha (serviço desligado) | **ok** (verificado por testes/código, não ao vivo) | Ambos os commands têm mensagens de erro controladas e testadas (mocks) para indisponibilidade/timeout/token desalinhado; comportamento confirmado por leitura de código + testes unitários, não por desligar um processo real nesta fase. |

---

## 4. Estado dos logs / correlação

| Item | Estado | Evidência |
|---|---|---|
| `request_id` no fluxo BC→IE | **ok** | Já existia antes desta fase (`campaigns.intelligence`, `integrations_bridge.intelligence`); confirmado por inspecção + testes `caplog` existentes. |
| `job_id`/`request_id` no fluxo BC→Renderer | **ok** | Já existia antes desta fase (`integrations_bridge.client`, `log_job_event`). |
| `external_job_id` na correlação de jobs/callback | **ok** (adicionado nesta fase) | `job_log_fields()` passou a incluir `external_job_id` (OBS-STG-006); 9 testes novos a passar. |
| Visibilidade efectiva dos logs INFO (`LOGGING` do Django) | **ok** (corrigido nesta fase) | `config/settings.py` define agora `LOGGING` (handler de consola, nível por `LOG_LEVEL`); validado com `getEffectiveLevel()` (`20`) via teste parametrizado e via comando manual documentado no runbook/checklist. |
| Ausência de token nos logs | **ok** | Testes explícitos em várias suites (`test_token_like_extra_is_dropped` e outros `caplog`-based ao longo da fase) confirmam que tokens nunca aparecem; redacção por `_FORBIDDEN_KEYS` mantida. |
| `duration_ms` no fluxo de jobs do renderer | **pendente** | Presente no fluxo IE; **não** adicionado ao log de submissão de jobs do renderer — limitação documentada explicitamente em OBS-STG-006 (fora do âmbito mínimo). |
| `workspace_id` no logger de transporte de baixo nível (`integrations_bridge.client`) | **parcial** | Ausente nesse logger específico, mas presente na linha `log_job_event` que acompanha o mesmo evento — correlação continua possível, só não nesse logger isolado. |
| Formato uniforme entre os três serviços | **parcial** | Backend Core emite `key=value`; IE e renderer emitem JSON. Os ids propagam-se (correlação manual é possível), mas não há agregação automática entre formatos — deliberadamente fora do escopo MVP (backlog §4.2: sem ELK). |
| Correlação validada **ao vivo**, entre processos reais, nesta fase | **não executada** | A validação de correlação foi feita por testes automatizados (`caplog`, mocks) dentro do `backend_core`; não foi feita uma captura de logs simultânea dos três processos reais a correr. |

---

## 5. Estado da segurança de secrets

| Item | Estado | Evidência |
|---|---|---|
| Tokens nunca em logs | **ok** | Redacção activa nos três serviços (Django: `_FORBIDDEN_KEYS`; IE e renderer: redacção recursiva por padrão de chave). Confirmado por testes dedicados em várias fases (`test_token_like_extra_is_dropped`, testes do IE↔BC anteriores). |
| Tokens nunca em documentação desta fase | **ok** | Todos os documentos criados (matriz, runbook, guias de smoke, checklist, este painel) usam exclusivamente placeholders (`<DEV_TOKEN>`, `<INTERNAL_API_TOKEN>`, `<ACCESS_TOKEN>`, …); confirmado por inspecção visual em cada prompt. |
| Guardas de arranque fail-fast (token vazio) | **ok** | Já existentes antes desta fase: Django (`_require_secure_intelligence_engine_config`), IE (`config_error` em `production`), Renderer (rejeita salvo `ALLOW_INSECURE_EMPTY_TOKEN=true` em dev). Confirmados por inspecção de código em OBS-STG-001. |
| Mesmo `INTERNAL_API_TOKEN` exigido nos três serviços | **ok** (por desenho, documentado) | Regra documentada na matriz e no runbook; **não** validada ao vivo nesta fase (exigiria os três processos a correr). |
| Gestão de secrets em staging real (cofre, rotação) | **pendente** | Fora do escopo desta fase (backlog §4.2); `.env` git-ignored é a única prática actual. |

---

## 6. Estado da documentação operacional

| Documento | Estado |
|---|---|
| Matriz operacional (`matriz_operacional_servicos.md`) | **ok** — criada e mantida actualizada ao longo da fase (OBS-STG-002, com edições em 003/004/005/006/007/008) |
| Runbook de arranque (`runbook_arranque_staging.md`) | **ok** — criado em OBS-STG-007 |
| Checklist de troubleshooting (`checklist_troubleshooting.md`) | **ok** — criado em OBS-STG-008, 16 casos |
| Guias de smoke (`smoke_intelligence_engine.md`, `smoke_content_renderer.md`) | **ok** — criados em OBS-STG-004/005 |
| Painel de prontidão operacional (este documento) | **ok** — criado em OBS-STG-009 |
| Documento de estado final da fase (`estado_observabilidade_staging_ecossistema.md`) | **pendente** — previsto para OBS-STG-010 |

---

## 7. Blockers de produção

Estes itens **bloqueiam** a passagem a produção (não bloqueiam o piloto técnico
controlado — ver §9/§10):

| # | Blocker | Estado | Nota |
|---|---|---|---|
| B1 | Sem observabilidade real (métricas/tracing/alertas) | **bloqueado** | Deliberadamente fora do escopo desta fase (backlog §4.2: sem Prometheus/Grafana/OTel/ELK). |
| B2 | Sem logs centralizados | **bloqueado** | Logs ficam na consola de cada processo; sem agregação cross-serviço. |
| B3 | Storage do renderer é local (MVP), sem S3/R2 | **bloqueado** | Confirmado em todas as fases anteriores; fora do escopo desta fase (backlog §13.3). |
| B4 | Scores/grades/recomendações do IE são heurísticos, não calibrados | **bloqueado** | Fora do escopo desta fase (backlog §13.4) — é validação de diagnóstico operacional, não de valor de negócio. |
| B5 | Sem staging contínuo / pipeline de deploy | **bloqueado** | Fora do escopo desta fase (backlog §4.2: sem CI/CD completo, sem Kubernetes). |
| B6 | Gestão segura de secrets (cofre/rotação) em staging/produção | **bloqueado** | Hoje só `.env` git-ignored; sem rotação nem cofre. |
| B7 | Discrepância de porta do report renderer (G9) — corrigida na padronização de portas | **resolvido** | `CONTENT_RENDERER_BASE_URL` e `REPORT_RENDERER_BASE_URL` apontam agora ambas para `:8202` por defeito no código. O workaround manual deixou de ser necessário. |
| B8 | Healthcheck agregado e smoke tests nunca executados contra processos reais nesta fase | **pendente** | Ver §2/§3 — a cobertura automatizada (mocks/testes unitários) é sólida, mas falta a confirmação operacional "ao vivo" antes de qualquer piloto real. |

---

## 8. Riscos em aberto

| ID | Risco | Estado |
|---|---|---|
| OBS-RSK-007 (backlog) | Validação real (3 serviços simultâneos) nunca executada nesta fase — só documentada como executável | **em aberto** — mitigação: runbook + guias de smoke deixam o caminho pronto a executar; falta a execução em si. |
| G9 (matriz) | Discrepância de porta do report renderer (8003 vs 8002) | **resolvido** — ambos `CONTENT_RENDERER_BASE_URL` e `REPORT_RENDERER_BASE_URL` defaultam agora para `:8202` no código. |
| Heterogeneidade de formato de log entre serviços | **em aberto** — aceitável para o âmbito MVP desta fase (sem agregação automática); revisitar se uma stack de observabilidade real for introduzida no futuro. |
| Falta de liveness público (sem auth) no `backend_core` | **em aberto** — mitigado por `GET /api/v1/schema/` como proxy; um probe de infra dedicado pode precisar de um endpoint próprio. |
| Caso 4/Caso 6 da checklist (falha interna do IE / callback sem chegar) dependem de inspecção de código fora do escopo desta fase | **em aberto** — diagnóstico do lado do Backend Core está documentado; causa raiz dentro do IE/renderer fica fora desta fase por desenho (backlog §5.2.8). |

---

## 9. Decisão de prontidão — Piloto técnico controlado

**Estado: PRONTO para piloto técnico controlado**, com as ressalvas explícitas
abaixo.

Critérios cumpridos:

- Os três serviços são funcionais e têm integrações já validadas em loops reais
  (IE↔BC e BC↔Renderer), ainda que essas validações específicas sejam de fases
  anteriores a esta, não repetidas ao vivo dentro de OBS-STG-001…009.
- Existe healthcheck agregado testado (com mocks) para diagnóstico rápido de
  disponibilidade.
- Existem smoke tests documentados e testados (com mocks) para os dois loops
  principais, prontos para execução manual contra processos reais.
- Existe runbook de arranque e checklist de troubleshooting accionáveis por
  alguém sem conhecimento do código.
- A correlação de logs por `request_id`/`job_id`/`external_job_id`/`workspace_id`
  está implementada e testada; tokens nunca aparecem em logs nem documentação.
- Nenhum secret real foi exposto em nenhum artefacto desta fase.

**Ressalva explícita:** esta prontidão assume que, **antes de qualquer piloto
real**, alguém executa de facto o runbook (§5–§8) e os dois smoke tests contra
os três serviços a correr simultaneamente — passo que esta fase **deixou
pronto a executar, mas não executou** (ver B8/§3). Recomenda-se tratar essa
execução como o primeiro passo do piloto, não como opcional.

---

## 10. Decisão de prontidão — Produção

**Estado: NÃO PRONTO para produção.**

Motivos explícitos (blockers B1–B6 de §7, todos fora do escopo desta fase por
desenho do backlog §4.2/§13):

- Sem observabilidade real (métricas, tracing distribuído, alertas).
- Sem centralização de logs.
- Storage do renderer é local (MVP), sem S3/R2.
- Scores/recomendações do IE são heurísticos, sem calibração de negócio.
- Sem staging contínuo nem pipeline de deploy/CI-CD.
- Sem gestão segura de secrets (cofre/rotação) — hoje apenas `.env` git-ignored.

Esta fase entrega **apenas** a camada mínima de operação (healthchecks, smoke
tests, runbook, troubleshooting, logs mínimos) — exactamente o que o backlog
definiu como objectivo (§1/§14), e não pretende, nem deve ser lida como,
prontidão para produção.

---

## 11. Resumo executivo (uma linha por dimensão)

| Dimensão | Estado |
|---|---|
| Serviços | ok (funcionais; execução simultânea real nesta fase não executada) |
| Healthchecks | ok (agregado testado); liveness público do BC pendente |
| Smoke tests | ok (documentados e testados com mocks); execução real nesta fase não executada |
| Logs/correlação | ok (campos e visibilidade corrigidos); duration_ms do renderer e formato uniforme pendentes/parciais |
| Segurança de secrets | ok |
| Documentação operacional | ok (estado final da fase pendente — OBS-STG-010) |
| Blockers de produção | bloqueado (6 itens, todos deliberadamente fora do escopo) |
| **Piloto técnico controlado** | **PRONTO** (com a ressalva de §9) |
| **Produção** | **NÃO PRONTO** |

---

## 12. Referências

- Backlog da fase: [`01_backlog.md`](01_backlog.md)
- Matriz operacional: [`matriz_operacional_servicos.md`](matriz_operacional_servicos.md)
- Runbook: [`runbook_arranque_staging.md`](runbook_arranque_staging.md)
- Checklist de troubleshooting: [`checklist_troubleshooting.md`](checklist_troubleshooting.md)
- Relatórios da fase: `resultados/prompt_01_analise_estado_operacional.md` …
  `resultados/prompt_08_checklist_troubleshooting.md`
