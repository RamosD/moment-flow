# Prompt 11 — Actualizar runbook local — Resultado

**Data:** 2026-07-03
**Fase:** `06_staging_infraestrutura_real_local` (STG-LOCAL-011)
**Âmbito:** consolidar o runbook para reflectir a stack staging local real — PostgreSQL, MinIO, secrets, scripts, quality gate, segurança, observabilidade e E2E (estado honesto). Sem alterar produto.
**Estado de execução:** `executado` — runbook reescrito e consolidado numa estrutura única de 22 secções, todos os comandos-chave revalidados contra a stack real nesta iteração, matriz de sintomas de 12 itens criada, validação por terceiro registada honestamente como pendente (não mascarada).

---

## 1. Leituras feitas (tarefas 1–2)

- Runbook da fase 05 (`runbook_staging_pre_producao.md`) — usado como
  referência de estrutura (secções numeradas, matriz de sintomas §15,
  critérios de pronto/não-pronto §16), não de conteúdo (fase 05 descreve
  uma stack não-local, esta fase descreve local-first).
- Os 10 relatórios de execução desta fase
  (`resultados_execucao/prompt_01_*` a `prompt_10_*`) — lidos
  integralmente; o runbook consolidado cita cada um nos pontos relevantes,
  em vez de repetir o conteúdo.
- O runbook existente (`runbook_staging_local.md`, criado
  incrementalmente nos Prompts 06/07/09/10) — usado como base, não
  descartado; a maior parte do conteúdo técnico já estava correcto,
  faltava consolidação estrutural e as secções explicitamente pedidas por
  este prompt que ainda não existiam (migrations, seeds, storage MinIO,
  E2E, matriz de sintomas de 12 itens, validação por terceiro).

## 2. Ficheiros criados/alterados

| Ficheiro | Operação |
|---|---|
| `frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/runbook_staging_local.md` | **reescrito/consolidado** — de 11 secções (+ 8.1/8.2) para 22 secções numeradas continuamente |
| `frontend/docs/.../resultados_execucao/prompt_11_runbook_local_resultado.md` | **criado** (este relatório) |

Nenhum ficheiro de código de produto foi alterado.

## 3. Secções do runbook consolidado

| § | Secção | Novo nesta iteração? |
|---|---|---|
| 0 | Antes de começar | Reaproveitado |
| 1 | Pré-requisitos | Expandido (bloqueio explícito se Docker indisponível) |
| 2 | Portas canónicas | Reaproveitado + nota de bind `127.0.0.1` (achado STG-LOCAL-009) |
| 3 | **Docker — infraestrutura** | **Novo** (secção dedicada, antes só implícita nos scripts) |
| 4 | Env local / secrets | Reaproveitado + reforço explícito sobre `ALLOW_INSECURE_EMPTY_TOKEN` |
| 5 | Scripts disponíveis | Reaproveitado |
| 6 | Start infra | Reaproveitado |
| 7 | Start apps | Reaproveitado |
| 8 | Healthchecks | Reaproveitado |
| 9 | **Migrations** | **Novo** — comando revalidado nesta iteração (ver §5) |
| 10 | **Seeds** | **Novo** |
| 11 | **Storage MinIO** | **Novo** — contrato e evidência do Prompt 04 |
| 12 | **E2E** | **Novo** — estado honesto: STG-LOCAL-008 ainda não executado (ver §6) |
| 13 | **Segurança** | **Novo** (resumo operacional dos 2 achados reais do Prompt 09) |
| 14 | **Observabilidade** | **Novo** (resumo operacional do Prompt 10) |
| 15 | Quality gate local | Reaproveitado, resumido |
| 16 | Paragem | Reaproveitado |
| 17 | Reset destrutivo | Reaproveitado, revalidado nesta iteração |
| 18 | Troubleshooting | Reaproveitado (10 sintomas já documentados) |
| 19 | **Matriz de sintomas (12 itens pedidos pelo backlog)** | **Novo** |
| 20 | **Validação por terceiro** | **Novo** — pendência registada, ver §6 |
| 21 | **Limitações conhecidas** | **Novo** — consolida as pendências das secções 12/20/14 |
| 22 | Referências | Reaproveitado, actualizado |

### 3.1 Matriz de sintomas (§19) — os 12 itens pedidos

Todos os 12 itens explicitamente listados na tarefa 5 estão cobertos, cada
um com causa mais provável e remissão para a secção de detalhe: Docker
indisponível, porta 5432 ocupada, porta 9000/9001 ocupada, DB migration
falha, MinIO health falha, bucket ausente, `Asset.public_url` vazio,
callback 403, IE down, Renderer down, frontend chama porta errada, E2E sem
recommendations.

## 4. Estado do E2E — honestidade explícita (secção 12)

O runbook **não declara E2E local validado**. Estado registado tal como é:

- `pnpm test:e2e` real contra a stack totalmente activa **não correu**
  nesta fase até este ponto (STG-LOCAL-008 continua pendente).
- O que está validado: o modo `-WithE2E` do quality gate falha de forma
  clara (não silenciosa) sem a stack activa; e o **fluxo funcional
  equivalente** ao que o E2E cobriria foi validado por chamadas HTTP
  directas em 4 iterações anteriores (03, 04, 09, 10).

Isto respeita explicitamente a regra "Não declarar E2E local validado se
rodou contra stack dev antiga" — por analogia, não declarar validado
quando não rodou de todo.

## 5. Comandos validados nesta iteração (contra scripts/stack reais)

| Comando | Resultado |
|---|---|
| `Import-DotEnvFile -Path .env.staging.local` (via `scripts\lib\staging-local-common.ps1`, dot-sourced) + `manage.py check` | ✅ `System check identified no issues (0 silenced).` — **substituiu** um trecho PowerShell inline não testado que estava no rascunho inicial deste runbook, pela função já validada nos scripts (mais fiável, um único mecanismo de carregamento de env em todo o runbook) |
| `scripts\staging-local-health.ps1` | ✅ 8/8 verificações `OK`/`SKIPPED` correctamente — infra saudável, 4 apps activos e correctamente identificados |
| `scripts\staging-local-infra-reset.ps1` (sem `-IAmSure`) | ✅ bloqueado, exit 1, `docker volume ls` confirmaria (não repetido nesta iteração — já confirmado nos Prompts 06/09) volumes intactos |
| `scripts\check-forbidden-ports.ps1` | ✅ OK |

Todos os outros comandos do runbook (migrations, seeds, quality gate,
scripts de infra/apps, diagnóstico MinIO/PostgreSQL) foram **já validados
em execuções reais nos Prompts 02–10** — este runbook cita o relatório de
origem em cada caso, não inventa nenhum comando novo não testado.

## 6. Validação por terceiro

**Sem terceiro disponível nesta sessão.** Registado explicitamente na
secção 20 do runbook como **pendência**, não mascarado como "feito". Não
foi pedida nem simulada uma validação por terceiro — a secção diz
literalmente que isto não aconteceu e que é uma pendência para antes de um
eventual fecho formal da fase (STG-LOCAL-012).

## 7. Greps executados

| Grep | Resultado |
|---|---|
| `password\|secret\|token\|api_key\|private_key` (case-insensitive) no runbook completo | ✅ Todas as ocorrências são nomes de variável (`INTERNAL_API_TOKEN`, `E2E_PASSWORD`, `STORAGE_SECRET_KEY`, etc.), cabeçalhos (`X-Internal-Token`), ou placeholders literais de exemplo (`<user>`, `<password>`, `<definido pelo operador>`) — nenhum valor real |
| `scripts/check-forbidden-ports.ps1` | ✅ OK — nenhuma porta proibida referenciada |
| Confirmação manual: nenhuma menção a cloud (AWS/R2/GCS/Azure), Kubernetes, ou produção como algo "pronto" | ✅ confirmado por leitura integral — o documento reafirma explicitamente "Não descreve produção. Não descreve cloud." no cabeçalho |
| Confirmação manual: `ALLOW_INSECURE_EMPTY_TOKEN` nunca recomendado como opção de staging | ✅ secção 4 diz explicitamente o oposto — "nunca é uma opção válida de staging local" |

## 8. Critérios de aceitação — verificação directa

| Critério | Estado |
|---|---|
| Runbook reflecte a stack local real | ✅ |
| Comandos são concretos e testáveis | ✅ — revalidados nesta iteração (§5) ou já validados em iterações anteriores, com referência cruzada |
| Não há secrets | ✅ (§7) |
| Reset destrutivo está separado | ✅ — secção 17, script próprio, `-IAmSure` + confirmação escrita, revalidado (§5) |
| Troubleshooting cobre PostgreSQL e MinIO | ✅ — secções 14, 18, 19 |
| Validação por terceiro feita ou pendente sem mascarar | ✅ — pendente, registado honestamente (§6) |

## 9. Riscos

| Risco | Situação |
|---|---|
| Runbook desactualizar-se à medida que os Prompts 12+ avançarem | Mitigado pela estrutura numerada estável e pelas referências cruzadas a relatórios, que não precisam de ser reescritas, só acrescentadas |
| Um operador seguir o runbook sem ter lido a nota sobre `E2E` (§12) e assumir que já está validado | Mitigado pelo aviso ⚠️ explícito logo no topo do documento (cabeçalho) e repetido na própria secção 12 |
| Comandos de diagnóstico MinIO/PostgreSQL (§14) usam `<user>`/`<password>` como placeholders — um operador novo pode não saber onde os obter | Mitigado pela referência cruzada à secção 4 (mecanismo de secrets) em todos os pontos onde credenciais são necessárias |

## 10. Próximo passo recomendado

Avançar para **STG-LOCAL-012** (fecho da fase): consolidar os 11
relatórios em um estado final, classificar honestamente a prontidão
(`pronto_para_staging_local_formal` / `pronto_parcialmente_com_pendencias`
/ outro), listar explicitamente o que falta —
principalmente STG-LOCAL-008 (E2E real) e a validação por terceiro (§6/§20
deste runbook) — sem declarar produção nem staging formal completo
enquanto essas duas pendências não forem resolvidas ou conscientemente
aceites como fora do âmbito de fecho.
