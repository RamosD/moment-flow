# BC-IE-001 — Análise, contrato e plano de integração Backend Core ↔ Intelligence Engine

> **Tipo:** relatório de análise (não altera runtime).
> **Fase:** `integracao_intelligence_engine` — tarefa **BC-IE-001**.
> **Data:** 2026-06-25.
> **Âmbito:** apenas inspecção do `backend_core`, do contrato do `intelligence_engine`
> e dos padrões internos de integração. **Nenhum ficheiro de runtime foi alterado.**
> O único ficheiro criado é este relatório (e a pasta `resultados/`).

---

## 0. Sumário executivo

- A infra-estrutura de integração interna **já existe e é madura** em
  `apps/integrations_bridge` (`InternalServiceClient`, `registry`, logging
  token-free, excepções tipadas, testes com transporte injectável). O caminho
  síncrono do MVP **reutiliza** essa camada — não precisa de novas dependências.
- O scaffolding actual da bridge para o Intelligence Engine é **assíncrono**
  (`ExternalJobReference` + `POST /jobs/` + callback) e **não corresponde** ao IE
  MVP, que é **síncrono** (endpoints nomeados, resposta inline). Esta é a
  divergência central (BC-IE-RSK-001 / INT-RSK-01). **Decisão confirmada: usar o
  caminho síncrono, isolado, sem `ExternalJobReference` e sem `/jobs/`.**
- **Settings:** `INTELLIGENCE_ENGINE_BASE_URL` e
  `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` **já existem**. O token é o partilhado
  `INTERNAL_API_TOKEN` (também já existe) — **reutilizar**, **não** criar
  `INTELLIGENCE_ENGINE_INTERNAL_TOKEN`. Faltam `INTELLIGENCE_ENGINE_ENABLED` e
  `INTELLIGENCE_ENGINE_DRY_RUN` (os switches globais `EXTERNAL_JOBS_*` governam o
  caminho **assíncrono** e não devem ser reaproveitados para o síncrono).
- **Endpoint recomendado:** `@action` em `CampaignViewSet` →
  `POST /api/v1/campaigns/{id}/intelligence/`, herdando autenticação, workspace e
  RBAC do `WorkspaceScopedRBACViewSet` já existente.
- **Persistência:** confirmado **não persistir snapshots** no MVP.
- Há uma **discrepância de contrato** a resolver no builder: o backlog §7.3 chama
  ao campo `reports`, mas o **contrato §7.1 (autoritativo) lê `previous_reports`**.
  O builder deve emitir `previous_reports`.

---

## 1. Contexto consultado

### 1.1 Documentos
- Backlog desta fase: [`01_backlog.md`](../01_backlog.md) — lido na íntegra.
- Prompts desta fase: [`02_prompts_integracao_intell_engine.md`](../02_prompts_integracao_intell_engine.md) — presente.
- **Contrato (autoritativo):**
  `intelligence_engine/docs/gestao/fundamentos/contrato_backend_core_intelligence_engine.md`
  — lido na íntegra (endpoints, auth, headers, payload, respostas, erros,
  timeout/retry, decisão síncrono vs job, persistência, exemplos, riscos).

> **Nota sobre caminhos:** o backlog (§5) aponta para
> `docs/gestao/fundamentos/...`, mas a localização real desta fase é
> `docs/backend_core/fundamentos/integracao_intelligence_engine/...`. Este
> relatório segue a localização real (a pasta de resultados pedida no prompt).

### 1.2 Backend Core — ficheiros inspeccionados
- Config: [`config/settings.py`](../../../../../config/settings.py), [`config/urls.py`](../../../../../config/urls.py), `.env.example`.
- Bridge: `apps/integrations_bridge/` — `clients.py`, `registry.py`, `services.py`,
  `intelligence.py`, `logging_utils.py`, `tests/test_settings_client_registry.py`.
- Campaigns: `apps/campaigns/` — `models.py`, `views.py`, `urls.py`, `services.py`,
  `serializers.py` (parcial), `tests/conftest.py`.
- RBAC / workspaces: `apps/rbac/viewsets.py`, `apps/rbac/permissions.py`,
  `apps/rbac/seeds.py`, `apps/workspaces/permissions.py`.
- Modelos de dados-fonte: `apps/catalogue/models.py` (Artist, Track,
  TrackPlatformLink), `apps/links/models.py` (SmartLink, SmartLinkClick),
  `apps/content/models.py` (ContentOutput), `apps/reports/models.py` (Report,
  MediaKit), `apps/core/models.py` (BaseModel/UUID).

---

## 2. Estado da infra-estrutura existente (o que é reutilizável)

### 2.1 `InternalServiceClient` (`apps/integrations_bridge/clients.py`)
Cliente JSON-sobre-HTTP em `urllib` (sem dependências novas). Já cumpre quase
tudo o que o BC-IE-003 pede:
- `post_json(path, payload, *, workspace_id, job_id, request_id)` → devolve
  `InternalResponse(status_code, data)` em 2xx com corpo JSON.
- Headers internos automáticos: `X-Internal-Token`, `X-Workspace-ID`, `X-Job-ID`,
  `X-Request-ID`, `Content-Type` (`build_headers`, `clients.py:86`).
- **Nunca regista o token** (logs só com ids/status — `clients.py:110-156`).
- Excepções tipadas: `InternalClientTimeout`, `InternalServiceUnavailable`,
  `InternalHTTPError` (com `status_code` e `body`), `InvalidJSONResponse`.
- Transporte injectável (`opener`) → testes sem HTTP real (já provado em
  `tests/test_settings_client_registry.py`).

**Reuso no síncrono:** chamar
`post_json("/intelligence/campaign", envelope, workspace_id=ws_id, job_id=None, request_id=req_id)`.
`job_id=None` → header `X-Job-ID` vazio, o que é aceitável (contrato §6:
`X-Job-ID` é opcional e ignorado no síncrono).

**Lacuna a cobrir:** o cliente base só devolve corpo em 2xx; um `422`/`403`/`5xx`
do IE chega como `InternalHTTPError`. É preciso uma camada fina por cima que
**normalize o envelope de resposta do IE** (sucesso: `status/result/explanations/
warnings`; erro: `error.code` no corpo) — ver §6 (BC-IE-003).

### 2.2 `registry.py`
Resolve `provider → (base_url, timeout)` a partir de settings, com leitura
**lazy** (respeita overrides de settings em testes). Já conhece o IE
(`INTELLIGENCE_ENGINE_BASE_URL/TIMEOUT_SECONDS`, `registry.py:69-72`). Os
mapeamentos `job_type → provider` e os switches `external_jobs_*` servem o
**caminho assíncrono** — não devem ser usados pelo síncrono.

### 2.3 `services.py` + `intelligence.py` (scaffolding **assíncrono**)
`create_and_submit_external_job` faz `POST /jobs/` com envelope de job
(`SUBMIT_PATH = "/jobs/"`, `services.py:34`) e espera callback. Os builders em
`intelligence.py` (`build_metrics_collection_payload`, etc.) produzem um shape
`{workspace_id, campaign_id, track_id, platform_links, *_context}` **diferente**
do `data` bundle do IE MVP. **Não reutilizar para o síncrono** (ver risco §9.1).

### 2.4 Logging token-free (`logging_utils.py`)
`log_job_event` emite uma linha `key=value` com ids/status e **dropa chaves
proibidas** (`token`, `secret`, …). Bom padrão a seguir nos logs do caminho
síncrono (campos: `request_id`, `workspace_id`, `campaign_id`, `status`,
`duration_ms`, `error_type`), conforme backlog §15.4.

### 2.5 Base RBAC/workspace (reutilização directa para o endpoint)
- `WorkspaceScopedRBACViewSet` (`apps/rbac/viewsets.py`): resolve workspace de
  `X-Workspace-ID`, **scopa o queryset ao workspace** e exige permissões por
  acção via `required_permissions[action]`.
- `HasWorkspacePermission` (`apps/rbac/permissions.py:34`): membership activo +
  todas as permissões declaradas.
- `resolve_active_workspace` (`apps/workspaces/permissions.py:18`): 400 se header
  ausente/inválido; 403 se não-membro (não distingue inexistência — não vaza).
- Permissões de campanha já seeded: `campaigns:view/create/update/delete`
  (`apps/rbac/seeds.py:25-28`).
- PK de todas as entidades é **UUID** (`apps/core/models.py:84`) → serialização
  exige `str(uuid)`.

---

## 3. Confirmação das settings (pré-check do BC-IE-002)

| Variável esperada (backlog §BC-IE-002) | Estado actual | Acção recomendada |
|---|---|---|
| `INTELLIGENCE_ENGINE_BASE_URL` | **Existe** (`settings.py:279`, default `http://localhost:8001`) | Reutilizar |
| `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` | **Existe** (`settings.py:282`, default `20`) | Reutilizar; rever default para 5–10 s (contrato §9.1) — configurável |
| `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` | **Não existe**; há `INTERNAL_API_TOKEN` partilhado (`settings.py:266`) | **Não criar.** Reutilizar `INTERNAL_API_TOKEN` (contrato §5: mesmo segredo nos dois serviços; o `InternalServiceClient` já o usa por omissão) |
| `INTELLIGENCE_ENGINE_ENABLED` | **Não existe**; só há `EXTERNAL_JOBS_ENABLED` (async) | **Criar** switch dedicado ao síncrono (default `True`) |
| `INTELLIGENCE_ENGINE_DRY_RUN` | **Não existe**; só há `EXTERNAL_JOBS_DRY_RUN` (async) | **Criar** switch dedicado ao síncrono (default `False`) |

**Justificação para switches dedicados:** os `EXTERNAL_JOBS_*` controlam a
submissão de jobs assíncronos (`/jobs/`); reaproveitá-los acoplaria o caminho
síncrono ao assíncrono e impediria, por exemplo, desligar o IE síncrono sem
afectar o renderer. Mantê-los separados respeita o isolamento exigido por
BC-IE-RSK-001.

**Segurança já garantida:** `INTERNAL_API_TOKEN` default `""`; o cliente nunca o
regista; `.env.example` tem placeholder vazio. Falta apenas (BC-IE-002) garantir
que **produção não arranca/avança com token vazio quando o IE está activo**
(`INTELLIGENCE_ENGINE_ENABLED=True` + `DRY_RUN=False` + token vazio → erro de
configuração claro).

---

## 4. Decisão técnica confirmada para o MVP

| Decisão | Confirmação | Fonte |
|---|---|---|
| Chamada **síncrona** a `POST /intelligence/campaign` | **Confirmada** | Backlog §6.1, contrato §3/§10, decisão IE-PDEC-001 |
| **Não** usar `ExternalJobReference` | **Confirmada** | Backlog §4.2/§6.4, contrato §3 (nota), PDEC-003 |
| **Não** implementar callbacks | **Confirmada** | Backlog §4.2 |
| **Não** persistir snapshots | **Confirmada** | Backlog §8.1, contrato §11, PDEC-002 |
| **Não** alterar o `intelligence_engine` | **Confirmada** | Backlog §4.2/§11 |
| **Não** chamar o renderer a partir do builder/IE | **Confirmada** | Backlog §11/§15.2 |

> **Sem divergência face ao prompt.** O código existente confirma a viabilidade
> do caminho síncrono (transporte reutilizável) e o scaffolding assíncrono fica
> reservado para trabalho pesado futuro (ex.: `metrics_collection`).

---

## 5. Discrepâncias / divergências encontradas (a tratar nas próximas tarefas)

1. **`reports` vs `previous_reports`** — backlog §7.3 (payload base) usa
   `"reports": []`; o contrato §7.1 (o que o IE **lê**) usa `"previous_reports"`.
   → O builder deve emitir **`previous_reports`** (contrato é autoritativo). O
   `data` do IE é permissivo (`extra="allow"`), mas só `previous_reports` é lido.
2. **Sync vs async scaffolding** — `integrations_bridge/intelligence.py` e os
   `job_type` da `registry` assumem `/jobs/`+callback; o IE MVP não implementa
   `/jobs/` nem esses job types. → Caminho síncrono **novo e isolado**.
3. **Switches** — globais `EXTERNAL_JOBS_*` ≠ switches do IE síncrono. → criar
   `INTELLIGENCE_ENGINE_ENABLED/DRY_RUN` dedicados.
4. **Token** — backlog sugere `INTELLIGENCE_ENGINE_INTERNAL_TOKEN`; o projecto já
   usa `INTERNAL_API_TOKEN` partilhado. → reutilizar (não duplicar segredo).
5. **Caminhos de docs** — backlog aponta `docs/gestao/...`; a fase vive em
   `docs/backend_core/fundamentos/integracao_intelligence_engine/...`. → usar a
   localização real nos relatórios/estado finais (BC-IE-010).
6. **`metadata.generated_at` é `null` por desenho** no IE (determinismo) — o
   timestamp é responsabilidade do Backend Core (contrato §8.1). → o serviço/
   endpoint deve carimbar `generated_at` do lado Django ao devolver/loggar.

---

## 6. Arquitectura proposta da integração síncrona (camadas e localização)

Proposta **híbrida** (respeita a fronteira arquitectural: bridge = transporte/
contrato de provider; campaigns = dados do domínio + orquestração):

```text
CampaignViewSet.intelligence (action)            [apps/campaigns/views.py]
  → CampaignIntelligenceService                  [apps/campaigns/ — orquestração]
      → CampaignIntelligencePayloadBuilder       [apps/campaigns/ — monta data bundle]
      → IntelligenceEngineSyncClient             [apps/integrations_bridge/ — provider]
          → InternalServiceClient.post_json      [apps/integrations_bridge/clients.py (reuso)]
              → POST {BASE_URL}/intelligence/campaign
```

- **Transporte genérico:** reutiliza `InternalServiceClient` tal como está.
- **Wrapper de provider (novo, na bridge):** `IntelligenceEngineSyncClient`
  conhece o endpoint nomeado, aplica timeout do registry/settings e **normaliza
  o envelope de resposta do IE** (sucesso vs `error.code`), traduzindo
  `InternalHTTPError(422/403/5xx)`/timeout/unavailable/invalid-json em
  resultados/erros tipados do lado Django.
- **Builder (novo, em campaigns):** o domínio sabe montar o seu próprio `data`
  bundle a partir dos modelos reais.
- **Serviço de domínio (novo/estendido, em campaigns):** valida workspace, trata
  `ENABLED`/`DRY_RUN`, chama o wrapper, mapeia a resposta e degrada com elegância.

> **Alternativa aceitável (Opção A):** concentrar builder + serviço também na
> `integrations_bridge` (há precedente: `intelligence.py` já lê
> `apps.catalogue.models` de forma lazy). A escolha final é uma **decisão
> pendente** (ver §10, PD-2). A recomendação é a híbrida acima.

### 6.1 Mapeamento do `data` bundle (modelo Django → contrato §7.1)

| Campo bundle (contrato §7.1) | Origem no Backend Core | Notas |
|---|---|---|
| `campaign` | `Campaign` (`apps/campaigns/models.py`) | `id, name, campaign_type, status, start_date, end_date, primary_goal` |
| `artist` | `Campaign.artist` → `Artist` (`apps/catalogue`) | `id, name, primary_genre, status`; usar `select_related("artist")` |
| `track` | `Campaign.track` → `Track` (`apps/catalogue`) | `id, title, release_date, track_type, status`; pode ser `None` |
| `smart_link_stats` | `SmartLink` + `SmartLinkClick` (`apps/links`) | `total_clicks`, `clicks_last_7_days`, `clicks_last_30_days`, `active_links`; **agregar** (ver §9.4) |
| `content_outputs` | `ContentOutput` (`apps/content`) filtrado por campaign | `id, output_type, status, created_at` |
| `previous_reports` | `Report` (`apps/reports`) filtrado por campaign | `id, report_type, status, period_end` (**nome `previous_reports`**, ver §5.1) |
| `media_kits` | `MediaKit` (`apps/reports`) filtrado por campaign | `id, status` |
| `goals` | `CampaignGoal` (`apps/campaigns`) | `goal_type, status, target_value, current_value, deadline` |

Envelope (contrato §7): `payload_version="1.0"`, `workspace_id=str(ws.id)`,
`request_id=uuid4().hex`, `entity={"type":"campaign","id":str(campaign.id)}`,
`context={"reference_date": <hoje ou data passada>.isoformat()}` (**enviar
sempre**, contrato §7/INT-RSK-03). Serialização JSON-safe: datas→ISO, UUID→str,
Decimal→float/str, enums→`.value`.

---

## 7. Ficheiros prováveis a alterar / criar (mapeados ao backlog)

| Tarefa | Ficheiro | Acção |
|---|---|---|
| BC-IE-002 | `config/settings.py` | **Editar:** add `INTELLIGENCE_ENGINE_ENABLED`, `INTELLIGENCE_ENGINE_DRY_RUN`; documentar reuso de `INTERNAL_API_TOKEN`; rever default de timeout; check de produção (token vazio) |
| BC-IE-002 | `.env.example` | **Editar:** add os 2 switches + nota de reuso do token |
| BC-IE-002 | `apps/integrations_bridge/tests/test_settings_client_registry.py` (ou novo) | **Editar/Criar:** asserts das novas settings |
| BC-IE-003 | `apps/integrations_bridge/intelligence_sync.py` | **Criar:** `IntelligenceEngineSyncClient` + normalização de envelope + erros tipados |
| BC-IE-003 | `apps/integrations_bridge/tests/test_intelligence_sync.py` | **Criar:** mocks HTTP (sucesso, 403, 422, 5xx, timeout, JSON inválido, token não logado) |
| BC-IE-004 | `apps/campaigns/intelligence_payload.py` (ou `services.py`) | **Criar:** `CampaignIntelligencePayloadBuilder` |
| BC-IE-004 | `apps/campaigns/tests/test_intelligence_payload.py` | **Criar:** campanha rica / mínima / sem relacionados |
| BC-IE-005 | `apps/campaigns/services.py` (ou `intelligence_service.py`) | **Criar/Editar:** `CampaignIntelligenceService` (orquestração, dry-run, disabled, degradação) |
| BC-IE-005 | `apps/campaigns/tests/test_intelligence_service.py` | **Criar:** client mockado, timeout/5xx, workspace mismatch |
| BC-IE-006 | `apps/campaigns/views.py` | **Editar:** `@action(detail=True, methods=["post"], url_path="intelligence")` + entrada `"intelligence"` em `required_permissions` |
| BC-IE-006 | `apps/campaigns/serializers.py` | **Editar (opcional):** serializer de resposta para OpenAPI |
| BC-IE-006 | `apps/campaigns/tests/test_intelligence_api.py` | **Criar:** auth, RBAC, cross-workspace, sucesso, erros |
| BC-IE-008 | (testes acima) | Cobertura de integração com mocks |
| BC-IE-010 | `docs/.../estado_integracao_intelligence_engine.md` + `resultados/prompt_final_*.md`; `README.md` | **Criar/Editar:** estado final |

> **Não** se prevê tocar em `clients.py`, `registry.py`, `services.py` nem
> `intelligence.py` da bridge (caminho assíncrono permanece intacto). Se o
> `registry` ganhar um helper de resolução do IE síncrono, será aditivo e
> opcional.

---

## 8. Endpoint, RBAC e workspace (detalhe do BC-IE-006)

- **Rota:** `POST /api/v1/campaigns/{id}/intelligence/` via `@action` na
  `CampaignViewSet` (padrão já usado em `content/views.py:175`,
  `links/views.py:99`). `POST` recomendado (BC-IE-PDEC-001: cálculo remoto, pode
  aceitar contexto, não cacheável).
- **Auth/Workspace/Scoping:** herdados do `WorkspaceScopedRBACViewSet`.
  `self.get_object()` usa o queryset já filtrado por workspace → **404 para
  campanha de outro workspace** (não vaza existência) e workspace garantido.
- **RBAC:** adicionar `"intelligence": ["campaigns:view"]` ao
  `required_permissions`. **Recomendação MVP:** reutilizar `campaigns:view`
  (intelligence é enriquecimento de leitura; sem alteração de seeds/roles). A
  criação de uma permissão dedicada `campaigns:intelligence` fica como decisão
  futura (exigiria `seeds.py` + re-seed).
- **Resposta normalizada:** `{ status, result:{analysis,scores,grade,moments,
  recommendations,summary}, explanations, warnings, metadata, generated_at }`,
  com `generated_at` carimbado pelo Django.

---

## 9. Riscos identificados

### 9.1 Divergência sync/async (BC-IE-RSK-001) — **Alto**
O scaffolding da bridge é `/jobs/`+callback; o IE MVP é síncrono. **Mitigação:**
caminho síncrono novo e isolado; não importar `create_and_submit_external_job`,
`ExternalJobReference` nem `SUBMIT_PATH`; switches dedicados.

### 9.2 RBAC / workspace (BC-IE-RSK-003) — **Crítico**
Expor intelligence sem validar workspace/permissão é critério de **não
aceitação** (backlog §11). **Mitigação:** herdar `WorkspaceScopedRBACViewSet`
(scoping no queryset + `get_object()`), declarar `required_permissions`, e
**testar** acesso negado (sem permissão) e cross-workspace (404).

### 9.3 Payload incompatível / contrato (BC-IE-RSK-002, INT-RSK-02/05) — **Alto**
Builder pode montar shape errado (ex.: `reports` em vez de `previous_reports`).
**Mitigação:** fixtures de contrato; `payload_version="1.0"`; testes de
campanha rica/mínima/vazia; alinhar nomes ao contrato §7.1.

### 9.4 N+1 e custo de agregação de cliques (BC-IE-RSK-006) — **Médio**
`smart_link_stats` agrega `SmartLinkClick` por janelas temporais. **Mitigação:**
`select_related("artist","track")`; `prefetch_related` para outputs/reports/
media_kits/goals; usar `.aggregate()`/`.count()` com filtros por data
(`clicked_at >= reference_date - 7d/30d`); `active_links` = `SmartLink` com
`status="active"` por campanha (`links/models.py:22`). Evitar iterar QuerySets.

### 9.5 Timeout / UX (BC-IE-RSK-004, INT-RSK-06) — **Médio/Alto**
Timeout do IE não pode causar 500 não controlado nem bloquear UX. **Mitigação:**
`INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` curto (5–10 s); tratar
`InternalClientTimeout`/`InternalServiceUnavailable` com erro controlado
(ex.: 503/504) ou degradação graciosa (insight é enriquecimento, não
bloqueante). Retry: **não** em 4xx; no máximo 1 retry curto em timeout/5xx
(decisão pendente PD-4).

### 9.6 Vazamento de detalhes internos / token (BC-IE-RSK-005, backlog §11) — **Médio/Crítico**
Token em logs ou stack trace em resposta = não aceitação. **Mitigação:** o
`InternalServiceClient` já não regista token; **não logar** corpos/headers;
mapear `InternalHTTPError`/`InvalidJSONResponse` para mensagens seguras; logs só
com `request_id`/`workspace_id`/`campaign_id`/`status`/`duration_ms`/`error_type`.

### 9.7 Heurísticas não calibradas parecerem definitivas (BC-IE-RSK-008) — **Médio**
**Mitigação:** propagar `explanations`/`warnings` do IE para o consumidor; evitar
linguagem absoluta na camada de apresentação.

### 9.8 Testes — **Médio**
Critério de aceitação exige testes unitários + API + mock HTTP a passar.
**Mitigação:** reutilizar `opener_returning`/`opener_raising`
(`test_settings_client_registry.py`) e as fixtures de
`campaigns/tests/conftest.py` (`workspace`, `owner`, `add_member`, `client_for`,
`ws_header`); cobrir completed/warnings/recommendations/moments/scores=unknown/
timeout/403/422/5xx/JSON inválido; assert token não logado (`caplog`) e
`request_id`/`workspace_id` propagados.

---

## 10. Decisões pendentes

| ID | Questão | Recomendação |
|---|---|---|
| PD-1 | Adoptar caminho síncrono (vs manter jobs async) | **Síncrono** (confirmado em §4) |
| PD-2 | Onde vive o builder/serviço (`integrations_bridge` vs `apps.campaigns`) | **Híbrido**: wrapper de provider na bridge; builder+serviço em campaigns (§6) |
| PD-3 | Permissão do endpoint: reutilizar `campaigns:view` ou criar `campaigns:intelligence` | **MVP: `campaigns:view`**; dedicada fica para futuro |
| PD-4 | Política de retry no request HTTP | **MVP:** sem retry automático ou 1 retry curto em timeout/5xx; nunca em 4xx |
| PD-5 | Default de `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` (actual 20 vs contrato 5–10) | Baixar para ~10 s; manter configurável |
| PD-6 | `context.reference_date`: sempre "hoje" vs parâmetro do request | **MVP:** "hoje" (UTC), com possibilidade de override por body |
| PD-7 | Persistir snapshot | **Não no MVP** (confirmado); modelo `CampaignIntelligenceSnapshot` fica para futuro |

---

## 11. Dependências e lacunas

- **Token partilhado alinhado** entre os dois serviços (`INTERNAL_API_TOKEN` no
  Django ≡ `INTERNAL_API_TOKEN` no IE) — necessário para o loop real (BC-IE-009).
- **IE a correr** em `INTELLIGENCE_ENGINE_BASE_URL` para validação real
  (BC-IE-009); até lá, `DRY_RUN`/mocks cobrem os testes.
- **Agregação de cliques** assume que `SmartLinkClick.clicked_at` e a ligação a
  `campaign` existem — **confirmado** (`apps/links/models.py:128,140`).
- **`MediaKit`/`Report` vivem em `apps/reports`** (não num app `media_kits`
  separado) — confirmado; o builder importa de `apps.reports.models`.
- **Lacuna de observabilidade** (logs estruturados do caminho síncrono) — não
  bloqueia o MVP, mas deve existir o mínimo (backlog §15.4).
- **Lacuna de produção** — check de configuração insegura (token vazio com IE
  activo) ainda por implementar (BC-IE-002).

---

## 12. Sequência de implementação objectiva (próximos prompts)

1. **BC-IE-002 — Settings.** Add `INTELLIGENCE_ENGINE_ENABLED`/`DRY_RUN`;
   reutilizar `INTERNAL_API_TOKEN`; rever default de timeout; check de produção;
   `.env.example`; testes de config.
2. **BC-IE-003 — Client síncrono.** `IntelligenceEngineSyncClient` (na bridge)
   sobre `InternalServiceClient`; normalizar envelope; erros tipados; mocks HTTP.
3. **BC-IE-004 — Builder.** `CampaignIntelligencePayloadBuilder` (em campaigns);
   mapeamento §6.1; JSON-safe; sem N+1; testes rica/mínima/vazia.
4. **BC-IE-005 — Serviço de domínio.** `CampaignIntelligenceService`; dry-run/
   disabled/timeout/degradação; mapear resposta; sem snapshot; testes mockados.
5. **BC-IE-006 — Endpoint.** `@action` em `CampaignViewSet`; RBAC `campaigns:view`;
   workspace via `get_object()`; serializer de resposta; OpenAPI; testes API.
6. **BC-IE-007 — Timeout/retry/fallback.** Consolidar política (§9.5); logs
   estruturados token-free; testes 403/422/5xx/timeout.
7. **BC-IE-008 — Mocks HTTP.** Cobertura completa de cenários (§9.8).
8. **BC-IE-009 — Loop real.** IE+BC a correr; token alinhado; evidências; IE
   desligado → erro controlado.
9. **BC-IE-010 — Documentação final.** Estado honesto + relatório final
   (localização real de docs, §5.5).

---

## 13. Próximo passo recomendado

Avançar para **BC-IE-002** (settings): adicionar `INTELLIGENCE_ENGINE_ENABLED` e
`INTELLIGENCE_ENGINE_DRY_RUN`, documentar a reutilização de `INTERNAL_API_TOKEN`
(sem criar `INTELLIGENCE_ENGINE_INTERNAL_TOKEN`), rever o default de timeout para
5–10 s, e adicionar o check que impede produção com token vazio quando o IE está
activo — actualizando `.env.example` e os testes de configuração. É a base mínima
e de baixo risco para todo o resto do caminho síncrono.

---

## 14. Conformidade com os critérios de aceitação do BC-IE-001

- [x] Plano técnico claro e executável (§6, §7, §12).
- [x] Ficheiros/módulos prováveis a alterar identificados (§7).
- [x] Decisão síncrona para o MVP confirmada; divergências registadas (§4, §5).
- [x] Riscos de RBAC, workspace, payload, timeout, logging e testes (§9).
- [x] Nenhum ficheiro de runtime alterado (apenas este relatório + pasta `resultados/`).
- [x] Relatório lista contexto, decisões, riscos, plano, pendências e próximo passo.
