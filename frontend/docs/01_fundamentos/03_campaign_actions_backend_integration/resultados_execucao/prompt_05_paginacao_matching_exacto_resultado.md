# Resultado — Prompt 05: paginação e matching exacto

## Execução de 2026-07-01 11:26:56 -01:00

**Estado da execução:** `executado_parcialmente`

### Resumo objectivo

A paginação da CampaignAction API foi endurecida para impedir truncamento silencioso e falsos estados “sem action”. O painel mantém paginação visível; o matching por recommendation usa agora um hook exacto dedicado e decide existência através de `count`, nunca apenas pelo conteúdo da primeira página.

O estado é parcial apenas porque o build não consegue escrever o cache TypeScript. Lint e typecheck integral passaram.

### Decisão mínima aplicada

- **Painel:** paginação visível de 25 items, com `count`, `next`, `previous`, `results`, `page` e `page_size` consumidos explicitamente.
- **Matching exacto:** primeira página com `page_size=100`, o máximo confirmado do backend, filtrada por `campaign + recommendation_ref`.
- `count > 0` é a fonte de verdade para “existe action”. `results` é apenas a página actualmente carregada.
- Se `count` exceder `results.length`, a UI mostra `+N more`; não afirma ter carregado todas as actions.
- Ordering não é enviado pelo frontend, preservando o default backend `-created_at`.

### Implementação entregue

- Criado `useCampaignActionsByRecommendation`, desactivado enquanto não existir campaign/ref e apoiado na query key específica já preparada para recommendation.
- Centralizado `RECOMMENDATION_ACTION_PAGE_SIZE=100` com documentação de que o resultado pode continuar parcial.
- `CreateActionFromRecommendationButton` usa `data.count` para distinguir “zero actions” de “página parcial”.
- O empty state do painel só declara campanha vazia quando `count === 0`.
- Se `count > 0` mas `results` vier vazia, o painel informa que apenas a página está vazia e oferece retorno à primeira página.
- O envelope paginado continua intacto em `useCampaignActions`; não existe `select` que descarte `count`, `next` ou `previous`.

### Ficheiros criados ou alterados

- Criado `frontend/src/entities/campaign-action/useCampaignActionsByRecommendation.ts`.
- Alterados `frontend/src/entities/campaign-action/index.ts` e `campaign-action-api.ts`.
- Alterado `frontend/src/features/campaign-actions/CreateActionFromRecommendationButton.tsx`.
- Alterados `frontend/src/widgets/campaign-actions-panel/CampaignActionsPanel.tsx` e `CampaignActionsPanel.module.css`.
- Criado este relatório.

### Validações executadas e resultado

- `pnpm lint`: **passou** na execução final. Uma tentativa anterior ficou lenta e foi terminada sem output de erro; o ESLint directo também passou.
- `pnpm build`: **bloqueado pelo ambiente** com `TS5033/EPERM` ao escrever `node_modules/.tmp/tsconfig.*.tsbuildinfo`; não chegou ao Vite.
- Typecheck alternativo de `tsconfig.app.json` e `tsconfig.node.json`, com build info em `%TEMP%`: **passou sem erros**.
- Inspecção de truncamento: não existe `slice` aplicado a CampaignAction `results`; o único `.slice(0, 48)` encontrado pertence à slug defensiva de `recommendation_ref`, não à paginação.
- Inspecção do envelope: `count`, `next`, `previous`, `results`, `page` e `page_size` são preservados/consumidos no read path.
- Browser e servidores: não usados/iniciados.
- Verificação de secrets no relatório e alterações: sem valores sensíveis encontrados.

### Pendências, riscos e próximo passo recomendado

- Reexecutar `pnpm build` num ambiente sem o bloqueio de escrita observado.
- O matching carrega no máximo 100 registos detalhados por recommendation; `count` impede falso zero, mas a UI resume o excedente em vez de o listar integralmente.
- Uma request exacta é feita por recommendation visível. Medir antes de introduzir batching ou infinite queries adicionais.
- Próximo passo recomendado: migrar o create path e usar esta query exacta antes de qualquer retry/deduplicação por `recommendation_ref + action_type`.
