# Intelligence Engine

Serviço FastAPI da plataforma **ChartRex / MomentFlow**.

> **Separação de responsabilidades**
>
> - O **Django (Backend Core)** governa o produto: utilizadores, workspaces,
>   RBAC, billing, créditos, campanhas, persistência principal e orquestração.
> - O **Content/Report Renderer** gera activos (PNG/PDF/HTML).
> - O **Intelligence Engine** (este serviço) calcula scores, detecta
>   oportunidades e recomenda acções de campanha — sem gerir utilizadores,
>   sem persistir estado de produto e sem chamar directamente o renderer.
> - O **Frontend** orquestra a experiência do utilizador, sempre através do
>   Django.

Ver o backlog completo em
[`docs/gestao/fundamentos/backlog.md`](docs/gestao/fundamentos/backlog.md).

Contrato de integração Backend Core ↔ Intelligence Engine (IE-009):
[`docs/gestao/fundamentos/contrato_backend_core_intelligence_engine.md`](docs/gestao/fundamentos/contrato_backend_core_intelligence_engine.md)
— recomenda chamadas **síncronas** ao endpoint composto no MVP (híbrido
sync-first), com headers, payloads, erros, timeouts e retries documentados.

## Estado

Fase actual: **IE-010 — validação e documentação final** (fase encerrada).
Estado detalhado, validações executadas e veredicto pronto/não-pronto em
[`estado_fastapi_intelligence_engine.md`](docs/gestao/fundamentos/estado_fastapi_intelligence_engine.md).

Implementado:

- Aplicação FastAPI via factory `create_app()` (`app/main.py`), com settings
  injectadas em `app.state` e rotas de diagnóstico montadas só fora de
  `production`.
- `GET /health` — público, devolve identificação do serviço.
- Configuração via variáveis de ambiente, validada no arranque
  (`app/core/config.py`): `INTERNAL_API_TOKEN` vazio em `production` impede
  o arranque (`config_error`).
- Autenticação interna por `X-Internal-Token` (`app/core/security.py`),
  aplicável como dependency a qualquer endpoint protegido, com comparação em
  tempo constante sobre bytes UTF-8 (`hmac.compare_digest`).
- Logger estruturado em JSON (UTC), com redacção de campos sensíveis e
  unificação dos loggers do Uvicorn (`app/core/logging.py`).
- Modelo de erro normalizado com os 5 códigos do contrato MVP —
  `invalid_payload`, `unauthorized_internal_request`, `not_found`,
  `internal_error`, `config_error` — mais o código de ciclo de vida
  `not_implemented` (501), agora sem uso (todos os motores implementados; o
  código mantém-se disponível para futuros stubs). Exception handlers
  em `app/main.py` cobrem `AppError`, validação de payload (422), rotas
  desconhecidas (404), outros erros de cliente do framework (p.ex. 405) e
  qualquer excepção não tratada (500, sem stack trace na resposta).
- **Schemas Pydantic e contratos internos** (`app/schemas/`): envelope comum
  validado (`payload_version`, `workspace_id`, `request_id`, `entity`),
  vocabulários controlados (entity type, health, grade, priority, severity,
  action, moment type, content pack, output type), e contratos de
  request/response para analysis, scoring, recommendations, moments e o
  endpoint composto.
- **Endpoints registados** (`app/api/`) com os contratos ligados à OpenAPI.
- **`POST /analysis/campaign` implementado** (`CampaignAnalysisService`):
  análise heurística determinística e explicável (sem IA generativa, sem
  chamadas externas, sem persistência).
- **`POST /scoring/campaign` implementado** (`ScoringEngine`): cinco scores
  0–100 (ou `null`/unknown), grade A/B/C/D/unknown, cada score com uma
  `Explanation` que enumera os componentes ponderados que o produziram — ou um
  `Warning` quando não é calculável. Determinístico, sem IA generativa, sem
  chamadas externas, sem persistência.
- **`POST /recommendations/campaign` implementado** (`RecommendationEngine`):
  recomendações de campanha com `action`, `priority`, `confidence`, `reason`,
  `suggested_content_pack`/`expected_outputs` (quando aplicável) e
  `explanations` por recomendação. Reaproveita o motor de scoring (apenas o
  output público) e lê os sinais do data bundle. **Só sugere** — nunca cria
  entidades no Django nem chama o renderer; cada pack/template sugerido vem do
  catálogo semeado do produto.
- **`POST /moments/detect` implementado** (`MomentDetector`): detecção
  determinística dos oito momentos MVP (release_window, weekly_growth,
  milestone_reached, low_engagement, content_gap, report_due, media_kit_missing,
  smart_link_activity), cada um com `type`, `severity`, `confidence`, `summary`,
  `recommended_action` (compatível com o recommendation engine) e
  `explanations`. Lê o data bundle directamente (baixo acoplamento); sem IA, sem
  scraping, sem chamadas externas, sem persistência. Dados insuficientes →
  lista vazia + warning.
- **`POST /intelligence/campaign` implementado** (`IntelligenceOrchestrator`):
  endpoint composto que orquestra os quatro motores e agrega `analysis`,
  `scores`, `grade`, `moments`, `recommendations`, `summary` executivo,
  `explanations` consolidadas e `warnings` consolidados (deduplicados por
  `code`). Uma falha previsível numa etapa é convertida em warning
  `<etapa>_unavailable` (sem `500` indevido); os serviços continuam testáveis
  isoladamente. Sem chamadas ao Backend Core nem ao renderer, sem persistência.
- Testes de segurança, contrato de erro, factory/gating, validação de
  schemas, contrato HTTP dos endpoints, do serviço de análise, e dos motores de
  scoring, recommendations, moments e do orquestrador composto (`tests/`).

**Todos os motores MVP estão implementados** (IE-004 → IE-008), o contrato de
integração com o Backend Core está documentado (IE-009) e a fase foi validada e
encerrada (IE-010 — ver tabela de validações no documento de estado).

## Endpoints

| Rota                          | Método | Autenticação | Estado            |
| ------------------------------ | ------- | ------------- | ------------------ |
| `/health`                      | GET     | público        | OK                 |
| `/analysis/campaign`           | POST    | X-Internal-Token | **implementado** |
| `/scoring/campaign`            | POST    | X-Internal-Token | **implementado** |
| `/recommendations/campaign`    | POST    | X-Internal-Token | **implementado** |
| `/moments/detect`              | POST    | X-Internal-Token | **implementado** |
| `/intelligence/campaign`       | POST    | X-Internal-Token | **implementado** |

Os contratos completos estão na OpenAPI gerada automaticamente
(`GET /openapi.json`, ou `/docs` em desenvolvimento).

## `POST /analysis/campaign`

Análise heurística, **determinística** e **explicável** de uma campanha. O
mesmo input gera sempre o mesmo output. As regras de recência são ancoradas a
um `context.reference_date` opcional (ISO `YYYY-MM-DD`); sem ele, as regras
degradam para presença em vez de lerem o relógio do sistema.

### Regras heurísticas

| Regra | Condição                                       | Sinal / efeito                            |
| ----- | ----------------------------------------------- | ------------------------------------------ |
| R0    | bundle de dados vazio                           | `campaign_health=unknown` + warning `insufficient_data` |
| R1    | content outputs `completed` presentes           | strength `has_content_outputs`             |
| R1b   | …e recentes (janela de 14 dias, se datáveis)    | strength `recent_content_outputs`          |
| R2    | sem content outputs `completed`                 | opportunity `content_gap`                  |
| R3    | smart link com actividade positiva              | strength `smart_link_activity`             |
| R4    | smart link presente mas sem actividade          | weakness `smart_link_no_activity`          |
| R4b   | estatísticas de smart link ausentes             | warning `smart_link_stats_missing`         |
| R5    | sem report `completed` recente (janela 30 dias) | opportunity `report_due`                   |
| R6    | sem media kit `generated`/`published`           | opportunity `media_kit_missing`            |
| R7    | campanha `active` sem conteúdo nem tracção       | risk `active_campaign_no_traction`         |
| C1–C3 | dados contraditórios/incompletos                | warning (nunca 500)                        |

`campaign_health`: `unknown` (R0) · `critical` (há risco e nenhum strength) ·
`warning` (há risco/weakness, ou sinais sem tendência positiva clara) ·
`good` (strengths, sem riscos nem weaknesses).

### Exemplo de request

```json
{
  "payload_version": "1.0",
  "workspace_id": "ws-1",
  "request_id": "req-1",
  "entity": { "type": "campaign", "id": "campaign-1" },
  "context": { "reference_date": "2026-06-24" },
  "data": {
    "campaign": { "id": "campaign-1", "status": "active" },
    "content_outputs": [{ "status": "completed", "created_at": "2026-06-20" }],
    "smart_link_stats": { "total_clicks": 1200, "clicks_last_7_days": 90 },
    "previous_reports": [{ "status": "completed", "period_end": "2026-06-10" }],
    "media_kits": [{ "status": "published" }]
  }
}
```

### Exemplo de response

```json
{
  "status": "completed",
  "engine": "intelligence_engine",
  "engine_version": "0.1.0",
  "request_id": "req-1",
  "workspace_id": "ws-1",
  "result": {
    "campaign_health": "good",
    "summary": "Campaign health assessed as 'good'. Signals — strengths: 3, weaknesses: 0, opportunities: 0, risks: 0.",
    "strengths": [
      "The campaign has produced content outputs.",
      "Recent content output activity.",
      "Smart links are receiving activity."
    ],
    "weaknesses": [],
    "opportunities": [],
    "risks": []
  },
  "explanations": [
    { "code": "has_content_outputs", "message": "1 completed content output(s) found.", "weight": 0.2 }
  ],
  "warnings": [],
  "metadata": { "generated_at": null, "payload_version": "1.0" }
}
```

> Os `data` bundles são deliberadamente permissivos (`extra="allow"`): o
> Backend Core pode enriquecer o payload sem quebrar o contrato. O envelope
> de identificação é estrito (`extra="forbid"`): campos desconhecidos no topo
> são rejeitados com `422 invalid_payload`.

## `POST /scoring/campaign`

Cálculo **determinístico** e **explicável** de cinco scores 0–100 (ou
`null`/unknown) e de uma `grade` A/B/C/D/unknown. O mesmo input gera sempre o
mesmo output (sem IA generativa, sem chamadas externas, sem persistência). As
regras de recência são ancoradas a `context.reference_date` (ISO
`YYYY-MM-DD`); sem ele, degradam para presença em vez de lerem o relógio.

Cada score é `round(100 · Σ pesoᵢ · valorᵢ)`, com cada `valorᵢ ∈ [0,1]` e os
pesos de cada score a somarem 1.0. Um score só é `null` quando os seus dados de
entrada estão ausentes (regra `computável sse`); uma campanha presente mas
fraca pontua baixo, não `null`. **Cada score calculável traz uma `Explanation`
que enumera os componentes ponderados; cada score não calculável traz um
`Warning`** (`<score>_unknown`) e valor `null`. Nada é opaco: o número é uma
soma ponderada auditável.

### Pesos e regras por score

**`campaign_readiness_score`** — quão completa está a configuração da campanha.
Calculável sse existe objecto `campaign`.

| Componente         | Peso | Vale 1.0 quando…                                  |
| ------------------ | ---: | -------------------------------------------------- |
| `status_known`     | 0.20 | `campaign.status` é um estado de ciclo de vida conhecido |
| `artist_present`   | 0.15 | há dados de artista                                |
| `track_present`    | 0.15 | há dados de faixa                                  |
| `goal_defined`     | 0.15 | `primary_goal` definido ou `goals` listados        |
| `schedule_defined` | 0.15 | `start_date` presente                              |
| `media_kit_ready`  | 0.20 | existe media kit `generated`/`published`           |

**`momentum_score`** — tracção actual; dominado por cliques (a tracção do smart
link é o sinal primário). Calculável sse `smart_link_stats` presente OU há
`content_outputs`.

| Componente       | Peso | Valor                                              |
| ---------------- | ---: | -------------------------------------------------- |
| `clicks_7d`      | 0.40 | `saturate(clicks_last_7_days, 100)`                |
| `clicks_30d`     | 0.25 | `saturate(clicks_last_30_days, 400)`               |
| `total_clicks`   | 0.15 | `saturate(total_clicks, 2000)`                     |
| `recent_content` | 0.20 | `saturate(outputs completos recentes, 2)`; sem `reference_date` → 0.5 se há outputs completos |

**`content_opportunity_score`** — espaço para criar conteúdo agora (alto = mais
lacunas, ponderado por oportunidade temporal). Calculável sse há
campaign/track/content_outputs/previous_reports/media_kits.

| Componente          | Peso | Vale 1.0 quando…                                |
| ------------------- | ---: | ------------------------------------------------ |
| `content_gap`       | 0.35 | sem conteúdo completo (recente → 0.0; antigo → 0.4; recência desconhecida → 0.2) |
| `report_due`        | 0.20 | sem report completo recente (janela 30 dias)     |
| `media_kit_missing` | 0.20 | sem media kit utilizável                          |
| `timing_relevance`  | 0.25 | janela de lançamento (±14 dias); senão `active`=0.6, `scheduled`=0.5, `paused`=0.3, outro=0.0 |

**`risk_score`** — risco de a campanha falhar (alto = mais risco). Calculável
sse `campaign` presente OU `smart_link_stats` presente.

| Componente           | Peso | Vale 1.0 quando…                                |
| -------------------- | ---: | ------------------------------------------------ |
| `no_traction`        | 0.35 | `active` + sem conteúdo + sem actividade de link |
| `link_inactivity`    | 0.20 | stats presentes mas sem cliques (0.5 se há links activos mas sem cliques; sem stats → 0.0) |
| `content_gap_active` | 0.15 | campanha `active` sem conteúdo completo           |
| `overdue`            | 0.15 | `end_date < reference_date` e não `completed`/`archived` |
| `data_quality`       | 0.15 | datas inconsistentes ou contadores de link negativos |

**`priority_score`** — urgência de agir. Mistura dos outros quatro (o risco
*aumenta* a prioridade). Pesos **renormalizados** sobre os scores disponíveis;
calculável sse pelo menos dois dos quatro existem.

| Score de entrada            | Peso |
| --------------------------- | ---: |
| `content_opportunity_score` | 0.35 |
| `momentum_score`            | 0.25 |
| `risk_score`                | 0.20 |
| `campaign_readiness_score`  | 0.20 |

### Grade

A `grade` deriva de um composto separado `overall_standing` que reflecte como a
campanha está (não a urgência): mistura de `readiness`, `momentum` e risco
*invertido* (`100 − risk`), renormalizada sobre o que existir.

| Composto `overall_standing` | Pesos                                         |
| --------------------------- | --------------------------------------------- |
| `readiness`                 | 0.35                                          |
| `momentum`                  | 0.35                                          |
| `risk_inverted` (100 − risk) | 0.30                                         |

Limiares: **A** ≥ 80 · **B** ≥ 65 · **C** ≥ 45 · **D** < 45 · **unknown**
quando nenhum dos três entra no composto.

### Tratamento de dados insuficientes

- Bundle vazio → os cinco scores `null`, `grade=unknown`, um `Warning`
  `<score>_unknown` por score, `grade_unknown` e um `insufficient_data`
  agregado. `status` permanece `completed` (não é um erro HTTP).
- Verificações de consistência **avisam, nunca rebentam**:
  `inconsistent_campaign_dates`, `negative_smart_link_stats` (contadores
  negativos são tratados como zero) e `future_content_output_date`.
- `context.reference_date` inválido → warning `invalid_reference_date`,
  ignorado.

### Exemplo de request

```json
{
  "payload_version": "1.0",
  "workspace_id": "ws-1",
  "request_id": "req-1",
  "entity": { "type": "campaign", "id": "campaign-1" },
  "context": { "reference_date": "2026-06-24" },
  "data": {
    "campaign": { "status": "active", "primary_goal": "grow", "start_date": "2026-06-01", "end_date": "2026-12-31" },
    "artist": { "name": "Nova" },
    "track": { "release_date": "2026-06-20" },
    "smart_link_stats": { "total_clicks": 2000, "clicks_last_7_days": 120, "clicks_last_30_days": 500, "active_links": 4 },
    "content_outputs": [{ "status": "completed", "created_at": "2026-06-22" }],
    "previous_reports": [{ "status": "completed", "period_end": "2026-06-10" }],
    "media_kits": [{ "status": "published" }]
  }
}
```

### Exemplo de response

```json
{
  "status": "completed",
  "engine": "intelligence_engine",
  "engine_version": "0.1.0",
  "request_id": "req-1",
  "workspace_id": "ws-1",
  "result": {
    "scores": {
      "campaign_readiness_score": 100,
      "momentum_score": 90,
      "content_opportunity_score": 25,
      "risk_score": 0,
      "priority_score": 51
    },
    "grade": "A"
  },
  "explanations": [
    { "code": "campaign_readiness_score", "message": "campaign_readiness_score=100/100 — weighted components: [status_known w0.20 v1.00, ...].", "weight": 0.2 },
    { "code": "momentum_score", "message": "momentum_score=90/100 — weighted components: [clicks_7d w0.40 v1.00, ..., recent_content w0.20 v0.50].", "weight": 0.25 },
    { "code": "grade", "message": "grade=A (overall_standing=96/100) — weighted blend of [readiness w0.35 v100, momentum w0.35 v90, risk_inverted w0.30 v100] ...", "weight": null }
  ],
  "warnings": [],
  "metadata": { "generated_at": null, "payload_version": "1.0" }
}
```

## `POST /recommendations/campaign`

Geração **determinística** e **explicável** de recomendações de campanha. O
motor **só sugere**: nunca cria entidades no Django, nunca chama o renderer,
nunca persiste. Honra a tese arquitectural —

```text
Intelligence recomenda → Django decide e cria jobs → Renderer gera activos.
```

**Baixo acoplamento.** O motor reutiliza o motor de scoring apenas pelo seu
output público (`ScoreSet`), que orienta prioridade/confiança e a decisão
"campanha saudável → no_action". Os gatilhos específicos (janela de
lançamento, milestone, crescimento semanal, media kit em falta, report em
atraso, smart link inactivo) são lidos directamente do data bundle. Não importa
helpers privados do scoring nem da análise.

**Compatível com o produto (risco IE-RSK-005).** Cada `suggested_content_pack`
e cada `expected_outputs.template_key` vem do catálogo semeado em
`backend_core/apps/content/seeds.py` (espelhado como constantes, sem importar
Django). O motor nunca recomenda algo que o produto não consiga cumprir; os
`Literal` `ContentPackKey`/`OutputType` reforçam o vocabulário ao nível do
schema.

### Regras

Cada regra dispara de forma independente; o resultado é ordenado por prioridade,
depois confiança (desc), depois nome da acção (determinístico).

| Gatilho | Acção | Prioridade | Confiança | Pack sugerido |
| --- | --- | --- | --- | --- |
| Dados insuficientes (todos os scores `null`) | `wait_for_more_data` | low | 0.30 | — |
| Faixa dentro da janela de lançamento (±14 dias) | `create_release_post` | high | 0.85 | `release_pack` |
| Campanha de lançamento `active`/`scheduled` (sem janela) | `create_release_post` | medium | 0.70 | `release_pack` |
| Goal `milestone` `achieved` | `create_milestone_post` | high | 0.80 | `milestone_pack` |
| `campaign_type = milestone_campaign` | `create_milestone_post` | high | 0.75 | `milestone_pack` |
| `total_clicks ≥ 1000` | `create_milestone_post` | medium | 0.65 | `milestone_pack` |
| `campaign_type = weekly_growth_campaign` (active) | `create_weekly_growth_post` | medium | 0.75 | `weekly_growth_pack` |
| `clicks_last_7_days ≥ 20` (active) | `create_weekly_growth_post` | medium | 0.65 | `weekly_growth_pack` |
| Sem media kit utilizável | `create_media_kit` | high (media_campaign) / medium | 0.70 | `auto_media_kit` |
| Sem report recente, com substância para reportar | `create_report` | medium | 0.70 | — (`system_report`) |
| Campanha `active` com actividade de smart link (sem post semanal) | `create_story` | low | 0.60 | — (`system_story`) |
| Smart link configurado mas inactivo | `improve_smart_link` | high (active) / medium | 0.70 | — |
| Nada disparou, dados suficientes | `no_action` | low | 0.50 | — |

Janelas/limiares documentados como constantes: `RELEASE_WINDOW_DAYS=14`,
`REPORT_DUE_AFTER_DAYS=30`, `MILESTONE_CLICKS_THRESHOLD=1000`,
`WEEKLY_GROWTH_CLICKS_THRESHOLD=20`. As confianças são fixas por regra (nunca
aleatórias).

**Dados insuficientes** → uma única recomendação `wait_for_more_data` e um
`Warning` `insufficient_data`. Avisos de consistência do scoring
(`inconsistent_campaign_dates`, `negative_smart_link_stats`,
`future_content_output_date`, `invalid_reference_date`) são propagados.

### Exemplo de request

```json
{
  "payload_version": "1.0",
  "workspace_id": "ws-1",
  "request_id": "req-1",
  "entity": { "type": "campaign", "id": "campaign-1" },
  "context": { "reference_date": "2026-06-24" },
  "data": {
    "campaign": { "status": "active", "campaign_type": "single_release" },
    "track": { "release_date": "2026-06-20" },
    "smart_link_stats": { "total_clicks": 1500, "clicks_last_7_days": 25 }
  }
}
```

### Exemplo de response (excerto)

```json
{
  "status": "completed",
  "result": {
    "recommendations": [
      {
        "action": "create_release_post",
        "priority": "high",
        "confidence": 0.85,
        "reason": "The campaign is in its release moment; publish a release post.",
        "suggested_content_pack": "release_pack",
        "expected_outputs": [
          { "output_type": "post", "format": "png", "template_key": "system_post" }
        ],
        "explanations": [
          { "code": "release_window", "message": "The track release date is within the release window.", "weight": null }
        ]
      }
    ]
  },
  "explanations": [
    { "code": "scoring_basis", "message": "Recommendations derived from scores — readiness=…, momentum=…, opportunity=…, risk=…, priority=…." }
  ],
  "warnings": []
}
```

## `POST /moments/detect`

Detecção **determinística** e **explicável** de momentos simples — sinais que
justificam uma acção de campanha. O detector é um *sensor* sobre o data bundle:
lê os sinais directamente (baixo acoplamento — não chama o scoring nem o
recommendation engine), mas mantém-se **consistente** com eles (mesmos limiares;
cada `recommended_action` é uma acção que o recommendation engine sabe cumprir).
Sem IA generativa, sem scraping, sem chamadas externas, sem persistência.

Cada momento tem `type`, `severity` (low/medium/high), `confidence` (0–1),
`summary`, `recommended_action` e `explanations`. A lista é ordenada por
severidade, depois confiança (desc), depois tipo (determinístico).

### Momentos detectados

| Momento | Gatilho | Severidade | Acção recomendada |
| --- | --- | --- | --- |
| `release_window` | faixa a ±14 dias da data de referência (±3 → high) | high/medium | `create_release_post` |
| `weekly_growth` | `weekly_growth_campaign` ou `clicks_last_7_days ≥ 20` | medium | `create_weekly_growth_post` |
| `milestone_reached` | goal milestone `achieved` / `milestone_campaign` / `total_clicks ≥ 1000` | high/medium | `create_milestone_post` |
| `low_engagement` | smart link presente mas sem actividade | high (active)/medium | `improve_smart_link` |
| `content_gap` | sem conteúdo completo (ou apenas conteúdo antigo) | high/medium/low | `create_release_post` |
| `report_due` | sem report recente, com substância para reportar | medium | `create_report` |
| `media_kit_missing` | campanha sem media kit utilizável | high (media_campaign)/medium | `create_media_kit` |
| `smart_link_activity` | smart links com actividade (e `weekly_growth` não disparou) | low | `create_story` |

Limiares (partilhados com scoring/recommendations): `RELEASE_WINDOW_DAYS=14`,
`RELEASE_IMMINENT_DAYS=3`, `RECENT_CONTENT_WINDOW_DAYS=14`,
`REPORT_DUE_AFTER_DAYS=30`, `MILESTONE_CLICKS_THRESHOLD=1000`,
`WEEKLY_GROWTH_CLICKS_THRESHOLD=20`. Confianças fixas por sinal (nunca
aleatórias). `weekly_growth` suprime o `smart_link_activity` (já captura a
actividade forte).

**Dados insuficientes** (bundle vazio) → `moments: []` e um `Warning`
`insufficient_data`. Avisos de consistência (`inconsistent_campaign_dates`,
`negative_smart_link_stats`, `invalid_reference_date`) avisam, nunca rebentam.

### Exemplo de request

```json
{
  "payload_version": "1.0",
  "workspace_id": "ws-1",
  "request_id": "req-1",
  "entity": { "type": "campaign", "id": "campaign-1" },
  "context": { "reference_date": "2026-06-24" },
  "data": {
    "campaign": { "status": "active", "campaign_type": "single_release" },
    "track": { "release_date": "2026-06-25" },
    "smart_link_stats": { "total_clicks": 1500, "clicks_last_7_days": 25 }
  }
}
```

### Exemplo de response (excerto)

```json
{
  "status": "completed",
  "result": {
    "moments": [
      {
        "type": "release_window",
        "severity": "high",
        "confidence": 0.9,
        "summary": "The track release date is within 1 day(s) of the reference date.",
        "recommended_action": "create_release_post",
        "explanations": [
          { "code": "release_window_detected", "message": "Track release_date is 1 day(s) from the reference date (window 14d).", "weight": null }
        ]
      }
    ]
  },
  "explanations": [],
  "warnings": []
}
```

## `POST /intelligence/campaign`

Endpoint **composto**: numa só chamada, o Backend Core obtém o diagnóstico
completo. O `IntelligenceOrchestrator` **orquestra** os quatro motores já
existentes (não reimplementa lógica) e agrega tudo:

```text
analysis (IE-004) · scoring (IE-005) · moments (IE-007) · recommendations (IE-006)
```

A resposta agrega `analysis`, `scores`, `grade`, `moments`, `recommendations` e
um `summary` executivo, mais `explanations` e `warnings` **consolidados**
(deduplicados por `code`, em ordem de etapa fixa). É determinístico, não chama o
Backend Core nem o renderer e não persiste.

**Resiliência por etapa.** Cada motor corre dentro de um `_safe`: uma falha
previsível numa etapa (excepção inesperada sobre input já validado) é convertida
num warning `<etapa>_unavailable` e a secção correspondente fica no seu valor por
omissão — **nunca um `500`** para o diagnóstico inteiro. Erros de payload
continuam a ser rejeitados a montante (`422` normalizado).

**Dados insuficientes** → `analysis.campaign_health=unknown`, scores `null`,
`grade=unknown`, `moments: []`, uma recomendação `wait_for_more_data` e um único
`Warning` `insufficient_data` consolidado.

### Exemplo de request

```json
{
  "payload_version": "1.0",
  "workspace_id": "ws-1",
  "request_id": "req-1",
  "entity": { "type": "campaign", "id": "campaign-1" },
  "context": { "reference_date": "2026-06-24" },
  "data": {
    "campaign": { "status": "active", "campaign_type": "single_release", "primary_goal": "grow", "start_date": "2026-06-01", "end_date": "2026-12-31" },
    "artist": { "name": "Nova" },
    "track": { "release_date": "2026-06-25" },
    "smart_link_stats": { "total_clicks": 1500, "clicks_last_7_days": 25, "clicks_last_30_days": 300, "active_links": 4 },
    "content_outputs": [{ "status": "completed", "created_at": "2026-06-22" }],
    "media_kits": [{ "status": "published" }]
  }
}
```

### Exemplo de response (excerto)

```json
{
  "status": "completed",
  "engine": "intelligence_engine",
  "engine_version": "0.1.0",
  "request_id": "req-1",
  "workspace_id": "ws-1",
  "result": {
    "analysis": { "campaign_health": "good", "summary": "…", "strengths": ["…"], "weaknesses": [], "opportunities": [], "risks": [] },
    "scores": { "campaign_readiness_score": 100, "momentum_score": 50, "content_opportunity_score": 45, "risk_score": 0, "priority_score": 48 },
    "grade": "A",
    "moments": [
      { "type": "release_window", "severity": "high", "confidence": 0.9, "summary": "…", "recommended_action": "create_release_post", "explanations": [ … ] }
    ],
    "recommendations": [
      { "action": "create_release_post", "priority": "high", "confidence": 0.85, "reason": "…", "suggested_content_pack": "release_pack", "expected_outputs": [ … ], "explanations": [ … ] }
    ],
    "summary": "Campaign health 'good', grade A. Scores — readiness 100, momentum 50, opportunity 45, risk 0, priority 48. 4 moment(s) detected; 4 recommendation(s), top action create_release_post."
  },
  "explanations": [
    { "code": "has_content_outputs", "message": "…" },
    { "code": "campaign_readiness_score", "message": "…", "weight": 0.2 },
    { "code": "scoring_basis", "message": "…" }
  ],
  "warnings": [],
  "metadata": { "generated_at": null, "payload_version": "1.0" }
}
```

## Stack

- **Python 3.13**
- **FastAPI** + **Uvicorn**
- **Pydantic** / **pydantic-settings** — validação e configuração
- **pytest** + **httpx** (via `TestClient`) — testes
- **ruff** — lint

## Instalação

```bash
cd intelligence_engine
python -m venv venv
# Windows
venv\Scripts\python.exe -m pip install -r requirements.txt
# macOS/Linux
venv/bin/python -m pip install -r requirements.txt
```

Copia o template de ambiente e ajusta se necessário:

```bash
cp .env.example .env
```

## Execução local

```bash
venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8201
```

Verificação rápida:

```bash
curl http://localhost:8201/health
```

Resposta esperada:

```json
{
  "status": "ok",
  "service": "intelligence_engine",
  "version": "0.1.0",
  "timestamp": "2026-06-24T00:00:00+00:00"
}
```

## Variáveis de ambiente

Ver [`.env.example`](.env.example) para a lista completa. Resumo:

| Variável              | Default              | Descrição                                                   |
| ---------------------- | --------------------- | ------------------------------------------------------------ |
| `APP_ENV`               | `development`          | `development` \| `production` \| `test`                       |
| `SERVICE_NAME`          | `intelligence_engine`  | Nome do serviço, devolvido em `/health`                      |
| `SERVICE_VERSION`       | `0.1.0`                | Versão do contrato MVP, devolvida em `/health`                |
| `LOG_LEVEL`             | `INFO`                 | Nível mínimo do logger estruturado                           |
| `INTERNAL_API_TOKEN`    | _(vazio)_              | Segredo partilhado para `X-Internal-Token`. Obrigatório (não vazio) em `production`; em `development`/`test` pode ficar vazio, mas então **nenhum** pedido a um endpoint protegido é aceite. |

Nenhuma destas variáveis deve conter segredos reais em `.env.example`, README
ou documentação.

## Autenticação interna (`X-Internal-Token`)

Todos os endpoints internos, **excepto `GET /health`**, exigem o header:

```text
X-Internal-Token: <token-partilhado>
```

Regras aplicadas por `app/core/security.require_internal_token` (dependency
que lê o token configurado de `request.app.state.settings`):

- header ausente → `403 unauthorized_internal_request`;
- header com valor errado → `403 unauthorized_internal_request`;
- nenhum `INTERNAL_API_TOKEN` configurado → `403` em **todos** os pedidos
  (não é tratado como acesso livre);
- comparação feita com `hmac.compare_digest` sobre os bytes UTF-8 (tempo
  constante; tolera tokens não-ASCII sem rebentar);
- o valor do token nunca é incluído em respostas, `details` de erro, ou
  registos de log (chaves com `token`, `secret`, `password`, `authorization`,
  `api_key`, `credential` são redigidas automaticamente pelo logger
  estruturado).

### Endpoints internos temporários de diagnóstico

`app/api/internal_debug.py` define três rotas **temporárias**, usadas apenas
para validar a autenticação e o contrato de erros nesta fase (não existe
ainda nenhum endpoint de negócio real). **Só são montadas fora de
`production`** (`app_env != "production"`):

| Rota                          | Método | Objectivo                                              |
| ------------------------------ | ------- | -------------------------------------------------------- |
| `/internal/_debug/ping`        | GET     | Confirma autenticação bem-sucedida (200)                 |
| `/internal/_debug/echo`        | POST    | Exercita validação de payload (`invalid_payload`, 422)   |
| `/internal/_debug/boom`        | GET     | Força uma excepção não tratada (`internal_error`, 500)   |

Estas rotas devem ser **removidas** quando os endpoints reais de
analysis/scoring/recommendations/moments (IE-004 em diante) passarem a
exercitar a mesma autenticação e o mesmo contrato de erro nos seus próprios
testes.

## Contrato de erro normalizado

Qualquer falha — autenticação, payload inválido, rota inexistente ou
excepção inesperada — é devolvida no formato comum (backlog, secção 6.5):

```json
{
  "status": "failed",
  "error": { "code": "unauthorized_internal_request", "message": "...", "details": {} },
  "metadata": { "engine": "intelligence_engine", "engine_version": "0.1.0" }
}
```

Códigos implementados: `invalid_payload` (422; também usado para outros erros
de cliente 4xx do framework, p.ex. 405, preservando o status original),
`unauthorized_internal_request` (403), `not_found` (404), `internal_error`
(500), `config_error` (falha de arranque, não chega a produzir resposta HTTP)
e `not_implemented` (501; código de ciclo de vida, actualmente sem uso —
todos os motores estão implementados). Excepções não tratadas nunca expõem stack trace ao
cliente; o traceback completo é registado apenas no logger estruturado do
servidor.

## Application factory

`app/main.py` expõe `create_app(settings=None)` e instancia `app =
create_app()` para o Uvicorn. A factory:

- valida a configuração ao construir `Settings` (logo, configuração inválida
  — p.ex. `INTERNAL_API_TOKEN` vazio em `production` — falha aqui, antes de a
  app existir);
- guarda as settings em `app.state.settings`, de onde as rotas e a
  autenticação as lêem (injecção explícita, sem singleton global no caminho
  do pedido);
- monta as rotas de diagnóstico apenas fora de `production`;
- unifica o logging: os loggers do Uvicorn (`uvicorn`, `uvicorn.error`,
  `uvicorn.access`) passam a propagar para o handler JSON da raiz, por isso
  **todas** as linhas de log — arranque, acesso e aplicação — saem no mesmo
  formato estruturado.

## Testes

```bash
venv/Scripts/python.exe -m pytest -v
```

197 testes (unitários + contrato HTTP), todos a passar. Não existe
configuração de coverage (`pytest-cov`) nem de type-checking estático
(`mypy`/`pyright`) no projecto — ver
[`estado_fastapi_intelligence_engine.md`](docs/gestao/fundamentos/estado_fastapi_intelligence_engine.md)
para detalhe sobre o que foi e não foi validado.

## Lint

```bash
venv/Scripts/python.exe -m ruff check .
venv/Scripts/python.exe -m ruff format --check .
```

## Estrutura

```text
intelligence_engine/
  app/
    main.py              # create_app() factory, lifespan, exception handlers
    constants.py          # SERVICE_NAME / SERVICE_VERSION
    api/
      health.py           # GET /health (lê settings de app.state)
      analysis.py         # POST /analysis/campaign
      scoring.py          # POST /scoring/campaign
      recommendations.py  # POST /recommendations/campaign
      moments.py          # POST /moments/detect
      intelligence.py     # POST /intelligence/campaign (composto)
      internal_debug.py   # TEMPORÁRIO — só fora de production
      _openapi.py         # fragmentos de documentação de erro partilhados
    core/
      config.py           # Settings (pydantic-settings), validação de produção
      security.py          # require_internal_token (dependency X-Internal-Token)
      logging.py           # Logger estruturado em JSON, UTC, com redacção
      errors.py             # AppError e os códigos de erro do contrato
    schemas/
      common.py           # vocabulários, EntityRef, BaseIntelligenceRequest, Explanation, Warning
      responses.py        # IntelligenceResponse[T], ResponseMetadata, ErrorResponse
      campaign.py         # data bundle + contrato de analysis
      scoring.py          # contrato de scoring
      recommendations.py  # contrato de recommendations
      moments.py          # contrato de moments
      intelligence.py     # contrato composto
    services/
      campaign_analysis.py  # CampaignAnalysisService (IE-004)
      scoring_engine.py     # ScoringEngine (IE-005)
      recommendation_engine.py  # RecommendationEngine (IE-006)
      moment_detector.py    # MomentDetector (IE-007)
      intelligence_orchestrator.py  # IntelligenceOrchestrator (IE-008)
  tests/
    test_health.py
    test_config.py
    test_security.py
    test_errors.py
    test_app_factory.py     # gating de production + falha de arranque
    test_schemas.py         # validação de schemas (válidos/inválidos)
    test_contract_endpoints.py  # contrato HTTP + OpenAPI
    test_campaign_analysis_service.py  # regras heurísticas + determinismo
    test_analysis_endpoint.py          # contrato HTTP de /analysis/campaign
    test_scoring_engine.py             # scores/grade + limites + determinismo
    test_scoring_endpoint.py           # contrato HTTP de /scoring/campaign
    test_recommendation_engine.py      # regras de recomendação + determinismo
    test_recommendations_endpoint.py   # contrato HTTP de /recommendations/campaign
    test_moment_detector.py            # detecção de momentos + determinismo
    test_moments_endpoint.py           # contrato HTTP de /moments/detect
    test_intelligence_orchestrator.py  # agregação/consolidação + resiliência
    test_intelligence_endpoint.py      # contrato HTTP de /intelligence/campaign
  docs/gestao/fundamentos/
    backlog.md
    resultados/            # Relatórios de execução de cada prompt
  requirements.txt
  pyproject.toml            # config do ruff
  pytest.ini
  .env.example
```

## Limitações

- **Heurísticas, não inteligência preditiva**: scores/pesos/limiares são
  constantes fixadas no MVP (IE-RSK-002), não calibradas com dados reais de
  produção. Mitigado por explicabilidade total (cada score/recomendação/momento
  traz a sua justificação), nunca apresentado como "IA".
- **Sem coverage formal**: não há `pytest-cov`/relatório de coverage
  configurado; a confiança vem de 197 testes deterministas (regra a regra,
  incluindo invariantes de "dados insuficientes" e de catálogo suportado) e não
  de uma percentagem de linhas cobertas.
- **Sem type-checking estático**: não há `mypy`/`pyright` configurado no
  projecto; a verificação de tipos é apenas a validação em runtime do Pydantic
  mais as anotações usadas pelo editor.
- **Sem integração real testada**: os testes exercitam o IE isoladamente
  (`TestClient`); não há ainda nenhuma chamada real do Backend Core Django a
  este serviço (o contrato IE-009 define o desenho, mas o "wiring" do lado
  Django não foi implementado nesta fase).
- **Catálogo de produto espelhado, não importado**: `RecommendationEngine` e
  `MomentDetector` espelham o catálogo semeado de `backend_core/apps/content`
  como constantes Python; se o catálogo real mudar sem actualizar estas
  constantes, as sugestões podem ficar desalinhadas (mitigação: testes de
  invariante dedicados, mas sem verificação cruzada automática entre os dois
  repositórios).
- **Sem persistência nem estado entre pedidos**: cada pedido é avaliado de
  forma isolada; não há memória de pedidos anteriores, deduplicação entre
  pedidos, nem _rate limiting_.
- **`internal_debug` ainda presente**: as rotas de diagnóstico
  (`app/api/internal_debug.py`) continuam montadas fora de `production`;
  servem apenas para exercitar autenticação/erros nos testes.

## Próximos passos

A fase do MVP do Intelligence Engine está **encerrada** (IE-004 → IE-010). Fora
do âmbito desta fase, e fora deste serviço:

- **Backend Core**: implementar o lado Django do contrato documentado em
  IE-009 — chamada síncrona ao endpoint composto, adaptador que monte o `data`
  bundle a partir dos modelos reais, e decisão sobre persistência de snapshots
  (pendências PD-1 a PD-4 do contrato).
- **Calibração**: rever pesos/limiares heurísticos à luz de dados reais de
  campanhas, quando existirem.
- **Observabilidade**: métricas básicas (latência, taxa de erro por endpoint)
  ficam fora do MVP, mas são recomendadas antes de produção a sério.
