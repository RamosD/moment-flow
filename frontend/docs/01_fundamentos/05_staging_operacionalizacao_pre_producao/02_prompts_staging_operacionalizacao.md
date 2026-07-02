# Pipeline: Staging Pré-Produção

## Prompt 01 (sonnet) — Arquitectura alvo

```prompt
Iteração 1

Objectivo:
Definir e documentar a arquitectura alvo de staging pré-produção, separando claramente dev local, staging técnico, pré-produção e produção.

Backlog de referência:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\

Documentos a criar ou actualizar:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\arquitectura_staging_pre_producao.md
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\prompt_01_arquitectura_alvo_resultado.md

Contexto:
A fase 04 validou a cadeia real Frontend -> Backend Core -> Intelligence Engine / Content Renderer em ambiente técnico controlado. Esta fase deve transformar essa validação num staging formal pré-produção, sem adicionar funcionalidades de produto.

Regras:
- Não alterar lógica funcional de produto neste prompt.
- Não alterar código runtime salvo correcções documentais/configuracionais estritamente necessárias.
- Não colocar secrets reais em documentação.
- Não declarar produção-ready.
- Não confundir dev local com staging formal.
- O frontend deve continuar a chamar apenas o Backend Core.
- O frontend nunca deve chamar Intelligence Engine ou Content Renderer directamente.
- O frontend nunca deve enviar X-Internal-Token.
- Usar português de Portugal.

Fonte de verdade:
1. instruções explícitas e recentes do utilizador;
2. backlog indicado;
3. código actual do repositório;
4. documentos finais da fase 04;
5. documentação de portas;
6. settings, env examples, scripts e runbooks existentes.

Tarefas:
1. Ler integralmente o backlog indicado.
2. Ler os documentos finais da fase 04, se existirem:
   - frontend\docs\01_fundamentos\04_staging_campaign_actions_with_real_ie_renderer\estado_staging_ie_renderer.md
   - frontend\docs\01_fundamentos\04_staging_campaign_actions_with_real_ie_renderer\arquitectura_staging_ie_renderer.md
   - frontend\docs\01_fundamentos\04_staging_campaign_actions_with_real_ie_renderer\resultados_execucao\prompt_10_estado_final_staging_resultado.md
3. Inventariar os componentes actuais:
   - Frontend Web;
   - Backend Core;
   - Intelligence Engine;
   - Content Renderer;
   - base de dados;
   - storage;
   - jobs;
   - callbacks;
   - healthchecks;
   - logs;
   - scripts de arranque;
   - variáveis de ambiente.
4. Documentar a arquitectura alvo de staging pré-produção:
   - componentes;
   - responsabilidades;
   - portas canónicas;
   - URLs internas e externas;
   - fluxo Frontend -> Backend Core;
   - fluxo Backend Core -> Intelligence Engine;
   - fluxo Backend Core -> Content Renderer;
   - callback Content Renderer -> Backend Core;
   - base de dados alvo;
   - storage alvo;
   - secrets;
   - logs;
   - healthchecks;
   - limites conhecidos.
5. Separar claramente:
   - dev local;
   - staging técnico;
   - staging pré-produção;
   - produção.
6. Identificar decisões pendentes, especialmente:
   - DB alvo;
   - provider de object storage;
   - mecanismo de secrets;
   - public_url ou signed_url;
   - estratégia de logs;
   - ferramenta E2E.
7. Criar ou actualizar arquitectura_staging_pre_producao.md.
8. Criar relatório de execução.

Validações:
- Verificar que a documentação criada não contém tokens, passwords, chaves privadas, connection strings reais ou secrets.
- Verificar que não foram introduzidas portas antigas como default activo.
- Verificar que a regra Frontend -> Backend Core continua explícita.
- Se executar comandos, limitar a comandos de inspecção seguros.

Critérios de aceitação:
- Arquitectura staging documentada.
- Limites entre dev/staging/prod claros.
- Responsabilidades de cada componente explícitas.
- Decisões pendentes registadas.
- Nenhum secret documentado.
- Nenhuma alteração funcional indevida.

Relatório:
Criar:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\prompt_01_arquitectura_alvo_resultado.md

O relatório deve incluir:
- estado da execução;
- resumo objectivo;
- ficheiros criados/alterados;
- decisões documentadas;
- decisões pendentes;
- validações executadas;
- riscos;
- próximo passo recomendado.
```

## Prompt 02 (sonnet) — DB staging

```prompt
Iteração 2

Objectivo:
Preparar e validar a migração do Backend Core de SQLite dev para uma base de dados alvo de staging, sem quebrar CampaignActions, artefactos, jobs e callbacks.

Backlog de referência:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\prompt_02_db_staging_resultado.md

Contexto:
A fase 04 foi validada com SQLite dev. Para staging pré-produção, é necessário validar o Backend Core numa base de dados alvo mais próxima do ambiente real.

Regras:
- Não apagar dados sem autorização explícita.
- Não commitar credenciais de base de dados.
- Não colocar connection strings reais em documentação.
- Não assumir que SQLite é suficiente para staging formal.
- Não declarar staging formal se continuar dependente de SQLite dev.
- Não alterar lógica funcional fora do escopo de configuração/migração.
- Se não existir DB alvo disponível, documentar bloqueio e preparar instruções/configuração sem fingir validação.

Fonte de verdade:
1. backlog indicado;
2. arquitectura criada no Prompt 01;
3. settings actuais do Backend Core;
4. migrations existentes;
5. testes existentes;
6. documentação de deploy/configuração existente.

Tarefas:
1. Inspeccionar configuração actual de base de dados no Backend Core.
2. Identificar suporte actual a DATABASE_URL ou variável equivalente.
3. Confirmar dependências necessárias para o DB alvo, por exemplo PostgreSQL.
4. Se o suporte ao DB alvo já existir:
   - documentar variáveis necessárias;
   - validar que não há credenciais hardcoded;
   - preparar comandos de migration.
5. Se o suporte não existir:
   - propor a alteração mínima segura;
   - implementar apenas se for claro, pequeno e alinhado com padrões do repositório;
   - caso contrário, documentar backlog técnico complementar.
6. Validar migrations relevantes:
   - users/auth;
   - workspaces;
   - campaigns;
   - campaign_actions;
   - reports;
   - media kits;
   - content pack requests;
   - content outputs;
   - external job references;
   - assets.
7. Criar ou documentar seed mínimo:
   - user dev/staging;
   - workspace;
   - artist;
   - campaign;
   - content packs.
8. Executar smoke API se houver DB alvo disponível:
   - auth;
   - workspace;
   - campaign;
   - campaign-actions;
   - reports/media kits/content pack requests;
   - external jobs, se aplicável.
9. Documentar backup/rollback básico para staging.
10. Criar relatório de execução.

Validações:
- python manage.py check
- python manage.py showmigrations, se aplicável
- python manage.py migrate, apenas contra DB alvo autorizado
- pytest apps/campaign_actions, se viável
- smoke API, se DB alvo estiver disponível
- grep por secrets em ficheiros alterados

Critérios de aceitação:
- DB alvo identificado e documentado.
- Configuração de DB staging clara.
- Migrations validadas ou bloqueio documentado.
- Fluxo CampaignActions não depende de SQLite para ser considerado staging formal.
- Nenhuma credencial real no repositório.
- Rollback/backup básico documentado.

Critérios de rejeição:
- Declarar DB staging validada sem DB alvo.
- Usar SQLite dev como staging formal.
- Escrever secrets no repositório.
- Apagar dados sem autorização.
- Ignorar falhas de migrations.

Relatório:
O relatório deve incluir:
- estado da execução;
- DB alvo identificado;
- variáveis necessárias;
- migrations executadas ou pendentes;
- dados seed;
- validações;
- bloqueios;
- riscos;
- próximo passo recomendado.
```

## Prompt 03 (sonnet) — Object storage

```prompt
Iteração 3

Objectivo:
Preparar Content Renderer e Backend Core para usar object storage em staging e resolver URL canónica dos assets, substituindo a dependência de storage local.

Backlog de referência:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\prompt_03_object_storage_resultado.md

Contexto:
A fase 04 validou outputs reais em storage local do Content Renderer. Para staging pré-produção, os assets devem depender de um provider adequado, com URL canónica ou signed URL, e não de content_renderer/storage local.

Regras:
- Não commitar credenciais de storage.
- Não inventar provider se a decisão não existir.
- Não quebrar o modo local de desenvolvimento.
- Não declarar object storage validado sem upload/download real.
- Não expor URLs assinadas com secrets no relatório.
- Não alterar lógica funcional fora do escopo de storage/assets.
- Se não houver provider real disponível, preparar contrato/configuração e registar bloqueio.

Fonte de verdade:
1. backlog indicado;
2. arquitectura da fase;
3. Content Renderer actual;
4. Backend Core Asset model/callbacks;
5. docs e env examples;
6. fase 04, especialmente limitações sobre Asset.public_url.

Tarefas:
1. Inspeccionar implementação actual de storage no Content Renderer.
2. Confirmar se existe abstraction para storage provider:
   - local;
   - S3;
   - R2;
   - MinIO;
   - outro.
3. Inspeccionar callbacks do Backend Core que persistem assets.
4. Confirmar campos disponíveis:
   - storage_provider;
   - storage_key;
   - public_url;
   - mime;
   - size;
   - metadata.
5. Definir contrato staging para assets:
   - storage_key estável;
   - public_url;
   - signed_url, se aplicável;
   - regras de expiração;
   - acesso público ou privado.
6. Se o provider já existir:
   - configurar env examples;
   - validar upload;
   - validar download;
   - validar public_url/signed_url;
   - validar Report, MediaKit e ContentOutput.
7. Se o provider não existir:
   - criar backlog técnico complementar;
   - documentar interface mínima necessária;
   - evitar implementação parcial perigosa.
8. Se for implementado algo:
   - manter compatibilidade com storage local;
   - adicionar testes;
   - actualizar env examples;
   - actualizar documentação.
9. Criar relatório.

Validações:
- npm test no Content Renderer, se alterado.
- python manage.py check, se Backend Core alterado.
- testes específicos de storage, se existirem.
- smoke de geração de report/media kit/content pack, se provider disponível.
- greps por secrets.
- confirmar que public_url não fica null quando o contrato exigir URL canónica.

Critérios de aceitação:
- Provider de storage staging identificado.
- Contrato de asset URL documentado.
- Storage local deixa de ser requisito para staging formal.
- public_url ou signed_url tem regra definida.
- Upload/download validado ou bloqueio explícito documentado.
- Sem secrets em código/logs/docs.

Critérios de rejeição:
- Declarar object storage pronto usando apenas storage local.
- Persistir secrets em ficheiros versionados.
- Quebrar modo local.
- Deixar outputs inacessíveis sem documentar limitação.

Relatório:
O relatório deve incluir:
- estado da execução;
- provider escolhido ou pendente;
- contrato de URL;
- ficheiros alterados;
- validações;
- limitações;
- riscos;
- próximo passo recomendado.
```

## Prompt 04 (sonnet) — Gestão de segredos

```prompt
Iteração 4

Objectivo:
Formalizar a gestão de segredos para staging pré-produção, removendo dependência de tokens manuais dispersos em .env local e garantindo que nenhum segredo real entra no repositório ou nos logs.

Backlog de referência:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\prompt_04_gestao_segredos_resultado.md

Contexto:
A fase 04 exigiu INTERNAL_API_TOKEN partilhado entre Backend Core, Intelligence Engine e Content Renderer. Em staging pré-produção, essa gestão deve ser formal, rotacionável e segura.

Regras:
- Nunca imprimir valores reais de secrets.
- Nunca commitar secrets.
- Nunca criar exemplos com tokens reais.
- Não desactivar autenticação interna em staging.
- Não usar ALLOW_INSECURE_EMPTY_TOKEN em staging.
- Não expor X-Internal-Token no frontend.
- O frontend não deve conter secrets internos.
- Se alterar ficheiros .env.example, usar placeholders seguros.

Fonte de verdade:
1. backlog indicado;
2. env examples existentes;
3. settings dos três serviços;
4. scripts de arranque;
5. docs de segurança;
6. resultados da fase 04.

Tarefas:
1. Inventariar secrets necessários:
   - INTERNAL_API_TOKEN;
   - DB credentials;
   - storage credentials;
   - JWT/secret key, se aplicável;
   - tokens de terceiros, se existirem;
   - callback/internal service tokens;
   - chaves de assinatura de URL, se aplicável.
2. Identificar onde cada secret é consumido:
   - Backend Core;
   - Intelligence Engine;
   - Content Renderer;
   - CI/CD;
   - scripts de staging.
3. Definir mecanismo de fornecimento para staging:
   - variáveis de ambiente;
   - secret store;
   - CI variables;
   - ficheiro local não versionado;
   - outro mecanismo existente.
4. Actualizar .env.example ou documentação com placeholders seguros.
5. Garantir que o frontend não tem:
   - INTERNAL_API_TOKEN;
   - X-Internal-Token;
   - DB credentials;
   - storage secrets;
   - IE/CR direct URLs se forem internas.
6. Verificar .gitignore para ficheiros sensíveis.
7. Criar ou actualizar documentação de rotação:
   - como gerar;
   - onde colocar;
   - como reiniciar serviços;
   - como validar;
   - como revogar.
8. Executar greps de segurança em ficheiros activos e docs da fase.
9. Criar relatório.

Validações:
- grep por padrões sensíveis:
  - INTERNAL_API_TOKEN=
  - SECRET_KEY=
  - PASSWORD=
  - AWS_SECRET
  - ACCESS_KEY
  - PRIVATE_KEY
  - Bearer valor hardcoded
  - X-Internal-Token
- confirmar que ocorrências são placeholders, guards, denylist, docs ou env local ignorado.
- confirmar que frontend/src não contém secrets internos.
- python manage.py check, se settings alterados.
- npm/pnpm lint se ficheiros JS/TS alterados.

Critérios de aceitação:
- Inventário de secrets completo.
- Mecanismo de secret staging documentado.
- .env.example usa placeholders seguros.
- Sem secrets reais no repositório.
- Sem tokens em logs/documentos.
- Rotação documentada.
- Frontend continua sem segredos internos.

Critérios de rejeição:
- Secret real em ficheiro versionado.
- ALLOW_INSECURE_EMPTY_TOKEN como prática de staging.
- X-Internal-Token acessível no browser.
- Documentação com token real.
- Falta de plano de rotação.

Relatório:
O relatório deve incluir:
- estado da execução;
- inventário de secrets sem valores;
- ficheiros alterados;
- greps executados;
- violações encontradas/corrigidas;
- pendências;
- riscos;
- próximo passo recomendado.
```

## Prompt 05 (sonnet) — Correlation-id

```prompt
Iteração 5

Objectivo:
Implementar ou preparar a propagação de um correlation-id único ponta-a-ponta entre Backend Core, Intelligence Engine, CampaignActions, artefactos, jobs, Content Renderer e callbacks.

Backlog de referência:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\prompt_05_correlation_id_resultado.md

Contexto:
A fase 04 identificou uma lacuna: não existe um correlation-id único ponta-a-ponta. Intelligence, jobs e callbacks têm request_ids independentes ou incompletos. Para staging pré-produção, é necessário rastrear uma operação completa.

Regras:
- Não registar tokens.
- Não registar payload integral da intelligence.
- Não quebrar compatibilidade dos endpoints.
- Não alterar o contrato público do frontend salvo se necessário e documentado.
- O correlation-id deve ser seguro, opaco e não conter PII.
- Não substituir IDs de domínio como action_id, campaign_id ou job_id; correlation-id complementa esses IDs.
- Se a alteração for grande, implementar incrementalmente e documentar pendências.

Fonte de verdade:
1. backlog indicado;
2. logs e lacunas da fase 04;
3. middleware/API client do Backend Core;
4. client de IE;
5. ExternalJobReference;
6. Content Renderer job service;
7. callback client;
8. logs estruturados existentes.

Tarefas:
1. Inspeccionar como request_id é gerado actualmente no Backend Core.
2. Inspeccionar como request_id é enviado para IE.
3. Inspeccionar como job request_id é gerado para ExternalJobReference.
4. Inspeccionar como Content Renderer recebe e loga request_id.
5. Inspeccionar callback para Backend Core.
6. Definir header canónico:
   - X-Request-ID ou equivalente existente.
7. Definir estratégia:
   - aceitar request_id existente se vier do frontend/proxy;
   - gerar no Backend Core se ausente;
   - reutilizar o mesmo id em IE, CampaignAction, artefacto, job e callback.
8. Implementar alteração mínima segura, se viável:
   - middleware/contexto no Backend Core;
   - propagação para IE;
   - propagação para ExternalJobReference;
   - propagação para Content Renderer;
   - callback preserva request_id;
   - logs incluem correlation_id/request_id.
9. Adicionar logs para criação de:
   - CampaignAction;
   - Report;
   - MediaKit;
   - ContentPackRequest;
   - ExternalJobReference.
10. Adicionar ou actualizar testes.
11. Se a implementação completa for demasiado grande, criar backlog técnico detalhado e implementar apenas fundamentos seguros.
12. Criar relatório.

Validações:
- python manage.py check.
- pytest relevante no Backend Core.
- npm test no Content Renderer, se alterado.
- pytest no Intelligence Engine, se alterado.
- smoke API:
  - intelligence;
  - report job;
  - callback.
- Greps de logs para garantir presença de correlation-id e ausência de secrets.

Critérios de aceitação:
- Uma operação pode ser rastreada BC -> IE -> CampaignAction -> Artifact -> Job -> Renderer -> Callback.
- Logs dos três serviços contêm o mesmo correlation-id ou a relação explícita entre ids.
- action_id, artifact_id e job_id aparecem associados ao correlation-id.
- Nenhum token aparece em logs.
- Testes relevantes passam.

Critérios de rejeição:
- Criar correlation-id diferente em cada serviço sem vínculo.
- Registar Authorization, Bearer ou X-Internal-Token.
- Quebrar callbacks existentes.
- Quebrar jobs existentes.
- Fazer alteração ampla sem testes.

Relatório:
O relatório deve incluir:
- estado da execução;
- desenho do correlation-id;
- ficheiros alterados;
- testes;
- exemplo de fluxo com ids redigidos;
- lacunas restantes;
- riscos;
- próximo passo recomendado.
```

## Prompt 06 (sonnet) — Health e logs

```prompt
Iteração 6

Objectivo:
Validar e endurecer observabilidade operacional mínima: healthchecks, readiness, logs estruturados, sinais de falha e diagnóstico de dependências.

Backlog de referência:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\prompt_06_health_logs_resultado.md

Contexto:
A fase 04 validou health individual dos serviços e logs básicos, mas o health agregado e a observabilidade operacional ainda precisam de consolidação para staging pré-produção.

Regras:
- Não expor secrets em logs.
- Não tornar health público se deve ser restrito.
- Não mascarar dependências indisponíveis.
- Não declarar readiness se apenas liveness passou.
- Não adicionar observabilidade pesada sem necessidade.
- Não alterar endpoints públicos sem compatibilidade.

Fonte de verdade:
1. backlog indicado;
2. endpoint de health agregado do Backend Core;
3. health do IE;
4. health do Content Renderer;
5. logs dos três serviços;
6. Prompt 06 da fase 04;
7. arquitectura da fase actual.

Tarefas:
1. Inspeccionar healthchecks existentes:
   - Backend Core schema/docs/admin;
   - /api/v1/system/health/dependencies/;
   - IE /health;
   - CR /health.
2. Confirmar autenticação do health agregado.
3. Validar health agregado com user staff, se possível.
4. Confirmar que o health agregado cobre:
   - DB;
   - IE;
   - Content Renderer;
   - Report Renderer;
   - storage, se existir.
5. Identificar se existe readiness separado de liveness.
6. Propor ou implementar readiness mínimo, se claro e seguro.
7. Validar logs estruturados:
   - intelligence call;
   - job created;
   - job submitted;
   - callback received;
   - callback processed;
   - job failed;
   - campaign action created.
8. Confirmar sinais operacionais:
   - erro IE down;
   - erro Renderer down;
   - callback failed;
   - DB unavailable, se seguro simular;
   - storage unavailable, se provider existir.
9. Actualizar documentação operacional de health/logs.
10. Criar relatório.

Validações:
- HTTP health dos serviços.
- health agregado com JWT staff, se disponível.
- python manage.py check.
- testes relevantes.
- greps de logs por:
  - X-Internal-Token;
  - Authorization;
  - Bearer;
  - password;
  - private_key;
  - api_key.
- smoke de falha controlada, se seguro.

Critérios de aceitação:
- Health agregado reflecte dependências reais.
- Liveness/readiness estão claros.
- Logs permitem diagnóstico sem secrets.
- Runbook pode apontar para endpoints e sinais concretos.
- Falhas IE/CR são visíveis e seguras.

Critérios de rejeição:
- Health diz ok quando dependência crítica está indisponível.
- Logs expõem tokens.
- Endpoint administrativo fica aberto indevidamente.
- Readiness confundido com liveness.

Relatório:
O relatório deve incluir:
- estado da execução;
- endpoints validados;
- resultados por dependência;
- lacunas de observabilidade;
- ficheiros alterados;
- validações;
- riscos;
- próximo passo recomendado.
```

## Prompt 07 (sonnet) — Estados operacionais

```prompt
Iteração 7

Objectivo:
Alinhar estados de artefactos, jobs e CampaignActions para que falhas do renderer sejam visíveis e não pareçam sucesso ou espera infinita.

Backlog de referência:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\prompt_07_estados_operacionais_resultado.md

Contexto:
A fase 04 confirmou que falhas do renderer deixam alguns artefactos em estados como queued/draft enquanto o ExternalJobReference fica failed. Para staging pré-produção, essa diferença precisa de ser clara para utilizador e suporte.

Regras:
- Não alterar lifecycle de CampaignAction sem decisão explícita.
- Não esconder falhas de job.
- Não marcar artefacto como completed/generated sem output real.
- Não criar retry destrutivo.
- Não quebrar compatibilidade de estados existentes.
- Se MediaKit não tem estado failed próprio, documentar e propor ajuste seguro.

Fonte de verdade:
1. backlog indicado;
2. models de Report, MediaKit, ContentPackRequest, ContentOutput, ExternalJobReference e CampaignAction;
3. callbacks do Backend Core;
4. UI do CampaignActionsPanel e painéis proprietários;
5. resultados da fase 04 sobre renderer indisponível.

Tarefas:
1. Mapear estados actuais:
   - CampaignAction;
   - Report;
   - MediaKit;
   - ContentPackRequest;
   - ContentOutput;
   - ExternalJobReference.
2. Mapear transições por fluxo:
   - report_generation;
   - media_kit_generation;
   - content_generation;
   - callback success;
   - callback failed;
   - renderer unavailable;
   - retry.
3. Identificar divergências:
   - artefacto queued com job failed;
   - MediaKit draft com job failed;
   - CampaignAction pending com artefacto failed;
   - public_url ausente;
   - output parcial.
4. Decidir abordagem mínima:
   - documentar estados distintos;
   - expor job status na UI;
   - actualizar metadata;
   - actualizar estado do artefacto;
   - ou backlog técnico futuro.
5. Implementar ajuste pequeno e seguro se estiver claro:
   - mensagem UI;
   - helper de status;
   - exposição de job failure;
   - documentação de suporte.
6. Adicionar testes se houver alteração de código.
7. Criar relatório.

Validações:
- python manage.py check, se backend alterado.
- pnpm test/lint/build, se frontend alterado.
- testes específicos de callbacks, se alterados.
- smoke de renderer unavailable, se seguro.
- Verificar que não há falso sucesso.

Critérios de aceitação:
- Estados artefacto/job estão documentados.
- Falha de renderer é visível ou claramente diagnosticável.
- Utilizador/suporte não interpretam job failed como sucesso.
- Retry não destrutivo permanece.
- Testes passam se houve alteração.

Critérios de rejeição:
- Esconder job failed.
- Alterar estados sem migração/teste.
- Marcar success sem output real.
- Quebrar deduplicação/lifecycle de CampaignAction.

Relatório:
O relatório deve incluir:
- estado da execução;
- matriz de estados;
- divergências encontradas;
- decisão tomada;
- ficheiros alterados;
- validações;
- riscos;
- próximo passo recomendado.
```

## Prompt 08 (sonnet) — RBAC e UX

```prompt
Iteração 8

Objectivo:
Validar e melhorar o mínimo necessário de RBAC/UX para piloto pré-produção, evitando affordances enganosas e mensagens de erro inseguras.

Backlog de referência:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\prompt_08_rbac_ux_resultado.md

Contexto:
A fase 04 validou que o backend devolve 403 de forma segura. A dívida conhecida é que o frontend pode mostrar affordances de escrita a utilizadores sem permissão, se o perfil não trouxer capabilities suficientes.

Regras:
- Backend continua a ser a autoridade de permissão.
- Não inferir permissões de forma insegura no browser.
- Não esconder 403 como 404.
- 404 deve ser genérico e não revelar cross-workspace.
- Não adicionar sistema RBAC novo se não existir contrato.
- Fazer apenas melhorias mínimas e seguras.
- Não quebrar fluxos de utilizador autorizado.

Fonte de verdade:
1. backlog indicado;
2. auth/me ou perfil actual;
3. RBAC backend;
4. CampaignActionsPanel;
5. CreateAction dialog;
6. useRecommendationDecision;
7. error mapping frontend;
8. resultados de 400/401/403/404 da fase 04.

Tarefas:
1. Inspeccionar contrato actual do perfil do utilizador.
2. Confirmar se existem capabilities ou roles suficientes no frontend.
3. Mapear affordances de escrita:
   - create action;
   - mark reviewed;
   - dismiss;
   - complete;
   - cancel;
   - retry.
4. Confirmar tratamento de erros:
   - 400 field errors;
   - 401 session;
   - 403 access denied;
   - 404 generic not found;
   - 502/503 service unavailable.
5. Se houver capabilities reais:
   - ocultar/desactivar affordances sem permissão;
   - manter mensagem clara.
6. Se não houver capabilities reais:
   - não inferir;
   - documentar limitação;
   - garantir que 403 é apresentado de forma honesta;
   - evitar UX que prometa sucesso.
7. Melhorar mensagens de job failed/renderer unavailable se o Prompt 07 deixou contrato claro.
8. Testar viewer/editor se existirem dados ou fixtures simples.
9. Criar relatório.

Validações:
- pnpm test.
- pnpm lint.
- pnpm build.
- smoke UI, se alterado.
- API 403/404, se possível.
- grep para garantir que não há lógica insegura de permissões hardcoded.

Critérios de aceitação:
- UX de erro 403 é honesta.
- 404 não revela dados cross-workspace.
- Affordances respeitam capabilities se disponíveis.
- Se capabilities não existem, limitação está documentada e backend continua autoridade.
- Fluxos autorizados continuam a funcionar.
- Testes/lint/build passam.

Critérios de rejeição:
- Esconder 403 como sucesso.
- Inferir permissões por email, workspace name ou heurística frágil.
- Criar permissões só no frontend.
- Quebrar utilizador autorizado.
- Expor detalhes cross-workspace.

Relatório:
O relatório deve incluir:
- estado da execução;
- contrato RBAC encontrado;
- alterações UX;
- testes;
- limitações;
- riscos;
- próximo passo recomendado.
```

## Prompt 09 (sonnet) — E2E automatizado

```prompt
Iteração 9

Objectivo:
Criar ou preparar um E2E automatizado repetível para o fluxo principal: login, War Room com intelligence real/controlada, CampaignActions, Renderer e persistência.

Backlog de referência:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\

Relatório a criar:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\prompt_09_e2e_automatizado_resultado.md

Contexto:
A fase 04 teve smoke visual manual com sucesso. Para pré-produção, é necessário tornar o fluxo repetível em teste automatizado, sem depender de dados manuais frágeis nem expor secrets.

Regras:
- Não usar mocks runtime para declarar E2E real.
- Não expor credenciais no repositório.
- Não commitar passwords.
- Não depender de dados partilhados sem namespace por execução.
- Não chamar IE/Renderer directamente a partir do frontend.
- Não tornar o teste instável por sleeps arbitrários longos.
- Se a stack real não puder correr automaticamente, criar harness parcial e documentar bloqueio.

Fonte de verdade:
1. backlog indicado;
2. smoke visual da fase 04;
3. scripts de arranque existentes;
4. package.json frontend;
5. ferramentas de teste existentes;
6. API de seed ou comandos Django;
7. documentação de portas.

Tarefas:
1. Verificar se Playwright, Cypress ou outra ferramenta já existe.
2. Se não existir, avaliar introdução mínima e segura, preferindo Playwright se compatível com o stack.
3. Definir cenário E2E:
   - preparar dados;
   - login;
   - abrir workspace/campaign;
   - abrir War Room;
   - executar intelligence;
   - criar manual task;
   - criar report action;
   - criar media kit action;
   - criar content pack action;
   - mark reviewed;
   - dismiss;
   - validar CampaignActionsPanel;
   - validar reload;
   - validar Network apenas Backend Core.
4. Definir estratégia de dados:
   - seed via Django command;
   - fixture namespace por execução;
   - cleanup;
   - ou dados staging estáveis documentados.
5. Definir configuração de secrets:
   - credenciais via env;
   - nunca no código.
6. Implementar teste se a ferramenta e ambiente permitirem.
7. Se não for seguro implementar tudo:
   - criar scaffolding;
   - documentar passos faltantes;
   - não declarar E2E automatizado completo.
8. Criar scripts package.json se apropriado.
9. Criar relatório.

Validações:
- pnpm test.
- pnpm lint.
- pnpm build.
- comando E2E criado, se possível.
- execução E2E, se ambiente permitir.
- grep por secrets.
- confirmar que o teste falha de forma útil se IE/CR indisponíveis.

Critérios de aceitação:
- Existe caminho E2E automatizável documentado.
- Teste real executa ou bloqueio está documentado.
- Dados são controlados ou namespaced.
- Secrets vêm de env.
- Network valida apenas Backend Core.
- Reload/persistência validada.
- E2E não depende de manual smoke para fechar staging formal.

Critérios de rejeição:
- Password hardcoded.
- Mocks declarados como E2E real.
- Teste depende de estado manual não documentado.
- Frontend chama IE/Renderer.
- Script instável ou sem diagnóstico.

Relatório:
O relatório deve incluir:
- estado da execução;
- ferramenta escolhida;
- ficheiros criados/alterados;
- cenário coberto;
- comandos;
- resultado da execução;
- limitações;
- riscos;
- próximo passo recomendado.
```

## Prompt 10 (sonnet) — Runbook staging

```prompt
Iteração 10

Objectivo:
Criar um runbook operacional para arrancar, validar, diagnosticar e parar staging pré-produção.

Backlog de referência:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\

Documentos a criar ou actualizar:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\runbook_staging_pre_producao.md
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\prompt_10_runbook_staging_resultado.md

Contexto:
A fase 04 comprovou o fluxo técnico. A fase actual precisa de tornar a operação repetível por qualquer técnico, com comandos, healthchecks, troubleshooting e limpeza.

Regras:
- Não incluir secrets reais.
- Não incluir passwords.
- Não assumir ambiente local como produção.
- Não esconder limitações.
- Não usar portas antigas.
- Não instruir a desactivar segurança interna em staging.
- O runbook deve ser prático e directo.

Fonte de verdade:
1. backlog indicado;
2. documentos dos Prompts 01 a 09;
3. docs de portas;
4. scripts existentes;
5. env examples;
6. runbooks anteriores.

Tarefas:
1. Criar runbook_staging_pre_producao.md.
2. Incluir secções:
   - pré-requisitos;
   - variáveis obrigatórias;
   - secrets obrigatórios sem valores;
   - ordem de arranque;
   - comandos por componente;
   - healthchecks;
   - smoke API;
   - smoke browser;
   - E2E automatizado, se existir;
   - troubleshooting DB;
   - troubleshooting IE;
   - troubleshooting Renderer;
   - troubleshooting callbacks;
   - troubleshooting storage;
   - troubleshooting auth/RBAC;
   - limpeza de dados dev/staging;
   - paragem segura;
   - critérios de pronto/não pronto.
3. Incluir comandos usando placeholders:
   - BACKEND_CORE_PORT;
   - VITE_DEV_PORT;
   - INTELLIGENCE_ENGINE_PORT;
   - PORT;
   - DATABASE_URL;
   - INTERNAL_API_TOKEN;
   - STORAGE_*.
4. Incluir checklist de validação rápida.
5. Incluir matriz de sintomas:
   - IE down;
   - renderer down;
   - callback 403;
   - job failed;
   - asset sem public_url;
   - 403 no frontend;
   - CORS;
   - DB migration.
6. Verificar que o runbook não contém secrets.
7. Criar relatório.

Validações:
- Revisão documental.
- Grep por padrões sensíveis no runbook.
- Confirmar que portas canónicas estão correctas.
- Confirmar que comandos não contradizem scripts reais.
- Executar comandos apenas se seguro e necessário.

Critérios de aceitação:
- Runbook criado.
- Técnico consegue arrancar e validar staging seguindo o documento.
- Troubleshooting cobre falhas comuns.
- Sem secrets.
- Sem portas antigas.
- Segurança interna permanece activa.

Critérios de rejeição:
- Runbook com tokens reais.
- Comandos que usam portas antigas.
- Instrução de usar ALLOW_INSECURE_EMPTY_TOKEN em staging.
- Falta de healthchecks.
- Falta de paragem segura.

Relatório:
O relatório deve incluir:
- estado da execução;
- ficheiros criados/alterados;
- secções do runbook;
- validações;
- riscos;
- próximo passo recomendado.
```

## Prompt 11 (sonnet) — Fecho pré-produção

```prompt
Iteração 11

Objectivo:
Consolidar a fase 05, actualizar o estado de staging pré-produção e decidir honestamente se o ambiente está pronto para piloto pré-produção, staging formal ou se continua parcialmente executado.

Backlog de referência:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\01_backlog.md

Pasta de resultados:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\

Documentos a criar ou actualizar:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\estado_staging_pre_producao.md
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\prompt_11_fecho_pre_producao_resultado.md

Contexto:
Esta é a iteração de fecho. Deve consolidar os Prompts 01 a 10, sem mascarar pendências. Produção não deve ser declarada pronta sem DB alvo, object storage, secrets, observabilidade, RBAC/UX e E2E automatizado validados.

Regras:
- Não declarar produção-ready.
- Não declarar staging formal se continuar dependente de SQLite/storage local.
- Não declarar E2E automatizado se apenas smoke manual existe.
- Não declarar object storage se só storage local foi usado.
- Não declarar secrets formalizados se dependem de .env manual local.
- Separar claramente:
  - implementado;
  - validado;
  - bloqueado;
  - pendente;
  - fora de escopo.
- Não expor secrets.
- Não alterar código funcional neste prompt.

Fonte de verdade:
1. backlog indicado;
2. relatórios dos Prompts 01 a 10;
3. arquitectura e runbook criados;
4. validações executadas;
5. código actual;
6. documentação da fase 04.

Tarefas:
1. Ler backlog da fase.
2. Ler todos os relatórios em:
   frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\
3. Ler documentos criados:
   - arquitectura_staging_pre_producao.md;
   - runbook_staging_pre_producao.md;
   - outros documentos da fase.
4. Criar ou actualizar estado_staging_pre_producao.md com:
   - resumo executivo;
   - estado final;
   - escopo executado;
   - escopo bloqueado;
   - validações concluídas;
   - validações pendentes;
   - riscos;
   - limitações;
   - decisão de prontidão.
5. Classificar o estado final usando uma opção honesta:
   - pronto_para_piloto_pre_producao;
   - pronto_parcialmente_com_pendencias;
   - executado_parcialmente;
   - bloqueado;
   - nao_pronto.
6. Consolidar critérios do backlog:
   - DB staging;
   - object storage;
   - Asset.public_url;
   - secrets;
   - correlation-id;
   - health/logs;
   - estados artefacto/job;
   - RBAC/UX;
   - E2E automatizado;
   - runbook.
7. Executar validações finais, se viável:
   - pnpm test;
   - pnpm lint;
   - pnpm build;
   - python manage.py check;
   - npm test Content Renderer;
   - pytest Intelligence Engine;
   - check-forbidden-ports;
   - greps de segurança.
8. Verificar documentos sem secrets.
9. Criar relatório final.

Critérios de aceitação:
- Estado final documentado.
- Decisão de prontidão honesta.
- Pendências não mascaradas.
- Produção não declarada indevidamente.
- Evidência consolidada.
- Documentos sem secrets.
- Próximos passos claros.

Critérios de rejeição:
- Declarar produção-ready.
- Declarar staging formal sem DB/storage/secrets/E2E adequados.
- Omitir bloqueios relevantes.
- Ignorar falhas de validação.
- Incluir tokens/passwords nos documentos.

Relatório:
Criar:
frontend\docs\01_fundamentos\05_staging_operacionalizacao_pre_producao\resultados_execucao\prompt_11_fecho_pre_producao_resultado.md

O relatório deve incluir:
- estado final;
- evidência consolidada;
- ficheiros criados/alterados;
- validações executadas;
- critérios aceites/rejeitados;
- limitações;
- riscos;
- decisão de prontidão;
- próximos passos recomendados.
```
