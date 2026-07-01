# Relatório de Execução — Hardening 07: Coverage Vitest (R-HARD-007)

- **Serviço:** `content_renderer`
- **Data:** 2026-06-24
- **Backlog de referência:** [`03_backlog_hardening_pos_mvp_renderer.md`](../03_backlog_hardening_pos_mvp_renderer.md) → **R-HARD-007**
- **Pré-requisito:** [Hardening 06 — Loop real Django ↔ Renderer](prompt_hardening_06_loop_real_django_renderer.md)

---

## 1. Prompt executado

Adicionar coverage ao `content_renderer` com Vitest (`@vitest/coverage-v8`),
script `npm run test:coverage`, thresholds iniciais e documentação, sem alterar
funcionalidades nem reduzir a qualidade dos testes.

## 2. Objectivo

Criar uma métrica inicial de qualidade (cobertura de testes) para controlar
regressões futuras, com thresholds mínimos exigíveis em CI/local.

## 3. Ficheiros criados

- [`docs/fundamentos/resultados/prompt_hardening_07_coverage_vitest.md`](prompt_hardening_07_coverage_vitest.md) — este relatório.

Nenhum ficheiro de código novo foi necessário (apenas configuração e dependência).

## 4. Ficheiros alterados

- [`package.json`](../../package.json) — nova dependência de desenvolvimento
  `@vitest/coverage-v8@^4.1.9` (mesma major/minor do `vitest` já instalado,
  `^4.1.9`); novo script `"test:coverage": "vitest run --coverage"`.
- [`vitest.config.ts`](../../vitest.config.ts) — bloco `test.coverage`:
  `provider: 'v8'`, `reporter: ['text', 'html', 'lcov']`,
  `reportsDirectory: './coverage'`, `include: ['src/**/*.ts']`, `exclude` (ver
  §6) e `thresholds` (ver §7).
- [`README.md`](../../README.md) — linha na tabela de scripts, secção
  "Testes" com exemplo de comando, nova subsecção "Coverage (R-HARD-007)" com
  interpretação dos relatórios gerados e tabela de thresholds vs. real, e
  actualização da lista "Próximos passos" (item 4 E2E marcado concluído, novo
  item 5 coverage concluído).
- [`docs/fundamentos/02_estado_content_report_renderer.md`](../02_estado_content_report_renderer.md)
  — tabela "Validações executadas" (linha de coverage configurada com números
  reais, substitui a antiga linha "⚠️ Não configurado"), secção "Pendências"
  (nova entrada ✅ coverage concluído) e "Próximo passo recomendado"
  (item 7 coverage marcado concluído, R-HARD-008 passa a item 8).

## 5. Provider instalado

`@vitest/coverage-v8@^4.1.9` — provider nativo V8 (sem instrumentação de
código, usa os contadores de cobertura do próprio motor V8), recomendado pela
documentação do Vitest e o sugerido no backlog. Instalado como
`devDependency`; `npm install` correu sem vulnerabilidades reportadas.

## 6. Âmbito de coverage (include/exclude)

- **Include:** `src/**/*.ts` (todo o código de produção).
- **Exclude** (com justificação):
  - `src/server.ts` — entrypoint do processo (chama `app.listen(...)` e regista
    handlers de `SIGINT`/`SIGTERM`); nunca é importado pelos testes — o
    comportamento testável está em `src/app.ts` (factory pura, 100% coberta).
  - `src/jobs/job.types.ts`, `src/renderers/renderer.types.ts`,
    `src/storage/storage.types.ts` — módulos exclusivamente de tipos
    (`interface`/`type`), sem código executável a medir.
- `dist/`, `node_modules/`, `coverage/`, `scripts/` e ficheiros de configuração
  nunca entram no `include` (apenas `src/**/*.ts` é incluído), por isso não
  precisaram de exclusão explícita adicional.

## 7. Thresholds definidos

Usados exactamente os valores sugeridos no backlog (§R-HARD-007), sem
necessidade de ajuste — a cobertura real ultrapassa todos:

| Métrica | Threshold | Cobertura real |
|---|---|---|
| Lines | 70% | **91.86%** |
| Functions | 65% | **95.89%** |
| Branches | 55% | **79.32%** |
| Statements | 70% | **91.9%** |

Não foi preciso "ajustar para valores conservadores" — os thresholds
sugeridos já são confortavelmente cumpridos pela suite existente (136 testes).
Mantidos tal como no backlog para não mascarar uma futura regressão atrás de
um threshold demasiado baixo.

## 8. Resultado real de coverage

Saída de `npm run test:coverage` (resumo por pasta; ficheiro completo no
relatório HTML local, não versionado):

```text
 Test Files  13 passed (13)
      Tests  136 passed (136)

 % Coverage report from v8
-------------------|---------|----------|---------|---------|
File               | % Stmts | % Branch | % Funcs | % Lines |
-------------------|---------|----------|---------|---------|
All files          |    91.9 |    79.32 |   95.89 |   91.86 |
 src               |     100 |    85.71 |     100 |     100 |
 src/callbacks      |   95.23 |    71.42 |     100 |   94.91 |
 src/config         |   89.65 |     87.3 |     100 |   91.07 |
 src/errors         |   79.31 |    79.41 |   93.33 |   79.31 |
 src/http           |    88.4 |    81.81 |     100 |    88.4 |
 src/jobs           |   98.63 |    81.81 |     100 |   98.59 |
 src/logging        |      80 |    82.75 |   81.81 |   79.41 |
 .../renderers/content   |   95.65 |    83.95 |     100 |   95.45 |
 .../renderers/media-kits|   88.82 |    71.54 |   96.42 |   88.76 |
 .../renderers/reports   |   94.26 |    72.22 |      96 |   94.21 |
 .../renderers/shared    |   88.46 |    77.55 |   94.44 |   88.31 |
 src/storage        |   94.11 |    82.75 |     100 |   94.11 |
 src/templates       |   97.46 |    95.23 |   88.23 |   97.46 |
-------------------|---------|----------|---------|---------|

Statements   : 91.9% ( 851/926 )
Branches     : 79.32% ( 514/648 )
Functions    : 95.89% ( 187/195 )
Lines        : 91.86% ( 836/910 )
```

Sem falhas de threshold — `vitest run --coverage` saiu com código `0`.
Ficheiros com menor cobertura de *branches* (`src/logging/logger.ts` 82.75%,
`src/errors/errors.ts` 79.41%) correspondem a ramos defensivos
(ex.: tipos de erro não-`Error`, chaves de redacção raras) já considerados
aceitáveis para esta fase — não há lacunas de comportamento de negócio
não testado.

## 9. Comandos executados

```bash
npm install --save-dev @vitest/coverage-v8@^4.1.9
npm run test:coverage
npm run build
npm run lint
npm test
```

## 10. Resultados

| Validação | Resultado |
|---|---|
| `npm install @vitest/coverage-v8` | ✅ 18 pacotes adicionados, 0 vulnerabilidades |
| `npm run test:coverage` | ✅ 136 testes, thresholds cumpridos, relatório gerado (`text`+`html`+`lcov`) |
| `npm run build` | ✅ Sem erros |
| `npm run lint` | ✅ Sem erros |
| `npm test` | ✅ **136 testes** (sem regressão; nenhum teste alterado/removido) |

## 11. Pendências

- Cobertura de *branches* em `src/logging/logger.ts` e
  `src/errors/errors.ts` fica acima do threshold global mas é a mais baixa do
  projecto (ramos defensivos raros) — não bloqueante, mas candidato a reforço
  futuro se thresholds subirem.
- Thresholds são **globais** (não por ficheiro); um ficheiro novo com baixa
  cobertura pode passar se a média global se mantiver acima do threshold —
  aceitável para esta fase inicial, a revisitar se o projecto crescer.
- `coverage/` é gerado localmente e nunca commitado (confirmado no
  `.gitignore` pré-existente); não há publicação automática do relatório
  (ex. Codecov) — fora do âmbito desta fase.

## 12. Próximo passo recomendado

Avançar para **R-HARD-008** (documentação final pós-hardening): consolidar
README, estado, guia E2E e relatórios, confirmando ausência de segredos e
registando pendências remanescentes de todo o backlog R-HARD-001..007.
