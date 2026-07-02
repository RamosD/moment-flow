# Estado — Staging Campaign Actions com IE e Renderer reais

> Fase: `04_staging_campaign_actions_with_real_ie_renderer`
> Estado: **FECHADA** (STG-CA-010), 2026-07-02
> Decisão de prontidão: **`pronto_para_piloto_tecnico_staging`** (não produção)

---

## 1. Resumo executivo

A fase validou a cadeia real **Frontend → Backend Core → Intelligence Engine / Content Renderer** em ambiente dev/staging controlado, removendo as duas limitações da fase 03:

- **Intelligence Engine real** (dry_run **desactivado**): a War Room recebe intelligence real (`source=engine`), grade/scores/moments/recommendations reais.
- **Content Renderer real** (jobs **não** dry_run): report/media kit/content pack geram jobs reais, callbacks e outputs (PDF/PNG) em storage local.

A tese da fase foi cumprida: uma CampaignAction nasce de **intelligence real** e aciona **outputs reais** através do renderer, com estado observável — sem mocks runtime. O smoke visual clicado no browser confirmou o fluxo ponta-a-ponta e a fronteira do frontend (só chama 8100).

**Não é produção-ready.** Ver §7 (pendente para produção).

---

## 2. Validações concluídas

### 2.1 Implementado (contrato/arquitectura)
- Fronteira do frontend (único `fetch`, boundary a 8100, guarda de `X-Internal-Token`).
- Client síncrono do IE (typed errors, retry só transitório, token só em header).
- Pipeline assíncrono do renderer (job persistido antes da chamada, callback, retry explícito não-destrutivo).
- Contrato CampaignAction (6 action_types, lifecycle, dedup, snapshot seguro, related_*).

### 2.2 Validado por API (real, sem dry_run)
| Área | Evidência | Prompt |
|---|---|---|
| Portas canónicas + healthchecks (8100/8201/8202/5200) | 4 serviços confirmados pelo conteúdo, não só HTTP | 02 |
| War Room com IE real | `source=engine`, grade, 2–3 recommendations reais | 03 |
| CampaignActions de recommendations reais | 6 action_types, dedup 400, snapshot mínimo, related_*, persistência | 04 |
| Content Renderer real | job `POST /jobs/`→202→callback→`completed`; Report→completed(PDF), MediaKit→generated(PDF), ContentPackRequest→completed(+ContentOutputs) | 05 |
| Observabilidade mínima | `request_id`/`job_id` correlacionados; 0 secrets em logs | 06 |
| Erros reais entre serviços | IE down→**503**, timeout→**503**, token inválido→**502**, payload inválido IE→**422**/CR→**400**, renderer down→job `failed`+artefacto honesto, retry não-destrutivo | 07 |
| Segurança frontend | greps limpos; único `fetch`; bundle só com 8100; 0 refs a 8201/8202/token | 08 |

### 2.3 Validado por browser (smoke visual real)
| Passo | Evidência | Prompt |
|---|---|---|
| Login real → workspace → campaign → War Room | clicado no browser gerido em 5200 | 09 |
| Intelligence real na UI | badge **"Live engine · intelligence_engine · v0.1.0"** (não dry_run) | 09 |
| Criar manual task/report/media kit/content pack | criados via UI; report→completed, media kit→generated (renderer real) | 09 |
| Mark reviewed / Dismiss com motivo | `create_release_post`→Completed; `improve_smart_link`→Dismissed+reason | 09 |
| CampaignActionsPanel | 24 actions, statuses coerentes, related_*, timestamps, dismiss reason | 09 |
| Reload / persistência | estado persiste; "Live engine" após reload | 09 |
| Network ao vivo | só `localhost:8100`; **zero** 8201/8202 | 09 |
| Dedup na UI | 2º artefacto mesmo ref+type → "Active action exists" | 09 |

### 2.4 Validações de qualidade (no fecho, 2026-07-02)
| Validação | Resultado |
|---|---|
| `pnpm test` (frontend) | ✅ 14/14 |
| `pnpm lint` | ✅ 0 erros |
| `pnpm build` | ✅ OK |
| `python manage.py check` | ✅ 0 issues |
| `npm test` (Content Renderer) | ✅ 136/136 |
| `pytest` (Intelligence Engine) | ✅ 197/197 |
| `scripts/check-forbidden-ports.ps1` | ✅ OK |
| Greps de segurança (frontend) + docs sem secrets | ✅ só guarda/doc/denylist; 0 valores de secret nos docs |

---

## 3. Validações bloqueadas por ambiente

| Item | Estado | Nota |
|---|---|---|
| Paginação do CampaignActionsPanel com volume real | **Não exercitada** | Controlos presentes mas 24 actions < page_size 25; não trocou de página (Prompt 09). |
| Network live capturado com Chrome MCP externo | **Substituído** | Sem browser Chrome ligado; usado servidor gerido (Claude Preview) + bundle estático (Prompts 08/09). Resultado equivalente. |
| Healthcheck agregado `/system/health/dependencies/` com JWT staff | **Parcial** | Endpoint identificado (Prompt 01/02); não exercido com staff em runtime. |

Nenhum bloqueio impediu a validação do fluxo principal; todos têm substituto ou são de baixo impacto para o piloto.

---

## 4. Evidências

Todos os relatórios em `resultados_execucao/`:
`prompt_01` (contratos/config) · `prompt_02` (portas/health) · `prompt_03` (IE real) · `prompt_04` (actions reais) · `prompt_05` (renderer real) · `prompt_06` (observabilidade) · `prompt_07` (erros reais) · `prompt_08` (segurança frontend) · `prompt_09` (smoke visual) · `prompt_10` (estado final).
Arquitectura: `arquitectura_staging_ie_renderer.md`.

---

## 5. Riscos

| ID | Risco | Sev. | Estado |
|---|---|---|---|
| STG-R01 | IE real gerar poucas recommendations (campanha "fraca", sem track) | Alto | Presente — grade C/D; recommendations reais mas mínimas. Criar dev data mais rica. |
| STG-R05 | Token interno em logs | Crítico | **Mitigado** — greps a 0. |
| STG-R06 | Renderer indisponível deixar action "presa" | Médio | **Mitigado** — job `failed` + artefacto honesto; retry não-destrutivo. |
| STG-R09 | Staging usar SQLite em vez de DB alvo | Médio | Presente — dev SQLite; declarar limite. |
| STG-R10 / OBS-L01 | Falta de correlation-id único ponta-a-ponta | Alto | Presente — correlação por `campaign_id`/`job_id`. Resolver antes de produção. |

---

## 6. Limitações

- **DB é SQLite dev**, não o alvo de staging formal.
- **Correlation-id único ponta-a-ponta** ausente (OBS-L01/L02); IE não regista o `request_id` recebido a nível app.
- **`Asset.public_url`** não populado no Backend Core (ficheiro servido pelo file server dev do CR).
- **`recommendation_ref` posicional** (IE real não devolve `id`) — estável por chamada, muda se a ordem/action mudar.
- **Paginação** não exercitada com volume real.
- **MediaKit** não tem estado `failed` próprio (falha vai para metadata).
- **Storage local**, não object storage.

---

## 7. Decisão de prontidão

### `pronto_para_piloto_tecnico_staging`

A cadeia real (IE + Renderer) está validada por API **e** por smoke visual no browser, com fronteira de segurança confirmada e falhas tratadas. É adequada para **piloto técnico controlado em staging**.

### **NÃO** pronto para produção
Falta, no mínimo:
- staging formal com DB alvo (não SQLite) e gestão de segredos;
- observabilidade completa (correlation-id único ponta-a-ponta, IE a registar request_id, retenção/agregação de logs);
- RBAC/UX de erro afinados e paginação exercitada com volume;
- E2E automatizado;
- aprovação operacional.

---

## 8. Próximos passos

1. **Staging formal:** provisionar DB alvo, object storage (S3/R2), gestão de segredos; parametrizar `RENDERER_PUBLIC_BASE_URL`/`public_url`.
2. **Observabilidade:** propagar um `X-Request-ID` único BC→IE→job e registá-lo em todos (incl. IE app-level); agregação/retenção de logs; métricas de job.
3. **RBAC/UX:** afinar mensagens de erro na UI; exercitar paginação com volume; capabilities finas para actions.
4. **E2E automatizado:** cobrir o fluxo War Room → actions → renderer com o stack real (evitar smoke manual não-repetível).
5. **Preparação para produção:** healthchecks agregados em uso, alertas, e checklist de segurança/secret rotation antes de qualquer promoção.
