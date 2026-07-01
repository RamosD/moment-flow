# Relatório de Execução — Hardening 05: Harness E2E com PostgreSQL (R-HARD-002)

- **Serviço:** `content_renderer`
- **Data:** 2026-06-23
- **Backlog de referência:** [`03_backlog_hardening_pos_mvp_renderer.md`](../03_backlog_hardening_pos_mvp_renderer.md) → **R-HARD-002**

---

## 1. Prompt executado

Criar um harness E2E com **PostgreSQL** para validar o `content_renderer` contra
o Backend Core (Django) num ambiente **multi-processo fiável**, sem alterar
indevidamente o `backend_core`, sem secrets reais e sem depender de SQLite para o
teste final. Não é obrigatório o E2E ficar 100% verde, mas o ambiente deve ficar
preparado e os impedimentos documentados com precisão.

## 2. Objectivo

Resolver o caveat conhecido (SQLite não partilha linhas commitadas entre
processos → callback `404`) preparando um harness baseado em PostgreSQL que: sobe
a base, configura o backend_core, migra/seed, arranca os dois serviços com o mesmo
token, corre o driver E2E e recolhe evidências — com _teardown_ limpo.

## 3. Ficheiros criados

| Ficheiro | Propósito |
|---|---|
| `docker-compose.e2e.yml` | PostgreSQL efémero (tmpfs) para E2E; credenciais **de dev** (não secrets); porta host `55432`; healthcheck. |
| `.env.e2e.example` | Template de variáveis E2E (DB + token + URLs); valores de dev, sem secrets; git-ignorado o `.env.e2e` real. |
| `scripts/run-e2e-postgres.ps1` | Orquestrador: compose up → readiness → migrate + seeds → renderer (:8002) + Django (:8000) → readiness → driver → evidências → teardown (`-KeepUp` opcional). |
| `docs/fundamentos/resultados/prompt_hardening_05_e2e_postgres_harness.md` | Este relatório. |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `scripts/e2e_backend_core.py` | Driver passa a fazer **polling** do estado da entidade (`wait_for`) após o `POST /jobs`, em vez de `sleep` fixo — alinhado ao callback em **background** (R-HARD-001). |
| `scripts/run-e2e.ps1` | Nota de cabeçalho: variante SQLite legada; aponta para o harness PostgreSQL. |
| `.gitignore` | `!.env.e2e.example` (template versionado) e `e2e-logs/` (evidências). |
| `docs/fundamentos/guia_e2e_backend_core.md` | Nova §8 "Harness E2E com PostgreSQL" (pré-requisitos, variáveis, comandos, evidências, limpeza, troubleshooting). |
| `README.md`, `docs/fundamentos/02_estado_content_report_renderer.md` | Apontador para o harness Postgres; estado/pendências. |

## 5. Estratégia PostgreSQL escolhida

- **Docker Compose** efémero (`docker-compose.e2e.yml`) com `postgres:16-alpine`,
  dados em **tmpfs** (base descartável, sem dados reais, limpeza trivial).
- O `backend_core` **já suporta** PostgreSQL nativamente
  (`config/settings.py`: `DB_ENGINE=postgres` + `DB_NAME/USER/PASSWORD/HOST/PORT`;
  `psycopg` 3 instalado) — **não foi necessário alterar o backend_core**.
- Porta host **55432** (≠ 5432) para não colidir com um Postgres local.
- Token interno partilhado gerado pelo harness; mesmo `DB_*` herdado pelos
  processos filho (renderer e Django).

## 6. Variáveis necessárias

`DB_ENGINE=postgres`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST=localhost`,
`DB_PORT=55432`, `INTERNAL_API_TOKEN` (partilhado), além das URLs de serviço
(`CONTENT_RENDERER_BASE_URL`, `REPORT_RENDERER_BASE_URL`, `BACKEND_PUBLIC_BASE_URL`,
`EXTERNAL_JOBS_ENABLED=true`, `EXTERNAL_JOBS_DRY_RUN=false`, `STORAGE_PROVIDER=local`).
Todos com defaults de **desenvolvimento** em `.env.e2e.example` / `docker-compose.e2e.yml`.

## 7. Comandos executados

```bash
npm run build           # renderer
npm run lint            # renderer
npm test                # renderer
python manage.py check  # backend_core
docker compose -f docker-compose.e2e.yml config   # validação do compose (parse)
docker compose -f docker-compose.e2e.yml up -d     # tentativa de smoke
```

## 8. Resultado dos comandos

| Comando | Resultado |
|---|---|
| `npm run build` | ✅ Sem erros |
| `npm run lint` | ✅ Sem erros |
| `npm test` | ✅ **136 testes**, 13 ficheiros (inalterado — prompt não toca em `src/`) |
| `python manage.py check` | ✅ `System check identified no issues (0 silenced).` |
| `docker compose ... config` | ✅ `exit 0` — compose válido, interpolação de `DB_*` resolvida |
| `docker compose ... up -d` | ❌ **Impedimento de ambiente** (ver §9) |

## 9. Impedimentos

- **Docker engine não estava a correr.** O CLI do Docker está instalado
  (`Docker version 28.3.2`, `Docker Compose v2.38.2`), mas o **engine do Docker
  Desktop não estava ligado**, pelo que não foi possível subir o contentor nem
  correr o smoke multi-processo completo. Erro exacto observado:

  ```text
  unable to get image 'postgres:16-alpine': error during connect:
  Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/images/postgres:16-alpine/json":
  open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
  ```

  **Não foi mascarado como sucesso.** Tudo o que não depende do engine foi
  validado: `manage.py check` (0 issues), `docker compose config` (exit 0),
  renderer verde. Para concluir o smoke basta **iniciar o Docker Desktop** e
  correr `scripts\run-e2e-postgres.ps1` (o harness está pronto e auto-contido).

- **Cobertura do driver:** o `e2e_backend_core.py` cobre `report_generation` e
  `media_kit_generation` (criam a entidade via serviços do backend e POSTam o
  envelope real). O cenário `content_generation` (via `ContentPackRequest`) fica
  como extensão recomendada do driver (R-HARD-003).

## 10. Próximo passo recomendado

1. Iniciar o **Docker Desktop** e correr `scripts\run-e2e-postgres.ps1`; arquivar
   o `e2e-logs/<timestamp>/e2e_results.json` como evidência.
2. Avançar para **R-HARD-003** — validar funcionalmente o loop Django → Renderer →
   Django (cenários `completed`/`failed`/`partially_completed` e idempotência do
   callback sob retry), estendendo o driver a `content_generation`.
