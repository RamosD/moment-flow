# BC-IE-008 — Validação ponta-a-ponta com mocks HTTP

> **Tipo:** testes de integração ponta-a-ponta (transporte HTTP mockado).
> **Fase:** `integracao_intelligence_engine` — tarefa **BC-IE-008**.
> **Data:** 2026-06-25.
> **Âmbito:** apenas testes no `backend_core`. **Não** foram tocados
> `intelligence_engine` nem `content_renderer`. Nenhum ficheiro de runtime foi
> alterado.
> **Base:** client/serviço/endpoint dos prompts 03–07.

---

## 0. Sumário executivo

- Criado um conjunto de testes **ponta-a-ponta** que exercita o **stack completo**
  através da API pública, mockando **apenas o transporte HTTP**:

  ```text
  POST /api/v1/campaigns/{id}/intelligence/
    → CampaignViewSet (auth + RBAC + workspace)
    → CampaignIntelligenceService (real)
    → CampaignIntelligencePayloadBuilder (real, lê modelos reais)
    → IntelligenceEngineClient (real) → opener falso (sem HTTP real)
    → resposta normalizada
  ```

- Técnica: a factory `build_intelligence_engine_client` é monkeypatchada para
  devolver um client **real** ligado a um `CapturingOpener`, permitindo **afirmar
  o payload e os headers efectivamente enviados** ao IE (impossível quando se
  mocka ao nível do serviço).
- Cobertos: completed completo, warnings + scores `unknown` + `wait_for_more_data`,
  timeout, conexão recusada, 403, 422, 5xx, JSON inválido, desligado, dry-run,
  RBAC/workspace, e token-não-logado.
- **13 testes novos**; ruff e `manage.py check` limpos; suite completa verde.

---

## 1. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| [`apps/campaigns/tests/test_intelligence_integration.py`](../../../../../apps/campaigns/tests/test_intelligence_integration.py) | **Novo.** 13 testes de integração (HTTP mockado no transporte) |

> Apenas teste. Nenhum módulo de runtime foi alterado — a integração já estava
> implementada (prompts 03–07); esta tarefa valida-a de ponta a ponta.

---

## 2. Abordagem de mock

- **`CapturingOpener`**: transporte falso `(request, timeout) -> resposta | excepção`
  que **captura** o `urllib.Request` (corpo + headers + timeout) e conta chamadas.
- **`_install_engine(monkeypatch, opener)`**: substitui
  `apps.campaigns.intelligence_service.build_intelligence_engine_client` por uma
  factory que devolve `IntelligenceEngineClient(URL, 5, internal_token=TOKEN,
  opener=opener, max_retries=0)`. **Tudo o resto é real** (serviço, builder,
  client, normalização).
- Erros HTTP simulados com `urllib.error.HTTPError(..., io.BytesIO(envelope))`
  para fornecer o corpo do envelope de erro do IE.
- `max_retries=0` nos testes → contagem de chamadas determinística.

Isto permite afirmar **o contrato de saída** (o que o Django envia ao IE), não só
a resposta de entrada.

---

## 3. Cenários cobertos

### 3.1 Sucesso e contrato de saída (`TestCompletedFlow`)
- **completed completo**: resposta 200 com `analysis, scores, grade, moments,
  recommendations, summary` (em `result`) + `explanations, warnings, metadata`;
  `source="engine"`, `generated_at` carimbado.
- **Payload de saída (contrato §7)**: `payload_version="1.0"`, `workspace_id`,
  `entity={type:campaign, id}`, `context.reference_date`, e `data` com
  `campaign/artist/track/smart_link_stats/content_outputs/previous_reports/reports/
  media_kits/goals`; `smart_link_stats.active_links==1`, `previous_reports`
  não-vazio.
- **Headers internos**: `X-Internal-Token==TOKEN`, `X-Workspace-ID==ws.id`,
  `Content-Type: application/json`; `timeout==5` aplicado.
- **Correlação**: `request_id` idêntico em **body**, **header `X-Request-ID`** e
  **resposta** — propagação verificada.
- **warnings / scores unknown / wait_for_more_data**: 200 com `grade="unknown"`,
  `scores.priority_score=None`, `recommendations[0].action=="wait_for_more_data"`,
  `warnings[0].code=="insufficient_data"`; campanha mínima → `data.track is None`.

### 3.2 Falhas mapeadas ponta-a-ponta (`TestFailureModes`)
| Cenário | Transporte | HTTP final |
|---|---|---|
| timeout | `TimeoutError` | **503** |
| conexão recusada | `URLError` | **503** |
| 403 interno | HTTPError 403 | **502** |
| 422 invalid_payload | HTTPError 422 | **502** |
| 5xx | HTTPError 500 | **503** |
| JSON inválido | corpo `not-json` | **502** |

### 3.3 Switches sem HTTP (`TestSwitches`)
- **desligado** (`ENABLED=False`) → 503 e `opener.calls==0`.
- **dry-run** (`DRY_RUN=True`) → 200, `source="dry_run"`, `opener.calls==0` (o
  builder corre, mas não há chamada real).

### 3.4 RBAC/workspace ainda aplicados (`TestAccessControlStillEnforced`)
- membro sem `campaigns:view` → **403**, `opener.calls==0`.
- campanha de outro workspace → **404**, `opener.calls==0` (não vaza, não chama IE).

### 3.5 Segurança/observabilidade (`TestSecurity`)
- **token nunca nos logs** (`TOKEN not in caplog.text`) no caminho de sucesso.
- `workspace_id` e `campaign_id` presentes nos logs (diagnóstico).

---

## 4. Validações executadas

| Verificação | Comando | Resultado |
|---|---|---|
| Testes de integração | `pytest apps/campaigns/tests/test_intelligence_integration.py` | **13 passed** |
| Suite completa | `pytest -q` | **459 passed** (446 + 13 novos) |
| Lint | `ruff check apps/campaigns/tests/test_intelligence_integration.py` | **All checks passed** |
| Django system check | `manage.py check` | **0 issues** |

> Os warnings são pré-existentes (`No directory at: staticfiles/`).

---

## 5. Conformidade com os critérios de aceitação

- [x] Testes com mock cobrem sucesso e principais falhas (completed, warnings,
      scores unknown, wait_for_more_data, timeout, 403, 422, 5xx, JSON inválido,
      desligado, dry-run).
- [x] Payload enviado ao IE é compatível com o contrato (afirmado via
      `CapturingOpener.sent_payload()`).
- [x] Headers internos verificados (`X-Internal-Token`, `X-Workspace-ID`,
      `X-Request-ID`).
- [x] RBAC/workspace continuam cobertos (403 sem permissão; 404 cross-workspace).
- [x] Token não aparece em logs.
- [x] Testes passam.
- [x] Validações executadas (ruff, suite, check).
- [x] Relatório com cenários, comandos, resultados, pendências e próximo passo.

---

## 6. Pendências / notas

- **Validação com IE real (BC-IE-009):** estes testes mockam o transporte; falta
  o loop real com os dois serviços a correr (token alinhado, campanha de teste).
- **Sobreposição de cobertura:** mantêm-se os testes unitários (client/serviço/
  API) — os de integração **complementam** (não substituem), validando a costura
  entre camadas e o contrato de saída.

---

## 7. Próximo passo recomendado

**BC-IE-009** — validar o loop real Backend Core ↔ Intelligence Engine: arrancar
ambos os serviços localmente, alinhar `INTERNAL_API_TOKEN`, configurar
`INTELLIGENCE_ENGINE_BASE_URL`, executar uma chamada real ao endpoint Django,
confirmar resposta com analysis/scores/moments/recommendations, confirmar
comportamento com o IE desligado e registar evidências (sem expor token).
