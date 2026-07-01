# Prompt 05 — Transições de estado de CampaignAction

## Execução de 2026-06-30 22:17:56 -01:00

- **Estado da execução:** executado
- **Backlog:** BE-CA-005 — Implementar transições de estado
- **Workflow engine:** não criado
- **Geração de artefactos:** não automatizada
- **Frontend/IE/Renderer:** sem alterações

## Resumo objectivo

Foi criada uma camada de serviço transaccional única para controlar o lifecycle
de CampaignAction. PATCH e as operações semânticas usam exactamente a mesma
matriz, validações e política de timestamps.

Foram mantidas duas formas de operação:

1. **PATCH simples** para transições gerais, incluindo `in_progress` e `failed`;
2. **actions custom** para intenções com semântica forte, seguindo o precedente
   de `NotificationViewSet.read/read-all` existente no projecto.

Actions públicas adicionadas:

```text
POST /api/v1/campaign-actions/{id}/mark-reviewed/
POST /api/v1/campaign-actions/{id}/dismiss/
POST /api/v1/campaign-actions/{id}/cancel/
POST /api/v1/campaign-actions/{id}/complete/
```

Todas continuam autenticadas por JWT, workspace-scoped, protegidas por
`campaigns:update` e sem `X-Internal-Token`.

## Matriz de transições

```text
pending
  -> in_progress
  -> completed
  -> failed
  -> dismissed
  -> cancelled

in_progress
  -> completed
  -> failed
  -> cancelled

completed -> terminal
failed    -> terminal
dismissed -> terminal
cancelled -> terminal
```

Repetir o estado actual é permitido e idempotente.

`failed` é terminal por decisão de simplicidade. Um retry deve criar uma nova
CampaignAction; isto é coerente com a constraint anti-duplicação, que permite
uma nova action quando a anterior está `failed`, `dismissed` ou `cancelled`.

Não é permitido dismiss depois de a action entrar em `in_progress`.

## Política de timestamps e dismiss reason

### Completed

- Define `completed_at` apenas se ainda estiver vazio.
- Preserva o timestamp em repetições idempotentes.
- Limpa defensivamente `cancelled_at` e `dismiss_reason`.

### Cancelled

- Define `cancelled_at` apenas se ainda estiver vazio.
- Preserva o timestamp em repetições idempotentes.
- Limpa defensivamente `completed_at` e `dismiss_reason`.

### Dismissed

- Exige `dismiss_reason` não vazio.
- Normaliza o motivo com `strip()`.
- Não usa `completed_at` nem `cancelled_at`; ambos são limpos defensivamente.
- Repetir dismiss é idempotente e pode conservar/actualizar o motivo válido.

### Outros estados

`pending`, `in_progress` e `failed` não mantêm timestamps terminais nem
`dismiss_reason` quando passam pelo serviço.

`updated_by` é actualizado com o actor autenticado em PATCH e actions custom.

## Implementação

`apps/campaign_actions/services.py` contém:

```text
ALLOWED_STATUS_TRANSITIONS
CampaignActionTransitionError
validate_status_transition(...)
transition_campaign_action(...)
```

`transition_campaign_action` usa `transaction.atomic` e `select_for_update`,
evitando que dois requests concorrentes validem o mesmo estado antigo.

O serializer:

- pré-valida a transição para produzir HTTP 400 claro;
- executa create/update dentro de transacção;
- passa a transição persistente pelo serviço;
- mantém `completed_at` e `cancelled_at` read-only.

Na criação, quando o cliente omite `status`:

```text
action_type = mark_reviewed -> status = completed + completed_at
action_type = dismiss       -> status = dismissed + dismiss_reason obrigatório
restantes tipos             -> status = pending
```

Se o cliente fornecer explicitamente um status incompatível com
`mark_reviewed` ou `dismiss`, a criação é rejeitada.

## Schema OpenAPI

- As quatro actions aparecem no schema como POST.
- Todas documentam `X-Workspace-ID`, `jwtAuth` e resposta
  `CampaignActionSerializer`.
- `dismiss` documenta `DismissCampaignActionSerializer`, com
  `dismiss_reason` obrigatório.
- As restantes actions documentam request sem body.
- A geração com `spectacular --validate` passou sem erros ou warnings emitidos.

## Ficheiros criados ou alterados

### Criados

```text
apps/campaign_actions/services.py
apps/campaign_actions/tests/__init__.py
apps/campaign_actions/tests/conftest.py
apps/campaign_actions/tests/test_transitions.py
docs/campaign_actions/resultados_execucao/prompt_05_transicoes_estado_resultado.md
```

### Alterados

```text
apps/campaign_actions/serializers.py
apps/campaign_actions/views.py
```

Não houve alteração de model ou migration.

## Validações executadas e resultado

| Validação | Resultado |
| --- | --- |
| `python manage.py check` | OK — 0 issues. |
| `ruff check --no-cache apps/campaign_actions` | OK — All checks passed. |
| `pytest apps/campaign_actions/tests/test_transitions.py -q` | OK — 22 passed. |
| Status inválido | HTTP 400. |
| Todas as transições permitidas | Cobertas e aceites. |
| Reabertura dos quatro estados terminais | Bloqueada com HTTP 400. |
| Dismiss sem motivo | HTTP 400. |
| Dismiss depois de `in_progress` | HTTP 400. |
| `completed_at` e `cancelled_at` | Preenchidos nos estados correspondentes. |
| Complete repetido | Idempotente; timestamp preservado. |
| Actions mark-reviewed/dismiss/cancel/complete | Cobertas pela API. |
| Criação semântica mark_reviewed/dismiss | Status/timestamps/motivo confirmados. |
| Geração e validação OpenAPI | OK; quatro paths semânticos presentes. |
| Browser | Não utilizado. |

Os 23 warnings finais são ambientais e já conhecidos: ausência da pasta
`staticfiles` e `.pytest_cache` sem permissão de escrita.

Numa execução intermédia, 13 testes passaram e 2 falharam porque o default
`pending` do model já era injectado pelo DRF mesmo quando o cliente omitia
`status`. A implementação foi corrigida para distinguir omissão através de
`initial_data`; a suite final passou integralmente com 22 testes.

## Pendências e riscos

1. **Migration local:** mantém-se a pendência ambiental de aplicar
   `campaign_actions.0001_initial` ao `db.sqlite3` do workspace.
2. **Bypass por ORM/admin:** regras de lifecycle vivem no serviço/API. Escritas
   directas no model podem ignorá-las; integrações futuras devem usar
   `transition_campaign_action`.
3. **Sincronização com artefactos:** ainda não existe sincronização automática
   entre o status da action e callbacks de content/report/media kit. Isso deve
   ser decidido em BE-CA-006 sem duplicar responsabilidades.
4. **Auditoria:** transições ainda não geram `AuditEvent`; ficou fora deste
   prompt e deve ser integrado apenas por decisão explícita posterior.
5. **Política terminal:** `failed` não reabre. Se o produto preferir retry da
   mesma action no futuro, a matriz e a regra anti-duplicação terão de ser
   revistas em conjunto.

## Próximo passo recomendado

Executar BE-CA-006: validar e documentar o fluxo em duas etapas para associar
artefactos existentes, mantendo CampaignAction como rastreio e sem criar ou
renderizar artefactos automaticamente.
