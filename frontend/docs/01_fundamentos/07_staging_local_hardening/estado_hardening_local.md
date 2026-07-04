# Estado — Staging Local Hardening (fase 07)

> Fase: `07_staging_local_hardening` (fecho — STG-HARD-010)
> Data: 2026-07-03
> Fonte: os 10 relatórios em `resultados_execucao/` (Prompts 01–10),
> `01_backlog.md`, `runbook_staging_local.md` (fase 06, actualizado por
> esta fase), e validação final executada nesta iteração de fecho.
> Não descreve produção. Não descreve cloud. Sem secrets reais.

---

## 1. Resumo executivo

A fase 06 fechou como `pronto_para_staging_local_formal`, com seis
pendências/riscos explicitamente registados para uma fase de
endurecimento futura. A fase 07 atacou todos os seis, um por prompt:

```text
STG-HARD-001  Flake E2E                          → corrigido, validado 7×
STG-HARD-002  Timeout PostgreSQL                  → corrigido, medido antes/depois
STG-HARD-003  Credenciais MinIO root              → corrigido, policy mínima validada
STG-HARD-004  Validação por segundo operador      → pendência organizacional, não fechada
STG-HARD-005  CI/CD real                          → proposta documentada, não activada (decisão)
STG-HARD-006  Cleanup local por run-id            → implementado, validado com isolamento real
STG-HARD-007  Diagnóstico de falhas E2E           → implementado; achado de segurança real corrigido
STG-HARD-008  Auditoria .gitignore                → auditado, sem alterações necessárias
STG-HARD-009  Revalidação de segurança            → revalidado, zero regressões
```

**Nenhum critério de rejeição do backlog ocorreu.** Duas pendências
permanecem conscientemente por fechar (validação por um segundo operador
humano real; activação de facto de uma pipeline CI) — ambas com o caminho
para as fechar já preparado e documentado, não escondidas.

## 2. Estado final por item

| Item | Estado | Evidência |
|---|---|---|
| **STG-HARD-001** — E2E | ✅ Implementado e validado | `prompt_01_...md` — waits baseados em resposta HTTP real; **7 execuções consecutivas, 12/12 `PASS`**, zero flakes reproduzidos |
| **STG-HARD-002** — Timeout PostgreSQL | ✅ Implementado e validado | `prompt_02_...md` — `DB_CONNECT_TIMEOUT_SECONDS` (default 5, só postgres); medido: `/ready/` 130.6s→~5.2s, endpoint normal >150s→~31s; risco residual documentado (não corrigido, fora do âmbito estreito) |
| **STG-HARD-003** — MinIO não-root | ✅ Implementado e validado | `prompt_03_...md` — utilizador `chartrex_renderer`, policy só `PutObject`+`GetObject`; validado: upload real funciona, listagem/admin negados |
| **STG-HARD-004** — Validação por 2º operador | ⏳ **Pendente — organizacional, não técnica** | `prompt_07_...md` — sem operador humano disponível nesta fase; pacote de validação (`checklist_validacao_runbook_operador.md`) pronto a entregar; 2 ambiguidades reais do runbook corrigidas por revisão própria e confirmadas ao vivo |
| **STG-HARD-005** — CI/CD real | ⏳ **Proposta documentada, não activada — decisão explícita** | `prompt_08_...md`, `proposta_cicd_github_actions.md` — sem plataforma CI configurada; GitHub Actions proposto (reutiliza o quality gate), mas o operador optou por não criar o workflow activo nesta iteração |
| **STG-HARD-006** — Cleanup por run-id | ✅ Implementado e validado | `prompt_04_...md` — `cleanup_e2e_run` + `cleanup-e2e-run.ps1`; validado com 2 run-ids reais, isolamento confirmado em PostgreSQL e MinIO |
| **STG-HARD-007** — Diagnóstico E2E | ✅ Implementado e validado | `prompt_05_...md` — `diagnostics.ts`, relatório HTML, `global-teardown.ts`; **achado real de segurança encontrado e corrigido** (trace continha JWT/password em claro) |
| **STG-HARD-008** — Auditoria `.gitignore` | ✅ Auditado — sem correcções necessárias | `prompt_06_...md` — todos os padrões suspeitos verificados com `git check-ignore`; nenhuma colisão com código-fonte encontrada além do já corrigido na fase 06 |
| **STG-HARD-009** — Revalidação de segurança | ✅ Revalidado — zero regressões | `prompt_09_...md` — frontend isolado, Network só Backend Core (E2E real), tokens internos nunca no browser, MinIO sem listagem pública, binds em `127.0.0.1`, logs/código sem secrets |
| **STG-HARD-010** — Fecho | ✅ Este documento | — |

## 3. Melhorias implementadas (resumo técnico)

- **E2E**: waits por resposta HTTP real (não fecho de diálogo) nos passos
  com artefacto; diagnóstico automático em falha (screenshot, trace,
  `e2e-diagnostics` com run-id/correlation-ids/endpoints, relatório HTML).
- **PostgreSQL**: `connect_timeout` de 5s (configurável), aplicado só a
  `DB_ENGINE=postgres`, sem afectar SQLite/dev.
- **MinIO**: utilizador de serviço não-root (`chartrex_renderer`) com
  policy mínima (`PutObject`+`GetObject`, sem `ListBucket`/delete/admin),
  criado idempotentemente pelo `minio-bucket-init`.
- **Cleanup**: comando Django + script PowerShell para apagar só os dados
  de um `--run-id`, com dry-run, confirmação, e remoção correspondente de
  objectos MinIO.
- **Segurança do próprio pipeline de testes**: redacção automática de
  segredos em traces do Playwright (achado real corrigido); correcção de
  falsos positivos no `secrets_grep` do quality gate (achado real
  corrigido, nunca um segredo real).
- **Documentação**: runbook com secções novas (§4 criação de env pela
  primeira vez, §9/§12 carregamento de env corrigido, §12.1 diagnóstico
  E2E, §17.1 cleanup por run-id); dois bugs reais de runbook/script
  corrigidos por revisão literal (não tácita).

## 4. Validações executadas no fecho (STG-HARD-010)

| Validação | Resultado |
|---|---|
| `staging-local-health.ps1 -RequireApps` | ✅ 8/8 `OK`/`SKIPPED` correctamente |
| `pnpm test:e2e` (execução dedicada de fecho) | ✅ 12/12 `PASS`, 19.8s |
| `staging-local-quality-gate.ps1` (execução completa) | Ver `resultados_execucao/prompt_10_fecho_hardening_local_resultado.md` §3 para o resultado final |
| `check-forbidden-ports.ps1` | ✅ `OK` |
| `secrets_grep` (via quality gate) | ✅ `PASS` — 927 ficheiros, 0 suspeitos |
| Segurança local crítica (bind 127.0.0.1, MinIO sem listagem pública, tokens server-to-server) | ✅ Revalidado no STG-HARD-009, sem regressão desde então |

## 5. Pendências (explícitas, não mascaradas)

1. **Validação por um segundo operador humano real** — nunca aconteceu
   nesta fase (nem na 06). Pacote pronto
   (`checklist_validacao_runbook_operador.md`); só falta um operador
   disponível.
2. **Activação de facto de uma pipeline CI/CD** — proposta completa e
   tecnicamente validada localmente (`proposta_cicd_github_actions.md`),
   mas nenhum `.github/workflows/*.yml` foi criado — decisão consciente do
   operador, revertível a qualquer momento.

Nenhuma das duas pendências é um risco técnico activo — são decisões
organizacionais explicitamente adiadas, com o caminho de fecho já
preparado.

## 6. Riscos remanescentes

| Risco | Severidade | Origem |
|---|---|---|
| Caminho de erro HTTP de um endpoint normal (não `/ready/`) fica bounded a ~31s, não ~5s, em `DEBUG=True` | Baixo-Médio | STG-HARD-002 — causa identificada (página de erro técnica do Django), não corrigida (fora do âmbito estreito) |
| Validação por terceiro continua pendente | Médio | STG-HARD-004 — organizacional |
| CI/CD não activado | Baixo | STG-HARD-005 — decisão, não falha |
| `dist`/`logs`/`media` continuam não ancorados nalguns `.gitignore`, sem colisão actual | Muito baixo | STG-HARD-008 — risco latente, sem evidência para corrigir agora |
| Sem agregação central de logs entre serviços | Baixo | Herdado da fase 06, aceitável para staging local de um operador |

## 7. Decisão de prontidão

**`hardening_local_concluido_com_pendencias`**

Justificação directa contra as cinco opções permitidas pelo backlog:

- **Não** `hardening_local_concluido` — há duas pendências reais e
  conscientes (validação por terceiro; CI/CD não activado), mesmo que
  ambas tenham caminho de fecho pronto.
- **Não** `executado_parcialmente` — todos os 9 itens técnicos do
  backlog foram efectivamente executados (implementados+validados, ou
  auditados sem necessidade de mudança, ou documentados como decisão
  explícita); nada ficou "a meio" sem resposta.
- **Não** `bloqueado` — nada impede o uso desta stack como staging local
  formal endurecido; as pendências são organizacionais, não técnicas.
- **Não** `nao_pronto` — o oposto do que a evidência mostra: quality
  gate, E2E, segurança e MinIO/PostgreSQL estão todos validados de facto.
- **Sim** `hardening_local_concluido_com_pendencias` — todo o trabalho
  técnico do backlog está feito e validado; as duas pendências
  remanescentes são organizacionais (pessoas/decisões), documentadas sem
  eufemismo, com o pacote de fecho já preparado para quando estiverem
  disponíveis.

**Produção continua fora do escopo — não declarada em nenhum ponto desta
fase.** Cloud continua fora do escopo. A classificação
`pronto_para_staging_local_formal` da fase 06 **não é reaberta** — esta
fase construiu sobre ela, não a substituiu.

## 8. Próximos passos

1. Entregar `checklist_validacao_runbook_operador.md` a um segundo
   operador real, assim que disponível — fecha STG-HARD-004.
2. Decidir (fora desta fase) se/quando activar
   `proposta_cicd_github_actions.md` como workflow real — fecha
   STG-HARD-005.
3. Considerar, numa fase futura, se o risco residual do STG-HARD-002
   (~31s em `DEBUG=True`) justifica correcção antes de qualquer staging
   não-local.
4. Nenhuma nova fase de hardening local é necessária para já — o próximo
   passo natural do projecto (produção, cloud, CI/CD real activado,
   containerização) pertence a uma fase nova, não a uma reabertura desta
   nem da fase 06.
