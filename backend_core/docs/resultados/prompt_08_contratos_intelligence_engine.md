# Relatório de execução — Prompt 08: Contratos do Intelligence Engine

- **Pipeline / Backlog:** Pipeline 08 — Integração FastAPI/Renderer (INT-501, INT-502, INT-503)
- **Data:** 2026-06-22
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`
- **Backlog:** [`01_backlog_integracao_fastapi_renderer.md`](../01_backlog_integracao_fastapi_renderer.md)

---

## 1. Prompt executado

Preparar contratos e handlers placeholder para integração futura com o FastAPI
Intelligence Engine (`metrics_collection`, `moment_detection`, `insight_generation`,
`recommendation_generation`), **sem implementar lógica analítica no Django**: o
Django apenas cria `ExternalJobReference`, monta payloads e guarda callbacks.

## 2. Objectivo

Deixar a fronteira pronta para o Intelligence Engine: builders de payload,
services para abrir jobs técnicos e handlers de callback que persistem o
resultado reportado sem o calcular — respeitando *Django orquestra; FastAPI
calcula e executa*.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/integrations_bridge/intelligence.py` | 4 builders de payload + 4 services (`request_metrics_collection`/`request_moment_detection`/`request_insight_generation`/`request_recommendation_generation`) |
| `apps/integrations_bridge/tests/test_intelligence.py` | 13 testes (criar jobs, platform links, dry-run, disabled, idempotência, callbacks, garantia de não-cálculo) |
| `docs/backend_core/integracoes/resultados/prompt_08_contratos_intelligence_engine.md` | Este relatório |

## 4. Ficheiros alterados

Nenhum ficheiro de produção alterado. Os **handlers placeholder** já existiam
(Prompt 03) e satisfazem o requisito sem alterações: `handle_metrics_collection_callback`,
`handle_moment_detection_callback`, `handle_insight_generation_callback`,
`handle_recommendation_generation_callback` — transitam o job, registam audit
`<job_type>.callback_received` e **não** criam modelos analíticos. O
`callback_payload`/`callback_received_at` são persistidos pela view antes do
dispatch.

Nenhuma alteração a models/migrations.

## 5. Comandos executados

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
ruff check .
python manage.py spectacular --file schema.yml
python -m pytest apps/integrations_bridge/tests/test_intelligence.py -q
python -m pytest -q   # suite completa
```

## 6. Resultado das validações

| Validação | Resultado |
|---|---|
| `manage.py check` | ✅ 0 issues |
| `makemigrations --check --dry-run` | ✅ No changes detected (sem alterações de modelo) |
| `ruff check .` | ✅ All checks passed |
| `spectacular` | ✅ schema gerado sem erros nem warnings |
| testes do prompt | ✅ **13 passed** |
| suite completa (`pytest`) | ✅ **341 passed**, 0 falhas |

## 7. Contratos definidos

Cada builder devolve o payload **de domínio**; o envelope da integrations_bridge
acrescenta `job_id`, `request_id`, `workspace_id`, `callback_url`, `entity`,
`payload_version`.

| Job type | Campos de domínio | Provider |
|---|---|---|
| `metrics_collection` | `payload_version`, `workspace_id`, `campaign_id`, `track_id`, `platform_links[]`, `requested_by`, `metadata` | `intelligence_engine` |
| `moment_detection` | `payload_version`, `workspace_id`, `campaign_id`, `track_id`, `metrics_context` | `intelligence_engine` |
| `insight_generation` | `payload_version`, `workspace_id`, `campaign_id`, `track_id`, `moments_context` | `intelligence_engine` |
| `recommendation_generation` | `payload_version`, `workspace_id`, `campaign_id`, `track_id`, `insights_context` | `intelligence_engine` |

`platform_links` deriva de `TrackPlatformLink` (id, platform, external_id, url,
canonical_url, status). Os `*_context` são entradas opcionais (resultados de
fases anteriores) passadas pelo chamador.

**Services:** `request_metrics_collection`, `request_moment_detection`,
`request_insight_generation`, `request_recommendation_generation` →
`create_and_submit_external_job` (resolve provider via registry, idempotency_key
default `"<job_type>:<track_id|campaign_id>"`, entidade relacionada = track quando
disponível, senão campaign). Honram `EXTERNAL_JOBS_ENABLED` (queued) e
`EXTERNAL_JOBS_DRY_RUN` (submitted simulado).

**Callback (placeholder):** valida token/workspace/entity, guarda `callback_payload`,
transita o `ExternalJobReference`, regista audit `<job_type>.callback_received`.
Garantia testada (`test_django_does_not_compute_metrics`): o resultado reportado
fica em `callback_payload` **tal e qual**, sem qualquer derivação no Django.

## 8. Decisões tomadas

- **Sem app analítica:** builders/services vivem em `apps/integrations_bridge`
  (camada de contrato), com imports lazy de catalogue/campaigns — não se criou
  uma app de métricas nem modelos técnicos (fora de escopo).
- **Entidade do job:** `track` quando fornecida (métricas são por faixa), senão
  `campaign`.
- **Idempotência:** chave default por entidade evita submissões concorrentes
  duplicadas; após estado terminal, uma nova chamada cria novo job.
- **Sem notificação técnica:** não foi adicionada notificação para admins (ver
  pendências) — manter simples nesta fase.

## 9. Pendências

- **Notificação técnica para admins** em callbacks de Intelligence Engine
  (opcional) — não implementada; pode ser adicionada quando houver um canal de
  notificação técnica/admin dedicado.
- **Modelos técnicos** (snapshots, moments, insights, recommendations) — pertencem
  ao FastAPI Intelligence Engine / a uma app técnica futura; o Django apenas guarda
  o `callback_payload` por agora.
- **Wiring de produto** (quando/como disparar `request_metrics_collection` etc.)
  — fora de escopo deste prompt (são services prontos a ser chamados).

## 10. Próximo passo recomendado

Prompt 09 — hardening da fase de integração (INT-601..604): segurança reforçada
de callbacks, timeouts/retries controlados (`retry_external_job` já existe),
logs estruturados (workspace_id/job_id/job_type/provider/status, sem tokens) e
melhoria do Django Admin de `ExternalJobReference`.
