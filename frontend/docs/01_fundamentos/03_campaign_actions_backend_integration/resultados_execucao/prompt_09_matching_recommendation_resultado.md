# Resultado — Prompt 09: matching de recommendations

## Execução de 2026-07-01 14:20:00 -01:00

**Estado da execução:** `executado_parcialmente`

### Resumo objectivo

- O matching passou a agrupar todas as `CampaignAction` pelo campo canónico top-level `recommendation_ref`; metadata não participa na correlação.
- Uma recommendation é representada por `CampaignAction[]`, preservando múltiplos tipos e histórico terminal.
- A deduplicação usa exclusivamente `recommendation_ref + action_type` e considera activos apenas `pending`, `in_progress` e `completed`.
- Actions `failed`, `dismissed` ou `cancelled` permanecem visíveis e permitem uma nova criação do mesmo tipo.
- O estado visual distingue `pending`, `in_progress`, `completed`, `failed`, `cancelled`, `dismissed` e `reviewed`. `reviewed` é derivado apenas de `action_type=mark_reviewed` com `status=completed`.
- O botão continua disponível quando existem actions de outros tipos e abre o diálogo como “Create another action”.
- Enquanto o diálogo está aberto, é feita uma pesquisa exacta por campaign, recommendation ref e action type. Todas as páginas desse filtro são carregadas antes de permitir submit, evitando falsos negativos após históricos superiores a 100 registos.
- Quando existe uma action activa do tipo seleccionado, apenas esse submit é bloqueado; o utilizador pode escolher outro tipo.
- Um erro 400 de duplicado força refetch da query exacta e invalida a raiz de matching, fazendo o diálogo e o estado da recommendation convergirem para a action persistente criada noutra tab/request.
- Não foi necessária alteração adicional no `CampaignRecommendationsPanel`: a integração existente da War Room renderiza o botão por recommendation e o próprio affordance gere as queries exactas.

### Ficheiros criados ou alterados

- `frontend/src/features/campaign-actions/recommendation-action-match.ts` — agrupamento, matriz activa, matching por tipo e estado reviewed.
- `frontend/src/features/campaign-actions/RecommendationActionState.tsx` — apresentação de múltiplas actions e dos sete estados requeridos.
- `frontend/src/features/campaign-actions/CreateActionFromRecommendationButton.tsx` — preserva criação de tipos adicionais e monta o diálogo apenas quando aberto.
- `frontend/src/features/campaign-actions/CreateActionFromRecommendationDialog.tsx` — preflight exacto por tipo, bloqueio selectivo e convergência após duplicado 400.
- `frontend/src/features/campaign-actions/index.ts` — exports dos novos helpers/tipos.
- `frontend/src/entities/campaign-action/useCampaignActionsByRecommendation.ts` — filtro opcional por tipo e query exacta all-pages para deduplicação.
- `frontend/src/entities/campaign-action/index.ts` — export da nova query.
- `frontend/docs/01_fundamentos/03_campaign_actions_backend_integration/resultados_execucao/prompt_09_matching_recommendation_resultado.md` — criado.

### Validações executadas e resultado

- `pnpm lint`: passou na execução final, exit code 0.
- `pnpm build`: não concluiu por limitação do ambiente (`TS5033 EPERM`) ao escrever `node_modules/.tmp/tsconfig.*.tsbuildinfo`; não chegou ao bundling Vite.
- Typecheck alternativo de `tsconfig.app.json` e `tsconfig.node.json`, com build info em `%TEMP%`: passou sem erros.
- ESLint dirigido aos ficheiros de matching/query/dialog: passou.
- Inspecção da matriz activa: contém apenas `pending`, `in_progress` e `completed`; os três estados terminais retryable não estão no conjunto.
- Inspecção do estado reviewed: exige simultaneamente `mark_reviewed` e `completed`.
- Inspecção das queries: o preflight inclui `campaign`, `recommendation_ref`, `action_type`, paginação até `count` e query key dedicada `all-pages`.
- Grep de matching por metadata ou primeiro match global: sem ocorrências.
- `git diff --check`: passou; apenas avisos informativos de normalização LF/CRLF.
- O frontend continua sem script/test runner unitário configurado; não foram criados testes nesta iteração.
- Browser e servidores não foram usados/iniciados.
- Relatório revisto: não contém secrets.

### Pendências, riscos ou próximo passo recomendado

- Reexecutar `pnpm build` num ambiente que permita escrever o cache incremental em `node_modules/.tmp`.
- Adicionar no Prompt 12 testes unitários para agrupamento por ref, múltiplos tipos, matriz activa/terminal, reviewed, dismissed versus cancelled e convergência após duplicado.
- O resumo junto da recommendation mantém a decisão da Iteração 05: mostra a primeira página de até 100 actions e explicita o excedente com `+N more`. Apenas o preflight de deduplicação carrega todas as páginas, quando o diálogo está aberto.
- Históricos excepcionalmente longos do mesmo tipo exigem requests sequenciais adicionais no preflight; isto privilegia consistência sobre submit prematuro e deve ser monitorizado.
- Próximo passo recomendado: implementar os affordances persistentes de Mark reviewed e Dismiss sobre este matching, mantendo a deduplicação por tipo.
