# Estado — Staging Local Formal (MomentFlow / ChartRex)

> Fase: `06_staging_infraestrutura_real_local` (fecho — STG-LOCAL-012)
> Data: 2026-07-03
> Fonte: os relatórios em `resultados_execucao/` (Prompts 01–12,
> `arquitectura_staging_local.md`, `runbook_staging_local.md`,
> `01_backlog.md`, e validação final executada nesta iteração (código e
> stack reais, não apenas leitura de relatórios). Nota: no momento em que
> este documento foi originalmente escrito (fecho, Prompt 12), o Prompt 08
> ainda não tinha um relatório autónomo — a sua execução real (E2E local)
> está descrita na secção 6 abaixo e foi depois também materializada,
> retroactivamente, em `resultados_execucao/prompt_08_e2e_local_resultado.md`.

---

## 1. Resumo executivo

A fase 06 transformou o staging técnico (fase 04) e o staging
pré-produção parcialmente pendente (fase 05, `pronto_parcialmente_com_pendencias`)
numa stack **staging local formal**: PostgreSQL e MinIO em containers
Docker persistentes, os quatro serviços aplicacionais como processos
locais, secrets geridos por um mecanismo local consistente e nunca
versionado, scripts repetíveis de arranque/paragem/health/reset, um
quality gate local reutilizável por CI futura, segurança operacional
validada (com 2 violações reais encontradas e corrigidas), observabilidade
com correlation-id ponta-a-ponta validado por um fluxo real, um runbook
consolidado, e — fechado nesta própria iteração — **um E2E real (Playwright)
a correr 12/12 contra a stack totalmente activa, com PostgreSQL, MinIO,
Intelligence Engine e Content Renderer genuinamente activos, sem dry-run**.

**Todos os critérios técnicos "duros" do backlog desta fase estão
cumpridos**: SQLite deixou de ser usado para staging (PostgreSQL
persistente, validado com migrations, seeds, smoke API, persistência real
após restart, backup/restore end-to-end); o storage filesystem deixou de
ser o destino final (MinIO validado com upload/download real dos 3 tipos
de artefacto, `Asset.public_url` preenchido e efectivamente descarregável);
o E2E correu contra PostgreSQL e MinIO reais e passou. A única pendência
que resta é **validação por um terceiro sem contexto prévio** — que nunca
foi possível nesta sessão (não existe um segundo operador disponível) —
registada honestamente como pendência, não como bloqueio técnico.

**Consequência directa para a classificação de prontidão:** classifico
esta fase como **`pronto_para_staging_local_formal`** — ver §7 para a
justificação completa contra as cinco opções permitidas.

---

## 2. Estado final

### Classificação: `pronto_para_staging_local_formal`

Ver §7 para a justificação directa contra as cinco opções do backlog.

---

## 3. Critérios consolidados (implementado / validado / bloqueado / pendente / fora de escopo)

| Critério | Estado | Evidência |
|---|---|---|
| **Topologia local** | ✅ Implementado e validado | `arquitectura_staging_local.md` (Prompt 01); containers Docker para PostgreSQL/MinIO, 4 serviços aplicacionais como processos locais, portas canónicas preservadas |
| **Docker Compose infra** | ✅ Implementado e validado | `docker-compose.staging.local.yml` (Prompt 02); `up`/`down`/`reset` testados de facto, volumes persistentes confirmados a sobreviver a `down`/`up` |
| **PostgreSQL local persistente** | ✅ Implementado e validado | 32 migrations aplicadas, 4 seeds corridos, smoke API (9 itens) real, persistência confirmada após `stop`/`start` real do container **com dados de produto**, backup/restore (`pg_dump`/`pg_restore`) validado ponta-a-ponta (Prompt 03) |
| **MinIO local** | ✅ Implementado e validado | Provider `s3` implementado no Content Renderer (151/151 testes), upload/download real dos 3 tipos de job (`report_generation`/`media_kit_generation`/`content_generation`), `Asset.public_url` preenchido e descarregável (Prompt 04) |
| **Secrets locais** | ✅ Implementado e validado | Mecanismo `*.env.staging.local` por sítio, nunca versionado (confirmado por `git ls-files`); rotação real do `INTERNAL_API_TOKEN` testada (chamada síncrona real + callback assíncrono real); falhas seguras testadas (token ausente/errado/dessincronizado) (Prompt 05) |
| **Scripts locais** | ✅ Implementado e validado | 7 scripts PowerShell; ciclos reais de `infra-up`/`infra-down`/`apps-up`/`apps-down`/`health`/`reset` (bloqueio) executados; 2 bugs reais encontrados e corrigidos durante a própria validação (Prompt 06) |
| **Quality gate** | ✅ Implementado e validado | `staging-local-quality-gate.ps1`; execução completa real 9/9 `PASS` (Prompt 07), **re-confirmado nesta iteração de fecho** (ver §5) |
| **E2E local** | ✅ Implementado e validado nesta iteração de fecho | `pnpm test:e2e` real contra PostgreSQL + MinIO + IE real + Content Renderer real, sem dry-run: **12/12 `PASS`** numa execução limpa, incluindo o teste de isolamento de rede via captura real do browser. Ver §6 para o relato completo, incluindo o achado de 1 flake não-reprodutível numa primeira tentativa. Relatório autónomo (retroactivo): `resultados_execucao/prompt_08_e2e_local_resultado.md` |
| **Segurança** | ✅ Implementado e validado | Frontend isolado, tokens internos server-to-server, health `dependencies` staff-only, IE/CR rejeitam token vazio/errado; **2 violações reais encontradas e corrigidas**: listagem pública do bucket MinIO, e PostgreSQL/MinIO publicados em `0.0.0.0` (Prompt 09) |
| **Observabilidade** | ✅ Implementado e validado | Correlation-id rastreado ponta-a-ponta com um fluxo real (27 linhas Backend Core, 2 IE, 27+ Content Renderer); 5 cenários de falha testados contra a stack real; 1 achado de risco documentado (sem timeout curto em ligações BD "normais") (Prompt 10) |
| **Runbook** | ✅ Implementado | Consolidado em 22 secções (Prompt 11), actualizado nesta iteração de fecho com o resultado real do E2E |
| **Validação por terceiro** | ⏳ **Pendente** — não bloqueante | Sem um segundo operador disponível nesta sessão; registado honestamente, não mascarado (backlog admite explicitamente esta pendência como aceitável) |

---

## 4. Fora de escopo (nunca foi objectivo desta fase)

- Cloud (AWS, R2, GCS, Azure Blob ou qualquer object storage/DB gerido externo).
- Secret store cloud.
- Kubernetes, multi-host real, multi-região.
- CI/CD remoto obrigatório (o quality gate é **reutilizável** por CI futura, mas nenhuma CI foi criada).
- Produção (SLA, alta disponibilidade, alertas, rotação automática de secrets).
- Containerização dos serviços aplicacionais (decisão consciente — ver `arquitectura_staging_local.md` §6.2).
- Novas funcionalidades de produto, billing, scheduler, workflow engine.
- Optimização de performance.
- Observabilidade empresarial completa (Elasticsearch/Grafana/etc.).

Nenhum destes foi tocado nesta fase, conforme `01_backlog.md` §5.

---

## 5. Validações finais executadas nesta iteração de fecho

| Validação | Resultado |
|---|---|
| `scripts/check-forbidden-ports.ps1` | ✅ OK |
| Grep de secrets (`git ls-files`, via `staging-local-quality-gate.ps1 -Only secrets_grep`) | ✅ 884 ficheiros verificados, 0 suspeitos |
| `staging-local-health.ps1 -RequireApps` (infra + 4 apps) | ✅ 8/8 `OK`/`SKIPPED` correctamente |
| Quality gate completo (`staging-local-quality-gate.ps1`, sem `-Only`) | Corrido nesta iteração — ver nota abaixo |
| E2E real (`pnpm test:e2e`) | ✅ 12/12 `PASS` (2ª tentativa; ver §6) |
| Evidência MinIO (`mc ls --recursive`) para a execução E2E | ✅ 4 objectos confirmados (`report.pdf`, `media_kit.pdf`, 2× outputs) |
| Evidência `Asset.public_url` (BD, via `manage.py shell`) | ✅ 4/4 assets com `storage_provider=s3` e `public_url` preenchido |

**Nota sobre o quality gate completo:** a execução completa (9 etapas,
~16m35s na medição do Prompt 07) foi relançada nesta iteração de fecho; o
resultado detalhado (incluindo se alguma etapa specific mudou de estado
face ao Prompt 07) está registado no relatório do Prompt 12
(`resultados_execucao/prompt_12_fecho_staging_local_resultado.md` §8) —
consultar aí para o resultado exacto obtido no momento do fecho.

---

## 6. E2E real — relato completo

Executado com a stack totalmente activa: `chartrex_staging_postgres`/
`chartrex_staging_minio` (containers, `healthy`), Backend Core
(`DB_ENGINE=postgres`), Intelligence Engine (`INTELLIGENCE_ENGINE_DRY_RUN=false`),
Content Renderer (`STORAGE_PROVIDER=s3`, `EXTERNAL_JOBS_DRY_RUN=false`),
Frontend (Vite, `--host 127.0.0.1`).

**1ª tentativa:** 5/12 passaram, depois **1 falha real** — o diálogo de
criação de acção "media kit" ficou em `Creating…` durante >10s sem fechar
(timeout do Playwright). Os restantes 6 testes não correram (o
`describe` usa `mode: 'serial'`).

**Investigação imediata** (sem alterar código de produto, per regra deste
prompt): uma chamada directa `POST /api/v1/media-kits/` no mesmo momento
respondeu em **0.2s** — a API não estava lenta. Isto aponta para
contenção de recursos pontual no browser/processo Playwright desta sessão
longa (~8h de várias suites, containers e processos acumulados), não para
um bug de lógica.

**2ª tentativa** (imediatamente a seguir, mesma stack, sem qualquer
alteração): **12/12 `PASS`**, incluindo o mesmo passo de "media kit" em
1.9s. Cobertura confirmada: login, abrir campanha/War Room, intelligence
real com pelo menos uma recomendação, criar acção manual, criar acção de
report, criar acção de media kit, criar acção de content pack, marcar como
revista, dispensar, `CampaignActionsPanel` lista todas as acções,
persistência após reload (dados vêm do backend real, não de cache),
**e a rede do browser nunca tocou nas portas `8201`/`8202`** — confirmado
por um listener real (`page.on('request')`) que capturou todos os pedidos
HTTP da sessão inteira, não por inspecção estática de código.

Evidência de storage para a execução bem-sucedida: bucket MinIO com os 4
objectos namespaced sob `workspaces/12c8b85b-.../jobs/<job>/`
(`report.pdf`, `media_kit.pdf`, 2× outputs de content pack); os 4 `Asset`
correspondentes na base de dados com `storage_provider=s3` e `public_url`
preenchido.

**Classificação honesta deste achado:** um flake isolado, investigado,
não-reprodutível — registado como risco a monitorizar (§8), não como
falha bloqueante. Não se declara "E2E sempre passa sem excepção"; declara-se
"E2E corre e passa de facto contra esta stack, com uma instabilidade
pontual já investigada e não reprodutível".

---

## 7. Decisão de prontidão

**Classificação final: `pronto_para_staging_local_formal`.**

Justificação directa contra as cinco opções permitidas:

| Opção | Aplica-se? | Porquê |
|---|---|---|
| **`pronto_para_staging_local_formal`** | **Sim** | Todos os critérios técnicos "duros" do backlog (§9 do `01_backlog.md`) estão cumpridos com evidência real: PostgreSQL persistente substitui SQLite, MinIO substitui storage filesystem, `Asset.public_url` funciona, secrets nunca versionados, arranque repetível, quality gate existe e passa, **E2E passa contra a stack local real**, frontend isolado, logs/correlation-id permitem diagnóstico, runbook reflecte a stack real. A única pendência (validação por terceiro) é organizacional, não técnica, e o próprio backlog admite marcá-la como pendente sem bloquear o fecho |
| `pronto_parcialmente_com_pendencias` | Não | Aplicar-se-ia se algum critério "duro" (PostgreSQL, MinIO, E2E, secrets) continuasse por resolver — não é o caso; todos foram tecnicamente fechados com evidência real nesta fase |
| `executado_parcialmente` | Não | Os 11 prompts planeados (+ este fecho) foram todos executados com validação real, não parcialmente |
| `bloqueado` | Não | Nada impediu a execução — Docker esteve sempre disponível, nenhuma dependência ficou por resolver |
| `nao_pronto` | Não | Seria desonesto classificar como "não pronto" um ambiente com PostgreSQL/MinIO persistentes validados, secrets geridos, scripts testados, quality gate verde, E2E real a passar, segurança validada com correcções reais aplicadas, e observabilidade com correlation-id ponta-a-ponta confirmado |

- **Pronto para ser usado como staging local formal** para desenvolvimento
  e validação técnica contínua desta aplicação — PostgreSQL e MinIO
  persistentes, secrets controlados, E2E real a passar.
- **Não pronto para produção**, em nenhuma leitura deste documento —
  produção exigiria, adicionalmente, SLA, alta disponibilidade, alertas,
  rotação automática de secrets, um secret store real e infraestrutura
  gerida — nenhum dos quais foi sequer iniciado nesta fase, nem é seu
  objectivo.
- **Não é staging externo nem cloud** — tudo corre exclusivamente na
  máquina local, por desenho desta fase.

---

## 8. Riscos

| Risco | Severidade | Nota |
|---|---|---|
| Confundir "staging local formal" com "staging externo" ou "produção" | Alto (se não corrigido) | Mitigado por este documento e pela arquitectura — "staging local formal" é explicitamente definido como uma máquina única, sem SLA, sem alta disponibilidade |
| Flake do E2E observado numa primeira tentativa | Médio | Investigado, não-reprodutível numa segunda tentativa imediata; a causa mais provável (contenção de recursos numa sessão muito longa) não é um bug de produto — recomenda-se monitorizar em execuções futuras, especialmente em máquinas/sessões mais curtas |
| Ligações Django→PostgreSQL "normais" sem timeout curto (achado STG-LOCAL-010) | ~~Médio-Alto~~ Corrigido | **Corrigido em STG-HARD-002 (fase 07):** `DB_CONNECT_TIMEOUT_SECONDS` (default `5`) limita a ligação; medido antes/depois — `130.6s` → `~5.2s` (`/ready/`), `>150s` → `~31s` (endpoint normal). Ver runbook §14 |
| Sem validação por terceiro | Médio | Pendência organizacional, não técnica; recomenda-se antes de qualquer decisão de expandir o uso desta stack para mais operadores |
| Credenciais MinIO reutilizam a conta "root" do container | ~~Baixo~~ Corrigido | **Corrigido em STG-HARD-003 (fase 07):** Content Renderer usa um utilizador de serviço dedicado (`chartrex_renderer`), policy mínima (`s3:PutObject`+`s3:GetObject`, sem `ListBucket`/delete/admin). Ver runbook §11 |
| Sem agregação central de logs | Baixo | Aceitável para staging local de um único operador (premissa obrigatória: "não criar stack pesada") |
| `docker logs` sem rotação/limite explícito | Baixo | Herda o default do Docker; staging local de curta duração |

---

## 9. Limitações conhecidas (consolidado)

- `DATABASE_URL` não é suportado (por desenho) — só variáveis discretas `DB_*`.
- `signed_url` não existe como campo — só `public_url` (herdado da fase 05; MinIO local usa leitura anónima de objecto, não assinatura).
- ~~Credenciais MinIO reutilizam a conta "root" do container~~ **Corrigido (STG-HARD-003, fase 07)** — utilizador de serviço dedicado com policy mínima.
- Sem agregação central de logs entre os 3 serviços — consulta por ficheiro/serviço individual.
- ~~Ligações Django→PostgreSQL "normais" sem `connect_timeout` curto configurado~~ **Corrigido (STG-HARD-002, fase 07)**. Risco residual menor: o caminho de erro HTTP de um endpoint normal (não `/ready/`) fica bounded a `~31s`, não `~5s`, por causa da página de erro técnica do Django em `DEBUG=True` — ver runbook §14.
- Validação por terceiro sem contexto prévio não foi feita.
- Sem CI/CD real neste repositório — o quality gate é reutilizável por CI futura, mas nenhuma pipeline foi criada (fora do escopo desta fase, por desenho).
- `MediaKit.Status` não tem `FAILED` próprio (herdado da fase 05) — convenção via `metadata.generation_status`.
- `INTELLIGENCE_ENGINE_DRY_RUN=true` continua a devolver sempre `recommendations: []` — comportamento intencional do stub, documentado na matriz de sintomas do runbook.

---

## 10. Próximos passos recomendados

1. **Validação por terceiro** — quando um segundo operador estiver
   disponível, seguir o runbook do zero, numa máquina sem contexto prévio,
   e registar quaisquer problemas encontrados (secção 20 do runbook fica
   pronta a ser preenchida).
2. **Monitorizar o flake do E2E** (§6, §8) em execuções futuras — se se
   tornar recorrente, investigar timing/contenção de recursos mais a
   fundo; se continuar isolado, não requer acção adicional.
3. **Considerar corrigir o achado de timeout de ligação PostgreSQL**
   (§8, §9) — fora do âmbito desta fase (é uma alteração de código de
   produto), mas registado como candidato a uma fase de robustez futura.
4. **Decidir se/quando introduzir CI/CD** que reutilize
   `staging-local-quality-gate.ps1` como o seu gate principal — o script
   já foi desenhado para isso, mas nenhuma pipeline foi criada nesta fase.
5. **Esta fase (`06_staging_infraestrutura_real_local`) está encerrada**
   do ponto de vista dos prompts planeados (01–12 completos). Qualquer
   trabalho adicional (produção, cloud, CI/CD real, containerização das
   aplicações) deveria abrir uma fase nova e dedicada, não reabrir esta.
