# OBS-STG-009 — Relatório de execução: Painel de prontidão operacional

> Relatório de execução do prompt 09. **Apenas documentação** — nenhum ficheiro
> de runtime alterado. Não toca `intelligence_engine` nem `content_renderer`.
>
> Fase: Observabilidade e Staging Técnico do Ecossistema.
> Backlog: [`../01_backlog.md`](../01_backlog.md).
> Data: 2026-06-25.

---

## 1. Objectivo

Criar um painel textual honesto que avalie se o ecossistema está pronto para
piloto técnico controlado e explicite, separadamente, por que não está pronto
para produção.

---

## 2. Leitura preparatória

- [`01_backlog.md`](../01_backlog.md) — secção OBS-STG-009 (conteúdo mínimo) e
  §13 (relação com produção/futuro), usados para os blockers de produção.
- [`matriz_operacional_servicos.md`](../matriz_operacional_servicos.md) — §10
  (resumo de prontidão já esboçado) e §11 (itens "por confirmar").
- [`runbook_arranque_staging.md`](../runbook_arranque_staging.md) e
  [`checklist_troubleshooting.md`](../checklist_troubleshooting.md) — para
  confirmar o estado real da documentação operacional (§6 do painel).
- Todos os relatórios anteriores (`prompt_01` a `prompt_08`), em particular
  `prompt_01` (gaps G1–G10, riscos) e `prompt_03` (resultado exacto da suite de
  testes: "479 passed, 3 skipped"), para basear cada estado do painel em
  evidência já registada, em vez de reformular de memória.

---

## 3. Ficheiro criado

| Ficheiro | Acção |
|---|---|
| `docs/.../painel_prontidao_operacional.md` | **Criado** |

Estrutura: estado dos serviços (§1) · healthchecks (§2) · smoke tests (§3) ·
logs/correlação (§4) · segurança de secrets (§5) · documentação operacional
(§6) · blockers de produção (§7) · riscos em aberto (§8) · decisão de piloto
(§9) · decisão de produção (§10) · resumo executivo (§11) · referências (§12).

---

## 4. Decisões tomadas

- **Distinção explícita entre "implementado e testado com mocks" e "validado
  ao vivo".** Esta foi a decisão central do painel: por exemplo, o healthcheck
  agregado e os dois smoke tests têm cobertura de testes automatizados sólida
  (20 + 11 + 11 testes, todos a passar), mas **nenhum dos três serviços foi
  efectivamente arrancado em simultâneo durante esta fase** — por isso essas
  linhas estão marcadas **"ok" para a implementação/teste** mas com uma linha
  separada **"não executada"** para a validação ao vivo, em vez de misturar os
  dois níveis numa única afirmação optimista.
- **Estados aplicados item a item, não por bloco.** Em vez de dizer "logs:
  ok", cada campo de correlação (`request_id`, `external_job_id`,
  `duration_ms`, formato uniforme, etc.) tem o seu próprio estado
  (ok/parcial/pendente), reflectindo fielmente o que `prompt_06` já
  documentava como limitação (`duration_ms` do renderer, formato heterogéneo).
- **Blockers de produção listados como "bloqueado" por desenho do backlog**,
  não como falhas desta fase — o backlog (§4.2/§13) exclui explicitamente
  observabilidade real, S3/R2, calibração de negócio, CI/CD e gestão de
  secrets avançada do escopo. O painel reflecte isso em vez de tratar esses
  itens como trabalho em atraso.
- **Decisão de piloto com ressalva explícita**, não um "sim" incondicional: o
  painel declara prontidão para piloto **condicionada** a que alguém execute,
  de facto, o runbook e os smoke tests contra os três processos reais antes do
  piloto arrancar — porque essa execução real não aconteceu nesta fase.
- **B7 (discrepância de porta do report renderer)** classificado como
  **"parcial"**, não "bloqueado" nem "ok": está mitigado por documentação (em
  três documentos diferentes desta fase) mas o default no código ainda é
  `:8003`, criando risco residual se a variável não for definida explicitamente.

---

## 5. Verificação de ausência de secrets

Inspecção visual do documento: todos os valores de token/secret citados são
placeholders (`<DEV_TOKEN>`, `<INTERNAL_API_TOKEN>`, `<ACCESS_TOKEN>`). Nenhum
valor real de `SECRET_KEY`/`DB_PASSWORD`/`INTERNAL_API_TOKEN` foi incluído.

---

## 6. Pendências

| Item | Estado | Nota |
|---|---|---|
| Execução real do runbook + smoke tests contra os três serviços simultaneamente | **pendente** | Não executada em nenhum prompt desta fase (OBS-STG-001 a 009); recomendado como primeiro passo antes de um piloto real (painel §9). |
| Liveness público (sem auth) do `backend_core` | **pendente** | Já registado em OBS-STG-003/007; usa-se `GET /api/v1/schema/` como proxy entretanto. |
| `duration_ms` no log de submissão de jobs do renderer | **pendente** | Limitação já documentada em OBS-STG-006; fora do âmbito mínimo. |
| Correcção do default de `REPORT_RENDERER_BASE_URL` (`:8003`→`:8002`) no código | **pendente** | Hoje só mitigado por documentação (matriz/runbook/checklist); não foi pedido nem feito nesta fase um ajuste ao default em `config/settings.py`. |
| Documento de estado final da fase | **pendente** | Previsto para OBS-STG-010. |

---

## 7. Conformidade com os critérios de aceitação

| Critério | Estado |
|---|---|
| `painel_prontidao_operacional.md` existe | ✅ |
| Critérios de piloto estão claros | ✅ §9 do painel (lista de critérios cumpridos + ressalva explícita) |
| Critérios de produção estão claros | ✅ §10 do painel (6 blockers explícitos, ligados ao escopo do backlog) |
| Estado é honesto e baseado nas evidências disponíveis | ✅ cada linha do painel referencia o prompt/relatório/teste que a fundamenta |
| Validações não executadas não são apresentadas como concluídas | ✅ marcadas explicitamente "não executada" em §1/§2/§3/§4 do painel, distintas de "ok" (implementado/testado) |
| Relatório lista ficheiros criados/alterados, decisões, pendências, próximo passo | ✅ este documento |

---

## 8. Próximo passo recomendado

**OBS-STG-010 — Validação final, documentação e estado da fase.** Executar (ou
documentar honestamente como não executável no ambiente actual) `pytest`,
`manage.py check`, lint, e — se o ambiente permitir arrancar os três serviços —
o healthcheck agregado e os dois smoke tests reais; criar
`estado_observabilidade_staging_ecossistema.md` e o relatório final
`resultados/prompt_final_observabilidade_staging.md`, reutilizando este painel
como base para a declaração final de prontidão (piloto: sim / produção: não).
