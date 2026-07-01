# Relatório de execução — Prompt 02: ExternalJobReference e submissão de jobs

- **Pipeline / Backlog:** Pipeline 02 — Integração FastAPI/Renderer (INT-101, INT-102, INT-103)
- **Data:** 2026-06-22
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`
- **Backlog:** [`01_backlog_integracao_fastapi_renderer.md`](../01_backlog_integracao_fastapi_renderer.md)

---

## 1. Prompt executado

Evoluir `ExternalJobReference` (campos de payload, timestamps de ciclo de vida,
`request_id`, `idempotency_key`, `retry_count` e novos estados) e criar um serviço
único `create_and_submit_external_job` para criar e submeter jobs externos de
forma idempotente, rastreável e segura — criando sempre a referência *antes* de
qualquer chamada externa, com suporte a dry-run, external-jobs-disabled e retry
explícito. Sem ligar ainda ContentPackRequest/Report/MediaKit, sem chamadas reais
em testes, sem expor o `INTERNAL_API_TOKEN`.

## 2. Objectivo

Tornar o `ExternalJobReference` a fronteira completa de um job externo (pedido,
submissão, resposta, callback, retry) e centralizar a sua abertura num único
serviço idempotente.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/integrations_bridge/migrations/0002_externaljobreference_callback_payload_and_more.py` | Migration aditiva (9 campos + 2 índices + alteração de choices) |
| `apps/integrations_bridge/tests/test_create_submit_job.py` | 10 testes: criação, dry-run, disabled, cliente mockado, timeout, erro HTTP, idempotência, retry, audit |
| `docs/backend_core/integracoes/resultados/prompt_02_external_job_reference_submission.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `apps/integrations_bridge/models.py` | Novos campos (`submitted_at`, `started_at`, `callback_received_at`, `request_payload`, `response_payload`, `callback_payload`, `request_id`, `idempotency_key`, `retry_count`); novos estados (`submitted`, `partially_completed`, `expired`, `timeout`); novos providers/job types alinhados com o registry; `TERMINAL_STATUSES`/`RETRYABLE_STATUSES`; índices |
| `apps/integrations_bridge/services.py` | `create_and_submit_external_job`, `build_request_envelope`, idempotência (`find_active_job`/`default_idempotency_key`), `retry_external_job`, `apply_job_callback` alargado aos novos estados |
| `apps/integrations_bridge/serializers.py` | Novos campos read-only no `ExternalJobReferenceSerializer` |
| `apps/integrations_bridge/admin.py` | `list_display`/`search_fields`/`readonly_fields` com `external_job_id`, `request_id`, `retry_count`, payloads e timestamps |

## 5. Migrations criadas

`0002_externaljobreference_callback_payload_and_more.py` — **aditiva e segura**
(campos nullable / com default, sem remoção de campos nem perda de dados; estados
antigos continuam válidos como strings).

## 6. Comandos executados

```powershell
python manage.py makemigrations integrations_bridge
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
ruff check .
python -m pytest apps/integrations_bridge/tests/test_create_submit_job.py -q
```

## 7. Resultado das validações

| Validação | Resultado |
|---|---|
| `makemigrations` | ✅ 1 migration gerada |
| `migrate` | ✅ aplicada (OK) |
| `manage.py check` | ✅ 0 issues |
| `makemigrations --check --dry-run` | ✅ No changes detected |
| `ruff check .` | ✅ All checks passed |
| testes do prompt | ✅ **10 passed** |
| suite completa (`pytest`) | ✅ **286 passed**, 0 falhas |

## 8. Decisões tomadas

- **Job criado antes da chamada externa**, sempre persistido; falha de submissão
  marca `failed`/`timeout` mas nunca apaga a referência.
- **Idempotência por `idempotency_key`** (default `"<job_type>:<entity_id>"`):
  um job não-terminal existente é reutilizado (`created=False`); chave indexada
  mas **não** única, para permitir retry.
- **Retry explícito** (`retry_external_job`) só a partir de `failed`/`timeout`/
  `cancelled`; cria um **novo** job com `retry_count+1` e `metadata.retried_from`,
  sem sobrescrever o antigo.
- **Configuração de submissão:** `EXTERNAL_JOBS_ENABLED=False` mantém `queued`;
  `EXTERNAL_JOBS_DRY_RUN=True` simula (`submitted`, `response_payload={"dry_run": true}`);
  caso contrário chamada real via cliente interno.
- **Envelope versionado** (`payload_version=1.0`) com `job_id`, `workspace_id`,
  `request_id`, `job_type`, `callback_url`, `entity` e `payload` — sem segredos.
- **Audit** de submissão (`external_job.submitted` / `.queued` / `.submission_failed`),
  best-effort.
- **Providers/JobTypes antigos preservados** (`fastapi_intelligence`, `worker`,
  `other`) para compatibilidade de linhas existentes.

## 9. Pendências

- Ligar `ContentPackRequest`/`Report`/`MediaKit` a `create_and_submit_external_job`
  (prompts INT-301/401/403, fora desta fase).
- Builders de payload de domínio específicos por job_type (INT-302+).
- Endpoint/serviço público de retry (INT-602).

## 10. Próximo passo recomendado

Prompt 03 — normalizar o callback interno, implementar o dispatcher por
`job_type` e garantir idempotência dos callbacks.
