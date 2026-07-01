# Relatório de execução — Prompt 01: Fundação do serviço FastAPI Intelligence Engine

## Objectivo

Criar a fundação técnica do serviço `intelligence_engine`, conforme IE-001 do
[backlog](../backlog.md): estrutura base, `GET /health`, configuração via
ambiente, logger estruturado, modelo de erro comum, README, `.env.example` e
testes mínimos. Sem implementar analysis, scoring, recommendations ou
moments.

## Inspecção prévia (sem alterações)

- `backlog.md` e `02_prompts_ie.md` lidos por completo.
- `backend_core`: `pyproject.toml` (config do `ruff`), `pytest.ini`,
  `requirements.txt`, `.env.example` — usados como referência de
  convenções Python do repositório (ruff `select = ["E","W","F","I","UP","B"]`,
  `line-length = 100`, `target-version = "py313"`; `pytest.ini` simples).
- `content_renderer`: `src/http/routes.ts` (formato do `GET /health`),
  `src/errors/errors.ts` (classe `AppError` com `code`/`statusCode`/`details`),
  `src/logging/logger.ts` (logger JSON com redacção por regex de chaves
  sensíveis), `src/config/env.ts` (loader de configuração validado,
  `ConfigError` no arranque), `.env.example` e `README.md` — usados apenas
  como referência de padrões; nenhum ficheiro destes componentes foi alterado.

Nenhum ficheiro em `backend_core/` ou `content_renderer/` foi modificado.

## Decisões tomadas

1. **Gestor de dependências**: `requirements.txt` (não havia `pyproject.toml`
   de packaging em nenhum dos componentes de referência Python; o
   `backend_core/pyproject.toml` é apenas configuração de `ruff`/`coverage`,
   não packaging). Segui o mesmo padrão: `requirements.txt` para dependências
   + `pyproject.toml` só para configuração do `ruff`, e `pytest.ini` para
   `pytest`.
2. **Estrutura de pastas**: segui a estrutura sugerida no backlog
   (`app/api`, `app/core`, `app/schemas`, `app/services`, `app/rules`,
   `tests/`), criando apenas os módulos necessários a esta fase
   (`api/health.py`, `core/config.py`, `core/logging.py`, `core/errors.py`,
   `constants.py`, `main.py`). `schemas/`, `services/` e `rules/` ficam com
   `__init__.py` vazio, prontos para as fases seguintes (IE-003 a IE-007).
3. **Configuração**: `pydantic-settings.BaseSettings` (já é dependência
   transitiva natural do FastAPI via `pydantic`), com `get_settings()` cacheado
   (`lru_cache`). Cobre `APP_ENV`, `SERVICE_NAME`, `SERVICE_VERSION`,
   `LOG_LEVEL`, `INTERNAL_API_TOKEN` — os nomes exactos pedidos no backlog
   (secção "Prompt 02"). `INTERNAL_API_TOKEN` é lido mas **não** validado nem
   aplicado nesta fase — isso é explicitamente IE-002 (autenticação interna),
   fora do escopo deste prompt.
4. **Logger estruturado**: construído sobre `logging` da stdlib (não
   `structlog`/`loguru`) para manter zero dependências extra, com um
   `JsonFormatter` que serializa uma linha JSON por registo e redige
   recursivamente qualquer chave que combine com
   `token|secret|password|authorization|api[-_]?key|credential` — mesma
   abordagem do `content_renderer`.
5. **Modelo de erro**: classe `AppError` (código, mensagem, `status_code`,
   `details`) com `to_response_body()` que produz exactamente o contrato da
   secção 6.5 do backlog (`status: "failed"`, `error.code/message/details`,
   `metadata.engine/engine_version`). Apenas `not_found` e `internal_error`
   estão implementados como subclasses concretas nesta fase; `invalid_payload`,
   `unauthorized_internal_request` e `config_error` ficam definidos no
   `Literal` de `ErrorCode` mas sem handler HTTP dedicado — isso e o
   middleware de autenticação são IE-002.
6. **Lifespan em vez de `on_event`**: usei `@asynccontextmanager` (API actual
   do FastAPI) em vez do decorator `@app.on_event("startup")`, que está
   deprecated.
7. **`GET /health` público**: sem dependência de autenticação, devolve
   `status`, `service`, `version`, `timestamp` (ISO 8601, UTC), conforme a
   secção 7.1 do backlog.

## Ficheiros criados

```text
intelligence_engine/
  app/__init__.py
  app/constants.py
  app/main.py
  app/api/__init__.py
  app/api/health.py
  app/core/__init__.py
  app/core/config.py
  app/core/logging.py
  app/core/errors.py
  app/schemas/__init__.py
  app/services/__init__.py
  app/rules/__init__.py
  tests/__init__.py
  tests/conftest.py
  tests/test_health.py
  tests/test_config.py
  requirements.txt
  pyproject.toml
  pytest.ini
  .env.example
  .gitignore
  README.md
  docs/gestao/fundamentos/resultados/prompt_01_fundacao_fastapi.md
```

Nenhum ficheiro existente foi alterado (a pasta `intelligence_engine/`
continha apenas `venv/` e `docs/` previamente).

## Comandos executados

```bash
# Dependências (no venv já existente em intelligence_engine/venv)
venv/Scripts/python.exe -m pip install -r requirements.txt

# Testes
venv/Scripts/python.exe -m pytest -v

# Lint
venv/Scripts/python.exe -m ruff check .

# Smoke test de arranque real
venv/Scripts/python.exe -m uvicorn app.main:app --port 8099
curl http://127.0.0.1:8099/health
```

## Resultados

- **pytest**: `5 passed` (2 testes de `/health`, 3 de configuração). 1 warning
  de depreciação (`StarletteDeprecationWarning: Using httpx with
  starlette.testclient is deprecated`) — proveniente da combinação
  `fastapi.testclient` + `httpx` instalados; não afecta o resultado dos
  testes nem o comportamento do serviço, fica como pendência de observação
  para quando o ecossistema FastAPI/Starlette estabilizar a alternativa.
- **ruff check .**: `All checks passed!` (após correcção de 2 linhas acima do
  `line-length = 100` em `app/core/logging.py` e `app/main.py`).
- **Smoke test real**: `uvicorn app.main:app --port 8099` arrancou e
  `curl http://127.0.0.1:8099/health` devolveu HTTP 200 com:
  ```json
  {"status":"ok","service":"intelligence_engine","version":"0.1.0","timestamp":"2026-06-24T17:23:22.879253+00:00"}
  ```
  O log de arranque confirmou logger estruturado em JSON sem qualquer
  segredo:
  ```json
  {"level": "info", "time": "...", "msg": "service_startup", "service": "intelligence_engine", "logger": "intelligence_engine", "app_env": "development"}
  ```
- Versões resolvidas e fixadas em `requirements.txt`: `fastapi==0.138.0`,
  `uvicorn[standard]==0.49.0`, `pydantic==2.13.4`, `pydantic-settings==2.14.2`,
  `pytest==9.1.1`, `httpx==0.28.1`, `ruff==0.15.19`.
- Confirmação manual: `.env.example` e README não contêm tokens, passwords
  ou segredos reais (`INTERNAL_API_TOKEN` fica vazio com comentário
  explícito de "never commit a real value").

## Pendências

- Autenticação `X-Internal-Token` (validação, middleware/dependency, 403 em
  ausência/erro de token, bloqueio de arranque em produção com token vazio) —
  IE-002.
- Erros normalizados completos (`invalid_payload`,
  `unauthorized_internal_request`, `config_error`) com exception handlers
  HTTP — IE-002.
- Schemas Pydantic dos contratos de negócio (`EntityRef`,
  `BaseIntelligenceRequest`, etc.) — IE-003.
- Warning de depreciação `httpx`/`starlette.testclient` — não bloqueante,
  reavaliar quando a stack actualizar a forma recomendada de testar FastAPI.

## Próximo passo recomendado

Avançar para **IE-002 — Configuração, segurança interna e erros
normalizados**: implementar o middleware/dependency de `X-Internal-Token`,
completar os exception handlers para os restantes códigos de erro do
contrato, e os testes de segurança correspondentes (token ausente, errado,
correcto; token vazio em produção; ausência de segredos em logs).
