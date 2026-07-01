# Prompt 02 — Criar model CampaignAction

## Execução de 2026-06-30 21:53:25 -01:00

- **Estado da execução:** executado_parcialmente
- **Backlog:** BE-CA-002 — Criar model CampaignAction
- **Código/model/migration:** concluídos
- **Aplicação ao `db.sqlite3` local:** pendente por limitação de escrita do ambiente

## Resumo objectivo

Foi criada a app dedicada `apps.campaign_actions`, conforme a decisão do Prompt
01, e implementada a entidade persistente `CampaignAction` com a migration
inicial correspondente.

O model segue os padrões do Backend Core:

- `BaseModel` para UUID, `created_at` e `updated_at`;
- `WorkspaceOwnedModel` para ownership obrigatório por workspace;
- `CreatedUpdatedByModel` para `created_by` e `updated_by` com `SET_NULL`;
- `JSONField(default=dict, blank=True)` para `recommendation_snapshot` e
  `metadata`;
- `TextChoices` para `action_type`, `status`, `priority` e `source`;
- relações opcionais para `ContentPackRequest`, `ContentOutput`, `Report` e
  `MediaKit`, todas com `SET_NULL` para preservar a action histórica;
- campaign obrigatória com `CASCADE` e reverse relation `campaign_actions`.

Não foram criados serializers, viewsets, URLs públicas ou alterações em frontend,
Intelligence Engine ou Content Renderer.

## Decisões implementadas

### Tipos

Foram incluídos os tipos MVP:

```text
content_pack
report_request
media_kit_request
manual_task
mark_reviewed
dismiss
```

`asset_request` ficou fora do model. Continua classificado no backlog como tipo
futuro/opcional e não existe execução automática correspondente.

### Estados

```text
pending
in_progress
completed
failed
dismissed
cancelled
```

O estado default é `pending`.

### Priority e source

- Priority: `low`, `medium`, `high`, `urgent`; default `medium`.
- Source: `recommendation`, `manual`; default `manual`.

O frontend actual ainda aceita prioridade livre. A futura adaptação para a API
persistente terá de normalizar os valores para este contrato.

### Índices

Foram criados explicitamente:

```text
workspace + campaign
workspace + campaign + recommendation_ref
status
action_type
created_at
```

### Constraint anti-duplicação

Foi criada a constraint parcial `unique_active_campaign_action` sobre:

```text
workspace + campaign + recommendation_ref + action_type
```

A constraint aplica-se apenas quando `recommendation_ref` não está vazia e o
status está em:

```text
pending
in_progress
completed
```

Isto segue a regra do backlog que permite nova action quando a anterior está em
`failed`, `dismissed` ou `cancelled`. Refs vazias, necessárias para `manual_task`
sem recommendation, não colidem.

A constraint foi validada em SQLite: um duplicado activo foi rejeitado com
`IntegrityError`, enquanto uma nova action em `failed` com a mesma chave foi
aceite.

## Ficheiros criados ou alterados

### Criados

```text
apps/campaign_actions/__init__.py
apps/campaign_actions/apps.py
apps/campaign_actions/models.py
apps/campaign_actions/admin.py
apps/campaign_actions/migrations/__init__.py
apps/campaign_actions/migrations/0001_initial.py
docs/campaign_actions/resultados_execucao/prompt_02_criar_model_campaign_action_resultado.md
```

### Alterados

```text
config/settings.py
```

`apps.campaign_actions` foi adicionado a `INSTALLED_APPS` entre `campaigns` e
`content`.

## Validações executadas e resultado

| Validação | Resultado |
| --- | --- |
| `python manage.py makemigrations campaign_actions` | O plano foi gerado, mas o Python não conseguiu criar o ficheiro por `PermissionError` no filesystem gerido. |
| `python manage.py makemigrations campaign_actions --dry-run --verbosity 3` | OK; forneceu a migration oficial completa. |
| Materialização da migration a partir da saída oficial | OK. |
| `python manage.py makemigrations` | OK — `No changes detected`. |
| `python manage.py makemigrations --check --dry-run` | OK — `No changes detected`; warning apenas por não conseguir abrir o DB local. |
| `python manage.py check` | OK — 0 issues. |
| `python manage.py migrate` sobre `db.sqlite3` local | Pendente/falhou — `django.db.utils.OperationalError: unable to open database file`. Nenhuma migration foi aplicada à base local. |
| Aplicação de todas as migrations numa base SQLite `:memory:` | OK, incluindo `campaign_actions.0001_initial`. |
| Teste da constraint parcial em SQLite `:memory:` | OK — duplicado activo bloqueado; retry `failed` permitido. |
| `pytest apps/core/tests/test_smoke.py -q` | OK — 3 passed; warning existente de `.pytest_cache` sem permissão. |
| `ruff check --no-cache apps/campaign_actions config/settings.py` | OK — All checks passed. |

O primeiro lint sem `--no-cache` também encontrou apenas a limitação de escrita
na `.ruff_cache`; foi repetido sem cache e passou.

## Pendências e riscos

1. **Aplicar à base local:** executar `python manage.py migrate` num ambiente onde
   `backend_core/db.sqlite3` seja gravável. Esta é a razão para o estado
   `executado_parcialmente`.
2. **Validação de negócio:** o model permite `recommendation_ref` vazia porque
   `manual_task` a admite. A obrigação da ref para outros tipos será aplicada no
   serializer/service do próximo prompt.
3. **Integridade cross-workspace/campaign:** as FKs existem, mas a validação de
   que campaign e todos os artefactos pertencem ao mesmo workspace/campaign fica
   para os serializers, conforme o backlog BE-CA-003.
4. **Transições e timestamps:** `completed_at`, `cancelled_at` e
   `dismiss_reason` estão persistidos, mas ainda não há serviço de transições que
   os preencha/valide. Isso pertence a BE-CA-005.
5. **Snapshot/metadata:** ainda não há limites de tamanho ou validação de
   estrutura; devem ser definidos no serializer para evitar payload excessivo ou
   sensível.
6. **Priority frontend:** valores livres actuais terão de ser mapeados para o enum
   do backend antes de o frontend passar a consumir `/campaign-actions/`.

## Próximo passo recomendado

Executar BE-CA-003: criar o serializer de CampaignAction com validação integral
de workspace/campaign, artefactos relacionados, recommendation ref/snapshot e
campos read-only. Antes disso, aplicar a migration ao DB local quando a permissão
de escrita estiver disponível.
