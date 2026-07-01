# Relatório de execução — Prompt 03: Callback normalizado, dispatcher e idempotência

- **Pipeline / Backlog:** Pipeline 03 — Integração FastAPI/Renderer (INT-201, INT-202, INT-203)
- **Data:** 2026-06-22
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`
- **Backlog:** [`01_backlog_integracao_fastapi_renderer.md`](../01_backlog_integracao_fastapi_renderer.md)

---

## 1. Prompt executado

Normalizar o callback interno (contrato `job_id`/`workspace_id`/`status`/`entity`/
`result`/`error`/`metadata`), implementar um `callback_dispatcher` por `job_type`
com handlers (content/report/media-kit + placeholders de metrics/moment/insight/
recommendation) e garantir idempotência de callbacks. Nesta fase os handlers
apenas actualizam o job e devolvem estrutura controlada — sem criar outputs/
assets, sem consumir créditos e sem lógica analítica. Sem expor o token.

## 2. Objectivo

Tornar o endpoint de callback genérico, seguro e idempotente, encaminhando cada
callback para o handler do seu `job_type`, preparando (sem executar) os efeitos
de produto das fases seguintes.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/integrations_bridge/callbacks.py` | `callback_dispatcher` + handlers por job_type (renderers + placeholders + fallback seguro) |
| `apps/integrations_bridge/tests/test_callback_dispatcher.py` | 17 testes: validação, segurança, dispatch, idempotência e placeholders |
| `docs/backend_core/integracoes/resultados/prompt_03_callback_dispatcher_idempotencia.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `apps/integrations_bridge/serializers.py` | `JobCallbackSerializer` normalizado (`job_id`/`workspace_id`/`entity`/`result`/`error`) + `CallbackEntitySerializer`, mantendo compatibilidade com a forma legada (`job`/`error_message`) |
| `apps/integrations_bridge/views.py` | Validação de workspace/entity, persistência de `callback_payload`/`callback_received_at`, idempotência (no-op em estado igual, 409 em terminal incompatível) e dispatch |
| `apps/integrations_bridge/services.py` | `apply_job_callback` define `started_at` e trata os novos estados |
| `config/settings.py` | `ENUM_NAME_OVERRIDES["ExternalJobStatusEnum"]` actualizado para os 9 estados (evita colisão de enum no OpenAPI) |

## 5. Comandos executados

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
ruff check .
python manage.py spectacular --file schema.yml
python -m pytest apps/integrations_bridge -q
```

## 6. Resultado das validações

| Validação | Resultado |
|---|---|
| `manage.py check` | ✅ 0 issues |
| `makemigrations --check --dry-run` | ✅ No changes detected (sem novos models) |
| `ruff check .` | ✅ All checks passed |
| `spectacular` | ✅ schema gerado sem erros nem warnings |
| testes do prompt | ✅ **17 passed** |
| suite integrations_bridge | ✅ **61 passed** |
| **suite completa** (`pytest`) | ✅ **286 passed** (235 baseline + 51 novos), 0 falhas |

## 7. Decisões tomadas

- **Compatibilidade retroactiva:** o serializer aceita `job_id` (novo) e `job`
  (legado), `error.message` e `error_message`. `workspace_id`/`entity` só são
  validados **quando fornecidos**, para não quebrar os testes/contratos
  existentes (restrição "não quebrar callback interno existente").
- **Códigos de resposta:** token ausente/errado/vazio → **403** (camada de
  permissão); payload inválido / `workspace_id` ou `entity` incompatível → **400**;
  job inexistente → **404**; callback repetido (mesmo estado) → **200** sem
  repetir efeitos; job terminal com estado diferente → **409**.
- **Idempotência por estado:** o efeito (transição + audit) só corre na primeira
  transição efectiva; um replay do mesmo estado devolve 200 sem novo audit.
- **Persistência do callback antes do dispatch:** `callback_payload` e
  `callback_received_at` são gravados antes de chamar o handler.
- **Placeholders sem lógica analítica:** metrics/moment/insight/recommendation
  apenas guardam o callback, transitam o estado e registam audit
  `<job_type>.callback_received` — nenhum cálculo em Django.
- **Fallback seguro:** `job_type` sem handler dedicado (ex.: `video_rendering`)
  não quebra o endpoint (`callback_unhandled`, `handled=False`).

## 8. Pendências

- Handlers de content/report/media-kit ainda **não** criam outputs/assets nem
  mexem em créditos/notifications (INT-303/304/402/404, fases seguintes).
- Ligação dos fluxos de produto (`ContentPackRequest`/`Report`/`MediaKit`) à
  submissão e ao callback.

## 9. Próximo passo recomendado

Prompt 04 — ligar `ContentPackRequest` à criação de `ExternalJobReference`
(`content_generation`) e definir o builder de payload, seguido do handler de
callback que cria `ContentOutput`/`Asset` e trata créditos/notifications.
