# Prompt 03 — Validar War Room com Intelligence Engine real

**Data:** 2026-07-01
**Fase:** `04_staging_campaign_actions_with_real_ie_renderer` (STG-CA-003, Incremento 1)
**Âmbito:** validar intelligence real via Backend Core, com dry-run desactivado. Sem alteração de lógica de produto.
**Estado de execução:** `executado`

---

## 1. Resumo objectivo

A War Room passou a receber **intelligence real** do Intelligence Engine através do Backend Core:

- `INTELLIGENCE_ENGINE_DRY_RUN` **desactivado** (`false`) — confirmado **efectivo** pela resposta `source=engine` (não `dry_run`).
- Token interno partilhado configurado nos dois serviços (BC + IE); chamada real BC→IE devolve **200**.
- Resposta real: `status=completed`, `grade=D`, `scores` reais, **3 recommendations reais**.
- Frontend chama **apenas** o Backend Core (`/campaigns/{id}/intelligence/`); nunca o IE; nunca envia `X-Internal-Token`.
- Erro controlado confirmado com IE indisponível → **HTTP 503** honesto, sem stacktrace.
- Logs correlacionam `request_id` nos três níveis, **sem tokens**.

---

## 2. dry_run activo/inactivo

| Flag | Valor | Estado efectivo |
|---|---|---|
| `INTELLIGENCE_ENGINE_DRY_RUN` | `false` | **INACTIVO** — provado por `source=engine` na resposta |
| `INTELLIGENCE_ENGINE_ENABLED` | `true` | activo |
| `EXTERNAL_JOBS_DRY_RUN` | `true` | mantido (renderer — fora do âmbito deste prompt; STG-CA-005) |

Configuração aplicada nesta iteração (`backend_core/.env`):
- `INTELLIGENCE_ENGINE_DRY_RUN=false`
- `INTERNAL_API_TOKEN=<definido, oculto>`
- `INTELLIGENCE_ENGINE_INTERNAL_TOKEN=<definido, oculto>` (igual ao anterior)

Criado `intelligence_engine/.env` com `APP_ENV=development` e o **mesmo** `INTERNAL_API_TOKEN` (verificado: token do BC == token do IE, ambos não-vazios).

Serviços **reiniciados** para aplicar (o Django anterior corria externamente em dry-run):
- Backend Core (8100) reiniciado com `manage.py runserver 127.0.0.1:8100 --noreload`.
- Intelligence Engine (8201) reiniciado com o token.

---

## 3. Pré-condições confirmadas

| Item | Resultado |
|---|---|
| IE health (8201) | `GET /health` → 200 `{"service":"intelligence_engine","version":"0.1.0"}` |
| Backend Core (8100) | `GET /api/v1/schema/` → 200 (Django) |
| Dev user | `ca014-dev@example.local` (password de sessão definida via Django shell; não armazenada) |
| Workspace | `46ca02a0-edcf-4835-8878-a6ff24b41598` — "CA014 Dev Workspace" |
| Campaign | `30930999-5cd3-47d8-afb0-2c218084ed7d` — "CA014 Test Campaign" (status=active) |
| Artist | "CA014 Test Artist" |
| Track | **ausente** (campanha sem track) — limita dados de intelligence (ver §8) |

---

## 4. Payload resumido (sem dados sensíveis)

- **Frontend → Backend Core:** `POST /api/v1/campaigns/{id}/intelligence/`, **sem body**, headers `Authorization: Bearer <jwt>` + `X-Workspace-ID: <ws>`.
- **Backend Core → IE:** `POST http://localhost:8201/intelligence/campaign`, headers internos (`X-Internal-Token`, `X-Workspace-ID`, `X-Request-ID`). Corpo do payload (construído pelo BC): `workspace_id`, `campaign_id`, `track_id=null`, `platform_links=[]`, contexto da campanha/artist. Nenhum segredo no corpo (token só em header).

---

## 5. Resposta IE via Backend Core

```
source         = engine        (não dry_run)
status         = completed
engine         = intelligence_engine
engine_version = 0.1.0
request_id     = 82b8472cbfb54c41be34ac98097fc02a
grade          = D
scores         = { campaign_readiness_score: 35, momentum_score: 0,
                   content_opportunity_score: 90, risk_score: 70,
                   priority_score: 52 }
result keys    = analysis, scores, grade, moments, recommendations, summary
warnings       = []
HTTP           = 200 (5461 bytes)
duration       = ~2.1 s (BC↔IE)
```

Chamada repetida (segunda execução): igualmente `source=engine, status=completed, recs=3` — determinística.

---

## 6. Número e tipo de recommendations

**3 recommendations reais.** Campos por recommendation (contrato real do IE):
`action`, `priority`, `confidence`, `reason`, `suggested_content_pack`, `expected_outputs`, `explanations`.

| # | action | priority | confidence |
|---|---|---|---|
| 0 | `improve_smart_link` | high | 0.7 |
| 1 | (medium) | medium | — |
| 2 | (medium) | medium | — |

Exemplo (rec[0], analítico, não sensível):
```json
{
  "action": "improve_smart_link",
  "priority": "high",
  "confidence": 0.7,
  "reason": "Smart links are configured but show no activity; improve them.",
  "suggested_content_pack": null,
  "expected_outputs": [],
  "explanations": [
    { "code": "smart_link_inactive",
      "message": "Smart-link statistics are present but show no clicks or active links.",
      "weight": null }
  ]
}
```

### Campos usados pelo frontend (achado relevante para STG-CA-004)
As recommendations reais **não trazem `id`, `title` nem `type`** (só `action`, `priority`, `reason`, `confidence`, `explanations`, `suggested_content_pack`, `expected_outputs`).

O frontend **já trata este caso por design**: `frontend/src/entities/campaign-action/recommendation-ref.ts` → `deriveRecommendationRef` prefere `id` quando existe e, quando ausente, deriva `ref = {campaignId}:i{index}:{slug(title|action|type)}`. Para rec[0] o ref seria `…:i0:improve-smart-link`. O snapshot (allowlist `id, title, label, action, type, description, reason, priority, confidence`) captura os campos presentes e ignora os ausentes.

**Implicação:** o `recommendation_ref` de recommendations reais é **posicional + conteúdo** (não um id estável do backend). Deduplicação e matching em STG-CA-004 dependem de `index + action` estáveis por chamada. Validar explicitamente na próxima iteração.

---

## 7. Evidência de fronteira e logs

### Frontend não chama IE directamente
- Grep runtime em `frontend/src`: **sem** `localhost:8201`, **sem** `/intelligence/campaign` (path interno do IE), **sem** envio de `X-Internal-Token`. As únicas ocorrências são comentários/constante defensiva.
- `frontend/src/features/campaign-intelligence/intelligence-api.ts` usa o `apiClient` central (base `http://localhost:8100/api/v1`) para `POST /campaigns/${id}/intelligence/`. Comentário do próprio ficheiro: *"the Intelligence Engine is never contacted directly."*
- `IntelligenceSource = 'engine' | 'dry_run'` — o estado visual suporta ambos; com IE real recebe `engine`.

### Logs (Backend Core) — request_id correlacionado, sem tokens
```
INFO integrations_bridge.intelligence intelligence_call start request_id=82b8472… workspace_id=46ca02a0…
INFO integrations_bridge.client       internal_call start job_id=None request_id=82b8472… url=http://localhost:8201/intelligence/campaign
INFO integrations_bridge.client       internal_call ok    job_id=None request_id=82b8472… status=200
INFO integrations_bridge.intelligence intelligence_call ok request_id=82b8472… workspace_id=46ca02a0… status=completed
INFO campaigns.intelligence           intelligence event=ok request_id=82b8472… workspace_id=46ca02a0… campaign_id=30930999… status=completed duration_ms=2130
```
Logs do IE (uvicorn access): `POST /intelligence/campaign HTTP/1.1 200`. **Nenhum token** em qualquer linha (só ids/status/duração).

---

## 8. Erros testados

**Cenário IE indisponível** (parado o processo em 8201, chamada, depois reiniciado):
```
POST /campaigns/{id}/intelligence/  → HTTP 503
body: { "detail": "Campaign intelligence is temporarily unavailable. Try again later." }
stacktrace no body? não
```
Mapeamento confirmado: `IntelligenceUnavailableError → 503` (retryável). Mensagem honesta e segura, sem detalhes internos. Após reinício do IE, a chamada voltou a `source=engine, status=completed, recs=3` (recuperação confirmada).

---

## 9. Validação no browser

**Não executada nesta iteração.** O frontend (5200) está a correr externamente com `strictPort`; usar as ferramentas de preview iniciaria um servidor concorrente e arriscaria derrubar o frontend em execução. A validação visual clicada fica consolidada para **STG-CA-009 (smoke visual)**, conforme ordem do backlog.

Substituto ao nível de código/contrato (feito): confirmado que o frontend consome o endpoint do Backend Core, distingue `engine`/`dry_run` e deriva refs de forma resiliente a recommendations sem id.

---

## 10. Validações executadas

| Validação | Resultado |
|---|---|
| HTTP real via Backend Core (`POST /campaigns/{id}/intelligence/`) | ✅ `source=engine`, `status=completed`, 3 recs |
| Repetição determinística | ✅ 2ª chamada idêntica |
| Cenário IE down | ✅ 503 controlado, sem stacktrace |
| Recuperação após reinício IE | ✅ `source=engine` |
| Grep frontend `localhost:8201` / call directa / token | ✅ ausente (só comentários) |
| Logs sem tokens/secrets | ✅ só ids/status/duração |
| Token BC == token IE (não-vazios) | ✅ |
| IE `/health` (8201) e BC schema (8100) | ✅ 200 |

---

## 11. Limitações

| Limitação | Impacto |
|---|---|
| Campanha de teste **sem track** e sem platform links → intelligence gera `grade=D`, `momentum_score=0` | Médio (STG-R01). São recommendations reais mas de um cenário "fraco". Para exercitar mais tipos de recommendation, criar dados dev com track/links. |
| Recommendations reais **sem `id`/`title`/`type`** → `recommendation_ref` é posicional+conteúdo | Médio (STG-R03/R04). Mitigado no frontend, mas deduplicação/matching a validar em STG-CA-004. |
| Validação visual no browser não executada | Baixo-médio — diferida para STG-CA-009. |
| `EXTERNAL_JOBS_DRY_RUN` ainda `true` | Esperado — renderer é STG-CA-005. |
| Backend Core reiniciado por Claude (o processo externo dry-run foi parado) | Operacional — documentado; serviços IE+BC+CR ficam a correr em background. |

---

## 12. Ficheiros alterados

| Ficheiro | Operação | Nota |
|---|---|---|
| `backend_core/.env` | **alterado** | `INTELLIGENCE_ENGINE_DRY_RUN=false`; `INTERNAL_API_TOKEN` e `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` definidos (dev, não commit) |
| `intelligence_engine/.env` | **criado** | `APP_ENV=development` + `INTERNAL_API_TOKEN` partilhado (dev, não commit) |
| `frontend/docs/.../resultados_execucao/prompt_03_...resultado.md` | **criado** | este relatório |
| `backend_core/db.sqlite3` | password de sessão do dev user redefinida (não persistida no relatório) |

Nenhum código de produto foi alterado. Os `.env` são locais de dev (cobertos por `.gitignore`); nenhum segredo consta deste relatório.

---

## 13. Próximo passo recomendado

Avançar para **STG-CA-004 (criar CampaignActions a partir de recommendations reais)**:
1. A partir das recommendations reais (`improve_smart_link`, etc.), criar `manual_task`, `mark_reviewed`, `dismiss`.
2. Validar `recommendation_ref` posicional+conteúdo (sem id) na criação, deduplicação (ref+type) e múltiplas actions por recommendation.
3. Confirmar que o `recommendation_snapshot` captura só a allowlist (sem copiar o payload integral do IE) com dados reais.

> Serviços a correr em background no fim desta iteração: Backend Core (8100), IE (8201), Content Renderer (8202), Frontend (5200).
