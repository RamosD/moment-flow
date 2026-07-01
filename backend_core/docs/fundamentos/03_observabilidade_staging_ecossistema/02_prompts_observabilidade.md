# Pipeline: Observabilidade e Staging do Ecossistema

## Prompt 01 (opus) — Analisar estado operacional actual

```prompt
Objectivo:
Inspeccionar o estado operacional actual dos três serviços principais do ecossistema MomentFlow/ChartRex — backend_core, intelligence_engine e content_renderer — para preparar uma execução segura da fase de observabilidade e staging técnico.

Contexto obrigatório:
- Componente alvo principal: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados
- Componentes relacionados:
  - backend_core
  - intelligence_engine
  - content_renderer
- Estado anterior relevante:
  - Backend Core ↔ Intelligence Engine já foi integrado e validado com loop real.
  - Content Renderer já teve MVP e hardening pós-MVP concluídos.
  - Esta fase não deve transformar o projecto numa stack completa de observabilidade.
  - Esta fase deve focar healthchecks, smoke tests, runbook, troubleshooting, logs mínimos e prontidão operacional.

Instruções:
- Lê o backlog completo antes de alterar qualquer ficheiro.
- Lê a documentação final da integração Backend Core ↔ Intelligence Engine, se existir no repositório.
- Lê a documentação final do Intelligence Engine, se estiver disponível.
- Lê a documentação final do Content Renderer, se estiver disponível.
- Inspecciona os healthchecks existentes nos três serviços.
- Inspecciona settings/envs relevantes no Backend Core.
- Inspecciona scripts de arranque existentes.
- Inspecciona testes E2E, smoke tests, testes opt-in ou validações reais existentes.
- Inspecciona padrões de logging existentes no Backend Core, especialmente:
  - request_id;
  - workspace_id;
  - campaign_id;
  - job_id;
  - provider;
  - duration_ms;
  - status;
  - error_type.
- Identifica portas default dos serviços.
- Identifica tokens internos necessários.
- Identifica gaps de diagnóstico.
- Identifica riscos relacionados com exposição de secrets, healthchecks detalhados, smoke tests frágeis e logs insuficientes.
- Não alteres código de runtime neste prompt.
- Podes criar apenas o relatório de análise.
- Cria o relatório em:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados\prompt_01_analise_estado_operacional.md

Critérios de aceitação:
- Existe relatório de análise.
- Healthchecks existentes foram identificados.
- Variáveis de ambiente críticas foram identificadas.
- Scripts/comandos existentes foram identificados.
- Lacunas operacionais foram listadas.
- Riscos foram registados.
- Existe plano técnico curto e executável para os próximos prompts.
- Nenhum runtime foi alterado sem necessidade.
```

## Prompt 02 (opus) — Criar matriz operacional dos serviços

```prompt
Objectivo:
Criar a matriz operacional central dos serviços do ecossistema, documentando portas, comandos, healthchecks, variáveis de ambiente, dependências, secrets e modos de arranque local/staging.

Contexto obrigatório:
- Componente alvo principal: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados
- Relatório anterior esperado:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados\prompt_01_analise_estado_operacional.md
- Documento a criar:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\matriz_operacional_servicos.md

Instruções:
- Lê o backlog e o relatório do Prompt 01.
- Não alteres runtime neste prompt, salvo se encontrares documentação existente que deva ser apenas referenciada.
- Cria o documento matriz_operacional_servicos.md.
- A matriz deve cobrir:
  - backend_core;
  - intelligence_engine;
  - content_renderer;
  - base de dados, se aplicável;
  - dependências internas;
  - dependências externas relevantes.
- Para cada serviço, documenta:
  - descrição;
  - directório;
  - porta default;
  - comando de instalação/preparação, se conhecido;
  - comando de arranque;
  - healthcheck;
  - variáveis obrigatórias;
  - variáveis opcionais;
  - variáveis sensíveis/secrets;
  - logs relevantes;
  - dependências de outros serviços;
  - modo local;
  - modo staging técnico.
- Usa placeholders para tokens e secrets.
- Nunca incluas valores reais de tokens.
- Se uma porta, comando ou variável não estiver confirmada, marca como "por confirmar" e indica como validar.
- Cria relatório de execução em:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados\prompt_02_matriz_operacional_servicos.md

Critérios de aceitação:
- matriz_operacional_servicos.md existe.
- Cada serviço principal tem porta, comando de arranque e healthcheck documentados ou marcados como por confirmar.
- Secrets estão claramente identificados como não versionáveis.
- Dependências entre serviços estão claras.
- O relatório lista ficheiros criados/alterados, decisões, lacunas e próximo passo recomendado.
```

## Prompt 03 (opus) — Implementar healthcheck agregado no Backend Core

```prompt
Objectivo:
Implementar no Backend Core um healthcheck agregado para consultar o estado operacional das dependências técnicas principais: Intelligence Engine, Content Renderer e, se fizer sentido no padrão do projecto, base de dados do Backend Core.

Contexto obrigatório:
- Componente alvo principal: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados
- Documento operacional esperado:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\matriz_operacional_servicos.md

Instruções:
- Lê o backlog e a matriz operacional.
- Identifica se já existe padrão de healthcheck no Backend Core.
- Escolhe a localização mais coerente para o endpoint.
- Sugestões de rota, adaptar ao padrão real:
  - GET /api/v1/system/health/external-services/
  - GET /api/v1/health/dependencies/
- Se o healthcheck expuser detalhes internos, protege o endpoint com autenticação/permissão adequada.
- Cria serviço interno para consultar dependências.
- Consulta GET /health do Intelligence Engine.
- Consulta GET /health do Content Renderer.
- Usa timeout curto e configurável, ou reutiliza timeouts existentes.
- Não envies tokens se os endpoints /health forem públicos.
- Se algum healthcheck exigir token, envia header interno sem logar token.
- Normaliza resposta com status geral:
  - ok;
  - degraded;
  - unavailable.
- Normaliza estado por dependência:
  - ok;
  - degraded;
  - unavailable;
  - misconfigured;
  - unknown.
- Inclui duration_ms por serviço.
- Não exponhas tokens.
- Evita expor URL completa se isso for sensível; podes indicar "configured" ou "not_configured".
- Garante que falha de uma dependência não gera 500 inesperado no healthcheck agregado.
- Cria testes com mocks para:
  - todos ok;
  - Intelligence Engine indisponível;
  - Content Renderer indisponível;
  - timeout;
  - base_url ausente/misconfigured;
  - resposta inválida.
- Actualiza documentação relevante.
- Cria relatório em:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados\prompt_03_healthcheck_agregado.md

Critérios de aceitação:
- Endpoint agregado existe.
- Falha de dependência gera degraded/unavailable e não 500 inesperado.
- Timeout é curto e configurável ou justificado.
- Resposta não expõe tokens nem dados sensíveis.
- Testes cobrem ok, degraded, timeout e misconfigured.
- Documentação foi actualizada.
- O relatório lista ficheiros alterados, rota criada, testes executados, resultados e próximo passo recomendado.
```

## Prompt 04 (opus) — Criar smoke test operacional do Intelligence Engine

```prompt
Objectivo:
Criar ou consolidar um smoke test operacional opt-in para validar rapidamente o loop real Backend Core → Intelligence Engine → Backend Core.

Contexto obrigatório:
- Componente alvo principal: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados
- A integração Backend Core ↔ Intelligence Engine já existe e já teve validação real anterior.
- Esta tarefa deve reutilizar o que já existe sempre que possível.

Instruções:
- Lê o backlog.
- Identifica testes opt-in existentes do loop real Backend Core ↔ Intelligence Engine.
- Reutiliza o teste opt-in existente se ele já cumprir o objectivo.
- Se faltar cobertura ou documentação, complementa sem duplicar.
- Garante que o smoke test só corre quando explicitamente activado, por exemplo com variável do tipo:
  - RUN_REAL_IE=1
  - ou padrão equivalente já existente.
- Valida configuração necessária:
  - INTELLIGENCE_ENGINE_BASE_URL;
  - INTELLIGENCE_ENGINE_INTERNAL_TOKEN ou token equivalente;
  - INTELLIGENCE_ENGINE_ENABLED;
  - INTELLIGENCE_ENGINE_DRY_RUN=false.
- Usa campanha de teste por fixture/factory ou documenta pré-condição.
- O smoke deve confirmar resposta com:
  - analysis;
  - scores;
  - grade;
  - moments;
  - recommendations;
  - summary.
- Deve confirmar que falha com IE indisponível é controlada.
- Deve confirmar que token não aparece nos logs.
- Actualiza ou cria documentação curta de como executar o smoke test.
- Não alteres intelligence_engine.
- Não alteres content_renderer.
- Cria relatório em:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados\prompt_04_smoke_intelligence_engine.md

Critérios de aceitação:
- Existe smoke test IE documentado.
- O smoke test corre apenas de forma explícita.
- Sucesso real é verificável quando o IE está activo.
- Falha com IE desligado está coberta ou documentada.
- Token não aparece nos logs.
- Testes relevantes passam ou limitações são documentadas.
- O relatório lista o que foi reutilizado, o que foi criado/alterado, comandos, resultados e próximo passo recomendado.
```

## Prompt 05 (opus) — Criar smoke test operacional do Content Renderer

```prompt
Objectivo:
Criar ou consolidar uma validação operacional rápida do loop Backend Core → Content Renderer → callback Backend Core, usando teste opt-in, script ou checklist executável conforme o estado real do projecto.

Contexto obrigatório:
- Componente alvo principal: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados
- Content Renderer já teve MVP e hardening pós-MVP concluídos.
- Backend Core já possui integração com serviços externos e ExternalJobReference.
- Esta fase não deve alterar o renderer salvo necessidade mínima e justificada.

Instruções:
- Lê o backlog.
- Identifica testes E2E existentes do renderer.
- Identifica como o Backend Core cria jobs para o renderer.
- Identifica como callbacks do renderer são recebidos e processados no Backend Core.
- Identifica payload mínimo para content_generation, report_generation ou outro job adequado.
- Reutiliza teste E2E/smoke existente se já houver.
- Se não houver teste real executável com o ambiente actual, cria checklist operacional clara e, se viável, teste opt-in.
- O smoke/checklist deve validar:
  - renderer GET /health;
  - token interno alinhado;
  - criação/submissão de job;
  - resposta 202, se aplicável;
  - callback para Backend Core;
  - ExternalJobReference actualizado;
  - estado final do job;
  - ficheiros/outputs esperados, se aplicável;
  - erro controlado quando renderer está indisponível.
- Garante que tokens não aparecem em logs.
- Não dupliques testes já existentes sem necessidade.
- Não alteres intelligence_engine.
- Não alteres content_renderer, salvo documentação mínima ou correcção claramente necessária.
- Actualiza documentação operacional.
- Cria relatório em:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados\prompt_05_smoke_content_renderer.md

Critérios de aceitação:
- Existe smoke test Renderer documentado ou checklist executável realista.
- O fluxo Backend Core → Renderer → callback está coberto por teste, smoke opt-in ou checklist operacional.
- Falha com renderer desligado é tratada ou documentada.
- Logs não expõem token.
- Validações relevantes foram executadas ou limitações documentadas.
- O relatório lista ficheiros alterados, evidência, limitações, comandos e próximo passo recomendado.
```

## Prompt 06 (opus) — Normalizar correlação por request_id e job_id

```prompt
Objectivo:
Garantir que os logs mínimos dos fluxos entre serviços são correlacionáveis por request_id, job_id, external_job_id, workspace_id e outros identificadores úteis, sem expor tokens ou payloads sensíveis.

Contexto obrigatório:
- Componente alvo principal: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados
- Fluxos a cobrir:
  - Backend Core → Intelligence Engine;
  - Backend Core → Content Renderer;
  - callbacks do Renderer → Backend Core.

Instruções:
- Lê o backlog.
- Inspecciona logs existentes do fluxo Backend Core → Intelligence Engine.
- Inspecciona logs existentes do fluxo Backend Core → Content Renderer.
- Inspecciona logs dos callbacks do Renderer para o Backend Core.
- Confirma se request_id já está presente no fluxo Intelligence.
- Confirma se job_id ou external_job_id já está presente no fluxo Renderer.
- Adiciona logs mínimos apenas onde existirem lacunas relevantes.
- Não logues payload completo.
- Não logues headers sensíveis.
- Não logues tokens.
- Campos recomendados quando aplicável:
  - request_id;
  - workspace_id;
  - campaign_id;
  - job_id;
  - external_job_id;
  - provider;
  - duration_ms;
  - status;
  - error_type.
- Mantém formato de logging consistente com o projecto.
- Ajusta ou cria testes para garantir:
  - presença de identificadores;
  - ausência de token nos logs;
  - logs úteis em sucesso e falha.
- Evita alterar demasiados módulos sem necessidade.
- Actualiza documentação ou troubleshooting se fizer sentido.
- Cria relatório em:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados\prompt_06_correlacao_logs.md

Critérios de aceitação:
- Fluxo IE é rastreável por request_id.
- Fluxo Renderer é rastreável por job_id/request_id quando aplicável.
- Callbacks são rastreáveis por job_id/external_job_id quando aplicável.
- Tokens não aparecem em logs.
- Testes de logging passam ou lacunas ficam documentadas.
- Validações relevantes foram executadas.
- O relatório lista ficheiros alterados, campos de log, testes, limitações e próximo passo recomendado.
```

## Prompt 07 (sonnet) — Criar runbook de arranque local e staging

```prompt
Objectivo:
Criar um runbook prático para arrancar e validar o ecossistema local/staging com backend_core, intelligence_engine e content_renderer.

Contexto obrigatório:
- Componente alvo principal: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados
- Documento a criar:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\runbook_arranque_staging.md
- Documentos já esperados:
  - matriz_operacional_servicos.md;
  - relatórios dos prompts anteriores.

Instruções:
- Lê o backlog.
- Lê a matriz operacional.
- Lê os relatórios dos prompts anteriores desta fase.
- Cria runbook_arranque_staging.md.
- O runbook deve ser prático, directo e executável.
- Inclui:
  - pré-requisitos;
  - directórios dos serviços;
  - portas;
  - variáveis de ambiente;
  - ordem recomendada de arranque;
  - como arrancar backend_core;
  - como arrancar intelligence_engine;
  - como arrancar content_renderer;
  - como validar GET /health de cada serviço;
  - como executar healthcheck agregado;
  - como executar smoke test IE;
  - como executar smoke test Renderer;
  - como parar serviços;
  - como limpar artefactos locais, se aplicável;
  - problemas comuns.
- Usa placeholders para tokens.
- Nunca incluas valores reais de secrets.
- Se algum comando não estiver confirmado, marca como "confirmar no ambiente" e explica como validar.
- Cria relatório em:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados\prompt_07_runbook_arranque_staging.md

Critérios de aceitação:
- runbook_arranque_staging.md existe.
- Comandos estão claros.
- Ordem de arranque está clara.
- Healthchecks e smoke tests estão incluídos.
- Não há secrets reais no documento.
- O relatório lista ficheiros criados/alterados, decisões, limitações e próximo passo recomendado.
```

## Prompt 08 (sonnet) — Criar checklist de troubleshooting

```prompt
Objectivo:
Criar uma checklist prática de troubleshooting para diagnosticar falhas comuns no ecossistema backend_core, intelligence_engine e content_renderer.

Contexto obrigatório:
- Componente alvo principal: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados
- Documento a criar:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\checklist_troubleshooting.md

Instruções:
- Lê o backlog.
- Lê a matriz operacional, o runbook e os relatórios anteriores desta fase.
- Cria checklist_troubleshooting.md.
- A checklist deve ser prática, accionável e utilizável por alguém que não implementou o código.
- Para cada caso, incluir:
  - sintoma;
  - causa provável;
  - como confirmar;
  - acção recomendada;
  - logs/campos úteis;
  - quando escalar.
- Cobrir pelo menos:
  - Intelligence Engine indisponível;
  - Intelligence Engine devolve 403;
  - Intelligence Engine devolve 422;
  - Intelligence Engine devolve 500;
  - Content Renderer indisponível;
  - Content Renderer não faz callback;
  - callback chega mas job não actualiza;
  - token interno desalinhado;
  - URL configurada errada;
  - timeout;
  - payload inválido;
  - erro de workspace/RBAC;
  - porta ocupada;
  - base de dados indisponível;
  - healthcheck agregado degraded;
  - logs sem request_id/job_id.
- Não incluir secrets reais.
- Não sugerir expor tokens nos logs.
- Incluir comandos de verificação apenas com placeholders.
- Cria relatório em:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados\prompt_08_checklist_troubleshooting.md

Critérios de aceitação:
- checklist_troubleshooting.md existe.
- Cada caso tem sintoma, causa provável, confirmação e acção recomendada.
- Inclui comandos úteis.
- Não expõe secrets.
- É utilizável por alguém fora da implementação.
- O relatório lista ficheiros criados/alterados, cobertura, limitações e próximo passo recomendado.
```

## Prompt 09 (sonnet) — Criar painel textual de prontidão operacional

```prompt
Objectivo:
Criar um painel textual de prontidão operacional para avaliar se o ecossistema está pronto para piloto técnico controlado e explicitar por que ainda não está pronto para produção.

Contexto obrigatório:
- Componente alvo principal: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados
- Documento a criar:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\painel_prontidao_operacional.md

Instruções:
- Lê o backlog.
- Lê os relatórios anteriores desta fase.
- Lê a matriz operacional, runbook e checklist de troubleshooting.
- Cria painel_prontidao_operacional.md.
- O painel deve ter uma visão objectiva do estado operacional.
- Incluir:
  - estado dos serviços;
  - estado dos healthchecks;
  - estado dos smoke tests;
  - estado dos logs/correlação;
  - estado da segurança de secrets;
  - estado da documentação operacional;
  - blockers de produção;
  - riscos em aberto;
  - decisão de prontidão para piloto;
  - decisão de prontidão para produção.
- Usar estados claros:
  - ok;
  - parcial;
  - pendente;
  - bloqueado;
  - não aplicável.
- Separar claramente:
  - pronto para piloto técnico controlado;
  - não pronto para produção.
- Não inventar validações. Se alguma validação não foi executada, marcar como "não executada" ou "pendente".
- Não incluir secrets reais.
- Cria relatório em:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados\prompt_09_painel_prontidao_operacional.md

Critérios de aceitação:
- painel_prontidao_operacional.md existe.
- Critérios de piloto estão claros.
- Critérios de produção estão claros.
- Estado é honesto e baseado nas evidências disponíveis.
- Validações não executadas não são apresentadas como concluídas.
- O relatório lista ficheiros criados/alterados, decisões, pendências e próximo passo recomendado.
```

## Prompt 10 (sonnet) — Validar fase e criar estado final

```prompt
Objectivo:
Fechar a fase Observabilidade e Staging Técnico do Ecossistema com validações finais, documentação de estado e relatório honesto.

Contexto obrigatório:
- Componente alvo principal: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados
- Documento de estado a criar:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\estado_observabilidade_staging_ecossistema.md
- Relatório final a criar:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados\prompt_10_estado_final_observabilidade_staging.md

Instruções:
- Lê o backlog.
- Lê todos os relatórios desta fase.
- Lê a matriz operacional, runbook, checklist de troubleshooting e painel de prontidão.
- Revê todos os ficheiros alterados nesta fase.
- Executa validações relevantes disponíveis, por exemplo:
  - pytest;
  - manage.py check;
  - ruff ou lint equivalente;
  - schema/OpenAPI se afectado;
  - healthcheck agregado, se implementado;
  - smoke test IE, se ambiente permitir;
  - smoke test Renderer, se ambiente permitir.
- Não inventes resultados.
- Se algum serviço não estiver disponível para validação real, documenta a limitação.
- Corrige apenas falhas directamente relacionadas com esta fase.
- Não faças refactors fora do escopo.
- Confirma ausência de secrets reais em:
  - docs desta fase;
  - relatórios;
  - .env.example, se alterado;
  - logs de exemplo;
  - testes adicionados.
- Cria estado_observabilidade_staging_ecossistema.md com:
  - resumo executivo;
  - escopo entregue;
  - healthchecks;
  - smoke tests;
  - logs/correlação;
  - documentação criada;
  - validações executadas;
  - limitações;
  - riscos em aberto;
  - decisão de prontidão para piloto;
  - decisão de prontidão para produção;
  - próximos passos recomendados.
- Cria relatório final em:
  backend_core\docs\backend_core\fundamentos\03_observabilidade_staging_ecossistema\resultados\prompt_10_estado_final_observabilidade_staging.md

Critérios de aceitação:
- Validações relevantes foram executadas ou limitações documentadas.
- Documento de estado final existe.
- Relatório final existe.
- Não há secrets reais em documentação/logs de exemplo.
- Estado final é honesto.
- Prontidão para piloto está explicitamente indicada.
- Prontidão para produção está explicitamente indicada.
- Próximo passo recomendado está claro.
```
