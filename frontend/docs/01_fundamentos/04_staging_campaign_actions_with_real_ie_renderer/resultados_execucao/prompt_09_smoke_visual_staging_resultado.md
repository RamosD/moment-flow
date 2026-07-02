# Prompt 09 — Smoke visual staging (browser real)

**Data:** 2026-07-02
**Fase:** `04_staging_campaign_actions_with_real_ie_renderer` (STG-CA-009, Incremento 3)
**Âmbito:** smoke visual clicado no browser, fluxo principal da War Room com **IE real** e **Renderer real**. Sem mocks runtime, sem dry_run.
**Estado de execução:** `executado` (browser real, não bloqueado)

---

## 1. Resumo objectivo

O fluxo principal foi executado **clicado num browser real** (Claude Preview, servidor gerido na porta canónica 5200) contra o stack real (Backend Core 8100, IE 8201, Renderer 8202):

- Login real → workspace → campaign → **War Room**.
- Intelligence **real** visível: badge **"Live engine · intelligence_engine · v0.1.0"** (source=engine, **não** dry_run), grade C, scores reais, 1 moment, **2 recommendations**.
- Criadas via UI: **manual task, report, media kit, content pack** (catálogo activo), **Mark reviewed** e **Dismiss com motivo**.
- **CampaignActionsPanel** coerente: 24 actions, statuses (Pending/Completed/Dismissed), `related_*` (report/media kit/content pack request ids), timestamps, dismiss reason, paginação presente.
- **Reload** → persistência visual confirmada (24 actions, smoke actions presentes, report `completed`/media kit `generated` via renderer real).
- **Network:** frontend chama **apenas** `localhost:8100`; **zero** chamadas a 8201/8202.
- Sem erros de consola; sem regressões óbvias de layout/dialogs/botões.

**Pronto para fecho (STG-CA-010).**

---

## 2. Ambiente e método

| Item | Valor |
|---|---|
| Browser | Claude Preview (servidor gerido) em `http://localhost:5200` (porta canónica) |
| Backend Core | `http://localhost:8100` (real) |
| IE / Renderer | `http://localhost:8201` / `http://localhost:8202` (reais, activos) |
| User | `ca014-dev@example.local` (password efémera definida via Django shell só para o smoke; não armazenada) |
| Workspace | CA014 Dev Workspace (`46ca02a0-…`) |
| Campaign | CA014 Test Campaign (`30930999-…`, active) |

Nota de setup: o Frontend externo corria com `strictPort` em 5200; foi parado e substituído por um servidor **gerido** na mesma porta canónica para permitir instrumentação de clique/Network. `.claude/launch.json` tinha `port: 5173` (porta proibida, inconsistente com o vite `server.port=5200`) — **corrigido para 5200** para alinhar com o mapa canónico.

---

## 3. Passos clicados — resultado por passo

| # | Passo | Resultado |
|---|---|---|
| 1 | Abrir `http://localhost:5200` | ✅ Página de login renderiza |
| 2 | Login real (email+password) | ✅ Autenticado; `POST /api/v1/auth/token/`→200, `GET /auth/me/`→200 |
| 3 | Seleccionar workspace | ✅ "CA014 Dev Workspace" activo no switcher |
| 4 | Abrir campaign | ✅ Campaigns → "CA014 Test Campaign" (detalhe) |
| 5 | Abrir War Room | ✅ Breadcrumb Campaigns / CA014 Test Campaign / War Room |
| 6 | Executar/refrescar intelligence real | ✅ `POST /campaigns/{id}/intelligence/`→200; badge **"Live engine"** (source=engine) |
| 7 | Confirmar recommendations reais | ✅ 2 recommendations: `improve_smart_link` (i0), `create_release_post` (i1); grade C; scores readiness 55 / momentum 20 / opportunity 15 / risk 20 / priority 25; 1 moment; "Why these results? (10)" |
| 8 | Criar manual task | ✅ "STG09 smoke manual task" (Pending) |
| 9 | Criar report action | ✅ "STG09 smoke report rec1" → Report `63caf984-…`; artefacto **completed** (renderer real) |
| 10 | Criar media kit action | ✅ "STG09 smoke media kit rec1" → Media kit `fa3aff49-…`; artefacto **generated** (renderer real) |
| 11 | Criar content pack action (catálogo activo) | ✅ Selector com catálogo (Auto Media Kit, Milestone Pack, **Release Pack**, Weekly Growth Pack); criada → Content pack request `873b111d-…` |
| 12 | Mark reviewed | ✅ `create_release_post` → **Completed** (timestamp Completed presente) |
| 13 | Dismiss com motivo | ✅ `improve_smart_link` → **Dismissed**, dismiss reason "STG09 smoke: not a priority this cycle" |
| 14 | Confirmar CampaignActionsPanel | ✅ 24 actions; statuses coerentes; `related_*` visíveis; timestamps (Created/Completed/Dismiss reason); "Page 1 of 1 · 24 actions" (Previous/Next presentes, disabled a <25) |
| 15 | Recarregar página | ✅ Sessão persistida (token localStorage); War Room recarrega |
| 16 | Confirmar persistência visual | ✅ 24 actions e todas as smoke actions presentes após reload; badge "Live engine" |
| 17 | Layout/botões/dialogs/mensagens | ✅ Dialogs "Create campaign action" e "Dismiss recommendation" correctos; badges/botões renderizam; **sem erros de consola**; sem regressão óbvia |
| 18 | Network | ✅ Só `localhost:8100`; **zero** 8201/8202 |

---

## 4. Evidência de intelligence real (não dry_run)

Cabeçalho da War Room:
```
Live engine   intelligence_engine · v0.1.0
Campaign health 'warning', grade C. Scores — readiness 55, momentum 20,
opportunity 15, risk 20, priority 25. 1 moment(s) detected;
2 recommendation(s), top action improve_smart_link.
Generated at 2026-07-02T02:41:27.974618+00:00
```
O badge **"Live engine"** e o nome/versão do engine provam `source=engine`. O selector de dry_run **não** foi usado.

---

## 5. Deduplicação observada na UI

Ao tentar criar um **2.º Report** para a recommendation `improve_smart_link` (que já tinha um Report de iterações anteriores), o botão de submissão do diálogo mudou para **"Active action exists"** (desactivado) — a deduplicação por `recommendation_ref + type` é visível e impede o duplicado. Criar o Report numa recommendation diferente (`create_release_post`) funcionou normalmente.

---

## 6. CampaignActionsPanel (detalhe)

Amostra (pós-reload), com `related_*`, statuses e timestamps:

| Título | Tipo | Status | related / motivo | Created |
|---|---|---|---|---|
| improve_smart_link | Dismiss | **Dismissed** | reason: "STG09 smoke: not a priority this cycle" | Jul 2, 01:48 |
| create_release_post | Mark reviewed | **Completed** | Completed: Jul 2, 01:47 | Jul 2, 01:47 |
| STG09 smoke content pack rec1 | Content pack | Pending | Content pack request: `873b111d-…` | Jul 2, 01:47 |
| STG09 smoke media kit rec1 | Media kit | Pending | Media kit: `fa3aff49-…` | Jul 2, 01:45 |
| STG09 smoke report rec1 | Report | Pending | Report: `63caf984-…` | Jul 2, 01:45 |
| STG09 smoke manual task | Manual task | Pending | — | Jul 2, 01:43 |

- **Paginação:** "Page 1 of 1 · 24 actions"; controlos Previous/Next presentes e correctamente **desactivados** (24 < page_size 25). Volume insuficiente para exercitar troca de página (ver limitações).
- Cada CampaignAction artefacto-backed mostra controlos de lifecycle (Complete / Dismiss / Cancel).

---

## 7. Network observado (tarefa 18)

`performance.getResourceEntries` após o fluxo completo + reload:

| Métrica | Valor |
|---|---|
| Hosts distintos | `localhost:5200` (assets Vite), `localhost:8100` (API) |
| Hosts de chamadas `/api/v1/` | **`localhost:8100`** (único) |
| Chamadas a `8201` / `8202` | **0** |

Endpoints observados (todos 8100): `auth/token`, `auth/me`, `workspaces`, `campaigns`, `campaigns/{id}`, `campaigns/{id}/intelligence/`, `campaign-actions` (+ filtros `recommendation_ref`), `reports`, `media-kits`, `content-outputs`, `content-pack-requests`. Confirma a fronteira: o browser nunca fala com IE/Renderer; toda a mediação é server-to-server no Backend Core.

> Nota: alguns `GET /campaign-actions` aparecem como `net::ERR_ABORTED` — são cancelamentos do React Query (requests duplicados em voo abortados no re-render); os retries devolvem 200. Não são erros funcionais.

---

## 8. Screenshots / evidência textual

- Screenshot 1 (War Room topo): badge "Live engine", grade C, grelha de scores — layout limpo.
- Screenshot 2 (Campaign Actions): cartões com badges Dismissed/Completed/Pending, `related_*` ids, dismiss reason, controlos de lifecycle — sem regressão.
- Snapshots de acessibilidade e `preview_eval` usados para confirmar textos/estados (ver secções 3–7). Nenhum secret capturado (só ids de domínio, títulos e estados).

---

## 9. Falhas visuais

**Nenhuma.** Sem erros de consola (`level=error` → vazio). Dialogs, botões, badges e mensagens renderizam correctamente. Sem regressão de layout observada nas páginas Login, Dashboard, Campaigns, Campaign detail e War Room.

---

## 10. Limitações

| Limitação | Impacto |
|---|---|
| Volume de actions (24) < page_size (25) → paginação **presente mas não trocou de página** | Baixo. Controlos existem e estão correctamente desactivados; a troca real de página não foi exercitada (exigiria >25 actions). |
| Alguns campos de formulário foram preenchidos via `preview_eval`/setter nativo (select de content pack) por limitação do selector CSS | Nenhum — o evento `change` foi disparado e o React reagiu; a submissão foi real (HTTP 200, artefacto criado). |
| Frontend externo (strictPort) substituído por servidor gerido na mesma porta 5200 | Operacional — documentado; ambiente equivalente. |
| DB é SQLite dev | Herdado (STG-R09); declarar no fecho. |

---

## 11. Ficheiros alterados

| Ficheiro | Operação |
|---|---|
| `.claude/launch.json` | **alterado** — `port` 5173 → **5200** (correcção para a porta canónica; 5173 é porta proibida) |
| `frontend/docs/.../resultados_execucao/prompt_09_smoke_visual_staging_resultado.md` | **criado** (este relatório) |
| `backend_core/db.sqlite3` | CampaignActions/artefactos reais criados via UI (manual task, report, media kit, content pack, mark reviewed, dismiss) |

Nenhum código de produto alterado. Password do dev user redefinida de forma efémera (não persistida no relatório). Nenhum segredo consta deste relatório.

---

## 12. Pronto / não pronto para fecho

**Pronto para fechar a fase (STG-CA-010) como piloto técnico controlado.** O smoke visual clicado passou com IE real e Renderer real, a fronteira do frontend está confirmada ao vivo (só 8100), e a persistência aguenta reload.

Ressalvas para produção (não para o piloto): SQLite dev (não staging alvo), correlation-id único ponta-a-ponta em falta (OBS-L01, Prompt 06), `Asset.public_url` não populado (Prompt 05), e paginação não exercitada com volume real.

---

## 13. Próximo passo recomendado

Avançar para **STG-CA-010 (fechar estado de staging)**:
1. Consolidar o relatório final da fase com as evidências dos Prompts 01–09.
2. Actualizar `estado_staging_ie_renderer.md`; listar validações concluídas, limitações e riscos.
3. Declarar **pronto para piloto técnico controlado** e **não pronto para produção** (falta staging formal, observabilidade ponta-a-ponta e aprovação operacional).

> Serviços a correr no fim desta iteração: Backend Core (8100), Intelligence Engine (8201), Content Renderer (8202), Frontend (5200, servidor gerido) — todos reais e activos.
