# Backlog: Backend Core — CampaignAction Persistente

# MomentFlow / ChartRex — Backend Core CampaignAction API

## 1. Objectivo do documento

Este documento define o backlog para introduzir no Backend Core uma entidade persistente de **CampaignAction**.

A fase frontend **02_campaign_actions_recommendation_to_execution** permitiu criar artefactos reais a partir de recommendations usando endpoints existentes:

```text id="gp1q55"
- content-pack-requests;
- reports;
- media-kits.
```

No entanto, a fase revelou uma limitação estrutural:

```text id="hvcya2"
Não existe uma entidade persistente que represente a acção operacional criada a partir de uma recommendation.
```

Hoje, a ligação `recommendation → artefacto` é apenas best-effort via `metadata.recommendation_ref`.

Esta fase corrige essa limitação criando uma API backend própria para rastrear o ciclo:

```text id="eooefs"
recommendation → campaign_action → artefacto relacionado
```

---

## 2. Tese da fase

A tese desta fase é:

```text id="i04s4b"
Uma recommendation convertida em execução deve gerar uma entidade rastreável, auditável e consultável.
```

Sem uma entidade `CampaignAction`, o sistema consegue criar artefactos, mas não consegue responder com robustez a perguntas como:

```text id="w01tnd"
- Que recommendations já foram tratadas?
- Que acções estão pendentes?
- Que acções falharam?
- Que output nasceu de qual recommendation?
- Quem criou a acção?
- Quando foi criada?
- Qual é o estado actual?
- A recommendation foi ignorada, concluída ou ainda está pendente?
```

---

# 3. Estado de partida

## 3.1 Já existe

O Backend Core já expõe contratos reais para:

```text id="zkm2hm"
POST /api/v1/content-pack-requests/
POST /api/v1/reports/
POST /api/v1/media-kits/
GET  /api/v1/content-pack-requests/?campaign={id}
GET  /api/v1/reports/?campaign={id}
GET  /api/v1/media-kits/?campaign={id}
```

O frontend já consegue projectar estes artefactos como “Campaign Actions”, mas essa projecção não é uma entidade real.

## 3.2 Não existe

Ainda não existe:

```text id="qsyryo"
- model CampaignAction;
- endpoint /api/v1/campaign-actions/;
- relação relacional recommendation_ref → action;
- estado próprio da action;
- mark_reviewed persistente;
- dismiss persistente;
- manual_task;
- asset_request;
- ligação formal action → content_pack_request/report/media_kit/content_output;
- histórico/auditoria específico da action.
```

---

# 4. Resultado esperado

Ao concluir esta fase, o Backend Core deve suportar:

```text id="o6ee1j"
- criar CampaignAction;
- listar CampaignActions por campanha;
- consultar CampaignAction por id;
- actualizar status da CampaignAction;
- marcar action como reviewed;
- dismiss com motivo;
- associar action a artefactos reais;
- expor endpoints workspace-scoped;
- respeitar RBAC;
- manter frontend sem acesso a serviços internos;
- documentar contratos em OpenAPI.
```

O frontend passa a poder usar uma entidade real em vez de inferir estado apenas por metadata.

---

# 5. Escopo

## 5.1 Dentro do escopo

Inclui:

```text id="evszvg"
- criar app/model ou módulo backend para campaign actions;
- criar migration;
- criar serializer;
- criar viewset;
- criar filtros;
- criar permissões workspace-scoped;
- criar endpoints REST;
- criar actions custom para mark_reviewed/dismiss/cancel/complete, se adequado;
- associar CampaignAction a campaign;
- associar CampaignAction a recommendation_ref;
- associar CampaignAction opcionalmente a artefactos existentes;
- integrar com schema OpenAPI;
- criar testes backend;
- validar com frontend existente;
- documentar contratos e limitações.
```

## 5.2 Fora do escopo

Não inclui:

```text id="qye7r3"
- alterar Intelligence Engine;
- persistir o payload completo da intelligence sem decisão explícita;
- criar workflow engine complexo;
- scheduler;
- notificações em tempo real;
- WebSockets;
- automação assíncrona avançada;
- geração automática de artefactos sem confirmação;
- UI frontend avançada;
- RBAC novo complexo fora do padrão existente;
- billing;
- produção.
```

---

# 6. Modelo conceptual

## 6.1 CampaignAction

Entidade central da fase.

Campos conceptuais:

```text id="i41b1w"
id
workspace_id
campaign_id
recommendation_ref
recommendation_snapshot
title
description
action_type
status
priority
source
dismiss_reason
created_by
created_at
updated_at
completed_at
cancelled_at
metadata
related_content_pack_request_id
related_content_output_id
related_report_id
related_media_kit_id
```

## 6.2 Recommendation Ref

`recommendation_ref` é a chave que permite associar uma recommendation transitória a uma action persistente.

Regra:

```text id="75ln33"
O backend não deve assumir que recommendation_ref é id nativo do Intelligence Engine.
```

Deve ser tratado como referência externa/funcional calculada pelo cliente ou pelo Backend Core.

## 6.3 Recommendation Snapshot

Como a intelligence não persiste recommendations, a action deve guardar um snapshot mínimo no momento da criação.

Campos sugeridos:

```text id="58145m"
recommendation_snapshot = {
  "title": "...",
  "description": "...",
  "type": "...",
  "priority": "...",
  "confidence": 0.82,
  "raw": {}
}
```

Regra:

```text id="5ejoy2"
Guardar snapshot suficiente para histórico, mas evitar armazenar payloads excessivos ou sensíveis.
```

---

# 7. Tipos de acção

## 7.1 Tipos suportados no MVP

```text id="xdc92l"
content_pack
report_request
media_kit_request
manual_task
mark_reviewed
dismiss
```

## 7.2 Tipos ainda opcionais ou futuros

```text id="5xi1uw"
asset_request
content_output
automation
```

## 7.3 Semântica dos tipos

### content_pack

Action que aponta para um `ContentPackRequest`.

```text id="22mhbb"
CampaignAction(action_type=content_pack)
→ related_content_pack_request
```

### report_request

Action que aponta para um `Report`.

```text id="u0sfu8"
CampaignAction(action_type=report_request)
→ related_report
```

### media_kit_request

Action que aponta para um `MediaKit`.

```text id="g0yddr"
CampaignAction(action_type=media_kit_request)
→ related_media_kit
```

### manual_task

Action sem artefacto técnico associado.

```text id="iej7vs"
CampaignAction(action_type=manual_task)
```

### mark_reviewed

Regista que a recommendation foi analisada sem gerar artefacto.

```text id="l6dghx"
CampaignAction(action_type=mark_reviewed, status=completed)
```

### dismiss

Regista que a recommendation foi ignorada.

```text id="xcrtp2"
CampaignAction(action_type=dismiss, status=dismissed, dismiss_reason=...)
```

---

# 8. Estados

Estados mínimos:

```text id="5vfnik"
pending
in_progress
completed
failed
dismissed
cancelled
```

Semântica:

```text id="j1ouzl"
pending      = action criada, ainda não executada/concluída
in_progress  = execução em curso ou artefacto em processamento
completed    = action concluída
failed       = execução falhou
dismissed    = recommendation ignorada
cancelled    = action cancelada
```

Regras:

```text id="7hk8w3"
- dismiss deve exigir dismiss_reason.
- completed pode preencher completed_at.
- cancelled pode preencher cancelled_at.
- status deve ser validado pelo backend.
- transições inválidas devem devolver erro 400/422.
```

---

# 9. Endpoints alvo

## 9.1 Listar actions

```text id="ku6h3i"
GET /api/v1/campaign-actions/?campaign={campaign_id}
```

Filtros esperados:

```text id="8u4mdt"
campaign
status
action_type
recommendation_ref
source
created_by
```

## 9.2 Criar action

```text id="1ksawp"
POST /api/v1/campaign-actions/
```

Payload conceptual:

```text id="bbrlrm"
{
  "campaign": "uuid",
  "recommendation_ref": "string",
  "recommendation_snapshot": {},
  "title": "string",
  "description": "string",
  "action_type": "report_request",
  "priority": "medium",
  "metadata": {}
}
```

## 9.3 Consultar action

```text id="au5vys"
GET /api/v1/campaign-actions/{id}/
```

## 9.4 Actualizar parcialmente

```text id="7bbyue"
PATCH /api/v1/campaign-actions/{id}/
```

Campos actualizáveis:

```text id="lywu0o"
title
description
status
priority
metadata
related_content_pack_request
related_content_output
related_report
related_media_kit
```

## 9.5 Marcar como reviewed

```text id="buo8le"
POST /api/v1/campaign-actions/{id}/mark-reviewed/
```

Ou, se preferir evitar action custom:

```text id="q0cyrk"
PATCH /api/v1/campaign-actions/{id}/
status=completed
```

Decisão a confirmar na investigação técnica.

## 9.6 Dismiss

```text id="j0eeua"
POST /api/v1/campaign-actions/{id}/dismiss/
```

Payload:

```text id="hdr3j0"
{
  "dismiss_reason": "string"
}
```

## 9.7 Cancel

```text id="4tt37z"
POST /api/v1/campaign-actions/{id}/cancel/
```

---

# 10. Regras de negócio

## 10.1 Workspace

Toda CampaignAction deve ser scoped a workspace.

```text id="ocns97"
CampaignAction.workspace_id deve corresponder ao workspace da Campaign.
```

O backend deve validar isto.

## 10.2 Campaign obrigatória

Toda CampaignAction deve estar associada a uma campaign.

```text id="h0o93z"
campaign é obrigatório.
```

## 10.3 Recommendation Ref

Para actions originadas de recommendation, `recommendation_ref` deve ser obrigatório.

Excepção:

```text id="ft9cwc"
manual_task pode não ter recommendation_ref, se criada manualmente fora de uma recommendation.
```

## 10.4 Snapshot

Para actions originadas de recommendation, `recommendation_snapshot` deve ser aceite.

Não deve ser obrigatório se o caso for `manual_task`.

## 10.5 Duplicação

O backend deve evitar duplicação óbvia.

Regra sugerida:

```text id="q102xg"
workspace + campaign + recommendation_ref + action_type
```

Não deve haver duplicado activo para a mesma combinação, excepto se status estiver em:

```text id="9cscbl"
cancelled
dismissed
failed
```

Decisão a confirmar.

## 10.6 Relação com artefactos

Se uma action cria ou aponta para um artefacto real, deve guardar FK opcional.

Relações possíveis:

```text id="bp8xda"
related_content_pack_request
related_content_output
related_report
related_media_kit
```

A action não deve substituir estes artefactos. Deve apenas rastrear a origem operacional.

---

# 11. Segurança e permissões

## 11.1 Autenticação

Usar JWT actual do Backend Core.

## 11.2 Workspace RBAC

A API deve seguir o padrão existente de viewsets workspace-scoped.

Requisitos:

```text id="skv00d"
- exigir X-Workspace-ID;
- filtrar por workspace activo;
- impedir acesso cross-workspace;
- validar campaign dentro do workspace;
- validar artefactos relacionados dentro do mesmo workspace.
```

## 11.3 Frontend

O frontend continua proibido de enviar:

```text id="vsfpew"
X-Internal-Token
INTERNAL_API_TOKEN
```

CampaignAction é API pública autenticada do Backend Core, não API interna.

---

# 12. Backlog técnico

---

# BE-CA-001 — Investigar padrões existentes no Backend Core

## Objectivo

Identificar a forma correcta de implementar CampaignAction sem quebrar padrões já existentes.

## Tarefas

```text id="vx26gl"
Ler apps existentes.
Inspeccionar WorkspaceScopedRBACViewSet.
Inspeccionar WorkspaceOwnedModel.
Inspeccionar padrões de serializers.
Inspeccionar filtros.
Inspeccionar permissões.
Inspeccionar tests existentes.
Inspeccionar schema OpenAPI.
Identificar app mais adequada:
- nova app campaign_actions;
- ou módulo dentro de campaigns.
Comparar com content/reports/media-kits.
Registar decisão técnica.
```

## Critérios de aceitação

```text id="j25qbn"
Padrões identificados.
Local da implementação decidido.
Riscos registados.
Nenhum código runtime alterado.
```

---

# BE-CA-002 — Criar model CampaignAction

## Objectivo

Criar a entidade persistente.

## Tarefas

```text id="e31z96"
Criar model CampaignAction.
Herdar do modelo base correcto, se existir.
Adicionar FK workspace.
Adicionar FK campaign.
Adicionar recommendation_ref.
Adicionar recommendation_snapshot JSON.
Adicionar title.
Adicionar description.
Adicionar action_type.
Adicionar status.
Adicionar priority.
Adicionar source.
Adicionar dismiss_reason.
Adicionar metadata JSON.
Adicionar related_content_pack_request FK opcional.
Adicionar related_content_output FK opcional.
Adicionar related_report FK opcional.
Adicionar related_media_kit FK opcional.
Adicionar created_by, se padrão existir.
Adicionar timestamps.
Definir indexes.
Definir constraints de duplicação, se seguro.
Criar migration.
```

## Critérios de aceitação

```text id="xeo7af"
Model criado.
Migration criada.
python manage.py makemigrations passa.
python manage.py migrate passa.
python manage.py check passa.
```

---

# BE-CA-003 — Criar serializers

## Objectivo

Expor CampaignAction de forma segura e consistente.

## Tarefas

```text id="e4mjjf"
Criar CampaignActionSerializer.
Criar CreateCampaignActionSerializer, se necessário.
Criar UpdateCampaignActionSerializer, se necessário.
Validar campaign dentro do workspace.
Validar artefactos relacionados dentro do workspace.
Validar action_type.
Validar status.
Validar dismiss_reason quando status=dismissed.
Impedir campos read-only indevidos.
Não expor dados sensíveis.
```

## Critérios de aceitação

```text id="etwgby"
Serializers criados.
Validações cross-workspace implementadas.
Erros 400/422 claros.
Testes unitários ou API cobrem validações principais.
```

---

# BE-CA-004 — Criar viewset e rotas

## Objectivo

Expor API REST pública autenticada para CampaignAction.

## Tarefas

```text id="ngevlu"
Criar CampaignActionViewSet.
Usar padrão workspace-scoped existente.
Registar rota:
GET/POST/PATCH /api/v1/campaign-actions/
Adicionar filtros:
campaign
status
action_type
recommendation_ref
source
created_by
Ordenação por created_at desc.
Garantir paginação, se padrão existir.
Garantir schema OpenAPI.
```

## Critérios de aceitação

```text id="99oohd"
Endpoints funcionam.
Schema OpenAPI actualizado.
GET lista por workspace.
POST cria action.
PATCH actualiza action.
Cross-workspace bloqueado.
```

---

# BE-CA-005 — Implementar transições de estado

## Objectivo

Controlar transições básicas de CampaignAction.

## Tarefas

```text id="uw8q1q"
Definir transições permitidas.
Implementar validação de status.
Implementar completed_at.
Implementar cancelled_at.
Implementar dismiss_reason.
Avaliar actions custom:
- mark-reviewed;
- dismiss;
- cancel;
- complete.
Ou usar PATCH simples, se for mais consistente com o projecto.
Documentar decisão.
```

## Critérios de aceitação

```text id="3yvin5"
Transições inválidas bloqueadas.
Dismiss exige motivo.
Completed preenche completed_at.
Cancel preenche cancelled_at.
Testes cobrem transições principais.
```

---

# BE-CA-006 — Integrar com artefactos existentes

## Objectivo

Permitir que CampaignAction aponte formalmente para artefactos reais.

## Tarefas

```text id="0fjmn9"
Validar FK para ContentPackRequest.
Validar FK para ContentOutput.
Validar FK para Report.
Validar FK para MediaKit.
Garantir que todos pertencem ao mesmo workspace/campaign.
Decidir se criação de CampaignAction também pode criar artefacto relacionado.
Se sim, implementar apenas se for simples e seguro.
Se não, documentar fluxo em duas etapas:
1. criar artefacto;
2. criar/actualizar CampaignAction com related_*.
```

## Critérios de aceitação

```text id="3x1jcb"
Relacionamentos funcionam.
Cross-workspace bloqueado.
Cross-campaign bloqueado ou validado.
Sem duplicação de responsabilidade.
```

---

# BE-CA-007 — Criar testes backend

## Objectivo

Garantir estabilidade mínima da nova API.

## Casos mínimos

```text id="eie96k"
listar actions por workspace;
criar action válida;
bloquear sem autenticação;
bloquear sem X-Workspace-ID;
bloquear campaign fora do workspace;
bloquear artefacto relacionado fora do workspace;
validar action_type inválido;
validar status inválido;
validar dismiss sem motivo;
filtrar por campaign;
filtrar por recommendation_ref;
actualizar status;
impedir duplicação óbvia, se constraint existir.
```

## Critérios de aceitação

```text id="j0h2lf"
Testes criados.
Testes passam.
Cobertura dos casos críticos.
```

---

# BE-CA-008 — Actualizar schema e documentação

## Objectivo

Documentar o contrato real da CampaignAction API.

## Tarefas

```text id="kbikvs"
Actualizar schema OpenAPI, se necessário.
Confirmar /api/v1/schema/.
Confirmar /api/v1/docs/.
Criar documento:
backend_core\docs\campaign_actions\arquitectura_campaign_actions_backend.md

Incluir:
- modelo;
- endpoints;
- payloads;
- estados;
- action types;
- permissões;
- relação com recommendations;
- relação com artefactos;
- limitações;
- decisões.
```

## Critérios de aceitação

```text id="7w9oc1"
Schema actualizado.
Docs geradas/consultáveis.
Documento técnico criado.
Sem secrets.
```

---

# BE-CA-009 — Validar integração com frontend

## Objectivo

Confirmar que o frontend pode migrar da projecção best-effort para a API real.

## Tarefas

```text id="y6gpiq"
Subir Backend Core em localhost:8100.
Subir frontend em localhost:5200.
Confirmar endpoint /campaign-actions/.
Criar action via API.
Listar action via API.
Validar auth/workspace.
Comparar contrato com frontend actual.
Identificar alterações necessárias no frontend.
Não alterar frontend neste prompt, salvo correcção mínima documentada.
```

## Critérios de aceitação

```text id="1yvx7e"
API CampaignAction validada.
Contrato compatível ou lacunas documentadas.
Próximo backlog frontend definido.
```

---

# BE-CA-010 — Estado final da fase backend

## Objectivo

Fechar a fase com relatório honesto.

## Tarefas

```text id="e6bahf"
Criar:
backend_core\docs\campaign_actions\estado_campaign_actions_backend.md

Criar relatório final em:
backend_core\docs\campaign_actions\resultados_execucao\prompt_final_campaign_actions_backend_resultado.md

Incluir:
- escopo entregue;
- endpoints criados;
- migrations;
- testes;
- validações;
- limitações;
- impacto no frontend;
- riscos;
- pronto/não pronto para piloto;
- pronto/não pronto para produção.
```

## Critérios de aceitação

```text id="9f83zg"
Estado final criado.
Relatório final criado.
Conclusão honesta.
Não declarar produção-ready sem evidência.
```

---

# 13. Critérios de aceitação da fase

A fase é aceite se:

```text id="ky5iu8"
- CampaignAction model existe;
- migration aplicada;
- API /campaign-actions/ existe;
- list/create/detail/patch funcionam;
- workspace scoping funciona;
- RBAC respeitado;
- campaign validada dentro do workspace;
- related artefacts validados dentro do workspace;
- recommendation_ref persistido;
- recommendation_snapshot persistido;
- status funciona;
- dismiss/reviewed suportados ou decisão documentada;
- testes backend passam;
- schema OpenAPI actualizado;
- documentação criada;
- frontend consegue consumir ou backlog frontend de adaptação fica claro.
```

---

# 14. Critérios de não aceitação

A fase não deve ser aceite se:

```text id="ka93k7"
- CampaignAction permite cross-workspace;
- CampaignAction permite campaign fora do workspace;
- related_report/media_kit/content_pack_request de outro workspace é aceite;
- API expõe dados sensíveis;
- status inválido é aceite;
- dismiss sem motivo é aceite;
- schema não reflecte a API;
- testes críticos não existem;
- frontend continua dependente apenas de metadata sem plano de migração;
- documentação declara produção-ready sem validação.
```

---

# 15. Riscos

| ID            | Risco                                                              | Impacto | Mitigação                                                                         |
| ------------- | ------------------------------------------------------------------ | ------: | --------------------------------------------------------------------------------- |
| BE-CA-RSK-001 | Duplicar responsabilidade dos artefactos existentes.               |    Alto | CampaignAction deve rastrear, não substituir Report/MediaKit/ContentPackRequest.  |
| BE-CA-RSK-002 | Cross-workspace data leak.                                         | Crítico | Validar workspace em campaign e related artefacts.                                |
| BE-CA-RSK-003 | Recommendation ref instável.                                       |    Alto | Guardar snapshot no momento da criação.                                           |
| BE-CA-RSK-004 | Constraints demasiado rígidas bloquearem casos reais.              |   Médio | Começar com regra anti-duplicação simples ou validar por serviço.                 |
| BE-CA-RSK-005 | Overengineering de workflow.                                       |   Médio | Estados mínimos; sem workflow engine.                                             |
| BE-CA-RSK-006 | Frontend e backend divergirem nos action_type.                     |   Médio | OpenAPI + enum central + adaptação frontend posterior.                            |
| BE-CA-RSK-007 | Dismiss/reviewed confundirem action com recommendation persistida. |   Médio | Documentar semântica: action representa decisão operacional sobre recommendation. |
| BE-CA-RSK-008 | Migration afectar dados existentes.                                |    Alto | Nova tabela isolada, sem alteração destrutiva.                                    |

---

# 16. Decisões pendentes

## BE-CA-PDEC-001 — Nova app ou dentro de campaigns?

Recomendação inicial:

```text id="uopzvi"
Criar app própria campaign_actions se o projecto já usa apps por domínio.
Caso contrário, módulo dentro de campaigns.
```

Resolver em BE-CA-001.

## BE-CA-PDEC-002 — Actions custom ou PATCH simples?

Recomendação inicial:

```text id="tbid06"
Usar PATCH para status simples.
Usar action custom apenas para operações com semântica forte, como dismiss com motivo.
```

Resolver em BE-CA-005.

## BE-CA-PDEC-003 — Criar artefacto e CampaignAction no mesmo endpoint?

Recomendação inicial:

```text id="3v5zuh"
Não nesta fase. Primeiro rastrear.
Frontend pode criar artefacto real e depois criar/actualizar CampaignAction.
```

Resolver em BE-CA-006.

## BE-CA-PDEC-004 — Constraint anti-duplicação

Recomendação inicial:

```text id="fzq6qe"
Evitar duplicados activos por workspace + campaign + recommendation_ref + action_type.
```

Resolver após inspeccionar padrões e impacto.

---

# 17. Ordem recomendada de execução

```text id="symtdb"
1. BE-CA-001 — Investigar padrões existentes no Backend Core
2. BE-CA-002 — Criar model CampaignAction
3. BE-CA-003 — Criar serializers
4. BE-CA-004 — Criar viewset e rotas
5. BE-CA-005 — Implementar transições de estado
6. BE-CA-006 — Integrar com artefactos existentes
7. BE-CA-007 — Criar testes backend
8. BE-CA-008 — Actualizar schema e documentação
9. BE-CA-009 — Validar integração com frontend
10. BE-CA-010 — Estado final da fase backend
```

---

# 18. Próxima fase após este backend

Depois desta fase, criar uma fase frontend de adaptação:

```text id="2vg03o"
frontend\docs\01_fundamentos\03_campaign_actions_backend_integration\01_backlog.md
```

Objectivo:

```text id="nwrd7p"
Migrar Campaign Actions do frontend de projecção best-effort para a API real /campaign-actions/.
```

---

# 19. Definição de pronto para piloto técnico controlado

A fase fica pronta para piloto técnico controlado quando:

```text id="56fqn0"
- CampaignAction é persistida;
- actions são consultáveis por campanha;
- actions respeitam workspace/RBAC;
- recommendation_ref e snapshot são persistidos;
- actions podem apontar para artefactos reais;
- mark reviewed/dismiss têm comportamento claro;
- testes críticos passam;
- frontend tem plano claro de adaptação.
```

Não fica pronta para produção até existirem:

```text id="ldo6m4"
- testes de integração completos;
- auditoria de permissões;
- observabilidade;
- plano de migração frontend executado;
- validação com utilizadores reais;
- deploy de staging;
- validação de carga mínima;
- logs/auditoria operacional.
```
