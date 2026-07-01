
# Backlog: FastAPI Intelligence Engine

# ChartRex / MomentFlow — FastAPI Intelligence Engine

## 1. Objectivo do documento

Este documento define o backlog técnico e funcional da fase **FastAPI Intelligence Engine** do projecto **ChartRex / MomentFlow**.

A fase anterior concluiu o **Content/Report Renderer**, incluindo MVP funcional e hardening pós-MVP. O projecto já consegue receber jobs do Backend Core, gerar activos PNG/PDF/HTML, guardar ficheiros em storage local, enviar callbacks e validar o loop Django ↔ Renderer ↔ Django em PostgreSQL.

A próxima fase deve criar o serviço técnico responsável por:

```text
- analisar dados de campanha;
- calcular scores;
- detectar oportunidades;
- sugerir acções;
- recomendar campanhas;
- gerar insights explicáveis;
- preparar o caminho para inteligência mais avançada no produto.
```

---

## 2. Tese arquitectural

A tese arquitectural mantém-se:

```text
Django governa o produto.
Renderer gera activos.
FastAPI Intelligence calcula, recomenda e detecta oportunidades.
Frontend orquestra a experiência do utilizador.
```

## 2.1 Responsabilidade do Backend Core Django

O Backend Core continua responsável por:

```text
- users;
- workspaces;
- RBAC;
- billing;
- créditos;
- entidades de produto;
- campanhas;
- catálogo musical;
- content packs;
- reports;
- media kits;
- estado de negócio;
- audit;
- notifications;
- callbacks;
- persistência principal;
- orquestração.
```

## 2.2 Responsabilidade do FastAPI Intelligence Engine

O Intelligence Engine será responsável por:

```text
- receber payloads técnicos enviados pelo Django;
- validar contratos internos;
- calcular scores;
- gerar insights técnicos;
- detectar oportunidades/momentos;
- recomendar acções de campanha;
- devolver respostas estruturadas e explicáveis;
- manter lógica de cálculo isolada do produto.
```

## 2.3 O que o Intelligence Engine não deve fazer

O Intelligence Engine **não** deve:

```text
- gerir utilizadores;
- gerir workspaces;
- decidir permissões;
- gerir billing;
- consumir créditos;
- persistir estado de produto como fonte de verdade;
- substituir o Backend Core;
- chamar directamente o renderer no MVP;
- publicar conteúdo;
- fazer scraping externo;
- depender obrigatoriamente de IA generativa no MVP;
- armazenar segredos ou tokens em logs;
- criar campanhas directamente sem passar pelo Django.
```

---

## 3. Contexto actual

## 3.1 Estado das fases anteriores

```text
Backend Core Django: concluído
Integração Backend Core ↔ serviços externos: concluída
Content/Report Renderer MVP: concluído
Hardening pós-MVP do renderer: concluído
E2E PostgreSQL: validado
Coverage renderer: configurado
Produção: ainda pendente de S3/R2, observabilidade e política operacional
```

## 3.2 Motivação da fase

O renderer já responde à pergunta:

```text
Como gerar activos?
```

O Intelligence Engine deve começar a responder:

```text
Quando gerar?
Porquê gerar?
Que campanha recomendar?
Que oportunidade existe?
Qual é a prioridade?
Que acção faz sentido agora?
```

---

# 4. Escopo do MVP

## 4.1 Incluído no MVP

O MVP do FastAPI Intelligence Engine inclui:

```text
- serviço FastAPI separado;
- estrutura Python moderna;
- GET /health;
- autenticação interna por X-Internal-Token;
- validação de payloads com Pydantic;
- contratos versionados por payload_version;
- endpoint de campaign analysis;
- endpoint de scoring;
- endpoint de recommendations;
- endpoint de moment detection simples;
- regras heurísticas explicáveis;
- sem dependência obrigatória de IA generativa;
- logs estruturados sem secrets;
- erros normalizados;
- testes unitários;
- testes de integração HTTP;
- documentação;
- guia de integração com Backend Core.
```

## 4.2 Fora do escopo do MVP

Não implementar nesta fase:

```text
- LLM obrigatório;
- integração com OpenAI/Claude/outros modelos externos;
- scraping externo;
- ingestão automática de redes sociais;
- modelo ML treinado;
- vector database;
- embeddings;
- agent framework;
- LangChain/LlamaIndex;
- filas persistentes;
- base de dados própria;
- UI/frontend;
- geração de activos;
- chamada directa ao content_renderer;
- publicação em redes sociais;
- deploy produção;
- observabilidade completa;
- multi-tenant storage próprio.
```

---

# 5. Localização esperada

A localização recomendada do serviço é:

```text
intelligence_engine/
```

Estrutura sugerida:

```text
intelligence_engine/
  app/
    main.py
    api/
      routes.py
      health.py
      analysis.py
      scoring.py
      recommendations.py
      moments.py
    core/
      config.py
      security.py
      logging.py
      errors.py
    schemas/
      common.py
      campaign.py
      scoring.py
      recommendations.py
      moments.py
      responses.py
    services/
      campaign_analysis.py
      scoring_engine.py
      recommendation_engine.py
      moment_detector.py
      explanation.py
    rules/
      scoring_rules.py
      recommendation_rules.py
      moment_rules.py
    tests/
      ...
  docs/
    fundamentos/
      resultados/
  pyproject.toml
  README.md
  .env.example
```

A IA local deve adaptar esta estrutura ao padrão real do repositório, caso já exista uma convenção diferente.

---

# 6. Contratos internos esperados

## 6.1 Autenticação interna

Todos os endpoints internos, excepto `GET /health`, devem exigir:

```text
X-Internal-Token: <token-partilhado>
```

Regras:

```text
- token ausente → 403;
- token errado → 403;
- token vazio em production → erro de arranque;
- token nunca deve aparecer em logs;
- token nunca deve aparecer em respostas;
- comparação deve ser segura.
```

## 6.2 Headers recomendados

```text
X-Workspace-ID
X-Request-ID
X-Job-ID, quando aplicável
X-Internal-Token
```

## 6.3 Payload comum

Todos os payloads principais devem incluir:

```json
{
  "payload_version": "1.0",
  "workspace_id": "string",
  "request_id": "string",
  "entity": {
    "type": "campaign|artist|track|content_pack_request|report|media_kit",
    "id": "string"
  },
  "context": {},
  "data": {}
}
```

## 6.4 Resposta comum

As respostas devem ser estruturadas, explicáveis e sem ambiguidades:

```json
{
  "status": "completed",
  "engine": "intelligence_engine",
  "engine_version": "0.1.0",
  "request_id": "string",
  "workspace_id": "string",
  "result": {},
  "explanations": [],
  "warnings": [],
  "metadata": {}
}
```

## 6.5 Erro comum

```json
{
  "status": "failed",
  "error": {
    "code": "invalid_payload",
    "message": "Payload inválido.",
    "details": {}
  },
  "metadata": {
    "engine": "intelligence_engine",
    "engine_version": "0.1.0"
  }
}
```

---

# 7. Endpoints MVP

## 7.1 `GET /health`

Objectivo:

```text
Validar que o serviço está vivo.
```

Resposta esperada:

```json
{
  "status": "ok",
  "service": "intelligence_engine",
  "version": "0.1.0",
  "timestamp": "2026-06-24T00:00:00Z"
}
```

---

## 7.2 `POST /analysis/campaign`

Objectivo:

```text
Analisar uma campanha e devolver diagnóstico técnico estruturado.
```

Entrada esperada:

```json
{
  "payload_version": "1.0",
  "workspace_id": "ws-1",
  "request_id": "req-1",
  "entity": {
    "type": "campaign",
    "id": "campaign-1"
  },
  "data": {
    "campaign": {},
    "artist": {},
    "track": {},
    "smart_link_stats": {},
    "content_outputs": [],
    "previous_reports": []
  }
}
```

Saída esperada:

```json
{
  "status": "completed",
  "result": {
    "campaign_health": "good|warning|critical|unknown",
    "summary": "string",
    "strengths": [],
    "weaknesses": [],
    "opportunities": [],
    "risks": []
  },
  "explanations": []
}
```

---

## 7.3 `POST /scoring/campaign`

Objectivo:

```text
Calcular scores explicáveis para campanha, artista, faixa ou oportunidade.
```

Scores iniciais sugeridos:

```text
campaign_readiness_score
momentum_score
content_opportunity_score
risk_score
priority_score
```

Saída esperada:

```json
{
  "status": "completed",
  "result": {
    "scores": {
      "campaign_readiness_score": 72,
      "momentum_score": 64,
      "content_opportunity_score": 81,
      "risk_score": 28,
      "priority_score": 76
    },
    "grade": "A|B|C|D|unknown"
  },
  "explanations": [
    {
      "code": "high_content_opportunity",
      "message": "A campanha tem oportunidade relevante para novo conteúdo.",
      "weight": 0.3
    }
  ]
}
```

---

## 7.4 `POST /recommendations/campaign`

Objectivo:

```text
Recomendar acções de campanha com base nos dados recebidos.
```

Recomendações iniciais possíveis:

```text
create_release_post
create_story
create_milestone_post
create_weekly_growth_post
create_media_kit
create_report
improve_smart_link
wait_for_more_data
no_action
```

Saída esperada:

```json
{
  "status": "completed",
  "result": {
    "recommendations": [
      {
        "action": "create_release_post",
        "priority": "high",
        "confidence": 0.82,
        "reason": "A campanha tem sinais suficientes para activar conteúdo de lançamento.",
        "suggested_content_pack": "release_pack",
        "expected_outputs": [
          {
            "output_type": "post",
            "format": "post_1_1",
            "template_key": "release_card"
          }
        ]
      }
    ]
  },
  "explanations": []
}
```

---

## 7.5 `POST /moments/detect`

Objectivo:

```text
Detectar momentos simples que justifiquem uma acção de campanha.
```

Momentos MVP sugeridos:

```text
release_window
weekly_growth
milestone_reached
low_engagement
content_gap
report_due
media_kit_missing
smart_link_activity
```

Saída esperada:

```json
{
  "status": "completed",
  "result": {
    "moments": [
      {
        "type": "milestone_reached",
        "severity": "medium",
        "confidence": 0.74,
        "summary": "A faixa atingiu um marco relevante.",
        "recommended_action": "create_milestone_post"
      }
    ]
  },
  "explanations": []
}
```

---

# 8. Backlog técnico

---

# IE-001 — Criar fundação do serviço FastAPI Intelligence

## Objectivo

Criar a fundação técnica do serviço `intelligence_engine`.

## Tarefas

```text
Criar pasta do serviço.
Criar pyproject.toml ou requirements.txt, conforme padrão do repositório.
Configurar FastAPI.
Configurar Uvicorn.
Criar app/main.py.
Criar GET /health.
Criar .env.example.
Criar loader de configuração.
Criar logger estruturado.
Criar modelo de erro comum.
Criar README inicial.
Criar testes mínimos.
```

## Critérios de aceitação

```text
Serviço arranca localmente.
GET /health devolve 200.
Config carrega variáveis de ambiente.
Logger não expõe secrets.
Testes mínimos passam.
README explica instalação e execução.
```

---

# IE-002 — Configuração, segurança interna e erros normalizados

## Objectivo

Implementar autenticação interna e modelo comum de erros.

## Tarefas

```text
Implementar X-Internal-Token.
Permitir bypass apenas em test/dev explicitamente configurado, se necessário.
Rejeitar token vazio em production.
Criar middleware de autenticação.
Criar comparação segura.
Criar AppError ou equivalente.
Normalizar respostas 400/403/404/422/500.
Garantir que secrets são redigidos nos logs.
Criar testes de segurança.
```

## Critérios de aceitação

```text
Endpoint protegido rejeita token ausente.
Endpoint protegido rejeita token errado.
Endpoint protegido aceita token correcto.
Token não aparece em logs.
Erros seguem contrato comum.
Testes passam.
```

---

# IE-003 — Definir schemas Pydantic e contratos internos

## Objectivo

Definir os contratos de entrada e saída do Intelligence Engine.

## Tarefas

```text
Criar schemas comuns:
- EntityRef
- BaseIntelligenceRequest
- BaseIntelligenceResponse
- Explanation
- Warning
- ErrorResponse

Criar schemas de campaign analysis.
Criar schemas de scoring.
Criar schemas de recommendations.
Criar schemas de moments.
Adicionar payload_version.
Validar workspace_id/request_id/entity.
Garantir respostas tipadas.
Criar exemplos no README.
Criar testes de validação.
```

## Critérios de aceitação

```text
Payload inválido devolve 400/422 normalizado.
Payload válido é aceite.
Schemas são reutilizáveis.
OpenAPI reflecte contratos.
Testes cobrem casos válidos e inválidos.
```

---

# IE-004 — Implementar campaign analysis MVP

## Objectivo

Criar análise inicial de campanha com heurísticas simples e explicáveis.

## Tarefas

```text
Criar CampaignAnalysisService.
Ler dados de campaign, artist, track, smart_link_stats e content_outputs.
Calcular campaign_health.
Identificar strengths.
Identificar weaknesses.
Identificar opportunities.
Identificar risks.
Gerar summary.
Gerar explanations.
Criar endpoint POST /analysis/campaign.
Criar testes unitários.
Criar testes HTTP.
```

## Regras MVP sugeridas

```text
Sem dados suficientes → campaign_health unknown.
Campanha com content_outputs recentes → strength.
Campanha sem content_outputs → opportunity content_gap.
Smart link com actividade positiva → strength.
Smart link sem actividade → weakness ou warning.
Report ausente em período relevante → opportunity report_due.
Media kit ausente → opportunity media_kit_missing.
```

## Critérios de aceitação

```text
Endpoint devolve análise estruturada.
Resultado é determinístico.
Resultado inclui explanations.
Não usa IA generativa.
Não depende de chamadas externas.
Testes passam.
```

---

# IE-005 — Implementar scoring engine MVP

## Objectivo

Calcular scores simples, determinísticos e explicáveis.

## Tarefas

```text
Criar ScoringEngine.
Implementar campaign_readiness_score.
Implementar momentum_score.
Implementar content_opportunity_score.
Implementar risk_score.
Implementar priority_score.
Implementar grade A/B/C/D/unknown.
Criar endpoint POST /scoring/campaign.
Criar explanations por score.
Criar testes unitários.
Criar testes HTTP.
```

## Regras MVP sugeridas

```text
Scores devem ir de 0 a 100.
Sem dados suficientes → score null ou unknown.
Cada score deve ter explanation.
Score não deve depender de modelo externo.
Pesos devem estar documentados.
```

## Critérios de aceitação

```text
Scores são calculados de forma consistente.
Scores têm explicação.
Payload incompleto é tratado sem 500.
Testes cobrem dados bons, fracos e ausentes.
```

---

# IE-006 — Implementar recommendation engine MVP

## Objectivo

Gerar recomendações de campanha com prioridade, confiança e justificação.

## Tarefas

```text
Criar RecommendationEngine.
Mapear scores/moments para acções recomendadas.
Implementar recomendações:
- create_release_post
- create_story
- create_milestone_post
- create_weekly_growth_post
- create_media_kit
- create_report
- improve_smart_link
- wait_for_more_data
- no_action

Criar endpoint POST /recommendations/campaign.
Gerar suggested_content_pack quando aplicável.
Gerar expected_outputs quando aplicável.
Gerar confidence.
Gerar priority.
Criar testes unitários.
Criar testes HTTP.
```

## Critérios de aceitação

```text
Endpoint devolve lista de recomendações.
Cada recomendação tem action, priority, confidence e reason.
Recomendação pode sugerir content_pack.
Recomendação não cria entidades no Django.
Resultado é explicável.
Testes passam.
```

---

# IE-007 — Implementar moment detection MVP

## Objectivo

Detectar momentos simples que justifiquem acção de campanha.

## Tarefas

```text
Criar MomentDetector.
Detectar release_window.
Detectar weekly_growth.
Detectar milestone_reached.
Detectar low_engagement.
Detectar content_gap.
Detectar report_due.
Detectar media_kit_missing.
Detectar smart_link_activity.
Criar endpoint POST /moments/detect.
Criar confidence por momento.
Criar severity por momento.
Criar recommended_action por momento.
Criar testes unitários.
Criar testes HTTP.
```

## Critérios de aceitação

```text
Momentos são detectados de forma determinística.
Cada momento tem type, severity, confidence e summary.
Não há scraping externo.
Não há chamadas a APIs externas.
Testes passam.
```

---

# IE-008 — Integrar análise, scoring, moments e recommendations num endpoint composto

## Objectivo

Criar endpoint composto para o Django obter diagnóstico completo numa chamada.

## Endpoint sugerido

```text
POST /intelligence/campaign
```

## Tarefas

```text
Criar IntelligenceOrchestrator.
Executar analysis.
Executar scoring.
Executar moment detection.
Executar recommendations.
Agregar resposta.
Gerar summary executivo.
Gerar explanations consolidadas.
Criar warnings quando dados forem insuficientes.
Criar testes unitários.
Criar testes HTTP.
```

## Saída esperada

```json
{
  "status": "completed",
  "result": {
    "analysis": {},
    "scores": {},
    "moments": [],
    "recommendations": [],
    "summary": "string"
  },
  "explanations": [],
  "warnings": []
}
```

## Critérios de aceitação

```text
Endpoint composto funciona.
Falha parcial controlada não gera 500 indevido.
Warnings indicam dados insuficientes.
Resultado é estável e explicável.
Testes passam.
```

---

# IE-009 — Preparar contrato Backend Core ↔ Intelligence Engine

## Objectivo

Documentar e preparar a integração entre Django e FastAPI Intelligence Engine.

## Tarefas

```text
Criar documento de contrato.
Definir payloads enviados pelo Django.
Definir respostas esperadas.
Definir headers.
Definir códigos de erro.
Definir timeout.
Definir retry no lado Django, se aplicável.
Definir se chamadas são síncronas ou via ExternalJobReference.
Definir se resultados ficam persistidos no Django.
Criar exemplos de request/response.
Criar checklist de integração.
```

## Decisão importante

A IA local deve analisar o Backend Core e propor a melhor opção:

```text
Opção A: chamadas síncronas internas para insights rápidos.
Opção B: ExternalJobReference para análises longas.
Opção C: híbrido.
```

## Recomendação inicial

```text
MVP: chamadas síncronas internas para analysis/scoring/recommendations.
Futuro: ExternalJobReference para análises pesadas.
```

## Critérios de aceitação

```text
Contrato documentado.
Timeout definido.
Erros documentados.
Exemplos criados.
Decisão síncrono vs job externo registada.
```

---

# IE-010 — Testes, qualidade e documentação final

## Objectivo

Fechar a fase com validações e documentação úteis.

## Tarefas

```text
Garantir testes unitários.
Garantir testes HTTP.
Garantir lint/typecheck, se configurado.
Adicionar coverage, se fizer sentido.
Actualizar README.
Criar docs/fundamentos/05_estado_intelligence_engine_engine.md.
Criar relatórios de execução dos prompts.
Documentar limitações.
Documentar próximos passos.
Confirmar ausência de secrets.
```

## Validações mínimas

```text
pytest
ruff ou lint equivalente, se configurado
mypy ou pyright, se configurado
uvicorn smoke test
GET /health
POST endpoints principais
```

## Critérios de aceitação

```text
Testes passam.
Documentação final existe.
Limitações estão explícitas.
Sem secrets em docs.
Estado final indica pronto/não pronto para integração.
```

---

# 9. Critérios de aceitação da fase

A fase FastAPI Intelligence Engine MVP fica concluída quando:

```text
Serviço FastAPI arranca localmente.
GET /health funciona.
Autenticação interna funciona.
Schemas Pydantic validam payloads.
Erros são normalizados.
Campaign analysis funciona.
Scoring funciona.
Recommendations funcionam.
Moment detection funciona.
Endpoint composto funciona.
Resultados são explicáveis.
Não há dependência obrigatória de IA generativa.
Não há scraping externo.
Testes passam.
README e documento de estado existem.
Contrato Backend Core ↔ Intelligence Engine está documentado.
```

---

# 10. Critérios de não aceitação

A fase não deve ser aceite se:

```text
Serviço não arranca.
Endpoints protegidos aceitam chamadas sem token.
Payload inválido causa 500.
Scores são opacos ou sem explicação.
Recomendações são aleatórias.
Há chamadas externas não documentadas.
Há secrets em logs ou docs.
Backend Core é bypassado em regras de produto.
Intelligence Engine cria estado próprio de produto.
Testes principais não passam.
Documentação não reflecte o estado real.
```

---

# 11. Riscos

| ID         | Risco                                                                 |    Impacto | Mitigação                                              |
| ---------- | --------------------------------------------------------------------- | ---------: | ------------------------------------------------------ |
| IE-RSK-001 | Intelligence Engine assumir regras de produto do Django.              |       Alto | Reforçar tese arquitectural nos prompts.               |
| IE-RSK-002 | Scores parecerem objectivos, mas serem heurísticos fracos.            | Médio/Alto | Explicar regras, pesos e limites.                      |
| IE-RSK-003 | MVP tentar usar IA generativa cedo demais.                            |      Médio | Começar com heurísticas determinísticas.               |
| IE-RSK-004 | Payloads do Django não estarem suficientemente definidos.             |       Alto | Criar contrato antes da integração.                    |
| IE-RSK-005 | Recomendações gerarem acções não suportadas pelo renderer.            |      Médio | Mapear apenas para content packs/templates existentes. |
| IE-RSK-006 | Endpoint composto ficar demasiado grande.                             |      Médio | Manter services separados e orchestration simples.     |
| IE-RSK-007 | Falta de dados reais limitar utilidade dos insights.                  |      Médio | Tratar dados insuficientes com warnings e `unknown`.   |
| IE-RSK-008 | Acoplamento excessivo ao formato actual de campaign/report/media kit. |      Médio | Usar payload_version e schemas explícitos.             |

---

# 12. Decisões pendentes

## IE-PDEC-001 — Chamada síncrona ou job externo

```text
Estado: pendente
```

### Questão

O Backend Core deve chamar o Intelligence Engine de forma síncrona ou via `ExternalJobReference`?

### Recomendação inicial

```text
MVP: síncrono para análises rápidas.
Futuro: job externo para análises pesadas.
```

---

## IE-PDEC-002 — Persistência dos resultados

```text
Estado: pendente
```

### Questão

Os resultados de intelligence devem ser persistidos no Django ou apenas devolvidos em tempo real?

### Recomendação inicial

```text
MVP: devolver em tempo real.
Depois: persistir snapshots de insights relevantes no Django.
```

---

## IE-PDEC-003 — Uso de IA generativa

```text
Estado: pendente
```

### Questão

Quando introduzir IA generativa?

### Recomendação inicial

```text
Não usar IA generativa no MVP.
Começar com heurísticas explicáveis.
Introduzir LLM apenas depois de haver contratos, métricas e avaliação.
```

---

## IE-PDEC-004 — Fonte de dados para scores

```text
Estado: pendente
```

### Questão

Que dados entram no score inicial?

### Recomendação inicial

```text
campaign;
artist;
track;
smart_link_stats;
content_outputs;
reports;
media_kits;
eventos ou milestones, quando existirem.
```

---

# 13. Ordem recomendada de execução

Executar em sequência:

```text
1. IE-001 — Fundação do serviço FastAPI Intelligence
2. IE-002 — Configuração, segurança e erros
3. IE-003 — Schemas Pydantic e contratos internos
4. IE-004 — Campaign analysis MVP
5. IE-005 — Scoring engine MVP
6. IE-006 — Recommendation engine MVP
7. IE-007 — Moment detection MVP
8. IE-008 — Endpoint composto
9. IE-009 — Contrato Backend Core ↔ Intelligence Engine
10. IE-010 — Testes, qualidade e documentação final
```

---

# 14. Relação com fases futuras

## 14.1 Relação com Renderer

O Intelligence Engine pode recomendar:

```text
- content_pack;
- expected_outputs;
- template_key;
- acção de campanha.
```

Mas **não deve chamar directamente o renderer no MVP**.

Fluxo recomendado:

```text
Intelligence Engine recomenda.
Django decide/cria job.
Renderer gera activos.
Django persiste estado.
```

## 14.2 Relação com Frontend

O futuro frontend deve consumir intelligence através do Django, não directamente através do Intelligence Engine.

Fluxo recomendado:

```text
Frontend → Django → Intelligence Engine → Django → Frontend
```

## 14.3 Relação com S3/R2

S3/R2 não bloqueia o Intelligence Engine, porque o Intelligence Engine não gera ficheiros no MVP.

## 14.4 Relação com Observabilidade

Observabilidade completa não é obrigatória no MVP, mas logs estruturados e métricas básicas devem ser consideradas para fases futuras.

---

# 15. Resultado esperado

Ao concluir esta fase, o projecto deve passar de:

```text
Sistema que gera activos a partir de jobs
```

para:

```text
Sistema que também recomenda quando e porquê gerar activos
```

Estado esperado:

```text
Pronto para integração com Backend Core: sim
Pronto para piloto técnico: sim
Pronto para produção: ainda depende das pendências globais de produção
```

---

# 16. Próximo passo após este backlog

Após este backlog, criar uma pipeline de prompts compatível com o Assistente Desktop para executar a implementação do FastAPI Intelligence Engine.

Ficheiro de pipeline recomendado:

```text
docs\fundamentos\pipelines\04_pipeline_intelligence_engine_engine.md
```

Ou, mantendo o padrão actual:

```text
docs\fundamentos\04_pipeline_intelligence_engine_engine.md
```

Recomendação:

```text
Criar a pipeline com 8 a 10 prompts, usando opus para arquitectura/contratos/core logic e sonnet para documentação/limpeza final.
```
