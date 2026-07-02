# Prompt 09 — E2E automatizado — Resultado

**Data:** 2026-07-02
**Fase:** `05_staging_operacionalizacao_pre_producao` (STG-PRE-009)
**Âmbito:** tornar o fluxo principal (login → War Room → intelligence → CampaignActions → persistência) repetível e automatizado, sem mocks runtime, sem secrets no repositório, sem dados partilhados frágeis.
**Estado de execução:** `executado e verde` — Playwright introduzido, seed namespaced por execução criado, suite completa (12 testes) a correr **de facto** contra os quatro serviços reais (Backend Core, Intelligence Engine real, Content Renderer real, frontend real), 3 execuções consecutivas sem falha e uma execução deliberada com o IE parado a falhar de forma diagnosticável.

---

## 1. Resumo objectivo

Não existia nenhuma ferramenta de E2E no repositório (`frontend/package.json`
só tinha o `node --test` de unidade). Introduzi **Playwright**
(`@playwright/test`) e um comando Django novo, `seed_e2e_run`, que cria um
utilizador/workspace/artist/campaign **namespaced por execução** — cada
corrida gera um `run-id` único (timestamp + sufixo aleatório), nunca reutiliza
dados partilhados, e é idempotente para o mesmo `run-id` (uma repetição não
duplica nada).

**Achado arquitectural relevante descoberto durante o desenho do cenário:**
não existe nenhuma affordance de "criar acção" independente de uma
recomendação — `CreateActionFromRecommendationButton` só aparece dentro de
cada card de recomendação (`CampaignRecommendationsPanel`/
`RecommendationItem`). Ou seja, **para criar manual task / report / media kit
/ content pack, a Intelligence tem de devolver pelo menos uma recomendação**;
sem isso, essa parte do fluxo é literalmente inacançável pela UI. Confirmei
por chamada directa ao `CampaignIntelligenceService` que uma campanha **nova
e vazia** (sem métricas, sem histórico) já recebe recomendações reais e
accionáveis de um Intelligence Engine real (`source=engine`, não
`dry_run`) — heurísticas como "sem media kit" ou "campanha de release activa"
disparam mesmo sem dados históricos. Por outro lado, confirmei no código
(`intelligence_service.py::_dry_run_result`) que **o modo dry-run devolve
sempre `recommendations: []`** — logo esta suite só consegue exercitar a
criação de CampaignActions com um Intelligence Engine **real e alcançável**,
nunca em dry-run. Isto está documentado directamente no cabeçalho do spec.

## 2. Ferramenta escolhida

**Playwright** (`@playwright/test@1.61.1` + Chromium). Critérios: já é a
preferência registada no backlog da fase; todo o código de UI deste projecto
usa elementos HTML nativos e acessíveis (`<dialog>`, `<select>`, `<label
htmlFor>`) sem nenhuma biblioteca de componentes customizada — o que torna
`getByRole`/`getByLabel` directamente utilizáveis, sem precisar de
`data-testid` novos em lado nenhum do código de produção.

## 3. Ficheiros criados/alterados

Novo (Playwright + comando de seed):
- `frontend/playwright.config.ts` — config (baseURL de `E2E_BASE_URL`, `webServer` reaproveita um dev server já a correr).
- `frontend/e2e/global-setup.ts` — invoca `seed_e2e_run` num subprocesso Python real, propaga ids (não-secretos) via `process.env` para os testes.
- `frontend/e2e/main-flow.spec.ts` — o cenário completo (secção 4).
- `frontend/tsconfig.e2e.json` — projecto TS próprio (`types: ["node"]`), referenciado a partir de `tsconfig.json` para que `pnpm build` também valide estes ficheiros.
- `backend_core/apps/core/management/commands/seed_e2e_run.py` — comando de seed namespaced.
- `backend_core/apps/core/tests/test_seed_e2e_run.py` — 4 testes (exige `E2E_PASSWORD`, dataset correcto, idempotência por `run-id`, sem colisão entre `run-id`s diferentes).

Alterados:
- `frontend/package.json` — novo script `test:e2e`; `@playwright/test` como devDependency.
- `frontend/eslint.config.js` — bloco novo para `e2e/**`/`playwright.config.ts` com globals de Node (o bloco existente só tinha `globals.browser`; sem isto o lint acusaria `process`/`require` como indefinidos).
- `frontend/tsconfig.json` — referencia o novo `tsconfig.e2e.json`.
- `frontend/.gitignore` — `/playwright-report`, `/test-results`, `/blob-report`.

## 4. Cenário coberto (`main-flow.spec.ts`)

Um único browser context partilhado por todos os passos (`test.describe.configure({ mode: 'serial' })` + `page` criada uma vez em `beforeAll`) — necessário porque o token de acesso vive só em memória (`AuthProvider`), e um `page` novo por teste perderia a sessão a meio do fluxo:

1. **login** — via `/login`, credenciais 100% vindas de `process.env` (nunca hardcoded).
2. **abrir campanha + War Room** — navega para `/campaigns/{id}` e clica "Open War Room".
3. **intelligence executa e produz ≥1 recomendação** — real ou dry-run; falha aqui é o sinal correcto quando a Intelligence não está acessível (secção 6).
4. **criar manual task** a partir da 1ª recomendação.
5. **criar report action**.
6. **criar media kit action**.
7. **criar content pack action** (selecciona o 1º content pack disponível).
8. **mark reviewed** na recomendação.
9. **dismiss** na recomendação (com motivo).
10. **CampaignActionsPanel** — confirma as 6 acções criadas (4 tipos + mark_reviewed + dismiss) visíveis, filtradas pelo título partilhado da recomendação.
11. **reload** — `page.reload()` e reconfirma as mesmas 6 acções + badges "Dismissed"/"Completed" — prova persistência real no backend, não cache de cliente.
12. **Network apenas Backend Core** — um listener de `page.on('request', …)` activo desde o login regista qualquer pedido cujo host não seja `localhost:5200`/`127.0.0.1:8100` ou cuja porta seja `8201`/`8202`; a asserção final exige lista vazia.

## 5. Estratégia de dados e secrets

- **Namespace por execução**: `seed_e2e_run --run-id=<único>` cria
  `e2e-<run-id>@example.local` + `E2E Workspace <run-id>` + artist/campaign
  com slugs `e2e-*-<run-id>`. `seed_rbac()`/`seed_content()` são chamados
  dentro do comando (idempotentes, garantem roles + content packs sem passo
  manual prévio).
- **Idempotência**: repetir o mesmo `--run-id` reutiliza o mesmo workspace/
  artist/campaign (`get_or_create` por slug) em vez de duplicar — validado em
  `test_rerun_with_same_run_id_is_idempotent`.
- **Secrets**: a password nunca é gerada, hardcoded, nem passada como
  argumento de CLI (ficaria no histórico do shell) — só é lida de
  `E2E_PASSWORD` (ambos no comando Django e no `global-setup.ts`). O
  `global-setup` propaga ids **não-secretos** para os testes via
  `process.env`; a password nunca é escrita em disco, nunca logada.
- Confirmado por grep (`password\s*=\s*['"]`, valores literais usados nas
  minhas próprias sessões de terminal) — zero ocorrências nos ficheiros
  novos, tracked ou untracked.

## 6. Resultado da execução real

Com os quatro serviços genuinamente a correr (Backend Core `:8100`,
Intelligence Engine real `:8201`, Content Renderer real `:8202`, frontend
`:5200`):

```text
$ E2E_PASSWORD=*** pnpm test:e2e
Running 12 tests using 1 worker
  ok  1 … login (2.1s)
  ok  2 … open campaign and War Room (974ms)
  ok  3 … intelligence executes and yields at least one recommendation (217ms)
  ok  4 … create manual task action from the recommendation (547ms)
  ok  5 … create report action from the recommendation (607ms)
  ok  6 … create media kit action from the recommendation (688ms)
  ok  7 … create content pack action from the recommendation (754ms)
  ok  8 … mark reviewed on the recommendation (336ms)
  ok  9 … dismiss the recommendation (579ms)
  ok 10 … CampaignActionsPanel lists every action created against this recommendation (46ms)
  ok 11 … reload: every action persists (real backend, not client cache) (1.8s)
  ok 12 … the frontend only ever talked to the Backend Core (6ms)
  12 passed (15.8s)
```

Corrido **3 vezes consecutivas** com sucesso (namespaces `run-id` diferentes
de cada vez, sem qualquer limpeza manual entre execuções — confirma
repetibilidade real). Na 2ª tentativa da 1ª execução, uma asserção minha
(`getByText('Completed')` sem `exact`) falhou por ambiguidade do próprio
teste (7 elementos a conter "Completed" — badges + `related_artifact_status`
do Prompt 07, ex.: `"Report: completed"`) — corrigido para escopar por acção
específica; não era um problema do produto.

**Falha diagnosticável com o Intelligence Engine parado (validação
explícita do backlog):** parei o processo do IE e corri a suite de novo.
`login` e `open campaign and War Room` continuam a passar (Backend Core e
frontend saudáveis); o passo 3 falha com um erro claro (`Recommendations`
section nunca aparece) e um screenshot anexado mostra o War Room preso em
**"Analyzing campaign…"** indefinidamente — o `intelligenceQuery.isPending`
nunca resolve dentro da janela do teste, porque o orçamento de
timeout/retries do Backend Core para o IE (configurado) é maior do que os
10–20s que o teste espera. Isto não é um bug do frontend (o código já trata
`isError` correctamente — `CampaignWarRoomPage.tsx`) nem foi mascarado: os 9
testes seguintes ficam correctamente marcados "did not run" em vez de
falharem em cascata com erros confusos. Reactivei o IE de seguida e a suite
voltou a passar 12/12.

## 7. Validações

- `npx tsc -b` (agora inclui `tsconfig.e2e.json`) — sem erros.
- `npx eslint .` — sem erros/avisos (globals de Node isolados a `e2e/**`).
- `npm test` (unidade) — 15/15 passed, inalterado.
- `pytest apps/core/tests/test_seed_e2e_run.py` — 4/4 passed.
- `pytest apps/core` — 24/24 passed.
- `python manage.py check` — 0 problemas.
- `pnpm test:e2e` — **12/12 passed**, 3 execuções consecutivas.
- Falha útil com IE indisponível — confirmada (secção 6).
- Grep de secrets nos ficheiros novos — zero ocorrências de password literal.

## 8. Limitações

- **Este E2E não arranca os serviços** (Backend Core, Intelligence Engine,
  Content Renderer) — assume-os já em execução, exactamente como o runbook
  operacional desta fase já descreve. Só o dev server do frontend é gerido
  opcionalmente pelo Playwright (`webServer`, reaproveita um já activo).
  Isto é deliberado: orquestrar múltiplos serviços Django/FastAPI/Node a
  partir do test runner do frontend seria frágil e sairia do âmbito desta
  fase técnica.
- **Depende de um Intelligence Engine real e alcançável** para a parte de
  criação de CampaignActions — em dry-run, `recommendations` vem sempre
  vazio e o cenário pára logo no passo 3 (falha útil, não um falso positivo,
  mas também não é "verde" nesse modo). Não há forma de contornar isto sem
  mudar a UI (não é âmbito desta fase) ou aceitar um `content_pack`/etc.
  "manual" sem recomendação (não existe essa affordance hoje).
- **Corre 1 worker/serial** — não há isolamento de dados entre steps que
  justifique paralelismo dentro do mesmo ficheiro (cada step depende do
  anterior); paralelizar entre *ficheiros* de spec diferentes seria seguro
  (namespaces diferentes por `global-setup` corrida), mas só há um ficheiro
  de momento.
- Dados de execuções reais (`E2E Workspace <run-id>`) ficam na base local —
  mesmo padrão de artefactos de smoke já deixados por prompts anteriores
  (`STG09 smoke …`, `Iter8 Smoke …`); não são destrutivos, não tocam dados
  doutro workspace.
- **Não corri em CI** (não existe pipeline de CI neste repositório, achado
  já registado na fase 04) — a validação desta iteração foi local, com os
  quatro serviços reais.

## 9. Riscos

- O timeout de 10–20s no passo de intelligence pode ser demasiado curto se o
  orçamento de retry do Backend Core para o IE for aumentado no futuro —
  reveria então esse timeout em conjunto com `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS`/`MAX_RETRIES`.
- Sem CI, esta suite só corre quando alguém a invoca manualmente — não há
  ainda um gate automático que a corra a cada alteração.
- O `seed_e2e_run` assume a topologia de venv actual
  (`backend_core/venv/Scripts/python.exe` no Windows) por omissão;
  `E2E_DJANGO_DIR`/`E2E_DJANGO_PYTHON` permitem sobrepor, mas isso não foi
  testado noutra topologia.

## 10. Próximo passo recomendado

1. Quando existir CI (fora do âmbito actual, já assinalado como lacuna na
   fase 04), acrescentar um job que arranque os três serviços de backend
   (ou aponte para um staging já de pé) e corra `pnpm test:e2e`.
2. Seguir para STG-PRE-010 (runbook operacional), incluindo nele os
   pré-requisitos e o comando `pnpm test:e2e` como parte do smoke de
   staging.
3. Se o produto decidir que criar uma CampaignAction sem recomendação
   associada é um requisito real (não apenas de teste), isso é uma decisão
   de produto/UX separada — não implementada aqui.
