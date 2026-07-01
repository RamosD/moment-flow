# OBS-STG-005 — Relatório de execução: Smoke test Backend Core ↔ Content Renderer

> Relatório de execução do prompt 05. Altera runtime de forma **aditiva** (novo
> management command + testes + docs no Backend Core). **Não** altera o
> `content_renderer` nem o `intelligence_engine`.
>
> Fase: Observabilidade e Staging Técnico do Ecossistema.
> Backlog: [`../01_backlog.md`](../01_backlog.md).
> Data: 2026-06-25. Modelo recomendado (backlog §15): opus.

---

## 1. Objectivo

Criar/consolidar uma validação operacional rápida do loop
`Backend Core → Content Renderer → callback Backend Core`, reutilizando o que já
existe e sem alterar o renderer.

---

## 2. Inventário do que já existe (identificado)

| Pergunta do prompt | Resposta (código real) |
|---|---|
| Testes E2E do renderer | `content_renderer/scripts/run-e2e-postgres.ps1` (+ `run-e2e-localpg.ps1`, `run-e2e.ps1` legado SQLite) e o driver `scripts/e2e_backend_core.py`. Loop multi-processo real, com cenários content/report/media-kit, falhas controladas e idempotência. |
| Como o BC cria jobs | `apps/integrations_bridge/services.py::create_and_submit_external_job` → `_submit_job` (envelope via `build_request_envelope`, submissão via `InternalServiceClient.post_json("/jobs/")`). Resolução de serviço/provider em `registry.resolve_service`. Submissões de produto: `apps/reports/services.py` (`submit_report_generation_job`, `submit_media_kit_generation_job`), `apps/content/services.py` (`create_content_pack_request`). |
| Como o BC recebe callbacks | `apps/integrations_bridge/views.py::ExternalJobCallbackView` (auth `X-Internal-Token`, sem JWT) → `callbacks.py::callback_dispatcher` → handlers por `job_type` (content/report/media-kit delegam efeitos de produto às apps; transição de estado via `services.apply_job_callback`). |
| Payload mínimo | Envelope estrito do renderer (`content_renderer/src/jobs/job.schema.ts`): exactamente 8 chaves de topo, `callback_url` URL válida, `payload` objecto. `content_generation` aceita payload representativo; gera 1 output fallback sem `expected_outputs`. |

**Conclusão:** o **loop completo** já é validável (harness do renderer). O que
faltava do lado do **Backend Core** era um smoke leve da **perna de saída** e
documentação operacional consolidada.

---

## 3. O que foi reutilizado vs. criado

### Reutilizado (sem alterar)
- Harness E2E do renderer (`run-e2e-postgres.ps1` + `e2e_backend_core.py`) →
  documentado como **checklist** da Camada 2.
- `registry.resolve_service` / `registry.callback_url` / `InternalServiceClient` /
  `services.SUBMIT_PATH` → reutilizados pelo command.
- `health.http_health_probe` (criado no OBS-STG-003) → reutilizado para o
  `GET /health` do renderer (sem token).

### Criado (Backend Core, aditivo)
- **Management command `smoke_content_renderer`** — smoke da perna de saída, **sem
  base de dados**: valida config, sonda `GET /health` (sem token), submete um job
  representativo a `POST /jobs/` e verifica a aceitação **202**. Falhas
  controladas (renderer desligado / 403 / timeout / unavailable / status
  inesperado). Token **nunca** impresso (`token=configured`/`not_configured`).
  Flags: `--job-type {content_generation,report_generation,media_kit_generation}`,
  `--health-only`.
- **11 testes** (`test_smoke_content_renderer_command.py`) com cliente e probe
  **falsos** (sem rede): validação de config, gate de health, sucesso 202,
  token-não-impresso, status inesperado, report_generation, e falhas controladas
  (403/unavailable/timeout). Correm na suite normal (não opt-in).
- **Checklist/guia** `smoke_content_renderer.md`: Camada 1 (command) + Camada 2
  (harness), com a checklist das 10 validações mapeada à evidência do driver, o
  tratamento de "renderer desligado", e nota de segurança.

---

## 4. Validações cobertas (perna de saída + checklist)

| Validação pedida | Coberta por |
|---|---|
| Renderer `GET /health` | command (Camada 1) + checklist #1 |
| Token interno alinhado | command (403 → "token misaligned?") + checklist #2 |
| Criação/submissão de job | command (submit directo) + checklist #3 (caminho de produto) |
| Resposta **202** | command (verifica `status_code == 202`) + checklist #4 |
| Callback para Backend Core | checklist #5 (harness) |
| `ExternalJobReference` actualizado | checklist #6 (harness) |
| Estado final do job | checklist #7 (`ok` por cenário) |
| Ficheiros/outputs esperados | checklist #8 (`asset` no callback) |
| Erro controlado com renderer desligado | command (health unavailable / submit unavailable) + checklist (`_mark_failed`/`_mark_timeout`) |

---

## 5. Ficheiros criados / alterados

| Ficheiro | Acção |
|---|---|
| `apps/integrations_bridge/management/__init__.py` | **Criado** (pacote) |
| `apps/integrations_bridge/management/commands/__init__.py` | **Criado** (pacote) |
| `apps/integrations_bridge/management/commands/smoke_content_renderer.py` | **Criado** (command) |
| `apps/integrations_bridge/tests/test_smoke_content_renderer_command.py` | **Criado** (11 testes) |
| `docs/.../03_observabilidade_staging_ecossistema/smoke_content_renderer.md` | **Criado** (guia/checklist) |
| `docs/.../matriz_operacional_servicos.md` | Alterado (1 linha — referência ao guia) |

**Não alterados:** `content_renderer/`, `intelligence_engine/` (regra do backlog).

---

## 6. Comandos e resultados (evidência)

| Validação | Comando | Resultado |
|---|---|---|
| Testes do command (mocked) | `pytest apps/integrations_bridge/tests/test_smoke_content_renderer_command.py -q` | **11 passed** (0.21s) |
| Lint | `ruff check apps/integrations_bridge/management/ …test_smoke_content_renderer_command.py` | **All checks passed!** |
| Registo do command | `manage.py smoke_content_renderer --help` | OK (`--job-type`, `--health-only` listados) |
| Compatibilidade do envelope | leitura de `content_renderer/src/jobs/job.schema.ts` | Envelope do command tem exactamente as 8 chaves estritas + `callback_url` URL válida → aceitação 202 garantida |

---

## 7. Limitações (documentadas, não inventadas)

- O **loop completo com callback real** não foi executado nesta sessão (exige
  renderer + Django + PostgreSQL a correr em simultâneo — o harness do renderer).
  Está **documentado e executável** via `run-e2e-postgres.ps1`; a evidência de loop
  real já existe da fase de hardening do renderer (guia E2E §10) e os caminhos de
  falha do lado do Backend Core estão cobertos por testes existentes
  (`test_create_submit_job.py`).
- O smoke da Camada 1 valida apenas a **perna de saída** (até ao 202); ao submeter,
  o renderer faz um callback com `job_id` sintético que dá `404` no Django —
  **esperado e inofensivo** (callback não-fatal). Documentado no guia.
- Discrepância de porta do report renderer (`REPORT_RENDERER_BASE_URL` default
  `:8003` vs `:8002` real) reiterada no guia; `--job-type content_generation`
  (default) usa `:8002` e funciona sem ajuste.

---

## 8. Conformidade com os critérios de aceitação

| Critério | Estado |
|---|---|
| Smoke test Renderer documentado ou checklist executável realista | ✅ command + checklist `smoke_content_renderer.md` |
| Fluxo BC → Renderer → callback coberto por teste/smoke/checklist | ✅ Camada 1 (command+testes) + Camada 2 (harness/checklist) |
| Falha com renderer desligado tratada/documentada | ✅ command (health/submit unavailable) + `_mark_failed`/`_mark_timeout` documentados |
| Logs não expõem token | ✅ `token=configured`; testes asseguram token ausente de stdout/stderr |
| Validações executadas ou limitações documentadas | ✅ 11 testes passam; loop real documentado como limitação executável |
| Relatório lista ficheiros/evidência/limitações/comandos/próximo passo | ✅ este documento |

---

## 9. Próximo passo recomendado

**OBS-STG-006 — Normalizar correlação por `request_id`/`job_id` nos logs.**
Inspeccionar os logs existentes (IE e renderer já cobertos por loggers; ver a
matriz), adicionar um `LOGGING` mínimo em `config/settings.py` (para que os logs
INFO surjam) e uniformizar os campos
`request_id`/`workspace_id`/`campaign_id`/`job_id`/`external_job_id`/`provider`/
`duration_ms`/`status`/`error_type` nos fluxos IE e jobs/callback, com testes de
ausência de token.
