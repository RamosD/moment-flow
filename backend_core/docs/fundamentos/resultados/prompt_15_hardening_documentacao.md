# Relatório de execução — Prompt 15: Hardening final e documentação

- **Pipeline / Backlog:** Pipeline 12 — Testes, hardening e documentação (BCORE-1601+ / Definition of Done, secção 28)
- **Data:** 2026-06-22
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`
- **Stack:** Django 6.0.6 · DRF 3.17.1 · SimpleJWT · drf-spectacular 0.29 · Python 3.13.2

---

## 1. Prompt executado

Fazer o hardening final do Backend Core Django/DRF e criar documentação técnica
mínima para desenvolvimento e operação local, **sem implementar features novas**,
sem alterar a arquitectura acordada, sem mover responsabilidades analíticas para
o Django e sem apagar migrations. Revisão de consistência (settings, apps, URLs,
admin, permissions, serializers, tests), verificação de multi-tenancy,
autenticação/permissões, padrões dos models (UUID/timestamps/workspace), ligação
de usage/audit aos fluxos críticos e geração do schema OpenAPI. Criar `README.md`
do backend, criar `02_estado_implementacao_backend_core.md` e gravar este
relatório.

## 2. Objectivo

Deixar o backend core **consistente, testado e documentado** antes de avançar
para frontend, FastAPI Intelligence Engine ou Content Renderer, corrigindo apenas
problemas pequenos directamente relacionados com hardening.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `README.md` | README do backend core: visão, requisitos, `.env`, instalação, migrations, seed, runserver, testes, ruff, OpenAPI, endpoints e fronteira Django vs FastAPI |
| `docs/backend_core/fundamentos/02_estado_implementacao_backend_core.md` | Estado de implementação: funcionalidades, endpoints, apps, validações, pendências, riscos, próximo passo |
| `.gitignore` | Evita commit de `.env`, `db.sqlite3`, `venv/`, `schema.yml`, caches e `.coverage` (hardening de segredos/artefactos) |
| `docs/backend_core/fundamentos/resultados/prompt_15_hardening_documentacao.md` | Este relatório |
| `schema.yml` | Artefacto gerado pela validação OpenAPI (gitignored) |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `requirements.txt` | Reescrito de **UTF-16-LE (sem BOM)** para **UTF-8**, mantendo os 32 pins exactamente iguais. Em UTF-16 sem BOM, `pip install -r requirements.txt` falha a parsear o ficheiro. |

Nenhum model, migration, serializer, viewset, permission ou contrato de API foi
alterado. Nenhum teste foi removido. Nenhuma dependência foi adicionada ou
removida.

## 5. Comandos executados

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --file schema.yml
python -m pytest -q
ruff check .
```

(executados via `venv/Scripts/python` e `venv/Scripts/ruff`.)

## 6. Resultado das validações

| Validação | Resultado |
|---|---|
| `python manage.py check` | ✅ **System check identified no issues (0 silenced).** |
| `python manage.py makemigrations --check --dry-run` | ✅ **No changes detected** (exit 0) — sem migrations em falta |
| `python manage.py spectacular --file schema.yml` | ✅ Schema gerado **sem erros nem warnings** (exit 0) |
| `pytest` | ✅ **235 passed**, 160 warnings, em ~377s (exit 0) — confirmado em duas execuções |
| `ruff check .` | ✅ **All checks passed!** (exit 0) |

**Sobre os 160 warnings do pytest:** são todos a mesma `UserWarning` benigna do
WhiteNoise — *"No directory at: ...\staticfiles\"* — porque `collectstatic` não
foi corrido em dev. Sem impacto funcional; resolve-se com
`python manage.py collectstatic` ou ignora-se em desenvolvimento.

## 7. Inconsistências encontradas

1. **`requirements.txt` em UTF-16-LE sem BOM** — quebraria `pip install -r
   requirements.txt`; inconsistente com os restantes ficheiros (UTF-8). *(corrigido)*
2. **Ausência de `.gitignore`** — risco de commit acidental de `.env`,
   `db.sqlite3`, `venv/` e artefactos quando o projecto for inicializado em git.
   *(corrigido com `.gitignore` mínimo)*
3. **Warning do WhiteNoise nos testes** (`staticfiles/` inexistente) — benigno;
   documentado, não corrigido (não justifica alterar settings).

Não foram encontradas inconsistências de arquitectura, de multi-tenancy, de
permissões nem de ligação de usage/audit. Os padrões estão homogéneos entre apps.

## 8. Verificações de consistência (sem alteração necessária)

- **Models:** todos os principais usam UUID PK + timestamps (`BaseModel`);
  entidades tenant-aware herdam `WorkspaceOwnedModel`. `Plan`/`PlanFeature`/
  `BillingWebhookEvent` globais; `Role`/`Template`/`ContentPack` com `workspace`
  nullable (global ou por workspace) — intencional e coerente com o backlog.
- **Multi-tenancy:** querysets filtram por `workspace` via mixins partilhados
  (`WorkspaceScopedRBACViewSet`, `GlobalOrWorkspaceReadViewSet`); workspace
  resolvido por `X-Workspace-ID` exigindo membership activa.
- **Auth/permissões:** `IsAuthenticated` + `HasWorkspacePermission` (RBAC por
  acção) por defeito; endpoint público só em `/l/<slug>/`; callback interno
  protegido por `X-Internal-Token` (comparação em tempo constante, `hmac`).
- **Usage & audit:** os 11 audit actions do BCORE-1201 estão ligados aos fluxos
  reais (workspace/member/artist/track/campaign/smart_link/content_pack/credits/
  plan); usage events idempotentes em criação de entidades.
- **Idempotência:** usage events, credit ledger, webhook Stripe e callback interno
  são idempotentes.
- **Admin:** entidades principais registadas; `AuditEvent` estritamente read-only.
- **OpenAPI:** schema gera limpo; enums problemáticos resolvidos por
  `ENUM_NAME_OVERRIDES`.

## 9. Correcções feitas

- Reescrita de `requirements.txt` para UTF-8 (conteúdo idêntico, 32 pacotes).
- Adição de `.gitignore` mínimo (segredos + artefactos).
- Limpeza do ficheiro temporário `pytest_result.txt` usado durante a validação.

Correcções deliberadamente **não** feitas (fora do âmbito / risco): warning do
WhiteNoise, implementação de features P1, alterações a models/migrations.

## 10. Pendências

(P1/futuras — ver detalhe em `02_estado_implementacao_backend_core.md`)

- Password reset / verificação de email (BCORE-103).
- `WorkspaceSettings` / `WorkspaceBranding` (BCORE-204).
- `Label` / `LabelArtist` (BCORE-504).
- `CampaignChannel` / `CampaignTimelineItem` (BCORE-604).
- `NotificationPreference` (BCORE-1102).
- Bridge real de geração de conteúdo para o Content Renderer (BCORE-705).
- Stripe checkout real e mapeamento customer→workspace.
- `collectstatic` para remover o warning do WhiteNoise em ambientes que sirvam estáticos.

## 11. Riscos

- **Webhook Stripe sem `STRIPE_WEBHOOK_SECRET`:** eventos aceites mas não
  verificados (`signature_verified: false`). Definir o secret antes de produção.
- **`INTERNAL_API_TOKEN` vazio:** todos os callbacks internos são rejeitados
  (default seguro); definir antes de ligar FastAPI/renderer/workers.
- **`SECRET_KEY` default inseguro:** apenas para dev; obrigatório definir em
  produção.
- **Fronteira analítica:** manter a disciplina de não implementar
  métricas/moments/insights/rendering no Django (mitigado pela
  `integrations_bridge`).

## 12. Próximo passo recomendado

1. Definir os segredos de ambiente (`SECRET_KEY`, `INTERNAL_API_TOKEN`,
   `STRIPE_WEBHOOK_SECRET`) num `.env` real.
2. Avançar para o **FastAPI Intelligence Engine / Content Renderer**, consumindo
   os contratos da `integrations_bridge`.
3. Iniciar o **frontend (Next.js)** contra `/api/v1/` usando o schema OpenAPI.
4. Endereçar pendências P1 conforme prioridade de produto.

---

## Critérios de aceitação — verificação

- ✅ `README.md` do backend_core existe e é útil.
- ✅ `02_estado_implementacao_backend_core.md` existe.
- ✅ Checks principais executados (check, makemigrations --check, spectacular,
  pytest, ruff) — todos verdes; limitações (warning WhiteNoise) explicadas.
- ✅ Inconsistências pequenas corrigidas (encoding de `requirements.txt`,
  `.gitignore`).
- ✅ Pendências documentadas.
- ✅ Relatório criado em
  `docs/backend_core/fundamentos/resultados/prompt_15_hardening_documentacao.md`.
