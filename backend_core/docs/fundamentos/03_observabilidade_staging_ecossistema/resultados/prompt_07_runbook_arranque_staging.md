# OBS-STG-007 — Relatório de execução: Runbook de arranque local/staging

> Relatório de execução do prompt 07. **Apenas documentação** — nenhum ficheiro
> de runtime alterado. Não toca `intelligence_engine` nem `content_renderer`.
>
> Fase: Observabilidade e Staging Técnico do Ecossistema.
> Backlog: [`../01_backlog.md`](../01_backlog.md).
> Data: 2026-06-25.

---

## 1. Objectivo

Criar um runbook prático e executável para arrancar e validar o ecossistema
local/staging (`backend_core` + `intelligence_engine` + `content_renderer`).

---

## 2. Leitura preparatória

- [`01_backlog.md`](../01_backlog.md) — secção OBS-STG-007 (conteúdo mínimo e
  critérios de aceitação) e §8/§9 (ordem de arranque, modos local/staging já
  esboçados no OBS-STG-002).
- [`matriz_operacional_servicos.md`](../matriz_operacional_servicos.md) — fonte
  de verdade de portas, comandos, variáveis, dependências e da discrepância de
  porta do report renderer (G9).
- [`smoke_intelligence_engine.md`](../smoke_intelligence_engine.md) e
  [`smoke_content_renderer.md`](../smoke_content_renderer.md) — comandos exactos
  dos smoke tests, reutilizados no runbook em vez de reescritos do zero.
- Relatórios anteriores (`prompt_01`…`prompt_06`) — confirmação de que o
  healthcheck agregado (OBS-STG-003), os dois management commands de smoke
  (OBS-STG-004/005) e o `LOGGING` (OBS-STG-006) já existem e podem ser
  referenciados directamente no runbook.

---

## 3. Ficheiro criado

| Ficheiro | Acção |
|---|---|
| `docs/.../runbook_arranque_staging.md` | **Criado** |

Conteúdo (secções, mapeadas ao "conteúdo mínimo" pedido):

1. Pré-requisitos (Python 3.13, Node ≥18.18, PostgreSQL opcional, Docker
   opcional, PowerShell, `curl`).
2. Directórios e portas (tabela de referência rápida + nota sobre a
   discrepância de porta do report renderer).
3. Variáveis de ambiente mínimas (um bloco `.env` por serviço, só placeholders).
4. Ordem de arranque recomendada (DB opcional → backend_core → IE → renderer →
   healthchecks → smoke tests), com subsecções de comando por serviço.
5. Validação de `GET /health` de cada serviço (IE/renderer públicos; proxy de
   liveness do Django via `/api/v1/schema/`, já que não existe `/health` público
   próprio).
6. Execução do healthcheck agregado (`/api/v1/system/health/dependencies/`,
   staff-only, com exemplo de resposta e os 3 códigos de erro de autorização).
7. Execução do smoke test do Intelligence Engine (comando + opt-in pytest,
   reaproveitando o guia OBS-STG-004).
8. Execução do smoke test do Content Renderer (Camada 1 + Camada 2,
   reaproveitando o guia OBS-STG-005).
9. Como parar os três serviços e o PostgreSQL do harness.
10. Como limpar artefactos locais (SQLite, storage do renderer, evidência E2E,
    PostgreSQL efémero).
11. Problemas comuns (10 entradas: token desalinhado, porta errada, callback
    404 em SQLite, healthcheck 401/403, porta ocupada, smokes a falhar,
    guardas fail-fast do IE/renderer/Django).
12. Referências cruzadas (matriz, guias de smoke, backlog, harness E2E).

---

## 4. Decisões tomadas

- **Reutilização, não duplicação:** os comandos exactos dos smoke tests (com
  todas as variantes de flags) já estão documentados em
  `smoke_intelligence_engine.md` e `smoke_content_renderer.md`; o runbook
  **referencia** esses guias e só reproduz o comando mínimo necessário para o
  fluxo de arranque, evitando duas fontes de verdade divergentes.
- **PostgreSQL tratado como opcional e explicitamente isolado (§4.3 / §7):** o
  arranque local simples (SQLite) é suficiente para validar IE e a perna de
  saída do renderer (202); o PostgreSQL só é necessário para o **loop completo**
  com callback, conforme já estabelecido em OBS-STG-005. Isto evita sugerir uma
  dependência pesada (Docker/Postgres) como obrigatória para um arranque local
  básico.
- **`backend_core` sem `/health` público próprio:** documentado o uso de
  `GET /api/v1/schema/` como *proxy* de liveness sem auth (consistente com a
  nota já registada na matriz, item "por confirmar" de OBS-STG-003), em vez de
  inventar um endpoint que não existe.
- **Referência condicional ao checklist de troubleshooting:** a secção 11
  ("Problemas comuns") cobre os casos mais imediatos do **arranque**
  (alinhamento de token, portas, guardas fail-fast), e remete para
  `checklist_troubleshooting.md` (OBS-STG-008) para diagnóstico mais
  exaustivo — **esse ficheiro ainda não existe** nesta fase (confirmado por
  inspecção do directório); o link fica pronto a resolver quando OBS-STG-008
  for executado, sem bloquear este runbook.
- **Token único de dev:** segue a convenção já usada nos guias anteriores —
  `<DEV_TOKEN>` como placeholder único, com a instrução explícita de usar o
  **mesmo valor literal** nos três serviços.

---

## 5. Verificação de ausência de secrets

- Inspecção visual do documento criado: todos os valores de `INTERNAL_API_TOKEN`/
  `SECRET_KEY`/`DB_PASSWORD` usam placeholders (`<DEV_TOKEN>`, `<SECRET_KEY>`,
  `<DB_PASSWORD>`) — nenhum valor real.
- Os únicos valores literais não-placeholder são `dev-local-token-only` (citado
  apenas como **exemplo ilustrativo** de "qualquer string não-vazia", não um
  segredo real reutilizável) e o `<ACCESS_TOKEN>` JWT do exemplo de healthcheck
  (placeholder).

---

## 6. Limitações

- **Não foi executado nenhum arranque real** dos três serviços nesta sessão
  (ambiente de execução não tem os processos a correr) — o runbook foi validado
  por **inspecção cruzada** com os relatórios/documentos já produzidos
  (matriz operacional, guias de smoke, código dos management commands), não por
  execução end-to-end neste momento. **Como validar:** seguir o runbook
  passo-a-passo num ambiente com os três serviços disponíveis e confirmar cada
  comando.
- **Host/bind de staging** (`--host` do uvicorn, bind do Node) continua "por
  confirmar" — já assinalado na matriz operacional (§11) e repetido aqui na
  secção 4.2 do runbook com a forma de validar (`curl http://<host>:<porta>/health`).
- **Checklist de troubleshooting** (OBS-STG-008) ainda não existe; a secção 11
  do runbook cobre apenas os problemas mais directamente ligados ao arranque,
  não um diagnóstico exaustivo.

---

## 7. Conformidade com os critérios de aceitação

| Critério | Estado |
|---|---|
| `runbook_arranque_staging.md` existe | ✅ |
| Comandos estão claros | ✅ um bloco PowerShell por passo, com saída esperada onde aplicável |
| Ordem de arranque está clara | ✅ §4 (lista numerada + subsecções por serviço) |
| Healthchecks e smoke tests estão incluídos | ✅ §5–§8 |
| Não há secrets reais no documento | ✅ ver §5 deste relatório |
| Relatório lista ficheiros criados/alterados, decisões, limitações, próximo passo | ✅ este documento |

---

## 8. Próximo passo recomendado

**OBS-STG-008 — Checklist de troubleshooting.** Cobrir os 14 casos listados no
backlog (IE indisponível/403/422/500, renderer indisponível/sem callback,
callback sem actualização de job, token desalinhado, URL errada, timeout,
payload inválido, RBAC, porta ocupada, DB indisponível), cada um com sintomas,
causa provável, comando de verificação e acção recomendada — reutilizando a
secção 11 deste runbook como ponto de partida e expandindo-a.
