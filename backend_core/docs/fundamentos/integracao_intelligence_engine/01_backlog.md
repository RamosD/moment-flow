# Backlog: Integração Backend Core ↔ Intelligence Engine

# MomentFlow / ChartRex — Integração Backend Core ↔ FastAPI Intelligence Engine

## 1. Objectivo do documento

Este documento define o backlog técnico e funcional para integrar o **Backend Core Django** com o **FastAPI Intelligence Engine**.

A fase anterior concluiu o MVP do `intelligence_engine`, incluindo:

```text
- serviço FastAPI separado;
- GET /health;
- autenticação interna por X-Internal-Token;
- configuração e erros normalizados;
- schemas Pydantic e contratos internos;
- POST /analysis/campaign;
- POST /scoring/campaign;
- POST /recommendations/campaign;
- POST /moments/detect;
- POST /intelligence/campaign;
- contrato Backend Core ↔ Intelligence Engine;
- documentação final;
- validação com 197 testes aprovados;
- lint aprovado.
```

A próxima fase deve ligar o Django ao endpoint composto:

```text
POST /intelligence/campaign
```

usando chamada interna síncrona no MVP.

---

## 2. Tese arquitectural

A tese mantém-se:

```text
Django governa o produto.
Renderer gera activos.
FastAPI Intelligence calcula, recomenda e detecta oportunidades.
Frontend orquestra a experiência do utilizador.
```

## 2.1 Responsabilidade do Backend Core

O Backend Core continua responsável por:

```text
- autenticação de utilizadores;
- autorização/RBAC;
- workspaces;
- campanhas;
- catálogo musical;
- smart links;
- reports;
- media kits;
- content outputs;
- billing/créditos;
- estado de produto;
- audit;
- persistência;
- orquestração.
```

## 2.2 Responsabilidade do Intelligence Engine

O Intelligence Engine é responsável por:

```text
- analisar payloads técnicos enviados pelo Django;
- calcular scores;
- detectar momentos;
- gerar recomendações;
- devolver insights explicáveis;
- não persistir estado de produto;
- não chamar o renderer;
- não decidir regras de produto.
```

---

## 3. Estado actual

```text
FastAPI Intelligence Engine MVP: concluído
Backend Core ↔ Intelligence Engine: por implementar
Contrato de integração: documentado
Modelo recomendado: síncrono no MVP
ExternalJobReference: reservado para análises futuras pesadas
Produção: ainda pendente de observabilidade, calibração e decisões operacionais
```

---

# 4. Escopo da integração MVP

## 4.1 Incluído

A integração MVP inclui:

```text
- ler o contrato Backend Core ↔ Intelligence Engine;
- configurar URL e timeout do Intelligence Engine no Backend Core;
- reutilizar ou adaptar InternalServiceClient existente;
- criar client síncrono para chamadas ao Intelligence Engine;
- criar adapter/builder do data bundle de campanha;
- recolher dados reais dos modelos Django;
- chamar POST /intelligence/campaign;
- expor serviço interno/use-case no Backend Core;
- expor endpoint API para obter intelligence de uma campanha;
- garantir workspace/RBAC;
- tratar timeout, indisponibilidade, erro 4xx/5xx e payload inválido;
- devolver resposta normalizada ao frontend/consumidor;
- criar testes unitários;
- criar testes de integração com mock HTTP;
- documentar a integração;
- criar relatório final da execução.
```

## 4.2 Fora do escopo

Não implementar nesta fase:

```text
- alteração no runtime do intelligence_engine;
- integração assíncrona via ExternalJobReference;
- callbacks do Intelligence Engine para o Django;
- persistência obrigatória de snapshots de insights;
- IA generativa;
- scraping externo;
- recolha real de métricas externas;
- frontend;
- chamada directa do Intelligence Engine para o renderer;
- geração automática de content packs;
- consumo de créditos;
- deploy produção;
- observabilidade completa.
```

---

# 5. Caminhos relevantes

## Backend Core

```text
momentflow\backend_core
```

## Intelligence Engine

```text
momentflow\intelligence_engine
```

## Content Renderer

```text
momentflow\content_renderer
```

## Contrato de integração

```text
momentflow\intelligence_engine\docs\gestao\fundamentos\contrato_backend_core_intelligence_engine.md
```

## Backlog desta fase

```text
momentflow\backend_core\docs\gestao\fundamentos\backlog_integracao_intelligence_engine.md
```

## Resultados desta fase

```text
momentflow\backend_core\docs\gestao\fundamentos\resultados
```

---

# 6. Decisão técnica principal

## 6.1 Modelo recomendado

```text
MVP: chamada síncrona interna do Backend Core para o Intelligence Engine.
Futuro: ExternalJobReference apenas para análises pesadas ou recolha assíncrona.
```

## 6.2 Justificação

O Intelligence Engine MVP é determinístico, sem I/O externo, sem scraping, sem persistência e sem IA generativa obrigatória. Logo, a chamada síncrona é suficiente e mais simples para o MVP.

## 6.3 Fluxo alvo

```text
Frontend ou consumidor interno
  → Backend Core Django
    → valida permissões/workspace
    → recolhe dados reais
    → monta data bundle
    → chama Intelligence Engine
    → recebe analysis/scoring/moments/recommendations
    → devolve resposta ao consumidor
```

## 6.4 Fluxo que não deve ser implementado no MVP

```text
Backend Core
  → ExternalJobReference
    → Intelligence Engine /jobs
      → callback para Backend Core
```

Este fluxo fica reservado para trabalhos futuros pesados.

---

# 7. Contrato esperado com o Intelligence Engine

## 7.1 Endpoint principal

```text
POST /intelligence/campaign
```

## 7.2 Headers

```text
X-Internal-Token: <token configurado>
X-Workspace-ID: <workspace_id>
X-Request-ID: <request_id>
```

Opcionalmente:

```text
X-Campaign-ID: <campaign_id>
```

## 7.3 Payload base

```json
{
  "payload_version": "1.0",
  "workspace_id": "string",
  "request_id": "string",
  "entity": {
    "type": "campaign",
    "id": "string"
  },
  "context": {
    "reference_date": "YYYY-MM-DD"
  },
  "data": {
    "campaign": {},
    "artist": {},
    "track": {},
    "smart_link_stats": {},
    "content_outputs": [],
    "reports": [],
    "media_kits": []
  }
}
```

## 7.4 Resposta esperada

```json
{
  "status": "completed",
  "engine": "fastapi_intelligence",
  "engine_version": "0.1.0",
  "request_id": "string",
  "workspace_id": "string",
  "result": {
    "analysis": {},
    "scores": {},
    "grade": "A|B|C|D|unknown",
    "moments": [],
    "recommendations": [],
    "summary": "string"
  },
  "explanations": [],
  "warnings": [],
  "metadata": {}
}
```

---

# 8. Estratégia de persistência no MVP

## 8.1 Decisão recomendada

```text
Não persistir snapshots de intelligence no MVP.
Devolver resultado em tempo real.
```

## 8.2 Justificação

A integração inicial deve validar o contrato e a utilidade do serviço sem introduzir novo modelo de dados.

## 8.3 Evolução futura

Persistência pode ser adicionada depois com um modelo como:

```text
CampaignIntelligenceSnapshot
```

Campos possíveis:

```text
workspace
campaign
request_id
payload_version
engine_version
summary
scores
grade
moments
recommendations
warnings
raw_response
created_at
```

---

# 9. Backlog técnico

---

# BC-IE-001 — Analisar contrato, estado actual e pontos de integração

## Objectivo

Inspeccionar o `backend_core`, o contrato do `intelligence_engine` e os padrões existentes de integração para preparar a implementação.

## Tarefas

```text
Ler o contrato Backend Core ↔ Intelligence Engine.
Ler o relatório final do Intelligence Engine, se disponível.
Inspeccionar apps relevantes no backend_core:
- campaigns;
- catalogue;
- links;
- content;
- reports;
- integrations_bridge;
- workspaces;
- permissions/RBAC.

Identificar InternalServiceClient existente.
Identificar settings existentes para serviços externos.
Identificar padrões de timeout, retry, dry-run e erros.
Identificar serializers/views/services existentes para Campaign.
Confirmar como obter workspace actual.
Confirmar como aplicar permissões.
Confirmar rotas/API existentes para campanhas.
Definir plano de implementação.
Não alterar código nesta tarefa, salvo documentação de plano se necessário.
```

## Critérios de aceitação

```text
Plano técnico criado.
Ficheiros prováveis a alterar identificados.
Decisão síncrona vs assíncrona confirmada para MVP.
Riscos de integração listados.
Dependências e dúvidas documentadas.
Relatório criado em docs/gestao/fundamentos/resultados.
```

---

# BC-IE-002 — Configurar settings do Intelligence Engine no Backend Core

## Objectivo

Adicionar ou consolidar configurações necessárias para o Django chamar o Intelligence Engine.

## Variáveis esperadas

```text
INTELLIGENCE_ENGINE_BASE_URL
INTELLIGENCE_ENGINE_TIMEOUT_SECONDS
INTELLIGENCE_ENGINE_INTERNAL_TOKEN
INTELLIGENCE_ENGINE_ENABLED
INTELLIGENCE_ENGINE_DRY_RUN
```

Se já existirem variáveis equivalentes, reutilizar o padrão existente em vez de duplicar.

## Tarefas

```text
Verificar settings.py/config actual.
Adicionar variáveis necessárias.
Garantir defaults seguros para desenvolvimento.
Garantir que produção não aceita token vazio.
Garantir que .env.example não contém secrets reais.
Documentar variáveis.
Actualizar testes de configuração, se existirem.
```

## Critérios de aceitação

```text
Settings do Intelligence Engine existem.
Valores são configuráveis por ambiente.
Token real não é versionado.
Produção não permite configuração insegura.
.env.example actualizado com placeholders seguros.
Testes/config checks passam.
```

---

# BC-IE-003 — Criar ou adaptar client síncrono para o Intelligence Engine

## Objectivo

Implementar client interno reutilizável para chamadas síncronas ao Intelligence Engine.

## Tarefas

```text
Reutilizar InternalServiceClient existente, se adequado.
Caso contrário, criar IntelligenceEngineClient pequeno e alinhado ao padrão do projecto.
Implementar chamada POST /intelligence/campaign.
Enviar headers:
- X-Internal-Token;
- X-Workspace-ID;
- X-Request-ID.

Aplicar timeout configurável.
Tratar respostas:
- 200 completed;
- 400/422 invalid_payload;
- 403 unauthorized_internal_request;
- 5xx internal_error;
- timeout;
- indisponibilidade;
- JSON inválido.

Nunca logar token.
Criar erros internos tipados.
Garantir logs úteis sem secrets.
Criar testes com mock HTTP.
```

## Critérios de aceitação

```text
Client chama POST /intelligence/campaign.
Timeout é aplicado.
Erros são normalizados no lado Django.
Token não aparece em logs.
Testes cobrem sucesso, timeout, 403, 422, 5xx e JSON inválido.
```

---

# BC-IE-004 — Criar builder do data bundle de campanha

## Objectivo

Criar adapter que monta o payload esperado pelo Intelligence Engine a partir dos modelos reais do Django.

## Dados a recolher

```text
Campaign
Artist
Track
SmartLink
SmartLinkClick / estatísticas agregadas
ContentOutput
Report
MediaKit
CampaignGoal, se existir
```

## Tarefas

```text
Criar CampaignIntelligencePayloadBuilder ou equivalente.
Receber campaign e workspace.
Validar que a campanha pertence ao workspace.
Montar envelope:
- payload_version;
- workspace_id;
- request_id;
- entity;
- context;
- data.

Montar data.campaign.
Montar data.artist.
Montar data.track.
Montar data.smart_link_stats.
Montar data.content_outputs.
Montar data.reports.
Montar data.media_kits.
Montar goals/milestones se existirem.
Garantir serialização JSON-safe de datas, UUIDs, decimals e enums.
Evitar queries N+1.
Usar select_related/prefetch_related quando aplicável.
Lidar com dados ausentes sem falhar.
Criar testes unitários com factories ou fixtures existentes.
```

## Critérios de aceitação

```text
Builder gera payload compatível com o contrato do Intelligence Engine.
Payload inclui payload_version 1.0.
Payload inclui workspace_id, request_id e entity campaign.
Datas são serializadas em ISO.
Dados ausentes geram payload válido.
Não há queries excessivas óbvias.
Testes cobrem campanha rica, campanha mínima e campanha sem dados relacionados.
```

---

# BC-IE-005 — Criar serviço de domínio para intelligence de campanha

## Objectivo

Criar serviço Django que orquestra builder + client e devolve o resultado de intelligence para uma campanha.

## Tarefas

```text
Criar CampaignIntelligenceService ou equivalente.
Receber campaign_id, workspace, request/user context.
Carregar campanha com segurança.
Validar workspace.
Montar payload com o builder.
Chamar IntelligenceEngineClient.
Tratar dry-run, se configurado.
Tratar serviço desactivado, se configurado.
Tratar timeout e indisponibilidade.
Mapear resposta do Intelligence Engine para formato interno.
Não persistir snapshot no MVP, salvo se já existir modelo adequado e decisão explícita.
Criar testes unitários com client mockado.
```

## Critérios de aceitação

```text
Serviço devolve intelligence de campanha com sucesso.
Serviço falha de forma controlada quando campanha não existe.
Serviço falha de forma controlada quando workspace não corresponde.
Serviço trata timeout/5xx sem crash.
Dry-run, se configurado, devolve resposta previsível e documentada.
Testes passam.
```

---

# BC-IE-006 — Expor endpoint API no Backend Core

## Objectivo

Disponibilizar endpoint no Backend Core para obter intelligence de uma campanha.

## Rota sugerida

A IA local deve adaptar ao padrão real do projecto. Sugestão:

```text
POST /api/campaigns/{campaign_id}/intelligence/
```

ou

```text
GET /api/campaigns/{campaign_id}/intelligence/
```

## Recomendação

Usar `POST` se a chamada aceita parâmetros/contexto ou pode disparar cálculo remoto. Usar `GET` apenas se o projecto tratar isto como leitura pura sem body.

## Tarefas

```text
Identificar viewset/router de campanhas.
Adicionar action ou endpoint dedicado.
Garantir autenticação de utilizador.
Garantir permissão/RBAC.
Garantir escopo por workspace.
Chamar CampaignIntelligenceService.
Devolver resposta normalizada.
Tratar erros:
- campanha não encontrada;
- sem permissão;
- Intelligence Engine desactivado;
- timeout;
- serviço indisponível;
- payload inválido;
- erro inesperado.

Criar serializer de resposta, se o padrão do projecto exigir.
Criar testes API.
Actualizar OpenAPI/schema, se aplicável.
```

## Critérios de aceitação

```text
Endpoint existe e está protegido.
Utilizador sem permissão não consegue aceder.
Campanha fora do workspace não é exposta.
Endpoint chama o serviço de intelligence.
Resposta inclui analysis, scores, moments, recommendations e summary.
Erros são previsíveis e testados.
OpenAPI/schema actualizado, se aplicável.
```

---

# BC-IE-007 — Implementar política de timeout, retry e fallback

## Objectivo

Definir comportamento operacional mínimo quando o Intelligence Engine falha.

## Tarefas

```text
Definir timeout default.
Definir política de retry para chamadas síncronas.
Recomendação:
- retry curto apenas para timeout/unavailable/5xx, se já houver padrão no projecto;
- não fazer retry em 4xx;
- não fazer retry longo em request HTTP do utilizador.

Garantir fallback controlado quando o serviço está indisponível.
Definir mensagens de erro.
Definir logs estruturados.
Garantir que erros não expõem secrets.
Criar testes para timeout, 5xx, 422 e 403.
```

## Critérios de aceitação

```text
Timeout configurável.
4xx não é retentado.
Timeout/5xx são tratados com erro controlado.
Resposta ao cliente não expõe detalhes internos sensíveis.
Logs ajudam diagnóstico sem expor token.
Testes passam.
```

---

# BC-IE-008 — Validar integração com mocks HTTP

## Objectivo

Garantir que o Backend Core integra correctamente com o Intelligence Engine sem depender de serviço real em todos os testes.

## Tarefas

```text
Criar testes com mock HTTP ou monkeypatch do client.
Cobrir resposta completed.
Cobrir warnings.
Cobrir recommendations.
Cobrir moments.
Cobrir scores unknown.
Cobrir timeout.
Cobrir 403 do serviço interno.
Cobrir 422 invalid_payload.
Cobrir 5xx.
Cobrir JSON inválido.
Validar que token não é logado.
Validar request_id propagado.
Validar workspace_id propagado.
```

## Critérios de aceitação

```text
Testes de integração com mock passam.
Cenários de erro estão cobertos.
Headers internos são enviados.
Payload enviado ao IE é compatível.
Resposta do Backend Core é estável.
```

---

# BC-IE-009 — Validar loop real Backend Core ↔ Intelligence Engine

## Objectivo

Executar uma validação manual ou automatizada com os dois serviços reais em execução.

## Pré-condições

```text
Backend Core a correr localmente.
Intelligence Engine a correr localmente.
INTERNAL_API_TOKEN alinhado nos dois serviços.
Campanha de teste existente no Backend Core.
```

## Tarefas

```text
Arrancar Intelligence Engine.
Arrancar Backend Core.
Configurar INTELLIGENCE_ENGINE_BASE_URL.
Configurar INTELLIGENCE_ENGINE_INTERNAL_TOKEN.
Executar chamada ao endpoint Django.
Confirmar chamada real ao Intelligence Engine.
Confirmar resposta com analysis, scores, moments e recommendations.
Confirmar logs sem token.
Confirmar comportamento com IE desligado.
Registar evidências.
```

## Critérios de aceitação

```text
Backend Core chama Intelligence Engine real.
Resposta é devolvida ao consumidor.
Falha com IE desligado é tratada de forma controlada.
Logs não expõem token.
Evidência documentada em relatório.
```

---

# BC-IE-010 — Documentar integração e estado final

## Objectivo

Fechar a fase com documentação final, estado honesto e próximos passos.

## Tarefas

```text
Actualizar documentação do Backend Core.
Criar ou actualizar documento:
docs/gestao/fundamentos/estado_integracao_intelligence_engine.md

Documentar:
- arquitectura da integração;
- variáveis de ambiente;
- endpoint Django;
- payload enviado ao IE;
- resposta recebida;
- tratamento de erros;
- timeout/retry;
- limitações;
- testes executados;
- pendências;
- pronto/não pronto para piloto;
- pronto/não pronto para produção.

Criar relatório final em:
docs/gestao/fundamentos/resultados/prompt_final_integracao_intelligence_engine.md
```

## Critérios de aceitação

```text
Documento de estado existe.
README/docs relevantes foram actualizados.
Relatório final existe.
Testes e validações estão documentados.
Pendências estão claras.
Estado final é honesto.
```

---

# 10. Critérios de aceitação da fase

A integração Backend Core ↔ Intelligence Engine fica concluída quando:

```text
Backend Core consegue chamar POST /intelligence/campaign.
Payload é montado a partir dos modelos reais.
Workspace e permissões são respeitados.
Endpoint Django existe e está protegido.
Resposta devolve analysis, scores, moments, recommendations e summary.
Timeout/indisponibilidade são tratados.
Token não aparece em logs.
Testes unitários passam.
Testes API passam.
Validação com mock HTTP passa.
Validação com serviço real é executada ou limitação documentada.
Documentação final existe.
```

---

# 11. Critérios de não aceitação

A fase não deve ser aceite se:

```text
Backend Core expõe intelligence sem validar workspace.
Backend Core expõe intelligence sem RBAC/permissão.
Token interno aparece em logs.
Payload enviado ao IE não segue contrato.
Endpoint depende de dados mockados em runtime normal.
Timeout do IE causa crash ou resposta 500 não controlada.
4xx do IE é tratado como sucesso.
Intelligence Engine é alterado sem necessidade.
Renderer é chamado directamente pelo Intelligence Engine ou pelo builder.
ExternalJobReference é usado indevidamente no MVP síncrono.
Testes principais não passam.
Documentação final omite pendências relevantes.
```

---

# 12. Riscos

| ID            | Risco                                                              |    Impacto | Mitigação                                                  |
| ------------- | ------------------------------------------------------------------ | ---------: | ---------------------------------------------------------- |
| BC-IE-RSK-001 | Divergência entre scaffolding assíncrono existente e MVP síncrono. |       Alto | Registar decisão explícita e isolar integração síncrona.   |
| BC-IE-RSK-002 | Builder montar payload incompleto ou incompatível com o IE.        |       Alto | Testes de contrato e payload fixtures.                     |
| BC-IE-RSK-003 | Workspace/RBAC mal aplicado expor dados de campanha.               |    Crítico | Testes de permissão e isolamento por workspace.            |
| BC-IE-RSK-004 | Timeout do IE degradar UX.                                         | Médio/Alto | Timeout curto, erro controlado e logs.                     |
| BC-IE-RSK-005 | Erros do IE vazarem detalhes internos.                             |      Médio | Mapear erros para resposta segura no Django.               |
| BC-IE-RSK-006 | Payload gerar queries N+1.                                         |      Médio | select_related/prefetch_related e testes/perfil simples.   |
| BC-IE-RSK-007 | Decisão de não persistir snapshots dificultar histórico.           |      Médio | Aceitar no MVP; planear snapshot futuro.                   |
| BC-IE-RSK-008 | Heurísticas ainda não calibradas parecerem definitivas.            |      Médio | Mostrar explanations/warnings e evitar linguagem absoluta. |

---

# 13. Decisões pendentes

## BC-IE-PDEC-001 — Endpoint Django: GET ou POST

```text
Estado: pendente
Recomendação: POST
```

Usar `POST` se a chamada representa cálculo remoto, pode aceitar contexto e não deve ser cacheada automaticamente.

---

## BC-IE-PDEC-002 — Persistência de snapshots

```text
Estado: pendente
Recomendação MVP: não persistir
```

No MVP, devolver em tempo real. Persistência pode entrar depois se houver necessidade de histórico, auditoria ou comparação temporal.

---

## BC-IE-PDEC-003 — Reutilizar ExternalJobReference ou caminho síncrono novo

```text
Estado: pendente
Recomendação MVP: caminho síncrono novo/reutilizando client interno
```

`ExternalJobReference` fica para análises longas ou assíncronas futuras.

---

## BC-IE-PDEC-004 — Política exacta de retry

```text
Estado: pendente
Recomendação MVP: timeout curto, no máximo retry simples em falhas transitórias se já houver padrão
```

Evitar retries longos durante request HTTP do utilizador.

---

# 14. Ordem recomendada de execução

Executar em sequência:

```text
1. BC-IE-001 — Analisar contrato, estado actual e pontos de integração
2. BC-IE-002 — Configurar settings do Intelligence Engine
3. BC-IE-003 — Criar ou adaptar client síncrono
4. BC-IE-004 — Criar builder do data bundle de campanha
5. BC-IE-005 — Criar serviço de domínio para intelligence de campanha
6. BC-IE-006 — Expor endpoint API no Backend Core
7. BC-IE-007 — Implementar política de timeout, retry e fallback
8. BC-IE-008 — Validar integração com mocks HTTP
9. BC-IE-009 — Validar loop real Backend Core ↔ Intelligence Engine
10. BC-IE-010 — Documentar integração e estado final
```

---

# 15. Relação com fases futuras

## 15.1 Frontend

Depois desta integração, o frontend deve consumir intelligence através do Backend Core, não directamente através do Intelligence Engine.

Fluxo recomendado:

```text
Frontend → Backend Core → Intelligence Engine → Backend Core → Frontend
```

## 15.2 Renderer

A integração não deve chamar o renderer directamente.

Fluxo correcto:

```text
Intelligence recomenda.
Backend Core decide.
Backend Core cria content pack/job, se aplicável.
Renderer gera activos.
```

## 15.3 S3/R2

S3/R2 não bloqueia esta integração, porque a fase não gera novos assets.

## 15.4 Observabilidade

Observabilidade completa não bloqueia o MVP, mas devem existir logs suficientes para diagnosticar:

```text
request_id
workspace_id
campaign_id
tempo de chamada ao IE
status da resposta
tipo de erro
```

Sem expor token.

---

# 16. Resultado esperado

Ao concluir esta fase, o projecto deve passar de:

```text
Intelligence Engine isolado e validado
```

para:

```text
Backend Core capaz de consultar intelligence real de campanhas
```

Estado esperado:

```text
Pronto para integração funcional: sim
Pronto para piloto técnico: sim
Pronto para produção: ainda não, salvo resolução de observabilidade, calibração e política operacional
```

---

