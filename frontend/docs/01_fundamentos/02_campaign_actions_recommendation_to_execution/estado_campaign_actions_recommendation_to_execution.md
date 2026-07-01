# Estado: Campaign Actions / Recommendation-to-Execution

> Fase: `02_campaign_actions_recommendation_to_execution`
> Data: 2026-06-30 (actualizado 2026-06-30 — CA-014 Iteração 02)
> Resultado da fase: **B — suporte parcial do Backend Core**

---

## 1. Resumo executivo

A fase **02_campaign_actions_recommendation_to_execution** transforma a Campaign War
Room de uma superfície analítica para uma superfície de execução operacional controlada.

O Backend Core **não tem** uma entidade `CampaignAction` nem endpoints de tasks.
O fluxo Recommendation-to-Execution foi implementado sobre os **3 endpoints reais de
execução existentes** no Backend Core (`/content-pack-requests/`, `/reports/`,
`/media-kits/`), projectados no frontend como `CampaignAction` — sem persistência
falsa, sem mocks runtime.

**A feature está implementada, passa em todas as validações estáticas, e os contratos
de API reais foram validados contra o Backend Core.** A criação dos 3 tipos de acção
(report, media kit, content pack request) foi confirmada com HTTP 201 real. O Campaign
Actions Panel foi confirmado com os 3 endpoints de listagem. O `recommendation_ref` em
metadata persiste e é recuperável.

**Limitação remanescente:** a validação UI visual (browser — render de recommendations,
botões de acção) não foi possível porque o Chrome extension não estava conectado e o
Intelligence Engine corre em modo dry-run (sem recommendations reais). O fluxo de
botão de acção por-recommendation não foi exercitado visualmente.

**Não é declarada como Recommendation-to-Execution validado a 100%.** É declarada
como implementação completa + contratos de API validados com backend real + UI visual
pendente de ambiente com IE real ou recommendations fixture.

---

## 2. Escopo entregue

### 2.1 Entregue

| Item | Estado |
|---|---|
| CA-001 — Investigar contratos reais do Backend Core | ✅ Concluído |
| CA-002 — Modelo frontend de Campaign Action | ✅ Concluído |
| CA-003 — API/hooks de Campaign Actions | ✅ Concluído |
| CA-004 — UI base (Dialog, Select, Textarea, FormField, Input, etc.) | ✅ Concluído |
| CA-005 — Draft de acção a partir de recommendation | ✅ Concluído |
| CA-006 — Affordance no RecommendationItem | ✅ Concluído |
| CA-007 — Modal "Create Action" | ✅ Concluído |
| CA-008 — Painel Campaign Actions na War Room | ✅ Concluído |
| CA-009 — Associação recommendation → estado da acção | ✅ Concluído (best-effort) |
| CA-010 — Mark Reviewed / Dismiss | ✅ Investigado → sem suporte backend → omitido |
| CA-012 — Tratamento de permissões e erros | ✅ Concluído (auditoria + correcção) |
| CA-013 — Documentar arquitectura da feature | ✅ Concluído |
| CA-014 — Validar integração real | ✅ Concluído (contratos API) / ⚠️ UI visual pendente |
| CA-015 — Estado final da fase | ✅ Este documento |

### 2.2 Não entregue

| Item | Estado | Razão |
|---|---|---|
| CA-011 — Integrar acções com outputs existentes | ⏳ Pendente | Só possível via metadata hoje; sem FK relacional no backend |
| CA-014 — Validar integração real | ⏳ Pendente | Ambiente indisponível (ver §8) |

---

## 3. Contratos reais usados

### 3.1 Endpoints de criação

| Tipo de acção frontend | Endpoint Backend Core | Método | Campos obrigatórios |
|---|---|---|---|
| `content_pack` | `POST /content-pack-requests/` | POST | `campaign` (UUID), `content_pack` (UUID) |
| `report_request` | `POST /reports/` | POST + PATCH | `campaign` (UUID), `title`, `report_type` |
| `media_kit_request` | `POST /media-kits/` | POST + PATCH | `artist` (UUID), `title` |

### 3.2 Endpoint de catálogo (read-only)

| Propósito | Endpoint | Método |
|---|---|---|
| Catálogo de content packs (type selector) | `GET /content-packs/?status=active` | GET |

### 3.3 Endpoints de listagem (painel)

| Recurso | Endpoint | Parâmetro de filtro |
|---|---|---|
| Content pack requests | `GET /content-pack-requests/?campaign=<id>` | `campaign` |
| Reports | `GET /reports/?campaign=<id>` | `campaign` |
| Media kits | `GET /media-kits/?campaign=<id>` | `campaign` |

---

## 4. Funcionalidades implementadas

### 4.1 Com Backend Core real

- **Criar content pack request** a partir de recommendation — POST real para
  `/content-pack-requests/` com `campaign` + `content_pack` seleccionado do catálogo.
- **Criar report** a partir de recommendation — POST real para `/reports/` com
  `campaign` + `title` + `report_type` (default `campaign_report`).
- **Criar media kit** a partir de recommendation — POST real para `/media-kits/` com
  `artist` (derivado de `campaign.artist`) + `title`.
- **Painel Campaign Actions** — agrega os 3 artefactos reais por campanha num único
  painel na War Room. Mostra título, tipo, status (normalizado), source, priority
  (via metadata), data de criação.
- **Estado da acção por recommendation** — se já existe um artefacto cujo
  `metadata.recommendation_ref` coincide com o ref derivado da recommendation,
  o botão "Create action" é substituído por badges de tipo + status (sem duplicação
  óbvia).
- **Resiliência partial-fail** — `Promise.allSettled`: uma falha (ex.: 403 em reports)
  não apaga o painel; só vai a ErrorState se **todos** falharem.
- **Tratamento completo de erros** — 401 (session expired), 403 (permission denied),
  404 (not found), 422 (inline field errors + alert geral sem status text HTTP),
  502/503 (service unavailable), network error.
- **Isolamento da War Room** — falha no painel de actions não afecta nenhum outro
  painel (intelligence, reports, media kits, content outputs têm queries independentes).
- **Segurança** — `X-Internal-Token` nunca enviado (guard activo em `client.ts`);
  nenhuma chamada directa a `intelligence_engine` ou `content_renderer`; sem secrets
  em `src/`.

### 4.2 Preparado mas condicionado por matching best-effort

- **Associação recommendation → acção** — best-effort via `metadata.recommendation_ref`
  gravado na criação. Não é uma FK relacional. Só funciona para acções criadas por
  este frontend. O ref pode divergir se a recommendation mudar de posição entre
  recálculos da intelligence (recommendations não são persistidas).
- **priority** — não é coluna dos 3 endpoints reais; gravada em `metadata.action_priority`
  na criação e lida na projecção. Convenção do frontend, não contrato backend.

---

## 5. Funcionalidades não implementadas

| Funcionalidade | Razão da ausência |
|---|---|
| **Mark Reviewed** | Recommendations não persistidas; sem endpoint de status `reviewed` em nenhum dos 3 artefactos |
| **Dismiss** | Idem; sem status `dismissed` persistível |
| **manual_task** | Sem endpoint de tasks no Backend Core |
| **asset_request** | Sem endpoint de asset requests no Backend Core |
| **Atualização de status de report/media-kit via UI** | `useUpdateCampaignAction` existe e funciona; falta affordance UI (fora do escopo desta fase) |
| **Ligação relacional a outputs existentes (CA-011)** | Sem FK no backend; só possível via metadata hoje |

Estas funcionalidades **não são mostradas como disabled** na UI do utilizador (não criam
expectativa falsa). Estão marcadas como `supported: false` em `CAMPAIGN_ACTION_CAPABILITIES`
e omitidas dos selectores de tipo.

---

## 6. Lacunas do Backend Core

| Lacuna | Impacto | Estado |
|---|---|---|
| Sem entidade `CampaignAction` persistente | Actions são projecções de 3 endpoints distintos; sem id unificado | Documentado; frontend projecta defensivamente |
| Recommendations não persistidas | Sem `id` estável entre recálculos | `recommendation_ref` derivado (best-effort) |
| Sem FK recommendation → action | Associação não relacional | `metadata.recommendation_ref` gravado na criação |
| Sem status `reviewed`/`dismissed` | Mark reviewed / dismiss não implementáveis | Omitidos; sem persistência falsa |
| `ContentPackRequest` sem PATCH | Artefacto imutável após criação | `updateCampaignAction` lança erro explícito para `content_pack` |
| Sem endpoint de tasks | `manual_task` não implementável | Marcado `supported: false` |
| Sem endpoint de asset requests | `asset_request` não implementável | Marcado `supported: false` |

Para uma traceabilidade firme de acções (recommendation → acção com status próprio,
mark_reviewed, dismiss, manual_task), é necessário backlog complementar no Backend Core
— ver §10 (Próximos Passos, CA-PDEC-006).

---

## 7. Estrutura frontend criada

```
src/
  entities/
    campaign-action/
      model.ts                              ← CampaignAction, CAMPAIGN_ACTION_CAPABILITIES
      campaign-action-api.ts                ← fetch/create/update sobre 3 endpoints
      recommendation-ref.ts                 ← derivação de RecommendationRef
      helpers.ts                            ← status normalization, labels, badge variants
      query-keys.ts                         ← keys scoped por workspace+campaign
      useCampaignActions.ts                 ← query agregada (Promise.allSettled)
      useCreateCampaignAction.ts            ← mutation + invalidações
      useUpdateCampaignAction.ts            ← mutation (report/media-kit); lança para content_pack
      index.ts

    content-pack/
      model.ts, content-pack-api.ts, useContentPacks.ts, index.ts

  features/
    campaign-actions/
      recommendation-action-draft.ts        ← builder defensivo de draft
      useRecommendationActionDraft.ts       ← hook (useMemo)
      action-type-options.ts                ← SELECT options derivadas de CAPABILITIES
      recommendation-action-match.ts        ← best-effort match rec→action
      RecommendationActionState.tsx         ← badges tipo + status
      CreateActionFromRecommendationButton.tsx  ← affordance por recommendation
      CreateActionFromRecommendationDialog.tsx  ← modal de criação real
      campaign-actions.module.css
      index.ts

  shared/
    ui/
      Dialog/                               ← wrapper <dialog> nativo
      ConfirmDialog/
      Select/
      Textarea/
      FormField/
      InlineFieldError/
      Input/

  widgets/
    campaign-actions-panel/
      CampaignActionsPanel.tsx              ← painel agregado na War Room
      CampaignActionsPanel.module.css
      index.ts
```

**Ficheiros modificados em código existente:**

| Ficheiro | Modificação |
|---|---|
| `features/campaign-intelligence/RecommendationItem.tsx` | Slot opcional `action?: ReactNode` |
| `features/campaign-intelligence/RecommendationsList.tsx` | Prop `renderAction` (render-prop pattern) |
| `features/campaign-intelligence/intelligence.module.css` | `.itemAction` |
| `widgets/campaign-recommendations-panel/CampaignRecommendationsPanel.tsx` | Pass-through de `renderAction` |
| `pages/campaign-war-room/CampaignWarRoomPage.tsx` | `actionsQuery` + `renderAction` + `CampaignActionsPanel` |
| `shared/ui/states/error-presets.ts` | Fix: description de ValidationError sem HTTP status text |
| `shared/ui/index.ts` | Exports dos novos componentes |

---

## 8. Validações executadas

| Validação | Resultado | Referência |
|---|---|---|
| `pnpm lint` (`eslint .`) | ✅ Limpo (sem erros) | Prompts 02–05, 07, 09, 11 |
| `pnpm build` (`tsc -b && vite build`) | ✅ Limpo (230 módulos, ~3.0s) | Prompts 02–05, 07, 09, 11 |
| Greps de segurança | ✅ Limpos | Prompts 07, 09, 11 |
| — `X-Internal-Token` / `INTERNAL_API_TOKEN` em `src/` | ✅ Apenas guard defensivo em `client.ts` | Prompts 07, 11 |
| — Chamadas directas a IE / CR em `src/` | ✅ Não encontradas | Prompts 07, 09, 11 |
| — Portas internas em `src/` | ✅ Não encontradas | Prompts 07, 09, 11 |
| — Secrets em `.env.example` / `.env.local` | ✅ Sem secrets | Prompts 07, 11 |
| Backend Core real confirmado em `:8000` | ✅ **Confirmado** | Prompt 11 |
| Frontend Vite confirmado em `:5173` | ✅ **Confirmado** | Prompt 11 |
| Login real (`POST /auth/token/`) | ✅ **HTTP 200** | Prompt 11 |
| `/auth/me/`, `/workspaces/`, `/campaigns/{id}/` | ✅ **HTTP 200** | Prompt 11 |
| Intelligence endpoint (`POST /intelligence/`) | ✅ **HTTP 200** (dry-run — sem recommendations reais) | Prompt 11 |
| Criação de report (`POST /reports/`) | ✅ **HTTP 201** com `recommendation_ref` em metadata | Prompt 11 |
| Criação de media kit (`POST /media-kits/` com `campaign`) | ✅ **HTTP 201** com `recommendation_ref` em metadata | Prompt 11 |
| Criação de content pack request (`POST /content-pack-requests/`) | ✅ **HTTP 201** com `recommendation_ref` em metadata | Prompt 11 |
| Campaign Actions Panel — listagens por campanha | ✅ **HTTP 200**, 3 endpoints, `recommendation_ref` recuperável | Prompt 11 |
| Erros 401, 404, 400 com field errors | ✅ Correctos | Prompt 11 |
| Validação UI visual (War Room → recommendations → botões de acção) | ⚠️ **PENDENTE** — Chrome extension não conectado + IE dry-run | Prompt 11 |

**Nota sobre CA-014 (Prompt 09 → Prompt 11):**
No Prompt 09, o serviço em `:8000` era uvicorn/FastAPI (não o Backend Core). No Prompt 11
(esta iteração), o Backend Core Django foi confirmado: `GET /api/v1/schema/` → 200,
`GET /admin/` → 200, `GET /` → 404.

**Limitação remanescente de CA-014:** a validação UI visual não foi executada porque:
1. O Chrome extension não estava conectado;
2. O Intelligence Engine corre em dry-run (`INTELLIGENCE_ENGINE_DRY_RUN=true`) — sem
   recommendations reais, os botões de acção por-recommendation não aparecem na War Room.
Para completar: (a) ligar o Chrome extension e navegar no browser, (b) correr o IE real
ou criar recommendations via fixture.

---

## 9. Riscos

| ID | Risco | Probabilidade | Impacto | Estado |
|---|---|---|---|---|
| CA-RSK-001 | Backend Core sem Campaign Actions API | Confirmado | Alto | **Materializado** — implementado com Resultado B |
| CA-RSK-002 | Recommendations sem `id` estável | Confirmado | Alto | **Mitigado** — `recommendation_ref` derivado, limitação documentada |
| CA-RSK-003 | Duplicação de acções para a mesma recommendation | Médio | Médio | **Parcialmente mitigado** — matching best-effort; se `actionsQuery` errar, botão volta a "Create action" (documentado) |
| CA-RSK-005 | Frontend assumir regras de negócio | Baixo | Alto | **Controlado** — Backend Core é fonte da verdade; nenhuma lógica de negócio no frontend |
| CA-RSK-006 | UI criar expectativa de automação | Baixo | Médio | **Controlado** — copy usa "Create action", não "Execute"; sem criação automática |
| CA-RSK-007 | 422/403 mal tratados | Baixo | Médio | **Mitigado** — auditoria completa em CA-012; correcção em `error-presets.ts` |
| CA-RSK-010 | Frontend chamar serviços internos | Baixo | Crítico | **Controlado** — guard em `client.ts`; greps verdes |

---

## 10. Pronto para piloto técnico controlado?

**Resposta: Condicionalmente sim — com requisitos claros.**

Para o piloto técnico controlado, os critérios do backlog §18 são:

| Critério | Estado |
|---|---|
| Caminho real recommendation → action existe | ✅ (3 endpoints reais, todos validados com HTTP 201) |
| Utilizador consegue criar ou registar uma acção | ✅ (confirmado via API; UI visual pendente) |
| Acção aparece associada à campanha | ✅ (painel agrega 3 endpoints; todos retornam HTTP 200) |
| Recommendation mostra estado coerente | ✅ (best-effort; `recommendation_ref` persistido e recuperável) |
| Falhas são tratadas | ✅ (auditoria completa + erros reais testados) |
| Sem atalhos inseguros | ✅ (greps verdes; guard de token activo) |
| Validação real foi executada | ✅ **Contratos de API validados** / ⚠️ UI visual pendente (Chrome + IE real) |
| Limitações estão documentadas | ✅ (arquitectura + este documento) |

**Estado do piloto**: os contratos de API estão validados com o Backend Core real.
O piloto técnico controlado pode ser iniciado. A validação UI visual completa (com
recommendations reais) requer o Intelligence Engine a correr sem dry-run.

---

## 11. Pronto para produção?

**Resposta: Não.**

Itens em falta para produção (conforme backlog §18):

- ❌ Testes E2E
- ❌ Auditoria de permissões (RBAC completo)
- ❌ UX refinada (revisão com utilizadores)
- ❌ Observabilidade frontend (error tracking)
- ❌ Tratamento robusto de refresh token
- ❌ Validação cross-browser
- ❌ Deploy de staging
- ❌ Validação com utilizadores reais
- ❌ CA-014 — validação integrada real

---

## 12. Próximos passos

| Prioridade | Item | Descrição |
|---|---|---|
| **Alta** | CA-014 (UI visual) | Contratos API validados ✅. Pendente: UI visual — requer Chrome extension conectado + IE real (sem dry-run) para render de recommendations e botões de acção |
| **Alta** | CA-PDEC-006 | Backlog backend complementar: entidade `CampaignAction` persistente com FK `campaign` + `recommendation_ref` + `status` + `related_*_id`. Pré-requisito para mark_reviewed, dismiss, manual_task, asset_request e traceabilidade firme |
| Média | CA-011 | Ligar acções a outputs existentes — requer CA-PDEC-006 para FK relacional; hoje só possível via metadata |
| Média | UX dos estados | Actualização de status de report/media-kit via UI (`useUpdateCampaignAction` já existe) |
| Baixa | mark_reviewed / dismiss | Requer CA-PDEC-006 (status persistível no backend) |
| Baixa | manual_task / asset_request | Requer CA-PDEC-006 (endpoint de tasks/asset requests no backend) |
| Baixa | Traceabilidade firme rec→action | Requer CA-PDEC-006 (FK `recommendation_ref` persistida, não apenas em metadata) |

---

## 13. Documentação gerada nesta fase

| Documento | Localização |
|---|---|
| Backlog da fase | `01_backlog.md` |
| Arquitectura da feature | `arquitectura_campaign_actions.md` |
| Este documento | `estado_campaign_actions_recommendation_to_execution.md` |
| Resultado CA-001 | `resultados_execucao/prompt_01_investigar_contratos_reais_resultado.md` |
| Resultado CA-002/003 | `resultados_execucao/prompt_02_modelar_acoes_dados_resultado.md` |
| Resultado CA-004/005 | `resultados_execucao/prompt_03_ui_draft_acao_resultado.md` |
| Resultado CA-006/007/008/009/012 | `resultados_execucao/prompt_04_criar_acao_war_room_resultado.md` |
| Resultado CA-008/009 (complement.) | `resultados_execucao/prompt_05_painel_campaign_actions_resultado.md` |
| Resultado CA-010 | `resultados_execucao/prompt_06_reviewed_dismissed_resultado.md` |
| Resultado CA-012 (audit.) | `resultados_execucao/prompt_07_erros_seguranca_resultado.md` |
| Resultado CA-013 | `resultados_execucao/prompt_08_documentar_arquitectura_resultado.md` |
| Resultado CA-014 (bloqueado) | `resultados_execucao/prompt_09_validar_integracao_real_resultado.md` |
| Resultado CA-014 (API validada) | `resultados_execucao/prompt_11_validacao_real_ca014_resultado.md` |
| Resultado CA-015 | `resultados_execucao/prompt_10_estado_final_resultado.md` |
