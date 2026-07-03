# Prompt 03 — Migrar Backend Core para PostgreSQL local persistente — Resultado

**Data:** 2026-07-02 / 2026-07-03
**Fase:** `06_staging_infraestrutura_real_local` (STG-LOCAL-003)
**Âmbito:** configurar e validar o Backend Core contra o container PostgreSQL da fase (não descartável, com volume), substituindo SQLite no staging local. Sem alterar lógica de produto.
**Estado de execução:** `executado` — Backend Core a arrancar com `DB_ENGINE=postgres` contra o container, 32 migrations aplicadas, 4 seeds executados, smoke API real cobrindo os 9 itens pedidos, 311 testes automatizados verdes contra PostgreSQL, persistência confirmada após restart real do container, backup/restore validado de facto.

---

## 1. Nota sobre o caminho da pasta

Como nos Prompts 01/02, os documentos desta execução foram criados em
`frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/`, a pasta
real do repositório.

## 2. Configuração usada (sem valores secretos)

Criado `backend_core/.env.staging.local` (ignorado pelo git —
`backend_core/.gitignore: .env.*`, confirmado com `git check-ignore`), **não
tocando** no `backend_core/.env` existente do developer (que continua
`DB_ENGINE=sqlite`, intacto). As variáveis são carregadas por
`set -a && . ./.env.staging.local && set +a` antes de cada comando
(`python-decouple` dá prioridade a `os.environ` sobre o `.env` versionado —
confirmado por leitura do código-fonte de `decouple.Config.get`).

| Variável | Valor usado nesta validação |
|---|---|
| `DEBUG` | `True` |
| `DB_ENGINE` | `postgres` |
| `DB_NAME` | `chartrex_staging` |
| `DB_USER` | `chartrex_staging` |
| `DB_PASSWORD` | *(não impresso — placeholder de dev já público em `docker-compose.staging.local.yml`, ver §7 "Riscos")* |
| `DB_HOST` | `127.0.0.1` |
| `DB_PORT` | **`5433`** (override — ver §7, LOCAL-R02 materializou-se nesta máquina) |
| `INTELLIGENCE_ENGINE_ENABLED` / `_DRY_RUN` | `true` / `true` (IE não arrancado nesta validação — fora do âmbito deste prompt) |
| `EXTERNAL_JOBS_ENABLED` / `_DRY_RUN` | `true` / `true` (Content Renderer não arrancado nesta validação — fora do âmbito deste prompt) |
| `E2E_PASSWORD` | gerado localmente com `secrets.token_urlsafe`, guardado só no ficheiro ignorado, nunca impresso |

Nenhum valor de `DB_PASSWORD` ou `E2E_PASSWORD` foi impresso em nenhum
comando, log ou neste relatório, conforme a regra explícita do prompt.

## 3. Migrations

```text
python manage.py check          → System check identified no issues (0 silenced).
python manage.py showmigrations → 32 migrations, todas [ ] (DB nova, antes do migrate)
python manage.py migrate        → 32/32 aplicadas com sucesso, 0 erros
```

Apps migradas: `contenttypes`, `auth`, `accounts`, `admin`, `workspaces`,
`rbac`, `audit`, `billing`, `core`, `catalogue`, `campaigns`, `reports`,
`content`, `campaign_actions`, `integrations_bridge`, `links`,
`notifications`, `sessions` — a mesma árvore de migrations do SQLite dev, sem
alteração de código.

## 4. Seeds

```text
seed_rbac    → RBAC seeded: 28 permissions, 7 roles (7 created).
seed_billing → Billing seeded: 7 plans, 63 features.
seed_content → Content seeded: 6 templates, 4 packs.
seed_e2e_run --run-id stg-local-003 → JSON com run_id, email, workspace_id, artist_id, campaign_id (idempotente — reexecutado 2x, mesmo workspace/campaign reutilizado)
```

Os 4 comandos pedidos correram sem erro contra o PostgreSQL do container.

## 5. Smoke API (real, HTTP contra `127.0.0.1:8100`)

Backend Core arrancado com `manage.py runserver 127.0.0.1:8100 --noreload`
contra o PostgreSQL do container. Todos os 9 itens pedidos validados com
pedidos HTTP reais (não apenas leitura de código):

| Item | Método/Endpoint | Resultado |
|---|---|---|
| auth (login) | `POST /api/v1/auth/token/` | `200`, `access`+`refresh` presentes |
| auth/me | `GET /api/v1/auth/me/` | `200`, perfil do utilizador seed_e2e_run |
| workspaces | `GET /api/v1/workspaces/` | `200`, 1 workspace (seed_e2e_run) |
| campaigns | `GET /api/v1/campaigns/` | `200`, 1 campaign (seed_e2e_run) |
| campaign-actions | `POST /api/v1/campaign-actions/` (`action_type=manual_task`) | `201` — criado sem exigir `recommendation_ref` (regra já documentada na fase 05: obrigatório só para acções não-manuais) |
| reports | `POST /api/v1/reports/` | `201`, `status=queued`, `metadata.external_job_id` presente |
| media-kits | `POST /api/v1/media-kits/` | `201`, `metadata.external_job_id` presente |
| content-pack-requests | `POST /api/v1/content-pack-requests/` | `201`, `metadata.external_job_id` presente |
| external jobs | `ExternalJobReference.objects.all()` (via `manage.py shell`) | 3 registos, `status=submitted` (dry-run simulado, `EXTERNAL_JOBS_DRY_RUN=true` — IE/Renderer não arrancados neste prompt), um por artefacto criado acima |

**Achado real durante esta validação (não um bug de produto — ambiente
local):** o primeiro conjunto de tentativas de login falhou com `401 No
active account found`, apesar de `check_password`/`authenticate()`
confirmarem a credencial correcta via `manage.py shell`. Diagnóstico:
`Get-NetTCPConnection -LocalPort 8100` revelou um processo Python **anterior
e não relacionado** já vinculado à porta 8100 (provavelmente uma instância
de `runserver` esquecida de uma sessão de trabalho anterior, a usar SQLite),
respondendo silenciosamente a todos os pedidos HTTP em vez do servidor
recém-arrancado contra PostgreSQL. Resolvido ao terminar os processos órfãos
(`Stop-Process`) e arrancar uma única instância limpa; confirmado por
`Get-NetTCPConnection` a mostrar um único PID depois. Sem isto, os testes de
smoke teriam produzido falsos negativos.

## 6. Persistência (validada duas vezes, de duas formas)

1. **Ciclo de infraestrutura vazio (Prompt 02):** `docker compose down` →
   `docker volume ls` confirma volumes → `docker compose up -d` → dados de
   sonda ainda presentes.
2. **Ciclo real com dados de produto (este prompt):** com `Report`,
   `CampaignAction`, `User` e `ExternalJobReference` já criados via smoke
   API, executei `docker compose stop postgres` seguido de
   `docker compose start postgres` (reinício real do container, não apenas
   do compose todo) e reconfirmei via `manage.py shell`:

```text
reports=1  campaign_actions=1  users=1
report_title=STG-LOCAL-003 smoke report
```

Todos os registos sobreviveram ao restart do container, confirmando que o
volume nomeado `chartrex_staging_postgres_data` é a persistência real, não
um efeito acidental de o container nunca ter parado.

## 7. Backup/restore local (documentado e validado de facto)

```powershell
# --- Backup (pg_dump, formato custom, comprimido) ---
docker exec -e PGPASSWORD=<password> chartrex_staging_postgres `
  sh -c "pg_dump -h 127.0.0.1 -U chartrex_staging -d chartrex_staging -F c -f /tmp/chartrex_staging_backup.dump"

# Copiar o dump para o host, se necessário:
docker cp chartrex_staging_postgres:/tmp/chartrex_staging_backup.dump ./chartrex_staging_backup.dump

# --- Restore (para uma base de dados nova — nunca sobre a base viva sem confirmação) ---
docker exec -e PGPASSWORD=<password> chartrex_staging_postgres `
  psql -h 127.0.0.1 -U chartrex_staging -d postgres -c "CREATE DATABASE <nome_destino> OWNER chartrex_staging;"
docker exec -e PGPASSWORD=<password> chartrex_staging_postgres `
  pg_restore -h 127.0.0.1 -U chartrex_staging -d <nome_destino> /tmp/chartrex_staging_backup.dump

# --- Backup de volume (alternativa ao nível do Docker, cobre todo o cluster) ---
docker run --rm -v chartrex_staging_postgres_data:/data -v ${PWD}:/backup alpine `
  tar czf /backup/chartrex_staging_postgres_data.tar.gz -C /data .

# =====================================================================
# RESET DESTRUTIVO — apaga TODOS os dados do PostgreSQL e do MinIO.
# Comando já documentado no Prompt 02, repetido aqui por completude:
# =====================================================================
docker compose -f docker-compose.staging.local.yml down -v
```

**Validado de facto nesta iteração** (não apenas escrito): `pg_dump` real →
ficheiro `.dump` de 239 291 bytes → `pg_restore` real para uma base de dados
`chartrex_staging_restore_test` isolada → `SELECT title FROM
reports_report` devolveu `STG-LOCAL-003 smoke report`, confirmando o
round-trip completo. A base de dados de teste e o ficheiro de dump foram
removidos no final (`DROP DATABASE`, `rm`) — a base de dados real
(`chartrex_staging`) nunca foi tocada por este teste.

Nota de plataforma: em git-bash/MSYS no Windows, caminhos como `/tmp/...`
passados como argumento a `docker exec` são reescritos para um caminho
Windows por conversão automática de path — usar `MSYS_NO_PATHCONV=1` antes
do comando quando o caminho se destina ao *interior* do container.

## 8. Ficheiros criados/alterados

| Ficheiro | Operação |
|---|---|
| `backend_core/.env.staging.local` | **criado** (ignorado pelo git — confirmado); contém `DB_*` apontando para o container, `E2E_PASSWORD` gerado localmente |
| `frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/resultados_execucao/prompt_03_postgresql_local_resultado.md` | **criado** (este relatório) |

Nenhum ficheiro de código de produto foi alterado. `backend_core/.env` (o
`.env` de desenvolvimento existente, SQLite) e `backend_core/db.sqlite3` **não
foram tocados**, conforme a regra explícita do prompt.

## 9. Validações executadas

| Validação | Resultado |
|---|---|
| `python manage.py check` | ✅ 0 issues |
| `python manage.py showmigrations` | ✅ 32 migrations listadas, todas aplicadas após o `migrate` |
| `python manage.py migrate` | ✅ 32/32 OK, 0 erros |
| `pytest apps/campaign_actions` | ✅ **61/61 passed** (150.36s) contra PostgreSQL |
| `pytest apps/reports apps/content apps/integrations_bridge` | ✅ **250/250 passed** (497.94s) contra PostgreSQL, após limpar uma `test_chartrex_staging` órfã de uma execução anterior interrompida (ver nota abaixo) |
| Smoke API (9 itens) | ✅ Todos `200`/`201` reais, ver §5 |
| Persistência após restart real do container | ✅ Confirmada com dados de produto, ver §6 |
| Backup/restore (`pg_dump`/`pg_restore`) | ✅ Round-trip real validado, ver §7 |
| Grep de `password\|secret\|token\|api_key\|private_key` neste relatório | ✅ Só nomes de variável e placeholders de comando (`<password>`, `<nome_destino>`) — nenhum valor real |
| `git check-ignore -q backend_core/.env.staging.local` | ✅ ignorado |

**Nota operacional (não um bug de produto):** a primeira tentativa de correr
o segundo bloco de `pytest` em background ficou órfã (processo Python
sobrevivente a uma interrupção da sessão), deixando uma sessão
`idle in transaction` presa a `test_chartrex_staging` e bloqueando
`DROP DATABASE`/recriação pelo runner seguinte. Diagnosticado via
`pg_stat_activity`, resolvido ao identificar e terminar o processo órfão
(`Get-CimInstance Win32_Process` + `Stop-Process`) e ao limpar a base de
dados de teste presa (`pg_terminate_backend` + `DROP DATABASE`) antes de
voltar a correr a suite, que passou limpa. Registado como risco operacional
de ambientes locais long-running, não como falha de migração/configuração.

## 10. Riscos

| Risco | Situação após este prompt |
|---|---|
| **LOCAL-R02 — Porta 5432 ocupada** | **Materializou-se de facto nesta máquina**: um serviço Windows nativo `postgresql-x64-18` já estava a ouvir em `127.0.0.1:5432` (confirmado via `Get-NetTCPConnection` + `Get-Process`), fazendo o Backend Core autenticar-se contra o Postgres errado (erro `password authentication failed`, uma mensagem genérica do Postgres para credenciais desconhecidas). Mitigado exactamente como previsto na arquitectura (Prompt 01, §5/§13): container recriado com `POSTGRES_PORT=5433`, `backend_core/.env.staging.local` actualizado para `DB_PORT=5433`. Nenhuma alteração ao serviço Windows nativo — não foi tocado. |
| Processos `runserver`/`pytest` órfãos de sessões anteriores a mascarar resultados | **Materializou-se duas vezes nesta máquina** (porta 8100 e ligação presa a `test_chartrex_staging`) — ver §5 e §9. Mitigado por diagnóstico via `Get-NetTCPConnection`/`Get-CimInstance Win32_Process` e `pg_stat_activity`; documentado aqui para o runbook futuro (STG-LOCAL-011) incluir esta verificação antes de declarar um smoke "falhado" prematuramente. |
| LOCAL-R08 — Dados acumulam em volumes locais | Sem alteração — este prompt criou dados reais (`Report`, `CampaignAction`, `User`) no volume persistente; o reset destrutivo documentado em §7 continua a via de limpeza, não executado nesta iteração. |
| Credenciais em `backend_core/.env.staging.local` | Ficheiro confirmado ignorado pelo git; valor de `DB_PASSWORD` nunca impresso nem escrito neste relatório. |

## 11. Próximo passo recomendado

Avançar para **STG-LOCAL-004** (Prompt 04 do pipeline): implementar e
validar o provider MinIO/S3-compatible no Content Renderer, usando o
container MinIO já disponível (Prompt 02) como destino de staging local dos
artefactos gerados a partir dos `Report`/`MediaKit`/`ContentPackRequest`
agora persistidos em PostgreSQL.
