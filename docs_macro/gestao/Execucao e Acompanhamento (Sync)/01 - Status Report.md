---
doc_id: exec-status-report
title: Status Report
project: ChartRex / MomentFlow
area: gestao_execucao
doc_type: status_report
status: active
owner: Aldino Ramos
created_at: 2026-06-23
updated_at: 2026-06-23
last_reviewed_at:
review_frequency: weekly
update_frequency: weekly
version: "1.0"
confidentiality: internal
source_of_truth: true
report_model: living_status_with_snapshots
report_period: weekly
current_status_date: 2026-06-23
current_phase: Content/Report Renderer
overall_status: green
health: controlled
progress_percent:
progress_confidence: qualitative
last_completed_milestone: Backend Core e integração Backend Core ↔ FastAPI/Renderer concluídos
next_milestone: Executar pipeline do Content/Report Renderer
last_snapshot_date: 2026-06-23
snapshot_count: 1
history_mode: append_only
---
---

doc_id: "exec-status-report"  
title: "Status Report"  
project: "ChartRex / MomentFlow"  
area: "gestao_execucao"  
doc_type: "status_report"  
status: "active"  
owner: "Aldino Ramos"  
created_at: "2026-06-23"  
updated_at: "2026-06-25"  
last_reviewed_at: "2026-06-25"  
review_frequency: "weekly"  
update_frequency: "weekly"  
version: "1.3"  
confidentiality: "internal"  
source_of_truth: true

report_model: "living_status_with_snapshots"  
report_period: "weekly"  
current_status_date: "2026-06-25"  
current_phase: "Transição pós-wiring-Intelligence-Engine para próxima fase"  
overall_status: "green"  
health: "controlled"  
progress_percent: null  
progress_confidence: "qualitative"  
last_completed_milestone: "Wiring síncrono Backend Core ↔ Intelligence Engine completo e validado (BC-IE-001 a BC-IE-010), incluindo loop real com os dois serviços a correr"  
next_milestone: "Decidir a próxima fase: S3/R2, frontend mínimo, observabilidade ou ambiente de staging contínuo"  
last_snapshot_date: "2026-06-25"  
snapshot_count: 4  
history_mode: "append_only"

ready_for_integration_environment: true  
ready_for_technical_pilot: true  
ready_for_production: false  
production_blockers:

- "Storage S3/R2 real"
    
- "Observabilidade e métricas operacionais (incluindo para a chamada síncrona ao Intelligence Engine)"
    
- "Política operacional para background jobs/fila persistente, se necessário"
    
- "Ambiente de staging com os dois serviços (Backend Core + Intelligence Engine) persistentemente disponíveis, para validação real contínua"
    
- "Calibração das heurísticas do Intelligence Engine e dos resultados devolvidos via o endpoint real com dados reais"
    

related_docs:

- "[[plano_execucao]]"
    
- "[[log_decisoes]]"
    
- "[[riscos_bloqueios]]"
    
- "[[matriz_validacao]]"
    
- "[[diario_execucao_ia]]"
    

tags:

- "project/momentflow"
    
- "gestao/status"
    
- "execucao"
    
- "obsidian"
    

## ai_update_mode: "controlled"  
ai_update_scope: "actualizar o status actual, resumo executivo, progresso por frente, riscos principais, bloqueios, decisões pendentes, próximos passos e histórico de snapshots com base nos documentos de execução."  
ai_may_create_sections: false  
ai_may_delete_content: false  
ai_should_preserve_history: true

# Status Report — ChartRex / MomentFlow

## 1. Instruções para IA actualizar este documento

Este documento é a **fonte de verdade executiva** sobre o estado actual do projecto.

Ao actualizar este ficheiro, a IA deve:

```text
1. Ler primeiro o README.md desta pasta.
2. Ler os metadados YAML deste documento.
3. Respeitar ai_update_mode e ai_update_scope.
4. Actualizar o campo updated_at no YAML.
5. Actualizar current_status_date.
6. Actualizar overall_status apenas com base em evidência.
7. Actualizar resumo executivo, progresso, riscos, bloqueios e próximos passos.
8. Adicionar um novo snapshot em "Histórico de status".
9. Não apagar snapshots antigos.
10. Não inventar percentagens, testes, comandos ou resultados.
11. Não transformar este documento num diário técnico detalhado.
12. Usar os outros documentos como fonte:
    - [[plano_execucao]]
    - [[diario_execucao_ia]]
    - [[matriz_validacao]]
    - [[riscos_bloqueios]]
    - [[log_decisoes]]
```

Regras de actualização:

```text
status_report.md = fotografia executiva actual + histórico resumido.
diario_execucao_ia.md = detalhe das execuções por IA.
matriz_validacao.md = evidência de testes e validações.
riscos_bloqueios.md = detalhe dos riscos e bloqueios.
plano_execucao.md = plano, fases e ordem de execução.
log_decisoes.md = decisões estruturais e racional.
```

A IA não deve:

```text
- apagar histórico;
- remover decisões;
- fechar riscos sem justificação;
- marcar validações como concluídas sem evidência;
- inventar progresso percentual;
- inventar comandos executados;
- inventar resultados de testes;
- expor tokens, passwords ou segredos.
```

Quando não houver evidência suficiente, usar:

```text
Estado: por confirmar
Evidência: não disponível
Acção necessária: validar manualmente
```

---

# 2. Status actual

## Estado geral

```text
Estado geral: GREEN
Saúde do projecto: Controlado
Data do status: 2026-06-25
Fase concluída: Wiring síncrono Backend Core ↔ Intelligence Engine (BC-IE-001 a BC-IE-010)
Fase actual: Transição pós-wiring-Intelligence-Engine para próxima fase
Pronto para integração: sim (chamada real Django → Intelligence Engine implementada e validada)
Pronto para piloto técnico: sim
Pronto para produção: não
Próximo marco: decidir explicitamente a próxima fase (ver secção 6 e PDEC-008 em log_decisoes)
```

## Resumo executivo

O projecto encontra-se em estado **controlado**.

A fundação do **Backend Core Django/DRF** foi concluída, incluindo autenticação, workspaces, RBAC, catálogo musical, campanhas, content core, smart links, billing, reports, media kits, notifications, audit, OpenAPI, Admin, testes e hardening.

A fase de **integração Backend Core ↔ serviços externos** também foi concluída, com suporte a `ExternalJobReference`, submissão de jobs externos, callbacks internos autenticados, idempotência, dry-run, logs, retries, segurança, testes end-to-end e documentação de estado.

A fase de **Content/Report Renderer** foi concluída em duas etapas (MVP funcional + hardening pós-MVP). O `content_renderer` está funcional e estabilizado para integração controlada, com callback em background, retry com backoff, `StorageProvider`, E2E com PostgreSQL, coverage Vitest e documentação final.

A fase de **FastAPI Intelligence Engine** foi concluída de fundação a fecho de fase (IE-001 a IE-010):

```text
- serviço FastAPI separado (intelligence_engine), determinístico e explicável;
- POST /analysis/campaign — análise heurística de campanha;
- POST /scoring/campaign — 5 scores 0-100 + grade A-D/unknown;
- POST /recommendations/campaign — recomendações de acção com prioridade/confiança, restritas ao catálogo real do produto;
- POST /moments/detect — detecção de 8 tipos de momento;
- POST /intelligence/campaign — endpoint composto que agrega os 4 anteriores, com resiliência por etapa (sem 500 indevido);
- autenticação interna X-Internal-Token, erros normalizados, logs sem secrets;
- sem IA generativa, sem scraping, sem persistência, sem chamada directa ao renderer;
- 197 testes aprovados, ruff limpo;
- contrato de integração Backend Core ↔ Intelligence Engine documentado, com recomendação de chamada síncrona ("sync-first");
- documento de estado final criado.
```

A fase de **wiring síncrono Backend Core ↔ Intelligence Engine** foi agora concluída (BC-IE-001 a BC-IE-010), executando o lado Django do contrato documentado em IE-009:

```text
- settings dedicados INTELLIGENCE_ENGINE_* com guarda de produção (recusa arrancar sem token, se DEBUG=False);
- client síncrono IntelligenceEngineClient (apps/integrations_bridge/intelligence_sync.py), reaproveitando InternalServiceClient;
- builder do data bundle de campanha CampaignIntelligencePayloadBuilder (apps/campaigns/intelligence_payload.py), JSON-safe e sem N+1;
- serviço de domínio CampaignIntelligenceService (apps/campaigns/intelligence_service.py), com switches ENABLED/DRY_RUN e mapeamento de erros;
- endpoint POST /api/v1/campaigns/{id}/intelligence/, com auth, RBAC (campaigns:view) e workspace scoping;
- política de timeout/retry/fallback: retry só em falhas transitórias (timeout/unavailable/5xx), nunca em 4xx;
- 13 cenários E2E com mocks HTTP (sucesso, falhas, RBAC, dry-run, token não logado);
- validação real com os dois serviços a correr de facto: um bug real de contrato foi encontrado (granularidade date/datetime em content_outputs[].created_at) e corrigido, e a chamada real devolveu 200/completed com todas as chaves esperadas, sem o token aparecer em nenhum log;
- 459 testes aprovados na suite completa do Backend Core, ruff limpo, manage.py check limpo, schema.yml sem diff;
- documento de estado final consolidado criado.
```

A chamada Django → Intelligence Engine **foi agora exercitada de facto**, não apenas documentada por contrato — incluindo o caso de falha (engine inacessível, tratado de forma segura e sem expor o token). A integração está **pronta para piloto técnico**, mas **não deve ainda ser declarada production-ready**: falta observabilidade dedicada para a chamada síncrona, a validação real é local/opt-in (não corre em staging contínuo) e os resultados do engine ainda não foram calibrados por um humano de negócio.

O `content_renderer` mantém-se igualmente **pronto para ambiente de integração e piloto técnico**, não production-ready, pelas mesmas razões já registadas (storage S3/R2, observabilidade, política operacional).

A próxima decisão de produto deve escolher entre:

```text
1. implementar storage S3/R2 real;
2. avançar para frontend mínimo de Campaign War Room;
3. preparar observabilidade e métricas operacionais (incluindo para a chamada síncrona ao Intelligence Engine);
4. criar um ambiente de staging com os dois serviços persistentemente disponíveis, para validação real contínua;
5. melhorar a qualidade visual dos templates.
```

Recomendação actual: **nenhuma recomendação técnica forte foi fixada nesta actualização documental** — esta sessão teve como âmbito consolidar o fecho do wiring síncrono, não decidir a fase seguinte (ver PDEC-008 em [[log_decisoes]]).

---

# 3. Progresso por frente

|Frente|Estado|Resumo|Próximo passo|
|---|--:|---|---|
|Visão de produto|Concluído para MVP|Produto definido como Music Campaign OS, com foco B2B/campaign-first.|Rever apenas se houver alteração estratégica.|
|Backend Core Django|Concluído|Fundação SaaS e produto implementada.|Manter apenas correcções/hardening.|
|Integração Backend Core ↔ serviços externos|Concluído|Jobs externos, callbacks, idempotência, billing/credits, notifications e audit integrados.|Usar contratos para serviços técnicos reais.|
|Content/Report Renderer — MVP|Concluído|Renderer gera PNG/PDF/HTML e envia callbacks no contrato do Django.|Manter evolução controlada.|
|Content/Report Renderer — hardening pós-MVP|Concluído|Callback background, retry, StorageProvider, E2E PostgreSQL, coverage e documentação final concluídos.|Encerrar fase e actualizar documentos de acompanhamento.|
|FastAPI Intelligence Engine|Concluído (MVP, IE-001 a IE-010)|5 endpoints funcionais, deterministas, explicáveis, contrato com Backend Core documentado.|Manter; calibrar heurísticas quando houver dados reais.|
|Wiring Backend Core ↔ Intelligence Engine|Concluído (BC-IE-001 a BC-IE-010)|Chamada síncrona real implementada e validada (mocks + loop real); bug de contrato encontrado e corrigido.|Observabilidade dedicada e staging contínuo antes de produção.|
|Frontend|Planeado|Ainda não é foco principal.|Avançar quando decidido (PDEC-008).|
|Storage produção|Pendente|Storage local funciona; interface StorageProvider preparada.|Implementar S3/R2 antes de produção.|
|Observabilidade|Pendente|Logs estruturados existem; métricas/tracing/dashboards ainda não.|Definir fase de produção/operabilidade.|
|Vídeo/Reels|Fora do escopo actual|Não implementar nesta fase.|Reavaliar após renderer estático e intelligence engine.|

---

# 4. Marcos concluídos

## Marcos técnicos

- Backend Core Django inicial implementado.
    
- Autenticação, JWT e Custom User implementados.
    
- Workspaces e multi-tenancy implementados.
    
- RBAC implementado.
    
- Catálogo musical implementado.
    
- Campanhas e objectivos implementados.
    
- Content core, templates, packs e outputs implementados.
    
- Smart links e tracking implementados.
    
- Billing, usage e créditos implementados.
    
- Reports, media kits e notifications implementados.
    
- Audit e integrations bridge implementados.
    
- OpenAPI/Admin/testes/hardening concluídos.
    
- Integração Backend Core ↔ serviços externos concluída.
    
- Contratos para Content Renderer, Report Renderer e Intelligence Engine preparados.
    
- Backlog do Content/Report Renderer criado.
    
- Pipeline de prompts do Content/Report Renderer criada.
    
- Content/Report Renderer MVP implementado.
    
- `GET /health` implementado.
    
- `POST /jobs` implementado.
    
- Autenticação interna com `X-Internal-Token` implementada.
    
- Validação de headers e envelope implementada.
    
- Storage local implementado.
    
- Endpoint `/files` em development implementado.
    
- Callback client implementado.
    
- Template engine implementado.
    
- SVG → PNG com Sharp implementado.
    
- `content_generation` real implementado.
    
- `report_generation` real com PDF/HTML implementado.
    
- `media_kit_generation` real com PDF/HTML implementado.
    
- Erros normalizados implementados.
    
- Partial success implementado.
    
- Timeouts implementados.
    
- Logs sem token implementados.
    
- Callback em background leve implementado.
    
- Retry de callback com backoff implementado.
    
- Echo de `template_key`/`template_id` no `content_generation` implementado.
    
- `StorageProvider` abstraction implementado.
    
- Harness E2E com PostgreSQL criado.
    
- Loop real Django ↔ Renderer ↔ Django validado com PostgreSQL.
    
- Coverage Vitest configurado.
    
- Documentação final pós-hardening concluída.
    
- FastAPI Intelligence Engine — fundação FastAPI (`create_app`, `GET /health`) implementada.
    
- Settings validadas no arranque, autenticação interna `X-Internal-Token`, logging estruturado e erros normalizados implementados.
    
- Schemas/contratos Pydantic comuns implementados.
    
- `POST /analysis/campaign` implementado.
    
- `POST /scoring/campaign` implementado.
    
- `POST /recommendations/campaign` implementado.
    
- `POST /moments/detect` implementado.
    
- `POST /intelligence/campaign` (endpoint composto) implementado.
    
- Contrato de integração Backend Core ↔ Intelligence Engine documentado.
    
- Validação final e documento de estado do Intelligence Engine concluídos.
    
- Settings `INTELLIGENCE_ENGINE_*` no Backend Core, com guarda de produção, implementados.
    
- Client síncrono `IntelligenceEngineClient` implementado.
    
- Builder do data bundle de campanha `CampaignIntelligencePayloadBuilder` implementado.
    
- Serviço de domínio `CampaignIntelligenceService` implementado.
    
- Endpoint `POST /api/v1/campaigns/{id}/intelligence/` implementado.
    
- Política de timeout/retry/fallback do wiring síncrono implementada.
    
- Validação E2E com mocks HTTP (13 cenários) do wiring síncrono concluída.
    
- Validação real do loop Backend Core → Intelligence Engine, com os dois serviços a correr, concluída (bug de granularidade date/datetime corrigido).
    
- Documento de estado final do wiring síncrono Backend Core ↔ Intelligence Engine criado.
    

---

# 5. Fase actual

## Nome da fase

```text
Transição pós-wiring-Intelligence-Engine para próxima fase
```

## Estado da fase anterior

```text
Wiring síncrono Backend Core ↔ Intelligence Engine — concluído (BC-IE-001 a BC-IE-010).
```

## Resultado da fase anterior

O wiring passou de:

```text
Contrato documentado (IE-009), sem nenhuma chamada real do Django ao Intelligence Engine.
```

para:

```text
Chamada síncrona real e validada: ViewSet action → CampaignIntelligenceService →
CampaignIntelligencePayloadBuilder → IntelligenceEngineClient → FastAPI Intelligence Engine real,
com auth, RBAC, workspace scoping, timeout/retry/fallback seguros, e um loop real confirmado com os
dois serviços a correr de facto (incluindo a correcção de um bug real de contrato).
```

## Objectivo da fase actual

Escolher e preparar a próxima fase do projecto, preservando a coerência arquitectural:

```text
Django governa o produto.
Renderer gera activos.
FastAPI Intelligence calcula, recomenda e detecta oportunidades.
```

## Entregáveis esperados da próxima fase, conforme a opção escolhida em PDEC-008

```text
S3/R2:
  provider real de object storage, credenciais/bucket/política de lifecycle definidos.

Frontend mínimo:
  rotas/telas prioritárias para operar campanhas, ver activos, reports e media kits.

Observabilidade:
  métricas, dashboards e alertas — incluindo para a chamada síncrona ao Intelligence Engine.

Staging contínuo:
  ambiente com os dois serviços (Backend Core + Intelligence Engine) persistentemente
  disponíveis, para que o loop real deixe de ser apenas local/opt-in.
```

---

# 6. Próximos passos

## Próximas acções imediatas

|Prioridade|Acção|Documento relacionado|Estado|
|--:|---|---|---|
|1|Actualizar diário de execução IA com a pipeline Backend Core ↔ Intelligence Engine (BC-IE-001 a BC-IE-010)|[[diario_execucao_ia]]|Concluído|
|2|Actualizar matriz de validação com testes/lint/loop real do wiring síncrono|[[matriz_validacao]]|Concluído|
|3|Actualizar riscos/bloqueios (RSK-014 mitigado, RSK-017 novo)|[[riscos_bloqueios]]|Concluído|
|4|Registar decisões técnicas do fecho de fase no log de decisões (DEC-021)|[[log_decisoes]]|Concluído|
|5|Fechar no plano de execução a fase de wiring síncrono|[[plano_execucao]]|Concluído|
|6|Decidir próxima fase: S3/R2, frontend mínimo, observabilidade ou staging contínuo|[[plano_execucao]] / [[log_decisoes]]|Pendente|

## Próximo marco recomendado

```text
Decidir explicitamente a próxima fase (PDEC-008 em log_decisoes) antes de criar qualquer novo backlog/pipeline.
```

## Alternativas ao próximo marco

```text
1. Implementar storage S3/R2 real.
2. Preparar observabilidade e métricas operacionais (incluindo para a chamada síncrona ao Intelligence Engine).
3. Criar frontend mínimo de Campaign War Room.
4. Criar ambiente de staging com os dois serviços persistentemente disponíveis, para validação real contínua.
5. Melhorar templates visuais do renderer.
```

---

# 7. Riscos principais

|ID|Risco|Impacto|Estado|Mitigação|
|---|---|--:|---|---|
|RSK-001|Renderer ficar demasiado acoplado ao payload interno do Django.|Médio|Mitigado / Monitorização|Uso de payload_version, schemas, leitura defensiva, E2E com PostgreSQL e documentação de contrato.|
|RSK-002|Dependências de PDF dificultarem instalação local.|Médio|Mitigado|Uso de `pdf-lib` pure JS e fallback HTML; sem Playwright no MVP.|
|RSK-003|Callback gerar ficheiro mas falhar ao notificar Django.|Alto|Mitigado / Monitorização|Callback em background, retry com backoff, logs e idempotência validada no loop real.|
|RSK-004|Storage local não servir para produção.|Médio|Aberto|`StorageProvider` criado; implementar S3/R2 antes de produção.|
|RSK-005|IA local adicionar features fora do escopo, como vídeo/editor visual.|Médio|Mitigado|Backlogs e prompts reforçaram escopo; vídeo continua fora da fase actual.|
|RSK-006|Background in-process perder job se o processo reiniciar entre 202 e callback.|Alto|Aberto / Aceite para MVP|Para produção, avaliar fila persistente ou mecanismo de reconciliação.|
|RSK-007|Falta de observabilidade operacional.|Médio|Aberto|Criar fase futura de métricas, tracing, dashboards e alertas.|
|RSK-008|`content_generation` partial/failed não coberto por E2E HTTP real.|Baixo/Médio|Monitorização|Coberto por testes do Django e Vitest; registar como validação indirecta.|
|RSK-013|Heurísticas do Intelligence Engine não calibradas com dados reais.|Médio/Alto|Monitorização|Explicabilidade total; rever pesos/limiares quando houver dados reais.|
|RSK-014|Wiring real Backend Core ↔ Intelligence Engine (mitigado).|Alto (residual: Médio)|Mitigado|Implementado e validado (BC-IE-001 a BC-IE-010), incluindo loop real com os dois serviços a correr.|
|RSK-015|Sem coverage/type-checking estático no Intelligence Engine.|Baixo/Médio|Monitorização|Confiança actual via 197 testes deterministas; avaliar ferramenta no futuro.|
|RSK-016|Catálogo de content packs/templates espelhado, não importado do Django.|Médio|Monitorização|Testes de invariante dedicados; sincronizar manualmente se o catálogo mudar.|
|RSK-017|Validação real do wiring é local/pontual, não contínua.|Médio|Monitorização|Loop real validado e documentado; avaliar staging contínuo antes de produção.|

---

# 8. Bloqueios actuais

```text
Sem bloqueios activos conhecidos.
```

Observação:

```text
Não há bloqueios para avançar para a próxima fase de produto.
Existem pendências de produção que devem ser tratadas antes de declarar o serviço production-ready.
```

---

# 9. Decisões relevantes recentes

|ID|Decisão|Estado|
|---|---|---|
|DEC-001|Django governa produto; FastAPI calcula; Renderer gera activos.|Activa|
|DEC-002|Backend Core permanece responsável por users, workspaces, RBAC, billing, estado e audit.|Activa|
|DEC-003|Renderer será serviço separado do Django.|Activa|
|DEC-004|Renderer MVP usará storage local.|Activa / Evolução pendente para S3/R2|
|DEC-005|Vídeo, Remotion e FFmpeg ficam fora do escopo actual.|Activa|
|DEC-006|Status report será documento vivo único com snapshots históricos.|Activa|
|DEC-007|Callback passa a executar em background leve, sem fila persistente nesta fase.|Activa|
|DEC-008|Callback terá retry simples com backoff, sem dead-letter queue nesta fase.|Activa|
|DEC-009|Storage passa a usar abstracção `StorageProvider`; provider real S3/R2 fica para fase futura.|Activa|
|DEC-010|PostgreSQL é a base recomendada para E2E multi-processo.|Activa|
|DEC-011|Renderer fica pronto para integração/piloto técnico, mas não production-ready.|Activa|
|DEC-016|FastAPI Intelligence Engine é a próxima fase recomendada (decisão histórica, já executada).|Activa|
|DEC-017|Storage S3/R2, observabilidade e política operacional são bloqueadores de produção.|Activa|
|DEC-019|FastAPI Intelligence Engine MVP concluído; integração síncrona ("sync-first") recomendada.|Activa|
|DEC-020|Próxima fase do projecto ainda não decidida após o fecho do Intelligence Engine.|Activa|
|DEC-021|Wiring síncrono Backend Core ↔ Intelligence Engine implementado e validado (BC-IE-001 a BC-IE-010).|Activa|

Nota: decisões completas devem estar registadas em [[log_decisoes]].

---

# 10. Validações recentes

## Backend Core e integração

Validações reportadas como concluídas em fases anteriores:

```text
python manage.py check
python manage.py makemigrations --check
ruff check .
python manage.py spectacular
pytest
testes E2E de integração
```

Estado: aprovado nas fases anteriores.

## Content/Report Renderer — MVP + hardening

Validações finais reportadas:

```text
npm run build
npm run lint
npm test
npm run test:coverage
E2E real com PostgreSQL
```

Resultado:

```text
Build: aprovado
Lint: aprovado
Testes: 136 passed
Coverage statements: 91.9%
Coverage branches: 79.32%
Coverage functions: 95.89%
Coverage lines: 91.86%
E2E PostgreSQL: loop Django ↔ Renderer validado
```

## FastAPI Intelligence Engine — MVP completo

Validações finais reportadas:

```text
venv/Scripts/python.exe -m pytest -q
venv/Scripts/python.exe -m ruff check .
venv/Scripts/python.exe -m ruff format --check .
```

Resultado:

```text
Testes: 197 passed, 1 warning (deprecação httpx/starlette.testclient, terceiros)
Lint: All checks passed!
Formatação: conforme (após correcção de 3 ficheiros pré-existentes)
Coverage/type-checking estático: não configurado — registado como limitação, não simulado
```

Validado adicionalmente por smoke test real (`TestClient(create_app())`):

```text
GET /health: 200, público
5 endpoints protegidos: 403 sem token, 200 com token
Payload malformado: 422 (não 500)
```

Confirmado por grep dirigido em app/ e requirements.txt:

```text
Sem IA generativa, scraping, persistência ou chamada directa ao renderer.
Sem secrets reais em README/.env.example/docs.
```

## Backend Core ↔ Intelligence Engine — wiring síncrono (BC-IE-001 a BC-IE-010)

Validações finais reportadas:

```text
venv/Scripts/python.exe -m pytest -q
venv/Scripts/python.exe -m ruff check apps/ config/
venv/Scripts/python.exe manage.py check
venv/Scripts/python.exe manage.py spectacular --file <tmp>   # diff vs schema.yml
RUN_REAL_IE=1 venv/Scripts/python.exe -m pytest apps/campaigns/tests/test_intelligence_real_loop.py -q
```

Resultado:

```text
Suite completa: 459 passed, 3 skipped (loop real opt-in, RUN_REAL_IE não definido), 245 warnings, 296.90s
Lint: All checks passed!
Django system check: 0 issues
Schema OpenAPI: sem diff após regeneração
13 cenários E2E com mocks HTTP: passed
Loop real (3 testes, com os dois serviços a correr): passed — 200/completed com analysis/scores/grade/moments/recommendations/summary; token ausente dos logs mesmo em falha real (engine inacessível)
mypy/pyright: não configurados no Backend Core (limitação pré-existente, documentada, não simulada)
```

Bug real encontrado e corrigido durante a validação real:

```text
422 invalid_payload / date_from_datetime_inexact em content_outputs[].created_at
(DateTimeField Django vs schema Pydantic `date` do Intelligence Engine).
Corrigido com helper _date_only() em apps/campaigns/intelligence_payload.py.
```

Confirmado por grep dirigido em docs/.env.example/relatórios/testes:

```text
Sem secrets reais — apenas tokens de teste claramente locais (ex.: real-loop-token-123, atados a 127.0.0.1).
```

## Validações E2E

Validado com loop real PostgreSQL:

```text
content_generation completed;
report_generation completed;
report_generation failed;
media_kit_generation completed;
media_kit_generation failed;
idempotência de callback.
```

Validação indirecta:

```text
content_generation partially_completed;
content_generation failed.
```

Motivo:

```text
O renderer tende a cair em fallback completed em vez de falhar por template/formato desconhecido.
Os cenários partial/failed de content_generation estão cobertos por testes do Django e Vitest, mas não por chamada HTTP real ponta-a-ponta.
```

Detalhes devem ser mantidos em [[matriz_validacao]].

---

# 11. Indicadores de acompanhamento

|Indicador|Valor actual|Observação|
|---|--:|---|
|Estado geral|Green|Projecto controlado.|
|Fase actual|Transição pós-renderer|Renderer concluído; próxima fase a decidir.|
|Backend Core|Concluído|Manter apenas hardening/correcções.|
|Integração Django ↔ serviços externos|Concluída|Contratos prontos e validados.|
|Renderer MVP|Concluído|Geração PNG/PDF/HTML funcional.|
|Renderer hardening|Concluído|Callback background, retry, StorageProvider, E2E, coverage e documentação concluídos.|
|Testes renderer|136 passed|Suite Vitest.|
|Coverage lines|91.86%|Acima do threshold.|
|Coverage statements|91.9%|Acima do threshold.|
|Coverage branches|79.32%|Acima do threshold.|
|Coverage functions|95.89%|Acima do threshold.|
|E2E PostgreSQL|Validado|Loop Django ↔ Renderer com Asset via callback.|
|Pronto para integração|Sim (renderer, Intelligence Engine e wiring síncrono)|Chamada real Django → Intelligence Engine implementada e validada.|
|Pronto para piloto técnico|Sim|Pode ser usado em piloto técnico controlado.|
|Pronto para produção|Não|Requer S3/R2, observabilidade, política operacional, staging contínuo e calibração de heurísticas/resultados.|
|FastAPI Intelligence Engine|Concluído (MVP, IE-001 a IE-010)|197 testes aprovados; contrato com Backend Core documentado.|
|Wiring Backend Core ↔ Intelligence Engine|Concluído (BC-IE-001 a BC-IE-010)|459 testes aprovados; loop real validado; bug de contrato corrigido.|
|Bloqueios activos|0|Nenhum bloqueio conhecido.|
|Percentagem global|Por confirmar|Não calcular sem baseline formal.|

---

# 12. Decisões pendentes

|ID|Decisão pendente|Impacto|Prazo/Quando decidir|
|---|---|--:|---|
|PDEC-002|Definir se S3/R2 entra antes do piloto técnico ou apenas antes da produção.|Alto|Antes de disponibilizar fora do ambiente controlado.|
|PDEC-003|Definir nível mínimo de observabilidade para produção.|Médio/Alto|Antes de produção.|
|PDEC-004|Definir se background in-process é suficiente para piloto ou se será necessária fila persistente.|Alto|Antes de workloads reais prolongados.|
|PDEC-006|Definir nível mínimo de qualidade visual dos templates.|Médio|Antes de demonstração externa ou piloto com utilizadores reais.|
|PDEC-008|Definir a próxima fase pós-wiring-Intelligence-Engine: S3/R2, frontend mínimo, observabilidade ou staging contínuo.|Alto|Imediato, antes da próxima pipeline.|

Nota: PDEC-001 (avançar para FastAPI Intelligence Engine) e PDEC-005 (prioridade entre Intelligence Engine e frontend) ficam resolvidas — o Intelligence Engine foi executado e concluído. PDEC-007 (wiring Backend Core ↔ Intelligence Engine como próxima fase) também fica resolvida — o wiring síncrono foi executado e concluído (BC-IE-001 a BC-IE-010). Sucedidas por PDEC-008.

---

# 13. Histórico de status

## 2026-06-25 — Snapshot pós-conclusão do wiring síncrono Backend Core ↔ Intelligence Engine

```text
Estado geral: GREEN
Fase actual: Transição pós-wiring-Intelligence-Engine para próxima fase
Saúde: Controlado
Pronto para integração: Sim
Pronto para piloto técnico: Sim
Pronto para produção: Não
```

### Resumo

O backlog `backend_core/docs/backend_core/fundamentos/integracao_intelligence_engine/01_backlog.md` (BC-IE-001 a BC-IE-010) foi executado de fundação a fecho de fase: análise/contrato/plano, settings dedicados com guarda de produção, client síncrono, builder do data bundle, serviço de domínio, endpoint API, política de timeout/retry/fallback, validação E2E com mocks HTTP (13 cenários) e validação real com os dois serviços a correr de facto.

Durante a validação real (BC-IE-009), foi encontrado e corrigido um bug genuíno de contrato: o Intelligence Engine rejeitava `content_outputs[].created_at` com `422 invalid_payload / date_from_datetime_inexact`, porque o campo é um `DateTimeField` Django mas o schema Pydantic do engine espera apenas uma data. A correcção (truncar para data antes de serializar) foi aplicada e revalidada — depois do fix, a chamada real devolveu `200/completed` com `analysis`, `scores`, `grade`, `moments`, `recommendations` e `summary`, e o token nunca apareceu em nenhum log, mesmo no cenário de falha (engine inacessível).

A integração entre o Backend Core e o Intelligence Engine deixa de ser apenas um contrato documentado e passa a ser uma chamada real, validada e pronta para piloto técnico. O projecto continua em estado controlado; a próxima decisão é escolher entre S3/R2, frontend mínimo, observabilidade ou um ambiente de staging contínuo (PDEC-008).

### Concluído

- Wiring síncrono Backend Core ↔ Intelligence Engine completo (BC-IE-001 a BC-IE-010).
    
- Settings `INTELLIGENCE_ENGINE_*` com guarda de produção.
    
- Client síncrono `IntelligenceEngineClient`.
    
- Builder do data bundle de campanha `CampaignIntelligencePayloadBuilder`.
    
- Serviço de domínio `CampaignIntelligenceService`.
    
- Endpoint `POST /api/v1/campaigns/{id}/intelligence/`.
    
- Política de timeout/retry/fallback (retry só em falhas transitórias).
    
- Validação E2E com mocks HTTP (13 cenários).
    
- Validação real do loop Backend Core → Intelligence Engine, com correcção de bug real.
    
- Documento de estado final consolidado.
    
- Actualização dos seis documentos de acompanhamento.
    

### Validações

```text
pytest -q (suite completa): 459 passed, 3 skipped (loop real opt-in), 245 warnings, 296.90s
ruff check apps/ config/: All checks passed!
manage.py check: 0 issues
schema.yml: sem diff após regeneração
Loop real (3 testes, com os dois serviços a correr): passed
mypy/pyright: não configurados no Backend Core (limitação pré-existente, documentada)
Sem secrets reais em .env.example/docs/relatórios/testes (grep dirigido)
```

### Em curso

- Decisão explícita sobre a próxima fase do projecto (PDEC-008).
    

### Riscos principais

- Sem observabilidade dedicada (métricas/alertas) para a chamada síncrona ao Intelligence Engine.
    
- Validação real é local/opt-in, não corre em CI nem em staging persistente (RSK-017).
    
- Heurísticas do Intelligence Engine e resultados devolvidos via o endpoint real não calibrados com dados reais.
    
- Storage local do renderer ainda não é adequado para produção.
    
- Observabilidade operacional geral ainda não implementada.
    

### Próximo foco

Decidir explicitamente a próxima fase (PDEC-008): S3/R2, frontend mínimo, observabilidade ou ambiente de staging contínuo.

---

## 2026-06-25 — Snapshot pós-conclusão do FastAPI Intelligence Engine

```text
Estado geral: GREEN
Fase actual: Transição pós-Intelligence-Engine para próxima fase
Saúde: Controlado
Pronto para integração: Sim (lado Intelligence Engine)
Pronto para piloto técnico: Sim
Pronto para produção: Não
```

### Resumo

A fase do FastAPI Intelligence Engine foi concluída de fundação a fecho (IE-001 a IE-010): fundação FastAPI, autenticação interna, schemas comuns, os quatro motores (analysis, scoring, recommendations, moments), o endpoint composto orquestrador, o contrato de integração com o Backend Core, e a validação/documentação final da fase.

O serviço é determinístico e explicável (cada score, recomendação e momento traz a sua justificação), sem IA generativa, sem scraping, sem persistência de estado de produto e sem chamada directa ao renderer — preservando a tese arquitectural do projecto.

O contrato de integração com o Backend Core (IE-009) identificou uma divergência: o Backend Core já tinha scaffolding assíncrono (`ExternalJobReference` + jobs + callback) preparado para o Intelligence Engine, mas o MVP implementado é síncrono. A recomendação registada foi um modelo híbrido com síncrono como default do MVP, reservando o caminho assíncrono para trabalho pesado futuro.

O Intelligence Engine está pronto para integração (do seu lado) e piloto técnico, mas a integração real com o Backend Core ainda não foi exercitada — falta o wiring do lado Django. O projecto continua em estado controlado; a próxima decisão é escolher entre avançar com esse wiring, S3/R2, frontend mínimo ou observabilidade.

### Concluído

- FastAPI Intelligence Engine MVP completo (IE-001 a IE-010).
    
- Fundação FastAPI, autenticação interna, erros normalizados, logging estruturado.
    
- Schemas/contratos Pydantic comuns.
    
- `POST /analysis/campaign`.
    
- `POST /scoring/campaign`.
    
- `POST /recommendations/campaign`.
    
- `POST /moments/detect`.
    
- `POST /intelligence/campaign` (endpoint composto).
    
- Contrato de integração Backend Core ↔ Intelligence Engine documentado.
    
- Validação final e documento de estado do Intelligence Engine.
    
- Actualização dos seis documentos de acompanhamento.
    

### Validações

```text
pytest -q: 197 passed, 1 warning (terceiros, não bloqueante)
ruff check .: All checks passed!
ruff format --check .: conforme (após correcção)
Smoke test real: GET /health público; 5 endpoints exigem X-Internal-Token; payload malformado → 422
Sem IA generativa, scraping, persistência ou chamada directa ao renderer (grep dirigido)
Sem secrets reais em README/.env.example/docs
```

### Em curso

- Decisão explícita sobre a próxima fase do projecto.
    

### Riscos principais

- Wiring real do Backend Core ao Intelligence Engine ainda não implementado.
    
- Heurísticas do Intelligence Engine não calibradas com dados reais.
    
- Sem coverage formal nem type-checking estático no Intelligence Engine.
    
- Storage local do renderer ainda não é adequado para produção.
    
- Observabilidade operacional ainda não implementada.
    

### Próximo foco

Decidir explicitamente a próxima fase (PDEC-007): wiring Backend Core ↔ Intelligence Engine, S3/R2, frontend mínimo ou observabilidade.

---

## 2026-06-24 — Snapshot pós-hardening do Content/Report Renderer

```text
Estado geral: GREEN
Fase actual: Transição pós-renderer para próxima fase
Saúde: Controlado
Pronto para integração: Sim
Pronto para piloto técnico: Sim
Pronto para produção: Não
```

### Resumo

A fase de Content/Report Renderer foi concluída com sucesso, incluindo MVP funcional e hardening pós-MVP.

O renderer está agora estabilizado para integração controlada com o Backend Core. O loop Django ↔ Renderer ↔ Django foi validado com PostgreSQL, com criação de assets via callback em content, report e media kit, além de validação de idempotência.

A fase de hardening também concluiu callback em background leve, retry com backoff, echo de `template_key/template_id`, abstracção de storage, harness E2E PostgreSQL, coverage Vitest e documentação final.

O projecto continua em estado controlado. A próxima decisão é escolher a próxima fase: FastAPI Intelligence Engine, S3/R2, frontend mínimo ou melhoria visual dos templates.

### Concluído

- Content/Report Renderer MVP.
    
- Hardening pós-MVP do renderer.
    
- Callback em background leve.
    
- Retry de callback com backoff.
    
- Echo de `template_key/template_id` no `content_generation`.
    
- Abstracção `StorageProvider`.
    
- Harness E2E com PostgreSQL.
    
- Loop real Django ↔ Renderer ↔ Django validado.
    
- Coverage Vitest configurado.
    
- Documentação final pós-hardening.
    
- Build, lint, testes e coverage aprovados.
    

### Validações

```text
npm run build: aprovado
npm run lint: aprovado
npm test: 136 passed
npm run test:coverage: aprovado
Coverage lines: 91.86%
Coverage statements: 91.9%
Coverage branches: 79.32%
Coverage functions: 95.89%
E2E PostgreSQL: aprovado para cenários principais
```

### Em curso

- Actualização dos documentos de acompanhamento.
    
- Preparação da decisão sobre a próxima fase.
    

### Riscos principais

- Storage local ainda não é adequado para produção.
    
- Observabilidade operacional ainda não implementada.
    
- Background jobs continuam in-process, sem fila persistente.
    
- `content_generation` partial/failed tem cobertura indirecta, não E2E HTTP real.
    

### Próximo foco

Decidir e preparar a próxima fase. Recomendação actual: criar backlog e pipeline para **FastAPI Intelligence Engine**.

---

## 2026-06-23 — Snapshot inicial

```text
Estado geral: GREEN
Fase actual: Content/Report Renderer
Saúde: Controlado
```

### Resumo

O projecto avançou bem nas fases técnicas de fundação. O Backend Core Django está concluído para o MVP técnico e a integração Backend Core ↔ serviços externos foi finalizada com contratos, callbacks, segurança, idempotência, testes e documentação.

A próxima fase é criar o Content/Report Renderer como primeiro serviço técnico real a responder aos jobs externos do Django.

### Concluído

- Backend Core Django.
    
- Integração com jobs externos.
    
- Callback interno autenticado.
    
- Idempotência de callbacks.
    
- Billing/credits ligados ao ciclo de geração.
    
- Notifications e audit nos fluxos críticos.
    
- Backlog do Content/Report Renderer.
    
- Pipeline de prompts do Content/Report Renderer.
    

### Em curso

- Preparação para execução da pipeline do Content/Report Renderer.
    

### Riscos principais

- Acoplamento excessivo ao payload do Django.
    
- Dependências pesadas para geração de PDF.
    
- Falha de callback após geração de ficheiros.
    
- Expansão indevida de escopo para vídeo/editor visual.
    

### Próximo foco

Executar o Prompt 01 da pipeline Content/Report Renderer e registar a execução no Diário de Execução IA.

---