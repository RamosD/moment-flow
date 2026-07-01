# Pipeline: FastAPI Intelligence Engine

## Prompt 01 (opus) — Criar fundação do serviço FastAPI

```prompt
Objectivo:
Criar a fundação técnica do serviço FastAPI Intelligence Engine em momentflow\intelligence_engine, alinhada com o backlog em momentflow\intelligence_engine\docs\gestao\fundamentos\backlog.md e com os padrões existentes no repositório.

Contexto obrigatório:
- O backlog está em: momentflow\intelligence_engine\docs\gestao\fundamentos\backlog.md
- O serviço a implementar está em: momentflow\intelligence_engine
- Os outros componentes de referência estão em:
  - momentflow\content_renderer
  - momentflow\backend_core
- Os relatórios de execução devem ficar em:
  - momentflow\intelligence_engine\docs\gestao\fundamentos\resultados
- Tese arquitectural:
  - Django governa o produto.
  - Renderer gera activos.
  - FastAPI Intelligence calcula, recomenda e detecta oportunidades.
  - Frontend orquestra a experiência do utilizador.

Instruções:
- Lê o backlog completo antes de alterar ficheiros.
- Inspecciona a estrutura existente de momentflow\intelligence_engine.
- Inspecciona momentflow\content_renderer e momentflow\backend_core apenas para identificar padrões úteis de documentação, configuração, contratos internos, healthchecks, logs, testes e organização.
- Não alteres momentflow\content_renderer nem momentflow\backend_core neste prompt.
- Cria ou ajusta a estrutura base do serviço FastAPI.
- Implementa uma aplicação FastAPI mínima com:
  - app/main.py ou equivalente;
  - GET /health;
  - configuração base;
  - logger estruturado inicial;
  - modelo base de erro;
  - README inicial;
  - .env.example sem secrets reais;
  - configuração de testes.
- Usa Python moderno e dependências adequadas ao padrão do repositório.
- Se o projecto já usar pyproject.toml, segue esse padrão; se usar requirements.txt, adapta.
- Mantém o escopo restrito à fundação técnica. Não implementes ainda analysis, scoring, recommendations ou moments.
- Garante que o serviço consegue arrancar localmente.
- Cria testes mínimos para GET /health e para arranque/configuração base.
- Garante que nenhum token, password ou segredo real é introduzido.
- Cria o relatório de execução em:
  momentflow\intelligence_engine\docs\gestao\fundamentos\resultados\prompt_01_fundacao_fastapi.md

Critérios de aceitação:
- A estrutura base do serviço FastAPI existe.
- GET /health devolve 200 com identificação do serviço.
- Existe configuração base via ambiente.
- Existe logger estruturado inicial.
- Existe modelo base de erro.
- Existe README inicial.
- Existe .env.example sem secrets reais.
- Existem testes mínimos.
- Foram executadas as validações disponíveis, por exemplo pytest e/ou checks equivalentes.
- O relatório prompt_01_fundacao_fastapi.md lista ficheiros criados/alterados, decisões tomadas, comandos executados, resultados, pendências e próximo passo recomendado.
```

## Prompt 02 (opus) — Implementar configuração, segurança interna e erros

```prompt
Objectivo:
Implementar configuração robusta, autenticação interna por X-Internal-Token e respostas de erro normalizadas no serviço FastAPI Intelligence Engine.

Contexto obrigatório:
- Lê o backlog em: momentflow\intelligence_engine\docs\gestao\fundamentos\backlog.md
- Trabalha apenas em: momentflow\intelligence_engine
- Usa momentflow\content_renderer e momentflow\backend_core apenas como referência de padrões, sem os alterar.
- Os relatórios devem ficar em: momentflow\intelligence_engine\docs\gestao\fundamentos\resultados

Instruções:
- Parte da fundação criada no Prompt 01.
- Implementa loader de configuração com validação clara das variáveis.
- Implementa suporte a variáveis como:
  - APP_ENV
  - SERVICE_NAME
  - SERVICE_VERSION
  - INTERNAL_API_TOKEN
  - LOG_LEVEL
- Define comportamento seguro:
  - GET /health não exige token.
  - Endpoints internos futuros devem exigir X-Internal-Token.
  - Token ausente deve devolver 403.
  - Token errado deve devolver 403.
  - Token vazio em ambiente production deve impedir o arranque ou gerar erro claro de configuração.
  - O token nunca deve aparecer em logs, respostas ou relatórios.
- Implementa mecanismo de autenticação interna reutilizável, por dependência FastAPI ou middleware, conforme melhor padrão para o serviço.
- Usa comparação segura para token quando aplicável.
- Implementa erro comum normalizado para:
  - invalid_payload
  - unauthorized_internal_request
  - not_found
  - internal_error
  - config_error, se aplicável
- Garante que erros inesperados são tratados sem expor stack traces em resposta pública.
- Garante que logs são úteis, mas redigem campos sensíveis como token, password, secret, authorization e api_key.
- Cria endpoints internos temporários apenas se forem necessários para testar a segurança; se criares, documenta que são de teste ou evita mantê-los na API final.
- Cria testes para:
  - endpoint protegido com token correcto;
  - endpoint protegido sem token;
  - endpoint protegido com token errado;
  - token não exposto em logs;
  - erro normalizado;
  - configuração inválida em production.
- Actualiza README e .env.example.
- Cria o relatório de execução em:
  momentflow\intelligence_engine\docs\gestao\fundamentos\resultados\prompt_02_config_seguranca_erros.md

Critérios de aceitação:
- Configuração é validada e documentada.
- X-Internal-Token funciona nos endpoints protegidos.
- GET /health continua público.
- Erros seguem contrato normalizado.
- Logs não expõem secrets.
- Testes de segurança e erro passam.
- Validações relevantes foram executadas.
- O relatório final inclui ficheiros alterados, comportamento implementado, comandos executados, resultados, pendências e próximo passo recomendado.
```

## Prompt 03 (opus) — Definir schemas Pydantic e contratos internos

```prompt
Objectivo:
Definir os schemas Pydantic e contratos internos do FastAPI Intelligence Engine, preparando os endpoints de analysis, scoring, recommendations e moments.

Contexto obrigatório:
- Lê o backlog em: momentflow\intelligence_engine\docs\gestao\fundamentos\backlog.md
- Trabalha apenas em: momentflow\intelligence_engine
- Consulta momentflow\backend_core para perceber entidades, nomes e payloads prováveis, sem alterar esse componente.
- Consulta momentflow\content_renderer apenas como referência de contratos internos, payload_version, headers e documentação, sem alterar esse componente.
- Os relatórios devem ficar em: momentflow\intelligence_engine\docs\gestao\fundamentos\resultados

Instruções:
- Define schemas Pydantic comuns para:
  - EntityRef;
  - BaseIntelligenceRequest;
  - BaseIntelligenceResponse;
  - Explanation;
  - Warning;
  - ErrorResponse;
  - Metadata comum;
  - campos de identificação como workspace_id, request_id e payload_version.
- Define schemas específicos para:
  - campaign analysis;
  - scoring;
  - recommendations;
  - moment detection;
  - endpoint composto futuro.
- Garante que payload_version é obrigatório e começa por 1.0.
- Garante que workspace_id, request_id e entity são validados.
- Garante que entity.type aceita apenas valores conhecidos no MVP, por exemplo campaign, artist, track, content_pack_request, report e media_kit.
- Define enums ou Literals para:
  - status;
  - health;
  - grade;
  - priority;
  - confidence;
  - action;
  - moment type;
  - severity.
- Garante que respostas são explícitas, explicáveis e estáveis.
- Não implementes ainda a lógica de negócio dos motores; nesta fase cria contratos, exemplos e testes de validação.
- Actualiza a OpenAPI automaticamente via FastAPI.
- Actualiza README com exemplos simples de request/response.
- Cria testes para payloads válidos e inválidos.
- Cria testes para garantir que erros de validação seguem o contrato normalizado, tanto quanto possível.
- Cria o relatório de execução em:
  momentflow\intelligence_engine\docs\gestao\fundamentos\resultados\prompt_03_schemas_contratos.md

Critérios de aceitação:
- Schemas comuns e específicos existem.
- Payloads válidos são aceites.
- Payloads inválidos são rejeitados com erro normalizado.
- OpenAPI reflecte os contratos.
- README inclui exemplos úteis.
- Testes de validação passam.
- Validações relevantes foram executadas.
- O relatório final inclui ficheiros alterados, decisões de contrato, comandos executados, resultados, pendências e próximo passo recomendado.
```

## Prompt 04 (opus) — Implementar campaign analysis MVP

```prompt
Objectivo:
Implementar o endpoint POST /analysis/campaign com análise heurística, determinística e explicável de campanhas.

Contexto obrigatório:
- Lê o backlog em: momentflow\intelligence_engine\docs\gestao\fundamentos\backlog.md
- Trabalha apenas em: momentflow\intelligence_engine
- Consulta momentflow\backend_core apenas para entender entidades de campanha, artista, track, reports, media kits, smart links e content outputs, sem alterar o Backend Core.
- Consulta momentflow\content_renderer apenas se precisares de perceber content packs/outputs gerados, sem alterar o Renderer.
- Os relatórios devem ficar em: momentflow\intelligence_engine\docs\gestao\fundamentos\resultados

Instruções:
- Parte dos schemas definidos no Prompt 03.
- Cria CampaignAnalysisService ou equivalente.
- Implementa POST /analysis/campaign como endpoint interno protegido por X-Internal-Token.
- O endpoint deve receber dados de campanha e devolver:
  - campaign_health;
  - summary;
  - strengths;
  - weaknesses;
  - opportunities;
  - risks;
  - explanations;
  - warnings quando existirem dados insuficientes.
- Usa regras heurísticas simples e documentadas.
- Regras MVP sugeridas:
  - Sem dados suficientes → campaign_health unknown e warning.
  - Campanha com content_outputs recentes → strength.
  - Campanha sem content_outputs → opportunity content_gap.
  - Smart link com actividade positiva → strength.
  - Smart link sem actividade → weakness ou warning.
  - Report ausente em período relevante → opportunity report_due.
  - Media kit ausente → opportunity media_kit_missing.
  - Dados contraditórios ou incompletos → warning, não 500.
- O resultado deve ser determinístico: o mesmo input deve gerar o mesmo output.
- Não uses IA generativa.
- Não faças chamadas externas.
- Não persistas dados.
- Garante que payloads incompletos são tratados com warnings e não com falha inesperada.
- Cria testes unitários para o serviço.
- Cria testes HTTP para o endpoint.
- Actualiza README com o contrato do endpoint e exemplos.
- Cria o relatório de execução em:
  momentflow\intelligence_engine\docs\gestao\fundamentos\resultados\prompt_04_campaign_analysis.md

Critérios de aceitação:
- POST /analysis/campaign funciona com token correcto.
- Endpoint rejeita chamadas sem token.
- Endpoint devolve análise estruturada e explicável.
- Dados insuficientes geram warnings, não erro 500.
- Resultado é determinístico.
- Testes unitários e HTTP passam.
- Validações relevantes foram executadas.
- O relatório final inclui ficheiros alterados, regras implementadas, comandos executados, resultados, pendências e próximo passo recomendado.
```

## Prompt 05 (opus) — Implementar scoring engine MVP

```prompt
Objectivo:
Implementar o scoring engine MVP para campanhas, com scores determinísticos, explicáveis e testáveis.

Contexto obrigatório:
- Lê o backlog em: momentflow\intelligence_engine\docs\gestao\fundamentos\backlog.md
- Trabalha apenas em: momentflow\intelligence_engine
- Consulta momentflow\backend_core para compreender dados de campanha e entidades relevantes, sem alterar esse componente.
- Os relatórios devem ficar em: momentflow\intelligence_engine\docs\gestao\fundamentos\resultados

Instruções:
- Cria ScoringEngine ou equivalente.
- Implementa POST /scoring/campaign como endpoint interno protegido por X-Internal-Token.
- Calcula os scores MVP:
  - campaign_readiness_score;
  - momentum_score;
  - content_opportunity_score;
  - risk_score;
  - priority_score.
- Scores devem seguir escala 0 a 100.
- Quando não houver dados suficientes, devolve score null ou estado unknown, de forma consistente com os schemas.
- Gera grade A/B/C/D/unknown.
- Cada score deve ter pelo menos uma explanation ou uma warning quando não puder ser calculado.
- Documenta os pesos/regras usados no README ou em documentação própria.
- Mantém o motor determinístico.
- Não uses IA generativa.
- Não faças chamadas externas.
- Não persistas resultados.
- Evita lógica opaca: cada score deve ser justificável.
- Cria testes unitários para:
  - campanha com bons sinais;
  - campanha com dados fracos;
  - campanha sem dados suficientes;
  - dados parciais;
  - limites 0 e 100.
- Cria testes HTTP para o endpoint.
- Garante que payload inválido não causa 500.
- Cria o relatório de execução em:
  momentflow\intelligence_engine\docs\gestao\fundamentos\resultados\prompt_05_scoring_engine.md

Critérios de aceitação:
- POST /scoring/campaign funciona.
- Scores são consistentes e explicáveis.
- Grade é calculada de forma estável.
- Dados insuficientes são tratados sem erro inesperado.
- Testes unitários e HTTP passam.
- Regras/pesos estão documentados.
- Validações relevantes foram executadas.
- O relatório final inclui ficheiros alterados, regras de scoring, comandos executados, resultados, pendências e próximo passo recomendado.
```

## Prompt 06 (opus) — Implementar recommendation engine MVP

```prompt
Objectivo:
Implementar o recommendation engine MVP para gerar recomendações de campanha com prioridade, confiança, justificação e acções compatíveis com o produto.

Contexto obrigatório:
- Lê o backlog em: momentflow\intelligence_engine\docs\gestao\fundamentos\backlog.md
- Trabalha apenas em: momentflow\intelligence_engine
- Consulta momentflow\backend_core para perceber content packs, campanhas e entidades relevantes, sem alterar o Backend Core.
- Consulta momentflow\content_renderer para perceber outputs/templates suportados, sem alterar o Renderer.
- Os relatórios devem ficar em: momentflow\intelligence_engine\docs\gestao\fundamentos\resultados

Instruções:
- Cria RecommendationEngine ou equivalente.
- Implementa POST /recommendations/campaign como endpoint interno protegido por X-Internal-Token.
- O motor deve gerar recomendações como:
  - create_release_post;
  - create_story;
  - create_milestone_post;
  - create_weekly_growth_post;
  - create_media_kit;
  - create_report;
  - improve_smart_link;
  - wait_for_more_data;
  - no_action.
- Cada recomendação deve conter:
  - action;
  - priority;
  - confidence;
  - reason;
  - suggested_content_pack quando aplicável;
  - expected_outputs quando aplicável;
  - explanations.
- As recomendações não devem criar entidades no Django.
- As recomendações não devem chamar directamente o renderer.
- O output deve ser compatível com a tese:
  - Intelligence recomenda.
  - Django decide e cria jobs.
  - Renderer gera activos.
- Usa as regras de scoring e analysis, se já existirem, mas mantém baixo acoplamento.
- Quando os dados forem insuficientes, devolver wait_for_more_data ou no_action com warning.
- Garante que actions sugeridas são suportáveis pelo produto ou ficam explicitamente marcadas como recomendação conceptual.
- Cria testes unitários para recomendações principais.
- Cria testes HTTP para o endpoint.
- Actualiza README com exemplos.
- Cria o relatório de execução em:
  momentflow\intelligence_engine\docs\gestao\fundamentos\resultados\prompt_06_recommendation_engine.md

Critérios de aceitação:
- POST /recommendations/campaign funciona.
- Recomendações têm action, priority, confidence e reason.
- Recomendações são determinísticas e explicáveis.
- Endpoint não persiste dados nem cria campanhas.
- Endpoint não chama o renderer.
- Dados insuficientes são tratados com warning ou recomendação de espera.
- Testes passam.
- Validações relevantes foram executadas.
- O relatório final inclui ficheiros alterados, regras implementadas, comandos executados, resultados, pendências e próximo passo recomendado.
```

## Prompt 07 (opus) — Implementar moment detection MVP

```prompt
Objectivo:
Implementar o detector de momentos MVP para identificar oportunidades simples que justifiquem acções de campanha.

Contexto obrigatório:
- Lê o backlog em: momentflow\intelligence_engine\docs\gestao\fundamentos\backlog.md
- Trabalha apenas em: momentflow\intelligence_engine
- Consulta momentflow\backend_core apenas para compreender dados disponíveis de campanhas, reports, media kits, smart links, tracks e content outputs, sem o alterar.
- Os relatórios devem ficar em: momentflow\intelligence_engine\docs\gestao\fundamentos\resultados

Instruções:
- Cria MomentDetector ou equivalente.
- Implementa POST /moments/detect como endpoint interno protegido por X-Internal-Token.
- Implementa detecção determinística dos momentos MVP:
  - release_window;
  - weekly_growth;
  - milestone_reached;
  - low_engagement;
  - content_gap;
  - report_due;
  - media_kit_missing;
  - smart_link_activity.
- Cada momento deve conter:
  - type;
  - severity;
  - confidence;
  - summary;
  - recommended_action;
  - explanations.
- Quando os dados forem insuficientes, devolver lista vazia ou warning explícito, conforme o contrato definido.
- Não uses IA generativa.
- Não faças scraping externo.
- Não faças chamadas a APIs externas.
- Não persistas resultados.
- Garante que os momentos recomendam apenas acções compatíveis com o recommendation engine.
- Cria testes unitários para cada tipo de momento.
- Cria testes HTTP para o endpoint.
- Actualiza README com exemplos.
- Cria o relatório de execução em:
  momentflow\intelligence_engine\docs\gestao\fundamentos\resultados\prompt_07_moment_detection.md

Critérios de aceitação:
- POST /moments/detect funciona.
- Momentos são detectados de forma determinística.
- Cada momento tem type, severity, confidence, summary e recommended_action.
- Dados insuficientes são tratados sem erro 500.
- Testes unitários e HTTP passam.
- Validações relevantes foram executadas.
- O relatório final inclui ficheiros alterados, regras de detecção, comandos executados, resultados, pendências e próximo passo recomendado.
```

## Prompt 08 (opus) — Implementar endpoint composto de intelligence

```prompt
Objectivo:
Implementar o endpoint composto POST /intelligence/campaign para agregar analysis, scoring, moment detection e recommendations numa única resposta coerente.

Contexto obrigatório:
- Lê o backlog em: momentflow\intelligence_engine\docs\gestao\fundamentos\backlog.md
- Trabalha apenas em: momentflow\intelligence_engine
- Consulta momentflow\backend_core e momentflow\content_renderer apenas para validar coerência de contratos, sem alterar esses componentes.
- Os relatórios devem ficar em: momentflow\intelligence_engine\docs\gestao\fundamentos\resultados

Instruções:
- Cria IntelligenceOrchestrator ou equivalente.
- Implementa POST /intelligence/campaign como endpoint interno protegido por X-Internal-Token.
- O endpoint composto deve executar:
  - campaign analysis;
  - scoring;
  - moment detection;
  - recommendations.
- A resposta deve agregar:
  - analysis;
  - scores;
  - moments;
  - recommendations;
  - summary;
  - explanations consolidadas;
  - warnings consolidados;
  - metadata.
- Evita duplicar demasiada lógica. O endpoint composto deve orquestrar serviços já existentes.
- Garante que uma falha parcial previsível não causa 500 indevido quando puder ser convertida em warning.
- Garante que erro de payload continua a ser rejeitado de forma normalizada.
- O resultado deve ser determinístico.
- Não chames o Backend Core a partir deste endpoint.
- Não chames o renderer a partir deste endpoint.
- Não persistas dados.
- Cria testes unitários para o orchestrator.
- Cria testes HTTP para o endpoint composto.
- Actualiza README com exemplo completo.
- Cria o relatório de execução em:
  momentflow\intelligence_engine\docs\gestao\fundamentos\resultados\prompt_08_endpoint_composto.md

Critérios de aceitação:
- POST /intelligence/campaign funciona.
- O endpoint devolve analysis, scores, moments e recommendations.
- Warnings são consolidados.
- Explanations são consolidadas.
- Serviços continuam testáveis isoladamente.
- Falhas previsíveis são tratadas sem 500 indevido.
- Testes passam.
- Validações relevantes foram executadas.
- O relatório final inclui ficheiros alterados, comportamento implementado, comandos executados, resultados, pendências e próximo passo recomendado.
```

## Prompt 09 (opus) — Documentar contrato Backend Core ↔ Intelligence Engine

```prompt
Objectivo:
Preparar e documentar o contrato de integração entre o Backend Core Django e o FastAPI Intelligence Engine, sem alterar o Backend Core nesta fase salvo necessidade documental muito justificada.

Contexto obrigatório:
- Lê o backlog em: momentflow\intelligence_engine\docs\gestao\fundamentos\backlog.md
- Trabalha principalmente em: momentflow\intelligence_engine
- Consulta momentflow\backend_core para identificar padrões de integração, ExternalJobReference, serviços internos, callbacks, entidades, reports, campaigns, content packs e possíveis pontos de integração.
- Consulta momentflow\content_renderer para comparar o padrão de serviço técnico externo já implementado.
- Os relatórios devem ficar em: momentflow\intelligence_engine\docs\gestao\fundamentos\resultados

Instruções:
- Analisa como o Backend Core integra serviços externos existentes.
- Analisa se, para o Intelligence Engine MVP, faz mais sentido:
  - Opção A: chamada síncrona interna para insights rápidos;
  - Opção B: ExternalJobReference para análises longas;
  - Opção C: modelo híbrido.
- Não implementes integração no Backend Core ainda, salvo se encontrares documentação já preparada para ser actualizada sem risco.
- Documenta a recomendação de integração.
- Cria ou actualiza documentação dentro de momentflow\intelligence_engine, por exemplo:
  - docs\gestao\fundamentos\contrato_backend_core_intelligence_engine.md
  - ou outro caminho equivalente já usado no projecto.
- A documentação deve incluir:
  - endpoints;
  - headers;
  - autenticação;
  - payloads;
  - respostas;
  - erros;
  - timeouts;
  - retry recomendado;
  - modo síncrono vs job externo;
  - persistência ou não dos resultados;
  - exemplos de request/response;
  - riscos;
  - decisões pendentes.
- Actualiza README com link para o contrato.
- Garante que exemplos não contêm secrets reais.
- Cria o relatório de execução em:
  momentflow\intelligence_engine\docs\gestao\fundamentos\resultados\prompt_09_contrato_backend_core.md

Critérios de aceitação:
- Existe documento de contrato Backend Core ↔ Intelligence Engine.
- Está clara a recomendação para síncrono, job externo ou híbrido.
- Estão documentados headers, payloads, respostas, erros, timeouts e retries.
- Exemplos não contêm secrets reais.
- Não foram feitas alterações indevidas em backend_core ou content_renderer.
- Validações/documentação relevantes foram revistas.
- O relatório final inclui ficheiros alterados, decisão recomendada, pendências e próximo passo recomendado.
```

## Prompt 10 (sonnet) — Validar qualidade, documentação final e estado da fase

```prompt
Objectivo:
Validar a implementação do FastAPI Intelligence Engine, consolidar documentação final e produzir um estado honesto da fase.

Contexto obrigatório:
- Lê o backlog em: momentflow\intelligence_engine\docs\gestao\fundamentos\backlog.md
- Trabalha em: momentflow\intelligence_engine
- Consulta momentflow\backend_core e momentflow\content_renderer apenas para confirmar coerência documental, sem os alterar.
- Os relatórios devem ficar em: momentflow\intelligence_engine\docs\gestao\fundamentos\resultados

Instruções:
- Revê toda a implementação feita nos prompts anteriores.
- Executa as validações disponíveis e relevantes, por exemplo:
  - pytest;
  - ruff;
  - mypy ou pyright, se configurado;
  - formatação, se configurada;
  - smoke test do GET /health, se viável;
  - testes HTTP dos endpoints principais.
- Não inventes resultados. Se algum comando não puder ser executado, documenta a razão.
- Corrige apenas falhas directamente relacionadas com a fase.
- Não faças refactors fora do escopo.
- Confirma que:
  - GET /health funciona;
  - endpoints protegidos exigem X-Internal-Token;
  - schemas validam payloads;
  - erros são normalizados;
  - campaign analysis funciona;
  - scoring funciona;
  - recommendations funcionam;
  - moment detection funciona;
  - endpoint composto funciona;
  - não há dependência obrigatória de IA generativa;
  - não há scraping externo;
  - não há persistência de estado de produto;
  - não há chamada directa ao renderer;
  - logs e docs não expõem secrets.
- Actualiza README com:
  - instalação;
  - execução;
  - variáveis de ambiente;
  - endpoints;
  - exemplos;
  - testes;
  - limitações;
  - próximos passos.
- Cria ou actualiza o documento:
  momentflow\intelligence_engine\docs\gestao\fundamentos\estado_fastapi_intelligence_engine.md
- O documento de estado deve incluir:
  - estado final da fase;
  - endpoints implementados;
  - validações executadas;
  - coverage, se existir;
  - limitações;
  - pendências;
  - pronto/não pronto para integração;
  - pronto/não pronto para produção.
- Confirma ausência de secrets reais em:
  - README;
  - .env.example;
  - docs\gestao\fundamentos;
  - docs\gestao\fundamentos\resultados.
- Cria o relatório final em:
  momentflow\intelligence_engine\docs\gestao\fundamentos\resultados\prompt_10_validacao_documentacao_final.md

Critérios de aceitação:
- Validações relevantes foram executadas ou limitações foram documentadas.
- Falhas relacionadas foram corrigidas ou registadas como pendência.
- README está actualizado.
- Documento de estado final existe.
- Relatório final existe.
- Não há secrets reais em documentação.
- Estado da fase é honesto: pronto para integração apenas se houver evidência; production-ready apenas se requisitos operacionais estiverem cumpridos.
- O relatório final inclui ficheiros alterados, comandos executados, resultados, pendências e próximo passo recomendado.
```
