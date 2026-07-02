# Prompt 10 — Estado final e fecho da fase staging

**Data:** 2026-07-02
**Fase:** `04_staging_campaign_actions_with_real_ie_renderer` (STG-CA-010, Fecho)
**Âmbito:** consolidar documentação, validações e decisão de prontidão. Sem alteração de código de produto.
**Estado de execução:** `executado`

---

## 1. Estado final

**Decisão: `pronto_para_piloto_tecnico_staging`** — e **não pronto para produção**.

A fase `04` está **fechada com estado honesto**. A cadeia real Frontend → Backend Core → Intelligence Engine (síncrono) / Content Renderer (assíncrono por callback) foi validada por **API** e por **smoke visual no browser**, com IE real (dry_run OFF), Renderer real (jobs OFF de dry_run), fronteira de segurança do frontend confirmada ao vivo e falhas entre serviços tratadas de forma controlada.

Separação exigida pelas regras:

| Categoria | Conteúdo |
|---|---|
| **Implementado** | fronteira frontend; client síncrono IE; pipeline assíncrono renderer; contrato CampaignAction (6 tipos, lifecycle, dedup, snapshot, related_*) |
| **Validado API** | portas/health (P02); IE real `source=engine` (P03); actions reais (P04); renderer real job→callback→completed (P05); observabilidade (P06); erros 502/503/422/400 + retry não-destrutivo (P07); segurança frontend (P08) |
| **Validado browser** | login→War Room→intelligence "Live engine"→criar 4 tipos de action→reviewed/dismiss→panel→reload→Network só 8100 (P09) |
| **Bloqueado por ambiente** | paginação com volume real (24<25); Network via Chrome MCP externo (substituído por servidor gerido + bundle); health agregado com JWT staff (parcial) |
| **Pendente para produção** | DB alvo (não SQLite); object storage; correlation-id único ponta-a-ponta; RBAC/UX; E2E automatizado; aprovação operacional |

Regras de honestidade respeitadas: **não** declarado produção-ready; IE **não** ficou em dry_run (provado `source=engine`); Renderer **recebeu jobs/outputs reais** (PDF/PNG, callbacks).

---

## 2. Evidência consolidada (Prompts 01–09)

| Prompt | Incremento | Resultado-chave |
|---|---|---|
| 01 | contratos/config | var exacta `INTELLIGENCE_ENGINE_DRY_RUN` vs `EXTERNAL_JOBS_DRY_RUN`; bloqueador do token partilhado |
| 02 | portas/health | 4 serviços canónicos confirmados (8100/8201/8202/5200) |
| 03 | IE real | War Room `source=engine`, grade real, recommendations reais; IE down→503 |
| 04 | actions reais | 6 action_types, dedup 400, snapshot seguro, related_*, persistência |
| 05 | renderer real | job 202→callback→`completed`; Report/MediaKit/ContentPack outputs reais; CR down→job `failed` honesto |
| 06 | observabilidade | `request_id`/`job_id` correlacionados; 0 secrets em logs |
| 07 | erros reais | 503 (IE down/timeout), 502 (token/4xx), 422/400 (payload), sem falso sucesso, sem retry destrutivo |
| 08 | segurança frontend | único `fetch`; bundle só 8100; 0 refs 8201/8202/token |
| 09 | smoke visual | fluxo clicado; "Live engine"; Network live só 8100; persistência pós-reload |

---

## 3. Ficheiros criados / alterados

| Ficheiro | Operação |
|---|---|
| `arquitectura_staging_ie_renderer.md` | **criado** — 4 serviços, portas, fluxos, segurança, lifecycle, related, observabilidade |
| `estado_staging_ie_renderer.md` | **criado** — resumo executivo, validações, riscos, limitações, decisão |
| `resultados_execucao/prompt_10_estado_final_staging_resultado.md` | **criado** — este relatório |
| `.claude/launch.json` | alterado no P09 — `port` 5173→5200 (correcção de porta canónica) |

Nenhum código de produto alterado nesta iteração. Dados dev acumulados nos Prompts 03–09 (CampaignActions/artefactos reais via API/UI). Nenhum segredo consta destes documentos.

---

## 4. Validações executadas (fecho, 2026-07-02)

| Validação | Resultado |
|---|---|
| `pnpm test` (frontend) | ✅ 14/14 |
| `pnpm lint` | ✅ 0 erros |
| `pnpm build` | ✅ built OK |
| `python manage.py check` | ✅ 0 issues |
| `npm test` (Content Renderer) | ✅ 136/136 (13 ficheiros) |
| `pytest` (Intelligence Engine) | ✅ 197/197 |
| `scripts/check-forbidden-ports.ps1` | ✅ OK — nenhuma porta proibida |
| Greps de segurança (frontend/src) | ✅ 5 ocorrências, todas guarda/doc/denylist |
| Docs da fase sem secrets (JWT/token/password) | ✅ 0 valores de secret |

---

## 5. Limitações

- DB SQLite dev (não staging alvo); storage local (não object storage).
- Correlation-id único ponta-a-ponta ausente (OBS-L01/L02); IE não regista o `request_id` recebido a nível app.
- `Asset.public_url` não populado no Backend Core.
- `recommendation_ref` posicional (IE real sem `id`).
- Paginação não exercitada com volume real; MediaKit sem estado `failed` próprio.

---

## 6. Riscos

| ID | Risco | Sev. | Estado |
|---|---|---|---|
| STG-R01 | Poucas recommendations (campanha fraca) | Alto | presente — criar dev data mais rica |
| STG-R05 | Token em logs | Crítico | **mitigado** (greps a 0) |
| STG-R06 | Renderer indisponível deixa action presa | Médio | **mitigado** (estado honesto + retry não-destrutivo) |
| STG-R09 | SQLite em vez de DB alvo | Médio | presente — declarado |
| STG-R10/OBS-L01 | Sem correlation-id único | Alto | presente — resolver antes de produção |

---

## 7. Decisão de prontidão

**`pronto_para_piloto_tecnico_staging`.**

O fluxo real (IE + Renderer) está validado por API e browser, com segurança e tratamento de falhas confirmados. Adequado a **piloto técnico controlado em staging**. **Não** pronto para produção (falta staging formal, observabilidade completa, RBAC/UX, E2E automatizado e aprovação operacional).

---

## 8. Próximos passos

1. **Staging formal** — DB alvo, object storage (S3/R2), gestão de segredos, `public_url` canónico.
2. **Observabilidade** — correlation-id único BC→IE→job registado em todos; agregação/retenção de logs; métricas de job.
3. **RBAC/UX** — mensagens de erro na UI, paginação com volume, capabilities finas.
4. **E2E automatizado** — cobrir War Room → actions → renderer com stack real.
5. **Preparação para produção** — health agregado em uso, alertas, checklist de segurança/rotação de segredos antes de qualquer promoção.

> Serviços a correr no fecho: Backend Core (8100), Intelligence Engine (8201), Content Renderer (8202), Frontend (5200, servidor gerido) — todos reais e activos.
