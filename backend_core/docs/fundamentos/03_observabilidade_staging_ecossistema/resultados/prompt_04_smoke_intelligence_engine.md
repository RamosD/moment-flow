# OBS-STG-004 — Relatório de execução: Smoke test Backend Core ↔ Intelligence Engine

> Relatório de execução do prompt 04. Altera runtime de forma **aditiva** (novo
> management command + testes + docs). **Não** altera o Intelligence Engine nem o
> Content Renderer.
>
> Fase: Observabilidade e Staging Técnico do Ecossistema.
> Backlog: [`../01_backlog.md`](../01_backlog.md).
> Data: 2026-06-25. Modelo recomendado (backlog §15): opus.

---

## 1. Objectivo

Criar/consolidar um smoke test **opt-in** para validar rapidamente o loop real
`Backend Core → Intelligence Engine → Backend Core`, reutilizando o que já existe.

---

## 2. O que já existia (e foi reutilizado)

O teste opt-in **`apps/campaigns/tests/test_intelligence_real_loop.py`** (criado na
fase de integração IE↔BC) já cumpre o núcleo do objectivo e foi **reutilizado sem
alterações**. Cobre, guardado por `RUN_REAL_IE`:

| Requisito do prompt | Coberto pelo teste existente |
|---|---|
| Corre só de forma explícita (`RUN_REAL_IE=1`) | ✅ `pytest.mark.skipif` |
| Sucesso real com as 6 chaves (`analysis`, `scores`, `grade`, `moments`, `recommendations`, `summary`) | ✅ `test_real_loop_returns_intelligence` + `test_real_loop_via_django_http_endpoint` |
| Falha com IE indisponível controlada | ✅ `test_real_loop_unavailable_is_controlled` (porta fechada → `IntelligenceUnavailableError`) |
| Token não aparece nos logs | ✅ `assert TOKEN not in caplog.text` (2 testes) |
| Campanha de teste por factory | ✅ `_rich_campaign()` |
| `ENABLED=True`, `DRY_RUN=False` | ✅ `_point_at_live_engine()` |

**Confirmação de que continua a saltar correctamente** (suite completa desta fase):

```text
SKIPPED apps/campaigns/tests/test_intelligence_real_loop.py:87  (RUN_REAL_IE não definido)
SKIPPED apps/campaigns/tests/test_intelligence_real_loop.py:106
SKIPPED apps/campaigns/tests/test_intelligence_real_loop.py:119
```

---

## 3. O que faltava (e foi complementado, sem duplicar)

O teste opt-in valida o caminho completo **mas exige test DB e o pytest runner**,
e **não valida explicitamente a configuração** nem serve um operador em staging. O
prompt pede ainda "validar configuração necessária" e permite um "management
command/script simples" (backlog OBS-STG-004 / decisão OBS-PDEC-002). Por isso
adicionou-se:

### 3.1 Management command `smoke_intelligence_engine`

`apps/campaigns/management/commands/smoke_intelligence_engine.py` — smoke
**operacional, sem base de dados**:

- **Valida a configuração** e falha cedo e claramente: `INTELLIGENCE_ENGINE_BASE_URL`,
  `INTELLIGENCE_ENGINE_INTERNAL_TOKEN`/`INTERNAL_API_TOKEN` (não vazio),
  `INTELLIGENCE_ENGINE_ENABLED=True`, `INTELLIGENCE_ENGINE_DRY_RUN=False`.
- Constrói um **payload sintético representativo** (sem ORM, sem escrever na DB) e
  chama o IE **real** via `IntelligenceEngineClient` (o mesmo cliente que o Django
  usa). Não duplica o builder dinâmico (esse é exercido pelo teste opt-in).
- Confirma `status=completed` e as **6 chaves**.
- **Falha controlada** (sem stack trace, `CommandError` → exit ≠ 0) em
  indisponível/timeout/4xx/5xx.
- **Token nunca impresso**: a config é reportada como `token=configured` /
  `token=not_configured`.
- Opção `--reference-date YYYY-MM-DD` (default: hoje, UTC).

### 3.2 Testes do command (não opt-in; correm na suite normal)

`apps/campaigns/tests/test_smoke_intelligence_command.py` — **11 testes** com
cliente IE **falso** (sem rede): validação de config (disabled, dry-run, token
vazio, base_url vazio, data inválida), sucesso com as 6 chaves, **token nunca
impresso** (`token=configured`, valor ausente de stdout/stderr), status inesperado,
chaves em falta, e falhas controladas (unavailable, HTTP 403). Estes testes dão
cobertura de CI ao **wiring** do command sem depender de um IE a correr.

### 3.3 Documentação

`smoke_intelligence_engine.md` — guia curto com as **duas** formas (command e
pytest opt-in), pré-condições, saída esperada, falhas controladas e nota de
segurança. Referenciado a partir da matriz operacional.

---

## 4. Ficheiros criados / alterados

| Ficheiro | Acção |
|---|---|
| `apps/campaigns/management/__init__.py` | **Criado** (pacote) |
| `apps/campaigns/management/commands/__init__.py` | **Criado** (pacote) |
| `apps/campaigns/management/commands/smoke_intelligence_engine.py` | **Criado** (command) |
| `apps/campaigns/tests/test_smoke_intelligence_command.py` | **Criado** (11 testes) |
| `docs/.../03_observabilidade_staging_ecossistema/smoke_intelligence_engine.md` | **Criado** (guia) |
| `docs/.../matriz_operacional_servicos.md` | Alterado (1 linha — referência ao guia) |
| `apps/campaigns/tests/test_intelligence_real_loop.py` | **Reutilizado, não alterado** |

**Não alterados:** `intelligence_engine/`, `content_renderer/` (regra do backlog).

---

## 5. Comandos e resultados

| Validação | Comando | Resultado |
|---|---|---|
| Testes do command (mocked) | `pytest apps/campaigns/tests/test_smoke_intelligence_command.py -q` | **11 passed** (0.12s) |
| Lint | `ruff check apps/campaigns/management/ …test_smoke_intelligence_command.py` | **All checks passed!** |
| Registo do command | `manage.py smoke_intelligence_engine --help` | OK (command descoberto, `--reference-date` listado) |
| Opt-in continua a saltar | `pytest -q` (suite completa) | os 3 testes do loop real aparecem como `SKIPPED` (esperado) |

> O **sucesso real** (IE a correr) é verificável com qualquer das duas opções —
> ver o guia. Não foi executado aqui contra um IE vivo porque o ambiente desta
> sessão não tem o serviço a correr; a evidência de loop real já existe (fase
> IE↔BC, `prompt_09`) e os caminhos de sucesso/falha estão cobertos por testes
> (mocked para o command; opt-in para o pytest). **Limitação documentada**, não
> inventada.

---

## 6. Conformidade com os critérios de aceitação

| Critério | Estado |
|---|---|
| Existe smoke test IE documentado | ✅ teste opt-in + command + guia `smoke_intelligence_engine.md` |
| Corre apenas de forma explícita | ✅ `RUN_REAL_IE` (pytest) / invocação manual do command |
| Sucesso real verificável quando IE activo | ✅ ambas as opções (ver guia) |
| Falha com IE desligado coberta/documentada | ✅ teste opt-in (porta fechada) + testes do command (unavailable/403) + guia |
| Token não aparece nos logs | ✅ `caplog` (opt-in) + `token=configured`/valor ausente (command + testes) |
| Testes passam ou limitações documentadas | ✅ 11 novos passam; loop real é opt-in/manual (limitação documentada) |
| Relatório lista reutilizado/criado/comandos/resultados/próximo passo | ✅ este documento |

---

## 7. Próximo passo recomendado

**OBS-STG-005 — Smoke test operacional Backend Core ↔ Content Renderer.**
Consolidar o harness existente (`content_renderer/scripts/run-e2e-postgres.ps1` +
`e2e_backend_core.py`) como smoke documentado/checklist executável, validar
health/token/criação de job/202/callback/`ExternalJobReference`/asset e tratar
explicitamente "renderer desligado" — **sem alterar o renderer**.
