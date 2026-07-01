# Relatório de execução — Prompt 10: Testes E2E, hardening e documentação

- **Pipeline / Backlog:** Pipeline 10 — Integração FastAPI/Renderer (INT-701..704 + estado final)
- **Data:** 2026-06-22
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`
- **Backlog:** [`01_backlog_integracao_fastapi_renderer.md`](../01_backlog_integracao_fastapi_renderer.md)

---

## 1. Prompt executado

Criar testes end-to-end dos fluxos de integração (Content Pack / Report / Media
Kit), consolidar a segurança de callbacks e os switches dry-run/disabled, correr
coverage e documentar o estado final da integração Backend Core ↔ FastAPI/Renderer.
Sem novas features, sem FastAPI/renderer reais, sem mover lógica técnica para o
Django, sem apagar testes nem esconder falhas.

## 2. Objectivo

Fechar o MVP da fase de integração com uma rede de testes ponta-a-ponta através da
API real, e deixar a documentação de estado (contratos, settings, segurança,
exemplos) para quem implementar o FastAPI/renderer a seguir.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `tests/test_integration_e2e.py` | 12 testes E2E (Content Pack completed+idempotência+failed, Report, Media Kit, segurança de callback, dry-run/disabled) via API real |
| `docs/backend_core/integracoes/02_estado_integracao_fastapi_renderer.md` | Estado da integração (funcionalidades, fluxos, contratos, settings, endpoints, segurança, exemplos, pendências) |
| `docs/backend_core/integracoes/resultados/prompt_10_testes_hardening_documentacao.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `README.md` | Subsecção "Notas de integração (jobs externos)" + link para o estado da integração |
| `schema.yml` | Regenerado (artefacto da validação OpenAPI) |

Nenhuma alteração a models/migrations, billing ou lógica de produto. Nenhum teste
existente removido.

## 5. Comandos executados

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
ruff check .
python manage.py spectacular --file schema.yml
python -m pytest tests/test_integration_e2e.py -q
coverage run -m pytest -q
coverage report
```

## 6. Resultado das validações

| Validação | Resultado |
|---|---|
| `manage.py check` | ✅ 0 issues |
| `makemigrations --check --dry-run` | ✅ No changes detected |
| `ruff check .` | ✅ All checks passed |
| `spectacular` | ✅ schema gerado sem erros nem warnings |
| testes E2E do prompt | ✅ **12 passed** |
| suite completa (`pytest` sob coverage) | ✅ **370 passed**, 0 falhas |

## 7. Cobertura

`coverage report` (configurado em `pyproject.toml`, `source = ["apps"]`,
`branch = true`, migrations/tests omitidos):

> **Cobertura total: 90%** (4216 stmts, 321 miss; 502 branches, 110 parciais).

Cobertura dos módulos de integração:

| Módulo | Cobertura |
|---|---|
| `integrations_bridge/models.py` | 100% |
| `integrations_bridge/admin.py` | 100% |
| `integrations_bridge/permissions.py` | 100% |
| `integrations_bridge/registry.py` | 96% |
| `integrations_bridge/services.py` | 94% |
| `integrations_bridge/views.py` | 94% |
| `integrations_bridge/serializers.py` | 93% |
| `integrations_bridge/clients.py` | 91% |
| `integrations_bridge/callbacks.py` | 90% |
| `integrations_bridge/logging_utils.py` | 88% |
| `integrations_bridge/intelligence.py` | 79% |

As linhas não cobertas são sobretudo ramos defensivos (ImportError guards,
fallbacks de transporte). Os fluxos críticos ficam exercitados pelos testes E2E +
por app.

## 8. Fluxos end-to-end validados

- **Content Pack:** workspace+owner+RBAC → artista/track/campanha → POST request
  (reserva créditos) → `ExternalJobReference content_generation` (submitted) →
  callback completed → 2 `ContentOutput` + 2 `Asset` + consume créditos +
  `UsageEvent content_pack_generated` + `Notification content_ready` + audit
  `content_pack.completed`; **replay idempotente** (sem duplicar); **failed**
  liberta créditos + audit `content_pack.failed`.
- **Report:** POST report → job `report_generation` → callback completed → `Asset`
  report_pdf + `Report.storage_asset` + completed + `Notification report_ready` +
  audit; replay idempotente.
- **Media Kit:** POST media kit → job `media_kit_generation` → callback completed
  → `Asset` media_kit_asset + generated + `Notification media_kit_ready` + audit.
- **Segurança de callback:** sem token / token errado → 403; `workspace_id`
  errado → 400; `entity` errada → 400; payload inválido → 400; job terminal → 409.
- **Switches:** dry-run → job `submitted` (sem HTTP); disabled → job `queued`.

## 9. Pendências

- FastAPI Intelligence Engine e Content/Report Renderer reais (fora de escopo).
- Modelos técnicos (snapshots/moments/insights) — do FastAPI.
- Notificação técnica para admins em callbacks de Intelligence Engine (opcional).
- `LOGGING` formal em settings (handlers/formatters por ambiente).
- `content_preview` — efeitos a definir quando o renderer existir.

## 10. Riscos

- **Acoplamento ao renderer real:** mitigado por dry-run + contratos versionados +
  `ExternalJobReference` como fronteira.
- **Duplicação de efeitos em callback:** mitigado por idempotência em camadas
  (guard do dispatcher + chaves de usage/créditos/assets/notifications).
- **Perda de créditos em falha técnica:** mitigado por reserve→consume/release.
- **Segurança de callbacks:** mitigado por token constante + `workspace_id`
  obrigatório + validação de entity + logs sem segredos.
- **Fronteira analítica:** mantida — nenhuma lógica de métricas/moments/insights
  no Django (testado).

## 11. Próximo passo recomendado

Implementar o **FastAPI Intelligence Engine** e o **Content/Report Renderer**
reais contra estes contratos (envelope em `/jobs/`, callback em
`/api/v1/internal/jobs/callback/` com `X-Internal-Token` + `workspace_id`), e
ligar `request_metrics_collection` & companhia aos fluxos de produto. Em paralelo,
arrancar o frontend contra `/api/v1/` usando o schema OpenAPI.
