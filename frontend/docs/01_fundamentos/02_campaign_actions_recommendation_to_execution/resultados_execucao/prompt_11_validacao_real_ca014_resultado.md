# Prompt 11 — Validação integrada real CA-014 (Campaign Actions)

> Fase: `02_campaign_actions_recommendation_to_execution`
> Backlog de referência: `01_backlog.md` (CA-014)
> Relatório anterior: `prompt_09_validar_integracao_real_resultado.md` (PENDENTE por ambiente)
> Data: 2026-06-30

---

## Execução 2026-06-30 (Iteração 02 — continuação de CA-014)

### Estado da execução

**executado_parcialmente** — todos os contratos de API validados com o Backend Core
real; criação dos 3 tipos de acção confirmada; Campaign Actions Panel confirmado;
`recommendation_ref` em metadata persiste e é recuperável; `pnpm lint` e `pnpm build`
verdes. A validação visual da UI (browser) não foi possível porque o Chrome extension
não estava conectado. Intelligence em dry-run (sem recomendações reais por design).

---

### Resumo objectivo

CA-014 pedia validar o fluxo completo `login → workspace → campanha → War Room →
criar action real` contra o Backend Core real, sem mocks. Esta iteração completou
a validação de todos os contratos de API e dados críticos. A validação UI visual
(navegação pelo browser, render de recommendations, botões de acção) ficou pendente
por limitação técnica do Chrome extension.

---

### Confirmação do Backend Core real em `localhost:8000`

| Endpoint | HTTP | Interpretação |
|---|---|---|
| `GET /` | **404** | Django sem rota raiz — correcto |
| `GET /api/v1/schema/` | **200** | Schema OpenAPI acessível |
| `GET /admin/` | **200** | Django admin acessível |

**Conclusão**: o serviço em `:8000` é o Django Backend Core. Contrasta com o Prompt
09 onde era uvicorn/FastAPI (200 em `/`, 404 em `/api/v1/schema/`).

**Comando usado:**
```
python manage.py runserver 127.0.0.1:8000
# (venv: backend_core/venv/Scripts/python.exe)
```

---

### Confirmação do frontend em `localhost:5173`

| URL | HTTP | Resultado |
|---|---|---|
| `http://localhost:5173/` | **200** | Vite dev server a responder |

**Variável de ambiente confirmada** (`.env.local`):
```
VITE_BACKEND_API_BASE_URL=http://localhost:8000/api/v1
```

**`.env.local` gitignored**: confirmado (`.env.*` em `.gitignore`, excepto `.env.example`).

**Comando usado:**
```
pnpm dev
# (frontend/ — Vite v8.1.0)
```

---

### Dados dev criados (sem segredos)

Os seguintes dados dev foram criados para esta validação. Não são dados de produção.

| Recurso | Identificador | Nota |
|---|---|---|
| Utilizador | `ca014-dev@example.local` | Criado via Django shell |
| Workspace | `46ca02a0-edcf-4835-8878-a6ff24b41598` — "CA014 Dev Workspace" | Criado via `create_workspace()` |
| Artist | `915a6fdc-270f-42fa-86ea-ef2ccd70746b` — "CA014 Test Artist" | Criado via Django ORM |
| Campaign | `30930999-5cd3-47d8-afb0-2c218084ed7d` — "CA014 Test Campaign" | Criado via Django ORM |

Nenhuma password ou token real está registado neste relatório.

---

### Validação de login / workspace / campanha / War Room

| Passo | Endpoint | HTTP | Resultado |
|---|---|---|---|
| Login | `POST /api/v1/auth/token/` | **200** | JWT access + refresh tokens recebidos |
| Perfil próprio | `GET /api/v1/auth/me/` | **200** | `email: ca014-dev@example.local`, `id` confirmado |
| Workspaces | `GET /api/v1/workspaces/` | **200** | 1 workspace visível |
| Campanha | `GET /api/v1/campaigns/{id}/` | **200** | `name: "CA014 Test Campaign"`, `status: active` |
| Intelligence | `POST /api/v1/campaigns/{id}/intelligence/` | **200** | Dry-run (ver nota abaixo) |

**Nota sobre intelligence (dry-run)**:
O Backend Core tem `INTELLIGENCE_ENGINE_DRY_RUN=true` (confirmar em `.env`). A resposta é:
```json
{
  "status": "completed",
  "source": "dry_run",
  "result": {
    "grade": "unknown",
    "moments": [],
    "recommendations": [],
    "summary": "Dry-run: Intelligence Engine was not called."
  },
  "warnings": [{"code": "dry_run", "message": "INTELLIGENCE_ENGINE_DRY_RUN is enabled"}]
}
```
A lista `result.recommendations` é vazia por design. O frontend lê `intelligence.result.recommendations`
(tipo `CampaignIntelligenceResult.recommendations`) — alinhado com o contrato real.
No browser, a War Room mostraria a secção de recommendations vazia (estado honesto).

---

### Validação de criação real de actions

#### A. Report request — `POST /api/v1/reports/`

```http
POST /api/v1/reports/
{
  "campaign": "30930999-5cd3-47d8-afb0-2c218084ed7d",
  "title": "CA014 Test Report",
  "report_type": "campaign_report",
  "metadata": {
    "recommendation_ref": "30930999-5cd3-47d8-afb0-2c218084ed7d:i0:ca014-test",
    "action_source": "recommendation",
    "action_priority": "high"
  }
}
```

**HTTP: 201** ✅

Resposta:
```json
{
  "id": "76f8f25f-5381-4b93-ae8d-f0bc178d324d",
  "title": "CA014 Test Report",
  "status": "queued",
  "campaign": "30930999-5cd3-47d8-afb0-2c218084ed7d"
}
```

#### B. Media kit request — `POST /api/v1/media-kits/`

**Nota sobre o campo `campaign`**: o frontend (`campaign-action-api.ts`) passa
`campaign: input.campaignId` no payload. Essencial para que o media kit apareça no
filtro `?campaign=<id>` do painel. Confirmado no código:

```ts
case 'media_kit_request': {
  const payload = {
    campaign: input.campaignId,
    artist: input.artistId,
    title: input.title,
  }
}
```

```http
POST /api/v1/media-kits/
{
  "campaign": "30930999-5cd3-47d8-afb0-2c218084ed7d",
  "artist": "915a6fdc-270f-42fa-86ea-ef2ccd70746b",
  "title": "CA014 Test Media Kit 2",
  "metadata": {
    "recommendation_ref": "30930999-5cd3-47d8-afb0-2c218084ed7d:i1:ca014-test-mk",
    "action_source": "recommendation",
    "action_priority": "medium"
  }
}
```

**HTTP: 201** ✅

Resposta:
```json
{
  "id": "7861ec84-374d-45e9-a0df-36ac4fffb450",
  "title": "CA014 Test Media Kit 2",
  "status": "draft",
  "campaign": "30930999-5cd3-47d8-afb0-2c218084ed7d",
  "artist": "915a6fdc-270f-42fa-86ea-ef2ccd70746b"
}
```

#### C. Content pack request — `POST /api/v1/content-pack-requests/`

Catálogo verificado (`GET /content-packs/?status=active`): **4 content packs activos**
(ex.: "Auto Media Kit" — `85ddb087-4227-4f9e-bccf-f513ff1b0af7`).

```http
POST /api/v1/content-pack-requests/
{
  "campaign": "30930999-5cd3-47d8-afb0-2c218084ed7d",
  "content_pack": "85ddb087-4227-4f9e-bccf-f513ff1b0af7",
  "metadata": {
    "recommendation_ref": "30930999-5cd3-47d8-afb0-2c218084ed7d:i2:ca014-test-cp",
    "action_source": "recommendation",
    "action_title": "CA014 Content Pack"
  }
}
```

**HTTP: 201** ✅

Resposta:
```json
{
  "id": "7b0c9a3c-34d4-4c5c-9f6e-2f00df39396e",
  "status": "queued",
  "campaign": "30930999-5cd3-47d8-afb0-2c218084ed7d",
  "content_pack": "85ddb087-4227-4f9e-bccf-f513ff1b0af7"
}
```

---

### Validação do Campaign Actions Panel

Os 3 endpoints de listagem filtrados por campanha, que alimentam o painel na War Room:

| Endpoint | HTTP | Resultados | recommendation_ref presente |
|---|---|---|---|
| `GET /content-pack-requests/?campaign=<id>&page_size=50` | **200** | 1 | ✅ |
| `GET /reports/?campaign=<id>&page_size=50` | **200** | 1 | ✅ |
| `GET /media-kits/?campaign=<id>&page_size=50` | **200** | 1 | ✅ |

Confirmado: `metadata.recommendation_ref` é recuperável em todos os artefactos
criados. O matching `recommendation → action` (best-effort) funciona.

---

### Validação da associação recommendation → action

A associação é **best-effort via `metadata.recommendation_ref`**. Confirmado:

1. Na criação, o frontend grava `metadata.recommendation_ref` com o valor derivado
   de `campaignId:i<index>:<slug>` ou `campaignId:id:<rec.id>`.
2. Na listagem, o campo `metadata.recommendation_ref` é recuperado nos 3 endpoints.
3. O `matchRecommendationAction` em `features/campaign-actions/recommendation-action-match.ts`
   compara o ref derivado da recommendation com o ref persistido no artefacto.
4. **Limitação documentada**: associação só existe para acções criadas por este frontend
   usando esta convenção. Artefactos criados por outros meios não são correlacionados.
   O ref pode divergir se a recommendation mudar entre recálculos (não persistida).

---

### Validação de erros

| Cenário | Endpoint | HTTP recebido | Esperado | Estado |
|---|---|---|---|---|
| Sem token | `GET /api/v1/campaigns/` | **401** | 401 | ✅ |
| Campanha inexistente | `GET /api/v1/campaigns/00000000-…/` | **404** | 404 | ✅ |
| Campo obrigatório em falta (`title` e `report_type`) | `POST /api/v1/reports/` | **400** | 400/422 | ✅ |
| Erros por campo | Resposta 400 incluiu `{"title": [...], "report_type": [...]}` | — | field-level | ✅ |

---

### Greps de segurança

| Verificação | Resultado |
|---|---|
| `X-Internal-Token` em `src/` | ✅ Apenas em `client.ts` (guard) e doc em `campaign-action-api.ts` |
| `INTERNAL_API_TOKEN` em `src/` | ✅ Não encontrado |
| `intelligence_engine` / `content_renderer` em `src/` | ✅ Não encontrado |
| `localhost:800[1-9]` / portas internas em `src/` | ✅ Não encontrado |
| Secrets em `.env.local` | ✅ Apenas `VITE_BACKEND_API_BASE_URL` |
| Secrets em `.env.example` | ✅ Apenas `VITE_BACKEND_API_BASE_URL` com nota de segurança |

---

### Validações de build

| Validação | Resultado |
|---|---|
| `pnpm lint` (`eslint .`) | ✅ **Exit 0 — sem erros** |
| `pnpm build` (`tsc -b && vite build`) | ✅ **230 módulos, 3.01s, exit 0** |
| `python manage.py check` | ✅ **0 issues (0 silenced)** — nenhum código backend alterado |

---

### Limitações desta validação

| Limitação | Causa | Impacto |
|---|---|---|
| Validação UI visual não executada (War Room no browser) | Chrome extension não conectado | A UI não foi navegada visualmente; todos os contratos de API foram validados via HTTP directo |
| Intelligence em dry-run | `INTELLIGENCE_ENGINE_DRY_RUN=true` no `.env` — IE não está a correr | `result.recommendations` é `[]`; sem affordances de acção visíveis no browser (mas os endpoints de criação funcionam) |
| HTTPS warnings em `manage.py check --deploy` | Ambiente local, DEBUG=True | Esperado e ignorado para dev local |

---

### Ficheiros criados ou alterados

**Criado:**
- `resultados_execucao/prompt_11_validacao_real_ca014_resultado.md` (este ficheiro).

**Nenhum ficheiro de código runtime foi alterado.** Foram criados dados dev no SQLite local
(utilizador, workspace, artista, campanha, relatório, media kit, content pack request) — todos
dados de desenvolvimento local sem impacto em produção.

---

### Validações executadas e resultado

- ✅ Portas 8000 e 5173 confirmadas livres antes de arrancar.
- ✅ Django Backend Core confirmado real em `:8000` (schema/admin 200, root 404).
- ✅ Vite dev server confirmado em `:5173` (HTTP 200).
- ✅ `.env.local` correcto e gitignored.
- ✅ `POST /api/v1/auth/token/` → 200 (login real).
- ✅ `GET /api/v1/auth/me/` → 200.
- ✅ `GET /api/v1/workspaces/` → 200, 1 workspace.
- ✅ `GET /api/v1/campaigns/{id}/` → 200.
- ✅ `POST /api/v1/campaigns/{id}/intelligence/` → 200 (dry-run; structure correcta).
- ✅ `POST /api/v1/reports/` → 201 com `recommendation_ref` em metadata.
- ✅ `POST /api/v1/media-kits/` (com `campaign`) → 201 com `recommendation_ref`.
- ✅ `POST /api/v1/content-pack-requests/` → 201 com `recommendation_ref`.
- ✅ `GET /content-pack-requests/?campaign=<id>` → 200, `recommendation_ref` recuperável.
- ✅ `GET /reports/?campaign=<id>` → 200, `recommendation_ref` recuperável.
- ✅ `GET /media-kits/?campaign=<id>` → 200, `recommendation_ref` recuperável.
- ✅ Erros 401, 404, 400 correctos.
- ✅ Greps de segurança limpos.
- ✅ `pnpm lint` → exit 0.
- ✅ `pnpm build` → 230 módulos, exit 0.
- ⚠️ Validação UI visual (browser) — pendente por Chrome extension não conectado.
- ⚠️ Recommendations reais — não disponíveis (dry-run por design).

---

### Pendências, riscos e próximo passo recomendado

- **Validação UI visual**: para completar CA-014 a 100%, é necessário navegar no browser
  `localhost:5173`, fazer login com `ca014-dev@example.local`, abrir a War Room, confirmar
  render de recommendations (requer IE real ou dados mockados via fixture), e confirmar
  os botões de acção. Com os dados actuais (dry-run), a War Room mostraria recommendations
  vazia — o fluxo de botão de acção não seria exercitável visualmente.
- **IE real**: para validação visual completa, o Intelligence Engine deve estar a correr
  em `:8001` com `INTELLIGENCE_ENGINE_DRY_RUN=false`, ou devem ser criadas fixtures de
  recommendations reais na sessão de intelligence.
- **CA-PDEC-006**: backlog backend complementar para entidade `CampaignAction` persistente
  continua recomendado para traceabilidade firme.
