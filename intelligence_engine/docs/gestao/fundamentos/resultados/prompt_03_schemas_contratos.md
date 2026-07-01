# Relatório de execução — Prompt 03: Schemas Pydantic e contratos internos

Definição dos schemas Pydantic e contratos internos do Intelligence Engine
(IE-003), preparando — sem implementar a lógica — os endpoints de analysis,
scoring, recommendations, moments e o endpoint composto.

## Contexto consultado (sem alterações)

Inspeccionados em `backend_core` para alinhar os vocabulários do contrato com
as entidades reais do produto (nenhum ficheiro alterado):

- `apps/campaigns/models.py` — `Campaign` (campaign_type, status), `CampaignGoal`.
- `apps/catalogue/models.py` — `Artist`, `Track` (track_type, status).
- `apps/content/models.py` — `ContentPack.PackType` (→ `ContentPackKey`),
  `Template.TemplateType` (→ `OutputType`), `ContentPackRequest`, `ContentOutput`.
- `apps/reports/models.py` — `Report`, `MediaKit`.
- `apps/links/models.py` — `SmartLink`, `SmartLinkClick` (→ `SmartLinkStats`).

Em `content_renderer` confirmou-se o padrão do envelope interno
(`src/jobs/job.schema.ts`): `payload_version` como string obrigatória, `entity
{type,id}` estrito, envelope `.strict()` (forbid extra). O Intelligence Engine
segue o mesmo padrão.

## Decisões de contrato

1. **Vocabulários alinhados ao Backend Core**. `ContentPackKey` e `OutputType`
   são `Literal`s derivados de `ContentPack.PackType` e `Template.TemplateType`.
   Assim uma recomendação nunca pode sugerir um pack/template que o Django não
   suporta (mitiga IE-RSK-005). `EntityType` usa exactamente os 6 tipos da
   secção 6.3 do backlog.
2. **Envelope estrito, `data` permissivo**. `BaseIntelligenceRequest` e os
   sub-modelos de identificação usam `extra="forbid"` (apanha typos/drift com
   422). O `CampaignDataBundle` e os seus sub-modelos usam `extra="allow"`,
   para o Django poder enriquecer o payload sem partir o contrato
   (mitiga IE-RSK-008). É o equilíbrio explícito entre contrato rígido e baixo
   acoplamento.
3. **`payload_version` obrigatório e pinned a "1.0"**. Tipo reutilizável
   `PayloadVersion` (Annotated + AfterValidator) que exige começar por "1.0";
   "2.0"/"0.9"/"" são rejeitados.
4. **`confidence` numérico (0.0–1.0)**, não Literal. O backlog usa exemplos
   numéricos (0.82, 0.74), por isso `ConfidenceScore` é um float restrito; as
   bandas qualitativas ficam cobertas por `Priority`, `Severity` e `Grade`
   (que são Literals). Decisão registada por divergir ligeiramente da
   sugestão "enums ou Literals para confidence".
5. **Scores `0–100` ou `null`**. `ScoreSet` tem cada score como `Score | None`
   (None = "unknown"), consistente com "sem dados → score null".
6. **Response genérica com PEP 695**. `IntelligenceResponse[ResultT]`
   (sintaxe de type parameters do Python 3.13) evita repetir o envelope cinco
   vezes e gera um schema OpenAPI distinto por endpoint
   (`IntelligenceResponse_ScoringResult_`, etc.). Confirmado compatível com
   Pydantic 2.13.
7. **Endpoints com contrato ligado mas motor por implementar**. Os 5 endpoints
   estão registados com `response_model` e `responses` (para a OpenAPI
   reflectir os contratos), protegidos por `X-Internal-Token`, e validam o
   payload — mas devolvem `501 not_implemented` enquanto os motores não
   existem (IE-004+). Foi adicionado um código de erro de ciclo de vida
   `not_implemented` (501) ao contrato — não é um erro de negócio; espelha o
   `not_implemented` do renderer e será removido quando os motores entrarem.
   "Payload válido aceite" significa, nesta fase, "passa a validação"; o motor
   responde 501 até IE-004+.

## Bug encontrado e corrigido

Ao testar `payload_version` inválido, o endpoint devolvia **500 em vez de
422**. Causa: um `ValueError` de validador custom (Pydantic v2) coloca o
objecto `ValueError` no `ctx` de cada erro; o `exc.errors()` passado tal e qual
ao `JSONResponse` não era serializável (`TypeError: Object of type ValueError
is not JSON serializable`). O teste anterior de 422
(`/internal/_debug/echo`) só exercitava um erro de "campo em falta", sem `ctx`,
pelo que o bug estava mascarado.

Correcção (`app/main.py`, `handle_validation_error`): passar `exc.errors()`
por `fastapi.encoders.jsonable_encoder` — o mesmo padrão do handler default do
FastAPI — tornando o corpo do erro sempre serializável. Adicionado teste de
regressão (`test_bad_payload_version_is_rejected_normalised_not_500`).

## Ficheiros criados

```text
app/schemas/common.py            # vocabulários, EntityRef, BaseIntelligenceRequest, Explanation, Warning
app/schemas/responses.py         # IntelligenceResponse[T], ResponseMetadata, ErrorResponse
app/schemas/campaign.py          # CampaignDataBundle + sub-modelos + contrato de analysis
app/schemas/scoring.py           # ScoreSet, ScoringResult/Request/Response
app/schemas/recommendations.py   # ExpectedOutput, Recommendation, contrato
app/schemas/moments.py           # Moment, contrato
app/schemas/intelligence.py      # IntelligenceResult, contrato composto
app/api/_openapi.py              # INTERNAL_ERROR_RESPONSES (403/422/501)
app/api/analysis.py              # POST /analysis/campaign
app/api/scoring.py               # POST /scoring/campaign
app/api/recommendations.py       # POST /recommendations/campaign
app/api/moments.py               # POST /moments/detect
app/api/intelligence.py          # POST /intelligence/campaign
tests/test_schemas.py            # validação de schemas (válidos/inválidos)
tests/test_contract_endpoints.py # contrato HTTP (403/422/501) + OpenAPI
docs/gestao/fundamentos/resultados/prompt_03_schemas_contratos.md
```

## Ficheiros alterados

```text
app/core/errors.py   # + código not_implemented (501) e NotImplementedYetError
app/main.py          # monta os 5 routers; jsonable_encoder no handler de validação
README.md            # estado IE-003, tabela de endpoints, exemplos request/response, estrutura
```

## Comandos executados

```bash
venv/Scripts/python.exe -m pytest -q          # 61 passed
venv/Scripts/python.exe -m ruff check .       # All checks passed!

# Geração da OpenAPI (contratos reflectidos)
venv/Scripts/python.exe -c "from app.main import create_app; create_app().openapi()"
```

## Resultados

- **pytest**: `61 passed` (era 26; +35 entre `test_schemas.py` e
  `test_contract_endpoints.py`, incluindo as parametrizações pelos 5
  endpoints). 1 warning conhecido (`httpx`/`starlette.testclient`).
- **ruff check .**: `All checks passed!` (incl. modernização para a sintaxe de
  generics PEP 695, UP046).
- **OpenAPI**: gera 9 paths e 37 schemas; cada endpoint de motor documenta a
  resposta 200 (schema concreto por endpoint) e as respostas 403/422/501 com
  `ErrorResponse`. `GET /openapi.json` validado por teste.
- **Contrato HTTP** (por endpoint): sem token → 403
  `unauthorized_internal_request`; payload válido → 501 `not_implemented`
  (validação passou); `entity.type` inválido → 422 `invalid_payload`;
  `payload_version` inválido → 422 (regressão coberta).
- Sem segredos reais em código, docs ou `.env.example` (scan confirmado).

## Pendências

- Lógica dos motores (analysis/scoring/recommendations/moments/composto) —
  IE-004 a IE-008. Cada um substitui o `501 not_implemented` do respectivo
  endpoint.
- `app/api/internal_debug.py` continua a existir (suporta os testes de
  segurança com 200-on-auth); remover quando os motores reais cobrirem o mesmo
  nos seus próprios testes.
- Warning de depreciação `httpx`/`starlette.testclient` — não bloqueante.
- O código `not_implemented` é temporário (ciclo de vida da fase); reavaliar a
  sua remoção quando todos os endpoints tiverem motor.

## Próximo passo recomendado

Avançar para **IE-004 — Campaign analysis MVP**: implementar
`CampaignAnalysisService` por trás de `POST /analysis/campaign`, lendo o
`CampaignDataBundle` e devolvendo `CampaignAnalysisResult` (health, summary,
strengths/weaknesses/opportunities/risks) com `explanations`/`warnings`
determinísticos e explicáveis, substituindo o `501` pelo resultado real.
