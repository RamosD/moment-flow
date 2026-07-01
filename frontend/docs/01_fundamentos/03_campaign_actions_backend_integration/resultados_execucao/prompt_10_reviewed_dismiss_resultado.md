# Resultado — Prompt 10: Mark Reviewed e Dismiss

## Execução de 2026-07-01 18:31:15 -01:00

**Estado da execução:** `executado_parcialmente`

### Resumo objectivo

- Foram adicionados affordances persistentes `Mark reviewed` e `Dismiss` por recommendation.
- `Mark reviewed` cria directamente uma `CampaignAction` com `action_type=mark_reviewed`, recommendation ref/snapshot canónicos e sem `status` explícito; o Backend Core aplica atomicamente `completed`.
- `Dismiss` abre um diálogo de confirmação, exige `dismiss_reason` não vazio e cria directamente uma `CampaignAction` com `action_type=dismiss`; o Backend Core aplica atomicamente `dismissed`.
- Não é criada uma action intermédia para chamar depois um endpoint semântico. Neste contexto há potencialmente várias actions por recommendation e não existe um id único cuja transição seja semanticamente inequívoca; os endpoints por id ficam reservados para operações explícitas sobre uma action no painel.
- Antes da criação, o fluxo consulta todas as páginas da chave exacta `campaign + recommendation_ref + action_type`. Se já existir action activa, converge para essa action sem novo POST.
- Se outra request ganhar a corrida e o POST devolver 400 de duplicado, o fluxo repete a consulta exacta e converge para a CampaignAction persistente.
- Após criação ou convergência são invalidadas lista, detalhe e queries exactas por recommendation ref. O estado visual deriva apenas das respostas persistentes e, por isso, reviewed/dismissed reaparecem após reload.
- Erros 400 de `dismiss_reason` são apresentados junto ao campo; 400 de duplicado converge; 401, 403 e 404 usam os presets globais seguros.
- Não existe persistência em localStorage/sessionStorage, estado local de domínio ou metadata de artefactos. O estado React limita-se à abertura do diálogo e ao texto ainda não submetido.

### Ficheiros criados ou alterados

- `frontend/src/features/campaign-actions/useRecommendationDecision.ts` — criado; preflight exacto, criação persistente, convergência de concorrência e invalidação.
- `frontend/src/features/campaign-actions/RecommendationDecisionActions.tsx` — criado; affordances Mark reviewed e Dismiss.
- `frontend/src/features/campaign-actions/DismissRecommendationDialog.tsx` — criado; confirmação, motivo obrigatório e erros de API.
- `frontend/src/features/campaign-actions/CreateActionFromRecommendationButton.tsx` — integração dos affordances por recommendation.
- `frontend/src/features/campaign-actions/campaign-actions.module.css` — estilos dos affordances e erro inline.
- `frontend/src/features/campaign-actions/index.ts` — exports actualizados.
- `frontend/src/entities/campaign-action/campaign-action-api.ts` — helper paginado exacto reutilizável por recommendation ref + action type.
- `frontend/src/entities/campaign-action/useCampaignActionsByRecommendation.ts` — reutilização do helper exacto.
- `frontend/src/entities/campaign-action/index.ts` — export do helper exacto.
- `frontend/docs/01_fundamentos/03_campaign_actions_backend_integration/resultados_execucao/prompt_10_reviewed_dismiss_resultado.md` — criado.

### Validações executadas e resultado

- `pnpm lint`: passou na execução final, exit code 0.
- `pnpm build`: não concluiu por limitação do ambiente (`TS5033 EPERM`) ao escrever `node_modules/.tmp/tsconfig.*.tsbuildinfo`; não chegou ao bundling Vite.
- Typecheck alternativo de `tsconfig.app.json` e `tsconfig.node.json`, com build info em `%TEMP%`: passou sem erros.
- ESLint dirigido aos ficheiros novos/alterados: passou; uma execução dirigida anterior ficou presa sem output e foi terminada antes da execução oficial bem-sucedida.
- Inspecção dos payloads: `mark_reviewed` e `dismiss` são POST directos de CampaignAction, `dismiss_reason` é top-level e não é enviado status inventado pelo frontend.
- Inspecção do backend: o serializer cria `mark_reviewed` como `completed` e `dismiss` como `dismissed`, exigindo motivo para dismiss.
- Inspecção de concorrência: preflight e recuperação do 400 usam a consulta exacta all-pages; mutations globais têm `retry: false`.
- Inspecção de invalidação: lista, detalhe e recommendation root são invalidados através de `invalidateCampaignActionCache`.
- Grep por localStorage, sessionStorage, metadata de artefactos e chamadas ambíguas a `markCampaignActionReviewed`/`dismissCampaignAction` nos novos fluxos: sem ocorrências.
- Grep por `X-Internal-Token`, `INTERNAL_API_TOKEN`, `intelligence_engine`, `content_renderer`, `localhost:8001` e `localhost:8002`: sem ocorrências nos ficheiros relevantes.
- `git diff --check`: passou; apenas avisos informativos de normalização LF/CRLF.
- O frontend continua sem script/test runner unitário configurado; não foram criados testes nesta iteração.
- Browser e servidores não foram usados/iniciados.
- Relatório revisto: não contém secrets.

### Pendências, riscos ou próximo passo recomendado

- Reexecutar `pnpm build` num ambiente que permita escrever o cache incremental em `node_modules/.tmp`.
- Adicionar no Prompt 12 testes para criação reviewed/dismissed, motivo vazio, 400 duplicado concorrente, 401, 403, 404 e invalidações.
- `dismissed` é terminal e não pertence ao conjunto de duplicados activos do backend; por decisão da Iteração 09, uma recommendation anteriormente dismissed pode receber uma nova action `dismiss`. Se o produto quiser impedir dismiss repetido, essa será uma regra UX adicional e não deve ser confundida com a constraint actual.
- A invalidação de cache após um POST concluído é best-effort: uma falha de refetch não transforma uma escrita bem-sucedida num erro que incentive repetição. O reload continua a recuperar o estado canónico.
- Próximo passo recomendado: implementar lifecycle e endpoints semânticos no painel, onde existe um CampaignAction id explícito e a transição deixa de ser ambígua.
