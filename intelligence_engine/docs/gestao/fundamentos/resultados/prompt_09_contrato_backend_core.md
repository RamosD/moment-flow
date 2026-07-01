# Relatório de execução — Prompt 09: Contrato Backend Core ↔ Intelligence Engine

Preparação e documentação do **contrato de integração** entre o Backend Core
(Django) e o Intelligence Engine (FastAPI). Tarefa **de análise e documentação**
— sem código de runtime, sem alterações ao `backend_core` nem ao
`content_renderer`.

## Contexto consultado (sem alterações)

### Backend Core — `apps/integrations_bridge` (padrão de integração existente)

- `clients.py` — `InternalServiceClient` (HTTP JSON sobre `urllib`): headers
  internos (`X-Internal-Token`, `X-Workspace-ID`, `X-Job-ID`, `X-Request-ID`),
  token nunca registado, erros tipados (`timeout`/`unavailable`/`http_error`/
  `invalid_json`).
- `registry.py` — resolve `job_type → provider → (base_url, timeout)`; settings
  `INTELLIGENCE_ENGINE_BASE_URL`, `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS`,
  `EXTERNAL_JOBS_ENABLED`, `EXTERNAL_JOBS_DRY_RUN`, `callback_url()`.
- `services.py` — `create_and_submit_external_job`: modelo **assíncrono**
  (`POST /jobs/` + envelope + callback), idempotência `<job_type>:<entity_id>`,
  `retry_external_job`.
- `models.py` — `ExternalJobReference` (job types do IE: `metrics_collection`,
  `moment_detection`, `insight_generation`, `recommendation_generation`;
  estados, terminais, retryáveis).
- `intelligence.py` — builders/services **já preparados** para o IE, mas
  modelados como jobs assíncronos (shape `{workspace_id, campaign_id, track_id,
  platform_links, *_context}`).
- `docs/.../resultados/prompt_08_contratos_intelligence_engine.md` — relatório
  do Backend Core que confirma o scaffolding assíncrono e os handlers de
  callback placeholder.

### Content Renderer (serviço técnico externo de referência)

- `src/http/routes.ts` / `middleware.ts` — confirma o padrão: `GET /health`
  público + `POST /jobs` protegido por `X-Internal-Token` (comparação em tempo
  constante) + **callback** com o resultado. Assíncrono.

### Intelligence Engine (lado implementado, IE-004 → IE-008)

- Endpoints **síncronos** nomeados (`/analysis`, `/scoring`, `/recommendations`,
  `/moments`, `/intelligence`), `GET /health` público; auth `X-Internal-Token`
  (`hmac.compare_digest`); envelope de request/response e contrato de erro
  (§6.4/6.5); `config.py`/`.env.example` (token obrigatório em produção).

## Achado central (a divergência)

O scaffolding de integração do Backend Core assume o Intelligence Engine como um
serviço **assíncrono** (`POST /jobs/` + callback, à imagem do renderer), mas o
**MVP implementado do IE é síncrono** (resultado no corpo da resposta, sem
`/jobs/`, sem callbacks, sem persistência). Esta é exactamente a decisão
pendente **IE-PDEC-001**.

## Decisão recomendada

**Híbrido com síncrono como default do MVP (sync-first):**

- **Agora (MVP):** o Django chama o IE de forma **síncrona** (preferencialmente o
  endpoint composto `POST /intelligence/campaign`), reutilizando o
  `InternalServiceClient` já existente apontado ao endpoint nomeado — sem
  `ExternalJobReference`, sem callback. Justificação: o cálculo do IE é em
  memória, determinístico, sem I/O (sub-milissegundo); um job assíncrono seria
  custo sem benefício.
- **Futuro:** o caminho assíncrono `/jobs/`+callback (que o Django já tem)
  fica reservado para trabalho **pesado** que não pertence ao MVP do IE — em
  particular `metrics_collection` (recolha real de métricas) e inferência ML.

Esta recomendação alinha com o backlog (IE-PDEC-001/002) e reconcilia os dois
contratos sem alterar o IE.

## Comportamento documentado (no contrato)

O documento de contrato cobre, conforme pedido:

- **endpoints** (tabela; recomendação do composto como entrada preferida);
- **headers** (obrigatórios e recomendados; fonte de verdade no corpo);
- **autenticação** (`X-Internal-Token`, tempo constante, regras de token);
- **payloads** (envelope comum + `data` bundle permissivo);
- **respostas** (envelope de sucesso; dados insuficientes = `200` + warning);
- **erros** (envelope normalizado + tabela código↔HTTP↔acção);
- **timeouts** (sugestão 5–10 s; `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS`);
- **retry recomendado** (idempotente/seguro por ausência de efeitos colaterais;
  retentar timeout/unavailable/5xx, nunca 4xx);
- **síncrono vs job externo** (tabela de decisão + mapeamento `job_type` ↔
  endpoint);
- **persistência** (nenhuma no IE; Django decide snapshots);
- **exemplos** request/response (composto, dados insuficientes, erro) **com
  tokens placeholder**, sem secrets;
- **riscos** (INT-RSK-01..06) e **decisões pendentes** (PD-1..4 + IE-PDEC-001..004).

## Ficheiros criados/alterados

### Criados

```text
docs/gestao/fundamentos/contrato_backend_core_intelligence_engine.md   # o contrato
docs/gestao/fundamentos/resultados/prompt_09_contrato_backend_core.md  # este relatório
```

### Alterados

```text
README.md   # link para o contrato (topo + secção "Próximos passos" IE-009 ✅)
```

### Não alterados (apenas consultados)

```text
backend_core/**        # nenhuma alteração (análise read-only)
content_renderer/**    # nenhuma alteração (análise read-only)
```

Nenhuma alteração de código de runtime no Intelligence Engine.

## Comandos executados / validações

```bash
cd intelligence_engine
venv/Scripts/python.exe -m pytest -q       # 197 passed (inalterado — sem mudanças de código)
venv/Scripts/python.exe -m ruff check .    # All checks passed!
```

- Revisão do contrato: cobre todos os itens exigidos (endpoints, headers, auth,
  payloads, respostas, erros, timeouts, retry, sync vs job, persistência,
  exemplos, riscos, pendências).
- **Sem secrets reais**: os exemplos usam `<INTERNAL_API_TOKEN>` (placeholder);
  o `.env.example` do IE mantém `INTERNAL_API_TOKEN=` vazio.
- **Sem alterações indevidas**: confirmado que `backend_core` e
  `content_renderer` não foram tocados.

## Pendências

- **PD-1** Confirmar com a equipa do Backend Core a adopção do caminho síncrono
  para o IE (vs. manter os jobs assíncronos do scaffolding). Recomendação:
  síncrono.
- **PD-2** Definir/implementar no Django o **adaptador** que monta o `data`
  bundle do IE a partir dos modelos (`campaigns`/`catalogue`/`links`/`content`/
  `reports`). Hoje os builders de `integrations_bridge/intelligence.py` produzem
  um shape diferente.
- **PD-3** Decidir se/quando persistir snapshots de insight no Django.
- **PD-4** Fixar `INTELLIGENCE_ENGINE_TIMEOUT_SECONDS` e a política de retry no
  lado Django.
- O wiring real no Backend Core (chamada síncrona, adaptador de payload) **não**
  foi implementado nesta fase, por instrução (não alterar o Backend Core).

## Próximo passo recomendado

Avançar para **IE-010 — Testes, qualidade e documentação final**: garantir
testes/lint, criar o documento de estado
(`docs/.../05_estado_intelligence_engine.md`), documentar limitações e próximos
passos, confirmar ausência de secrets, e registar o estado pronto/não-pronto
para integração. Em paralelo (lado Backend Core, fora deste âmbito), abrir o
trabalho de ligar o caminho síncrono conforme o contrato (PD-1/PD-2).
