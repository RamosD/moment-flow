# Relatório de execução — Revisão e hardening dos Prompts 01 e 02

Revisão crítica da fundação (IE-001) e da configuração/segurança/erros
(IE-002) já implementadas, com refactoring e hardening onde se justificou.
Nenhuma funcionalidade nova de negócio foi adicionada; o escopo manteve-se na
fundação técnica.

## Resultado da revisão

Foram identificados 7 pontos. Um deles (segurança em produção) era uma lacuna
real; os restantes eram melhorias de robustez/arquitectura/qualidade.

| # | Severidade | Problema | Resolução |
| - | ---------- | -------- | --------- |
| 1 | **Alta** | `internal_debug_router` (incluindo `/boom`, que devolve 500 deliberado, e `/echo`) era montado **em produção**, aumentando a superfície de ataque. | Router de diagnóstico passa a ser montado apenas quando `app_env != "production"` (mesmo padrão do `content_renderer` para rotas dev-only). |
| 2 | Média | `app` era um singleton criado no import, dificultando testar caminhos dependentes do ambiente (produção, falha de config). | Introduzida a factory `create_app(settings=None)`; `app = create_app()` mantém-se para o Uvicorn. |
| 3 | Média | Settings lidas de forma inconsistente: handlers/lifespan usavam um global de import; `security`/`health` chamavam `get_settings()`. | Settings injectadas em `app.state.settings` e lidas a partir de `request.app.state.settings` (injecção explícita, sem singleton no caminho do pedido). |
| 4 | Média | `hmac.compare_digest` sobre `str` levanta `TypeError` com tokens não-ASCII → potencial 500 em vez de 403. | Comparação passa a ser feita sobre bytes UTF-8. |
| 5 | Média | `StarletteHTTPException` não-404 (p.ex. 405) era rotulada `internal_error`, com incoerência código/status. | Mapeamento por classe de status: 404 → `not_found`; outros 4xx → `invalid_payload` (preservando o status original); 5xx → `internal_error`. |
| 6 | Baixa | Logs em formato misto (Uvicorn texto + JSON da app), timestamps em hora local, `redact()` aplicado duas vezes por registo. | Loggers do Uvicorn unificados no handler JSON da raiz; timestamps em UTC ISO-8601; uma única passagem de redacção. |
| 7 | Baixa | Fixture `client_with_token` duplicada em dois módulos; teste de "token fora dos logs" frágil (um `configure_logging` por teste apagaria o handler do `caplog`). | Fixtures centralizadas em `conftest.py` (factory + lifespan via context manager); teste de redacção em logs reescrito com um handler de captura próprio, robusto. |

## Ficheiros alterados

```text
app/main.py            — reescrito como factory create_app(); gating de produção; mapeamento 4xx/5xx; handlers parametrizados por settings
app/core/security.py   — settings via request.app.state; compare_digest sobre bytes UTF-8
app/core/logging.py    — timestamps UTC; redacção única; unificação dos loggers do Uvicorn
app/api/health.py      — lê settings de request.app.state
tests/conftest.py      — fixtures factory-based (client, client_with_token, internal_token), lifespan via context manager
tests/test_security.py — usa fixtures partilhadas; unit test de _tokens_match com não-ASCII; teste de logs robusto
tests/test_errors.py   — usa fixtures partilhadas; novo teste de 405 → invalid_payload
README.md              — secções de factory, gating de produção, DI por app.state, logging unificado
```

## Ficheiros criados

```text
tests/test_app_factory.py                  — gating de rotas em produção + falha de arranque
docs/gestao/fundamentos/resultados/prompt_02b_revisao_hardening.md
```

## Decisões de desenho

- **Factory + `app.state` em vez de DI por `Depends(get_settings)`**: a
  factory já tem as settings em mãos e guarda-as na app; ler de
  `request.app.state.settings` é o caminho mais directo e mantém a app
  testável sem depender da `lru_cache` global no caminho do pedido. A
  `get_settings()` cacheada continua a ser o default em operação normal.
- **Teste de token não-ASCII ao nível unitário**: tentar enviar um header
  não-ASCII via cliente HTTP falha já na camada `httpx` (headers HTTP não
  transportam não-ASCII), pelo que o cenário realista — token não-ASCII
  definido no **ambiente** (lado `configured`) — é coberto testando
  `_tokens_match` directamente. Confirma que devolve `False` em vez de
  levantar `TypeError`.
- **405 → `invalid_payload`**: dentro dos 5 códigos do contrato não existe um
  código perfeito para "método não permitido"; `invalid_payload` (pedido do
  cliente que não pode ser processado, preservando o status 405) é
  preferível a rotular como `internal_error`. Documentado no README.
- **Mantido**: o uso de `model_validator` em `Settings` a levantar
  `ConfigError` (não-`ValueError`, logo propagado tal e qual pelo Pydantic
  v2) — testado e estável; a factory expõe esse comportamento de forma
  testável (`test_create_app_blocks_boot_in_production_without_token`).

## Comandos executados

```bash
venv/Scripts/python.exe -m pytest -q          # 26 passed
venv/Scripts/python.exe -m ruff check .       # All checks passed!

# Smoke test real com Uvicorn + token configurado
INTERNAL_API_TOKEN=smoke-token venv/Scripts/python.exe -m uvicorn app.main:app --port 8097
curl http://127.0.0.1:8097/health                                            # 200
curl http://127.0.0.1:8097/internal/_debug/ping                              # 403
curl -H "X-Internal-Token: smoke-token" http://127.0.0.1:8097/internal/_debug/ping  # 200
grep -i "smoke-token" smoke.log                                              # sem ocorrências
```

## Resultados

- **pytest**: `26 passed` (era 20; +6 entre gating de produção, falha de
  arranque, 405 e o unit test de comparação não-ASCII). 1 warning conhecido
  (`httpx`/`starlette.testclient`).
- **ruff check .**: `All checks passed!`.
- **Smoke test real**: `/health` 200, `/internal/_debug/ping` 403 sem token e
  200 com token; o log mostra agora **todas** as linhas (arranque, acesso
  Uvicorn e aplicação) em JSON estruturado com timestamps UTC, e o token não
  aparece em nenhuma linha.

## Pendências (inalteradas / novas)

- Schemas Pydantic dos contratos de negócio — IE-003.
- Remover `app/api/internal_debug.py` quando os endpoints reais (IE-004+)
  exercitarem a mesma autenticação e contrato de erro.
- Warning de depreciação `httpx`/`starlette.testclient` — não bloqueante.
- O campo `color_message` (com sequências ANSI) que o Uvicorn anexa a alguns
  registos passa agora a aparecer no JSON unificado; é inócuo (não é segredo),
  mas pode ser filtrado no futuro se se quiser um JSON mais limpo.

## Próximo passo recomendado

Avançar para **IE-003 — schemas Pydantic e contratos internos**. A factory,
o `app.state` e o gating de produção deixam o terreno preparado para
substituir `internal_debug.py` pelos routers reais de
analysis/scoring/recommendations/moments a partir de IE-004.
