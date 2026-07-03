# Prompt 02 — Criar Compose local — Resultado

**Data:** 2026-07-02
**Fase:** `06_staging_infraestrutura_real_local` (STG-LOCAL-002)
**Âmbito:** criar um Docker Compose local mínimo com apenas as duas
dependências de infraestrutura (PostgreSQL, MinIO), sem containerizar os
serviços aplicacionais. Sem alterar produto.
**Estado de execução:** `executado` — compose criado, validado com Docker
real (`config`, `up`, healthchecks, bucket, persistência através de um
ciclo `down`/`up`), sem secrets reais, portas canónicas confirmadas.

---

## 1. Nota sobre o caminho da pasta

Como no Prompt 01, os documentos desta execução foram criados em
`frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/`, que é
a pasta real e existente no repositório (o prompt referenciava
`06_staging_infraestrutura_real`, que não existe).

## 2. Ficheiros criados/alterados

| Ficheiro | Operação | Descrição |
|---|---|---|
| `docker-compose.staging.local.yml` (raiz do repositório) | **criado** | Compose com `postgres`, `minio` e `minio-bucket-init` (execução única) |
| `.env.staging.local.example` (raiz do repositório) | **criado** | Placeholders de todas as variáveis consumidas pelo compose, com comentários |
| `.gitignore` | **alterado** | Adicionada a linha `!.env.staging.local.example` para manter o exemplo rastreado pelo git, mantendo `.env.staging.local` (ficheiro real) ignorado pela regra já existente `.env.*` |
| `frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/resultados_execucao/prompt_02_compose_local_resultado.md` | **criado** | Este relatório |

Nenhum código de produto (`backend_core/`, `content_renderer/`,
`intelligence_engine/`, `frontend/src/`) foi alterado, conforme a regra
explícita do prompt.

## 3. Serviços definidos

| Serviço | Imagem | Papel | Porta(s) publicada(s) | Volume | Healthcheck |
|---|---|---|---|---|---|
| `postgres` | `postgres:16-alpine` | Base de dados de staging local, persistente | `${POSTGRES_PORT:-5432}:5432` | `chartrex_staging_postgres_data` → `/var/lib/postgresql/data` | `pg_isready -U <user> -d <db>` |
| `minio` | `minio/minio:latest` | Object storage S3-compatible, persistente | `${MINIO_API_PORT:-9000}:9000` (S3 API), `${MINIO_CONSOLE_PORT:-9001}:9001` (Console) | `chartrex_staging_minio_data` → `/data` | `curl -f http://localhost:9000/minio/health/live` |
| `minio-bucket-init` | `minio/mc:latest` | Serviço auxiliar de **execução única** (`restart: "no"`) — configura o alias `mc` e cria o bucket de staging (`mc mb --ignore-existing`) depois de `minio` estar `healthy` | nenhuma (não expõe porta) | nenhum (efémero por desenho — não guarda estado próprio) | não aplicável (corre e termina) |

Nenhum serviço aplicacional (Frontend, Backend Core, Intelligence Engine,
Content Renderer) foi adicionado a este compose — decisão já fechada em
`arquitectura_staging_local.md` §6.2 (Prompt 01) e reafirmada pela premissa
obrigatória deste prompt.

### 3.1 Rede e volumes

- Rede dedicada `chartrex_staging_local` (nome fixo via `name:`), partilhada
  pelos três serviços do compose. Os processos aplicacionais locais (fora do
  Docker) continuam a aceder via `127.0.0.1`/`localhost` nas portas
  publicadas — não precisam de estar nesta rede.
- Volumes nomeados com `name:` fixo (`chartrex_staging_postgres_data`,
  `chartrex_staging_minio_data`) para não depender do nome do
  projecto/directório do checkout — evita volumes órfãos se o repositório
  for clonado para um caminho diferente.

## 4. Variáveis necessárias (sem valores reais)

Todas documentadas com comentários em `.env.staging.local.example`; nenhum
valor real existe em nenhum ficheiro versionado:

| Variável | Consumida por | Default no compose (placeholder, não segredo) |
|---|---|---|
| `POSTGRES_DB` | `postgres` | `chartrex_staging` |
| `POSTGRES_USER` | `postgres` | `chartrex_staging` |
| `POSTGRES_PASSWORD` | `postgres` | `chartrex_staging_local_only` |
| `POSTGRES_PORT` | mapeamento de porta do host | `5432` |
| `MINIO_ROOT_USER` | `minio`, `minio-bucket-init` | `chartrex_staging_minio` |
| `MINIO_ROOT_PASSWORD` | `minio`, `minio-bucket-init` | `chartrex_staging_local_only` |
| `MINIO_API_PORT` | mapeamento de porta do host (S3 API) | `9000` |
| `MINIO_CONSOLE_PORT` | mapeamento de porta do host (Console) | `9001` |
| `STORAGE_BUCKET` | `minio-bucket-init` | `chartrex-staging` |

Os defaults acima (`chartrex_staging_local_only`, `change-me-local-only` no
`.env.staging.local.example`) são placeholders de desenvolvimento local
explícitos — mesmo padrão já usado e aceite em
`content_renderer/docker-compose.e2e.yml` (`chartrex_e2e_dev_only`) e
reconhecido como não-segredo nos greps de fecho da fase 05. Um operador real
deve substituí-los por valores próprios em `.env.staging.local` (ficheiro
ignorado pelo git), nunca editar os defaults no compose.

## 5. Comandos documentados

```powershell
# --- Start (sobe postgres + minio; minio-bucket-init corre uma vez e termina) ---
docker compose -f docker-compose.staging.local.yml up -d

# --- Status ---
docker compose -f docker-compose.staging.local.yml ps

# --- Logs (todos os serviços, streaming) ---
docker compose -f docker-compose.staging.local.yml logs -f

# --- Logs de um serviço específico ---
docker compose -f docker-compose.staging.local.yml logs postgres
docker compose -f docker-compose.staging.local.yml logs minio
docker compose -f docker-compose.staging.local.yml logs minio-bucket-init

# --- Stop (pára e remove containers/rede; PRESERVA os volumes) ---
docker compose -f docker-compose.staging.local.yml down
```

```powershell
# =====================================================================
# RESET DESTRUTIVO — apaga os volumes (todos os dados de PostgreSQL e
# MinIO são perdidos). Separado deliberadamente dos comandos acima.
# Exige confirmação explícita do operador antes de correr.
# =====================================================================
docker compose -f docker-compose.staging.local.yml down -v
```

Não foi criado nenhum script `.ps1`/`.sh` dedicado nesta iteração — isso é
o âmbito explícito de **STG-LOCAL-006** (scripts de arranque local), um
prompt posterior. Este prompt cobre apenas a documentação dos comandos
directos do Docker Compose, conforme a tarefa 10 do prompt ("Documentar
comandos"), não a criação de wrappers.

## 6. Healthchecks

| Serviço | Mecanismo | Validado nesta iteração |
|---|---|---|
| `postgres` | `pg_isready -U chartrex_staging -d chartrex_staging` (a cada 5s, até 20 tentativas, `start_period` 10s) | ✅ Container atingiu `healthy` em ~10s após `up -d` |
| `minio` | `curl -f http://localhost:9000/minio/health/live` (mesma cadência) | ✅ Container atingiu `healthy` em ~10s após `up -d`; confirmado que a imagem `minio/minio:latest` inclui `curl` (`docker run --entrypoint sh minio/minio:latest -c "ls /usr/bin"` → `curl` presente) |
| `minio-bucket-init` | `depends_on: minio: condition: service_healthy` — só arranca depois do MinIO estar saudável | ✅ Confirmado pela ordem nos logs de `docker compose up`: `minio Healthy` antes de `minio-bucket-init Starting` |

## 7. Validações executadas (todas com Docker real, não simuladas)

| Validação | Resultado |
|---|---|
| `docker --version` / `docker compose version` | ✅ Docker 28.3.2, Compose v2.38.2 — disponível e a correr (`docker ps` respondeu) |
| Inspecção de compose existente no repositório (`**/docker-compose*.yml`) | ✅ Só existia `content_renderer/docker-compose.e2e.yml` (Postgres descartável em `tmpfs`, propósito distinto — E2E efémero); usado como referência de sintaxe, não de persistência |
| `docker compose -f docker-compose.staging.local.yml config` | ✅ Configuração resolvida sem erros, portas/volumes/healthchecks correctos |
| `docker pull postgres:16-alpine`, `docker pull minio/minio:latest`, `docker pull minio/mc:latest` | ✅ As três imagens descarregadas com sucesso |
| Inspecção da imagem `minio/minio:latest` para escolher o mecanismo de healthcheck (`curl` disponível, `mc` não vem embutido) | ✅ Confirmado via `docker run --entrypoint sh` — decisão de usar `curl` em vez de `mc ready local` (que exigiria alias pré-configurado dentro do próprio container) |
| `docker compose -f docker-compose.staging.local.yml up -d` | ✅ `postgres` e `minio` chegaram a `healthy`; `minio-bucket-init` arrancou depois e terminou com exit code `0` |
| `docker compose -f docker-compose.staging.local.yml ps` | ✅ `chartrex_staging_postgres` e `chartrex_staging_minio` reportados `Up ... (healthy)` |
| `docker logs chartrex_staging_minio_bucket_init` | ✅ `Added local successfully` / `Bucket created successfully local/chartrex-staging` / `bucket chartrex-staging pronto` |
| Confirmação do bucket via `docker inspect ... ExitCode` | ✅ `0` |
| **Teste de persistência de dados:** `INSERT` de uma linha de sonda em PostgreSQL → `docker compose down` (sem `-v`) → `docker volume ls` confirma os dois volumes ainda existem → `docker compose up -d` novamente → `SELECT` confirma a linha ainda lá → `minio-bucket-init` recria o alias e confirma o bucket já existe (idempotente) | ✅ Linha de sonda presente após o ciclo completo `down`/`up`; volumes sobreviveram; bucket persistiu. Linha de sonda removida no final (`DROP TABLE`) para não deixar dados de teste na base |
| `docker volume ls --filter name=chartrex_staging` (antes e depois do `down`) | ✅ `chartrex_staging_postgres_data` e `chartrex_staging_minio_data` presentes em ambos os momentos |
| `docker compose -f docker-compose.staging.local.yml down` (estado final, sem `-v`) | ✅ Containers e rede removidos; volumes preservados — stack fica parada e limpa para a próxima iteração |
| `scripts/check-forbidden-ports.ps1` | ✅ `OK - nenhuma porta proibida encontrada em ficheiros activos` |
| Grep de `password\|secret\|token\|api_key\|private_key` (case-insensitive) em `docker-compose.staging.local.yml` | ✅ Só nomes de variável (`POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD`) e o placeholder óbvio `chartrex_staging_local_only` — mesmo padrão já aceite na fase 05/E2E, não um segredo real |
| Grep de `password\|secret\|token\|api_key\|private_key` (case-insensitive) em `.env.staging.local.example` | ✅ Só nomes de variável e o placeholder `change-me-local-only` |
| `git check-ignore -v .env.staging.local .env.staging.local.example docker-compose.staging.local.yml` | ✅ `.env.staging.local` (ficheiro real) → ignorado; `.env.staging.local.example` → **não** ignorado (rastreado); `docker-compose.staging.local.yml` → **não** ignorado (rastreado) |
| Confirmação manual: nenhuma porta proibida (8000, 8001, 8002, 8003, 1420, 9011, 5173, 5174, 8080–8085) usada | ✅ Portas usadas: 5432, 9000, 9001 — nenhuma coincide |

## 8. Limitações

- O serviço `minio-bucket-init` corre **sempre** que `docker compose up` é
  executado (mesmo que os outros serviços já estejam saudáveis e o bucket já
  exista) — é intencional e seguro (`mc mb --ignore-existing` é idempotente),
  mas significa que o comando `up` normal já inclui a criação/confirmação do
  bucket; não há um passo manual separado necessário no fluxo normal.
- O compose não valida que as portas do host (5432, 9000, 9001) estão livres
  antes de arrancar — se já houver outra instância local de PostgreSQL ou
  MinIO a usar essas portas, o `docker compose up` falha com erro de bind.
  O override de porta (`POSTGRES_PORT`, `MINIO_API_PORT`,
  `MINIO_CONSOLE_PORT`) já está disponível no compose (risco LOCAL-R02/R03
  do backlog), mas não foi testado nesta iteração com portas alternativas —
  fica documentado como possível, não como validado com um valor não-default.
- Este prompt não liga nenhum serviço aplicacional (Backend Core, Content
  Renderer) a este PostgreSQL/MinIO — essa validação de ponta-a-ponta é
  STG-LOCAL-003 e STG-LOCAL-004, fora do âmbito deste prompt.
- O nome do bucket (`chartrex-staging`) e as credenciais do MinIO
  (`MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`) ainda não foram ligados a
  `STORAGE_ACCESS_KEY`/`STORAGE_SECRET_KEY` do Content Renderer — o MinIO
  usa por definição credenciais "root"; a criação de credenciais de acesso
  dedicadas (não-root) para o Content Renderer, se desejada, é uma decisão
  de STG-LOCAL-004/005, não deste prompt.

## 9. Riscos

| Risco | Situação após este prompt |
|---|---|
| LOCAL-R01 — Docker indisponível | Não se materializou nesta máquina — Docker 28.3.2 disponível e a correr; documentado como pré-requisito no cabeçalho do compose |
| LOCAL-R02 — Porta 5432 ocupada | Mitigação (`POSTGRES_PORT`) presente no compose; não testada nesta iteração com valor alternativo |
| LOCAL-R03 — Porta 9000/9001 ocupada | Mitigação (`MINIO_API_PORT`, `MINIO_CONSOLE_PORT`) presente no compose; não testada nesta iteração com valor alternativo |
| LOCAL-R04 — Secrets locais versionados por acidente | Mitigado: `.env.staging.local` confirmado ignorado pelo git (`git check-ignore`); só `.env.staging.local.example` (placeholders) é rastreado; grep de segurança limpo |
| LOCAL-R05 — `public_url` do MinIO não acessível pelo Backend/Frontend | Não resolvido neste prompt (é STG-LOCAL-004) — este compose só expõe o MinIO ao host local (`localhost:9000`/`:9001`); a decisão de endpoint interno vs. público para o `Asset.public_url` continua pendente |
| LOCAL-R08 — Dados acumulam em volumes locais | Mitigado parcialmente: reset destrutivo (`down -v`) está documentado e claramente separado do `down` normal; não foi executado nesta iteração (exige autorização explícita, que não foi dada) |
| LOCAL-R10 — Containerizar apps cedo demais | Não se materializou — este compose contém apenas `postgres`, `minio` e o serviço auxiliar efémero `minio-bucket-init`; nenhum serviço aplicacional foi containerizado |

## 10. Próximo passo recomendado

Avançar para **STG-LOCAL-003** (Prompt 03 do pipeline): configurar o
Backend Core para usar este PostgreSQL local persistente
(`DB_ENGINE=postgres`, `DB_HOST=127.0.0.1`, `DB_PORT=5432` ou o override
definido em `.env.staging.local`), correr `migrate`, seeds e smoke API
reais contra ele, e confirmar persistência de dados de produto (não apenas
da linha de sonda usada para validar o compose nesta iteração).
