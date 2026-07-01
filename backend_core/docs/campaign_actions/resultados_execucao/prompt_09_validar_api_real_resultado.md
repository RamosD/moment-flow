# Prompt 09 — Validar CampaignAction API real

## Execução de 2026-07-01 07:15 (Atlantic/Cape_Verde)

### Estado da execução

`executado`

### Resumo objectivo

A CampaignAction API foi validada através de HTTP real contra o Backend Core
Django iniciado em `http://localhost:8000` com `manage.py runserver`. Foram
confirmados schema, Swagger UI, Django Admin, autenticação JWT, workspace
scoping, CRUD parcial, filtros, operação dismiss, artefactos relacionados e os
principais erros de segurança/validação.

A porta 8000 estava livre antes da execução e voltou a ficar livre depois. O
servidor foi identificado pelo header `WSGIServer/0.2 CPython/3.13.2`, pelo
Django Admin e pelo schema drf-spectacular; não era FastAPI/uvicorn.

O `db.sqlite3` configurado no projecto continuou inacessível com `unable to open
database file`. Para não alterar nem investigar prolongadamente essa limitação,
a validação usou uma SQLite isolada em `%TEMP%`, recebeu todas as migrations e
dados dev sintéticos, e executou exactamente o código, settings base, URLs,
middleware, autenticação, permissions, serializers e viewsets do Backend Core.

Nenhum token, password ou secret é incluído neste relatório.

### Ficheiros criados ou alterados

- Criado
  `docs/campaign_actions/resultados_execucao/prompt_09_validar_api_real_resultado.md`.
- Foram criados durante a execução `config/runtime_validation_settings.py` e
  `runtime_validation_http.py`; ambos eram auxiliares transitórios e foram
  removidos após a validação.
- Não ficou qualquer alteração em código runtime.
- Foi criada a base isolada
  `%TEMP%/momentflow_campaign_actions_prompt09_20260701_0708.sqlite3`. A sua
  remoção foi recusada pela política do sandbox; não pertence ao repositório e
  contém apenas dados sintéticos desta validação.

### Validações executadas e resultado

#### Ambiente e migrations

- Porta 8000 antes do arranque: livre.
- `python` global: não tinha Django instalado; foi usado o Python correcto em
  `backend_core/venv/Scripts/python.exe` (Django 6.0.6).
- `python manage.py check`: passou, 0 issues.
- Acesso ao `db.sqlite3` local: falhou com `unable to open database file`,
  limitação ambiental já registada em prompts anteriores.
- Migrations na SQLite isolada: todas aplicadas; `campaign_actions.0001_initial`
  confirmada como aplicada.
- Seed dev sintético: 3 utilizadores, 2 workspaces, 2 campaigns, 2 reports, 1
  media kit e 1 content-pack request.

#### Serviço e schema

- `GET /api/v1/schema/`: 200.
- `GET /api/v1/docs/` com content negotiation HTML: 200.
- `GET /admin/`: 200 após redirect para o login do Django Admin.
- Schema validado por `manage.py spectacular --validate`.
- Paths confirmados no schema:
  - `/api/v1/campaign-actions/`;
  - `/api/v1/campaign-actions/{id}/`;
  - `/cancel/`;
  - `/complete/`;
  - `/dismiss/`;
  - `/mark-reviewed/`.
- Não foi usado browser.

#### HTTP real — 30 verificações aprovadas

- Login JWT de owner, viewer e owner de workspace estrangeiro: 200.
- `GET /api/v1/auth/me/`: 200 e utilizador correcto.
- `GET /api/v1/workspaces/`: 200 e isolamento por membership confirmado.
- Listagem de campaigns e dados dev relacionados: 200.
- Listagem de reports, media kits e content-pack requests: 200.
- `GET /api/v1/campaign-actions/`: 200 e envelope paginado confirmado.
- `POST /api/v1/campaign-actions/`: 201 para manual task válida.
- `GET /api/v1/campaign-actions/{id}/`: 200 e payload persistido confirmado.
- `PATCH /api/v1/campaign-actions/{id}/`: 200; título actualizado e transição
  `pending -> in_progress` persistida.
- Criação `report_request` com `related_report` válido da mesma campaign e
  workspace: 201.
- Filtros `campaign`, `status`, `action_type` e `recommendation_ref`: 200 e pelo
  menos um resultado correspondente em cada caso.
- `POST /api/v1/campaign-actions/{id}/dismiss/`: 200, status `dismissed` e motivo
  aceites.
- Sem autenticação: 401.
- Sem `X-Workspace-ID`: 400.
- Viewer sem `campaigns:update` a criar: 403.
- UUID de action inexistente: 404.
- `action_type` inválido: 400 com erro no campo. O Backend Core/DRF usa 400, não
  422, para este contrato.
- Campaign de outro workspace no payload: 400 com erro em `campaign`.
- Related report de outro workspace no payload: 400 com erro em
  `related_report`.

#### Testes automatizados

- Suite completa `apps/campaign_actions/tests`: 56 passed.
- Subset API `apps/campaign_actions/tests/test_api.py`: 13 passed.
- Warnings não funcionais:
  - directório `staticfiles` ausente em ambiente local;
  - pytest sem permissão para actualizar `.pytest_cache`.

### Pendências, riscos ou próximo passo recomendado

- Resolver a acessibilidade do `backend_core/db.sqlite3` local ou validar contra
  PostgreSQL de desenvolvimento/staging. Não foi feito troubleshooting adicional
  nesta execução.
- Remover manualmente a base sintética em `%TEMP%` quando a política do ambiente
  o permitir.
- Exercitar a constraint parcial anti-duplicação em PostgreSQL/CI.
- A validação não cobre sincronização automática com artefactos, backfill de
  histórico ou AuditEvent, porque essas capacidades não estão implementadas.
- Próximo passo recomendado: integrar o frontend exclusivamente com esta API e
  repetir estes smoke tests em staging com PostgreSQL e o fluxo de autenticação
  do ambiente.
