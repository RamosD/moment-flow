# Relatório de Execução — Hardening 06: Loop real Django → Renderer → Django (R-HARD-003)

- **Serviço:** `content_renderer`
- **Data:** 2026-06-23
- **Backlog de referência:** [`03_backlog_hardening_pos_mvp_renderer.md`](../03_backlog_hardening_pos_mvp_renderer.md) → **R-HARD-002/003**
- **Pré-requisito:** [Hardening 05 — Harness E2E PostgreSQL](prompt_hardening_05_e2e_postgres_harness.md)

---

## 1. Prompt executado

Executar e validar o loop real Django → Renderer → Django com **PostgreSQL**,
confirmando criação/actualização de `Asset`, `ContentOutput`, `Report` e
`MediaKit` via callback, em 8 cenários (completed/partial/failed + idempotência),
com **evidência** e sem declarar verde sem prova.

## 2. Objectivo

Validação funcional da integração (não apenas ambiente): provar, com PostgreSQL
multi-processo, que o renderer gera activos e o callback actualiza o Django de
forma correcta e idempotente, e que falhas controladas não deixam estado
inconsistente.

## 3. Ambiente usado

- **PostgreSQL 18** local. Docker indisponível (engine do Docker Desktop
  desligado), por isso criou-se um **cluster descartável** com os binários do
  PostgreSQL (`initdb`/`pg_ctl`), `--auth=trust`, porta **55432**, base
  `chartrex_e2e` (efémera, removida no fim). `libpq` do PostgreSQL no `PATH`
  (psycopg 3).
- `backend_core` (Django) com `DB_ENGINE=postgres`, migrado + seed
  (`seed_rbac`/`seed_billing`/`seed_content`). **Sem alterações ao backend_core.**
- `content_renderer` (`node dist/server.js`) em **:8002**; Django (`runserver`) em
  **:8010** (porta livre — ver §8); `INTERNAL_API_TOKEN` partilhado;
  `EXTERNAL_JOBS_ENABLED=true`, `EXTERNAL_JOBS_DRY_RUN=false`,
  `STORAGE_PROVIDER=local`.
- Driver: `scripts/e2e_backend_core.py` (estendido); orquestração:
  `scripts/run-e2e-localpg.ps1` (novo, sem Docker).

## 4. Dados criados

Por execução, um `User` + `Workspace` efémeros e, conforme o cenário:
`Artist`, `Campaign`, `ContentPackRequest` (pack `release_pack`), `Report`
(`weekly_report`), `MediaKit`. Cada um gera um `ExternalJobReference`
(content/report/media_kit). Workspace da execução validada:
`ccbf96f3-1f99-4a84-9ab7-9ed81eb86e5f`.

## 5. Cenários executados

| # | Cenário | Via |
|---|---|---|
| 1 | content_generation **completed** | loop real (renderer renderiza PNG + callback) |
| 2 | content_generation **partially_completed** | `pytest` backend (renderer não o produz via payload — ver §8) |
| 3 | content_generation **failed** | `pytest` backend (idem) |
| 4 | report_generation **completed** | loop real (PDF + callback) |
| 5 | report_generation **failed** | loop real (payload inválido → failed callback real) |
| 6 | media_kit_generation **completed** | loop real (PDF + callback) |
| 7 | media_kit_generation **failed** | loop real (payload inválido → failed callback real) |
| 8 | **idempotência** | loop real (re-entrega do mesmo job) |

## 6. Evidências por cenário

Saída real do driver (`e2e-logs/20260623-212357/e2e_results.json`):

| Cenário | HTTP | job_id | Estado final (Django) | Asset |
|---|---|---|---|---|
| **content completed** | 202 | `58b8c88c…4384` | `request=completed`, `job=completed`, **3 ContentOutput** | **3 Asset** PNG (`output_003.png` 52016 B, checksum ✓) |
| **idempotência** | 202 | `58b8c88c…4384` | outputs 3→3; asset ids idênticos | `no_duplicates=true` |
| **report completed** | 202 | `f9975762…b10849` | `Report=completed`, `job=completed`, `direct_probe=200` | `report.pdf` (application/pdf 1089 B, checksum ✓) |
| **report failed** | 202 | `4bfae702…64be` | `Report=failed`, `job=failed` | nenhum (`asset_linked=false`) |
| **media_kit completed** | 202 | `8abaa899…5cc0` | `MediaKit=generated`, `job=completed` | `media_kit.pdf` (application/pdf 1034 B, checksum ✓) |
| **media_kit failed** | 202 | `7e685fe8…608d` | `MediaKit=draft` (consistente), `job=failed` | nenhum (`asset_linked=false`) |

Todos os cenários do loop real: `ok=true`.

**Cenários 2 e 3 (content partial/failed)** — `pytest`
`apps/content/tests/test_content_callback.py`:
`TestPartiallyCompleted` (request `partially_completed`, 1 ContentOutput
completed + 1 failed, **1 Asset** só para o completed; créditos consumidos/
libertados conforme outputs obrigatórios) e `TestFailed` (request `failed`,
créditos libertados, sem Asset) — **passam**. A emissão de callbacks
partial/failed pelo renderer está coberta pela suite Vitest do renderer.

## 7. Resultado final

| Validação | Resultado |
|---|---|
| `npm run build` | ✅ Sem erros |
| `npm run lint` | ✅ Sem erros |
| `npm test` | ✅ **136 testes** |
| `python manage.py check` | ✅ `0 issues` |
| `pytest` (content callback + integrations_bridge + reports) | ✅ **134 passed** |
| **E2E real PostgreSQL** | ✅ 6 cenários do loop `ok=true`; 2 cenários content partial/failed via pytest |

**Critérios de aceitação:** loop validado com PostgreSQL ✅; Asset criado via
callback em content **e** report **e** media kit ✅; estados finais confirmados ✅;
idempotência validada ✅; falhas controladas sem estado inconsistente ✅; relatório
com evidências ✅.

## 8. Falhas e causas

- **`404` em TODOS os callbacks na 1.ª execução.** Causa: um **servidor Django
  antigo** (system Python, SQLite) ficou a escutar na **porta 8000** de uma
  sessão anterior. O Django do harness não conseguiu ligar a 8000 e os callbacks
  do renderer foram parar ao servidor antigo (SQLite, sem os jobs) → `404`.
  Diagnóstico: a porta 8000 estava ocupada por um PID de `C:\Python313\python.exe`
  (não o `venv` do harness); `IsInternalService` devolve `403` para token errado e
  `404` só para job inexistente — logo era a BD errada, não auth. **Correcção:**
  correr o Django do harness numa porta livre (`-DjangoPort 8010`), com
  `BACKEND_PUBLIC_BASE_URL` a apontar para essa porta (o `callback_url` do
  envelope passa a apontar para o servidor certo). Repetida a execução → todos os
  cenários `ok=true`. **Não foi mascarada** — está documentada no guia §10.
- **psycopg sem `libpq`.** `Error loading psycopg ... libpq library not found`.
  Causa: o `libpq.dll` do PostgreSQL não estava no `PATH`. Correcção: adicionar
  `C:\Program Files\PostgreSQL\18\bin` ao `PATH` (feito pelo harness).
- **Docker indisponível** (engine desligado) → usou-se o cluster local com os
  binários do PostgreSQL (sem Docker), igualmente PostgreSQL real.

## 9. Pendências

- `content_generation` **partially_completed/failed** não é reproduzível pelo
  **loop real** via payload (o renderer cai sempre em fallback `completed`). Para
  o exercitar ponta-a-ponta seria preciso injectar uma falha de storage/render no
  renderer — fora do âmbito; está coberto por `pytest` (Django) + Vitest (renderer).
- Harness depende de um PostgreSQL a correr (Docker ou cluster local). Não há
  ainda automação para o iniciar quando o Docker está desligado (documentado no
  guia §9).
- Limpeza de dados E2E: a base do cluster local é descartável (removida no fim);
  o harness Docker usa `tmpfs` + `down -v`.

## 10. Próximo passo recomendado

Avançar para **R-HARD-007 (coverage Vitest)** e **R-HARD-008 (documentação final
pós-hardening)**. O loop Django ↔ Renderer está **verde com PostgreSQL**, pelo que
a recomendação do backlog (§11) — avançar para o FastAPI Intelligence Engine — fica
desbloqueada após o coverage e a documentação final.
