# Prompt 06 — Observabilidade mínima

**Data:** 2026-07-01
**Fase:** `04_staging_campaign_actions_with_real_ie_renderer` (STG-CA-006, Incremento 2)
**Âmbito:** rastreabilidade `request_id`/`job_id` na cadeia Frontend → Backend Core → IE/Renderer, sem exposição de secrets. Sem alteração de código de produto.
**Estado de execução:** `executado`

---

## 1. Resumo objectivo

Foi gerado um fluxo fresco correlacionado (intelligence → CampaignAction → report → job → callback) e inspeccionados os logs dos três serviços.

- **Rastreabilidade presente:** `request_id` no Backend Core (IE e renderer), `job_id` correlacionado BC↔CR, `campaign_id`/`workspace_id` transversais.
- **Sem secrets:** greps por token/Authorization/Bearer/password/private_key/api_key nos três logs → **0 correspondências**.
- **Sem payload integral do IE:** greps por analysis/scores/recommendations/grade/summary/action → **0 correspondências**.
- **Erros 503 seguros:** mensagem honesta, sem stacktrace nem internals.
- **Lacuna real (não mascarada):** não existe **um** correlation-id único ponta-a-ponta; cada subsistema gera o seu `request_id`. A criação de CampaignAction e de artefactos não emite `request_id` em log. IE não regista o `request_id` recebido nos seus logs (só uvicorn access).

---

## 2. IDs rastreados (fluxo fresco, stamp=224340)

| Entidade | ID |
|---|---|
| campaign_id | `30930999-5cd3-47d8-afb0-2c218084ed7d` |
| workspace_id | `46ca02a0-edcf-4835-8878-a6ff24b41598` |
| intelligence request_id | `7457594660dd4839aa66664996fa4fc0` |
| CampaignAction (manual_task) | `c08f0745-0ccc-4250-ae0e-ca192c78b595` |
| CampaignAction (report_request) | `cf529198-f6ef-449e-b07a-7861bc1d7b55` |
| artifact (Report) | `19b77cfb-44dc-4482-8b80-5e7e73d64549` |
| job_id (report_generation) | `f2da9e53-c8a6-42c8-80f0-48dd87560d75` |
| job request_id (BC↔CR) | `19829d283c9543ba9cb49cbc7bc15051` |

**Nota crítica:** o `request_id` da intelligence (`7457…`) **≠** o `request_id` do job (`19829…`). São gerados independentemente (o job gera o seu em `create_and_submit_external_job`). A correlação ponta-a-ponta faz-se por `campaign_id` + `workspace_id` (+ `job_id` na parte do renderer), não por um `request_id` único.

---

## 3. Correlação mínima confirmada (tarefa 5)

| Chave | Onde aparece | Correlaciona? |
|---|---|---|
| `campaign_id` | intelligence (BC), job_created/callback (BC) | ✅ transversal |
| `workspace_id` | BC (todos), CR (todos) | ✅ transversal |
| `job_id` | BC (job_created→submitted→callback), CR (accepted→render→callback) | ✅ BC↔CR |
| `request_id` (job) | BC ↔ CR (mesmo valor `19829…`) | ✅ BC↔CR |
| `request_id` (intelligence) | BC (intelligence_call) | ⚠️ só BC (IE não o regista) |
| `action_id` | resposta da API | ⚠️ sem log de criação |
| `artifact_id` | BC job logs? (não) / resposta API | ⚠️ sem log dedicado |

---

## 4. Amostras redigidas de logs

### 4.1 Backend Core — intelligence (síncrono)
```
INFO integrations_bridge.intelligence intelligence_call start request_id=7457…4fc0 workspace_id=46ca02a0…
INFO integrations_bridge.client       internal_call start job_id=None request_id=7457…4fc0 url=http://localhost:8201/intelligence/campaign
INFO integrations_bridge.client       internal_call ok    job_id=None request_id=7457…4fc0 status=200
INFO campaigns.intelligence           intelligence event=ok request_id=7457…4fc0 workspace_id=46ca02a0… campaign_id=30930999… status=completed duration_ms=2066
```

### 4.2 Backend Core — renderer job + callback
```
INFO integrations_bridge event=job_created   job_id=f2da9e53… job_type=report_generation provider=report_renderer status=queued    request_id=19829…5051
INFO integrations_bridge.client internal_call start job_id=f2da9e53… request_id=19829…5051 url=http://localhost:8202/jobs/
INFO integrations_bridge.client internal_call ok    job_id=f2da9e53… request_id=19829…5051 status=202
INFO integrations_bridge event=job_submitted job_id=f2da9e53… status=submitted request_id=19829…5051
INFO integrations_bridge event=callback_received  job_id=f2da9e53… status=submitted request_id=19829…5051
INFO integrations_bridge event=callback_processed job_id=f2da9e53… status=completed request_id=19829…5051
"POST /api/v1/internal/jobs/callback/ HTTP/1.1" 200
```

### 4.3 Content Renderer — job/render/callback
```
job.accepted        job_id=f2da9e53… workspace_id=46ca02a0… request_id=19829…5051 job_type=report_generation
render.started      job_id=f2da9e53… request_id=19829…5051
report.render_finished status=completed format=pdf fallback_html=false file_size_bytes=1142
render.completed    status=completed outputs=1
callback.attempt_started callback_url=http://localhost:8100/api/v1/internal/jobs/callback/ attempt=1 max_attempts=3
callback.completed  http_status=200 attempts=1
```

### 4.4 Intelligence Engine
```
{"level":"info", "msg":"127.0.0.1:62328 - \"POST /intelligence/campaign HTTP/1.1\" 200", "service":"intelligence_engine", "logger":"uvicorn.access"}
```
Só uvicorn access (200). O IE **não** emite log app-level com o `request_id` recebido nem com o resultado — ver lacunas.

### 4.5 Erro 503 (IE indisponível)
Resposta ao cliente:
```json
{ "detail": "Campaign intelligence is temporarily unavailable. Try again later." }
```
Log Backend Core (redigido):
```
WARNING integrations_bridge.intelligence intelligence_call unavailable request_id=3240…46eb workspace_id=46ca02a0…
WARNING integrations_bridge.intelligence intelligence_call retry request_id=3240…46eb attempt=1 of=2 reason=IntelligenceEngineUnavailable
WARNING campaigns.intelligence intelligence event=unavailable request_id=3240…46eb campaign_id=30930999… error_type=IntelligenceEngineUnavailable duration_ms=8706
Service Unavailable: /api/v1/campaigns/30930999…/intelligence/
```
Sem stacktrace, sem token, sem URL interna na resposta; `error_type` é apenas o nome da classe (seguro). A política de retry (`attempt=1 of=2`) é observável.

---

## 5. Erros 502/503 (tarefa 6)

| Cenário | HTTP | Mensagem ao cliente | Fuga de internals? |
|---|---|---|---|
| IE indisponível (timeout/unreachable/5xx) | **503** | "Campaign intelligence is temporarily unavailable. Try again later." | não |
| Renderer indisponível (job) | job `failed` + artefacto `queued` honesto (Prompt 05) | "External service is unavailable." (interno) | não |
| IE 4xx / corpo inusável → **502** | 502 | "Campaign intelligence could not be retrieved from the engine." (mapeado em `campaigns/views.py`) | não |

O **502** (IntelligenceUpstreamError) está confirmado por código e mapeamento (4xx do IE / corpo inusável → 502); não foi forçado em runtime nesta iteração por exigir mismatch de token/config disruptivo. O **503** foi exercitado em runtime (acima).

---

## 6. Segurança dos logs (tarefas 3,4,7,8)

Greps nos três ficheiros de log (Backend Core + IE + Content Renderer):

| Padrão | Correspondências |
|---|---|
| `X-Internal-Token` / `x-internal-token` | **0** |
| `Authorization` | **0** |
| `Bearer` | **0** |
| `INTERNAL_API_TOKEN` / `internal_api_token` | **0** |
| `password` | **0** |
| `private_key` | **0** |
| `api_key` | **0** |

Payload integral do IE nos logs:

| Padrão | Correspondências |
|---|---|
| `recommendations` | **0** |
| `"analysis"` / `"scores"` / `"grade"` | **0** |
| `summary` | **0** |
| `improve_smart_link` (conteúdo de recommendation) | **0** |

O `X-Internal-Token` viaja apenas em headers; nunca é registado. O snapshot persistido é a allowlist mínima (Prompt 04) e o serializer redige chaves sensíveis na leitura.

---

## 7. Lacunas (não mascaradas)

| ID | Lacuna | Severidade |
|---|---|---|
| OBS-L01 | **Sem correlation-id único ponta-a-ponta.** intelligence, criação de action, artefacto e job têm `request_id` independentes (ou nenhum). Correlação depende de `campaign_id`/`workspace_id`/`job_id`. | Média |
| OBS-L02 | **IE não regista o `request_id` recebido** nos logs app-level (só uvicorn access com 200). Impossível cruzar o `request_id` do BC com o processamento do IE pelos logs do IE. | Média |
| OBS-L03 | **Criação de CampaignAction e de artefactos (report/media kit/content pack) não emite log com `request_id`/`action_id`/`artifact_id`.** Só o request HTTP (`POST /... 201`) aparece. | Média |
| OBS-L04 | Logs não persistidos (stdout dos processos dev). Sem agregação/retenção. | Baixa (dev) |
| OBS-L05 | `Asset.public_url` não populado no BC (herdado do Prompt 05). | Baixa |

Estas lacunas não bloqueiam o piloto técnico controlado (a cadeia é rastreável por `campaign_id`+`job_id`), mas devem ser resolvidas antes de operação/produção.

---

## 8. Riscos

| ID | Risco | Mitigação |
|---|---|---|
| OBS-R01 (=STG-R10) | Falta de correlation-id único pode atrasar debugging em incidentes multi-serviço | Propagar um `X-Request-ID` único do BC para IE e para o job, e registá-lo em todos (incluindo IE app-level) |
| OBS-R02 | Ausência de log na criação de action/artefacto dificulta auditoria fina | Já existe `audit` (record_audit_event) para submissões; considerar log estruturado adicional na criação de CampaignAction |
| STG-R05 | Token em logs | **Mitigado** — greps a 0 |

---

## 9. Validações executadas

| Validação | Resultado |
|---|---|
| Fluxo fresco correlacionado gerado | ✅ intelligence→action→report→job→callback |
| `request_id` no BC (intelligence, job, callback) | ✅ |
| `job_id` correlacionado BC↔CR | ✅ (`f2da9e53…`) |
| Logs IE (request/processamento/resposta) | ⚠️ só uvicorn access (sem request_id app-level) |
| Logs CR (job/status/callback) | ✅ completos, com job_id/request_id |
| Erro 503 mensagem segura | ✅ |
| Greps de secrets (7 padrões × 3 logs) | ✅ 0 |
| Greps de payload IE (6 padrões × 3 logs) | ✅ 0 |
| Serviços finais (8100/8201/8202) | ✅ 200 |

---

## 10. Ficheiros alterados

Apenas este relatório (**criado**):
`frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_06_observabilidade_minima_resultado.md`

Nenhum código de produto, settings ou `.env` alterado. Dados de teste adicionais criados via API (1 intelligence call, 2 CampaignActions, 1 Report + job/output). Nenhum segredo consta deste relatório.

---

## 11. Próximo passo recomendado

Avançar para **STG-CA-007 (erros reais entre serviços)** e **STG-CA-008 (segurança frontend)**:
1. Testar token interno inválido (se seguro), timeout e callback inválido, confirmando erros controlados e ausência de retry destrutivo.
2. Confirmar no browser/Network que o frontend chama apenas `localhost:8100` (STG-CA-008) — greps já limpos; falta a evidência de Network.
3. Considerar (fora do âmbito de validação, como dívida) propagar um correlation-id único ponta-a-ponta (OBS-L01/OBS-L02).

> Serviços a correr em background: Backend Core (8100), Intelligence Engine (8201), Content Renderer (8202), Frontend (5200).
