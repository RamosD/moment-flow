# Smoke test — Backend Core ↔ Intelligence Engine

> Como validar rapidamente o loop real
> **Backend Core → Intelligence Engine → Backend Core** (OBS-STG-004).
>
> Há **duas** formas, complementares. Nenhuma corre por acidente: ambas exigem
> activação explícita. O token interno **nunca** é impresso/logado.

---

## 1. Pré-condições (configuração)

O Intelligence Engine tem de estar a correr e o Backend Core configurado para o
loop real:

| Variável | Valor exigido |
|---|---|
| `INTELLIGENCE_ENGINE_BASE_URL` | URL do IE a correr (ex.: `http://127.0.0.1:8001`) |
| `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` (ou `INTERNAL_API_TOKEN`) | **não vazio**; o **mesmo** valor configurado no IE |
| `INTELLIGENCE_ENGINE_ENABLED` | `True` |
| `INTELLIGENCE_ENGINE_DRY_RUN` | `False` |

Arranque do IE (terminal separado), com um token de **dev** descartável:

```powershell
cd intelligence_engine
$env:INTERNAL_API_TOKEN="<DEV_TOKEN>"; $env:APP_ENV="development"
venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

> Sugestão: antes do smoke, confirma a disponibilidade com o healthcheck agregado
> (`GET /api/v1/system/health/dependencies/`, staff-only) ou directamente
> `curl http://127.0.0.1:8001/health`.

---

## 2. Opção A — Management command (operacional, sem base de dados)

A forma mais leve para **local/staging**: valida a configuração, chama o IE real
com um payload representativo e confirma o contrato da resposta. **Não escreve
nada na base de dados.**

```powershell
cd backend_core
$env:INTELLIGENCE_ENGINE_BASE_URL="http://127.0.0.1:8001"
$env:INTELLIGENCE_ENGINE_INTERNAL_TOKEN="<DEV_TOKEN>"
$env:INTELLIGENCE_ENGINE_ENABLED="true"; $env:INTELLIGENCE_ENGINE_DRY_RUN="false"
venv/Scripts/python.exe manage.py smoke_intelligence_engine
# opcional: ancorar as regras de recência a uma data
venv/Scripts/python.exe manage.py smoke_intelligence_engine --reference-date 2026-06-25
```

**Saída de sucesso** (exemplo; o token nunca aparece):

```text
smoke_ie config base_url=http://127.0.0.1:8001 enabled=True dry_run=False token=configured timeout_s=10
smoke_ie start request_id=<hex> base_url=http://127.0.0.1:8001
smoke_ie ok {"status": "completed", "engine": "intelligence_engine", "engine_version": "0.1.0",
             "request_id": "<hex>", "keys_present": ["analysis","scores","grade","moments",
             "recommendations","summary"], "grade": "A", "moments": 4, "recommendations": 4, "warnings": 0}
```

**Falhas controladas** (sai com código ≠ 0, sem stack trace, sem token):

- **Configuração inválida** (IE desligado, dry-run, token/URL vazios) → mensagem
  `Cannot run the Intelligence Engine smoke — …`.
- **IE indisponível / timeout** → `Intelligence Engine call failed (…). Smoke failed.`
- **IE devolve 4xx/5xx** (ex.: token desalinhado → 403) → `Intelligence Engine returned HTTP 403 (…). Smoke failed.`

---

## 3. Opção B — Teste opt-in pytest (loop completo, com base de dados)

Cobre o **caminho completo** (factory de campanha → builder → service → cliente →
HTTP real → endpoint Django com auth+RBAC). Reutiliza o teste existente
[`apps/campaigns/tests/test_intelligence_real_loop.py`](../../../../apps/campaigns/tests/test_intelligence_real_loop.py),
guardado por `RUN_REAL_IE` (sem essa variável, os 3 testes aparecem como
`SKIPPED`).

```powershell
cd backend_core
$env:RUN_REAL_IE="1"
$env:REAL_IE_BASE_URL="http://127.0.0.1:8001"
$env:REAL_IE_TOKEN="<DEV_TOKEN>"
venv/Scripts/python.exe -m pytest apps/campaigns/tests/test_intelligence_real_loop.py -q
```

Os 3 testes validam:

1. `get_campaign_intelligence()` real → `source=engine`, `status=completed`, as
   **6 chaves** (`analysis`, `scores`, `grade`, `moments`, `recommendations`,
   `summary`) e **token ausente** de `caplog`.
2. IE inacessível (porta fechada) → `IntelligenceUnavailableError` controlado.
3. Endpoint Django real `POST /api/v1/campaigns/{id}/intelligence/` (auth+RBAC) →
   `200` com o corpo completo e token ausente dos logs.

---

## 4. Qual usar?

| Cenário | Usa |
|---|---|
| Verificação rápida de conectividade/contrato/config em staging, sem dados nem test DB | **Opção A** (command) |
| Validação completa do caminho de produto (builder/service/endpoint/RBAC) | **Opção B** (pytest opt-in) |
| Diagnóstico de disponibilidade antes do smoke | Healthcheck agregado (`/api/v1/system/health/dependencies/`) |

---

## 5. Segurança

- O token viaja **apenas** no header `X-Internal-Token` (gerido pelo cliente
  interno); **nunca** é impresso pelo command nem logado pelo cliente.
- O command redige o estado do token como `token=configured` / `token=not_configured`.
- Os exemplos deste documento usam o placeholder `<DEV_TOKEN>` — **nunca** um
  valor real.
