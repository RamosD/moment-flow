# Estado — FastAPI Intelligence Engine

> Documento de estado da fase (IE-001 → IE-010). Actualizado em 2026-06-24.
> Reflecte o que foi **executado e verificado** nesta sessão; não inventa
> resultados que não foram corridos.

## 1. Estado final da fase

**Fase encerrada.** Os cinco motores/endpoints do MVP estão implementados,
testados e documentados; o contrato de integração com o Backend Core está
escrito; não há regressões nas validações disponíveis (pytest, ruff).

| Item | Estado |
| --- | --- |
| Fundação FastAPI (factory, settings, logging, erros) | ✅ Implementado (IE-001/002) |
| Schemas/contratos comuns | ✅ Implementado (IE-003) |
| `POST /analysis/campaign` | ✅ Implementado (IE-004) |
| `POST /scoring/campaign` | ✅ Implementado (IE-005) |
| `POST /recommendations/campaign` | ✅ Implementado (IE-006) |
| `POST /moments/detect` | ✅ Implementado (IE-007) |
| `POST /intelligence/campaign` (composto) | ✅ Implementado (IE-008) |
| Contrato de integração Backend Core ↔ IE | ✅ Documentado (IE-009) |
| Validação e documentação final | ✅ Esta fase (IE-010) |

## 2. Endpoints implementados

| Rota | Método | Auth | Função |
| --- | --- | --- | --- |
| `/health` | GET | pública | identificação do serviço |
| `/analysis/campaign` | POST | `X-Internal-Token` | análise heurística (`campaign_health`, strengths/weaknesses/opportunities/risks) |
| `/scoring/campaign` | POST | `X-Internal-Token` | 5 scores 0–100 + `grade` A–D/unknown |
| `/recommendations/campaign` | POST | `X-Internal-Token` | recomendações de acção com prioridade/confiança |
| `/moments/detect` | POST | `X-Internal-Token` | detecção de 8 tipos de momento |
| `/intelligence/campaign` | POST | `X-Internal-Token` | composto — agrega os quatro anteriores |

Nenhum endpoint usa o código de ciclo de vida `not_implemented` (501); está
definido mas sem uso (todos os motores existem).

## 3. Validações executadas

Todas as validações abaixo foram **corridas nesta sessão**, em
`D:\Workspace\ChartRex\momentflow\intelligence_engine`, com
`venv\Scripts\python.exe`.

### 3.1 Testes automatizados

```text
$ venv/Scripts/python.exe -m pytest -q
197 passed, 1 warning in ~1.3s
```

O único warning é uma `StarletteDeprecationWarning` sobre `httpx`/
`starlette.testclient` (biblioteca de terceiros, não relacionado com o código
do MVP, não bloqueante).

### 3.2 Lint

```text
$ venv/Scripts/python.exe -m ruff check .
All checks passed!
```

### 3.3 Formatação

```text
$ venv/Scripts/python.exe -m ruff format --check .
```

Resultado inicial: 3 ficheiros com formatação desalinhada
(`app/main.py`, `tests/test_app_factory.py`, `tests/test_security.py`) — todas
diferenças de _wrapping_ de linha sem alteração semântica (pré-existentes,
não introduzidas nesta fase). Corrigido com
`venv/Scripts/python.exe -m ruff format <ficheiros>`; reconfirmado:

```text
$ venv/Scripts/python.exe -m ruff format --check .
3 files reformatted, 48 files already formatted   # antes da correcção
# depois da correcção:
$ venv/Scripts/python.exe -m ruff check .
All checks passed!
$ venv/Scripts/python.exe -m pytest -q
197 passed, 1 warning in 1.30s   # sem regressão
```

### 3.4 Type-checking estático (mypy/pyright)

**Não executado — não configurado.** `pip list` confirma que não existe
`mypy` nem `pyright` instalado no `venv`, e não há ficheiro de configuração
(`mypy.ini`, `pyrightconfig.json`, secção `[tool.mypy]`/`[tool.pyright]` em
`pyproject.toml`). Não foi adicionado nesta fase para não introduzir uma nova
ferramenta fora do âmbito do prompt. A correcção de tipos depende, por agora,
apenas da validação em runtime do Pydantic e das anotações usadas pelo editor.

### 3.5 Coverage

**Não executado — não configurado.** Não existe `pytest-cov` instalado nem
configuração de coverage. Não foi adicionado nesta fase pela mesma razão.
A confiança na implementação vem de 197 testes deterministas organizados por
regra/serviço (ver secção 4), não de uma percentagem de linhas cobertas.

### 3.6 Smoke test manual (via `TestClient`, processo real do `create_app()`)

Corrido nesta sessão com um script ad-hoc que instancia `create_app()` e
exercita os endpoints reais (não os testes do `tests/`, mas o mesmo caminho de
código de produção):

```text
GET  /health                              → 200 (sem token, público)
POST /analysis/campaign       sem token    → 403 unauthorized_internal_request
POST /analysis/campaign       com token    → 200 status=completed
POST /scoring/campaign        sem token    → 403 unauthorized_internal_request
POST /scoring/campaign        com token    → 200 status=completed
POST /recommendations/campaign sem token   → 403 unauthorized_internal_request
POST /recommendations/campaign com token   → 200 status=completed
POST /moments/detect          sem token    → 403 unauthorized_internal_request
POST /moments/detect          com token    → 200 status=completed
POST /intelligence/campaign   sem token    → 403 unauthorized_internal_request
POST /intelligence/campaign   com token    → 200 status=completed
POST /scoring/campaign        payload malformado → 422 invalid_payload
```

Os logs estruturados emitidos durante este smoke test foram inspeccionados
manualmente: nenhuma linha contém o valor do token (`smoke-test-token-123456`)
— confirma o comportamento já coberto por `tests/test_security.py::
test_token_is_never_present_in_logs`.

### 3.7 Verificações de ausência de funcionalidades fora do âmbito do MVP

Confirmado por leitura de `app/` (grep dirigido, sem resultados):

| Verificação | Resultado |
| --- | --- |
| Chamadas HTTP a serviços externos (`requests`, `httpx.get/post` para fora, `urllib`) | Nenhuma ocorrência em `app/` |
| Scraping (`beautifulsoup`, `selenium`, `playwright`, `scrapy`) | Nenhuma ocorrência |
| IA generativa (`openai`, `anthropic`, `transformers`, `torch`, `sklearn`) | Nenhuma ocorrência nem em `app/`, nem em `requirements.txt` |
| Base de dados/persistência (`sqlalchemy`, `psycopg`, `sqlite3`, `create_engine`) | Nenhuma ocorrência |
| Chamada directa ao Content Renderer | Nenhuma ocorrência — confirmado também por leitura dos services (`recommendation_engine.py`, `intelligence_orchestrator.py`): só sugerem `suggested_content_pack`/`expected_outputs`, nunca chamam um renderer |

`requirements.txt` confirma a superfície de dependências mínima: `fastapi`,
`uvicorn`, `pydantic`, `pydantic-settings`, `pytest`, `httpx` (cliente de
testes), `ruff`. Nenhuma biblioteca de IA, scraping ou base de dados.

## 4. Cobertura funcional por teste (sem ferramenta de coverage)

| Ficheiro | Nº testes | Foco |
| --- | --- | --- |
| `test_health.py` | — | `GET /health` |
| `test_config.py` | — | `Settings`, bloqueio de arranque em produção |
| `test_security.py` | — | `X-Internal-Token`, tempo constante, ausência de leak em logs |
| `test_errors.py` | — | `AppError`, envelope de erro |
| `test_app_factory.py` | — | gating de rotas de diagnóstico fora de produção |
| `test_schemas.py` | — | validação de payloads (válidos/inválidos) |
| `test_contract_endpoints.py` | — | contrato HTTP comum aos 5 endpoints + OpenAPI sem `501` |
| `test_campaign_analysis_service.py` + `test_analysis_endpoint.py` | — | regras R0–R7/C1–C3, determinismo, contrato HTTP |
| `test_scoring_engine.py` + `test_scoring_endpoint.py` | — | 5 scores, grade, dados insuficientes, contrato HTTP |
| `test_recommendation_engine.py` + `test_recommendations_endpoint.py` | — | regras de recomendação, invariante de catálogo suportado, contrato HTTP |
| `test_moment_detector.py` + `test_moments_endpoint.py` | — | 8 momentos, supressão weekly_growth/smart_link_activity, contrato HTTP |
| `test_intelligence_orchestrator.py` + `test_intelligence_endpoint.py` | — | agregação, isolamento, consolidação/dedup, resiliência por etapa, contrato HTTP |

Total: **197 testes**, todos a passar nesta sessão.

## 5. Limitações conhecidas

- Heurísticas de scoring/recomendação/detecção usam pesos e limiares fixos no
  código (MVP), não calibrados com dados reais de produção (IE-RSK-002).
- Sem coverage formal nem type-checking estático configurados (secções 3.4 e
  3.5) — a confiança vem da suite de testes determinista, não de métricas de
  ferramenta.
- Sem integração real testada contra o Backend Core Django: os testes
  exercitam o IE isoladamente; o "wiring" do lado Django (chamada síncrona ao
  endpoint composto, adaptador de payload) não foi implementado, por estar
  fora do âmbito desta fase (ver contrato IE-009, pendências PD-1 a PD-4).
- O catálogo de content packs/templates é espelhado como constantes Python no
  IE (`recommendation_engine.py`, `moment_detector.py`), não importado do
  Django — risco de desalinhamento se o catálogo real mudar sem actualizar
  estas constantes (IE-RSK-005, mitigado por testes de invariante).
- As rotas de diagnóstico temporárias (`app/api/internal_debug.py`) continuam
  presentes (montadas só fora de `production`), por servirem os testes de
  autenticação/erro; candidatas a remoção numa fase futura.
- Nenhuma métrica de observabilidade (latência, taxa de erro) além de logs
  estruturados — aceitável para o MVP (backlog secção 14.4), recomendado antes
  de produção real.

## 6. Pendências

| ID | Descrição | Lado |
| --- | --- | --- |
| PD-1 | Confirmar adopção do caminho síncrono para o IE (vs. jobs assíncronos já existentes em `integrations_bridge`) | Backend Core |
| PD-2 | Implementar o adaptador Django que monta o `data` bundle do IE a partir dos modelos reais | Backend Core |
| PD-3 | Decidir se/quando persistir snapshots de insight | Backend Core |
| PD-4 | Fixar `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` e política de retry do lado Django | Backend Core |
| — | Calibrar pesos/limiares heurísticos com dados reais | Intelligence Engine (futuro) |
| — | Adicionar coverage/type-checking se a equipa decidir investir nessa ferramenta | Intelligence Engine (futuro) |
| — | Observabilidade (métricas) antes de produção a sério | Intelligence Engine (futuro) |

## 7. Pronto / não pronto

### 7.1 Pronto para integração com o Backend Core

**Sim, do lado do Intelligence Engine.** O serviço expõe um contrato estável,
testado e documentado (5 endpoints + `/health`), com autenticação obrigatória,
erros normalizados e exemplos completos. **Falta o lado Django** (PD-1/PD-2) —
isto não bloqueia o IE, mas significa que a integração ponta-a-ponta ainda não
foi exercitada com tráfego real do Django.

### 7.2 Pronto para piloto técnico

**Sim.** É possível ligar manualmente o Django (ou um cliente de teste) ao IE
seguindo o contrato documentado e obter respostas reais e explicáveis,
incluindo o caminho de dados insuficientes e o de falha parcial controlada.

### 7.3 Pronto para produção

**Não, ainda não — depende de pendências fora do âmbito desta fase**, em
linha com a expectativa do próprio backlog (secção 15):

- Falta o wiring real do Backend Core (PD-1/PD-2/PD-3/PD-4).
- Falta calibração das heurísticas com dados reais.
- Falta observabilidade básica (métricas, não só logs).
- Não há coverage nem type-checking formal — risco aceitável para um MVP
  interno, mas a rever antes de produção a sério.

Nenhuma destas pendências é um bloqueador de **arquitectura**: o desenho
(determinístico, explicável, sem IA generativa, sem persistência, baixo
acoplamento) está implementado e validado; o que falta é trabalho de
integração e operação fora do código deste serviço.

## 8. Ausência de secrets — confirmação

Verificado nesta sessão por leitura/grep dirigido em `README.md`,
`.env.example`, `docs/gestao/fundamentos/**/*.md`:

- `.env.example`: `INTERNAL_API_TOKEN=` vazio, com comentário explícito a
  proibir um valor real.
- `docs/gestao/fundamentos/contrato_backend_core_intelligence_engine.md`:
  todos os exemplos de header usam o placeholder `<INTERNAL_API_TOKEN>`.
- Relatórios em `docs/gestao/fundamentos/resultados/`: as únicas ocorrências
  de "token" em valores literais são tokens de desenvolvimento locais usados
  em comandos de smoke test manual (`smoke-test-token`, `smoke-token`,
  `smoke`) — não são segredos reais, nunca foram usados em produção, e são
  consistentes com o padrão já documentado no `.env.example`.
- Nenhuma ocorrência de padrões de secret conhecidos (`sk-...`, chaves AWS
  `AKIA...`, blocos `-----BEGIN ...`) em ficheiros do projecto (fora de
  `venv/`, que são bibliotecas de terceiros).

## 9. Referências

- Backlog: [`backlog.md`](backlog.md)
- Contrato de integração: [`contrato_backend_core_intelligence_engine.md`](contrato_backend_core_intelligence_engine.md)
- Relatórios de execução por prompt: [`resultados/`](resultados/)
- README: [`../../../README.md`](../../../README.md)
