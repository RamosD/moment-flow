# Relatório de execução — Prompt 12: Audit e Integrations Bridge

- **Pipeline / Backlog:** Pipeline 11 — Audit, Admin e Integrations bridge (BCORE-1201, 1301, 1302)
- **Data:** 2026-06-21
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`

---

## 1. Prompt executado

Implementar auditoria funcional e uma ponte de integração para jobs externos
futuros. Criar `apps.audit` com `AuditEvent` (actor types user/system/admin/
api_key/worker) e `record_audit_event`, integrado em acções críticas; registar
`AuditEvent` no Admin como **read-only**. Criar `apps.integrations_bridge` com
`ExternalJobReference` (job types e estados), `create_external_job_reference` e um
**endpoint interno de callback** autenticado por `X-Internal-Token` /
`INTERNAL_API_TOKEN`. Testes de service de audit, admin read-only, criação de job
reference e callback com/sem token.

## 2. Objectivo

O Django mantém **rastreabilidade de acções críticas** e **acompanha pedidos
técnicos externos** sem executar lógica pesada. FastAPI/Renderer/workers ficarão
responsáveis por métricas, moments, insights e renderização real; aqui só se
guardam referências de estado e se recebem callbacks autenticados.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/audit/__init__.py`, `apps/audit/apps.py` | App `apps.audit` |
| `apps/audit/models.py` | `AuditEvent` (append-only, UUID, sem `updated_at`) |
| `apps/audit/utils.py` | Hashing salted (SHA-256) de IP/user-agent |
| `apps/audit/services.py` | `record_audit_event` (deriva hashes do request; actor_type por defeito) |
| `apps/audit/admin.py` | Admin **read-only** (sem add/change/delete) |
| `apps/audit/migrations/0001_initial.py` | Migration inicial |
| `apps/audit/tests/conftest.py` | Fixtures (rbac, workspace) |
| `apps/audit/tests/test_audit.py` | Service, privacidade, admin read-only, integração |
| `apps/integrations_bridge/__init__.py`, `.../apps.py` | App `apps.integrations_bridge` |
| `apps/integrations_bridge/models.py` | `ExternalJobReference` |
| `apps/integrations_bridge/services.py` | `create_external_job_reference`, `apply_job_callback` |
| `apps/integrations_bridge/permissions.py` | `IsInternalService` (X-Internal-Token, comparação constante) |
| `apps/integrations_bridge/serializers.py` | Serializers + `JobCallbackSerializer` |
| `apps/integrations_bridge/views.py` | `ExternalJobCallbackView` (callback interno) |
| `apps/integrations_bridge/urls.py` | Rota `/internal/jobs/callback/` |
| `apps/integrations_bridge/admin.py` | Admin (timestamps read-only) |
| `apps/integrations_bridge/migrations/0001_initial.py` | Migration inicial |
| `apps/integrations_bridge/tests/conftest.py` | Fixtures (rbac, workspace, api_client) |
| `apps/integrations_bridge/tests/test_integrations_bridge.py` | Criação + callback com/sem token, terminal, 404/400 |
| `docs/.../resultados/prompt_12_audit_integrations_bridge.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `config/settings.py` | `apps.audit` e `apps.integrations_bridge` em `INSTALLED_APPS`; `INTERNAL_API_TOKEN` (via ambiente) |
| `config/urls.py` | Rota do callback interno montada em `api/v1/` |
| `.env.example` | Variável `INTERNAL_API_TOKEN` (vazia) |
| `apps/workspaces/services.py` | Audit `workspace.created` em `create_workspace` |
| `apps/workspaces/views.py` | Audit `member.added` (perform_create) e `member.role_changed` (perform_update) |
| `apps/catalogue/views.py` | Audit `artist.created` e `track.created` |
| `apps/campaigns/views.py` | Audit `campaign.created` |
| `apps/links/views.py` | Audit `smart_link.created` |
| `apps/content/services.py` | Audit `content_pack.requested` |
| `apps/billing/services.py` | Audit `credits.granted` / `credits.consumed` (só quando `created`); serviço `change_subscription_plan` → `billing.plan_changed` |

## 5. Migrations criadas

```text
apps/audit/migrations/0001_initial.py
    + AuditEvent (UUID PK; FKs nullable workspace/actor_user com SET_NULL;
      actor_type; action; entity_type/entity_id; before_data/after_data JSON;
      ip_address_hash/user_agent_hash; created_at indexado;
      índices workspace+action / entity_type+entity_id / actor_user)

apps/integrations_bridge/migrations/0001_initial.py
    + ExternalJobReference (FK nullable workspace; job_type/provider/status;
      external_job_id; related_entity_type/id; requested_by; requested_at/
      completed_at/failed_at; unique provider+external_job_id;
      índices workspace+status / job_type+status / related_entity_type+id)
```

`makemigrations --check --dry-run` confirma **No changes detected**; nenhuma
migration anterior foi alterada.

## 6. Comandos executados

```powershell
python manage.py makemigrations audit integrations_bridge   # 0001_initial em cada app
python manage.py migrate                                    # aplica audit.0001 e integrations_bridge.0001
python manage.py check                                      # 0 issues
python manage.py makemigrations --check --dry-run            # No changes detected
python -m pytest -q                                         # 198 passed
ruff check .                                                # All checks passed!
python manage.py spectacular --file schema.yml              # 0 errors
```

## 7. Resultado das validações

| Validação | Resultado |
|---|---|
| `makemigrations` / `migrate` | OK — `audit.0001_initial` e `integrations_bridge.0001_initial` aplicadas |
| `manage.py check` | OK — `System check identified no issues (0 silenced)` |
| `makemigrations --check` | OK — `No changes detected` |
| `pytest` | **198 passed** (181 anteriores + **17 novos**) — 0 regressões |
| `ruff check .` | OK — `All checks passed!` |
| OpenAPI (`spectacular`) | OK — **0 erros** (3 warnings benignos: hint do `PublicSmartLinkSerializer` e colisões de enum `status`) |

**Nota benigna:** persiste o `UserWarning` do WhiteNoise sobre `staticfiles/`.

## 8. Decisões tomadas

- **AuditEvent imutável:** assenta em `UUIDModel` + `created_at` (sem `updated_at`)
  para sinalizar imutabilidade; Admin nega `add`/`change`/`delete` e todos os
  campos são `readonly` — o trilho é fiável.
- **Privacidade (sem IP em claro):** `ip_address_hash`/`user_agent_hash` são
  SHA-256 *salted* com `SECRET_KEY`; quando não há request, ficam vazios. Teste
  confirma que o hash difere do IP em claro e tem 64 chars.
- **`record_audit_event` flexível:** aceita `request` (deriva hashes) ou hashes
  explícitos; `actor_type` por defeito é `user` se houver `actor_user`, senão
  `system`. Hooks de view passam `request`; hooks de service passam só
  `actor_user`.
- **Integração "simples e sem excesso":** audit nos pontos pedidos —
  `workspace.created`, `member.added`, `member.role_changed`, `artist.created`,
  `track.created`, `campaign.created`, `content_pack.requested`,
  `smart_link.created`, `credits.granted`, `credits.consumed` e
  `billing.plan_changed`. Os créditos só auditam quando a entrada do ledger é
  **nova** (`created=True`), evitando duplicar audit em *replays* idempotentes.
- **`billing.plan_changed` "quando aplicável":** não existe endpoint de mudança
  de plano, por isso criou-se o serviço sancionado `change_subscription_plan`
  (actualiza o plano da subscrição activa e regista o audit; *no-op* não audita).
- **Import de audit protegido nos services de billing/content:** `try/except
  ImportError` — billing/content não falham se a app audit for removida; nas
  views (catalogue/campaigns/links/workspaces) o import é direto (audit é uma
  dependência estável e sem ciclos: audit não importa essas apps).
- **Bridge — só estado, nunca execução:** `ExternalJobReference` guarda
  referência/estado; `create_external_job_reference` cria em `queued`;
  `apply_job_callback` faz a transição e preenche `completed_at`/`failed_at`.
  Nenhum serviço externo é chamado.
- **Callback interno seguro e idempotente:** `IsInternalService` compara
  `X-Internal-Token` com `INTERNAL_API_TOKEN` em tempo constante (`hmac.compare_digest`);
  **token vazio rejeita tudo** (default seguro). Callback repetido para o mesmo
  estado é *no-op* (200); transição a partir de estado terminal devolve **409**;
  job inexistente **404**; sem identificador **400**.
- **Sem segredos no código:** `INTERNAL_API_TOKEN` vem do ambiente; `.env.example`
  documenta-o vazio.

## 9. Pendências

- **Cobertura de audit mais ampla:** ficaram de fora (propositadamente, "sem
  excesso") acções como `report.requested`, `media_kit.created`,
  `smart_link.clicked`, `content_output.created` e *soft deletes* — fáceis de
  ligar ao mesmo `record_audit_event` quando necessário.
- **`actor_type` `admin`/`api_key`:** o valor existe no enum mas ainda não há
  caminho que o produza (sem acções de Admin auditadas nem API keys); fica para
  quando esses fluxos existirem.
- **Sem endpoint de criação de `ExternalJobReference` via API:** as referências
  criam-se por serviço (`create_external_job_reference`), a ser chamado pelos
  fluxos de geração (report/media kit/content) num passo futuro; o callback já
  existe para fechar o ciclo.
- **FastAPI / Celery / serviços externos:** fora do escopo (restrições) — nada é
  executado nem chamado; só contrato de estado.
- **Ligação geração → job → notificação:** o renderer/worker, ao concluir via
  callback, deverá actualizar a entidade de produto (report/media kit) e emitir
  `create_notification` — ainda por ligar.
- **`collectstatic`** continua por correr (warning benigno do WhiteNoise).

## 10. Próximo passo recomendado

Avançar para **Pipeline 12 — Testes, hardening e documentação** (BCORE-1601+):
factories `factory-boy`, testes transversais de multi-tenancy e RBAC por role,
cobertura (`coverage`) e geração do `schema.yml` versionado. Em paralelo, fechar o
ciclo de orquestração: os fluxos de geração (`content_pack.requested`,
`report`/`media_kit`) passam a criar um `ExternalJobReference` via
`create_external_job_reference`, e o callback interno actualiza a entidade de
produto + emite `create_notification` (`report_ready`/`media_kit_ready`),
ligando billing → bridge → reports/notifications de ponta a ponta.
