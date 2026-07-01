# Resultado — Prompt 04: migrar read path do Campaign Actions Panel

## Execução de 2026-07-01 11:16:20 -01:00

**Estado da execução:** `executado_parcialmente`

### Resumo objectivo

O Campaign Actions Panel e o estado de actions por recommendation passaram a ler exclusivamente CampaignActions persistentes através da entity `/campaign-actions/`. A War Room deixou de executar a agregação antiga de content pack requests, reports e media kits. Foi aplicado o corte temporal explícito do Prompt 01, sem dual-read.

O estado é parcial apenas porque `pnpm build` permanece bloqueado por permissões do ambiente. Lint e typecheck integral passaram; a validação visual foi deliberadamente adiada.

### Implementação entregue

- `CampaignActionsPanel` usa `useCampaignActions(workspaceId, campaignId, { page, page_size: 25 })` e respeita o envelope paginado.
- Paginação visível com Previous/Next, página actual, total de páginas e contagem global.
- Cada item usa o id real da CampaignAction como key e mostra title, action type, status, priority, source e created_at.
- completed_at, cancelled_at e dismiss_reason aparecem apenas quando relevantes.
- As quatro relações `related_*` são mostradas apenas quando têm id; nenhuma relação é inferida por metadata.
- Copy alterada para “Persistent actions”; o empty state explica que artefactos anteriores permanecem nos seus painéis próprios.
- Loading, error e empty states foram preservados.
- `CampaignWarRoomPage` deixou de iniciar a query legada agregada.
- Cada recommendation faz pesquisa exacta por `recommendation_ref` na CampaignAction API. Uma falha nesse lookup apenas desabilita a criação nessa recommendation.
- Matching passou a usar `recommendation_ref` top-level e representa múltiplas CampaignActions; deixou de seleccionar apenas o primeiro match.
- O módulo temporário do create dialog deixou de conter GETs, projecção de artefactos e `Promise.allSettled`; conserva apenas os POSTs antigos necessários ao create path ainda não migrado.

### Isolamento de falhas

- Falha da lista CampaignAction é tratada dentro do `CampaignActionsPanel`.
- Falha de lookup exacto não lança erro para o painel de Intelligence.
- Campaign Header, Intelligence, Content Outputs, Reports e Media Kits mantêm queries e renderização independentes.

### Ficheiros criados ou alterados

- Alterados `frontend/src/widgets/campaign-actions-panel/CampaignActionsPanel.tsx` e `CampaignActionsPanel.module.css`.
- Alterado `frontend/src/pages/campaign-war-room/CampaignWarRoomPage.tsx` para remover o read legado.
- Alterados `CreateActionFromRecommendationButton.tsx`, `RecommendationActionState.tsx`, `recommendation-action-match.ts`, `campaign-actions.module.css` e `features/campaign-actions/index.ts` para o contrato persistente.
- Reduzido `legacy-artifact-action-projection.ts` ao create path temporário, sem qualquer leitura/agregação.
- Ajuste mínimo de compilação em `CreateActionFromRecommendationDialog.tsx` após simplificar o hook legado.
- Criado este relatório.

### Validações executadas e resultado

- `pnpm lint`: **passou**.
- `pnpm build`: **bloqueado pelo ambiente** com `TS5033/EPERM` ao escrever os ficheiros `node_modules/.tmp/tsconfig.*.tsbuildinfo`; não chegou ao Vite.
- Typecheck alternativo de `tsconfig.app.json` e `tsconfig.node.json`, usando build info em `%TEMP%`: **passou sem erros**.
- Scan do read path por `useLegacyArtifactActionProjections`, `Promise.allSettled` e GETs de artefactos: **sem ocorrências**.
- `git diff --check`: **passou**, apenas com avisos informativos LF/CRLF.
- Browser: não usado. A validação visual do painel, paginação e responsividade fica para o prompt final.
- Servidores: não iniciados.
- Verificação de secrets no relatório e alterações: sem valores sensíveis encontrados.

### Pendências, riscos e próximo passo recomendado

- Reexecutar `pnpm build` num ambiente com permissão para o cache incremental TypeScript.
- O create dialog continua temporariamente a criar apenas o artefacto antigo e ainda não persiste CampaignAction. Não deve ser considerado pronto para rollout até FE-CAI-006/007/008 concluírem snapshot seguro e escrita em duas etapas.
- Os lookups exactos evitam falsos negativos de paginação, mas introduzem uma request por recommendation visível; avaliar batching/cache apenas se medições reais mostrarem necessidade.
- A apresentação completa de retries e deduplicação activa por action type continua no escopo de FE-CAI-009.
- Próximo passo recomendado: implementar snapshot seguro e migrar o create path antes de validar a UI end-to-end.
