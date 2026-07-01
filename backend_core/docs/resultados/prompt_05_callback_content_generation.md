# Relatório de execução — Prompt 05: Callback de content_generation

- **Pipeline / Backlog:** Pipeline 05 — Integração FastAPI/Renderer (INT-303, INT-304)
- **Data:** 2026-06-22
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`
- **Backlog:** [`01_backlog_integracao_fastapi_renderer.md`](../01_backlog_integracao_fastapi_renderer.md)

---

## 1. Prompt executado

Implementar o handler **real** de callback para `content_generation`: ao receber
`completed`/`partially_completed`/`failed`, produzir efeitos de produto no Django —
actualizar `ContentPackRequest` e `ContentOutput`, criar `Asset` (metadados),
confirmar consumo / libertar créditos reservados, registar `UsageEvent`, emitir
`Notification` e `AuditEvent` — de forma **idempotente**. Sem renderer, sem
ficheiros reais, sem chamadas externas, sem métricas/insights.

## 2. Objectivo

Fechar o ciclo *pedido → job → callback → outputs/assets/billing/notification/
audit* para content packs, mantendo a fronteira (o Django só transforma o
resultado reportado em estado de produto) e garantindo que um callback repetido
nunca duplica efeitos.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/content/callbacks.py` | Efeitos de produto do callback `content_generation` (success/partial/failed), shape de `result` documentado, idempotência por chaves |
| `apps/content/tests/test_content_callback.py` | 9 testes end-to-end (completed, failed, repeated, partial, regra de créditos, workspace/entity rejeitados) |
| `docs/backend_core/integracoes/resultados/prompt_05_callback_content_generation.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `apps/integrations_bridge/callbacks.py` | `handle_content_generation_callback` delega no content app; `content_preview` passa a ter handler próprio (thin, sem efeitos de produto) |

Nenhuma alteração a models/migrations, nem a billing/notifications/audit (apenas
consumo dos seus serviços). Nenhum teste existente removido.

## 5. Shape esperado de `result` (completed / partially_completed)

```json
{
  "outputs": [
    {
      "output_type": "post", "format": "png", "status": "completed",
      "title": "...", "caption": "...", "cta": "...",
      "required": true, "template_key": "system_post",
      "asset": {
        "storage_provider": "s3", "bucket": "...", "storage_key": "...",
        "file_name": "...", "mime_type": "image/png",
        "file_size_bytes": 12345, "width": 1080, "height": 1080,
        "duration_seconds": null, "checksum": "..."
      },
      "metadata": {}
    }
  ]
}
```

## 6. Comandos executados

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
ruff check .
python manage.py spectacular --file schema.yml
python -m pytest apps/content/tests/test_content_callback.py -q
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
| suite completa (`pytest`) | ✅ **309 passed**, 0 falhas |

## 8. Decisões tomadas

- **Lógica de produto no content app:** `apps/content/callbacks.py` faz os efeitos;
  o `integrations_bridge` mantém-se genérico e apenas delega (import lazy, sem
  ciclo). `content_preview` ganhou handler próprio para não criar outputs/créditos.
- **Idempotência em duas camadas:** (1) o dispatcher já bloqueia o re-dispatch
  quando o job está terminal (callback repetido devolve 200 sem reexecutar); (2)
  cada efeito é chaveado — `content_pack_generated:<id>` (usage),
  `content_pack_consume:<id>` / `content_pack_release:<id>` (créditos),
  `external_output_key` por output (sem Asset/Output duplicado), e um guard de
  `event` por notificação. Não se relaxou idempotência para passar testes.
- **Asset:** criado só para outputs `completed` com bloco `asset` e sem
  `storage_asset` ainda; `ContentOutput.storage_asset` é ligado.
- **Transaccional:** os efeitos de cada callback correm em `transaction.atomic()`.
- **Sem dados sensíveis em logs:** apenas ids; o token nunca é tocado aqui.

## 9. Regra de créditos em partial success

- `completed` → **consumir** (settle dos créditos reservados).
- `partially_completed`:
  - se **pelo menos um output obrigatório** (`required: true`) ficou `completed`
    → **consumir**;
  - se **todos os obrigatórios falharam** → **libertar**;
  - se não há `required` identificável → consumir se algum output ficou
    `completed`, caso contrário libertar.
- `failed` → **libertar** sempre (a falha técnica não cobra o cliente).

Implementado em `_should_consume(status, outputs)` e testado em
`test_partial_consumes_when_required_succeeds` /
`test_partial_releases_when_all_required_fail`.

## 10. Pendências

- Report e MediaKit → job + callback (INT-401..404).
- Contratos/placeholders do Intelligence Engine (metrics/moment/insight) — handlers
  placeholder já existem (Prompt 03); falta o detalhe de payloads (INT-501..503).
- Reprocessamento/limpeza de assets em retry (fora do âmbito).

## 11. Próximo passo recomendado

Prompt 06 — ligar `Report` e `MediaKit` à criação de `ExternalJobReference`
(`report_generation` / `media_kit_generation`) e respectivos builders de payload,
seguidos dos handlers de callback que criam `Asset` (report_pdf / media_kit_asset)
e emitem notification/audit.
