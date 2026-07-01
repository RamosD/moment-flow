# Resultado — Prompt 12: segurança, erros e testes

## Execução de 2026-07-01 19:04:38 -01:00

**Estado da execução:** `executado_parcialmente`

### Resumo objectivo

- Foi revista a cadeia completa: API client, entity CampaignAction, criação/orquestração, matching, reviewed/dismiss, lifecycle, painel e composição da War Room.
- O mapping HTTP foi isolado numa função testável e mantém classes distintas para 400/422, 401, 403, 404, 502/503 e falhas de rede.
- 403 continua a produzir “Access denied” e nunca é apresentado como 404. O preset de 404 usa copy genérica e não mostra a mensagem/detail potencialmente associada a um objecto cross-workspace.
- O cliente continua a notificar a sessão global em 401 autenticado; network errors e service unavailable têm presets próprios.
- A sanitização de headers foi endurecida: headers custom não podem substituir `Authorization`, `X-Workspace-ID` ou `X-Internal-Token`. Estes valores pertencem exclusivamente aos providers centrais.
- Writes de CampaignAction passam por sanitização defensiva que remove `workspace` do body, mesmo para callers não tipados. Create/update/dismiss continuam a receber o workspace apenas pelo header central.
- O builder de decisões reviewed/dismiss foi separado e garante bodies sem `status`, `workspace` ou metadata substituta; dismiss_reason é normalizado top-level.
- Não existia Vitest, `tsx` ou `ts-node`. Em vez de adicionar dependências/lockfile sem runtime disponível, foi introduzido `node:test` nativo do Node 22 com type stripping, sem packages novos.
- Foram adicionados 14 testes automatizados para labels/enums, priority, snapshot allowlist/sanitização/tamanho, recommendation ref, workspace stripping, decision payloads, matching múltiplo/deduplicação, reviewed/dismissed, lifecycle, retry-as-new, headers protegidos, erros HTTP/presets e guard estrutural de partial success sem recriação de artefacto.
- O CampaignActionsPanel permanece isolado na War Room; erro da sua query continua confinado ao próprio painel.

### Ficheiros criados ou alterados

- `frontend/package.json` — script `pnpm test` com runner nativo; sem alteração de dependências.
- `frontend/tests/campaign-actions.test.mjs` — criado; 14 testes automatizados.
- `frontend/src/shared/api/security.ts` — criado; protecção de headers provider-owned.
- `frontend/src/shared/api/error-mapping.ts` — criado; mapping HTTP testável.
- `frontend/src/shared/api/client.ts` — adopção dos helpers de segurança e erros.
- `frontend/src/shared/api/index.ts` — exports dos helpers.
- `frontend/src/shared/ui/states/error-presets.ts` — import directo testável das classes de erro.
- `frontend/src/entities/campaign-action/write-payload.ts` — criado; remoção defensiva de workspace.
- `frontend/src/entities/campaign-action/campaign-action-api.ts` — sanitização comum em POST/PATCH/dismiss.
- `frontend/src/entities/campaign-action/index.ts` — export do sanitizer.
- `frontend/src/features/campaign-actions/recommendation-decision-payload.ts` — criado; payloads reviewed/dismiss puros.
- `frontend/src/features/campaign-actions/useRecommendationDecision.ts` — reutilização do builder.
- `frontend/src/features/campaign-actions/index.ts` — export do builder/tipo.
- `frontend/src/features/campaign-actions/recommendation-snapshot.ts` — import runtime explícito para permitir testes nativos.
- `frontend/docs/01_fundamentos/03_campaign_actions_backend_integration/resultados_execucao/prompt_12_seguranca_erros_testes_resultado.md` — criado.
- `frontend/pnpm-lock.yaml` não foi alterado.

### Validações executadas e resultado

- `pnpm test`: passou na execução final; 14 testes, 14 passed, 0 failed.
- A primeira tentativa do runner com isolamento default encontrou `spawn EPERM`; o script final usa `--experimental-test-isolation=none` e executa in-process com sucesso.
- `pnpm lint`: passou na execução final, exit code 0.
- `pnpm build`: não concluiu por limitação do ambiente (`TS5033 EPERM`) ao escrever `node_modules/.tmp/tsconfig.*.tsbuildinfo`; não chegou ao bundling Vite.
- Typecheck alternativo de `tsconfig.app.json` e `tsconfig.node.json`, com build info em `%TEMP%`: passou sem erros após as alterações finais.
- Grep `X-Internal-Token`: apenas documentação/guard e teste que prova remoção; nenhum envio.
- Grep `INTERNAL_API_TOKEN`, `api_key` e `private_key`: apenas denylist do snapshot e dado sintético do teste; nenhum valor real.
- Grep `intelligence_engine`, `content_renderer`, `localhost:8001` e `localhost:8002`: zero ocorrências em source/tests/config.
- Grep `Bearer`: uma ocorrência dinâmica `Bearer ${token}` no cliente central; scan de Bearer hardcoded passou sem ocorrências.
- Grep `password`: apenas o fluxo de login tipado/UI e a denylist; scan de valores hardcoded passou sem ocorrências.
- Scan adicional de padrões de secrets: passou, sem candidatos.
- Inspecção de `workspace:` nos fluxos CampaignAction: ocorrências pertencem ao model/response e referências de artefactos; o teste prova remoção do body e não existem POST/PATCH com workspace explícito.
- Testes confirmam que 403 e 404 são classes/presets diferentes e que o preset 404 não reproduz detail potencialmente sensível.
- `git diff --check`: passou; apenas avisos informativos de normalização LF/CRLF.
- Browser e servidores não foram usados/iniciados.
- Relatório revisto: não contém secrets.

### Pendências, riscos ou próximo passo recomendado

- Reexecutar `pnpm build` num ambiente que permita escrever o cache incremental em `node_modules/.tmp` e criar subprocessos do Vite.
- O runner nativo depende de Node 22 e flags experimentais de type stripping/test isolation. É deliberadamente leve e sem dependências; pode ser substituído por Vitest numa alteração isolada quando instalação e lockfile puderem ser validados normalmente.
- Os testes cobrem a lógica pura crítica. React Query hooks, dialogs montados, fetch real e a recuperação de partial success continuam sem teste de integração com mocks; o guard de partial success actual é estrutural.
- O frontend não recebe capabilities/RBAC no perfil actual. Assim, viewers podem ainda ver affordances de escrita, mas o backend permanece autoridade, devolve 403 e a UI apresenta “Access denied”, não “Not found”. Ocultar preventivamente exige um contrato de capabilities real, não inferência pelo browser.
- 404 cross-workspace foi validado ao nível de mapping/copy, não por smoke HTTP real nesta iteração.
- Próximo passo recomendado: executar a limpeza/documentação final e smoke HTTP contra Backend Core num ambiente autorizado, incluindo 401/403/404 cross-workspace e lifecycle completo.
