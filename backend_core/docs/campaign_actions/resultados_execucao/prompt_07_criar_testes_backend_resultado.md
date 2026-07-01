# Prompt 07 — Criar testes backend de CampaignAction

## Execução de 2026-07-01 06:57:48 -01:00

- **Estado da execução:** executado
- **Backlog:** BE-CA-007 — Criar testes backend
- **Suite CampaignAction:** 56 testes passados
- **Alterações runtime:** nenhuma
- **Frontend:** sem alterações

## Resumo objectivo

Foi criada uma suite API persistente para os contratos críticos ainda cobertos
apenas por validações ad hoc. A nova suite complementa os testes já existentes de
lifecycle e artefactos relacionados.

A estrutura segue o padrão do projecto:

- `pytest` + `pytest-django`;
- DRF `APIClient`;
- fixtures locais em `apps/campaign_actions/tests/conftest.py`;
- seed RBAC real;
- dados criados por ORM apenas para preparar cenários;
- assertions feitas contra a API pública real.

Não foi criada uma factory-boy adicional: os fixtures locais existentes já
forneciam user, workspace, campaign, autenticação e header, evitando duplicação.

## Cobertura criada

### CRUD e contrato HTTP

- lista paginada por workspace;
- criação válida;
- atribuição server-side de `workspace`, `created_by` e `updated_by`;
- consulta detail;
- PATCH de title, description, priority e metadata;
- detail cross-workspace devolve 404;
- PUT e DELETE devolvem 405.

### Autenticação, tenant e RBAC

- request sem autenticação devolve 401;
- request autenticado sem `X-Workspace-ID` devolve 400;
- campaign de outro workspace é rejeitada com 400;
- viewer pode listar mas não criar;
- lista nunca devolve actions de outro workspace.

### Validação

- `action_type` inválido é rejeitado;
- `status` inválido é rejeitado;
- criação dismiss sem `dismiss_reason` é rejeitada;
- duplicado activo pela chave workspace/campaign/ref/type é rejeitado;
- depois de a action original ficar `failed`, uma nova action com a mesma chave é
  aceite, conforme a regra definida.

### Filtros

Foram cobertos:

```text
campaign
recommendation_ref
status
action_type
created_by
```

As assertions comparam conjuntos de IDs, não posições. Os requests de filtro
incluem `ordering=created_at` explicitamente, evitando testes dependentes de uma
ordem implícita.

### Cobertura já existente consolidada

`test_related_artifacts.py` cobre:

- related artefact de outro workspace;
- related artefact de outra campaign;
- Report/MediaKit sem campaign;
- compatibilidade entre action type e os quatro campos `related_*`;
- coerência ContentPackRequest/ContentOutput;
- PATCH de relações.

`test_transitions.py` cobre:

- status inválido;
- matriz completa de transições;
- estados terminais;
- timestamps;
- dismiss reason;
- actions mark-reviewed/dismiss/cancel/complete;
- idempotência;
- criação semântica.

## Ficheiros criados ou alterados

### Criados

```text
apps/campaign_actions/tests/test_api.py
docs/campaign_actions/resultados_execucao/prompt_07_criar_testes_backend_resultado.md
```

Nenhum ficheiro runtime, fixture existente ou factory global foi alterado.

## Validações executadas e resultado

| Validação | Resultado |
| --- | --- |
| `pytest apps/campaign_actions/tests/test_api.py -q` | OK — 13 passed. |
| `pytest apps/campaign_actions/tests -q` | OK — 56 passed em 104.22s. |
| `python manage.py check` | OK — 0 issues. |
| `ruff check --no-cache apps/campaign_actions` | OK — All checks passed. |
| Listagem por workspace | Coberta. |
| Create/detail/PATCH | Cobertos. |
| Sem autenticação/header | 401/400 confirmados. |
| Campaign cross-workspace | Rejeitada. |
| Related artefact cross-workspace/campaign | Coberto pelos 21 testes de artefactos. |
| Choices inválidos e dismiss sem motivo | Rejeitados. |
| Filtros campaign/ref/status/type | Cobertos; `created_by` também. |
| Duplicação activa e retry após failed | Cobertos. |
| Browser | Não utilizado. |

Os 57 warnings da suite completa são ambientais e já conhecidos:

- pasta `staticfiles` ausente durante requests do test client;
- `.pytest_cache` sem permissão de escrita.

Não houve warning funcional nem falha de teste.

## Pendências e riscos

1. **Suite global:** foi executada a suite completa da app CampaignAction, não a
   suite integral do Backend Core. A regressão global deve ser executada antes do
   fecho final ou CI.
2. **Cobertura percentual:** não foi executado `coverage`; os contratos pedidos
   estão cobertos por casos explícitos, mas não foi calculada percentagem.
3. **PostgreSQL:** os testes correram no backend SQLite de teste. A constraint
   parcial deve também ser exercitada em CI/staging PostgreSQL antes de produção.
4. **Migration local:** continua pendente aplicar a migration ao `db.sqlite3` do
   workspace, que permanece sem permissão de escrita neste ambiente. As bases de
   teste aplicaram a migration com sucesso.
5. **Drift cross-domain:** os testes validam a ligação no momento de
   create/PATCH; alterações posteriores do artefacto relacionado continuam um
   risco já registado no Prompt 06.

## Próximo passo recomendado

Executar BE-CA-008: regenerar/validar OpenAPI, criar a documentação de
arquitectura backend e confirmar que todos os contratos, enums, headers,
filtros, lifecycle e limitações estão documentados sem secrets.
