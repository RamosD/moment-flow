# Backlog: Campaign Actions / Recommendation-to-Execution

# MomentFlow / ChartRex — Campaign Actions / Recommendation-to-Execution

## 1. Objectivo do documento

Este documento define o backlog da fase **02_campaign_actions_recommendation_to_execution**.

A fase anterior, **Frontend Foundation & Campaign War Room MVP**, ficou concluída e validada com Backend Core real. A War Room já permite visualizar campanhas, intelligence, scores, moments, recommendations, content outputs, reports e media kits.

Esta nova fase tem como objectivo transformar a War Room de uma superfície apenas analítica para uma superfície de **execução operacional controlada**.

A tese da fase é:

```text id="gq6cle"
Uma recommendation só tem valor real quando pode ser convertida numa acção acompanhável.
```

---

## 2. Resultado esperado

Ao concluir esta fase, o utilizador deve conseguir, a partir da War Room:

```text id="9ypkzb"
- ver recommendations accionáveis;
- transformar uma recommendation numa acção operacional;
- escolher um tipo de acção;
- confirmar a criação da acção;
- acompanhar o estado da acção;
- distinguir recommendation analisada, pendente, convertida ou ignorada;
- ver relação entre recommendation e outputs/resultados quando aplicável.
```

A War Room passa de:

```text id="uuhah4"
"o que devo fazer?"
```

para:

```text id="aowfyy"
"o que vou executar agora e em que estado está?"
```

---

# 3. Estado de partida

## 3.1 Já existe

O frontend já tem:

```text id="efwais"
- estrutura modular escalável;
- routing;
- API client central;
- auth/session;
- workspace foundation;
- Campaigns list;
- Campaign detail;
- Campaign War Room;
- Campaign Intelligence feature;
- RecommendationsList;
- RecommendationItem;
- MomentsList;
- ScoreGrid;
- WarningsPanel;
- ExplanationsPanel;
- Content Outputs panel;
- Reports panel;
- Media Kits panel;
- Error handling transversal;
- tratamento de 401/403/404/502/503;
- validação integrada real com Backend Core.
```

## 3.2 Princípio que continua obrigatório

O frontend continua a chamar apenas o Backend Core.

```text id="hmbs3m"
Frontend → Backend Core → Intelligence Engine
Frontend → Backend Core → Content Renderer
```

Proibido:

```text id="fukh01"
Frontend → Intelligence Engine
Frontend → Content Renderer
Frontend → serviços internos com X-Internal-Token
```

---

# 4. Tese funcional da fase

As recommendations geradas pela intelligence podem originar diferentes tipos de acção.

Exemplos:

```text id="n5uwwv"
- criar tarefa/acção manual;
- gerar content pack;
- iniciar pedido de asset;
- criar report;
- criar media kit;
- marcar recommendation como analisada;
- ignorar recommendation com motivo;
- associar recommendation a output já existente;
- transformar recommendation em plano de execução.
```

Nesta fase, o foco é criar o **ciclo mínimo de execução**, não automatizar tudo.

---

# 5. Escopo da fase

## 5.1 Dentro do escopo

Esta fase inclui:

```text id="z3chh3"
- investigação dos contratos reais existentes no Backend Core;
- identificação de endpoints existentes para acções, content packs, content outputs, reports e media kits;
- definição do modelo frontend para Recommendation Action;
- criação de uma feature campaign-actions;
- adição de botões de acção nas recommendations;
- criação de modal/drawer de "Criar acção";
- criação de tipos de acção suportados no MVP;
- criação de estado visual por recommendation;
- criação de painel de acções da campanha na War Room;
- consumo apenas de endpoints do Backend Core;
- tratamento de loading/error/success;
- validação de 401/403/404/422/502/503;
- documentação da arquitectura da feature;
- validação integrada real com Backend Core quando possível;
- relatório final honesto.
```

## 5.2 Fora do escopo

Não implementar nesta fase:

```text id="vk0hd6"
- chamada directa ao Intelligence Engine;
- chamada directa ao Content Renderer;
- execução automática sem confirmação do utilizador;
- scheduler;
- workflows complexos multi-step;
- aprovação hierárquica;
- notificações em tempo real;
- websockets;
- Kanban completo de acções;
- calendário;
- edição avançada de campanhas;
- geração visual avançada de assets;
- editor de conteúdo completo;
- preview/renderização avançada de media;
- testes E2E completos;
- produção;
- billing;
- permissões complexas no frontend como fonte da verdade.
```

---

# 6. Conceitos principais

## 6.1 Recommendation

Uma recommendation é uma sugestão gerada pela intelligence da campanha.

Pode ter campos variáveis porque o contrato da intelligence ainda é parcialmente flexível.

Campos esperados ou tolerados:

```text id="75s8ow"
- id, se existir;
- title;
- label;
- action;
- description;
- priority;
- type;
- reason;
- confidence;
- metadata.
```

Quando não existir `id`, o frontend deve derivar uma chave estável defensiva a partir de:

```text id="1ov9c2"
campaignId + índice + title/action/type
```

Sem assumir que essa chave é identificador persistente do backend.

## 6.2 Campaign Action

Uma Campaign Action representa uma acção operacional criada a partir de uma recommendation ou criada manualmente dentro da campanha.

Campos conceptuais:

```text id="x5ueaq"
- id;
- workspace_id;
- campaign_id;
- recommendation_ref;
- title;
- description;
- action_type;
- status;
- priority;
- source;
- created_by;
- created_at;
- updated_at;
- due_date;
- metadata;
- related_output_id;
- related_report_id;
- related_media_kit_id.
```

A IA local deve confirmar se este conceito já existe no Backend Core antes de criar qualquer contrato novo.

## 6.3 Action Type

Tipos mínimos esperados no MVP:

```text id="sap734"
manual_task
content_pack
asset_request
report_request
media_kit_request
mark_reviewed
dismiss
```

A implementação deve usar apenas os tipos suportados pelo Backend Core real. Se o Backend Core não suportar todos, a UI deve limitar-se aos tipos existentes ou criar placeholders honestos.

## 6.4 Action Status

Estados mínimos:

```text id="s4g7lc"
pending
in_progress
completed
failed
dismissed
cancelled
```

Se o backend usar nomes diferentes, o frontend deve mapear para badges visuais sem alterar o contrato real.

---

# 7. Experiência alvo na War Room

## 7.1 Antes desta fase

A War Room mostra:

```text id="wvdkq4"
- summary;
- grade;
- scores;
- moments;
- recommendations;
- warnings;
- explanations;
- outputs;
- reports;
- media kits.
```

## 7.2 Depois desta fase

A War Room deve mostrar também:

```text id="1dnetw"
- botões de acção por recommendation;
- estado de execução por recommendation;
- painel "Campaign Actions";
- acções criadas;
- relação entre recommendation e acção;
- feedback de sucesso/erro;
- retry quando aplicável.
```

## 7.3 Fluxo principal

```text id="un2d87"
1. Utilizador abre Campaign War Room.
2. Utilizador vê recommendations.
3. Utilizador escolhe uma recommendation.
4. Utilizador clica em "Create action" ou equivalente.
5. Sistema abre modal/drawer com dados pré-preenchidos.
6. Utilizador escolhe o tipo de acção.
7. Utilizador confirma.
8. Frontend chama Backend Core.
9. Backend Core cria/regista a acção ou dispara o fluxo suportado.
10. War Room actualiza o estado.
11. Recommendation aparece como convertida/analisada.
12. Acção aparece no painel Campaign Actions.
```

---

# 8. Estrutura frontend esperada

A fase deve respeitar a arquitectura já criada.

Estrutura alvo provável:

```text id="53xwwy"
src/
  entities/
    campaign-action/
      model.ts
      campaign-action-api.ts
      useCampaignActions.ts
      useCreateCampaignAction.ts
      useUpdateCampaignAction.ts
      query-keys.ts
      index.ts

  features/
    campaign-actions/
      CreateActionFromRecommendationButton.tsx
      CreateActionFromRecommendationDialog.tsx
      RecommendationActionState.tsx
      RecommendationActionMenu.tsx
      useRecommendationActionDraft.ts
      action-type-options.ts
      index.ts

  widgets/
    campaign-actions-panel/
      CampaignActionsPanel.tsx
      CampaignActionsPanel.module.css
      index.ts

  shared/
    ui/
      Dialog ou Modal, se ainda não existir
      Select, se ainda não existir
      Textarea, se ainda não existir
      FormField, se necessário
```

A IA local deve adaptar a estrutura ao código real.

---

# 9. Contratos de Backend Core

## 9.1 Regra

A IA local deve primeiro inspeccionar o Backend Core.

Não assumir que os endpoints existem.

Confirmar:

```text id="xhsa3u"
- schema OpenAPI;
- apps existentes;
- models;
- serializers;
- viewsets;
- rotas;
- permissões;
- filtros;
- payloads;
- estados;
- validações;
- respostas de erro.
```

## 9.2 Endpoints a investigar

Procurar endpoints reais para:

```text id="vqv02s"
- campaign actions;
- tasks;
- action items;
- content packs;
- content outputs;
- reports;
- media kits;
- generation jobs;
- recommendations;
- campaign intelligence history;
- audit logs.
```

Possíveis rotas, apenas como hipótese:

```text id="15n9va"
GET    /api/v1/campaign-actions/?campaign={id}
POST   /api/v1/campaign-actions/
PATCH  /api/v1/campaign-actions/{id}/
POST   /api/v1/campaigns/{id}/actions/
POST   /api/v1/content-packs/
POST   /api/v1/reports/
POST   /api/v1/media-kits/
```

Se não existirem endpoints para Campaign Actions, a IA local deve documentar claramente a lacuna.

## 9.3 Se o Backend Core não tiver suporte

Se não existir suporte backend para acções, esta fase deve dividir-se em duas opções:

```text id="0ozjaq"
Opção A:
Implementar apenas UI preparada, com botões desactivados e mensagem honesta:
"Action creation is not available yet because Backend Core does not expose campaign actions."

Opção B:
Criar backlog técnico complementar no Backend Core para Campaign Actions API.
```

Não criar mocks runtime para fingir que acções existem.

---

# 10. Backlog técnico-funcional

---

# CA-001 — Investigar contratos reais de acções e outputs no Backend Core

## Objectivo

Confirmar o que o Backend Core já suporta para transformar recommendations em acções.

## Tarefas

```text id="8ia2sn"
Ler este backlog.
Ler arquitectura_frontend.md.
Ler estado_frontend_foundation_campaign_war_room.md.
Inspeccionar backend_core/schema.yml.
Inspeccionar rotas Django/DRF.
Procurar models/serializers/viewsets relacionados com:
- action;
- task;
- recommendation;
- content pack;
- content output;
- report;
- media kit;
- generation job;
- audit/event.

Confirmar endpoints existentes.
Confirmar permissões.
Confirmar se há filtros por campaign.
Confirmar se há criação por POST.
Confirmar payloads.
Confirmar respostas.
Confirmar erros possíveis.
Confirmar se existe relação persistente recommendation → action.
Confirmar se a intelligence é persistida ou apenas recalculada.
Documentar lacunas.
Não alterar runtime, salvo relatório.
```

## Critérios de aceitação

```text id="tuw6zw"
Relatório de investigação criado.
Endpoints reais confirmados ou marcados como ausentes.
Lacunas backend documentadas.
Riscos identificados.
Decisão recomendada para a fase registada.
```

---

# CA-002 — Definir modelo frontend de Campaign Action

## Objectivo

Criar tipos frontend defensivos para acções de campanha, alinhados ao Backend Core real.

## Tarefas

```text id="f7h0h6"
Criar entity campaign-action se houver contrato backend.
Criar tipos:
- CampaignAction;
- CampaignActionStatus;
- CampaignActionType;
- CampaignActionSource;
- CreateCampaignActionPayload;
- UpdateCampaignActionPayload;
- RecommendationRef.

Se o backend não tiver contrato:
- criar apenas tipos internos de UI para draft/action intent;
- não fingir persistência.

Garantir snake_case se a API usar snake_case.
Campos incertos devem ser opcionais.
Criar helpers de label/status/badge.
```

## Critérios de aceitação

```text id="rcz0iz"
Tipos criados ou lacuna documentada.
Não há contrato inventado como se fosse real.
Build passa.
Lint passa.
```

---

# CA-003 — Criar API/hooks de Campaign Actions

## Objectivo

Criar a camada de dados para listar/criar/actualizar acções de campanha, se o Backend Core suportar.

## Tarefas

```text id="yjeijc"
Criar campaign-action-api.ts.
Criar query keys.
Criar useCampaignActions.
Criar useCreateCampaignAction.
Criar useUpdateCampaignAction, se suportado.
Usar TanStack Query.
Incluir workspaceId + campaignId nas query keys.
Invalidar queries relevantes após criação/actualização.
Tratar 401/403/404/422/502/503.
Nunca chamar IE/Renderer.
Se endpoints não existirem:
- não criar chamadas falsas;
- criar camada desactivada/documentada;
- preparar UI para disabled state.
```

## Critérios de aceitação

```text id="4q9vnl"
Hooks reais existem se endpoints existirem.
Sem mocks runtime.
Sem chamada directa a serviços internos.
Errors tratados.
Build/lint passam.
```

---

# CA-004 — Criar UI base necessária para acções

## Objectivo

Adicionar componentes UI mínimos em `shared/ui` para suportar criação de acções.

## Componentes possíveis

```text id="p80izh"
Dialog ou Modal
Select
Textarea
FormField
InlineFieldError
ConfirmDialog
```

## Tarefas

```text id="rwvnx6"
Inspeccionar se componentes já existem.
Criar apenas o necessário.
Manter CSS Modules + design tokens.
Garantir acessibilidade básica:
- foco;
- labels;
- aria;
- escape/close no modal, se aplicável;
- botão cancel/confirm.
Não instalar UI framework pesado.
Não introduzir dependências desnecessárias.
```

## Critérios de aceitação

```text id="90oaq4"
Componentes mínimos existem.
Acessibilidade básica respeitada.
Sem design system pesado.
Build/lint passam.
```

---

# CA-005 — Criar draft de acção a partir de recommendation

## Objectivo

Permitir transformar uma recommendation flexível num draft de acção consistente.

## Tarefas

```text id="ap7m3d"
Criar helper para extrair dados da recommendation.
Mapear title/action/label para título do draft.
Mapear description/reason para descrição.
Mapear priority/confidence quando existir.
Criar recommendation_ref defensivo.
Criar action_type sugerido, se possível.
Criar useRecommendationActionDraft.
Garantir que recommendations sem id continuam funcionais.
Não assumir shape fixo da recommendation.
```

## Critérios de aceitação

```text id="d3tomb"
Draft é criado para recommendations variadas.
Não quebra com campos em falta.
Campos incertos são tratados defensivamente.
Build/lint passam.
```

---

# CA-006 — Adicionar acções ao RecommendationItem

## Objectivo

Adicionar affordance visual para executar uma recommendation.

## Tarefas

```text id="iblo3u"
Actualizar RecommendationItem ou criar wrapper em feature campaign-actions.
Adicionar botão:
- Create action;
ou
- Convert to action;
ou
- Review action.

Mostrar estado quando recommendation já tem acção associada, se houver dados.
Evitar duplicação de acções quando já existe associação.
Tratar modo disabled quando Backend Core não suporta actions.
Mostrar tooltip/mensagem honesta quando indisponível.
Não transformar recommendation automaticamente sem confirmação.
```

## Critérios de aceitação

```text id="dw5z25"
Cada recommendation accionável tem botão/ação clara.
Estados disabled/converted/reviewed existem.
Sem criação automática.
Build/lint passam.
```

---

# CA-007 — Criar modal/drawer "Create Action"

## Objectivo

Permitir confirmar a criação de acção a partir de uma recommendation.

## Campos mínimos

```text id="p49dk3"
title
description
action_type
priority
due_date, opcional
notes, opcional
```

## Tarefas

```text id="5vaf8j"
Criar CreateActionFromRecommendationDialog.
Pré-preencher dados a partir do draft.
Permitir editar título/descrição.
Permitir escolher action_type suportado.
Validar campos obrigatórios.
Mostrar erros 422 por campo, se disponíveis.
Mostrar loading durante submit.
Mostrar sucesso.
Mostrar erro.
Fechar modal após sucesso ou manter com feedback claro.
Invalidar Campaign Actions e dados relacionados.
```

## Critérios de aceitação

```text id="drjsrg"
Modal funciona.
Payload respeita contrato real.
Erros são tratados.
Sucesso actualiza UI.
Build/lint passam.
```

---

# CA-008 — Criar painel Campaign Actions na War Room

## Objectivo

Mostrar acções operacionais associadas à campanha.

## Tarefas

```text id="p8vvyc"
Criar widget campaign-actions-panel.
Listar acções da campanha, se endpoint existir.
Mostrar:
- título;
- status;
- type;
- priority;
- origem;
- data de criação;
- relação com recommendation, se existir.
Tratar loading/error/empty.
Se Backend Core não suportar actions:
- mostrar estado honesto "Campaign actions are not available yet".
Integrar no layout da War Room.
```

## Critérios de aceitação

```text id="92q4ws"
Painel aparece na War Room.
Lista dados reais quando existirem.
Empty state honesto.
Erro tratado.
Build/lint passam.
```

---

# CA-009 — Associar recommendation ao estado da acção

## Objectivo

Evitar que a War Room mostre recommendations como se nunca tivessem sido tratadas quando já existe uma acção criada.

## Tarefas

```text id="tc4s4t"
Criar função de matching recommendation → action.
Usar recommendation_ref quando existir.
Se não existir id persistente, usar chave derivada defensiva.
Mostrar estados:
- not_started;
- action_created;
- in_progress;
- completed;
- dismissed;
- unavailable.

Actualizar RecommendationItem com badge/estado.
Evitar duplicação de action se já houver associação.
Documentar limitações se a associação não for persistente no backend.
```

## Critérios de aceitação

```text id="qa35rp"
Recommendations mostram estado de execução.
Associação usa contrato real quando disponível.
Não há duplicação óbvia.
Limitações documentadas.
Build/lint passam.
```

---

# CA-010 — Suportar Mark Reviewed / Dismiss

## Objectivo

Permitir ao utilizador marcar uma recommendation como analisada ou ignorada com motivo, se o backend suportar.

## Tarefas

```text id="ankl3t"
Confirmar se backend suporta status reviewed/dismissed.
Se suportar:
- criar acção ou update correspondente;
- pedir motivo no dismiss;
- actualizar UI;
- invalidar queries.
Se não suportar:
- não persistir falso estado;
- mostrar indisponível ou documentar lacuna.
```

## Critérios de aceitação

```text id="u961rw"
Reviewed/dismiss funciona se backend suportar.
Sem persistência falsa.
Erros tratados.
Build/lint passam.
```

---

# CA-011 — Integrar acções com outputs existentes

## Objectivo

Preparar a relação entre acções e outputs já existentes na War Room.

## Tarefas

```text id="81rq8o"
Confirmar se Campaign Action pode referenciar:
- content_output;
- report;
- media_kit;
- generation job.
Se suportado:
- mostrar link/estado no Campaign Actions Panel;
- mostrar relação no RecommendationItem.
Se não suportado:
- documentar lacuna;
- não inventar relação persistente.
```

## Critérios de aceitação

```text id="kjoobx"
Relações reais são mostradas.
Lacunas documentadas.
Sem mocks runtime.
Build/lint passam.
```

---

# CA-012 — Tratamento de permissões e erros

## Objectivo

Garantir que a experiência é segura e clara em falhas.

## Casos

```text id="vi93xp"
401 sessão expirada
403 sem permissão
404 campanha/acção inexistente
422 validação
502/503 serviço indisponível
network error
workspace ausente
backend sem endpoint de actions
```

## Tarefas

```text id="yplqio"
Usar ErrorState e componentes dedicados existentes.
Mostrar mensagens claras.
Não mostrar stack traces.
Não mostrar tokens.
Tratar 422 por campo quando possível.
Tratar 403 como permissão insuficiente.
Tratar ausência de backend support como indisponibilidade funcional, não crash.
```

## Critérios de aceitação

```text id="xc0stv"
Erros comuns tratados.
Sem dados sensíveis na UI.
Build/lint passam.
```

---

# CA-013 — Documentar arquitectura da feature Campaign Actions

## Objectivo

Documentar como a nova feature foi desenhada e como deve evoluir.

## Documento sugerido

```text id="i4hhcw"
frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\arquitectura_campaign_actions.md
```

## Conteúdo

```text id="g9hctj"
- objectivo da feature;
- contratos usados;
- endpoints reais;
- lacunas backend;
- estrutura frontend criada;
- entity campaign-action;
- feature campaign-actions;
- widget campaign-actions-panel;
- fluxo recommendation → action;
- tratamento de errors;
- regras de segurança;
- o que não fazer;
- próximos passos.
```

## Critérios de aceitação

```text id="uc4cvy"
Documento criado.
Documento reflecte código real.
Sem secrets.
Limitações claras.
```

---

# CA-014 — Validar integração real

## Objectivo

Validar a fase contra Backend Core real, sem mocks runtime.

## Tarefas

```text id="7no48o"
Subir Backend Core real.
Subir frontend.
Login real.
Seleccionar workspace real.
Abrir campaign real.
Abrir War Room.
Validar recommendations.
Criar action real, se backend suportar.
Validar Campaign Actions Panel.
Validar estados de recommendation.
Validar errors.
Executar pnpm lint.
Executar pnpm build.
Executar python manage.py check se backend for alterado.
Executar greps de segurança.
Registar evidência.
```

## Critérios de aceitação

```text id="g71fei"
Integração real validada ou limitação documentada.
Sem mocks runtime.
Build/lint passam.
Segurança validada.
```

---

# CA-015 — Estado final da fase

## Objectivo

Fechar a fase com relatório honesto.

## Tarefas

```text id="g2s5of"
Criar relatório final em:
frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\resultados\prompt_final_campaign_actions_recommendation_to_execution.md

Criar/actualizar estado em:
frontend\docs\01_fundamentos\02_campaign_actions_recommendation_to_execution\estado_campaign_actions_recommendation_to_execution.md

Incluir:
- escopo entregue;
- contratos usados;
- funcionalidades implementadas;
- lacunas;
- validações;
- riscos;
- pronto/não pronto para piloto;
- pronto/não pronto para produção;
- próximos passos.
```

## Critérios de aceitação

```text id="8fvfx2"
Relatório final existe.
Estado final existe.
Conclusão é honesta.
Não declara produção-ready sem evidência.
```

---

# 11. Critérios de aceitação da fase

A fase fica aceite se:

```text id="6k4rmy"
- contratos reais foram investigados;
- não foram inventados endpoints;
- RecommendationItem tem affordance de execução;
- Create Action existe se backend suportar;
- Campaign Actions Panel existe;
- recommendations mostram estado de execução quando possível;
- erros são tratados;
- workspace/auth continuam respeitados;
- frontend chama apenas Backend Core;
- não há X-Internal-Token no frontend;
- não há chamadas directas ao IE/Renderer;
- pnpm lint passa;
- pnpm build passa;
- documentação da feature existe;
- relatório final existe;
- estado final é honesto.
```

Se o backend não suportar Campaign Actions, a fase pode ser aceite parcialmente apenas se:

```text id="2mfitn"
- a lacuna estiver documentada;
- a UI não fingir persistência;
- os botões estiverem desactivados ou claramente marcados como indisponíveis;
- existir backlog complementar para Backend Core.
```

---

# 12. Critérios de não aceitação

A fase não deve ser aceite se:

```text id="7499o9"
- frontend inventa acções sem backend real;
- runtime usa mocks para simular sucesso;
- recommendations aparecem como convertidas sem persistência real;
- X-Internal-Token aparece como header enviado pelo frontend;
- frontend chama IE directamente;
- frontend chama Renderer directamente;
- errors mostram stack trace ou tokens;
- War Room quebra quando actions falham;
- criação de action duplica acções sem controlo;
- build falha;
- lint falha sem justificação;
- documentação declara produção-ready sem evidência.
```

---

# 13. Riscos

| ID         | Risco                                                   | Impacto | Mitigação                                                                          |
| ---------- | ------------------------------------------------------- | ------: | ---------------------------------------------------------------------------------- |
| CA-RSK-001 | Backend Core não tem Campaign Actions API.              |    Alto | Investigar primeiro; não fingir persistência; criar backlog backend se necessário. |
| CA-RSK-002 | Recommendations não têm id persistente.                 |    Alto | Criar recommendation_ref defensivo; documentar limitações.                         |
| CA-RSK-003 | Duplicação de acções para a mesma recommendation.       |   Médio | Matching recommendation → action; bloquear duplicação quando possível.             |
| CA-RSK-004 | Overengineering de workflow.                            |   Médio | MVP com criação simples e estados básicos.                                         |
| CA-RSK-005 | Frontend assumir regras de negócio.                     |    Alto | Backend Core continua fonte da verdade.                                            |
| CA-RSK-006 | UI criar expectativa de automação que ainda não existe. |   Médio | Copy honesta; distinguir create action de execute automation.                      |
| CA-RSK-007 | 422/403 mal tratados em criação.                        |   Médio | Reusar ErrorState + field errors.                                                  |
| CA-RSK-008 | Acções ficarem desligadas de outputs reais.             |   Médio | Preparar relações; documentar lacunas.                                             |
| CA-RSK-009 | Fase misturar actions, rendering e reports avançados.   |    Alto | Manter escopo: recommendation → action.                                            |
| CA-RSK-010 | Frontend chamar serviços internos por atalho.           | Crítico | API client apenas Backend Core; greps de segurança.                                |

---

# 14. Decisões pendentes

## CA-PDEC-001 — Campaign Actions já existem no Backend Core?

```text id="e1nml2"
Estado: pendente
Resolver em CA-001.
```

## CA-PDEC-002 — Action deve ser entidade persistente ou apenas pedido de geração?

```text id="kk9lsc"
Estado: pendente
Recomendação: entidade persistente é melhor para rastreabilidade, mas depende do Backend Core real.
```

## CA-PDEC-003 — Recommendations têm id estável?

```text id="psawpr"
Estado: pendente
Recomendação: se não tiverem, usar recommendation_ref derivado e documentar limitação.
```

## CA-PDEC-004 — Create Action deve abrir modal ou drawer?

```text id="14yf0z"
Estado: pendente
Recomendação: modal simples no MVP; drawer só se o formulário crescer.
```

## CA-PDEC-005 — Mark Reviewed/Dismiss deve persistir?

```text id="fw887n"
Estado: pendente
Recomendação: só persistir se Backend Core suportar.
```

## CA-PDEC-006 — Criar backlog backend complementar?

```text id="kopgv7"
Estado: pendente
Resolver após CA-001.
```

---

# 15. Ordem recomendada de execução

```text id="x10srr"
1. CA-001 — Investigar contratos reais de acções e outputs no Backend Core
2. CA-002 — Definir modelo frontend de Campaign Action
3. CA-003 — Criar API/hooks de Campaign Actions
4. CA-004 — Criar UI base necessária para acções
5. CA-005 — Criar draft de acção a partir de recommendation
6. CA-006 — Adicionar acções ao RecommendationItem
7. CA-007 — Criar modal/drawer "Create Action"
8. CA-008 — Criar painel Campaign Actions na War Room
9. CA-009 — Associar recommendation ao estado da acção
10. CA-010 — Suportar Mark Reviewed / Dismiss
11. CA-011 — Integrar acções com outputs existentes
12. CA-012 — Tratamento de permissões e erros
13. CA-013 — Documentar arquitectura da feature Campaign Actions
14. CA-014 — Validar integração real
15. CA-015 — Estado final da fase
```

---

# 16. Possíveis resultados da fase

## Resultado A — Backend Core já suporta Campaign Actions

Estado ideal.

```text id="v1dhcx"
A fase implementa criação real de acções, painel de acções e associação recommendation → action.
```

## Resultado B — Backend Core suporta parcialmente

Estado aceitável.

```text id="gwp7h8"
A fase implementa o que existe, documenta lacunas e evita falsa persistência.
```

## Resultado C — Backend Core não suporta

Estado aceitável apenas como descoberta e preparação.

```text id="jey0db"
A fase entrega UI preparada/desactivada, documentação, e backlog complementar Backend Core.
```

Neste caso, não declarar que Recommendation-to-Execution está funcional.

---

# 17. Próxima fase provável

Se esta fase for concluída com Campaign Actions reais, a próxima evolução natural será:

```text id="e91sgs"
03_content_pack_generation_from_actions
```

Ou:

```text id="hkqpzu"
03_reports_media_kits_execution_flow
```

A escolha depende de qual acção trouxer mais valor no piloto técnico.

---

# 18. Definição de pronto para piloto técnico controlado

A fase fica pronta para piloto técnico controlado quando:

```text id="scqcwl"
- existe caminho real recommendation → action;
- utilizador consegue criar ou registar uma acção;
- acção aparece associada à campanha;
- recommendation mostra estado coerente;
- falhas são tratadas;
- não há atalhos inseguros;
- validação real foi executada;
- limitações estão documentadas.
```

Não fica pronta para produção até existirem:

```text id="n3tyaw"
- testes E2E;
- auditoria de permissões;
- UX refinada;
- observabilidade frontend;
- tratamento robusto de refresh token;
- validação cross-browser;
- deploy de staging;
- validação com utilizadores reais.
```
