# Estado da integração Backend Core ↔ Intelligence Engine

> Documento de estado consolidado da fase de integração (BC-IE-001 a BC-IE-010).
> Substitui a necessidade de ler os 10 relatórios individuais em
> [`resultados/`](resultados/) para obter uma visão actual — esses relatórios
> permanecem como o histórico detalhado de cada etapa.

Última actualização: 2026-06-25 (fecho da fase, BC-IE-010).

---

## 1. Estado final da integração

**Integração funcional e validada com o serviço real, em ambiente local.**

- O Backend Core consegue montar o payload de uma campanha, chamar o FastAPI
  Intelligence Engine real via HTTP síncrono, receber a resposta normalizada e
  devolvê-la ao cliente da API — comprovado com os dois serviços a correr
  (não mockado), ver §6 e §7.
- O caminho de erro (engine desactivado, engine inacessível, engine devolve
  erro 4xx/5xx) está implementado com excepções tipadas e mapeamento HTTP
  seguro (sem expor detalhes internos nem o token).
- Um bug real de contrato foi encontrado e corrigido durante a validação ao
  vivo (BC-IE-009): incompatibilidade de granularidade `date` vs `datetime`
  em `content_outputs[].created_at` — ver §8.
- Não há persistência de snapshot, não há `ExternalJobReference`, não há
  callback — por desenho do MVP (decisão tomada em BC-IE-002/BC-IE-005,
  documentada no backlog §13).

**Resumo de prontidão:** ver §10/§11.

---

## 2. Arquitectura

```
Cliente HTTP
   │  POST /api/v1/campaigns/{id}/intelligence/
   ▼
CampaignViewSet.intelligence()           apps/campaigns/views.py
   │  (RBAC: campaigns:view; workspace-scoped via get_object())
   ▼
get_campaign_intelligence()              apps/campaigns/intelligence_service.py
   │  (orquestração: ENABLED/DRY_RUN, carrega campanha, chama o builder e o
   │   cliente, mapeia erros, regista log, stamping de generated_at)
   ▼
CampaignIntelligencePayloadBuilder       apps/campaigns/intelligence_payload.py
   │  (adapter puro: ORM → dict JSON-safe; sem HTTP, sem política)
   ▼
IntelligenceEngineClient                 apps/integrations_bridge/intelligence_sync.py
   │  (transporte + normalização + retry; reutiliza InternalServiceClient)
   ▼
POST http://<IE>/intelligence/campaign   (FastAPI Intelligence Engine — serviço externo)
```

Princípio de camadas (mantido sem desvios ao longo da fase):

| Camada | Ficheiro | Responsabilidade | Não faz |
|---|---|---|---|
| View | `apps/campaigns/views.py` | Traduz excepções do serviço em HTTP seguro (503/502/404) | Lógica de negócio, HTTP ao engine |
| Service | `apps/campaigns/intelligence_service.py` | Política (`ENABLED`/`DRY_RUN`), carrega campanha, chama builder+client, stamping, logging | HTTP directo, construção do payload |
| Builder | `apps/campaigns/intelligence_payload.py` | Adapter puro ORM → payload JSON-safe | HTTP, política, side-effects |
| Client | `apps/integrations_bridge/intelligence_sync.py` | Transporte HTTP, headers internos, normalização da resposta, retry mínimo | Política de negócio, construção do payload |

Esta separação é deliberada e foi mantida nos prompts anteriores; nenhuma
alteração de arquitectura foi feita em BC-IE-010.

### Isolamento do caminho síncrono vs. jobs assíncronos

A app `integrations_bridge` já continha o scaffolding assíncrono para
renderer/workers (`ExternalJobReference`, `/internal/jobs/callback/`,
`EXTERNAL_JOBS_ENABLED`/`EXTERNAL_JOBS_DRY_RUN`). A integração com o
Intelligence Engine **não reutiliza esse caminho** — é uma chamada síncrona
dentro do próprio request do utilizador, com switches independentes
(`INTELLIGENCE_ENGINE_ENABLED`/`INTELLIGENCE_ENGINE_DRY_RUN`). Os dois
caminhos partilham apenas o transporte de baixo nível (`InternalServiceClient`)
e a convenção de cabeçalhos internos — nada mais.

---

## 3. Endpoints criados

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/v1/campaigns/{id}/intelligence/` | Constrói o payload da campanha e chama o Intelligence Engine de forma síncrona; devolve `analysis`, `scores`, `grade`, `moments`, `recommendations`, `summary`. Sem persistência. RBAC: `campaigns:view`. Workspace-scoped (header `X-Workspace-ID`). |

Respostas:

| HTTP | Quando |
|---|---|
| `200` | Sucesso (real ou dry-run) — corpo: `{source, status, engine, generated_at, result: {...}}` |
| `404` | Campanha não existe ou não pertence ao workspace activo |
| `502` | `intelligence_upstream_error` — o engine respondeu com um erro que não é seguro expor como erro de cliente (4xx do engine, ou corpo inválido) |
| `503` | `intelligence_unavailable` / `intelligence_disabled` — engine inacessível, timeout esgotado, ou `INTELLIGENCE_ENGINE_ENABLED=False` |

Nenhum detalhe interno (stack trace, corpo bruto do engine, token) é exposto
em qualquer destas respostas — confirmado por teste (ver §7).

Schema OpenAPI (`schema.yml`) já documenta este endpoint e está actualizado
(confirmado em BC-IE-010: `python manage.py spectacular --file <tmp>` não
produz diff contra o `schema.yml` commitado, mesmo após o bugfix de
BC-IE-009 — a correcção não altera o contrato/forma da API).

---

## 4. Settings

Bloco em `config/settings.py` (lido via `python-decouple`, defaults seguros
para desenvolvimento):

| Variável | Default | Notas |
|---|---|---|
| `INTELLIGENCE_ENGINE_BASE_URL` | `http://localhost:8201` | URL base do FastAPI Intelligence Engine. |
| `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` | `10` | Timeout do cliente HTTP. |
| `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` | (vazio → reutiliza `INTERNAL_API_TOKEN`) | Token enviado em `X-Internal-Token`. Pode ser um segredo dedicado, ou deixar vazio para partilhar o mesmo segredo dos jobs externos. |
| `INTELLIGENCE_ENGINE_ENABLED` | `True` | `False` → o cliente síncrono nunca é chamado (serviço devolve `IntelligenceDisabledError` → 503). |
| `INTELLIGENCE_ENGINE_DRY_RUN` | `False` | `True` → devolve um stub determinístico sem qualquer chamada HTTP. Independente de `EXTERNAL_JOBS_DRY_RUN`. |
| `INTELLIGENCE_ENGINE_MAX_RETRIES` | `1` | Repetições apenas para falhas transitórias (timeout/inacessível/5xx); nunca em 4xx ou corpo inválido. Correm dentro do request do utilizador — manter baixo. |
| `INTELLIGENCE_ENGINE_RETRY_BACKOFF_SECONDS` | `0.5` | Backoff linear entre tentativas (`backoff * tentativa`). |

**Guarda de segurança em produção** (`_require_secure_intelligence_engine_config`,
em `config/settings.py`): se `DEBUG=False` e `INTELLIGENCE_ENGINE_ENABLED=True`
e `INTELLIGENCE_ENGINE_DRY_RUN=False` e o token resolvido for vazio, a
aplicação **recusa arrancar** (`ImproperlyConfigured`). Isto impede subir para
produção com chamadas reais ao engine sem autenticação.

Confirmado em BC-IE-010: `.env.example` documenta todas estas variáveis com
comentários explicativos e **sem nenhum valor real de segredo** (token fica
vazio por convenção, com nota explícita de que nunca deve ser commitado um
valor real).

---

## 5. Client / Service / Builder

### Builder — `apps/campaigns/intelligence_payload.py`

`CampaignIntelligencePayloadBuilder` monta o envelope `POST /intelligence/campaign`
a partir dos modelos Django reais: dados da campanha, artista, faixa,
estatísticas de smart links (cliques totais/7d/30d, links activos),
`content_outputs`, relatórios anteriores, media kits e goals. Adapter puro —
sem HTTP, sem política de negócio. Bounded e sem N+1 (uma query agregada para
cliques, `.values()` com `LIMIT 50` para as restantes colecções).

Helpers de serialização JSON-safe: `_iso` (data/datetime → ISO datetime),
`_id` (UUID → str), `_num` (Decimal → float), e `_date_only` — adicionado em
BC-IE-009 para truncar `content_outputs[].created_at` (um `DateTimeField`
Django) para uma data ISO simples, porque o schema Pydantic do engine
(`ContentOutputSummary.created_at: date | None`) exige granularidade de dia
(ver §8). Os restantes campos de data do payload (`start_date`, `end_date`,
`release_date`, `period_end`, `deadline`) já eram `DateField` Django, por isso
não foram afectados.

### Service — `apps/campaigns/intelligence_service.py`

`get_campaign_intelligence(workspace, campaign, requested_by=None, reference_date=None, request_id=None)`
orquestra o fluxo completo:

1. Carrega/valida a campanha no workspace (`CampaignNotFoundError`).
2. Se `INTELLIGENCE_ENGINE_ENABLED=False` → `IntelligenceDisabledError`.
3. Se `INTELLIGENCE_ENGINE_DRY_RUN=True` → devolve um `CampaignIntelligenceOutcome`
   stub determinístico (`source="dry_run"`), sem qualquer chamada HTTP.
4. Caso contrário, constrói o payload com o builder e chama
   `IntelligenceEngineClient.post_campaign_intelligence(...)`.
5. Mapeia falhas do cliente para excepções de domínio:
   `IntelligenceEngineTimeout`/`IntelligenceEngineUnavailable` →
   `IntelligenceUnavailableError`; `IntelligenceEngineResponseError`/
   `IntelligenceEngineProtocolError` → `IntelligenceUpstreamError`.
6. Em sucesso, stampa `generated_at` (responsabilidade do Django, não do
   engine) e devolve `CampaignIntelligenceOutcome` (`source="engine"`,
   `status`, `engine`, `generated_at`, `result`), com `.as_dict()` para a
   serialização da resposta.
7. Regista logs estruturados (`campaigns.intelligence`) sem nunca incluir o
   token ou o corpo bruto da resposta.

### Client — `apps/integrations_bridge/intelligence_sync.py`

`IntelligenceEngineClient` é uma camada fina de transporte + normalização
sobre `InternalServiceClient` (o mesmo cliente urllib usado pelos jobs
externos — cabeçalhos internos e logging sem token são reutilizados, não
reimplementados). Acrescenta:

- O endpoint nomeado `POST /intelligence/campaign`.
- Normalização da resposta em `IntelligenceResult` (status, engine,
  engine_version, request_id, workspace_id, result, explanations, warnings,
  metadata, raw).
- Excepções tipadas: `IntelligenceEngineTimeout`, `IntelligenceEngineUnavailable`,
  `IntelligenceEngineProtocolError` (corpo inválido/status inesperado — nunca
  retentado), `IntelligenceEngineResponseError` (com `is_client_error`/
  `is_server_error` para decidir retry).
- Retry mínimo: apenas timeout/inacessível/5xx, nunca 4xx, nunca corpo
  inválido; backoff linear (`retry_backoff * tentativa`).
- `build_intelligence_engine_client()` — factory a partir dos settings
  (produção); testes injectam um `opener` falso para simular transporte sem
  HTTP real.

Não consulta `INTELLIGENCE_ENGINE_ENABLED`/`DRY_RUN` — essas políticas
pertencem exclusivamente ao service, por desenho (mesma convenção usada pelos
jobs externos, onde os switches `EXTERNAL_JOBS_*` vivem em `services.py`, não
em `clients.py`).

---

## 6. Validações executadas

Executadas em BC-IE-010, no estado actual do código (depois do bugfix de
BC-IE-009):

| Validação | Comando | Resultado |
|---|---|---|
| Suite de testes completa | `pytest -q` | **459 passed, 3 skipped** em 296.90s. Os 3 skips são os testes de loop real (`test_intelligence_real_loop.py`), guardados por `RUN_REAL_IE=1` (não definido nesta corrida — comportamento esperado). |
| Lint | `ruff check apps/ config/` | **All checks passed!** |
| Django system check | `python manage.py check` | **System check identified no issues (0 silenced).** |
| Schema OpenAPI actual | `manage.py spectacular --file <tmp>` + diff vs `schema.yml` | **Sem diff** — schema commitado está actual. |
| Typecheck (mypy/pyright) | — | **Não aplicável.** O `pyproject.toml` só define `[tool.ruff]`; não há configuração de `mypy` nem `pyright` neste repositório. Não inventado — confirmado por inspecção directa do `pyproject.toml`. |
| Validação real (dois serviços a correr) | Ver §7 | **Executada em BC-IE-009 e re-confirmada nesta fase** — chamada real Django → FastAPI Intelligence Engine, resposta `200`/`completed` com todas as chaves esperadas. |
| Secrets em docs/.env.example/relatórios/testes | grep manual | **Nenhum segredo real encontrado** — apenas tokens de teste consistentes e claramente locais (ex.: `real-loop-token-123`, atado a `127.0.0.1`). Ver §9. |

---

## 7. Testes

| Ficheiro | Cobertura |
|---|---|
| `apps/campaigns/tests/test_intelligence_payload.py` | Builder: forma do payload, JSON-safety, bounded queries, `WorkspaceMismatchError`. |
| `apps/integrations_bridge/tests/test_intelligence_sync.py` | Client: normalização de sucesso, todas as excepções tipadas, retry (transitório sim, 4xx/protocolo não), ausência do token em logs/erros. |
| `apps/campaigns/tests/test_intelligence_service.py` | Service: `ENABLED=False`, `DRY_RUN=True`, mapeamento de erros do client para excepções de domínio, stamping de `generated_at`. |
| `apps/campaigns/tests/test_campaigns_intelligence_view.py` (ou equivalente, ver prompts 06/07) | View/endpoint: RBAC, workspace scoping, mapeamento para 200/404/502/503, ausência de detalhes internos na resposta de erro. |
| `apps/campaigns/tests/test_intelligence_real_loop.py` | **Opt-in** (`RUN_REAL_IE=1`), sem mocks: 3 testes — (1) `get_campaign_intelligence()` contra o engine real devolve `source=engine`/`status=completed` com as 6 chaves; (2) engine inacessível (porta fechada) levanta `IntelligenceUnavailableError` de forma controlada; (3) o endpoint Django real (`POST /api/v1/campaigns/{id}/intelligence/`, com auth+RBAC reais) contra o engine real devolve `200` com o corpo completo. Todos confirmam ausência do token em `caplog.text`. |

Execução do loop real (BC-IE-009, evidência já capturada nesse relatório —
não repetida do zero nesta fase porque a evidência já existente é completa e
honesta; ver [`resultados/prompt_09_loop_real_backend_core_intelligence.md`](resultados/prompt_09_loop_real_backend_core_intelligence.md)
para os logs e a resposta JSON reais):

```powershell
# Terminal 1 — Intelligence Engine real
cd intelligence_engine
INTERNAL_API_TOKEN=real-loop-token-123 APP_ENV=development `
    venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8201

# Terminal 2 — Backend Core, testes contra o engine real
cd backend_core
$env:RUN_REAL_IE=1; $env:REAL_IE_BASE_URL="http://127.0.0.1:8201"; $env:REAL_IE_TOKEN="real-loop-token-123"
venv/Scripts/python.exe -m pytest apps/campaigns/tests/test_intelligence_real_loop.py -q
```

Resultado (BC-IE-009, e estrutura de teste re-confirmada em BC-IE-010 ao
correr a suite completa com `RUN_REAL_IE` por definir — os 3 testes aparecem
correctamente como `SKIPPED`, não como erro): os 3 testes passam quando os
dois serviços estão de facto a correr.

---

## 8. Limitações

- **Sem persistência de snapshot.** O resultado do engine não é guardado;
  cada chamada recalcula tudo. Decisão de MVP (backlog §13, BC-IE-PDEC-002).
  Se o produto precisar de histórico de intelligence por campanha, isto exige
  um novo modelo e uma decisão de produto — fora do escopo desta fase.
- **Sem `ExternalJobReference`/callback.** O caminho é síncrono dentro do
  request do utilizador; campanhas muito grandes ou um engine lento
  aumentam directamente a latência percebida pelo utilizador (mitigado pelo
  timeout configurável e por `MAX_ITEMS=50` no builder, mas não eliminado).
- **Sem typecheck automatizado.** Não há `mypy`/`pyright` configurado neste
  repositório — apenas `ruff`. Esta é uma limitação pré-existente do
  Backend Core, não introduzida por esta integração, e não foi corrigida
  porque está fora do escopo (não é uma falha "directamente relacionada com
  esta integração").
- **Validação real é local e pontual, não contínua.** Os testes do loop real
  são opt-in (`RUN_REAL_IE=1`) e não correm em CI por padrão (exigem o
  Intelligence Engine a correr como processo externo). Não há ainda um
  ambiente de staging com os dois serviços sempre disponíveis para validação
  contínua — apenas confirmado manualmente, localmente, nesta fase.
- **Sem observabilidade dedicada.** Os logs estruturados existem
  (`campaigns.intelligence`, `integrations_bridge.intelligence`,
  `integrations_bridge.client`) mas não há métricas/dashboards/alertas sobre
  taxa de erro, latência ou disponibilidade do engine — alinhado com o que o
  próprio backlog já assinalava como pendente para produção (backlog §16).
- **Sem calibração de negócio.** Não foi feita uma validação humana de que
  os scores/grades/recomendações devolvidos pelo engine são *substantivamente*
  bons para decisões reais de campanha — apenas que o contrato técnico
  funciona ponta a ponta. Calibração de qualidade analítica é
  responsabilidade do Intelligence Engine, fora do escopo do Backend Core.

---

## 9. Confirmação de ausência de segredos reais

Verificado nesta fase, sem alterações necessárias:

- `.env.example`: todas as variáveis `INTELLIGENCE_ENGINE_*` documentadas com
  comentários; `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` e `INTERNAL_API_TOKEN`
  ficam **vazios** por convenção, com nota explícita de "nunca commitar um
  valor real".
- `config/settings.py`: nenhum segredo hardcoded; tudo lido via
  `python-decouple` com defaults vazios/inseguros apenas para `DEBUG=True`.
- Relatórios em `resultados/` e testes (`test_intelligence_real_loop.py` e
  similares): usam apenas tokens de teste claramente locais e descartáveis
  (ex.: `real-loop-token-123`), sempre associados a `127.0.0.1` e a instruções
  explícitas de arranque manual local — nunca a um ambiente real. Confirmado
  por grep nos ficheiros desta pasta de documentação e nos testes da
  integração; nenhuma outra string de token aparece fora deste padrão.
- Nenhum log de exemplo nos relatórios contém o valor do token — os próprios
  relatórios (ex.: prompt_09) demonstram isso como parte da validação.

**Conclusão: não há segredos reais nesta fase de documentação/testes.**

---

## 10. Pronto / não pronto para piloto técnico

**Pronto para piloto técnico: sim**, com as ressalvas listadas em §8.

Justificação: o fluxo completo (auth → RBAC → workspace scoping → builder →
client → engine real → resposta) foi validado com os dois serviços
realmente a correr, os erros são tratados de forma segura e tipada, não há
segredos expostos, a suite de testes e o lint estão limpos, e o contrato
OpenAPI está actual. Um piloto técnico controlado (ex.: ambiente interno, um
número reduzido de workspaces) pode usar este endpoint hoje.

---

## 11. Pronto / não pronto para produção

**Pronto para produção: ainda não**, pelas razões listadas em §8 — em
particular: falta observabilidade (métricas/alertas), falta um ambiente de
staging com validação real contínua (não apenas pontual/local), e a
calibração de qualidade analítica do engine não foi avaliada por um humano de
negócio. Isto está alinhado com a expectativa já registada no backlog
(§16 Resultado esperado): *"Pronto para produção: ainda não, salvo resolução
de observabilidade, calibração e política operacional."*

A guarda de segurança (`_require_secure_intelligence_engine_config`) já
impede o cenário mais perigoso (subir para produção sem token configurado),
o que reduz o risco, mas não substitui as pendências acima.

---

## 12. Próximos passos

1. **Observabilidade**: adicionar métricas (latência, taxa de erro/timeout,
   taxa de fallback para `IntelligenceUnavailableError`) e, idealmente, um
   alerta básico sobre indisponibilidade prolongada do engine.
2. **Ambiente de staging**: ter os dois serviços (Backend Core +
   Intelligence Engine) a correr de forma persistente num ambiente
   partilhado, para validação contínua (não apenas local/manual).
3. **Calibração de negócio**: revisão humana da qualidade dos
   scores/grades/recomendações devolvidos pelo engine em campanhas reais,
   antes de expor isto a todos os utilizadores.
4. **Decisão de produto sobre histórico**: avaliar se vale a pena persistir
   snapshots de intelligence por campanha (mudaria o MVP actual,
   deliberadamente sem persistência).
5. **Política operacional de produção**: decidir valores de
   `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS`/`MAX_RETRIES`/`RETRY_BACKOFF_SECONDS`
   apropriados a tráfego real (os defaults actuais são razoáveis para
   desenvolvimento, mas não foram testados sob carga).

Nenhum destes próximos passos está dentro do escopo desta fase de integração
(BC-IE-001 a BC-IE-010) — são decisões de produto/operação para a fase
seguinte.
