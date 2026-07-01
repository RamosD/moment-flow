# Relatório de execução — Prompt 02: Configuração, segurança interna e erros normalizados

## Objectivo

Implementar (IE-002 do [backlog](../backlog.md)) configuração robusta com
validação no arranque, autenticação interna por `X-Internal-Token` e o
modelo de erro normalizado completo, partindo da fundação criada no Prompt
01.

## Contexto consultado (sem alterações)

- `backend_core` e `content_renderer` voltaram a ser usados apenas como
  referência de padrão (`content_renderer/src/config/env.ts` — validação de
  token vazio em produção; `content_renderer/src/errors/errors.ts` — classes
  de erro por código; `content_renderer/src/logging/logger.ts` — redacção por
  regex). Nenhum ficheiro destes componentes foi alterado.
- Backlog secções 6.1 ("Autenticação interna"), 6.5 ("Erro comum") e
  `02_prompts_ie.md` (Prompt 02) seguidos à letra para os comportamentos
  exigidos.

## Decisões tomadas

1. **Validação de produção dentro do `pydantic.model_validator`**: em vez de
   uma função externa de validação (estilo `content_renderer`), usei
   `@model_validator(mode="after")` em `Settings` que levanta `ConfigError`
   (não um `ValueError` genérico) quando `app_env == "production"` e
   `internal_api_token` está vazio depois de `strip()`. Como `ConfigError`
   não é `ValueError`/`TypeError`/`AssertionError`, o Pydantic não o
   converte em `ValidationError` — propaga tal e qual, com mensagem clara,
   impedindo `Settings()` (e portanto o arranque do `uvicorn`, que avalia
   `get_settings()` à importação de `app.main`) de completar.
2. **Sem bypass inseguro em dev/test**: ao contrário do `content_renderer`
   (`ALLOW_INSECURE_EMPTY_TOKEN`), não criei uma flag de bypass. Decisão:
   quando `INTERNAL_API_TOKEN` está vazio (só possível fora de produção), a
   dependency `require_internal_token` rejeita **todos** os pedidos com 403
   — "token não configurado" nunca é tratado como "acesso livre". Isto
   simplifica a superfície de configuração e evita um interruptor que possa
   ser deixado activo por engano. Documentado no README e no `.env.example`.
3. **Comparação seg ura**: `hmac.compare_digest` em `app/core/security.py`
   (tempo constante), em vez de `==`.
4. **Dependency reutilizável, não middleware**: `require_internal_token` é
   uma dependency FastAPI (`Depends`), aplicada ao nível do `APIRouter`
   (`dependencies=[Depends(require_internal_token)]`) em vez de middleware
   ASGI — permite que `GET /health` fique fora do router protegido sem
   nenhuma lógica condicional de "skip auth for this path", e qualquer router
   futuro (`analysis`, `scoring`, ...) só precisa de declarar a mesma
   dependency.
5. **Endpoints temporários de diagnóstico** (`app/api/internal_debug.py`):
   como não existe ainda nenhum endpoint de negócio real para validar a
   autenticação e o contrato de erro, criei três rotas explicitamente
   documentadas como temporárias e a remover quando IE-004+ trouxer
   endpoints reais:
   - `GET /internal/_debug/ping` — confirma 200 quando autenticado;
   - `POST /internal/_debug/echo` — corpo Pydantic obrigatório, usado para
     exercitar `invalid_payload` (422);
   - `GET /internal/_debug/boom` — levanta `RuntimeError` deliberadamente,
     usado para exercitar `internal_error` (500) sem stack trace na
     resposta.
   Documentado no código (docstring do módulo) e no README como módulo a
   apagar.
6. **Exception handlers em `app/main.py`** (4 handlers, por ordem de
   especificidade):
   - `AppError` → resposta directa via `exc.status_code`/`exc.code`.
   - `RequestValidationError` (FastAPI) → convertido para
     `InvalidPayloadError` (422), com `details.errors` = `exc.errors()`
     (nunca inclui o token, que é um header consumido por uma dependency
     separada, não um campo validado do corpo).
   - `StarletteHTTPException` → 404 mapeado para `NotFoundError`; qualquer
     outro código mapeado para `AppError("internal_error", ...)` preservando
     o `status_code` original sem expor detalhes internos.
   - `Exception` (catch-all) → `InternalError` (500) genérico para o
     cliente; o traceback completo só é escrito no logger estruturado do
     servidor.
7. **Bug encontrado e corrigido durante a validação manual**: a primeira
   versão do catch-all usava `logger.exception(...)`, que depende de
   `sys.exc_info()` estar populado no momento da chamada. Ao testar
   manualmente o endpoint `/internal/_debug/boom`, o campo `exc_info` saía
   como `"NoneType: None"` — o contexto de excepção activa já não estava
   disponível quando o handler do Starlette invoca o nosso handler (a
   chamada não corre dentro de um bloco `except` activo no sentido do
   `sys.exc_info()`). Corrigido passando `exc_info=exc` explicitamente a
   `logger.error(...)`, o que resolveu o problema — confirmado com
   traceback completo no log após a correcção (ver secção de resultados).
8. **`ConfigError` movido para `app/core/errors.py`** (já existia desde o
   Prompt 01) e importado em `config.py` — não há import circular porque
   `errors.py` não depende de `config.py`.

## Ficheiros criados/alterados

### Criados

```text
app/core/security.py
app/api/internal_debug.py
tests/test_security.py
tests/test_errors.py
docs/gestao/fundamentos/resultados/prompt_02_config_seguranca_erros.md
```

### Alterados

```text
app/core/config.py     — field_validator (strip) + model_validator (produção)
app/core/errors.py      — + InvalidPayloadError, UnauthorizedInternalRequestError, ConfigError
app/main.py              — + 3 exception handlers (RequestValidationError, StarletteHTTPException, Exception), registo do router internal_debug
tests/test_config.py    — + 4 testes de validação de produção/whitespace
.env.example             — secção INTERNAL_API_TOKEN expandida com as regras
README.md                — secções "Autenticação interna", "Contrato de erro normalizado", estrutura e estado actualizados
```

## Comandos executados

```bash
venv/Scripts/python.exe -m pytest -v
venv/Scripts/python.exe -m ruff check .

# Verificação manual do bloqueio de arranque em produção
APP_ENV=production INTERNAL_API_TOKEN= venv/Scripts/python.exe -c "from app.core.config import Settings; Settings(_env_file=None)"

# Smoke test real com uvicorn + token configurado
INTERNAL_API_TOKEN=smoke-test-token venv/Scripts/python.exe -m uvicorn app.main:app --port 8098
curl http://127.0.0.1:8098/health
curl http://127.0.0.1:8098/internal/_debug/ping                                    # sem token
curl -H "X-Internal-Token: smoke-test-token" http://127.0.0.1:8098/internal/_debug/ping
curl -H "X-Internal-Token: smoke-test-token" http://127.0.0.1:8098/internal/_debug/boom
grep -i "smoke-test-token" uvicorn_smoke2.log   # confirmar ausência do token nos logs
```

## Resultados

- **pytest**: `20 passed` (5 do Prompt 01 + 15 novos: 4 de configuração de
  produção/whitespace, 6 de segurança, 4 de contrato de erro). 1 warning de
  depreciação já conhecido (`httpx`/`starlette.testclient`), inalterado
  desde o Prompt 01.
- **ruff check .**: `All checks passed!`.
- **Bloqueio de arranque em produção**: confirmado —
  `Settings(_env_file=None)` com `APP_ENV=production` e
  `INTERNAL_API_TOKEN=""` levanta
  `ConfigError: INTERNAL_API_TOKEN is required and must not be empty in production.`
- **Smoke test real (uvicorn)**:
  - `GET /health` → 200, sem token, igual ao Prompt 01.
  - `GET /internal/_debug/ping` sem token → 403
    `{"status":"failed","error":{"code":"unauthorized_internal_request",...}}`.
  - `GET /internal/_debug/ping` com token correcto → 200
    `{"status":"ok","authenticated":true}`.
  - `GET /internal/_debug/boom` com token correcto → 500
    `{"status":"failed","error":{"code":"internal_error","message":"Unexpected internal error.","details":{}},...}`
    — sem nome da excepção, sem ficheiro, sem traceback na resposta.
  - `grep -i "smoke-test-token" uvicorn_smoke2.log` → nenhuma ocorrência; o
    log de erro mostra `exception_type: "RuntimeError"` e o traceback
    completo (para diagnóstico server-side), mas nunca o valor do token.
- Nota observada (não é falha): quando uma excepção não tratada ocorre,
  além do nosso log estruturado, o `Starlette ServerErrorMiddleware` escreve
  também o seu próprio traceback no `stderr` do processo (comportamento
  nativo do Starlette/Uvicorn, independente da nossa aplicação). Isto é
  visível apenas nos logs do servidor, nunca na resposta HTTP ao cliente —
  não constitui uma fuga de informação para o chamador.

## Pendências

- Schemas Pydantic dos contratos de negócio (`EntityRef`,
  `BaseIntelligenceRequest`, `BaseIntelligenceResponse`, `Explanation`,
  `Warning`) — IE-003.
- Os endpoints temporários `app/api/internal_debug.py` devem ser removidos
  quando os endpoints reais de analysis/scoring/recommendations/moments
  (IE-004 em diante) passarem a exercitar a mesma autenticação e o mesmo
  contrato de erro nos seus próprios testes.
- Warning de depreciação `httpx`/`starlette.testclient` — ainda não
  bloqueante, mantém-se como pendência de observação desde o Prompt 01.
- O mapeamento genérico de `StarletteHTTPException` para código
  `internal_error` (quando o status não é 404) é uma simplificação; se
  surgirem casos de uso reais com 401/405/413, etc., poderá justificar-se um
  mapeamento de código mais específico nessa altura.

## Próximo passo recomendado

Avançar para **IE-003 — Definir schemas Pydantic e contratos internos**:
`EntityRef`, `BaseIntelligenceRequest`, `BaseIntelligenceResponse`,
`Explanation`, `Warning`, validação de `payload_version`/`workspace_id`/
`request_id`/`entity.type`, e os schemas específicos de
analysis/scoring/recommendations/moments — preparando o terreno para
substituir `internal_debug.py` pelos endpoints reais a partir de IE-004.
