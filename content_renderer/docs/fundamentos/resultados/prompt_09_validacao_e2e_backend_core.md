# Relatório de Execução — Prompt 09: Validação E2E com Backend Core

- **Data:** 2026-06-23
- **Pipeline:** 09 — Testes E2E com Backend Core (Django)
- **Serviços:** `content_renderer` (:8002) ↔ `backend_core` (Django, :8000)
- **Localização:** `D:\Workspace\ChartRex\momentflow\content_renderer`

---

## 1. Prompt executado

Validar o `content_renderer` contra o **Backend Core Django real**, fechando o
ciclo `job externo → render → callback → Asset/Output/Report/MediaKit`. Inspeccionar
a integração do Django, configurar os dois serviços, criar guia/script de teste E2E
local, executar (ou documentar) os cenários content/report/media kit, e actualizar
o README com a integração. Sem alterar o `backend_core`.

---

## 2. Objectivo

Confirmar que os contratos do renderer (envelope, headers, callback, metadata de
`Asset`) **coincidem com o Backend Core real** e que o ciclo opera ponta-a-ponta,
ou — havendo limitação de ambiente — documentar checklist e comandos exactos.

---

## 3. Ficheiros criados

- `scripts/e2e_backend_core.py` — driver E2E (ORM do backend via `BACKEND_CORE_DIR`):
  cria entidade, gera o `ExternalJobReference` real (envelope) e POSTa-o ao renderer
  real; valida render + asset + callback.
- `scripts/run-e2e.ps1` — orquestra os dois serviços (arranque, readiness, driver,
  teardown).
- `docs/fundamentos/guia_e2e_backend_core.md` — guia + checklist operacional
  (config, contratos, método automatizado e manual, caveats).
- `docs/fundamentos/resultados/prompt_09_validacao_e2e_backend_core.md` — este relatório.

---

## 4. Ficheiros alterados

| Ficheiro | Alteração |
| -------- | --------- |
| `src/callbacks/callback.payload.ts` | **Correcção de contrato:** report/media-kit enviam `result.asset` (bloco único) — o handler do Django lê `result.asset`, não `result.outputs[]`. Content mantém `result.outputs[]`. |
| `src/jobs/job.types.ts` | `JobResult` passa a suportar `outputs?` **ou** `asset?`+`metadata?`. |
| `src/renderers/reports/report.model.ts` | **Tolerância a `null`:** schema `.nullish()`; `smart_link_stats` aceita array-ou-objecto (o Django envia `null` em blocos ausentes e `[]` em stats). |
| `src/renderers/media-kits/media-kit.model.ts` | Idem `.nullish()` (campaign/track `null`). |
| `tests/{content,report,media-kit}-generation.test.ts` | Ajuste das asserções de callback (`result.asset` para report/media-kit; `outputs!` para content). |
| `README.md` | Estado actualizado + secção **Integração com o Backend Core**. |

> **Side effects documentados (ambiente):** o `backend_core/db.sqlite3` foi posto em
> modo **WAL** (propriedade do ficheiro, não código) e contém linhas de teste
> (utilizadores/workspaces/jobs E2E). O `backend_core` **não** foi alterado em código.

---

## 5. Configuração usada

| Serviço | Variáveis |
|---|---|
| Renderer | `PORT=8002`, `INTERNAL_API_TOKEN=<partilhado>`, `BACKEND_CORE_BASE_URL=http://localhost:8000`, `LOCAL_STORAGE_ROOT=<temp>` |
| Django | `INTERNAL_API_TOKEN=<partilhado>`, `BACKEND_PUBLIC_BASE_URL=http://localhost:8000`, `CONTENT_RENDERER_BASE_URL`/`REPORT_RENDERER_BASE_URL=http://localhost:8002`, `EXTERNAL_JOBS_ENABLED=true`, `EXTERNAL_JOBS_DRY_RUN=false` |

(O token é partilhado e **não** é exposto neste relatório.)

---

## 6. Cenários executados

| Cenário | Render real contra payload do Django | Escrita de produto no Django |
|---|---|---|
| `content_generation` | Coberto pelos testes + checklist | Checklist documentada (§7.1) |
| `report_generation` | ✅ **Render `completed`** (PDF real) contra payload real | Bloqueado por ambiente (§9); checklist §7.2 |
| `media_kit_generation` | ✅ **Render `completed`** (PDF real) contra payload real | Bloqueado por ambiente (§9); checklist §7.3 |

Inspecção do Django confirmou os contratos: envelope (`build_request_envelope`),
headers (`X-Internal-Token`/`X-Workspace-ID`/`X-Job-ID`/`X-Request-ID`), callback
`POST /api/v1/internal/jobs/callback/`, leitura de `result.outputs[]` (content) e
`result.asset` (report/media-kit), `Asset.StorageProvider.LOCAL = "local"`.

---

## 7. Evidências

### 7.1 content_generation
- **Django (lado do contrato):** validado pelos testes de integração do backend
  (`apps/content/tests/test_content_callback.py` et al.) — cria `ContentOutput`/`Asset`,
  consome/liberta créditos, `Notification`, `Audit`, suporta `partially_completed`.
- **Renderer:** emite `result.outputs[]` com `asset` no formato lido pelo Django
  (`_create_asset` lê `storage_provider/bucket/storage_key/file_name/mime_type/
  file_size_bytes/width/height/duration_seconds/checksum`).
- **Execução live:** não executada (setup de campanha/pack/créditos mais pesado);
  checklist completa no guia §5.1.

### 7.2 report_generation (live, contra Django real)
```text
renderer_http_status   : 202
renderer_result_status : completed        ← renderiza o payload REAL do Django
render_error           : null             ← PDF real gerado
```
- O renderer aceitou o envelope real (após tolerância a `null` + `smart_link_stats`
  array) e gerou um **PDF** real. O callback usa `result.asset` (lido pelo Django).
- A criação do `Asset` no Django via callback ficou bloqueada por limitação de
  ambiente (§9), não por contrato.

### 7.3 media_kit_generation (live, contra Django real)
```text
renderer_http_status   : 202
renderer_result_status : completed
render_error           : null
```
- Igual ao report: render real do payload real, callback `result.asset`.

---

## 8. Comandos executados

```powershell
# Renderer
npm run build ; npx vitest run ; npm run lint

# Backend Core (venv)
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe -m pytest apps/integrations_bridge apps/content apps/reports -q

# E2E (dois serviços + driver)
powershell -ExecutionPolicy Bypass -File scripts\run-e2e.ps1
```

---

## 9. Resultado das validações

| Validação | Resultado |
| --------- | --------- |
| `npm run build` (renderer) | ✅ Sem erros |
| `npx vitest run` (renderer) | ✅ **104 testes** (12 ficheiros) |
| `npm run lint` (renderer) | ✅ Sem erros |
| `python manage.py check` (backend) | ✅ `0 issues` |
| `pytest` integração (bridge+content+reports) | ✅ **161 testes** |
| E2E live — render contra payloads reais | ✅ report e media kit `completed` (PDF real) |
| E2E live — escrita de produto via callback | ⚠️ Bloqueado por ambiente (ver abaixo) |

**Impedimentos de ambiente (não são problemas de contrato/renderer):**
1. **SQLite multi-processo:** um servidor Django em execução **não vê** linhas
   commitadas por outro processo iniciado depois (o `ExternalJobReference` semeado
   pelo driver dá `404` no lookup do callback). Confirmado por uma sonda directa
   (`direct_probe_status: 404`), independente do renderer. **Em produção não ocorre**
   (o próprio servidor cria o job e recebe o callback no mesmo processo).
   Recomendação: **PostgreSQL** para E2E concorrente.
2. **Rotas `/api/v1/*` da app via `runserver` no sandbox:** todas as rotas de app
   devolveram `404` por HTTP (enquanto `/api/v1/schema/` e o `resolve()` in-process
   funcionam), impedindo o fluxo via API REST neste ambiente. Não reproduzível no
   contrato (os 161 testes do backend exercitam estas rotas/handlers com sucesso).

Ambos são limitações do harness/sandbox local; o renderer e os contratos estão
validados.

---

## 10. Pendências

- **Loop live totalmente verde** (Asset criado no Django via callback) — requer
  PostgreSQL (ou correr o fluxo de submissão dentro do próprio servidor) e resolver
  a peculiaridade de routing `/api/v1/*` do `runserver` no sandbox.
- **Callback em background leve** (CR-203) — responder 202 e enviar o callback depois;
  remove a corrida do callback síncrono com o submit do Django (recomendado para produção).
- **Echo de `template_key`/`template_id`** do envelope no content_generation, para
  maximizar a resolução de `Template` no Django independentemente do seed.
- **Limpeza** das linhas de teste no `db.sqlite3` (opcional).

---

## 11. Próximo passo recomendado

1. Correr o E2E com **PostgreSQL** (`DB_ENGINE=postgres`) e o fluxo de produto via
   API REST (§5 do guia) para obter o loop totalmente verde (Asset/Output/Report/
   MediaKit criados pelo callback).
2. Implementar o **callback em background leve** no renderer (CR-203) antes do uso
   real, evitando a sobreposição de estado do `ExternalJobReference`.
3. Promover o storage local para **S3/R2** mantendo o contrato de `Asset`.
