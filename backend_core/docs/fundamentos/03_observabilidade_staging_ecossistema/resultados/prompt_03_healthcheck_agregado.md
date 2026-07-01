# OBS-STG-003 — Relatório de execução: Healthcheck agregado no Backend Core

> Relatório de execução do prompt 03. Este prompt **altera runtime** (novo
> endpoint + serviço + setting), de forma aditiva e isolada na app
> `integrations_bridge`.
>
> Fase: Observabilidade e Staging Técnico do Ecossistema.
> Backlog: [`../01_backlog.md`](../01_backlog.md).
> Data: 2026-06-25. Modelo recomendado (backlog §15): opus.

---

## 1. Objectivo

Implementar no Backend Core um healthcheck **agregado** que sonde o estado
operacional das dependências técnicas — Intelligence Engine, Content Renderer e a
base de dados do próprio Backend Core — com resposta normalizada, timeout curto,
sem expor secrets e sem que a falha de uma dependência rebente o endpoint.

---

## 2. Padrão de healthcheck pré-existente

- **Backend Core:** não existia qualquer rota de health/liveness/readiness
  (confirmado no Prompt 01). O harness E2E usava `GET /api/v1/schema/` como proxy
  de readiness.
- **Intelligence Engine** e **Content Renderer:** ambos expõem `GET /health`
  **público** (sem auth). É exactamente isto que o agregado consome.

Como não havia padrão interno, adoptou-se a rota sugerida pelo backlog, adaptada,
e colocou-se a lógica na app que **já** possui o conhecimento das dependências
(URLs/clients/registry): `integrations_bridge`.

---

## 3. Rota criada

```text
GET /api/v1/system/health/dependencies/
```

- **Protegida** (`IsAdminUser` — staff only). Decisão alinhada com OBS-PDEC-001
  ("protegido se incluir detalhe das dependências") e OBS-RSK-005 (não expor
  informação operacional sensível a qualquer utilizador).
- Sem auth → **401**; autenticado não-staff → **403**; staff → **200**.
- Devolve **sempre HTTP 200** com o estado no corpo (decisão deliberada: é um
  endpoint de diagnóstico, não uma liveness probe de load-balancer; evita
  qualquer ambiguidade de "500 inesperado"). Uma variante `503-on-unavailable`
  pode ser adicionada depois se um probe automático o exigir.

### 3.1 Forma da resposta

```json
{
  "status": "ok",
  "service": "backend_core",
  "checked_at": "2026-06-25T12:00:00+00:00",
  "dependencies": {
    "intelligence_engine": { "status": "ok", "url": "configured", "duration_ms": 12 },
    "content_renderer":    { "status": "ok", "url": "configured", "duration_ms": 18 },
    "database":            { "status": "ok", "duration_ms": 1 }
  }
}
```

- **Estado geral:** `ok` | `degraded` | `unavailable`.
  - `ok` = todas as dependências `ok`; `unavailable` = nenhuma `ok`;
    `degraded` = situação mista.
- **Estado por dependência:** `ok` | `degraded` | `unavailable` | `misconfigured` | `unknown`.
  - `ok` = 2xx + corpo `{"status":"ok"}`; `degraded` = respondeu mas não saudável
    (non-2xx, ou 2xx com corpo inesperado/ inválido); `unavailable` =
    timeout/inacessível; `misconfigured` = `base_url` ausente (probe nem é
    chamado); `unknown` = erro inesperado do próprio probe (defensivo).
- **`duration_ms`** por dependência.
- **Sem secrets:** o probe ao `/health` **não envia** `X-Internal-Token` (são
  públicos); a URL é reduzida a `configured` / `not_configured`; o `detail` é
  vocabulário controlado (`timeout`, `connection_error`, `http_503`,
  `unexpected_body`, `base_url_not_configured`) — nunca corpos, URLs ou tokens.

---

## 4. Ficheiros criados / alterados

| Ficheiro | Acção | Conteúdo |
|---|---|---|
| `apps/integrations_bridge/health.py` | **Criado** | Serviço `check_dependencies()` + probe `http_health_probe()` + check de DB + agregação + log sumário token-free. Probe injectável (testes). |
| `apps/integrations_bridge/views.py` | Alterado | Nova `SystemDependencyHealthView` (`IsAdminUser`, `GET`, `@extend_schema`). Imports: `OpenApiTypes`, `IsAdminUser`, `check_dependencies`. |
| `apps/integrations_bridge/urls.py` | Alterado | Rota `system/health/dependencies/`. |
| `config/settings.py` | Alterado | Novo `HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS` (default `2.0`, `cast=float`). |
| `.env.example` | Alterado | Documenta `HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS` (sem secrets). |
| `apps/integrations_bridge/tests/test_dependency_health.py` | **Criado** | 20 testes (probe + agregador + endpoint). |
| `schema.yml` | Regenerado | Inclui o novo endpoint (`security: jwtAuth`, resposta `object`). |
| `README.md` (backend_core) | Alterado | Linha na tabela de endpoints. |
| `docs/.../matriz_operacional_servicos.md` | Alterado | Healthcheck do Backend Core actualizado (de "inexistente" para o endpoint real); nova variável; item "por confirmar" resolvido. |

**Nenhuma alteração** foi feita ao Intelligence Engine nem ao Content Renderer
(regra do backlog §5.2.8) — o agregado apenas **consome** os `/health` já existentes.

---

## 5. Timeout — curto e configurável

`HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS` (default **2.0s**, `float` para permitir
sub-segundo), lido via `python-decouple`. É deliberadamente baixo (fail-fast) para
o endpoint continuar responsivo mesmo com uma dependência pendurada — em vez de
reutilizar `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` (10s), que é demasiado longo para
um healthcheck. Mitiga OBS-RSK-004 (timeout agressivo → estado `degraded`/
`unavailable` por dependência, nunca falha total).

---

## 6. Testes executados

### 6.1 Testes novos (`test_dependency_health.py`) — 20, todos a passar

| Grupo | Cobre |
|---|---|
| `TestProbe` (9) | corpo ok→`ok`; corpo inesperado/`status!=ok`→`degraded`; objecto não-2xx→`degraded http_<code>`; `HTTPError`→`degraded`; timeout→`unavailable`; erro de ligação→`unavailable`; **probe não envia `X-Internal-Token`**. |
| `TestAggregator` (8) | **todos ok**; **IE indisponível**→degraded; **renderer indisponível**→degraded; **timeout**→unavailable na dependência + degraded geral; **misconfigured** (base_url vazio, probe não chamado)→degraded; **todas externas indisponíveis**→`unavailable`; timeout configurável respeitado; excepção no probe não rebenta o agregado (`unknown`). |
| `TestEndpoint` (4) | sem auth→**401**; não-staff→**403**; staff→**200**; **sem 500** quando o probe real falha (degrada para `unknown`). |

Comando e resultado:

```text
pytest apps/integrations_bridge/tests/test_dependency_health.py -q
→ 20 passed
```

Cobre explicitamente os casos pedidos: **todos ok, IE indisponível, renderer
indisponível, timeout, base_url ausente/misconfigured, resposta inválida**.

### 6.2 Validações transversais

| Validação | Comando | Resultado |
|---|---|---|
| Suite da app afectada | `pytest apps/integrations_bridge/ -q` | **145 passed** |
| Lint | `ruff check` (ficheiros alterados) | **All checks passed!** |
| Django system check | `python manage.py check` | **no issues** |
| Schema OpenAPI | `manage.py spectacular --file schema.yml` | Regenerado **sem warnings**; endpoint presente e seguro (`jwtAuth`). |
| Suite completa | `pytest -q` | _ver §6.3_ |

### 6.3 Suite completa

```text
pytest -q
→ 479 passed, 3 skipped em 287.11s
```

Os 3 `skipped` são os testes opt-in do loop real IE (`test_intelligence_real_loop.py`,
guardados por `RUN_REAL_IE`) — comportamento esperado. O total subiu de 459
(fecho da integração IE↔BC) para 479 = +20 testes novos do healthcheck agregado.
Nenhuma regressão.

---

## 7. Decisões e justificações

1. **Localização (`integrations_bridge`).** É a app que já possui os clients,
   o registry e as URLs das dependências; reutiliza esse conhecimento e mantém o
   Backend Core como ponto de orquestração (backlog §5.2.7).
2. **Rota `system/health/dependencies/`.** Combina o namespace extensível
   `system/health/` com `dependencies` (cobre IE + renderer + DB; "external-services"
   seria impreciso por incluir a DB interna).
3. **Protecção `IsAdminUser`.** Protegido por expor detalhe operacional; usa o
   padrão DRF idiomático e não quebra quando `INTERNAL_API_TOKEN` está vazio em
   local (ao contrário de reutilizar `IsInternalService`). Um superuser existe em
   qualquer setup real (`createsuperuser`).
4. **Sempre 200.** Diagnóstico no corpo; satisfaz "nunca 500 inesperado" sem
   ambiguidade. Variante 503 fica como evolução opcional.
5. **DB incluída** mas com nota: a própria autenticação (`IsAdminUser`) já implica
   DB de pé; o check explícito completa a visão de "dependências" e é barato.

---

## 8. Lacunas / pendências

| Item | Estado | Nota |
|---|---|---|
| Liveness próprio do Backend Core (sem auth) | Não criado | O agregado é staff-only por desenho; uma liveness pública simples pode ser útil para probes de infra. Fora do âmbito mínimo desta fase; `GET /api/v1/schema/` serve de proxy entretanto. |
| `LOGGING` em `settings.py` | Por tratar | O endpoint emite `event=health_check overall=…` (INFO), mas sem `LOGGING` configurado pode não surgir — a resolver em **OBS-STG-006**. |
| Variante `503-on-unavailable` | Decisão adiada | Adicionar só se um probe automático externo o exigir. |
| Discrepância de porta do report renderer | Documentada | O agregado sonda `CONTENT_RENDERER_BASE_URL` (:8002). O report renderer partilha o processo; não há sonda separada para `:8003` (alinhado com a matriz). |

---

## 9. Conformidade com os critérios de aceitação

| Critério | Estado |
|---|---|
| Endpoint agregado existe | ✅ `GET /api/v1/system/health/dependencies/` |
| Falha de dependência → degraded/unavailable, não 500 | ✅ testes `TestAggregator` + `test_no_500_when_real_probe_fails` |
| Timeout curto e configurável ou justificado | ✅ `HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS` (2.0s, configurável) |
| Resposta não expõe tokens nem dados sensíveis | ✅ sem token enviado; URL→`configured`/`not_configured`; `detail` controlado; teste `test_probe_sends_no_internal_token` |
| Testes cobrem ok, degraded, timeout e misconfigured | ✅ (e ainda unavailable, invalid response, auth) |
| Documentação actualizada | ✅ matriz + README + `.env.example` + schema |
| Relatório lista ficheiros, rota, testes, resultados e próximo passo | ✅ este documento |

---

## 10. Próximo passo recomendado

**OBS-STG-004 — Smoke test operacional Backend Core ↔ Intelligence Engine.**
Reutilizar o teste opt-in `apps/campaigns/tests/test_intelligence_real_loop.py`
(`RUN_REAL_IE=1`) e/ou criar um management command opt-in; validar
`ENABLED`/`DRY_RUN=false`/token/`BASE_URL`, confirmar as 6 chaves do resultado e a
ausência de token nos logs, e documentar o caso "IE desligado". O healthcheck
agregado agora criado dá o sinal rápido de disponibilidade antes de correr o smoke.
