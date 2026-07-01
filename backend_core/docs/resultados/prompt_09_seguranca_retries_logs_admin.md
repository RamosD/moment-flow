# Relatório de execução — Prompt 09: Segurança, retries, logs e Admin

- **Pipeline / Backlog:** Pipeline 09 — Integração FastAPI/Renderer (INT-601, INT-602, INT-603, INT-604)
- **Data:** 2026-06-22
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`
- **Backlog:** [`01_backlog_integracao_fastapi_renderer.md`](../01_backlog_integracao_fastapi_renderer.md)

---

## 1. Prompt executado

Reforçar a segurança dos callbacks internos, consolidar o retry controlado,
implementar logs estruturados sem tokens e melhorar o Django Admin de
`ExternalJobReference`. Sem novas features de produto, sem renderer/FastAPI, sem
relaxar validações.

## 2. Objectivo

Endurecer a operação da fronteira de integração: callbacks mais seguros, retry
rastreável e idempotente, observabilidade sem fuga de segredos e um Admin útil
para investigação operacional.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/integrations_bridge/logging_utils.py` | `log_job_event` — log estruturado `key=value` (sem token/payloads), com drop defensivo de chaves proibidas |
| `apps/integrations_bridge/tests/test_hardening.py` | 17 testes (segurança de callback, retry permitido/bloqueado, logs sem token, Admin) |
| `docs/backend_core/integracoes/resultados/prompt_09_seguranca_retries_logs_admin.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `apps/integrations_bridge/serializers.py` | `workspace_id` passou a **obrigatório** no callback |
| `apps/integrations_bridge/views.py` | validação de `workspace_id` incondicional; logs estruturados em received/noop/rejected/processed; log de payload inválido |
| `apps/integrations_bridge/permissions.py` | log de rejeição de token (sem expor o token) |
| `apps/integrations_bridge/services.py` | logs em job_created/submitted/queued/submission_failed/timeout/retried; docstring de retry |
| `apps/integrations_bridge/models.py` | `RETRYABLE_STATUSES` passa a incluir `expired` |
| `apps/integrations_bridge/admin.py` | filtro por `workspace`, `date_hierarchy`, acção segura `mark_cancelled` |
| 5 ficheiros de teste de callback | `workspace_id` adicionado aos payloads (agora obrigatório) |

Nenhuma alteração a migrations (todas as mudanças são de class-attrs/admin/serializer).

## 5. Comandos executados

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
ruff check .
python manage.py spectacular --file schema.yml
python -m pytest apps/integrations_bridge -q
python -m pytest -q   # suite completa
```

## 6. Resultado das validações

| Validação | Resultado |
|---|---|
| `manage.py check` | ✅ 0 issues |
| `makemigrations --check --dry-run` | ✅ No changes detected |
| `ruff check .` | ✅ All checks passed |
| `spectacular` | ✅ schema gerado sem erros nem warnings |
| testes do prompt | ✅ **17 passed** |
| suite completa (`pytest`) | ✅ **358 passed**, 0 falhas |

## 7. Regras de retry definidas

- **Permitido** apenas a partir de `failed`, `timeout`, `cancelled`, `expired`
  (`RETRYABLE_STATUSES`).
- **Bloqueado** em `queued`, `submitted`, `running`, `completed`
  (`partially_completed` também) → `RetryNotAllowed`.
- O retry **cria um novo job** (o anterior é preservado), com `retry_count + 1` e
  `metadata.retried_from = <job_id antigo>` (rastreabilidade).
- Reutiliza o mesmo `idempotency_key` → um retry ainda em curso não é duplicado.
- Honra dry-run / disabled como qualquer submissão.

## 8. Regras de logging definidas

- **Logger:** `integrations_bridge`; helper `log_job_event(event, job, **extra)`.
- **Eventos:** `job_created`, `job_submitted` (com `dry_run` quando aplicável),
  `job_queued`, `job_submission_failed`, `job_timeout`, `job_retried`,
  `callback_received`, `callback_noop`, `callback_rejected`, `callback_processed`;
  o cliente HTTP loga `internal_call start/ok/http_error/timeout/unavailable`.
- **Campos incluídos:** `workspace_id`, `job_id`, `job_type`, `provider`,
  `status`, `request_id` (+ extras não-sensíveis como `reason`, `retried_from`).
- **Nunca incluídos:** `INTERNAL_API_TOKEN`, payloads completos, secrets. Chaves
  proibidas (`token`/`secret`/`password`/…) são removidas defensivamente.
  Rejeições de token logam só o `reason` (`invalid_token` /
  `internal_token_not_configured`), nunca o valor.

## 9. Segurança de callback reforçada

- Token ausente / errado / não configurado → **403** (camada de permissão,
  comparação constante `hmac.compare_digest`, log de `reason`).
- `workspace_id` agora **obrigatório** → **400** se ausente (decisão abaixo).
- `workspace_id` deve bater com `job.workspace` → **400**.
- `entity.type` / `entity.id` devem bater (quando presentes) → **400**.
- `status` inválido / payload inválido → **400**.
- Job terminal com estado diferente → **409**; mesmo estado → **200** no-op.

**Decisão (tightening, não relaxamento):** `workspace_id` passou de opcional a
**obrigatório**, conforme exigido pelo prompt e pelo backlog (INT-601:
"callbacks sem workspace_id são rejeitados"). Isto **endurece** a validação;
18 testes existentes que omitiam `workspace_id` foram actualizados para o incluir.

## 10. Admin de jobs

- **Filtros:** `status`, `job_type`, `provider`, `workspace`.
- **Search:** `external_job_id`, `related_entity_type`, `related_entity_id`,
  `request_id`, `workspace__name`.
- **Readonly:** todos os payloads (`request/response/callback`), `request_id`,
  `idempotency_key`, `retry_count` e timestamps de ciclo de vida.
- **Ordenação:** `-created_at` + `date_hierarchy` por `created_at`.
- **Acção segura:** `mark_cancelled` — cancela apenas jobs **não-terminais**
  (transição local, nunca chama serviço externo).

## 11. Pendências

- Testes end-to-end transversais (INT-701..704) — ciclos completos com asserções
  de isolamento e replay (parcialmente cobertos pelos testes por app).
- Integração real do Intelligence Engine (fora de escopo — FastAPI).
- `LOGGING` config formal em settings (handlers/formatters por ambiente) — os logs
  já são emitidos via `logging` standard; falta apenas a configuração de produção.

## 12. Próximo passo recomendado

Prompt 10 — testes end-to-end e hardening final da fase de integração (INT-701..704):
ciclos completos Content Pack / Report / Media Kit (pedido → job → callback →
outputs/assets/créditos/notification), replay idempotente e isolamento de
workspace ponta-a-ponta, fechando o MVP de integração.
