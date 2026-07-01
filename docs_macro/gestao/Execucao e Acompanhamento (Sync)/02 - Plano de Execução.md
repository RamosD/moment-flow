---

doc_id: "exec-plano-execucao"  
title: "Plano de Execução"  
project: "ChartRex / MomentFlow"  
area: "gestao_execucao"  
doc_type: "execution_plan"  
status: "active"  
owner: "Aldino Ramos"  
created_at: "2026-06-23"  
updated_at: "2026-06-25"  
last_reviewed_at: "2026-06-25"  
review_frequency: "weekly"  
update_frequency: "per_phase"  
version: "1.3"  
confidentiality: "internal"  
source_of_truth: true

planning_horizon: "phase_based"  
execution_model: "pipeline_prompts_ia_local"  
current_phase: "Transição pós-wiring-Intelligence-Engine para próxima fase"  
current_phase_status: "decision_pending"  
active_pipeline: null  
active_backlog: null  
last_completed_phase: "Backend Core ↔ Intelligence Engine — wiring síncrono (BC-IE-001 a BC-IE-010)"  
last_completed_pipeline: "Backend Core ↔ Intelligence Engine — wiring síncrono"  
next_recommended_phase: "por decidir"  
next_recommended_backlog: null  
next_recommended_pipeline: null

ready_for_integration_environment: true  
ready_for_technical_pilot: true  
ready_for_production: false

---

related_docs:

- "[[status_report]]"
    
- "[[log_decisoes]]"
    
- "[[riscos_bloqueios]]"
    
- "[[matriz_validacao]]"
    
- "[[diario_execucao_ia]]"
    

tags:

- "project/momentflow"
    
- "gestao/plano"
    
- "execucao"
    
- "ia-local"
    
- "obsidian"
    

## ai_update_mode: "controlled"  
ai_update_scope: "actualizar fases, ordem de execução, dependências, estado das actividades, próximos prompts, critérios de pronto e decisões de transição entre fases."  
ai_may_create_sections: true  
ai_may_delete_content: false  
ai_should_preserve_history: true

# Plano de Execução — ChartRex / MomentFlow

## 1. Instruções para IA actualizar este documento

Este documento define a **ordem de execução do projecto**, as fases, dependências, pipelines, critérios de pronto e decisões de transição.

Ao actualizar este ficheiro, a IA deve:

```text
1. Ler primeiro o README.md desta pasta.
2. Ler os metadados YAML deste documento.
3. Respeitar ai_update_mode e ai_update_scope.
4. Actualizar updated_at no YAML.
5. Actualizar current_phase, active_pipeline e active_backlog quando aplicável.
6. Marcar fases concluídas apenas com evidência.
7. Não apagar fases anteriores.
8. Não inventar prompts executados.
9. Não inventar validações.
10. Manter histórico de execução e transições.
11. Usar os documentos relacionados:
    - [[status_report]]
    - [[diario_execucao_ia]]
    - [[matriz_validacao]]
    - [[riscos_bloqueios]]
    - [[log_decisoes]]
```

A IA pode:

```text
- actualizar estados de fases;
- adicionar novas fases planeadas;
- adicionar pipelines previstas;
- actualizar dependências;
- actualizar critérios de pronto;
- adicionar decisões pendentes;
- adicionar entradas ao histórico de execução.
```

A IA não deve:

```text
- apagar histórico de fases;
- remover decisões antigas;
- marcar uma fase como concluída sem evidência;
- declarar produção-ready sem S3/R2, observabilidade e política operacional;
- alterar a tese arquitectural sem decisão registada;
- criar novas fases fora do escopo sem indicação explícita.
```

Quando não houver evidência suficiente, usar:

```text
Estado: por confirmar
Evidência: não disponível
Acção necessária: validar manualmente
```

---

# 2. Tese de execução

A execução do projecto deve obedecer à tese arquitectural:

```text
Django governa o produto.
Renderer gera activos.
FastAPI Intelligence calcula, recomenda e detecta oportunidades.
Frontend orquestra a experiência do utilizador.
```

## Responsabilidades por componente

|Componente|Responsabilidade|
|---|---|
|Backend Core Django|Produto, utilizadores, workspaces, RBAC, billing, entidades de negócio, estado, audit, callbacks e orquestração.|
|Content/Report Renderer|Receber jobs técnicos, gerar activos PNG/PDF/HTML, guardar ficheiros e devolver callbacks.|
|FastAPI Intelligence Engine|Análise, scoring, recomendações, detecção de momentos e inteligência operacional.|
|Frontend|Experiência de utilizador, Campaign War Room, operação de campanhas e visualização.|
|Storage S3/R2|Armazenamento de produção para assets gerados.|

---

# 3. Estado executivo actual

```text
Estado geral: GREEN
Fase actual: Transição pós-wiring-Intelligence-Engine para próxima fase
Última fase concluída: Backend Core ↔ Intelligence Engine — wiring síncrono (BC-IE-001 a BC-IE-010)
Pronto para integração: Sim
Pronto para piloto técnico: Sim
Pronto para produção: Não
```

## Resumo

O projecto concluiu as fases de Backend Core, integração com serviços externos, Content/Report Renderer (MVP + hardening), o FastAPI Intelligence Engine MVP completo e agora o **wiring síncrono real entre o Backend Core e o Intelligence Engine**.

O `content_renderer` está estabilizado para integração controlada:

```text
- MVP funcional concluído;
- hardening pós-MVP concluído;
- callback em background leve;
- retry de callback com backoff;
- echo de template_key/template_id;
- StorageProvider abstraction;
- E2E com PostgreSQL;
- loop real Django ↔ Renderer ↔ Django validado;
- coverage configurado;
- documentação final concluída.
```

O `intelligence_engine` está funcional e validado de fundação a fecho de fase:

```text
- 5 endpoints implementados: /analysis/campaign, /scoring/campaign, /recommendations/campaign, /moments/detect, /intelligence/campaign (composto);
- determinístico, explicável, sem IA generativa, sem scraping, sem persistência, sem chamada directa ao renderer;
- 197 testes aprovados, ruff limpo;
- contrato de integração com o Backend Core documentado (recomendação síncrona "sync-first");
- documento de estado final criado.
```

O **wiring síncrono Backend Core ↔ Intelligence Engine** foi agora implementado e validado de ponta a ponta:

```text
- settings dedicados (INTELLIGENCE_ENGINE_*) com guarda de produção;
- client síncrono IntelligenceEngineClient, builder do data bundle, serviço de domínio e endpoint API;
- política de timeout/retry/fallback (retry só em falhas transitórias, nunca em 4xx);
- 13 cenários E2E com mocks HTTP;
- loop real com os dois serviços a correr de facto, incluindo um bug real de contrato encontrado e corrigido;
- 459 testes aprovados (suite completa do Backend Core), ruff limpo;
- documento de estado final consolidado criado.
```

A próxima acção é decidir a próxima fase de implementação — ver decisão pendente PDEC-008 em [[log_decisoes]].

---

# 4. Roadmap por fases

|Ordem|Fase|Estado|Resultado esperado|Dependência|
|--:|---|---|---|---|
|1|Visão de produto e posicionamento|Concluído|Produto definido como Music Campaign OS.|Nenhuma|
|2|Backend Core Django|Concluído|Fundação SaaS/produto implementada.|Fase 1|
|3|Integração Backend Core ↔ serviços externos|Concluído|Contratos de jobs/callbacks e integrações internas estabilizados.|Fase 2|
|4|Content/Report Renderer — MVP|Concluído|Renderer gera PNG/PDF/HTML e envia callbacks.|Fase 3|
|5|Content/Report Renderer — hardening pós-MVP|Concluído|Renderer pronto para integração/piloto técnico.|Fase 4|
|6|Transição pós-renderer|Concluído|Decidiu-se avançar para o FastAPI Intelligence Engine.|Fase 5|
|7|FastAPI Intelligence Engine|Concluído|Motores MVP (analysis, scoring, recommendations, moments) + endpoint composto + contrato de integração documentados.|Fase 6|
|8|Transição pós-Intelligence-Engine|Concluído|Decidiu-se avançar para o wiring síncrono Backend Core ↔ Intelligence Engine.|Fase 7|
|9|Wiring Backend Core ↔ Intelligence Engine|Concluído|Lado Django do contrato IE-009 implementado e validado (chamada síncrona, adaptador de payload, loop real).|Fase 8|
|10|Transição pós-wiring-Intelligence-Engine|Em curso|Decidir próxima fase e preparar backlog/pipeline.|Fase 9|
|11|Storage S3/R2 real|Planeado|Storage de produção para assets.|Fase 5|
|12|Frontend mínimo Campaign War Room|Planeado|Interface operacional mínima.|Backend + Renderer|
|13|Observabilidade e produção|Planeado|Métricas, tracing, dashboards, alertas e política operacional.|Serviços estabilizados|
|14|Templates visuais avançados|Futuro|Melhor qualidade visual dos assets.|Renderer estabilizado|
|15|Vídeo/Reels|Futuro / fora do escopo actual|Geração de vídeo, se fizer sentido.|Decisão futura|

---

# 5. Fases concluídas

## 5.1 Visão de produto e posicionamento

```text
Estado: concluído
```

### Resultado

Produto definido como **Music Campaign OS**, com foco em:

```text
- campanha primeiro;
- artistas, equipas e labels;
- geração de activos;
- reports;
- media kits;
- inteligência para momentos e recomendações;
- potencial de monetização B2B.
```

### Critério de pronto

```text
Visão consolidada e usada como base para arquitectura e backlog.
```

---

## 5.2 Backend Core Django

```text
Estado: concluído
```

### Resultado

Backend Core implementado com:

```text
- autenticação;
- JWT;
- Custom User;
- workspaces;
- multi-tenancy;
- RBAC;
- catálogo musical;
- campanhas;
- content core;
- smart links;
- billing;
- usage;
- créditos;
- reports;
- media kits;
- notifications;
- audit;
- OpenAPI;
- Admin;
- testes;
- hardening.
```

### Critério de pronto

```text
Backend Core funcional e validado para suportar entidades de produto e orquestração.
```

---

## 5.3 Integração Backend Core ↔ serviços externos

```text
Estado: concluído
```

### Resultado

Integração concluída com:

```text
- ExternalJobReference;
- submissão de jobs externos;
- callback interno autenticado;
- idempotência;
- dry-run;
- logs;
- retries;
- segurança;
- testes E2E;
- documentação.
```

### Critério de pronto

```text
Backend Core preparado para delegar processamento técnico a serviços externos.
```

---

## 5.4 Content/Report Renderer — MVP

```text
Estado: concluído
```

### Resultado

Renderer MVP implementado com:

```text
- serviço Node.js/TypeScript;
- GET /health;
- POST /jobs;
- X-Internal-Token;
- validação de headers;
- validação de envelope;
- storage local;
- /files em development;
- callback client;
- template engine;
- SVG → PNG;
- content_generation real;
- report_generation real com PDF/HTML;
- media_kit_generation real com PDF/HTML;
- erros normalizados;
- partial success;
- timeouts;
- logs sem token;
- README;
- documento de estado;
- relatórios de execução.
```

### Critério de pronto

```text
Renderer gera activos reais e devolve callbacks no contrato do Django.
```

---

## 5.5 Content/Report Renderer — hardening pós-MVP

```text
Estado: concluído
```

### Backlog

```text
docs\fundamentos\03_backlog_hardening_pos_mvp_renderer.md
```

### Pipeline executada

```text
Hardening Pós-MVP do Content/Report Renderer
```

### Prompts executados

|Prompt|Item|Estado|
|--:|---|---|
|01|Callback em background leve|Concluído|
|02|Retry de callback com backoff|Concluído|
|03|Echo de template_key/template_id|Concluído|
|04|StorageProvider abstraction|Concluído|
|05|Harness E2E com PostgreSQL|Concluído|
|06|Loop real Django ↔ Renderer ↔ Django|Concluído|
|07|Coverage Vitest|Concluído|
|08|Documentação final pós-hardening|Concluído|

### Resultado

O renderer passou de:

```text
MVP funcional com pendências técnicas
```

para:

```text
Serviço estabilizado para integração real controlada com o Backend Core.
```

### Validações

```text
npm run build: aprovado
npm run lint: aprovado
npm test: 136 passed
npm run test:coverage: aprovado
Coverage statements: 91.9%
Coverage branches: 79.32%
Coverage functions: 95.89%
Coverage lines: 91.86%
E2E PostgreSQL: loop Django ↔ Renderer validado
```

### Critério de pronto

```text
Renderer pronto para ambiente de integração e piloto técnico.
```

### Limitação assumida

```text
Ainda não é production-ready.
```

Motivos:

```text
- storage S3/R2 real não implementado;
- observabilidade e métricas operacionais não implementadas;
- background jobs continuam in-process;
- fila persistente ainda não existe.
```

---

## 5.6 FastAPI Intelligence Engine — MVP completo

```text
Estado: concluído
```

### Backlog

```text
intelligence_engine/docs/gestao/fundamentos/backlog.md
```

### Pipeline executada

```text
FastAPI Intelligence Engine — fundação a fecho de fase
```

### Prompts executados

|Prompt|Item|Estado|
|--:|---|---|
|01|Fundação FastAPI (factory, GET /health)|Concluído|
|02 / 02b|Config, segurança interna, erros normalizados + revisão de hardening|Concluído|
|03|Schemas e contratos Pydantic comuns|Concluído|
|04|Campaign analysis (`POST /analysis/campaign`)|Concluído|
|05|Scoring engine (`POST /scoring/campaign`)|Concluído|
|06|Recommendation engine (`POST /recommendations/campaign`)|Concluído|
|07|Moment detection (`POST /moments/detect`)|Concluído|
|08|Endpoint composto (`POST /intelligence/campaign`)|Concluído|
|09|Contrato de integração Backend Core ↔ Intelligence Engine|Concluído|
|10|Validação e documentação final|Concluído|

### Resultado

O Intelligence Engine passou de:

```text
Inexistente
```

para:

```text
Serviço FastAPI separado, determinístico e explicável, com 5 endpoints
funcionais (analysis, scoring, recommendations, moments, intelligence
composto), autenticação interna, erros normalizados, e contrato de
integração documentado com o Backend Core.
```

### Validações

```text
pytest -q: 197 passed, 1 warning (deprecação de terceiros, não bloqueante)
ruff check .: All checks passed!
ruff format --check .: conforme (após correcção de 3 ficheiros pré-existentes)
Smoke test real (TestClient): GET /health público; 5 endpoints exigem X-Internal-Token; payload malformado → 422
Grep dirigido: sem IA generativa, scraping, persistência ou chamada directa ao renderer
Grep dirigido: sem secrets reais em README/.env.example/docs
```

### Critério de pronto

```text
Intelligence Engine pronto para integração (do seu lado) e piloto técnico.
```

### Limitação assumida

```text
Ainda não é production-ready.
```

Motivos:

```text
- heurísticas (pesos/limiares) não calibradas com dados reais;
- sem coverage formal nem type-checking estático configurados;
- observabilidade limitada a logs estruturados.
```

Nota: a limitação "não está integrado de facto com o Backend Core" registada nesta secção fica resolvida pela fase 5.7 (wiring síncrono).

---

## 5.7 Backend Core ↔ Intelligence Engine — wiring síncrono

```text
Estado: concluído
```

### Backlog

```text
backend_core/docs/backend_core/fundamentos/integracao_intelligence_engine/01_backlog.md
```

### Pipeline executada

```text
Backend Core ↔ Intelligence Engine — wiring síncrono
```

### Prompts executados

|Prompt|Item|Estado|
|--:|---|---|
|01|Análise, contrato e plano de integração|Concluído|
|02|Settings do Intelligence Engine no Backend Core|Concluído|
|03|Client síncrono para o Intelligence Engine|Concluído|
|04|Builder do data bundle de campanha|Concluído|
|05|Serviço de domínio para intelligence de campanha|Concluído|
|06|Endpoint API de intelligence de campanha|Concluído|
|07|Timeout, retry e fallback|Concluído|
|08|Validação ponta-a-ponta com mocks HTTP|Concluído|
|09|Loop real Backend Core ↔ Intelligence Engine (sem mocks)|Concluído|
|10|Validação de qualidade e documentação de estado final|Concluído|

### Resultado

O wiring passou de:

```text
Contrato documentado, mas sem qualquer chamada real do Django ao Intelligence Engine
```

para:

```text
Chamada síncrona real e validada: ViewSet action → CampaignIntelligenceService →
CampaignIntelligencePayloadBuilder → IntelligenceEngineClient → FastAPI Intelligence Engine real,
com auth, RBAC, workspace scoping, timeout/retry/fallback seguros, e um loop real confirmado com os
dois serviços a correr de facto.
```

### Validações

```text
pytest -q (suite completa do Backend Core): 459 passed, 3 skipped (loop real opt-in), 245 warnings, 296.90s
ruff check apps/ config/: All checks passed!
manage.py check: 0 issues
schema.yml: sem diff após regeneração
13 cenários E2E com mocks HTTP (sucesso, warnings, timeout, 403, 422, 5xx, JSON inválido, desligado,
dry-run, RBAC/workspace, token não logado)
Loop real: 200/completed com analysis/scores/grade/moments/recommendations/summary; token ausente dos
logs mesmo em falha (engine inacessível)
mypy/pyright: não configurados no Backend Core (limitação pré-existente, documentada, não simulada)
Grep dirigido: sem secrets reais em .env.example/docs/relatórios/testes
```

### Critério de pronto

```text
Wiring síncrono pronto para piloto técnico.
```

### Limitação assumida

```text
Ainda não é production-ready.
```

Motivos:

```text
- sem observabilidade dedicada (métricas/alertas) para a chamada síncrona;
- validação real é local/opt-in (RUN_REAL_IE=1), não corre em CI nem em staging persistente;
- sem calibração de negócio dos scores/recomendações devolvidos via o endpoint real;
- bug real de granularidade date/datetime foi encontrado e corrigido nesta fase — outras divergências
  de contrato semelhantes podem só aparecer sob validação real adicional.
```

---

# 6. Fase actual — Transição pós-wiring-Intelligence-Engine

```text
Estado: em curso
Tipo: decisão de próxima fase
```

## Objectivo

Escolher e preparar a próxima fase de implementação, sem avançar para código antes de actualizar os documentos de acompanhamento e registar a decisão.

## Actividades da fase actual

|ID|Actividade|Estado|Documento relacionado|
|---|---|---|---|
|TR3-001|Actualizar diario_execucao_ia.md|Concluído|[[diario_execucao_ia]]|
|TR3-002|Actualizar matriz_validacao.md|Concluído|[[matriz_validacao]]|
|TR3-003|Actualizar riscos_bloqueios.md|Concluído|[[riscos_bloqueios]]|
|TR3-004|Actualizar log_decisoes.md|Concluído|[[log_decisoes]]|
|TR3-005|Actualizar plano_execucao.md|Concluído|Este documento|
|TR3-006|Actualizar status_report.md|Em curso|[[status_report]]|
|TR3-007|Decidir próxima fase|Pendente|[[log_decisoes]] / [[plano_execucao]]|
|TR3-008|Criar backlog da próxima fase|Pendente|A definir|
|TR3-009|Criar pipeline da próxima fase|Pendente|A definir|

Nota: TR-001 a TR-009 (transição pós-renderer) foram concluídas com a execução do FastAPI Intelligence Engine. TR2-001 a TR2-009 (transição pós-Intelligence-Engine) foram concluídas com a execução do wiring síncrono Backend Core ↔ Intelligence Engine. Esta nova tabela (TR3-xxx) cobre a transição pós-wiring-Intelligence-Engine.

## Critério de pronto da fase actual

```text
Documentos de acompanhamento actualizados.
Decisão da próxima fase registada.
Backlog da próxima fase criado.
Pipeline da próxima fase criada.
```

---

# 7. Próximas fases candidatas

## 7.1 FastAPI Intelligence Engine — concluído

```text
Estado: concluído (IE-001 a IE-010)
```

Ver secção 5.6. Esta candidata deixa de ser "próxima fase" e passa a fase concluída; a candidata sucessora, 7.6 (wiring Backend Core ↔ Intelligence Engine), também já está concluída — ver secção 5.7.

---

## 7.6 Wiring Backend Core ↔ Intelligence Engine — concluído

```text
Estado: concluído (BC-IE-001 a BC-IE-010)
```

Ver secção 5.7. Esta candidata deixa de ser "próxima fase" e passa a fase concluída; a próxima decisão (PDEC-008) é entre as candidatas remanescentes (7.2 a 7.5, mais a nova 7.7).

---

## 7.7 Ambiente de staging com validação real contínua

```text
Estado: planeado
Prioridade sugerida: média
```

### Objectivo

Disponibilizar o Backend Core e o Intelligence Engine persistentemente em ambiente partilhado, para que a validação real do wiring síncrono (hoje local/opt-in via `RUN_REAL_IE=1`) possa correr de forma recorrente, não apenas pontual.

### Justificação

A validação real capturada em BC-IE-009 é genuína, mas pontual no tempo. Sem staging persistente, futuras divergências de contrato entre os dois serviços só seriam detectadas manualmente.

### Dependências

```text
Wiring síncrono Backend Core ↔ Intelligence Engine concluído (BC-IE-001 a BC-IE-010).
Decisão sobre infraestrutura de staging.
```

### Critério de pronto para iniciar

```text
Ambiente de staging definido.
Decisão sobre se o loop real entra numa pipeline de CI dedicada.
```

---

## 7.2 Storage S3/R2 real

```text
Estado: planeado
Prioridade sugerida: média/alta antes de produção
```

### Objectivo

Substituir storage local por provider real de object storage.

### Justificação

Storage local é suficiente para MVP e piloto controlado, mas não para produção.

### Dependências

```text
StorageProvider abstraction concluída.
Decisão sobre provider: S3, Cloudflare R2 ou equivalente.
Credenciais e bucket de ambiente definidos.
```

### Critério de pronto para iniciar

```text
Provider escolhido.
Ambiente de desenvolvimento definido.
Política de secrets definida.
```

---

## 7.3 Frontend mínimo Campaign War Room

```text
Estado: planeado
Prioridade sugerida: média
```

### Objectivo

Criar interface mínima para operar campanhas, visualizar activos, reports e media kits.

### Justificação

Após backend e renderer, o produto precisa de uma experiência utilizável.

### Dependências

```text
Backend Core estável.
Renderer estável.
Decisão sobre UX mínima.
```

### Critério de pronto para iniciar

```text
Backlog UX mínimo criado.
Rotas/telas prioritárias definidas.
```

---

## 7.4 Observabilidade e produção

```text
Estado: planeado
Prioridade sugerida: alta antes de produção
```

### Objectivo

Preparar métricas, tracing, dashboards e alertas.

### Justificação

O renderer já tem logs estruturados, mas ainda não tem métricas operacionais, tracing ou dashboards.

### Dependências

```text
Serviços estabilizados.
Ambiente de integração definido.
Decisão sobre stack de observabilidade.
```

### Critério de pronto para iniciar

```text
Stack de observabilidade definida.
Métricas mínimas acordadas.
```

---

## 7.5 Templates visuais avançados

```text
Estado: futuro
Prioridade sugerida: baixa/média
```

### Objectivo

Melhorar qualidade visual dos outputs gerados.

### Justificação

Útil para demonstração e piloto externo, mas não deve bloquear a inteligência do produto.

### Dependências

```text
Critérios mínimos de design definidos.
Possível frontend ou preview definido.
```

---

# 8. Ordem recomendada a partir de agora

## Histórico — ordem seguida após o Intelligence Engine MVP (já executada)

```text
1. Concluir actualização dos documentos de acompanhamento.
2. Registar decisão da próxima fase.
3. Executar o backlog do wiring síncrono Backend Core ↔ Intelligence Engine (BC-IE-001 a BC-IE-010).
4. Decidir entre S3/R2, frontend mínimo, observabilidade ou staging contínuo.
```

Os passos 1–3 foram executados com sucesso (ver secção 5.7); o passo 4 mantém-se em aberto (PDEC-008).

## Recomendação a partir de agora

```text
1. Concluir actualização dos documentos de acompanhamento (esta secção).
2. Registar decisão explícita da próxima fase (PDEC-008 em log_decisoes).
3. Criar backlog da fase escolhida.
4. Criar pipeline de prompts da fase escolhida.
5. Executar a implementação.
```

## Veredicto recomendado

```text
Sem veredicto técnico fixado nesta actualização documental — ver PDEC-008 em [[log_decisoes]].
```

Nota: esta actualização documental não inclui uma recomendação de produto forte para a fase seguinte; cabe ao decisor escolher entre S3/R2, frontend mínimo, observabilidade ou ambiente de staging contínuo (secção 7.7).

---

# 9. Plano imediato de execução documental

Antes da próxima implementação, actualizar os documentos nesta ordem:

|Ordem|Documento|Objectivo|Estado|
|--:|---|---|---|
|1|diario_execucao_ia.md|Registar pipeline Backend Core ↔ Intelligence Engine (BC-IE-001 a BC-IE-010)|Concluído|
|2|matriz_validacao.md|Registar validações do wiring síncrono|Concluído|
|3|riscos_bloqueios.md|Actualizar riscos novos/mitigados pós-wiring (RSK-014 mitigado, RSK-017 novo)|Concluído|
|4|log_decisoes.md|Registar decisões técnicas do fecho de fase (DEC-021)|Concluído|
|5|plano_execucao.md|Reflectir fase concluída e próxima decisão|Concluído|
|6|status_report.md|Reflectir estado executivo pós-wiring|Em curso|

## Critério de pronto documental

```text
Os seis documentos principais reflectem o mesmo estado:
- Wiring síncrono Backend Core ↔ Intelligence Engine concluído (BC-IE-001 a BC-IE-010);
- chamada real Django → Intelligence Engine implementada e validada (mocks + loop real);
- produção ainda pendente (renderer, Intelligence Engine e wiring síncrono);
- próxima fase por decidir.
```

---

# 10. Critérios para avançar para próxima implementação

Só avançar para a próxima implementação quando:

```text
status_report.md actualizado;
plano_execucao.md actualizado;
diario_execucao_ia.md actualizado;
matriz_validacao.md actualizado;
riscos_bloqueios.md actualizado;
log_decisoes.md actualizado;
próxima fase decidida;
backlog da próxima fase criado;
pipeline da próxima fase criada.
```

---

# 11. Critérios de produção

O projecto ainda **não** deve ser considerado pronto para produção.

## Bloqueadores de produção

```text
Storage S3/R2 real.
Observabilidade e métricas operacionais.
Política operacional para background jobs.
Gestão de retries/falhas persistentes.
Segurança e gestão de secrets por ambiente.
Deploy e CI/CD definidos.
```

## Não bloqueia piloto técnico controlado

```text
Storage local.
Background in-process.
Templates simples.
Ausência de frontend completo.
Validação real do wiring ser local/opt-in em vez de contínua em staging (RSK-017).
```

---

# 12. Histórico de execução

## 2026-06-25 — Fecho do wiring síncrono Backend Core ↔ Intelligence Engine

```text
Estado: concluído
Pipeline: Backend Core ↔ Intelligence Engine — wiring síncrono
Prompts: 01–10
Resultado: sucesso
```

### Concluído

```text
Análise, contrato e plano de integração (caminho síncrono, isolado de ExternalJobReference).
Settings INTELLIGENCE_ENGINE_* com guarda de produção.
Client síncrono IntelligenceEngineClient (apps/integrations_bridge/intelligence_sync.py).
Builder do data bundle de campanha (apps/campaigns/intelligence_payload.py).
Serviço de domínio CampaignIntelligenceService (ENABLED/DRY_RUN, mapeamento de erros).
Endpoint POST /api/v1/campaigns/{id}/intelligence/ (auth + RBAC + workspace scoping).
Política de timeout/retry/fallback (retry só em falhas transitórias).
Validação E2E com mocks HTTP (13 cenários).
Validação real com os dois serviços a correr de facto (bug de granularidade date/datetime corrigido).
Documentação de estado final e fecho de fase.
```

### Evidências

```text
pytest -q (suite completa): 459 passed, 3 skipped (loop real opt-in), 245 warnings, 296.90s
ruff check apps/ config/: All checks passed!
manage.py check: 0 issues
schema.yml: sem diff após regeneração
Loop real: 200/completed com analysis/scores/grade/moments/recommendations/summary; token ausente dos logs
Grep dirigido: sem secrets reais em .env.example/docs/relatórios/testes
mypy/pyright: não configurados (limitação pré-existente, documentada)
```

### Decisão de transição

```text
A fase de wiring síncrono Backend Core ↔ Intelligence Engine fica encerrada.
A chamada real Django → Intelligence Engine está implementada e validada, pronta para piloto técnico.
Produção continua dependente de observabilidade dedicada, staging contínuo e calibração de negócio.
```

### Próximo foco

```text
Actualizar documentos de acompanhamento (em curso).
Decidir explicitamente a próxima fase (PDEC-008).
```

---

## 2026-06-24/25 — Fecho do FastAPI Intelligence Engine MVP

```text
Estado: concluído
Pipeline: FastAPI Intelligence Engine — fundação a fecho de fase
Prompts: 01–10 (incluindo 02b)
Resultado: sucesso
```

### Concluído

```text
Fundação FastAPI (factory, settings, erros, logging estruturado).
Autenticação interna X-Internal-Token + hardening de segurança.
Schemas/contratos Pydantic comuns.
POST /analysis/campaign.
POST /scoring/campaign.
POST /recommendations/campaign.
POST /moments/detect.
POST /intelligence/campaign (composto).
Contrato de integração Backend Core ↔ Intelligence Engine documentado.
Validação final e documento de estado.
```

### Evidências

```text
pytest -q: 197 passed, 1 warning (terceiros, não bloqueante)
ruff check .: All checks passed!
ruff format --check .: conforme (após correcção)
Smoke test real: GET /health público; 5 endpoints exigem X-Internal-Token; payload malformado → 422
Sem IA generativa, scraping, persistência ou chamada directa ao renderer (grep dirigido)
Sem secrets reais em README/.env.example/docs
```

### Decisão de transição

```text
A fase FastAPI Intelligence Engine fica encerrada para o MVP.
O serviço está pronto para integração (do seu lado) e piloto técnico.
Produção continua dependente do wiring real do Backend Core, calibração de heurísticas e observabilidade.
```

### Próximo foco

```text
Actualizar documentos de acompanhamento (em curso).
Decidir explicitamente a próxima fase (PDEC-007).
```

---

## 2026-06-24 — Fecho do hardening pós-MVP do renderer

```text
Estado: concluído
Pipeline: Hardening Pós-MVP do Content/Report Renderer
Prompts: 01–08
Resultado: sucesso
```

### Concluído

```text
Callback em background leve.
Retry de callback com backoff.
Echo de template_key/template_id.
StorageProvider abstraction.
Harness E2E PostgreSQL.
Loop real Django ↔ Renderer ↔ Django.
Coverage Vitest.
Documentação final pós-hardening.
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
```

### Decisão de transição

```text
A fase Content/Report Renderer fica encerrada para MVP + hardening.
O serviço está pronto para integração e piloto técnico.
Produção continua dependente de S3/R2, observabilidade e política operacional.
```

### Próximo foco

```text
Actualizar documentos de acompanhamento.
Registar decisão sobre próxima fase.
Recomendação: FastAPI Intelligence Engine.
```

---

## 2026-06-23 — Preparação do Content/Report Renderer

```text
Estado: concluído
Pipeline: Content/Report Renderer
Resultado: pipeline criada e executada posteriormente.
```

### Resumo

Foi preparada e executada a fase do Content/Report Renderer, transformando o renderer de backlog em serviço funcional.

---

## 2026-06-23 — Fases anteriores concluídas

```text
Estado: concluído
Fases: Backend Core + Integração Backend Core ↔ serviços externos
```

### Resumo

O Backend Core e a camada de integração com serviços externos foram concluídos antes da implementação do renderer.

---

# 13. Notas finais

Este plano deve continuar a ser o documento que responde:

```text
O que já foi feito?
O que está em curso?
O que vem a seguir?
Que dependências existem?
Que critérios faltam cumprir?
Quando podemos avançar?
```

O próximo update deste ficheiro deve acontecer quando:

```text
a próxima fase for decidida;
o backlog da próxima fase for criado;
a pipeline da próxima fase for criada;
ou surgir alteração relevante de prioridade.
```