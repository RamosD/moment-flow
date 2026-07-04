# Prompt 00 — Validação dos achados de produto — Resultado

> Fase: `08_prontidao_piloto_produto` (investigação preparatória — Prompt 00)
> Data: 2026-07-04
> Natureza: investigação curta de validação. Nenhum código funcional foi
> alterado. Nenhum backlog final foi criado. Nenhuma pipeline foi criada.
> Âmbito: apenas produto/UX/contratos. Sem cloud, produção, CI/CD ou hardening.
> Método: pesquisa textual ampla seguida de leitura directa de tipos,
> serializers, hooks e componentes (não apenas nomes de ficheiro).

---

## 1. Veredicto executivo

A análise externa (Claude Fable 5) está **substancialmente correcta nos seus
achados críticos**. O achado central — *o produto gera artefactos reais com
`Asset.public_url` mas a UI não permite abri-los/descarregá-los* — está
**confirmado com evidência dura**: `public_url` **não existe em lado nenhum de
`frontend/src`**, não há entidade `asset` no frontend, e não existe um único
`href`, `download` ou `window.open` que aponte para um artefacto.

Correcção importante a fazer antes do backlog: a formulação "`public_url` chega
ao frontend" é **refutada** — `public_url` existe no contrato do backend
(`AssetSerializer`, endpoint `/assets/`), mas os serializers de
report/media-kit/content-output expõem apenas `storage_asset` (um UUID/FK), não
o URL. Para obter um link de download o frontend precisaria de um **segundo
salto** (`GET /assets/{id}/`) que nenhum código actual faz. Isto não enfraquece
o achado — reforça-o e define o trabalho: ou o frontend passa a resolver o
asset, ou os serializers de artefacto passam a embeber `public_url`.

Dos 8 riscos de produto levantados, **7 ficam confirmados** e **1 fica
confirmado-com-nuance** (funil de eventos: inexistente como produto, embora
exista infraestrutura de `AuditEvent` técnica que pode servir de base parcial).
Um ponto merece nuance a favor do produto: `confidence`, `reason` e
`explanations` por recomendação **já chegam ao browser** dentro do payload de
intelligence (passthrough) — a falha é puramente de renderização, não de
contrato, o que torna esse achado um *quick win* barato.

---

## 2. Achados confirmados

| # | Achado | Estado | Evidência-chave |
|---|---|---|---|
| A2 | UI não permite abrir/descarregar artefactos | ✅ Confirmado | Zero `href`/`download`/`window.open`/`<a>` para artefactos em `frontend/src` |
| A3 | Sem auto-refresh/polling de estados | ✅ Confirmado | Nenhum `refetchInterval` no repositório; só `staleTime` e `refetch()` manual |
| A4 | Recomendações não mostram `explanations`/`confidence` inline | ✅ Confirmado (com nuance: dados já no payload) | `RecommendationItem` só mostra título/prioridade/descrição; `ExplanationsPanel` é envelope-level, não por item |
| A5 | UUIDs crus visíveis ao utilizador | ✅ Confirmado | `CampaignActionsPanel` renderiza `Report: <uuid>` etc. |
| A6 | Copy técnico visível | ✅ Confirmado | "persistent CampaignAction", "Artifact-backed…", "recommendation_ref… canonical CampaignAction fields" |
| A7 | Dashboard vazio/placeholder | ✅ Confirmado | `DashboardPage` = "Your overview will appear here in a later phase" e é a rota index `/` |
| A8 | Sem funil mínimo de eventos de produto | ✅ Confirmado (com nuance) | Existe `AuditEvent` técnico; não existem eventos de produto (`war_room_viewed`, `artifact_opened`, `artifact_rated`) |

---

## 3. Achados parcialmente confirmados

| # | Achado | Estado | Nota |
|---|---|---|---|
| A1 | "`public_url` chega ao frontend" | ⚠️ Parcial → **refutado na forma, confirmado no espírito** | `public_url` existe no **backend** (`AssetSerializer` + `/assets/`), mas **não** no frontend. Os artefactos expõem só `storage_asset` (UUID). Falta o salto `GET /assets/{id}/`, que não existe no frontend |
| A4 | `confidence`/`explanations` por recomendação | ⚠️ Parcial | **Não são mostrados** (confirmado), mas **estão presentes no payload** que o browser recebe (passthrough do IE). É lacuna de UI, não de contrato |
| A8 | Funil de eventos | ⚠️ Parcial | Não existe funil de produto; existe `AuditEvent` (auditoria técnica: quem/o quê/entidade). Eventos server-side como `action_created` são parcialmente auditáveis; eventos de comportamento (view/open/rate) não existem |

---

## 4. Achados refutados

| # | Achado (formulação literal) | Porquê é refutado |
|---|---|---|
| A1 | "`public_url` chega ao frontend" | Refutado como afirmação literal: `public_url` **não aparece** em nenhum ficheiro de `frontend/src`. A única referência a assets no frontend é `storage_asset?: UUID \| null` em três modelos. O URL vive só no backend |

Nota: refutar esta *formulação* **não** contradiz a análise do Fable 5, que
afirmava precisamente "ausência de uso de `public_url` no frontend" — essa
ausência está confirmada. A refutação é apenas da leitura optimista de que "o
dado já chega à UI".

---

## 5. Achados inconclusivos

| Tema | Porquê inconclusivo |
|---|---|
| Qualidade percebida real dos artefactos (PDF/PNG) | Não avaliável por código: como a UI não os abre, não há forma de julgar se um media kit/report gerado é "enviável". Requer inspecção manual dos ficheiros no MinIO — fora do âmbito deste prompt de código |
| Se `recommendationTitle` mostra um título legível ou um `action` cru | O IE emite `action`/`reason` (não `title`/`description`); o frontend lê `['title','label','name','type']` para o título e cai para `action`. Se o Backend Core não remapeia, o "título" exibido pode ser a string técnica `create_media_kit`. Não confirmei o reshape exacto — merece verificação visual no War Room |
| Cobertura de `content-pack-requests` na UI | A entidade existe (`entities/content-pack-request`), mas não localizei um painel dedicado de outputs do content pack no War Room. Requer confirmação se os outputs do pack aparecem no `CampaignAssetsPanel` (content-outputs) ou não têm superfície própria |

---

## 6. Evidência por área

### 6.1 `public_url` e assets

**Backend (contrato existe):**
- `AssetSerializer` expõe `public_url` explicitamente —
  [core/serializers.py:31](../../../../../backend_core/apps/core/serializers.py) (campo `public_url` na lista de `fields`).
- Endpoint REST existe: `router.register("assets", AssetViewSet, basename="asset")` —
  [core/urls.py:10](../../../../../backend_core/apps/core/urls.py). O `AssetSerializer` devolve também `mime_type`, `file_name`, `file_size_bytes`, `storage_provider`, etc.
- Os serializers de artefacto expõem **`storage_asset` (FK/UUID), não o URL**:
  `ReportSerializer` (`storage_asset`, [reports/serializers.py:45](../../../../../backend_core/apps/reports/serializers.py)),
  `MediaKitSerializer` (`storage_asset`, reports/serializers.py:133).
- O callback do renderer preenche `public_url` no `Asset` associado —
  [reports/callbacks.py:109](../../../../../backend_core/apps/reports/callbacks.py),
  [content/callbacks.py:329](../../../../../backend_core/apps/content/callbacks.py).

**Frontend (o dado não chega ao utilizador):**
- `public_url` **não aparece em nenhum ficheiro de `frontend/src`** (pesquisa
  textual ampla). As únicas correspondências de assets são
  `storage_asset?: UUID | null` em:
  [report/model.ts:40](../../../../src/entities/report/model.ts),
  [media-kit/model.ts:58](../../../../src/entities/media-kit/model.ts),
  [content-output/model.ts:46](../../../../src/entities/content-output/model.ts).
- **Não existe entidade `asset` no frontend** — não há
  `frontend/src/entities/asset/`. Logo não há tipo `Asset`, nem API client, nem
  hook que faça `GET /assets/{id}/` para resolver `public_url`.

**Conclusão:** o pipeline de dados está partido no último passo. O backend sabe
o URL; o frontend nunca o pede. **Refutado** que "`public_url` chega ao
frontend"; **confirmada** a ausência de uso no frontend.

### 6.2 Abertura/download na UI

- Pesquisa por `href=`, `download`, `window.open`, `<a `, `.pdf`, `public_url`
  em `frontend/src`: **zero** correspondências ligadas a artefactos (só os três
  `storage_asset`).
- `CampaignReportsPanel` — mostra `report.title`, `humanize(report_type)`,
  mensagem de falha e `Badge` de estado. **Sem link**:
  [CampaignReportsPanel.tsx:57-78](../../../../src/widgets/campaign-reports-panel/CampaignReportsPanel.tsx).
- `CampaignAssetsPanel` (content outputs) — `title`/`output_type`, `format` e
  `Badge` de estado. **Sem link**:
  [CampaignAssetsPanel.tsx:44-63](../../../../src/widgets/campaign-assets-panel/CampaignAssetsPanel.tsx).
- `CampaignMediaKitsPanel` — mesmo padrão (título + estado), sem `href`
  (confirmado pela ausência total de `href`/`download` no frontend).
- `CampaignActionsPanel` — as relações são mostradas como texto
  `{label}: {id}` com o UUID cru; **não são links**:
  [CampaignActionsPanel.tsx:107-115](../../../../src/widgets/campaign-actions-panel/CampaignActionsPanel.tsx).

**Consegue o utilizador…?**
- Abrir report PDF → **Não.**
- Abrir media kit PDF → **Não.**
- Abrir outputs do content pack → **Não.**
- Chegar ao artefacto a partir da action relacionada → **Não** (só vê o UUID).

**Achado A2: confirmado.** Este é o bloqueio de valor nº 1.

### 6.3 Polling/auto-refresh

- **Nenhum `refetchInterval`** em todo o `frontend/src`.
- `staleTime`: 30s global ([queryClient.ts:22](../../../../src/app/providers/queryClient.ts)),
  2min em intelligence ([useCampaignIntelligence.ts:30](../../../../src/features/campaign-intelligence/useCampaignIntelligence.ts)),
  5min em workspaces.
- `invalidateQueries` existe **apenas após mutações** (criar acção, troca de
  workspace) — [useCreateActionFromRecommendation.ts:217-228](../../../../src/features/campaign-actions/useCreateActionFromRecommendation.ts),
  [invalidate-campaign-action-cache.ts](../../../../src/entities/campaign-action/invalidate-campaign-action-cache.ts).
  Nunca é disparado pela conclusão assíncrona de um job de renderer.
- `refetch()` só aparece em `ErrorState` (retry manual pelo utilizador).
- Estados não-terminais existem nos tipos (`queued`, `processing`, `rendering`,
  `uploading`, `validating`, `pending`, `in_progress`) mas **nada os observa**.

**Consequência:** quando o Renderer termina e o callback actualiza o backend, a
UI **não reflecte a mudança sem reload manual**. O utilizador cria uma acção,
vê "processing/queued" e o estado nunca progride sozinho. **Achado A3:
confirmado.**

### 6.4 Recomendações, explanations e confidence

**No payload (o dado existe):**
- Schema do IE `Recommendation` tem `confidence`, `reason`, e `explanations`
  por recomendação — [recommendations.py:37-43](../../../../../intelligence_engine/app/schemas/recommendations.py).
- O Backend Core faz **passthrough** do bloco `result` do motor:
  `result=result.result` — [intelligence_service.py:250](../../../../../backend_core/apps/campaigns/intelligence_service.py).
  Logo `confidence`/`reason`/`explanations` por recomendação **chegam ao
  browser** dentro de cada objecto de `result.recommendations`.

**Na UI (o dado não é mostrado):**
- O tipo `CampaignRecommendation` declara só `id/type/title/description/
  priority/action` + índice `[key: string]: unknown` —
  [intelligence.ts:39-47](../../../../src/entities/campaign/intelligence.ts).
  `confidence`/`explanations`/`reason` **não são tipados**.
- `RecommendationItem` renderiza apenas título, badge de prioridade e
  `description = readString(description) ?? readString(action)` — **nunca
  `confidence` nem `explanations` por item** —
  [RecommendationItem.tsx:26-41](../../../../src/features/campaign-intelligence/RecommendationItem.tsx).
- `ExplanationsPanel` mostra as explicações **do envelope** (a nota consolidada
  `scoring_basis`), num `<details>` "Why these results?" **no fundo de toda a
  secção**, desligado de cada recomendação —
  [ExplanationsPanel.tsx](../../../../src/features/campaign-intelligence/ExplanationsPanel.tsx),
  ligado em [CampaignWarRoomPage.tsx:108](../../../../src/pages/campaign-war-room/CampaignWarRoomPage.tsx).

**Achado A4: confirmado**, com a nuance decisiva de que é uma lacuna de
renderização (dados presentes) e não de contrato — logo, barato de fechar.

### 6.5 UUIDs e copy técnico

**UUIDs crus (A5: confirmado):**
- `CampaignActionsPanel` → `relatedItems()` devolve `[label, id]` onde `id` é o
  UUID de `related_report`/`related_media_kit`/`related_content_pack_request`/
  `related_content_output`, renderizado como `{label}: {id}` (e `title={id}`) —
  [CampaignActionsPanel.tsx:72-79 e 107-115](../../../../src/widgets/campaign-actions-panel/CampaignActionsPanel.tsx).
  Exemplo visível ao utilizador: `Report: 3fa85f64-5717-4562-b3fc-…`.

**Copy técnico (A6: confirmado)** — texto user-facing (JSX/props, não
comentários nem testes):
- Diálogo: descrição *"Artifact-backed actions create the artifact first, then
  register a persistent CampaignAction with the related id."* —
  [CreateActionFromRecommendationDialog.tsx:298](../../../../src/features/campaign-actions/CreateActionFromRecommendationDialog.tsx).
- Diálogo: *"Source, recommendation_ref and the safe recommendation_snapshot are
  recorded automatically as canonical CampaignAction fields."* — dialog.tsx:461-464.
- Diálogo: *"Artifact created; action not registered"*, *"Retry CampaignAction
  only"*, *"Retry is disabled because the artifact scope/relation conflicts."*
- `CampaignActionsPanel`: *"Persistent actions recorded for this campaign."*,
  *"Only CampaignActions recorded in the new API appear here. Earlier artifacts
  remain available in their own panels."*, *"Related artifact unavailable or not
  linked."* — CampaignActionsPanel.tsx:118,173,231.

### 6.6 Dashboard

- `DashboardPage` é placeholder declarado: header *"Welcome to MomentFlow. Start
  from your campaigns."* e Card *"Your overview will appear here in a later
  phase."* — [DashboardPage.tsx:10-19](../../../../src/pages/dashboard/DashboardPage.tsx).
- É a **rota index** (`/`), i.e. a primeira página pós-login:
  `{ index: true, element: <DashboardPage /> }` —
  [routes.tsx:30](../../../../src/app/router/routes.tsx).
- **Sem next-best-action, sem valor accionável.** **Achado A7: confirmado.**

### 6.7 Funil de eventos

- Existe `AuditEvent` — [audit/models.py:16](../../../../../backend_core/apps/audit/models.py):
  captura `action`, `actor_type`, `entity_type`, `entity_id`, `before_data`/
  `after_data`, IP/UA **hasheados**. É um **registo de auditoria técnica**
  (imutável, orientado a compliance/segurança), não um funil de produto.
- `record_audit_event` é chamado em ~23 sítios (submissão de jobs, callbacks,
  intelligence, links, billing, workspaces) — server-side.
- **Não existem** eventos de produto/comportamento: `war_room_viewed`,
  `recommendation_seen`, `artifact_opened`, `artifact_rated`. Por natureza,
  três destes (view/open/rate) são eventos de browser e não poderiam viver só
  no backend.

**Achado A8: confirmado (funil ausente), com nuance:** o `AuditEvent` pode ser
uma **base parcial** para eventos server-side (`action_created`,
`artifact_ready`), mas não substitui a instrumentação do lado do utilizador nem
está modelado como funil.

### 6.8 Contratos existentes úteis para a fase 08

| Contrato | Estado | Campos úteis já disponíveis | Lacuna |
|---|---|---|---|
| `GET /assets/{id}/` | ✅ Existe | `public_url`, `mime_type`, `file_name`, `file_size_bytes`, `storage_provider` | Frontend não tem entidade/hook para o consumir |
| `GET /reports/?campaign=` | ✅ Existe | `storage_asset` (UUID), `status`, `metadata.error` | Não embebe `public_url` → exige 2º salto |
| `GET /media-kits/` | ✅ Existe | `storage_asset` (UUID), `status`, `items` | Idem |
| `GET /content-outputs/?campaign=` | ✅ Existe | `storage_asset` (UUID), `status`, `format` | Idem |
| `GET /content-pack-requests/` | ✅ Existe (entidade FE presente) | — | Sem painel de outputs próprio confirmado |
| `GET /campaign-actions/` | ✅ Existe | `related_*` (UUIDs) + `related_artifact_status` | Relações são UUIDs, não links resolvidos |
| `POST /campaigns/{id}/intelligence/` | ✅ Existe | recomendações com `confidence`/`reason`/`explanations` (passthrough) | Frontend não tipa nem renderiza esses campos |
| Evento de produto | ❌ Não existe | `AuditEvent` (técnico) como base parcial | Sem funil de produto |

**Decisão de contrato para a fase 08:** para o download, escolher entre (a)
frontend passa a resolver `storage_asset` via `GET /assets/{id}/` (sem tocar no
backend), ou (b) backend embebe `public_url`/`file_name` nos serializers de
artefacto (uma chamada em vez de duas). A opção (b) é mais simples para a UI e
evita N+1, mas é alteração de contrato do backend — decisão a tomar no backlog.

---

## 7. Riscos de produto validados

1. **Loop de valor não fecha** — o utilizador não consegue abrir o que pediu.
   Risco de adopção crítico para qualquer piloto. (A1/A2)
2. **Silêncio pós-acção** — sem polling, o estado parece "preso"; percepção de
   produto partido mesmo com backend saudável. (A3)
3. **Explicabilidade desperdiçada** — o diferenciador (recomendações com razão e
   confiança) está no payload e não é mostrado. (A4)
4. **Linguagem de engenharia** — UUIDs e jargão minam a confiança do
   utilizador-alvo (manager/artista). (A5/A6)
5. **Primeira impressão vazia** — o dashboard-index não dá valor imediato. (A7)
6. **Piloto não mensurável** — sem funil, não há como saber se o piloto
   funcionou. (A8)

---

## 8. Implicações para a fase 08

- A fase deve ser de **produto/UX/instrumentação**, não de infra. Todos os
  riscos técnicos foram fechados nas fases 06/07; os riscos validados aqui são
  100% de experiência de produto.
- O maior rácio impacto/esforço é **resolver o download** — o backend já tem o
  contrato (`/assets/`), falta a superfície no frontend (ou embeber o URL).
- Vários achados são **quick wins de renderização** (explicabilidade inline,
  esconder UUIDs, copy humano) porque o dado já existe.
- Decisão de contrato a registar no backlog: resolver asset no frontend **vs.**
  embeber `public_url` nos serializers de artefacto.
- A instrumentação de funil precisa de decisão: reutilizar/estender
  `AuditEvent` para eventos server-side **vs.** um modelo de evento de produto
  dedicado; e como capturar eventos de browser (`viewed`/`opened`/`rated`).

---

## 9. Candidatos prioritários de backlog

Ordenados por impacto/esforço (não é o backlog final — são candidatos):

1. **PIL-001 — Abrir/descarregar artefactos.** Expor `public_url` na UI
   (report, media kit, content outputs e a partir da action relacionada).
   Impacto máximo, esforço baixo. Fecha A1/A2.
2. **PIL-002 — Auto-refresh de artefactos em curso.** `refetchInterval`
   condicional a estados não-terminais + invalidação ao completar. Fecha A3.
3. **PIL-004 — Explicabilidade inline.** Mostrar `confidence` e as
   `explanations` por recomendação no `RecommendationItem` (dados já no
   payload). Fecha A4.
4. **PIL-003 — Copy humano + esconder UUIDs.** Rever strings user-facing e
   substituir `Report: <uuid>` por links nomeados. Fecha A5/A6.
5. **PIL-005 — Funil mínimo de eventos.** Decidir modelo e capturar os 6
   eventos ponta-a-ponta. Fecha A8 e torna o piloto mensurável.

(PIL-007 preview do que vai ser gerado e PIL-008 next-best-action no dashboard
são candidatos secundários, para capacidade sobrante.)

---

## 10. Critérios de aceitação para avançar para backlog

- [x] Relatório criado neste caminho.
- [x] Cada achado relevante classificado (confirmado / parcial / refutado /
      inconclusivo).
- [x] `public_url` classificado com base no código (existe no backend, ausente
      no frontend).
- [x] Download/abertura classificado com base no código (inexistente).
- [x] Polling/auto-refresh classificado (inexistente).
- [x] Recomendações/`explanations`/`confidence` classificado (não mostrado;
      dados presentes no payload).
- [x] UUIDs/copy técnico classificado com ficheiro/linha.
- [x] Dashboard classificado (placeholder, rota index).
- [x] Funil de eventos classificado (ausente; `AuditEvent` técnico como base
      parcial).
- [x] Recomendação clara para a fase 08.
- [x] Nenhum código funcional alterado.

---

## 11. Ficheiros inspeccionados

**Frontend — tipos/entidades:**
- `frontend/src/entities/report/model.ts`
- `frontend/src/entities/media-kit/model.ts`
- `frontend/src/entities/content-output/model.ts`
- `frontend/src/entities/campaign-action/model.ts`
- `frontend/src/entities/campaign/intelligence.ts`
- (verificada a ausência de `frontend/src/entities/asset/`)

**Frontend — componentes/widgets/páginas:**
- `frontend/src/widgets/campaign-actions-panel/CampaignActionsPanel.tsx`
- `frontend/src/widgets/campaign-reports-panel/CampaignReportsPanel.tsx`
- `frontend/src/widgets/campaign-assets-panel/CampaignAssetsPanel.tsx`
- `frontend/src/widgets/campaign-recommendations-panel/CampaignRecommendationsPanel.tsx`
- `frontend/src/features/campaign-intelligence/RecommendationItem.tsx`
- `frontend/src/features/campaign-intelligence/ExplanationsPanel.tsx`
- `frontend/src/features/campaign-intelligence/intelligence-format.ts`
- `frontend/src/features/campaign-actions/CreateActionFromRecommendationDialog.tsx`
- `frontend/src/pages/campaign-war-room/CampaignWarRoomPage.tsx`
- `frontend/src/pages/dashboard/DashboardPage.tsx`
- `frontend/src/app/router/routes.tsx`
- `frontend/src/app/providers/queryClient.ts` (via pesquisa)

**Frontend — E2E:**
- `frontend/e2e/main-flow.spec.ts`

**Backend:**
- `backend_core/apps/core/serializers.py`
- `backend_core/apps/core/urls.py`
- `backend_core/apps/reports/serializers.py` (via pesquisa)
- `backend_core/apps/reports/callbacks.py` / `content/callbacks.py` (via pesquisa)
- `backend_core/apps/campaigns/intelligence_service.py`
- `backend_core/apps/audit/models.py`
- `backend_core/apps/audit/services.py` (via pesquisa)

**Intelligence Engine:**
- `intelligence_engine/app/schemas/recommendations.py`
- `intelligence_engine/app/services/recommendation_engine.py`

---

## 12. Limitações da investigação

- **Não houve execução da UI.** Toda a validação é estática (tipos, hooks,
  componentes, serializers). Não confirmei visualmente o que o utilizador vê no
  browser — em particular se `recommendationTitle` mostra um título legível ou a
  string técnica `create_media_kit` (ver §5, inconclusivo).
- **Qualidade dos artefactos não avaliada** — inacessível pela UI; exigiria
  abrir os ficheiros no MinIO.
- **Reshape exacto Backend Core → recomendações** não foi lido linha a linha
  além do passthrough `result=result.result`; assumi que os campos sobrevivem
  porque o contrato frontend os trata como untyped passthrough. Baixo risco,
  mas não é prova formal de cada campo.
- **`CampaignMediaKitsPanel`** foi inferido por padrão + ausência global de
  `href`/`download`, não lido integralmente.
- **Painel de outputs do content pack** não foi localizado com certeza (§5).

---

## 13. Próximo passo recomendado

Avançar para a criação do **backlog da fase 08** (`01_backlog.md`), incorporando
as correcções desta validação:

1. Reformular o achado A1 no backlog como **"`public_url` existe no backend
   (`/assets/`) mas não é consumido pelo frontend; falta o salto de resolução
   OU embeber o URL no serializer de artefacto"** — e registar essa decisão de
   contrato como item explícito.
2. Enquadrar A4 como **quick win de renderização** (dados já no payload), não
   como trabalho de contrato.
3. Priorizar PIL-001/002/003/004 (fechar o loop + confiança) e PIL-005 (tornar
   o piloto mensurável), deixando dashboard e preview como secundários.
4. Antes de implementar, resolver as duas decisões de contrato: (a) resolver
   asset no frontend vs. embeber `public_url` no backend; (b) modelo de evento
   de produto vs. extensão de `AuditEvent`.
5. Recomenda-se uma verificação visual curta do War Room (rever o item
   inconclusivo do título da recomendação) antes de fechar o backlog.
