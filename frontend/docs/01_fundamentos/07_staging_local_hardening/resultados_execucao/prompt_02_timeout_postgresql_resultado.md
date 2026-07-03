# Prompt 02 — Timeout curto de ligação PostgreSQL — Resultado

**Data:** 2026-07-03
**Fase:** `07_staging_local_hardening` (STG-HARD-002)
**Âmbito:** adicionar e validar um timeout curto de ligação PostgreSQL no Backend
Core, para que pedidos normais deixem de ficar pendurados por minutos quando o
PostgreSQL local está indisponível — sem quebrar SQLite/dev, sem retries
infinitos, sem expor credenciais.
**Estado de execução:** `executado` — configuração introduzida, validada com
PostgreSQL up (`check`, `showmigrations`, 455 testes) e com PostgreSQL down
(medições reais antes/depois via paragem controlada do container), recuperação
confirmada. **Um achado do relatório da fase 06 foi corrigido**: `/ready/` não
tinha, de facto, nenhuma protecção prévia — ver §4.

---

## 1. Contexto e achado original

A fase 06 (`prompt_10_observabilidade_local_resultado.md` §6.1) documentou:
"pedidos normais à BD não têm timeout curto... ao contrário do `/ready/` (que
usa `HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS`, curto e configurado)". Um pedido
normal (`GET /workspaces/`) ficou pendurado >2 minutos com o PostgreSQL parado,
sem erro, até ser interrompido manualmente. Ficou registado como risco a
corrigir numa fase de hardening — esta.

## 2. Configuração `DATABASES` inspeccionada

`backend_core/config/settings.py` (antes desta alteração): `DB_ENGINE=sqlite`
(default) usa `django.db.backends.sqlite3`; `DB_ENGINE=postgres` usa
`django.db.backends.postgresql` com `NAME`/`USER`/`PASSWORD`/`HOST`/`PORT` lidos
de env — **sem `OPTIONS`**, logo sem `connect_timeout`. `CONN_MAX_AGE` nunca
definido (default Django `0` — uma ligação nova por pedido), confirmado por
inspecção directa das settings resolvidas em runtime.

## 3. Alteração introduzida

`backend_core/config/settings.py`:

```python
DB_CONNECT_TIMEOUT_SECONDS = config("DB_CONNECT_TIMEOUT_SECONDS", default=5, cast=int)

if config("DB_ENGINE", default="sqlite") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER"),
            "PASSWORD": config("DB_PASSWORD"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
            "OPTIONS": {
                "connect_timeout": DB_CONNECT_TIMEOUT_SECONDS,
            },
        }
    }
else:
    DATABASES = {  # SQLite — inalterado, sem OPTIONS.
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"},
    }
```

- **Nova variável de ambiente:** `DB_CONNECT_TIMEOUT_SECONDS` (opcional,
  default `5`). Documentada em `backend_core/.env.example` com comentário, sem
  segredo.
- **Só aplicada quando `DB_ENGINE=postgres`** — o ramo `sqlite` do `if/else`
  nunca recebe `OPTIONS`; confirmado por inspecção directa (`settings.DATABASES`
  resolvido com `DB_ENGINE=sqlite` mostra `OPTIONS={}`, sem `connect_timeout`).
- **Sem retries** — `connect_timeout` só limita a espera por uma ligação;
  não introduz nenhuma repetição automática.
- **`/ready/` protegido pela mesma alteração** — `_check_database()`
  (`apps/integrations_bridge/health.py`) usa `connections["default"]`, ou seja,
  a mesma configuração `DATABASES` — nenhuma alteração adicional foi necessária
  em `health.py`.

## 4. Achado corrigido do relatório da fase 06

O relatório do Prompt 10 (fase 06) afirmava que `/ready/` já tinha protecção
via `HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS`. **Isto estava incorrecto** —
confirmado por leitura de código (`_check_database()` não recebe nem usa
nenhum timeout) e por medição directa nesta iteração: **com o código anterior
a esta alteração**, `/ready/` ficou pendurado **130.6s** (medido, não
extrapolado) antes de responder `503` com PostgreSQL parado —
`HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS` protege apenas as sondas HTTP ao
Intelligence Engine/Content Renderer (`check_dependencies()`), nunca a
verificação da base de dados. Este relatório substitui essa afirmação; ver
`runbook_staging_local.md` §14 (actualizado) para a correcção formal.

## 5. Medições antes/depois (PostgreSQL parado de forma controlada)

Metodologia: `git stash` isolou temporariamente a alteração para obter uma
baseline "antes" real (não apenas extrapolada da fase 06), no mesmo ambiente,
com o mesmo container `chartrex_staging_postgres` parado via `docker stop` /
reiniciado via `docker start`. Todas as medições usam `Stopwatch` real à volta
de um pedido HTTP isolado (não sobreposto a outros pedidos).

| Cenário | Endpoint | Antes (sem `connect_timeout`) | Depois (`DB_CONNECT_TIMEOUT_SECONDS=5`) |
|---|---|---:|---:|
| PostgreSQL **up** | `GET /ready/` | 423ms | 224–247ms |
| PostgreSQL **up** | `POST /auth/token/` (lê BD) | 1722ms | 945–1266ms |
| PostgreSQL **down** | `GET /ready/` | **130.6s** (503) | **5.1–5.3s** (503) |
| PostgreSQL **down** | `POST /auth/token/` (lê BD) | **>150s** (client desistiu; servidor continuava preso) | **~31s** (500) — ver §6 |
| PostgreSQL **restart** | ambos | recuperação `200` confirmada | recuperação `200` confirmada |

`/ready/`: melhoria de **~25×** (130.6s → 5.1–5.3s), consistente e repetida
(3 medições independentes, `5.07s` / `5.12s` / `5.32s`).

## 6. Risco residual identificado e não corrigido (fora do âmbito estreito desta tarefa)

Um pedido "normal" cujo primeiro contacto com a BD é o próprio pedido (ex.:
`POST /api/v1/auth/token/`, sem sessão/ligação prévia no processo) fica
bounded a **~31s**, não aos ~5s configurados. Investigado até à causa (sem
alterar produto):

1. Um script isolado (fora do caminho HTTP, chamando
   `User._default_manager.get_by_natural_key(...)` directamente após
   `django.setup()`) fica bounded a **5.07s** — exactamente igual ao
   `/ready/`. **O `connect_timeout` em si funciona correctamente.**
2. Um teste directo `psycopg.connect(..., connect_timeout=5)` (sem Django) fica
   bounded a **5.07s** — confirma que não é um problema psycopg/libpq/Windows.
3. A diferença só aparece no caminho HTTP real, e só quando a excepção não é
   tratada (500). Com `DEBUG=True` (staging local, `backend_core/.env.staging.local`),
   Django renderiza a página de erro técnica, que reavalia os
   `context_processors` de `TEMPLATES` (`django.contrib.auth.context_processors.auth`,
   entre outros) — cada um tenta a sua própria ligação à BD, cada uma já
   limitada a `~5s`, mas em série, não em paralelo, somando até aos `~31s`
   observados (confirmado por log: um único traceback de
   `psycopg.errors.ConnectionTimeout` por pedido, sem retries explícitos no
   código da aplicação — o tempo extra é inteiramente da máquina de
   renderização de erro do Django em modo `DEBUG`, não de nenhuma lógica desta
   fase nem de retries escondidos).

**Decisão:** não corrigido nesta iteração. Não há uma causa "inequívoca e
limitada" que justifique tocar na máquina de excepções do Django (ex.:
handler DRF customizado ou `DEBUG=False`) sem alargar o âmbito desta tarefa —
e mesmo `~31s` já é uma melhoria enorme e mensurável sobre os `>150s`/minutos
anteriores. Registado como risco residual explícito (ver §9), não escondido.

## 7. Validações executadas

| Validação | Resultado |
|---|---|
| `manage.py check` (PostgreSQL up) | ✅ `System check identified no issues` |
| `manage.py showmigrations` (PostgreSQL up) | ✅ todas as apps `[X]` (nenhuma pendente) |
| `settings.DATABASES["default"]["OPTIONS"]` com `DB_ENGINE=postgres` | ✅ `{'connect_timeout': 5}` |
| `settings.DATABASES["default"]["OPTIONS"]` com `DB_ENGINE=sqlite` | ✅ `{}` — sem `connect_timeout`, sem quebra |
| `pytest apps/core apps/workspaces` (SQLite, sem overrides — dev normal) | ✅ **38 passed** |
| `pytest apps/workspaces apps/core apps/campaign_actions apps/reports apps/content` (PostgreSQL) | ✅ **279 passed** |
| `pytest apps/integrations_bridge` (PostgreSQL, execução limpa) | ✅ **176 passed** |
| `GET /ready/` com PostgreSQL down | ✅ `503` em `5.1–5.3s` (3 medições) |
| `POST /auth/token/` com PostgreSQL down | ✅ `500` em `~31s` (bounded, não infinito) — risco residual documentado (§6) |
| Recuperação após `docker start postgres` | ✅ `/ready/` e `/auth/token/` voltam a `200`/`401` normal |
| Grep `DB_PASSWORD=`, `Authorization: Bearer`, `X-Internal-Token:`, DSN com password | ✅ 0 ocorrências em `.local-runtime/logs/backend_core.{out,err}.log` e nos diffs desta iteração |
| `scripts/check-forbidden-ports.ps1` | ✅ `OK` |

### Nota sobre uma execução de teste contaminada

Uma primeira tentativa de `pytest apps/workspaces apps/core apps/campaign_actions
apps/reports apps/content apps/integrations_bridge` produziu 71 erros em
`apps/integrations_bridge` — **causa identificada, não é regressão de
produto**: o container PostgreSQL foi parado (para o teste de timing do §5)
enquanto essa execução de `pytest` ainda decorria em segundo plano, contra a
mesma base de dados de teste real. `apps/integrations_bridge` é a última pasta
na lista e por isso a única afectada (679 testes anteriores já tinham
terminado). Re-executada isoladamente, com o PostgreSQL estável do início ao
fim: **176 passed, 0 failed** — confirma que os 71 erros eram inteiramente
contaminação da minha própria acção concorrente, não um efeito da alteração de
`connect_timeout`.

## 8. Ficheiros alterados

| Ficheiro | Operação |
|---|---|
| `backend_core/config/settings.py` | `DB_CONNECT_TIMEOUT_SECONDS` + `OPTIONS.connect_timeout` só no ramo `postgres` |
| `backend_core/.env.example` | novo comentário + `DB_CONNECT_TIMEOUT_SECONDS=5` |
| `frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/runbook_staging_local.md` | §14 corrigida (achado `/ready/` da fase 06 estava incorrecto) e complementada com o comportamento medido; §18 (troubleshooting) e §21 (limitações) actualizadas |
| `frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/prompt_02_timeout_postgresql_resultado.md` | **criado** (este relatório) |

`backend_core/.env.staging.local` **não foi alterado** (secret-bearing;
`DB_CONNECT_TIMEOUT_SECONDS` fica ausente ali de propósito, usando o default
`5` de `settings.py` — comportamento já validado em todas as medições acima).

## 9. Riscos remanescentes

| Risco | Severidade | Estado |
|---|---|---|
| Caminho de erro HTTP de um pedido "normal" (não `/ready/`) fica bounded a `~31s`, não `~5s`, por causa da página de erro técnica do Django em `DEBUG=True` (§6) | Baixo-Médio | Documentado, causa identificada, não corrigido (fora do âmbito estreito de STG-HARD-002); `~31s` continua a ser uma melhoria de ordens de magnitude sobre o comportamento anterior (minutos/infinito) |
| `manage.py runserver` falha a arrancar (excepção não tratada em `check_migrations()`) se o PostgreSQL já estiver down **no momento do arranque** do processo (não é o cenário original desta tarefa — esse era sobre um processo já a correr que perde a BD a meio) | Baixo | Observado incidentalmente durante a validação; comportamento pré-existente do próprio Django (`check_migrations()` só apanha `ImproperlyConfigured`, não `OperationalError`), não introduzido nem agravado por esta alteração; fora do âmbito desta tarefa |
| `DB_CONNECT_TIMEOUT_SECONDS=5` é um valor de staging local; não avaliado para latências de rede maiores (staging não-local/produção) | Baixo | A rever nessa fase futura, se/quando existir |

## 10. Critérios de aceitação — verificação

- ✅ Pedidos normais deixam de ficar pendurados por minutos (`>150s` → `~31s`
  no pior caso observado; `/ready/`: `130.6s` → `~5.2s`).
- ✅ `/ready/` continua rápido (na verdade, ficou protegido pela primeira vez —
  ver §4).
- ✅ Recuperação após restart do PostgreSQL confirmada nos dois lados
  (antes/depois da alteração).
- ✅ SQLite/dev não quebra — `OPTIONS={}` confirmado, 38/38 testes SQLite
  `PASS`.
- ✅ Testes relevantes passam — 455/455 (`279 + 176`) contra PostgreSQL real.
- ✅ Configuração documentada (`.env.example`, `runbook_staging_local.md`).
- ✅ Nenhum secret em logs/docs/código (greps dedicados, §7).

Nenhum critério de rejeição ocorreu: sem incompatibilidade com SQLite, sem
timeout "demasiado alto para ser útil" (5s é curto e o comportamento `/ready/`
prova-o), sem retry infinito, sem credenciais em erros, sem quebra de
migrations/testes, sem alteração de produto além do estritamente pedido.

## 11. Próximo passo recomendado

1. Seguir para **STG-HARD-003** (credenciais MinIO não-root) ou **STG-HARD-001**
   (estabilizar E2E local), conforme prioridade do operador — ambas já têm
   trabalho preparatório desta sessão (STG-HARD-001 tem uma alteração de wait
   de E2E já feita, ainda por validar em execução real da stack).
2. Considerar, numa fase futura (não esta), se vale a pena reduzir o caminho
   de erro `DEBUG=True` de `~31s` para mais perto de `~5s` — não decidido aqui,
   apenas medido e registado (§6, §9).
3. Nenhuma acção necessária sobre o achado incidental do `runserver` que não
   arranca com PostgreSQL já down no arranque (§9) — comportamento pré-existente
   do Django, fora do âmbito desta tarefa; registar como possível item de
   backlog futuro se algum dia isso incomodar um operador real.
