# Smoke test / checklist — Backend Core ↔ Content Renderer

> Como validar o loop **Backend Core → Content Renderer → callback Backend Core**
> (OBS-STG-005).
>
> São **duas camadas** complementares:
> 1. **Smoke da perna de saída** (rápido, sem base de dados) — um *management
>    command* que valida health + token + aceitação **202**.
> 2. **Loop completo assíncrono** (callback → `ExternalJobReference` → `Asset`) —
>    o harness E2E multi-processo **já existente** no repositório do renderer,
>    aqui descrito como checklist operacional.
>
> O token interno **nunca** aparece em logs/saída. Os exemplos usam o placeholder
> `<DEV_TOKEN>` — **nunca** um valor real.

---

## 1. Pré-condições

| Variável (Backend Core) | Valor |
|---|---|
| `INTERNAL_API_TOKEN` | **não vazio**; o **mesmo** valor no renderer |
| `CONTENT_RENDERER_BASE_URL` | URL do renderer (`http://localhost:8202`) |
| `REPORT_RENDERER_BASE_URL` | `http://localhost:8202` (renderer único serve report/media-kit na mesma porta) |
| `EXTERNAL_JOBS_ENABLED` | `True` (loop completo) |
| `EXTERNAL_JOBS_DRY_RUN` | `False` (loop completo) |
| `BACKEND_PUBLIC_BASE_URL` | `http://localhost:8100` (base do `callback_url`) |

Renderer (mesmo token):

```powershell
cd content_renderer
$env:INTERNAL_API_TOKEN="<DEV_TOKEN>"; $env:PORT="8202"; $env:NODE_ENV="development"
npm run build; npm start    # ou: npm run dev
```

---

## 2. Camada 1 — Smoke da perna de saída (command, sem base de dados)

Valida que o Backend Core, com a sua configuração actual, **chega** ao renderer,
está **alinhado no token** e o renderer **aceita** o job (202). Não escreve na base
de dados do Backend Core.

```powershell
cd backend_core
$env:INTERNAL_API_TOKEN="<DEV_TOKEN>"
$env:CONTENT_RENDERER_BASE_URL="http://localhost:8202"
venv/Scripts/python.exe manage.py smoke_content_renderer
# só health, sem despoletar render:
venv/Scripts/python.exe manage.py smoke_content_renderer --health-only
# outros tipos (usam REPORT_RENDERER_BASE_URL → apontar para :8202):
venv/Scripts/python.exe manage.py smoke_content_renderer --job-type report_generation
```

**Saída de sucesso** (o token nunca aparece):

```text
smoke_renderer config job_type=content_generation provider=content_renderer base_url=http://localhost:8202 token=configured timeout_s=30 external_jobs_enabled=True external_jobs_dry_run=False
smoke_renderer health provider=content_renderer base_url=http://localhost:8202 status=ok duration_ms=8
smoke_renderer submit job_id=<hex> request_id=<hex> job_type=content_generation
smoke_renderer ok {"status_code": 202, "ack_status": "accepted", "job_id": "<hex>", "job_type": "content_generation", "renderer": "content_renderer"}
note: the renderer renders in the background and will POST a callback; this command verifies only the 202 acceptance ...
```

**O que cobre:** renderer `GET /health` · token interno alinhado · submissão de job ·
resposta **202**. **O que NÃO cobre:** callback, `ExternalJobReference`, `Asset`
(é a perna assíncrona — Camada 2).

> Nota: ao submeter (sem `--health-only`), o renderer renderiza em background e
> **tenta** um callback para `callback_url`. Como o `job_id` é sintético e não
> existe na base de dados do Backend Core, esse callback resulta em `404` no
> Django (ou falha de ligação se o servidor não estiver a correr) — **esperado e
> inofensivo** (o callback do renderer é não-fatal). O 202 é o que este smoke
> valida.

**Falhas controladas** (exit ≠ 0, sem stack trace, sem token):

| Situação | Mensagem |
|---|---|
| Token vazio | `INTERNAL_API_TOKEN is empty — … 403 … Smoke failed.` |
| Base URL não configurada | `Provider '…' … has no base URL configured. Smoke failed.` |
| **Renderer desligado** (`GET /health` inacessível) | `Renderer /health is 'unavailable' (connection_error). Smoke failed.` |
| Token desalinhado (renderer devolve 403) | `Renderer rejected the job with HTTP 403 (token misaligned?). Smoke failed.` |
| Timeout a aceitar | `Renderer timed out accepting the job. Smoke failed.` |
| Indisponível ao submeter | `Renderer is unavailable (cannot submit the job). Smoke failed.` |

---

## 3. Camada 2 — Loop completo (harness E2E existente)

O **loop real** (job → 202 → render → storage → **callback** → Django cria/actualiza
`Asset` + entidade) é cross-process e exige uma base de dados partilhável entre
processos (**PostgreSQL** — o SQLite não vê linhas commitadas por outro processo, o
callback dá 404). Está **já implementado** no repositório do renderer e não deve
ser duplicado:

```powershell
cd content_renderer
npm run build
powershell -ExecutionPolicy Bypass -File scripts\run-e2e-postgres.ps1
# manter os serviços de pé para inspecção:
powershell -ExecutionPolicy Bypass -File scripts\run-e2e-postgres.ps1 -KeepUp
# sem Docker, contra um PostgreSQL local:
powershell -ExecutionPolicy Bypass -File scripts\run-e2e-localpg.ps1
```

O harness: sobe PostgreSQL efémero, migra+seed, arranca renderer (8002) e Django
(8000) com o **mesmo token**, espera readiness (`/health` do renderer;
`/api/v1/schema/` do Django) e corre o driver `scripts/e2e_backend_core.py`, que
exercita os cenários e imprime um JSON com `ok` por cenário; a evidência fica em
`content_renderer/e2e-logs/<timestamp>/`.

### Checklist de validação (mapeada à evidência do driver)

| # | Validação | Onde verificar |
|---|---|---|
| 1 | Renderer `GET /health` responde `ok` | `renderer_up=True` no output do harness |
| 2 | Token interno alinhado nos dois processos | mesmo `INTERNAL_API_TOKEN`; ausência de `403` |
| 3 | Backend Core cria/submete job | `ExternalJobReference` criado (driver semeia em DRY-RUN e faz de *submitter*) |
| 4 | Resposta **202** do renderer | `renderer_http_status: 202` por cenário |
| 5 | Callback chega ao Backend Core | `report_status/media_kit_status/request_status` finalizado |
| 6 | `ExternalJobReference` actualizado | `job_status: completed` (ou `failed` nos cenários de falha) |
| 7 | Estado final do job correcto | `ok: true` por cenário no JSON do driver |
| 8 | Ficheiros/outputs esperados | `asset` (storage_key/checksum/mime) preenchido; ficheiro em `LOCAL_STORAGE_ROOT` |
| 9 | Erro controlado (payload inválido) | cenários `*_failed`: `report_status: failed` / job `failed`, sem asset |
| 10 | Idempotência | cenário content: `idempotency.no_duplicates: true` |

### Renderer desligado (degradação controlada)

- **Antes de submeter:** o smoke da Camada 1 (`smoke_content_renderer`) reporta
  `Renderer /health is 'unavailable'` e sai com erro — diagnóstico imediato.
- **No caminho de produto** (submissão real via `create_and_submit_external_job`):
  se o renderer estiver inacessível/timeout, o Backend Core marca o
  `ExternalJobReference` como `failed`/`timeout` (ver `services._submit_job` →
  `_mark_failed` / `_mark_timeout`) e regista um log de job — **nunca** uma
  excepção não tratada. (Coberto por testes em
  `apps/integrations_bridge/tests/test_create_submit_job.py`.)

---

## 4. Qual usar?

| Cenário | Usa |
|---|---|
| "O renderer está de pé e aceita jobs?" (rápido, sem DB) | **Camada 1** — `manage.py smoke_content_renderer` |
| Validar o loop completo com callback, asset e idempotência | **Camada 2** — `run-e2e-postgres.ps1` |
| Estado de disponibilidade agregado antes de tudo | `GET /api/v1/system/health/dependencies/` (staff-only) |

---

## 5. Segurança

- O token viaja **apenas** no header `X-Internal-Token`; o cliente interno nunca o
  loga; o command redige-o como `token=configured` / `token=not_configured`.
- O probe a `GET /health` é **público** e **não** envia token.
- Os logs do renderer redigem chaves sensíveis recursivamente.
- Documentação e scripts usam apenas placeholders / valores dev descartáveis.
