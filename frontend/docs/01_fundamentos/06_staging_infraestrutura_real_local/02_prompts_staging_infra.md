# Pipeline: Staging Infraestrutura Real Local

## Prompt 01 (sonnet) — Definir topologia local

```prompt 
Iteração 01

Actua como arquitecto de infraestrutura local, tech lead full-stack e guardião de escopo.

Objectivo:
Definir e documentar a topologia staging local-first da fase 06, assumindo obrigatoriamente que tudo deve correr na máquina local.

Backlog de referência:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\

Documentos a criar ou actualizar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\arquitectura_staging_local.md
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_01_topologia_local_resultado.md

Premissa obrigatória:
Toda a infraestrutura desta fase é local.
Não usar cloud.
Não desenhar AWS, R2, GCS, Azure Blob, Kubernetes ou secret store cloud.
PostgreSQL deve correr em container local.
MinIO deve correr em container local.
Os serviços aplicacionais devem continuar preferencialmente como processos locais, salvo decisão técnica muito clara e justificada.

Topologia alvo base:
- Frontend Web: localhost:5200
- Backend Core: localhost:8100
- Intelligence Engine: localhost:8201
- Content Renderer: localhost:8202
- PostgreSQL container: localhost:5432
- MinIO S3 API container: localhost:9000
- MinIO Console container: localhost:9001

Regras:
- Não implementar features de produto.
- Não declarar produção-ready.
- Não alterar código runtime neste prompt, salvo documentação.
- Não colocar secrets em documentos.
- Não usar portas proibidas como default activo.
- O frontend deve continuar a chamar apenas o Backend Core.
- O frontend nunca deve chamar Intelligence Engine ou Content Renderer directamente.
- O frontend nunca deve enviar X-Internal-Token.
- Não fingir cloud ou staging externo.
- Não fingir CI/CD remoto.
- Usar português de Portugal.

Fonte de verdade:
1. backlog indicado;
2. documentação e resultados da fase 05;
3. docs de portas;
4. runbook da fase 05;
5. settings/env examples/scripts existentes;
6. código actual.

Tarefas:
1. Ler integralmente o backlog da fase 06.
2. Confirmar que a premissa local-first está reflectida no backlog.
3. Ler, se existirem:
   - frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\estado_staging_pre_producao.md
   - frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\arquitectura_staging_pre_producao.md
   - frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\runbook_staging_pre_producao.md
   - frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\prompt_11_fecho_pre_producao_resultado.md
4. Inventariar componentes actuais:
   - Frontend Web;
   - Backend Core;
   - Intelligence Engine;
   - Content Renderer;
   - PostgreSQL;
   - MinIO;
   - secrets locais;
   - quality gate local;
   - E2E.
5. Documentar a topologia local:
   - serviços em processo local;
   - containers obrigatórios;
   - portas;
   - volumes;
   - ordem de arranque;
   - healthchecks;
   - dependências;
   - rede local;
   - fronteiras de segurança.
6. Explicar por que PostgreSQL e MinIO devem ser containers locais persistentes.
7. Explicar por que os serviços aplicacionais não devem ser containerizados já, salvo necessidade.
8. Identificar riscos locais:
   - Docker indisponível;
   - portas ocupadas;
   - volumes locais acumularem dados;
   - secrets locais versionados por acidente.
9. Criar ou actualizar arquitectura_staging_local.md.
10. Criar relatório de execução.

Validações:
- Verificar que o documento não contém secrets.
- Verificar que nenhuma porta proibida é usada como default activo.
- Confirmar que cloud está explicitamente fora do escopo.
- Confirmar que PostgreSQL e MinIO estão definidos como containers locais.
- Confirmar que a regra Frontend -> Backend Core está explícita.
- Executar apenas comandos de inspecção seguros, se necessário.

Critérios de aceitação:
- Topologia local-first documentada.
- PostgreSQL e MinIO definidos como containers obrigatórios.
- Serviços aplicacionais definidos como processos locais por defeito.
- Portas canónicas claras.
- Volumes persistentes previstos.
- Cloud e produção explicitamente fora do escopo.
- Nenhum secret documentado.

Critérios de rejeição:
- Desenhar cloud.
- Declarar produção-ready.
- Usar SQLite como staging formal.
- Usar filesystem local do Content Renderer como storage staging final.
- Usar portas antigas/proibidas.
- Permitir chamada directa Frontend -> IE/Renderer.
- Escrever secrets em documentação.

Relatório:
Criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_01_topologia_local_resultado.md

O relatório deve incluir:
- estado da execução;
- topologia local definida;
- ficheiros criados/alterados;
- decisões tomadas;
- decisões pendentes;
- validações executadas;
- riscos;
- próximo passo recomendado.
```

## Prompt 02 (sonnet) — Criar Compose local

``````prompt 
Iteração 2

Actua como DevOps local, engenheiro de plataforma e guardião de segurança.

Objectivo:
Criar um Docker Compose local mínimo para subir apenas as dependências de infraestrutura: PostgreSQL e MinIO.

Backlog de referência:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_02_compose_local_resultado.md

Premissa obrigatória:
Tudo deve correr localmente.
PostgreSQL deve correr em container local.
MinIO deve correr em container local.
Não usar cloud.
Não containerizar os serviços aplicacionais neste prompt.

Regras:
- Não colocar secrets reais no compose.
- Não commitar ficheiros .env reais.
- Não usar passwords reais em documentação.
- Não apagar volumes sem autorização explícita.
- Separar comandos destrutivos de comandos normais.
- Usar volumes persistentes.
- Permitir override de portas quando possível.
- Não usar portas proibidas.
- Não alterar produto.

Tarefas:
1. Ler o backlog da fase 06.
2. Ler arquitectura_staging_local.md, se já existir.
3. Inspeccionar se já existe docker-compose no repositório.
4. Criar ou actualizar um compose local para infraestrutura, por exemplo:
   - docker-compose.staging.local.yml
5. Definir serviço PostgreSQL:
   - imagem postgres adequada;
   - porta local 5432 por defeito;
   - volume persistente;
   - healthcheck;
   - variáveis por placeholders/env local ignorado.
6. Definir serviço MinIO:
   - imagem minio adequada;
   - porta S3 API 9000;
   - porta Console 9001;
   - volume persistente;
   - healthcheck;
   - variáveis por placeholders/env local ignorado.
7. Criar inicialização de bucket staging no MinIO:
   - por serviço auxiliar mc;
   - ou por script seguro separado;
   - sem credenciais reais versionadas.
8. Criar ou actualizar ficheiro exemplo de env local:
   - apenas placeholders;
   - nomes das variáveis;
   - comentários claros.
9. Garantir .gitignore para env local real.
10. Documentar comandos:
   - start;
   - stop;
   - status;
   - logs;
   - reset destrutivo.
11. Criar relatório.

Validações:
- docker compose config, se Docker estiver disponível.
- docker compose up, se seguro.
- healthcheck PostgreSQL.
- healthcheck MinIO.
- confirmar volumes.
- confirmar bucket staging.
- scripts/check-forbidden-ports.ps1.
- grep por secrets nos ficheiros criados/alterados.

Critérios de aceitação:
- Compose local sobe PostgreSQL e MinIO.
- Volumes persistem entre restarts.
- Healthchecks existem.
- Bucket MinIO staging é criado ou há comando claro para criar.
- Nenhum secret real em ficheiros versionados.
- Reset destrutivo está separado e identificado.
- Serviços aplicacionais não foram desnecessariamente containerizados.

Critérios de rejeição:
- Compose com passwords reais.
- MinIO sem volume persistente.
- PostgreSQL sem volume persistente.
- Usar SQLite como alternativa.
- Usar cloud.
- Usar portas proibidas.
- Reset destrutivo misturado com start normal.

Relatório:
Criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_02_compose_local_resultado.md

O relatório deve incluir:
- estado da execução;
- ficheiros criados/alterados;
- serviços definidos;
- variáveis necessárias sem valores reais;
- comandos executados;
- healthchecks;
- limitações;
- riscos;
- próximo passo recomendado.
```

## Prompt 03 (sonnet) — Migrar para PostgreSQL local

``````prompt 
Iteração 3

Actua como engenheiro backend Django, DevOps local e guardião de dados.

Objectivo:
Configurar e validar o Backend Core contra PostgreSQL local persistente em container, substituindo SQLite no staging local.

Backlog de referência:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_03_postgresql_local_resultado.md

Premissa obrigatória:
PostgreSQL deve ser o container local definido no compose da fase.
Não usar SQLite para declarar staging local.
Não usar PostgreSQL descartável sem volume para declarar staging local.
Não usar cloud.

Regras:
- Não apagar db.sqlite3 nem dados existentes sem autorização explícita.
- Não commitar DB_PASSWORD.
- Não imprimir DB_PASSWORD.
- Não alterar lógica de produto.
- Não usar DATABASE_URL se o projecto usa variáveis DB_* discretas, salvo se já existir suporte.
- Se Docker/PostgreSQL não estiver disponível, documentar bloqueio sem fingir validação.

Tarefas:
1. Confirmar que o PostgreSQL container local está disponível.
2. Confirmar variáveis necessárias:
   - DB_ENGINE=postgres
   - DB_NAME
   - DB_USER
   - DB_PASSWORD
   - DB_HOST=127.0.0.1 ou localhost conforme validado
   - DB_PORT=5432 ou override documentado
3. Garantir que as variáveis são carregadas por ficheiro local ignorado ou ambiente, não por ficheiro versionado.
4. Arrancar Backend Core contra PostgreSQL local.
5. Executar:
   - python manage.py check
   - python manage.py showmigrations
   - python manage.py migrate
6. Executar seeds necessários:
   - seed_rbac;
   - seed_billing, se necessário;
   - seed_content;
   - seed_e2e_run ou seed staging local, se aplicável.
7. Validar smoke API:
   - auth;
   - auth/me;
   - workspaces;
   - campaigns;
   - campaign-actions;
   - reports;
   - media-kits;
   - content-pack-requests;
   - external jobs.
8. Confirmar persistência:
   - parar containers;
   - subir novamente;
   - confirmar dados ainda existem.
9. Documentar backup/restore local:
   - pg_dump;
   - pg_restore;
   - volume backup;
   - reset destrutivo.
10. Criar relatório.

Validações obrigatórias:
- python manage.py check
- python manage.py showmigrations
- python manage.py migrate
- pytest apps/campaign_actions
- pytest apps/reports apps/content apps/integrations_bridge, se viável
- smoke API
- persistência após restart do container
- grep por secrets nos ficheiros alterados

Critérios de aceitação:
- Backend Core arranca com DB_ENGINE=postgres.
- SQLite não é usado no staging local.
- Migrations passam.
- Seeds funcionam.
- Smoke API passa.
- Dados persistem após restart.
- Credenciais não ficam versionadas.
- Backup/restore local está documentado.

Critérios de rejeição:
- Declarar PostgreSQL local validado usando SQLite.
- Usar container descartável sem volume como staging local.
- Escrever DB_PASSWORD em docs/scripts.
- Ignorar falhas de migration.
- Apagar dados sem autorização.
- Chamar isto de produção.

Relatório:
Criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_03_postgresql_local_resultado.md

O relatório deve incluir:
- estado da execução;
- configuração usada sem valores secretos;
- migrations;
- seeds;
- smoke API;
- persistência;
- backup/restore;
- ficheiros alterados;
- validações;
- riscos;
- próximo passo recomendado.
```

## Prompt 04 (sonnet) — Implementar MinIO storage

``````prompt 
Iteração 4

Actua como engenheiro Node/TypeScript, backend integrator e guardião de storage.

Objectivo:
Implementar e validar o provider MinIO/S3-compatible no Content Renderer, usando MinIO local em container como object storage staging local.

Backlog de referência:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_04_minio_storage_resultado.md

Premissa obrigatória:
Provider obrigatório nesta fase: MinIO local em container.
Não escolher AWS S3, R2, GCS ou cloud.
O provider deve ser S3-compatible, mas o alvo de validação é MinIO local.
O storage local filesystem deve continuar disponível como default dev, mas não como destino staging local.

Regras:
- Não commitar access key/secret key.
- Não imprimir credenciais MinIO.
- Não quebrar provider local.
- Não alterar Backend Core desnecessariamente se Asset.public_url já está implementado.
- Não declarar MinIO validado sem upload/download real.
- Não usar filesystem local como fallback silencioso em staging local.
- Não expor bucket com política insegura sem documentar.
- Não alterar produto fora de storage.

Tarefas:
1. Confirmar que MinIO container local está disponível.
2. Confirmar bucket staging.
3. Inspeccionar a abstracção StorageProvider do Content Renderer.
4. Implementar provider S3-compatible/MinIO:
   - factory;
   - config;
   - upload;
   - metadata;
   - public_url local;
   - erros controlados.
5. Definir variáveis de ambiente com placeholders:
   - STORAGE_PROVIDER=minio ou s3;
   - STORAGE_ENDPOINT=http://127.0.0.1:9000;
   - STORAGE_BUCKET;
   - STORAGE_ACCESS_KEY;
   - STORAGE_SECRET_KEY;
   - STORAGE_FORCE_PATH_STYLE, se necessário;
   - STORAGE_PUBLIC_BASE_URL, se necessário.
6. Garantir que local storage continua default para dev.
7. Validar com Content Renderer real:
   - report_generation;
   - media_kit_generation;
   - content_generation.
8. Validar no Backend Core:
   - Asset.storage_provider;
   - Asset.storage_key;
   - Asset.public_url;
   - download por URL.
9. Adicionar testes unitários do provider/factory.
10. Actualizar documentação/runbook.
11. Criar relatório.

Validações:
- npm test no Content Renderer.
- python manage.py check, se Backend Core for tocado.
- smoke real de Report.
- smoke real de MediaKit.
- smoke real de ContentPackRequest.
- download real via public_url.
- verificar objectos no bucket MinIO.
- grep por secrets.
- check-forbidden-ports.
- confirmar que provider local ainda passa testes.

Critérios de aceitação:
- Content Renderer grava artefactos no MinIO.
- Outputs existem no bucket.
- Asset.public_url fica preenchido.
- Download por URL funciona.
- Provider local continua disponível para dev.
- Credenciais MinIO não ficam versionadas.
- Testes passam.
- Storage local filesystem deixa de ser requisito para staging local.

Critérios de rejeição:
- Declarar MinIO pronto sem upload/download.
- Usar filesystem local em staging local sem avisar.
- Commitar credenciais.
- Quebrar provider local.
- Deixar public_url vazio.
- Escolher cloud.
- Usar signed_url sem decisão clara.

Relatório:
Criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_04_minio_storage_resultado.md

O relatório deve incluir:
- estado da execução;
- provider implementado;
- variáveis necessárias sem valores;
- ficheiros alterados;
- testes;
- smoke real;
- evidência MinIO;
- limitações;
- riscos;
- próximo passo recomendado.
```

## Prompt 05 (sonnet) — Formalizar secrets locais

``````prompt 
Iteração 5

Actua como engenheiro de segurança, DevOps local e guardião de configuração.

Objectivo:
Formalizar secrets locais para a stack staging local, sem commitar ficheiros reais e sem depender de cópia artesanal insegura.

Backlog de referência:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_05_secrets_locais_resultado.md

Premissa obrigatória:
Secret store cloud está fora do escopo.
CI/CD remoto está fora do escopo obrigatório.
A solução deve ser local, version-safe e repetível.

Regras:
- Nunca imprimir valores reais de secrets.
- Nunca commitar .env real.
- Não usar ALLOW_INSECURE_EMPTY_TOKEN.
- Não permitir INTERNAL_API_TOKEN vazio.
- Não colocar secrets no frontend.
- Não criar VITE_* com segredos.
- Não escrever passwords em relatórios.
- Não usar tokens reais em exemplos.
- Todos os exemplos devem usar placeholders.

Tarefas:
1. Inventariar secrets locais:
   - SECRET_KEY;
   - INTERNAL_API_TOKEN;
   - DB_PASSWORD;
   - MINIO_ROOT_USER;
   - MINIO_ROOT_PASSWORD;
   - STORAGE_ACCESS_KEY;
   - STORAGE_SECRET_KEY;
   - E2E_PASSWORD;
   - STRIPE_*, se aplicável e opcional.
2. Definir ficheiro ou mecanismo local ignorado:
   - por exemplo .env.staging.local;
   - ou pasta local ignorada;
   - ou scripts que leem env do utilizador.
3. Garantir que o mecanismo é compatível com:
   - Docker Compose infra;
   - Backend Core;
   - Intelligence Engine;
   - Content Renderer;
   - Frontend;
   - Playwright E2E.
4. Criar ou actualizar .env.example com placeholders seguros, se necessário.
5. Validar .gitignore:
   - .env;
   - .env.*;
   - ficheiros locais staging.
6. Validar rotação local do INTERNAL_API_TOKEN:
   - gerar novo valor sem imprimir;
   - aplicar nos três serviços;
   - reiniciar;
   - testar IE real;
   - testar Renderer callback.
7. Validar falha segura:
   - token ausente;
   - token dessincronizado;
   - ALLOW_INSECURE_EMPTY_TOKEN indevido, se seguro.
8. Criar relatório.

Validações:
- grep por secrets em git ls-files.
- grep frontend/src e dist por INTERNAL_API_TOKEN, X-Internal-Token e secrets.
- python manage.py check.
- health IE/CR/Backend.
- smoke intelligence.
- smoke renderer callback.
- confirmar .env reais ignorados.

Critérios de aceitação:
- Existe mecanismo local claro de secrets.
- Nenhum secret real fica versionado.
- INTERNAL_API_TOKEN sincronizado nos três serviços.
- DB e MinIO recebem credenciais por env local ignorado.
- Rotação local documentada e testada.
- IE e CR rejeitam token vazio.
- Frontend continua sem secrets.

Critérios de rejeição:
- Commitar .env real.
- Imprimir tokens/passwords.
- Usar ALLOW_INSECURE_EMPTY_TOKEN.
- Criar VITE_INTERNAL_API_TOKEN ou equivalente.
- Deixar token vazio em staging local.
- Declarar seguro sem greps.

Relatório:
Criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_05_secrets_locais_resultado.md

O relatório deve incluir:
- estado da execução;
- mecanismo local definido;
- inventário sem valores;
- ficheiros alterados;
- rotação testada;
- falhas seguras;
- greps;
- riscos;
- próximo passo recomendado.
```

## Prompt 06 (sonnet) — Criar scripts locais

``````prompt 
Iteração 6

Actua como DevOps local, engenheiro de automação e guardião de runbook.

Objectivo:
Criar scripts repetíveis para arrancar, validar, parar e, separadamente, resetar a stack staging local.

Backlog de referência:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_06_scripts_locais_resultado.md

Premissa obrigatória:
Infraestrutura local via Docker Compose para PostgreSQL e MinIO.
Serviços aplicacionais preferencialmente processos locais.
Nada de cloud.
Nada de secrets versionados.

Regras:
- Scripts não podem conter secrets reais.
- Reset destrutivo deve ser separado, explícito e exigir confirmação.
- Não usar portas proibidas.
- Não apagar volumes por acidente.
- Não alterar produto.
- Não quebrar comandos dev existentes.
- Não esconder falhas de healthcheck.

Tarefas:
1. Inspeccionar scripts existentes.
2. Definir nomes dos scripts conforme convenção do repositório.
3. Criar script para subir infraestrutura:
   - PostgreSQL;
   - MinIO;
   - bucket staging.
4. Criar script para parar infraestrutura sem apagar volumes.
5. Criar script de health:
   - PostgreSQL;
   - MinIO;
   - Backend Core live/ready;
   - Backend Core dependencies, se token staff disponível;
   - IE /health;
   - CR /health;
   - Frontend.
6. Criar script de reset destrutivo:
   - claramente separado;
   - exige confirmação;
   - documenta perda de dados.
7. Criar script opcional ou instruções para apps:
   - Backend Core;
   - Intelligence Engine;
   - Content Renderer;
   - Frontend.
8. Garantir que scripts leem env local ignorado.
9. Actualizar runbook.
10. Criar relatório.

Validações:
- Executar script de start infra, se seguro.
- Executar script de health.
- Executar script de stop infra.
- Não executar reset destrutivo sem autorização.
- scripts/check-forbidden-ports.ps1.
- grep por secrets nos scripts.
- validar sintaxe PowerShell ou shell conforme plataforma.

Critérios de aceitação:
- Infra local sobe de forma repetível.
- Infra local para sem apagar volumes.
- Health script detecta serviços correctos.
- Reset destrutivo é seguro e explícito.
- Scripts não contêm secrets.
- Runbook actualizado.
- Portas canónicas preservadas.

Critérios de rejeição:
- Reset destrutivo embutido em start/stop.
- Scripts com passwords/tokens.
- Health que passa com serviço errado.
- Comandos dependem de conhecimento tácito.
- Serviços em portas proibidas.

Relatório:
Criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_06_scripts_locais_resultado.md

O relatório deve incluir:
- estado da execução;
- scripts criados/alterados;
- comandos validados;
- healthchecks;
- reset destrutivo;
- ficheiros alterados;
- limitações;
- riscos;
- próximo passo recomendado.
```

## Prompt 07 (sonnet) — Quality gate local

``````prompt 
Iteração 7

Actua como QA lead, engenheiro DevOps local e guardião de regressões.

Objectivo:
Criar um quality gate local, executável manualmente e reutilizável futuramente em CI, sem depender de CI/CD remoto.

Backlog de referência:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_07_quality_gate_local_resultado.md

Premissa obrigatória:
Não criar CI/CD remoto obrigatório nesta fase.
O alvo é um quality gate local/CI-ready.

Regras:
- Não mascarar testes falhados.
- Não ignorar suites principais sem justificar.
- Não imprimir secrets.
- Não exigir cloud.
- Não exigir E2E por defeito se a stack não estiver activa, mas documentar modo com E2E.
- Não quebrar comandos existentes.

Tarefas:
1. Inventariar comandos de validação existentes:
   - Backend Core;
   - Intelligence Engine;
   - Content Renderer;
   - Frontend;
   - check-forbidden-ports;
   - greps de secrets.
2. Criar script quality local:
   - python manage.py check;
   - pytest Backend Core;
   - pytest Intelligence Engine;
   - npm test Content Renderer;
   - frontend unit tests;
   - frontend lint;
   - frontend build;
   - check-forbidden-ports;
   - grep de secrets em git ls-files.
3. Criar modo opcional com E2E:
   - só quando stack local staging estiver activa;
   - documentar variável ou flag.
4. Garantir saídas claras:
   - sucesso;
   - falha;
   - etapa que falhou.
5. Documentar pré-requisitos e tempo esperado.
6. Actualizar runbook.
7. Criar relatório.

Validações:
- Executar quality gate completo, se viável.
- Executar pelo menos subconjuntos quando limitações de tempo existirem.
- Confirmar que falha real retorna exit code não-zero.
- Confirmar que não imprime secrets.
- Confirmar que não usa portas proibidas.

Critérios de aceitação:
- Quality gate local existe.
- Suites principais cobertas.
- Falhas ficam visíveis.
- E2E pode ser executado opcionalmente contra stack local.
- Script é reutilizável por CI futura.
- Sem secrets impressos.

Critérios de rejeição:
- Ignorar falhas.
- Usar skip/xfail para passar.
- Exigir CI remoto.
- Exigir cloud.
- Não validar frontend build/lint.
- Não validar Backend Core.
- Não rodar greps de secrets.

Relatório:
Criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_07_quality_gate_local_resultado.md

O relatório deve incluir:
- estado da execução;
- script criado/alterado;
- comandos cobertos;
- resultado da execução;
- etapas opcionais;
- limitações;
- riscos;
- próximo passo recomendado.
```

## Prompt 08 (sonnet) — Executar E2E local

``````prompt 
Iteração 8

Actua como QA automation, DevOps local e guardião de validação E2E.

Objectivo:
Executar o Playwright E2E contra a stack staging local com PostgreSQL e MinIO, sem dry_run, sem mocks runtime e sem storage filesystem como destino staging.

Backlog de referência:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_08_e2e_local_resultado.md

Premissa obrigatória:
O E2E deve correr contra a stack local staging:
- Backend Core contra PostgreSQL container;
- Content Renderer contra MinIO container;
- Intelligence Engine real;
- Frontend real;
- sem dry_run;
- sem mocks runtime.

Regras:
- Não imprimir E2E_PASSWORD.
- Não usar SQLite.
- Não usar storage filesystem como destino staging.
- Não alterar o E2E para remover cobertura crítica.
- Não chamar IE/Renderer directamente no frontend.
- Não declarar E2E local validado se rodou contra stack dev antiga.
- Dados devem ser namespaced.
- Se a stack não estiver disponível, declarar bloqueio.

Tarefas:
1. Confirmar pré-condições:
   - PostgreSQL container healthy;
   - MinIO container healthy;
   - Backend Core usando PostgreSQL;
   - IE real activo;
   - Content Renderer usando MinIO;
   - Frontend activo;
   - secrets locais carregados;
   - E2E_PASSWORD disponível sem imprimir valor.
2. Executar seed_e2e_run contra PostgreSQL.
3. Executar pnpm test:e2e com base URL local.
4. Confirmar:
   - login;
   - workspace/campaign;
   - War Room;
   - intelligence real;
   - manual task;
   - report;
   - media kit;
   - content pack;
   - mark reviewed;
   - dismiss;
   - CampaignActionsPanel;
   - reload/persistência;
   - Network apenas Backend Core.
5. Confirmar storage:
   - report.pdf no MinIO;
   - media_kit.pdf no MinIO;
   - content outputs no MinIO;
   - Asset.public_url preenchido.
6. Registar run-id/correlation-id.
7. Criar relatório.

Validações:
- pnpm test:e2e.
- health live/ready/dependencies.
- verificar dados no PostgreSQL.
- verificar objectos no MinIO.
- grep logs por secrets.
- confirmar Network sem 8201/8202.
- confirmar que dados são namespaced.

Critérios de aceitação:
- E2E passa contra stack local staging.
- DB usado é PostgreSQL.
- Storage usado é MinIO.
- Outputs existem no MinIO.
- Asset.public_url funciona.
- Frontend só chama Backend Core.
- Dados são namespaced.
- Secrets não aparecem em logs.

Critérios de rejeição:
- E2E rodar contra SQLite.
- E2E rodar contra storage local filesystem.
- E2E com dry_run.
- E2E com mocks runtime.
- E2E alterado para remover report/media kit/content pack.
- Frontend chamar IE/Renderer.
- Password/token em logs.

Relatório:
Criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_08_e2e_local_resultado.md

O relatório deve incluir:
- estado da execução;
- ambiente usado;
- run-id;
- comandos;
- resultado E2E;
- evidência PostgreSQL;
- evidência MinIO;
- Network;
- logs/correlation-id;
- limitações;
- riscos;
- próximo passo recomendado.
```

## Prompt 09 (sonnet) — Segurança local

``````prompt 
Iteração 9

Actua como revisor de segurança aplicacional, DevSecOps local e guardião de fronteiras arquitecturais.

Objectivo:
Validar segurança operacional básica da stack staging local: frontend, tokens internos, CORS, health endpoints, PostgreSQL e MinIO.

Backlog de referência:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_09_seguranca_local_resultado.md

Premissa obrigatória:
Tudo é local, mas segurança continua obrigatória.
Local não significa desactivar autenticação interna.

Regras:
- Não imprimir tokens.
- Não executar pentest agressivo.
- Não usar ALLOW_INSECURE_EMPTY_TOKEN.
- Não expor X-Internal-Token no browser.
- Não tornar health dependencies público.
- Não declarar seguro sem evidência.
- Não alterar permissões destrutivamente.
- Não mascarar violações.

Tarefas:
1. Validar frontend:
   - bundle sem IE/Renderer URLs;
   - bundle sem INTERNAL_API_TOKEN;
   - Network apenas Backend Core.
2. Validar API client:
   - Authorization dinâmico;
   - X-Workspace-ID dinâmico;
   - X-Internal-Token bloqueado/removido.
3. Validar Backend Core:
   - live público;
   - ready público;
   - dependencies staff-only;
   - 401/403 correctos.
4. Validar IE:
   - /health público;
   - endpoints internos exigem X-Internal-Token.
5. Validar Content Renderer:
   - /health público;
   - /jobs exige X-Internal-Token;
   - ALLOW_INSECURE_EMPTY_TOKEN não activo.
6. Validar MinIO:
   - credenciais não versionadas;
   - bucket staging acessível conforme contrato;
   - listagem pública indevida não permitida, se a política exigir privado;
   - public_url funciona conforme decisão local.
7. Validar PostgreSQL:
   - credenciais não versionadas;
   - acesso local controlado;
   - não há password em logs.
8. Executar greps:
   - repositório;
   - frontend dist;
   - logs.
9. Criar relatório.

Validações:
- pnpm build e grep dist.
- Network browser ou E2E.
- curl health endpoints.
- testes 401/403, se viável.
- grep logs por Authorization, Bearer, X-Internal-Token, password, private_key, api_key.
- check-forbidden-ports.

Critérios de aceitação:
- Frontend isolado.
- Tokens internos apenas server-to-server.
- Health detalhado protegido.
- IE/CR não aceitam token vazio.
- MinIO sem credenciais expostas.
- DB credentials não versionadas.
- Logs sem secrets.
- Greps passam.

Critérios de rejeição:
- X-Internal-Token no browser.
- Frontend chama IE/Renderer.
- dependencies público.
- ALLOW_INSECURE_EMPTY_TOKEN activo.
- Bucket exposto sem decisão.
- Secrets em logs/docs/código.
- DB_PASSWORD versionado.

Relatório:
Criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_09_seguranca_local_resultado.md

O relatório deve incluir:
- estado da execução;
- verificações feitas;
- resultados;
- violações;
- correcções;
- pendências;
- riscos;
- próximo passo recomendado.
```

## Prompt 10 (sonnet) — Observabilidade local

``````prompt 
Iteração 10

Actua como engenheiro de observabilidade local, SRE e guardião de suporte operacional.

Objectivo:
Validar observabilidade local com logs, healthchecks e correlation-id ponta-a-ponta na stack com PostgreSQL e MinIO.

Backlog de referência:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_10_observabilidade_local_resultado.md

Premissa obrigatória:
Observabilidade local deve ser simples.
Não criar stack pesada de logs.
Não depender apenas de memória da consola sem documentar onde consultar.

Regras:
- Não imprimir secrets.
- Não registar payload integral de intelligence.
- Não criar Elasticsearch/Grafana/etc. nesta fase.
- Não declarar observabilidade empresarial.
- Não ocultar falhas.
- Não quebrar formato de logs existente.

Tarefas:
1. Definir destino dos logs locais:
   - stdout;
   - ficheiros locais ignorados;
   - docker logs;
   - outro mecanismo simples.
2. Definir retenção local simples:
   - manual;
   - rotação simples;
   - limpeza documentada.
3. Validar correlation-id em:
   - Backend Core;
   - Intelligence Engine;
   - Content Renderer.
4. Executar fluxo real:
   - intelligence;
   - CampaignAction;
   - Report;
   - MediaKit;
   - ContentPack;
   - callback.
5. Seguir a operação por correlation-id.
6. Validar falhas locais:
   - IE down;
   - Renderer down;
   - MinIO down;
   - PostgreSQL down, se seguro;
   - callback 403, se seguro.
7. Confirmar logs sem:
   - Authorization;
   - Bearer;
   - X-Internal-Token;
   - password;
   - private_key;
   - api_key.
8. Actualizar runbook com troubleshooting local:
   - onde ver logs;
   - como filtrar por correlation-id;
   - como diagnosticar MinIO;
   - como diagnosticar PostgreSQL.
9. Criar relatório.

Validações:
- health live/ready/dependencies.
- smoke real com correlation-id.
- grep logs por secrets.
- consulta por correlation-id.
- E2E, se disponível.
- docker logs para PostgreSQL/MinIO.
- check-forbidden-ports.

Critérios de aceitação:
- Operação local é rastreável por correlation-id.
- Logs indicam falhas principais.
- Logs não contêm secrets.
- Runbook explica onde consultar logs.
- MinIO/PostgreSQL têm diagnóstico básico.
- Observabilidade local é suficiente para suporte técnico.

Critérios de rejeição:
- Correlation-id perdido.
- Logs com tokens.
- Falhas sem sinal operacional.
- Runbook sem instrução de logs.
- Criar stack pesada desnecessária.
- Declarar observabilidade de produção.

Relatório:
Criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_10_observabilidade_local_resultado.md

O relatório deve incluir:
- estado da execução;
- destino dos logs;
- fluxo rastreado;
- falhas testadas;
- greps;
- lacunas;
- riscos;
- próximo passo recomendado.
```

## Prompt 11 (sonnet) — Actualizar runbook local

``````prompt 
Iteração 11

Actua como revisor operacional, QA de documentação e guardião de conhecimento transferível.

Objectivo:
Actualizar o runbook para reflectir a stack staging local real com PostgreSQL, MinIO, secrets locais, scripts, quality gate e E2E.

Backlog de referência:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\

Documentos a criar ou actualizar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\runbook_staging_local.md
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_11_runbook_local_resultado.md

Premissa obrigatória:
O runbook deve ser executável localmente.
Não incluir cloud.
Não incluir produção.
Não incluir secrets reais.

Regras:
- Não colocar tokens/passwords.
- Não documentar ALLOW_INSECURE_EMPTY_TOKEN como opção de staging.
- Não usar portas antigas.
- Não esconder reset destrutivo.
- Não assumir conhecimento tácito.
- Não declarar validação por terceiro se não houve terceiro.
- Não alterar produto.

Tarefas:
1. Ler runbook da fase 05.
2. Ler relatórios da fase 06 até ao momento.
3. Criar ou actualizar runbook_staging_local.md.
4. Incluir:
   - pré-requisitos;
   - Docker;
   - PostgreSQL container;
   - MinIO container;
   - env local/secrets;
   - start infra;
   - start apps;
   - healthchecks;
   - migrations;
   - seeds;
   - storage MinIO;
   - quality gate;
   - E2E;
   - segurança;
   - observabilidade;
   - troubleshooting;
   - reset destrutivo;
   - paragem.
5. Incluir matriz de sintomas:
   - Docker indisponível;
   - porta 5432 ocupada;
   - porta 9000/9001 ocupada;
   - DB migration falha;
   - MinIO health falha;
   - bucket ausente;
   - Asset.public_url vazio;
   - callback 403;
   - IE down;
   - Renderer down;
   - frontend chama porta errada;
   - E2E sem recommendations.
6. Se houver terceiro disponível:
   - pedir validação;
   - registar problemas;
   - corrigir.
7. Se não houver terceiro:
   - marcar validação por terceiro como pendente.
8. Criar relatório.

Validações:
- grep por secrets no runbook.
- check-forbidden-ports.
- confirmar comandos contra scripts reais.
- executar comandos seguros de health, se possível.
- validar que reset destrutivo está separado.

Critérios de aceitação:
- Runbook reflecte a stack local real.
- Comandos são concretos e testáveis.
- Não há secrets.
- Reset destrutivo está separado.
- Troubleshooting cobre PostgreSQL e MinIO.
- Validação por terceiro feita ou pendente sem mascarar.

Critérios de rejeição:
- Runbook com tokens/passwords.
- Runbook com cloud.
- Runbook com produção.
- ALLOW_INSECURE_EMPTY_TOKEN recomendado.
- Portas proibidas.
- Comandos inventados não testados.
- Declarar validação por terceiro sem terceiro.

Relatório:
Criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_11_runbook_local_resultado.md

O relatório deve incluir:
- estado da execução;
- ficheiros criados/alterados;
- secções do runbook;
- comandos validados;
- validação por terceiro ou pendência;
- greps;
- riscos;
- próximo passo recomendado.
```

## Prompt 12 (sonnet) — Fechar staging local

``````prompt 
Iteração 12

Actua como arquitecto de solução, tech lead, QA lead e guardião de prontidão.

Objectivo:
Consolidar a fase 06 e decidir honestamente se a stack pode ser considerada staging local formal, sem declarar produção.

Backlog de referência:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\

Documentos a criar ou actualizar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\estado_staging_local.md
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\arquitectura_staging_local.md
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\runbook_staging_local.md
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_12_fecho_staging_local_resultado.md

Premissa obrigatória:
Esta fase fecha staging local formal, não produção.
Não declarar cloud.
Não declarar staging externo.
Não declarar produção-ready.

Regras:
- Não declarar fase aceite se continuar dependente de SQLite.
- Não declarar fase aceite se storage staging ainda for filesystem local.
- Não declarar fase aceite se MinIO não foi validado.
- Não declarar fase aceite se E2E não rodou contra PostgreSQL e MinIO.
- Não declarar secrets resolvidos se existem secrets versionados.
- Separar implementado, validado, bloqueado, pendente e fora de escopo.
- Não expor secrets.
- Não alterar código funcional neste prompt.

Fonte de verdade:
1. backlog indicado;
2. relatórios dos Prompts 01 a 11;
3. arquitectura local;
4. runbook local;
5. validações executadas;
6. código actual;
7. documentação da fase 05.

Tarefas:
1. Ler backlog da fase.
2. Ler todos os relatórios em:
   frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\
3. Consolidar critérios:
   - topologia local;
   - Docker Compose infra;
   - PostgreSQL local persistente;
   - MinIO local;
   - secrets locais;
   - scripts locais;
   - quality gate;
   - E2E local;
   - segurança;
   - observabilidade;
   - runbook.
4. Actualizar arquitectura_staging_local.md.
5. Actualizar runbook_staging_local.md.
6. Criar estado_staging_local.md com:
   - resumo executivo;
   - estado final;
   - validações concluídas;
   - validações pendentes;
   - riscos;
   - limitações;
   - decisão de prontidão;
   - próximos passos.
7. Classificar o estado final usando uma opção honesta:
   - pronto_para_staging_local_formal;
   - pronto_parcialmente_com_pendencias;
   - executado_parcialmente;
   - bloqueado;
   - nao_pronto.
8. Executar validações finais, se viável:
   - quality gate local;
   - E2E local;
   - healthchecks;
   - check-forbidden-ports;
   - greps de secrets.
9. Criar relatório final.

Critérios de aceitação:
- Estado final documentado.
- Decisão de prontidão honesta.
- PostgreSQL local validado ou pendência explícita.
- MinIO local validado ou pendência explícita.
- E2E local validado ou pendência explícita.
- Secrets sem exposição.
- Produção não declarada.
- Próxima fase clara.

Critérios de rejeição:
- Declarar produção-ready.
- Declarar staging local formal com SQLite.
- Declarar staging local formal com storage filesystem.
- Omitir falhas de MinIO/PostgreSQL/E2E.
- Incluir tokens/passwords.
- Declarar validação por terceiro sem terceiro.
- Ignorar falhas de quality gate.

Relatório:
Criar:
frontend\docs\01_fundamentos\06_staging_infraestrutura_real\resultados_execucao\prompt_12_fecho_staging_local_resultado.md

O relatório deve incluir:
- estado final;
- evidência consolidada;
- critérios aceites;
- critérios rejeitados;
- validações executadas;
- ficheiros criados/alterados;
- limitações;
- riscos;
- decisão de prontidão;
- próximos passos recomendados.
```
