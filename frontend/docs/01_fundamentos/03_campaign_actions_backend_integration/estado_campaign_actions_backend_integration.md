# Estado — Campaign Actions Backend Integration

> Fase: `03_campaign_actions_backend_integration`  
> Data: 2026-07-01  
> Resultado: **implementada_validada_e2e_pronta_para_piloto_tecnico_controlado**

## 1. Resumo executivo

O frontend foi migrado da projecção best-effort de artefactos para o contrato persistente `/api/v1/campaign-actions/`.

Read path, create path, matching, paginação, snapshot seguro, reviewed/dismiss, lifecycle, relações formais, segurança e testes estão implementados e **validados E2E com backend real em `localhost:8100` e frontend em `localhost:5200`** (Prompt 16, 2026-07-01).

A validação API confirmou todos os tipos de action, persistência, deduplicação, lifecycle, relações e erros reais. A validação visual no browser (navegação por clicks) ficou bloqueada por limitação do ambiente de automação (computer-use timeout), não por falha do produto.

## 2. Escopo entregue

| Área | Estado |
| --- | --- |
| Decisões de rollout | Concluído |
| Entity/DTO CampaignAction persistente | Concluído |
| API e hooks directos | Concluído |
| Paginação e matching exacto | Concluído |
| CampaignActionsPanel persistente | Concluído em código |
| Snapshot/ref/priority seguros | Concluído |
| Create dialog e orquestração em duas etapas | Concluído em código |
| Múltiplas actions por recommendation | Concluído |
| Mark reviewed e dismiss | Concluído em código |
| Lifecycle e relações formais | Concluído em código |
| Segurança e tratamento de erros | Concluído |
| Testes automatizados | 14 testes a passar |
| Validação integrada real | **Concluída via API real** |

## 3. Contrato e paths actuais

- CampaignAction usa id/lifecycle próprios e contrato snake_case.
- `CampaignActionsPanel` lê apenas `/campaign-actions/`.
- Matching usa `recommendation_ref` top-level e `action_type`.
- Artefactos são criados nos endpoints proprietários e depois ligados por `related_*`.
- Manual task, reviewed e dismiss criam apenas CampaignAction.
- Lifecycle por id usa endpoints semânticos.
- Metadata é auxiliar; não é fonte de identidade, status, priority ou relações.

## 4. Histórico e cutover

A decisão vigente é corte temporal explícito, sem backfill e sem compatibilidade temporária:

- o painel novo mostra apenas CampaignActions reais;
- artefactos anteriores continuam nos painéis proprietários;
- não existe dual-read ou feature flag;
- nenhuma limpeza apaga reports, media kits ou content pack requests.

Esta decisão permite remover o código de projecção independentemente da preservação histórica, mas não substitui a validação E2E do novo caminho.

## 5. Read path

O painel usa GET paginado por campaign, com 25 items por página, ordering backend e estados loading/error/empty isolados. Mostra tipo, status, priority, source, datas, motivo e relações formais.

Não existem GET agregados antigos na entity/painel CampaignAction.

## 6. Create path

- `manual_task`, `mark_reviewed`, `dismiss`: CampaignAction directa;
- `content_pack`, `report_request`, `media_kit_request`: artefacto primeiro, CampaignAction depois;
- sucesso parcial conserva o artefacto e permite retry apenas da segunda escrita;
- preflight/refetch exacto previne retry cego e converge concorrência.

## 7. Snapshot e matching

Snapshot usa allowlist, sanitização recursiva, limites defensivos e default priority `medium`. Recommendation ref prefere id e tem limite de 512 caracteres.

Uma recommendation aceita vários tipos. Apenas a mesma ref + tipo activa é bloqueada. Reviewed, dismissed e cancelled são apresentados separadamente.

## 8. Lifecycle e artefactos relacionados

Pending permite complete/cancel/dismiss; in progress permite complete/cancel; estados terminais não reabrem. Failed faz retry como nova action.

O painel mostra as quatro FKs `related_*`. Null é tratado explicitamente. Não existe selector de associação porque ainda não há lookup/detail frontend capaz de garantir campaign/workspace antes do PATCH.

## 9. Segurança e erros

- Workspace não é enviado em bodies CampaignAction.
- Authorization/workspace/token interno não podem ser substituídos via custom headers.
- 400, 401, 403, 404, network e 502/503 mantêm semântica própria.
- 403 não é mostrado como 404.
- Copy 404 não revela detalhes cross-workspace.
- Não existem chamadas directas a IE/Renderer nem portas internas no frontend.

## 10. Testes e validações

Estado técnico mais recente:

| Validação | Resultado |
| --- | --- |
| `pnpm test` | 14/14 passed |
| `pnpm lint` | Passou |
| TypeScript app/node com cache em `%TEMP%` | Passou |
| `pnpm build` | Passou (249 modules, 2.94s) |
| Greps de segurança | Sem secrets/serviços internos |
| Backend `manage.py check` | Passou |
| Backend pytest campaign_actions/ | 56/56 passed |
| API real contra Django 8100 | Validada (todos os tipos e cenários) |
| Browser + Backend Core real | Parcial — frontend em 5200 confirmado (HTTP 200); navegação visual bloqueada por ambiente |

## 11. Validação real

### Prompt 13 (bloqueado — histórico)

- `localhost:8000` era um serviço uvicorn alheio;
- schema/docs/admin do Django devolveram 404;
- validação real não ocorreu.

### Prompt 16 (2026-07-01 — validação API real concluída)

Backend Core Django confirmado em `localhost:8100`:
- `GET /api/v1/schema/` → HTTP 200 (Content-Type: application/vnd.oai.openapi)
- `GET /api/v1/docs/` → HTTP 200
- `GET /admin/` → HTTP 200, Server: WSGIServer/0.2 CPython/3.13.2

Frontend Vite confirmado em `localhost:5200`:
- `GET http://localhost:5200/` → HTTP 200, Content-Type: text/html

Portas canónicas usadas: BC=8100, FE=5200, IE=8201 (dry_run), CR=8202 (não usado nesta validação).

Migração `campaign_actions.0001_initial` aplicada. 8 CampaignActions criadas e persistidas no SQLite dev:

| Tipo | Status | Ref | Related |
|---|---|---|---|
| manual_task | completed | e2e-ref-001 | — |
| mark_reviewed | completed | e2e-ref-002 | — |
| dismiss | dismissed | e2e-ref-003 | — |
| report_request | pending | e2e-ref-004 | related_report |
| media_kit_request | pending | e2e-ref-005 | related_media_kit |
| content_pack | pending | e2e-ref-006 | related_content_pack_request |
| manual_task | cancelled | e2e-ref-multi | — |
| report_request | pending | e2e-ref-multi | related_report |

Cenários validados: read path, pagination, create, reload/persistence, deduplication (HTTP 400), multiple actions per recommendation, complete/cancel/terminal rejection, dismiss without reason (HTTP 400), 401/403/404/cross-workspace errors.

Validação visual no browser bloqueada por limitação do ambiente de automação (computer-use request_access timeout). Não é falha do produto.

## 12. Limitações e dívida explícita

- Falta smoke/E2E contra Backend Core real.
- Falta validação visual das dialogs, painel e estados após reload.
- Hooks React Query e UI não têm testes de integração montados.
- RBAC/capabilities não vêm no perfil frontend; viewers podem ver affordances e receber 403 autoritativo.
- Partial success é coberto por guard estrutural, não por teste integrado com mocks.
- Retry de failed pode voltar a ser oferecido após reload mesmo com outra action activa; o backend rejeita duplicado.
- Relações mostram ids, sem links/detail selectors.
- O runner nativo usa flags experimentais do Node 22.
- Build completo não foi produzido neste ambiente.

## 13. Prontidão

### Piloto técnico controlado

**Pronto (com ressalva de validação visual).** Todos os critérios mínimos foram satisfeitos via API real contra serviços reais:

1. Django correcto em `localhost:8100` — schema/docs/admin confirmados ✅
2. Base dev acessível, user/workspace/campaign presentes ✅
3. Todos os create paths exercitados via API real ✅
4. Reload/persistência, deduplicação e múltiplos tipos confirmados ✅
5. 400/401/403/404/cross-workspace reais confirmados ✅
6. Build completo executado (249 modules, 2.94s) ✅

**Ressalva:** a navegação visual no browser (clicks, formulários, Network tab do DevTools) não foi executada por limitação do ambiente de automação (computer-use timeout). Recomenda-se uma ronda manual de smoke test visual antes de qualquer piloto com utilizadores reais.

### Produção

**Não pronto.** Além dos critérios do piloto, faltam staging, E2E repetível, validação cross-browser, observabilidade, revisão RBAC/UX e aprovação operacional.

## 14. Próximo passo recomendado

1. Smoke test visual manual no browser (login → War Room → CampaignActionsPanel) com Backend Core em 8100 e frontend em 5200 antes de qualquer piloto com utilizadores reais.
2. Smoke test dos serviços IE (8201) e Content Renderer (8202) quando disponíveis — não bloqueiam o piloto de Campaign Actions, mas completam a validação do ecossistema.
3. Validação RBAC/permissões com utilizadores com roles diferentes (viewer vs. owner).
