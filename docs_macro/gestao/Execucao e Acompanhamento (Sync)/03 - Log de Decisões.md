---

doc_id: "exec-log-decisoes"  
title: "Log de Decisões"  
project: "ChartRex / MomentFlow"  
area: "gestao_execucao"  
doc_type: "decision_log"  
status: "active"  
owner: "Aldino Ramos"  
created_at: "2026-06-23"  
updated_at: "2026-06-25"  
last_reviewed_at: "2026-06-25"  
review_frequency: "weekly"  
update_frequency: "on_decision"  
version: "1.3"  
confidentiality: "internal"  
source_of_truth: true

decision_count: 21  
last_decision_id: "DEC-021"  
decision_id_prefix: "DEC"  
decision_mode: "append_only"  
current_phase: "Transição pós-wiring-Intelligence-Engine para próxima fase"  
last_completed_phase: "Backend Core ↔ Intelligence Engine — wiring síncrono (BC-IE-001 a BC-IE-010)"  
next_recommended_phase: "por decidir"

---

related_docs:

- "[[status_report]]"
    
- "[[plano_execucao]]"
    
- "[[riscos_bloqueios]]"
    
- "[[matriz_validacao]]"
    
- "[[diario_execucao_ia]]"
    

tags:

- "project/momentflow"
    
- "gestao/decisoes"
    
- "arquitectura"
    
- "execucao"
    
- "obsidian"
    

## ai_update_mode: "append_only"  
ai_update_scope: "adicionar novas decisões com contexto, opções consideradas, decisão tomada, justificação, impacto, reversibilidade, estado e documentos relacionados."  
ai_may_create_sections: false  
ai_may_delete_content: false  
ai_should_preserve_history: true

# Log de Decisões — ChartRex / MomentFlow

## 1. Instruções para IA actualizar este documento

Este documento é a **fonte de verdade das decisões estruturais** do projecto.

A IA deve tratar este ficheiro como **append-only**.

Ao actualizar este ficheiro, a IA deve:

```text
1. Ler primeiro o README.md desta pasta.
2. Ler os metadados YAML deste documento.
3. Respeitar ai_update_mode: append_only.
4. Actualizar updated_at no YAML.
5. Actualizar decision_count e last_decision_id quando adicionar decisões.
6. Adicionar novas decisões com ID sequencial.
7. Não apagar decisões antigas.
8. Não reescrever decisões antigas sem criar uma nova decisão de revisão.
9. Não marcar decisões como substituídas sem indicar a decisão que as substitui.
10. Não inventar decisões.
11. Distinguir decisão tomada de decisão pendente.
12. Registar contexto, opções consideradas, decisão, justificação, impacto e reversibilidade.
```

A IA pode:

```text
- adicionar novas decisões;
- adicionar notas de revisão a decisões existentes;
- marcar decisões como activas, substituídas, revistas ou canceladas;
- criar decisões de substituição;
- actualizar a tabela de resumo;
- actualizar metadados de contagem.
```

A IA não deve:

```text
- apagar decisões;
- remover racional histórico;
- converter decisão pendente em tomada sem evidência;
- alterar a tese arquitectural sem decisão explícita;
- expor tokens, passwords ou segredos;
- transformar este documento em status report ou diário de execução.
```

Quando não houver evidência suficiente, usar:

```text
Estado: por confirmar
Evidência: não disponível
Acção necessária: validar manualmente
```

---

# 2. Convenção de decisões

## Formato de ID

```text
DEC-001
DEC-002
DEC-003
```

## Estados permitidos

```text
activa
revista
substituída
cancelada
pendente
```

## Reversibilidade

```text
alta    = pode ser revertida com baixo impacto;
média   = reversível, mas exige refactor/migração;
baixa   = difícil de reverter sem impacto significativo;
nula    = decisão histórica ou estratégica já consolidada.
```

## Modelo de decisão

Cada decisão deve conter:

```text
ID;
data;
estado;
contexto;
opções consideradas;
decisão tomada;
justificação;
impacto;
reversibilidade;
owner;
documentos relacionados.
```

---

# 3. Resumo executivo das decisões activas

|ID|Decisão|Estado|Reversibilidade|
|---|---|---|---|
|DEC-001|Django governa produto; Renderer gera activos; FastAPI Intelligence calcula/recomenda.|activa|baixa|
|DEC-002|Backend Core Django mantém responsabilidade sobre produto, utilizadores, workspaces, RBAC, billing, estado e audit.|activa|baixa|
|DEC-003|Content/Report Renderer é serviço separado do Django.|activa|média|
|DEC-004|Renderer MVP usa storage local, mas produção exige provider real S3/R2.|activa|média|
|DEC-005|Vídeo, Remotion e FFmpeg ficam fora do escopo actual.|activa|alta|
|DEC-006|Status report será documento vivo único com snapshots históricos.|activa|alta|
|DEC-007|Renderer usa Node.js + TypeScript.|activa|média|
|DEC-008|Renderer usa contratos internos com `X-Internal-Token`.|activa|média|
|DEC-009|`POST /jobs` responde 202 e executa render/callback em background leve.|activa|média|
|DEC-010|Callback usa retry simples com backoff, sem fila persistente nesta fase.|activa|média|
|DEC-011|`StorageProvider` passa a ser a abstracção de storage.|activa|média|
|DEC-012|PostgreSQL é base recomendada para E2E multi-processo.|activa|alta|
|DEC-013|Renderer está pronto para integração e piloto técnico, mas não para produção.|activa|alta|
|DEC-014|Coverage Vitest passa a ser métrica mínima de qualidade do renderer.|activa|alta|
|DEC-015|`template_key`/`template_id` devem ser ecoados no `content_generation` quando aplicável.|activa|alta|
|DEC-016|FastAPI Intelligence Engine é a próxima fase recomendada.|activa|alta|
|DEC-017|Storage S3/R2, observabilidade e política operacional são bloqueadores de produção.|activa|média|
|DEC-018|Próxima implementação só deve avançar após actualizar os documentos de acompanhamento.|activa|alta|
|DEC-019|FastAPI Intelligence Engine MVP (IE-001 a IE-010) concluído; integração síncrona ("sync-first") recomendada com o Backend Core.|activa|média|
|DEC-020|Próxima fase do projecto ainda não decidida após o fecho do Intelligence Engine; requer decisão explícita antes de nova implementação.|activa|alta|
|DEC-021|Wiring síncrono Backend Core ↔ Intelligence Engine implementado e validado (BC-IE-001 a BC-IE-010), incluindo loop real com os dois serviços a correr.|activa|média|

---

# 4. Decisões detalhadas

## DEC-001 — Tese arquitectural principal

```text
Data: 2026-06-23
Estado: activa
Owner: Aldino Ramos
Reversibilidade: baixa
```

### Contexto

O projecto precisa separar responsabilidades entre produto, geração de activos e inteligência, evitando que um único serviço concentre regras de negócio, geração e análise.

### Opções consideradas

```text
1. Colocar tudo no Backend Core Django.
2. Criar serviços técnicos separados, mas manter Django como fonte de verdade.
3. Criar microsserviços autónomos com estado próprio.
```

### Decisão tomada

```text
Django governa o produto.
Renderer gera activos.
FastAPI Intelligence calcula, recomenda e detecta oportunidades.
Frontend orquestra a experiência do utilizador.
```

### Justificação

Esta separação mantém o domínio de produto centralizado no Django, enquanto permite escalar capacidades técnicas especializadas em serviços separados.

### Impacto

```text
- Backend Core continua fonte de verdade.
- Serviços externos não decidem RBAC, billing ou estado de negócio.
- Contratos internos passam a ser críticos.
- Callbacks e idempotência tornam-se peças centrais da arquitectura.
```

### Documentos relacionados

```text
[[plano_execucao]]
[[status_report]]
[[matriz_validacao]]
```

---

## DEC-002 — Backend Core Django como núcleo de produto

```text
Data: 2026-06-23
Estado: activa
Owner: Aldino Ramos
Reversibilidade: baixa
```

### Contexto

O produto precisa manter consistência sobre utilizadores, workspaces, entidades de negócio, estados e billing.

### Opções consideradas

```text
1. Distribuir regras de produto pelos serviços técnicos.
2. Manter o Django como núcleo de produto.
3. Permitir que cada serviço mantenha estado próprio.
```

### Decisão tomada

O Backend Core Django mantém responsabilidade sobre:

```text
- users;
- workspaces;
- RBAC;
- billing;
- créditos;
- entidades de negócio;
- estado;
- audit;
- notifications;
- callbacks;
- orquestração dos jobs externos.
```

### Justificação

Evita duplicação de regras e reduz inconsistência entre serviços.

### Impacto

```text
- Renderer não tem autenticação pública.
- Renderer não calcula permissões.
- Renderer não gere créditos.
- FastAPI Intelligence não deve assumir estado de produto.
```

### Documentos relacionados

```text
[[plano_execucao]]
[[status_report]]
```

---

## DEC-003 — Content/Report Renderer separado do Django

```text
Data: 2026-06-23
Estado: activa
Owner: Aldino Ramos
Reversibilidade: média
```

### Contexto

A geração de activos PNG/PDF/HTML envolve dependências e preocupações técnicas diferentes das regras de produto do Django.

### Opções consideradas

```text
1. Implementar geração de activos directamente no Django.
2. Criar serviço técnico separado para renderer.
3. Adiar renderer e simular outputs no Backend Core.
```

### Decisão tomada

Criar `content_renderer` como serviço separado.

### Justificação

Permite isolar dependências de renderização, manter o Django mais limpo e preparar futura escalabilidade técnica.

### Impacto

```text
- Necessário contrato interno de job.
- Necessário callback do renderer para o Django.
- Necessário storage partilhável ou metadata compatível.
- Necessário E2E Django ↔ Renderer.
```

### Documentos relacionados

```text
[[plano_execucao]]
[[matriz_validacao]]
[[diario_execucao_ia]]
```

---

## DEC-004 — Storage local no MVP, S3/R2 antes de produção

```text
Data: 2026-06-23
Estado: activa
Owner: Aldino Ramos
Reversibilidade: média
```

### Contexto

O renderer precisava de persistir activos gerados. Para MVP e testes locais, storage local é suficiente. Para produção, não é adequado.

### Opções consideradas

```text
1. Implementar S3/R2 logo no MVP.
2. Usar storage local no MVP e abstrair depois.
3. Guardar ficheiros no Django.
```

### Decisão tomada

Usar storage local no MVP, mas tratar S3/R2 como requisito antes de produção.

### Justificação

Permitiu validar rapidamente o ciclo de geração sem bloquear em credenciais, buckets, CDN ou configuração cloud.

### Impacto

```text
- MVP e piloto técnico controlado podem usar storage local.
- Produção exige provider real.
- Storage local deve ser substituível.
```

### Documentos relacionados

```text
[[riscos_bloqueios]]
[[matriz_validacao]]
```

---

## DEC-005 — Vídeo, Remotion e FFmpeg fora do escopo actual

```text
Data: 2026-06-23
Estado: activa
Owner: Aldino Ramos
Reversibilidade: alta
```

### Contexto

A geração de vídeo aumenta complexidade técnica, dependências, tempo de render, storage e custos.

### Opções consideradas

```text
1. Implementar vídeo desde o MVP.
2. Implementar apenas imagens/PDF/HTML.
3. Criar suporte técnico mínimo a vídeo sem expor produto.
```

### Decisão tomada

Vídeo, Remotion e FFmpeg ficam fora do escopo actual.

### Justificação

O objectivo imediato é validar o ciclo de geração de activos estáticos e documentos.

### Impacto

```text
- Renderer fica mais simples.
- Dependências pesadas são evitadas.
- Vídeo pode ser reavaliado depois de Intelligence Engine, storage produção e frontend.
```

### Documentos relacionados

```text
[[plano_execucao]]
[[riscos_bloqueios]]
```

---

## DEC-006 — Status report como documento vivo único

```text
Data: 2026-06-23
Estado: activa
Owner: Aldino Ramos
Reversibilidade: alta
```

### Contexto

Era necessário acompanhar o projecto no Obsidian sem criar excesso de documentos por período.

### Opções consideradas

```text
1. Criar vários status reports por semana.
2. Manter um único status_report.md vivo com snapshots.
3. Usar apenas diário de execução IA.
```

### Decisão tomada

Manter um único `status_report.md` vivo, com o estado actual no topo e snapshots históricos no fim.

### Justificação

Reduz dispersão e mantém uma fonte executiva de verdade.

### Impacto

```text
- Status actual fica sempre no mesmo ficheiro.
- Histórico é preservado por snapshots.
- IA deve actualizar o topo e acrescentar snapshot sem apagar anteriores.
```

### Documentos relacionados

```text
[[status_report]]
```

---

## DEC-007 — Renderer em Node.js + TypeScript

```text
Data: 2026-06-23
Estado: activa
Owner: Aldino Ramos
Reversibilidade: média
```

### Contexto

O renderer precisava de stack adequada para HTTP interno, validação, renderização de SVG/PNG e eventual evolução de documentos.

### Opções consideradas

```text
1. Python/FastAPI.
2. Node.js + TypeScript.
3. Implementar no Django.
```

### Decisão tomada

Implementar `content_renderer` em Node.js + TypeScript.

### Justificação

Node.js + TypeScript é adequado para serviço HTTP leve, validação com Zod, geração SVG/PNG e integração futura com ferramentas de renderização.

### Impacto

```text
- Serviço separado do Backend Core.
- Build/lint/testes próprios via npm.
- Contratos tipados em TypeScript.
```

### Documentos relacionados

```text
[[plano_execucao]]
[[diario_execucao_ia]]
[[matriz_validacao]]
```

---

## DEC-008 — Autenticação interna por X-Internal-Token

```text
Data: 2026-06-23
Estado: activa
Owner: Aldino Ramos
Reversibilidade: média
```

### Contexto

O renderer é um serviço interno e não deve ser exposto como API pública.

### Opções consideradas

```text
1. Sem autenticação entre serviços.
2. Token interno simples.
3. OAuth/mTLS já no MVP.
```

### Decisão tomada

Usar `X-Internal-Token` para autenticação interna entre Backend Core e renderer.

### Justificação

Suficiente para MVP/integração controlada, simples de testar e compatível com os contratos existentes.

### Impacto

```text
- Todas as chamadas internas relevantes exigem token.
- Token nunca deve ser logado.
- Produção pode evoluir para mTLS ou mecanismo mais robusto.
```

### Documentos relacionados

```text
[[riscos_bloqueios]]
[[matriz_validacao]]
```

---

## DEC-009 — Callback em background leve

```text
Data: 2026-06-23
Estado: activa
Owner: Aldino Ramos
Reversibilidade: média
```

### Contexto

O fluxo síncrono de render/callback podia criar corrida entre o callback do renderer e o estado do `ExternalJobReference` no Django.

### Opções consideradas

```text
1. Manter callback síncrono.
2. Usar background leve in-process.
3. Implementar fila persistente com Redis/BullMQ/RabbitMQ/Kafka.
```

### Decisão tomada

`POST /jobs` responde `202 Accepted` rapidamente e agenda render/callback em background leve in-process.

### Justificação

Resolve o risco imediato de corrida sem introduzir complexidade operacional de filas persistentes.

### Impacto

```text
- Callback deixa de bloquear a resposta HTTP.
- O serviço fica mais alinhado com o contrato 202.
- Em caso de restart entre 202 e callback, o job em curso pode ser perdido.
- Fila persistente continua como decisão futura para produção ou workloads críticos.
```

### Documentos relacionados

```text
[[riscos_bloqueios]]
[[matriz_validacao]]
[[diario_execucao_ia]]
```

---

## DEC-010 — Retry simples de callback com backoff

```text
Data: 2026-06-23
Estado: activa
Owner: Aldino Ramos
Reversibilidade: média
```

### Contexto

Falhas temporárias do Django poderiam fazer o callback falhar à primeira tentativa.

### Opções consideradas

```text
1. Tentativa única.
2. Retry simples em memória.
3. Dead-letter queue/fila persistente.
```

### Decisão tomada

Implementar retry simples com backoff para callback, sem dead-letter queue nesta fase.

### Justificação

Aumenta resiliência sem introduzir infraestrutura adicional.

### Impacto

```text
- Falhas temporárias têm nova tentativa.
- 4xx não são mascarados como sucesso.
- Idempotência do callback no Django torna-se ainda mais importante.
- Restart do processo ainda perde retries em curso.
```

### Documentos relacionados

```text
[[riscos_bloqueios]]
[[matriz_validacao]]
```

---

## DEC-011 — StorageProvider como abstracção de storage

```text
Data: 2026-06-23
Estado: activa
Owner: Aldino Ramos
Reversibilidade: média
```

### Contexto

O renderer usava storage local, mas a produção exige S3/R2 ou equivalente.

### Opções consideradas

```text
1. Manter dependência directa de LocalStorage.
2. Criar abstracção StorageProvider.
3. Implementar S3/R2 já nesta fase.
```

### Decisão tomada

Criar `StorageProvider` como interface de storage e manter LocalStorage como implementação actual.

### Justificação

Permite migrar para S3/R2 depois sem reescrever os renderers.

### Impacto

```text
- Renderers deixam de depender de implementação concreta.
- LocalStorage continua funcional.
- S3/R2 fica preparado como evolução.
```

### Documentos relacionados

```text
[[plano_execucao]]
[[riscos_bloqueios]]
```

---

## DEC-012 — PostgreSQL para E2E multi-processo

```text
Data: 2026-06-23
Estado: activa
Owner: Aldino Ramos
Reversibilidade: alta
```

### Contexto

SQLite apresentou limitações em testes multi-processo, impedindo validação fiável do callback em ambiente real.

### Opções consideradas

```text
1. Continuar com SQLite.
2. Usar PostgreSQL via Docker.
3. Usar PostgreSQL local descartável.
```

### Decisão tomada

Usar PostgreSQL como base recomendada para E2E multi-processo.

### Justificação

PostgreSQL permite validar o loop Django ↔ Renderer ↔ Django com processos separados e estado partilhado correctamente.

### Impacto

```text
- E2E real fica mais fiável.
- Harness pode usar Docker ou cluster local.
- SQLite deixa de ser referência para E2E multi-processo.
```

### Documentos relacionados

```text
[[matriz_validacao]]
[[diario_execucao_ia]]
```

---

## DEC-013 — Renderer pronto para integração/piloto, não para produção

```text
Data: 2026-06-24
Estado: activa
Owner: Aldino Ramos
Reversibilidade: alta
```

### Contexto

O renderer concluiu MVP e hardening pós-MVP, com build/lint/testes/coverage e E2E PostgreSQL validados, mas ainda existem pendências de produção.

### Opções consideradas

```text
1. Declarar production-ready.
2. Declarar pronto para integração/piloto técnico.
3. Bloquear avanço até S3/R2 e observabilidade.
```

### Decisão tomada

Declarar o renderer pronto para ambiente de integração e piloto técnico, mas não para produção.

### Justificação

O serviço está funcional e validado, mas produção exige storage real, observabilidade, métricas e política operacional.

### Impacto

```text
- Pode avançar a próxima fase de produto.
- Não deve haver deploy de produção ainda.
- Pendências de produção ficam registadas em riscos/bloqueios.
```

### Documentos relacionados

```text
[[status_report]]
[[plano_execucao]]
[[riscos_bloqueios]]
```

---

## DEC-014 — Coverage Vitest como métrica mínima de qualidade

```text
Data: 2026-06-24
Estado: activa
Owner: Aldino Ramos
Reversibilidade: alta
```

### Contexto

O renderer já tinha testes, mas sem coverage formal.

### Opções consideradas

```text
1. Não configurar coverage.
2. Configurar coverage sem thresholds.
3. Configurar coverage com thresholds iniciais realistas.
```

### Decisão tomada

Configurar coverage com Vitest e thresholds iniciais.

### Justificação

Ajuda a controlar regressões e dá métrica objectiva da qualidade da suite.

### Impacto

```text
- npm run test:coverage passa a fazer parte da validação.
- Cobertura actual fica documentada.
- Thresholds podem evoluir no futuro.
```

### Documentos relacionados

```text
[[matriz_validacao]]
[[diario_execucao_ia]]
```

---

## DEC-015 — Echo de template_key/template_id no content_generation

```text
Data: 2026-06-23
Estado: activa
Owner: Aldino Ramos
Reversibilidade: alta
```

### Contexto

O Django pode precisar de resolver o template usado em cada output de `content_generation`.

### Opções consideradas

```text
1. Não devolver informação de template.
2. Devolver apenas template_key resolvido.
3. Ecoar template_key/template_id quando recebidos e adicionar metadata de resolução.
```

### Decisão tomada

Ecoar `template_key` e `template_id` quando aplicável e adicionar metadata de resolução/fallback.

### Justificação

Melhora compatibilidade com o Backend Core e torna o output mais auditável.

### Impacto

```text
- Outputs ficam mais explícitos.
- Template_id nunca é inventado.
- Fallback fica visível em metadata.
```

### Documentos relacionados

```text
[[matriz_validacao]]
[[diario_execucao_ia]]
```

---

## DEC-016 — FastAPI Intelligence Engine como próxima fase recomendada

```text
Data: 2026-06-24
Estado: activa
Owner: Aldino Ramos
Reversibilidade: alta
```

### Contexto

Backend Core e renderer estão concluídos para MVP/piloto técnico. O próximo salto de valor do produto está na capacidade de gerar insights, detectar momentos e recomendar acções.

### Opções consideradas

```text
1. Avançar para FastAPI Intelligence Engine.
2. Implementar S3/R2 antes de qualquer nova funcionalidade.
3. Criar frontend mínimo primeiro.
4. Melhorar templates visuais primeiro.
```

### Decisão tomada

Recomendar FastAPI Intelligence Engine como próxima fase.

### Justificação

O produto já consegue gerar activos; o próximo valor diferencial está em saber **quando**, **porquê** e **com que acção** gerar campanhas.

### Impacto

```text
- Próximo backlog recomendado será para Intelligence Engine.
- S3/R2 e observabilidade continuam pendências de produção.
- Frontend pode vir depois ou em paralelo controlado.
```

### Documentos relacionados

```text
[[plano_execucao]]
[[status_report]]
```

---

## DEC-017 — S3/R2, observabilidade e política operacional como bloqueadores de produção

```text
Data: 2026-06-24
Estado: activa
Owner: Aldino Ramos
Reversibilidade: média
```

### Contexto

O renderer está pronto para integração/piloto, mas ainda não tem storage produção, métricas operacionais nem política robusta de execução persistente.

### Opções consideradas

```text
1. Tratar estas pendências como opcionais.
2. Tratar como bloqueadores de produção.
3. Resolver todas antes de avançar para qualquer nova fase.
```

### Decisão tomada

Tratar S3/R2, observabilidade e política operacional como bloqueadores de produção, mas não como bloqueadores de integração/piloto técnico.

### Justificação

Permite avançar produto sem ocultar os requisitos mínimos de produção.

### Impacto

```text
- Produção continua bloqueada.
- Piloto técnico controlado pode avançar.
- Riscos devem permanecer abertos/monitorizados.
```

### Documentos relacionados

```text
[[riscos_bloqueios]]
[[status_report]]
[[plano_execucao]]
```

---

## DEC-018 — Actualizar documentação antes da próxima implementação

```text
Data: 2026-06-24
Estado: activa
Owner: Aldino Ramos
Reversibilidade: alta
```

### Contexto

Após concluir a pipeline de hardening, havia risco de avançar para nova implementação sem consolidar os documentos de acompanhamento.

### Opções consideradas

```text
1. Avançar directamente para a próxima implementação.
2. Actualizar primeiro os documentos de acompanhamento.
3. Actualizar apenas o status report.
```

### Decisão tomada

Actualizar os documentos de acompanhamento antes da próxima implementação.

Documentos a actualizar:

```text
status_report.md
plano_execucao.md
diario_execucao_ia.md
matriz_validacao.md
riscos_bloqueios.md
log_decisoes.md
```

### Justificação

Mantém rastreabilidade, reduz perda de contexto e evita incoerência entre execução, validação, riscos e decisões.

### Impacto

```text
- Próxima implementação só deve avançar após consolidação documental.
- Decisão da próxima fase deve ser registada.
- Backlog/pipeline da próxima fase devem nascer com base no estado real.
```

### Documentos relacionados

```text
[[status_report]]
[[plano_execucao]]
[[diario_execucao_ia]]
[[matriz_validacao]]
[[riscos_bloqueios]]
```

---

## DEC-019 — FastAPI Intelligence Engine MVP concluído; integração síncrona recomendada

```text
Data: 2026-06-24
Estado: activa
Owner: Aldino Ramos
Reversibilidade: média
```

### Contexto

O FastAPI Intelligence Engine foi implementado de fundação a fecho de fase (IE-001 a IE-010): autenticação interna, contratos Pydantic, `POST /analysis/campaign`, `POST /scoring/campaign`, `POST /recommendations/campaign`, `POST /moments/detect` e o endpoint composto `POST /intelligence/campaign`. Ao documentar o contrato de integração com o Backend Core (IE-009), identificou-se que o Backend Core já tinha scaffolding assíncrono (`ExternalJobReference` + `POST /jobs/` + callback) preparado para o Intelligence Engine, mas o MVP implementado é síncrono (resposta inline, sem persistência, sem callback).

### Opções consideradas

```text
1. Adaptar o Intelligence Engine ao modelo assíncrono já existente no Backend Core (jobs + callback).
2. Recomendar chamada síncrona directa ao endpoint composto, reaproveitando o InternalServiceClient já existente no Django.
3. Híbrido: síncrono como default do MVP, assíncrono reservado para trabalho pesado futuro (ex.: recolha real de métricas, ML).
```

### Decisão tomada

```text
Adoptar a opção híbrida (3): síncrono como default do MVP do Intelligence Engine, com o caminho assíncrono de jobs/callback reservado para trabalho pesado futuro que não pertence ao MVP.
```

### Justificação

```text
O cálculo do Intelligence Engine é em memória, determinístico e sem I/O (sub-milissegundo); um job assíncrono seria custo sem benefício para o MVP.
A recomendação resolve directamente a decisão pendente IE-PDEC-001 do backlog do Intelligence Engine.
```

### Impacto

```text
- O wiring real do lado Django (chamada síncrona ao endpoint composto, adaptador de payload) ainda não foi implementado — ver RSK-014 em [[riscos_bloqueios]].
- O caminho assíncrono já existente no Backend Core (ExternalJobReference) fica disponível para uma fase futura, sem necessidade de remoção.
- Documentado em intelligence_engine/docs/gestao/fundamentos/contrato_backend_core_intelligence_engine.md.
```

### Documentos relacionados

```text
[[plano_execucao]]
[[riscos_bloqueios]]
[[matriz_validacao]]
```

---

## DEC-020 — Próxima fase do projecto ainda não decidida

```text
Data: 2026-06-25
Estado: activa
Owner: Aldino Ramos
Reversibilidade: alta
```

### Contexto

Com o Backend Core, o Content/Report Renderer e agora o FastAPI Intelligence Engine MVP concluídos, existem várias frentes candidatas para a próxima fase: wiring real do Backend Core ao Intelligence Engine, storage S3/R2, frontend mínimo Campaign War Room, ou observabilidade/produção.

### Opções consideradas

```text
1. Implementar o wiring síncrono do Backend Core ao Intelligence Engine (contrato IE-009).
2. Storage S3/R2 real.
3. Frontend mínimo Campaign War Room.
4. Observabilidade e produção.
```

### Decisão tomada

```text
Não fixar, nesta actualização documental, qual destas opções é a próxima fase. Registar a decisão como pendente (PDEC-007) e exigir decisão explícita antes de iniciar qualquer nova implementação.
```

### Justificação

```text
Esta sessão teve como âmbito actualizar os documentos de acompanhamento após o fecho do Intelligence Engine, não decidir a próxima fase de produto. Forçar uma recomendação sem análise dedicada arriscaria repetir o risco RSK-012 (dispersão de foco).
```

### Impacto

```text
- Nenhuma nova implementação deve avançar antes desta decisão ser tomada explicitamente.
- O backlog/pipeline da próxima fase só deve ser criado depois da decisão.
```

### Documentos relacionados

```text
[[plano_execucao]]
[[status_report]]
[[riscos_bloqueios]]
```

---

## DEC-021 — Wiring síncrono Backend Core ↔ Intelligence Engine implementado e validado

```text
Data: 2026-06-25
Estado: activa
Owner: Aldino Ramos
Reversibilidade: média
```

### Contexto

Após o fecho do FastAPI Intelligence Engine MVP (DEC-019), a decisão pendente PDEC-007 listava o wiring real do Backend Core ao Intelligence Engine como a primeira de várias alternativas de próxima fase. O backlog `backend_core/docs/backend_core/fundamentos/integracao_intelligence_engine/01_backlog.md` (BC-IE-001 a BC-IE-010) foi executado nesta sessão para implementar essa alternativa.

### Opções consideradas

```text
1. Implementar o wiring síncrono do Backend Core ao Intelligence Engine (opção escolhida).
2. Avançar primeiro para storage S3/R2 real.
3. Avançar primeiro para frontend mínimo Campaign War Room.
4. Avançar primeiro para observabilidade e produção.
```

### Decisão tomada

```text
Implementar e validar o wiring síncrono completo: settings dedicados (INTELLIGENCE_ENGINE_*), client
síncrono (IntelligenceEngineClient), builder do data bundle de campanha
(CampaignIntelligencePayloadBuilder), serviço de domínio (CampaignIntelligenceService com
ENABLED/DRY_RUN), endpoint POST /api/v1/campaigns/{id}/intelligence/, política de timeout/retry/fallback,
validação E2E com mocks HTTP e validação real com os dois serviços a correr de facto.
```

### Justificação

```text
O Intelligence Engine já estava pronto do seu lado (IE-001 a IE-010, 197 testes), mas o valor de produto
da inteligência (scoring, recomendações, momentos) só chega a utilizadores reais quando o Django chamar
o serviço de facto. Esta era a opção que tornava a inteligência efectivamente utilizável, em vez de apenas
documentada por contrato.
```

### Impacto

```text
- RSK-014 (wiring não implementado) passa de "aberto" para "mitigado" — ver [[riscos_bloqueios]].
- Um bug real de contrato foi encontrado e corrigido durante a validação real (granularidade
  date/datetime em content_outputs[].created_at), confirmando que a validação foi genuína.
- Documento de estado consolidado criado:
  backend_core/docs/backend_core/fundamentos/integracao_intelligence_engine/estado_integracao_intelligence_engine.md.
- Pendências remanescentes (observabilidade, staging contínuo, calibração de negócio) ficam registadas
  como não bloqueadoras de piloto técnico, mas bloqueadoras de produção.
- PDEC-007 fica resolvida; sucedida por PDEC-008 (próxima fase pós-wiring).
```

### Documentos relacionados

```text
[[plano_execucao]]
[[riscos_bloqueios]]
[[matriz_validacao]]
[[diario_execucao_ia]]
```

---

# 5. Decisões pendentes

## PDEC-001 — Próxima fase efectiva (pós-renderer)

```text
Estado: resolvida — ver DEC-016 e DEC-019
Prioridade: alta (histórica)
```

### Questão

Avançar imediatamente para FastAPI Intelligence Engine ou antecipar S3/R2/observabilidade?

### Opções

```text
1. FastAPI Intelligence Engine.
2. Storage S3/R2 real.
3. Frontend mínimo Campaign War Room.
4. Observabilidade e produção.
5. Templates visuais avançados.
```

### Resolução

```text
A opção 1 (FastAPI Intelligence Engine) foi executada e concluída (IE-001 a IE-010).
Esta decisão pendente fica resolvida; sucedida por PDEC-007 (próxima fase pós-Intelligence-Engine).
```

---

## PDEC-007 — Próxima fase efectiva (pós-Intelligence-Engine)

```text
Estado: resolvida — ver DEC-021
Prioridade: alta (histórica)
```

### Questão

Com o Backend Core, o Renderer e o Intelligence Engine MVP concluídos, qual deve ser a próxima fase?

### Opções

```text
1. Implementar o wiring síncrono do Backend Core ao Intelligence Engine (contrato IE-009, pendências PD-1 a PD-4).
2. Storage S3/R2 real.
3. Frontend mínimo Campaign War Room.
4. Observabilidade e produção.
5. Templates visuais avançados.
```

### Resolução

```text
A opção 1 (wiring síncrono Backend Core ↔ Intelligence Engine) foi executada e concluída (BC-IE-001 a BC-IE-010).
Esta decisão pendente fica resolvida; sucedida por PDEC-008 (próxima fase pós-wiring).
```

---

## PDEC-008 — Próxima fase efectiva (pós-wiring Backend Core ↔ Intelligence Engine)

```text
Estado: pendente
Prioridade: alta
```

### Questão

Com o Backend Core, o Renderer, o Intelligence Engine MVP e agora o wiring síncrono entre os dois concluídos, qual deve ser a próxima fase?

### Opções

```text
1. Storage S3/R2 real.
2. Frontend mínimo Campaign War Room.
3. Observabilidade e produção (incluindo métricas/alertas para a chamada síncrona ao Intelligence Engine).
4. Templates visuais avançados.
5. Ambiente de staging com os dois serviços (Backend Core + Intelligence Engine) persistentemente disponíveis, para validação real contínua.
```

### Recomendação actual

```text
Sem recomendação técnica forte registada nesta sessão — esta actualização documental teve como âmbito consolidar o fecho do wiring síncrono, não decidir a fase seguinte.
```

### Critério de decisão

```text
Se o objectivo for preparar produção: S3/R2 + observabilidade + staging contínuo.
Se o objectivo for demonstração para utilizador: frontend mínimo + melhoria visual.
Se o objectivo for confiança contínua na integração: ambiente de staging com validação real recorrente.
```

---

## PDEC-002 — Momento de implementação de S3/R2

```text
Estado: pendente
Prioridade: média/alta
```

### Questão

S3/R2 deve entrar antes do piloto técnico ou apenas antes de produção?

### Recomendação actual

```text
Manter S3/R2 como obrigatório antes de produção.
Para piloto técnico controlado, storage local pode ser aceite.
```

---

## PDEC-003 — Política operacional para background jobs

```text
Estado: pendente
Prioridade: média/alta
```

### Questão

Background in-process é suficiente para piloto ou será necessária fila persistente?

### Recomendação actual

```text
Aceitar background in-process para piloto técnico controlado.
Avaliar fila persistente antes de workloads reais prolongados ou produção.
```

---

## PDEC-004 — Nível mínimo de observabilidade

```text
Estado: pendente
Prioridade: média
```

### Questão

Que métricas, tracing e dashboards são mínimos antes de produção?

### Recomendação actual

```text
Definir observabilidade mínima antes de produção, não necessariamente antes da próxima fase de produto.
```

---

# 6. Histórico de revisões

## 2026-06-25 — Fecho do wiring síncrono Backend Core ↔ Intelligence Engine

```text
Decisões adicionadas/actualizadas:
DEC-021
PDEC-007 marcada como resolvida; PDEC-008 criada como sucessora.
```

### Resumo

Registada a conclusão do wiring síncrono Backend Core ↔ Intelligence Engine (BC-IE-001 a BC-IE-010): client, builder, serviço de domínio, endpoint API, política de timeout/retry/fallback, validação E2E com mocks e validação real com os dois serviços a correr de facto (incluindo a correcção de um bug real de contrato). Registada a decisão pendente sobre qual deve ser a próxima fase do projecto.

---

## 2026-06-25 — Fecho do FastAPI Intelligence Engine

```text
Decisões adicionadas/actualizadas:
DEC-019, DEC-020
PDEC-001 marcada como resolvida; PDEC-007 criada como sucessora.
```

### Resumo

Registada a conclusão do FastAPI Intelligence Engine MVP (IE-001 a IE-010), a recomendação de integração síncrona ("sync-first") com o Backend Core, e a decisão pendente sobre qual deve ser a próxima fase do projecto.

---

## 2026-06-24 — Actualização pós-hardening do renderer

```text
Decisões adicionadas/actualizadas:
DEC-007 a DEC-018
```

### Resumo

Registadas as decisões decorrentes da implementação e hardening do Content/Report Renderer, incluindo callback em background, retry, StorageProvider, E2E com PostgreSQL, coverage e posição oficial de que o renderer está pronto para integração/piloto técnico, mas não para produção.

---

## 2026-06-23 — Decisões iniciais de arquitectura e acompanhamento

```text
Decisões adicionadas:
DEC-001 a DEC-006
```

### Resumo

Registadas as decisões fundacionais sobre arquitectura, separação de responsabilidades, renderer separado, storage local no MVP, exclusão de vídeo e modelo de status report vivo.

---

# 7. Nota final

Este documento deve permanecer curto o suficiente para consulta rápida, mas completo o suficiente para explicar **por que** as principais decisões foram tomadas.

O próximo update deve acontecer quando:

```text
- a próxima fase for decidida;
- o backlog da próxima fase for criado;
- a pipeline da próxima fase for criada;
- uma decisão activa for revista ou substituída;
- uma decisão pendente for fechada.
```