# Relatório de execução — Prompt 01: Settings, cliente interno e service registry

- **Pipeline / Backlog:** Pipeline 01 — Integração FastAPI/Renderer (INT-001, INT-002, INT-003)
- **Data:** 2026-06-22
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`
- **Backlog:** [`01_backlog_integracao_fastapi_renderer.md`](../01_backlog_integracao_fastapi_renderer.md)

---

## 1. Prompt executado

Implementar a base de configuração e comunicação interna entre o Backend Core
Django/DRF e os serviços técnicos externos futuros (FastAPI Intelligence Engine,
Content Renderer, Report Renderer, Video Renderer futuro): variáveis de ambiente,
settings via `python-decouple` sem segredos hardcoded, cliente HTTP interno
reutilizável com headers internos e tratamento de erros, e um service registry
que resolve provider/base_url/timeout por `job_type`. Sem renderer/FastAPI/Celery
reais, sem mover lógica analítica para o Django, sem expor o `INTERNAL_API_TOKEN`.

## 2. Objectivo

Preparar a orquestração segura (configuração + transporte + resolução de
serviço) que os prompts seguintes usam para submeter jobs externos, mantendo a
fronteira *Django governa o produto; FastAPI calcula e executa; Renderer gera
activos*.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/integrations_bridge/registry.py` | Service registry: `job_type → provider`, resolução de `base_url`/`timeout`, `callback_url()` e switches `external_jobs_enabled/dry_run/should_submit_externally` |
| `apps/integrations_bridge/clients.py` | `InternalServiceClient` (stdlib `urllib`), headers internos obrigatórios, exceções tipadas (timeout/HTTP/indisponível/JSON inválido), transporte injectável |
| `apps/integrations_bridge/tests/test_settings_client_registry.py` | 24 testes: settings, registry, headers, sucesso, timeout, erro HTTP, indisponível, JSON inválido, dry-run e token nunca logado |
| `docs/backend_core/integracoes/resultados/prompt_01_settings_cliente_registry.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `config/settings.py` | Bloco de settings de integração via `decouple` (URLs, timeouts, callback path, switches); nota de segredo no `INTERNAL_API_TOKEN` |
| `.env.example` | Documentação das novas variáveis de integração |

## 5. Variáveis adicionadas

```text
BACKEND_PUBLIC_BASE_URL=http://localhost:8000
INTELLIGENCE_ENGINE_BASE_URL=http://localhost:8001
INTELLIGENCE_ENGINE_TIMEOUT_SECONDS=20
CONTENT_RENDERER_BASE_URL=http://localhost:8002
CONTENT_RENDERER_TIMEOUT_SECONDS=30
REPORT_RENDERER_BASE_URL=http://localhost:8003
REPORT_RENDERER_TIMEOUT_SECONDS=30
INTERNAL_CALLBACK_PATH=/api/v1/internal/jobs/callback/
EXTERNAL_JOBS_ENABLED=true
EXTERNAL_JOBS_DRY_RUN=false
```

`INTERNAL_API_TOKEN` (já existente) foi mantido e marcado como segredo (nunca
logado nem exposto em schema/relatório).

## 6. Comandos executados

```powershell
python manage.py check
ruff check .
python manage.py spectacular --file schema.yml
python -m pytest apps/integrations_bridge/tests/test_settings_client_registry.py -q
```

## 7. Resultado das validações

| Validação | Resultado |
|---|---|
| `manage.py check` | ✅ 0 issues |
| `ruff check .` | ✅ All checks passed |
| `spectacular` | ✅ schema gerado sem erros nem warnings |
| testes do prompt | ✅ **24 passed** |
| suite integrations_bridge | ✅ **61 passed** (inclui prompts 02/03 e testes existentes) |
| suite completa (`pytest`) | ✅ **286 passed**, 0 falhas |

## 8. Decisões tomadas

- **Sem dependência nova:** o cliente usa a stdlib (`urllib.request`) em vez de
  `requests`/`httpx` — nenhum pacote foi adicionado a `requirements.txt`.
- **Transporte injectável (`opener`):** permite testar sucesso/timeout/erro sem
  qualquer chamada de rede real.
- **Token só em headers, nunca logado:** o logger regista `job_id`, `request_id`,
  URL e status — nunca headers/token (teste `test_token_never_logged`).
- **Providers canónicos:** `intelligence_engine`, `content_renderer`,
  `report_renderer` — alinhados com as choices do modelo em Prompt 02.
- **Settings lidas lazily** no registry (não no import) para respeitar overrides
  de settings em testes.

## 9. Pendências

- Ligar o registry/cliente à submissão real de jobs (Prompt 02 — `create_and_submit_external_job`).
- `video_renderer` fica como provider futuro (não mapeado nesta fase).

## 10. Próximo passo recomendado

Prompt 02 — evoluir `ExternalJobReference` (payloads, request_id, idempotency_key,
retry_count, novos estados) e implementar `create_and_submit_external_job` usando
este registry e cliente.
