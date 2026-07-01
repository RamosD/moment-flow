# Prompt 01 — Investigação dos padrões do Backend Core

## Execução de 2026-06-30 21:44:56 -01:00

- **Estado da execução:** executado
- **Backlog:** BE-CA-001 — Investigar padrões existentes no Backend Core
- **Alterações runtime:** nenhuma

## Resumo objectivo

Foi lido integralmente o backlog `docs/campaign_actions/01_backlog.md` e foram
inspeccionados os padrões actuais de `core`, `workspaces`, `rbac`, `campaigns`,
`content`, `reports`, `audit`, configuração, routing, OpenAPI, migrations e testes.

A decisão técnica é criar uma app de domínio dedicada:

```text
apps/campaign_actions
```

e não colocar `CampaignAction` dentro de `apps/campaigns`.

Razões principais:

1. `CampaignAction` tem ciclo de vida, estados, filtros, transições e API próprios.
2. A entidade relaciona o domínio `campaigns` com artefactos de `content` e
   `reports`; não é apenas uma propriedade de `Campaign`.
3. `campaigns` é hoje uma dependência a montante de `content` e `reports`. Uma app
   dedicada pode depender das migrations iniciais das três apps sem carregar
   `campaigns` com dependências descendentes e sem misturar responsabilidades.
4. O projecto já está organizado em apps por domínio (`campaigns`, `content`,
   `reports`, `links`, `notifications`, `audit`, etc.).
5. A nova tabela pode ser introduzida de forma aditiva e isolada, sem alterar as
   tabelas e contratos existentes.

## Padrões confirmados

### Apps Django

- Apps locais vivem em `apps/<dominio>` e usam `AppConfig` em `apps.py`.
- A estrutura recorrente é `models.py`, `serializers.py`, `filters.py`, `views.py`,
  `urls.py`, `admin.py`, `migrations/` e `tests/`.
- Cada app regista os seus viewsets num `DefaultRouter`; `config/urls.py` monta o
  `urls.py` da app sob `/api/v1/`.
- A app deve ser adicionada a `INSTALLED_APPS` e incluída em `config/urls.py`.

### Identidade, timestamps e ownership

- `BaseModel` fornece UUID não sequencial, `created_at`, `updated_at` e ordenação
  por `-created_at`.
- `WorkspaceOwnedModel` fornece uma FK obrigatória `workspace` com
  `on_delete=CASCADE`.
- `CreatedUpdatedByModel` fornece `created_by` e `updated_by` opcionais, ambos
  para `settings.AUTH_USER_MODEL`, com `SET_NULL`.
- O user real é `accounts.User`, identificado por UUID e email.
- Para `CampaignAction`, o padrão recomendado é herdar de `BaseModel`,
  `WorkspaceOwnedModel` e `CreatedUpdatedByModel`.
- Não se recomenda `SoftDeleteModel`: a entidade já tem estados terminais
  `cancelled` e `dismissed`, e a API alvo não precisa de DELETE. Isto segue o
  padrão de `Report`, que usa lifecycle em vez de soft delete.

### Workspace e campaign

- O workspace activo vem exclusivamente do header público autenticado
  `X-Workspace-ID`.
- Header ausente/malformado produz 400; workspace inexistente ou membership não
  activa produz 403 sem revelar a existência do tenant.
- Não há workspace global implícito.
- `Campaign` é `WorkspaceOwnedModel`, tem UUID, soft delete e `created_by` /
  `updated_by`.
- `CampaignAction.workspace` deve ser sempre preenchido no servidor com
  `request.workspace`; nunca deve ser writable no serializer.
- `CampaignAction.campaign` deve ser obrigatório e validado contra o workspace
  activo. O padrão corrente faz esta validação nos serializers.

### JSON, nomes e enums

- Metadata usa `models.JSONField(default=dict, blank=True)`.
- O mesmo padrão serve para `recommendation_snapshot`, com validação adicional de
  tamanho/estrutura a definir antes da implementação.
- Choices são classes internas `models.TextChoices` (`Status`, `ActionType`, etc.)
  e os valores persistidos usam `snake_case`.
- Models, serializers e viewsets usam singular em PascalCase; rotas usam plural
  em kebab-case, pelo que a rota é `campaign-actions`.
- O backend usa nomes JSON em `snake_case`; o frontend actual projecta campos em
  camelCase e precisará de adaptação explícita.

### Viewsets, permissões e scoping

- O padrão central é `WorkspaceScopedRBACViewSet`.
- A base combina JWT (`IsAuthenticated`), `HasWorkspacePermission`,
  `lookup_field = "id"` e queryset filtrado por `request.workspace`.
- Objectos de outro workspace ficam fora do queryset e detalhes/updates devolvem
  404; membership inválida devolve 403.
- Cada viewset declara `required_permissions` por action DRF (`list`, `retrieve`,
  `create`, `partial_update`, actions custom, etc.).
- Para o MVP recomenda-se reutilizar permissões existentes, evitando alterar a
  matriz RBAC nesta fase:

  ```text
  list/retrieve  -> campaigns:view
  create         -> campaigns:update
  partial_update -> campaigns:update
  transições     -> campaigns:update
  ```

  Uma permission set nova `campaign_actions:*` só deve ser introduzida se houver
  uma decisão de produto para gerir Campaign Actions separadamente. Isso exigiria
  alterar `apps/rbac/seeds.py`, mapear todos os roles e garantir que o seed é
  reaplicado em ambientes existentes.
- Não usar `X-Internal-Token`: esta é uma API pública JWT + workspace RBAC. O token
  interno permanece reservado às integrações service-to-service.

### Serializers e integridade cross-workspace

- `campaigns`, `content` e `reports` usam um mixin local que obtém
  `request.workspace` do contexto e compara `obj.workspace_id`.
- `workspace`, `created_by`, `updated_by`, timestamps e timestamps de transição
  devem ser read-only e atribuídos no servidor.
- `perform_create` deve passar `workspace=request.workspace` e
  `created_by=request.user`; `perform_update` deve passar
  `updated_by=request.user`.
- Validar individualmente `campaign` e todas as FKs `related_*`.
- A validação de CampaignAction deve ser mais forte do que apenas same-workspace:
  cada artefacto relacionado deve também pertencer à mesma campaign da action.
  Para `Report` e `MediaKit`, cuja `campaign` é opcional, não aceitar associação
  quando a campaign esteja vazia ou seja diferente.
- A validação deve funcionar também em PATCH, combinando os valores enviados com
  a instance existente.
- O comportamento corrente do DRF para erros de serializer é HTTP 400; o backlog
  aceita 400/422, portanto 400 é o contrato mais consistente.

### Filtros, ordenação e paginação

- Filtros usam `django_filters.FilterSet` e são ligados por `filterset_class`.
- O FilterSet alvo deve incluir `campaign`, `status`, `action_type`,
  `recommendation_ref`, `source` e `created_by`.
- O viewset deve expor `ordering_fields` e manter `-created_at` como default.
- A paginação global é `StandardResultsSetPagination`: 25 itens por omissão,
  `page_size` configurável e máximo 100.

### OpenAPI e routing

- `drf-spectacular` é o schema backend configurado globalmente.
- Viewsets workspace-scoped documentam `X-Workspace-ID` com
  `@extend_schema(parameters=[OpenApiParameter(...)])`.
- Serializers e `TextChoices` alimentam automaticamente componentes e enums.
- Actions custom devem declarar request/response serializers com
  `@extend_schema`.
- Endpoints existentes: `/api/v1/schema/`, `/api/v1/docs/` e
  `/api/v1/redoc/`.
- O artefacto local é regenerado com
  `python manage.py spectacular --file schema.yml` quando a API for implementada.

### Testes e factories

- Testes usam `pytest`, `pytest-django`, DRF `APIClient` e factory-boy.
- Há fixtures por app e fixtures partilhadas em `tests/conftest.py`.
- `tests/factories.py` usa `SelfAttribute` para herdar workspace do parent e
  impedir grafos cross-tenant acidentais.
- Os testes de referência cobrem 400 de FK cross-workspace, 403 de membership ou
  RBAC, 404 para objectos fora do queryset, paginação/filtros e campos atribuídos
  pelo servidor.
- A nova factory deve derivar `workspace` de `campaign.workspace`.

## Contrato conceptual recomendado

Sem implementar ainda, a próxima iteração deve seguir este desenho:

- Model em `apps/campaign_actions/models.py`.
- `CampaignAction(BaseModel, WorkspaceOwnedModel, CreatedUpdatedByModel)`.
- `campaign`: FK obrigatória para `campaigns.Campaign`.
- `recommendation_ref`: string funcional externa, opcional apenas para
  `manual_task`; não é FK do Intelligence Engine.
- `recommendation_snapshot` e `metadata`: JSON objects com `default=dict`.
- `action_type`: `TextChoices` com o MVP do backlog (`content_pack`,
  `report_request`, `media_kit_request`, `manual_task`, `mark_reviewed`,
  `dismiss`). `asset_request` permanece fora do MVP até decisão explícita.
- `status`: apenas `pending`, `in_progress`, `completed`, `failed`, `dismissed`,
  `cancelled`. O `unknown` do frontend é um estado de projecção e não deve ser
  persistido.
- `source`: pelo menos `recommendation` e `manual`, alinhado com o frontend.
- `dismiss_reason`, `completed_at`, `cancelled_at` e FKs `related_*` opcionais.
- FKs de artefacto com `SET_NULL`, para preservar a action como registo histórico
  caso o artefacto deixe de existir.
- API sem DELETE; lifecycle controlado por PATCH/actions semânticas.
- Regras de transição centralizadas num serviço ou método único, usado tanto por
  PATCH como por actions custom, para não divergir timestamps e validações.

## Decisões ainda necessárias antes de fechar o model

1. **Priority:** o backlog sugere valores como `medium`, mas o frontend actual
   aceita texto livre e pode produzir valores como `Priority 1`. Não criar um
   enum rígido sem definir a normalização/migração do frontend. Opções seguras:
   CharField livre no primeiro contrato, ou enum `low/medium/high/urgent` com
   adaptação frontend explícita.
2. **Anti-duplicação:** a chave sugerida
   `(workspace, campaign, recommendation_ref, action_type)` apenas para estados
   activos pode ser uma `UniqueConstraint(condition=...)`, suportada pelos DBs
   alvo, mas precisa de excluir refs vazias e de definir exactamente “activo”.
   Uma validação apenas no serializer tem race condition. Recomenda-se fechar a
   semântica antes de gerar a migration.
3. **Transições:** definir a matriz completa. `dismiss` deve exigir motivo;
   `completed` deve definir `completed_at`; `cancelled` deve definir
   `cancelled_at`; sair de estados terminais deve ser bloqueado salvo decisão
   explícita.
4. **Actions custom:** o padrão do projecto suporta `@action`. Recomenda-se
   `dismiss` e `mark-reviewed` como actions semânticas; PATCH continua adequado
   para edição normal e outras transições, desde que use a mesma regra central.
5. **Sincronização:** decidir se `CampaignAction.status` é independente ou se
   acompanha callbacks dos artefactos. Sem integração adicional, os dois estados
   podem divergir.

## Audit/events existentes

- Existe `apps.audit` com `AuditEvent` append-only e o serviço público interno
  `record_audit_event(...)`.
- O serviço regista actor, workspace, entidade, snapshots before/after, metadata
  e hashes de IP/user-agent.
- É adequado para futura auditoria de criação/transições de CampaignAction.
- Existe também `billing.UsageEvent`, mas é medição de uso/billing e não deve ser
  reutilizado como histórico da action.
- Conforme solicitado, nenhuma integração com audit/events foi feita nesta
  iteração.

## Ficheiros prováveis nos próximos prompts

### Novos

```text
apps/campaign_actions/__init__.py
apps/campaign_actions/apps.py
apps/campaign_actions/models.py
apps/campaign_actions/serializers.py
apps/campaign_actions/filters.py
apps/campaign_actions/services.py
apps/campaign_actions/views.py
apps/campaign_actions/urls.py
apps/campaign_actions/admin.py
apps/campaign_actions/migrations/__init__.py
apps/campaign_actions/migrations/0001_initial.py
apps/campaign_actions/tests/__init__.py
apps/campaign_actions/tests/conftest.py
apps/campaign_actions/tests/test_models.py
apps/campaign_actions/tests/test_campaign_actions_api.py
apps/campaign_actions/tests/test_permissions.py
apps/campaign_actions/tests/test_transitions.py
```

### A alterar

```text
config/settings.py
config/urls.py
tests/factories.py
tests/test_multitenancy.py
schema.yml                         # artefacto gerado/validado
docs/campaign_actions/arquitectura_campaign_actions_backend.md
```

`apps/rbac/seeds.py` só entra nesta lista se for aprovada uma permission set nova.
Não é necessário alterar Intelligence Engine, Content Renderer, nem os models
existentes de campaigns/content/reports para criar as FKs a partir da nova app.

## Riscos e bloqueios

| Risco | Impacto | Mitigação recomendada |
| --- | --- | --- |
| Leak cross-workspace por FK relacionada | Crítico | Validar todas as FKs contra `request.workspace` e cobrir cada uma com testes 400. |
| Artefacto do mesmo workspace mas de outra campaign | Alto | Validar simultaneamente workspace e `campaign_id`, incluindo PATCH. |
| Estado da action divergir do estado do artefacto | Alto | Definir source of truth e política de sincronização antes de integrar callbacks. |
| Acções históricas desaparecerem ao frontend trocar de projecção para a nova API | Alto | Decidir backfill/import dos artefactos que já têm `metadata.recommendation_ref`, ou documentar corte temporal. |
| `recommendation_ref` instável ou excessivamente longo | Alto | Tratar como string externa, definir `max_length`, indexar e guardar snapshot mínimo. |
| Snapshot/metadata excessivo ou sensível | Alto | Validar object, tamanho e chaves aceites; não copiar payload integral sem decisão. |
| Constraint anti-duplicação demasiado rígida | Médio/Alto | Definir estados activos, tratamento de string vazia e concorrência antes da migration. |
| Semântica de priority incompatível com frontend | Médio | Fechar vocabulário ou manter string livre no primeiro contrato. |
| Permissões novas deixarem roles existentes sem acesso | Alto | Reutilizar `campaigns:*` no MVP ou acompanhar nova permission com seed/deploy explícito. |
| Efeito de `on_delete` inesperado | Médio | Campaign obrigatória com política explícita; related artefacts com `SET_NULL`; testes de preservação histórica. |
| SQLite/PostgreSQL divergirem em constraint/index | Médio | Validar migration e testes nos dois motores antes de produção. |
| Acoplamento circular de migrations | Baixo com app dedicada | Migration inicial da nova app depende das migrations de campaigns/content/reports; nenhuma app existente passa a depender dela. |

Não há bloqueio para iniciar BE-CA-002. Há, contudo, quatro decisões que devem ser
fechadas nesse prompt antes de consolidar a migration: priority, constraint de
duplicação, matriz de transições e política de dados legados.

## Ficheiros criados ou alterados nesta execução

- Criado
  `docs/campaign_actions/resultados_execucao/prompt_01_investigar_padroes_backend_resultado.md`.
- Criada a pasta `docs/campaign_actions/resultados_execucao` como consequência do
  ficheiro acima.
- Nenhum ficheiro runtime foi alterado.

## Validações executadas e resultado

| Validação | Resultado |
| --- | --- |
| Leitura integral de `docs/campaign_actions/01_backlog.md` | OK |
| Inspecção estática das apps, settings, URLs, migrations, schema e testes pedidos | OK |
| Inspecção dos tipos/payloads frontend actuais de Campaign Actions | OK; incompatibilidades registadas |
| `venv/Scripts/python.exe manage.py check` | OK — 0 issues |
| Pytest dirigido a campaigns/content/reports/RBAC de referência | OK — 36 passed; 37 warnings já existentes |
| Browser/servidores/migrations | Não executados, conforme instrução |

Nota de execução: o wrapper do comando de testes atingiu o timeout depois de o
pytest já ter emitido o resumo `36 passed in 73.07s`. Os warnings foram sobre a
pasta `staticfiles` ausente e impossibilidade de actualizar `.pytest_cache`; não
houve falhas de teste. `git status` não pôde ser usado porque este workspace não
foi exposto como working tree Git; a verificação de alterações foi feita por
inspecção directa dos caminhos.

## Próximo passo recomendado

Executar BE-CA-002 numa app nova `apps/campaign_actions`, começando por fechar as
quatro decisões pendentes e criar apenas o model/migration aditivos. Não integrar
audit, callbacks, frontend ou serviços internos nesse passo.
