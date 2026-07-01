# Prompt 10 — Estado final da fase (Campaign Actions / Recommendation-to-Execution)

> Fase: `02_campaign_actions_recommendation_to_execution`
> Backlog de referência: `01_backlog.md` (CA-015)
> Relatórios anteriores: prompt_01 a prompt_09

---

## Execução 2026-06-30 (Iteração 01)

### Estado da execução

**Concluído** (documentos finais criados; nenhum código runtime alterado; lint/build
não executados neste prompt porque não houve alteração de código).

---

### Resumo objectivo

CA-015 pedia fechar a fase com relatório honesto. Foram lidos todos os 9 resultados
anteriores, o backlog completo (`01_backlog.md`) e o documento de arquitectura
(`arquitectura_campaign_actions.md`), e o estado real do código foi verificado.

**Conclusão da fase: Resultado B — suporte parcial do Backend Core.**

---

### Distinção obrigatória

#### A. Funcionalidade real com backend

Os seguintes fluxos estão **implementados sobre contratos reais** do Backend Core e
deverão funcionar numa integração real (sujeitos a CA-014):

| Funcionalidade | Endpoint real | Notas |
|---|---|---|
| Criar content pack request a partir de recommendation | `POST /content-pack-requests/` | Requer selecção de `content_pack` do catálogo |
| Criar report a partir de recommendation | `POST /reports/` | `report_type` default `campaign_report` |
| Criar media kit a partir de recommendation | `POST /media-kits/` | `artist` derivado de `campaign.artist` |
| Listar acções da campanha no painel | `GET /content-pack-requests/`, `/reports/`, `/media-kits/` (filtrado por `campaign`) | Agrega 3 endpoints em paralelo |
| Mostrar estado da acção por recommendation | Matching por `metadata.recommendation_ref` | Best-effort; ver B |

#### B. Funcionalidade preparada mas condicionada por limitação do Backend Core

Os seguintes elementos estão implementados mas com **limitação documentada**:

| Elemento | Limitação | Causa |
|---|---|---|
| Associação recommendation → acção | Best-effort via `metadata.recommendation_ref` — não é FK relacional | Backend Core não tem campo `recommendation_ref` nos artefactos como contrato; usamos `metadata` JSON |
| priority, description no artefacto | Convenção de metadata — não é coluna do backend | Os 3 endpoints não têm colunas `priority`/`description` |
| Matching recommendation → acção existente | Só detecta acções criadas por este frontend; ref pode divergir entre recálculos | Recommendations não são persistidas; ref é derivado de índice + conteúdo |

#### C. Funcionalidades não implementadas por ausência de contrato backend

| Funcionalidade | Razão | Decisão |
|---|---|---|
| Mark Reviewed | Backend sem status `reviewed` em nenhum dos 3 artefactos; recommendations não persistidas | Omitido — sem persistência falsa |
| Dismiss | Idem | Omitido — sem persistência falsa |
| manual_task | Sem endpoint de tasks no Backend Core | Marcado `supported: false` em `CAMPAIGN_ACTION_CAPABILITIES` |
| asset_request | Sem endpoint de asset requests | Idem |

#### D. Validação pendente por ambiente

A validação interactiva (login → workspace → campanha → War Room → criar acção) ficou
**pendente**:

- Durante CA-014 (Prompt 09), o serviço em `localhost:8000` era uvicorn/FastAPI a
  responder 200 em `/` mas 404 em `/admin/`, `/api/v1/schema/`, `/api/v1/auth/` —
  indicativo de que **não era o Django Backend Core**.
- O frontend não estava a correr em `:5173`.
- Conforme instrução, não foi feito troubleshooting de ambiente.
- **Aviso**: ligar o frontend ao serviço errado (IE/CR em vez de Backend Core) seria
  uma violação arquitectural. Confirmar `:8000` é o Django Backend Core antes de
  exercitar o fluxo.

---

### Critérios de aceitação da fase (backlog §11) — avaliação final

| Critério | Estado |
|---|---|
| Contratos reais foram investigados | ✅ (CA-001 / Prompt 01) |
| Não foram inventados endpoints | ✅ (apenas os 3 confirmados) |
| RecommendationItem tem affordance de execução | ✅ (CA-006/CA-007 / Prompt 04) |
| Create Action existe se backend suportar | ✅ (3 tipos reais; Prompt 04) |
| Campaign Actions Panel existe | ✅ (CA-008 / Prompts 04–05) |
| Recommendations mostram estado de execução | ✅ (best-effort; Prompt 04) |
| Erros são tratados | ✅ (CA-012 / Prompt 07 — auditoria + correcção) |
| workspace/auth respeitados | ✅ (guard workspaceId; guard `X-Internal-Token`) |
| Frontend chama apenas Backend Core | ✅ (greps verdes; prompts 07, 09) |
| Sem `X-Internal-Token` no frontend | ✅ (guard activo; nunca enviado) |
| Sem chamadas directas a IE/Renderer | ✅ (greps verdes) |
| `pnpm lint` passa | ✅ (limpo em todos os prompts com código) |
| `pnpm build` passa | ✅ (230 módulos; limpo em todos os prompts com código) |
| Documentação da feature existe | ✅ (`arquitectura_campaign_actions.md`) |
| Relatório final existe | ✅ (este ficheiro) |
| Estado final é honesto | ✅ |

**Critérios de aceitação parcial** (quando backend não suporta — backlog §11):

| Critério | Estado |
|---|---|
| Lacuna documentada | ✅ (arquitectura + estado) |
| UI não finge persistência | ✅ (sem mocks runtime) |
| Tipos sem suporte claramente indisponíveis ou omitidos | ✅ (`CAMPAIGN_ACTION_CAPABILITIES`; mark_reviewed/dismiss omitidos) |
| Backlog complementar Backend Core existe | ✅ (CA-PDEC-006 documentado) |

**Critérios de não aceitação** (backlog §12) — confirmados como **não violados**:

- Frontend não inventa acções sem backend real ✅
- Runtime não usa mocks para simular sucesso ✅
- Recommendations não aparecem como convertidas sem persistência real ✅
- `X-Internal-Token` não aparece como header enviado ✅
- Frontend não chama IE directamente ✅
- Frontend não chama Renderer directamente ✅
- Erros não mostram stack trace ou tokens ✅
- War Room não quebra quando actions falham ✅
- Build não falha ✅
- Lint não falha ✅
- Documentação não declara produção-ready sem evidência ✅

---

### Ficheiros criados ou alterados

**Criados:**
- `estado_campaign_actions_recommendation_to_execution.md` — estado final honesto da
  fase, cobrindo escopo, contratos, funcionalidades implementadas/não implementadas,
  lacunas, validações, riscos, critérios de piloto/produção e próximos passos.
- `resultados_execucao/prompt_10_estado_final_resultado.md` (este ficheiro).

**Nenhum ficheiro de runtime foi alterado.**

---

### Validações executadas e resultado

- ➖ `pnpm lint` — **não executado**: nenhum ficheiro de código runtime foi alterado neste
  prompt. Estado verde confirmado no prompt_09 (última execução com lint: eslint limpo).
- ➖ `pnpm build` — **não executado**: idem. Estado verde confirmado no prompt_09 (230
  módulos, sem erros de tipo).
- ✅ Documentos verificados: ambos existem e foram escritos.
- ✅ Grep de segurança nos documentos criados: sem passwords, API keys, private keys, nem
  valores de tokens reais. Ocorrências de `X-Internal-Token` são menções de documentação
  (descreve a regra), não tokens reais.
- ➖ `python manage.py check` — **não aplicável**: nenhum código backend foi alterado em
  nenhum prompt desta fase (todos os prompts foram frontend-only).
- ➖ Browser — **não usado**, conforme instrução.

---

### Pendências, riscos e próximo passo recomendado

- **CA-014 (validação integrada real)** — permanece pendente. Requer:
  1. Django Backend Core a responder em `localhost:8000` (confirmar `/api/v1/schema/`
     e `/admin/` antes de iniciar o frontend);
  2. Vite dev server em `localhost:5173`;
  3. Utilizador dev, workspace e campanha reais.
  - Aviso: o serviço ASGI que estava em `:8000` durante o Prompt 09 **não era** o Backend
    Core. Não confirmar o serviço antes de exercitar o fluxo é risco arquitectural.

- **CA-PDEC-006 (backlog backend complementar)** — recomendado antes do piloto firme:
  entidade `CampaignAction` persistente no Backend Core com FK `campaign` +
  `recommendation_ref` + `status` + campos relacionais opcionais. Pré-requisito para
  mark_reviewed, dismiss, manual_task, asset_request e traceabilidade relacional.

- **Próxima fase provável** (conforme backlog §17):
  - `03_content_pack_generation_from_actions`, ou
  - `03_reports_media_kits_execution_flow`,
  dependendo do valor a entregar no piloto técnico. A escolha deve seguir CA-PDEC-006 se
  rastreabilidade firme for requisito.
