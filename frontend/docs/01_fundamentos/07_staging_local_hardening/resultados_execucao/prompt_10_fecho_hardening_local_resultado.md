# Prompt 10 — Fecho de hardening local — Resultado

**Data:** 2026-07-03
**Fase:** `07_staging_local_hardening` (STG-HARD-010, fecho)
**Âmbito:** consolidar a fase 07, decidir honestamente se o staging local
formal ficou endurecido, sem declarar produção nem reabrir a
classificação da fase 06.
**Estado de execução:** `executado` — os 9 relatórios anteriores lidos e
consolidados (mais um, `prompt_01`, materializado agora — ver §2), quality
gate completo re-executado do zero para o fecho (10/10 obrigatórias
`PASS`), E2E revalidado (12/12), classificação final:
**`hardening_local_concluido_com_pendencias`**.

---

## 1. Estado final

**Classificação: `hardening_local_concluido_com_pendencias`** — ver
`estado_hardening_local.md` §7 para a justificação completa contra as
cinco opções permitidas pelo backlog.

Resumo: todos os itens técnicos do backlog (E2E, timeout PostgreSQL,
MinIO não-root, cleanup por run-id, diagnóstico E2E, auditoria
`.gitignore`, revalidação de segurança) foram implementados e validados
com evidência real. As duas pendências remanescentes (validação por um
segundo operador humano; activação de facto de uma pipeline CI) são
**organizacionais, não técnicas** — ambas com o caminho de fecho já
preparado e documentado, nunca escondidas.

## 2. Nota sobre o Prompt 01 (E2E) — materializado neste fecho

O trabalho técnico de STG-HARD-001 (investigação do flake, correcção dos
waits em `main-flow.spec.ts`) foi feito no arranque desta fase, mas **não
tinha um relatório próprio** até este fecho — a fase seguiu para os
Prompts 02–09 sem essa lacuna ser notada. Corrigido agora,
retroactivamente mas sem inventar nada: `prompt_01_estabilizar_e2e_local_resultado.md`
documenta a causa, a correcção, e agrega a evidência de validação já
acumulada ao longo de toda a fase (7 execuções limpas, 12/12, em
diferentes iterações). Esta materialização tardia é, em si, um pequeno
achado de processo desta fase — registado, não escondido.

## 3. Estado por item do backlog

| Item | Estado | Prompt/evidência |
|---|---|---|
| **STG-HARD-001** — Estabilizar E2E | ✅ Implementado e validado | 01 — waits por resposta HTTP real; 7/7 execuções limpas, zero flakes |
| **STG-HARD-002** — Timeout PostgreSQL | ✅ Implementado e validado | 02 — `DB_CONNECT_TIMEOUT_SECONDS`; `/ready/` 130.6s→~5.2s; risco residual (~31s em `DEBUG=True`) documentado |
| **STG-HARD-003** — MinIO não-root | ✅ Implementado e validado | 03 — utilizador `chartrex_renderer`, policy mínima; upload real confirmado, admin/listagem negados |
| **STG-HARD-004** — Validação por 2º operador | ⏳ Pendente, organizacional | 07 — sem operador disponível; checklist pronta; 2 ambiguidades reais do runbook corrigidas e confirmadas ao vivo |
| **STG-HARD-005** — CI/CD real | ⏳ Proposta documentada, não activada | 08 — sem plataforma CI existente; GitHub Actions proposto, decisão de não activar tomada explicitamente pelo operador |
| **STG-HARD-006** — Cleanup por run-id | ✅ Implementado e validado | 04 — `cleanup_e2e_run` + script; isolamento real confirmado (2 run-ids distintos, Postgres+MinIO) |
| **STG-HARD-007** — Diagnóstico E2E | ✅ Implementado e validado | 05 — `diagnostics.ts`, relatório HTML, redacção de traces; achado real de segurança corrigido |
| **STG-HARD-008** — Auditoria `.gitignore` | ✅ Auditado, sem correcções necessárias | 06 — todos os padrões suspeitos verificados, nenhuma colisão nova |
| **STG-HARD-009** — Revalidação de segurança | ✅ Revalidado, zero regressões | 09 — frontend isolado, binds `127.0.0.1`, MinIO sem listagem pública, tokens só server-to-server |
| **STG-HARD-010** — Fecho | ✅ Este relatório | — |

12 de 12 critérios técnicos do backlog cumpridos ou formalmente decididos;
2 pendências organizacionais registadas sem eufemismo.

## 4. Validações executadas nesta iteração de fecho

```powershell
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-health.ps1 -RequireApps
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-quality-gate.ps1
pnpm test:e2e   # (frontend/, via Import-DotEnvFile do backend_core primeiro)
pwsh -ExecutionPolicy Bypass -File scripts\check-forbidden-ports.ps1
```

| Validação | Resultado |
|---|---|
| `staging-local-health.ps1 -RequireApps` | ✅ 8/8 `OK`/`SKIPPED` correctamente |
| `pnpm test:e2e` (execução dedicada de fecho) | ✅ **12/12 `PASS`**, 19.8s — 7ª execução limpa consecutiva desta fase |
| `staging-local-quality-gate.ps1` (execução completa, do zero) | ✅ **10/10 etapas obrigatórias `PASS`** (`e2e` `SKIP`, por desenho, sem `-WithE2E`) |
| `check-forbidden-ports.ps1` | ✅ `OK` |
| `secrets_grep` (dentro do quality gate) | ✅ `PASS` — 927 ficheiros, 0 suspeitos |

### 4.1 Resultado completo do quality gate

| Etapa | Estado | Duração |
|---|---|---|
| `backend_core_check` | PASS | 3.9s |
| `backend_core_pytest` | PASS | 648.4s |
| `intelligence_engine_pytest` | PASS | 5.9s |
| `content_renderer_typecheck` | PASS | 68.5s |
| `content_renderer_lint` | PASS | 61.0s |
| `content_renderer_test` | PASS | 26.9s |
| `frontend_test` | PASS | 1.7s |
| `frontend_lint` | PASS | 73.0s |
| `frontend_build` | PASS | 22.6s |
| `forbidden_ports` | PASS | 23.5s |
| `secrets_grep` | PASS | 1.4s |
| `e2e` | SKIP | — (opcional, validado à parte acima) |

**10/10 `PASS`, 936.8s totais (~15m37s)** — nenhuma etapa mascarada,
nenhuma falha ignorada. Consistente com as execuções completas anteriores
desta e da fase 06 (mesma suite, mesmo resultado qualitativo).

## 5. Ficheiros criados/alterados ao longo de toda a fase 07 (consolidado)

| Área | Ficheiros |
|---|---|
| Backend Core | `config/settings.py` (timeout), `apps/core/management/commands/cleanup_e2e_run.py` (novo), `apps/core/tests/test_cleanup_e2e_run.py` (novo), `.env.example` |
| Content Renderer | `.env.example` (credenciais) |
| Docker/infra | `docker-compose.staging.local.yml` (utilizador MinIO não-root), `.env.staging.local.example` |
| Frontend/E2E | `e2e/main-flow.spec.ts`, `e2e/diagnostics.ts` (novo), `e2e/global-teardown.ts` (novo), `playwright.config.ts` |
| Scripts | `scripts/cleanup-e2e-run.ps1` (novo), `scripts/staging-local-quality-gate.ps1` (env-loading do E2E; `secrets_grep` mais preciso) |
| Documentação (fase 06, actualizada por esta fase) | `runbook_staging_local.md` (§4, §9, §10, §11, §12, §12.1, §14, §17.1, §18, §21), `estado_staging_local.md` (§8, §9) |
| Documentação (fase 07, nova) | `estado_hardening_local.md`, `checklist_validacao_runbook_operador.md`, `proposta_cicd_github_actions.md`, 10 relatórios em `resultados_execucao/` |

Nenhum ficheiro `.env.staging.local` real foi alterado de forma insegura;
nenhum secret foi versionado; nenhum deploy foi criado.

## 6. Critérios de aceitação da fase — verificação final

- ✅ E2E local estabilizado (7/7 execuções limpas ao longo da fase, causa
  do flake original identificada e tratada).
- ✅ Timeout PostgreSQL tratado (medido antes/depois), com decisão
  explícita sobre o risco residual não corrigido.
- ✅ Credenciais MinIO endurecidas (não-root, policy mínima, validada).
- ✅ Runbook — pendência de validação por terceiro explicitamente aceite,
  não mascarada; pacote de validação pronto.
- ✅ CI/CD — bloqueio/decisão concreta documentada (proposta completa, não
  activada por escolha, não por incapacidade).
- ✅ Quality gate verde (10/10).
- ✅ Segurança local revalidada (zero regressões).
- ✅ Produção não declarada em nenhum documento desta fase.
- ✅ Nenhum secret exposto (greps dedicados em todas as iterações).

## 7. Critérios de rejeição — confirmados como não tendo ocorrido

- ❌ Declarar hardening concluído ignorando flake — não ocorre; o flake
  foi investigado, corrigido e validado 7×.
- ❌ Ignorar timeout PostgreSQL — corrigido e medido.
- ❌ Manter MinIO root sem decisão — corrigido, com policy mínima.
- ❌ Declarar validação por terceiro sem terceiro — nunca declarada;
  pendência explícita mantida.
- ❌ Criar CI insegura — nenhuma CI foi criada; a proposta não tem
  secrets nem deploy.
- ❌ Mascarar falhas — o achado do `secrets_grep` (falsos positivos) e o
  achado de segurança do trace do Playwright foram ambos investigados e
  corrigidos abertamente, documentados em detalhe.
- ❌ Reintroduzir `ListBucket` público — confirmado `403` em STG-HARD-009.
- ❌ Regressão para `0.0.0.0` — confirmado `127.0.0.1` nas 3 portas em
  STG-HARD-009.
- ❌ Frontend a chamar IE/Renderer — confirmado isolado (bundle + E2E
  real) em STG-HARD-009.
- ❌ Declarar produção-ready — não ocorre em nenhum documento desta fase.

## 8. Riscos remanescentes (herdados de `estado_hardening_local.md` §6)

O risco mais relevante para um leitor futuro continua a ser confundir
"staging local formal endurecido" (o que esta fase entrega) com "staging
externo" ou "produção" — mitigado pela linguagem explícita em todos os
documentos desta fase, tal como na fase 06.

## 9. Decisão de prontidão

**`hardening_local_concluido_com_pendencias`** — ver `estado_hardening_local.md`
§7 para o texto completo da decisão e a justificação contra as cinco
opções do backlog.

## 10. Próximos passos recomendados

1. Entregar `checklist_validacao_runbook_operador.md` a um segundo
   operador real assim que disponível (fecha STG-HARD-004).
2. Decidir, fora desta fase, se/quando activar
   `proposta_cicd_github_actions.md` (fecha STG-HARD-005).
3. Esta fase (`07_staging_local_hardening`) está encerrada do ponto de
   vista dos prompts planeados (01–10 completos). Trabalho adicional
   (produção, cloud, CI/CD real activado, containerização das aplicações)
   deveria abrir uma fase nova, não reabrir esta nem a fase 06.
