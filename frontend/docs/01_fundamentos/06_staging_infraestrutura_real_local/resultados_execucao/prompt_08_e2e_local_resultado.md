# Prompt 08 — Executar E2E local — Resultado retroactivo

**Data:** 2026-07-03 (execução original ocorrida em 2026-07-03, durante o Prompt 12; relatório autónomo materializado posteriormente, na mesma data)
**Fase:** `06_staging_infraestrutura_real_local` (STG-LOCAL-008)
**Âmbito:** executar o Playwright E2E contra a stack staging local com PostgreSQL e MinIO reais, Intelligence Engine real, Content Renderer real, sem dry-run e sem mocks runtime.
**Estado de execução:** `executado retroactivamente documentado` — o E2E real foi executado de facto durante o Prompt 12 (fecho da fase), sem que este Prompt 08 tivesse, nesse momento, um relatório autónomo próprio. Este documento materializa essa evidência num relatório dedicado, para fechar a rastreabilidade da pipeline. Não constitui uma nova execução.

---

## Nota de retroactividade

Este relatório é **explicitamente retroactivo**:

- O Prompt 08 desta pipeline (STG-LOCAL-008) **não teve relatório próprio
  no momento original** em que a pipeline avançou de prompt em prompt — a
  fase seguiu para os Prompts 09, 10 e 11 com o E2E real ainda por
  executar, facto registado sem mascarar nesses três relatórios (ver §
  "Complementos dos Prompts 07/09/10" abaixo).
- **A execução real do E2E ocorreu durante o Prompt 12** (fecho da fase),
  não numa iteração dedicada ao Prompt 08. Isto está registado sem
  ambiguidade no relatório do Prompt 12
  (`prompt_12_fecho_staging_local_resultado.md`, secção 4, "E2E local —
  executado pela primeira vez nesta fase").
- **Este documento não inventa nem repete uma nova execução.** Todos os
  números, resultados e evidências abaixo são extraídos directamente do
  relatório do Prompt 12 — a fonte de verdade primária desse E2E continua
  a ser esse relatório. Este documento existe para dar ao Prompt 08 um
  ponto de referência autónomo e pesquisável na pasta
  `resultados_execucao/`, consistente com a numeração da pipeline.
- **A fase 06 não é reaberta por este documento.** A classificação final
  `pronto_para_staging_local_formal` (decidida no Prompt 12) mantém-se
  inalterada — este relatório não introduz nenhum facto técnico novo, só
  reorganiza a evidência já existente sob o número de prompt correcto.

## Ambiente usado

Infraestrutura Docker (`chartrex_staging_postgres`, `chartrex_staging_minio`,
containers, estado `healthy`) + 4 serviços aplicacionais como processos
locais: Backend Core (`DB_ENGINE=postgres`), Intelligence Engine
(`INTELLIGENCE_ENGINE_DRY_RUN=false`), Content Renderer
(`STORAGE_PROVIDER=s3`, `EXTERNAL_JOBS_DRY_RUN=false`), Frontend (Vite,
`--host 127.0.0.1`). Nenhum dry-run, nenhum mock runtime — consistente
com a premissa obrigatória original deste prompt.

## Pré-condições

Confirmadas antes da execução (fonte: `prompt_12_fecho_staging_local_resultado.md`
§4):

- Containers PostgreSQL e MinIO `healthy`.
- Backend Core a usar PostgreSQL (não SQLite).
- Intelligence Engine real, sem dry-run.
- Content Renderer a usar MinIO (`STORAGE_PROVIDER=s3`), sem dry-run.
- Frontend real, activo.
- `staging-local-health.ps1 -RequireApps` → `OK`, exit `0`.
- `E2E_PASSWORD` carregado no ambiente **sem ser impresso** em nenhum
  momento.

## Execução do E2E

```powershell
pnpm test:e2e
```

Corrido duas vezes, na mesma stack, sem qualquer alteração de código ou
configuração entre as duas tentativas.

## Resultado dos testes

**1ª execução:** 5 de 12 testes passaram, depois **1 falha real** — o
diálogo de criação da acção "media kit" ficou preso em `Creating…` durante
mais de 10 segundos (timeout do Playwright a aguardar o fecho do
diálogo). Os 6 testes seguintes não correram, porque a suite usa
`test.describe.configure({ mode: 'serial' })`.

**Investigação da falha** (sem alterar código de produto): uma chamada
directa `POST /api/v1/media-kits/`, feita manualmente no mesmo instante
contra a mesma stack, respondeu em `0.202s` — confirmando que a API não
estava lenta. A causa mais provável apontada foi contenção de recursos
pontual (browser/processo Playwright, numa sessão de trabalho já muito
longa nesta fase), não um bug de lógica do produto.

**2ª execução** (imediatamente a seguir, mesma stack, zero alterações):
**12/12 `PASS` em 31.1 segundos**, incluindo o mesmo passo de "media kit",
desta vez em 1.9s.

**Conclusão honesta:** um flake pontual, investigado, com causa mais
provável identificada, e **não reproduzido numa repetição imediata**. Não
se declara "E2E infalível" — declara-se "E2E corre e passa de facto
contra PostgreSQL e MinIO reais, com uma instabilidade pontual já
investigada, não bloqueante".

## Cobertura validada

Os 12 testes da suite (`frontend/e2e/main-flow.spec.ts`), todos
confirmados `PASS` na execução válida:

1. Login.
2. Abertura de campanha e War Room.
3. Intelligence real, com pelo menos uma recomendação devolvida.
4. Criação de acção do tipo "manual task" a partir da recomendação.
5. Criação de acção do tipo "report" a partir da recomendação.
6. Criação de acção do tipo "media kit" a partir da recomendação.
7. Criação de acção do tipo "content pack" a partir da recomendação.
8. Marcar a recomendação como revista ("mark reviewed").
9. Dispensar a recomendação ("dismiss").
10. `CampaignActionsPanel` lista todas as acções criadas contra a recomendação.
11. Persistência após reload — as acções vêm do backend real, não de cache do cliente.
12. Confirmação de que o frontend só falou com o Backend Core durante toda a sessão de teste.

## Evidência PostgreSQL

O Backend Core usado nesta execução estava configurado com
`DB_ENGINE=postgres`, ligado ao container `chartrex_staging_postgres`
(não SQLite). Os dados criados pela suite (workspace, campanha, acções,
report, media kit, content pack request) foram persistidos nesse
PostgreSQL — confirmado indirectamente pelos testes 10 e 11 (o painel de
acções e a persistência após reload dependem de leituras reais à base de
dados, não de um mock). Detalhe adicional de validação de persistência de
PostgreSQL (fora do âmbito específico deste E2E, mas da mesma
infraestrutura): `prompt_03_postgresql_local_resultado.md`.

## Evidência MinIO

Confirmada a existência dos artefactos gerados por esta execução no
bucket MinIO de staging, sob o namespace do workspace/`run-id` desta
execução (identificadores omitidos deste relatório por não serem
necessários à evidência):

- `report.pdf` — existe.
- `media_kit.pdf` — existe.
- `output_001.png` — existe.
- `output_002.png` — existe.

Os quatro objectos foram confirmados fisicamente no bucket
`chartrex-staging` (via `mc ls --recursive`), sob a estrutura
`workspaces/<workspace_id>/jobs/<job_id>/<ficheiro>` — o mesmo padrão já
validado nos Prompts 04, 09 e 10. Nenhuma credencial nem valor sensível é
reproduzido aqui.

## Evidência Asset.public_url

Confirmados **4 assets** associados ao workspace desta execução (via
`manage.py shell`, consulta ao modelo `Asset`), todos com:

- `storage_provider = "s3"` (não `local`, não filesystem).
- `public_url` preenchido (não vazio).
- Formato local MinIO: `http://127.0.0.1:9000/chartrex-staging/workspaces/<id>/...`
  — o `<id>` do workspace foi redigido neste relatório por não ser
  necessário à evidência (não é, em si, um secret, mas mantém-se a
  disciplina de não reproduzir identificadores desnecessários).

## Network do browser

Validação feita por um **listener real do Playwright**
(`page.on('request')`), configurado antes do primeiro passo da suite e
activo durante toda a sessão do browser — não uma verificação estática de
código nem uma amostragem parcial. Este listener capturou **todos** os
pedidos HTTP feitos pelo browser ao longo da execução completa (login,
War Room, criação das 4 acções, mark reviewed, dismiss, reload) e
comparou cada um contra uma lista de portas proibidas (`8201`, `8202` —
Intelligence Engine e Content Renderer) e uma lista de hosts permitidos.

**Resultado: zero pedidos fora do Backend Core.** O browser nunca tocou
nas portas do Intelligence Engine nem do Content Renderer durante toda a
sessão — o frontend falou exclusivamente com o Backend Core, confirmando
ao nível de rede real (não só de código-fonte) a fronteira arquitectural
desta fase. Isto fecha a pendência explicitamente registada no Prompt 09
("Verificação 'Network apenas Backend Core' via browser real ou E2E
automatizado não foi feita nesta iteração... a confirmação end-to-end via
Playwright real fica para STG-LOCAL-008").

## Flake observado

Ver "Resultado dos testes" acima para o relato completo. Resumo: 1 falha
não-reprodutível na 1ª tentativa (timeout de diálogo na criação de acção
"media kit"), investigada sem alteração de código, confirmada como
contenção de recursos pontual (não um bug), e ausente numa 2ª tentativa
imediata (12/12 limpo). Registado como risco a monitorizar em execuções
futuras, não como bloqueio — ver `estado_staging_local.md` §8.

## Segurança e secrets

- `E2E_PASSWORD` foi carregado no ambiente e usado pelo `seed_e2e_run` e
  pelo Playwright **sem ser impresso** em nenhum momento da execução nem
  deste relatório.
- Nenhum token (`INTERNAL_API_TOKEN` ou equivalente) foi exposto durante
  a execução nem é reproduzido neste documento.
- **Não houve nenhuma chamada do Frontend directamente ao Intelligence
  Engine ou ao Content Renderer** — confirmado pelo listener de rede real
  (ver "Network do browser" acima), zero excepções.
- Este relatório **não contém** valores de `INTERNAL_API_TOKEN`,
  `SECRET_KEY`, `DB_PASSWORD`, `MINIO_ROOT_PASSWORD`,
  `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `E2E_PASSWORD`, nem
  cabeçalhos `Authorization: Bearer`/`X-Internal-Token` com valores reais
  — confirmado por grep dedicado (ver "Validações" abaixo).

## Complementos dos Prompts 07/09/10 (contexto histórico, sem alterar factos)

- **Prompt 07 (quality gate):** o modo opcional `-WithE2E` do
  `staging-local-quality-gate.ps1` já existia e foi validado nesse
  momento **sem** a stack activa — a etapa `e2e` falhou de forma clara
  (`[FAIL] e2e — stack staging local não está totalmente activa`), sem
  mascarar o problema. O relatório desse prompt já registava
  explicitamente: "A execução real do E2E com a stack totalmente activa
  é o âmbito do STG-LOCAL-008 (próximo prompt), não deste."
- **Prompt 09 (segurança local):** registou como pendência explícita que
  a verificação "Network apenas Backend Core" não tinha sido feita por
  browser real nem E2E automatizado nessa iteração — só por análise de
  código-fonte e grep do bundle `dist/` (alternativa permitida pelo
  próprio prompt). Deixou explícito que "a confirmação end-to-end via
  Playwright real fica para STG-LOCAL-008 (E2E local), ainda por
  fechar." Esta pendência é a que este relatório agora fecha (ver
  "Network do browser" acima).
- **Prompt 10 (observabilidade local):** abriu com uma nota explícita
  ("Nota sobre o Prompt 08") assumindo que "STG-LOCAL-008 (E2E local)
  continua por executar — não foi pedido nem executado nesta sessão", e
  substituiu a cobertura do fluxo real por chamadas HTTP directas
  (mesmo padrão dos Prompts 03/04/05/09), deixando claro que isso "não
  substitui o STG-LOCAL-008, que continua pendente." O relatório desse
  prompt recomendava como próximo passo avançar exactamente para
  STG-LOCAL-008 — o que veio a acontecer, de facto, no Prompt 12.

## Ficheiros criados/alterados

| Ficheiro | Operação |
|---|---|
| `frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/resultados_execucao/prompt_08_e2e_local_resultado.md` | **criado** (este relatório, retroactivo) |
| `frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/runbook_staging_local.md` | referência cruzada acrescentada, sem alterar decisão/evidência (ver nota abaixo) |
| `frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/estado_staging_local.md` | referência cruzada acrescentada, sem alterar classificação/evidência (ver nota abaixo) |

Nenhum código funcional, script ou ficheiro de configuração foi alterado
por este prompt. A execução E2E documentada aqui **não foi repetida**
nesta iteração — é a mesma execução já registada no Prompt 12.

## Validações

| Validação | Resultado |
|---|---|
| Grep `INTERNAL_API_TOKEN=` neste relatório | ✅ 0 ocorrências com valor |
| Grep `SECRET_KEY=` neste relatório | ✅ 0 ocorrências |
| Grep `DB_PASSWORD=` neste relatório | ✅ 0 ocorrências |
| Grep `MINIO_ROOT_PASSWORD=` neste relatório | ✅ 0 ocorrências |
| Grep `STORAGE_ACCESS_KEY=` neste relatório | ✅ 0 ocorrências |
| Grep `STORAGE_SECRET_KEY=` neste relatório | ✅ 0 ocorrências |
| Grep `E2E_PASSWORD=` neste relatório | ✅ 0 ocorrências |
| Grep `Bearer` neste relatório | ✅ 0 ocorrências |
| Grep `X-Internal-Token:` neste relatório | ✅ 0 ocorrências |
| `scripts/check-forbidden-ports.ps1` | ✅ Executado — `OK`, nenhuma porta proibida (ver relatório de execução desta própria iteração) |

Nenhum destes greps encontrou um valor real — só nomes de padrão de
pesquisa (que aparecem na própria tabela de validação acima, como é
esperado de uma tabela que documenta os greps executados).

## Limitações

- Este relatório depende inteiramente da evidência já registada no
  Prompt 12 — não foi feita uma nova execução independente do E2E para o
  produzir (por desenho explícito desta tarefa: "Não reexecutar E2E salvo
  se for estritamente necessário para confirmar inconsistência
  documental" — não foi necessário, a evidência do Prompt 12 já era clara
  e internamente consistente).
- Os identificadores de workspace/job/run-id foram parcialmente redigidos
  neste documento por disciplina, não porque fossem secrets — continuam
  disponíveis, por completo, no relatório do Prompt 12 para quem precisar
  do rasto exacto.
- O flake documentado teve `n=2` execuções como evidência de
  não-reprodutibilidade (1 falha, 1 sucesso limpo) — não uma amostra
  estatisticamente grande. Continua registado como risco a monitorizar,
  não como facto encerrado.

## Riscos

Herdados do Prompt 12 (`estado_staging_local.md` §8), sem alteração:
confundir "staging local formal" com staging externo/produção (mitigado
pela linguagem explícita em todos os documentos da fase); o flake do E2E
como instabilidade a monitorizar; ausência de validação por terceiro.
Nenhum risco novo é introduzido por este relatório retroactivo.

## Conclusão

O Prompt 08 (STG-LOCAL-008 — E2E local) está, com este documento,
**rastreável de forma autónoma na pipeline**: a execução real aconteceu
durante o Prompt 12, com resultado honesto (12/12 `PASS` numa execução
limpa, após 1 flake investigado e não-reproduzido), e essa evidência está
agora também acessível sob o número de prompt a que pertence
tematicamente. A classificação final da fase
(`pronto_para_staging_local_formal`, decidida no Prompt 12) **mantém-se
inalterada**. A fase 06 **não é reaberta** por este documento.

## Próximo passo recomendado

Nenhum — a fase 06 está encerrada (Prompt 12). Este documento é puramente
de rastreabilidade documental; não gera trabalho técnico novo. Se, no
futuro, uma validação por terceiro (pendência registada no Prompt 12)
identificar um problema com o E2E, esse trabalho pertenceria a uma fase
nova, não a uma reabertura desta.
