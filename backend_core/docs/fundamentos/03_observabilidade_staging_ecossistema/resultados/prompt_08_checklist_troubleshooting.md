# OBS-STG-008 — Relatório de execução: Checklist de troubleshooting

> Relatório de execução do prompt 08. **Apenas documentação** — nenhum ficheiro
> de runtime alterado. Não toca `intelligence_engine` nem `content_renderer`.
>
> Fase: Observabilidade e Staging Técnico do Ecossistema.
> Backlog: [`../01_backlog.md`](../01_backlog.md).
> Data: 2026-06-25.

---

## 1. Objectivo

Criar uma checklist prática de troubleshooting para os 14 casos exigidos pelo
backlog (+2 adicionais já antecipados em OBS-STG-007), utilizável por alguém
que não implementou o código.

---

## 2. Leitura preparatória

- [`01_backlog.md`](../01_backlog.md) — secção OBS-STG-008 (lista de 14 casos e
  critérios de aceitação).
- [`matriz_operacional_servicos.md`](../matriz_operacional_servicos.md) — portas,
  variáveis, discrepância de porta do report renderer (G9), guardas fail-fast.
- [`runbook_arranque_staging.md`](../runbook_arranque_staging.md) — §11
  ("Problemas comuns") reutilizada como ponto de partida, agora expandida com
  causa/confirmação/logs/escalonamento por caso.
- `prompt_06_correlacao_logs.md` — campos de log disponíveis por fluxo
  (`request_id`, `workspace_id`, `job_id`, `external_job_id`, `provider`,
  `duration_ms`, `error_type`/`error_code`), usados para preencher a coluna
  "Logs/campos úteis" de cada caso com nomes reais, não inventados.
- Para fundamentar causas/sintomas com precisão, foi inspeccionado o código
  (apenas leitura, sem alteração) de:
  `apps/integrations_bridge/intelligence_sync.py` (erros tipados do cliente IE:
  `IntelligenceEngineTimeout`/`Unavailable`/`ResponseError`/`ProtocolError`,
  mapeamento 4xx-não-retry vs 5xx-retry),
  `apps/campaigns/intelligence_service.py` (erros de serviço:
  `IntelligenceDisabledError`/`UnavailableError`/`UpstreamError` → 503/502),
  `apps/campaigns/views.py` (RBAC/workspace: 404 para cross-workspace, em vez
  de 403, por desenho),
  `apps/integrations_bridge/clients.py` (excepções de transporte:
  `InternalClientTimeout`/`InternalServiceUnavailable`/`InternalHTTPError`/
  `InvalidJSONResponse`),
  `apps/integrations_bridge/views.py` (`ExternalJobCallbackView._resolve_job` —
  base do Caso 7, callback sem correspondência de `job_id`).

---

## 3. Ficheiro criado

| Ficheiro | Acção |
|---|---|
| `docs/.../checklist_troubleshooting.md` | **Criado** |

Estrutura: secção "Como usar" + índice de 16 casos + uma secção por caso
(sintoma / causa provável / como confirmar / acção recomendada / logs e campos
úteis / quando escalar) + comandos de verificação de referência + critério
geral de escalonamento + referências cruzadas.

---

## 4. Cobertura

### 4.1 Casos exigidos pelo backlog (14/14)

| # backlog | Caso | Cobertura |
|---|---|---|
| 1 | Intelligence Engine indisponível | ✅ Caso 1 |
| 2 | Intelligence Engine devolve 403 | ✅ Caso 2 |
| 3 | Intelligence Engine devolve 422 | ✅ Caso 3 |
| 4 | Intelligence Engine devolve 500 | ✅ Caso 4 |
| 5 | Content Renderer indisponível | ✅ Caso 5 |
| 6 | Content Renderer não faz callback | ✅ Caso 6 |
| 7 | Callback chega mas job não actualiza | ✅ Caso 7 |
| 8 | Token interno desalinhado | ✅ Caso 8 |
| 9 | URL configurada errada | ✅ Caso 9 (inclui G9: porta 8002 vs 8003) |
| 10 | Timeout | ✅ Caso 10 |
| 11 | Payload inválido | ✅ Caso 11 |
| 12 | Erro de workspace/RBAC | ✅ Caso 12 |
| 13 | Porta ocupada | ✅ Caso 13 |
| 14 | Base de dados indisponível | ✅ Caso 14 |

### 4.2 Casos adicionais (referenciados no prompt do OBS-STG-008, fora da lista mínima do backlog)

| Caso | Cobertura |
|---|---|
| Healthcheck agregado em `degraded` | ✅ Caso 15 |
| Logs sem `request_id`/`job_id` | ✅ Caso 16 |

Todos os 16 casos seguem o mesmo formato de 6 campos pedido no prompt
(sintoma, causa provável, como confirmar, acção recomendada, logs/campos
úteis, quando escalar).

---

## 5. Decisões tomadas

- **Causas fundamentadas no código real, não genéricas:** cada "causa provável"
  reflecte o comportamento efectivamente implementado (ex.: Caso 7 explica que
  o `404` do callback do `smoke_content_renderer` é **esperado e inofensivo**,
  porque esse command não escreve `ExternalJobReference`; Caso 12 explica que
  acesso cross-workspace devolve **404**, não 403, por desenho de
  `WorkspaceScopedRBACViewSet`/`get_object()`). Isto evita que alguém sem
  contexto do código trate um comportamento normal como bug.
- **Distinção 4xx (não retry) vs 5xx (retry) no IE:** Casos 2/3 (4xx) vs Caso 4
  (5xx) reflectem `IntelligenceEngineClient.post_campaign_intelligence`, que
  **não** repete em `403`/`422` mas repete em `5xx` até
  `INTELLIGENCE_ENGINE_MAX_RETRIES` — relevante para quem está a diagnosticar
  "porque é que demorou X segundos antes de falhar".
- **"Quando escalar" como critério de fronteira, não de "não sei":** cada caso
  define explicitamente a condição que separa "ainda diagnosticável por esta
  checklist" de "precisa de alguém com acesso ao código do
  `intelligence_engine`/`content_renderer`" — consistente com a regra da fase
  de não alterar esses dois serviços e não assumir conhecimento do seu código
  interno.
- **Reutilização da secção 11 do runbook:** os 10 problemas comuns já
  documentados em `runbook_arranque_staging.md` foram a base de partida; aqui
  foram expandidos para o formato de 6 campos e completados com os casos que o
  runbook não cobria (422, 500, callback sem actualização, RBAC, healthcheck
  degraded, logs sem correlação).
- **Comandos de verificação só com placeholders:** secção 2 do documento lista
  os comandos mais repetidos (curl de healthcheck, smoke tests, nível de log,
  porta ocupada, estado do PostgreSQL) num único bloco de referência, todos com
  `<ACCESS_TOKEN>`/`<DEV_TOKEN>` como placeholder — nunca um valor literal.

---

## 6. Verificação de ausência de secrets

- Inspecção visual do documento: todos os tokens/credenciais usam placeholders
  (`<DEV_TOKEN>`, `<ACCESS_TOKEN>`). Nenhum valor real de
  `INTERNAL_API_TOKEN`/`SECRET_KEY`/`DB_PASSWORD`.
- Nenhuma instrução do documento sugere logar ou imprimir o valor de um token —
  pelo contrário, cada caso relevante (2, 8, 16) reforça explicitamente que o
  estado do token é reportado como `configured`/`not_configured`, nunca o
  valor, e a secção 3 ("Quando escalar") repete essa regra para qualquer
  evidência levada para fora deste documento.

---

## 7. Limitações

- **Não foi executado nenhum cenário real de falha** nesta sessão (sem
  processos a correr) — os sintomas/causas foram fundamentados por leitura do
  código (excepções tipadas, condições de retry, lógica de resolução de job),
  não por reprodução ao vivo. **Como validar:** reproduzir deliberadamente cada
  caso (ex.: desligar o IE, desalinhar o token, submeter payload inválido) num
  ambiente com os três serviços a correr, e confirmar que o sintoma/log
  descrito corresponde.
- **Caso 4 (IE 500)** depende de uma falha interna do próprio `intelligence_engine`,
  que está fora do código inspeccionado nesta fase (não se altera esse
  serviço) — a checklist documenta como **confirmar e isolar** o sintoma do
  lado do Backend Core, mas não pode prescrever a causa raiz dentro do IE.
- **Caso 6 (sem callback)** assume que a causa mais comum em ambiente local é
  SQLite multi-processo (já documentado nas fases anteriores); outras causas de
  rede/firewall em staging não foram exploradas em detalhe, por não haver
  ambiente de staging real disponível para inspecção.

---

## 8. Conformidade com os critérios de aceitação

| Critério | Estado |
|---|---|
| `checklist_troubleshooting.md` existe | ✅ |
| Cada caso tem sintoma, causa provável, confirmação e acção recomendada | ✅ + logs/campos úteis + quando escalar (6 campos, acima do mínimo pedido) |
| Inclui comandos úteis | ✅ por caso + secção 2 consolidada |
| Não expõe secrets | ✅ ver §6 deste relatório |
| É utilizável por alguém fora da implementação | ✅ linguagem orientada a sintoma observável, sem assumir leitura de código |
| Relatório lista ficheiros criados/alterados, cobertura, limitações, próximo passo | ✅ este documento |

---

## 9. Próximo passo recomendado

**OBS-STG-009 — Painel textual de prontidão operacional.** Consolidar, num
documento único e honesto, o estado de: serviços, healthchecks, smoke tests,
logs/correlação e segurança de secrets (já implementados/documentados em
OBS-STG-001 a 008), terminando com uma decisão explícita e separada para
"pronto para piloto técnico" vs "pronto para produção" — reutilizando a secção
10 (Prontidão) já esboçada em `matriz_operacional_servicos.md` como ponto de
partida.
