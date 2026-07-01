# Prompt 04 — Criar API REST e rotas de CampaignAction

## Execução de 2026-06-30 22:06:10 -01:00

- **Estado da execução:** executado
- **Backlog:** BE-CA-004 — Criar viewset e rotas
- **API criada:** `/api/v1/campaign-actions/`
- **Frontend/IE/Renderer:** sem alterações

## Resumo objectivo

Foi criada a API REST pública autenticada de CampaignAction, seguindo o padrão
`WorkspaceScopedRBACViewSet` do Backend Core.

Operações expostas:

```text
GET   /api/v1/campaign-actions/
POST  /api/v1/campaign-actions/
GET   /api/v1/campaign-actions/{id}/
PATCH /api/v1/campaign-actions/{id}/
```

`PUT` e `DELETE` não são suportados e devolvem HTTP 405. Não foi criado qualquer
endpoint interno.

## Viewset e segurança

`CampaignActionViewSet` herda de `WorkspaceScopedRBACViewSet`, portanto aplica:

- autenticação JWT global do DRF;
- `IsAuthenticated`;
- `HasWorkspacePermission`;
- resolução obrigatória de `X-Workspace-ID`;
- membership activa no workspace;
- queryset filtrado por `request.workspace`;
- `lookup_field = id`;
- 404 para details de outro workspace, sem revelar o objecto.

A matriz RBAC reutiliza permissões existentes, conforme a decisão do Prompt 01:

```text
list/retrieve  -> campaigns:view
create         -> campaigns:update
partial_update -> campaigns:update
```

Isto evita introduzir permissions/roles novos e preserva a semântica actual:
viewers podem consultar actions, mas não criar nem actualizar.

`perform_create` atribui server-side:

```text
workspace = request.workspace
created_by = request.user
updated_by = request.user
```

`perform_update` actualiza `updated_by` com o utilizador autenticado.

CampaignAction não usa nem documenta `X-Internal-Token`.

## Filtros, pesquisa, ordenação e paginação

Foi criado `CampaignActionFilter` com filtros exactos para:

```text
campaign
status
action_type
recommendation_ref
source
created_by
```

O viewset também permite pesquisa por `title`, `description` e
`recommendation_ref`.

Ordenação default:

```text
-created_at
```

Campos de ordenação permitidos:

```text
created_at
updated_at
status
priority
action_type
```

A paginação é herdada da configuração global
`StandardResultsSetPagination`: 25 itens por omissão, `page_size` configurável e
máximo 100.

## OpenAPI

- A classe está anotada com `@extend_schema`.
- `X-Workspace-ID` aparece como header obrigatório nas quatro operações.
- As operações usam `jwtAuth` no schema.
- O schema contém os filtros e enums de CampaignAction.
- O schema gerado para CampaignAction contém apenas `GET`, `POST`, `GET detail` e
  `PATCH`.
- Não aparece `X-Internal-Token` em nenhuma operação CampaignAction.

O schema foi gerado e validado num ficheiro temporário. O `schema.yml` do
workspace não foi sobrescrito; a actualização formal do artefacto/documentação
continua prevista para BE-CA-008.

## Ficheiros criados ou alterados

### Criados

```text
apps/campaign_actions/filters.py
apps/campaign_actions/views.py
apps/campaign_actions/urls.py
docs/campaign_actions/resultados_execucao/prompt_04_criar_api_rotas_resultado.md
```

### Alterados

```text
config/urls.py
```

`config/urls.py` passou a incluir `apps.campaign_actions.urls` sob `/api/v1/`.

## Validações executadas e resultado

| Validação | Resultado |
| --- | --- |
| `python manage.py check` | OK — 0 issues. |
| `ruff check --no-cache apps/campaign_actions config/urls.py` | OK — All checks passed. |
| Resolução Django da rota list | OK — `campaign-action-list`. |
| Resolução Django da rota detail | OK — `campaign-action-detail`. |
| Geração `manage.py spectacular --validate` para ficheiro temporário | OK — sem erros/warnings emitidos. |
| `GET /api/v1/schema/` via Django test client | HTTP 200; contém `/api/v1/campaign-actions/`. |
| Schema CampaignAction | GET/POST/GET detail/PATCH presentes; sem PUT/DELETE. |
| Header público | `X-Workspace-ID` obrigatório e `jwtAuth` documentado. |
| Header interno nas operações CampaignAction | Ausente. |
| Request anónimo | HTTP 401. |
| Request autenticado sem `X-Workspace-ID` | HTTP 400. |
| Utilizador fora do workspace | HTTP 403. |
| List/create/detail/PATCH | OK. |
| PUT/DELETE | HTTP 405. |
| Detail cross-workspace | HTTP 404. |
| Lista cross-workspace | Isolada; nenhum id estrangeiro devolvido. |
| Filtros pedidos | Todos responderam com payload paginado. |
| Ordenação default | Registo mais recente primeiro. |
| Viewer list/create | GET 200; POST 403. |
| Atribuição de workspace/created_by/updated_by | Confirmada. |
| `pytest apps/core/tests/test_smoke.py -q` | OK — 3 passed; 1 warning ambiental de `.pytest_cache`. |
| Browser/servidor real | Não utilizados; test client e geração directa foram suficientes. |

A primeira execução do test client foi interrompida por `testserver` não constar
de `ALLOWED_HOSTS` fora do pytest. A matriz foi repetida com esse host permitido
apenas no processo de validação em memória e passou integralmente; não foi
alterada configuração runtime para acomodar o teste.

## Pendências e riscos

1. **Migration no DB local:** `campaign_actions.0001_initial` continua por
   aplicar ao `db.sqlite3` do workspace porque esse ficheiro não é gravável neste
   ambiente. A API foi validada com todas as migrations numa SQLite em memória.
2. **Transições de estado:** PATCH já aceita os valores válidos do enum, mas a
   matriz origem → destino e o preenchimento de `completed_at`/`cancelled_at`
   ainda pertencem a BE-CA-005. Até lá, é possível persistir um estado terminal
   sem o timestamp correspondente.
3. **Testes versionados:** a matriz API foi executada, mas a suite permanente de
   `apps/campaign_actions/tests` continua pendente para BE-CA-007.
4. **Schema versionado:** integração foi confirmada, mas o `schema.yml` principal
   só deve ser regenerado/entregue em BE-CA-008.
5. **Auditoria:** não foi integrada neste prompt, conforme o escopo anterior.

## Próximo passo recomendado

Executar BE-CA-005 imediatamente: centralizar transições de estado, bloquear
transições inválidas e preencher atomicamente `completed_at`, `cancelled_at` e
`dismiss_reason`, mantendo PATCH e futuras actions custom sobre a mesma regra de
serviço.
