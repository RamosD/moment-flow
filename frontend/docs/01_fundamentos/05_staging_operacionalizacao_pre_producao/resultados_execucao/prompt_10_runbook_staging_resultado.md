# Prompt 10 — Runbook operacional staging — Resultado

**Data:** 2026-07-02
**Fase:** `05_staging_operacionalizacao_pre_producao` (STG-PRE-010)
**Âmbito:** consolidar num único documento prático como arrancar, validar,
diagnosticar e parar o staging técnico/pré-produção, sem secrets, sem portas
antigas, sem instruir a desactivar segurança interna.
**Estado de execução:** `executado` — runbook novo criado, validado contra os
scripts/comandos reais existentes (não inventados), grep de secrets e de
portas proibidas limpos.

---

## 1. Resumo objectivo

Não existia nenhum runbook neste repositório (procurei por `*runbook*` em
toda a árvore de `frontend/docs` — zero resultados). Construí
`runbook_staging_pre_producao.md` inteiramente a partir de fontes já
validadas nos Prompts 01–09 desta fase (arquitectura alvo, `.env.example`
dos quatro serviços, `docs/configuracao/portas_projeto.md`,
`scripts/check-forbidden-ports.ps1`, e os dois comandos de smoke operacional
já existentes no Backend Core — `smoke_intelligence_engine` e
`smoke_content_renderer`, cujo próprio docstring já diz explicitamente que
foram pensados "for local or staging operation and the runbook"). Não
inventei nenhum comando, endpoint ou variável — tudo foi confirmado por
leitura directa do código/scripts antes de entrar no documento.

## 2. Ficheiros criados

- `frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/runbook_staging_pre_producao.md` (novo)
- `frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/resultados_execucao/prompt_10_runbook_staging_resultado.md` (este relatório)

Nenhum ficheiro de código foi alterado nesta iteração.

## 3. Secções do runbook

1. **Antes de começar** — âmbito explícito (staging pré-produção/técnico,
   nunca produção), aviso de placeholders.
2. **Pré-requisitos** — Python/Node/DB/Playwright/portas.
3. **Portas canónicas** — tabela + comando `check-forbidden-ports.ps1` +
   regra inviolável (frontend só fala com o Backend Core).
4. **Variáveis obrigatórias por serviço** — os quatro `.env` com
   placeholders, incluindo a correcção explícita de que **`DATABASE_URL` não
   existe neste projecto** (só variáveis discretas `DB_*` via
   python-decouple) — evita que o runbook contradiga a realidade do código
   só para seguir literalmente o enunciado do prompt.
5. **Secrets obrigatórios (sem valores)** — tabela + lista explícita do que
   **nunca fazer** (`ALLOW_INSECURE_EMPTY_TOKEN=true`, token vazio com
   `DEBUG=False`, commitar `.env` real).
6. **Ordem de arranque** — BD → Backend Core → IE/Renderer (qualquer ordem
   entre si) → Frontend por último.
7. **Comandos por componente** — um bloco por serviço, usando os scripts
   reais de cada `package.json`/venv (`npm run build`+`npm start` para
   produção, `npm run dev` para staging técnico; `pnpm build`+`pnpm dev`/
   `pnpm preview`).
8. **Healthchecks** — os 5 endpoints reais (`/health` IE e CR, `/live/`,
   `/ready/`, `/dependencies/` do Backend Core) + nota de latência
   IPv6/Windows (achado STG-PRE-006).
9. **Smoke API** — login/perfil + os dois comandos `smoke_intelligence_engine`/
   `smoke_content_renderer` já existentes (nunca imprimem o token).
10. **Smoke browser** — passo a passo login → War Room → criar acção →
    reload → confirmar Network só toca o Backend Core.
11. **E2E automatizado** — comando `pnpm test:e2e` + as três pré-condições
    reais descobertas no Prompt 09 (serviços genuinamente a correr, IE fora
    de dry-run, `E2E_PASSWORD` exportado).
12. **Troubleshooting** — 8 sub-secções (DB, IE, Renderer, callbacks,
    storage/`public_url`, auth/RBAC, CORS, migrations), cada uma com
    sintoma → diagnóstico → acção, incluindo os achados reais das fases 04/05
    (Prompt 04: token vazio; Prompt 06: latência; Prompt 07: job failed vs.
    artefacto preso).
13. **Limpeza de dados dev/staging** — namespace por execução (E2E/CA-014/
    STG09), snippet de shell para remover um namespace específico, aviso
    contra `flush`/`migrate zero` em dados reais.
14. **Paragem segura** — ordem inversa ao arranque, sem sinais especiais de
    drain necessários.
15. **Checklist de validação rápida** — 12 itens verificáveis.
16. **Matriz de sintomas** — tabela de referência rápida ligando cada sintoma
    pedido (IE down, Renderer down, callback 403, job failed, asset sem
    `public_url`, 403 no frontend, CORS, DB migration) à secção de
    troubleshooting correspondente.
17. **Critérios de pronto/não pronto** — distingue explicitamente "pronto
    para piloto técnico" (já alcançado, fase 04) de "pronto para staging
    pré-produção formal" (ainda pendente: PostgreSQL persistente, object
    storage real, secret store, esquema de hosts, CI) — nunca declara
    produção.
18. **Referências** — para todos os relatórios de Prompts 01–09 e para o
    checklist detalhado já existente do Content Renderer
    (`backend_core/docs/fundamentos/03_observabilidade_staging_ecossistema/smoke_content_renderer.md`).

## 4. Validações

- **Grep de secrets** — `SECRET_KEY=`, `INTERNAL_API_TOKEN=`, `DB_PASSWORD=`,
  `password[:=]` seguidos de valores alfanuméricos ≥6 caracteres: **zero
  ocorrências** no runbook. Todos os valores são placeholders `<...>`.
- **`scripts/check-forbidden-ports.ps1`** corrido a partir da raiz do
  repositório: `OK - nenhuma porta proibida encontrada em ficheiros
  activos.` (a única menção às portas proibidas no runbook é a própria
  frase "nunca usar: 8000, 8001, …", que o regex do script — desenhado para
  `localhost:<porta>`/`PORT=<porta>` — correctamente não confunde com uso
  activo).
- **Portas canónicas conferidas uma a uma** contra
  `docs/configuracao/portas_projeto.md`: 5200/5201/8100/8201/8202 — correctas.
- **Comandos conferidos contra os scripts reais**:
  - `backend_core/requirements.txt` e `intelligence_engine/requirements.txt` existem.
  - `content_renderer/package.json` scripts (`dev`, `build`, `start`) — confirmados.
  - `frontend/package.json` scripts (`dev`, `build`, `preview`, `test:e2e`) — confirmados (o último, novo do Prompt 09).
  - `seed_rbac`, `seed_content`, `seed_e2e_run` — comandos Django reais, confirmados por leitura directa.
  - `smoke_intelligence_engine`/`smoke_content_renderer` — flags (`--reference-date`, `--health-only`, `--job-type`) confirmadas pelos docstrings dos próprios comandos.
  - Endpoints de health (`/live/`, `/ready/`, `/dependencies/`, `/health` IE/CR) — confirmados contra o código do Prompt 06.
- **Nenhum comando neste runbook desactiva segurança interna** — a única
  menção a `ALLOW_INSECURE_EMPTY_TOKEN` é para dizer explicitamente para
  nunca a activar em staging.
- Não corri nenhum comando destrutivo (migrations/flush) durante esta
  validação — a revisão foi documental + os greps/script acima, conforme a
  regra "executar comandos apenas se seguro e necessário" (não havia
  necessidade de recriar o ambiente para validar um documento).

## 5. Riscos

- O runbook assume, para os comandos "por componente", a topologia actual
  de venv/`node_modules` local — se o staging pré-produção real vier a usar
  containers, os comandos de arranque mudam (mas as variáveis/portas/ordem
  continuam válidas).
- Secções que dependem de decisões ainda pendentes (provider de storage,
  mecanismo de secrets, topologia de DB persistente, esquema de hosts) só
  podem ficar genéricas até essas decisões serem tomadas — assinalado
  explicitamente na secção 16 do runbook (critérios de pronto/não pronto)
  para não passar a falsa impressão de que staging pré-produção formal já
  está fechado.
- Este runbook não foi ainda seguido "às cegas" por outra pessoa que não eu
  — a validação foi por revisão + greps, não por um terceiro a executá-lo do
  zero numa máquina nova.

## 6. Próximo passo recomendado

1. Seguir para STG-PRE-011 (fecho de prontidão pré-produção) — consolidar os
   relatórios desta fase, declarar honestamente pronto/não pronto para
   piloto pré-produção (distinto de produção), e listar riscos/limitações
   remanescentes.
2. Quando alguém sem contexto prévio desta fase seguir este runbook do zero
   numa máquina nova, validar e corrigir quaisquer passos que se revelem
   incompletos (esta primeira versão foi escrita e revista por quem já tem
   o ambiente configurado).
