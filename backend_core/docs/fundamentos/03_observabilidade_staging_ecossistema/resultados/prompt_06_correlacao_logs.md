# OBS-STG-006 — Relatório de execução: Correlação de logs entre serviços

> Relatório de execução do prompt 06. Alterações **mínimas e aditivas** (2 módulos
> de runtime). **Não** altera o `intelligence_engine` nem o `content_renderer`.
>
> Fase: Observabilidade e Staging Técnico do Ecossistema.
> Backlog: [`../01_backlog.md`](../01_backlog.md).
> Data: 2026-06-25. Modelo recomendado (backlog §15): opus.

---

## 1. Objectivo

Garantir que os logs mínimos dos fluxos entre serviços são correlacionáveis
(`request_id`, `job_id`, `external_job_id`, `workspace_id`, …) sem expor tokens
nem payloads, tocando o menor número possível de módulos.

---

## 2. Inspecção dos logs existentes (estado de partida)

| Fluxo | Logger | Campos já presentes | Lacuna |
|---|---|---|---|
| **BC → Intelligence Engine** (serviço) | `campaigns.intelligence` | `event`, `request_id`, `workspace_id`, `campaign_id`, `status`, `duration_ms`, `error_type`, `error_code` | — (rastreável por `request_id`) |
| **BC → Intelligence Engine** (cliente) | `integrations_bridge.intelligence` | `request_id`, `workspace_id`, `status`, `error_code`, `attempt` | — |
| **BC → Renderer / transporte** | `integrations_bridge.client` | `job_id`, `request_id`, `url`, `status` | (workspace_id/provider só na camada de job) |
| **BC → Renderer / job + callbacks** | `integrations_bridge` (`log_job_event`) | `event`, `workspace_id`, `job_id`, `job_type`, `provider`, `status`, `request_id` | **faltava `external_job_id`** |
| **Healthcheck agregado** | `integrations_bridge` | `event=health_check`, `overall`, estado por dependência | — |

**Confirmações pedidas:**
- `request_id` **já presente** no fluxo Intelligence (serviço + cliente). ✅
- `job_id` **já presente** no fluxo Renderer (transporte + `log_job_event`). ✅
- **`external_job_id` ausente** do `log_job_event` — única lacuna real de
  correlação (os callbacks podem ser resolvidos por `external_job_id`, ver
  `views.ExternalJobCallbackView._resolve_job`).

**Lacuna estrutural adicional:** `config/settings.py` **não definia `LOGGING`** →
os logs INFO podiam **não surgir** (handler de último recurso do Python só emite
≥ WARNING), tornando a correlação inútil na prática.

---

## 3. Alterações efectuadas (mínimas)

### 3.1 `config/settings.py` — `LOGGING` mínimo (+ `LOG_LEVEL`)

Config estruturada de consola para os loggers do projecto, garantindo que os
logs de correlação (que já existiam e já eram ricos) **efectivamente aparecem**:

- Handler `console` (StreamHandler) com formato
  `"%(asctime)s %(levelname)s %(name)s %(message)s"`.
- Loggers `integrations_bridge` (e filhos `.client`/`.intelligence` por herança) e
  `campaigns.intelligence` a `LOG_LEVEL` (default `INFO`, via `python-decouple`).
- `propagate: True` e `disable_existing_loggers: False` — **não** quebra a captura
  de logs em testes (`caplog`) nem os loggers do Django.

### 3.2 `apps/integrations_bridge/logging_utils.py` — `external_job_id`

`job_log_fields` passa a incluir `external_job_id` (`None` enquanto o serviço
externo não reportar um). Como **todos** os `log_job_event` (submissão, callback,
retry, timeout, …) usam `job_log_fields`, a correcção propaga-se a todo o fluxo de
jobs e callbacks numa única alteração.

> Não foram logados payloads completos, headers nem tokens. O mecanismo de
> redacção (`_FORBIDDEN_KEYS` em `log_job_event`) mantém-se.

---

## 4. Campos de log por fluxo (resultado)

| Campo | IE (serviço) | IE (cliente) | Renderer/job + callback |
|---|:---:|:---:|:---:|
| `request_id` | ✅ | ✅ | ✅ |
| `workspace_id` | ✅ | ✅ | ✅ |
| `campaign_id` | ✅ | — | — (n/a) |
| `job_id` | — (n/a) | — (n/a) | ✅ |
| `external_job_id` | — (n/a) | — (n/a) | ✅ **(novo)** |
| `provider` | — (implícito IE) | — | ✅ |
| `duration_ms` | ✅ | — | — (ver §7) |
| `status` | ✅ | ✅ | ✅ |
| `error_type` / `error_code` | ✅ | ✅ (`error_code`) | ✅ (via extra) |

---

## 5. Ficheiros alterados / criados

| Ficheiro | Acção |
|---|---|
| `config/settings.py` | Alterado (+`LOG_LEVEL`, +`LOGGING`) |
| `apps/integrations_bridge/logging_utils.py` | Alterado (+`external_job_id` em `job_log_fields`) |
| `apps/integrations_bridge/tests/test_log_correlation.py` | **Criado** (9 testes) |
| `docs/.../matriz_operacional_servicos.md` | Alterado (nota de logs + item "por confirmar" resolvido) |

**Não alterados:** `intelligence_engine/`, `content_renderer/`. Apenas **2 módulos
de runtime** tocados.

---

## 6. Testes e validações (evidência)

| Validação | Comando | Resultado |
|---|---|---|
| Testes de correlação novos | `pytest apps/integrations_bridge/tests/test_log_correlation.py -q` | **9 passed** |
| **Não-regressão de `caplog`** (risco principal do `LOGGING`) | `pytest …test_intelligence_sync.py …test_hardening.py …test_settings_client_registry.py …test_intelligence_service.py …test_intelligence_integration.py -q` | **106 passed** |
| Suites afectadas completas | `pytest apps/integrations_bridge/ apps/campaigns/ -q` | **243 passed, 3 skipped** (os 3 opt-in do loop real) |
| Lint | `ruff check` (ficheiros alterados) | **All checks passed!** |
| Django system check | `python manage.py check` | **no issues** |

Os **9 testes novos** cobrem: presença de `external_job_id` (com e sem valor);
linha de `log_job_event` com `event/job_id/external_job_id/request_id/workspace_id/
provider/status` (sucesso) e com `error_type` (falha); **token-like extras
descartados** (`token`/`secret` ausentes da linha; `reason=ok` presente); e que os
loggers `integrations_bridge*` e `campaigns.intelligence` emitem a INFO
(`getEffectiveLevel() ≤ INFO`).

---

## 7. Limitações (documentadas)

- **`duration_ms` na submissão do renderer** não foi adicionado: a submissão é um
  *ack* rápido (202) e a duração é menos significativa; o `duration_ms` já existe
  no fluxo IE (o mais sensível à latência). Adicionável depois sem alterar o
  contrato — fica fora do âmbito mínimo desta tarefa.
- **`workspace_id` na camada de transporte** (`integrations_bridge.client`) não foi
  adicionado: a correlação já é possível pela linha `log_job_event` (que tem
  `workspace_id`+`provider`+`external_job_id`). Evitou-se mexer no cliente
  partilhado sem necessidade.
- **Logs cross-serviço em formatos diferentes**: o Backend Core emite `key=value`;
  o IE e o renderer emitem JSON. A correlação por `request_id`/`job_id` é possível
  (os ids propagam-se), mas uma agregação automática exigiria parsing de dois
  formatos — fora do âmbito MVP desta fase (sem ELK/observabilidade completa).

---

## 8. Conformidade com os critérios de aceitação

| Critério | Estado |
|---|---|
| Fluxo IE rastreável por `request_id` | ✅ (já existia; confirmado e agora sempre visível via `LOGGING`) |
| Fluxo Renderer rastreável por `job_id`/`request_id` | ✅ (transporte + `log_job_event`) |
| Callbacks rastreáveis por `job_id`/`external_job_id` | ✅ (`external_job_id` adicionado a `job_log_fields`) |
| Tokens não aparecem em logs | ✅ redacção mantida; teste `test_token_like_extra_is_dropped` |
| Testes de logging passam ou lacunas documentadas | ✅ 9 novos + 106 de não-regressão |
| Validações relevantes executadas | ✅ §6 |
| Relatório lista ficheiros/campos/testes/limitações/próximo passo | ✅ este documento |

---

## 9. Próximo passo recomendado

**OBS-STG-007 — Runbook de arranque local/staging.** Documentar pré-requisitos,
portas, ordem de arranque, variáveis, arranque/paragem dos três serviços,
verificação de healthchecks (`/api/v1/system/health/dependencies/` + `/health` do
IE/renderer) e execução dos smoke tests (commands `smoke_intelligence_engine` /
`smoke_content_renderer` + harness E2E), reutilizando a matriz operacional e os
guias de smoke já criados.
