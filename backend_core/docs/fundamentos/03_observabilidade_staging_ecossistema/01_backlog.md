# Backlog: Observabilidade e Staging do Ecossistema

# MomentFlow / ChartRex — Observabilidade e Staging Técnico do Ecossistema

## 1. Objectivo do documento

Este documento define o backlog técnico da fase **Observabilidade e Staging Técnico do Ecossistema**.

A fase anterior concluiu a integração:

```text
Backend Core ↔ FastAPI Intelligence Engine
```

O projecto tem agora três componentes principais funcionais:

```text
backend_core
content_renderer
intelligence_engine
```

Esta fase tem como objectivo preparar uma camada mínima de operação, diagnóstico e validação contínua entre os serviços, antes de avançar para uma experiência de frontend mais forte ou para exposição alargada em piloto.

---

## 2. Resultado esperado da fase

Ao concluir esta fase, deve ser possível:

```text
- arrancar os serviços principais de forma documentada;
- verificar rapidamente se cada serviço está disponível;
- validar o loop Backend Core → Intelligence Engine;
- validar o loop Backend Core → Content Renderer;
- correlacionar logs por request_id;
- executar smoke tests integrados;
- diagnosticar falhas comuns sem abrir o código;
- saber claramente o que está pronto para piloto técnico e o que ainda não está pronto para produção.
```

---

## 3. Estado de partida

## 3.1 Componentes existentes

```text
backend_core:
  - Django/DRF;
  - gestão do produto;
  - campanhas;
  - catálogo;
  - content outputs;
  - reports/media kits;
  - integração síncrona com intelligence_engine;
  - integração com content_renderer já existente;
  - endpoint POST /api/v1/campaigns/{id}/intelligence/.

intelligence_engine:
  - FastAPI;
  - GET /health;
  - POST /analysis/campaign;
  - POST /scoring/campaign;
  - POST /recommendations/campaign;
  - POST /moments/detect;
  - POST /intelligence/campaign;
  - auth interna por X-Internal-Token.

content_renderer:
  - serviço técnico de geração de assets;
  - healthcheck;
  - jobs;
  - callback;
  - storage local MVP;
  - hardening pós-MVP concluído.
```

## 3.2 Estado funcional

```text
Backend Core ↔ Intelligence Engine: validado com loop real
Backend Core ↔ Content Renderer: validado anteriormente com E2E PostgreSQL
Piloto técnico: possível
Produção: ainda não
```

## 3.3 Motivo da fase

A aplicação já tem serviços técnicos relevantes, mas ainda precisa de uma camada mínima de operação para responder rapidamente:

```text
Está tudo de pé?
Que serviço falhou?
A falha é de autenticação interna, payload, timeout ou indisponibilidade?
O Backend Core consegue falar com o Intelligence Engine?
O Backend Core consegue falar com o Renderer?
Os request_id aparecem nos logs?
Existe um comando simples para smoke test?
Existe runbook para diagnóstico?
```

---

# 4. Escopo da fase

## 4.1 Incluído

Esta fase inclui:

```text
- healthchecks agregados no Backend Core;
- comando ou script de smoke test integrado;
- validação operacional Backend Core ↔ Intelligence Engine;
- validação operacional Backend Core ↔ Content Renderer;
- documentação de arranque local/staging;
- documentação de variáveis de ambiente;
- runbook de diagnóstico;
- checklist de troubleshooting;
- logs mínimos com request_id/workspace_id/campaign_id/job_id quando aplicável;
- validação de ausência de secrets nos logs e docs;
- estado final da prontidão operacional.
```

## 4.2 Fora do escopo

Não implementar nesta fase:

```text
- stack completa de observabilidade com Prometheus/Grafana;
- tracing distribuído completo;
- OpenTelemetry obrigatório;
- centralização real de logs em Elasticsearch/Kibana;
- deploy Kubernetes;
- CI/CD completo;
- S3/R2 do renderer;
- frontend;
- billing/créditos;
- persistência de snapshots de intelligence;
- circuit breaker sofisticado;
- filas persistentes novas;
- alteração profunda da arquitectura.
```

---

# 5. Princípios de implementação

## 5.1 Princípio principal

```text
Observabilidade mínima, útil e incremental.
```

## 5.2 Regras

```text
1. Não transformar esta fase numa plataforma de observabilidade completa.
2. Não introduzir dependências pesadas sem necessidade.
3. Reutilizar healthchecks e clients existentes.
4. Preferir comandos/scripts simples e documentados.
5. Garantir que tokens nunca aparecem em logs.
6. Garantir que falhas são diagnosticáveis.
7. Manter o Backend Core como ponto de orquestração.
8. Não alterar o Intelligence Engine nem o Content Renderer salvo necessidade documental ou de compatibilidade mínima.
```

---

# 6. Caminhos relevantes

## Backend Core

```text
backend_core
```

## Intelligence Engine

```text
intelligence_engine
```

## Content Renderer

```text
content_renderer
```

## Backlog desta fase

```text
backend_core\docs\backend_core\fundamentos\observabilidade_staging_ecossistema\01_backlog.md
```

## Resultados desta fase

```text
backend_core\docs\backend_core\fundamentos\observabilidade_staging_ecossistema\resultados
```

## Documento de estado esperado

```text
backend_core\docs\backend_core\fundamentos\observabilidade_staging_ecossistema\estado_observabilidade_staging_ecossistema.md
```

---

# 7. Backlog técnico

---

# OBS-STG-001 — Analisar estado operacional actual dos três serviços

## Objectivo

Inspeccionar o estado actual do `backend_core`, `intelligence_engine` e `content_renderer`, identificando healthchecks, scripts, configurações, logs e lacunas operacionais.

## Tarefas

```text
Ler este backlog.
Ler documentação final da integração Backend Core ↔ Intelligence Engine.
Ler documentação final do Intelligence Engine.
Ler documentação final do Content Renderer.
Inspeccionar healthchecks existentes.
Inspeccionar settings/envs relevantes.
Inspeccionar scripts de arranque existentes.
Inspeccionar logs existentes.
Inspeccionar testes E2E/smoke existentes.
Identificar portas default dos serviços.
Identificar tokens internos necessários.
Identificar gaps de diagnóstico.
Propor plano de execução.
Não alterar runtime neste passo, salvo relatório.
```

## Critérios de aceitação

```text
Plano técnico criado.
Healthchecks existentes identificados.
Variáveis de ambiente críticas identificadas.
Lacunas operacionais listadas.
Riscos registados.
Relatório criado em resultados.
```

---

# OBS-STG-002 — Criar matriz operacional dos serviços

## Objectivo

Criar documentação central com a matriz dos serviços do ecossistema, portas, healthchecks, variáveis, dependências e comandos de arranque.

## Tarefas

```text
Criar documento de matriz operacional.
Listar backend_core.
Listar intelligence_engine.
Listar content_renderer.
Listar base de dados, se aplicável.
Listar portas default.
Listar comandos de arranque.
Listar healthchecks.
Listar variáveis obrigatórias.
Listar variáveis opcionais.
Listar dependências entre serviços.
Listar modo local.
Listar modo staging técnico.
Indicar quais variáveis são secrets e nunca devem ser logadas.
```

## Documento sugerido

```text
backend_core\docs\backend_core\fundamentos\observabilidade_staging_ecossistema\matriz_operacional_servicos.md
```

## Critérios de aceitação

```text
Matriz operacional existe.
Cada serviço tem porta, healthcheck e comando de arranque.
Secrets estão claramente identificados como não versionáveis.
Dependências entre serviços estão claras.
```

---

# OBS-STG-003 — Implementar healthcheck agregado no Backend Core

## Objectivo

Permitir que o Backend Core consulte e exponha o estado dos serviços técnicos dependentes.

## Endpoint sugerido

A IA local deve adaptar ao padrão real do projecto.

Sugestão:

```text
GET /api/v1/system/health/external-services/
```

ou, se houver padrão interno:

```text
GET /api/v1/health/dependencies/
```

## Serviços a verificar

```text
Intelligence Engine
Content Renderer
Base de dados do Backend Core, se ainda não existir healthcheck próprio
```

## Tarefas

```text
Identificar padrão existente de healthcheck no Backend Core.
Criar serviço interno para consultar dependências.
Consultar GET /health do Intelligence Engine.
Consultar GET /health do Content Renderer.
Aplicar timeout curto.
Não enviar tokens em healthcheck público se os /health forem públicos.
Se algum healthcheck exigir token, enviar header interno sem logar.
Normalizar resposta.
Incluir duration_ms por serviço.
Incluir status por serviço:
- ok;
- degraded;
- unavailable;
- misconfigured;
- unknown.

Evitar que falha de um serviço quebre o healthcheck agregado.
Criar endpoint protegido se expuser detalhes internos.
Criar testes com mocks.
```

## Resposta sugerida

```json
{
  "status": "ok|degraded|unavailable",
  "service": "backend_core",
  "dependencies": {
    "intelligence_engine": {
      "status": "ok",
      "url": "configured",
      "duration_ms": 12
    },
    "content_renderer": {
      "status": "ok",
      "url": "configured",
      "duration_ms": 18
    }
  }
}
```

## Critérios de aceitação

```text
Endpoint agregado existe.
Falha de uma dependência gera degraded/unavailable, não 500 inesperado.
Timeout é curto e configurável.
Resposta não expõe tokens nem URLs sensíveis em excesso.
Testes cobrem ok, degraded, timeout e misconfigured.
```

---

# OBS-STG-004 — Criar smoke test operacional Backend Core ↔ Intelligence Engine

## Objectivo

Criar comando, script ou teste opt-in para validar rapidamente o loop real:

```text
Backend Core → Intelligence Engine → Backend Core
```

## Tarefas

```text
Reutilizar o teste opt-in existente, se já existir.
Ou criar management command/script simples.
Garantir que o teste só corre quando explicitamente activado.
Validar configuração:
- INTELLIGENCE_ENGINE_BASE_URL;
- INTELLIGENCE_ENGINE_INTERNAL_TOKEN ou token equivalente;
- INTELLIGENCE_ENGINE_ENABLED;
- INTELLIGENCE_ENGINE_DRY_RUN=false.

Criar ou localizar campanha de teste.
Executar chamada ao endpoint Django ou ao service.
Confirmar resposta com:
- analysis;
- scores;
- grade;
- moments;
- recommendations;
- summary.

Confirmar logs sem token.
Documentar comandos.
```

## Critérios de aceitação

```text
Existe smoke test IE documentado.
Corre apenas de forma explícita.
Sucesso real é verificável.
Falha com IE desligado é documentada.
Token não aparece nos logs.
```

---

# OBS-STG-005 — Criar smoke test operacional Backend Core ↔ Content Renderer

## Objectivo

Criar ou consolidar validação rápida do loop:

```text
Backend Core → Content Renderer → callback Backend Core
```

## Tarefas

```text
Identificar testes E2E existentes do renderer.
Identificar como o Backend Core cria jobs para o renderer.
Identificar payload mínimo para content_generation ou report_generation.
Criar smoke test opt-in ou documentar comando existente.
Validar:
- renderer health;
- token interno;
- criação de job;
- resposta 202, se aplicável;
- callback;
- ExternalJobReference actualizado;
- ficheiros/outputs esperados;
- erro controlado quando renderer está indisponível.

Não alterar o renderer salvo necessidade mínima.
```

## Critérios de aceitação

```text
Existe smoke test Renderer documentado.
Loop real ou checklist executável está disponível.
Falha com renderer desligado é tratada.
Logs não expõem token.
Resultado fica documentado em relatório.
```

---

# OBS-STG-006 — Normalizar correlação por request_id/job_id nos logs

## Objectivo

Garantir que os logs mínimos dos fluxos entre serviços são correlacionáveis.

## Fluxos a cobrir

```text
Backend Core → Intelligence Engine
Backend Core → Content Renderer
Callbacks do Renderer → Backend Core
```

## Tarefas

```text
Inspeccionar logs existentes.
Confirmar presença de request_id no fluxo Intelligence.
Confirmar presença de request_id/job_id no fluxo Renderer.
Adicionar logs mínimos se faltarem.
Não logar payloads completos.
Não logar headers sensíveis.
Não logar tokens.
Incluir campos úteis:
- request_id;
- workspace_id;
- campaign_id;
- job_id;
- external_job_id;
- provider;
- duration_ms;
- status;
- error_type.

Criar ou ajustar testes de logs sem secrets.
```

## Critérios de aceitação

```text
Logs principais têm identificadores de correlação.
Fluxo IE é rastreável por request_id.
Fluxo Renderer é rastreável por job_id/request_id.
Tokens não aparecem em logs.
Testes de ausência de token passam.
```

---

# OBS-STG-007 — Criar runbook de arranque local/staging

## Objectivo

Documentar como arrancar o ecossistema local ou staging técnico com os três serviços.

## Documento sugerido

```text
backend_core\docs\backend_core\fundamentos\observabilidade_staging_ecossistema\runbook_arranque_staging.md
```

## Conteúdo mínimo

```text
Pré-requisitos.
Portas.
Ordem de arranque.
Variáveis de ambiente.
Como arrancar backend_core.
Como arrancar intelligence_engine.
Como arrancar content_renderer.
Como validar healthchecks.
Como executar smoke tests.
Como parar serviços.
Como limpar artefactos locais, se aplicável.
Problemas comuns.
```

## Critérios de aceitação

```text
Runbook existe.
Comandos estão claros.
Ordem de arranque está clara.
Healthchecks e smoke tests estão incluídos.
Não há secrets reais no documento.
```

---

# OBS-STG-008 — Criar checklist de troubleshooting

## Objectivo

Criar guia prático para diagnosticar falhas comuns no ecossistema.

## Documento sugerido

```text
backend_core\docs\backend_core\fundamentos\observabilidade_staging_ecossistema\checklist_troubleshooting.md
```

## Casos a cobrir

```text
Intelligence Engine indisponível.
Intelligence Engine devolve 403.
Intelligence Engine devolve 422.
Intelligence Engine devolve 500.
Content Renderer indisponível.
Content Renderer não faz callback.
Callback chega mas job não actualiza.
Token interno desalinhado.
URL configurada errada.
Timeout.
Payload inválido.
Erro de workspace/RBAC.
Porta ocupada.
Base de dados indisponível.
```

## Critérios de aceitação

```text
Checklist existe.
Cada caso tem sintomas, causa provável e acção recomendada.
Inclui comandos de verificação.
Não expõe secrets.
É utilizável por alguém que não implementou o código.
```

---

# OBS-STG-009 — Criar painel textual de prontidão operacional

## Objectivo

Criar documento simples de prontidão operacional para saber se o ecossistema está pronto para piloto técnico.

## Documento sugerido

```text
backend_core\docs\backend_core\fundamentos\observabilidade_staging_ecossistema\painel_prontidao_operacional.md
```

## Conteúdo mínimo

```text
Estado dos serviços.
Estado dos healthchecks.
Estado dos smoke tests.
Estado dos logs/correlação.
Estado da segurança de secrets.
Estado dos blockers de produção.
Decisão: pronto/não pronto para piloto.
Decisão: pronto/não pronto para produção.
```

## Critérios de aceitação

```text
Painel existe.
Critérios de piloto estão claros.
Critérios de produção estão claros.
Estado é honesto.
```

---

# OBS-STG-010 — Validação final, documentação e estado da fase

## Objectivo

Fechar a fase com documentação final, validações e relatório de estado.

## Tarefas

```text
Executar testes relevantes.
Executar manage.py check.
Executar lint, se disponível.
Executar healthcheck agregado, se implementado.
Executar smoke test IE, se ambiente permitir.
Executar smoke test Renderer, se ambiente permitir.
Não inventar resultados se algum serviço não estiver disponível.
Actualizar documentação final.
Criar documento de estado:
backend_core\docs\backend_core\fundamentos\observabilidade_staging_ecossistema\estado_observabilidade_staging_ecossistema.md

Criar relatório final em:
backend_core\docs\backend_core\fundamentos\observabilidade_staging_ecossistema\resultados\prompt_final_observabilidade_staging.md
```

## Critérios de aceitação

```text
Validações relevantes executadas ou limitações documentadas.
Documentação final existe.
Estado final é honesto.
Sem secrets em docs/logs de exemplo.
Prontidão para piloto está explicitamente indicada.
Prontidão para produção está explicitamente indicada.
Próximo passo recomendado está claro.
```

---

# 8. Critérios de aceitação da fase

A fase fica concluída quando:

```text
Matriz operacional dos serviços existe.
Healthcheck agregado existe ou limitação justificada.
Smoke test IE existe e está documentado.
Smoke test Renderer existe ou checklist realista está documentada.
Runbook de arranque existe.
Checklist de troubleshooting existe.
Painel de prontidão operacional existe.
Logs principais têm request_id/job_id quando aplicável.
Tokens não aparecem em logs/documentação.
Validações relevantes foram executadas ou limitações foram documentadas.
Documento de estado final existe.
```

---

# 9. Critérios de não aceitação

A fase não deve ser aceite se:

```text
Documentos incluírem tokens reais.
Healthcheck agregado expuser secrets ou dados sensíveis.
Smoke tests dependerem de dados frágeis não documentados.
Falha de uma dependência gerar 500 inesperado no healthcheck agregado.
Logs não permitirem correlacionar chamadas entre serviços.
Runbook não permitir arrancar os serviços.
Troubleshooting for genérico e não accionável.
Relatório final declarar produção-ready sem evidência.
```

---

# 10. Riscos

| ID          | Risco                                                              | Impacto    | Mitigação                                                              |
| ----------- | ------------------------------------------------------------------ | ---------- | ---------------------------------------------------------------------- |
| OBS-RSK-001 | Transformar a fase numa stack completa de observabilidade.         | Médio/Alto | Manter escopo MVP: healthchecks, smoke tests, runbooks e logs mínimos. |
| OBS-RSK-002 | Expor tokens em logs ou documentação.                              | Crítico    | Testes/grep de secrets e redacção de logs.                             |
| OBS-RSK-003 | Smoke tests frágeis por dependerem de dados locais específicos.    | Médio      | Usar fixtures, comandos opt-in ou checklist explícita.                 |
| OBS-RSK-004 | Healthcheck agregado gerar falsos negativos por timeout agressivo. | Médio      | Timeout curto mas configurável; estado degraded em vez de falha total. |
| OBS-RSK-005 | Healthcheck detalhado expor informação operacional sensível.       | Médio      | Proteger endpoint ou reduzir detalhe público.                          |
| OBS-RSK-006 | Logs insuficientes dificultarem diagnóstico.                       | Médio      | Exigir request_id/job_id/workspace_id/status/duration_ms.              |
| OBS-RSK-007 | Validação real não ser executável no ambiente local.               | Médio      | Documentar limitação e fornecer checklist/runbook executável.          |
| OBS-RSK-008 | Confundir pronto para piloto com pronto para produção.             | Alto       | Painel de prontidão deve separar claramente piloto e produção.         |

---

# 11. Decisões pendentes

## OBS-PDEC-001 — Endpoint de healthcheck agregado deve ser público ou protegido?

```text
Estado: pendente
Recomendação: protegido se incluir detalhe das dependências.
```

## OBS-PDEC-002 — Criar management command ou teste opt-in para smoke tests?

```text
Estado: pendente
Recomendação: teste opt-in primeiro; management command se for útil para operação manual.
```

## OBS-PDEC-003 — Healthcheck agregado deve consultar renderer e IE em tempo real?

```text
Estado: pendente
Recomendação: sim, mas com timeout curto e estado degraded em falha.
```

## OBS-PDEC-004 — Métricas devem ser só logs ou endpoint dedicado?

```text
Estado: pendente
Recomendação MVP: logs estruturados e painel textual; endpoint de métricas fica para fase posterior.
```

---

# 12. Ordem recomendada de execução

```text
1. OBS-STG-001 — Analisar estado operacional actual dos três serviços
2. OBS-STG-002 — Criar matriz operacional dos serviços
3. OBS-STG-003 — Implementar healthcheck agregado no Backend Core
4. OBS-STG-004 — Criar smoke test operacional Backend Core ↔ Intelligence Engine
5. OBS-STG-005 — Criar smoke test operacional Backend Core ↔ Content Renderer
6. OBS-STG-006 — Normalizar correlação por request_id/job_id nos logs
7. OBS-STG-007 — Criar runbook de arranque local/staging
8. OBS-STG-008 — Criar checklist de troubleshooting
9. OBS-STG-009 — Criar painel textual de prontidão operacional
10. OBS-STG-010 — Validação final, documentação e estado da fase
```

---

# 13. Relação com fases futuras

## 13.1 Frontend / Campaign War Room

Depois desta fase, o frontend pode avançar com menor risco porque haverá forma clara de validar se os serviços técnicos estão disponíveis.

## 13.2 Produção

Esta fase não torna o sistema production-ready. Para produção ainda serão necessários, pelo menos:

```text
- observabilidade real;
- logs centralizados;
- alertas;
- política de deploy;
- gestão segura de secrets;
- S3/R2 para assets;
- calibração dos scores/recomendações;
- testes em staging contínuo;
- hardening operacional.
```

## 13.3 S3/R2

S3/R2 continua como blocker de produção do renderer, mas não bloqueia staging técnico.

## 13.4 Calibração de negócio

Scores, grades e recomendações do Intelligence Engine continuam heurísticos. Esta fase só garante diagnóstico operacional, não validação de valor de negócio.

---

# 14. Resultado esperado

Ao concluir esta fase, o ecossistema deve passar de:

```text
Serviços funcionais mas diagnosticados manualmente
```

para:

```text
Serviços funcionais com healthchecks, smoke tests, runbook e diagnóstico mínimo
```

Estado esperado:

```text
Pronto para piloto técnico controlado: sim
Pronto para produção: não
```

---

# 15. Próximo passo após este backlog

Criar uma pipeline de prompts compatível com o Assistente Desktop para executar este backlog.

Ficheiro sugerido:

```text
backend_core\docs\backend_core\fundamentos\observabilidade_staging_ecossistema\02_pipeline.md
```

Recomendação de modelos:

```text
Prompt 01: opus
Prompts 02–06: opus
Prompts 07–10: sonnet
```

Justificação:

```text
A fase combina análise arquitectural, integração técnica, healthchecks e smoke tests.
A documentação operacional final pode ser feita com sonnet.
```
