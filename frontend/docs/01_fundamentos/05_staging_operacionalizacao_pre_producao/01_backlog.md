# Backlog — Staging Operacionalização Pré-Produção

> Fase: `05_staging_operacionalizacao_pre_producao`
> Estado: planeada
> Dependência anterior: `04_staging_campaign_actions_with_real_ie_renderer` fechada como `pronto_para_piloto_tecnico_staging`
> Objectivo: transformar o piloto técnico staging num ambiente pré-produção minimamente confiável, observável e operável

---

# 1. Objectivo

Preparar o ambiente de staging formal para suportar um piloto técnico mais amplo e servir como base de pré-produção.

A fase anterior validou a cadeia real:

```text id="qen7r5"
Frontend → Backend Core → Intelligence Engine
Frontend → Backend Core → Content Renderer
Backend Core → CampaignActions + artefactos + jobs + callbacks
```

Esta fase não deve adicionar nova funcionalidade de produto. O foco é operacionalização:

```text id="hsg4qp"
- DB alvo/staging formal;
- object storage;
- public_url canónico dos assets;
- gestão de segredos;
- correlation-id único ponta-a-ponta;
- logs e observabilidade;
- healthchecks operacionais;
- RBAC/UX mínimo;
- E2E automatizado repetível;
- documentação de runbook.
```

---

# 2. Tese da fase

A tese desta fase é:

```text id="2ad3dl"
Um fluxo funcional validado em dev só passa a ser candidato a pré-produção quando é reproduzível, observável, seguro, recuperável e independente de SQLite/storage local.
```

---

# 3. Fora do escopo

Não incluir nesta fase:

```text id="jt5gzv"
- novas features de Campaign Actions;
- billing;
- scheduler;
- workflow engine;
- realtime/WebSockets;
- optimizações de performance extensas;
- produção;
- multi-region;
- object storage definitivo de produção sem validação staging;
- mudanças de UX grandes fora de RBAC/erros/estados.
```

---

# 4. Backlog incremental

## STG-PRE-001 — Definir arquitectura alvo de staging

### Objectivo

Documentar a arquitectura formal de staging e separar claramente dev local, staging técnico e produção.

### Tarefas

```text id="9p2fda"
- documentar componentes;
- documentar portas/URLs;
- documentar DB alvo;
- documentar storage alvo;
- documentar fluxo de secrets;
- documentar logs;
- documentar healthchecks;
- documentar responsabilidades de cada serviço;
- documentar o que ainda não é produção.
```

### Critérios de aceitação

```text id="dbjvdw"
- arquitectura staging documentada;
- limites dev/staging/prod claros;
- nenhuma decisão implícita fica escondida em .env local.
```

---

## STG-PRE-002 — Migrar de SQLite dev para DB alvo staging

### Objectivo

Preparar e validar Backend Core com base de dados staging real.

### Tarefas

```text id="o2l1xu"
- escolher DB alvo staging;
- configurar DATABASE_URL ou equivalente;
- aplicar migrations;
- validar campaign_actions;
- validar reports/media kits/content pack requests;
- validar external jobs;
- validar users/workspaces/campaigns;
- criar seed mínimo;
- executar smoke API.
```

### Critérios de aceitação

```text id="q1r0yj"
- Backend Core arranca com DB staging;
- migrations passam;
- dados mínimos existem;
- fluxo Campaign Actions funciona fora de SQLite;
- rollback/backup básico documentado.
```

---

## STG-PRE-003 — Configurar object storage e Asset.public_url

### Objectivo

Substituir storage local por storage adequado a staging e popular URL pública canónica dos assets.

### Tarefas

```text id="5037au"
- confirmar provider alvo: S3, R2, MinIO ou equivalente;
- configurar credenciais via env/secret store;
- configurar bucket/container staging;
- actualizar Content Renderer para gravar no provider;
- garantir storage_key estável;
- garantir public_url ou signed_url conforme contrato;
- actualizar Backend Core para persistir Asset.public_url quando aplicável;
- validar report.pdf, media_kit.pdf e outputs content pack.
```

### Critérios de aceitação

```text id="qgxiox"
- assets deixam de depender de content_renderer/storage local;
- outputs são acessíveis por URL canónica;
- Report/MediaKit/ContentOutput referenciam assets correctos;
- secrets de storage não aparecem em código/logs/docs.
```

---

## STG-PRE-004 — Gestão de segredos

### Objectivo

Remover dependência de tokens manuais em `.env` local e formalizar secrets de staging.

### Tarefas

```text id="0bu3zc"
- inventariar secrets;
- definir origem dos secrets;
- configurar INTERNAL_API_TOKEN partilhado;
- configurar tokens IE/CR;
- configurar DB credentials;
- configurar storage credentials;
- documentar rotação;
- impedir commit acidental;
- validar que logs não expõem secrets.
```

### Critérios de aceitação

```text id="esargx"
- nenhum secret real em repositório;
- todos os serviços recebem secrets por mecanismo controlado;
- rotação documentada;
- greps de segurança passam.
```

---

## STG-PRE-005 — Correlation-id único ponta-a-ponta

### Objectivo

Propagar um identificador único desde o Backend Core até IE, Renderer, jobs e callbacks.

### Tarefas

```text id="iqxk4j"
- definir header canónico: X-Request-ID ou equivalente;
- gerar/aceitar request_id no Backend Core;
- propagar para IE;
- registar no IE em logs app-level;
- propagar para ExternalJobReference;
- propagar para Content Renderer;
- devolver/usar no callback;
- registar action_id/artifact_id/job_id/request_id juntos;
- actualizar testes.
```

### Critérios de aceitação

```text id="8111tm"
- uma operação pode ser rastreada BC→IE→CampaignAction→Artifact→Job→Renderer→Callback;
- logs dos três serviços contêm correlation-id;
- nenhum token é registado;
- debugging deixa de depender apenas de campaign_id/job_id.
```

---

## STG-PRE-006 — Observabilidade e healthchecks operacionais

### Objectivo

Tornar staging operável: logs, health agregado, readiness e sinais de falha.

### Tarefas

```text id="dchrf2"
- validar /api/v1/system/health/dependencies/ com utilizador staff;
- validar health IE;
- validar health CR;
- adicionar readiness quando fizer sentido;
- definir logs estruturados mínimos;
- definir eventos de job;
- definir métricas mínimas;
- documentar sinais de alerta;
- documentar troubleshooting.
```

### Critérios de aceitação

```text id="4h54q2"
- health agregado reflecte DB, IE e CR;
- falhas são visíveis;
- runbook explica diagnóstico;
- logs têm ids suficientes para suporte.
```

---

## STG-PRE-007 — Alinhar estados de artefacto e job

### Objectivo

Reduzir ambiguidade quando o renderer falha e o artefacto fica `queued`/`draft`.

### Tarefas

```text id="bmi7lz"
- mapear estados Report vs ExternalJobReference;
- mapear estados MediaKit vs ExternalJobReference;
- mapear estados ContentPackRequest vs ExternalJobReference;
- decidir se falha de job deve reflectir no artefacto;
- tratar MediaKit sem estado failed próprio;
- documentar divergências restantes;
- ajustar UI se necessário para mostrar job failure.
```

### Critérios de aceitação

```text id="slzgh4"
- utilizador não interpreta job failed como sucesso;
- suporte consegue identificar causa;
- CampaignAction/artefacto/job têm estados coerentes ou explicitamente distintos.
```

---

## STG-PRE-008 — RBAC/UX mínimo para piloto

### Objectivo

Evitar affordances enganosas para utilizadores sem permissão e melhorar feedback de erro.

### Tarefas

```text id="dfn2j3"
- confirmar capabilities disponíveis no perfil;
- se não existirem, documentar limitação;
- ocultar/desactivar acções de escrita quando houver informação suficiente;
- garantir 403 visível como Access denied;
- garantir 404 genérico;
- melhorar mensagens de job failed/renderer unavailable;
- validar viewer vs editor, se possível.
```

### Critérios de aceitação

```text id="sm4cfp"
- utilizador sem permissão não recebe UX enganosa;
- backend continua autoridade;
- erros são honestos e seguros;
- sem inferência insegura de permissões no browser.
```

---

## STG-PRE-009 — E2E automatizado repetível

### Objectivo

Transformar o smoke manual em teste automatizado reproduzível.

### Tarefas

```text id="xzzo9m"
- escolher ferramenta: Playwright ou equivalente;
- definir seed/fixtures;
- automatizar login;
- abrir War Room;
- executar intelligence real ou ambiente controlado;
- criar manual task;
- criar report/media kit/content pack;
- validar related_*;
- validar reload/persistência;
- validar Network apenas Backend Core;
- limpar dados ou usar namespace por execução.
```

### Critérios de aceitação

```text id="7c3kal"
- E2E corre de forma repetível;
- não depende de dados manuais frágeis;
- não expõe secrets;
- falha de IE/CR é distinguível de falha de frontend.
```

---

## STG-PRE-010 — Runbook operacional staging

### Objectivo

Criar guia prático para arrancar, validar, diagnosticar e parar staging.

### Tarefas

```text id="lmk5ui"
- comandos de arranque;
- variáveis obrigatórias;
- ordem de start;
- healthchecks;
- smoke test;
- troubleshooting IE;
- troubleshooting Renderer;
- troubleshooting callbacks;
- troubleshooting DB;
- troubleshooting storage;
- limpeza de dados dev;
- paragem segura.
```

### Critérios de aceitação

```text id="h5c7vx"
- qualquer técnico consegue arrancar e validar staging;
- problemas comuns têm diagnóstico claro;
- não há secrets no runbook.
```

---

## STG-PRE-011 — Fecho de prontidão pré-produção

### Objectivo

Consolidar evidência e decidir se staging formal está pronto para piloto pré-produção.

### Tarefas

```text id="3yt4vk"
- consolidar relatórios;
- actualizar estado;
- listar validações concluídas;
- listar riscos;
- listar limitações;
- declarar pronto/não pronto;
- separar piloto técnico, pré-produção e produção;
- definir próximos passos.
```

### Critérios de aceitação

```text id="ew74s6"
- estado final honesto;
- produção não declarada sem critérios;
- evidência rastreável.
```

---

# 5. Critérios de aceitação da fase

A fase é aceite se:

```text id="kqts4z"
- DB staging substitui SQLite dev;
- migrations passam;
- object storage substitui storage local;
- Asset.public_url ou URL canónica está resolvida;
- secrets são geridos fora do repositório;
- correlation-id único existe ponta-a-ponta;
- healthchecks DB/IE/CR funcionam;
- logs são suficientes e sem secrets;
- estados de artefacto/job são claros;
- RBAC/UX mínimo está validado;
- E2E automatizado cobre fluxo principal;
- runbook operacional existe;
- estado final documentado.
```

---

# 6. Critérios de rejeição

A fase não é aceite se:

```text id="x0zqtl"
- continuar dependente de SQLite dev para declarar staging formal;
- continuar dependente de storage local para outputs;
- secrets forem colocados no repositório;
- tokens aparecerem em logs;
- IE/Renderer forem chamados directamente pelo frontend;
- health agregado não reflectir dependências;
- outputs não tiverem URL acessível;
- E2E for manual apenas;
- erros de renderer ficarem invisíveis ao utilizador/suporte;
- produção for declarada sem staging formal.
```

---

# 7. Riscos principais

| ID      | Risco                                               | Impacto | Mitigação                          |
| ------- | --------------------------------------------------- | ------: | ---------------------------------- |
| PRE-R01 | DB staging diverge do SQLite                        |    Alto | migrations e smoke em DB alvo      |
| PRE-R02 | Object storage introduz problemas de permissão/CORS |    Alto | validar upload, download e URL     |
| PRE-R03 | Secrets mal geridos                                 | Crítico | secret store/env controlado, greps |
| PRE-R04 | Correlation-id incompleto                           |    Alto | propagar e testar ponta-a-ponta    |
| PRE-R05 | E2E instável                                        |   Médio | fixtures determinísticas e limpeza |
| PRE-R06 | RBAC incompleto                                     |   Médio | backend autoridade + UX honesta    |
| PRE-R07 | Job failed invisível                                |    Alto | alinhar estados e mensagens        |
| PRE-R08 | Staging confundido com produção                     |    Alto | documentação e gates claros        |

---

# 8. Ordem recomendada

```text id="c0kesw"
Incremento 0 — Arquitectura e ambiente
STG-PRE-001
STG-PRE-002
STG-PRE-003
STG-PRE-004

Incremento 1 — Observabilidade
STG-PRE-005
STG-PRE-006

Incremento 2 — Estado e UX operacional
STG-PRE-007
STG-PRE-008

Incremento 3 — Repetibilidade
STG-PRE-009
STG-PRE-010

Fecho
STG-PRE-011
```

---

# 9. Documentos esperados

```text id="x1o6w5"
frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/01_backlog.md
frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/arquitectura_staging_pre_producao.md
frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/runbook_staging_pre_producao.md
frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/estado_staging_pre_producao.md
frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/resultados_execucao/
```

---

# 10. Próximo passo

Gerar a pipeline de prompts para execução assistida por IA local desta fase.
