# Prompt 01 — Arquitectura alvo de staging pré-produção — Resultado

**Data:** 2026-07-02
**Fase:** `05_staging_operacionalizacao_pre_producao` (STG-PRE-001)
**Âmbito:** documentar a arquitectura alvo de staging pré-produção, sem alterar código de produto.
**Estado de execução:** `executado`

---

## 1. Resumo objectivo

Foi lido integralmente o backlog da fase (`01_backlog.md`) e o pipeline de
prompts (`02_prompts_staging_operacionalizacao.md`), os três documentos finais
da fase 04 (`estado_staging_ie_renderer.md`, `arquitectura_staging_ie_renderer.md`,
`prompt_10_estado_final_staging_resultado.md`), o mapa de portas
(`docs/configuracao/portas_projeto.md`), os quatro `.env.example`
(`backend_core`, `intelligence_engine`, `content_renderer`, `frontend`), o
bloco de configuração de `DATABASES`/`LOGGING` em `backend_core/config/settings.py`,
o healthcheck agregado (`backend_core/apps/integrations_bridge/health.py`), a
matriz operacional da fase 03 (`backend_core/docs/fundamentos/03_observabilidade_staging_ecossistema/matriz_operacional_servicos.md`)
e o harness E2E do Content Renderer (`content_renderer/docker-compose.e2e.yml`).

Com base nesta leitura, foi criado `arquitectura_staging_pre_producao.md`
descrevendo: os quatro níveis de ambiente (dev local / staging técnico /
staging pré-produção / produção), componentes e responsabilidades, portas
canónicas e URLs, os quatro fluxos (Frontend→Backend Core, Backend
Core→Intelligence Engine, Backend Core→Content Renderer, callback
Content Renderer→Backend Core), estado actual vs. alvo de base de dados,
storage, secrets, logs/observabilidade e healthchecks, limites conhecidos
herdados da fase 04, e as sete decisões pendentes explicitamente listadas no
backlog (DB alvo, provider de object storage, mecanismo de secrets,
`public_url`/`signed_url`, estratégia de logs, ferramenta E2E, mais o esquema
de hosts de staging).

Nenhuma decisão de arquitectura foi tomada implicitamente: onde o backlog
pede uma escolha (provider, DB, secrets, URL de assets, logs, E2E), o
documento regista as opções em consideração e remete para o prompt seguinte
correspondente (STG-PRE-002 a STG-PRE-009), sem fingir que a decisão já foi
tomada.

---

## 2. Ficheiros criados / alterados

| Ficheiro | Operação |
|---|---|
| `frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/arquitectura_staging_pre_producao.md` | **criado** |
| `frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/resultados_execucao/prompt_01_arquitectura_alvo_resultado.md` | **criado** (este relatório) |

Nenhum ficheiro de código foi alterado. Nenhuma migration, configuração
runtime ou `.env` foi tocada.

---

## 3. Decisões documentadas (não pendentes)

Estas já estavam implícitas no código/config actual e foram tornadas
explícitas no documento:

- Portas canónicas (5200/5201 frontend, 8100 Backend Core, 8201 Intelligence
  Engine, 8202 Content Renderer) não mudam entre níveis de ambiente — só o
  host muda.
- PostgreSQL já é suportado nativamente em `config/settings.py`
  (`DB_ENGINE=postgres`) e já é usado no harness E2E do Content Renderer
  (`postgres:16-alpine`, dados em tmpfs) — não é preciso construir suporte de
  raiz, apenas decidir a topologia de staging persistente (STG-PRE-002).
  Confirma-se o padrão via `git blame`/leitura: sem alterações necessárias
  neste prompt.
- `STORAGE_PROVIDER` no Content Renderer é validado contra uma lista fechada
  que hoje só contém `'local'` (`content_renderer/src/config/env.ts`) — um
  valor desconhecido falha o arranque; a extensão para S3/R2/MinIO é trabalho
  de STG-PRE-003, não desta fase.
- `Asset.public_url` **não existe como campo populado** — o modelo `Asset`
  (`backend_core/apps/core/models.py`) tem `storage_key` mas não é preenchido
  com uma URL pública canónica; confirma a limitação já registada na fase 04.
- O healthcheck agregado (`GET /api/v1/system/health/dependencies/`,
  staff-only) já cobre IE + Content Renderer + DB e nunca lança excepção —
  está implementado e só falta ser exercitado com utilizador staff em runtime
  de staging (pendência herdada, não desta fase).
- Regra de fronteira (frontend só fala com Backend Core; nunca envia
  `X-Internal-Token`) confirmada inalterada no código (`shared/api/client.ts`,
  `shared/api/security.ts`) e reafirmada explicitamente no documento.

---

## 4. Decisões pendentes (registadas, não resolvidas)

| Decisão | Estado | Prompt onde se resolve |
|---|---|---|
| DB alvo de staging | PostgreSQL é a opção natural (já suportado); topologia por decidir | STG-PRE-002 |
| Provider de object storage | Nenhum escolhido (S3 / R2 / MinIO / outro) | STG-PRE-003 |
| Mecanismo de gestão de secrets | Nenhum escolhido (secret store / CI vars / processo controlado) | STG-PRE-004 |
| `public_url` vs `signed_url` | Depende do provider e da política de acesso — nenhuma definida | STG-PRE-003 |
| Estratégia de logs (agregação/retenção) | Não existe hoje (só stdout por processo) | STG-PRE-006 (parcial) |
| Ferramenta E2E | Playwright é a preferência do backlog; nada instalado | STG-PRE-009 |
| Esquema de hosts em staging pré-produção | Não definido (máquina única vs. hosts/containers separados) | A esclarecer antes de STG-PRE-010 |

---

## 5. Validações executadas

| Validação | Resultado |
|---|---|
| Grep por portas proibidas (8000-8003, 1420, 9011, 5173, 5174, 8080-8085) no documento criado | ✅ única ocorrência é a linha que **lista** as portas como proibidas (documentação da regra), nenhuma usada como default activo |
| `scripts/check-forbidden-ports.ps1` (script oficial do repositório) | ✅ `OK — nenhuma porta proibida encontrada em ficheiros activos.` |
| Grep por padrões de secret (`INTERNAL_API_TOKEN=<valor>`, `SECRET_KEY=<valor>`, `PASSWORD=<valor>`, `AWS_SECRET`, `ACCESS_KEY=`, `PRIVATE_KEY=`, `Bearer <token>`) no documento criado | ✅ única ocorrência é o nome da variável `DB_PASSWORD` num placeholder textual, sem valor real |
| Confirmação da regra "frontend só fala com Backend Core" no documento | ✅ presente em §2 (fluxos) e §11 (nenhuma decisão pendente a contradiz) |
| Nenhuma alteração de código runtime | ✅ apenas dois ficheiros de documentação foram criados |

---

## 6. Riscos

| Risco | Severidade | Nota |
|---|---|---|
| Esquema de hosts de staging pré-produção ainda indefinido | Médio | Pode bloquear a escrita do runbook (STG-PRE-010) se não for esclarecido antes; registado como decisão pendente adicional |
| Decisões pendentes (DB/storage/secrets) podem divergir do que os Prompts 02-04 acabarem por implementar | Baixo | Este documento é o "alvo" antes da implementação; espera-se actualização incremental à medida que cada prompt fecha uma decisão |
| Documento pode ficar desactualizado se código mudar antes do fecho da fase (Prompt 11) | Baixo | Mitigado por remeter sempre à fonte de verdade (código, `.env.example`, settings) em vez de duplicar valores que podem mudar |

---

## 7. Próximo passo recomendado

Avançar para **Prompt 02 (STG-PRE-002 — DB staging)**: inspeccionar a
configuração actual de `DATABASE_URL`/`DB_ENGINE`, confirmar dependências
para PostgreSQL, validar migrations contra o DB alvo e documentar
backup/rollback básico — sem declarar staging formal enquanto o Backend Core
continuar dependente de SQLite.
