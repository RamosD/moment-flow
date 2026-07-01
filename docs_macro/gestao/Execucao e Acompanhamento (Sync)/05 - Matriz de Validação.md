---

doc_id: "exec-matriz-validacao"  
title: "Matriz de Validação"  
project: "ChartRex / MomentFlow"  
area: "gestao_execucao"  
doc_type: "validation_matrix"  
status: "active"  
owner: "Aldino Ramos"  
created_at: "2026-06-23"  
updated_at: "2026-06-25"  
last_reviewed_at: "2026-06-25"  
review_frequency: "weekly"  
update_frequency: "per_validation"  
version: "1.3"  
confidentiality: "internal"  
source_of_truth: true

current_phase: "Transição pós-wiring-Intelligence-Engine para próxima fase"  
last_completed_phase: "Backend Core ↔ Intelligence Engine — wiring síncrono (BC-IE-001 a BC-IE-010)"  
validation_scope: "produto_e_tecnico"

validation_count_total: 59  
validation_count_passed: 53  
validation_count_failed: 0  
validation_count_pending: 4  
validation_count_indirect: 2  
last_validation_id: "VAL-059"  
validation_id_prefix: "VAL"

ready_for_integration_environment: true  
ready_for_technical_pilot: true  
ready_for_production: false

---

related_docs:

- "[[status_report]]"
    
- "[[plano_execucao]]"
    
- "[[log_decisoes]]"
    
- "[[riscos_bloqueios]]"
    
- "[[diario_execucao_ia]]"
    

tags:

- "project/momentflow"
    
- "gestao/validacao"
    
- "qualidade"
    
- "testes"
    
- "execucao"
    
- "obsidian"
    

## ai_update_mode: "controlled"  
ai_update_scope: "actualizar critérios de aceitação, comandos executados, resultados, evidências, falhas, pendências e estado de validação, sem marcar validações como aprovadas sem evidência."  
ai_may_create_sections: true  
ai_may_delete_content: false  
ai_should_preserve_history: true

# Matriz de Validação — ChartRex / MomentFlow

## 1. Instruções para IA actualizar este documento

Este documento é a **fonte de verdade de validação** do projecto.

A IA deve actualizar este ficheiro sempre que houver nova validação técnica, funcional, E2E, documental, operacional ou de qualidade.

Ao actualizar este ficheiro, a IA deve:

```text
1. Ler primeiro o README.md desta pasta.
2. Ler os metadados YAML deste documento.
3. Respeitar ai_update_mode e ai_update_scope.
4. Actualizar updated_at no YAML.
5. Actualizar contadores de validação.
6. Adicionar validações com ID sequencial VAL-XXX.
7. Não marcar validação como passed sem evidência.
8. Não inventar comandos executados.
9. Não inventar resultados.
10. Distinguir validação directa, indirecta, pendente e falhada.
11. Registar comandos, evidências, artefactos e limitações.
12. Ligar validações a riscos e decisões quando aplicável.
13. Não apagar validações antigas.
14. Não expor tokens, passwords ou segredos.
```

A IA pode:

```text
- adicionar validações;
- actualizar estado de validações existentes;
- adicionar evidências;
- adicionar comandos executados;
- marcar validações como indirectas quando não houver E2E real;
- adicionar pendências de validação;
- actualizar histórico.
```

A IA não deve:

```text
- transformar teste indirecto em E2E real;
- marcar produção como validada sem S3/R2, observabilidade e política operacional;
- apagar falhas;
- esconder limitações;
- declarar cobertura total quando há ressalvas documentadas;
- confundir validação técnica com validação de produto final.
```

Quando não houver evidência suficiente, usar:

```text
Estado: por confirmar
Evidência: não disponível
Acção necessária: validar manualmente
```

---

# 2. Convenções de validação

## Estados permitidos

```text
passed          = validado com evidência directa;
failed          = falhou;
pending         = ainda não validado;
indirect        = validado por testes indirectos, não por E2E real;
not_applicable  = não aplicável ao escopo actual;
blocked         = não pode ser validado por impedimento externo.
```

## Tipos de validação

```text
unit
integration
e2e
manual
static_analysis
security
documentation
coverage
operational
contract
```

## Severidade de falha

```text
baixa
média
alta
crítica
```

## Critério de evidência mínima

Uma validação só pode ser marcada como `passed` quando existir pelo menos um dos seguintes elementos:

```text
- comando executado com sucesso;
- teste automatizado aprovado;
- relatório de execução;
- evidência E2E;
- checklist manual concluída;
- artefacto gerado;
- output validado;
- estado final confirmado no sistema.
```

---

# 3. Resumo executivo

```text
Estado geral de validação: aprovado para integração e piloto técnico
Falhas abertas: 0
Validações pendentes: 4
Validações indirectas: 2
Pronto para integração: sim
Pronto para piloto técnico: sim
Pronto para produção: não
```

## Leitura executiva

O projecto tem validação suficiente para avançar para a próxima fase de produto.

O **Content/Report Renderer** foi validado em duas camadas (MVP funcional + hardening pós-MVP), o **FastAPI Intelligence Engine** foi validado de fundação a fecho de fase (IE-001 a IE-010) e agora o **wiring síncrono Backend Core ↔ Intelligence Engine** (BC-IE-001 a BC-IE-010) foi validado de ponta a ponta — incluindo um loop real com os dois serviços a correr de facto, não apenas mocks.

Validações finais do Content/Report Renderer:

```text
- build aprovado;
- lint aprovado;
- 136 testes aprovados;
- coverage Vitest configurado e acima dos thresholds;
- E2E PostgreSQL validado nos cenários principais;
- callback em background validado;
- retry de callback validado;
- StorageProvider validado;
- loop Django ↔ Renderer ↔ Django validado;
- documentação final pós-hardening validada.
```

Validações finais do FastAPI Intelligence Engine:

```text
- 197 testes aprovados (pytest);
- ruff check e ruff format --check aprovados;
- smoke test real (TestClient) nos 5 endpoints + /health;
- autenticação X-Internal-Token validada nos 5 endpoints protegidos;
- payloads malformados → 422 normalizado, nunca 500;
- ausência de IA generativa, scraping, persistência e chamada directa ao renderer confirmada por grep dirigido;
- ausência de secrets reais em README/.env.example/docs confirmada;
- contrato de integração Backend Core ↔ Intelligence Engine documentado (IE-009).
```

Validações finais do wiring síncrono Backend Core ↔ Intelligence Engine:

```text
- 459 testes aprovados (pytest -q), 3 skipped (loop real opt-in quando RUN_REAL_IE não está definido);
- ruff check apps/ config/ aprovado;
- manage.py check sem issues;
- schema.yml regenerado sem diff;
- client síncrono, builder de payload, serviço de domínio e endpoint API implementados em camadas isoladas;
- política de timeout/retry/fallback validada (retry só em falhas transitórias, nunca em 4xx);
- 13 cenários E2E com mocks HTTP (sucesso, warnings, timeout, conexão recusada, 403, 422, 5xx, JSON inválido, desligado, dry-run, RBAC/workspace, token não logado);
- loop real validado com os dois serviços a correr de facto: bug de granularidade date/datetime encontrado e corrigido (content_outputs[].created_at), depois confirmado 200/completed com todas as chaves esperadas;
- ausência do token confirmada em logs reais, mesmo em cenário de falha (engine inacessível).
```

Limitações principais:

```text
Renderer: content_generation partially_completed e content_generation failed têm cobertura indirecta por testes Django/Vitest, mas não foram reproduzidos por E2E HTTP real ponta-a-ponta.
Intelligence Engine (isolado): sem coverage formal (pytest-cov) nem type-checking estático (mypy/pyright) configurados.
Wiring Backend Core ↔ Intelligence Engine: sem typecheck configurado no Backend Core (apenas ruff); validação real é local/opt-in (RUN_REAL_IE=1), não corre em CI por padrão; sem observabilidade dedicada (métricas/alertas) para a chamada síncrona; sem calibração de negócio dos scores/recomendações devolvidos via o endpoint real.
```

Conclusão:

```text
Pode avançar para integração e piloto técnico controlado, em todos os três componentes (renderer, Intelligence Engine, wiring síncrono).
Não deve ser declarado production-ready sem S3/R2, observabilidade, métricas e política operacional (renderer), calibração de heurísticas (Intelligence Engine), nem sem observabilidade e staging contínuo para a chamada síncrona (wiring).
```

---

# 4. Comandos finais de validação

## Content/Report Renderer

```bash
npm run build
npm run lint
npm test
npm run test:coverage
```

## FastAPI Intelligence Engine

```bash
venv/Scripts/python.exe -m pytest -q
venv/Scripts/python.exe -m ruff check .
venv/Scripts/python.exe -m ruff format --check .
```

## Backend Core / Integração

```bash
python manage.py check
pytest
```

## Backend Core ↔ Intelligence Engine — wiring síncrono

```bash
venv/Scripts/python.exe -m pytest -q
venv/Scripts/python.exe -m ruff check apps/ config/
venv/Scripts/python.exe manage.py check
venv/Scripts/python.exe manage.py spectacular --file <tmp>   # diff vs schema.yml
# Loop real (opt-in, exige os dois serviços a correr):
RUN_REAL_IE=1 REAL_IE_BASE_URL=http://127.0.0.1:8001 REAL_IE_TOKEN=<token-local> \
    venv/Scripts/python.exe -m pytest apps/campaigns/tests/test_intelligence_real_loop.py -q
```

## E2E

```text
E2E PostgreSQL executado para validar o loop Django ↔ Renderer ↔ Django.
Loop real (sem mocks) executado para validar o loop Django ↔ Intelligence Engine (BC-IE-009).
```

---

# 5. Resultado consolidado das validações

|Métrica|Resultado|Estado|
|---|--:|---|
|Build renderer|Sem erros|passed|
|Lint renderer|Sem erros|passed|
|Testes renderer|136 passed|passed|
|Coverage statements|91.9%|passed|
|Coverage branches|79.32%|passed|
|Coverage functions|95.89%|passed|
|Coverage lines|91.86%|passed|
|Backend `manage.py check`|0 issues|passed|
|Pytest backend relevante|passed|passed|
|E2E PostgreSQL|aprovado para cenários principais|passed|
|Testes Intelligence Engine|197 passed|passed|
|Lint Intelligence Engine (ruff check)|Sem erros|passed|
|Formatação Intelligence Engine (ruff format --check)|Conforme (após correcção)|passed|
|Coverage/type-checking Intelligence Engine|Não configurado|pending|
|Testes wiring Backend Core ↔ Intelligence Engine|459 passed, 3 skipped|passed|
|Lint wiring (ruff check apps/ config/)|Sem erros|passed|
|Backend `manage.py check` (pós-wiring)|0 issues|passed|
|Schema OpenAPI (pós-wiring)|Sem diff após regeneração|passed|
|Loop real Backend Core ↔ Intelligence Engine|200/completed com todas as chaves; token ausente dos logs|passed|
|Typecheck Backend Core (mypy/pyright)|Não configurado|pending|
|Falhas abertas|0|passed|

---

# 6. Matriz geral de validação

| ID      | Área         | Validação                                        | Tipo                   | Estado   | Evidência                   | Observação                                           |
| ------- | ------------ | ------------------------------------------------ | ---------------------- | -------- | --------------------------- | ---------------------------------------------------- |
| VAL-001 | Backend Core | Autenticação, users, workspaces e RBAC           | integration            | passed   | Fase Backend Core concluída | Validado em fase anterior.                           |
| VAL-002 | Backend Core | Catálogo musical, campanhas e content core       | integration            | passed   | Fase Backend Core concluída | Validado em fase anterior.                           |
| VAL-003 | Backend Core | Smart links, tracking, billing e créditos        | integration            | passed   | Fase Backend Core concluída | Validado em fase anterior.                           |
| VAL-004 | Backend Core | Reports, media kits, notifications e audit       | integration            | passed   | Fase Backend Core concluída | Validado em fase anterior.                           |
| VAL-005 | Integração   | ExternalJobReference e callbacks internos        | integration            | passed   | Fase integração concluída   | Base para serviços externos.                         |
| VAL-006 | Renderer MVP | `GET /health`                                    | integration            | passed   | Testes renderer             | Healthcheck funcional.                               |
| VAL-007 | Renderer MVP | `POST /jobs`                                     | integration            | passed   | Testes renderer             | Recepção de jobs validada.                           |
| VAL-008 | Renderer MVP | Autenticação interna `X-Internal-Token`          | security               | passed   | Testes renderer             | Token não exposto nos logs.                          |
| VAL-009 | Renderer MVP | Validação de headers e envelope                  | contract               | passed   | Testes renderer             | Zod + consistência headers/body.                     |
| VAL-010 | Renderer MVP | Storage local                                    | integration            | passed   | Testes renderer             | Storage local funcional.                             |
| VAL-011 | Renderer MVP | Endpoint `/files` em development                 | integration            | passed   | Testes renderer             | Path traversal bloqueado.                            |
| VAL-012 | Renderer MVP | Callback client                                  | integration            | passed   | Testes renderer             | Callback completed/failed implementado.              |
| VAL-013 | Renderer MVP | Template engine                                  | unit                   | passed   | Testes renderer             | Templates e fallback validados.                      |
| VAL-014 | Renderer MVP | SVG → PNG com Sharp                              | integration            | passed   | Testes renderer             | PNG real gerado.                                     |
| VAL-015 | Renderer MVP | `content_generation` completed                   | e2e                    | passed   | E2E PostgreSQL              | ContentOutput e Asset criados.                       |
| VAL-016 | Renderer MVP | `report_generation` completed                    | e2e                    | passed   | E2E PostgreSQL              | Report completed + Asset ligado.                     |
| VAL-017 | Renderer MVP | `report_generation` failed                       | e2e                    | passed   | E2E PostgreSQL              | Falha controlada reflectida no Django.               |
| VAL-018 | Renderer MVP | `media_kit_generation` completed                 | e2e                    | passed   | E2E PostgreSQL              | MediaKit generated + Asset ligado.                   |
| VAL-019 | Renderer MVP | `media_kit_generation` failed                    | e2e                    | passed   | E2E PostgreSQL              | Falha controlada reflectida no Django.               |
| VAL-020 | Renderer MVP | Erros normalizados                               | unit/integration       | passed   | Testes renderer             | Códigos e payloads normalizados.                     |
| VAL-021 | Renderer MVP | Timeouts                                         | unit/integration       | passed   | Testes renderer             | Render/callback timeouts cobertos.                   |
| VAL-022 | Renderer MVP | Logs sem token                                   | security               | passed   | Testes renderer             | Tokens não aparecem nos logs.                        |
| VAL-023 | Hardening    | Callback em background leve                      | integration            | passed   | Testes renderer             | `POST /jobs` responde 202 antes do callback.         |
| VAL-024 | Hardening    | Retry de callback com backoff                    | integration            | passed   | Testes renderer             | Retry em timeout/5xx; sem retry em 4xx.              |
| VAL-025 | Hardening    | Echo `template_key`/`template_id`                | contract               | passed   | Testes renderer             | Campos ecoados quando aplicável.                     |
| VAL-026 | Hardening    | `StorageProvider` abstraction                    | unit/integration       | passed   | Testes renderer             | Renderers dependem de interface.                     |
| VAL-027 | Hardening    | Harness E2E PostgreSQL                           | operational            | passed   | Relatório E2E               | PostgreSQL usado para E2E multi-processo.            |
| VAL-028 | Hardening    | Loop real Django ↔ Renderer ↔ Django             | e2e                    | passed   | E2E PostgreSQL              | Assets criados por callback nos cenários principais. |
| VAL-029 | Hardening    | Idempotência de callback                         | e2e                    | passed   | E2E PostgreSQL              | Reentrega não duplica outputs/assets indevidamente.  |
| VAL-030 | Hardening    | Coverage Vitest                                  | coverage               | passed   | `npm run test:coverage`     | Thresholds cumpridos.                                |
| VAL-031 | Hardening    | Documentação final pós-hardening                 | documentation          | passed   | README + estado + guia E2E  | Documentação actualizada.                            |
| VAL-032 | Hardening    | Ausência de secrets em documentação              | security/documentation | passed   | Verificação documental      | Sem secrets reais detectados.                        |
| VAL-033 | Content      | `content_generation partially_completed`         | unit/integration       | indirect | Testes Django + Vitest      | Não validado por E2E HTTP real.                      |
| VAL-034 | Content      | `content_generation failed`                      | unit/integration       | indirect | Testes Django + Vitest      | Não validado por E2E HTTP real.                      |
| VAL-035 | Produção     | Storage S3/R2 real                               | operational            | pending  | Não implementado            | Bloqueador de produção.                              |
| VAL-036 | Produção     | Observabilidade, métricas e política operacional | operational            | pending  | Não implementado            | Bloqueador de produção.                              |
| VAL-037 | Intelligence Engine | Fundação FastAPI (`create_app`, `GET /health`) | integration | passed | `pytest` 5 passed | Health público funcional. |
| VAL-038 | Intelligence Engine | Config, `X-Internal-Token`, erros normalizados, logs sem secrets | security/integration | passed | `pytest` 26 passed (após hardening 02b) | Bloqueio de arranque em produção sem token validado. |
| VAL-039 | Intelligence Engine | Schemas/contratos Pydantic comuns | contract | passed | `pytest` 61 passed | Envelope estrito + data bundle permissivo. |
| VAL-040 | Intelligence Engine | `POST /analysis/campaign` | unit/integration | passed | `pytest` 91 passed | Regras R0–R7/C1–C3, determinismo. |
| VAL-041 | Intelligence Engine | `POST /scoring/campaign` | unit/integration | passed | `pytest` 124 passed | 5 scores + grade, dados insuficientes tratados. |
| VAL-042 | Intelligence Engine | `POST /recommendations/campaign` | unit/integration | passed | `pytest` 152 passed | Acções restritas ao catálogo real do produto. |
| VAL-043 | Intelligence Engine | `POST /moments/detect` | unit/integration | passed | `pytest` 182 passed | 8 tipos de momento, recommended_action compatível. |
| VAL-044 | Intelligence Engine | `POST /intelligence/campaign` (composto) | unit/integration | passed | `pytest` 197 passed | Resiliência por etapa (sem 500 indevido); determinístico. |
| VAL-045 | Intelligence Engine | Contrato de integração Backend Core ↔ Intelligence Engine | documentation | passed | `contrato_backend_core_intelligence_engine.md` | Recomendação sync-first; sem secrets reais. |
| VAL-046 | Intelligence Engine | Ausência de IA generativa, scraping, persistência e chamada directa ao renderer | static_analysis | passed | grep dirigido em `app/` + `requirements.txt` | Nenhuma ocorrência encontrada. |
| VAL-047 | Intelligence Engine | Coverage formal e type-checking estático (mypy/pyright) | coverage/static_analysis | pending | Não instalado/configurado | Não bloqueia integração/piloto; avaliar no futuro. |
| VAL-048 | Wiring BC↔IE | Settings `INTELLIGENCE_ENGINE_*` + guarda de produção (BC-IE-002) | security/integration | passed | `pytest` 31 passed (settings/client registry); suite completa 377 passed | `ImproperlyConfigured` se token vazio em produção. |
| VAL-049 | Wiring BC↔IE | Client síncrono `IntelligenceEngineClient` (BC-IE-003) | unit/integration | passed | `pytest apps/integrations_bridge/tests/test_intelligence_sync.py` 20 passed; `apps/integrations_bridge/` 118 passed | Token nunca logado; erros normalizados em tipos próprios. |
| VAL-050 | Wiring BC↔IE | Builder do data bundle de campanha (BC-IE-004) | unit/integration | passed | `pytest apps/campaigns/tests/test_intelligence_payload.py` 13 passed; `apps/campaigns/` 25 passed | JSON-safe; sem N+1; `WorkspaceMismatchError` validado. |
| VAL-051 | Wiring BC↔IE | Serviço de domínio `CampaignIntelligenceService` (BC-IE-005) | unit/integration | passed | `pytest apps/campaigns/tests/test_intelligence_service.py` 18 passed; `apps/campaigns/ apps/integrations_bridge/` 161 passed | `ENABLED`/`DRY_RUN`, mapeamento de erros, stamping `generated_at`. |
| VAL-052 | Wiring BC↔IE | Endpoint `POST /api/v1/campaigns/{id}/intelligence/` (BC-IE-006) | integration/contract | passed | `pytest apps/campaigns/tests/test_intelligence_api.py` 11 passed; suite completa 439 passed; `manage.py spectacular` sem warnings | RBAC `campaigns:view`; 404/502/503 mapeados. |
| VAL-053 | Wiring BC↔IE | Timeout, retry e fallback (BC-IE-007) | integration | passed | Suites-alvo 87 passed; suite completa 446 passed | Retry só em timeout/unavailable/5xx; nunca em 4xx. |
| VAL-054 | Wiring BC↔IE | Validação E2E com mocks HTTP, 13 cenários (BC-IE-008) | integration/e2e | passed | `pytest apps/campaigns/tests/test_intelligence_integration.py` 13 passed; suite completa 459 passed | Inclui RBAC/workspace e token-não-logado. |
| VAL-055 | Wiring BC↔IE | Loop real Backend Core → Intelligence Engine, sem mocks (BC-IE-009) | e2e | passed | 3 testes opt-in (`RUN_REAL_IE=1`) passed com os dois serviços a correr | Bug de granularidade `date`/`datetime` encontrado e corrigido nesta validação. |
| VAL-056 | Wiring BC↔IE | Correcção do bug `date_from_datetime_inexact` sem regressão | unit/integration | passed | `pytest` (payload/integração, pós-fix) 26 passed | Único fix de runtime desta fase (`_date_only()` em `intelligence_payload.py`). |
| VAL-057 | Wiring BC↔IE | Suite completa do Backend Core pós-wiring (BC-IE-010) | integration | passed | `pytest -q`: 459 passed, 3 skipped, 245 warnings, 296.90s | Skips são o loop real opt-in (esperado sem `RUN_REAL_IE`). |
| VAL-058 | Wiring BC↔IE | Ausência de secrets reais em `.env.example`/docs/relatórios/testes (BC-IE-010) | security/documentation | passed | Grep dirigido nos relatórios e testes da integração | Apenas tokens de teste claramente locais (`real-loop-token-123`). |
| VAL-059 | Wiring BC↔IE | Coverage formal e type-checking estático (mypy/pyright) no Backend Core | coverage/static_analysis | pending | Não instalado/configurado (`pyproject.toml` só define `[tool.ruff]`) | Não bloqueia piloto técnico; limitação pré-existente do repositório. |

---

# 7. Validações por fase

## 7.1 Backend Core Django

```text
Estado: passed
```

### Validações

|ID|Validação|Estado|
|---|---|---|
|VAL-001|Autenticação, users, workspaces e RBAC|passed|
|VAL-002|Catálogo musical, campanhas e content core|passed|
|VAL-003|Smart links, tracking, billing e créditos|passed|
|VAL-004|Reports, media kits, notifications e audit|passed|

### Observação

Backend Core foi validado em fase anterior e serve como núcleo de produto.

---

## 7.2 Integração Backend Core ↔ serviços externos

```text
Estado: passed
```

### Validações

|ID|Validação|Estado|
|---|---|---|
|VAL-005|ExternalJobReference e callbacks internos|passed|

### Observação

A integração com serviços externos permitiu a implementação e validação do renderer.

---

## 7.3 Content/Report Renderer — MVP

```text
Estado: passed
```

### Validações

|ID|Validação|Estado|
|---|---|---|
|VAL-006|GET /health|passed|
|VAL-007|POST /jobs|passed|
|VAL-008|X-Internal-Token|passed|
|VAL-009|Validação de headers/envelope|passed|
|VAL-010|Storage local|passed|
|VAL-011|/files em development|passed|
|VAL-012|Callback client|passed|
|VAL-013|Template engine|passed|
|VAL-014|SVG → PNG|passed|
|VAL-015|content_generation completed|passed|
|VAL-016|report_generation completed|passed|
|VAL-017|report_generation failed|passed|
|VAL-018|media_kit_generation completed|passed|
|VAL-019|media_kit_generation failed|passed|
|VAL-020|Erros normalizados|passed|
|VAL-021|Timeouts|passed|
|VAL-022|Logs sem token|passed|

---

## 7.4 Content/Report Renderer — hardening pós-MVP

```text
Estado: passed
```

### Validações

|ID|Validação|Estado|
|---|---|---|
|VAL-023|Callback em background leve|passed|
|VAL-024|Retry de callback com backoff|passed|
|VAL-025|Echo template_key/template_id|passed|
|VAL-026|StorageProvider abstraction|passed|
|VAL-027|Harness E2E PostgreSQL|passed|
|VAL-028|Loop real Django ↔ Renderer ↔ Django|passed|
|VAL-029|Idempotência de callback|passed|
|VAL-030|Coverage Vitest|passed|
|VAL-031|Documentação final pós-hardening|passed|
|VAL-032|Ausência de secrets em documentação|passed|

---

## 7.5 FastAPI Intelligence Engine — MVP completo (IE-001 a IE-010)

```text
Estado: passed (com pendências de coverage/type-checking registadas)
```

### Validações

|ID|Validação|Estado|
|---|---|---|
|VAL-037|Fundação FastAPI + GET /health|passed|
|VAL-038|Config/segurança/erros|passed|
|VAL-039|Schemas/contratos|passed|
|VAL-040|POST /analysis/campaign|passed|
|VAL-041|POST /scoring/campaign|passed|
|VAL-042|POST /recommendations/campaign|passed|
|VAL-043|POST /moments/detect|passed|
|VAL-044|POST /intelligence/campaign (composto)|passed|
|VAL-045|Contrato Backend Core ↔ Intelligence Engine|passed|
|VAL-046|Ausência de IA generativa/scraping/persistência/chamada renderer|passed|
|VAL-047|Coverage/type-checking estático|pending|

### Observação

O Intelligence Engine foi validado de fundação a fecho de fase nesta sessão (197 testes, ruff limpo). A única pendência de validação é a ausência de ferramentas de coverage e type-checking estático, que não bloqueiam integração/piloto técnico.

---

## 7.6 Backend Core ↔ Intelligence Engine — wiring síncrono (BC-IE-001 a BC-IE-010)

```text
Estado: passed (com pendências de observabilidade/staging/calibração registadas)
```

### Validações

|ID|Validação|Estado|
|---|---|---|
|VAL-048|Settings `INTELLIGENCE_ENGINE_*` + guarda de produção|passed|
|VAL-049|Client síncrono `IntelligenceEngineClient`|passed|
|VAL-050|Builder do data bundle de campanha|passed|
|VAL-051|Serviço de domínio `CampaignIntelligenceService`|passed|
|VAL-052|Endpoint `POST /api/v1/campaigns/{id}/intelligence/`|passed|
|VAL-053|Timeout, retry e fallback|passed|
|VAL-054|Validação E2E com mocks HTTP (13 cenários)|passed|
|VAL-055|Loop real Backend Core → Intelligence Engine|passed|
|VAL-056|Correcção do bug `date_from_datetime_inexact`|passed|
|VAL-057|Suite completa do Backend Core pós-wiring|passed|
|VAL-058|Ausência de secrets reais|passed|
|VAL-059|Coverage/type-checking estático no Backend Core|pending|

### Observação

Esta foi a primeira validação que exercitou a chamada real Django → Intelligence Engine ponta-a-ponta, com os dois serviços a correr simultaneamente (não apenas mocks). Um bug real de contrato (granularidade `date`/`datetime`) foi encontrado e corrigido durante esta validação — ver VAL-055/VAL-056 e [[riscos_bloqueios#RSK-014]]. Documento de estado consolidado: `backend_core/docs/backend_core/fundamentos/integracao_intelligence_engine/estado_integracao_intelligence_engine.md`.

---

# 8. Validações indirectas

## VAL-033 — `content_generation partially_completed`

```text
Estado: indirect
Tipo: unit/integration
Área: content_generation
```

### Resultado

O cenário `content_generation partially_completed` está coberto por testes do Backend Core e por testes Vitest do renderer, mas não foi reproduzido por chamada HTTP real ponta-a-ponta.

### Justificação

O renderer é resiliente e tende a usar fallback `completed` quando recebe template/formato desconhecido, dificultando a reprodução natural de partial success via E2E HTTP real.

### Evidência

```text
Testes Django: cobrem callback partially_completed.
Testes Vitest: cobrem emissão/handling de partially_completed.
E2E HTTP real: não reproduzido.
```

### Estado executivo

```text
Aceite para MVP e piloto técnico.
Reavaliar antes de produção ou se houver mecanismo controlado de falha.
```

---

## VAL-034 — `content_generation failed`

```text
Estado: indirect
Tipo: unit/integration
Área: content_generation
```

### Resultado

O cenário `content_generation failed` está coberto por testes do Backend Core e por testes Vitest do renderer, mas não foi reproduzido por chamada HTTP real ponta-a-ponta.

### Justificação

O renderer foi desenhado com fallbacks para evitar falhas por template/formato inválido. Para reproduzir `failed` via E2E real seria necessário injectar falha controlada de storage/render, o que não faz parte do fluxo normal.

### Evidência

```text
Testes Django: cobrem callback failed.
Testes Vitest: cobrem falha de render/storage/callback.
E2E HTTP real: não reproduzido.
```

### Estado executivo

```text
Aceite para MVP e piloto técnico.
Reavaliar antes de produção ou em fase de testes destrutivos/controlados.
```

---

# 9. Validações pendentes

## VAL-035 — Storage S3/R2 real

```text
Estado: pending
Tipo: operational
Prioridade: alta antes de produção
```

### Objectivo

Validar provider real de object storage para produção.

### Critérios de aceitação futuros

```text
Provider S3/R2 implementado.
Credenciais via ambiente/secret manager.
Upload de assets validado.
Metadata de Asset compatível.
URLs públicas/assinadas definidas.
Testes de integração criados.
Falhas de upload tratadas.
```

### Bloqueia

```text
Produção.
```

---

## VAL-036 — Observabilidade, métricas e política operacional

```text
Estado: pending
Tipo: operational
Prioridade: alta antes de produção
```

### Objectivo

Validar capacidade operacional mínima para produção.

### Critérios de aceitação futuros

```text
Métricas de jobs.
Métricas de callbacks.
Métricas de render duration.
Métricas de storage writes.
Taxa de erro por job_type.
Dashboards.
Alertas.
Política para background jobs.
Política para retry/reconciliação.
Runbook operacional.
```

### Bloqueia

```text
Produção.
```

---

## VAL-047 — Coverage formal e type-checking estático do Intelligence Engine

```text
Estado: pending
Tipo: coverage/static_analysis
Prioridade: baixa — não bloqueia integração/piloto
```

### Objectivo

Avaliar se vale a pena introduzir `pytest-cov` e `mypy`/`pyright` no Intelligence Engine.

### Situação actual

```text
Não instalado nem configurado.
Confiança actual vem de 197 testes deterministas organizados por regra/serviço, não de métrica de coverage.
```

### Bloqueia

```text
Não bloqueia integração nem piloto técnico.
Recomendado rever antes de uma fase de produção mais exigente.
```

---

## VAL-059 — Coverage formal e type-checking estático do Backend Core

```text
Estado: pending
Tipo: coverage/static_analysis
Prioridade: baixa — não bloqueia integração/piloto
```

### Objectivo

Avaliar se vale a pena introduzir `mypy`/`pyright` no Backend Core (não existe nenhum configurado).

### Situação actual

```text
pyproject.toml só define secções [tool.ruff]; não há mypy nem pyright configurados.
Confiança actual vem de 459 testes (pytest -q) e ruff limpo, não de typecheck estático.
Limitação pré-existente do repositório, não introduzida por esta integração.
```

### Bloqueia

```text
Não bloqueia integração nem piloto técnico.
```

---

# 10. Falhas abertas

```text
Nenhuma falha aberta conhecida.
```

|ID|Falha|Severidade|Estado|Acção|
|---|---|--:|---|---|
|—|Nenhuma|—|—|—|

---

# 11. Decisão de qualidade actual

```text
O projecto pode avançar para a próxima fase de produto.
O renderer está aprovado para integração e piloto técnico.
O renderer não está aprovado para produção.
```

## Justificação

```text
A suite técnica está verde.
O E2E PostgreSQL validou os cenários principais.
Coverage está acima dos thresholds.
Não há falhas abertas.
As pendências remanescentes são de produção/operabilidade, não de MVP/piloto.
```

---

# 12. Critérios para avançar para próxima implementação

Antes da próxima implementação, confirmar que:

```text
status_report.md foi actualizado.
plano_execucao.md foi actualizado.
log_decisoes.md foi actualizado.
riscos_bloqueios.md foi actualizado.
matriz_validacao.md foi actualizado.
diario_execucao_ia.md foi actualizado.
```

Depois disso, avançar apenas se:

```text
a próxima fase estiver decidida;
o backlog da próxima fase estiver criado;
a pipeline da próxima fase estiver criada.
```

---

# 13. Produção — validações obrigatórias futuras

O projecto só deve ser considerado production-ready quando estas validações forem adicionadas e aprovadas:

|ID futuro|Validação|Estado actual|
|---|---|---|
|VAL-PROD-001|S3/R2 real|pending|
|VAL-PROD-002|Observabilidade|pending|
|VAL-PROD-003|Métricas operacionais|pending|
|VAL-PROD-004|Política de background jobs/reconciliação|pending|
|VAL-PROD-005|Gestão de secrets por ambiente|pending|
|VAL-PROD-006|CI/CD com gates de qualidade|pending|
|VAL-PROD-007|Deploy em ambiente de integração|pending|
|VAL-PROD-008|Runbook operacional|pending|

---

# 14. Histórico de validação

## 2026-06-25 — Validação final do wiring síncrono Backend Core ↔ Intelligence Engine (BC-IE-001 a BC-IE-010)

```text
Estado: aprovado para piloto técnico
```

### Evidências

```text
pytest -q (suite completa Backend Core): 459 passed, 3 skipped, 245 warnings, 296.90s
ruff check apps/ config/: All checks passed!
manage.py check: 0 issues
schema.yml: sem diff após regeneração
13 cenários E2E com mocks HTTP (sucesso, warnings, timeout, 403, 422, 5xx, JSON inválido, desligado, dry-run, RBAC/workspace, token não logado)
Loop real com os dois serviços a correr: 200/completed com analysis/scores/grade/moments/recommendations/summary; token ausente dos logs mesmo em falha (engine inacessível)
Bug real encontrado e corrigido durante a validação real: 422 date_from_datetime_inexact em content_outputs[].created_at
mypy/pyright: não configurados no Backend Core (limitação pré-existente, registada, não simulada)
Grep dirigido: sem secrets reais em .env.example/docs/relatórios/testes
```

### Resultado

```text
Wiring síncrono Backend Core ↔ Intelligence Engine aprovado para piloto técnico.
Produção permanece pendente de observabilidade, staging contínuo (validação real fora do modo local/opt-in) e calibração de negócio dos resultados do engine.
```

---

## 2026-06-25 — Validação final do FastAPI Intelligence Engine (IE-001 a IE-010)

```text
Estado: aprovado para integração e piloto técnico
```

### Evidências

```text
pytest -q: 197 passed, 1 warning (deprecação httpx/starlette.testclient, terceiros)
ruff check .: All checks passed!
ruff format --check .: conforme (após correcção de 3 ficheiros pré-existentes)
mypy/pyright/pytest-cov: não instalados nem configurados
Smoke test real (TestClient): GET /health público; 5 endpoints protegidos exigem X-Internal-Token; payload malformado → 422
Grep dirigido: sem IA generativa, scraping, persistência ou chamada directa ao renderer
Grep dirigido: sem secrets reais em README/.env.example/docs
```

### Resultado

```text
FastAPI Intelligence Engine aprovado para integração (lado Intelligence Engine) e piloto técnico.
Produção permanece pendente do wiring real do Backend Core, calibração de heurísticas e observabilidade.
```

---

## 2026-06-24 — Validação pós-hardening do renderer

```text
Estado: aprovado para integração e piloto técnico
```

### Evidências

```text
npm run build: aprovado
npm run lint: aprovado
npm test: 136 passed
npm run test:coverage: aprovado
Coverage statements: 91.9%
Coverage branches: 79.32%
Coverage functions: 95.89%
Coverage lines: 91.86%
E2E PostgreSQL: aprovado para cenários principais
Documentação final: concluída
```

### Resultado

```text
Content/Report Renderer aprovado para integração e piloto técnico.
Produção permanece pendente de validações operacionais.
```

---

## 2026-06-23 — Validação inicial do Content/Report Renderer

```text
Estado: MVP funcional aprovado
```

### Evidências

```text
GET /health validado.
POST /jobs validado.
content_generation validado.
report_generation validado.
media_kit_generation validado.
storage local validado.
callback client validado.
erros/timeouts/logs validados.
```

---

## 2026-06-23 — Validações de Backend Core e integração

```text
Estado: aprovado em fase anterior
```

### Evidências

```text
Backend Core implementado.
Integração com serviços externos implementada.
ExternalJobReference e callbacks internos validados.
```

---

# 15. Próxima revisão recomendada

Rever este documento quando:

```text
- diário de execução IA for actualizado;
- próxima fase for decidida;
- backlog do FastAPI Intelligence Engine for criado;
- pipeline do FastAPI Intelligence Engine for criada;
- S3/R2 for priorizado;
- ambiente de integração/piloto for definido;
- surgir nova falha de validação;
- houver alteração nos contratos Django ↔ serviços externos.
```

## Recomendação actual

```text
Após concluir a actualização dos documentos de acompanhamento, avançar para decisão formal da próxima fase.
O wiring Backend Core ↔ Intelligence Engine já foi executado e validado nesta sessão; sem recomendação técnica forte registada entre as alternativas remanescentes (S3/R2, frontend mínimo ou observabilidade) — ver decisão pendente PDEC-008 em [[log_decisoes]].
```