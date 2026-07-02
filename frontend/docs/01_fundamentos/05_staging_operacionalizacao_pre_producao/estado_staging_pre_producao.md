# Estado — Staging Pré-Produção (MomentFlow / ChartRex)

> Fase: `05_staging_operacionalizacao_pre_producao` (fecho — STG-PRE-011)
> Data: 2026-07-02
> Fonte: os 10 relatórios em `resultados_execucao/`, `arquitectura_staging_pre_producao.md`,
> `runbook_staging_pre_producao.md`, `01_backlog.md`, e validação final executada
> nesta iteração (código actual, não apenas relatórios).

---

## 1. Resumo executivo

A fase 05 executou os 10 prompts técnicos planeados (STG-PRE-001 a
STG-PRE-010), todos com validação real (não apenas leitura de código):
PostgreSQL validado tecnicamente, `Asset.public_url` resolvido e
descarregado de facto, inventário de secrets com um incidente real
remediado, correlation-id ponta-a-ponta confirmado nos logs dos três
serviços, health agregado validado com utilizador staff real (com um
achado de latência real corrigido), um bug real de artefactos presos
encontrado e corrigido, RBAC/UX confirmado já honesto por desenho, um E2E
Playwright real a correr 12/12 contra os quatro serviços genuinamente
activos, e um runbook operacional completo.

**O que a fase não fez — e não deveria fazer, por desenho do próprio
backlog:** não escolheu um provider de object storage, não cortou o
staging técnico para uma instância PostgreSQL persistente, e não
implementou um mecanismo de secrets fora do `.env` manual. Estas são
**decisões de infraestrutura/produto**, explicitamente fora do que o
backlog pediu para decidir implicitamente — ficam registadas como
pendências, não como falhas de execução.

**Consequência directa para a classificação de prontidão:** o backlog
desta fase (§5, critérios de aceitação) exige DB staging a substituir
SQLite, object storage a substituir storage local, e secrets geridos fora
do repositório para considerar a fase "staging pré-produção formal"
fechada. Nenhum dos três está feito — continuam exactamente onde a fase 04
os deixou, agora com o caminho técnico para os resolver completamente
documentado e sem bloqueios de código. Por isso este documento classifica
o estado como **`pronto_parcialmente_com_pendencias`** — não
`pronto_para_piloto_pre_producao`, e claramente não produção.

---

## 2. Estado final

### Classificação: `pronto_parcialmente_com_pendencias`

Justificação directa contra as cinco opções permitidas:

| Opção | Aplica-se? | Porquê |
|---|---|---|
| `pronto_para_piloto_pre_producao` | **Não** | 3 dos critérios de aceitação do backlog da fase (DB, storage, secrets) continuam dependentes de infraestrutura local/manual — o próprio backlog proíbe declarar isto pronto nessas condições |
| **`pronto_parcialmente_com_pendencias`** | **Sim** | Todo o trabalho tecnicamente executável dentro desta fase foi executado e validado; o que falta é decisão/provisionamento de infraestrutura, não código nem validação |
| `executado_parcialmente` | Não | Todos os 10 prompts foram executados por completo, com validação real, não parcialmente |
| `bloqueado` | Não | Nada impediu a execução — as pendências são decisões conscientemente adiadas, não bloqueios técnicos encontrados |
| `nao_pronto` | Não | O ambiente já é significativamente mais observável, seguro e reproduzível do que no fecho da fase 04 (`pronto_para_piloto_tecnico_staging`); seria desonesto classificar como "não pronto" um ambiente que já corre um E2E real de ponta-a-ponta |

**Nível de ambiente alcançado, na terminologia da própria arquitectura desta
fase (`arquitectura_staging_pre_producao.md` §1):** o ambiente continua,
tecnicamente, no nível **"staging técnico"** (validado na fase 04), agora
com observabilidade, correlation-id, estados de artefacto/job honestos,
RBAC/UX confirmado, E2E automatizado e um runbook — mas **não** atingiu o
nível "staging pré-produção" completo, porque esse nível exige
especificamente DB não-SQLite, storage não-local e secrets não-manuais em
staging real, e nenhum dos três foi cortado.

---

## 3. Escopo executado (implementado e validado)

| Item do backlog (§5) | Estado | Evidência |
|---|---|---|
| Migrations passam | ✅ Implementado e validado | `python manage.py migrate` — 32 migrations, 0 pendentes (`showmigrations` limpo, reconfirmado nesta iteração) |
| `Asset.public_url` resolvido | ✅ Implementado e validado | Campo novo + persistência nos 2 callbacks + smoke real de download (PDF/PNG válidos) — Prompt 03 |
| Correlation-id único ponta-a-ponta | ✅ Implementado e validado | `X-Request-ID` rastreado em BD e logs dos 3 serviços para CampaignAction/Report/MediaKit/ContentPackRequest — Prompt 05 |
| Healthchecks DB/IE/CR funcionam | ✅ Implementado e validado | Agregado (staff-only) + liveness/readiness novos (públicos) + achado de latência IPv6/Windows corrigido — Prompt 06 |
| Logs suficientes, sem secrets | ✅ Implementado e validado | Loggers estruturados nos 3 serviços; greps de segurança limpos em todas as iterações — Prompts 05, 06 |
| Estados de artefacto/job claros | ✅ Implementado e validado | Bug real corrigido (falha de submissão síncrona deixava artefacto preso); `related_artifact_status` exposto na API/UI — Prompt 07 |
| RBAC/UX mínimo validado | ✅ Confirmado (maioritariamente já correcto) | Backend já é a única autoridade; UX de erro já honesta (403/404/401/503 distintos); 2 painéis melhorados para mostrar causa de falha — Prompt 08 |
| E2E automatizado cobre fluxo principal | ✅ Implementado e validado | Playwright real, 12/12, 3 execuções consecutivas, contra os 4 serviços genuinamente a correr; falha diagnosticável confirmada com IE parado — Prompt 09 |
| Runbook operacional existe | ✅ Implementado | `runbook_staging_pre_producao.md`, 17 secções, comandos conferidos contra scripts reais — Prompt 10 |
| Arquitectura alvo documentada | ✅ Implementado | `arquitectura_staging_pre_producao.md` — Prompt 01 |

---

## 4. Escopo bloqueado / pendente (decisão de infraestrutura, não de código)

| Item do backlog (§5) | Estado | Porquê não está feito | Trabalho de código necessário quando a decisão for tomada |
|---|---|---|---|
| DB staging substitui SQLite dev | ⏳ **Pendente** — validado tecnicamente, não cortado | PostgreSQL 16 confirmado a funcionar (migrations, seed, CRUD via API, 56/56 testes) contra uma instância **descartável**; o staging técnico real continua `DB_ENGINE=sqlite` — falta decidir e provisionar uma instância **persistente** | **Nenhum** — `DB_ENGINE=postgres` já funciona; só falta apontar-lhe uma instância real |
| Object storage substitui storage local | ⏳ **Pendente** — nenhum provider escolhido | `STORAGE_PROVIDER=local` continua a única implementação; a interface `StorageProvider` já está pronta para uma segunda implementação | Só no Content Renderer: nova implementação da interface (ex.: `s3-storage.ts`) + entrada na factory. **Zero alterações no Backend Core** (já persiste/expõe `public_url` de forma agnóstica de provider) |
| Secrets geridos fora do repositório | ⏳ **Pendente** — mecanismo continua `.env` manual | Não existe CI/CD neste repositório (sem `.github/workflows`); não existe secret store provisionado | Nenhum — os 3 serviços já lêem tudo por variável de ambiente (`python-decouple`/`pydantic-settings`); só falta decidir onde essas variáveis são injectadas em staging real |
| Esquema de hosts de staging pré-produção | ⏳ **Pendente** — nenhum definido | Continua implicitamente `localhost`/máquina única | Decisão de topologia (containers, hosts separados, etc.), não de código |
| `signed_url` para bucket privado | ⏳ **Pendente**, condicional | Só necessário se o provider escolhido usar bucket privado — decisão ainda não existe | Campo novo, distinto de `public_url`, quando/se necessário |
| CI/CD a correr o E2E automaticamente | ⏳ **Pendente** | Não existe pipeline de CI/CD neste repositório | Fora do âmbito de código desta fase — depende de escolha de plataforma |

**Nenhum destes itens foi "esquecido" ou "não teve tempo"** — cada relatório
de Prompt (01, 02, 03, 04, 09, 10) regista explicitamente a decisão de não
inventar a escolha, por instrução directa do backlog desta fase.

---

## 5. Fora de escopo (nunca foi objectivo desta fase)

- Produção (SLA, alta disponibilidade, alertas, rotação automática de secrets, aprovação operacional).
- Multi-region.
- Novas funcionalidades de produto em CampaignActions, billing, scheduler, workflow engine, realtime/WebSockets.
- Optimizações de performance extensas.
- Mudanças de UX grandes fora de RBAC/erros/estados.

Nenhum destes foi tocado nesta fase, conforme `01_backlog.md` §3.

---

## 6. Validações concluídas (re-executadas nesta iteração de fecho)

| Validação | Resultado |
|---|---|
| `python manage.py check` (Backend Core) | ✅ 0 issues |
| `python manage.py showmigrations` | ✅ 0 pendentes |
| `pytest` completo (Backend Core) | ✅ 598 passed, 1 failed (pré-existente, não relacionado — `test_intelligence_payload.py`, data fixa desactualizada, já rastreado em `task_1d40d090`), 3 skipped (exigem `RUN_REAL_IE=1`) |
| `pytest` completo (Intelligence Engine) | ✅ 198/198 passed |
| `npm test` (Content Renderer, vitest) | ✅ 136/136 passed |
| `npx tsc -b` (frontend) | ✅ sem erros |
| `npx eslint .` (frontend) | ✅ sem erros/avisos |
| `npm test` (frontend, unidade) | ✅ 15/15 passed |
| `pnpm test:e2e` (Playwright, Prompt 09) | ✅ 12/12 passed (3 execuções consecutivas documentadas no Prompt 09; não re-executado nesta iteração de fecho por não alterar código — ver §8) |
| `scripts/check-forbidden-ports.ps1` | ✅ OK — nenhuma porta proibida |
| Grep de secrets em toda a árvore do repositório (`git ls-files`) | ✅ 0 valores reais — as 3 ocorrências assinaladas por um grep amplo são placeholders documentados de uma fase anterior (`postgres`, `chartrex_e2e_dev_only`), não segredos reais |
| Grep de secrets nos documentos desta fase (`resultados_execucao/`, arquitectura, runbook) | ✅ 0 valores reais — só nomes de variáveis e placeholders `<...>` |

---

## 7. Validações pendentes (não executáveis dentro desta fase)

- **E2E automatizado em CI** — não há pipeline para correr `pnpm test:e2e`
  automaticamente a cada alteração; corre hoje só manualmente.
- **Smoke completo contra PostgreSQL + object storage real** — impossível
  sem a decisão de provider/topologia; o que foi validado (Prompt 02) foi
  contra uma instância descartável, suficiente para confirmar viabilidade
  técnica, não para fechar staging formal.
- **Validação de rotação de secrets automatizada** — a rotação manual foi
  validada em runtime real (Prompt 04); uma rotação agendada/automatizada
  não existe nem foi pedida nesta fase.
- **Um terceiro a seguir o runbook do zero** — o runbook (Prompt 10) foi
  validado por revisão + greps + confirmação contra scripts reais, não por
  outra pessoa a executá-lo numa máquina nova sem contexto prévio.

---

## 8. Riscos

| Risco | Severidade | Nota |
|---|---|---|
| Confundir "staging técnico com observabilidade" com "staging pré-produção formal" | **Alto** | Mitigado por este documento e pela arquitectura — declarado explicitamente `pronto_parcialmente_com_pendencias`, nunca "pronto" sem qualificação |
| DB staging continuar em SQLite indefinidamente por falta de decisão de topologia | Alto | Sem prazo definido; a validação técnica (Prompt 02) já remove o risco de "descobrir tarde" que PostgreSQL não funciona |
| Object storage local ser usado além do piloto técnico (sem controlo de acesso, sem durabilidade garantida) | Médio | Documentado como limitação explícita desde a fase 04; interface já pronta para um provider real quando decidido |
| Secrets geridos manualmente por múltiplos operadores em staging real | Médio | Sem mecanismo formal; mitigado parcialmente pela disciplina já documentada (rotação, `.gitignore` correcto, nunca em ficheiro versionado) |
| `MediaKit` sem estado `FAILED` próprio continuar a exigir uma convenção de metadata em 3 sítios (backend serializer, frontend helper, painel dedicado) | Baixo–Médio | Já registado como decisão de produto pendente (Prompt 07); task de pesquisa própria já aberta (`task_0dbdcedf`) |
| E2E só corre localmente, sem gate automático | Médio | Sem CI/CD no repositório; qualquer regressão só é apanhada se alguém correr `pnpm test:e2e` manualmente |
| `INTELLIGENCE_ENGINE_DRY_RUN=true` esconder silenciosamente a ausência de recomendações (E2E e UX dependem de recomendações reais) | Baixo | Já documentado (Prompt 09) — dry-run devolve sempre `recommendations: []`, comportamento intencional do stub, não um bug |

---

## 9. Limitações conhecidas (consolidado, não exaustivo além do já registado por prompt)

- `DATABASE_URL` não é suportado (por desenho) — só variáveis discretas `DB_*`.
- `signed_url` não existe como campo — só `public_url`.
- Nenhum agregador/retenção central de logs — só stdout por processo.
- `MediaKit.Status` não tem `FAILED` próprio — convenção via `metadata.generation_status`.
- `CampaignAction` permanece com lifecycle totalmente independente do artefacto relacionado — uma acção pode ficar `pending` com o artefacto já `failed` (visível via `related_artifact_status`, não corrigido automaticamente, por decisão consciente).
- Não existe endpoint "as minhas permissões neste workspace" — RBAC é só por-view no backend.
- Criar uma CampaignAction na UI exige pelo menos uma recomendação da Intelligence — não há afforance de criação independente.
- Sem CI/CD no repositório.

---

## 10. Decisão de prontidão

**Classificação final: `pronto_parcialmente_com_pendencias`.**

- **Pronto para continuar o piloto técnico staging** (nível já alcançado na
  fase 04) **com observabilidade, correlation-id, estados honestos, RBAC/UX
  validado e E2E automatizado adicionados** — este é um avanço real e
  utilizável hoje.
- **Não pronto para declarar "staging pré-produção formal"** enquanto DB,
  object storage e secrets continuarem dependentes de SQLite/storage
  local/`.env` manual — três decisões de infraestrutura explicitamente fora
  do âmbito de "não inventar" desta fase.
- **Produção não é, em nenhuma leitura deste documento, declarada pronta.**
  Produção exige, adicionalmente ao que falta acima, SLA, alta
  disponibilidade, alertas e rotação automática de secrets — nenhum dos
  quais foi sequer iniciado.

---

## 11. Próximos passos recomendados

1. **Decisão de produto/infra** (fora do âmbito de código): escolher a
   topologia de PostgreSQL persistente, o provider de object storage, e o
   mecanismo de secrets para staging real. Nenhum destes tem bloqueio
   técnico — são decisões, não trabalho de engenharia pendente.
2. Quando essas decisões existirem, o trabalho de implementação é pequeno e
   já mapeado por prompt (§4 acima) — nenhum deles exige tocar no Backend
   Core além de configuração.
3. Introduzir CI/CD (mesmo mínimo) para correr `pnpm test:e2e` e as suites
   de teste automaticamente — actualmente é 100% manual.
4. Resolver as decisões de produto pendentes assinaladas no Prompt 07
   (`MediaKit.Status.FAILED`) e Prompt 08 (endpoint de capabilities), se o
   produto as considerar prioritárias.
5. Validar o runbook com um técnico sem contexto prévio da fase, numa
   máquina nova, para confirmar que os passos são suficientes na prática.
