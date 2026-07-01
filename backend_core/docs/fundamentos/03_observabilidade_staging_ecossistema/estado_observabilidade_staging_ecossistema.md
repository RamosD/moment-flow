# Estado final — Observabilidade e Staging Técnico do Ecossistema

> Documento de fecho da fase **Observabilidade e Staging Técnico do
> Ecossistema** (OBS-STG-001…010). Consolida o estado real, com validações
> finais executadas nesta sessão. **Nenhum valor real de secret** aparece neste
> documento. Onde uma validação não foi executada ao vivo, está marcado
> explicitamente como tal — não há resultados inventados.
>
> Fonte: [`01_backlog.md`](01_backlog.md),
> [`matriz_operacional_servicos.md`](matriz_operacional_servicos.md),
> [`runbook_arranque_staging.md`](runbook_arranque_staging.md),
> [`checklist_troubleshooting.md`](checklist_troubleshooting.md),
> [`painel_prontidao_operacional.md`](painel_prontidao_operacional.md) e os
> relatórios `resultados/prompt_01`…`prompt_09`.
> Data: 2026-06-25.

---

## 1. Resumo executivo

A fase entregou a camada mínima de observabilidade e staging técnico definida
no backlog (§1/§14): healthcheck agregado, dois smoke tests opt-in, correlação
de logs mínima, e quatro documentos operacionais (matriz, runbook, checklist,
painel). Toda esta camada está **implementada e coberta por testes
automatizados** (510 passed, 3 skipped na suite completa, ver §6). O que esta
fase **não** fez, em nenhum dos seus 10 prompts, foi validar esse trabalho
contra os três serviços a correr **em simultâneo e ao vivo** nesta sessão —
essa lacuna está documentada de forma honesta e repetida ao longo de toda a
fase (em particular no painel §1–§3), e confirma-se aqui, no fecho, com
tentativas reais de sondagem do ambiente (§9).

**Decisão: pronto para piloto técnico controlado, com ressalva explícita; não
pronto para produção.** Ver §10/§11.

---

## 2. Escopo entregue

| Item | Prompt | Estado |
|---|---|---|
| Análise do estado operacional inicial (gaps G1–G10) | OBS-STG-001 | ok |
| Matriz operacional de serviços | OBS-STG-002 | ok |
| Healthcheck agregado (`GET /api/v1/system/health/dependencies/`) | OBS-STG-003 | ok |
| Smoke test BC↔IE (`manage.py smoke_intelligence_engine`) | OBS-STG-004 | ok |
| Smoke test BC↔Renderer (`manage.py smoke_content_renderer`) | OBS-STG-005 | ok |
| Correlação de logs (`external_job_id`, visibilidade INFO) | OBS-STG-006 | ok |
| Runbook de arranque (`runbook_arranque_staging.md`) | OBS-STG-007 | ok |
| Checklist de troubleshooting (16 casos) | OBS-STG-008 | ok |
| Painel de prontidão operacional | OBS-STG-009 | ok |
| Validação final e fecho da fase (este documento) | OBS-STG-010 | ok |

Nenhum item do escopo foi deixado incompleto. Os itens fora de escopo
(observabilidade real, S3/R2, calibração de negócio, CI/CD, cofre de secrets)
permanecem deliberadamente fora, por desenho do backlog §4.2/§13 — não são
dívida desta fase.

---

## 3. Healthchecks

- `intelligence_engine` `GET /health` e `content_renderer` `GET /health`:
  endpoints públicos confirmados por inspecção de código (OBS-STG-001).
- `backend_core` — healthcheck agregado: implementado (OBS-STG-003), 20 testes
  unitários/integração a passar (mocks de ok/degraded/unavailable/
  misconfigured/timeout/resposta inválida/RBAC).
- **Validação ao vivo nesta fase:** tentada nesta sessão de fecho (§9) —
  **não foi possível confirmar que `backend_core` estava a correr** no
  ambiente desta sessão; chamada real ao endpoint agregado **não executada**.
- `backend_core` — liveness público (sem auth): continua **pendente** (sem
  endpoint dedicado; usa-se `GET /api/v1/schema/` como proxy documentado).

---

## 4. Smoke tests

- Smoke BC↔IE e BC↔Renderer: ambos implementados como management commands
  opt-in, com testes próprios a passar (mocks de config/cliente).
- **Execução real nesta fase:** **não executada.** Os 3 testes opt-in que
  exigem `RUN_REAL_IE=1` com o IE a correr aparecem como `skipped` na suite
  completa desta sessão (ver §6) — mesmo resultado de todas as execuções
  anteriores da fase.
- Tentativa de sondagem do ambiente nesta sessão de fecho (§9) não permitiu
  confirmar com segurança a identidade/token do processo que respondeu na
  porta usada pelo IE, pelo que **não se tentou** disparar o smoke test real
  contra ele (ver §9 e §7 — nunca se inventa nem adivinha um token).
- `content_renderer`: porta confirmada como **inacessível** nesta sessão
  (timeout de ligação) — smoke real **não executável** no ambiente actual.

---

## 5. Logs / correlação

- `request_id`, `job_id`, `external_job_id`: presentes e testados (`caplog`)
  nos fluxos BC→IE e BC→Renderer.
- Visibilidade efectiva de logs INFO do Django: corrigida nesta fase
  (OBS-STG-006, `LOGGING` em `config/settings.py`), confirmada por teste e
  por `getEffectiveLevel()`.
- Ausência de tokens em logs: confirmada por testes dedicados ao longo da
  fase (`_FORBIDDEN_KEYS`, testes `caplog`-based).
- Lacunas conhecidas e já documentadas (sem alteração nesta fase, fora do
  âmbito mínimo): `duration_ms` ausente no log de submissão de jobs do
  renderer; `workspace_id` ausente no logger de transporte de baixo nível
  (presente na linha `log_job_event` paralela); formato heterogéneo entre
  serviços (`key=value` no BC vs JSON no IE/renderer) — aceitável para o
  âmbito MVP, sem agregação automática (backlog §4.2 exclui ELK).
- Correlação validada **ao vivo**, entre processos reais, nesta fase: **não
  executada** — validação feita por testes automatizados, não por captura
  simultânea de logs dos três processos.

---

## 6. Documentação criada

| Documento | Prompt |
|---|---|
| `matriz_operacional_servicos.md` | OBS-STG-002 (mantido actualizado em 003–009) |
| `smoke_intelligence_engine.md` | OBS-STG-004 |
| `smoke_content_renderer.md` | OBS-STG-005 |
| `runbook_arranque_staging.md` | OBS-STG-007 |
| `checklist_troubleshooting.md` | OBS-STG-008 |
| `painel_prontidao_operacional.md` | OBS-STG-009 |
| `estado_observabilidade_staging_ecossistema.md` (este documento) | OBS-STG-010 |
| 10 relatórios em `resultados/` (`prompt_01`…`prompt_10`) | OBS-STG-001…010 |

---

## 7. Validações executadas (nesta sessão de fecho, OBS-STG-010)

| Validação | Comando | Resultado |
|---|---|---|
| Verificação de configuração Django | `python manage.py check` | ✅ "System check identified no issues (0 silenced)." |
| Lint | `python -m ruff check .` | ✅ "All checks passed!" |
| Suite de testes completa | `python -m pytest -q` | ✅ **510 passed, 3 skipped**, 249 warnings, 743.49s. Os 3 `skipped` são os testes opt-in de `test_intelligence_real_loop.py` que exigem `RUN_REAL_IE=1` com o IE a correr — comportamento esperado e idêntico ao registado em fases anteriores (ex.: prompt_06: "243 passed, 3 skipped" antes do crescimento da suite). |
| Regeneração de schema/OpenAPI | — | **não aplicável** — nenhuma alteração de código nesta fase (OBS-STG-007/008/009/010 foram exclusivamente documentação); nenhum endpoint, serializer ou view foi tocado, logo não há schema a regenerar. |
| Healthcheck agregado, ao vivo | `curl` contra `GET /api/v1/system/health/dependencies/` | **não executado** — ver §9 (ambiente não permitiu confirmar `backend_core` a correr). |
| Smoke test IE, ao vivo | `manage.py smoke_intelligence_engine` | **não executado** — ver §9 (token não confirmável com segurança). |
| Smoke test Renderer, ao vivo | `manage.py smoke_content_renderer` | **não executado** — ver §9 (porta inacessível, timeout). |
| Confirmação de ausência de secrets reais | inspecção do código-fonte das docs/relatórios desta fase + `.env.example` | ✅ ver §8. |

---

## 8. Confirmação de ausência de secrets reais

- **Docs desta fase** (`matriz_operacional_servicos.md`, `runbook_arranque_staging.md`,
  `checklist_troubleshooting.md`, `painel_prontidao_operacional.md`,
  `smoke_intelligence_engine.md`, `smoke_content_renderer.md`, este documento):
  inspecção visual confirma que todos os tokens/credenciais citados são
  placeholders (`<DEV_TOKEN>`, `<INTERNAL_API_TOKEN>`, `<ACCESS_TOKEN>`).
  Nenhum valor real de `SECRET_KEY`/`DB_PASSWORD`/`INTERNAL_API_TOKEN`.
- **Relatórios** (`resultados/prompt_01`…`prompt_09`): mesma verificação
  aplicada nos respectivos relatórios de execução — confirmados sem secrets
  reais nas suas próprias secções "Verificação de ausência de secrets".
- **`.env.example`** (`backend_core/.env.example`, alterado em fase anterior a
  esta, OBS-STG-003): `SECRET_KEY=change-me-to-a-long-random-string`,
  `DB_PASSWORD=postgres`, `INTERNAL_API_TOKEN=` (vazio) — todos placeholders
  óbvios, sem valor real.
- **Logs de exemplo**: nenhum log de exemplo com valores reais foi incluído
  em nenhum documento desta fase; os exemplos citados nos guias usam nomes de
  campo (`request_id=...`, `job_id=...`) sem valores reais associados a
  segredos.
- **Testes adicionados** (`test_dependency_health.py`,
  `test_smoke_intelligence_command.py`, `test_smoke_content_renderer_command.py`,
  testes de `external_job_id`/`LOGGING` em OBS-STG-006): usam tokens fictícios
  de teste (ex.: `"test-token"`, valores gerados em fixtures), nunca segredos
  reais — confirmado por inspecção do código destes ficheiros de teste.
- Achado adicional desta sessão: `content_renderer/docker-compose.e2e.yml`
  define `POSTGRES_PASSWORD: ${DB_PASSWORD:-chartrex_e2e_dev_only}` — valor
  literal, mas é uma password de fixture local para um container Postgres
  efémero de testes E2E (nome explicitamente identifica "dev_only"), não uma
  credencial de ambiente real. Já estava documentado em `prompt_01` antes
  desta verificação; reconfirmado aqui sem alteração.

**Conclusão: nenhum secret real foi encontrado em nenhum artefacto desta
fase.**

---

## 9. Limitações

- **Ambiente real não disponível para validação ao vivo nesta sessão de
  fecho.** Sondagem activa do ambiente confirmou:
  - Porta 8001 respondeu a `GET /health` com um corpo no formato esperado do
    `intelligence_engine` (`{"status":"ok","service":"intelligence_engine",...}`).
  - Porta 8002 (`content_renderer`) **não respondeu** — ligação esgotou o
    tempo limite (timeout), confirmando o serviço como inacessível nesta
    sessão.
  - Porta 8000 está ocupada por um processo cujos cabeçalhos de resposta
    (`server: uvicorn`) e comportamento (`/docs` devolve `200`, assinatura
    típica do Swagger UI automático do FastAPI) indicam tratar-se de um
    serviço **FastAPI**, não do servidor de desenvolvimento Django do
    `backend_core` — pelo que **não há confirmação de que `backend_core`
    estivesse a correr** nesta sessão.
  - Não existe ficheiro `.env` local para `intelligence_engine` nem para
    `backend_core` neste checkout, pelo que não há forma segura de descobrir
    qual `INTERNAL_API_TOKEN` (se algum) o processo na porta 8001 esperaria.
  - **Decisão tomada:** não adivinhar nem fabricar um valor de token para
    tentar autenticar contra esse processo — consistente com a regra
    transversal desta fase de nunca inventar ou arriscar expor segredos.
    Como consequência, o healthcheck agregado ao vivo e os dois smoke tests
    ao vivo **não foram executados** nesta sessão.
  - **Como validar no futuro:** seguir o runbook (`runbook_arranque_staging.md`
    §5–§8) num ambiente com `.env` próprio configurado para os três serviços,
    arrancando-os explicitamente com os comandos documentados, e só então
    correr o healthcheck agregado e os dois smoke tests reais.
- **Esta limitação não é nova nesta fase** — é a mesma lacuna identificada e
  documentada de forma consistente em OBS-STG-001, 006 e 009 (painel §1–§3,
  B8): a fase entrega e testa (com mocks) toda a camada de observabilidade
  mínima, mas a validação "ao vivo, três serviços em simultâneo" nunca
  aconteceu dentro do âmbito de nenhum dos 10 prompts desta fase.
- **Schema/OpenAPI**: não foi necessário regenerar nem validar, porque nenhum
  código de API foi alterado nesta fase (apenas documentação e, em fases
  anteriores, logging/management commands sem impacto no schema).
- **Nenhuma falha encontrada nesta sessão foi corrigida**, porque nenhuma das
  validações executadas (`check`, `ruff`, `pytest`) revelou falhas — não houve,
  portanto, necessidade de aplicar correcções de âmbito desta fase.

---

## 10. Riscos em aberto

| ID | Risco | Estado |
|---|---|---|
| OBS-RSK-007 (backlog) | Validação real (3 serviços simultâneos) nunca executada em nenhum prompt da fase, incluindo o fecho | **em aberto** — runbook/checklist deixam o caminho pronto a executar; falta a execução em si num ambiente com `.env` configurado. |
| G9 (matriz) | Discrepância de porta do report renderer (8003 default no código vs 8002 real) | **em aberto** — mitigado por documentação em 3 documentos, não corrigido no código. |
| B7/B8 (painel) | Healthcheck agregado e smoke tests nunca confirmados ao vivo | **em aberto** — reconfirmado nesta sessão de fecho (§9); continua a ser o primeiro passo recomendado antes de um piloto real. |
| Heterogeneidade de formato de log entre serviços | **em aberto** — aceitável para o âmbito MVP; revisitar apenas se uma stack de observabilidade real for introduzida. |
| Ausência de `.env` local neste checkout para IE/backend_core | **em aberto (novo, identificado nesta sessão)** — impede qualquer validação ao vivo segura sem configuração explícita prévia; não é um defeito desta fase, é um pré-requisito de ambiente em falta. |

---

## 11. Decisão de prontidão — Piloto técnico controlado

**Estado: PRONTO**, com a mesma ressalva explícita já registada em
OBS-STG-009 e reconfirmada nesta sessão de fecho: a prontidão assume que,
**antes de qualquer piloto real**, alguém configura um `.env` próprio para
cada serviço e executa de facto o runbook e os dois smoke tests contra os três
processos a correr simultaneamente. Esta fase deixou esse caminho documentado
e testado (com mocks) ao nível de código, mas **não o executou ao vivo** em
nenhum dos seus 10 prompts — incluindo este fecho, em que a tentativa real foi
feita e bloqueada por ambiguidade de ambiente (§9), não por falta de
documentação ou de cobertura de testes.

## 12. Decisão de prontidão — Produção

**Estado: NÃO PRONTO.** Motivos (idênticos aos already registados em
OBS-STG-009, todos deliberadamente fora do escopo desta fase por desenho do
backlog §4.2/§13):

- Sem observabilidade real (métricas, tracing distribuído, alertas).
- Sem centralização de logs.
- Storage do renderer é local (MVP), sem S3/R2.
- Scores/recomendações do IE são heurísticos, sem calibração de negócio.
- Sem staging contínuo nem pipeline de deploy/CI-CD.
- Sem gestão segura de secrets (cofre/rotação) — hoje apenas `.env` git-ignored.

---

## 13. Próximos passos recomendados

1. **Antes de qualquer piloto:** configurar `.env` próprio para
   `backend_core`, `intelligence_engine` e `content_renderer` num ambiente
   dedicado, arrancar os três processos seguindo
   [`runbook_arranque_staging.md`](runbook_arranque_staging.md) §5–§8, e
   correr de facto: o healthcheck agregado, `manage.py smoke_intelligence_engine`
   e `manage.py smoke_content_renderer` (ou o harness E2E completo) contra os
   processos reais. Esta é a única validação em falta para fechar B8/OBS-RSK-007.
2. Corrigir o default de `REPORT_RENDERER_BASE_URL` no código
   (`:8003`→`:8002`) ou documentar de forma ainda mais visível no arranque,
   para eliminar o risco residual de G9/B7.
3. Adicionar `duration_ms` ao log de submissão de jobs do renderer, quando
   uma futura fase retomar logging (fora do âmbito mínimo actual).
4. Se/quando uma fase futura introduzir observabilidade real (métricas,
   tracing, agregação de logs), revisitar a heterogeneidade de formato de log
   entre os três serviços.
5. Tratar B1–B6 (observabilidade real, logs centralizados, storage S3/R2,
   calibração de scores, CI/CD/staging contínuo, cofre de secrets) como
   backlog de uma fase de produção dedicada — fora do escopo desta fase.

---

## 14. Referências

- Backlog da fase: [`01_backlog.md`](01_backlog.md)
- Matriz operacional: [`matriz_operacional_servicos.md`](matriz_operacional_servicos.md)
- Runbook: [`runbook_arranque_staging.md`](runbook_arranque_staging.md)
- Checklist de troubleshooting: [`checklist_troubleshooting.md`](checklist_troubleshooting.md)
- Painel de prontidão: [`painel_prontidao_operacional.md`](painel_prontidao_operacional.md)
- Relatórios da fase: `resultados/prompt_01_analise_estado_operacional.md` …
  `resultados/prompt_10_estado_final_observabilidade_staging.md`
