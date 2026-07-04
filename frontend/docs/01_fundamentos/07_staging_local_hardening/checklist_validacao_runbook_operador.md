# Checklist de validação do runbook por um segundo operador

**Fase:** `07_staging_local_hardening` (STG-HARD-004)
**Como usar:** entregar só este ficheiro + o runbook
(`../06_staging_infraestrutura_real_local/runbook_staging_local.md`) a um
operador sem contexto prévio desta fase. Nenhuma explicação verbal deve ser
necessária — se for, isso é uma ambiguidade a corrigir no runbook, não a
resolver de viva voz. Marcar cada linha com o resultado real; escrever
qualquer dúvida na coluna "Notas", mesmo que pareça trivial.

| # | Passo (secção do runbook) | Comando | Resultado esperado | OK? | Notas/dúvidas |
|---|---|---|---|---|---|
| 1 | Pré-requisitos (§1) | `docker info` | Sem erro | | |
| 2 | Pré-requisitos (§1) | Confirmar `pwsh -v` ≥ 7 | Versão 7+ | | |
| 3 | Env local (§4) | Copiar `.env.staging.local.example` → `.env.staging.local` (raiz) | Ficheiro criado | | |
| 4 | Env local (§4) | Criar os 3 `.env.staging.local` de serviço a partir dos `.env.example` respectivos, com os overrides da tabela de §4 | 3 ficheiros criados, `INTERNAL_API_TOKEN` idêntico nos 3 | | |
| 5 | Start infra (§6) | `staging-local-infra-up.ps1` | Containers `healthy`, bucket criado | | |
| 6 | Start apps (§7) | `staging-local-apps-up.ps1` | 4 serviços `saudável` | | |
| 7 | Health (§8) | `staging-local-health.ps1 -RequireApps` | `RESULTADO: OK` | | |
| 8 | Migrations/check (§9) | `manage.py check` + `showmigrations` + `migrate` (com `Import-DotEnvFile -Required:$true`) | 0 erros, todas migrations `[X]` | | |
| 9 | Seeds (§10) | `seed_rbac`/`seed_billing`/`seed_content` | Sem erro | | |
| 10 | `seed_e2e_run` (§10) | `manage.py seed_e2e_run --run-id <id>` | Uma linha JSON com `workspace_id`/`campaign_id` | | |
| 11 | Smoke básico | `curl http://127.0.0.1:8100/api/v1/system/health/ready/` | `200 {"status":"ok",...}` | | |
| 12 | Quality gate (parcial) | `staging-local-quality-gate.ps1 -Only backend_core_check,forbidden_ports,secrets_grep` | 3/3 `PASS` | | |
| 13 | Quality gate (completo) | `staging-local-quality-gate.ps1` | 9/9 `PASS` (~15-20 min) | | |
| 14 | E2E (§12) — só se a stack estiver activa | `staging-local-quality-gate.ps1 -WithE2E` (carrega o env do `backend_core` antes — ver §12) | 12/12 `PASS` | | |
| 15 | Diagnóstico E2E (§12.1) — só se algum teste falhar no passo 14 | Abrir `frontend/playwright-report/index.html` | Screenshot/trace/`e2e-diagnostics` visíveis para o teste falhado | | |
| 16 | Cleanup por run-id (§17.1) | `cleanup-e2e-run.ps1 -RunId <id-do-passo-10> -DryRun` | Mostra contagens, não apaga nada | | |
| 17 | Cleanup por run-id (§17.1) | `cleanup-e2e-run.ps1 -RunId <id-do-passo-10>` | Pede para escrever o run-id, depois limpa | | |
| 18 | Stop apps (§16) | `staging-local-apps-down.ps1` | Processos parados, portas libertas | | |
| 19 | Stop infra (§16) | `staging-local-infra-down.ps1` | Containers parados, **volumes preservados** | | |
| 20 | Reset destrutivo (§17) — **só leitura, nunca executar sem autorização explícita e separada** | Ler o script, não correr | Confirmar que exige `-IAmSure` + escrever "apagar"; **não executar** nesta validação | | |

## Registo de execução

**Segundo operador disponível nesta iteração?** _(preencher: sim/não)_

**Se sim** — nome/identificação do operador, data, máquina usada (SO,
versão Docker/PowerShell), e o resultado linha a linha da tabela acima.

**Se não** — esta checklist fica como pacote pronto a entregar. Nenhuma
linha acima foi marcada como "validada por terceiro" nem deve ser
interpretada como tal.

## Regras para quem preencher isto

- Nunca escrever um valor real de `E2E_PASSWORD`, `INTERNAL_API_TOKEN`,
  `DB_PASSWORD`, `MINIO_ROOT_PASSWORD`/`MINIO_RENDERER_PASSWORD` nesta
  tabela nem no relatório — só confirmar "definido"/"sincronizado".
- Uma dúvida "resolvida" por alguém a explicar em voz alta, sem escrever a
  correcção no runbook, **não conta como resolvida** — tem de virar uma
  edição real do runbook.
- Um comando que falhou e foi "contornado" sem se perceber porquê deve
  ficar registado como falha, não como sucesso silencioso.
