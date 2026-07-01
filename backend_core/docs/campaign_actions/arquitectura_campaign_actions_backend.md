# Arquitectura e contrato da CampaignAction API

> Estado documentado: 2026-07-01  
> Implementação: Backend Core Django/DRF  
> Base URL: `/api/v1/`

## 1. Objectivo

CampaignAction é a entidade persistente que representa uma decisão ou acção
operacional associada a uma campaign.

Resolve o intervalo que existia entre uma recommendation transitória e os
artefactos reais criados pelo produto:

```text
recommendation -> CampaignAction -> artefacto existente opcional
```

A entidade permite saber que recommendation foi tratada, qual a acção escolhida,
quem a criou, qual o seu estado e a que artefacto real ficou ligada.

CampaignAction não substitui Campaign, ContentPackRequest, ContentOutput, Report
ou MediaKit. É uma camada de rastreio operacional.

## 2. Fronteira de segurança

CampaignAction é uma **API pública autenticada do Backend Core**.

- Usa a autenticação JWT normal do Backend Core.
- Exige `X-Workspace-ID` em todas as operações.
- Aplica membership e RBAC do workspace.
- Não usa `X-Internal-Token`.
- Não expõe nem espera `INTERNAL_API_TOKEN`.
- Não chama o Intelligence Engine directamente.
- Não chama o Content Renderer ou Report Renderer directamente.
- Não cria jobs internos nem callbacks.

Headers esperados pelo cliente:

```http
Authorization: Bearer <jwt>
X-Workspace-ID: <workspace-uuid>
Content-Type: application/json
```

## 3. Localização da implementação

A implementação vive numa app de domínio dedicada:

```text
apps/campaign_actions/
  admin.py
  apps.py
  filters.py
  models.py
  serializers.py
  services.py
  urls.py
  views.py
  migrations/0001_initial.py
  tests/
```

Integração no projecto:

- `apps.campaign_actions` está em `INSTALLED_APPS`;
- `apps.campaign_actions.urls` está montado em `/api/v1/`;
- o router DRF regista `campaign-actions`;
- o schema usa drf-spectacular.

## 4. Model persistente

Classe:

```text
CampaignAction(BaseModel, WorkspaceOwnedModel, CreatedUpdatedByModel)
```

Não usa soft delete. O lifecycle é representado por status terminais.

### 4.1 Campos

| Campo | Tipo/model | Default | Contrato API |
| --- | --- | --- | --- |
| `id` | UUID PK | UUID gerado | read-only |
| `workspace` | FK Workspace, CASCADE | obrigatório | read-only; vem de `X-Workspace-ID` |
| `campaign` | FK Campaign, CASCADE | obrigatório | create-only/imutável |
| `recommendation_ref` | CharField(512) | `""` | obrigatório salvo `manual_task`; imutável |
| `recommendation_snapshot` | JSONField | `{}` | object JSON; imutável |
| `title` | CharField(255) | obrigatório | writable |
| `description` | TextField | `""` | writable |
| `action_type` | TextChoices | obrigatório | create-only/imutável |
| `status` | TextChoices | `pending` | writable via PATCH/serviço |
| `priority` | TextChoices | `medium` | writable |
| `source` | TextChoices | `manual` | create-only/imutável |
| `dismiss_reason` | TextField | `""` | requerido quando dismissed |
| `metadata` | JSONField | `{}` | JSON livre, writable |
| `related_content_pack_request` | FK nullable, SET_NULL | `null` | writable, opcional |
| `related_content_output` | FK nullable, SET_NULL | `null` | writable, opcional |
| `related_report` | FK nullable, SET_NULL | `null` | writable, opcional |
| `related_media_kit` | FK nullable, SET_NULL | `null` | writable, opcional |
| `created_by` | FK User, SET_NULL | `null` | read-only; preenchido pelo servidor |
| `updated_by` | FK User, SET_NULL | `null` | interno; não aparece no serializer |
| `completed_at` | DateTime nullable | `null` | read-only; calculado |
| `cancelled_at` | DateTime nullable | `null` | read-only; calculado |
| `created_at` | DateTime | automático | read-only |
| `updated_at` | DateTime | automático | read-only |

### 4.2 Índices

```text
workspace + campaign
workspace + campaign + recommendation_ref
status
action_type
created_at
```

### 4.3 Anti-duplicação

Existe uma `UniqueConstraint` parcial chamada
`unique_active_campaign_action` sobre:

```text
workspace + campaign + recommendation_ref + action_type
```

A constraint aplica-se quando:

- `recommendation_ref` não está vazia; e
- status é `pending`, `in_progress` ou `completed`.

Uma nova action com a mesma chave é permitida se a anterior estiver `failed`,
`dismissed` ou `cancelled`. O serializer faz a mesma verificação para devolver
erro 400 legível; a constraint protege contra concorrência.

## 5. Action types

| Valor | Semântica | Relações permitidas |
| --- | --- | --- |
| `content_pack` | Pedido/resultado de content pack | ContentPackRequest e/ou ContentOutput |
| `report_request` | Pedido de report | Report |
| `media_kit_request` | Pedido de media kit | MediaKit |
| `manual_task` | Tarefa manual sem artefacto técnico | nenhuma |
| `mark_reviewed` | Recommendation analisada sem artefacto | nenhuma; cria como completed |
| `dismiss` | Recommendation rejeitada | nenhuma; cria como dismissed |

Não estão implementados como action types:

```text
asset_request
content_output
automation
```

ContentOutput pode ser relacionado a uma action `content_pack`, mas não é um
action type autónomo.

## 6. Priority e source

Priority aceita apenas:

```text
low
medium
high
urgent
```

Source aceita apenas:

```text
recommendation
manual
```

O frontend deve normalizar prioridades livres antigas antes de usar a API nova.

## 7. Estados e lifecycle

Estados:

```text
pending
in_progress
completed
failed
dismissed
cancelled
```

### 7.1 Matriz permitida

```text
pending -> in_progress | completed | failed | dismissed | cancelled

in_progress -> completed | failed | cancelled

completed -> terminal
failed    -> terminal
dismissed -> terminal
cancelled -> terminal
```

Repetir o estado actual é idempotente. `failed` não reabre; retry cria uma nova
CampaignAction.

### 7.2 Timestamps e motivo

- Ao entrar em `completed`, o serviço define `completed_at` uma única vez.
- Ao entrar em `cancelled`, define `cancelled_at` uma única vez.
- Repetir completed/cancelled preserva o timestamp original.
- `dismissed` exige `dismiss_reason` não vazio e normalizado.
- Dismiss não usa completed/cancelled timestamps.
- Timestamps incompatíveis são limpos defensivamente pelo serviço.
- `updated_by` recebe o actor autenticado.

As transições usam `transaction.atomic` e `select_for_update`.

## 8. Endpoints reais

| Método | Endpoint | Operação |
| --- | --- | --- |
| GET | `/api/v1/campaign-actions/` | lista paginada |
| POST | `/api/v1/campaign-actions/` | cria action |
| GET | `/api/v1/campaign-actions/{id}/` | detail |
| PATCH | `/api/v1/campaign-actions/{id}/` | actualização parcial/transição |
| POST | `/api/v1/campaign-actions/{id}/mark-reviewed/` | transita para completed |
| POST | `/api/v1/campaign-actions/{id}/dismiss/` | transita para dismissed |
| POST | `/api/v1/campaign-actions/{id}/cancel/` | transita para cancelled |
| POST | `/api/v1/campaign-actions/{id}/complete/` | transita para completed |

PUT e DELETE não são suportados; devolvem 405.

## 9. Payloads principais

Todos os exemplos usam placeholders, não identificadores ou credenciais reais.

### 9.1 Criar tarefa manual

```json
{
  "campaign": "<campaign-uuid>",
  "title": "Contactar parceiro de media",
  "description": "Confirmar disponibilidade para a campanha.",
  "action_type": "manual_task",
  "priority": "medium",
  "source": "manual",
  "metadata": {}
}
```

`manual_task` não exige recommendation ref nem snapshot.

### 9.2 Criar action a partir de recommendation

```json
{
  "campaign": "<campaign-uuid>",
  "recommendation_ref": "<opaque-recommendation-ref>",
  "recommendation_snapshot": {
    "title": "Prepare campaign report",
    "description": "Summarise campaign progress",
    "type": "report",
    "priority": "high",
    "confidence": 0.82
  },
  "title": "Create campaign report",
  "description": "Generate the report for review.",
  "action_type": "report_request",
  "priority": "high",
  "source": "recommendation",
  "related_report": "<report-uuid>",
  "metadata": {}
}
```

`related_report` é opcional. A action pode ser criada antes e ligada por PATCH,
embora o fluxo recomendado seja criar primeiro o artefacto.

### 9.3 Ligar um artefacto existente

```http
PATCH /api/v1/campaign-actions/<action-uuid>/
```

```json
{
  "related_content_pack_request": "<content-pack-request-uuid>",
  "related_content_output": "<content-output-uuid>"
}
```

### 9.4 Actualizar estado por PATCH

```json
{
  "status": "in_progress"
}
```

PATCH usa a mesma matriz transaccional das operations semânticas.

### 9.5 Dismiss semântico

```http
POST /api/v1/campaign-actions/<action-uuid>/dismiss/
```

```json
{
  "dismiss_reason": "Not relevant for the current campaign."
}
```

As actions `mark-reviewed`, `cancel` e `complete` não recebem body.

### 9.6 Resposta/lista

Campos JSON usam snake_case. A lista usa o envelope global de paginação:

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "<action-uuid>",
      "workspace": "<workspace-uuid>",
      "campaign": "<campaign-uuid>",
      "recommendation_ref": "<opaque-recommendation-ref>",
      "recommendation_snapshot": {},
      "title": "Create campaign report",
      "description": "",
      "action_type": "report_request",
      "status": "pending",
      "priority": "medium",
      "source": "recommendation",
      "dismiss_reason": "",
      "metadata": {},
      "related_content_pack_request": null,
      "related_content_output": null,
      "related_report": "<report-uuid>",
      "related_media_kit": null,
      "created_by": "<user-uuid>",
      "completed_at": null,
      "cancelled_at": null,
      "created_at": "<iso-8601-datetime>",
      "updated_at": "<iso-8601-datetime>"
    }
  ]
}
```

## 10. Campos actualizáveis e imutáveis

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

Create-only/imutáveis:

```text
campaign
recommendation_ref
recommendation_snapshot
action_type
source
```

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

`updated_by` existe no model, mas não faz parte da representação pública.

## 11. Filtros, pesquisa, ordenação e paginação

Filtros exactos:

```text
campaign
status
action_type
recommendation_ref
source
created_by
```

Exemplo:

```http
GET /api/v1/campaign-actions/?campaign=<campaign-uuid>&status=pending
```

Pesquisa textual (`search`):

```text
title
description
recommendation_ref
```

Ordenação (`ordering`):

```text
created_at
updated_at
status
priority
action_type
```

Prefixo `-` selecciona ordem descendente. O default é `-created_at`.

Paginação:

- 25 itens por omissão;
- query parameter `page_size`;
- máximo 100 itens por página.

## 12. Permissões e workspace scoping

Permissões:

| Operação | Permission RBAC |
| --- | --- |
| list/retrieve | `campaigns:view` |
| create/PATCH | `campaigns:update` |
| mark-reviewed/dismiss/cancel/complete | `campaigns:update` |

Com os roles actuais, viewer pode ler mas não criar/alterar.

O workspace activo é resolvido exclusivamente de `X-Workspace-ID` e exige uma
membership activa.

Comportamento de segurança:

| Situação | Resultado |
| --- | --- |
| Sem autenticação | 401 |
| Header ausente ou UUID inválido | 400 |
| Sem membership activa | 403 |
| Sem permission RBAC | 403 |
| Detail de outro workspace | 404 |
| Campaign/artefacto de outro workspace no payload | 400 de campo |

`workspace` enviado no body é ignorado por ser read-only; o servidor usa sempre
`request.workspace`.

## 13. Recommendations

### 13.1 recommendation_ref

`recommendation_ref` é uma string opaca de correlação, não uma FK e não um id
nativo garantido do Intelligence Engine.

- máximo 512 caracteres;
- é normalizada com trim;
- obrigatória salvo `manual_task`;
- imutável depois da criação;
- participa na regra anti-duplicação.

O backend não interpreta a estrutura interna da ref. O frontend pode continuar a
usar a convenção derivada existente, mas não deve tratá-la como identificador de
uma entidade persistida fora do Backend Core.

### 13.2 recommendation_snapshot

O snapshot preserva contexto mínimo porque recommendations são recalculadas e
podem não ter id estável.

Regras reais:

- object JSON no topo; arrays/primitivos são rejeitados;
- pode ser omitido para `manual_task`;
- tem de ser não vazio para os restantes action types;
- máximo 65 536 bytes após codificação JSON UTF-8;
- imutável depois da criação.

Chaves sensíveis conhecidas são rejeitadas na escrita e redigidas na leitura de
dados legados/directos. A lista inclui nomes como password, token, api key,
authorization, private key e client secret.

O snapshot não deve conter o payload integral da intelligence. Deve conter apenas
o contexto necessário para histórico e UI.

`metadata` é diferente: permanece JSON livre sem schema de negócio rígido.

## 14. Relação com artefactos reais

### 14.1 Campos reais dos artefactos

| Artefacto | Workspace | Campaign |
| --- | --- | --- |
| ContentPackRequest | obrigatória | obrigatória |
| ContentOutput | obrigatória | obrigatória |
| Report | obrigatória | nullable |
| MediaKit | obrigatória | nullable |

Para ser relacionado, qualquer artefacto tem de pertencer ao mesmo workspace e
à mesma campaign da CampaignAction.

Report e MediaKit com campaign nula são rejeitados, porque não existe evidência
relacional de que pertencem à campaign da action.

### 14.2 Compatibilidade

- `content_pack` aceita ContentPackRequest e/ou ContentOutput.
- `report_request` aceita apenas Report.
- `media_kit_request` aceita apenas MediaKit.
- `manual_task`, `mark_reviewed` e `dismiss` não aceitam artefactos.

Se request e output forem fornecidos juntos e o output tiver
`content_pack_request`, os requests têm de coincidir.

As FKs usam `SET_NULL`: remover o artefacto preserva a CampaignAction.

### 14.3 Fluxo em duas etapas

O Backend Core mantém ownership claro:

```text
1. Criar artefacto no endpoint proprietário.
2. Criar ou actualizar CampaignAction com related_*.
```

Endpoints proprietários:

```text
/api/v1/content-pack-requests/
/api/v1/content-outputs/
/api/v1/reports/
/api/v1/media-kits/
```

CampaignAction não cria o artefacto, não submete render job e não duplica billing,
callbacks ou regras do domínio proprietário.

## 15. Como o frontend deve consumir

1. Usar apenas o cliente autenticado do Backend Core.
2. Enviar JWT e `X-Workspace-ID`; nunca enviar headers internos.
3. Listar por campaign com `/campaign-actions/?campaign=<campaign-uuid>`.
4. Respeitar paginação; não assumir que todos os registos cabem numa página.
5. Para artefactos, criar primeiro no endpoint proprietário e depois persistir a
   CampaignAction ou fazer PATCH com a FK.
6. Usar as actions semânticas para reviewed/dismiss/cancel/complete.
7. Tratar erros 400 por campo e 403/404 sem inferir existência cross-workspace.
8. Normalizar priority para `low|medium|high|urgent`.
9. Mapear explicitamente snake_case backend para o modelo de UI.

O frontend actual projecta actions sobre três endpoints e usa campos como
`type`, `artifactKind`, `rawStatus`, `campaignId` e `createdAt`. A API persistente
não devolve esses campos. O contrato novo usa:

```text
action_type
related_content_pack_request / related_content_output / related_report / related_media_kit
status
campaign
created_at / updated_at
```

A migração frontend deve substituir a projecção best-effort conscientemente; não
deve apenas trocar a URL mantendo os tipos antigos.

## 16. O que não fazer

- Não chamar Intelligence Engine ou renderers directamente a partir do frontend.
- Não enviar `X-Internal-Token` ou qualquer secret interno.
- Não tentar escolher workspace através do body.
- Não assumir que recommendation ref é id nativo do Intelligence Engine.
- Não guardar payload integral/sensível da intelligence no snapshot.
- Não assumir que POST CampaignAction cria Report, MediaKit ou conteúdo.
- Não ligar artefactos de outro workspace/campaign.
- Não alterar campaign, action type, source, ref ou snapshot depois da criação.
- Não usar PUT ou DELETE.
- Não reabrir actions terminais; retry após failed cria nova action.
- Não depender de metadata como substituto das FKs `related_*`.

## 17. OpenAPI e testes

Schema e documentação interactiva:

```text
GET /api/v1/schema/
GET /api/v1/docs/
GET /api/v1/redoc/
```

A geração local com `python manage.py spectacular --validate` inclui os seis
paths CampaignAction (collection, detail e quatro actions semânticas), JWT,
header workspace, filtros, enums e payload dismiss.

Suite da app:

```text
56 passed
```

Cobertura funcional inclui CRUD, autenticação/header, RBAC, scoping, filtros,
duplicação, lifecycle e artefactos relacionados.

## 18. Limitações e riscos actuais

1. **Sem backfill:** artefactos históricos com `metadata.recommendation_ref` não
   geram CampaignAction automaticamente. O frontend não deve perder histórico ao
   migrar sem uma decisão de import/corte temporal.
2. **Sem sincronização automática:** status do artefacto e da action podem
   divergir. Callbacks de content/reports não actualizam CampaignAction.
3. **Sem auditoria CampaignAction:** o projecto tem `AuditEvent`, mas estas
   transições ainda não o usam.
4. **Validação na camada API:** ORM/admin directo pode contornar lifecycle e
   validações cross-model.
5. **Drift posterior:** um Report/MediaKit/ContentOutput pode ser alterado depois
   da ligação e deixar de coincidir com a campaign da action.
6. **Sem automação:** não existem scheduler, WebSockets, workflow engine ou
   criação automática de artefactos.
7. **Sem teste PostgreSQL nesta execução:** a constraint parcial foi validada em
   SQLite; PostgreSQL deve ser exercitado em CI/staging.
8. **Migration local pendente neste workspace:** a migration foi validada em
   bases de teste/in-memory, mas o `db.sqlite3` local não pôde ser escrito por
   limitação do ambiente.
9. **Suite global pendente:** passaram os 56 testes da app; a suite integral do
   Backend Core não foi executada nesta fase de documentação.

Estas limitações impedem declarar a feature pronta para produção sem validação
adicional, staging, auditoria e plano de migração frontend.
