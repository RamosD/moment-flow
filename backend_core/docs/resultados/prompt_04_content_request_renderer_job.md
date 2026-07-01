# Relatório de execução — Prompt 04: ContentPackRequest → job de content_generation

- **Pipeline / Backlog:** Pipeline 04 — Integração FastAPI/Renderer (INT-301, INT-302)
- **Data:** 2026-06-22
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`
- **Backlog:** [`01_backlog_integracao_fastapi_renderer.md`](../01_backlog_integracao_fastapi_renderer.md)

---

## 1. Prompt executado

Ligar o fluxo de `ContentPackRequest` à criação e submissão de um
`ExternalJobReference` do tipo `content_generation`, depois de validar workspace,
RBAC, campanha, pack, quotas e créditos. Criar o builder
`build_content_generation_payload`, definir `idempotency_key`
(`content_generation:<request_id>`), manter o fluxo transaccional no que é seguro
e registar audit `content_pack.job_submitted`. Sem implementar callback completed,
sem criar Asset real, sem gerar ficheiros, sem renderer e sem alterar billing.

## 2. Objectivo

Fechar a ponta "pedido de produto → job externo" para content packs, com payload
de domínio completo para o renderer, idempotência e rastreabilidade de falhas —
mantendo a fronteira *Django orquestra; Renderer gera activos*.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/content/payloads.py` | `build_content_generation_payload` — payload de domínio (campaign/artist/track/pack/templates/expected_outputs/branding/smart_link/billing_context), sem segredos |
| `conftest.py` (raiz) | Fixture autouse: testes correm em **dry-run** por defeito (sem HTTP real aos renderers inexistentes); testes que precisam sobrepõem |
| `apps/content/tests/test_content_generation_job.py` | 14 testes (criação de job, payload, dry-run, idempotência, disabled, falha rastreável, billing, isolation) |
| `docs/backend_core/integracoes/resultados/prompt_04_content_request_renderer_job.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `apps/content/services.py` | `create_content_pack_request` cria/submete o job `content_generation` **após** o commit do request (`_submit_content_generation_job`); link request↔job em `metadata.external_job_id`; audit `content_pack.job_submitted`; submissão resiliente (erro não perde o request) |

Nenhuma alteração a models/migrations, billing, serializers públicos ou contratos
de API. Nenhum teste existente removido.

## 5. Comandos executados

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
ruff check .
python manage.py spectacular --file schema.yml
python -m pytest apps/content/tests/test_content_generation_job.py -q
python -m pytest -q   # suite completa
```

## 6. Resultado das validações

| Validação | Resultado |
|---|---|
| `manage.py check` | ✅ 0 issues |
| `makemigrations --check --dry-run` | ✅ No changes detected (sem alterações de modelo) |
| `ruff check .` | ✅ All checks passed |
| `spectacular` | ✅ schema gerado sem erros nem warnings |
| testes do prompt | ✅ **14 passed** |
| suite completa (`pytest`) | ✅ **300 passed**, 0 falhas |

## 7. Decisões tomadas

- **Domínio vs envelope:** `build_content_generation_payload` devolve o payload
  *de domínio*; o envelope da integrations_bridge (Prompt 02) adiciona os campos
  de transporte (`job_id`, `request_id`, `workspace_id`, `callback_url`, `entity`,
  `payload_version`). O `request_payload` guardado no job contém **todos** os
  campos exigidos pelo prompt (testado em `test_stored_envelope_has_transport_fields`).
- **Transacção segura:** request + usage + reserva de créditos + audit
  `content_pack.requested` ficam num `transaction.atomic()`; a submissão externa
  corre **fora** da transacção (uma chamada HTTP nunca deve segurar a transacção
  do request). Assim: se a criação do request falhar não há job; se a submissão
  falhar o request **não se perde**.
- **Rastreabilidade de falha:** `create_and_submit_external_job` já marca o job
  `failed`/`timeout` sem rebentar; um erro inesperado é apanhado, registado em
  `request.metadata.job_submission_error` e auditado — o request sobrevive sempre.
- **Idempotência:** `idempotency_key = content_generation:<request_id>`; reenviar
  o mesmo request reutiliza o job não-terminal (sem duplicar).
- **Estados:** `ContentPackRequest` mantém-se `queued` (não tem estado
  `submitted`); o `ExternalJobReference` reflecte `queued`/`submitted`/dry-run.
- **Sem segredos no payload:** apenas contexto de produto e `billing_context`
  não-sensível (custo, `usage_event_id`, flag de reserva) — sem saldos nem tokens.
- **Testes em dry-run por defeito:** novo `conftest.py` de raiz evita qualquer
  chamada HTTP real durante a suite (alinhado com "dry-run local enquanto os
  serviços não existem").

## 8. Pendências

- Handler de callback `content_generation` *completed/failed* (INT-303): criar
  `ContentOutput`/`Asset`, confirmar consumo / libertar créditos reservados,
  emitir notification e audit `content_pack.completed`/`.failed`.
- Resultado parcial (`partially_completed`, INT-304).
- Report e MediaKit → job + callback (INT-401..404).

## 9. Próximo passo recomendado

Prompt 05 — handler de callback de `content_generation`: ao receber `completed`,
criar `ContentOutput` e `Asset`, confirmar o consumo dos créditos reservados,
emitir `Notification` e audit; ao receber `failed`, libertar créditos e notificar.
