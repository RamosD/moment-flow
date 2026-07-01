# Resultado — Prompt 03: API e hooks directos de CampaignAction

## Execução de 2026-07-01 11:08:10 -01:00

**Estado da execução:** `executado_parcialmente`

### Resumo objectivo

A entity `campaign-action` passou a expor uma camada de API directa e cinco hooks para a entidade persistente do Backend Core. Todas as operações usam exclusivamente `/campaign-actions/`; a entity não chama nem agrega content pack requests, reports ou media kits.

O estado é parcial apenas porque o comando obrigatório `pnpm build` continua bloqueado por permissões do ambiente. Lint e typecheck integral passaram.

### Implementação entregue

- GET paginado de `/campaign-actions/` com filtros exactos `campaign`, `status`, `action_type`, `recommendation_ref`, `source` e `created_by`, além de `page` e `page_size`.
- GET detail, POST create e PATCH update.
- POST semântico para `mark-reviewed`, `dismiss`, `cancel` e `complete`.
- `useCampaignActions`, `useCampaignAction`, `useCreateCampaignAction`, `useUpdateCampaignAction` e `useCampaignActionTransition`.
- `useCampaignActions` devolve o envelope DRF completo (`count`, `next`, `previous`, `results`); não trunca nem transforma a resposta numa lista silenciosa.
- Leituras propagam o `AbortSignal` fornecido por TanStack Query.
- Query keys incluem workspace, campaign, filtros e paginação. Pesquisas com `recommendation_ref` têm uma família de keys exacta própria.
- Mutations invalidam listas da campaign, detail da action e a família exacta da recommendation quando existe ref.
- Create/update/dismiss removem defensivamente qualquer campo `workspace` recebido de um caller não tipado. O workspace continua exclusivamente no header injectado pelo cliente central.
- Erros 400 e 422 continuam mapeados para `ValidationError` pelo `apiClient` central.
- Nenhuma função desta entity aceita headers customizados; autenticação e `X-Workspace-ID` continuam centralizados.

### Ficheiros criados ou alterados

- Criado/actualizado `frontend/src/entities/campaign-action/campaign-action-api.ts`.
- Actualizados `model.ts`, `query-keys.ts` e `index.ts`.
- Criados/actualizados `useCampaignActions.ts`, `useCampaignAction.ts`, `useCreateCampaignAction.ts`, `useUpdateCampaignAction.ts` e `useCampaignActionTransition.ts`.
- Criado `invalidate-campaign-action-cache.ts` para invalidação consistente das três superfícies de cache.
- Criado este relatório.
- Nenhum ficheiro de UI foi alterado nesta iteração.

### Validações executadas e resultado

- `pnpm lint`: **passou**.
- `pnpm build`: **bloqueado pelo ambiente** com `TS5033/EPERM` ao escrever `node_modules/.tmp/tsconfig.app.tsbuildinfo` e `tsconfig.node.tsbuildinfo`; a execução não chegou ao Vite.
- Typecheck alternativo de `tsconfig.app.json` e `tsconfig.node.json`, usando build info em `%TEMP%`: **passou sem erros**.
- `git diff --check`: **passou**, com apenas avisos informativos LF/CRLF.
- Scan da entity: apenas chamadas `apiClient.get/post/patch` para a constante `/campaign-actions/`; sem `Promise.allSettled` ou endpoints de artefactos.
- `X-Internal-Token`: encontrado apenas em comentários, documentação e no guard defensivo do cliente central que bloqueia o header.
- `INTERNAL_API_TOKEN`: sem ocorrências em `frontend/src`.
- `intelligence_engine`: sem ocorrências em `frontend/src`.
- `content_renderer`: sem ocorrências em `frontend/src`.
- `localhost:8001`: sem ocorrências em `frontend/src`.
- `localhost:8002`: sem ocorrências em `frontend/src`.
- Browser e servidores: não usados/iniciados.
- Verificação de secrets no relatório e alterações: sem valores sensíveis encontrados.

### Pendências, riscos e próximo passo recomendado

- Reexecutar `pnpm build` num ambiente com permissão para o cache incremental TypeScript.
- A War Room continua deliberadamente na projecção legada até ao prompt de cutover; os hooks novos ainda não são consumidores da UI.
- Implementar FE-CAI-004 para paginação visível/infinita e evitar falsos negativos fora da página carregada.
- Executar depois FE-CAI-005: ligar o Campaign Actions Panel à query persistente e aplicar o corte histórico decidido no Prompt 01.
- A criação de artefactos e a escrita CampaignAction em duas etapas continuam para o incremento próprio; estes hooks não criam artefactos implicitamente.
