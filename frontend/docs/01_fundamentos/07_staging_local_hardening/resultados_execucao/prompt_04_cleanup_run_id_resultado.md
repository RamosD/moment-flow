# Prompt 04 — Cleanup seguro por run-id (PostgreSQL + MinIO) — Resultado

**Data:** 2026-07-03
**Fase:** `07_staging_local_hardening` (STG-HARD-006)
**Âmbito:** cleanup seguro, por `--run-id`, dos dados de E2E/smoke em
PostgreSQL e MinIO, sem tocar noutras execuções e sem usar o reset
destrutivo como limpeza normal.
**Estado de execução:** `executado` — management command Django
(`cleanup_e2e_run`) + script PowerShell orquestrador
(`cleanup-e2e-run.ps1`, Postgres + MinIO), validados contra a stack real com
dois run-ids distintos: um limpo, um preservado, ambos com artefactos MinIO
reais.

---

## 1. Inventário: como o run-id se reflecte nos dados (leitura de código)

A partir de `seed_e2e_run.py` e do layout de chaves do Content Renderer
(`content_renderer/src/storage/s3-storage.ts`):

| Entidade | Como o run-id aparece | Mecanismo de limpeza |
|---|---|---|
| `User` | email `e2e-{run_id}@example.local` | Apagado explicitamente, à parte |
| `Workspace` | nome `E2E Workspace {run_id}` | **Hard delete** (ver §2) — raiz da cascata |
| `Artist`, `Track`, `Campaign` | FK `workspace` (`WorkspaceOwnedModel`, `on_delete=CASCADE`) | Cascata automática do hard delete do workspace |
| `CampaignAction` | FK `workspace` (CASCADE) | Cascata |
| `Report` (+`ReportSection`), `MediaKit` (+`MediaKitItem`) | FK `workspace` (CASCADE) | Cascata |
| `ContentPackRequest`, `ContentOutput` | FK `workspace` (CASCADE) | Cascata |
| `Asset` | FK `workspace` (CASCADE) | Cascata |
| `WorkspaceMember`, `Role` (se específico do workspace) | FK `workspace` (CASCADE) | Cascata |
| `ExternalJobReference` | FK `workspace` (**`on_delete=SET_NULL`**) | **Apagado explicitamente antes** do workspace (ver §2) |
| `AuditEvent` | FK `workspace` (**`on_delete=SET_NULL`**) | **Apagado explicitamente antes** do workspace (ver §2) |
| Objectos MinIO | chave `workspaces/<workspace_id>/jobs/<job_id>/<ficheiro>` | `mc rm --recursive` sob o prefixo `workspaces/<workspace_id>/` |

**Nunca tocado** (dados globais/partilhados, sem FK para `workspace`):
`Permission`, `Role` de sistema (`workspace=None`), `Template`,
`ContentPack`, `ContentPackTemplate` — confirmado por leitura directa dos
modelos, não por suposição.

## 2. Achado crítico de leitura de código (evitou um bug real)

`Workspace` (e `Campaign`/`Artist`/`Track`/`Asset`) são `SoftDeleteModel`: o
seu manager **default** (`.objects`) sobrepõe `.delete()` para só marcar
`deleted_at` — **nunca remove a linha nem despoleta uma cascata real**. Um
`Workspace.objects.filter(id=X).delete()` "ingénuo" teria deixado os dados
todos na base de dados, com `deleted_at` preenchido, sem cascata nenhuma —
exactamente o oposto do que este prompt pede.

**Correcção aplicada:** o comando usa
`Workspace.all_objects.filter(id=workspace.id).hard_delete()` — o método
real (`SoftDeleteQuerySet.hard_delete()` → `super().delete()`), que
desencadeia a cascata `CASCADE` real do Django/PostgreSQL.

Um segundo achado, já antecipado por leitura de código antes de qualquer
teste: `ExternalJobReference` e `AuditEvent` apontam para `workspace` com
`on_delete=SET_NULL` — um simples `workspace.delete()` (mesmo hard) **não os
apaga**, só lhes põe `workspace_id=NULL`, tornando-os órfãos e
indetectáveis por `workspace_id` a partir desse momento. O comando
apaga-os **explicitamente antes** de apagar o workspace, dentro da mesma
transacção atómica.

## 3. Estratégia implementada

Combinação (opção explicitamente permitida pelo prompt):

1. **Management command Django** — `backend_core/apps/core/management/commands/cleanup_e2e_run.py`.
   Resolve o workspace/utilizador exactos do run-id (por email e nome de
   workspace, os mesmos que `seed_e2e_run` cria), conta tudo, e — só se
   confirmado — apaga tudo numa única transacção atómica. Nunca toca em
   MinIO (sem dependências Python de S3 no Backend Core).
2. **Script PowerShell** — `scripts/cleanup-e2e-run.ps1`. Chama o
   management command (dry-run sempre primeiro, para pré-visualização),
   depois, se confirmado, remove os objectos MinIO sob
   `workspaces/<workspace_id>/` com credenciais **root** (o utilizador de
   serviço `chartrex_renderer`, STG-HARD-003, não tem `s3:ListBucket` nem
   `s3:DeleteObject` — de propósito, não é ele que faz cleanup).

## 4. Segurança do comando (por desenho)

- **`--run-id` vazio ou só espaços é sempre rejeitado** (`CommandError`,
  testado).
- **Um run-id que não corresponda a nada não é erro** — `"found": false`,
  exit 0 (idempotente).
- **Confirmação explícita antes de apagar de facto**: sem `--dry-run`, o
  comando pede para **escrever o run-id de volta** (mesmo padrão do
  `staging-local-infra-reset.ps1`, a uma escala muito menor); `--yes`
  salta o prompt para uso não-interactivo (CI local).
- **Dry-run mostra contagens e o `workspace_id`, nunca um segredo** — o
  comando nunca lê `E2E_PASSWORD`/tokens/credenciais MinIO.
- **Verificação cruzada de posse**: se workspace e utilizador existirem mas
  não pertencerem um ao outro (`workspace.created_by != user`), o comando
  recusa-se a adivinhar e levanta `CommandError` sem apagar nada — testado
  com uma colisão artificial (§7).
- **Reset destrutivo continua completamente separado** —
  `staging-local-infra-reset.ps1` não foi alterado; este cleanup nunca
  chama `docker compose down -v` nem qualquer equivalente.

## 5. Ficheiros criados/alterados

| Ficheiro | Operação |
|---|---|
| `backend_core/apps/core/management/commands/cleanup_e2e_run.py` | **criado** |
| `backend_core/apps/core/tests/test_cleanup_e2e_run.py` | **criado** — 10 testes |
| `scripts/cleanup-e2e-run.ps1` | **criado** |
| `frontend/docs/.../06_staging_infraestrutura_real_local/runbook_staging_local.md` | Nova secção **§17.1** (cleanup por run-id, distinta do reset em §17); §5 (tabela de scripts) actualizada |
| `frontend/docs/.../07_staging_local_hardening/resultados_execucao/prompt_04_cleanup_run_id_resultado.md` | **criado** (este relatório) |

Nenhum ficheiro de secrets (`*.env.staging.local`) foi alterado — este
cleanup só lê credenciais já existentes (root MinIO, para a limpeza de
objectos), nunca as imprime.

## 6. Testes automatizados

| Teste | Resultado |
|---|---|
| `test_rejects_empty_run_id` | ✅ |
| `test_rejects_whitespace_only_run_id` | ✅ |
| `test_nonexistent_run_id_is_a_no_op_not_an_error` | ✅ |
| `test_dry_run_deletes_nothing` | ✅ |
| `test_real_cleanup_removes_the_full_namespaced_dataset` (inclui `CampaignAction`, `ExternalJobReference`, `AuditEvent` criados manualmente para exercitar os dois caminhos de cascata) | ✅ |
| `test_other_run_id_is_untouched` | ✅ |
| `test_rerun_after_cleanup_reseeds_cleanly` | ✅ |
| `test_interactive_confirmation_mismatch_aborts_without_deleting` | ✅ |
| `test_interactive_confirmation_match_deletes` | ✅ |
| `test_mismatched_ownership_refuses_to_guess` | ✅ |

**10/10 `PASS`** contra SQLite (dev) e novamente **10/10 `PASS`** contra
PostgreSQL real. Suites relacionadas revalidadas sem regressão: `apps/core
apps/workspaces apps/campaigns apps/catalogue apps/campaign_actions
apps/reports apps/content apps/audit` → **291 passed, 3 skipped** (os 3
skips são testes opt-in de Intelligence Engine real, pré-existentes, não
relacionados). `manage.py check` → sem problemas.

## 7. Validação de isolamento contra a stack real

Dois run-ids seedados (`seed_e2e_run`), cada um com um media kit real criado
via HTTP (Backend Core → Content Renderer → MinIO), exactamente o mesmo
padrão usado nos smoke tests dos prompts anteriores desta fase:

| Run-id | Papel | Workspace |
|---|---|---|
| `stghard006keep` | preservar | `3d212b26-...` |
| `stghard006remove` | limpar | `4145558e-...` |

**Antes do cleanup** — confirmado por `mc ls --recursive`, ambos os
workspaces com 1 objecto MinIO cada (`media_kit.pdf`).

**Dry-run para `stghard006remove`:** contagens correctas (1 campanha, 1
artista, 1 media kit, 1 external job, 4 audit events, 1 asset, 1
utilizador; 1 objecto MinIO) — confirmado que nada foi alterado (reconfirmado
por `mc ls` a seguir, objecto ainda lá).

**Cleanup real (`-Force`, não-interactivo) para `stghard006remove`:**
PostgreSQL limpo com sucesso; objecto MinIO
(`workspaces/4145558e.../jobs/.../media_kit.pdf`) removido, confirmado pela
própria saída do `mc rm`.

**Isolamento confirmado:**
- Dry-run pós-cleanup de `stghard006remove` → `"found": false` (nada resta).
- Dry-run de `stghard006keep` → **todos os dados intactos** (mesmas
  contagens de antes: 1 campanha, 1 artista, 1 media kit, 1 external job, 4
  audit events, 1 asset, 1 utilizador, 1 objecto MinIO).

**Reseed depois do cleanup:** `seed_e2e_run --run-id=stghard006remove`
executado de novo com sucesso, workspace novo e diferente do apagado
(`360f51d7-...` ≠ `4145558e-...`) — confirma que o cleanup não deixa
nenhum estado (constraint `unique`, registo órfão) que impeça reutilizar o
mesmo run-id.

Todos os dados de teste desta validação (`stghard006keep`,
`stghard006remove` reseedado) foram limpos com o próprio
`cleanup-e2e-run.ps1` no final, deixando a stack no estado em que estava
antes desta iteração.

## 8. Consistência PostgreSQL/MinIO

Consistente por desenho: o script só tenta limpar MinIO **depois** de o
PostgreSQL confirmar sucesso (se o `manage.py cleanup_e2e_run` falhar ou for
cancelado pelo operador, o script sai sem tocar em MinIO — nunca haveria um
estado "MinIO limpo, Postgres não", que seria pior que o inverso, já que o
`workspace_id` só é conhecido através do Postgres). O caminho inverso
(Postgres limpo, MinIO falha a limpar — ex.: MinIO em baixo) é possível e
está **documentado, não escondido**: o script imprime um aviso explícito
("PostgreSQL já está limpo — este aviso não é revertível automaticamente")
e termina com `exit 0` (o Postgres já está correcto; a limpeza de MinIO pode
ser repetida manualmente mais tarde apontando ao mesmo `workspace_id`,
impresso no output).

## 9. Critérios de aceitação — verificação

- ✅ Existe cleanup seguro por run-id (management command + script).
- ✅ run-id vazio é rejeitado (`CommandError`, testado).
- ✅ Cleanup não apaga dados de outras execuções (validado com 2 run-ids
  reais contra a stack).
- ✅ MinIO e PostgreSQL ficam consistentes (ver §8) — limitação clara para
  o único caso assimétrico possível (MinIO falha depois de Postgres já
  limpo).
- ✅ Reset destrutivo continua separado (`staging-local-infra-reset.ps1`
  inalterado).
- ✅ Runbook actualizado (§17.1 nova, §5 tabela de scripts).
- ✅ Testes passam (10/10 novos + 291/291 relacionados).

Nenhum critério de rejeição ocorreu: nenhum volume foi apagado como cleanup
normal, nenhum dado fora do run-id foi tocado, nenhuma limpeza correu sem
confirmação, nenhum script contém segredos, `seed_e2e_run`/reseed continuam
a funcionar, e o único estado potencialmente inconsistente (MinIO falhar
depois do Postgres já limpo) está documentado, não escondido.

## 10. Limitações / riscos remanescentes

| Item | Severidade | Nota |
|---|---|---|
| Limpeza de MinIO depende do MinIO estar acessível no momento da chamada | Baixo | Se estiver em baixo, o script avisa e termina `exit 0` (Postgres já limpo); reexecutar mais tarde é seguro (idempotente) |
| A pré-contagem de objectos MinIO no dry-run depende de `docker run` funcionar (rede `chartrex_staging_local`, container MinIO respondendo) | Baixo | Falha graciosamente (mostra "não foi possível pré-contar"), não bloqueia o dry-run do Postgres |
| Comando não tem um modo "listar todos os run-ids existentes" | Baixo | Fora do âmbito pedido; o operador precisa de já saber o run-id (normal, é o mesmo requisito de `seed_e2e_run`) |
| RBAC/`Role` workspace-scoped (raro, nenhum criado por `seed_e2e_run` hoje) cascata correctamente, mas não foi exercitado por um teste dedicado | Muito baixo | Coberto pela mesma cascata `WorkspaceOwnedModel`/`CASCADE` já validada para os outros modelos; risco teórico, não observado |

## 11. Próximo passo recomendado

1. Seguir para **STG-HARD-001** (E2E, ainda com execução real pendente) ou
   **STG-HARD-007** (diagnóstico/artefactos), conforme prioridade.
2. Considerar, numa iteração futura, um modo `--all-e2e` que liste (não
   apague) todos os workspaces com nome a começar por `"E2E Workspace "` —
   útil para auditoria de acumulação, sem tornar isso um cleanup em massa
   por defeito (continuaria a exigir um `--run-id` explícito para apagar).
3. Nenhuma acção adicional necessária sobre o achado do §2
   (soft-delete vs hard-delete) — já corrigido e testado; vale a pena
   mantê-lo em mente para qualquer futuro comando que apague `Workspace`
   directamente.
