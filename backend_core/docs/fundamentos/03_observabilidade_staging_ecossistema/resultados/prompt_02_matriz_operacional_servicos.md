# OBS-STG-002 — Relatório de execução: Matriz operacional dos serviços

> Relatório de execução do prompt 02. **Nenhum código de runtime foi alterado** —
> apenas documentação foi criada.
>
> Fase: Observabilidade e Staging Técnico do Ecossistema.
> Backlog: [`../01_backlog.md`](../01_backlog.md).
> Data: 2026-06-25. Modelo recomendado (backlog §15): opus.

---

## 1. Objectivo

Criar a matriz operacional central dos serviços do ecossistema, documentando
portas, comandos, healthchecks, variáveis (obrigatórias/opcionais/secrets),
dependências e modos de arranque local/staging — usando placeholders para todos
os segredos.

## 2. Ficheiros criados / alterados

| Ficheiro | Acção | Tipo |
|---|---|---|
| `…/03_observabilidade_staging_ecossistema/matriz_operacional_servicos.md` | **Criado** | Documentação (referência central) |
| `…/03_observabilidade_staging_ecossistema/resultados/prompt_02_matriz_operacional_servicos.md` | **Criado** | Relatório de execução (este ficheiro) |

**Runtime alterado:** nenhum. Não foi tocado código, settings, scripts nem `.env`.

## 3. Fontes inspeccionadas (confirmação de valores)

Para garantir que comandos/portas/variáveis estão correctos e não inventados:

| Fonte | Confirma |
|---|---|
| `resultados/prompt_01_analise_estado_operacional.md` | Healthchecks, portas, secrets, lacunas (base desta matriz) |
| `intelligence_engine/requirements.txt` | Stack IE (fastapi 0.138, uvicorn[standard], pydantic 2) |
| `content_renderer/package.json` | Scripts (`dev`/`build`/`start`/`test`/`lint`/`typecheck`), Node ≥18.18 |
| `content_renderer/docker-compose.e2e.yml` | PostgreSQL `postgres:16-alpine`, porta `55432→5432`, tmpfs, `pg_isready` |
| `.env.example` (×3) + `.env.e2e.example` | Variáveis e defaults dos três serviços |
| READMEs (×3) + `config/settings.py`, `config/urls.py` | Comandos de arranque, ausência de healthcheck no Django, defaults de settings |

## 4. Conteúdo da matriz (cobertura)

A matriz cobre, conforme pedido:

- ✅ `backend_core`, `intelligence_engine`, `content_renderer`.
- ✅ Base de dados (secção dedicada — só o Backend Core a usa; PostgreSQL para staging/E2E).
- ✅ Dependências internas (grafo + tabela direccional).
- ✅ Dependências externas relevantes (nenhuma obrigatória nesta fase; S3/R2 e Stripe fora do escopo; Docker só para o harness).

Por serviço: descrição, directório, porta, instalação/preparação, arranque,
healthcheck, variáveis obrigatórias, opcionais e sensíveis, logs relevantes,
dependências, e modo local vs staging.

## 5. Decisões tomadas

1. **Report renderer como serviço "lógico".** Documentado como o mesmo processo do
   `content_renderer` (uma porta, três tipos de job), registando explicitamente a
   discrepância `REPORT_RENDERER_BASE_URL=8003` (default) vs `8002` (real).
2. **Readiness temporário do Django.** Como não há healthcheck, a matriz indica
   `GET /api/v1/schema/` como proxy de readiness (foi o usado pelo harness E2E),
   deixando claro que o agregado dedicado chega em OBS-STG-003.
3. **Secrets sempre como placeholder** (`<INTERNAL_API_TOKEN>`, `<SECRET_KEY>`,
   `<DB_PASSWORD>`, …) e um registo consolidado de secrets com regras de
   não-versionamento e as guardas de arranque já existentes.
4. **Separação local vs staging** numa tabela própria (DEBUG, DB, DRY_RUN,
   APP_ENV/NODE_ENV, URLs, storage).

## 6. Lacunas e itens "por confirmar" registados

| Item | Estado | Como validar (na matriz §11) |
|---|---|---|
| Porta efectiva do report renderer (8003 vs 8002) | Discrepância conhecida (G9) | `curl :8002/health` vs `:8003/health`; apontar para `:8002`. |
| Host/bind do IE e renderer em staging | por confirmar | Definir `--host`/bind e validar com `curl`. |
| Healthcheck dedicado do Backend Core | inexistente | Criar em OBS-STG-003; proxy `:8000/api/v1/schema/` entretanto. |
| Visibilidade de logs INFO (Django sem `LOGGING`) | ausente | Confirmar/adicionar em OBS-STG-006. |

Estas lacunas são **operacionais e/ou de documentação** — nenhuma exige alterar
runtime neste prompt (coerente com a instrução).

## 7. Conformidade com os critérios de aceitação

| Critério | Estado |
|---|---|
| `matriz_operacional_servicos.md` existe | ✅ |
| Cada serviço principal com porta, comando de arranque e healthcheck (ou "por confirmar") | ✅ (Backend Core: healthcheck marcado como inexistente/a criar + proxy de readiness) |
| Secrets claramente identificados como não versionáveis | ✅ §5 da matriz (registo consolidado + 🔒 nas tabelas) |
| Dependências entre serviços claras | ✅ §7 da matriz (grafo + tabela direccional) |
| Relatório lista ficheiros, decisões, lacunas e próximo passo | ✅ este ficheiro |
| Sem valores reais de tokens | ✅ apenas placeholders |
| Runtime não alterado sem necessidade | ✅ só documentação |

## 8. Próximo passo recomendado

**OBS-STG-003 — Healthcheck agregado no Backend Core.** É o maior redutor de risco
operacional e o primeiro item que toca runtime. Recomendações já alinhadas com as
decisões pendentes do backlog:

- Endpoint **protegido** (OBS-PDEC-001), ex.: `GET /api/v1/system/health/external-services/`.
- Consulta em tempo real a `GET /health` do IE (`:8001`) e do renderer (`:8002`)
  com **timeout curto e configurável** (OBS-PDEC-003).
- Normalizar `ok|degraded|unavailable|misconfigured|unknown` por dependência, com
  `duration_ms`; falha de uma dependência → `degraded`, **nunca 500**.
- Testes com mocks (ok / degraded / timeout / misconfigured).
- Resolver na matriz/runbook a discrepância de porta do report renderer ao
  configurar os alvos do healthcheck.
