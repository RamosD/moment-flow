# Prompt 06 — Integrar artefactos relacionados

## Execução de 2026-06-30 22:25:04 -01:00

- **Estado da execução:** executado
- **Backlog:** BE-CA-006 — Integrar com artefactos existentes
- **Criação automática de artefactos:** não implementada
- **Frontend/IE/Renderer:** sem alterações

## Resumo objectivo

CampaignAction passou a validar formalmente a associação aos quatro tipos de
artefacto existentes, considerando simultaneamente:

1. workspace activo;
2. campaign seleccionada;
3. compatibilidade com `action_type`;
4. coerência entre ContentPackRequest e ContentOutput quando ambos são ligados.

As relações continuam opcionais na criação. A API de CampaignAction rastreia
artefactos, mas não os cria nem substitui os endpoints proprietários.

## Campos reais confirmados

### Campaign

- `workspace`: obrigatório, via `WorkspaceOwnedModel`;
- entidade soft-deletable;
- é a referência obrigatória de CampaignAction.

### ContentPackRequest

- `workspace`: obrigatório;
- `campaign`: obrigatório, `CASCADE`;
- representa o pedido de geração de um content pack.

### ContentOutput

- `workspace`: obrigatório;
- `campaign`: obrigatório, `CASCADE`;
- `content_pack_request`: opcional e nullable;
- representa um output já criado, não o pedido em si.

### Report

- `workspace`: obrigatório;
- `campaign`: opcional e nullable, `SET_NULL`;
- pode existir como report genérico de artist/track/workspace.

Para ser ligado a CampaignAction, um Report tem de possuir campaign e esta tem de
ser exactamente a campaign da action. Um report com campaign nula é rejeitado.

### MediaKit

- `workspace`: obrigatório;
- `campaign`: opcional e nullable, `SET_NULL`;
- `artist`: obrigatório.

Para ser ligado a CampaignAction, um MediaKit tem de possuir campaign e esta tem
de ser exactamente a campaign da action. Um media kit com campaign nula é
rejeitado.

## Matriz de compatibilidade

| `action_type` | Relações permitidas |
| --- | --- |
| `content_pack` | `related_content_pack_request`, `related_content_output` |
| `report_request` | `related_report` |
| `media_kit_request` | `related_media_kit` |
| `manual_task` | nenhuma |
| `mark_reviewed` | nenhuma |
| `dismiss` | nenhuma |

Para `content_pack`, ContentPackRequest é a relação operacional preferencial e
ContentOutput é aceite como resultado downstream. É permitido ligar um ou ambos.

Quando ambos são fornecidos e o ContentOutput já aponta para um
ContentPackRequest, os dois requests têm de coincidir. Um ContentOutput sem
`content_pack_request` pode ainda ser associado, desde que workspace e campaign
coincidam.

Não foi incluído `asset_request`, `content_output` como action type autónomo, nem
qualquer tipo futuro.

## Regras de validação

Para cada `related_*`, o serializer:

- aceita `null`/ausência;
- rejeita objecto de outro workspace;
- rejeita objecto de outra campaign no mesmo workspace;
- rejeita Report/MediaKit com campaign nula;
- rejeita relação incompatível com o action type;
- aplica as mesmas regras em create e PATCH, usando os valores efectivos da
  instance quando um campo não é enviado.

As validações retornam HTTP 400 associado ao campo `related_*` concreto.

## Fluxo adoptado

O fluxo oficial é em duas etapas:

```text
1. Criar o artefacto no endpoint existente:
   /content-pack-requests/, /content-outputs/, /reports/ ou /media-kits/

2. Criar ou actualizar CampaignAction com a FK related_* correspondente.
```

CampaignAction não chama serviços de geração, não cria jobs, não regista usage
billing e não duplica lógica de content/reports.

## Ficheiros criados ou alterados

### Criado

```text
apps/campaign_actions/tests/test_related_artifacts.py
docs/campaign_actions/resultados_execucao/prompt_06_integrar_artefactos_relacionados_resultado.md
```

### Alterado

```text
apps/campaign_actions/serializers.py
```

Não houve alteração de models, migrations, viewsets ou rotas.

## Validações executadas e resultado

| Validação | Resultado |
| --- | --- |
| `python manage.py check` | OK — 0 issues. |
| `ruff check --no-cache apps/campaign_actions` | OK — All checks passed. |
| `pytest apps/campaign_actions/tests/test_related_artifacts.py -q` | OK — 21 passed. |
| Regressão `test_transitions.py` | OK — 22 passed. |
| Relações correctas para content pack/report/media kit | Aceites. |
| Criação sem `related_*` | Aceite para os três action types de artefacto. |
| Outro workspace | Rejeitado para as quatro FKs. |
| Outra campaign no mesmo workspace | Rejeitado para as quatro FKs. |
| Report/MediaKit com campaign nula | Rejeitados. |
| Relações incompatíveis com cada action type | Rejeitadas. |
| Request/output de content pack incoerentes | Rejeitados. |
| PATCH com action type existente | Compatibilidade aplicada; relação correcta aceite. |
| Browser | Não utilizado. |

Total das suites executadas neste prompt: 43 testes passados. Os warnings são os
ambientais já conhecidos relativos a `staticfiles` e `.pytest_cache` sem escrita.

## Pendências e riscos

1. **Migration local:** continua pendente aplicar
   `campaign_actions.0001_initial` ao `db.sqlite3` não gravável deste workspace.
2. **Integridade entre tabelas:** workspace/campaign cross-model não pode ser
   garantida por uma FK/constraint SQL simples; a protecção está no serializer.
   Escritas directas por ORM/admin podem contorná-la.
3. **Alteração posterior do artefacto:** Report, MediaKit e outros endpoints podem
   alterar relações depois de a CampaignAction ser ligada. Isso pode criar drift
   histórico sem tocar na action. Uma política de imutabilidade ou auditoria
   cross-domain deve ser avaliada antes de produção.
4. **Sincronização de status:** associar um artefacto não sincroniza o seu status
   com CampaignAction. A action continua a ter lifecycle próprio.
5. **Relações opcionais:** uma action pode existir antes do artefacto. O cliente
   deve fazer PATCH depois de criar o artefacto e tratar falhas parciais do fluxo
   em duas etapas.
6. **On delete:** as FKs `related_*` usam `SET_NULL`; apagar um artefacto preserva
   a CampaignAction, mas remove a navegação relacional para ele.

## Próximo passo recomendado

Executar BE-CA-007: consolidar a suite backend completa de CampaignAction,
cobrindo autenticação, header, RBAC, scoping, CRUD, filtros, choices,
anti-duplicação, lifecycle e as validações de artefactos agora implementadas.
