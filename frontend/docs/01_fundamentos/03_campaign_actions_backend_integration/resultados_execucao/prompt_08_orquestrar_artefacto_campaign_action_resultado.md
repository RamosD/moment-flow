# Prompt 08 — Orquestrar artefacto e CampaignAction

## Execução de 2026-07-01 14:09:17 -01:00

**Estado da execução:** `executado_parcialmente`

### Resumo objectivo

- Implementada a feature `useCreateActionFromRecommendation` com a ordem obrigatória: criação do artefacto proprietário, seguida da criação da `CampaignAction` com a FK `related_*` correspondente.
- Os POST de `content-pack-requests`, `reports` e `media-kits` ficaram nas respectivas entities; `campaign-action` não chama esses endpoints.
- `manual_task`, `mark_reviewed` e `dismiss` criam apenas `CampaignAction`, sem artefacto.
- Após sucesso, são invalidadas as queries do domínio do artefacto e as listas, detalhe e matching exacto da `CampaignAction`.
- O diálogo passou a executar o fluxo real para `content_pack`, `report_request` e `media_kit_request`, mantendo protecção contra double submit.
- Em sucesso parcial, o id e tipo do artefacto são preservados num erro tipado. O retry consulta primeiro `campaign + recommendation_ref + action_type` e cria ou reconcilia apenas a `CampaignAction`; não repete o POST do artefacto e não executa rollback destrutivo.
- A resposta do artefacto é validada contra o workspace activo e a campaign do payload antes do segundo POST. Conflitos de scope ou de relação ficam não-retryable.

### Ficheiros criados ou alterados nesta iteração

- `frontend/src/entities/content-pack-request/model.ts` — criado.
- `frontend/src/entities/content-pack-request/content-pack-request-api.ts` — criado.
- `frontend/src/entities/content-pack-request/query-keys.ts` — criado.
- `frontend/src/entities/content-pack-request/index.ts` — criado.
- `frontend/src/entities/report/model.ts` — payload de criação acrescentado.
- `frontend/src/entities/report/report-api.ts` — POST proprietário acrescentado.
- `frontend/src/entities/report/index.ts` — exports actualizados.
- `frontend/src/entities/media-kit/model.ts` — payload de criação acrescentado.
- `frontend/src/entities/media-kit/media-kit-api.ts` — POST proprietário acrescentado.
- `frontend/src/entities/media-kit/index.ts` — exports actualizados.
- `frontend/src/entities/campaign-action/index.ts` — export público da invalidação canónica.
- `frontend/src/features/campaign-actions/useCreateActionFromRecommendation.ts` — criado; orquestração, sucesso parcial e retry seguro.
- `frontend/src/features/campaign-actions/CreateActionFromRecommendationDialog.tsx` — integração do submit real e recuperação de sucesso parcial.
- `frontend/src/features/campaign-actions/action-type-options.ts` — activação dos tipos com artefacto.
- `frontend/src/features/campaign-actions/campaign-actions.module.css` — apresentação do estado parcial/retry.
- `frontend/src/features/campaign-actions/index.ts` — exports actualizados.
- `frontend/docs/01_fundamentos/03_campaign_actions_backend_integration/resultados_execucao/prompt_08_orquestrar_artefacto_campaign_action_resultado.md` — criado.

### Validações executadas

- `pnpm lint`: passou, exit code 0.
- `pnpm build`: não concluiu por limitação do ambiente (`TS5033 EPERM`) ao escrever `node_modules/.tmp/tsconfig.*.tsbuildinfo`.
- TypeScript da app e configuração, executado separadamente com `tsBuildInfoFile` em `%TEMP%`: passou sem erros.
- Bundling Vite isolado: não concluiu por `spawn EPERM` ao carregar `vite.config.ts`, também uma restrição do ambiente.
- Inspecção do bloco `retryCampaignActionRegistration`: passou; não contém chamadas a `createArtifact`, `createContentPackRequest`, `createReport` ou `createMediaKit`.
- Inspecção do `QueryClient`: mutations têm `retry: false`, portanto não existe retry automático do primeiro passo.
- Grep dos endpoints: os POST proprietários existem apenas nas respectivas entities; a feature consome as funções públicas.
- Grep por `X-Internal-Token`, `INTERNAL_API_TOKEN`, `intelligence_engine`, `content_renderer`, `localhost:8001` e `localhost:8002` nos ficheiros runtime relevantes: sem ocorrências.
- `git diff --check`: passou; apenas avisos informativos de normalização LF/CRLF.
- Não existe script/test runner unitário configurado no `frontend/package.json`; validação do retry foi feita por typecheck e inspecção estática.
- Relatório revisto: não contém secrets.
- Browser e servidores não foram usados.

### Pendências, riscos e próximo passo recomendado

- O build completo deve ser repetido num ambiente que permita criar processos do Vite e escrever os ficheiros incrementais em `node_modules/.tmp`.
- Criar testes unitários para os caminhos: sucesso integral, falha no segundo POST, retry com action ausente, reconciliação de action existente e conflito de FK/scope.
- O estado de sucesso parcial é mantido em memória no diálogo. Um reload perde a acção de retry guiado, embora o artefacto permaneça íntegro e o matching exacto continue a impedir retry cego dentro da sessão.
- Existe uma janela concorrente inevitável entre os dois POST: uma criação concorrente pode fazer o backend rejeitar a `CampaignAction` depois de o artefacto existir. O fluxo trata isso como sucesso parcial e reconcilia por matching exacto, sem apagar nem recriar o artefacto.
- Próximo passo recomendado: implementar os fluxos semânticos de reviewed/dismiss sobre actions existentes e cobrir a orquestração com testes automatizados.
