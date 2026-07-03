# Pipeline: Staging Local Hardening

## Prompt 01 (opus) — Estabilizar E2E local

```prompt
Iteração 1

Actua como QA automation lead, engenheiro frontend, engenheiro backend e guardião de regressões.

Objectivo:
Investigar e reduzir o flake observado no E2E local da fase 06, especialmente no fluxo de criação de Media Kit, sem remover cobertura e sem mascarar falhas.

Backlog de referência:
frontend/docs/01_fundamentos/07_staging_local_hardening/01_backlog.md

Pasta de resultados:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/

Relatório a criar:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/prompt_01_estabilizar_e2e_local_resultado.md

Contexto:
A fase 06 fechou como pronto_para_staging_local_formal. Durante o fecho, o E2E real foi executado contra PostgreSQL local e MinIO local. A primeira execução falhou no passo de criação de Media Kit, ficando o diálogo em Creating… por timeout. Uma chamada directa à API respondeu rapidamente. A segunda execução passou 12/12 em 31.1s. O flake ficou documentado como risco a monitorizar, não como bloqueio.

Premissas obrigatórias:
- A stack continua local-first.
- PostgreSQL corre em container local.
- MinIO corre em container local.
- Backend Core, Intelligence Engine, Content Renderer e Frontend correm como processos locais, salvo decisão técnica muito clara.
- Não usar cloud.
- Não usar dry_run.
- Não usar mocks runtime para fazer passar o E2E.
- Não remover cobertura.

Regras:
- Não apagar ou enfraquecer testes E2E existentes.
- Não remover o passo de Media Kit.
- Não resolver com sleep cego como solução principal.
- Não aumentar timeout global sem diagnóstico.
- Não introduzir retries cegos para esconder instabilidade.
- Não alterar produto sem evidência clara de bug real.
- Não expor E2E_PASSWORD, tokens, passwords ou access keys.
- Manter a validação Network apenas Backend Core.
- Manter cobertura de PostgreSQL e MinIO.
- Registar qualquer flake de forma explícita.

Fonte de verdade:
1. backlog indicado;
2. relatório autónomo do Prompt 08 da fase 06, se existir;
3. frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/resultados_execucao/prompt_12_fecho_staging_local_resultado.md;
4. frontend/e2e/;
5. scripts/staging-local-health.ps1;
6. scripts/staging-local-quality-gate.ps1;
7. logs em .local-runtime/logs/;
8. código frontend relacionado com Campaign Actions, Reports, Media Kits e Content Packs.

Tarefas:
1. Ler o backlog da fase 07.
2. Ler o relatório do E2E da fase 06 e identificar exactamente o flake observado.
3. Localizar os testes Playwright responsáveis por:
   - login;
   - abertura da campaign/War Room;
   - criação de manual task;
   - criação de report;
   - criação de media kit;
   - criação de content pack;
   - mark reviewed;
   - dismiss;
   - reload/persistência;
   - validação de Network.
4. Inspeccionar os waits/selectors associados ao diálogo de criação de Media Kit.
5. Determinar se o teste espera:
   - mudança de texto;
   - fecho do modal;
   - resposta de API;
   - mudança de estado no backend;
   - callback do Renderer;
   - actualização assíncrona via query/refetch.
6. Melhorar waits com base em sinais reais:
   - resposta HTTP relevante;
   - estado de UI específico;
   - presença do item criado;
   - estado de artefacto;
   - public_url quando aplicável;
   - ausência de chamadas a 8201/8202 pelo browser.
7. Melhorar diagnóstico em caso de falha:
   - screenshot;
   - Playwright trace, se já suportado ou fácil activar;
   - logs relevantes por run-id/correlation-id;
   - mensagens de erro mais accionáveis;
   - indicação clara do passo onde falhou.
8. Evitar sleeps arbitrários. Se algum pequeno timeout local for inevitável, justificar no relatório e limitar o impacto.
9. Executar a stack local ou confirmar que já está activa:
   - PostgreSQL healthy;
   - MinIO healthy;
   - Backend Core com DB_ENGINE=postgres;
   - Intelligence Engine real;
   - Content Renderer com STORAGE_PROVIDER=s3;
   - Frontend activo.
10. Executar o E2E pelo menos 3 vezes consecutivas, se viável.
11. Registar:
   - número de execuções;
   - número de passes;
   - número de flakes;
   - tempo de cada execução;
   - ponto de falha, se existir.
12. Se houver falha real de produto, parar e documentar antes de alterar produto. Corrigir produto apenas se a causa for inequívoca e limitada.
13. Actualizar documentação/runbook apenas se os comandos ou diagnóstico E2E mudarem.
14. Criar relatório.

Validações obrigatórias:
- scripts/staging-local-health.ps1 -RequireApps
- pnpm test:e2e
- repetir pnpm test:e2e pelo menos 3 vezes, se viável
- validar Network apenas Backend Core
- validar objectos MinIO dos artefactos criados
- validar Asset.public_url
- grep de logs por tokens/secrets, se logs forem recolhidos
- scripts/check-forbidden-ports.ps1

Critérios de aceitação:
- E2E passa em múltiplas execuções consecutivas ou o risco fica medido com evidência.
- Media Kit continua coberto.
- Report continua coberto.
- Content Pack continua coberto.
- Manual Task continua coberta.
- Network apenas Backend Core continua validada.
- PostgreSQL e MinIO continuam a ser usados.
- Falhas E2E deixam evidência diagnóstica.
- Nenhum secret é exposto.
- Não foi reduzida cobertura.

Critérios de rejeição:
- Remover teste de Media Kit.
- Aumentar timeout global sem diagnóstico.
- Introduzir retry cego para esconder falhas.
- Usar mocks/dry_run.
- Deixar de validar MinIO ou PostgreSQL.
- Esconder flake.
- Alterar produto sem causa raiz clara.

Expectativa verificável:
No final, deve existir o relatório prompt_01_estabilizar_e2e_local_resultado.md com ficheiros alterados, causa provável do flake, ajustes feitos, número de execuções E2E, resultados, evidência de Network/MinIO/Asset.public_url, pendências e próximo passo recomendado.
```

## Prompt 02 (opus) — Controlar timeout PostgreSQL

```prompt
Iteração 1

Actua como engenheiro backend Django, SRE local e guardião de disponibilidade.

Objectivo:
Adicionar e validar timeout curto de ligação PostgreSQL para evitar que pedidos normais do Backend Core fiquem pendurados quando o PostgreSQL local está indisponível.

Backlog de referência:
frontend/docs/01_fundamentos/07_staging_local_hardening/01_backlog.md

Pasta de resultados:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/

Relatório a criar:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/prompt_02_timeout_postgresql_resultado.md

Contexto:
Na fase 06, foi observado que /ready/ falhava rapidamente quando PostgreSQL estava down, mas pedidos normais como GET /api/v1/workspaces/ podiam ficar pendurados por mais de dois minutos. O achado foi documentado como risco de hardening.

Premissas obrigatórias:
- A alteração deve aplicar-se a PostgreSQL.
- SQLite/dev não pode quebrar.
- O timeout deve ser configurável por env quando fizer sentido.
- O valor default deve ser seguro para staging local.
- Não esconder a falha com retry infinito.
- Não expor credenciais em erro/log.

Regras:
- Não alterar modelos ou migrations sem necessidade.
- Não alterar lógica funcional de produto.
- Não reduzir segurança.
- Não aumentar indisponibilidade com retries longos.
- Não tornar /ready/ mais lento.
- Não aplicar parâmetro incompatível ao SQLite.
- Não imprimir DB_PASSWORD.
- Documentar comportamento antes/depois.

Fonte de verdade:
1. backlog indicado;
2. backend_core/config/settings.py;
3. backend_core/.env.example;
4. backend_core/.env.staging.local, apenas para execução local, sem imprimir valores;
5. frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/resultados_execucao/prompt_10_observabilidade_local_resultado.md;
6. runbook staging local da fase 06;
7. testes backend existentes.

Tarefas:
1. Ler o achado de observabilidade da fase 06 sobre PostgreSQL down.
2. Inspeccionar a configuração DATABASES em backend_core/config/settings.py.
3. Confirmar como o projecto escolhe DB_ENGINE=sqlite vs DB_ENGINE=postgres.
4. Definir uma variável de ambiente para timeout de ligação PostgreSQL, se fizer sentido, por exemplo DB_CONNECT_TIMEOUT_SECONDS.
5. Definir default curto e razoável para staging local.
6. Aplicar o timeout apenas quando DB_ENGINE=postgres.
7. Garantir que SQLite ignora essa configuração.
8. Actualizar .env.example com placeholder/comentário, sem segredo.
9. Validar comportamento normal com PostgreSQL up:
   - manage.py check;
   - migrations/showmigrations;
   - smoke básico.
10. Validar comportamento com PostgreSQL down:
   - /ready/ continua a falhar rapidamente;
   - GET /api/v1/workspaces/ ou endpoint equivalente falha em tempo controlado;
   - erro não expõe credenciais.
11. Validar recuperação depois de PostgreSQL voltar:
   - /ready/ volta a 200;
   - endpoint normal volta a responder.
12. Executar testes relevantes.
13. Actualizar runbook com o novo comportamento e troubleshooting.
14. Criar relatório.

Validações obrigatórias:
- python manage.py check com PostgreSQL up
- python manage.py showmigrations com PostgreSQL up
- pytest apps/workspaces apps/core, se existirem e forem relevantes
- pytest apps/campaign_actions apps/reports apps/content apps/integrations_bridge, se viável
- smoke GET /api/v1/system/health/ready/ com PostgreSQL up
- smoke endpoint normal com PostgreSQL up
- parar PostgreSQL container de forma controlada
- medir tempo de falha de /ready/
- medir tempo de falha de endpoint normal
- reiniciar PostgreSQL container
- confirmar recuperação
- grep por DB_PASSWORD/secrets em logs e ficheiros alterados
- scripts/check-forbidden-ports.ps1

Critérios de aceitação:
- Pedidos normais deixam de ficar pendurados por minutos quando PostgreSQL está down.
- /ready/ continua rápido.
- Recuperação após restart funciona.
- SQLite/dev não quebra.
- Testes relevantes passam.
- Configuração é documentada.
- Não há secrets em logs/docs/código.

Critérios de rejeição:
- Timeout aplicado ao SQLite de forma incompatível.
- Timeout demasiado alto para ser útil.
- Retry infinito.
- Erros com credenciais.
- Quebra de migrations/testes.
- Alterar produto sem necessidade.

Expectativa verificável:
No final, deve existir o relatório prompt_02_timeout_postgresql_resultado.md com ficheiros alterados, configuração introduzida, medições antes/depois ou comparação documentada, testes executados, riscos remanescentes e próximo passo recomendado.
```

## Prompt 03 (opus) — Criar credenciais MinIO não-root

```prompt
Iteração 3

Actua como engenheiro DevSecOps, engenheiro Node/TypeScript e guardião de permissões mínimas.

Objectivo:
Substituir o uso das credenciais root do MinIO pelo Content Renderer por credenciais dedicadas de serviço com permissões mínimas.

Backlog de referência:
frontend/docs/01_fundamentos/07_staging_local_hardening/01_backlog.md

Pasta de resultados:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/

Relatório a criar:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/prompt_03_minio_credenciais_nao_root_resultado.md

Contexto:
Na fase 06, o Content Renderer usou credenciais root do MinIO como STORAGE_ACCESS_KEY/STORAGE_SECRET_KEY. Isso foi aceite para staging local, mas registado como limitação. Esta fase deve criar credenciais dedicadas para o serviço, com policy mínima.

Premissas obrigatórias:
- MinIO continua local em container.
- Provider do Content Renderer continua STORAGE_PROVIDER=s3.
- Cloud continua fora do escopo.
- Root do MinIO deve ficar reservado para administração local.
- Content Renderer deve usar credenciais próprias.
- public_url deve continuar a funcionar.
- Listagem pública do bucket não pode ser reintroduzida.

Regras:
- Não imprimir credenciais.
- Não commitar .env real.
- Não expor access key/secret key em logs.
- Não voltar a usar mc anonymous set download se isso reintroduzir ListBucket.
- Não dar permissões admin ao utilizador do Content Renderer.
- Não dar DeleteObject salvo necessidade comprovada.
- Não quebrar provider local.
- Não quebrar upload/download real.
- Não alterar Backend Core desnecessariamente.

Fonte de verdade:
1. backlog indicado;
2. docker-compose.staging.local.yml;
3. .env.staging.local.example;
4. content_renderer/.env.example;
5. content_renderer/src/storage/s3-storage.ts;
6. content_renderer/src/storage/storage.factory.ts;
7. relatório Prompt 04 da fase 06;
8. relatório Prompt 09 da fase 06;
9. runbook staging local.

Tarefas:
1. Ler como o MinIO é inicializado no docker-compose.staging.local.yml.
2. Ler a política actual que permite download anónimo sem ListBucket.
3. Definir utilizador de serviço para o Content Renderer, por exemplo chartrex_renderer.
4. Definir policy mínima para o utilizador:
   - s3:PutObject;
   - s3:GetObject;
   - s3:AbortMultipartUpload, se o SDK exigir;
   - s3:ListBucket apenas se tecnicamente necessário e, se usado, limitado ao bucket;
   - sem admin;
   - sem delete por default.
5. Implementar criação idempotente do utilizador/policy no minio-bucket-init ou script equivalente.
6. Garantir que root continua apenas para administração.
7. Actualizar placeholders de env:
   - STORAGE_ACCESS_KEY;
   - STORAGE_SECRET_KEY;
   - eventual MINIO_RENDERER_USER;
   - eventual MINIO_RENDERER_PASSWORD.
8. Actualizar content_renderer/.env.staging.local localmente, se necessário, sem commitar valores reais.
9. Validar que Content Renderer usa as novas credenciais.
10. Validar uploads reais:
   - report.pdf;
   - media_kit.pdf;
   - content outputs.
11. Validar download via public_url.
12. Validar que as credenciais de serviço não conseguem operações administrativas.
13. Validar que bucket não permite ListBucket público.
14. Actualizar runbook.
15. Criar relatório.

Validações obrigatórias:
- docker compose config
- docker compose up -d com minio-bucket-init
- mc admin user info ou equivalente, sem imprimir segredo
- teste de upload real via Content Renderer
- smoke report/media kit/content pack
- download por public_url
- tentativa de operação admin com credencial de serviço deve falhar
- tentativa de listagem pública do bucket deve falhar
- npx vitest run no Content Renderer
- grep por STORAGE_SECRET_KEY/STORAGE_ACCESS_KEY com valores reais em git ls-files
- scripts/check-forbidden-ports.ps1

Critérios de aceitação:
- Content Renderer usa credenciais dedicadas não-root.
- Root fica reservado para administração local.
- Uploads continuam a funcionar.
- Downloads por public_url continuam a funcionar.
- Policy é mínima e documentada.
- ListBucket público não é reintroduzido.
- Credenciais não são versionadas.
- Testes passam.

Critérios de rejeição:
- Content Renderer continua a usar root sem justificação.
- Policy concede admin.
- Policy concede permissões excessivas sem motivo.
- Bucket volta a listar publicamente.
- Credenciais reais aparecem em ficheiros versionados ou logs.
- Provider local quebra.
- MinIO deixa de funcionar no staging local.

Expectativa verificável:
No final, deve existir o relatório prompt_03_minio_credenciais_nao_root_resultado.md com policy aplicada, ficheiros alterados, validações de upload/download, testes de permissões, greps de secrets, limitações e próximo passo recomendado.
```

## Prompt 04 (sonnet) — Implementar cleanup por run-id

```prompt
Iteração 4

Actua como engenheiro backend, QA automation e guardião de dados locais.

Objectivo:
Criar cleanup seguro por run-id para dados de E2E/smoke em PostgreSQL e MinIO, sem usar reset destrutivo como limpeza normal.

Backlog de referência:
frontend/docs/01_fundamentos/07_staging_local_hardening/01_backlog.md

Pasta de resultados:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/

Relatório a criar:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/prompt_04_cleanup_run_id_resultado.md

Contexto:
A fase 06 criou dados persistentes em PostgreSQL e MinIO para smoke/E2E. O reset destrutivo existe, mas deve continuar separado. Esta tarefa deve permitir limpar apenas dados de uma execução específica, por run-id, sem apagar dados de outras execuções.

Premissas obrigatórias:
- PostgreSQL local continua persistente.
- MinIO local continua persistente.
- Dados E2E devem estar namespaced por run-id/workspace/campaign quando possível.
- Reset destrutivo continua separado e exige confirmação.
- Cleanup normal não pode apagar volumes inteiros.

Regras:
- Não apagar dados fora do run-id.
- Não apagar todos os dados por default.
- Não executar reset destrutivo.
- Não expor secrets.
- Não criar script que aceite run-id vazio.
- Não apagar dados de produção, cloud ou ambiente externo.
- Não quebrar seed_e2e_run nem E2E.
- Se não for possível garantir limpeza segura, parar e documentar.

Fonte de verdade:
1. backlog indicado;
2. backend_core/apps/core/management/commands/seed_e2e_run.py;
3. testes E2E em frontend/e2e/;
4. models relacionados com workspace/campaign/actions/reports/media kits/content pack/assets/external jobs;
5. layout das chaves MinIO usado pelo Content Renderer;
6. scripts locais existentes;
7. runbook staging local.

Tarefas:
1. Inventariar dados criados por seed_e2e_run e pelo E2E.
2. Identificar como run-id é reflectido em:
   - email do utilizador;
   - workspace;
   - artist;
   - campaign;
   - reports;
   - media kits;
   - content pack requests;
   - campaign actions;
   - external jobs;
   - assets;
   - objectos MinIO.
3. Definir estratégia de cleanup segura:
   - management command Django;
   - script PowerShell que chama management command;
   - limpeza MinIO por prefixo derivado de workspace/job;
   - ou combinação.
4. Implementar cleanup por run-id com confirmação explícita.
5. Impedir execução com run-id vazio.
6. Implementar modo dry-run do cleanup, se viável.
7. Garantir que o cleanup mostra contagens, não secrets.
8. Validar criando uma execução de teste namespaced e limpando apenas essa execução.
9. Confirmar que dados de outra execução permanecem.
10. Confirmar que objectos MinIO associados são removidos ou que a limitação é documentada.
11. Actualizar runbook.
12. Criar relatório.

Validações obrigatórias:
- Criar ou reutilizar dois run-id distintos
- Executar cleanup dry-run para um deles
- Executar cleanup real para um deles, com confirmação
- Confirmar que o outro run-id permanece
- Confirmar consistência PostgreSQL/MinIO
- Executar E2E ou seed_e2e_run depois do cleanup para garantir que nada quebrou
- python manage.py check
- testes relevantes do management command, se criado
- grep por secrets nos scripts/relatório
- scripts/check-forbidden-ports.ps1

Critérios de aceitação:
- Existe cleanup seguro por run-id.
- run-id vazio é rejeitado.
- Cleanup não apaga dados de outras execuções.
- MinIO e PostgreSQL ficam consistentes ou limitações são claras.
- Reset destrutivo continua separado.
- Runbook actualizado.
- Testes passam.

Critérios de rejeição:
- Apagar volumes como cleanup normal.
- Apagar dados fora do run-id.
- Cleanup sem confirmação.
- Script com secrets.
- Quebrar E2E/seed.
- Deixar estado inconsistente sem documentar.

Expectativa verificável:
No final, deve existir o relatório prompt_04_cleanup_run_id_resultado.md com estratégia implementada, ficheiros alterados, validações de isolamento por run-id, resultados de PostgreSQL/MinIO, riscos e próximo passo recomendado.
```

## Prompt 05 (sonnet) — Reforçar diagnóstico E2E

```prompt
Iteração 5

Actua como QA automation, engenheiro de observabilidade local e guardião de diagnóstico.

Objectivo:
Melhorar a capacidade de diagnosticar falhas E2E, especialmente nos fluxos assíncronos de Renderer, MinIO e callbacks.

Backlog de referência:
frontend/docs/01_fundamentos/07_staging_local_hardening/01_backlog.md

Pasta de resultados:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/

Relatório a criar:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/prompt_05_diagnostico_e2e_resultado.md

Contexto:
O E2E da fase 06 passou, mas houve um flake inicial. A fase 07 deve garantir que futuras falhas deixam evidência accionável: run-id, correlation-id, screenshots, traces, logs relevantes e caminhos dos artefactos.

Premissas obrigatórias:
- Não remover cobertura.
- Não expor secrets.
- Não criar dependência cloud.
- Diagnóstico deve ser local e simples.
- E2E deve continuar a validar Network apenas Backend Core.
- Logs devem ser correlacionáveis.

Regras:
- Não imprimir E2E_PASSWORD.
- Não imprimir INTERNAL_API_TOKEN.
- Não gravar Authorization/Bearer em artefactos.
- Não guardar payload integral de intelligence se isso já foi evitado antes.
- Não transformar o E2E num teste superficial.
- Não usar screenshots/traces como substituto de asserts.
- Não quebrar o quality gate.

Fonte de verdade:
1. backlog indicado;
2. frontend/e2e/;
3. playwright config;
4. scripts/staging-local-quality-gate.ps1;
5. scripts/staging-local-health.ps1;
6. .local-runtime/logs/;
7. relatórios da fase 06 sobre observabilidade e E2E;
8. runbook staging local.

Tarefas:
1. Inspeccionar configuração Playwright actual.
2. Confirmar se screenshots, videos e traces já estão configurados.
3. Garantir artefactos úteis em falha:
   - screenshot;
   - trace;
   - test output;
   - run-id;
   - correlation-id quando disponível.
4. Melhorar logging do próprio teste:
   - run-id usado;
   - campaign/workspace redigidos quando necessário;
   - endpoints de backend usados;
   - número de acções encontradas.
5. Criar ou actualizar helper de diagnóstico E2E, se fizer sentido.
6. Integrar recolha de logs locais por run-id/correlation-id quando houver falha, se viável.
7. Garantir que paths de logs são documentados:
   - backend_core.err.log;
   - intelligence_engine.out.log;
   - content_renderer.out.log;
   - frontend.out.log;
   - artefactos Playwright.
8. Confirmar que os artefactos não contêm secrets.
9. Actualizar runbook.
10. Executar E2E para validar que a instrumentação não quebra.
11. Criar relatório.

Validações obrigatórias:
- pnpm test:e2e
- verificar directoria de artefactos Playwright
- simular falha controlada se for seguro e não destrutivo, apenas para confirmar screenshot/trace
- grep em artefactos gerados por INTERNAL_API_TOKEN, E2E_PASSWORD, Bearer, X-Internal-Token
- scripts/staging-local-health.ps1 -RequireApps
- scripts/check-forbidden-ports.ps1

Critérios de aceitação:
- Falhas E2E deixam evidência accionável.
- Artefactos são localizáveis por run-id/test.
- Logs são correlacionáveis.
- Nenhum secret aparece em artefactos.
- E2E continua a passar.
- Runbook explica como diagnosticar falhas.

Critérios de rejeição:
- Artefactos com tokens/passwords.
- Screenshots/traces substituem asserts.
- E2E deixa de validar Network.
- Diagnóstico depende de cloud.
- Logs ficam espalhados sem referência.
- Quality gate quebra sem justificação.

Expectativa verificável:
No final, deve existir o relatório prompt_05_diagnostico_e2e_resultado.md com melhorias implementadas, artefactos gerados, greps de segurança, validações E2E, limitações e próximo passo recomendado.
```

## Prompt 06 (sonnet) — Auditar gitignore perigoso

```prompt
Iteração 6

Actua como engenheiro de configuração, revisor de repositório e guardião de rastreabilidade de código.

Objectivo:
Auditar ficheiros .gitignore para detectar padrões não ancorados que possam esconder código-fonte por acidente, como aconteceu com content_renderer/src/storage/ na fase 06.

Backlog de referência:
frontend/docs/01_fundamentos/07_staging_local_hardening/01_backlog.md

Pasta de resultados:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/

Relatório a criar:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/prompt_06_auditoria_gitignore_resultado.md

Contexto:
Na fase 06, foi descoberto que content_renderer/.gitignore tinha o padrão storage/ não ancorado, escondendo content_renderer/src/storage/ do histórico git. O padrão foi corrigido ali. Esta tarefa verifica se existe o mesmo problema noutros .gitignore.

Premissas obrigatórias:
- Corrigir apenas padrões perigosos com evidência.
- Não passar a versionar artefactos gerados.
- Não remover ignores necessários.
- Não alterar código funcional.
- Não fazer limpeza destrutiva.
- Não esconder achados.

Regras:
- Usar git check-ignore para confirmar suspeitas.
- Não corrigir por estética.
- Não mexer em ignores globais sem necessidade.
- Não versionar dist/build/logs/storage gerados.
- Não alterar .env ignores que protegem secrets.
- Se houver dúvida, documentar em vez de alterar.

Fonte de verdade:
1. backlog indicado;
2. todos os ficheiros .gitignore do repositório;
3. git status;
4. git check-ignore;
5. estrutura de pastas do repositório;
6. relatório do Prompt 04 da fase 06 sobre content_renderer/.gitignore.

Tarefas:
1. Localizar todos os ficheiros .gitignore.
2. Listar padrões potencialmente perigosos:
   - storage/;
   - dist/;
   - build/;
   - logs/;
   - data/;
   - tmp/;
   - cache/;
   - output/;
   - public/;
   - assets/.
3. Para cada padrão suspeito, identificar:
   - se está ancorado;
   - se pode atingir subpastas de código;
   - se existe código em paths afectados.
4. Usar git check-ignore em paths representativos.
5. Corrigir apenas casos claramente perigosos:
   - ancorar com / quando o alvo é a raiz do serviço;
   - ou usar padrão mais específico.
6. Confirmar que artefactos gerados continuam ignorados.
7. Confirmar que código-fonte relevante deixa de estar ignorado.
8. Verificar git status para novos ficheiros inesperados.
9. Criar relatório.

Validações obrigatórias:
- listar .gitignore encontrados
- git check-ignore antes/depois em paths suspeitos
- git status --ignored, se útil
- confirmar que .env reais continuam ignorados
- confirmar que dist/build/storage runtime continuam ignorados quando devem
- scripts/check-forbidden-ports.ps1, se não for desnecessário
- grep de secrets apenas se algum ficheiro ignore/env for tocado

Critérios de aceitação:
- Padrões perigosos são auditados.
- Código-fonte não fica escondido por .gitignore.
- Artefactos gerados continuam ignorados.
- .env reais continuam ignorados.
- Alterações são mínimas e justificadas.
- Relatório documenta achados e não-achados.

Critérios de rejeição:
- Remover ignores necessários.
- Passar a versionar artefactos gerados.
- Alterar ignores sem evidência.
- Deixar código-fonte claramente ignorado.
- Tocar em .env ignores de forma insegura.
- Criar ruído massivo no git status.

Expectativa verificável:
No final, deve existir o relatório prompt_06_auditoria_gitignore_resultado.md com .gitignore analisados, padrões suspeitos, comandos git check-ignore executados, alterações feitas ou justificativa para não alterar, riscos e próximo passo recomendado.
```

## Prompt 07 (sonnet) — Validar runbook por operador

```prompt
Iteração 7

Actua como revisor operacional, QA de documentação e guardião de transferência de conhecimento.

Objectivo:
Preparar e, se houver operador disponível, executar a validação do runbook staging local por uma segunda pessoa sem contexto prévio.

Backlog de referência:
frontend/docs/01_fundamentos/07_staging_local_hardening/01_backlog.md

Pasta de resultados:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/

Relatório a criar:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/prompt_07_validacao_runbook_operador_resultado.md

Contexto:
A fase 06 deixou a validação por terceiro como pendência organizacional. A fase 07 deve tentar fechar essa pendência ou preparar um pacote de validação objectivo, sem fingir que foi feito.

Premissas obrigatórias:
- Não declarar validação por terceiro sem segundo operador real.
- Não orientar verbalmente e depois deixar o runbook incompleto.
- Não colocar secrets no relatório.
- Não executar reset destrutivo sem autorização explícita.
- Não declarar produção.
- Não reabrir fase 06.

Regras:
- O operador deve receber o runbook e pré-requisitos, não conhecimento tácito.
- Ajuda verbal crítica deve virar correcção de runbook.
- Dúvidas devem ser registadas.
- Falhas devem ser registadas.
- Se não houver operador disponível, criar checklist/pacote e marcar pendente.
- Não mascarar passos não executados.
- Não expor tokens/passwords.

Fonte de verdade:
1. backlog indicado;
2. frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/runbook_staging_local.md;
3. scripts locais existentes;
4. relatórios da fase 06;
5. relatórios já criados da fase 07;
6. estado final da fase 06.

Tarefas:
1. Ler o runbook staging local actual.
2. Criar uma checklist de validação por operador cobrindo:
   - pré-requisitos;
   - start infra;
   - start apps;
   - health;
   - migrations/check;
   - seed_e2e_run;
   - smoke básico;
   - quality gate parcial ou completo;
   - E2E, se viável;
   - cleanup por run-id, se já existir;
   - stop apps;
   - stop infra;
   - reset destrutivo apenas por leitura, salvo autorização explícita.
3. Se houver segundo operador disponível:
   - pedir execução seguindo apenas o runbook;
   - registar dúvidas;
   - registar comandos que falham;
   - corrigir runbook;
   - repetir os passos corrigidos, se possível.
4. Se não houver segundo operador disponível:
   - criar pacote de validação pronto para entrega;
   - marcar pendência como não fechada;
   - não declarar critério cumprido.
5. Verificar que o runbook não contém secrets.
6. Criar relatório.

Validações:
- grep por secrets no runbook e relatório
- scripts/check-forbidden-ports.ps1
- execução dos comandos pelo operador, se houver operador
- health real, se executado
- quality gate ou subconjunto, se executado
- E2E, se executado

Critérios de aceitação:
- Segundo operador executa o runbook sem ajuda verbal crítica, ou pendência fica formalmente registada.
- Ambiguidades identificadas são corrigidas.
- Comandos principais são confirmados ou marcados como pendentes.
- Runbook não contém secrets.
- Reset destrutivo continua protegido.
- Relatório é honesto.

Critérios de rejeição:
- Declarar validação sem operador.
- Ajudar verbalmente e não actualizar documentação.
- Ignorar falhas.
- Expor secrets.
- Executar reset destrutivo sem autorização.
- Confundir staging local com produção.

Expectativa verificável:
No final, deve existir o relatório prompt_07_validacao_runbook_operador_resultado.md com checklist usada, operador disponível ou não, passos executados, dúvidas, correcções de runbook, pendências e próximo passo recomendado.
```

## Prompt 08 (opus) — Preparar CI/CD real

```prompt
Iteração 8

Actua como engenheiro DevOps, QA lead e guardião de qualidade automatizada.

Objectivo:
Preparar uma primeira pipeline CI/CD real ou, se a plataforma não existir/estiver indefinida, documentar bloqueio concreto e deixar o caminho CI-ready claro, reutilizando o quality gate local.

Backlog de referência:
frontend/docs/01_fundamentos/07_staging_local_hardening/01_backlog.md

Pasta de resultados:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/

Relatório a criar:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/prompt_08_cicd_real_resultado.md

Contexto:
A fase 06 criou um quality gate local reutilizável por CI futura, mas não criou CI/CD real. Esta fase deve identificar a plataforma disponível e, se for seguro, criar uma pipeline mínima. Se não houver plataforma clara, não inventar: documentar bloqueio e preparar proposta.

Premissas obrigatórias:
- Sem deploy automático.
- Sem produção.
- Sem cloud obrigatória, salvo plataforma CI já existente no repositório.
- Sem secrets hardcoded.
- E2E não deve ser obrigatório se a stack local completa não estiver disponível no executor.
- Reutilizar scripts existentes quando possível.

Regras:
- Não inventar GitHub Actions/GitLab/Azure Pipelines se o repositório não indicar essa plataforma.
- Não commitar tokens.
- Não imprimir secrets.
- Não mascarar testes falhados.
- Não ignorar quality gate.
- Não criar deploy remoto.
- Não tornar E2E obrigatório sem infra.
- Documentar limitações.

Fonte de verdade:
1. backlog indicado;
2. scripts/staging-local-quality-gate.ps1;
3. package.json e pnpm/npm configs;
4. backend_core/pytest.ini;
5. intelligence_engine/pytest.ini;
6. content_renderer/package.json;
7. frontend/package.json;
8. .github/, .gitlab-ci.yml, azure-pipelines.yml ou equivalentes, se existirem;
9. resultados do Prompt 07 da fase 06 sobre quality gate.

Tarefas:
1. Detectar plataforma CI/CD já presente:
   - .github/workflows;
   - .gitlab-ci.yml;
   - azure-pipelines.yml;
   - Jenkinsfile;
   - outra.
2. Se existir plataforma clara:
   - criar workflow mínimo;
   - reutilizar staging-local-quality-gate.ps1 quando fizer sentido;
   - ou espelhar comandos por serviço se o runner não for Windows/PowerShell;
   - garantir instalação de dependências;
   - garantir cache segura;
   - garantir que secrets não são necessários para o gate obrigatório.
3. Se não existir plataforma clara:
   - criar documento de desenho/proposta;
   - não criar workflow arbitrário;
   - documentar decisão pendente.
4. Pipeline mínima deve cobrir:
   - backend_core_check;
   - backend_core_pytest;
   - intelligence_engine_pytest;
   - content_renderer typecheck/lint/test;
   - frontend test/lint/build;
   - forbidden ports;
   - secrets grep.
5. E2E:
   - deixar como job manual/opcional;
   - ou não incluir, se o executor não tiver stack local;
   - nunca declarar E2E CI pronto sem execução real.
6. Validar localmente, sempre que possível, os comandos que o CI vai executar.
7. Actualizar runbook/estado da fase 07.
8. Criar relatório.

Validações obrigatórias:
- Verificar existência/ausência de plataforma CI
- Validar sintaxe do workflow, se criado
- Executar scripts/staging-local-quality-gate.ps1 ou comandos equivalentes
- Confirmar que workflow não contém secrets
- Confirmar que não existe deploy automático
- Confirmar que E2E não é obrigatório sem stack
- scripts/check-forbidden-ports.ps1
- grep por secrets em ficheiros CI alterados

Critérios de aceitação:
- Existe workflow CI real mínimo ou bloqueio concreto documentado.
- Quality gate local é reutilizado ou espelhado.
- Jobs falham correctamente.
- Nenhum secret no YAML.
- Sem deploy automático.
- E2E é opcional/manual ou justificado como fora do CI inicial.
- Documentação actualizada.

Critérios de rejeição:
- Inventar plataforma não suportada.
- Hardcodar secrets.
- Criar deploy automático.
- Ignorar testes falhados.
- Tornar E2E obrigatório sem infra.
- Duplicar lógica de forma inconsistente.
- Declarar CI pronto sem validação mínima.

Expectativa verificável:
No final, deve existir o relatório prompt_08_cicd_real_resultado.md com plataforma detectada, workflow criado ou bloqueio documentado, comandos cobertos, validações executadas, limitações e próximo passo recomendado.
```

## Prompt 09 (sonnet) — Revalidar segurança local

```prompt
Iteração 9

Actua como revisor de segurança aplicacional, DevSecOps local e guardião de fronteiras arquitecturais.

Objectivo:
Revalidar a segurança local após as alterações de hardening: timeout PostgreSQL, credenciais MinIO não-root, cleanup, diagnóstico E2E e eventual CI/CD.

Backlog de referência:
frontend/docs/01_fundamentos/07_staging_local_hardening/01_backlog.md

Pasta de resultados:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/

Relatório a criar:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/prompt_09_revalidacao_seguranca_local_resultado.md

Contexto:
Na fase 06, a segurança local encontrou e corrigiu dois problemas reais: MinIO permitia listagem anónima do bucket e PostgreSQL/MinIO estavam publicados em 0.0.0.0. Esta revalidação garante que o hardening não reintroduziu regressões.

Premissas obrigatórias:
- Local não significa desactivar segurança.
- Frontend continua a chamar apenas Backend Core.
- X-Internal-Token continua server-to-server.
- MinIO não pode listar bucket publicamente.
- PostgreSQL/MinIO devem estar bindados a 127.0.0.1.
- Secrets não podem aparecer em logs/docs/código.

Regras:
- Não executar pentest agressivo.
- Não imprimir tokens.
- Não alterar permissões sem necessidade.
- Não mascarar violações.
- Não declarar seguro sem evidência.
- Não reabrir fase 06.
- Não declarar produção.

Fonte de verdade:
1. backlog indicado;
2. relatório Prompt 09 da fase 06;
3. docker-compose.staging.local.yml;
4. frontend/dist após build;
5. frontend/src/shared/api/;
6. .local-runtime/logs/;
7. MinIO policy actual;
8. PostgreSQL bind actual;
9. relatórios anteriores da fase 07.

Tarefas:
1. Validar frontend:
   - build fresco;
   - bundle sem URLs 8201/8202;
   - bundle sem INTERNAL_API_TOKEN real;
   - apenas VITE_BACKEND_API_BASE_URL como URL externa esperada.
2. Validar Network apenas Backend Core:
   - preferencialmente via Playwright/E2E;
   - se não for executado, justificar e usar evidência de bundle/código.
3. Validar API client:
   - bloqueio de X-Internal-Token no browser;
   - Authorization dinâmico;
   - X-Workspace-ID dinâmico.
4. Validar Backend Core:
   - live público;
   - ready público;
   - dependencies staff-only;
   - 401/403 correctos.
5. Validar IE/CR:
   - /health público;
   - endpoints internos exigem X-Internal-Token;
   - token ausente/errado rejeitado.
6. Validar MinIO:
   - download por public_url continua;
   - listagem pública do bucket continua 403;
   - credenciais não-root funcionam para upload;
   - credenciais não-root não fazem admin.
7. Validar PostgreSQL/MinIO bind:
   - docker port deve indicar 127.0.0.1, não 0.0.0.0.
8. Validar logs:
   - sem Authorization/Bearer;
   - sem X-Internal-Token com valor;
   - sem DB_PASSWORD;
   - sem STORAGE_SECRET_KEY;
   - sem E2E_PASSWORD.
9. Executar greps em git ls-files.
10. Criar relatório.

Validações obrigatórias:
- npm/pnpm build frontend
- grep dist por 8201/8202
- health endpoints
- testes 401/403
- docker port postgres/minio
- teste ListBucket público deve falhar
- teste download objecto conhecido deve passar
- grep logs por secrets
- scripts/staging-local-quality-gate.ps1 -Only secrets_grep, se disponível
- scripts/check-forbidden-ports.ps1

Critérios de aceitação:
- Frontend isolado.
- Network apenas Backend Core confirmada ou justificação clara.
- Tokens internos apenas server-to-server.
- MinIO sem ListBucket público.
- PostgreSQL/MinIO bindados em 127.0.0.1.
- Credenciais MinIO não-root validadas.
- Logs sem secrets.
- Greps passam.

Critérios de rejeição:
- Regressão para 0.0.0.0.
- Bucket lista publicamente.
- Frontend chama IE/Renderer.
- Token interno no browser.
- Secrets em logs/docs/código.
- dependencies público.
- ALLOW_INSECURE_EMPTY_TOKEN activo.

Expectativa verificável:
No final, deve existir o relatório prompt_09_revalidacao_seguranca_local_resultado.md com verificações executadas, violações encontradas/corrigidas, greps, evidência de MinIO/PostgreSQL/frontend, riscos e próximo passo recomendado.
```

## Prompt 10 (opus) — Fechar hardening local

```prompt
Iteração 10

Actua como arquitecto de solução, tech lead, QA lead e guardião de prontidão.

Objectivo:
Consolidar a fase 07_staging_local_hardening e decidir honestamente se o staging local formal ficou endurecido, sem declarar produção.

Backlog de referência:
frontend/docs/01_fundamentos/07_staging_local_hardening/01_backlog.md

Pasta de resultados:
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/

Documentos a criar ou actualizar:
frontend/docs/01_fundamentos/07_staging_local_hardening/estado_hardening_local.md
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/prompt_10_fecho_hardening_local_resultado.md

Documentos que podem ser actualizados se necessário:
frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/runbook_staging_local.md
frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/estado_staging_local.md

Contexto:
A fase 06 fechou como pronto_para_staging_local_formal. A fase 07 endurece riscos remanescentes: flake E2E, timeout PostgreSQL, credenciais MinIO não-root, validação por segundo operador, CI/CD real ou bloqueio documentado, cleanup local, diagnóstico E2E, auditoria gitignore e segurança local.

Premissas obrigatórias:
- Não declarar produção.
- Não declarar cloud.
- Não reabrir a classificação da fase 06.
- Separar implementado, validado, pendente, bloqueado e fora de escopo.
- Não esconder flakes.
- Não esconder falhas de security/quality gate.
- Não expor secrets.
- Não alterar código funcional neste prompt, salvo correcções documentais finais.

Regras:
- Não declarar hardening fechado se os riscos principais foram ignorados.
- Se algum item não foi executado, classificar honestamente.
- Se CI/CD real não foi criado, documentar bloqueio.
- Se segundo operador não validou runbook, manter pendência organizacional.
- Se E2E ainda tiver flake, quantificar e documentar.
- Se MinIO continuar root, justificar ou marcar pendência.
- Se timeout PostgreSQL não foi corrigido, marcar risco.
- Produção continua fora do escopo.

Fonte de verdade:
1. backlog indicado;
2. todos os relatórios em frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/;
3. runbook staging local;
4. estado staging local da fase 06;
5. scripts locais;
6. quality gate;
7. E2E;
8. relatórios da fase 06 quando necessário.

Tarefas:
1. Ler integralmente o backlog da fase 07.
2. Ler todos os relatórios da fase 07.
3. Consolidar estado por item:
   - STG-HARD-001 E2E;
   - STG-HARD-002 timeout PostgreSQL;
   - STG-HARD-003 MinIO não-root;
   - STG-HARD-004 runbook por segundo operador;
   - STG-HARD-005 CI/CD real;
   - STG-HARD-006 cleanup por run-id;
   - STG-HARD-007 diagnóstico E2E;
   - STG-HARD-008 gitignore;
   - STG-HARD-009 segurança;
   - STG-HARD-010 fecho.
4. Executar validações finais, se viável:
   - scripts/staging-local-health.ps1 -RequireApps;
   - scripts/staging-local-quality-gate.ps1;
   - pnpm test:e2e;
   - repetir E2E se a fase mexeu no E2E;
   - scripts/check-forbidden-ports.ps1;
   - secrets_grep;
   - segurança local crítica.
5. Criar estado_hardening_local.md com:
   - resumo executivo;
   - estado final;
   - melhorias implementadas;
   - validações executadas;
   - pendências;
   - riscos remanescentes;
   - decisão de prontidão;
   - próximos passos.
6. Actualizar runbook staging local se o hardening mudou comandos, diagnóstico, cleanup, MinIO, CI ou timeout.
7. Criar relatório final.
8. Classificar estado final com uma opção honesta:
   - hardening_local_concluido;
   - hardening_local_concluido_com_pendencias;
   - executado_parcialmente;
   - bloqueado;
   - nao_pronto.

Critérios de aceitação:
- Estado final documentado.
- E2E estabilizado ou risco quantificado.
- Timeout PostgreSQL tratado ou decisão documentada.
- Credenciais MinIO endurecidas ou pendência justificada.
- Runbook validado por segundo operador ou pendência explícita.
- CI/CD real criado ou bloqueio concreto documentado.
- Quality gate verde ou falhas explícitas.
- Segurança local revalidada.
- Produção não declarada.
- Secrets não expostos.

Critérios de rejeição:
- Declarar hardening concluído ignorando flake.
- Ignorar timeout PostgreSQL.
- Manter MinIO root sem decisão.
- Declarar validação por terceiro sem terceiro.
- Criar CI insegura.
- Mascarar falhas.
- Reintroduzir ListBucket público.
- Regressão para 0.0.0.0.
- Frontend chamar IE/Renderer.
- Declarar produção-ready.

Expectativa verificável:
No final, deve existir estado_hardening_local.md e prompt_10_fecho_hardening_local_resultado.md, contendo estado final, ficheiros alterados, validações executadas, pendências, riscos, decisão de prontidão e próximo passo recomendado.
```
