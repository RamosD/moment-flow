# Contrato de integração — Backend Core ↔ Intelligence Engine

> **Estado:** proposto (IE-009). Documenta o contrato e a recomendação de
> integração para o **MVP** do Intelligence Engine. **Não** introduz código de
> integração no Backend Core; o Backend Core já tem a maior parte da
> infra-estrutura necessária (ver §2).
>
> **Âmbito:** apenas o serviço `intelligence_engine`. Nenhum ficheiro de
> `backend_core` ou `content_renderer` foi alterado por este documento.

---

## 1. Objectivo

Definir como o **Backend Core (Django)** deve chamar o **Intelligence Engine
(FastAPI)** e o que esperar em troca: endpoints, autenticação, headers,
payloads, respostas, erros, timeouts, retries, modo síncrono vs job externo,
persistência, exemplos, riscos e decisões pendentes.

Princípio arquitectural (inalterado):

```text
Django governa o produto e orquestra.
Intelligence Engine calcula scores, momentos e recomendações — e devolve.
Django decide o que fazer com o resultado (criar jobs, persistir, notificar).
```

---

## 2. Padrão de integração existente (análise)

O Backend Core **já** tem uma camada de integração madura em
`apps/integrations_bridge`, usada hoje para o Content/Report Renderer:

- **`InternalServiceClient`** (`clients.py`) — cliente HTTP JSON sobre
  `urllib` (sem dependências novas). Envia sempre os headers internos
  (`X-Internal-Token`, `X-Workspace-ID`, `X-Job-ID`, `X-Request-ID`,
  `Content-Type`), **nunca regista o token**, e normaliza falhas em excepções
  tipadas: `InternalClientTimeout`, `InternalServiceUnavailable`,
  `InternalHTTPError`, `InvalidJSONResponse`.
- **`registry.py`** — resolve `job_type → provider → (base_url, timeout)` a
  partir de settings. Para o Intelligence Engine:
  `INTELLIGENCE_ENGINE_BASE_URL`, `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS`.
  Switches globais: `EXTERNAL_JOBS_ENABLED`, `EXTERNAL_JOBS_DRY_RUN`.
- **`ExternalJobReference`** (`models.py`) + **`create_and_submit_external_job`**
  (`services.py`) — modelo **assíncrono**: o Django regista um job, faz
  `POST /jobs/` no serviço externo com um envelope
  (`job_id`, `workspace_id`, `request_id`, `job_type`, `callback_url`,
  `entity`, `payload_version`, `payload`), e o serviço externo **responde mais
  tarde** via callback para `callback_url`. Inclui idempotência
  (`<job_type>:<entity_id>`) e retry explícito (`retry_external_job`).
- **`intelligence.py`** — builders/services **já preparados** para o
  Intelligence Engine, mas modelados como jobs assíncronos
  (`metrics_collection`, `moment_detection`, `insight_generation`,
  `recommendation_generation`), com handlers de callback placeholder que apenas
  persistem o `callback_payload` (não calculam nada).

O **Content Renderer** confirma o mesmo padrão assíncrono: `GET /health`
público + `POST /jobs` protegido por `X-Internal-Token` (comparação em tempo
constante), valida o envelope, e **devolve um ack rápido** seguido de
**callback** com o resultado.

### 2.1 Divergência fundamental (o ponto de decisão)

O Intelligence Engine **MVP** (IE-004 → IE-008) é **síncrono**: cada endpoint
calcula em memória (heurísticas determinísticas, sem I/O, sem rede) e devolve o
resultado **no corpo da resposta HTTP**. **Não** implementa `POST /jobs/`, não
emite callbacks, não persiste, e não expõe `metrics_collection` nem
`insight_generation`.

| Dimensão | Backend Core (scaffolding actual) | Intelligence Engine MVP (implementado) |
|---|---|---|
| Modelo | Assíncrono: `POST /jobs/` + callback | Síncrono: pedido → resposta inline |
| Endpoints | `/jobs/` (genérico, `job_type` no envelope) | `/analysis/campaign`, `/scoring/campaign`, `/recommendations/campaign`, `/moments/detect`, `/intelligence/campaign` |
| Job types | `metrics_collection`, `moment_detection`, `insight_generation`, `recommendation_generation` | n/a (endpoints nomeados) |
| Resultado | Callback para o Django | Corpo da resposta |
| Persistência | `ExternalJobReference` no Django | Nenhuma (em tempo real) |

Esta divergência é exactamente a decisão pendente **IE-PDEC-001** (síncrono vs
job externo). A recomendação está em §3.

---

## 3. Recomendação: híbrido com **síncrono como default do MVP** (Opção C, sync-first)

**Para o MVP, usar chamadas síncronas** aos endpoints nomeados do Intelligence
Engine. Justificação:

- O cálculo do MVP é **em memória, determinístico, sem I/O** (sub-milissegundo).
  Não há nada "longo" que justifique um job assíncrono.
- Um round-trip de callback acrescenta latência, estado (`ExternalJobReference`),
  segurança de callback e idempotência — **custo sem benefício** para insights
  rápidos.
- Alinha com o backlog (IE-PDEC-001: "MVP síncrono; futuro job externo para
  análises pesadas") e com IE-PDEC-002 ("MVP: devolver em tempo real").

**Reservar o caminho assíncrono (`ExternalJobReference` + `/jobs/` + callback)
para trabalho pesado futuro** que o scaffolding do Backend Core já antecipa e
que **não** faz parte do MVP do Intelligence Engine — em particular
`metrics_collection` (recolha real de métricas de plataformas, que implicaria
scraping/APIs externas) e futura inferência ML. Daí "híbrido".

```text
MVP  (agora):   Django --HTTP sync-->  /intelligence/campaign  --inline-->  Django
Futuro (pesado): Django --/jobs/--> IE (job)  ... IE --callback--> Django
```

> **Nota de integração (não implementada aqui):** para chamar o IE de forma
> síncrona, o Django **reutiliza** o `InternalServiceClient.post_json` já
> existente, apontando-o para o endpoint nomeado em vez de `/jobs/`. Não é
> preciso `ExternalJobReference` para o caminho síncrono. O wiring no Backend
> Core fica para uma fase futura (ver §11) — **este documento não o
> implementa**.

---

## 4. Endpoints

Base URL: `INTELLIGENCE_ENGINE_BASE_URL` (ex.: `http://intelligence:8001`).

| Método | Rota | Autenticação | Descrição | Recomendado para |
|---|---|---|---|---|
| GET | `/health` | pública | Liveness; identifica serviço/versão | health-check/monitorização |
| POST | `/analysis/campaign` | `X-Internal-Token` | Diagnóstico de campanha | análise isolada |
| POST | `/scoring/campaign` | `X-Internal-Token` | 5 scores 0–100 + grade | scoring isolado |
| POST | `/recommendations/campaign` | `X-Internal-Token` | Recomendações de acção | recomendações isoladas |
| POST | `/moments/detect` | `X-Internal-Token` | Momentos detectados | momentos isolados |
| POST | `/intelligence/campaign` | `X-Internal-Token` | **Composto**: análise + scores + momentos + recomendações + summary | **entrada preferida** (uma chamada) |

**Recomendação:** o Django deve preferir o **endpoint composto**
`POST /intelligence/campaign` — obtém o diagnóstico completo numa única chamada
síncrona, com `explanations`/`warnings` consolidados. Os endpoints individuais
ficam disponíveis para casos em que só se precisa de uma faceta.

---

## 5. Autenticação

- Header obrigatório em todos os endpoints excepto `GET /health`:
  `X-Internal-Token: <segredo-partilhado>`.
- O segredo é o mesmo `INTERNAL_API_TOKEN` partilhado (o Django já o tem em
  settings; o IE lê-o de `INTERNAL_API_TOKEN`).
- Comparação em **tempo constante** (`hmac.compare_digest` sobre bytes UTF-8).
- Token ausente, vazio ou errado → **403 `unauthorized_internal_request`**.
- Se o IE não tiver token configurado (dev/test), **todos** os pedidos
  protegidos são rejeitados (403) — "sem token" nunca significa "acesso livre".
- Em `production`, o IE **não arranca** com token vazio (`config_error` no boot).
- O token viaja **apenas em headers**, nunca em payloads, respostas ou logs (de
  ambos os lados).

---

## 6. Headers

| Header | Obrigatório | Notas |
|---|---|---|
| `X-Internal-Token` | sim (excepto `/health`) | segredo partilhado |
| `Content-Type: application/json` | sim | corpo JSON |
| `X-Workspace-ID` | recomendado | correlação/observabilidade; o IE também recebe `workspace_id` no corpo |
| `X-Request-ID` | recomendado | correlação de logs entre serviços; o IE também recebe `request_id` no corpo |
| `X-Job-ID` | opcional | só relevante no caminho assíncrono; ignorado no síncrono |

> No caminho síncrono, a **fonte de verdade** dos identificadores é o **corpo**
> (`workspace_id`, `request_id`). Os headers servem correlação/observabilidade.
> (No caminho assíncrono do renderer, o `/jobs/` exige consistência estrita
> entre header e corpo — isso não se aplica ao síncrono do IE.)

---

## 7. Payload (request)

Envelope comum (igual para todos os endpoints de campanha):

```jsonc
{
  "payload_version": "1.0",          // obrigatório; tem de começar por "1.0"
  "workspace_id": "ws-1",            // obrigatório, não vazio
  "request_id": "req-abc-123",       // obrigatório, não vazio
  "entity": { "type": "campaign", "id": "campaign-1" },  // type ∈ vocabulário fechado
  "context": { "reference_date": "2026-06-24" },          // opcional; ancora regras temporais
  "data": { /* campaign data bundle — ver abaixo */ }
}
```

- **`entity.type`** ∈ `campaign | artist | track | content_pack_request | report | media_kit`.
- **`context.reference_date`** (ISO `YYYY-MM-DD`) ancora todas as regras de
  recência/janela. **Recomenda-se enviá-lo sempre**; sem ele, as regras
  degradam para presença (não lêem o relógio), preservando determinismo.
- Campos desconhecidos **no topo** do envelope → `422` (envelope estrito).

### 7.1 `data` — campaign data bundle (permissivo)

O `data` é **deliberadamente permissivo** (`extra="allow"`): o Django pode
enriquecer sem quebrar o contrato. Campos lidos pelo MVP:

```jsonc
{
  "campaign": { "id", "name", "campaign_type", "status", "start_date", "end_date", "primary_goal" },
  "artist":   { "id", "name", "primary_genre", "status" },
  "track":    { "id", "title", "release_date", "track_type", "status" },
  "smart_link_stats": { "total_clicks", "clicks_last_7_days", "clicks_last_30_days", "active_links" },
  "content_outputs":  [ { "id", "output_type", "status", "created_at" } ],
  "previous_reports": [ { "id", "report_type", "status", "period_end" } ],
  "media_kits":       [ { "id", "status" } ],
  "goals":            [ { "goal_type", "status", ... } ]
}
```

Os shapes espelham as entidades do Backend Core (`apps.campaigns`,
`apps.catalogue`, `apps.content`, `apps.reports`, `apps.links`) **sem as
importar**. Vocabulários relevantes: `campaign.status`
(`draft|scheduled|active|paused|completed|archived`), `campaign.campaign_type`
(`single_release|…|weekly_growth_campaign|milestone_campaign|media_campaign|…`),
`content_outputs[].status=completed`, `media_kits[].status∈{generated,published}`.

> **Mapeamento com o scaffolding assíncrono do Django.** Os builders actuais
> (`build_*_payload` em `integrations_bridge/intelligence.py`) produzem
> `{workspace_id, campaign_id, track_id, platform_links, *_context}` — um shape
> **diferente** deste `data` bundle. Quando o Django ligar o caminho síncrono,
> tem de montar este `data` a partir dos seus modelos. Ver §10.

---

## 8. Respostas

### 8.1 Sucesso (`200`)

Envelope comum (`backlog` §6.4):

```jsonc
{
  "status": "completed",
  "engine": "intelligence_engine",
  "engine_version": "0.1.0",
  "request_id": "req-abc-123",
  "workspace_id": "ws-1",
  "result": { /* específico do endpoint */ },
  "explanations": [ { "code", "message", "weight"? } ],
  "warnings": [ { "code", "message", "details"? } ],
  "metadata": { "generated_at": null, "payload_version": "1.0" }
}
```

- `result` do composto: `{ analysis, scores, grade, moments, recommendations, summary }`.
- `metadata.generated_at` é **`null`** por desenho (determinismo;
  o timestamping é do Backend Core).
- **Dados insuficientes não são erro**: devolvem `200` com `status=completed`,
  secções vazias/`unknown` e um `Warning` `insufficient_data`.

### 8.2 Erro (`4xx/5xx`)

Envelope normalizado (`backlog` §6.5):

```jsonc
{
  "status": "failed",
  "error": { "code": "invalid_payload", "message": "…", "details": { } },
  "metadata": { "engine": "intelligence_engine", "engine_version": "0.1.0" }
}
```

| HTTP | `error.code` | Quando | Lado Django |
|---|---|---|---|
| 403 | `unauthorized_internal_request` | token ausente/errado | corrigir token; **não** retentar |
| 422 | `invalid_payload` | envelope/tipos inválidos | corrigir payload; **não** retentar |
| 404 | `not_found` | rota inexistente | corrigir URL; **não** retentar |
| 500 | `internal_error` | excepção inesperada (sem stack trace exposto) | retry seguro (ver §9) |
| — | `config_error` | só no boot do IE (token vazio em prod) | operacional, não chega a HTTP |

> O `internal_error` **nunca** expõe stack trace no corpo; o traceback fica
> apenas no logger estruturado do IE.

---

## 9. Timeouts e retry recomendado

### 9.1 Timeouts

- O Django usa `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` (registry).
- O cálculo síncrono é sub-milissegundo; o tempo de parede é dominado por
  rede/serialização. **Sugestão: 5–10 s** (margem ampla; idêntico ao padrão do
  renderer para chamadas internas).
- Timeout no cliente → o Django trata como `InternalClientTimeout`.

### 9.2 Retry

O Intelligence Engine síncrono **não tem efeitos colaterais** (não persiste,
não cria entidades, não chama terceiros). Logo, **todas as chamadas são
idempotentes e seguras de retentar**.

| Situação | Retry? | Política sugerida |
|---|---|---|
| `InternalClientTimeout` | sim | até 2 tentativas, backoff curto (ex.: 0.5 s, 1 s) |
| `InternalServiceUnavailable` (serviço em baixo) | sim | até 2 tentativas, backoff |
| `500 internal_error` | sim (cauteloso) | 1 retry; se persistir, degradar |
| `403`, `404`, `422` | **não** | erro de contrato/configuração; corrigir, não retentar |
| `InvalidJSONResponse` | não | tratar como falha; investigar |

- Como o resultado é determinístico e sem estado, **não é necessária chave de
  idempotência** no caminho síncrono (cada chamada é independente).
- Recomenda-se **degradação graciosa** no Django: se o IE falhar após os
  retries, a feature de produto continua sem o insight (o insight é
  enriquecimento, não bloqueante).

---

## 10. Modo síncrono vs job externo (resumo de decisão)

| Caminho | Quando usar | Mecanismo | Persistência |
|---|---|---|---|
| **Síncrono (MVP, recomendado)** | analysis/scoring/recommendations/moments/intelligence | `InternalServiceClient.post_json(<endpoint nomeado>)` | nenhuma no IE; Django decide se faz snapshot |
| **Job externo (futuro)** | trabalho pesado: recolha real de métricas, ML | `ExternalJobReference` + `POST /jobs/` + callback (já existe no Django) | `ExternalJobReference` + `callback_payload` |

### 10.1 Mapeamento `job_type` (scaffolding) ↔ endpoint síncrono (IE MVP)

Quando o Django migrar o IE para síncrono, o mapeamento conceptual é:

| `job_type` (Django actual) | Endpoint síncrono IE | Notas |
|---|---|---|
| `moment_detection` | `POST /moments/detect` | directo |
| `recommendation_generation` | `POST /recommendations/campaign` | directo |
| `insight_generation` | `POST /analysis/campaign` (+ `/scoring/campaign`) | "insight" ≈ análise+scoring |
| `metrics_collection` | **n/a no MVP** | implica recolha externa → fica no caminho assíncrono futuro |
| (tudo de uma vez) | `POST /intelligence/campaign` | **preferido**: 1 chamada |

---

## 11. Persistência dos resultados

- **O Intelligence Engine não persiste nada** (IE-PDEC-002 — MVP em tempo real).
- O **Django decide**: para o MVP, consumir a resposta em tempo real e
  apresentá-la; quando fizer sentido, persistir um **snapshot** de insights
  relevantes num modelo do Django (fora de âmbito deste documento).
- Os identificadores (`request_id`, `workspace_id`) e o `payload_version` são
  ecoados na resposta para correlação/auditoria do lado do Django.

---

## 12. Exemplos

> Os tokens nos exemplos são **placeholders**, não segredos reais.

### 12.1 Health (sem auth)

```bash
curl http://intelligence:8001/health
```

```json
{ "status": "ok", "service": "intelligence_engine", "version": "0.1.0", "timestamp": "2026-06-24T00:00:00+00:00" }
```

### 12.2 Composto (síncrono, recomendado)

```bash
curl -X POST http://intelligence:8001/intelligence/campaign \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: <INTERNAL_API_TOKEN>" \
  -H "X-Workspace-ID: ws-1" \
  -H "X-Request-ID: req-abc-123" \
  -d '{
    "payload_version": "1.0",
    "workspace_id": "ws-1",
    "request_id": "req-abc-123",
    "entity": { "type": "campaign", "id": "campaign-1" },
    "context": { "reference_date": "2026-06-24" },
    "data": {
      "campaign": { "status": "active", "campaign_type": "single_release", "primary_goal": "grow", "start_date": "2026-06-01", "end_date": "2026-12-31" },
      "artist": { "name": "Nova" },
      "track": { "release_date": "2026-06-25" },
      "smart_link_stats": { "total_clicks": 1500, "clicks_last_7_days": 25, "clicks_last_30_days": 300, "active_links": 4 },
      "content_outputs": [ { "status": "completed", "created_at": "2026-06-22" } ],
      "media_kits": [ { "status": "published" } ]
    }
  }'
```

Resposta (excerto):

```json
{
  "status": "completed",
  "engine": "intelligence_engine",
  "engine_version": "0.1.0",
  "request_id": "req-abc-123",
  "workspace_id": "ws-1",
  "result": {
    "analysis": { "campaign_health": "good", "summary": "…", "strengths": ["…"], "weaknesses": [], "opportunities": [], "risks": [] },
    "scores": { "campaign_readiness_score": 100, "momentum_score": 50, "content_opportunity_score": 45, "risk_score": 0, "priority_score": 48 },
    "grade": "A",
    "moments": [ { "type": "release_window", "severity": "high", "confidence": 0.9, "summary": "…", "recommended_action": "create_release_post", "explanations": [ … ] } ],
    "recommendations": [ { "action": "create_release_post", "priority": "high", "confidence": 0.85, "reason": "…", "suggested_content_pack": "release_pack", "expected_outputs": [ … ], "explanations": [ … ] } ],
    "summary": "Campaign health 'good', grade A. Scores — readiness 100, momentum 50, opportunity 45, risk 0, priority 48. …"
  },
  "explanations": [ { "code": "campaign_readiness_score", "message": "…", "weight": 0.2 } ],
  "warnings": [],
  "metadata": { "generated_at": null, "payload_version": "1.0" }
}
```

### 12.3 Dados insuficientes (não é erro)

```bash
curl -X POST http://intelligence:8001/intelligence/campaign \
  -H "Content-Type: application/json" -H "X-Internal-Token: <INTERNAL_API_TOKEN>" \
  -d '{ "payload_version":"1.0", "workspace_id":"ws-1", "request_id":"req-1", "entity":{"type":"campaign","id":"c1"} }'
```

```json
{
  "status": "completed",
  "result": {
    "analysis": { "campaign_health": "unknown", "summary": "Insufficient data to analyse this campaign." },
    "scores": { "campaign_readiness_score": null, "momentum_score": null, "content_opportunity_score": null, "risk_score": null, "priority_score": null },
    "grade": "unknown",
    "moments": [],
    "recommendations": [ { "action": "wait_for_more_data", "priority": "low", "confidence": 0.3, "reason": "…" } ],
    "summary": "Campaign health 'unknown', grade unknown. …"
  },
  "warnings": [ { "code": "insufficient_data", "message": "…" } ]
}
```

### 12.4 Erro de payload (rejeitado, normalizado)

```json
// entity.type inválido → HTTP 422
{
  "status": "failed",
  "error": { "code": "invalid_payload", "message": "Payload inválido.", "details": { "errors": [ … ] } },
  "metadata": { "engine": "intelligence_engine", "engine_version": "0.1.0" }
}
```

---

## 13. Riscos

| ID | Risco | Mitigação |
|---|---|---|
| INT-RSK-01 | **Divergência sync/async**: o scaffolding do Django assume `/jobs/`+callback; o IE MVP é síncrono. | Adoptar §3 (sync-first); ligar o caminho síncrono no Django (reutilizar `InternalServiceClient`) numa fase futura, sem tocar no IE. |
| INT-RSK-02 | **Mapeamento de payload**: builders do Django produzem shape diferente do `data` bundle do IE. | Adaptador no Django que monta o `data` bundle a partir dos modelos (§7.1, §10.1). Documentado, não implementado aqui. |
| INT-RSK-03 | `reference_date` ausente reduz fidelidade temporal (regras degradam para presença). | Django enviar sempre `context.reference_date`. |
| INT-RSK-04 | Heurísticas MVP parecerem objectivas mas serem fracas (IE-RSK-002). | Explicabilidade: cada score/momento/recomendação expõe `explanations`; pesos centralizados e auditáveis. |
| INT-RSK-05 | Acoplamento ao formato actual de campaign/report/media kit (IE-RSK-008). | `payload_version` + `data` permissivo; envelope estrito no topo. |
| INT-RSK-06 | Indisponibilidade do IE bloquear features de produto. | Degradação graciosa no Django (insight é enriquecimento, não bloqueante) + retries (§9). |

---

## 14. Decisões

| ID | Questão | Decisão (recomendada) |
|---|---|---|
| IE-PDEC-001 | Síncrono vs job externo | **Síncrono no MVP**; híbrido (job externo) reservado para trabalho pesado futuro (§3). |
| IE-PDEC-002 | Persistir resultados | **Não no IE** (tempo real); Django decide snapshots futuros (§11). |
| IE-PDEC-003 | IA generativa | **Não no MVP**; heurísticas explicáveis. |
| IE-PDEC-004 | Fonte de dados dos scores | `campaign`, `artist`, `track`, `smart_link_stats`, `content_outputs`, `previous_reports`, `media_kits`, `goals` (§7.1). |

### Decisões pendentes (a confirmar com a equipa do Backend Core)

- **PD-1:** Confirmar a adopção do caminho síncrono no Django para o IE (vs.
  manter os jobs assíncronos do scaffolding). Recomendação: síncrono.
- **PD-2:** Definir quem monta o `data` bundle (provável: um serializer/serviço
  novo em `integrations_bridge` ou em `apps.campaigns`).
- **PD-3:** Decidir se/quando persistir snapshots de insight no Django.
- **PD-4:** Confirmar valores de `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` e
  política de retry no lado Django.

---

## 15. Checklist de integração (lado Backend Core, fase futura)

- [ ] Configurar `INTELLIGENCE_ENGINE_BASE_URL` e `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS`.
- [ ] Partilhar o `INTERNAL_API_TOKEN` (mesmo segredo nos dois serviços).
- [ ] Implementar um adaptador que monte o `data` bundle a partir dos modelos.
- [ ] Chamar `POST /intelligence/campaign` (síncrono) via `InternalServiceClient`.
- [ ] Tratar erros tipados (`timeout`/`unavailable`/`http_error`/`invalid_json`) com degradação graciosa + retries (§9).
- [ ] Não persistir o token em lado nenhum; confirmar ausência de secrets em logs.
- [ ] (Opcional) Persistir snapshot de insight se o produto o exigir.
- [ ] (Futuro) Manter `metrics_collection` e trabalho pesado no caminho assíncrono `/jobs/`+callback.

---

## 16. Referências

- Backlog: [`backlog.md`](backlog.md) (§6 contratos, §7 endpoints, §9 critérios, §12 decisões).
- Relatórios de execução: [`resultados/`](resultados/) (prompts 01–08).
- Backend Core (consultado, **não alterado**): `apps/integrations_bridge/`
  (`clients.py`, `registry.py`, `services.py`, `models.py`, `intelligence.py`).
- Content Renderer (consultado, **não alterado**): `src/http/routes.ts`,
  `src/http/middleware.ts` (padrão `/health` + `/jobs` + callback).
