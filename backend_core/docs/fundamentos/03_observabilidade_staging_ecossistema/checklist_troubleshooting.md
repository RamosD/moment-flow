# Checklist de troubleshooting — Ecossistema MomentFlow/ChartRex

> Guia prático para diagnosticar falhas comuns entre `backend_core`,
> `intelligence_engine` e `content_renderer` (OBS-STG-008). Pensado para alguém
> que **não implementou o código** — cada caso tem sintoma, causa provável, como
> confirmar, acção recomendada, logs/campos úteis e quando escalar.
>
> Fonte: [`01_backlog.md`](01_backlog.md), [`matriz_operacional_servicos.md`](matriz_operacional_servicos.md),
> [`runbook_arranque_staging.md`](runbook_arranque_staging.md) e os relatórios
> `prompt_01`…`prompt_07`. **Nenhum valor real de secret** aparece neste
> documento — apenas placeholders (`<DEV_TOKEN>`, `<ACCESS_TOKEN>`, …). Os
> comandos de verificação **nunca** imprimem o token — só o seu estado
> (`configured`/`not_configured`) ou ausência/presença.

---

## 0. Como usar este documento

1. Identifica o sintoma na tabela de [índice](#1-índice-de-casos).
2. Segue **"Como confirmar"** primeiro — não actues sem confirmar a causa.
3. Aplica a **"Acção recomendada"**.
4. Se não resolver em 2 tentativas, ou se o sintoma combinar com **"Quando
   escalar"**, pára e escala (ver §3).

Antes de qualquer diagnóstico, confirma o estado geral com o
**healthcheck agregado** (precisa de JWT de utilizador `is_staff`):

```powershell
curl -H "Authorization: Bearer <ACCESS_TOKEN>" http://127.0.0.1:8100/api/v1/system/health/dependencies/
```

---

## 1. Índice de casos

| # | Caso |
|---|---|
| 1 | [Intelligence Engine indisponível](#caso-1--intelligence-engine-indisponível) |
| 2 | [Intelligence Engine devolve 403](#caso-2--intelligence-engine-devolve-403) |
| 3 | [Intelligence Engine devolve 422](#caso-3--intelligence-engine-devolve-422) |
| 4 | [Intelligence Engine devolve 500](#caso-4--intelligence-engine-devolve-500) |
| 5 | [Content Renderer indisponível](#caso-5--content-renderer-indisponível) |
| 6 | [Content Renderer não faz callback](#caso-6--content-renderer-não-faz-callback) |
| 7 | [Callback chega mas o job não actualiza](#caso-7--callback-chega-mas-o-job-não-actualiza) |
| 8 | [Token interno desalinhado](#caso-8--token-interno-desalinhado) |
| 9 | [URL configurada errada](#caso-9--url-configurada-errada) |
| 10 | [Timeout](#caso-10--timeout) |
| 11 | [Payload inválido](#caso-11--payload-inválido) |
| 12 | [Erro de workspace / RBAC](#caso-12--erro-de-workspace--rbac) |
| 13 | [Porta ocupada](#caso-13--porta-ocupada) |
| 14 | [Base de dados indisponível](#caso-14--base-de-dados-indisponível) |
| 15 | [Healthcheck agregado em degraded](#caso-15--healthcheck-agregado-em-degraded) |
| 16 | [Logs sem request_id/job_id](#caso-16--logs-sem-request_idjob_id) |

---

### Caso 1 — Intelligence Engine indisponível

| Campo | Detalhe |
|---|---|
| **Sintoma** | `POST /api/v1/campaigns/{id}/intelligence/` devolve **503** com `intelligence_unavailable`; ou `manage.py smoke_intelligence_engine` falha com "Intelligence Engine call failed". |
| **Causa provável** | O processo do IE não está a correr, ou está numa porta/host diferente do configurado. |
| **Como confirmar** | `curl http://127.0.0.1:8201/health` (sem token — endpoint público). Sem resposta/connection refused ⇒ confirmado. |
| **Acção recomendada** | Arrancar o IE (ver [`runbook_arranque_staging.md`](runbook_arranque_staging.md) §4.2). Confirmar `INTELLIGENCE_ENGINE_BASE_URL` no `backend_core` aponta para o host/porta correctos. |
| **Logs/campos úteis** | `campaigns.intelligence`: `event=intelligence_call_failed` / `error_type=IntelligenceUnavailableError`, `request_id`, `workspace_id`. `integrations_bridge.intelligence`: `intelligence_call unavailable request_id=… workspace_id=…`. |
| **Quando escalar** | O IE está confirmadamente a correr e a responder a `curl` directo mas o `backend_core` continua a reportar indisponível (sugere erro de rede/DNS/firewall entre processos, não de configuração). |

---

### Caso 2 — Intelligence Engine devolve 403

| Campo | Detalhe |
|---|---|
| **Sintoma** | Resposta **502** (`intelligence_upstream_error`) no Backend Core; no log aparece `status=403`. |
| **Causa provável** | `INTERNAL_API_TOKEN`/`INTELLIGENCE_ENGINE_INTERNAL_TOKEN` do `backend_core` não é **idêntico** ao `INTERNAL_API_TOKEN` do IE. |
| **Como confirmar** | Ver [Caso 8](#caso-8--token-interno-desalinhado). |
| **Acção recomendada** | Alinhar o token nos dois serviços e reiniciar ambos os processos (env vars só são lidas no arranque). |
| **Logs/campos úteis** | `integrations_bridge.intelligence`: `intelligence_call http_error … status=403 error_code=…`. **Nunca** aparece o valor do token — só `token=configured`/`not_configured` nos commands de smoke. |
| **Quando escalar** | Os dois tokens foram confirmados idênticos por inspecção directa dos `.env` (não pelos logs) e o 403 persiste — pode ser um terceiro processo antigo a responder na porta (ver [Caso 13](#caso-13--porta-ocupada)). |

---

### Caso 3 — Intelligence Engine devolve 422

| Campo | Detalhe |
|---|---|
| **Sintoma** | Resposta **502** (`intelligence_upstream_error`) no Backend Core; no log aparece `status=422`. |
| **Causa provável** | O payload construído pelo `backend_core` (`build_campaign_intelligence_payload`) não passou a validação do IE — normalmente dados de campanha incompletos/incoerentes (datas, faixas, metas). |
| **Como confirmar** | Procurar `error_code` no log (`intelligence_call http_error … error_code=…`); um `error_code` de validação (não `http_error` genérico) indica payload rejeitado, não problema de rede/auth. |
| **Acção recomendada** | Verificar os dados da campanha de origem (datas, `primary_goal`, faixas associadas). Correr `manage.py smoke_intelligence_engine` para isolar se é um problema do payload sintético do smoke ou de uma campanha real específica. |
| **Logs/campos úteis** | `error_code` (vindo do envelope do IE, nunca o corpo completo), `request_id`, `campaign_id` (no log do serviço, não no do cliente). |
| **Quando escalar** | O `error_code` não é reconhecível ou o smoke test (payload sintético, conhecido como válido) também recebe 422 — sugere incompatibilidade de contrato entre as versões do IE e do Backend Core, não um problema de dados. |

---

### Caso 4 — Intelligence Engine devolve 500

| Campo | Detalhe |
|---|---|
| **Sintoma** | Resposta **502** (`intelligence_upstream_error`) no Backend Core; no log aparece `status=500` (após esgotar `INTELLIGENCE_ENGINE_MAX_RETRIES`, já que 5xx é retryable). |
| **Causa provável** | Erro interno do próprio IE (bug, dependência interna a falhar) — fora do controlo directo do Backend Core. |
| **Como confirmar** | Repetir directamente contra o IE: `curl -X POST http://127.0.0.1:8201/intelligence/campaign -H "X-Internal-Token: <DEV_TOKEN>" -H "Content-Type: application/json" -d "<payload-de-teste>"` e observar o `5xx`. |
| **Acção recomendada** | Consultar a consola/logs do processo do IE directamente (fora do âmbito desta fase do Backend Core). Confirmar se é reproduzível ou intermitente. |
| **Logs/campos úteis** | `intelligence_call http_error … status=500`, `intelligence_call retry … attempt=… of=…` (confirma que houve retries antes de desistir). |
| **Quando escalar** | Reproduzível de forma consistente, ou afecta múltiplas campanhas diferentes — não é um caso isolado de dados. |

---

### Caso 5 — Content Renderer indisponível

| Campo | Detalhe |
|---|---|
| **Sintoma** | `manage.py smoke_content_renderer` (ou `--health-only`) falha com `Renderer /health is 'unavailable'`; jobs ficam em `failed`/`timeout`. |
| **Causa provável** | Processo do renderer não está a correr, ou porta/URL errada (ver também [Caso 9](#caso-9--url-configurada-errada) para a discrepância 8002/8003). |
| **Como confirmar** | `curl http://localhost:8202/health` (público, sem token). |
| **Acção recomendada** | Arrancar o renderer (runbook §4.3). Confirmar `CONTENT_RENDERER_BASE_URL`/`REPORT_RENDERER_BASE_URL` apontam para `:8202`. |
| **Logs/campos úteis** | `integrations_bridge`: `event=job_submission_failed … error_type=…`, `provider=content_renderer`, `job_id`. |
| **Quando escalar** | O `curl` directo ao `/health` funciona mas o Backend Core continua a reportar indisponível (rede/DNS entre processos). |

---

### Caso 6 — Content Renderer não faz callback

| Campo | Detalhe |
|---|---|
| **Sintoma** | O job foi aceite (**202**) mas o `ExternalJobReference` nunca sai de `submitted`/`accepted`; nenhum evento `callback.*` aparece nos logs do renderer. |
| **Causa provável** | (a) `backend_core` está a correr em **SQLite** — o callback chega a um processo que não vê a linha commitada por outro processo, resulta em `404` silencioso do lado do renderer (não-fatal para ele); (b) `BACKEND_PUBLIC_BASE_URL` mal configurado no Backend Core, gerando um `callback_url` que o renderer não consegue alcançar; (c) o renderer ainda está a renderizar (`RENDER_TIMEOUT_SECONDS` longo). |
| **Como confirmar** | Verificar `DB_ENGINE` do Backend Core (`postgres` é necessário para o loop completo — runbook §4.3). Verificar nos logs do renderer se há uma tentativa de callback com erro de ligação/404. Esperar `RENDER_TIMEOUT_SECONDS` antes de concluir que nunca vai chegar. |
| **Acção recomendada** | Para validar o loop completo, usar PostgreSQL + o harness E2E (`run-e2e-postgres.ps1`), não SQLite — ver [`smoke_content_renderer.md`](smoke_content_renderer.md) Camada 2. Confirmar `BACKEND_PUBLIC_BASE_URL` e `INTERNAL_CALLBACK_PATH`. |
| **Logs/campos úteis** | Renderer: eventos `callback.attempt`/`callback.failed` (formato JSON próprio do renderer). Backend Core: ausência de qualquer `event=job_callback_received` para esse `job_id`/`external_job_id`. |
| **Quando escalar** | Confirmado PostgreSQL + URL de callback correctos e o callback continua a não chegar — pode ser um problema de rede/firewall entre os dois processos. |

---

### Caso 7 — Callback chega mas o job não actualiza

| Campo | Detalhe |
|---|---|
| **Sintoma** | Os logs do renderer confirmam que o `POST` de callback foi feito (e devolveu `2xx`), mas o `ExternalJobReference` continua sem o estado final actualizado. |
| **Causa provável** | O `job_id`/`external_job_id` enviado no corpo do callback não corresponde a nenhum `ExternalJobReference` existente (`_resolve_job` em `ExternalJobCallbackView` não encontra a linha) — normalmente porque o `job_id` é sintético (ex.: gerado por `smoke_content_renderer`, que **não** escreve na base de dados) ou porque o job pertence a outro ambiente/base de dados. |
| **Como confirmar** | O callback do `smoke_content_renderer` (Camada 1) **espera-se** que resulte em `404` — está documentado como inofensivo (ver [`smoke_content_renderer.md`](smoke_content_renderer.md) §2). Fora desse caso, verificar se o `job_id` no corpo do callback corresponde a um `ExternalJobReference` existente na base de dados activa. |
| **Acção recomendada** | Se for o smoke da Camada 1: nenhuma acção — comportamento esperado. Se for um job real: confirmar que o Backend Core e o renderer apontam à **mesma** base de dados/ambiente, e que o job não foi criado/eliminado entre a submissão e o callback. |
| **Logs/campos úteis** | `integrations_bridge`: ausência de log `event=job_callback_processed` para o `external_job_id` esperado; resposta `404` do endpoint de callback (visível no log do renderer, não no do Backend Core se a vista devolver 404 antes de logar). |
| **Quando escalar** | O `job_id` é real (criado por um fluxo de produto, não pelo smoke) e a correspondência na base de dados existe, mas a actualização ainda assim não acontece — sugere um erro de processamento no `callback_dispatcher`, não de correlação de ids. |

---

### Caso 8 — Token interno desalinhado

| Campo | Detalhe |
|---|---|
| **Sintoma** | `403` em qualquer chamada entre serviços (IE ou renderer); `smoke_intelligence_engine`/`smoke_content_renderer` reportam "token misaligned?". |
| **Causa provável** | `INTERNAL_API_TOKEN` (ou a variante específica do IE) tem valores **diferentes** entre os processos — normalmente porque um `.env` foi editado depois do outro arrancar, ou os processos usam ficheiros `.env` diferentes. |
| **Como confirmar** | Nos commands de smoke, confirmar `token=configured` em ambos (não revela o valor); confirmar visualmente que os `.env` dos serviços envolvidos têm o **mesmo** valor literal (nunca via log). |
| **Acção recomendada** | Igualar o valor nos `.env` dos serviços envolvidos e **reiniciar todos** (as env vars só são lidas no arranque do processo). |
| **Logs/campos úteis** | `status=403` nos logs de cliente (`integrations_bridge.intelligence`, `integrations_bridge.client`); nunca o valor do token. |
| **Quando escalar** | Os três `.env` foram confirmados idênticos por inspecção directa e o `403` persiste após reiniciar todos os processos. |

---

### Caso 9 — URL configurada errada

| Campo | Detalhe |
|---|---|
| **Sintoma** | `connection refused`/timeout imediato apesar do serviço alvo estar a correr; ou um serviço **errado** responde (ex.: outro processo na mesma porta). |
| **Causa provável mais comum** | `INTELLIGENCE_ENGINE_BASE_URL`, `CONTENT_RENDERER_BASE_URL`, ou `REPORT_RENDERER_BASE_URL` apontam para portas antigas. Portas correctas: Django `:8100`, IE `:8201`, renderer `:8202`. |
| **Como confirmar** | `curl http://localhost:8202/health` responde; `curl http://127.0.0.1:8201/health` responde; `curl http://127.0.0.1:8100/api/v1/schema/` responde. |
| **Acção recomendada** | Confirmar que os `.env` usam as portas padronizadas (ver `docs/configuracao/portas_projeto.md`). Confirmar também `INTELLIGENCE_ENGINE_BASE_URL`/`CONTENT_RENDERER_BASE_URL`/`REPORT_RENDERER_BASE_URL` apontam ao host/porta reais. |
| **Logs/campos úteis** | `event=job_submission_failed reason=…`/`intelligence_call unavailable … reason=no_base_url` quando a URL está vazia/`misconfigured`; o healthcheck agregado mostra `misconfigured` por dependência. |
| **Quando escalar** | URLs confirmadas correctas e o erro persiste — ver [Caso 1](#caso-1--intelligence-engine-indisponível)/[Caso 5](#caso-5--content-renderer-indisponível). |

---

### Caso 10 — Timeout

| Campo | Detalhe |
|---|---|
| **Sintoma** | IE: `IntelligenceEngineTimeout` → 503 após `INTELLIGENCE_ENGINE_MAX_RETRIES` tentativas. Renderer: job marcado `timeout` na submissão, ou healthcheck agregado mostra `unavailable` com `duration_ms` próximo do timeout configurado. |
| **Causa provável** | Serviço alvo lento (carga, arranque a frio) ou timeout configurado demasiado agressivo para o ambiente. |
| **Como confirmar** | Comparar `duration_ms` reportado nos logs/healthcheck com `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS`/`CONTENT_RENDERER_TIMEOUT_SECONDS`/`HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS`. Repetir o `curl /health` directo e medir o tempo de resposta. |
| **Acção recomendada** | Se o serviço estiver genuinamente lento (não indisponível), considerar aumentar o timeout correspondente. Se for consistentemente rápido em `curl` directo mas lento via Backend Core, investigar rede/proxy intermédio. |
| **Logs/campos úteis** | `intelligence_call timeout request_id=… workspace_id=…`; `event=job_submission_timeout`; `duration_ms` no healthcheck agregado. |
| **Quando escalar** | Timeout aumentado para um valor generoso (ex.: 30s) e o sintoma persiste — não é um problema de timeout, é indisponibilidade real. |

---

### Caso 11 — Payload inválido

| Campo | Detalhe |
|---|---|
| **Sintoma** | IE devolve `422` (ver [Caso 3](#caso-3--intelligence-engine-devolve-422)); renderer devolve `400`/`413` na submissão do job. |
| **Causa provável** | Dados de origem incompletos/incoerentes (campanha) ou payload acima de `MAX_JOB_PAYLOAD_BYTES` (renderer). |
| **Como confirmar** | `error_code`/`status_code` no log do cliente; para o renderer, `413` indica excesso de tamanho — confirmar `MAX_JOB_PAYLOAD_BYTES`. |
| **Acção recomendada** | Corrigir os dados de origem (campanha) ou reduzir o tamanho do payload (ex.: menos assets/variações por job). Usar o smoke test (payload sintético conhecido) para confirmar se o problema é no payload específico ou no contrato em geral. |
| **Logs/campos úteis** | `error_code`, `status_code`, `request_id`/`job_id` — **nunca** o corpo do payload (não é logado por desenho). |
| **Quando escalar** | O payload sintético do smoke test também falha — é um problema de contrato/versão, não de dados de um caso específico. |

---

### Caso 12 — Erro de workspace / RBAC

| Campo | Detalhe |
|---|---|
| **Sintoma** | `403 Forbidden` (sem permissão) ou `404 Not Found` (campanha "não existe") em endpoints do Backend Core, mesmo com o recurso a existir. |
| **Causa provável** | (a) Falta o header `X-Workspace-ID` ou tem o UUID errado; (b) o utilizador autenticado não tem a permissão RBAC necessária (`campaigns:view`/`campaigns:create`/…); (c) o recurso pertence a **outro** workspace — por desenho, isto devolve **404**, não 403, para não revelar a existência do recurso. |
| **Como confirmar** | Confirmar o header `X-Workspace-ID` enviado no pedido corresponde ao workspace do utilizador. Verificar as permissões do utilizador/role no painel RBAC (`apps.rbac`). |
| **Acção recomendada** | Corrigir o header `X-Workspace-ID`; atribuir a permissão RBAC em falta; confirmar que o recurso pertence de facto ao workspace esperado. |
| **Logs/campos úteis** | Resposta da API (`detail`/`code` da `APIException`); `workspace_id` no log do serviço (quando aplicável, ex.: `campaigns.intelligence`). Auditoria (`apps.audit`) regista acções relevantes. |
| **Quando escalar** | Permissões e workspace confirmados correctos e o erro persiste — pode ser um problema no `WorkspaceScopedRBACViewSet` ou na atribuição de roles, fora do âmbito desta checklist. |

---

### Caso 13 — Porta ocupada

| Campo | Detalhe |
|---|---|
| **Sintoma** | Erro no arranque tipo `address already in use` / `EADDRINUSE`; ou um serviço "antigo" continua a responder com comportamento desactualizado. |
| **Causa provável** | Um processo anterior (terminal fechado sem `Ctrl+C`, ou IDE a manter o processo vivo) ainda detém a porta `8100`/`8201`/`8202`. |
| **Como confirmar** | `Get-NetTCPConnection -LocalPort 8201 \| Select-Object OwningProcess` (ajustar a porta); confirmar o `PID` devolvido. |
| **Acção recomendada** | `Stop-Process -Id <PID>` e reiniciar o serviço pretendido. |
| **Logs/campos úteis** | N/A (é um erro de arranque do processo, não um log estruturado da aplicação). |
| **Quando escalar** | A porta continua ocupada por um processo que não é claramente identificável como um dos três serviços (pode ser outro serviço do sistema a usar a mesma porta). |

---

### Caso 14 — Base de dados indisponível

| Campo | Detalhe |
|---|---|
| **Sintoma** | `backend_core` falha a arrancar ou a responder a qualquer pedido (erro de ligação à base de dados); healthcheck agregado mostra `database: {"status": "unavailable"}`. |
| **Causa provável** | SQLite: ficheiro `db.sqlite3` bloqueado/corrompido (raro) ou ausente sem `migrate` corrido. PostgreSQL: container/serviço não está a correr, ou credenciais (`DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD`) erradas. |
| **Como confirmar** | PostgreSQL: `docker inspect --format '{{.State.Health.Status}}' chartrex_e2e_postgres` (esperar `healthy`); ou `pg_isready -h <host> -p <port>`. SQLite: confirmar que `python manage.py migrate` foi corrido e o ficheiro existe. |
| **Acção recomendada** | Arrancar/reiniciar o PostgreSQL (`docker compose -f content_renderer/docker-compose.e2e.yml up -d`) ou corrigir as credenciais no `.env`. Para SQLite, correr `migrate` novamente. |
| **Logs/campos úteis** | `integrations_bridge`: secção `database` do healthcheck agregado (`status`, `duration_ms`); excepções Django no arranque (`OperationalError`). |
| **Quando escalar** | Credenciais confirmadas correctas e o PostgreSQL reporta `healthy` mas o Django continua sem conseguir ligar — pode ser firewall/rede entre o Django e o container. |

---

### Caso 15 — Healthcheck agregado em `degraded`

| Campo | Detalhe |
|---|---|
| **Sintoma** | `GET /api/v1/system/health/dependencies/` devolve `200` com `status: "degraded"` (não `ok`, não `unavailable`). |
| **Causa provável** | **Pelo menos uma, mas não todas**, as dependências (`intelligence_engine`, `content_renderer`, `database`) estão `unavailable`/`misconfigured`/`unknown` — por desenho, `degraded` (não `unavailable`) significa que o sistema ainda está parcialmente operacional. |
| **Como confirmar** | Inspeccionar o campo `dependencies` da resposta — identifica exactamente qual(is) dependência(s) falha(m) e com que `status`. |
| **Acção recomendada** | Resolver a dependência específica reportada como não-`ok`, seguindo o caso correspondente desta checklist (1, 5, 9 ou 14, conforme a dependência). |
| **Logs/campos úteis** | `integrations_bridge`: `event=health_check overall=degraded …` com o detalhe por dependência. |
| **Quando escalar** | Todas as dependências reportam `ok` individualmente por `curl` directo, mas o agregado continua a mostrar `degraded` — pode ser um problema no próprio healthcheck agregado (ex.: timeout demasiado agressivo, `HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS`). |

---

### Caso 16 — Logs sem `request_id`/`job_id`

| Campo | Detalhe |
|---|---|
| **Sintoma** | As linhas de log dos fluxos inter-serviços não mostram `request_id`/`job_id`/`external_job_id`/`workspace_id`, dificultando a correlação. |
| **Causa provável** | (a) Nível de log efectivo acima de `INFO` (`LOG_LEVEL` mal configurado); (b) os logs nunca chegam à consola porque faltava o `LOGGING` do Django (gap já corrigido em OBS-STG-006, mas pode regredir se `config/settings.py` for alterado sem cuidado). |
| **Como confirmar** | `python manage.py shell -c "import logging; print(logging.getLogger('integrations_bridge').getEffectiveLevel())"` → esperado `20` (= `INFO`). Se devolver `30` (`WARNING`) ou mais, os logs de correlação estão a ser suprimidos. |
| **Acção recomendada** | Confirmar `LOG_LEVEL=INFO` (ou ausente, que usa o default `INFO`) no `.env` do Backend Core; confirmar que `config/settings.py` ainda define `LOGGING` com os loggers `integrations_bridge`/`campaigns.intelligence`. |
| **Logs/campos úteis** | A própria ausência dos campos é o sintoma; comparar com os campos esperados documentados no relatório [`prompt_06_correlacao_logs.md`](resultados/prompt_06_correlacao_logs.md) §4. |
| **Quando escalar** | `getEffectiveLevel()` confirma `INFO` e ainda assim os campos de correlação não aparecem — sugere uma regressão no código de logging (`logging_utils.py`/`intelligence_sync.py`), não de configuração. |

---

## 2. Comandos de verificação de referência

```powershell
# Healthchecks directos (públicos, sem token)
curl http://127.0.0.1:8201/health
curl http://localhost:8202/health

# Healthcheck agregado (staff-only)
curl -H "Authorization: Bearer <ACCESS_TOKEN>" http://127.0.0.1:8100/api/v1/system/health/dependencies/

# Smoke tests (ver guias dedicados para mais detalhe)
cd backend_core
.\venv\Scripts\python.exe manage.py smoke_intelligence_engine
.\venv\Scripts\python.exe manage.py smoke_content_renderer --health-only

# Confirmar nível efectivo de log (deve ser 20 = INFO)
.\venv\Scripts\python.exe manage.py shell -c "import logging; print(logging.getLogger('integrations_bridge').getEffectiveLevel())"

# Confirmar processo a ocupar uma porta (Windows)
Get-NetTCPConnection -LocalPort 8201 | Select-Object OwningProcess

# Estado do PostgreSQL do harness E2E
docker inspect --format '{{.State.Health.Status}}' chartrex_e2e_postgres
```

> Nenhum destes comandos imprime um token real. Quando um command de smoke
> reporta o estado do token, fá-lo como `token=configured`/`token=not_configured`
> — nunca o valor.

---

## 3. Quando escalar (critério geral)

Escala (procura quem mantém o `intelligence_engine`/`content_renderer`, ou abre
uma issue com a evidência recolhida) quando:

- A causa provável de um caso foi **confirmada como descartada** (ex.: token
  alinhado, URL correcta, serviço a responder a `curl` directo) e o sintoma
  persiste.
- O mesmo sintoma ocorre tanto no smoke test (payload/condições sintéticas e
  conhecidas) como num fluxo real — indica problema de contrato/infra, não de
  dados de um caso isolado.
- O healthcheck agregado e os `/health` directos discordam de forma persistente
  (ex.: agregado sempre `unavailable` com os directos sempre `ok`).
- Haveria necessidade de inspeccionar o código interno de `intelligence_engine`
  ou `content_renderer` para diagnosticar — esta checklist cobre apenas o que é
  diagnosticável do lado do `backend_core`/operação, sem abrir o código desses
  dois serviços (consistente com a regra de não os alterar nesta fase).

Ao escalar, inclui sempre: o `request_id`/`job_id`/`external_job_id` relevante,
o resultado do healthcheck agregado, e os comandos já tentados — **nunca** o
valor do token.

---

## 4. Referências

- Runbook de arranque: [`runbook_arranque_staging.md`](runbook_arranque_staging.md)
- Matriz operacional: [`matriz_operacional_servicos.md`](matriz_operacional_servicos.md)
- Smoke IE: [`smoke_intelligence_engine.md`](smoke_intelligence_engine.md)
- Smoke Renderer: [`smoke_content_renderer.md`](smoke_content_renderer.md)
- Correlação de logs: [`resultados/prompt_06_correlacao_logs.md`](resultados/prompt_06_correlacao_logs.md)
- Backlog da fase: [`01_backlog.md`](01_backlog.md)
