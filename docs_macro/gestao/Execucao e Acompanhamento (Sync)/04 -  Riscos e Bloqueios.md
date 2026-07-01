---

doc_id: "exec-riscos-bloqueios"  
title: "Riscos e Bloqueios"  
project: "ChartRex / MomentFlow"  
area: "gestao_execucao"  
doc_type: "risk_blocker_register"  
status: "active"  
owner: "Aldino Ramos"  
created_at: "2026-06-23"  
updated_at: "2026-06-25"  
last_reviewed_at: "2026-06-25"  
review_frequency: "weekly"  
update_frequency: "on_change"  
version: "1.3"  
confidentiality: "internal"  
source_of_truth: true

current_phase: "Transição pós-wiring-Intelligence-Engine para próxima fase"  
last_completed_phase: "Backend Core ↔ Intelligence Engine — wiring síncrono (BC-IE-001 a BC-IE-010)"  
overall_risk_level: "medium"  
risk_count_total: 17  
risk_count_open: 5  
risk_count_monitoring: 9  
risk_count_mitigated: 3  
risk_count_closed: 0  
blocker_count_total: 0  
blocker_count_open: 0  
last_risk_id: "RSK-017"  
last_blocker_id: null  
risk_id_prefix: "RSK"  
blocker_id_prefix: "BLK"

ready_for_integration_environment: true  
ready_for_technical_pilot: true  
ready_for_production: false

---

related_docs:

- "[[status_report]]"
    
- "[[plano_execucao]]"
    
- "[[log_decisoes]]"
    
- "[[matriz_validacao]]"
    
- "[[diario_execucao_ia]]"
    

tags:

- "project/momentflow"
    
- "gestao/riscos"
    
- "gestao/bloqueios"
    
- "execucao"
    
- "obsidian"
    

## ai_update_mode: "controlled"  
ai_update_scope: "actualizar riscos, bloqueios, impacto, probabilidade, mitigação, responsável, estado, decisões necessárias e histórico de alterações, preservando riscos encerrados e evidência."  
ai_may_create_sections: false  
ai_may_delete_content: false  
ai_should_preserve_history: true

# Riscos e Bloqueios — ChartRex / MomentFlow

## 1. Instruções para IA actualizar este documento

Este documento é a **fonte de verdade para riscos, bloqueios, mitigação e impedimentos** do projecto.

A IA deve actualizar este ficheiro apenas quando houver alteração real de risco, bloqueio, impacto, probabilidade, mitigação, responsável ou estado.

Ao actualizar este ficheiro, a IA deve:

```text
1. Ler primeiro o README.md desta pasta.
2. Ler os metadados YAML deste documento.
3. Respeitar ai_update_mode e ai_update_scope.
4. Actualizar updated_at no YAML.
5. Actualizar contadores de riscos e bloqueios.
6. Adicionar novos riscos com ID sequencial RSK-XXX.
7. Adicionar novos bloqueios com ID sequencial BLK-XXX.
8. Não apagar riscos antigos.
9. Não apagar bloqueios resolvidos.
10. Mover riscos/bloqueios encerrados para a secção adequada.
11. Não marcar risco como mitigado ou fechado sem evidência.
12. Não mascarar bloqueios como riscos.
13. Distinguir risco, bloqueio e decisão pendente.
14. Ligar riscos a decisões quando aplicável.
15. Não expor tokens, passwords ou segredos.
```

A IA pode:

```text
- adicionar riscos;
- adicionar bloqueios;
- actualizar impacto;
- actualizar probabilidade;
- actualizar mitigação;
- alterar estado com justificação;
- adicionar evidência;
- adicionar notas de revisão;
- actualizar histórico.
```

A IA não deve:

```text
- apagar histórico;
- fechar risco sem justificação;
- remover bloqueio resolvido;
- inventar mitigação executada;
- inventar evidência;
- declarar produção-ready se existirem bloqueadores de produção abertos;
- alterar decisões arquitecturais sem registar em [[log_decisoes]].
```

Quando não houver evidência suficiente, usar:

```text
Estado: por confirmar
Evidência: não disponível
Acção necessária: validar manualmente
```

---

# 2. Convenções

## Diferença entre risco e bloqueio

```text
Risco = algo que pode acontecer e afectar o projecto.
Bloqueio = algo que já está a impedir o avanço.
```

## Estados de risco

```text
open        = risco activo sem mitigação concluída;
monitoring  = risco conhecido, parcialmente mitigado, sob observação;
mitigated   = mitigação aplicada; manter em observação;
accepted    = risco aceite conscientemente;
closed      = risco encerrado;
```

## Estados de bloqueio

```text
open
in_resolution
resolved
cancelled
```

## Escala de impacto

```text
baixo
médio
alto
crítico
```

## Escala de probabilidade

```text
baixa
média
alta
```

## Prioridade

```text
P1 = tratar imediatamente;
P2 = tratar antes da próxima fase crítica;
P3 = monitorizar;
P4 = aceitar temporariamente.
```

---

# 3. Resumo executivo

```text
Estado geral de risco: médio
Bloqueios activos: 0
Pronto para integração: sim
Pronto para piloto técnico: sim
Pronto para produção: não
```

## Leitura executiva

O projecto está em estado **controlado**.

O risco técnico principal da fase do renderer — a comunicação Backend Core Django ↔ Content/Report Renderer — foi substancialmente mitigado com o hardening pós-MVP:

```text
- callback em background leve;
- retry de callback com backoff;
- echo de template_key/template_id;
- StorageProvider abstraction;
- harness E2E com PostgreSQL;
- loop real Django ↔ Renderer ↔ Django validado;
- coverage Vitest;
- documentação final.
```

O **FastAPI Intelligence Engine MVP** foi concluído (IE-001 a IE-010), com motores deterministas e explicáveis, 197 testes a passar, e o contrato de integração com o Backend Core documentado. Agora, o **wiring síncrono Backend Core ↔ Intelligence Engine** (BC-IE-001 a BC-IE-010) foi implementado e validado de ponta a ponta, incluindo um loop real com os dois serviços a correr de facto — o que mitiga substancialmente o risco anteriormente mais relevante desta área:

```text
- RSK-014 (wiring real não implementado) passa de aberto para mitigado: a chamada síncrona Django → Intelligence Engine foi implementada, testada com mocks (13 cenários) e validada com o loop real (200/completed, token nunca exposto nos logs);
- um bug real de contrato (granularidade date/datetime em content_outputs[].created_at) foi encontrado e corrigido durante a validação real — evidência de que a validação foi genuína, não apenas teórica.
```

Os novos riscos identificados nesta fase são, na sua maioria, esperados de um MVP heurístico recém-ligado e não bloqueiam integração/piloto:

```text
- heurísticas de scoring/recomendação/momentos não calibradas com dados reais;
- ausência de coverage formal e type-checking estático no Intelligence Engine e no Backend Core;
- catálogo de content packs/templates espelhado como constantes, não importado do Django;
- validação real do wiring é local/opt-in (RUN_REAL_IE=1), não corre em CI por padrão;
- sem observabilidade dedicada (métricas/alertas) para a chamada síncrona ao Intelligence Engine.
```

Riscos de produção ainda relevantes (herdados do renderer):

```text
- storage local não é adequado para produção;
- observabilidade e métricas operacionais ainda não existem;
- background jobs continuam in-process;
- não existe fila persistente nem dead-letter;
- política de deploy/CI/CD/segredos ainda não está formalizada.
```

Conclusão:

```text
Pode avançar para integração e piloto técnico controlado, nos três componentes (renderer, Intelligence Engine e wiring síncrono).
Não deve avançar para produção sem resolver os riscos de produção do renderer, calibrar as heurísticas do Intelligence Engine, nem sem observabilidade e validação contínua (não apenas local) para a chamada síncrona Backend Core ↔ Intelligence Engine.
```

---

# 4. Bloqueios actuais

```text
Sem bloqueios activos conhecidos.
```

## Tabela de bloqueios

|ID|Bloqueio|Impacto|Estado|Responsável|Acção necessária|
|---|---|--:|---|---|---|
|—|Nenhum bloqueio activo|—|—|—|—|

---

# 5. Riscos abertos

## RSK-004 — Storage local não é adequado para produção

```text
Estado: open
Prioridade: P2
Impacto: alto
Probabilidade: alta
Responsável: a definir
Data de identificação: 2026-06-23
Última revisão: 2026-06-24
```

### Descrição

O `content_renderer` usa storage local para guardar assets gerados. Isto é aceitável para MVP, desenvolvimento, integração e piloto técnico controlado, mas não é adequado para produção.

### Impacto

```text
- perda de ficheiros em caso de rebuild/redeploy;
- dificuldade de escalar horizontalmente;
- URLs locais não adequadas a consumo externo;
- ausência de lifecycle policy;
- ausência de gestão cloud de permissões/bucket/CDN;
- dificuldade de partilhar assets entre ambientes.
```

### Mitigação actual

```text
StorageProvider abstraction foi implementado.
LocalStorage continua funcional.
Provider S3/R2 real ainda não implementado.
```

### Mitigação recomendada

```text
Implementar provider S3/R2 antes de produção.
Definir bucket, credenciais, permissões e política de lifecycle.
Actualizar contrato de Asset se necessário, mantendo retrocompatibilidade.
Criar testes de integração para provider real ou mockado.
```

### Decisão relacionada

```text
DEC-004 — Storage local no MVP, S3/R2 antes de produção.
DEC-011 — StorageProvider como abstracção de storage.
DEC-017 — S3/R2, observabilidade e política operacional como bloqueadores de produção.
```

### Estado executivo

```text
Não bloqueia próxima fase de produto.
Bloqueia produção.
```

---

## RSK-006 — Background in-process pode perder job em restart

```text
Estado: open
Prioridade: P2
Impacto: alto
Probabilidade: média
Responsável: a definir
Data de identificação: 2026-06-24
Última revisão: 2026-06-24
```

### Descrição

O renderer usa background leve in-process para executar render/callback após responder `202`. Se o processo reiniciar entre o `202` e o callback, o trabalho em curso pode perder-se.

### Impacto

```text
- job aceite pode nunca concluir;
- Django pode ficar à espera de callback;
- necessidade de reconciliação manual ou automática;
- risco maior em produção ou workloads longos.
```

### Mitigação actual

```text
Callback background implementado.
Retry com backoff implementado.
Logs estruturados existem.
E2E PostgreSQL validado.
```

### Mitigação recomendada

```text
Para piloto técnico, aceitar risco com monitorização.
Antes de produção, avaliar:
- fila persistente;
- mecanismo de reconciliação;
- worker separado;
- retry persistido;
- job lease/heartbeat.
```

### Decisão relacionada

```text
DEC-009 — Callback em background leve.
DEC-010 — Retry simples de callback com backoff.
DEC-017 — S3/R2, observabilidade e política operacional como bloqueadores de produção.
```

### Estado executivo

```text
Não bloqueia integração/piloto técnico controlado.
Bloqueia produção se não houver política operacional.
```

---

## RSK-007 — Falta de observabilidade operacional

```text
Estado: open
Prioridade: P2
Impacto: médio/alto
Probabilidade: alta
Responsável: a definir
Data de identificação: 2026-06-24
Última revisão: 2026-06-24
```

### Descrição

O renderer tem logs estruturados sem secrets, mas ainda não tem métricas operacionais, tracing distribuído, dashboards ou alertas.

### Impacto

```text
- dificuldade em detectar falhas silenciosas;
- dificuldade em medir latência de render;
- dificuldade em acompanhar callbacks falhados;
- falta de indicadores para produção;
- troubleshooting dependente de logs manuais.
```

### Mitigação actual

```text
Logs estruturados existem.
Eventos de job/render/callback são registados.
Coverage e testes existem.
```

### Mitigação recomendada

```text
Definir métricas mínimas:
- jobs accepted;
- jobs completed;
- jobs failed;
- callbacks completed;
- callbacks failed;
- callback retry count;
- render duration;
- callback latency;
- storage write duration;
- error rate por job_type.

Definir dashboards e alertas antes de produção.
```

### Decisão relacionada

```text
DEC-017 — S3/R2, observabilidade e política operacional como bloqueadores de produção.
```

### Estado executivo

```text
Não bloqueia próxima fase de produto.
Bloqueia produção.
```

---

## RSK-008 — `content_generation` partial/failed sem E2E HTTP real

```text
Estado: monitoring
Prioridade: P3
Impacto: médio
Probabilidade: baixa/média
Responsável: a definir
Data de identificação: 2026-06-24
Última revisão: 2026-06-24
```

### Descrição

Os cenários `content_generation partially_completed` e `content_generation failed` não foram reproduzidos por loop HTTP real ponta-a-ponta. O renderer é resiliente e tende a cair em fallback `completed` quando recebe template/formato desconhecido.

### Cobertura actual

```text
Coberto por testes do Backend Core.
Coberto por testes Vitest do renderer.
Não coberto por chamada HTTP real E2E ponta-a-ponta.
```

### Impacto

```text
- menor evidência E2E para partial/failed em content_generation;
- risco limitado, porque os handlers Django e renderer foram testados separadamente;
- pode ser relevante antes de produção ou antes de cenários reais de falha.
```

### Mitigação recomendada

```text
Criar mecanismo controlado de falha em ambiente de teste, sem expor em produção.
Ou manter cobertura indirecta como suficiente para MVP/piloto.
Registar na matriz de validação como validação indirecta.
```

### Estado executivo

```text
Não bloqueia integração.
Não bloqueia piloto técnico.
Monitorizar antes de produção.
```

---

## RSK-009 — Produção sem política formal de secrets/deploy/CI-CD

```text
Estado: open
Prioridade: P2
Impacto: alto
Probabilidade: média
Responsável: a definir
Data de identificação: 2026-06-24
Última revisão: 2026-06-24
```

### Descrição

O serviço já tem `.env.example` sem secrets e logs com redacção, mas ainda não existe política formal de gestão de secrets, deploy, CI/CD, ambientes e rotação de tokens para produção.

### Impacto

```text
- risco operacional;
- risco de configuração inconsistente entre ambientes;
- risco de token mal gerido;
- dificuldade de deploy repetível;
- falta de gates formais de qualidade.
```

### Mitigação actual

```text
.env.example sem secrets.
INTERNAL_API_TOKEN não é logado.
Build/lint/testes/coverage existem.
```

### Mitigação recomendada

```text
Definir gestão de secrets por ambiente.
Definir CI/CD.
Definir variáveis obrigatórias por ambiente.
Definir rotação de INTERNAL_API_TOKEN.
Definir checks obrigatórios antes de deploy.
```

### Estado executivo

```text
Não bloqueia desenvolvimento.
Bloqueia produção.
```

---

# 6. Riscos em monitorização

## RSK-001 — Acoplamento excessivo ao payload interno do Django

```text
Estado: monitoring
Prioridade: P3
Impacto: médio
Probabilidade: média
Responsável: a definir
Data de identificação: 2026-06-23
Última revisão: 2026-06-24
```

### Descrição

O renderer consome payloads enviados pelo Backend Core. Alterações futuras no Django podem quebrar o renderer se o contrato não for versionado e validado.

### Mitigação aplicada

```text
Uso de payload_version.
Validação de envelope.
Schemas Zod.
Leitura defensiva de payload.
E2E PostgreSQL.
Documentação de contratos.
```

### Mitigação futura

```text
Manter compatibilidade por payload_version.
Adicionar testes de contrato sempre que o Backend Core mudar payloads.
```

### Estado executivo

```text
Mitigado parcialmente.
Continuar a monitorizar.
```

---

## RSK-003 — Callback falhar após geração de ficheiros

```text
Estado: monitoring
Prioridade: P3
Impacto: alto
Probabilidade: baixa/média
Responsável: a definir
Data de identificação: 2026-06-23
Última revisão: 2026-06-24
```

### Descrição

O renderer pode gerar ficheiros com sucesso, mas falhar ao notificar o Django via callback.

### Mitigação aplicada

```text
Callback em background.
Retry com backoff.
Timeouts.
Logs estruturados.
Callback não-fatal.
Idempotência validada no loop real.
```

### Risco remanescente

```text
Sem retry persistente.
Restart do processo pode perder tentativa em curso.
Sem dead-letter queue.
```

### Estado executivo

```text
Risco mitigado para integração/piloto.
Continuar a monitorizar antes de produção.
```

---

## RSK-010 — Idempotência sob retry em cenários extremos

```text
Estado: monitoring
Prioridade: P3
Impacto: médio/alto
Probabilidade: baixa
Responsável: a definir
Data de identificação: 2026-06-24
Última revisão: 2026-06-24
```

### Descrição

Retry de callback pode reentregar uma mensagem já processada se a resposta HTTP se perder após o Django processar a primeira entrega.

### Mitigação aplicada

```text
Idempotência validada no E2E PostgreSQL.
Django deve tratar callback como idempotente.
```

### Mitigação recomendada

```text
Manter testes de idempotência.
Adicionar cenários adicionais quando houver fila persistente ou S3/R2.
```

### Estado executivo

```text
Monitorização.
Não bloqueia piloto técnico.
```

---

## RSK-011 — Qualidade visual inicial dos templates pode limitar demonstração externa

```text
Estado: monitoring
Prioridade: P3
Impacto: médio
Probabilidade: média
Responsável: a definir
Data de identificação: 2026-06-24
Última revisão: 2026-06-24
```

### Descrição

Os templates actuais cumprem o objectivo técnico de gerar assets, mas podem não ter qualidade visual suficiente para uma demonstração externa ou piloto com utilizadores reais exigentes.

### Impacto

```text
- percepção de valor pode ficar abaixo do potencial do produto;
- demonstrações podem parecer técnicas demais;
- pode limitar adopção inicial.
```

### Mitigação recomendada

```text
Definir nível mínimo de qualidade visual.
Criar fase de melhoria de templates antes de demonstração externa.
Separar melhoria visual de estabilidade técnica.
```

### Estado executivo

```text
Não bloqueia backend/intelligence.
Pode bloquear demonstração externa.
```

---

## RSK-012 — Próxima fase pode dispersar foco entre Intelligence, S3/R2 e frontend

```text
Estado: monitoring
Prioridade: P2
Impacto: médio/alto
Probabilidade: média
Responsável: Aldino Ramos
Data de identificação: 2026-06-24
Última revisão: 2026-06-24
```

### Descrição

Após o renderer, há várias opções legítimas de próxima fase: FastAPI Intelligence Engine, S3/R2, frontend mínimo, observabilidade ou templates avançados. Avançar em várias em paralelo pode dispersar foco.

### Impacto

```text
- aumento de WIP;
- perda de clareza;
- pipelines concorrentes;
- maior risco de dívida técnica;
- menor velocidade de entrega.
```

### Mitigação recomendada

```text
Registar decisão explícita da próxima fase em [[log_decisoes]].
Criar backlog único da fase escolhida.
Criar pipeline única antes de executar.
Manter S3/R2 e observabilidade como pendências de produção, salvo decisão contrária.
```

### Estado executivo

```text
Monitorizar.
Decisão recomendada: avançar para FastAPI Intelligence Engine.
```

---

## RSK-013 — Heurísticas do Intelligence Engine não calibradas com dados reais

```text
Estado: monitoring
Prioridade: P3
Impacto: médio/alto
Probabilidade: alta
Responsável: a definir
Data de identificação: 2026-06-24
Última revisão: 2026-06-25
```

### Descrição

Os pesos, limiares e confianças usados pelo scoring engine, recommendation engine e moment detector são constantes fixadas no código do MVP (ex.: `RELEASE_WINDOW_DAYS=14`, `MILESTONE_CLICKS_THRESHOLD=1000`), não calibradas com dados reais de campanhas.

### Mitigação aplicada

```text
Cada score/recomendação/momento traz uma Explanation/Warning que expõe os componentes e pesos usados.
Nunca apresentado como "IA" ou inferência opaca.
197 testes deterministas cobrem as regras, mas não a sua adequação ao mundo real.
```

### Mitigação recomendada

```text
Rever pesos/limiares quando existirem dados reais de campanhas em produção.
```

### Estado executivo

```text
Não bloqueia integração nem piloto técnico.
Monitorizar antes de qualquer decisão de produto baseada nos scores/recomendações.
```

---

## RSK-015 — Ausência de coverage formal e type-checking estático no Intelligence Engine

```text
Estado: monitoring
Prioridade: P4
Impacto: baixo/médio
Probabilidade: alta
Responsável: a definir
Data de identificação: 2026-06-24
Última revisão: 2026-06-25
```

### Descrição

O Intelligence Engine não tem `pytest-cov` nem `mypy`/`pyright` instalados ou configurados. A confiança na implementação vem de 197 testes deterministas organizados por regra/serviço, não de métricas de coverage.

### Mitigação aplicada

```text
197 testes cobrindo regras, contratos HTTP, invariantes de catálogo suportado e determinismo.
ruff check/format mantêm consistência de estilo.
```

### Mitigação recomendada

```text
Avaliar introduzir pytest-cov e mypy/pyright se a equipa decidir investir nessa ferramenta, sem urgência para o MVP.
```

### Estado executivo

```text
Não bloqueia integração nem piloto técnico.
```

---

## RSK-016 — Catálogo de content packs/templates espelhado, não importado do Django

```text
Estado: monitoring
Prioridade: P3
Impacto: médio
Probabilidade: baixa/média
Responsável: a definir
Data de identificação: 2026-06-24
Última revisão: 2026-06-25
```

### Descrição

O `RecommendationEngine` e o `MomentDetector` espelham o catálogo semeado em `backend_core/apps/content/seeds.py` (packs/templates) como constantes Python no Intelligence Engine, em vez de o importar directamente. Se o catálogo real do Django mudar sem actualizar estas constantes, as sugestões podem ficar desalinhadas com o que o produto consegue cumprir.

### Mitigação aplicada

```text
Testes de invariante dedicados garantem que nenhuma recomendação/momento referencia um pack/template fora do catálogo espelhado.
Baixo acoplamento deliberado: o Intelligence Engine não importa Django.
```

### Mitigação recomendada

```text
Sempre que o catálogo real do Django mudar, actualizar as constantes espelhadas no Intelligence Engine e os testes de invariante.
```

### Estado executivo

```text
Não bloqueia integração nem piloto técnico.
Monitorizar sempre que o catálogo de content packs/templates do Django evoluir.
```

---

## RSK-017 — Validação real do wiring Backend Core ↔ Intelligence Engine é local/pontual, não contínua

```text
Estado: monitoring
Prioridade: P3
Impacto: médio
Probabilidade: média
Responsável: a definir
Data de identificação: 2026-06-25
Última revisão: 2026-06-25
```

### Descrição

A validação real (com os dois serviços a correr de facto) do wiring síncrono Backend Core ↔ Intelligence Engine é feita por testes opt-in (`RUN_REAL_IE=1`) que exigem o Intelligence Engine a correr manualmente como processo externo. Não há CI nem ambiente de staging com os dois serviços persistentemente disponíveis para validação contínua.

### Impacto

```text
- regressões no contrato entre os dois serviços podem não ser detectadas automaticamente;
- a confiança na integração depende de execução manual e disciplinada do loop real;
- sem ambiente de staging, a "validação real" fica pontual no tempo (capturada em BC-IE-009), não recorrente.
```

### Mitigação aplicada

```text
Testes opt-in dedicados (apps/campaigns/tests/test_intelligence_real_loop.py) com instruções claras de arranque.
Evidência real capturada e documentada em backend_core/docs/.../resultados/prompt_09_loop_real_backend_core_intelligence.md.
```

### Mitigação recomendada

```text
Criar ambiente de staging com os dois serviços persistentemente disponíveis.
Avaliar incluir o loop real numa pipeline de CI dedicada (fora do caminho crítico do PR normal).
```

### Decisão relacionada

```text
DEC-021 — Wiring síncrono Backend Core ↔ Intelligence Engine implementado e validado.
```

### Estado executivo

```text
Não bloqueia integração nem piloto técnico.
Monitorizar antes de produção.
```

---

# 7. Riscos mitigados

## RSK-014 — Wiring real do Backend Core ao Intelligence Engine (mitigado)

```text
Estado: mitigated
Prioridade: P3
Impacto: alto (residual: médio)
Probabilidade: baixa (após mitigação)
Responsável: a definir
Data de identificação: 2026-06-24
Última revisão: 2026-06-25
```

### Descrição

O contrato de integração entre o Backend Core Django e o FastAPI Intelligence Engine estava documentado (IE-009), mas o lado Django (chamada real ao endpoint composto, adaptador que monta o `data` bundle a partir dos modelos reais) não estava implementado. Este risco foi **resolvido pela execução do backlog `backend_core/docs/backend_core/fundamentos/integracao_intelligence_engine/01_backlog.md`** (BC-IE-001 a BC-IE-010).

### Mitigação aplicada

```text
Client síncrono IntelligenceEngineClient (apps/integrations_bridge/intelligence_sync.py).
Builder do data bundle CampaignIntelligencePayloadBuilder (apps/campaigns/intelligence_payload.py).
Serviço de domínio CampaignIntelligenceService (ENABLED/DRY_RUN, mapeamento de erros).
Endpoint POST /api/v1/campaigns/{id}/intelligence/ (auth + RBAC + workspace scoping).
Política de timeout/retry/fallback (retry só em falhas transitórias, nunca em 4xx).
13 cenários E2E com mocks HTTP.
Loop real com os dois serviços a correr de facto (BC-IE-009): um bug real de contrato (granularidade
date/datetime em content_outputs[].created_at) foi encontrado e corrigido; após o fix, a chamada real
devolveu 200/completed com analysis/scores/grade/moments/recommendations/summary, sem o token aparecer
em qualquer log.
```

### Risco remanescente

```text
A validação real é local/opt-in (RUN_REAL_IE=1), não corre em CI por padrão — ver RSK-017.
Sem observabilidade dedicada (métricas/alertas) para a chamada síncrona.
Sem calibração de negócio dos scores/recomendações devolvidos via o endpoint real.
```

### Decisão relacionada

```text
DEC-019 — FastAPI Intelligence Engine MVP concluído; contrato síncrono recomendado.
DEC-021 — Wiring síncrono Backend Core ↔ Intelligence Engine implementado e validado (ver [[log_decisoes]]).
```

### Estado executivo

```text
Mitigado. A integração real ponta-a-ponta com o Backend Core está implementada e validada para piloto técnico.
Continuar a monitorizar antes de produção (observabilidade, staging contínuo, calibração).
```

---

## RSK-002 — Dependências de PDF dificultarem instalação local

```text
Estado: mitigated
Prioridade: P4
Impacto: médio
Probabilidade: baixa
Responsável: a definir
Data de identificação: 2026-06-23
Última revisão: 2026-06-24
```

### Descrição

A geração de PDF poderia exigir dependências pesadas, browser/headless ou ferramentas difíceis de instalar.

### Mitigação aplicada

```text
Uso de pdf-lib pure JS.
Fallback HTML.
Sem Playwright.
Sem browser.
Sem FFmpeg.
```

### Estado executivo

```text
Mitigado para MVP e piloto técnico.
Reavaliar se layouts PDF avançados exigirem outra stack.
```

---

## RSK-005 — IA local adicionar features fora do escopo

```text
Estado: mitigated
Prioridade: P4
Impacto: médio
Probabilidade: baixa
Responsável: Aldino Ramos
Data de identificação: 2026-06-23
Última revisão: 2026-06-24
```

### Descrição

A execução assistida por IA poderia adicionar features fora do escopo, como vídeo, editor visual, Remotion, FFmpeg, frontend ou lógica de produto no renderer.

### Mitigação aplicada

```text
Backlogs e prompts com restrições claras.
Relatórios de execução confirmam escopo respeitado.
Vídeo e editor visual continuam fora do escopo.
```

### Estado executivo

```text
Mitigado.
Continuar a reforçar restrições nos próximos prompts.
```

---

# 8. Riscos aceites temporariamente

## Risco aceite — Storage local em piloto técnico controlado

```text
Risco relacionado: RSK-004
Estado: accepted_for_technical_pilot
```

### Justificação

Storage local é inadequado para produção, mas aceitável para ambiente de integração ou piloto técnico controlado.

### Condições de aceitação

```text
- ambiente controlado;
- dados não críticos;
- sem escala horizontal;
- sem promessa de persistência de produção;
- backups/limpeza controlados manualmente;
- utilizadores limitados.
```

---

## Risco aceite — Background in-process em piloto técnico controlado

```text
Risco relacionado: RSK-006
Estado: accepted_for_technical_pilot
```

### Justificação

Background in-process é suficiente para piloto técnico controlado, desde que não haja workloads prolongados ou críticos.

### Condições de aceitação

```text
- baixo volume;
- monitorização manual;
- logs disponíveis;
- possibilidade de repetir jobs;
- sem SLA formal;
- sem produção.
```

---

# 9. Produção — bloqueadores explícitos

O projecto **não deve ser considerado production-ready** enquanto os seguintes pontos não forem tratados:

|ID|Bloqueador de produção|Risco relacionado|Estado|
|---|---|---|---|
|PROD-001|Implementar storage S3/R2 real|RSK-004|Aberto|
|PROD-002|Definir observabilidade mínima|RSK-007|Aberto|
|PROD-003|Definir métricas operacionais|RSK-007|Aberto|
|PROD-004|Definir política de background jobs/fila persistente|RSK-006|Aberto|
|PROD-005|Formalizar secrets, deploy e CI/CD|RSK-009|Aberto|
|PROD-006|Validar política de recuperação/reconciliação|RSK-006 / RSK-003|Aberto|

---

# 10. Matriz rápida de risco

|ID|Risco|Impacto|Probabilidade|Estado|Prioridade|
|---|---|--:|--:|---|---|
|RSK-001|Acoplamento ao payload Django|médio|média|monitoring|P3|
|RSK-002|Dependências PDF|médio|baixa|mitigated|P4|
|RSK-003|Callback falhar após geração|alto|baixa/média|monitoring|P3|
|RSK-004|Storage local não serve produção|alto|alta|open|P2|
|RSK-005|IA sair do escopo|médio|baixa|mitigated|P4|
|RSK-006|Background in-process perder job em restart|alto|média|open|P2|
|RSK-007|Falta de observabilidade|médio/alto|alta|open|P2|
|RSK-008|Content partial/failed sem E2E HTTP real|médio|baixa/média|monitoring|P3|
|RSK-009|Falta de política secrets/deploy/CI-CD|alto|média|open|P2|
|RSK-010|Idempotência sob retry extremo|médio/alto|baixa|monitoring|P3|
|RSK-011|Qualidade visual dos templates|médio|média|monitoring|P3|
|RSK-012|Dispersão de foco na próxima fase|médio/alto|média|monitoring|P2|
|RSK-013|Heurísticas do Intelligence Engine não calibradas|médio/alto|alta|monitoring|P3|
|RSK-014|Wiring real Backend Core ↔ Intelligence Engine (mitigado: implementado e validado)|alto|baixa|mitigated|P3|
|RSK-015|Sem coverage/type-checking no Intelligence Engine|baixo/médio|alta|monitoring|P4|
|RSK-016|Catálogo de content packs espelhado, não importado do Django|médio|baixa/média|monitoring|P3|
|RSK-017|Validação real do wiring é local/pontual, não contínua|médio|média|monitoring|P3|

---

# 11. Histórico de alterações

## 2026-06-25 — Actualização pós-wiring Backend Core ↔ Intelligence Engine

```text
Estado: actualizado
```

### Alterações

```text
- RSK-014 (wiring real Backend Core ↔ Intelligence Engine não implementado) movido de "aberto" para "mitigado":
  implementado e validado nesta sessão (BC-IE-001 a BC-IE-010), incluindo loop real com os dois serviços a correr.
- Adicionado RSK-017 (validação real é local/pontual, não contínua) — monitoring.
- Confirmado que não existem bloqueios activos.
- Confirmado que produção continua bloqueada (renderer, Intelligence Engine isolado e wiring síncrono).
- Riscos não relacionados com esta fase (RSK-001 a RSK-013, RSK-015, RSK-016) mantidos sem alteração de estado.
```

### Evidência

```text
Backlog executado: backend_core/docs/backend_core/fundamentos/integracao_intelligence_engine/01_backlog.md
459 testes aprovados (pytest -q), 3 skipped (loop real opt-in), ruff limpo, manage.py check limpo.
Loop real validado (200/completed; token ausente dos logs); bug de granularidade date/datetime corrigido.
Documento de estado: backend_core/docs/backend_core/fundamentos/integracao_intelligence_engine/estado_integracao_intelligence_engine.md
```

---

## 2026-06-25 — Actualização pós-Intelligence-Engine

```text
Estado: actualizado
```

### Alterações

```text
- Adicionado RSK-013 (heurísticas não calibradas).
- Adicionado RSK-014 (wiring real Backend Core ↔ Intelligence Engine pendente) — open.
- Adicionado RSK-015 (sem coverage/type-checking no Intelligence Engine).
- Adicionado RSK-016 (catálogo de content packs espelhado).
- Confirmado que não existem bloqueios activos.
- Confirmado que produção continua bloqueada (renderer e Intelligence Engine).
- Riscos do renderer (RSK-001 a RSK-012) mantidos sem alteração de estado.
```

### Evidência

```text
FastAPI Intelligence Engine MVP concluído (IE-001 a IE-010).
197 testes aprovados, ruff limpo.
Contrato de integração documentado.
Documento de estado: intelligence_engine/docs/gestao/fundamentos/estado_fastapi_intelligence_engine.md
```

---

## 2026-06-24 — Actualização pós-hardening do renderer

```text
Estado: actualizado
```

### Alterações

```text
- Riscos de callback e payload foram reclassificados como mitigados/monitorização.
- Risco de storage local mantido aberto como bloqueador de produção.
- Adicionado risco de background in-process.
- Adicionado risco de observabilidade.
- Adicionado risco de política de secrets/deploy/CI-CD.
- Adicionado risco de dispersão na próxima fase.
- Confirmado que não existem bloqueios activos.
- Confirmado que produção continua bloqueada.
```

### Evidência

```text
Hardening pós-MVP concluído.
E2E PostgreSQL validado.
136 testes aprovados.
Coverage configurado.
Documentação final pós-hardening concluída.
```

---

## 2026-06-23 — Registo inicial de riscos do Content/Report Renderer

```text
Estado: criado
```

### Riscos iniciais

```text
RSK-001 — Acoplamento ao payload Django.
RSK-002 — Dependências de PDF.
RSK-003 — Falha de callback.
RSK-004 — Storage local.
RSK-005 — IA sair do escopo.
```

---

# 12. Próxima revisão recomendada

Rever este documento quando acontecer um destes eventos:

```text
- próxima fase for decidida;
- backlog do FastAPI Intelligence Engine for criado;
- S3/R2 for priorizado;
- ambiente de integração/piloto for definido;
- surgir falha real de callback;
- for definido plano de produção;
- for definida stack de observabilidade;
- houver alteração relevante no contrato Django ↔ Renderer.
```

## Recomendação actual

```text
Manter riscos de produção abertos (renderer, Intelligence Engine e wiring síncrono).
O wiring Backend Core ↔ Intelligence Engine já foi executado e validado nesta sessão (RSK-014 mitigado).
Decidir explicitamente a próxima fase (S3/R2, frontend mínimo ou observabilidade) e registar em [[log_decisoes]] (PDEC-008).
```