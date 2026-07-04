# Prompt 07 — Validação do runbook por um segundo operador — Resultado

**Data:** 2026-07-03
**Fase:** `07_staging_local_hardening` (STG-HARD-004)
**Âmbito:** validar (ou preparar a validação de) o runbook staging local por
alguém sem contexto tácito da fase.
**Estado de execução:** `preparado, não fechado` — **nenhum segundo
operador humano esteve disponível nesta sessão.** Não se declara validação
por terceiro. Em vez disso: (a) foi criado um pacote de validação completo
e entregável; (b) foi feita uma revisão de documentação linha-a-linha do
runbook, seguindo-o literalmente (não de memória), que encontrou e corrigiu
**dois achados reais** — um deles um bug funcional latente no próprio
`staging-local-quality-gate.ps1`, não só na documentação.

---

## 1. Disponibilidade de operador

**Não houve segundo operador humano disponível nesta sessão.** Este
prompt foi executado de forma autónoma, na sequência dos anteriores desta
mesma fase. Isto é reportado sem eufemismo, exactamente como o backlog
exige (§20 do runbook já regista esta mesma pendência desde a fase 06).

Como o próprio prompt antecipa este cenário ("se não houver operador
disponível: criar pacote de validação pronto para entrega; marcar
pendência como não fechada"), o trabalho desta iteração seguiu esse
caminho: **checklist entregável** +
**correcção de ambiguidades reais encontradas por leitura cuidadosa,
literal, do runbook** (não por memória tácita de como a stack "costuma"
ser operada) — a mesma disciplina que se pediria a um operador real, sem
fingir que substitui um.

## 2. Pacote de validação criado

`frontend/docs/01_fundamentos/07_staging_local_hardening/checklist_validacao_runbook_operador.md`
— 20 passos, do pré-requisito ao reset destrutivo (este último **só
leitura**, nunca executado), com colunas para resultado e dúvidas. Pronta
a entregar a um segundo operador quando um estiver disponível; nenhuma
linha foi marcada como "validada" nesta iteração.

## 3. Achados reais (encontrados por leitura literal do runbook, corrigidos)

### 3.1 `backend_core/.env.staging.local` — sem instruções de criação pela primeira vez

O runbook (§4, antes desta correcção) dizia "ficheiros já criados" mas
nunca explicava **como** criá-los da primeira vez — só a raiz tem um
`.env.staging.local.example` dedicado; os três serviços só têm o
`.env.example` genérico de **dev**, com valores que não servem para
staging (`DB_ENGINE=sqlite`, `STORAGE_PROVIDER=local`). Um operador sem
contexto que copiasse o `.env.example` verbatim ficaria com uma stack que
"funciona" (não há erro), mas contra SQLite/filesystem local, não contra
o PostgreSQL/MinIO do container — invalidando silenciosamente o próprio
propósito da fase 06/07.

**Corrigido**: nova tabela em §4 com as chaves exactas a mudar por
ficheiro, relativamente ao `.env.example` de cada serviço.

### 3.2 `seed_e2e_run`/E2E podia seedar contra SQLite em silêncio — achado mais grave, com bug real de script

Leitura de código (`frontend/e2e/global-setup.ts`): o `seed_e2e_run`
chamado pelo E2E herda **só** o ambiente do processo `pwsh` que invoca
`pnpm test:e2e` (`spawnSync(..., { env: process.env })`) — nunca lê
`backend_core/.env.staging.local` por si só. Nem o runbook §12 nem
`scripts/staging-local-quality-gate.ps1` (`-WithE2E`) carregavam esse
ficheiro antes de invocar `pnpm test:e2e`. Um operador a seguir §12
literalmente, numa sessão `pwsh` nova, teria o `seed_e2e_run` a criar dados
em **SQLite** (default de dev), não no PostgreSQL do container — o E2E
"passaria" tecnicamente (a UI funciona contra qualquer BD), mas sem validar
nada do que a fase 06/07 realmente exige.

**Corrigido em dois sítios**:
1. `frontend/docs/.../runbook_staging_local.md` §12 — adicionado
   `Import-DotEnvFile -Path backend_core\.env.staging.local -Required:$true`
   antes de `pnpm test:e2e`.
2. **`scripts/staging-local-quality-gate.ps1`** (`-WithE2E`) — mesma
   correcção aplicada directamente no script (não só na documentação),
   porque este é o "caminho oficial" recomendado pelo próprio runbook para
   correr E2E; documentar a correcção só no runbook e deixar o script
   com o mesmo bug lateral seria "ajudar verbalmente e não corrigir",
   exactamente o que este prompt proíbe.

### 3.3 §9/§10 (migrations/seeds) — mesmo género de risco, `-Required:$false` implícito

`Import-DotEnvFile` só lança erro com `-Required:$true`; sem essa flag,
falha em silêncio. O runbook (§9) já usava a função mas sem `-Required`.
**Corrigido**: `-Required:$true` adicionado a §9; nota equivalente
acrescentada a §10 (mesma sessão `pwsh`, ou repetir o carregamento).

## 4. Actualização — re-validação ao vivo concluída (mesma sessão, depois do Docker Desktop ficar disponível)

O Docker Desktop desta máquina não estava a correr no início desta
iteração; a correcção do §3.2 foi por isso inicialmente só verificada por
leitura de código. **O Docker Desktop ficou disponível ainda dentro desta
mesma sessão** (confirmado por um arranque em segundo plano concluído
depois deste relatório ter sido escrito pela primeira vez), o que permitiu
fechar esta limitação de facto, já na iteração seguinte (STG-HARD-009):

```powershell
$env:E2E_PASSWORD = '<definido pelo operador>'
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-quality-gate.ps1 -WithE2E -Only e2e
```

Corrido **numa sessão `pwsh` completamente nova**, sem nenhum
`Import-DotEnvFile` manual prévio — exactamente o cenário que o achado do
§3.2 previa como perigoso. Resultado: **12/12 `PASS` em 18.4s**, incluindo
a criação real de media kit (exige upload real ao MinIO, só possível
contra o container real, nunca contra SQLite/local) e o teste dedicado de
isolamento de rede. **A correcção funciona ao vivo, confirmado, não só por
leitura de código.**

Esta secção deixa de ser uma limitação e passa a ser evidência de fecho.

## 5. Ficheiros criados/alterados

| Ficheiro | Operação |
|---|---|
| `frontend/docs/.../06_staging_infraestrutura_real_local/runbook_staging_local.md` | §4 (tabela de criação de `.env.staging.local`), §9 (`-Required:$true`), §10 (nota), §12 (carregar env do backend_core antes do E2E) |
| `scripts/staging-local-quality-gate.ps1` | `-WithE2E`: carrega `backend_core\.env.staging.local` (`-Required:$true`) antes de invocar `pnpm test:e2e` |
| `frontend/docs/.../07_staging_local_hardening/checklist_validacao_runbook_operador.md` | **criado** |
| `frontend/docs/.../07_staging_local_hardening/resultados_execucao/prompt_07_validacao_runbook_operador_resultado.md` | **criado** (este relatório) |

## 6. Validações executadas

| Validação | Resultado |
|---|---|
| Grep de secrets no runbook + checklist (`INTERNAL_API_TOKEN=`, `E2E_PASSWORD=`, `DB_PASSWORD=`, `MINIO_*_PASSWORD=`, `Bearer <token>`) | ✅ 0 ocorrências |
| `scripts/check-forbidden-ports.ps1` | ✅ `OK` |
| Execução real dos comandos por um operador | ❌ Não aplicável — sem operador (§1) |
| Health real / quality gate / E2E re-executados nesta iteração | ❌ Não executados — Docker Desktop indisponível nesta janela (§4); a stack tinha sido validada nas iterações anteriores desta mesma fase, mas não com o env-loading agora corrigido |

## 7. Critérios de aceitação — verificação honesta

- ⏳ "Segundo operador executa sem ajuda verbal crítica **ou** pendência
  fica formalmente registada" — **a segunda opção aplica-se**: pendência
  registada, não mascarada.
- ✅ Ambiguidades identificadas foram corrigidas (§3, no runbook e num
  script).
- ✅ "Comandos principais confirmados ou marcados como pendentes" — a
  correcção nova (env-loading do E2E) foi confirmada ao vivo (§4), já
  dentro desta mesma sessão.
- ✅ Runbook não contém secrets.
- ✅ Reset destrutivo continua protegido (`-IAmSure` + confirmação escrita)
  — **não executado** nesta iteração, só lido.
- ✅ Relatório é honesto — nenhuma validação por terceiro é reclamada.

Nenhum critério de rejeição ocorreu: não se declarou validação sem
operador, nenhuma ajuda verbal ficou por documentar (o oposto — dois
achados reais viraram correcções permanentes), nenhuma falha foi ignorada,
nenhum secret foi exposto, o reset destrutivo não foi executado, e em
nenhum momento staging local foi confundido com produção.

## 8. Riscos remanescentes

| Risco | Severidade | Nota |
|---|---|---|
| Validação por terceiro continua pendente (arrastada da fase 06) | Médio | Sem mudança de fundo nesta iteração — só ficou mais barata de fazer (pacote pronto, ambiguidades já reduzidas, correcções já confirmadas ao vivo) |

## 9. Próximo passo recomendado

1. Entregar `checklist_validacao_runbook_operador.md` a um segundo
   operador real assim que um esteja disponível — é o único passo que
   falta para fechar STG-HARD-004 de facto (todas as correcções técnicas já
   estão feitas e confirmadas ao vivo).
2. Seguir para **STG-HARD-010** (fecho da fase), conforme prioridade do
   operador.
