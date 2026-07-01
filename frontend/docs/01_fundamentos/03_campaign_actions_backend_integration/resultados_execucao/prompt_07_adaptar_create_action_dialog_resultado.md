# Resultado — Prompt 07: adaptar Create Action dialog

## Execução de 2026-07-01 13:16:32 -01:00

**Estado da execução:** `executado_parcialmente`

### Resumo objectivo

O `CreateActionFromRecommendationDialog` foi migrado para criar CampaignAction persistente no caso `manual_task`, usando exclusivamente campos canónicos top-level. Os tipos dependentes de artefacto permanecem visíveis mas desactivados até à orquestração do Prompt 08; o caminho legado que chamava directamente os endpoints proprietários foi removido.

O estado é parcial porque content pack, report e media kit ainda dependem do Prompt 08 e porque `pnpm build` continua bloqueado pelo ambiente. Lint e typecheck integral passaram.

### Implementação entregue

- Action type options canónicas contêm os seis tipos persistíveis; `asset_request` permanece ausente.
- O dialog oferece `manual_task` activo e mostra `content_pack`, `report_request` e `media_kit_request` desactivados com copy “orchestration pending”.
- `mark_reviewed` e `dismiss` não aparecem neste dialog, pois pertencem aos fluxos semânticos próprios.
- Priority livre foi substituída por Select exacto `low|medium|high|urgent`.
- `manual_task` executa `POST /campaign-actions/` através de `useCreateCampaignAction`.
- O payload usa `title`, `description`, `priority`, `source`, `recommendation_ref` e `recommendation_snapshot` como campos top-level; não envia metadata substituta.
- A criação bem-sucedida reutiliza as invalidações da entity para lista, detail e matching exacto.
- Double submit é bloqueado no handler e nos controlos enquanto `mutation.isPending`.
- Duplicado 400 em `recommendation_ref` mostra “Action already exists” e invalida a query exacta para refetch/convergência.
- Field errors usam os nomes snake_case reais: `recommendation_ref`, `recommendation_snapshot`, `related_report`, `related_media_kit`, `related_content_pack_request`, `dismiss_reason` e `priority`.
- O dialog deixou de importar catálogo de content packs ou chamar `/content-pack-requests/`, `/reports/` e `/media-kits/`.

### Estado honesto da orquestração

Os três tipos com artefacto não executam submit nesta iteração. Mantê-los desactivados evita criar apenas o artefacto e deixar CampaignAction ausente. O Prompt 08 deve activá-los depois de implementar artefacto primeiro, CampaignAction relacionada depois, incluindo recuperação de sucesso parcial.

### Ficheiros criados ou alterados

- Alterado `frontend/src/features/campaign-actions/CreateActionFromRecommendationDialog.tsx`.
- Alterado `frontend/src/features/campaign-actions/action-type-options.ts`.
- Alterados `recommendation-action-draft.ts` e `features/campaign-actions/index.ts` para os novos tipos/options.
- Removido `frontend/src/features/campaign-actions/legacy-artifact-action-projection.ts`.
- Criado este relatório.

### Validações executadas e resultado

- `pnpm lint`: **passou** na execução final.
- ESLint dirigido aos ficheiros alterados: **passou**.
- `pnpm build`: **bloqueado pelo ambiente** com `TS5033/EPERM` ao escrever `node_modules/.tmp/tsconfig.*.tsbuildinfo`; não chegou ao Vite.
- Typecheck alternativo de `tsconfig.app.json` e `tsconfig.node.json`, usando build info em `%TEMP%`: **passou sem erros**.
- Grep do dialog por `apiClient`, endpoints proprietários, `action_priority`, `action_description` e `metadata`: **sem ocorrências**.
- Inspecção de payload, field errors, duplicate handling e double-submit: **passou**.
- Browser e servidores: não usados/iniciados. Validação visual fica para o prompt final.
- Verificação de secrets no relatório e alterações: sem valores sensíveis encontrados.

### Pendências, riscos e próximo passo recomendado

- Implementar Prompt 08 antes de activar content pack/report/media kit no Select.
- A UX actual escolhe `manual_task` por omissão mesmo quando a recommendation sugere um tipo com artefacto; isto é deliberado para impedir um fluxo incompleto.
- Reexecutar `pnpm build` num ambiente sem o bloqueio de escrita.
- Próximo passo recomendado: criar funções proprietárias nas entities de artefacto e a orquestração artefacto -> CampaignAction com retry apenas da segunda escrita.
