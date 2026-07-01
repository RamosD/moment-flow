# BC-IE-002 — Settings do Intelligence Engine no Backend Core

> **Tipo:** implementação de configuração (settings + env + testes).
> **Fase:** `integracao_intelligence_engine` — tarefa **BC-IE-002**.
> **Data:** 2026-06-25.
> **Âmbito:** apenas configuração no `backend_core`. **Não** foi implementado o
> client HTTP nem o payload builder. **Não** foram tocados `intelligence_engine`
> nem `content_renderer`.
> **Base:** plano do [`prompt_01_analise_plano_integracao.md`](prompt_01_analise_plano_integracao.md).

---

## 0. Sumário executivo

- Consolidadas as 5 settings do Intelligence Engine, **reutilizando os padrões
  existentes** (`python-decouple` + defaults seguros), sem duplicar segredos.
- `INTELLIGENCE_ENGINE_BASE_URL` e `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` já
  existiam; o timeout foi consolidado para **10 s** (contrato §9.1: 5–10 s).
- `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` foi adicionada como **override opcional
  que por omissão reutiliza `INTERNAL_API_TOKEN`** (o segredo partilhado que o IE
  já lê — contrato §5). Não há segundo segredo a gerir.
- `INTELLIGENCE_ENGINE_ENABLED` (default `True`) e `INTELLIGENCE_ENGINE_DRY_RUN`
  (default `False`) adicionadas como **switches do caminho síncrono**,
  independentes dos `EXTERNAL_JOBS_*` (assíncrono).
- **Guarda de produção:** fora de `DEBUG`, se o IE estiver `ENABLED`, não em
  `DRY_RUN` e sem token → `ImproperlyConfigured` no arranque (fail-fast).
- `.env.example` actualizado com placeholders seguros (token vazio).
- Testes: estendidos + novos (guarda de produção). **377 passed** na suite
  completa; ruff e `manage.py check` limpos.

---

## 1. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| [`config/settings.py`](../../../../../config/settings.py) | Import de `ImproperlyConfigured`; consolidação das 5 settings do IE; helper `_require_secure_intelligence_engine_config` + chamada no arranque |
| [`.env.example`](../../../../../.env.example) | Bloco do IE: timeout 10, `ENABLED`, `DRY_RUN`, `INTERNAL_TOKEN` (placeholder vazio com nota de reuso) |
| [`apps/integrations_bridge/tests/test_settings_client_registry.py`](../../../../../apps/integrations_bridge/tests/test_settings_client_registry.py) | Presença das novas settings; bools do IE; token = `INTERNAL_API_TOKEN`; nova classe `TestIntelligenceEngineConfigGuard` (5 casos) |

> Nenhum outro ficheiro de runtime foi alterado. `clients.py`, `registry.py`,
> `services.py` e `intelligence.py` da bridge ficaram **intactos** (caminho
> assíncrono preservado).

---

## 2. Settings consolidadas (estado final)

```python
# config/settings.py (excertos)
INTELLIGENCE_ENGINE_BASE_URL = config("INTELLIGENCE_ENGINE_BASE_URL", default="http://localhost:8001")
INTELLIGENCE_ENGINE_TIMEOUT_SECONDS = config("INTELLIGENCE_ENGINE_TIMEOUT_SECONDS", default=10, cast=int)
INTELLIGENCE_ENGINE_INTERNAL_TOKEN = config("INTELLIGENCE_ENGINE_INTERNAL_TOKEN", default=INTERNAL_API_TOKEN)
INTELLIGENCE_ENGINE_ENABLED = config("INTELLIGENCE_ENGINE_ENABLED", default=True, cast=bool)
INTELLIGENCE_ENGINE_DRY_RUN = config("INTELLIGENCE_ENGINE_DRY_RUN", default=False, cast=bool)
```

| Variável | Default (dev) | Configurável por env | Notas |
|---|---|---|---|
| `INTELLIGENCE_ENGINE_BASE_URL` | `http://localhost:8001` | ✅ | Já existia |
| `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` | `10` | ✅ | Era `20`; consolidado para 10 (contrato §9.1) |
| `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` | `INTERNAL_API_TOKEN` (vazio em dev) | ✅ | Override opcional; reutiliza o segredo partilhado |
| `INTELLIGENCE_ENGINE_ENABLED` | `True` | ✅ | Switch do caminho síncrono |
| `INTELLIGENCE_ENGINE_DRY_RUN` | `False` | ✅ | Switch do caminho síncrono |

---

## 3. Decisões e justificações

### 3.1 Token: reutilizar `INTERNAL_API_TOKEN` (sem duplicar segredo)
O backlog listava `INTELLIGENCE_ENGINE_INTERNAL_TOKEN`, mas o contrato §5 define
que **os dois serviços partilham o mesmo `INTERNAL_API_TOKEN`** e o
`InternalServiceClient` já o usa por omissão. Em vez de criar um segundo segredo
(risco de divergência e de mais um valor a rodar/proteger), a setting existe mas
**faz fallback** para `INTERNAL_API_TOKEN`:

```python
INTELLIGENCE_ENGINE_INTERNAL_TOKEN = config("INTELLIGENCE_ENGINE_INTERNAL_TOKEN", default=INTERNAL_API_TOKEN)
```

Assim a variável pedida **existe e é configurável** (permite um token por-serviço
se algum dia for necessário), mas o comportamento por omissão é o do contrato:
um único segredo partilhado. Cumpre "evita duplicação e documenta a decisão".

### 3.2 Switches dedicados ao síncrono (independentes dos `EXTERNAL_JOBS_*`)
Os `EXTERNAL_JOBS_ENABLED/DRY_RUN` governam a submissão **assíncrona** (`/jobs/`
+ callback) usada pelos renderers. O caminho do IE é **síncrono** e deve poder
ser ligado/desligado sem afectar o pipeline de jobs. Daí `INTELLIGENCE_ENGINE_
ENABLED/DRY_RUN` próprios — alinhado com o isolamento exigido em BC-IE-RSK-001.

### 3.3 Timeout consolidado para 10 s
O cálculo do IE é sub-milissegundo; o tempo de parede é rede/serialização. O
contrato §9.1 sugere 5–10 s. Mantém-se configurável por env; o default passou de
20 para 10. Sem testes a depender do valor 20 (o teste existente só verifica que
é `int`).

### 3.4 Sinal de "produção" = `DEBUG=False`
O projecto **não** tem marcador de ambiente (`ENVIRONMENT`/`DJANGO_ENV`); a
convenção existente é `DEBUG`. A guarda usa `not DEBUG` como sinal de produção,
consistente com os avisos já presentes em `settings.py`.

---

## 4. Guarda de configuração insegura (produção)

```python
def _require_secure_intelligence_engine_config(*, debug, enabled, dry_run, token):
    if not debug and enabled and not dry_run and not token:
        raise ImproperlyConfigured(...)  # mensagem accionável, sem expor segredos

_require_secure_intelligence_engine_config(
    debug=DEBUG, enabled=INTELLIGENCE_ENGINE_ENABLED,
    dry_run=INTELLIGENCE_ENGINE_DRY_RUN, token=INTELLIGENCE_ENGINE_INTERNAL_TOKEN,
)
```

Tabela de comportamento:

| DEBUG | ENABLED | DRY_RUN | token | Resultado |
|:---:|:---:|:---:|:---:|---|
| False | True | False | vazio | **`ImproperlyConfigured`** (boot recusado) |
| False | True | False | definido | OK |
| False | True | True | vazio | OK (dry-run não chama) |
| False | False | — | vazio | OK (desligado não chama) |
| True | True | False | vazio | OK (conveniência de dev) |

Implementado como **helper puro** → testável directamente sem reload de settings
nem subprocess. A mensagem é accionável e **não** inclui o valor do token.

---

## 5. `.env.example` (placeholders seguros)

- `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS=10`, `INTELLIGENCE_ENGINE_ENABLED=true`,
  `INTELLIGENCE_ENGINE_DRY_RUN=false`.
- `INTELLIGENCE_ENGINE_INTERNAL_TOKEN=` (**vazio**), com nota: deixar vazio para
  reutilizar `INTERNAL_API_TOKEN`; é segredo, nunca commitar valor real; em
  produção o boot é recusado se resolver para vazio com o IE activo e sem
  dry-run.
- **Sem secrets reais** no ficheiro (confirmado).

---

## 6. Validações executadas

| Verificação | Comando | Resultado |
|---|---|---|
| Testes de settings/registry/client | `pytest apps/integrations_bridge/tests/test_settings_client_registry.py` | **31 passed** |
| Suite completa | `pytest -q` | **377 passed**, 221 warnings (pré-existentes) |
| Lint | `ruff check config/settings.py …tests/test_settings_client_registry.py` | **All checks passed** |
| Django system check | `manage.py check` | **0 issues** |

> Os warnings são pré-existentes e não relacionados (ex.: `No directory at:
> staticfiles/`, naive datetimes em testes). Nenhum introduzido por esta fase.

### 6.1 Novos testes (resumo)
- `test_integration_settings_present` — agora inclui as 3 novas settings do IE.
- `test_intelligence_engine_switches_are_bool` — `ENABLED`/`DRY_RUN` são `bool`.
- `test_intelligence_engine_token_defaults_to_shared_internal_token` — confirma a
  reutilização do `INTERNAL_API_TOKEN`.
- `TestIntelligenceEngineConfigGuard` — 5 casos cobrindo a matriz da §4.

---

## 7. Conformidade com os critérios de aceitação

- [x] Settings do IE existem/consolidadas (BASE_URL, TIMEOUT, TOKEN, ENABLED, DRY_RUN).
- [x] URL, timeout, token, enabled e dry-run configuráveis por ambiente.
- [x] Produção não permite token vazio quando inseguro (guarda `ImproperlyConfigured`).
- [x] `.env.example` sem secrets reais (placeholders seguros).
- [x] Testes/config checks passam (377 passed; ruff/check limpos).
- [x] Relatório lista ficheiros, decisões, validações, pendências e próximo passo.

---

## 8. Pendências / decisões deixadas em aberto

- **PD-5 (resolvida):** default de timeout → 10 s.
- **Marcador de ambiente:** a guarda usa `DEBUG`. Se mais tarde se introduzir um
  `ENVIRONMENT`/`DJANGO_ENV` explícito, a condição deve passar a usá-lo.
- **Default de teste para dry-run do IE:** o `conftest.py` raiz força
  `EXTERNAL_JOBS_DRY_RUN=True` (async). Não se adicionou equivalente para o IE
  síncrono porque o client ainda não existe; deverá ser considerado em BC-IE-003/
  BC-IE-005 (forçar `INTELLIGENCE_ENGINE_DRY_RUN=True` por omissão nos testes que
  exercitem o serviço, para nunca fazer HTTP real).
- **Persistência de snapshots:** continua fora do MVP (PDEC-002).

---

## 9. Próximo passo recomendado

Avançar para **BC-IE-003 — client síncrono**: criar
`apps/integrations_bridge/intelligence_sync.py` (`IntelligenceEngineSyncClient`)
sobre o `InternalServiceClient` existente, lendo
`INTELLIGENCE_ENGINE_BASE_URL`/`TIMEOUT_SECONDS`/`INTERNAL_TOKEN`, fazendo
`POST /intelligence/campaign`, normalizando o envelope de resposta do IE
(sucesso vs `error.code`) e mapeando timeout/403/422/5xx/JSON-inválido para erros
tipados — com testes de mock HTTP reutilizando o padrão `opener_returning`/
`opener_raising`.
