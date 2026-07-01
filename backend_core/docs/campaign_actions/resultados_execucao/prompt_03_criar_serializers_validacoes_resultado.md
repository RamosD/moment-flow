# Prompt 03 — Criar serializers e validações de CampaignAction

## Execução de 2026-06-30 22:01:11 -01:00

- **Estado da execução:** executado
- **Backlog:** BE-CA-003 — Criar serializers
- **Frontend/IE/Renderer:** sem alterações
- **Viewset/rotas:** não criados neste prompt

## Resumo objectivo

Foi criado `CampaignActionSerializer`, um `ModelSerializer` único para leitura,
criação e actualização parcial. A opção por um serializer único segue o padrão
actual das apps `campaigns`, `content` e `reports`; as diferenças entre create e
PATCH são tratadas por validação object-level com os valores efectivos da
instance.

O serializer inclui todos os campos públicos do contrato CampaignAction e marca
como read-only:

```text
id
workspace
created_by
completed_at
cancelled_at
created_at
updated_at
```

`workspace` e `created_by` serão atribuídos pelo futuro viewset, seguindo o
padrão `serializer.save(workspace=request.workspace,
created_by=request.user)`.

## Validações implementadas

### Workspace e campaign

- Escritas exigem `request.workspace` no contexto do serializer.
- `campaign` tem de pertencer ao workspace activo.
- Em PATCH, a campaign efectiva é obtida da instance quando não é enviada.
- A campaign não pode ser alterada depois da criação.

### Artefactos relacionados

Foram validados os quatro campos:

```text
related_content_pack_request
related_content_output
related_report
related_media_kit
```

Cada objecto tem de:

1. pertencer ao workspace activo;
2. pertencer à mesma campaign efectiva da CampaignAction.

Isto também se aplica a PATCH. Para `Report` ou `MediaKit` com campaign nula, a
associação é rejeitada por não corresponder à campaign da action.

### Choices

`action_type`, `status`, `priority` e `source` são validados automaticamente
pelos `TextChoices` do model através dos `ChoiceField` gerados pelo DRF. Valores
fora dos enums produzem erro de campo HTTP 400 quando usados na futura API.

### Dismiss

`dismiss_reason`, depois de normalizado com `strip()`, é obrigatório quando:

```text
action_type == dismiss
ou
status == dismissed
```

### Recommendation ref e snapshot

- `recommendation_ref` é normalizada com `strip()`.
- É obrigatória para todos os tipos excepto `manual_task`.
- `recommendation_snapshot` é opcional para `manual_task`.
- Para os restantes tipos, é obrigatório um snapshot não vazio.
- O snapshot tem de ser um objecto JSON; arrays/primitivos no topo são
  rejeitados.
- O tamanho máximo defensivo é 65 536 bytes após codificação JSON UTF-8.
- Chaves sensíveis conhecidas, inclusive aninhadas, são rejeitadas na escrita
  (`token`, `access_token`, `refresh_token`, `api_key`, `password`, `secret`,
  `authorization`, `private_key`, `client_secret`, `internal_api_token`, etc.).
- Na representação, essas chaves também são redigidas como `[REDACTED]`,
  protegendo dados legados ou inseridos por caminhos que não usam o serializer.

Não é assumido que `recommendation_ref` seja um id nativo do Intelligence
Engine.

### Metadata

`metadata` continua a usar o `JSONField` do model sem schema de negócio rígido.
A validação em memória confirmou que estruturas JSON livres, incluindo listas,
são aceites.

### Duplicação activa

Além da constraint parcial criada no model, o serializer faz uma pré-validação
para devolver erro de campo claro antes do INSERT.

A chave é:

```text
workspace + campaign + recommendation_ref + action_type
```

e aplica-se a `pending`, `in_progress` e `completed`. A instance corrente é
excluída em PATCH. A constraint de base de dados continua necessária para
proteger contra concorrência entre requests.

### Imutabilidade após criação

Os seguintes campos podem ser usados na criação, mas não podem ser alterados em
PATCH:

```text
campaign
recommendation_ref
recommendation_snapshot
action_type
source
```

Isto preserva a identidade e origem histórica da action e respeita a lista de
campos actualizáveis do backlog.

## Ficheiros criados ou alterados

### Criados

```text
apps/campaign_actions/serializers.py
docs/campaign_actions/resultados_execucao/prompt_03_criar_serializers_validacoes_resultado.md
```

Nenhum outro ficheiro runtime foi alterado.

## Validações executadas e resultado

| Validação | Resultado |
| --- | --- |
| `python manage.py check` | OK — 0 issues. |
| `ruff check --no-cache apps/campaign_actions/serializers.py` | OK — All checks passed. |
| Matriz de validação do serializer em SQLite `:memory:` | OK. |
| Campaign noutro workspace | Rejeitada. |
| Quatro FKs relacionadas noutro workspace/campaign | Rejeitadas. |
| `action_type` e `status` inválidos | Rejeitados. |
| Dismiss sem motivo | Rejeitado. |
| Ref ausente em tipo não-manual | Rejeitada. |
| Snapshot ausente em tipo não-manual | Rejeitado. |
| Snapshot sensível ou com shape inválido | Rejeitado; redacção de leitura confirmada. |
| Duplicado activo | Rejeitado pelo serializer. |
| Retry com estado `failed` | Aceite. |
| PATCH válido usando valores efectivos da instance | Aceite. |
| Testes existentes de isolamento em campaigns/content/reports | OK — 7 passed; 8 warnings ambientais já conhecidos. |
| Browser | Não utilizado. |

Os warnings dos testes são os já observados: pasta `staticfiles` ausente e
`.pytest_cache` sem permissão de escrita. Não houve falhas.

## Pendências e riscos

1. **Testes persistentes:** a matriz nova foi executada, mas ainda não existe uma
   suite versionada em `apps/campaign_actions/tests`. Deve ser criada em
   BE-CA-007 para evitar regressões.
2. **Lifecycle:** `completed_at` e `cancelled_at` são read-only, mas só serão
   preenchidos quando o serviço de transições de BE-CA-005 existir.
3. **Transições:** os enums são validados, mas a matriz origem → destino ainda não
   é aplicada neste prompt.
4. **Atribuição server-side:** sem viewset, `workspace`, `created_by` e
   `updated_by` ainda não são preenchidos por uma API.
5. **Dados sensíveis:** a lista defensiva cobre nomes de chaves conhecidos, mas
   nenhum detector consegue identificar segredos guardados sob nomes neutros. O
   snapshot deve continuar mínimo e nunca copiar indiscriminadamente o payload
   integral da intelligence.
6. **DB local:** mantém-se a pendência do Prompt 02 para aplicar
   `campaign_actions.0001_initial` ao `db.sqlite3` quando o ficheiro for gravável.

## Próximo passo recomendado

Executar BE-CA-004: criar filtros, `CampaignActionViewSet` workspace-scoped e
rota `/api/v1/campaign-actions/`, usando este serializer e atribuição server-side
de workspace/user. A implementação deve manter a API sem DELETE e sem
`X-Internal-Token`.
