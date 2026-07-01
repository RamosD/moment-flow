# Pipeline: Integrar Backend Core com Intelligence Engine

## Prompt 01 (opus) — Analisar contrato e plano de integração

```prompt
Objectivo:
Inspeccionar o Backend Core, o backlog e o contrato do Intelligence Engine para preparar uma implementação segura, incremental e alinhada com a arquitectura do projecto.

Contexto obrigatório:
- Repositório/componente alvo: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados
- Intelligence Engine já implementado e validado noutro componente.
- Content Renderer já implementado noutro componente.
- Tese arquitectural:
  - Django governa o produto.
  - Renderer gera activos.
  - FastAPI Intelligence calcula, recomenda e detecta oportunidades.
  - Frontend orquestra a experiência do utilizador.

Instruções:
- Lê o backlog completo antes de alterar ficheiros.
- Localiza e lê o contrato Backend Core ↔ Intelligence Engine, se estiver disponível no repositório ou referenciado no backlog.
- Inspecciona as apps relevantes do Backend Core:
  - campaigns;
  - catalogue;
  - links;
  - content;
  - reports;
  - integrations_bridge;
  - workspaces;
  - users/autenticação/permissões;
  - configuração/settings;
  - routers/views/viewsets/API;
  - serializers;
  - testes existentes.
- Inspecciona padrões existentes de integração interna:
  - InternalServiceClient ou equivalente;
  - settings de serviços externos;
  - timeouts;
  - dry-run;
  - retry;
  - tratamento de erros;
  - logs;
  - OpenAPI/schema;
  - testes com mocks HTTP.
- Confirma se já existem settings como:
  - INTELLIGENCE_ENGINE_BASE_URL;
  - INTELLIGENCE_ENGINE_TIMEOUT_SECONDS;
  - INTELLIGENCE_ENGINE_INTERNAL_TOKEN;
  - INTELLIGENCE_ENGINE_ENABLED;
  - INTELLIGENCE_ENGINE_DRY_RUN.
- Confirma a decisão técnica recomendada no MVP:
  - chamada síncrona interna para POST /intelligence/campaign;
  - não usar ExternalJobReference nesta fase;
  - não implementar callbacks;
  - não persistir snapshots, salvo se o backlog ou o código já indicar decisão contrária.
- Não alteres código neste prompt, salvo se for necessário criar apenas o relatório de análise.
- Identifica os ficheiros prováveis a alterar.
- Identifica riscos, decisões pendentes, dependências e lacunas.
- Define uma sequência de implementação objectiva para os próximos prompts.
- Cria o relatório em:
  backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados\prompt_01_analise_plano_integracao.md

Critérios de aceitação:
- Existe um plano técnico claro e executável.
- Foram identificados os ficheiros/módulos prováveis a alterar.
- Foi confirmada a decisão síncrona para o MVP ou registada a divergência encontrada.
- Foram identificados riscos de RBAC, workspace, payload, timeout, logging e testes.
- Nenhum ficheiro de runtime foi alterado sem necessidade.
- O relatório lista contexto consultado, decisões, riscos, plano, pendências e próximo passo recomendado.
```

## Prompt 02 (opus) — Configurar settings do Intelligence Engine

```prompt
Objectivo:
Adicionar ou consolidar no Backend Core as configurações necessárias para chamar o FastAPI Intelligence Engine de forma segura e controlada.

Contexto obrigatório:
- Repositório/componente alvo: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados
- Resultado esperado: o Backend Core deve conseguir configurar URL, token, timeout, enabled/dry-run para o Intelligence Engine.

Instruções:
- Parte do plano criado no Prompt 01.
- Inspecciona a configuração actual do Backend Core.
- Reutiliza padrões existentes para settings/env sempre que possível.
- Adiciona ou consolida as variáveis:
  - INTELLIGENCE_ENGINE_BASE_URL;
  - INTELLIGENCE_ENGINE_TIMEOUT_SECONDS;
  - INTELLIGENCE_ENGINE_INTERNAL_TOKEN;
  - INTELLIGENCE_ENGINE_ENABLED;
  - INTELLIGENCE_ENGINE_DRY_RUN.
- Se já existirem variáveis equivalentes, evita duplicação e documenta a decisão.
- Define defaults seguros para desenvolvimento.
- Garante que produção não aceita configuração insegura quando o Intelligence Engine estiver enabled e o token estiver vazio.
- Garante que .env.example ou documentação equivalente usa placeholders seguros e não contém secrets reais.
- Actualiza testes de configuração se existirem.
- Cria novos testes de configuração se o projecto tiver padrão para isso.
- Não implementes ainda o client HTTP nem o payload builder.
- Não alteres intelligence_engine nem content_renderer.
- Cria o relatório em:
  backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados\prompt_02_settings_intelligence_engine.md

Critérios de aceitação:
- Settings do Intelligence Engine existem ou foram consolidados.
- URL, timeout, token, enabled e dry-run são configuráveis por ambiente.
- Produção não permite token vazio quando isso for inseguro.
- .env.example ou documentação equivalente não contém secrets reais.
- Testes/config checks relevantes passam ou a limitação fica documentada.
- O relatório lista ficheiros alterados, decisões, validações executadas, pendências e próximo passo recomendado.
```

## Prompt 03 (opus) — Criar client síncrono do Intelligence Engine

```prompt
Objectivo:
Implementar ou adaptar um client interno no Backend Core para chamar de forma síncrona o endpoint POST /intelligence/campaign do FastAPI Intelligence Engine.

Contexto obrigatório:
- Repositório/componente alvo: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados
- Endpoint alvo no Intelligence Engine:
  - POST /intelligence/campaign
- Modelo MVP:
  - síncrono;
  - sem ExternalJobReference;
  - sem callbacks;
  - sem persistência obrigatória.

Instruções:
- Reutiliza InternalServiceClient existente se for adequado.
- Se o padrão existente não for adequado para chamadas síncronas nomeadas, cria um IntelligenceEngineClient pequeno e alinhado com o estilo do projecto.
- O client deve enviar:
  - X-Internal-Token;
  - X-Workspace-ID;
  - X-Request-ID.
- Usa INTELLIGENCE_ENGINE_BASE_URL.
- Usa INTELLIGENCE_ENGINE_TIMEOUT_SECONDS.
- Usa INTELLIGENCE_ENGINE_INTERNAL_TOKEN.
- Respeita INTELLIGENCE_ENGINE_ENABLED e INTELLIGENCE_ENGINE_DRY_RUN, se fizer sentido nesta camada ou se o padrão do projecto centralizar isso no service.
- Implementa método explícito para chamar POST /intelligence/campaign.
- Trata respostas:
  - 200 completed;
  - 400/422 invalid_payload;
  - 403 unauthorized_internal_request;
  - 5xx;
  - timeout;
  - serviço indisponível;
  - JSON inválido;
  - resposta com status inesperado.
- Cria erros internos tipados ou reutiliza erros existentes.
- Garante que o token nunca é logado.
- Garante logs úteis com request_id, workspace_id e status, sem secrets.
- Cria testes com mock HTTP/monkeypatch para sucesso e falhas principais.
- Não implementes ainda o payload builder nem endpoint API.
- Não alteres intelligence_engine nem content_renderer.
- Cria o relatório em:
  backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados\prompt_03_client_sincrono_intelligence_engine.md

Critérios de aceitação:
- Existe client síncrono para POST /intelligence/campaign.
- Headers internos são enviados correctamente.
- Timeout é aplicado.
- 4xx, 5xx, timeout e JSON inválido são tratados de forma previsível.
- Token não aparece em logs nem em mensagens de erro.
- Testes do client passam.
- Validações relevantes foram executadas.
- O relatório lista ficheiros alterados, comportamento implementado, testes, pendências e próximo passo recomendado.
```

## Prompt 04 (opus) — Criar builder do data bundle de campanha

```prompt
Objectivo:
Criar o adapter/builder que monta o payload esperado pelo Intelligence Engine a partir dos modelos reais do Backend Core.

Contexto obrigatório:
- Repositório/componente alvo: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados
- Payload alvo:
  - payload_version: 1.0;
  - workspace_id;
  - request_id;
  - entity type campaign;
  - context.reference_date;
  - data.campaign;
  - data.artist;
  - data.track;
  - data.smart_link_stats;
  - data.content_outputs;
  - data.reports;
  - data.media_kits;
  - goals/milestones quando existirem.

Instruções:
- Inspecciona modelos e relações reais nas apps:
  - campaigns;
  - catalogue;
  - links;
  - content;
  - reports;
  - workspaces.
- Cria CampaignIntelligencePayloadBuilder ou nome equivalente alinhado com o padrão do projecto.
- O builder deve receber campaign, workspace e request_id/contexto quando aplicável.
- Valida que a campanha pertence ao workspace.
- Serializa de forma JSON-safe:
  - UUIDs;
  - datas;
  - datetimes;
  - Decimal;
  - enums/choices;
  - valores nulos.
- Monta data.campaign com campos relevantes e seguros.
- Monta data.artist, se existir.
- Monta data.track, se existir.
- Monta data.smart_link_stats com agregados úteis:
  - total_clicks;
  - clicks_last_7_days;
  - clicks_last_30_days;
  - active_links, se aplicável;
  - outros campos existentes e úteis.
- Monta data.content_outputs com outputs recentes/relevantes.
- Monta data.reports com reports relevantes.
- Monta data.media_kits com media kits relevantes.
- Inclui goals/milestones se existirem no domínio actual.
- Evita queries N+1.
- Usa select_related/prefetch_related ou queries agregadas quando necessário.
- Trata dados ausentes gerando payload válido, não erro inesperado.
- Cria testes unitários com factories/fixtures existentes.
- Testa pelo menos:
  - campanha rica com dados relacionados;
  - campanha mínima;
  - campanha sem smart links;
  - campanha sem content outputs;
  - campanha sem reports/media kits;
  - workspace inválido.
- Não chames ainda o Intelligence Engine neste prompt.
- Não alteres intelligence_engine nem content_renderer.
- Cria o relatório em:
  backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados\prompt_04_builder_data_bundle_campaign.md

Critérios de aceitação:
- Builder gera payload compatível com o contrato do Intelligence Engine.
- Payload inclui payload_version 1.0, workspace_id, request_id e entity campaign.
- Dados ausentes são tratados sem falha inesperada.
- Datas/UUIDs/enums são JSON-safe.
- Workspace mismatch é tratado de forma segura.
- Testes unitários passam.
- Validações relevantes foram executadas.
- O relatório lista ficheiros alterados, decisões de mapeamento, testes, pendências e próximo passo recomendado.
```

## Prompt 05 (opus) — Criar serviço de domínio para intelligence de campanha

```prompt
Objectivo:
Criar o serviço de domínio no Backend Core que orquestra carregamento da campanha, validações, payload builder e client síncrono do Intelligence Engine.

Contexto obrigatório:
- Repositório/componente alvo: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados
- Builder criado no Prompt 04.
- Client criado no Prompt 03.
- Modelo MVP:
  - resposta em tempo real;
  - sem persistência obrigatória de snapshots;
  - sem ExternalJobReference.

Instruções:
- Cria CampaignIntelligenceService ou nome equivalente alinhado com o projecto.
- O serviço deve receber:
  - campaign_id ou campaign;
  - workspace;
  - user/request context, se necessário;
  - request_id.
- Carrega a campanha de forma segura e eficiente.
- Valida workspace.
- Garante que dados de outro workspace não são expostos.
- Usa o builder para montar o payload.
- Usa o client para chamar POST /intelligence/campaign.
- Trata INTELLIGENCE_ENGINE_ENABLED:
  - se desactivado, devolver erro controlado ou resposta dry-run conforme padrão do projecto.
- Trata INTELLIGENCE_ENGINE_DRY_RUN:
  - devolver resposta previsível e documentada ou evitar chamada real, conforme padrão existente.
- Trata erros do client:
  - timeout;
  - indisponibilidade;
  - 403;
  - 422;
  - 5xx;
  - JSON inválido.
- Mapeia erros para excepções/retornos internos consistentes com o Backend Core.
- Não persistir snapshot no MVP, salvo se já houver decisão explícita no backlog ou no plano.
- Garante logs úteis sem token.
- Cria testes unitários com client mockado.
- Não exponhas ainda endpoint API neste prompt, salvo se o padrão do projecto juntar service e endpoint de forma inevitável.
- Não alteres intelligence_engine nem content_renderer.
- Cria o relatório em:
  backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados\prompt_05_service_campaign_intelligence.md

Critérios de aceitação:
- Serviço devolve intelligence de campanha com sucesso usando builder + client.
- Serviço trata campanha inexistente.
- Serviço trata workspace inválido.
- Serviço trata IE desactivado/dry-run.
- Serviço trata timeout/5xx/4xx sem crash.
- Token não aparece em logs.
- Testes unitários passam.
- Validações relevantes foram executadas.
- O relatório lista ficheiros alterados, comportamento implementado, testes, pendências e próximo passo recomendado.
```

## Prompt 06 (opus) — Expor endpoint API no Backend Core

```prompt
Objectivo:
Expor no Backend Core um endpoint protegido para obter intelligence de uma campanha através do serviço criado.

Contexto obrigatório:
- Repositório/componente alvo: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados
- Serviço de domínio criado no Prompt 05.
- Endpoint sugerido pelo backlog:
  - POST /api/campaigns/{campaign_id}/intelligence/
  - ou rota equivalente alinhada com o padrão real do projecto.

Instruções:
- Inspecciona routers/viewsets existentes de campaigns.
- Escolhe a abordagem mais consistente com o projecto:
  - action em ViewSet;
  - APIView dedicada;
  - route dedicada.
- Recomendação: usar POST se a chamada dispara cálculo remoto e pode aceitar contexto; usar GET apenas se o padrão do projecto tratar isto como leitura pura sem body.
- Garante autenticação do utilizador.
- Garante RBAC/permissões de acesso à campanha.
- Garante isolamento por workspace.
- Chama CampaignIntelligenceService.
- Devolve resposta normalizada ao cliente.
- Garante que a resposta inclui, quando o IE responder com sucesso:
  - analysis;
  - scores;
  - grade;
  - moments;
  - recommendations;
  - summary;
  - explanations;
  - warnings;
  - metadata.
- Trata erros:
  - campanha não encontrada;
  - sem permissão;
  - workspace inválido;
  - IE desactivado;
  - dry-run;
  - timeout;
  - serviço indisponível;
  - payload inválido;
  - erro inesperado controlado.
- Cria serializer de resposta se o padrão do projecto exigir.
- Actualiza OpenAPI/schema se o projecto tiver geração/documentação de API.
- Cria testes API para sucesso, permissão negada, campanha inexistente, workspace errado e falha do IE.
- Não alteres intelligence_engine nem content_renderer.
- Cria o relatório em:
  backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados\prompt_06_endpoint_api_campaign_intelligence.md

Critérios de aceitação:
- Endpoint API existe e está protegido.
- Utilizador sem permissão não acede aos dados.
- Campanha fora do workspace não é exposta.
- Endpoint chama o serviço de intelligence.
- Resposta de sucesso contém os blocos principais do IE.
- Erros são previsíveis e testados.
- OpenAPI/schema actualizado, se aplicável.
- Testes API passam.
- Validações relevantes foram executadas.
- O relatório lista ficheiros alterados, rota criada, decisões, testes, pendências e próximo passo recomendado.
```

## Prompt 07 (opus) — Implementar política de timeout, retry e fallback

```prompt
Objectivo:
Consolidar o comportamento operacional mínimo do Backend Core quando o Intelligence Engine falha, demora ou devolve erro.

Contexto obrigatório:
- Repositório/componente alvo: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados
- Client, builder, service e endpoint já implementados nos prompts anteriores.

Instruções:
- Revê o comportamento actual implementado nos Prompts 03 a 06.
- Define timeout default curto e configurável.
- Define política de retry mínima:
  - não fazer retry em 4xx;
  - considerar retry simples apenas para timeout/unavailable/5xx se já houver padrão no projecto;
  - evitar retry longo durante request HTTP do utilizador.
- Garante fallback controlado para:
  - IE desactivado;
  - IE em dry-run;
  - timeout;
  - conexão recusada;
  - 5xx;
  - 403 interno;
  - 422 invalid_payload;
  - JSON inválido;
  - resposta inesperada.
- Garante que a resposta ao consumidor não expõe token, stack trace ou detalhes sensíveis.
- Garante logs úteis com:
  - request_id;
  - workspace_id;
  - campaign_id;
  - tempo de chamada, se já existir padrão simples;
  - tipo de erro;
  - status da resposta.
- Nunca logar X-Internal-Token.
- Actualiza testes existentes ou cria testes dedicados aos cenários de falha.
- Actualiza documentação de comportamento operacional.
- Não alteres intelligence_engine nem content_renderer.
- Cria o relatório em:
  backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados\prompt_07_timeout_retry_fallback.md

Critérios de aceitação:
- Timeout é configurável.
- 4xx não é retentado.
- Timeout/5xx/unavailable são tratados de forma controlada.
- Erros devolvidos ao cliente são seguros.
- Logs ajudam diagnóstico sem expor secrets.
- Testes de falha passam.
- Validações relevantes foram executadas.
- O relatório lista ficheiros alterados, política aplicada, testes, pendências e próximo passo recomendado.
```

## Prompt 08 (opus) — Validar integração com mocks HTTP

```prompt
Objectivo:
Validar de ponta a ponta, dentro do Backend Core, a integração com o Intelligence Engine usando mocks HTTP ou monkeypatch, sem depender do serviço real em todos os testes.

Contexto obrigatório:
- Repositório/componente alvo: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados
- Endpoints, service, builder e client já implementados.

Instruções:
- Cria ou completa testes com mock HTTP/monkeypatch do client.
- Cobre o fluxo completo:
  - API do Backend Core;
  - service;
  - builder;
  - client mockado;
  - resposta normalizada.
- Testa resposta completed do IE com:
  - analysis;
  - scores;
  - grade;
  - moments;
  - recommendations;
  - summary;
  - explanations;
  - warnings.
- Testa warnings do IE.
- Testa scores unknown.
- Testa recommendations vazias ou wait_for_more_data, se aplicável.
- Testa timeout.
- Testa 403 do IE.
- Testa 422 invalid_payload.
- Testa 5xx.
- Testa JSON inválido.
- Testa IE desactivado e dry-run.
- Valida que:
  - X-Internal-Token é enviado ao IE;
  - workspace_id é propagado;
  - request_id é propagado;
  - campaign_id/entity.id é correcto;
  - token não aparece em logs.
- Usa padrões existentes de fixtures/factories.
- Evita testes frágeis baseados em ordem de campos JSON quando não for necessário.
- Não alteres intelligence_engine nem content_renderer.
- Cria o relatório em:
  backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados\prompt_08_validacao_mocks_http.md

Critérios de aceitação:
- Testes com mock cobrem sucesso e principais falhas.
- Payload enviado ao IE é compatível com contrato.
- Headers internos são verificados.
- RBAC/workspace continuam cobertos.
- Token não aparece em logs.
- Testes passam.
- Validações relevantes foram executadas.
- O relatório lista cenários cobertos, comandos executados, resultados, pendências e próximo passo recomendado.
```

## Prompt 09 (opus) — Validar loop real Backend Core para Intelligence Engine

```prompt
Objectivo:
Validar a integração real entre Backend Core e Intelligence Engine com ambos os serviços em execução, registando evidências e limitações.

Contexto obrigatório:
- Repositório/componente alvo: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados
- Intelligence Engine está no componente momentflow\intelligence_engine.
- Este prompt pode consultar instruções de execução do Intelligence Engine, mas não deve alterar esse componente.

Pré-condições esperadas:
- Backend Core consegue arrancar localmente.
- Intelligence Engine consegue arrancar localmente.
- INTELLIGENCE_ENGINE_BASE_URL aponta para o serviço real.
- INTELLIGENCE_ENGINE_INTERNAL_TOKEN está alinhado com o token do IE.
- Existe campanha de teste no Backend Core ou fixture adequada.

Instruções:
- Tenta executar uma validação real com os dois serviços.
- Arranca ou documenta como arrancar o Intelligence Engine.
- Arranca ou documenta como arrancar o Backend Core.
- Executa chamada ao endpoint Django criado.
- Confirma que o Backend Core chama o IE real.
- Confirma que a resposta contém:
  - analysis;
  - scores;
  - grade;
  - moments;
  - recommendations;
  - summary.
- Confirma que logs não expõem token.
- Testa comportamento com IE desligado ou URL inválida, se viável.
- Se a validação real não puder ser executada por limitação de ambiente, não inventes resultado:
  - explica a limitação;
  - mantém testes mockados como evidência;
  - deixa checklist manual clara.
- Não alteres intelligence_engine nem content_renderer.
- Corrige apenas problemas directamente relacionados com a integração se forem encontrados.
- Cria o relatório em:
  backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados\prompt_09_loop_real_backend_core_intelligence.md

Critérios de aceitação:
- Loop real Backend Core → Intelligence Engine foi validado ou limitação foi documentada.
- Resposta real ou esperada está documentada.
- Falha com IE indisponível é tratada de forma controlada.
- Logs não expõem token.
- Evidências foram registadas.
- Testes relevantes continuam a passar.
- O relatório lista comandos, resultados, limitações, pendências e próximo passo recomendado.
```

## Prompt 10 (sonnet) — Documentar integração e estado final

```prompt
Objectivo:
Fechar a fase de integração Backend Core ↔ Intelligence Engine com documentação final, validação de qualidade e estado honesto.

Contexto obrigatório:
- Repositório/componente alvo: backend_core
- Backlog da fase: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\01_backlog.md
- Pasta de resultados: backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados
- Integração implementada nos prompts anteriores.

Instruções:
- Revê todos os ficheiros alterados nesta fase.
- Executa as validações disponíveis e relevantes do Backend Core, por exemplo:
  - pytest;
  - python manage.py check;
  - ruff ou lint equivalente;
  - typecheck, se existir;
  - testes API relevantes;
  - testes de integração/mocks;
  - validação real, se viável.
- Não inventes resultados. Se algum comando não puder ser executado, documenta a razão.
- Corrige apenas falhas directamente relacionadas com esta integração.
- Não faças refactors fora do escopo.
- Actualiza documentação relevante:
  - README ou docs do Backend Core, se aplicável;
  - documentação de variáveis de ambiente;
  - documentação do endpoint Django;
  - documentação de payload enviado ao IE;
  - documentação de resposta;
  - política de timeout/retry/fallback.
- Cria ou actualiza:
  backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\estado_integracao_intelligence_engine.md
- O documento de estado deve incluir:
  - estado final da integração;
  - arquitectura;
  - endpoints criados;
  - settings;
  - client/service/builder;
  - validações executadas;
  - testes;
  - limitações;
  - pendências;
  - pronto/não pronto para piloto;
  - pronto/não pronto para produção;
  - próximos passos.
- Confirma ausência de secrets reais em:
  - docs;
  - .env.example;
  - relatórios;
  - logs de exemplo;
  - testes.
- Cria o relatório final em:
  backend_core\docs\backend_core\fundamentos\integracao_intelligence_engine\resultados\prompt_10_documentacao_estado_final.md

Critérios de aceitação:
- Validações relevantes foram executadas ou limitações foram documentadas.
- Falhas relacionadas foram corrigidas ou registadas.
- Documento de estado final existe.
- Relatório final existe.
- Documentação de configuração e endpoint está actualizada.
- Não há secrets reais em documentação.
- Estado final é honesto.
- Próximo passo recomendado está claro.
```
