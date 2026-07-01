# Relatório de execução — Prompt 06: Report e MediaKit → jobs externos

- **Pipeline / Backlog:** Pipeline 06 — Integração FastAPI/Renderer (INT-401, INT-403)
- **Data:** 2026-06-22
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`
- **Backlog:** [`01_backlog_integracao_fastapi_renderer.md`](../01_backlog_integracao_fastapi_renderer.md)

---

## 1. Prompt executado

Ligar a criação de `Report` e `MediaKit` à criação e submissão de
`ExternalJobReference` (`report_generation` / `media_kit_generation`), com builders
de payload versionados, idempotência por entidade, dry-run, falha rastreável e
audit `report.job_submitted` / `media_kit.job_submitted`. Sem implementar callback
completed/failed, sem gerar PDF/media kit reais, sem renderer, sem alterar o
modelo de billing.

## 2. Objectivo

Fechar a ponta "pedido de produto → job externo" para reports e media kits,
reutilizando a infra dos prompts 01–02 (registry, cliente, `create_and_submit_external_job`)
e mantendo a fronteira *Django orquestra; Renderer gera activos*.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/reports/payloads.py` | `build_report_generation_payload` e `build_media_kit_generation_payload` (payloads de domínio, sem segredos) |
| `apps/reports/tests/test_report_media_kit_jobs.py` | 10 testes (job criado, payload JSON, dry-run, idempotência, falha rastreável, usage, isolation) |
| `docs/backend_core/integracoes/resultados/prompt_06_report_media_kit_jobs.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `apps/reports/services.py` | `submit_report_generation_job` / `submit_media_kit_generation_job` + helper `_submit_external_job` (resiliente, idempotente, audita); mantém os hooks de usage existentes |
| `apps/reports/views.py` | `ReportViewSet.perform_create` valida quota `reports_per_month` e submete o job; `MediaKitViewSet.perform_create` submete o job |

Nenhuma alteração a models/migrations, billing ou notifications. Nenhum teste
existente removido.

## 5. Comandos executados

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
ruff check .
python manage.py spectacular --file schema.yml
python -m pytest apps/reports -q
python -m pytest -q   # suite completa
```

## 6. Resultado das validações

| Validação | Resultado |
|---|---|
| `manage.py check` | ✅ 0 issues |
| `makemigrations --check --dry-run` | ✅ No changes detected (sem alterações de modelo) |
| `ruff check .` | ✅ All checks passed |
| `spectacular` | ✅ schema gerado sem erros nem warnings |
| testes do prompt | ✅ **10 passed** (suite `apps/reports`: 25 passed) |
| suite completa (`pytest`) | ✅ **319 passed**, 0 falhas |

## 7. Decisão sobre usage report_requested / report_generated

**Mantido `report_generated`** (o padrão actual), em vez de introduzir
`report_requested`. Razões:

- O contador de quota `reports_per_month` já agrega eventos `report_generated`
  (`_count_reports_this_period` em `apps/billing/services.py`); mudar o tipo
  partiria o enforcement de quota existente.
- O evento é registado por `record_creation_usage`, **idempotente** por entidade
  (`report_generated:<report_id>`), evitando duplicação em retry.
- Não há ainda separação de "requested" vs "generated" no billing; introduzir um
  novo tipo seria uma alteração de billing sem necessidade (restrição do prompt).

A quota `reports_per_month` passou a ser **validada na criação** do report
(`check_workspace_limit`, que falha aberto sem plano), espelhando o fluxo de
content packs. Media kits não têm quota dedicada (não consta do modelo de billing).

## 8. Decisões técnicas

- **Domínio vs envelope:** os builders devolvem o payload de domínio; o envelope
  (Prompt 02) acrescenta `job_id`/`request_id`/`workspace_id`/`callback_url`/
  `entity`/`payload_version`. O `request_payload` guardado no job contém o
  contrato completo.
- **Idempotência:** `report_generation:<report_id>` / `media_kit_generation:<media_kit_id>`.
- **Estados:** `Report` mantém-se `queued`; `MediaKit` mantém-se `draft`; o
  `ExternalJobReference` reflecte `queued`/`submitted`/dry-run.
- **Resiliência:** submissão fora de qualquer transacção de escrita do request;
  erro inesperado é apanhado e registado em `metadata.job_submission_error`
  (entidade nunca se perde); `create_and_submit_external_job` já marca o job
  `failed`/`timeout` sem rebentar.
- **Sem segredos:** payloads só com contexto de produto e stats agregados
  (cliques de smart links), sem tokens nem dados privados.

## 9. Pendências

- Handlers de callback `report_generation` / `media_kit_generation`
  *completed/failed* (INT-402/404): criar `Asset` (report_pdf / media_kit_asset),
  ligar `storage_asset`, marcar `completed`/`generated` ou `failed`, emitir
  notification (`report_ready` / `media_kit_ready`) e audit.
- Contratos/placeholders do Intelligence Engine (INT-501..503).

## 10. Próximo passo recomendado

Prompt 07 — implementar os handlers de callback de `report_generation` e
`media_kit_generation`: em `completed`, criar `Asset` e ligar
`Report.storage_asset` / `MediaKit.storage_asset`, marcar estado final, emitir
`Notification` (`report_ready` / `media_kit_ready`) e `AuditEvent`; em `failed`,
marcar erro e notificar — tudo idempotente.
