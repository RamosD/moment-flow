# Backlog — Staging Campaign Actions with Real IE and Renderer

> Fase: `04_staging_campaign_actions_with_real_ie_renderer`
> Estado: planeada
> Dependência anterior: `03_campaign_actions_backend_integration` validada para piloto técnico controlado
> Objectivo: validar Campaign Actions em staging com Intelligence Engine real e Content Renderer real

---

# 1. Objectivo

Validar a cadeia real de execução da Campaign War Room e Campaign Actions em ambiente de staging/dev controlado, usando:

```text id="w5cefc"
Frontend Web       -> Backend Core
Backend Core       -> Intelligence Engine
Backend Core       -> Content Renderer
Backend Core       -> DB persistente
```

A fase anterior validou:

```text id="5lhs4r"
- Backend Core real;
- Frontend real;
- CampaignAction API;
- criação de manual task;
- mark reviewed;
- dismiss;
- report action;
- media kit action;
- content pack action;
- related_*;
- deduplicação;
- lifecycle;
- reload/persistência;
- build/lint/testes.
```

Esta fase deve remover as duas principais limitações restantes:

```text id="7ilj4w"
- Intelligence Engine em dry_run;
- Content Renderer não exercitado.
```

---

# 2. Tese da fase

A tese desta fase é:

```text id="fbarkg"
Uma CampaignAction só está pronta para piloto operacional quando nasce de intelligence real e consegue acionar outputs reais através do renderer.
```

Não basta confirmar que a API aceita payloads. É preciso confirmar que a cadeia:

```text id="rvnkba"
recommendation real -> action -> artefacto -> renderer/job/output -> estado observável
```

funciona sem mocks runtime.

---

# 3. Portas oficiais

Usar exclusivamente o mapa canónico:

```text id="qsyil4"
Frontend Web / Vite:        http://localhost:5200
Backend Core / Django:      http://localhost:8100
Intelligence Engine:        http://localhost:8201
Content Renderer:           http://localhost:8202
```

Não usar portas antigas como default activo.

---

# 4. Escopo

## 4.1 Dentro do escopo

Inclui:

```text id="19j35d"
- arrancar Backend Core em 8100;
- arrancar Frontend Web em 5200;
- arrancar Intelligence Engine real em 8201;
- arrancar Content Renderer real em 8202;
- desactivar dry_run do IE no Backend Core;
- confirmar healthchecks dos serviços;
- validar War Room com intelligence real;
- validar recommendations reais;
- criar CampaignActions a partir de recommendations reais;
- criar artefactos relacionados;
- validar envio de jobs/requests ao renderer;
- validar estados queued/processing/completed/failed quando aplicável;
- validar callbacks ou polling existentes;
- validar logs com request_id/job_id;
- validar segurança e ausência de chamadas directas do frontend ao IE/Renderer;
- actualizar documentação de estado.
```

## 4.2 Fora do escopo

Não inclui:

```text id="oj7st2"
- produção;
- carga/performance;
- multi-tenant avançado;
- billing;
- retries complexos;
- scheduler;
- WebSockets;
- workflow engine;
- alteração estrutural da CampaignAction API;
- backfill histórico;
- chamadas directas frontend -> IE;
- chamadas directas frontend -> Renderer.
```

---

# 5. Pré-condições

Antes de executar:

```text id="7vqhkc"
- fase 03 fechada para piloto técnico controlado;
- portas padronizadas;
- Backend Core arranca em 8100;
- Frontend arranca em 5200;
- IE arranca em 8201;
- Renderer arranca em 8202;
- DB dev/staging acessível;
- migration campaign_actions aplicada;
- content packs disponíveis;
- dados dev/staging mínimos disponíveis;
- tokens internos configurados apenas no backend/serviços;
- frontend sem acesso a secrets internos.
```

---

# 6. Configuração esperada

## 6.1 Backend Core

```env id="ytl5q2"
BACKEND_CORE_PORT=8100
CORS_ALLOWED_ORIGINS=http://localhost:5200,http://127.0.0.1:5200
INTELLIGENCE_ENGINE_BASE_URL=http://localhost:8201
CONTENT_RENDERER_BASE_URL=http://localhost:8202
REPORT_RENDERER_BASE_URL=http://localhost:8202
```

O modo dry-run da intelligence deve estar desactivado para esta fase:

```env id="j4rrms"
INTELLIGENCE_ENGINE_DRY_RUN=false
```

O nome exacto da variável deve ser confirmado no código actual.

## 6.2 Frontend

```env id="9dhzpf"
VITE_BACKEND_API_BASE_URL=http://localhost:8100/api/v1
VITE_DEV_PORT=5200
```

O frontend não deve ter:

```text id="mw4n62"
INTELLIGENCE_ENGINE_BASE_URL
CONTENT_RENDERER_BASE_URL
INTERNAL_API_TOKEN
X-Internal-Token
```

## 6.3 Intelligence Engine

```env id="at50uh"
INTELLIGENCE_ENGINE_PORT=8201
```

Deve expor healthcheck e responder a requests reais do Backend Core.

## 6.4 Content Renderer

```env id="w92fvm"
PORT=8202
BACKEND_CORE_BASE_URL=http://localhost:8100
RENDERER_PUBLIC_BASE_URL=http://localhost:8202
LOCAL_STORAGE_PUBLIC_BASE_URL=http://localhost:8202/files
```

---

# 7. Backlog incremental

---

## STG-CA-001 — Confirmar contratos e configuração real

### Objectivo

Confirmar as variáveis, endpoints, healthchecks e fluxos reais entre Backend Core, Intelligence Engine e Content Renderer.

### Tarefas

```text id="bcucwj"
- inspeccionar settings do Backend Core;
- confirmar variável exacta de dry_run;
- confirmar client do Intelligence Engine;
- confirmar client do Content Renderer;
- confirmar endpoints health;
- confirmar token interno service-to-service;
- confirmar callbacks ou polling;
- confirmar campos de job_id/request_id;
- confirmar storage local do renderer;
- confirmar estados possíveis de reports/media kits/content outputs/content pack requests.
```

### Critérios de aceitação

```text id="r9708m"
- mapa de configuração confirmado;
- nenhum segredo exposto;
- endpoints reais identificados;
- decisões pendentes registadas.
```

---

## STG-CA-002 — Arrancar serviços em portas canónicas

### Objectivo

Arrancar os quatro componentes com o mapa oficial de portas.

### Tarefas

```text id="4fnxux"
- Backend Core em 8100;
- Frontend em 5200;
- Intelligence Engine em 8201;
- Content Renderer em 8202;
- validar /api/v1/schema/;
- validar /api/v1/docs/;
- validar /admin/;
- validar frontend HTTP 200;
- validar IE health;
- validar Renderer health.
```

### Critérios de aceitação

```text id="ohhzo6"
- todos os serviços correctos respondem;
- nenhuma porta antiga é usada;
- frontend aponta apenas para Backend Core.
```

---

## STG-CA-003 — Validar War Room com Intelligence Engine real

### Objectivo

Confirmar que a War Room obtém intelligence real via Backend Core.

### Tarefas

```text id="0ltr18"
- desactivar dry_run;
- executar POST /campaigns/{id}/intelligence/;
- confirmar chamada Backend Core -> IE;
- confirmar resposta não-dry-run;
- confirmar recommendations reais;
- confirmar grade/score real quando aplicável;
- confirmar logs com request_id;
- confirmar erros 502/503 se IE estiver indisponível.
```

### Critérios de aceitação

```text id="kruu45"
- intelligence real recebida;
- recommendations accionáveis existem;
- frontend continua sem chamar IE directamente;
- falhas do IE são apresentadas sem quebrar War Room.
```

---

## STG-CA-004 — Criar CampaignActions a partir de recommendations reais

### Objectivo

Validar que recommendations reais podem ser convertidas em actions persistentes.

### Tarefas

```text id="bc8xhr"
- criar manual_task a partir de recommendation real;
- criar mark_reviewed;
- criar dismiss com motivo;
- criar report_request;
- criar media_kit_request;
- criar content_pack;
- confirmar recommendation_ref;
- confirmar recommendation_snapshot mínimo e seguro;
- confirmar deduplicação por ref + type;
- confirmar múltiplas actions por recommendation.
```

### Critérios de aceitação

```text id="twacms"
- todas as actions suportadas funcionam;
- snapshot não copia payload integral do IE;
- reload mantém estado;
- painel mostra CampaignActions reais.
```

---

## STG-CA-005 — Validar Content Renderer real

### Objectivo

Confirmar que artefactos que dependem do renderer avançam para job/output real.

### Tarefas

```text id="2trw6b"
- criar report action;
- criar media kit action;
- criar content pack action;
- confirmar artefacto proprietário criado;
- confirmar CampaignAction com related_*;
- confirmar chamada Backend Core -> Content Renderer;
- confirmar job_id quando aplicável;
- confirmar callback/polling;
- confirmar output ou estado final;
- confirmar erro controlado se renderer falhar.
```

### Critérios de aceitação

```text id="kvnxwt"
- Renderer real recebe jobs;
- estados evoluem correctamente;
- related_* continua consistente;
- frontend não chama renderer directamente.
```

---

## STG-CA-006 — Validar observabilidade mínima

### Objectivo

Garantir rastreio suficiente para operar staging.

### Tarefas

```text id="51h7t3"
- confirmar request_id nos logs do Backend Core;
- confirmar job_id nos fluxos do renderer;
- confirmar logs IE sem payload sensível;
- confirmar logs renderer sem tokens;
- confirmar erros 502/503 com mensagens seguras;
- confirmar que X-Internal-Token não aparece em logs.
```

### Critérios de aceitação

```text id="z3xm0t"
- fluxo rastreável;
- erros úteis para suporte;
- sem secrets em logs.
```

---

## STG-CA-007 — Validar erros reais entre serviços

### Objectivo

Testar falhas controladas nos serviços internos.

### Tarefas

```text id="9snkc2"
- IE indisponível;
- Renderer indisponível;
- token interno inválido, se seguro testar;
- timeout;
- payload inválido;
- artefacto sem renderer;
- callback inválido, se aplicável.
```

### Critérios de aceitação

```text id="bewf6q"
- Backend Core devolve erro controlado;
- frontend mostra erro honesto;
- não há stacktrace sensível;
- não há retry destrutivo.
```

---

## STG-CA-008 — Validar segurança frontend

### Objectivo

Confirmar que a regra arquitectural continua intacta.

### Tarefas

```text id="25zdk4"
- inspecionar Network no browser;
- confirmar chamadas apenas a localhost:8100;
- greps por 8201/8202 no frontend;
- greps por X-Internal-Token;
- greps por INTERNAL_API_TOKEN;
- confirmar que .env.local frontend não tem secrets internos.
```

### Critérios de aceitação

```text id="cbrd45"
- frontend chama apenas Backend Core;
- sem internal token no browser;
- sem URLs internas no bundle.
```

---

## STG-CA-009 — Smoke visual staging

### Objectivo

Validar experiência mínima clicada no browser.

### Tarefas

```text id="jrf0f8"
- login;
- abrir War Room;
- executar intelligence real;
- ver recommendations;
- criar manual task;
- criar report action;
- criar media kit action;
- criar content pack action;
- executar reviewed;
- executar dismiss;
- ver painel;
- reload;
- confirmar persistência.
```

### Critérios de aceitação

```text id="aclrib"
- fluxo principal clicável;
- estados visuais coerentes;
- sem regressão óbvia de layout.
```

---

## STG-CA-010 — Fechar estado de staging

### Objectivo

Consolidar evidência e decidir prontidão para piloto técnico mais amplo.

### Tarefas

```text id="9knhzm"
- criar relatório final da fase;
- actualizar documento de estado;
- listar validações concluídas;
- listar limitações;
- listar riscos;
- declarar pronto/não pronto para piloto;
- declarar não pronto para produção se faltar staging formal, observabilidade ou aprovação operacional.
```

### Critérios de aceitação

```text id="80czix"
- relatório final criado;
- estado actualizado;
- conclusão honesta.
```

---

# 8. Critérios de aceitação da fase

A fase é aceite se:

```text id="g5cxxf"
- Backend Core real corre em 8100;
- Frontend real corre em 5200;
- IE real corre em 8201;
- Renderer real corre em 8202;
- dry_run da intelligence está desactivado;
- War Room recebe recommendations reais;
- CampaignActions são criadas a partir de recommendations reais;
- report/media kit/content pack exercitam renderer real ou job real;
- related_* permanece correcto;
- reload confirma persistência;
- falhas IE/Renderer são tratadas;
- logs permitem rastrear request_id/job_id;
- frontend não chama IE/Renderer;
- frontend não envia X-Internal-Token;
- pnpm test/lint/build passam;
- python manage.py check passa;
- testes relevantes dos serviços passam;
- smoke visual staging passa;
- estado final documentado.
```

---

# 9. Critérios de rejeição

A fase não é aceite se:

```text id="f4p835"
- IE continuar em dry_run e a fase for declarada real;
- Renderer não for exercitado e a fase for declarada completa;
- frontend chamar 8201 ou 8202 directamente;
- frontend enviar X-Internal-Token;
- serviços correrem em portas antigas;
- CampaignActions forem criadas sem recommendation real;
- related_* ficar inconsistente;
- errors internos expuserem tokens/stacktrace sensível;
- build/lint/test falharem sem explicação;
- validação visual não for feita e mesmo assim for declarada pronta para piloto operacional.
```

---

# 10. Riscos

| ID      | Risco                                              | Impacto | Mitigação                                                 |
| ------- | -------------------------------------------------- | ------: | --------------------------------------------------------- |
| STG-R01 | IE real não gerar recommendations suficientes      |    Alto | Criar campanha/dev data adequada; documentar limitação    |
| STG-R02 | Renderer criar jobs mas não finalizar              |    Alto | Validar pelo menos estado queued/processing e logs/job_id |
| STG-R03 | Diferença entre dry_run e IE real quebrar snapshot |    Alto | Validar snapshot com payload real                         |
| STG-R04 | Frontend depender de assumptions do dry_run        |   Médio | Smoke visual com IE real                                  |
| STG-R05 | Token interno aparecer em logs                     | Crítico | Greps e revisão de logs                                   |
| STG-R06 | Renderer indisponível deixar action “presa”        |   Médio | Erro controlado e estado honesto                          |
| STG-R07 | Ports antigas reaparecerem em scripts              |   Médio | Usar check de portas antes do smoke                       |
| STG-R08 | E2E manual não ser repetível                       |   Médio | Documentar passos e evidências                            |
| STG-R09 | Staging usar SQLite em vez de DB alvo              |   Médio | Declarar ambiente e limites                               |
| STG-R10 | Falta de observabilidade atrasar debugging         |    Alto | request_id/job_id obrigatórios                            |

---

# 11. Ordem recomendada

```text id="cclcz3"
Incremento 0 — Preparação
STG-CA-001
STG-CA-002

Incremento 1 — Intelligence real
STG-CA-003
STG-CA-004

Incremento 2 — Renderer real
STG-CA-005
STG-CA-006
STG-CA-007

Incremento 3 — Segurança e smoke visual
STG-CA-008
STG-CA-009

Fecho
STG-CA-010
```

---

# 12. Documentos esperados

```text id="fulxs9"
frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/01_backlog.md
frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/arquitectura_staging_ie_renderer.md
frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/estado_staging_ie_renderer.md
frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/
```

---

# 13. Próximo passo

Gerar a pipeline de prompts para execução assistida por IA local desta fase.
