# Prompt 09 — Validar integração real (Campaign Actions)

> Fase: `02_campaign_actions_recommendation_to_execution`
> Backlog de referência: `01_backlog.md` (CA-014)
> Relatórios anteriores: prompt_01 a prompt_08

---

## Execução 2026-06-30 (Iteração 01)

### Estado da execução

**Parcialmente concluído — validação interactiva PENDENTE por limitação de
ambiente.** As validações técnicas estáticas (lint, build, greps de segurança)
passaram. A validação integrada real (login → workspace → campanha → War Room →
criar action) **não foi possível** porque o Backend Core (Django) não está a
correr em `localhost:8000` e o frontend não está a correr em `localhost:5173`.
Conforme instrução, **não foi feito troubleshooting de ambiente** e nenhum mock
foi usado para declarar sucesso.

### Resumo objectivo

CA-014 pedia validar a feature contra o Backend Core real. A pré-condição —
serviços reais a correr — não se verifica neste ambiente. A descoberta concreta
está documentada abaixo. Nenhuma falha de código directamente relacionada com a
validação foi encontrada (as validações estáticas estão verdes); por isso
**nenhuma correcção de código foi aplicada**.

### Descoberta de ambiente (factual)

Sondagem dos serviços esperados:

| Alvo | Resultado | Interpretação |
|---|---|---|
| `GET http://localhost:8000/` | **HTTP 200**, `Server: uvicorn` | Há um serviço ASGI a responder |
| `GET http://localhost:8000/admin/` | **HTTP 404** | O Django Backend Core registaria `/admin/` |
| `GET http://localhost:8000/api/v1/schema/` | **HTTP 404** | `config/urls.py` regista esta rota — deveria existir |
| `GET http://localhost:8000/api/v1/auth/` | **HTTP 404** | `config/urls.py` regista esta rota — deveria existir |
| `GET http://localhost:8000/api/v1/docs/` | **HTTP 404** | `config/urls.py` regista esta rota — deveria existir |
| `localhost:5173` (frontend) | **Sem listener / timeout** | Vite dev server não está a correr |

**Conclusão**: o serviço em `:8000` é **uvicorn** (servidor ASGI, típico de
FastAPI) que devolve **200 em `/`** e **404 em todas as rotas do Backend Core**
(`/admin/`, `/api/v1/schema/`, `/api/v1/auth/`, `/api/v1/docs/`). O Django
Backend Core não tem rota raiz `/` (logo `/` daria 404) e teria `/admin/` e
`/api/v1/schema/`. Portanto **o que está em `:8000` NÃO é o Backend Core** — é,
muito provavelmente, o `intelligence_engine` ou o `content_renderer` (ambos
FastAPI/uvicorn).

Como a `VITE_BACKEND_API_BASE_URL` aponta para `http://localhost:8000/api/v1`,
**iniciar o frontend agora apontá-lo-ia para um serviço que não é o Backend
Core** — o login falharia com 404 e qualquer "validação" seria enganosa.
Iniciar o frontend nessas condições não constitui validação real e por isso não
foi feito.

Decisão (conforme instrução "não fazer troubleshooting de ambiente"): não foi
iniciado o Django, não foi iniciado o Vite, não foi alterada a base URL. A
validação interactiva fica **pendente** até existir um ambiente com o Backend
Core (Django) real a correr em `:8000`.

### Checklist CA-014 — estado

| Passo | Estado |
|---|---|
| Confirmar Backend Core real em `:8000` | ❌ Não confirmado — serviço em `:8000` não é o Backend Core (uvicorn, 404 nas rotas Django) |
| Confirmar frontend em `:5173` | ❌ Não está a correr |
| `VITE_BACKEND_API_BASE_URL` correcta | ✅ `http://localhost:8000/api/v1` (verificado em `.env.local` / `.env.example`) |
| Login real | ⏳ Pendente (sem Backend Core) |
| Seleccionar workspace real | ⏳ Pendente |
| Abrir campanha real | ⏳ Pendente |
| Abrir War Room | ⏳ Pendente |
| Recommendations renderizam | ⏳ Pendente (validável só em runtime real) |
| Botões de acção / estado indisponível honesto | ⏳ Pendente em runtime; ✅ verificado por código (prompt_04/07) |
| Criação real de action | ⏳ Pendente |
| Campaign Actions Panel lista dados reais | ⏳ Pendente |
| Recommendation mostra estado coerente | ⏳ Pendente |
| reviewed/dismissed | ✅ Confirmado indisponível por contrato (prompt_06) — nada a validar em runtime |
| Outputs/reports/media kits independentes | ⏳ Pendente em runtime; ✅ verificado por código (prompt_07, isolamento por query) |
| Erros tratados | ⏳ Pendente em runtime; ✅ verificado por código (prompt_07) |

### Ficheiros criados ou alterados

**Nenhum ficheiro de runtime foi alterado.** Não foram encontradas falhas de
código directamente relacionadas com a validação (lint, build e greps verdes;
o caminho interactivo não foi exercitável). Não foram criados mocks.

Criado:
- `docs/.../resultados_execucao/prompt_09_validar_integracao_real_resultado.md`
  (este ficheiro).

### Validações executadas e resultado

- ✅ `pnpm lint` → `eslint .` sem erros nem avisos.
- ✅ `pnpm build` → `tsc -b && vite build`, 230 módulos transformados, ~3.0s,
  sem erros de tipo.
- ✅ Greps de segurança (frontend `src/`):
  - `X-Internal-Token` / `INTERNAL_TOKEN` — apenas no guard defensivo de
    `client.ts` e em comentário de `campaign-action-api.ts`. Nunca enviado.
  - `INTERNAL_API_TOKEN` — não encontrado.
  - `intelligence_engine` / `content_renderer` / portas internas — não
    encontrados em `src/`. Toda a rede passa por `apiClient` → Backend Core.
- ➖ `python manage.py check` — **não aplicável**: nenhum código backend foi
  alterado nesta fase (todos os prompts foram frontend-only).
- ➖ Validação interactiva / browser — **PENDENTE por ambiente** (sem Backend
  Core real em `:8000`; frontend não iniciado). Sem troubleshooting, conforme
  instrução.
- ➖ Tokens — não expostos (não foi feito login; nenhuma credencial manipulada).

### Aceitação parcial da fase (conforme backlog §16, Resultado B/C)

O backlog prevê explicitamente aceitação parcial quando a validação real não é
possível, desde que:

- a lacuna esteja documentada → ✅ (este relatório + arquitectura);
- a UI não finja persistência → ✅ (verificado por código; 3 endpoints reais,
  `Promise.allSettled`, sem mocks runtime);
- os tipos sem suporte estejam claramente marcados como indisponíveis ou
  omitidos → ✅ (`CAMPAIGN_ACTION_CAPABILITIES`; mark_reviewed/dismiss omitidos);
- exista backlog complementar para o Backend Core → ✅ (CA-PDEC-006 documentado).

A fase **não** declara "Recommendation-to-Execution validado em runtime real".
Declara: **implementação completa e green em validações estáticas; validação
integrada real pendente de um ambiente com o Backend Core a correr.**

### Pendências, riscos e próximo passo recomendado

- **CA-014 permanece PENDENTE**: requer um ambiente com:
  1. Django Backend Core a correr em `localhost:8000` (a responder a
     `/api/v1/schema/`, `/api/v1/auth/`, `/admin/`);
  2. frontend Vite em `localhost:5173`;
  3. utilizador dev, workspace, e campanha reais seedados.
  - **Importante**: confirmar que o serviço em `:8000` é o Django Backend Core
    e **não** o `intelligence_engine`/`content_renderer` (uvicorn) — actualmente
    é um serviço ASGI que devolve 404 nas rotas do Backend Core. Validar a
    base URL antes de exercitar o fluxo.
- **Risco**: se a validação real for feita contra o serviço errado em `:8000`
  (um serviço interno FastAPI), a UI falharia com 404 e/ou o frontend estaria a
  comunicar com um serviço interno — violação arquitectural. O próximo executor
  deve garantir que `:8000` é o Backend Core (Django) antes de validar.
- **CA-015 (relatório final da fase)**: pode ser produzido agora como estado
  honesto, marcando CA-014 como pendente de ambiente, ou após CA-014 ser
  concluído num ambiente adequado.
- **CA-011 (ligar acções a outputs)**: continua pendente; só possível via
  metadata hoje.
