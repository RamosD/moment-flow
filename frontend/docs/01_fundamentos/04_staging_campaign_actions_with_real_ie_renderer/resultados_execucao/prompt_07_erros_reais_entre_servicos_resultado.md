# Prompt 07 — Erros reais entre serviços (falhas controladas)

**Data:** 2026-07-02
**Fase:** `04_staging_campaign_actions_with_real_ie_renderer` (STG-CA-007, Incremento 2)
**Âmbito:** validar comportamento real de falhas controladas entre Backend Core (8100), Intelligence Engine (8201) e Content Renderer (8202), sem corromper dados nem expor secrets. Sem alteração de código de produto.
**Estado de execução:** `executado`

---

## 1. Resumo objectivo

Todos os cenários de falha do backlog (STG-CA-007) foram exercitados em **API real** e degradam de forma **controlada e honesta**:

| # | Cenário | Resultado HTTP / estado | Stacktrace? | Secret em log? |
|---|---|---|---|---|
| Baseline | IE up, config real | **200** `source=engine`, 2 recs | — | não |
| S1 | IE indisponível (porta inválida) | **503** honesto | não | não |
| S3 | IE timeout (IP não-roteável, 3 s) | **503** honesto (~3 s) | não | não |
| S5 | Token interno inválido (IE → 403) | **502** honesto (4xx→502) | não | não |
| S4a | Payload inválido para o IE | **422** envelope controlado | não | não |
| S4b | Payload inválido / job_type desconhecido no CR | **400** envelope controlado | não | não |
| S2 | Renderer indisponível (porta inválida) | report **201**+`queued`, job **failed** | não | não |
| Retry | Retry de job falhado (renderer real) | novo job **submitted**, antigo **preservado** | — | não |

Conclusões:
- **Sem falso sucesso:** intelligence com falha devolve 502/503 (nunca 200); report com renderer em baixo fica `queued` + job `failed` (nunca `completed`).
- **Sem retry destrutivo:** intelligence faz retry **bounded** (`attempt=1 of=2`) só para transitórios e **não persiste** no path síncrono; jobs **não** têm retry automático; `retry_external_job` cria um **novo** job e **preserva** o antigo.
- **Sem stacktrace nem secrets** em nenhuma resposta ou log (greds a 0).
- **Recuperação total** e **sem drift**: após todos os testes, o baseline volta a `source=engine`; `.env` intacto; `python manage.py check` → 0 issues.

---

## 2. Método (seguro e reversível)

O Backend Core usa **python-decouple**, que lê `os.environ` **antes** do `.env`. Isto permitiu injectar configuração de falha através de **variáveis de ambiente num processo BC de scratch (porta 8110)**, deixando **intactos**:

- o `.env` (nunca editado);
- o BC pristine em **8100** (config real);
- os processos IE (8201), CR (8202) e Frontend (5200) — **nunca parados**.

Cada cenário de config foi um lançamento efémero do BC de scratch em 8110 com a variável em causa; a limpeza foi apenas matar o processo de scratch. Cenários de payload (S4) foram chamadas directas aos endpoints internos do IE/CR (com o token real lido do `.env` para uma variável de shell, **nunca impresso**). Cenário de token inválido (S5) usou um valor **deliberadamente errado** (o valor real nunca foi exposto).

Nenhuma operação destrutiva; nenhum dado corrompido; nenhuma porta antiga usada (mapa canónico 8100/8201/8202/5200).

Contexto dev (memória CA-014): user `ca014-dev@example.local`, workspace `46ca02a0-…`, campaign `30930999-…` (JWT efémero cunhado via `AccessToken.for_user` e apagado no fim).

---

## 3. Mapeamento de erros confirmado (código + runtime)

Grounding em `apps/campaigns/intelligence_service.py`, `apps/integrations_bridge/intelligence_sync.py`, `clients.py`, `services.py` — e confirmado em runtime:

| Falha upstream (IE) | Excepção típada | HTTP ao cliente | Retry |
|---|---|---|---|
| Timeout | `IntelligenceEngineTimeout` → `IntelligenceUnavailableError` | **503** | sim (transitório) |
| Inalcançável / connection refused | `IntelligenceEngineUnavailable` → `IntelligenceUnavailableError` | **503** | sim |
| 5xx do IE | `IntelligenceEngineResponseError(server)` → `IntelligenceUnavailableError` | **503** | sim |
| 4xx do IE (403 token / 422 payload / 404 rota) | `IntelligenceEngineResponseError(client)` → `IntelligenceUpstreamError` | **502** | **não** (config/contrato) |
| Body inusável / JSON inválido | `IntelligenceEngineProtocolError` → `IntelligenceUpstreamError` | **502** | **não** |
| `INTELLIGENCE_ENGINE_ENABLED=false` | `IntelligenceDisabledError` | **503** | — |

| Falha do renderer (job) | Estado do job | Artefacto |
|---|---|---|
| Timeout | `timeout` | preservado (ex.: report `queued`) |
| Inalcançável / HTTP error / JSON inválido | `failed` (`error_message`) | preservado |
| `job_type` desconhecido / provider não configurado | `failed` | preservado |

A referência do job é **persistida antes** de qualquer chamada externa → uma falha de submissão nunca perde a referência nem corrompe o artefacto.

---

## 4. Cenários — evidência

### S1 — IE indisponível (porta inválida 8299)
`POST /api/v1/campaigns/{id}/intelligence/` (BC scratch → IE em `http://localhost:8299`):
```
HTTP 503
{ "detail": "Campaign intelligence is temporarily unavailable. Try again later." }
keys = ["detail"]   stacktrace = não
```
Log (redigido) — retry bounded, sem token:
```
INFO  integrations_bridge.intelligence intelligence_call start request_id=9b79…
INFO  integrations_bridge.client       internal_call start ... url=http://localhost:8299/intelligence/campaign
WARN  integrations_bridge.client       internal_call unavailable ...
WARN  integrations_bridge.intelligence intelligence_call retry ... attempt=1 of=2 reason=IntelligenceEngineUnavailable
WARN  campaigns.intelligence           intelligence event=unavailable ... error_type=IntelligenceEngineUnavailable duration_ms=8724
Service Unavailable: /api/v1/campaigns/30930999…/intelligence/
```

### S3 — IE timeout (IP não-roteável `10.255.255.1`, timeout=3 s, retries=0)
```
HTTP 503   { "detail": "Campaign intelligence is temporarily unavailable. Try again later." }
elapsed ~3 s   stacktrace = não
```
Log (redigido) — path de timeout explícito:
```
INFO  internal_call start ... url=http://10.255.255.1:8201/intelligence/campaign
WARN  integrations_bridge.client       internal_call timeout ...
WARN  integrations_bridge.intelligence intelligence_call timeout ...
WARN  campaigns.intelligence           intelligence event=unavailable ... error_type=IntelligenceEngineTimeout duration_ms=3045
```

### S5 — Token interno inválido (IE real 8201, token deliberadamente errado)
```
HTTP 502
{ "detail": "Campaign intelligence could not be retrieved from the engine." }
stacktrace = não
```
Log (redigido) — IE devolve 403, BC mapeia 4xx→502 **sem retry**; valor do token **nunca** aparece:
```
WARN  integrations_bridge.client       internal_call http_error ... status=403
WARN  integrations_bridge.intelligence intelligence_call http_error ... status=403 error_code=unauthorized_internal_request
ERROR campaigns.intelligence           intelligence event=upstream_error ... status=403 error_code=unauthorized_internal_request duration_ms=2093
```
Grep pelo valor do token no log → **0**.

### S4 — Payload inválido (endpoints internos seguros, token real)
IE `POST /intelligence/campaign` com corpo malformado:
```
HTTP 422
{ "status": "failed", "error": { "code": "invalid_payload", "message": "Invalid payload.",
  "details": { "errors": [ { "type": "missing", "loc": ["body","payload_version"], "msg": "Field required" } … ] } } }
stacktrace = não
```
CR `POST /jobs/` com `job_type` desconhecido:
```
HTTP 400
{ "error": { "code": "invalid_payload", "message": "Invalid job payload.",
  "details": { "issues": [ { "path": "request_id", "message": "Invalid input: expected string, received undefined" } … ] } } }
stacktrace = não   (sem callback disparado — recusa no intake)
```
Ambos devolvem envelope de erro estruturado (só nomes de campos de schema, nada sensível), sem stacktrace.

### S2 — Renderer indisponível (porta inválida 8299)
`POST /api/v1/reports/` (BC scratch → renderer em `http://localhost:8299`):
```
POST /api/v1/reports/  → HTTP 201        (report persistido, sem rollback)
Report.status      = queued              (honesto — sem output, storage_asset=None)
Job.status         = failed
Job.error_message  = "External service is unavailable."
Job.retry_count    = 0
Job.submitted_at   = None                (nunca marcado submitted)
```
Log (redigido):
```
INFO  integrations_bridge event=job_created ... status=queued job_type=report_generation provider=report_renderer
INFO  integrations_bridge.client internal_call start ... url=http://localhost:8299/jobs/
WARN  integrations_bridge.client internal_call unavailable ...
WARN  integrations_bridge event=job_submission_failed ... status=failed
"POST /api/v1/reports/ HTTP/1.1" 201
```

### Retry — não destrutivo (renderer real 8202)
`retry_external_job(<job S2 falhado>)` com o renderer real disponível:
```
BEFORE old(90f527b1…): status=failed  retry_count=0
AFTER  old(90f527b1…): status=failed            ← PRESERVADO (terminal, inalterado)
NEW   (27309dea…):     status=submitted retry_count=1 retried_from=90f527b1…  (ids distintos)
event=job_created → internal_call ok status=202 → job_submitted → job_retried
```
Confirma: **sem retry automático**; o retry explícito só parte de estado terminal retryável, cria um **novo** job e **não sobrescreve** o antigo (idempotency_key reutilizado, `retried_from` liga os dois).

---

## 5. Falso sucesso? — não

| Situação de falha | Estado observável | Falso sucesso? |
|---|---|---|
| Intelligence (IE down/timeout/token) | 502 / 503 (nunca 200) | não |
| Report com renderer em baixo | report `queued` + job `failed` (nunca `completed`; `storage_asset=None`) | não |
| Job submetido com falha | `failed`/`timeout`, `submitted_at=None` | não |

O artefacto próprio é sempre **preservado** num estado honesto; a CampaignAction liga-se via `related_*` ao artefacto real (não é marcada `completed` por callbacks do renderer nesta fase — contrato da fase 03).

---

## 6. Segurança dos logs (greps redigidos)

Greps nos logs dos três processos por `x-internal-token | authorization | bearer | secret | internal_api_token | traceback` e pelo **valor** do token de teste:

| Alvo | Correspondências |
|---|---|
| Secrets/headers/stacktrace (S1, S3, S5, S2) | **0** |
| Valor do token (real e dummy) | **0** |

O `X-Internal-Token` viaja apenas em headers; os logs só contêm `request_id`, `job_id`, `workspace_id`, `campaign_id`, `status`, `error_type`, `error_code`, `duration_ms`. As mensagens ao cliente são genéricas e seguras.

### Fronteira do frontend (grep `frontend/src`)
`localhost:8201 | localhost:8202 | :8201 | :8202 | X-Internal-Token | INTERNAL_API_TOKEN | /intelligence/campaign | /jobs/` → apenas 2 ocorrências, ambas **documentais** (comentário em `shared/api/client.ts` e `shared/README.md` a proibir chamadas directas). Nenhuma chamada runtime a IE/CR; nenhum token no frontend.

---

## 7. Configurações alteradas / restauradas

| Item | Alteração | Restauro |
|---|---|---|
| `backend_core/.env` | **nenhuma** (overrides foram por env-var no processo de scratch) | n/a — confirmado intacto (`DRY_RUN=false`, URLs 8201/8202) |
| BC pristine (8100) | **nunca reiniciado / config real** | n/a |
| IE (8201), CR (8202), FE (5200) | **nunca parados** | n/a |
| BC scratch (8110) | processos efémeros com env de falha | **mortos** (8110 sem listener) |
| JWT dev temporário | cunhado para os testes | **apagado** |
| Ficheiros git rastreados | nenhum modificado | `git status` limpo (só este relatório em `resultados_execucao/`) |

Validações finais:
- Recuperação: `POST /campaigns/{id}/intelligence/` (BC 8100) → **200 `source=engine`**, 2 recs.
- `python manage.py check` → **System check identified no issues (0 silenced).**
- Health final: BC 8100 (200), IE 8201 (ok), CR 8202 (200), FE 5200 (200).

Dados dev criados (esperado, não destrutivo): 1 Report `3d540edf…` (`queued`), 1 job falhado `90f527b1…`, 1 job de retry `27309dea…` (submitted→completed via renderer real).

---

## 8. Riscos

| ID | Risco | Sev. | Nota |
|---|---|---|---|
| STG-R06 | Renderer indisponível deixar action "presa" | **Mitigado** | Estado honesto (report `queued`, job `failed`); recuperável por retry explícito não-destrutivo. |
| STG-R05 | Token em logs | **Mitigado** | Greps a 0 (incl. valor do token). |
| P07-R01 | Report/MediaKit sem estado `failed` próprio ficam `queued`/`draft` quando o job falha | Baixo | Estado é honesto (não é sucesso), mas requer olhar o job para ver a causa; alinhar contrato de estado artefacto↔job antes de produção. |
| P07-R02 | MediaKit regista falha em `metadata` (não em `status`) | Baixo | Herdado do Prompt 01/05; ao operar, inspeccionar metadata. |
| OBS-L01 | Sem correlation-id único ponta-a-ponta (herdado do Prompt 06) | Média | Debugging de incidentes cruza por `campaign_id`/`job_id`. |

---

## 9. Validações executadas

| Validação | Resultado |
|---|---|
| S1 IE indisponível → 503 controlado | ✅ |
| S3 IE timeout → 503 controlado (~3 s) | ✅ |
| S5 token inválido → 502 (4xx→502, sem retry) | ✅ |
| S4a payload inválido IE → 422 controlado | ✅ |
| S4b payload/job_type inválido CR → 400 controlado | ✅ |
| S2 renderer indisponível → report `queued` + job `failed` | ✅ |
| Sem falso sucesso (nunca 200/`completed` em falha) | ✅ |
| Sem retry destrutivo (bounded / explícito preserva antigo) | ✅ |
| Sem stacktrace nas respostas | ✅ |
| Greps de secrets/token nos logs | ✅ 0 |
| Fronteira frontend (sem 8201/8202/token) | ✅ só docs |
| `.env` intacto + serviços restaurados | ✅ |
| Recuperação baseline `source=engine` | ✅ |
| `python manage.py check` | ✅ 0 issues |

---

## 10. Ficheiros alterados

Apenas este relatório (**criado**):
`frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_07_erros_reais_entre_servicos_resultado.md`

Nenhum código de produto, `settings.py` ou `.env` alterado. Dados dev adicionais criados via fluxo real (1 report + 2 jobs). Nenhum segredo consta deste relatório.

---

## 11. Próximo passo recomendado

Avançar para **STG-CA-008 (segurança frontend)** e **STG-CA-009 (smoke visual staging)**:
1. Confirmar no browser/Network que o frontend chama **apenas** `localhost:8100` (greps já limpos; falta a evidência de Network) e que uma falha de IE/renderer é apresentada de forma honesta na UI (War Room não quebra; action não fica em falso sucesso).
2. Executar o smoke visual clicado (login → War Room → intelligence real → recommendations → actions → reload).
3. Dívida técnica (fora do âmbito de validação): correlation-id único ponta-a-ponta (OBS-L01/OBS-L02) e alinhar o contrato de estado artefacto↔job em falha (P07-R01).

> Serviços a correr em background no fim desta iteração: Backend Core (8100), Intelligence Engine (8201), Content Renderer (8202), Frontend (5200) — todos em config real, restaurados.
