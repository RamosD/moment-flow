# Backlog — Staging Infraestrutura Real Local

> Fase: `06_staging_infraestrutura_real_local`
> Estado: planeada
> Caminho recomendado: `frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/01_backlog.md`
> Alternativa aceitável: manter a pasta actual `06_staging_infraestrutura_real`, mas explicitar no conteúdo que a fase é local-first
> Dependência anterior: `05_staging_operacionalizacao_pre_producao` fechada como `pronto_parcialmente_com_pendencias`
> Objectivo: montar uma infraestrutura staging local, persistente, reproduzível e próxima do real, sem depender de cloud, SQLite, storage local filesystem ou execução manual dispersa

---

# 1. Premissa central

Toda a infraestrutura desta fase deve correr na máquina local.

Isto significa:

```text
- PostgreSQL em container local persistente;
- MinIO em container local persistente;
- Backend Core em processo local, salvo decisão explícita;
- Intelligence Engine em processo local, salvo decisão explícita;
- Content Renderer em processo local, salvo decisão explícita;
- Frontend em processo local/Vite/preview;
- sem AWS, R2, GCS, Azure Blob ou serviços cloud nesta fase;
- sem secret store cloud nesta fase;
- sem CI/CD remoto obrigatório nesta fase.
```

A palavra “real” nesta fase significa:

```text
- sem SQLite;
- sem storage filesystem local como destino final de artefactos;
- sem dry_run;
- sem mocks runtime;
- com persistência;
- com secrets controlados;
- com healthchecks;
- com E2E real;
- com arranque repetível.
```

---

# 2. Objectivo

Transformar o staging técnico validado numa stack local formal, capaz de simular as dependências reais mínimas:

```text
Frontend → Backend Core → Intelligence Engine
Frontend → Backend Core → Content Renderer
Backend Core → PostgreSQL
Content Renderer → MinIO
Content Renderer → Backend Core callback
Backend Core → Asset.public_url
```

Esta fase deve provar que a aplicação funciona localmente com infraestrutura persistente e S3-compatible, sem depender de serviços cloud.

---

# 3. Tese da fase

```text
Antes de pensar em cloud, CI/CD remoto ou produção, o projecto precisa de uma stack local reproduzível que substitua SQLite e storage local por equivalentes reais controlados: PostgreSQL e MinIO.
```

---

# 4. Estado de partida

A fase 05 deixou concluído:

```text
- PostgreSQL validado tecnicamente contra instância descartável;
- Asset.public_url implementado e validado;
- secrets inventariados;
- fallback de INTELLIGENCE_ENGINE_INTERNAL_TOKEN corrigido;
- .gitignore endurecido para .env.*;
- correlation-id ponta-a-ponta implementado;
- health live/ready/dependencies implementado;
- estados artefacto/job corrigidos;
- RBAC/UX mínimo validado;
- Playwright E2E criado e verde;
- runbook operacional criado;
- suite Backend Core verde após correcção do teste com data fixa.
```

Pendências que esta fase resolve em modo local:

```text
- substituir SQLite por PostgreSQL local persistente;
- substituir storage filesystem por MinIO local;
- configurar secrets locais de forma controlada e não versionada;
- criar arranque repetível;
- correr E2E contra a stack local staging;
- criar quality gate local/CI-ready;
- validar segurança e observabilidade local;
- actualizar runbook para a stack local.
```

---

# 5. Fora do escopo

Não incluir nesta fase:

```text
- cloud;
- produção;
- deploy externo;
- CI/CD remoto obrigatório;
- Kubernetes;
- multi-host real;
- multi-region;
- object storage cloud;
- secret store cloud;
- novas funcionalidades de produto;
- billing;
- scheduler;
- workflow engine;
- alterações grandes de UX/RBAC;
- optimização de performance;
- observabilidade empresarial completa.
```

Também fica fora do escopo containerizar todos os serviços aplicacionais, salvo se for claramente necessário e de baixo risco.

---

# 6. Topologia alvo

## 6.1 Topologia local-first recomendada

```text
Máquina local
├── Frontend Web
│   └── http://localhost:5200
├── Backend Core
│   └── http://localhost:8100
├── Intelligence Engine
│   └── http://localhost:8201
├── Content Renderer
│   └── http://localhost:8202
├── PostgreSQL container
│   └── localhost:5432
└── MinIO container
    ├── S3 API: http://localhost:9000
    └── Console: http://localhost:9001
```

## 6.2 Estratégia de containerização

```text
Obrigatório nesta fase:
- PostgreSQL em container;
- MinIO em container.

Preferencial nesta fase:
- Backend Core, Intelligence Engine, Content Renderer e Frontend continuam em processos locais.

Opcional/futuro:
- containerizar serviços aplicacionais depois de a stack local estar estável.
```

Motivo:

```text
Reduzir risco. Primeiro estabilizar dependências persistentes locais; só depois containerizar tudo.
```

---

# 7. Decisões fechadas desta fase

```text
DB alvo local: PostgreSQL em container.
Object storage alvo local: MinIO em container.
Provider storage: S3-compatible via MinIO.
Cloud: fora do escopo.
CI remoto: fora do escopo obrigatório.
Quality gate: local/CI-ready.
Secrets: locais, não versionados, injectados por env/script controlado.
```

---

# 8. Backlog incremental

---

## STG-LOCAL-001 — Definir topologia local

### Objectivo

Documentar a topologia staging local, incluindo processos locais, containers de infraestrutura, portas, volumes e fronteiras de segurança.

### Tarefas

```text
- confirmar pasta/caminho da fase;
- documentar topologia local-first;
- definir containers obrigatórios: PostgreSQL e MinIO;
- definir serviços locais: Backend Core, IE, CR, Frontend;
- definir portas;
- definir volumes persistentes;
- definir rede;
- definir ordem de arranque;
- definir healthchecks;
- definir limites entre staging local e produção;
- actualizar arquitectura da fase.
```

### Critérios de aceitação

```text
- topologia local documentada;
- PostgreSQL e MinIO definidos como containers obrigatórios;
- cloud explicitamente fora do escopo;
- portas canónicas claras;
- fronteira Frontend → Backend Core preservada;
- nenhuma dependência implícita fica escondida.
```

---

## STG-LOCAL-002 — Criar Docker Compose de infraestrutura local

### Objectivo

Criar um Docker Compose mínimo para subir apenas as dependências de infraestrutura local: PostgreSQL e MinIO.

### Tarefas

```text
- criar docker-compose.staging.local.yml ou equivalente;
- definir serviço postgres;
- definir serviço minio;
- definir volume persistente para PostgreSQL;
- definir volume persistente para MinIO;
- definir healthcheck do PostgreSQL;
- definir healthcheck do MinIO;
- definir bucket inicial de staging;
- definir credenciais via env local ignorado;
- evitar secrets reais no compose;
- documentar comandos de start/stop/reset.
```

### Critérios de aceitação

```text
- docker compose sobe PostgreSQL e MinIO;
- volumes persistem entre restarts;
- containers têm healthchecks;
- bucket MinIO staging é criado;
- compose não contém secrets reais;
- reset destrutivo é separado e claramente marcado.
```

---

## STG-LOCAL-003 — Migrar Backend Core para PostgreSQL local persistente

### Objectivo

Configurar o Backend Core para usar o PostgreSQL container como base de dados staging local.

### Tarefas

```text
- configurar DB_ENGINE=postgres;
- configurar DB_HOST=127.0.0.1;
- configurar DB_PORT=5432 ou porta local definida;
- configurar DB_NAME, DB_USER, DB_PASSWORD via env local ignorado;
- aplicar migrations;
- executar seeds mínimos;
- validar auth;
- validar workspaces;
- validar campaigns;
- validar CampaignActions;
- validar Reports;
- validar MediaKits;
- validar ContentPackRequests;
- validar ExternalJobReference;
- documentar backup/restore local.
```

### Critérios de aceitação

```text
- Backend Core arranca contra PostgreSQL local;
- SQLite não é usado no staging local;
- migrations passam;
- seeds funcionam;
- smoke API passa;
- dados persistem após restart dos containers;
- credenciais não ficam versionadas.
```

---

## STG-LOCAL-004 — Implementar MinIO como object storage

### Objectivo

Implementar e validar provider S3-compatible no Content Renderer usando MinIO local.

### Tarefas

```text
- confirmar abstracção StorageProvider existente;
- adicionar provider minio ou s3-compatible;
- configurar endpoint MinIO: http://127.0.0.1:9000;
- configurar bucket staging;
- configurar access key/secret via env local ignorado;
- configurar public_url ou URL canónica local;
- manter provider local como default dev;
- validar upload de report.pdf;
- validar upload de media_kit.pdf;
- validar upload de outputs content pack;
- validar download via URL;
- validar Asset.public_url no Backend Core;
- adicionar testes do provider/factory.
```

### Critérios de aceitação

```text
- Content Renderer grava artefactos no MinIO;
- storage filesystem local deixa de ser requisito para staging local;
- Asset.public_url fica populado;
- download via URL MinIO funciona;
- provider local continua disponível para dev;
- credenciais MinIO não são versionadas;
- testes passam.
```

---

## STG-LOCAL-005 — Formalizar secrets locais

### Objectivo

Criar uma forma local, segura e repetível de injectar secrets sem commitar `.env` reais.

### Tarefas

```text
- definir ficheiro local ignorado para secrets staging local;
- documentar variáveis obrigatórias por serviço;
- garantir INTERNAL_API_TOKEN partilhado entre Backend Core, IE e CR;
- garantir SECRET_KEY do Backend Core;
- garantir DB_PASSWORD;
- garantir MINIO_ROOT_USER/MINIO_ROOT_PASSWORD;
- garantir STORAGE_ACCESS_KEY/STORAGE_SECRET_KEY;
- garantir E2E_PASSWORD;
- criar exemplos com placeholders;
- validar .gitignore;
- validar rotação local do INTERNAL_API_TOKEN;
- validar que ALLOW_INSECURE_EMPTY_TOKEN não é usado.
```

### Critérios de aceitação

```text
- secrets reais não entram no repositório;
- existe mecanismo local claro de carregamento;
- serviços arrancam com secrets injectados;
- IE e CR rejeitam token vazio;
- rotação local é documentada;
- frontend continua sem secrets.
```

---

## STG-LOCAL-006 — Criar scripts de arranque local

### Objectivo

Criar comandos repetíveis para arrancar, validar e parar a stack staging local.

### Tarefas

```text
- criar script start infra;
- criar script stop infra;
- criar script reset infra, marcado como destrutivo;
- criar script start apps, se adequado;
- criar script check health;
- validar PostgreSQL;
- validar MinIO;
- validar Backend Core;
- validar IE;
- validar CR;
- validar Frontend;
- documentar ordem de arranque.
```

### Critérios de aceitação

```text
- técnico consegue subir infraestrutura local com um comando ou sequência curta;
- healthchecks confirmam serviços;
- comandos não contêm secrets;
- reset destrutivo é explícito;
- runbook reflecte os comandos reais.
```

---

## STG-LOCAL-007 — Quality gate local

### Objectivo

Criar um quality gate local que possa futuramente ser usado por CI, sem exigir CI remoto nesta fase.

### Tarefas

```text
- criar script quality local;
- executar python manage.py check;
- executar pytest Backend Core;
- executar pytest Intelligence Engine;
- executar npm test Content Renderer;
- executar frontend test;
- executar frontend lint;
- executar frontend build;
- executar check-forbidden-ports;
- executar greps de secrets;
- documentar tempo aproximado e pré-requisitos.
```

### Critérios de aceitação

```text
- quality gate local executa suites principais;
- falhas ficam visíveis;
- não imprime secrets;
- pode ser reutilizado por CI no futuro;
- não depende de cloud.
```

---

## STG-LOCAL-008 — Executar E2E contra staging local

### Objectivo

Executar o Playwright E2E contra a stack staging local com PostgreSQL e MinIO.

### Tarefas

```text
- garantir PostgreSQL local activo;
- garantir MinIO activo;
- garantir Backend Core contra PostgreSQL;
- garantir Content Renderer contra MinIO;
- garantir IE real activo;
- garantir Frontend activo;
- configurar E2E_PASSWORD via secret local;
- executar seed_e2e_run contra PostgreSQL;
- correr pnpm test:e2e;
- validar Network apenas Backend Core;
- validar criação de manual task;
- validar report;
- validar media kit;
- validar content pack;
- validar outputs no MinIO;
- validar Asset.public_url;
- validar reload/persistência.
```

### Critérios de aceitação

```text
- E2E passa contra stack staging local;
- DB usado é PostgreSQL;
- storage usado é MinIO;
- outputs existem no MinIO;
- frontend não chama IE/Renderer;
- dados são namespaced;
- secrets não aparecem em logs.
```

---

## STG-LOCAL-009 — Segurança operacional local

### Objectivo

Validar segurança básica da stack local: tokens, CORS, bundle frontend, MinIO, DB e health endpoints.

### Tarefas

```text
- verificar frontend bundle sem IE/Renderer URLs internas;
- verificar frontend bundle sem INTERNAL_API_TOKEN;
- verificar Network apenas Backend Core;
- verificar X-Internal-Token apenas server-to-server;
- verificar health live/ready público;
- verificar dependencies staff-only;
- verificar IE/CR exigem token interno;
- verificar ALLOW_INSECURE_EMPTY_TOKEN false;
- verificar MinIO sem credenciais expostas;
- verificar bucket sem listagem pública indevida, se aplicável;
- verificar PostgreSQL não usa credenciais versionadas;
- grep de logs por secrets.
```

### Critérios de aceitação

```text
- frontend isolado;
- tokens internos não aparecem no browser;
- MinIO não expõe credenciais;
- DB credentials não estão versionadas;
- health detalhado protegido;
- greps de segurança passam.
```

---

## STG-LOCAL-010 — Observabilidade local

### Objectivo

Garantir diagnóstico local com logs, healthchecks e correlation-id ponta-a-ponta.

### Tarefas

```text
- definir onde ficam logs locais;
- definir retenção simples ou rotação manual;
- validar correlation-id em Backend Core;
- validar correlation-id em IE;
- validar correlation-id em Content Renderer;
- seguir fluxo completo por correlation-id;
- validar erro IE down;
- validar erro Renderer down;
- validar erro MinIO down;
- validar erro PostgreSQL down, se seguro;
- actualizar runbook com troubleshooting local.
```

### Critérios de aceitação

```text
- operação local é rastreável por correlation-id;
- falhas principais são diagnosticáveis;
- logs não contêm secrets;
- runbook explica onde olhar.
```

---

## STG-LOCAL-011 — Validar runbook local

### Objectivo

Actualizar e validar o runbook para a stack local-first.

### Tarefas

```text
- actualizar runbook da fase 05;
- incluir Docker Compose infra;
- incluir PostgreSQL local;
- incluir MinIO local;
- incluir secrets locais;
- incluir quality gate;
- incluir E2E local;
- incluir troubleshooting MinIO;
- incluir troubleshooting PostgreSQL;
- incluir reset destrutivo controlado;
- se possível, pedir a outro técnico para seguir o runbook;
- se não houver terceiro, marcar validação por terceiro como pendente.
```

### Critérios de aceitação

```text
- runbook reflecte a stack local real;
- comandos foram testados;
- não contém secrets;
- reset destrutivo está claramente separado;
- validação por terceiro é feita ou marcada como pendente sem mascarar.
```

---

## STG-LOCAL-012 — Fechar staging local formal

### Objectivo

Consolidar evidências e decidir se a stack local pode ser considerada staging local formal.

### Tarefas

```text
- ler relatórios da fase;
- actualizar arquitectura;
- actualizar runbook;
- criar estado final;
- listar validações concluídas;
- listar pendências;
- listar riscos;
- classificar prontidão;
- separar staging local formal de produção;
- definir próxima fase.
```

### Critérios de aceitação

```text
- estado final documentado;
- PostgreSQL local validado;
- MinIO local validado;
- secrets locais validados;
- E2E local passa;
- quality gate local existe;
- runbook actualizado;
- produção não declarada.
```

---

# 9. Critérios de aceitação da fase

A fase é aceite se:

```text
- PostgreSQL em container local substitui SQLite no staging local;
- MinIO em container local substitui storage filesystem como destino staging;
- Backend Core persiste dados no PostgreSQL;
- Content Renderer grava artefactos no MinIO;
- Asset.public_url funciona com MinIO;
- secrets locais não são versionados;
- arranque da stack é repetível;
- quality gate local existe;
- E2E passa contra a stack local;
- frontend continua isolado;
- logs/correlation-id permitem diagnóstico local;
- runbook reflecte a stack real;
- estado final está documentado.
```

---

# 10. Critérios de rejeição

A fase não é aceite se:

```text
- staging local continuar dependente de SQLite;
- staging local continuar dependente de storage filesystem como destino final;
- MinIO não for usado;
- secrets forem commitados;
- ALLOW_INSECURE_EMPTY_TOKEN for usado;
- frontend chamar IE ou Renderer;
- E2E rodar contra stack antiga/local dev sem PostgreSQL/MinIO;
- quality gate não existir;
- runbook não reflectir os comandos reais;
- produção for declarada pronta.
```

---

# 11. Riscos principais

| ID        | Risco                                                | Impacto | Mitigação                                                  |
| --------- | ---------------------------------------------------- | ------: | ---------------------------------------------------------- |
| LOCAL-R01 | Docker não disponível ou instável na máquina         |    Alto | validar Docker antes de implementar; documentar requisitos |
| LOCAL-R02 | Porta 5432 já ocupada                                |   Médio | permitir override documentado de POSTGRES_PORT             |
| LOCAL-R03 | Porta 9000/9001 ocupada                              |   Médio | permitir override documentado de MinIO ports               |
| LOCAL-R04 | Secrets locais versionados por acidente              | Crítico | `.gitignore`, greps e placeholders                         |
| LOCAL-R05 | MinIO public_url não acessível pelo Backend/Frontend |    Alto | definir endpoint interno/externo claramente                |
| LOCAL-R06 | Content Renderer quebra modo local antigo            |   Médio | manter provider local como default dev                     |
| LOCAL-R07 | E2E flakey por ordem de arranque                     |   Médio | healthcheck antes do E2E                                   |
| LOCAL-R08 | Dados acumulam em volumes locais                     |   Baixo | reset destrutivo documentado                               |
| LOCAL-R09 | Confundir staging local com produção                 |    Alto | documentação explícita e gates                             |
| LOCAL-R10 | Containerizar apps cedo demais                       |   Médio | limitar containers obrigatórios a PostgreSQL e MinIO       |

---

# 12. Ordem recomendada

```text
Incremento 0 — Base local
STG-LOCAL-001
STG-LOCAL-002
STG-LOCAL-003
STG-LOCAL-005

Incremento 1 — Storage real local
STG-LOCAL-004
STG-LOCAL-006

Incremento 2 — Validação
STG-LOCAL-007
STG-LOCAL-008

Incremento 3 — Operação
STG-LOCAL-009
STG-LOCAL-010
STG-LOCAL-011

Fecho
STG-LOCAL-012
```

---

# 13. Documentos esperados

Se for criada pasta nova:

```text
frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/01_backlog.md
frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/arquitectura_staging_local.md
frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/runbook_staging_local.md
frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/estado_staging_local.md
frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/resultados_execucao/
```

Se for mantida a pasta actual:

```text
frontend/docs/01_fundamentos/06_staging_infraestrutura_real/01_backlog.md
frontend/docs/01_fundamentos/06_staging_infraestrutura_real/arquitectura_staging_local.md
frontend/docs/01_fundamentos/06_staging_infraestrutura_real/runbook_staging_local.md
frontend/docs/01_fundamentos/06_staging_infraestrutura_real/estado_staging_local.md
frontend/docs/01_fundamentos/06_staging_infraestrutura_real/resultados_execucao/
```

Recomendação prática:

```text
Manter a pasta actual se já foi criada, mas alterar o título, a fase e o conteúdo para local-first.
```

---

# 14. Resultado esperado

Ao fechar esta fase, o projecto deve sair de:

```text
staging técnico validado em dev
```

para:

```text
staging local formal, persistente, reproduzível e validável
```

Sem declarar produção.

---

# 15. Próximo passo

Gerar a pipeline de prompts ajustada para a IA local executar esta fase com a premissa obrigatória:

```text
Tudo deve correr localmente.
PostgreSQL deve correr em container local.
MinIO deve correr em container local.
Não usar cloud.
Não criar CI/CD remoto obrigatório.
```
