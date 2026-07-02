# Prompt 02 — DB staging — Resultado

**Data:** 2026-07-02
**Fase:** `05_staging_operacionalizacao_pre_producao` (STG-PRE-002)
**Âmbito:** validar a migração do Backend Core de SQLite dev para PostgreSQL, sem quebrar CampaignActions, artefactos, jobs e callbacks. Sem alteração de lógica funcional de produto.
**Estado de execução:** `executado` (validação técnica completa contra PostgreSQL descartável; **cutover da instância de staging persistente não é âmbito deste prompt** — ver §8)

---

## 1. Resumo objectivo

A configuração de base de dados do Backend Core (`backend_core/config/settings.py`)
**já suporta PostgreSQL nativamente** via `DB_ENGINE=postgres` (branch já
implementado, `psycopg==3.3.4` já em `requirements.txt`). Não foi necessária
nenhuma alteração de código para activar o suporte — apenas validação.

Foi criada uma instância PostgreSQL 16 **descartável e isolada** (reutilizando
o padrão já existente em `content_renderer/docker-compose.e2e.yml`, dados em
tmpfs) e validado, ponta-a-ponta, sem tocar no `.env`/`db.sqlite3` de
desenvolvimento reais:

1. `python manage.py check` — OK.
2. `python manage.py migrate` — as 32 migrations de todas as 14 apps locais
   aplicaram-se sem erro numa base de dados PostgreSQL vazia.
3. Seed mínimo (`seed_rbac`, `seed_billing`, `seed_content` + um seed ad-hoc
   idempotente de user/workspace/artist/campaign) — executado com sucesso.
4. Smoke API real: login JWT, `/auth/me/`, `/workspaces/`, `/campaigns/`,
   `/campaign-actions/` (create), `/reports/` (create), `/media-kits/`
   (create), `/content-pack-requests/` (create) — todos `200`/`201`.
5. `pytest apps/campaign_actions` — **56/56 passed** contra PostgreSQL.
6. A instância descartável foi removida no fim (`docker compose down -v`);
   o ambiente de desenvolvimento (`.env`, `db.sqlite3`) ficou **intocado**.

**Conclusão:** o suporte a PostgreSQL está tecnicamente validado e pronto a
usar. O que falta para "staging formal" não é código — é **decidir e
provisionar uma instância PostgreSQL persistente** (não descartável) e apontar
lá o Backend Core de staging. Isso é uma decisão operacional/de topologia,
registada como pendente, não uma limitação de código.

---

## 2. DB alvo identificado

| Aspecto | Valor |
|---|---|
| Engine | **PostgreSQL** (16, testado; `config/settings.py` aceita qualquer versão suportada pelo driver `psycopg` 3.x) |
| Activação | `DB_ENGINE=postgres` no `.env` do Backend Core (já suportado, sem alteração de código) |
| Driver | `psycopg==3.3.4` (já em `requirements.txt`) |
| Precedente já existente no repositório | `content_renderer/docker-compose.e2e.yml` já usa `postgres:16-alpine` para o harness E2E do Content Renderer (dados em tmpfs, descartável) |
| Suporte a `DATABASE_URL` | **Não existe.** Não há `dj-database-url`/`django-environ` no `requirements.txt`; a configuração usa variáveis discretas (`DB_ENGINE`/`DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`) via `python-decouple`, consistente com o padrão do resto do projecto (todos os `.env.example` dos 4 serviços usam variáveis discretas, nenhum usa uma URL única). Ver decisão em §6. |

---

## 3. Variáveis necessárias (sem valores reais)

Já documentadas em `backend_core/.env.example` (nenhuma alteração necessária):

```dotenv
DB_ENGINE=postgres
DB_NAME=<nome_da_base_de_dados_staging>
DB_USER=<utilizador_staging>
DB_PASSWORD=<password_staging>      # segredo — nunca commitar o valor real
DB_HOST=<host_staging>
DB_PORT=5432
```

**Confirmação de ausência de credenciais hardcoded:** `config/settings.py`
lê todos os 6 valores exclusivamente via `config(...)` (python-decouple);
`DB_NAME`, `DB_USER`, `DB_PASSWORD` **não têm default** quando
`DB_ENGINE=postgres` — se não forem fornecidos, o arranque falha com
`UndefinedValueError` em vez de usar um valor inseguro. Só `DB_HOST`
(`localhost`) e `DB_PORT` (`5432`) têm default, e são configuração, não
segredos. O `.env.example` só contém os nomes das variáveis, nunca valores
reais.

---

## 4. Migrations — validadas

`python manage.py migrate` contra PostgreSQL 16 vazio aplicou, sem erro, as
migrations de todas as apps locais relevantes (mais Django/DRF/SimpleJWT):

| Área pedida | App | Migrations | Resultado |
|---|---|---|---|
| Users/auth | `accounts` | `0001_initial` | ✅ |
| Workspaces | `workspaces` | `0001_initial`, `0002_workspacemember_role_fk` | ✅ |
| Campaigns | `campaigns` | `0001_initial` | ✅ |
| CampaignActions | `campaign_actions` | `0001_initial` | ✅ |
| Reports (Report + MediaKit) | `reports` | `0001_initial` | ✅ |
| Content pack requests / outputs | `content` | `0001_initial` | ✅ |
| External job references | `integrations_bridge` | `0001_initial`, `0002_externaljobreference_callback_payload_and_more` | ✅ |
| Assets | `core` | `0001_initial` | ✅ |
| (adicional, dependências) | `rbac`, `catalogue`, `billing`, `audit`, `links`, `notifications` | `0001_initial` cada | ✅ |

`python manage.py showmigrations` confirmou `[X]` em todas as entradas antes
(SQLite dev) e depois (PostgreSQL) — nenhuma migration pendente em nenhum dos
dois motores.

---

## 5. Seed mínimo — criado e validado (idempotente)

Não existia nenhum seed que cobrisse **user/workspace/artist/campaign**; os
três seeds existentes (`seed_rbac`, `seed_billing`, `seed_content`) só cobrem
dados de sistema (roles/permissions, planos de billing, templates/packs) e
foram reutilizados sem alteração.

Executados por esta ordem contra a instância PostgreSQL de validação:

```powershell
python manage.py seed_rbac      # RBAC seeded: 28 permissions, 7 roles (7 created)
python manage.py seed_billing   # Billing seeded: 7 plans, 63 features
python manage.py seed_content   # Content seeded: 6 templates, 4 packs
```

Para o mínimo pedido (user dev/staging, workspace, artist, campaign) foi
escrito e executado um script ad-hoc **idempotente** (`get_or_create` em
todos os passos), via `manage.py shell < script.py`, e depois **apagado do
repositório** (não é um artefacto permanente — só o padrão fica documentado
aqui para reprodutibilidade):

```python
from apps.accounts.models import User
from apps.workspaces.models import Workspace, WorkspaceMember
from apps.rbac.models import Role
from apps.catalogue.models import Artist
from apps.campaigns.models import Campaign

user, _ = User.objects.get_or_create(
    email="stg-pre-dev@example.local",
    defaults={"full_name": "Staging Pre-Prod Dev", "is_active": True},
)
# definir password via user.set_password(<password>) fora do repositório

workspace, _ = Workspace.objects.get_or_create(
    slug="stg-pre-demo",
    defaults={"name": "STG-PRE Demo Workspace",
              "workspace_type": Workspace.WorkspaceType.ARTIST,
              "status": Workspace.Status.ACTIVE},
)

owner_role = Role.objects.filter(key="owner").first()
WorkspaceMember.objects.get_or_create(
    workspace=workspace, user=user,
    defaults={"role": owner_role, "role_key": "owner",
              "status": WorkspaceMember.Status.ACTIVE},
)

artist, _ = Artist.objects.get_or_create(
    workspace=workspace, slug="stg-pre-demo-artist",
    defaults={"name": "STG-PRE Demo Artist", "status": Artist.Status.ACTIVE},
)

Campaign.objects.get_or_create(
    workspace=workspace, artist=artist, name="STG-PRE Demo Campaign",
    defaults={"campaign_type": Campaign.CampaignType.SINGLE_RELEASE,
              "status": Campaign.Status.ACTIVE},
)
```

**Idempotência confirmada:** o script foi executado duas vezes; na segunda
execução todos os `created=False` com os mesmos IDs — nenhum duplicado.

**Recomendação (backlog complementar, não implementada nesta iteração):**
se um seed de demo/staging for necessário com frequência (nomeadamente para
o E2E automatizado de STG-PRE-009), vale a pena promovê-lo a um management
command próprio (`seed_staging_demo`), seguindo o padrão exacto de
`seed_rbac`/`seed_billing`/`seed_content`. Não foi feito aqui para não
introduzir uma peça de código nova nesta iteração focada em DB, mas fica
registado para o Prompt 09.

---

## 6. Suporte a `DATABASE_URL` — decisão

**Não implementado nesta iteração.** O projecto usa consistentemente
variáveis discretas (`DB_ENGINE`/`DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/
`DB_PORT`) nos 4 serviços, sem nenhuma dependência tipo `dj-database-url` ou
`django-environ`. Introduzir suporte a uma única variável `DATABASE_URL`
exigiria uma dependência nova só para uma conveniência sintáctica, sem
resolver nenhum bloqueio real — as variáveis discretas já são suficientes e
já foram validadas. Registado como **melhoria técnica opcional e não
bloqueante**, não como pendência crítica.

---

## 7. Dependência de driver — nota operacional (não é alteração de código)

`psycopg==3.3.4` (o pacote "puro", sem extensões pré-compiladas) depende da
biblioteca nativa `libpq`. Nesta máquina de validação (Windows, sem
PostgreSQL client tools instalado), `import psycopg` falhava com
`ImportError: no pq wrapper available` até se instalar `psycopg[binary]`
(mesma versão) **apenas na venv local**, sem alterar `requirements.txt`.

- Isto **não é uma alteração de código nem de dependência do repositório** —
  foi só um passo local de preparação de ambiente para conseguir correr a
  validação nesta máquina Windows.
- **Nota para o runbook (STG-PRE-010):** máquinas de staging real (tipicamente
  Linux) costumam ter `libpq5`/`libpq-dev` disponível via gestor de pacotes do
  SO, ou podem instalar `psycopg[binary]` para evitar essa dependência de
  sistema. Em Windows local, `psycopg[binary]` é a via mais simples. Registar
  esta nota no runbook de troubleshooting de DB.

---

## 8. Smoke API — executado contra PostgreSQL

Servidor de validação arrancado numa porta dedicada (não 8100, para não
colidir com o ambiente de dev real) com `DB_ENGINE=postgres` só nas
variáveis de ambiente do processo (nunca escritas no `.env` versionado nem
no `.env` de dev real, que permaneceu com `DB_ENGINE=sqlite` inalterado).

| Passo | Endpoint | Resultado |
|---|---|---|
| Auth (login JWT) | `POST /api/v1/auth/token/` | ✅ `200`, `access`+`refresh` presentes |
| Perfil | `GET /api/v1/auth/me/` | ✅ `200` |
| Workspace | `GET /api/v1/workspaces/` | ✅ `200`, 1 resultado (seed) |
| Campaign | `GET /api/v1/campaigns/` | ✅ `200`, 1 resultado (seed) |
| CampaignAction | `GET` + `POST /api/v1/campaign-actions/` | ✅ `200` (lista vazia) → `201` (criação `manual_task`) |
| Report | `POST /api/v1/reports/` | ✅ `201`, `status=queued`, `ExternalJobReference` criado (`job_type=report_generation`) |
| MediaKit | `POST /api/v1/media-kits/` | ✅ `201`, `status=draft`, `ExternalJobReference` criado (`job_type=media_kit_generation`) |
| ContentPackRequest | `POST /api/v1/content-pack-requests/` | ✅ `201`, `status=queued`, `ExternalJobReference` criado (`job_type=content_generation`), `usage_event_id` gerado (hook de billing) |
| External jobs | `ExternalJobReference` (via shell) | ✅ 3 jobs persistidos com `provider`/`job_type` correctos |

**Nota honesta sobre os jobs (não é falha de PostgreSQL):** os 3 jobs ficaram
em `status=submitted` porque o Content Renderer já estava a correr nesta
máquina (de uma sessão anterior) com `BACKEND_CORE_BASE_URL` a apontar para
o Backend Core principal (`:8100`, SQLite), não para o servidor de validação
efémero desta iteração (porta dedicada). O callback nunca chegou a este
servidor de validação — comportamento esperado dado o desalinhamento de
portas entre o processo de validação e o Content Renderer já activo, **não**
uma falha de escrita/leitura em PostgreSQL. A criação do job, a persistência
do `ExternalJobReference` com FKs correctas (`campaign`, `workspace`,
`content_type`/`object_id` do artefacto relacionado) e o hook de billing
(`usage_event_id`) confirmam que o modelo de dados de jobs funciona
correctamente em PostgreSQL. O Backend Core principal (`:8100`) não estava a
correr durante este teste, pelo que **não houve nenhum efeito no ambiente de
desenvolvimento real** (o Content Renderer só recebeu uma tentativa de
callback recusada por "connection refused", sem persistir nada indevido).

---

## 9. `pytest apps/campaign_actions` — 56/56 contra PostgreSQL

```text
56 passed, 56 warnings in 79.36s
```

Executado com `DB_ENGINE=postgres` apontando à mesma instância descartável
(o `pytest-django` cria e destrói a sua própria base de dados de teste,
isolada da base `chartrex_e2e` usada no smoke API). Nenhum teste alterado.

---

## 10. Backup / rollback básico (staging)

**Backup** (uma instância PostgreSQL de staging real, não a descartável
usada nesta validação):

```powershell
pg_dump -h <DB_HOST> -U <DB_USER> -d <DB_NAME> -F c -f backup_staging_<data>.dump
```

**Restore:**

```powershell
pg_restore -h <DB_HOST> -U <DB_USER> -d <DB_NAME> --clean --if-exists backup_staging_<data>.dump
```

**Rollback de migration** (uma app específica, para o estado anterior):

```powershell
python manage.py migrate <app_label> <migration_anterior>
# ex.: python manage.py migrate campaign_actions zero   # desfaz tudo da app
```

**Regras para staging:**
- Nunca correr `migrate` directamente contra uma instância partilhada sem
  backup recente.
- `pg_dump`/`pg_restore` nunca devem incluir a password na linha de comandos
  documentada — usar `~/.pgpass` ou `PGPASSWORD` como variável de ambiente
  não persistida em histórico de shell.
- Para o harness descartável (`docker-compose.e2e.yml`), não se aplica
  backup — os dados são tmpfs e intencionalmente perdidos ao parar o
  container; não usar este harness para dados que precisem de persistir.

---

## 11. Ficheiros criados / alterados

| Ficheiro | Operação |
|---|---|
| `frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/arquitectura_staging_pre_producao.md` | **alterado** — 2 linhas actualizadas (§10 limites conhecidos, §11 decisões pendentes) para reflectir que o DB foi validado tecnicamente nesta iteração, sem declarar staging formal cortado |
| `frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/resultados_execucao/prompt_02_db_staging_resultado.md` | **criado** (este relatório) |
| `backend_core/.env` | **não alterado** (validação usou variáveis de ambiente do processo, nunca escritas no ficheiro) |
| `backend_core/db.sqlite3` | **não alterado** |
| `backend_core/requirements.txt` | **não alterado** |
| `backend_core/_seed_staging_demo.py` (script ad-hoc temporário) | **criado e depois apagado** — não ficou no repositório; conteúdo preservado em §5 deste relatório |
| Container Docker `chartrex_e2e_postgres` (via `content_renderer/docker-compose.e2e.yml`, reutilizado sem alteração) | **criado e depois removido** (`docker compose down -v`) — dados em tmpfs, nada persistido |
| venv local (`backend_core/venv`) | `psycopg[binary]==3.3.4` instalado localmente para permitir a validação nesta máquina Windows — **não versionado** (`venv/` está no `.gitignore`), não afecta `requirements.txt` |

---

## 12. Validações executadas

| Validação | Resultado |
|---|---|
| `python manage.py check` (SQLite, baseline) | ✅ 0 issues |
| `python manage.py check` (PostgreSQL) | ✅ 0 issues |
| `python manage.py showmigrations` (SQLite, baseline) | ✅ todas `[X]` |
| `python manage.py showmigrations` (PostgreSQL, antes do migrate) | ✅ todas `[ ]` (base vazia, como esperado) |
| `python manage.py migrate` (PostgreSQL) | ✅ 32 migrations aplicadas sem erro |
| `seed_rbac` / `seed_billing` / `seed_content` (PostgreSQL) | ✅ todos correram sem erro |
| Seed ad-hoc user/workspace/artist/campaign (PostgreSQL) | ✅ criado; segunda execução confirmou idempotência |
| Smoke API (auth/workspace/campaign/campaign-actions/reports/media-kits/content-pack-requests) | ✅ todos `200`/`201` |
| `pytest apps/campaign_actions` (PostgreSQL) | ✅ 56/56 passed |
| Grep por segredos nos ficheiros alterados (`INTERNAL_API_TOKEN=`, `SECRET_KEY=`, `PASSWORD=`, `AWS_SECRET`, `ACCESS_KEY=`, `PRIVATE_KEY=`, valores reais de DB) | ✅ 0 ocorrências de valores reais |
| `scripts/check-forbidden-ports.ps1` | ✅ OK — nenhuma porta proibida |
| Confirmação de que `.env`/`db.sqlite3` de dev não foram alterados | ✅ `git status` sem alterações fora dos dois ficheiros de documentação |
| Container descartável removido no fim | ✅ `docker compose down -v` confirmado |

---

## 13. Bloqueios

Nenhum bloqueio impediu a validação técnica. O único item que **não** foi
resolvido (e não era objectivo desta iteração) é o **cutover de uma
instância PostgreSQL de staging persistente real** — isso depende de uma
decisão de infraestrutura (onde/como provisionar essa instância) que está
fora do âmbito de "preparar e validar" e é tratada como decisão pendente
(ver arquitectura §11, linha "DB alvo de staging").

---

## 14. Riscos

| Risco | Severidade | Nota |
|---|---|---|
| Confundir "PostgreSQL validado tecnicamente" com "staging formal a correr em PostgreSQL" | Alto | Mitigado explicitamente neste relatório e na arquitectura — o ambiente de staging técnico actual **continua em SQLite** até alguém provisionar e cortar para uma instância persistente |
| `psycopg` (sem `[binary]`) pode falhar em ambientes Windows sem `libpq` | Médio | Documentado como nota operacional para o runbook (STG-PRE-010); não afecta Linux com `libpq` de sistema |
| Falta de `DATABASE_URL` pode ser vista como lacuna por ferramentas de deploy que esperam essa convenção (ex.: alguns PaaS) | Baixo | Registado como melhoria técnica opcional; variáveis discretas já cobrem o caso de uso actual |
| Seed ad-hoc não persistido como management command pode ser esquecido/recriado de forma inconsistente no futuro | Baixo | Recomendado promover a `seed_staging_demo` no Prompt 09 (E2E), não urgente agora |

---

## 15. Próximo passo recomendado

Avançar para **Prompt 03 (STG-PRE-003 — Object storage)**: inspeccionar a
abstracção de storage do Content Renderer (`STORAGE_PROVIDER`, hoje só
`local`), o modelo `Asset` do Backend Core (`storage_key` existe,
`public_url` não), e propor o contrato de URL canónica/assinada antes de
escolher o provider — sem declarar object storage pronto enquanto só
`local` estiver implementado.
