# Resultado — Prompt 11: lifecycle e artefactos relacionados

## Execução de 2026-07-01 18:38:41 -01:00

**Estado da execução:** `executado_parcialmente`

### Resumo objectivo

- O Campaign Actions Panel passou a expor operações semânticas sobre um CampaignAction id explícito.
- A matriz apresentada replica o Backend Core: `pending` permite complete, cancel e dismiss; `in_progress` permite complete e cancel; `completed`, `failed`, `dismissed` e `cancelled` não expõem transições.
- Complete usa `/complete/`, cancel usa `/cancel/` com confirmação e dismiss usa `/dismiss/` com `dismiss_reason` obrigatório.
- Não existe optimistic status nem reopen. Erros deixam a action no estado retornado pela query persistente.
- Uma action `failed` oferece “Retry as new action”. O retry cria uma nova CampaignAction com os campos canónicos, recommendation context e FKs formais compatíveis; a action failed original não é alterada.
- Após retry bem-sucedido, o controlo indica “New action created” e evita um segundo POST imediato a partir da mesma linha.
- `completed_at`, `cancelled_at` e `dismiss_reason` continuam a ser apresentados exclusivamente a partir da resposta do servidor.
- As quatro relações formais são mostradas directamente: `related_content_pack_request`, `related_content_output`, `related_report` e `related_media_kit`. Não existe inferência por metadata.
- Actions que normalmente dependem de artefacto mas têm todas as FKs null mostram “Related artifact unavailable or not linked”. Actions manuais/review/dismiss aceitam naturalmente ausência de relação.
- Não foi introduzido selector para ligar artefactos existentes: o frontend ainda não tem rotas/detail/selectors que garantam campaign e workspace antes do PATCH. A associação continua possível no contrato tipado, mas não é exposta sem scoping seguro.
- Não existia UI de edição de title/description/priority; por isso não foi acrescentado um formulário PATCH nesta iteração. O hook `useUpdateCampaignAction` existente permanece disponível para uma UI futura.

### Ficheiros criados ou alterados

- `frontend/src/entities/campaign-action/lifecycle.ts` — criado; matriz do painel, estados terminais e builder de retry-as-new.
- `frontend/src/entities/campaign-action/index.ts` — exports de lifecycle.
- `frontend/src/entities/campaign-action/useCampaignActionTransition.ts` — invalidação best-effort após transição concluída.
- `frontend/src/entities/campaign-action/useCreateCampaignAction.ts` — invalidação best-effort após POST concluído.
- `frontend/src/widgets/campaign-actions-panel/CampaignActionLifecycleControls.tsx` — criado; complete, cancel, dismiss e retry.
- `frontend/src/widgets/campaign-actions-panel/DismissCampaignActionDialog.tsx` — criado; dismiss semântico com motivo obrigatório.
- `frontend/src/widgets/campaign-actions-panel/CampaignActionsPanel.tsx` — integração dos controlos, timestamps e relações/null.
- `frontend/src/widgets/campaign-actions-panel/CampaignActionsPanel.module.css` — layout responsivo dos controlos, erros e diálogo.
- `frontend/docs/01_fundamentos/03_campaign_actions_backend_integration/resultados_execucao/prompt_11_lifecycle_artefactos_resultado.md` — criado.

### Validações executadas e resultado

- `pnpm lint`: passou na execução final, exit code 0.
- `pnpm build`: não concluiu por limitação do ambiente (`TS5033 EPERM`) ao escrever `node_modules/.tmp/tsconfig.*.tsbuildinfo`; não chegou ao bundling Vite.
- Typecheck alternativo de `tsconfig.app.json` e `tsconfig.node.json`, com build info em `%TEMP%`: passou sem erros.
- ESLint dirigido aos helpers, hooks e componentes de lifecycle: passou.
- Inspecção da matriz: pending contém apenas complete/cancel/dismiss; in_progress contém apenas complete/cancel; todos os estados terminais devolvem zero transições.
- Inspecção dos endpoints: os controlos produzem inputs semânticos `complete`, `cancel` e `dismiss`; dismiss envia `dismiss_reason` top-level.
- Inspecção do retry: requer status failed, cria payload novo sem id/status/timestamps e copia apenas relações formais compatíveis com o action type.
- Inspecção do painel: mostra `completed_at`, `cancelled_at`, `dismiss_reason` e os quatro campos `related_*`; não consulta metadata para relações.
- Grep por headers/tokens/serviços internos e portas proibidas: sem ocorrências nos ficheiros relevantes.
- `git diff --check`: passou; apenas avisos informativos de normalização LF/CRLF.
- O frontend continua sem script/test runner unitário configurado; não foram criados testes nesta iteração.
- Browser e servidores não foram usados/iniciados.
- Relatório revisto: não contém secrets.

### Pendências, riscos ou próximo passo recomendado

- Reexecutar `pnpm build` num ambiente que permita escrever o cache incremental em `node_modules/.tmp`.
- Adicionar no Prompt 12 testes unitários para a matriz de transições, builder de retry por action type, estados terminais e motivo obrigatório.
- Depois de reload, uma linha failed pode voltar a oferecer retry mesmo que já exista uma nova action activa; o backend continua autoridade e rejeita duplicado activo. Uma evolução pode fazer preflight exacto por ref + tipo também neste controlo.
- A apresentação das relações usa ids porque ainda não existem rotas detail dedicadas. Criar links ou selectors apenas quando cada entity expuser lookup limitado à campaign/workspace actual.
- A invalidação posterior a uma escrita é best-effort para não representar uma transição/POST já concluído como falha; um refetch ou reload recupera o estado canónico.
- Próximo passo recomendado: introduzir o test runner e cobrir lifecycle/matching/orquestração antes da limpeza e validação final da fase.
