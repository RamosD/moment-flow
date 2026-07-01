# BC-IE-009 — Validação do loop real Backend Core ↔ Intelligence Engine

> **Tipo:** validação ponta-a-ponta com os dois serviços a correr de verdade
> (sem mocks) + correcção de um bug de integração encontrado.
> **Fase:** `integracao_intelligence_engine` — tarefa **BC-IE-009**.
> **Data:** 2026-06-25.
> **Âmbito:** `backend_core` (código + um novo ficheiro de teste opt-in).
> **Não** foram alterados `intelligence_engine` nem `content_renderer` — ambos
> foram apenas arrancados e inspeccionados (read-only) para diagnóstico.
> **Base:** client/builder/serviço/endpoint dos prompts 03–08.

---

## 0. Sumário executivo

A validação real foi **executada com sucesso** — não foi necessário recorrer
ao checklist manual de limitação de ambiente. Ambos os serviços arrancaram
localmente, foi feita uma chamada real (HTTP de verdade, sem mocks) do
Backend Core ao Intelligence Engine através do endpoint Django criado em
BC‑IE‑006, e a resposta real contém todos os blocos exigidos.

No processo, foi descoberto e corrigido **um bug real de integração** no
`backend_core` (não no contrato, não no IE): o builder enviava
`content_outputs[].created_at` como **datetime completo** (`"...T08:11:25+00:00"`),
mas o IE valida esse campo como **data pura** (`date`), rejeitando o payload
com `422 invalid_payload` / `date_from_datetime_inexact`. Corrigido no builder
(`apps/campaigns/intelligence_payload.py`), sem tocar no `intelligence_engine`.

Depois da correcção:
- Chamada real ao endpoint Django **`POST /api/v1/campaigns/{id}/intelligence/`**
  devolveu **200** com `source="engine"` e os 6 blocos (`analysis`, `scores`,
  `grade`, `moments`, `recommendations`, `summary`) populados pelo IE real.
- IE indisponível (porta fechada) → **`IntelligenceUnavailableError`**
  controlado (mapeia para 503), sem excepção não tratada.
- Token nunca apareceu em nenhum log capturado (client, sync, serviço).
- Suite completa do `backend_core`: **459 passed, 3 skipped** (os 3 *skipped*
  são os testes opt-in do loop real, que só correm com `RUN_REAL_IE=1`) — e
  **462 passed** (459 + 3) quando corridos com `RUN_REAL_IE=1`.

---

## 1. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| [`apps/campaigns/intelligence_payload.py`](../../../../../apps/campaigns/intelligence_payload.py) | **Bug fix.** Novo helper `_date_only()`; `_content_outputs()` passa a truncar `created_at` para data pura em vez de emitir datetime completo |
| [`apps/campaigns/tests/test_intelligence_real_loop.py`](../../../../../apps/campaigns/tests/test_intelligence_real_loop.py) | **Novo.** 3 testes opt-in (`RUN_REAL_IE=1`) que correm o loop real: serviço directo (sucesso), serviço directo (IE indisponível), e o endpoint HTTP Django completo (auth+RBAC+serviço+builder+HTTP real) |

> Nenhum outro módulo de runtime foi tocado. O `intelligence_engine` e o
> `content_renderer` não foram alterados — apenas arrancados/inspeccionados.

---

## 2. Como arrancar os dois serviços

### 2.1 Intelligence Engine (FastAPI)

```bash
cd intelligence_engine
INTERNAL_API_TOKEN=real-loop-token-123 APP_ENV=development \
    venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

- `INTERNAL_API_TOKEN` tem de estar definido — em `development`/`test`, se
  ficar vazio, **todos** os pedidos a endpoints protegidos são rejeitados com
  403 (não é um bypass; ver `intelligence_engine/README.md` linha 654/672).
- Confirmação de saúde: `GET http://127.0.0.1:8001/health` → `200
  {"status":"ok","service":"intelligence_engine",...}` (endpoint público, sem
  token).

### 2.2 Backend Core (Django)

```bash
cd backend_core
# .env (ou variáveis de ambiente) alinhadas com o IE:
#   INTELLIGENCE_ENGINE_BASE_URL=http://127.0.0.1:8001
#   INTELLIGENCE_ENGINE_INTERNAL_TOKEN=real-loop-token-123
#   INTELLIGENCE_ENGINE_ENABLED=True
#   INTELLIGENCE_ENGINE_DRY_RUN=False
venv/Scripts/python.exe manage.py runserver 8000
```

Para os testes automatizados do loop real (em vez de arrancar o `runserver`),
os mesmos valores são injectados via `django.test.override_settings`/fixture
`settings` no próprio teste — não é necessário um `.env` separado:

```bash
RUN_REAL_IE=1 REAL_IE_BASE_URL=http://127.0.0.1:8001 \
    REAL_IE_TOKEN=real-loop-token-123 \
    venv/Scripts/python.exe -m pytest apps/campaigns/tests/test_intelligence_real_loop.py -v
```

---

## 3. Diagnóstico e correcção do bug encontrado

### 3.1 Sintoma

Com os dois serviços a correr e o token alinhado, o teste
`test_real_loop_returns_intelligence` falhava: o serviço recebia
`IntelligenceUpstreamError`, e o log mostrava:

```
WARNING  integrations_bridge.client:clients.py:121 internal_call http_error ... status=422
WARNING  integrations_bridge.intelligence:intelligence_sync.py:258 intelligence_call http_error ... status=422 error_code=invalid_payload
ERROR    campaigns.intelligence:intelligence_service.py:289 intelligence event=upstream_error ... status=422 error_code=invalid_payload
```

O *error handling* (client → serviço → 502/503) funcionou correctamente — o
problema estava no **conteúdo do payload**, não no tratamento de erro.

### 3.2 Isolamento da causa

1. Confirmado primeiro que o IE real funciona: um payload construído à mão
   (seguindo o contrato documentado) enviado directamente via `urllib`
   devolveu **200** com resposta `completed` completa (grade A, 4 moments, 4
   recommendations) — prova que o IE e o contrato funcionam de ponta a ponta.
2. Foi extraído o payload **real** gerado pelo `CampaignIntelligencePayloadBuilder`
   (mesma campanha "rica" usada no teste) e enviado em bruto (raw `urllib`,
   contornando a supressão de detalhe do serviço) directamente ao IE:

   ```bash
   POST http://127.0.0.1:8001/intelligence/campaign
   → 422
   {"status":"failed","error":{"code":"invalid_payload","message":"Invalid payload.",
     "details":{"errors":[{"type":"date_from_datetime_inexact",
       "loc":["body","data","content_outputs",0,"created_at"],
       "msg":"Datetimes provided to dates should have zero time - e.g. be exact dates",
       "input":"2026-06-25T08:11:25.360389+00:00"}]}}}
   ```

3. Confirmado no esquema do IE (`intelligence_engine/app/schemas/campaign.py:71`,
   apenas lido, não alterado):

   ```python
   class ContentOutputSummary(BaseModel):
       ...
       created_at: date | None = None
   ```

   Todos os exemplos do contrato e do README do IE usam datas puras
   (`"created_at": "2026-06-22"`), nunca datetimes com hora/offset.

4. No `backend_core`, `ContentOutput.created_at` é um `DateTimeField`
   (via `CreatedUpdatedByModel`), e o builder fazia
   `_iso(r["created_at"])` → `.isoformat()` de um `datetime`, produzindo
   `"2026-06-25T08:11:25.360389+00:00"` em vez de `"2026-06-25"`.

**Conclusão:** bug genuíno no `backend_core` (o builder não respeitava a
granularidade de data exigida pelo contrato/IE para este campo), não uma
limitação de ambiente nem um problema do contrato/IE. Autorizado a corrigir
por estar directamente relacionado com a integração.

### 3.3 Correcção aplicada

`apps/campaigns/intelligence_payload.py`:

```python
def _date_only(value):
    """Serialize a date/datetime to a plain ISO *date* (no time), or ``None``.

    The engine's contract types ``content_outputs[].created_at`` as a ``date``
    (it only needs day-level granularity for windowing), but the source field
    is a ``DateTimeField``. Truncate instead of emitting a full datetime, which
    the engine's schema rejects (422 ``date_from_datetime_inexact``).
    """
    if value is None:
        return None
    if hasattr(value, "date"):
        value = value.date()
    return value.isoformat()
```

E em `_content_outputs()`:

```python
"created_at": _date_only(r["created_at"]),   # era _iso(r["created_at"])
```

Os restantes campos de data do payload (`start_date`, `end_date`,
`release_date`, `period_end`, `deadline`) já são `DateField` no Django, logo
`_iso()` já produzia data pura nesses casos — só `content_outputs.created_at`
estava afectado.

---

## 4. Validação real (depois da correcção)

### 4.1 Loop real via serviço directo

```bash
RUN_REAL_IE=1 REAL_IE_BASE_URL=http://127.0.0.1:8001 REAL_IE_TOKEN=real-loop-token-123 \
    venv/Scripts/python.exe -m pytest apps/campaigns/tests/test_intelligence_real_loop.py -v -s --log-cli-level=INFO
```

Resultado: **3 passed**. Logs capturados (nenhum contém o token):

```
INFO  integrations_bridge.intelligence:intelligence_sync.py:229 intelligence_call start request_id=... workspace_id=...
INFO  integrations_bridge.client:clients.py:111 internal_call start job_id=None request_id=... url=http://127.0.0.1:8001/intelligence/campaign
INFO  integrations_bridge.client:clients.py:153 internal_call ok job_id=None request_id=... status=200
INFO  integrations_bridge.intelligence:intelligence_sync.py:295 intelligence_call ok request_id=... workspace_id=... status=completed
INFO  campaigns.intelligence:intelligence_service.py:289 intelligence event=ok request_id=... workspace_id=... campaign_id=... status=completed duration_ms=51
```

Resposta real (`outcome.as_dict()`), confirmando os 6 blocos no `result` (vem
do IE real, não inventado):

```json
{
  "status": "completed",
  "source": "engine",
  "engine": "intelligence_engine",
  "engine_version": "0.1.0",
  "result": {
    "analysis": { "campaign_health": "good", "...": "..." },
    "scores": {
      "campaign_readiness_score": 100, "momentum_score": 0,
      "content_opportunity_score": 60, "risk_score": 15, "priority_score": 44
    },
    "grade": "C",
    "moments": [ "... 3 moment(s) detected ..." ],
    "recommendations": [ "...", "..." ],
    "summary": "Campaign health 'good', grade C. Scores — readiness 100, momentum 0, opportunity 60, risk 15, priority 44. 3 moment(s) detected; 2 recommendation(s), top action create_release_post."
  },
  "explanations": [ "... 9 entries, pesos e fórmulas do IE ..." ],
  "warnings": [],
  "metadata": { "generated_at": null, "payload_version": "1.0" },
  "generated_at": "2026-06-25T08:14:02.965512+00:00"
}
```

### 4.2 Loop real via endpoint Django HTTP (o endpoint criado em BC-IE-006)

Novo teste `test_real_loop_via_django_http_endpoint` dirige o pedido pelo
**stack real completo**: `APIClient` autenticado → `CampaignViewSet`
(auth+RBAC+workspace) → `CampaignIntelligenceService` → builder → client real
→ HTTP real para o IE em `127.0.0.1:8001`.

```bash
RUN_REAL_IE=1 venv/Scripts/python.exe -m pytest \
    apps/campaigns/tests/test_intelligence_real_loop.py::test_real_loop_via_django_http_endpoint -v -s --log-cli-level=INFO
```

Resultado: **1 passed**. `resp.status_code == 200`, `resp.data["source"] ==
"engine"`, os 6 campos presentes em `resp.data["result"]`, e `TOKEN not in
caplog.text`.

### 4.3 IE indisponível (URL inválida) — comportamento controlado

```python
settings.INTELLIGENCE_ENGINE_BASE_URL = "http://127.0.0.1:8009"  # porta fechada
```

Resultado: **`IntelligenceUnavailableError`** levantada de forma controlada
(o serviço mapeia para 503 no endpoint — confirmado já em BC-IE-007/008).
Log (sem token):

```
WARNING integrations_bridge.client:clients.py:136 internal_call unavailable job_id=None request_id=...
WARNING integrations_bridge.intelligence:intelligence_sync.py:249 intelligence_call unavailable request_id=... workspace_id=...
WARNING campaigns.intelligence:intelligence_service.py:289 intelligence event=unavailable request_id=... workspace_id=... campaign_id=... error_type=IntelligenceEngineUnavailable duration_ms=2029
```

### 4.4 Token nunca exposto

Em todos os cenários acima (sucesso, endpoint HTTP, indisponível) foi
verificado `TOKEN not in caplog.text` — confirmado automaticamente pelos
testes e inspeccionado manualmente nos logs reproduzidos nesta secção.

---

## 5. Validações executadas

| Verificação | Comando | Resultado |
|---|---|---|
| Loop real (serviço + endpoint + indisponível) | `RUN_REAL_IE=1 pytest apps/campaigns/tests/test_intelligence_real_loop.py -v` | **3 passed** |
| Payload + integração (mocked) | `pytest apps/campaigns/tests/test_intelligence_payload.py apps/campaigns/tests/test_intelligence_integration.py -q` | **26 passed** |
| Suite completa (sem `RUN_REAL_IE`) | `pytest -q` | **459 passed, 3 skipped** (skips = testes opt-in do loop real) |
| Lint | `ruff check apps/ config/` | **All checks passed** |
| Django system check | `manage.py check` | **0 issues** |

> Os 3 *skipped* na suite normal são deliberados — os testes do loop real só
> correm com `RUN_REAL_IE=1` e o IE a correr (ver §2.2); não são uma falha.

---

## 6. Conformidade com os critérios de aceitação

- [x] Loop real Backend Core → Intelligence Engine foi **validado** (não foi
      necessário documentar limitação de ambiente).
- [x] Resposta real está documentada (§4.1) com os 6 blocos exigidos.
- [x] Falha com IE indisponível é tratada de forma controlada (§4.3).
- [x] Logs não expõem token (§4.4, verificado em todos os cenários).
- [x] Evidências registadas (comandos + logs + corpo de resposta real nesta
      secção).
- [x] Testes relevantes continuam a passar (459 mockados + 3 reais = 462).
- [x] Relatório com comandos, resultados, limitações, pendências e próximo
      passo.

---

## 7. Pendências / notas

- **Teste opt-in, não na CI por omissão:** `test_intelligence_real_loop.py`
  só corre com `RUN_REAL_IE=1` e o IE a correr localmente em
  `127.0.0.1:8001` com um token conhecido. Não está pensado para correr na
  CI normal (que não tem o IE disponível) — é uma ferramenta de validação
  manual/local, à semelhança do pedido do prompt.
- **Bug encontrado era específico a `content_outputs.created_at`:** os
  restantes campos de data do payload já eram `DateField` no Django, logo
  já produziam datas puras; não há indícios de problemas equivalentes
  noutros campos (confirmado por inspecção do esquema do IE, §3.2.3).
- **403/422 de configuração ainda não testados ao vivo:** o cenário "token
  desalinhado" (403 real) e o de payload genuinamente inválido (422
  genuíno, não o bug agora corrigido) já estão cobertos pelos testes
  mockados (BC-IE-008); não foi considerado necessário reproduzi-los ao
  vivo, dado que o mecanismo de erro HTTP→excepção típica já foi confirmado
  ao vivo no cenário de indisponibilidade (§4.3) e nos 403/422 mockados.
- **Processo do IE:** o `uvicorn` arrancado para esta validação ficou a
  correr em `127.0.0.1:8001` durante os testes; deve ser parado manualmente
  após a revisão deste relatório (não é gerido pela suite de testes).

---

## 8. Próximo passo recomendado

**BC-IE-010** (encerramento da fase) — consolidar a documentação final da
integração: rever o conjunto de relatórios 01–09, confirmar que a
documentação operacional (`.env.example`, settings, runbook de
arranque/diagnóstico) está coerente com o comportamento validado nesta
tarefa, e produzir o relatório de encerramento da fase
`integracao_intelligence_engine` com um resumo do que foi entregue, o que
ficou fora do MVP (snapshot/job assíncrono/circuit breaker) e recomendações
para a próxima fase.
