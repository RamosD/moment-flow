# Relatório de execução — Prompt 07: Callbacks de report e media kit

- **Pipeline / Backlog:** Pipeline 07 — Integração FastAPI/Renderer (INT-402, INT-404)
- **Data:** 2026-06-22
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`
- **Backlog:** [`01_backlog_integracao_fastapi_renderer.md`](../01_backlog_integracao_fastapi_renderer.md)

---

## 1. Prompt executado

Implementar os handlers de callback para `report_generation` e
`media_kit_generation`: em `completed` criar `Asset` e ligar
`Report.storage_asset` / `MediaKit.storage_asset`, marcar estado final, emitir
`Notification` e `AuditEvent`; em `failed` registar o erro e notificar — tudo
**idempotente**. Sem gerar PDF/ficheiro real, sem renderer, sem página pública,
sem email, sem relaxar as validações de callback.

## 2. Objectivo

Fechar o ciclo *pedido → job → callback → asset/estado/notification/audit* para
reports e media kits, mantendo a fronteira (o Django só transforma o resultado
reportado em estado de produto) e a idempotência de callbacks repetidos.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/reports/callbacks.py` | Efeitos de produto dos callbacks `report_generation` / `media_kit_generation` (completed/failed), shape de `result` documentado, idempotência por chaves |
| `apps/reports/tests/test_report_media_kit_callbacks.py` | 9 testes end-to-end (completed, failed, duplicado, workspace/entity mismatch, payload inválido) |
| `docs/backend_core/integracoes/resultados/prompt_07_callbacks_reports_media_kits.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `apps/integrations_bridge/callbacks.py` | `handle_report_generation_callback` / `handle_media_kit_generation_callback` delegam no reports app (import lazy, sem ciclo) |
| `apps/integrations_bridge/tests/test_callback_dispatcher.py` | 3 testes de placeholder genérico migrados de `report_generation` para `metrics_collection` (report/media_kit deixaram de ser placeholders) |

Nenhuma alteração a models/migrations, billing ou notifications. Nenhum teste
existente removido.

## 5. Shape esperado de `result` (completed)

```json
{
  "asset": {
    "title": "June Recap", "format": "pdf",
    "storage_provider": "s3", "bucket": "...", "storage_key": "...",
    "file_name": "report.pdf", "mime_type": "application/pdf",
    "file_size_bytes": 23456, "checksum": "...", "metadata": {}
  },
  "metadata": {}
}
```

O bloco do asset pode vir no topo de `result` ou sob `"asset"` (ambos suportados).

## 6. Comandos executados

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
ruff check .
python manage.py spectacular --file schema.yml
python -m pytest apps/reports apps/integrations_bridge -q
python -m pytest -q   # suite completa
```

## 7. Resultado das validações

| Validação | Resultado |
|---|---|
| `manage.py check` | ✅ 0 issues |
| `makemigrations --check --dry-run` | ✅ No changes detected (sem alterações de modelo) |
| `ruff check .` | ✅ All checks passed |
| `spectacular` | ✅ schema gerado sem erros nem warnings |
| testes do prompt | ✅ **9 passed** |
| suite completa (`pytest`) | ✅ **328 passed**, 0 falhas |

## 8. Decisões tomadas

- **Asset de report → `REPORT_PDF`:** o modelo `Asset` não tem um tipo
  `report_html` e adicioná-lo seria uma alteração de modelo (migration). Para
  respeitar "não alterar modelo sem necessidade", reports PDF **e** HTML usam
  `REPORT_PDF`, preservando o `format`/`mime_type` reais nos campos do asset e em
  `metadata`. Asset de media kit usa `MEDIA_KIT_ASSET`.
- **`Report` sem campo `error_message`:** o erro é guardado em
  `Report.metadata["error"]` (o estado passa a `failed`).
- **`MediaKit` sem estado `failed`:** a falha é registada em
  `MediaKit.metadata` (`generation_status="failed"`, `error=<msg>`), mantendo o
  estado `draft`; o `ExternalJobReference` fica `failed` e há notification + audit.
  Rastreabilidade garantida sem alterar o modelo.
- **Lógica de produto no reports app:** `apps/reports/callbacks.py` faz os efeitos;
  o `integrations_bridge` mantém-se genérico e delega (resolução de entidade
  protegida contra UUID inválido).
- **Idempotência em camadas:** (1) o dispatcher bloqueia o re-dispatch quando o
  job está terminal; (2) o `Asset` só é criado quando a entidade ainda não tem
  `storage_asset`; (3) a `Notification` é protegida por um guard de `event`. Não
  se relaxou nenhuma validação de callback.
- **Notifications:** `report_ready` (`REPORT_READY`) / `media_kit_ready`
  (`MEDIA_KIT_READY`); falhas usam `SYSTEM` com `event` em `metadata`.

## 9. Pendências

- Contratos/payloads e handlers definitivos do Intelligence Engine
  (`metrics_collection` / `moment_detection` / `insight_generation` /
  `recommendation_generation`) — handlers placeholder existem (Prompt 03), falta o
  detalhe (INT-501..503).
- Testes end-to-end transversais (INT-701..704) e hardening final da fase de
  integração (logs estruturados, retries, admin de jobs — INT-602/603/604).

## 10. Próximo passo recomendado

Prompt 08 — definir os contratos/payloads placeholder do Intelligence Engine
(`metrics_collection`, `moment_detection`, `insight_generation`,
`recommendation_generation`): builders de payload e confirmação dos handlers
placeholder (guardar `callback_payload`, audit simples), **sem** lógica analítica
no Django.
