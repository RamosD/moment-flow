# Resultado — Prompt 01: congelar decisões de rollout

## Execução de 2026-07-01 10:34:41 -01:00

**Estado da execução:** `executado`

### Resumo objectivo

Foram fechadas as decisões de rollout da fase `03_campaign_actions_backend_integration`. O cutover usará a CampaignAction API persistente como única fonte do Campaign Actions Panel, sem apagar artefactos históricos, sem dual-read e sem alterar código runtime nesta execução.

### Decisões fechadas

#### DEC-01 — Histórico e backfill: opção B, corte temporal explícito

- O ponto de corte é a activação da versão frontend que substitui o read path do painel.
- A partir desse cutover, o Campaign Actions Panel mostra exclusivamente registos reais devolvidos por `GET /api/v1/campaign-actions/?campaign=<id>`.
- Artefactos anteriores sem CampaignAction não são apagados nem migrados pelo browser. Continuam visíveis nos painéis proprietários de content packs, reports e media kits, mas deixam de ser projectados como CampaignActions.
- CampaignActions reais já existentes na API continuam visíveis, independentemente de terem sido criadas antes ou depois do cutover.
- Não haverá backfill nesta fase, feature flag de compatibilidade, merge de fontes ou dual-read. Um rollback de release não deve transformar-se num modo híbrido permanente.

**Impacto e riscos:** o painel pode parecer perder histórico no momento do cutover, embora os dados de origem permaneçam intactos. Há também fragmentação de consulta entre o novo painel e os painéis proprietários. A mitigação é tornar o corte explícito na copy/release note e preservar esses painéis; qualquer backfill futuro será um trabalho backend separado e deliberado.

#### DEC-02 — Ordem das duas escritas: artefacto primeiro

Para `content_pack`, `report_request` e `media_kit_request`, a ordem é:

1. criar o artefacto no endpoint proprietário;
2. criar a CampaignAction com a FK `related_*` correspondente.

Se o primeiro passo tiver sucesso e o segundo falhar:

- conservar o id e o contexto do artefacto como sucesso parcial;
- não repetir automaticamente nem por retry cego o POST do artefacto;
- antes do retry, fazer pesquisa exacta por `campaign + recommendation_ref + action_type`;
- se já existir uma action activa/completed, convergir para esse registo e, se necessário e válido, completar apenas a ligação por PATCH;
- se não existir action que bloqueie a chave, repetir somente o POST de CampaignAction usando o artefacto já criado;
- não executar rollback destrutivo do artefacto.

`manual_task`, `mark_reviewed` e `dismiss` não criam artefactos e, portanto, usam apenas a escrita CampaignAction.

#### DEC-03 — Reviewed e dismiss

- Quando a recommendation ainda não tem qualquer CampaignAction, **Mark reviewed** cria uma action com `action_type=mark_reviewed`; o backend persiste-a como `completed`.
- Quando a recommendation ainda não tem qualquer CampaignAction, **Dismiss** cria uma action com `action_type=dismiss` e `dismiss_reason` obrigatório; o backend persiste-a como `dismissed`.
- Quando já existe uma CampaignAction, a operação actua sobre o id explícito dessa action através de `/{id}/mark-reviewed/` ou `/{id}/dismiss/`.
- Se houver várias actions para a recommendation, a UI não pode escolher implicitamente o primeiro match: a action alvo tem de ser inequívoca.
- Uma transição inválida num estado terminal deve mostrar o erro do backend; não deve criar silenciosamente uma action substituta.
- Review e dismiss não são persistidos em estado local nem em metadata dos artefactos.

#### DEC-04 — Múltiplas actions por recommendation

- A cardinalidade frontend passa de um match para `CampaignAction[]` agrupado por `recommendation_ref`.
- A identidade de deduplicação é apenas `recommendation_ref + action_type`, sempre no âmbito de workspace e campaign.
- Alinhado com o backend, `pending`, `in_progress` e `completed` bloqueiam outra action com a mesma chave; `failed`, `dismissed` e `cancelled` permitem uma nova tentativa.
- Uma action de um tipo não bloqueia a criação de outro tipo para a mesma recommendation.
- Matching, badges e affordances devem considerar todas as actions e nunca usar “primeiro match bloqueia todos os tipos”.
- Antes de concluir que uma action não existe, o frontend deve usar o filtro exacto; uma primeira página incompleta não é prova de ausência.

### Impacto consolidado

| Área | Decisão de implementação futura |
| --- | --- |
| Read path | Um único read path persistente em `/campaign-actions/`; sem agregação de content-pack requests, reports e media kits. Os painéis proprietários permanecem independentes. |
| Create path | Artefacto proprietário primeiro e CampaignAction relacionada depois; sucesso parcial recupera apenas a segunda escrita. |
| Matching | Agrupar por `recommendation_ref`, distinguir por `action_type` e consultar por filtro exacto quando a lista carregada não basta. |
| Reviewed/dismiss | Criar actions próprias apenas quando não existe CampaignAction; caso contrário usar o endpoint semântico no id explícito. Nunca usar metadata de artefactos. |
| Histórico | Sem eliminação e sem backfill nesta fase; artefactos legados ficam nos painéis próprios e deixam de alimentar o Campaign Actions Panel após o cutover. |

### Evidência consultada

- backlog completo da fase;
- arquitectura e estado final da CampaignAction API no Backend Core;
- estado final da fase frontend anterior;
- implementação actual em `frontend/src/entities/campaign-action/`, `frontend/src/features/campaign-actions/`, `frontend/src/widgets/campaign-actions-panel/` e `frontend/src/pages/campaign-war-room/`;
- implementação backend relevante de filtros, serializer, lifecycle, endpoints semânticos e constraint de deduplicação.

### Ficheiros criados ou alterados

- Criado `frontend/docs/01_fundamentos/03_campaign_actions_backend_integration/resultados_execucao/prompt_01_congelar_decisoes_rollout_resultado.md`.
- Nenhum ficheiro runtime foi alterado.

### Validações executadas e resultado

- Leitura integral das fontes documentais pedidas: concluída.
- Inspecção do frontend no escopo indicado: concluída; confirmou projecção sobre três endpoints, `Promise.allSettled`, metadata como correlação e bloqueio por primeiro match.
- Verificação do contrato backend no código: concluída; confirmou filtros exactos, endpoints semânticos, defaults de reviewed/dismiss e unicidade activa por ref + tipo.
- Browser e servidores: não usados/iniciados.
- Build e lint: não executados, pois não houve alteração runtime.
- Verificação de secrets no relatório: concluída sem valores sensíveis encontrados.

### Pendências, riscos e próximo passo recomendado

- Implementar primeiro o novo DTO/API/paginação e só depois activar o cutover definido nesta decisão.
- A recuperação de sucesso parcial precisa de estado UX explícito que conserve o id do artefacto; um simples re-submit do formulário é inseguro.
- A paginação pode causar falsos negativos no matching; a consulta exacta por ref + tipo é obrigatória antes de criar/repetir.
- O status da CampaignAction e o status do artefacto podem divergir e devem ser apresentados como estados distintos.
- Próximo passo recomendado: iniciar FE-CAI-002 a FE-CAI-004, mantendo estas quatro decisões como critérios de aceitação do read e create paths.
