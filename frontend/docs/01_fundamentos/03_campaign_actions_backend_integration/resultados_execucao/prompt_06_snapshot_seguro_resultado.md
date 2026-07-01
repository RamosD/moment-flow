# Resultado — Prompt 06: snapshot seguro e normalização

## Execução de 2026-07-01 13:03:57 -01:00

**Estado da execução:** `executado_parcialmente`

### Resumo objectivo

Foi criado um builder seguro para o contexto persistível de recommendations: `recommendation_ref` limitada, `recommendation_snapshot` allowlisted/sanitizada e priority normalizada para o enum real. O contexto foi integrado no `RecommendationActionDraft`, sem alterar ainda o submit do create dialog.

O estado é parcial apenas porque `pnpm build` continua bloqueado pela escrita do cache TypeScript no ambiente. Lint e typecheck integral passaram.

### Implementação entregue

- `deriveRecommendationRef` continua a preferir o id da recommendation e mantém o fallback `campaignId + índice + title/action/type`.
- Refs são trimmed e limitadas a 512 caracteres. Valores longos preservam um prefixo e recebem hash determinístico do valor completo para reduzir colisões por truncamento.
- Snapshot copia exclusivamente `id`, `title`, `label`, `action`, `type`, `description`, `reason`, `priority` e `confidence`.
- Não existe spread, serialização ou cópia integral do objecto recommendation.
- Sanitização recursiva remove chaves sensíveis após normalizar case e separadores, incluindo `X-Internal-Token` como `x_internal_token`.
- Valores circulares, não JSON, profundidade excessiva e colecções excessivas são descartados/limitados defensivamente.
- Cada campo tem limite defensivo e o snapshot final fica abaixo de 60 KiB, deixando margem para o limite backend de 65 536 bytes.
- O fallback `{ title: "Recommendation", priority: "medium" }` garante object não vazio.
- Priority normaliza para `low|medium|high|urgent`; valores ausentes/desconhecidos usam o default documentado `medium`.
- `RecommendationActionDraft` transporta agora `recommendationSnapshot` e priority tipada, preparando payloads reais top-level.
- Nenhuma nova CampaignAction escreve priority em metadata. O dialog legado continua temporariamente a escrever metadata apenas no artefacto antigo; será removido quando o create path for migrado.

### Ficheiros criados ou alterados

- Criado `frontend/src/features/campaign-actions/recommendation-snapshot.ts`.
- Alterado `frontend/src/entities/campaign-action/recommendation-ref.ts` e respectivos exports em `index.ts`.
- Alterados `frontend/src/features/campaign-actions/recommendation-action-draft.ts` e `features/campaign-actions/index.ts`.
- Ajuste mínimo de tipo em `CreateActionFromRecommendationDialog.tsx`, sem alteração do submit.
- Criado este relatório.

### Validações executadas e resultado

- `pnpm lint`: **passou**.
- ESLint dirigido aos ficheiros alterados após o último ajuste: **passou**.
- `pnpm build`: detectou inicialmente uma incompatibilidade no state legado de priority, corrigida; a execução permanece **bloqueada pelo ambiente** com `TS5033/EPERM` nos ficheiros `node_modules/.tmp/tsconfig.*.tsbuildinfo`.
- Typecheck alternativo de `tsconfig.app.json` e `tsconfig.node.json`, usando build info em `%TEMP%`: **passou sem erros** após a correcção.
- Grep por `JSON.stringify(recommendation)`, spread de recommendation ou `Object.entries(recommendation)`: **sem ocorrências**.
- Inspecção da allowlist, lista sensível, limite de bytes e cap de 512 caracteres: **passou**.
- Testes unitários: não criados porque o projecto continua sem test runner.
- Browser e servidores: não usados/iniciados.
- Verificação de secrets no relatório e alterações: sem valores sensíveis encontrados.

### Pendências, riscos e próximo passo recomendado

- Adicionar testes unitários do builder quando FE-CAI-014 introduzir o test runner: allowlist, sanitização recursiva, UTF-8, circularidade, limites, ref longa e matriz de priority.
- Confirmar com samples reais do Intelligence Engine se prioridades numéricas seguem a escala assumida `1..4`; valores fora/ambíguos continuam seguros pelo default/mapeamento conservador.
- Reexecutar `pnpm build` num ambiente sem o bloqueio de escrita.
- Próximo passo recomendado: migrar o create dialog para usar `recommendationSnapshot`, `recommendationRef.ref` e `priority` como campos top-level da CampaignAction.
