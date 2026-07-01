# Gestão de Execução — ChartRex / MomentFlow

**NOTA PARA HUMANOS: Todos so ficheiros nesta pasta devem ser atualizadas pela IA local executora e será manualmente sincronizada para o Obsidian! Qualquer nota escrita via Obsidian será perdida.**

Esta pasta contém os documentos mínimos de acompanhamento executivo, técnico e operacional do projecto **ChartRex / MomentFlow**.

O objectivo é manter uma visão clara sobre:

- estado actual do projecto;
    
- plano de execução;
    
- decisões tomadas;
    
- riscos e bloqueios;
    
- validações realizadas;
    
- execução assistida por IA.
    

Esta pasta deve ser usada como **fonte de verdade de acompanhamento** no Obsidian.

---

# 1. Documentos da pasta

Esta pasta deve conter apenas os seguintes documentos principais:

```text
status_report.md
plano_execucao.md
log_decisoes.md
riscos_bloqueios.md
matriz_validacao.md
diario_execucao_ia.md
README.md
```

Não criar documentos adicionais nesta pasta sem decisão explícita.

---

# 2. Função de cada documento

## `status_report.md`

Documento vivo com a fotografia executiva do projecto.

Deve responder:

```text
Qual é o estado actual?
O projecto está verde, amarelo ou vermelho?
O que foi concluído?
O que está em curso?
Quais são os principais riscos?
Quais são os próximos passos?
```

Deve conter o status actual no topo e histórico resumido no fim.

---

## `plano_execucao.md`

Documento que define a ordem de execução do projecto.

Deve responder:

```text
Que fases existem?
Qual é a fase actual?
Que backlog está activo?
Que pipeline está activa?
Que prompts já foram executados?
Que prompts faltam?
Quais são as dependências?
Quais são os critérios de pronto?
```

---

## `log_decisoes.md`

Registo estruturado de decisões.

Deve responder:

```text
Que decisão foi tomada?
Quando?
Porquê?
Que opções foram consideradas?
Qual é o impacto?
A decisão é reversível?
```

Este documento deve ser mantido em modo **append-only**: novas decisões são adicionadas, decisões antigas não são apagadas.

---

## `riscos_bloqueios.md`

Registo de riscos e bloqueios.

Deve responder:

```text
O que pode correr mal?
O que já está a bloquear?
Qual é o impacto?
Qual é a mitigação?
Quem deve actuar?
Qual é o estado?
```

Separar claramente:

```text
Risco = ainda pode acontecer.
Bloqueio = já está a impedir avanço.
```

---

## `matriz_validacao.md`

Documento de controlo de qualidade e validação.

Deve responder:

```text
Como sabemos que uma funcionalidade está pronta?
Que critérios de aceitação foram validados?
Que comandos foram executados?
Que testes passaram?
Que evidências existem?
Que validações ainda estão pendentes?
```

Este documento deve ligar execução técnica a evidência objectiva.

---

## `diario_execucao_ia.md`

Registo das execuções feitas por IA local.

Deve responder:

```text
Que pipeline foi executada?
Que prompt foi executado?
Que modelo foi usado?
Que ficheiros foram alterados?
Que comandos foram executados?
O que passou?
O que falhou?
Que pendências ficaram?
Qual é o próximo prompt?
```

Este documento não substitui os relatórios individuais gerados por cada prompt. Serve como índice executivo das execuções.

---

# 3. Convenções de metadados

Todos os documentos principais devem começar com YAML frontmatter.

Campos mínimos obrigatórios:

```yaml
---
doc_id: ""
title: ""
project: "ChartRex / MomentFlow"
area: "gestao_execucao"
doc_type: ""
status: "active"
owner: "Aldino Ramos"
created_at: "YYYY-MM-DD"
updated_at: "YYYY-MM-DD"
last_reviewed_at: null
review_frequency: "weekly"
update_frequency: "as_needed"
version: "1.0"
confidentiality: "internal"
source_of_truth: true
related_docs: []
tags: []
ai_update_mode: "controlled"
ai_update_scope: ""
ai_may_create_sections: false
ai_may_delete_content: false
ai_should_preserve_history: true
---
```

## Regras dos metadados

- `doc_id` deve ser estável e nunca deve mudar.
    
- `updated_at` deve ser actualizado sempre que houver alteração de conteúdo.
    
- `last_reviewed_at` deve ser actualizado quando o documento for revisto, mesmo sem alteração relevante.
    
- `source_of_truth: true` indica que o documento é referência oficial para aquele tema.
    
- `ai_may_delete_content` deve permanecer `false`, salvo decisão explícita.
    
- `ai_should_preserve_history` deve permanecer `true`.
    
- `ai_update_scope` deve indicar exactamente o que a IA pode actualizar.
    

---

# 4. Instruções gerais para IA

Ao actualizar documentos nesta pasta, a IA deve obedecer às regras abaixo.

## 4.1 Regras obrigatórias

A IA deve:

```text
ler primeiro o README.md;
ler os metadados YAML do documento a actualizar;
respeitar o campo ai_update_mode;
respeitar o campo ai_update_scope;
actualizar updated_at;
preservar histórico;
não apagar conteúdo antigo sem instrução explícita;
não criar novos documentos sem autorização;
não transformar documentos de acompanhamento em documentação técnica extensa;
não inventar validações, testes ou resultados;
distinguir claramente facto, inferência e pendência;
manter linguagem objectiva, curta e accionável.
```

## 4.2 Regras de segurança documental

A IA não deve:

```text
apagar decisões antigas;
apagar snapshots de status;
apagar entradas do diário de execução;
marcar validações como concluídas sem evidência;
fechar riscos sem justificação;
inventar percentagens de progresso;
inventar comandos executados;
inventar resultados de testes;
criar novos ficheiros fora da lista aprovada;
expor tokens, passwords, secrets ou caminhos sensíveis desnecessários.
```

## 4.3 Quando houver incerteza

Se a IA não tiver evidência suficiente, deve escrever:

```text
Estado: por confirmar
Evidência: não disponível
Acção necessária: validar manualmente
```

Nunca deve preencher lacunas com suposições apresentadas como factos.

---

# 5. Modos de actualização por documento

## `status_report.md`

Modo recomendado:

```yaml
ai_update_mode: "controlled"
```

A IA deve:

```text
actualizar o status actual no topo;
actualizar resumo executivo;
actualizar progresso por frente;
actualizar riscos principais;
actualizar próximos passos;
adicionar snapshot curto ao histórico;
não apagar snapshots antigos.
```

Não deve transformar o status report num diário detalhado.

---

## `plano_execucao.md`

Modo recomendado:

```yaml
ai_update_mode: "controlled"
```

A IA deve:

```text
actualizar fase actual;
actualizar backlog activo;
actualizar pipeline activa;
marcar actividades concluídas;
registar dependências;
actualizar próximos passos;
manter histórico de fases ou alterações relevantes.
```

---

## `log_decisoes.md`

Modo recomendado:

```yaml
ai_update_mode: "append_only"
```

A IA deve:

```text
adicionar novas decisões no fim ou na secção apropriada;
usar IDs sequenciais;
não apagar decisões antigas;
não reescrever decisões sem indicar revisão;
registar contexto, decisão, justificação e impacto.
```

Formato de ID recomendado:

```text
DEC-001
DEC-002
DEC-003
```

---

## `riscos_bloqueios.md`

Modo recomendado:

```yaml
ai_update_mode: "controlled"
```

A IA deve:

```text
actualizar estado dos riscos;
adicionar novos riscos;
adicionar novos bloqueios;
actualizar mitigação;
actualizar impacto e probabilidade quando houver nova informação;
não remover riscos fechados;
mover riscos fechados para secção de encerrados.
```

IDs recomendados:

```text
RSK-001
BLK-001
```

---

## `matriz_validacao.md`

Modo recomendado:

```yaml
ai_update_mode: "controlled"
```

A IA deve:

```text
adicionar validações por funcionalidade;
registar critérios de aceitação;
registar comandos executados;
registar resultados reais;
marcar estado como pendente, aprovado ou falhado;
não marcar como aprovado sem evidência;
ligar validações ao diário de execução IA quando aplicável.
```

IDs recomendados:

```text
VAL-001
VAL-002
VAL-003
```

---

## `diario_execucao_ia.md`

Modo recomendado:

```yaml
ai_update_mode: "append_only"
```

A IA deve:

```text
adicionar uma entrada por prompt executado;
registar pipeline;
registar prompt;
registar modelo usado, se conhecido;
registar ficheiros criados/alterados;
registar comandos executados;
registar resultado;
registar pendências;
registar próximo passo.
```

IDs recomendados:

```text
IA-001
IA-002
IA-003
```

---

# 6. Fluxo recomendado de actualização

Após cada execução relevante, actualizar nesta ordem:

```text
1. diario_execucao_ia.md
2. matriz_validacao.md
3. riscos_bloqueios.md, se houver risco/bloqueio novo ou alterado
4. log_decisoes.md, se houve decisão relevante
5. plano_execucao.md
6. status_report.md
```

O `status_report.md` deve ser actualizado por último, porque resume os outros documentos.

---

# 7. Critérios para considerar a pasta actualizada

A pasta está actualizada quando:

```text
diário IA tem a última execução registada;
matriz de validação reflecte os testes/resultados mais recentes;
riscos e bloqueios reflectem o estado actual;
decisões relevantes foram registadas;
plano de execução mostra a fase actual;
status report resume correctamente o estado do projecto;
todos os updated_at foram actualizados nos documentos alterados.
```

---

# 8. Convenções de estado

Usar estes estados sempre que possível.

## Estado geral do projecto

```text
green     = controlado
yellow    = atenção necessária
red       = bloqueado ou crítico
unknown   = informação insuficiente
```

## Estado de actividade

```text
not_started
planned
in_progress
blocked
done
cancelled
deferred
```

## Estado de validação

```text
pending
passed
failed
not_applicable
```

## Estado de risco

```text
open
monitoring
mitigated
closed
accepted
```

## Estado de bloqueio

```text
open
in_resolution
resolved
cancelled
```

---

# 9. Relação entre documentos

```text
status_report.md
  resume:
    plano_execucao.md
    riscos_bloqueios.md
    matriz_validacao.md
    diario_execucao_ia.md
    log_decisoes.md

plano_execucao.md
  define:
    fases
    pipelines
    ordem
    dependências

diario_execucao_ia.md
  regista:
    prompts executados
    resultados
    alterações

matriz_validacao.md
  comprova:
    testes
    critérios
    evidências

riscos_bloqueios.md
  controla:
    riscos
    impedimentos
    mitigação

log_decisoes.md
  preserva:
    decisões estruturais
    racional
    impacto
```

---

# 10. Regras para links Obsidian

Usar links internos no formato:

```text
[[status_report]]
[[plano_execucao]]
[[log_decisoes]]
[[riscos_bloqueios]]
[[matriz_validacao]]
[[diario_execucao_ia]]
```

Quando referenciar uma secção específica:

```text
[[riscos_bloqueios#Riscos abertos]]
[[matriz_validacao#Validações pendentes]]
```

Evitar links quebrados para documentos que não existem.

---

# 11. Regra de ouro

Se a IA tiver de actualizar apenas um documento depois de uma execução técnica, deve actualizar primeiro:

```text
diario_execucao_ia.md
```

Se tiver de actualizar apenas um documento para informar o estado a um decisor, deve actualizar:

```text
status_report.md
```

Se tiver de provar que algo está pronto, deve actualizar:

```text
matriz_validacao.md
```

---

# 12. Nota final

Esta pasta não é documentação técnica detalhada do produto. É documentação de **controlo de execução**.

Documentação técnica detalhada deve permanecer nos módulos próprios, por exemplo:

```text
docs/backend_core/
docs/content_renderer/
docs/fastapi_intelligence/
docs/frontend/
```

Esta pasta deve manter-se curta, limpa e orientada à decisão.