# Resultado — Prompt 02: remodelar entity CampaignAction

## Execução de 2026-07-01 10:58:16 -01:00

**Estado da execução:** `executado_parcialmente`

### Resumo objectivo

`entities/campaign-action` foi remodelada para representar exclusivamente o contrato persistente real de `/api/v1/campaign-actions/`, usando o padrão `snake_case` já adoptado pelas restantes entities. A implementação antiga de API e hooks agregados foi removida da entity. O comportamento pré-cutover da War Room foi isolado numa projecção explicitamente legada na feature, sem mudança visual ou de fluxo nesta iteração.

O estado é parcial apenas porque `pnpm build` ficou bloqueado por permissões do ambiente; lint e typecheck completo passaram.

### Contrato entregue

- `CampaignAction` contém os 22 campos públicos reais do serializer backend.
- Enums exactos para `action_type`, `status`, `priority` e `source`.
- `asset_request`, `artifactKind`, `rawStatus`, status `unknown` e ids de artefacto deixaram de fazer parte do modelo canónico.
- `CreateCampaignActionPayload` é uma union discriminada por `action_type`, exige recommendation ref/snapshot nos tipos não manuais e limita relações incompatíveis.
- `UpdateCampaignActionPayload` contém apenas campos actualizáveis; não permite campos imutáveis nem server-managed.
- `DismissCampaignActionPayload` representa o body do endpoint semântico dismiss.
- Helpers passaram a operar directamente sobre os enums persistentes e incluem labels de priority/source.
- Não foram implementadas chamadas à CampaignAction API neste prompt.

### Compatibilidade mínima

A listagem e criação antigas continuam temporariamente operacionais através de `features/campaign-actions/legacy-artifact-action-projection.ts`. Os nomes `LegacyArtifactActionProjection`, `artifactId` e `actionType` tornam explícito que estes valores não são CampaignActions persistentes. A entity canónica já não importa `apiClient`, não agrega endpoints e não exporta os hooks antigos.

Esta ponte deve ser removida em FE-CAI-003/FE-CAI-005, quando os hooks directos e o read cutover forem implementados.

### Ficheiros criados ou alterados

**Entity canónica:**

- Alterados `frontend/src/entities/campaign-action/model.ts`, `helpers.ts`, `index.ts` e `query-keys.ts`.
- Removidos `campaign-action-api.ts`, `useCampaignActions.ts`, `useCreateCampaignAction.ts` e `useUpdateCampaignAction.ts`.

**Compatibilidade temporária e referências de build:**

- Criado `frontend/src/features/campaign-actions/legacy-artifact-action-projection.ts`.
- Alterados `action-type-options.ts`, `recommendation-action-draft.ts`, `recommendation-action-match.ts`, `RecommendationActionState.tsx`, `CreateActionFromRecommendationButton.tsx`, `CreateActionFromRecommendationDialog.tsx` e `features/campaign-actions/index.ts`.
- Alterados apenas os imports/hook legado em `CampaignWarRoomPage.tsx` e `CampaignActionsPanel.tsx`; não houve alteração visual nem cutover do read path.

**Documentação:**

- Criado este relatório.

### Validações executadas e resultado

- `pnpm lint`: **passou**.
- `pnpm build`: **bloqueado pelo ambiente**. A execução final falhou exclusivamente com `TS5033/EPERM` ao tentar escrever `node_modules/.tmp/tsconfig.*.tsbuildinfo`.
- Typecheck alternativo de `tsconfig.app.json` e `tsconfig.node.json`, com build info em `%TEMP%`: **passou sem erros**.
- `vite build` isolado: **bloqueado pelo ambiente** com `spawn EPERM` ao carregar a configuração.
- `git diff --check`: **passou**, apenas com avisos informativos LF/CRLF.
- Inspecção da entity canónica: **passou**; sem `apiClient`, `Promise.allSettled`, endpoints de artefactos, `artifactKind` ou `rawStatus`.
- Browser e servidores: não usados/iniciados.
- Verificação de secrets no relatório e alterações: sem valores sensíveis encontrados.

### Pendências, riscos e próximo passo recomendado

- Reexecutar `pnpm build` num ambiente que permita escrever o cache TypeScript e criar subprocessos do Vite.
- Implementar FE-CAI-003: cliente e hooks directos para list/detail/create/PATCH/transições da CampaignAction API.
- Depois dos hooks reais, executar o corte do painel e remover integralmente `legacy-artifact-action-projection.ts`.
- A War Room ainda lê a projecção antiga por decisão de escopo desta iteração; não confundir build compatível com integração backend concluída.
- Os payloads impedem relações incompatíveis em object literals, mas o backend continua a ser a autoridade para lifecycle, tenant/campaign e deduplicação.
