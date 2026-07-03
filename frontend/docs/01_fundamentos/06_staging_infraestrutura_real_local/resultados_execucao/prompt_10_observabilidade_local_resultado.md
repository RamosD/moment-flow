# Prompt 10 — Observabilidade local — Resultado

**Data:** 2026-07-03
**Fase:** `06_staging_infraestrutura_real_local` (STG-LOCAL-010)
**Âmbito:** validar observabilidade local — logs, healthchecks, correlation-id ponta-a-ponta — na stack com PostgreSQL e MinIO. Sem stack pesada de logs, sem registar payload integral de intelligence.
**Estado de execução:** `executado` — destino de logs definido e documentado (incluindo um achado real: Django escreve em stderr, não stdout), correlation-id rastreado com sucesso através de um fluxo real completo (27 linhas Backend Core, 2 Intelligence Engine, 27+ Content Renderer), 5 cenários de falha testados contra a stack real (IE down, Content Renderer down, MinIO down, PostgreSQL down, callback com token errado), **um achado real de risco não-trivial identificado** (pedidos normais à BD não têm timeout curto, ao contrário do `/ready/`).

---

## 1. Nota sobre o Prompt 08 (E2E local)

Esta iteração assume que **STG-LOCAL-008 (E2E local) continua por
executar** — não foi pedido nem executado nesta sessão. O fluxo "real" da
tarefa 4 (intelligence → CampaignAction → Report → MediaKit →
ContentPackRequest → callback) foi validado por chamadas HTTP directas
contra a stack activa (o mesmo padrão já usado nos Prompts 03/04/05/09),
não pelo Playwright. Isto é suficiente para os objectivos desta iteração
(observabilidade), mas **não substitui** o STG-LOCAL-008, que continua
pendente.

## 2. Ambiente usado

Infraestrutura Docker (containers já existentes, encontrados **parados**
no arranque desta iteração — `docker ps -a` mostrava os três containers
`Exited` há 6 horas, provavelmente um restart do Docker Desktop; recriados
com `docker compose up -d` sem perda de dados, volumes intactos) + 4
processos aplicacionais (reaproveitados de sessões anteriores + reiniciados
pontualmente durante os testes de falha desta iteração).

## 3. Destino dos logs locais (tarefa 1)

| Serviço | Destino | Nota |
|---|---|---|
| Backend Core | `.local-runtime\logs\backend_core.err.log` | **Achado real**: o Django `runserver` escreve os seus logs (incluindo os loggers estruturados de `integrations_bridge`, `campaigns.intelligence`, etc.) em **STDERR**, não STDOUT — `backend_core.out.log` estava vazio (0 bytes) apesar do serviço estar activo e a processar pedidos há horas. Não é um bug dos scripts desta fase (`apps-up.ps1` já redirecciona ambos os fluxos correctamente); é comportamento por desenho do próprio `runserver`. Documentado no runbook (§8.2) para que ninguém perca tempo a assumir "sem logs" ao olhar só para o `.out.log`. |
| Intelligence Engine | `.local-runtime\logs\intelligence_engine.out.log` | JSON estruturado, uma linha por evento, via stdout normal |
| Content Renderer | `.local-runtime\logs\content_renderer.out.log` | idem |
| Frontend | `.local-runtime\logs\frontend.out.log` | Só arranque/HMR do Vite |
| PostgreSQL | `docker logs chartrex_staging_postgres` | Sem persistência em ficheiro adicional nesta fase |
| MinIO | `docker logs chartrex_staging_minio` | idem |

Nenhuma stack pesada foi criada (sem Elasticsearch/Grafana/Loki/etc.) —
mecanismo simples, consistente com a premissa obrigatória.

## 4. Retenção (tarefa 2)

Manual, sem rotação automática. Ficheiros em `.local-runtime\logs\` são
**substituídos** (não acrescentados indefinidamente) a cada arranque via
`staging-local-apps-up.ps1`; limpeza manual documentada
(`Remove-Item .local-runtime\logs\*.log -Force`). `docker logs` segue a
retenção default do driver `json-file` do Docker — aceitável para staging
local de curta duração, explicitamente não para produção.

## 5. Correlation-id — fluxo real rastreado (tarefas 3, 4, 5)

Executado um fluxo completo com um `X-Request-ID` próprio
(`obs-trace-stg-local-010-<timestamp>`) enviado em todos os pedidos:

```text
1. POST /campaigns/{id}/intelligence/          → Backend Core → Intelligence Engine (síncrono, real, source=engine)
2. POST /campaign-actions/ (manual_task)        → Backend Core
3. POST /reports/                                → Backend Core → Content Renderer → MinIO → callback
4. POST /media-kits/                             → idem
5. POST /content-pack-requests/                  → idem (2 outputs)
```

**Resultado do rastreio** (mesmo `X-Request-ID`/`correlation_id` em todos):

| Serviço | Ocorrências do id | Eventos observados |
|---|---|---|
| Backend Core (`backend_core.err.log`) | **27** | `intelligence_call start/ok`, `campaign_action_created`, `report_created`, `job_created`/`job_submitted` ×3, `media_kit_created`, `content_pack_request_created`, `callback_received`/`callback_processed` ×3 |
| Intelligence Engine (`intelligence_engine.out.log`) | **2** | `intelligence.request_received`, `intelligence.request_completed` |
| Content Renderer (`content_renderer.out.log`) | **27+** | `job.accepted`/`job.scheduled`/`render.started`/`*.render_finished`/`render.completed`/`callback.*` para os 3 jobs |

Todos os três artefactos terminaram com o mesmo `correlation_id` na base
de dados (`Report.correlation_id`, `MediaKit.correlation_id`,
`ContentPackRequest.correlation_id`), confirmando que o id sobrevive desde
o pedido HTTP inicial até ao registo final persistido — **nenhuma perda de
correlation-id em nenhum ponto do fluxo**.

Confirmado por download real: os 4 objectos (`report.pdf`, `media_kit.pdf`,
2× `output_*.png`) existem no bucket MinIO sob
`workspaces/<ws>/jobs/<job_id>/`, com os `job_id` correspondentes aos
`external_job_id` vistos nos logs.

**Confirmado também: o payload integral de intelligence não é
registado** — os logs do Intelligence Engine só têm `request_received`/
`request_completed` com `request_id`/`workspace_id`; nenhum `score`,
`recommendation` ou `moment` aparece em nenhum log de nenhum dos três
serviços (grep dedicado, ver §7).

## 6. Falhas locais testadas (tarefa 6)

| Cenário | Método | Resultado observado | Sinal de log |
|---|---|---|---|
| **Intelligence Engine down** | Processo parado, chamada de intelligence real | `503`, `{"detail":"Campaign intelligence is temporarily unavailable..."}`, correlation-id preservado | `WARNING integrations_bridge.client internal_call unavailable` → `WARNING campaigns.intelligence intelligence event=unavailable ... error_type=IntelligenceEngineUnavailable duration_ms=4613` |
| **Content Renderer down** | Processo parado, `POST /reports/` | `201` (o *recurso* Report é criado), `status="failed"`, `metadata.error="External service is unavailable."` | `WARNING integrations_bridge event=job_submission_failed` |
| **MinIO down** | `docker compose stop minio`, `POST /reports/` | `201` inicial (`queued`), job aceite (`202`) pelo Content Renderer, depois `status="failed"` — o Content Renderer aceita o job e só falha ao tentar gravar no storage | Content Renderer: `render.completed status=failed` → `callback.completed status=failed` |
| **PostgreSQL down** | `docker compose stop postgres` | `/live/` continua `200` (correcto — não depende de BD); `/ready/` falha rápido `503`; **um pedido normal que lê a BD (`GET /workspaces/`) ficou pendurado >2 minutos** sem responder, sem erro — teve de ser interrompido manualmente | `/ready/`: `psycopg.errors.ConnectionTimeout: connection timeout expired` (rápido, por desenho). O pedido normal nunca produziu nenhuma linha de log — nem sucesso nem erro — até ser interrompido |
| **Callback com token errado** | `POST /internal/jobs/callback/` com `X-Internal-Token` inválido | `403`, `{"detail":"Invalid or missing internal token."}` | `WARNING integrations_bridge event=callback_rejected reason=invalid_token` — **valor do token nunca aparece no log** (confirmado por grep dedicado) |

Todos os serviços parados foram reiniciados a seguir e a recuperação
confirmada (`GET /workspaces/` voltou a responder `200` com dados reais
depois do PostgreSQL voltar; `/ready/` voltou a `200`).

### 6.1 Achado real: pedidos normais à BD não têm timeout curto

Ao contrário de `/ready/` (que usa
`HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS`, curto e configurado, e por isso
falha em segundos), um pedido normal que lê a base de dados
(`GET /api/v1/workspaces/`) **não tem nenhuma protecção equivalente** — a
ligação Django→PostgreSQL "normal" não define um `connect_timeout` curto.
Com o PostgreSQL parado, o pedido ficou pendurado sem resposta durante mais
de 2 minutos (interrompido manualmente; o tempo real até falhar
naturalmente não foi medido, mas ultrapassa largamente o que seria
aceitável para diagnóstico operacional). Isto significa que, num cenário
real de PostgreSQL em baixo, o sintoma para um operador não seria "erro
claro" mas sim "a aplicação parece pendurada" — só o `/ready/` dedicado dá
sinal rápido. Documentado no runbook (§8.2) como instrução de diagnóstico:
verificar sempre `/ready/` primeiro perante um pedido pendurado.

Este achado é registado como **risco documentado**, não corrigido nesta
iteração — corrigir exigiria alterar a configuração `DATABASES` do
Backend Core (`config/settings.py`, ex.: adicionar `options:
{"connect_timeout": N}` aos parâmetros de ligação Postgres), o que é uma
alteração de código de produto fora do âmbito de uma iteração de
observabilidade (que audita e documenta, não corrige comportamento de
runtime salvo achados de segurança — ver critério do Prompt 09, não deste).

## 7. Greps executados (tarefa 7)

| Grep | Âmbito | Resultado |
|---|---|---|
| `Authorization: Bearer <valor>`, `X-Internal-Token: <valor>`, `password[:=]<valor>`, `private_key`, `api_key` | `.local-runtime\logs\{backend_core,intelligence_engine,content_renderer,frontend}.{out,err}.log` (8 ficheiros) | ✅ 0 ocorrências |
| `password\|secret\|token` | `docker logs chartrex_staging_postgres` / `chartrex_staging_minio` (log completo) | ✅ 0 ocorrências |
| Valor literal do token errado usado no teste de callback (§6) | `backend_core.err.log` | ✅ 0 ocorrências — confirma que mesmo um token **incorrecto** submetido por um atacante/erro não fica registado |
| `recommendations`, `campaign_readiness_score`, `moments` (payload integral de intelligence) | `backend_core.err.log`, `intelligence_engine.out.log` | ✅ 0 ocorrências — confirma a regra "não registar payload integral de intelligence" |
| `scripts/check-forbidden-ports.ps1` | repositório | ✅ OK |

**`E2E_PASSWORD` nunca impresso** nesta iteração.

## 8. Runbook actualizado (tarefa 8)

`runbook_staging_local.md` — nova secção **8.2 "Observabilidade local"**:
onde consultar logs de cada serviço (incluindo o achado stderr/stdout do
Django), retenção/limpeza, como seguir uma operação por correlation-id
(com exemplo `Select-String`), como diagnosticar MinIO e PostgreSQL. Secção
**9 "Troubleshooting"** ganhou 5 novas linhas cobrindo exactamente os 5
cenários de falha testados no §6 deste relatório (sintoma real → causa →
resolução, não hipotético).

## 9. Lacunas

- Timeout curto para ligações Django→PostgreSQL "normais" (não só o
  `/ready/`) — achado documentado (§6.1), não corrigido (fora do âmbito de
  observabilidade).
- Sem agregação central de logs entre os 3 serviços — consulta é sempre
  por ficheiro/serviço individual (`Select-String`/`grep`), nunca uma
  vista unificada. Aceitável para staging local de um único operador,
  explicitamente fora do âmbito ("não criar stack pesada").
- `docker logs` sem rotação/limite configurado explicitamente — herda o
  default do Docker, não uma decisão desta fase.
- Retenção dos ficheiros `.local-runtime\logs\*.log` é "substituição no
  próximo arranque", não uma política formal de rotação por tamanho/tempo.

## 10. Riscos

| Risco | Severidade | Estado |
|---|---|---|
| Pedidos à BD sem timeout curto mascaram uma falha real de PostgreSQL como "aplicação lenta/pendurada" | **Médio-Alto** | Documentado (§6.1) e no runbook; não corrigido — decisão consciente de não alterar `config/settings.py` numa iteração de observabilidade |
| Ficheiros de log locais podem crescer sem limite dentro de uma única sessão longa | Baixo | Aceitável para staging local; limpeza manual documentada |
| Ausência de agregação central dificulta correlacionar eventos entre serviços sem saber já o correlation-id à partida | Baixo | Mitigado pela disciplina de sempre gerar/propagar `X-Request-ID` explicitamente nos smoke tests e (quando existir) no E2E |
| MinIO down é diagnosticável (log claro), mas só depois de o job já ter sido aceite — não há verificação prévia de conectividade ao storage antes de aceitar o job | Baixo | Comportamento de produto, não de observabilidade — fora do âmbito desta iteração |

## 11. Próximo passo recomendado

Avançar para **STG-LOCAL-008** (E2E local, ainda pendente desta pipeline):
correr `pnpm test:e2e` real contra a stack agora bem instrumentada
(correlation-id validado, troubleshooting documentado), o que deve tornar
qualquer falha do E2E mais rápida de diagnosticar usando exactamente os
mecanismos descritos neste relatório e no runbook §8.2. Considerar também,
fora desta fase, avaliar se o achado §6.1 (timeout de ligação à BD)
justifica uma correcção de produto — não decidido aqui, apenas registado.
