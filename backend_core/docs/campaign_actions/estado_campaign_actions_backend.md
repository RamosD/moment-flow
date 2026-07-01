# Estado final — CampaignAction API no Backend Core

> Fase: Iteração 01 — Backend Core CampaignAction API  
> Estado avaliado em: 2026-07-01  
> Documento de contrato: `arquitectura_campaign_actions_backend.md`

## 1. Resumo executivo

A fase entregou uma entidade persistente `CampaignAction` numa app Django
dedicada, com migration, serializer, validações de tenant/campaign, lifecycle,
API REST pública autenticada, filtros, RBAC, OpenAPI, Django Admin e testes.

A API está disponível no Backend Core em:

```text
/api/v1/campaign-actions/
```

É uma API pública autenticada por JWT e scoped por `X-Workspace-ID`. Não usa
`X-Internal-Token`, não chama o Intelligence Engine e não chama Content/Report
Renderer directamente.

O escopo backend desta iteração está implementado e foi exercitado por 56 testes
dedicados, validação OpenAPI e 30 verificações HTTP contra `manage.py runserver`.
Contudo, a fase não pode ser declarada pronta para produção: a migration não foi
aplicada à base local configurada por limitação de acesso, PostgreSQL/staging não
foram exercitados, a suite global não foi executada, não existe backfill e o
frontend continua a usar a projecção best-effort anterior.

Conclusão:

| Alvo | Estado | Fundamentação |
| --- | --- | --- |
| Escopo de implementação backend | Concluído | Model, API, lifecycle, relações, schema e testes entregues |
| Piloto técnico isolado da API | Condicionalmente pronto | Requer migration em DB alvo e smoke test nesse ambiente |
| Piloto end-to-end via frontend | Não pronto | Frontend ainda não consome a entidade persistente |
| Produção | Não pronto | Faltam PostgreSQL/staging, rollout, backfill, auditoria/observabilidade e validação global |

## 2. Estado por categoria

### 2.1 Implementado e validado

- app `apps.campaign_actions` carregada em `INSTALLED_APPS`;
- model e migration inicial;
- serializer read/write com validações cross-workspace e cross-campaign;
- lifecycle transaccional e operações semânticas;
- viewset workspace-scoped com JWT e RBAC;
- rotas collection/detail;
- filtros, pesquisa, ordering e paginação global;
- relação formal com ContentPackRequest, ContentOutput, Report e MediaKit;
- deduplicação activa no serializer e constraint parcial;
- schema drf-spectacular;
- Django Admin;
- 56 testes dedicados;
- smoke HTTP real com auth, workspace, CRUD, filtros e erros principais.

### 2.2 Implementado, mas não validado no ambiente alvo

- aplicação da migration ao `backend_core/db.sqlite3` local: o ficheiro configurado
  devolve `unable to open database file`;
- índices e constraint parcial em PostgreSQL real;
- comportamento sob concorrência em PostgreSQL;
- deploy e migration em staging;
- integração com a configuração real de produção;
- suite completa de todas as apps do Backend Core.

A migration foi aplicada com sucesso em bases SQLite de teste/in-memory e numa
SQLite isolada usada no smoke HTTP. Isto valida o grafo e a operação em SQLite,
mas não substitui validação PostgreSQL/staging.

### 2.3 Não implementado

- criação automática de artefactos pela CampaignAction;
- sincronização automática entre status da action e status do artefacto;
- backfill de artefactos históricos que guardam recommendation ref em metadata;
- AuditEvent para create/update/transições CampaignAction;
- workflow engine, scheduler, WebSockets ou notificações em tempo real;
- `asset_request` como action type;
- PUT, DELETE ou reabertura de estados terminais;
- endpoints internos ou autenticação por internal token;
- chamadas directas ao Intelligence Engine ou renderers.

### 2.4 Pendente para frontend

- substituir a agregação de content-pack requests, reports e media kits por GET
  `/campaign-actions/`;
- remodelar a entity frontend conforme os campos reais;
- persistir recommendation ref/snapshot em CampaignAction;
- activar manual task, mark reviewed e dismiss;
- suportar múltiplas actions por recommendation;
- respeitar paginação e deduplicação por ref + action type;
- executar o fluxo artefacto primeiro, CampaignAction relacionada depois;
- decidir backfill, corte temporal ou compatibilidade temporária antes do
  cutover.

O backlog de handoff foi criado em:

```text
frontend/docs/01_fundamentos/03_campaign_actions_backend_integration/01_backlog.md
```

## 3. Escopo entregue

### 3.1 Localização

```text
apps/campaign_actions/
  __init__.py
  admin.py
  apps.py
  filters.py
  models.py
  serializers.py
  services.py
  urls.py
  views.py
  migrations/
    0001_initial.py
  tests/
    conftest.py
    test_api.py
    test_related_artifacts.py
    test_transitions.py
```

Integrações no projecto:

- `config/settings.py`: `apps.campaign_actions` em `INSTALLED_APPS`;
- `config/urls.py`: include em `/api/v1/`;
- router DRF: basename `campaign-action`, prefix `campaign-actions`.

### 3.2 Model criado

Classe:

```text
CampaignAction(BaseModel, WorkspaceOwnedModel, CreatedUpdatedByModel)
```

Campos públicos:

| Grupo | Campos |
| --- | --- |
| Identidade/tenant | `id`, `workspace`, `campaign` |
| Recommendation | `recommendation_ref`, `recommendation_snapshot` |
| Conteúdo | `title`, `description`, `metadata` |
| Classificação | `action_type`, `status`, `priority`, `source` |
| Decisão | `dismiss_reason` |
| Relações | `related_content_pack_request`, `related_content_output`, `related_report`, `related_media_kit` |
| Actor | `created_by`; `updated_by` existe no model mas não na API pública |
| Lifecycle | `completed_at`, `cancelled_at`, `created_at`, `updated_at` |

Choices:

```text
action_type:
  content_pack
  report_request
  media_kit_request
  manual_task
  mark_reviewed
  dismiss

status:
  pending
  in_progress
  completed
  failed
  dismissed
  cancelled

priority:
  low
  medium
  high
  urgent

source:
  recommendation
  manual
```

`asset_request` ficou explicitamente fora. ContentOutput é uma relação de uma
action `content_pack`, não um action type.

### 3.3 Migration

Migration criada:

```text
apps/campaign_actions/migrations/0001_initial.py
```

Inclui tabela, FKs, choices, timestamps, índices e constraint.

Índices:

```text
workspace + campaign
workspace + campaign + recommendation_ref
status
action_type
created_at
```

Constraint parcial `unique_active_campaign_action`:

```text
workspace + campaign + recommendation_ref + action_type
```

aplicável quando recommendation ref não é vazia e status é `pending`,
`in_progress` ou `completed`.

Estado de aplicação:

- SQLite de teste/in-memory: aplicada;
- SQLite isolada do smoke HTTP: aplicada;
- `db.sqlite3` local configurada: não aplicada por inacessibilidade ambiental;
- PostgreSQL/staging: não validada nesta fase.

### 3.4 Serializer

`CampaignActionSerializer` é a representação read/write única.

Read-only/server-managed:

```text
id
workspace
created_by
completed_at
cancelled_at
created_at
updated_at
```

Create-only/imutáveis após criação:

```text
campaign
recommendation_ref
recommendation_snapshot
action_type
source
```

Actualizáveis por PATCH:

```text
title
description
status
priority
metadata
dismiss_reason
related_content_pack_request
related_content_output
related_report
related_media_kit
```

Validações implementadas:

- campaign no workspace activo;
- artefacto relacionado no mesmo workspace e campaign;
- compatibilidade entre action type e campo `related_*`;
- consistência entre content output e content pack request quando ambos existem;
- recommendation ref obrigatória excepto manual task;
- snapshot object não vazio excepto manual task;
- snapshot até 65 536 bytes;
- rejeição/redacção defensiva de chaves sensíveis no snapshot;
- dismiss reason obrigatório para action/status dismissed;
- action type e status limitados aos choices;
- campos identitários imutáveis;
- duplicado activo rejeitado com erro legível.

`DismissCampaignActionSerializer` valida o body da operação dismiss.

### 3.5 Serviço de lifecycle

`services.py` centraliza as transições:

```text
pending -> in_progress | completed | failed | dismissed | cancelled
in_progress -> completed | failed | cancelled
completed | failed | dismissed | cancelled -> terminal
```

Repetir o estado actual é idempotente.

Regras:

- completed define `completed_at` uma vez;
- cancelled define `cancelled_at` uma vez;
- dismissed exige e persiste motivo;
- timestamps/motivo incompatíveis são limpos;
- `updated_by` recebe o actor;
- transição usa `transaction.atomic` e `select_for_update`;
- retry após failed é uma nova CampaignAction.

### 3.6 Viewset, endpoints e schema

`CampaignActionViewSet` herda de `WorkspaceScopedRBACViewSet`.

Endpoints:

| Método | Endpoint | Estado |
| --- | --- | --- |
| GET | `/api/v1/campaign-actions/` | Implementado e validado |
| POST | `/api/v1/campaign-actions/` | Implementado e validado |
| GET | `/api/v1/campaign-actions/{id}/` | Implementado e validado |
| PATCH | `/api/v1/campaign-actions/{id}/` | Implementado e validado |
| POST | `/api/v1/campaign-actions/{id}/mark-reviewed/` | Implementado e validado |
| POST | `/api/v1/campaign-actions/{id}/dismiss/` | Implementado e validado |
| POST | `/api/v1/campaign-actions/{id}/cancel/` | Implementado e validado |
| POST | `/api/v1/campaign-actions/{id}/complete/` | Implementado e validado |

PUT e DELETE devolvem 405.

O schema drf-spectacular inclui collection, detail, quatro actions semânticas,
enums, JWT, header workspace, filtros e payload dismiss.

### 3.7 Filtros, pesquisa, ordering e paginação

Filtros exactos:

```text
campaign
status
action_type
recommendation_ref
source
created_by
```

Pesquisa:

```text
title
description
recommendation_ref
```

Ordering permitido:

```text
created_at
updated_at
status
priority
action_type
```

Default: `-created_at`.

Paginação global: 25 por omissão, `page_size`, máximo 100.

### 3.8 Permissões e workspace scoping

| Operação | Permission |
| --- | --- |
| list/retrieve | `campaigns:view` |
| create/PATCH | `campaigns:update` |
| operações semânticas | `campaigns:update` |

Comportamento validado:

- sem JWT: 401;
- sem `X-Workspace-ID`: 400;
- sem membership/permission: 403;
- detail de outro workspace: 404;
- campaign/artefacto fora do workspace: 400 de campo;
- viewer lista, mas não cria;
- workspace do body não escolhe tenant; o servidor usa `request.workspace`.

Não existe endpoint interno e `X-Internal-Token` não faz parte do contrato.

## 4. Relação com recommendations

`recommendation_ref` é correlação persistente e opaca, não FK nem id garantido
do Intelligence Engine. É imutável, tem no máximo 512 caracteres e participa na
deduplicação.

`recommendation_snapshot` preserva contexto mínimo porque recommendations podem
ser recalculadas e não ter identidade estável. O frontend deve enviar uma
allowlist pequena, nunca o payload integral de intelligence.

O backend não consulta, valida ou chama o Intelligence Engine para resolver a
ref. Esta separação é intencional.

## 5. Relação com artefactos

| Action type | Relações permitidas |
| --- | --- |
| `content_pack` | ContentPackRequest e/ou ContentOutput |
| `report_request` | Report |
| `media_kit_request` | MediaKit |
| `manual_task` | nenhuma |
| `mark_reviewed` | nenhuma |
| `dismiss` | nenhuma |

Todas as relações são opcionais na criação e usam `SET_NULL`. A validação exige
mesmo workspace e mesma campaign. Report/MediaKit com campaign nula são
rejeitados para esta associação.

Fluxo suportado:

```text
1. criar artefacto no endpoint proprietário;
2. criar CampaignAction com related_* ou ligar por PATCH.
```

CampaignAction não gera artefactos, não dispara renderer e não duplica regras de
billing/callback dos domínios proprietários.

## 6. Testes

Suite dedicada:

| Ficheiro | Cobertura | Resultado final |
| --- | --- | --- |
| `test_api.py` | CRUD, auth, header, RBAC, scoping, choices, duplicação, filtros | 13 testes aprovados |
| `test_related_artifacts.py` | relações válidas, cross-scope/campaign, null campaign, compatibilidade | 21 testes aprovados |
| `test_transitions.py` | PATCH lifecycle, timestamps, dismiss, terminalidade, actions semânticas | 22 testes aprovados |
| Total | CampaignAction | 56 aprovados |

Execução final em 2026-07-01:

```text
56 passed, 57 warnings
```

Warnings ambientais conhecidos:

- directório `staticfiles` ausente;
- pytest sem permissão para actualizar `.pytest_cache`.

Nenhum warning correspondeu a falha funcional dos testes.

## 7. Validações executadas

### 7.1 Nesta conclusão

- `python manage.py check`: 0 issues;
- `python -m pytest apps/campaign_actions/tests -q`: 56 passed;
- `python manage.py spectacular --validate`: passou e confirmou os seis paths
  OpenAPI CampaignAction;
- inspecção de app, settings, urls, migration, serializers, services, viewset,
  filters e testes;
- browser não usado.

Os comandos foram executados com o Python do venv do Backend Core.

### 7.2 Ao longo da fase

- migration aplicada em bases SQLite de teste/in-memory;
- schema OpenAPI gerado e validado;
- HTTP real contra Django `manage.py runserver` em localhost:8000;
- header do servidor confirmou WSGI/Django, não FastAPI/uvicorn;
- `/api/v1/schema/`, `/api/v1/docs/` e `/admin/`: 200;
- 30 verificações HTTP aprovadas: login, `/auth/me`, workspaces, CRUD,
  paginação, quatro filtros, related report, dismiss, 401, 403, 404, 400 e dois
  cenários cross-workspace;
- porta 8000 libertada após validação;
- documentação verificada contra padrões de credenciais reais.

## 8. Limitações

1. O `db.sqlite3` local configurado não pôde ser aberto; a migration permanece
   por aplicar nesse ficheiro.
2. A constraint parcial não foi validada em PostgreSQL.
3. A suite global do Backend Core não foi executada.
4. Não houve deploy ou smoke test em staging.
5. Artefactos históricos não são convertidos automaticamente em CampaignAction.
6. O status do artefacto e o status da action podem divergir.
7. Transições feitas directamente por ORM/admin podem contornar o serviço e
   algumas validações API.
8. Uma relação válida pode sofrer drift se o artefacto mudar de campaign depois.
9. AuditEvent não regista ainda as operações desta app.
10. Não existem métricas/alertas específicos para falhas CampaignAction.
11. O frontend actual não consome a API persistente.

## 9. Impacto no frontend

O frontend ainda:

- agrega content-pack requests, reports e media kits como actions;
- usa ids/status dos artefactos;
- guarda recommendation ref e priority em metadata;
- faz matching best-effort por uma única action;
- não oferece manual task, mark reviewed ou dismiss persistentes.

A adaptação não é uma simples troca de URL. Requer:

- novo model/DTO;
- API hooks directos;
- paginação;
- snapshot seguro;
- fluxo em duas etapas para artefactos;
- múltiplas actions por recommendation;
- deduplicação por action type;
- decisão de backfill/corte temporal.

Sem essa decisão, o cutover pode esconder histórico antigo.

## 10. Riscos activos

| Risco | Probabilidade | Impacto | Mitigação recomendada |
| --- | --- | --- | --- |
| Migration falha no DB alvo | Desconhecida | Alto | CI/staging PostgreSQL + backup/rollback |
| Histórico desaparece no frontend | Alta sem decisão | Alto | backfill ou corte temporal explícito |
| Duplicados sob concorrência | Baixa/Média | Médio | constraint DB + teste PostgreSQL |
| Drift action/artefacto | Média | Médio | mostrar estados separados; futura sincronização |
| Snapshot com dados indevidos | Média | Alto | allowlist frontend + validação backend existente |
| Relações cross-tenant | Baixa | Crítico | manter serializer/RBAC e testes |
| ORM/admin contorna lifecycle | Baixa/Média | Alto | serviço obrigatório/auditoria futura |
| Falta de observabilidade | Média | Médio | AuditEvent, métricas e alertas |
| Frontend assume criação automática | Média | Alto | fluxo em duas etapas e documentação |

## 11. Pronto para piloto?

### 11.1 Piloto técnico da API

**Condicionalmente sim.**

Condições mínimas:

1. aplicar migration numa base descartável/staging, preferencialmente
   PostgreSQL;
2. executar smoke test de list/create/detail/PATCH/actions nesse ambiente;
3. confirmar JWT, `X-Workspace-ID` e roles reais;
4. confirmar plano de rollback da migration;
5. monitorizar 400/403/500 e duplicados;
6. usar a API apenas através do Backend Core.

### 11.2 Piloto end-to-end do produto

**Não.**

O frontend ainda não está integrado e não existe decisão de histórico/backfill.
Um piloto directo pela UI continuaria a testar a projecção antiga, não esta API.

## 12. Pronto para produção?

**Não.**

Faltam evidências obrigatórias:

- migration e constraint validadas em PostgreSQL;
- staging/deploy real;
- suite global/regressão;
- plano de backfill/cutover;
- frontend integrado e validado;
- observabilidade/auditoria;
- estratégia para divergência action/artefacto;
- operação/rollback documentados;
- validação de segurança e carga proporcionais ao ambiente.

Os 56 testes e o smoke HTTP sustentam a qualidade do escopo da app, mas não são
evidência suficiente para declarar produção-ready.

## 13. Próximos passos recomendados

### Prioridade 0 — fechar ambiente backend

1. Resolver/evitar o `db.sqlite3` local inacessível.
2. Aplicar migration em PostgreSQL de CI/staging.
3. Executar `migrate`, `check`, schema, suite CampaignAction e smoke HTTP.
4. Executar suite global do Backend Core.

### Prioridade 1 — decisão de dados e frontend

1. Decidir backfill, corte temporal ou compatibilidade temporária.
2. Executar `FE-CAI-001 — Congelar contrato e rollout`.
3. Adaptar entity, hooks, panel e recommendation state.
4. Implementar fluxo artefacto -> CampaignAction relacionada.
5. Validar manual task, reviewed e dismiss na UI.

### Prioridade 2 — hardening

1. Integrar AuditEvent para create/update/transições.
2. Adicionar métricas e logs estruturados sem snapshots/secrets.
3. Avaliar sincronização explícita de status com artefactos.
4. Testar concorrência/deduplicação em PostgreSQL.
5. Rever drift de relações após update de artefactos.

### Prioridade 3 — produção

1. Staging end-to-end.
2. Plano de migration/rollback e backup.
3. Revisão de segurança/RBAC.
4. Observabilidade e alertas.
5. Aprovação operacional e rollout gradual.

## 14. Decisão final da fase

A Iteração 01 do Backend Core CampaignAction API fica **fechada como
implementada e validada no âmbito da app e de integração HTTP local isolada**.

Não fica fechada como produção-ready. As pendências ambientais, de dados,
frontend e operação passam para as fases seguintes sem serem ocultadas ou
reclassificadas como concluídas.
