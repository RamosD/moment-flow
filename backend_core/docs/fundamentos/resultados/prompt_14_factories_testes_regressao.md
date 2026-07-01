# Relatório de execução — Prompt 14: Factories e Testes de Regressão

- **Pipeline / Backlog:** Pipeline 12 — Testes e qualidade (BCORE-1601 Factories, 1602 Multi-tenancy, 1603 RBAC, 1604 Billing)
- **Data:** 2026-06-21
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`

---

## 1. Prompt executado

Criar factories com `factory-boy` para as entidades principais e reforçar testes
críticos de **multi-tenancy**, **RBAC**, **billing**, **content pack requests** e
**smart links**, reduzindo o risco de regressão antes de avançar para integração
com FastAPI/renderer ou frontend. Corrigir bugs directamente ligados aos testes
criados, sem implementar features novas nem relaxar permissões.

## 2. Objectivo

Estabelecer uma rede de segurança de regressão transversal (não por app), com
factories reutilizáveis que constroem grafos de dados tenant-consistentes, e
asserções de isolamento, permissões e billing através da API real.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `tests/__init__.py` | Pacote de testes transversais na raiz |
| `tests/factories.py` | 24 factories `factory-boy` (todas as entidades pedidas) |
| `tests/conftest.py` | Fixtures partilhadas (`seeded`, `auth_client`, `add_member`, `ws_header`) |
| `tests/test_smoke_factories.py` | Smoke test: todas as factories constroem objectos válidos e tenant-consistentes |
| `tests/test_multitenancy.py` | Isolamento A↔B em artists, tracks, campaigns, smart links e billing |
| `tests/test_rbac.py` | Fronteiras de permissões para viewer/editor/admin/owner/billing_admin |
| `tests/test_billing.py` | Usage idempotente, ciclo de créditos, bloqueios e quota de campanhas |
| `tests/test_smart_links.py` | Criação, destinos, clique registado e link pausado |
| `tests/test_content_pack_requests.py` | Criação válida, bloqueio sem permissão, workspace inválido |
| `docs/.../resultados/prompt_14_factories_testes_regressao.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `pytest.ini` | `testpaths = apps tests` (descobre a nova suite transversal sem mexer nas existentes) |
| `pyproject.toml` | `[tool.coverage.run]` / `[tool.coverage.report]` (source=apps, branch, omit migrations/tests) |

Nenhum model, serializer, viewset ou contrato de API foi alterado (restrição
respeitada). Nenhum teste existente foi removido.

## 5. Factories criadas

`User`, `Workspace`, `Permission`, `Role`, `WorkspaceMember`, `Asset`, `Artist`,
`Track`, `TrackPlatformLink`, `Campaign`, `CampaignGoal`, `Template`,
`TemplateVersion`, `ContentPack`, `ContentPackRequest`, `ContentOutput`,
`SmartLink`, `SmartLinkDestination`, `Plan`, `Subscription`, `UsageEvent`,
`CreditLedgerEntry`, `Report`, `MediaKit` — **24 factories** (todas as do prompt).

Padrões: entidades-filhas derivam `workspace` do pai via `SelfAttribute`
(consistência tenant garantida); slugs/keys via `Sequence` (unicidade);
`UserFactory` usa o manager `create_user` (password com hash).

## 6. Comandos executados

```powershell
python -m pytest tests/ -q                      # 37 passed (suite nova)
python -m coverage run -m pytest                # 235 passed (suite completa)
python -m coverage report                       # TOTAL 91%
ruff check .                                    # All checks passed!
python manage.py check                          # 0 issues
```

## 7. Resultado das validações

| Validação | Resultado |
|---|---|
| `pytest` (completo) | **235 passed** (198 anteriores + **37 novos**) — 0 regressões |
| `coverage run -m pytest` + `coverage report` | OK — **91%** de cobertura total (branch) |
| `ruff check .` | OK — `All checks passed!` |
| `manage.py check` | OK — `System check identified no issues (0 silenced)` |

Cobertura por domínio testado (destaques): `billing/models` 99%, `billing/views`
90%, `campaigns/models` 100% / `views` 98%, `catalogue/models` 100% / `views` 91%,
`links/models` 100%, `reports/models` 100%, `workspaces/services` 100%.
`billing/services` 74% (caminhos menos comuns — purchase/expiration/period usage —
ficam para testes futuros). **Nota benigna:** persiste o `UserWarning` do
WhiteNoise sobre `staticfiles/`.

## 8. Cobertura dos critérios de teste

- **Multi-tenancy:** utilizador de B não lista, não lê por id (404) nem altera
  (404) dados de A (artists, tracks, campaigns, smart links); não-membro com
  header de workspace alheio é bloqueado (403); saldo de créditos é por workspace.
- **RBAC:** criar artista → viewer 403 / editor 201 / admin 201 / owner 201 /
  billing_admin 403; ver billing → viewer 403 / editor 403 / admin 200 / owner 200
  / billing_admin 200 (alinhado com os papéis seed, sem relaxar permissões).
- **Billing:** usage idempotente (mesma `idempotency_key` não duplica); grant →
  reserve → release → consume → refund com saldo correcto; settle de reserva sem
  dupla cobrança; consumo idempotente; bloqueio por falta de créditos
  (`InsufficientCredits`); quota de campanhas no plano trial (2.ª criação → 402).
- **Smart links:** criação via API (slug gerado), adição de destino, clique
  registado no endpoint público (302 + `SmartLinkClick`), link pausado não resolve
  (404, sem clique).
- **Content pack requests:** criação válida (queued), bloqueio sem permissão
  (viewer → 403), bloqueio por campanha de outro workspace (400).

## 9. Bugs encontrados

**Nenhum.** Todos os 37 testes novos passaram na primeira execução contra a
implementação existente. A suite confirma que o comportamento de multi-tenancy,
RBAC, billing, smart links e content pack requests das fases anteriores está
correcto. Não foi necessária nenhuma correcção de código de produção.

## 10. Correcções feitas

Apenas infra-estrutura de testes/qualidade (sem alterar regras de negócio):

- `pytest.ini` passou a incluir `tests` em `testpaths` (descoberta da suite nova).
- `pyproject.toml` ganhou configuração de `coverage` (antes existia o pacote mas
  não havia config, pelo que `coverage report` não tinha `source`/omits) — agora
  o passo de validação de cobertura é executável e significativo.

## 11. Pendências

- **`billing/services` a 74%:** falta cobrir `purchase_credits`, `expiration`,
  `change_subscription_plan`, `get_period_usage` e ramos de idempotência por
  corrida; candidatos a testes adicionais.
- **`integrations_bridge`/`audit` transversais:** cobertos pelos testes por-app;
  poderiam ganhar asserções no pacote `tests/` (ex.: audit emitido em
  `workspace.created`/`credits.*`).
- **`pytest-factoryboy`:** as factories são importadas directamente; registá-las
  como fixtures é opcional e fica para depois.
- **CI:** falta um passo que corra `check` + `pytest` + `coverage` + `ruff` e
  publique o relatório de cobertura.
- **`collectstatic`** continua por correr (warning benigno do WhiteNoise).

## 12. Próximo passo recomendado

Com a rede de regressão estabelecida (235 testes, 91%), avançar para a
**integração FastAPI/renderer** fechando o ciclo billing → `integrations_bridge`
→ reports/notifications: os fluxos de geração (content pack / report / media kit)
criam um `ExternalJobReference` via `create_external_job_reference`, e o callback
interno autenticado actualiza a entidade de produto e emite `create_notification`.
Em paralelo, adicionar um passo de CI que corra a suite completa com cobertura e
falhe abaixo de um limiar (ex.: 85%).
