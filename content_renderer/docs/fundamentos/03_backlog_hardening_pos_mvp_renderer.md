# Backlog: Hardening Pós-MVP do Content/Report Renderer

# ChartRex / MomentFlow — Content Renderer

## 1. Objectivo do documento

Este documento define o backlog de **hardening pós-MVP** do serviço `content_renderer`.

A implementação inicial do renderer já concluiu o MVP funcional:

```text id="bdmirz"
GET /health;
POST /jobs;
autenticação interna;
validação de headers e envelope;
storage local;
callback client;
template engine;
content_generation com PNG;
report_generation com PDF/HTML;
media_kit_generation com PDF/HTML;
erros normalizados;
partial success;
timeouts;
logs sem token;
documentação final;
testes, build e lint verdes.
```

Esta fase não deve adicionar novas capacidades de produto. O objectivo é estabilizar o serviço para integração real controlada com o `backend_core`.

---

## 2. Veredicto da fase anterior

Estado do renderer após o MVP:

```text id="qh7of6"
MVP funcional: sim
Integração controlada: sim
Produção: ainda não
```

Critérios já cumpridos:

```text id="zgyk9l"
build sem erros;
lint sem erros;
104 testes a passar;
jobs reais de content/report/media kit;
callbacks completed/partially_completed/failed;
storage local funcional;
documentação consolidada.
```

Pendências técnicas que motivam este backlog:

```text id="tgtwpn"
callback em background leve;
E2E completo com PostgreSQL;
validação real Django → Renderer → Django;
preparação para storage S3/R2;
coverage Vitest;
retry de callback;
eco de template_key/template_id no content_generation.
```

---

## 3. Tese arquitectural mantida

A regra arquitectural permanece:

```text id="uz0hnu"
Django governa o produto.
Renderer gera activos.
FastAPI Intelligence calcula e recomenda.
```

O renderer continua sem responsabilidade sobre:

```text id="ztlvvt"
utilizadores;
workspaces;
RBAC;
billing;
créditos;
decisões de produto;
permissões;
estado de negócio;
audit de negócio.
```

O renderer apenas:

```text id="m7yloi"
recebe job técnico;
valida contrato interno;
gera ficheiros;
persiste outputs no storage configurado;
envia callback técnico ao Django;
regista logs técnicos.
```

---

## 4. Escopo desta fase

Esta fase inclui:

```text id="z1cu3g"
callback em background leve;
melhor controlo de estado interno do job;
E2E real com PostgreSQL;
validação do loop Django → Renderer → Django;
echo de template_key/template_id no content_generation;
preparação da interface de storage para S3/R2;
retry simples de callback com backoff;
coverage Vitest;
actualização da documentação de estado.
```

---

## 5. Fora do escopo

Não implementar nesta fase:

```text id="d7nyxf"
novos templates visuais avançados;
editor visual;
vídeo;
Remotion;
FFmpeg;
publicação automática em redes sociais;
FastAPI Intelligence Engine;
métricas musicais;
moment detection;
recommendations;
frontend;
migração completa para S3/R2, salvo se explicitamente decidido;
CDN;
autenticação pública no renderer.
```

---

# 6. Backlog técnico

---

# R-HARD-001 — Implementar callback em background leve

## Objectivo

Alterar o fluxo de `POST /jobs` para responder rapidamente `202 Accepted` e executar o ciclo de render/callback em background leve.

## Problema actual

O renderer já executa render e callback, mas o fluxo síncrono pode criar corrida com o estado do `ExternalJobReference` no Django.

## Comportamento pretendido

```text id="061xb4"
POST /jobs recebe envelope válido;
valida token, headers e body;
regista job accepted;
responde 202 rapidamente;
executa render em background leve;
guarda ficheiros;
envia callback completed/partially_completed/failed;
loga resultado.
```

## Abordagem sugerida

Usar background leve sem fila complexa:

```text id="hkpzma"
setImmediate;
Promise.resolve().then(...);
ou mecanismo equivalente simples em Node.js.
```

Não introduzir ainda:

```text id="78udpa"
BullMQ;
Redis;
RabbitMQ;
Kafka;
worker pool complexo;
base de dados de jobs.
```

## Tarefas

```text id="a7zgfz"
Criar função scheduleJobExecution(envelope).
Separar recepção HTTP da execução do render.
Garantir que POST /jobs devolve 202 antes do callback.
Mover dispatch/render/storage/callback para execução assíncrona.
Garantir tratamento global de erros no background.
Garantir logs job.accepted, job.scheduled, render.started, render.completed, callback.completed.
Garantir que erro no background não derruba o processo.
Criar testes com callback assíncrono.
Actualizar README.
Actualizar documento de estado.
```

## Critérios de aceitação

```text id="zansv2"
POST /jobs devolve 202 sem esperar pelo callback.
Callback continua a ser enviado.
Erro no render gera callback failed.
Erro no callback é logado e não derruba o processo.
Testes cobrem fluxo assíncrono.
Build passa.
Lint passa.
Testes passam.
```

---

# R-HARD-002 — Criar harness E2E com PostgreSQL

## Objectivo

Validar o ciclo completo com base de dados real adequada a múltiplos processos.

## Problema actual

A validação com SQLite apresentou limitações em cenário multi-processo, impedindo confirmar o loop completo de criação de `Asset` via callback em ambiente real.

## Comportamento pretendido

```text id="1bbhba"
backend_core usa PostgreSQL;
content_renderer corre em localhost:8002;
Django corre em localhost:8000;
Django cria job;
renderer recebe job;
renderer gera ficheiro;
renderer envia callback;
Django actualiza ExternalJobReference;
Django cria Asset;
Django actualiza ContentOutput, Report ou MediaKit.
```

## Tarefas

```text id="stbs0d"
Criar docker-compose.e2e.yml ou instruções para PostgreSQL local.
Documentar variáveis DB do backend_core.
Preparar script de setup E2E.
Criar base de dados temporária para E2E.
Executar migrações do backend_core.
Criar dados mínimos: user, workspace, artist, track, campaign, content pack, report, media kit.
Subir backend_core.
Subir content_renderer.
Executar fluxo content_generation.
Executar fluxo report_generation.
Executar fluxo media_kit_generation.
Validar estados no Django.
Limpar dados de teste quando possível.
Documentar evidências.
```

## Critérios de aceitação

```text id="v78svu"
PostgreSQL sobe localmente.
Backend Core executa migrações.
Renderer recebe jobs reais do Django.
content_generation cria ContentOutput e Asset no Django.
report_generation actualiza Report e liga Asset.
media_kit_generation actualiza MediaKit e liga Asset.
Callback não devolve 404.
Teste ou checklist E2E fica documentado.
```

---

# R-HARD-003 — Validar loop real Django → Renderer → Django

## Objectivo

Confirmar, com evidência, que o contrato de integração está totalmente fechado.

## Diferença face ao R-HARD-002

O R-HARD-002 cria o ambiente.
O R-HARD-003 valida funcionalmente os cenários de negócio/técnicos.

## Cenários obrigatórios

```text id="gaful3"
content_generation completed;
content_generation partially_completed;
content_generation failed;
report_generation completed;
report_generation failed;
media_kit_generation completed;
media_kit_generation failed.
```

## Validações no Django

Para `content_generation`:

```text id="t8nuxw"
ExternalJobReference fica completed ou failed;
ContentPackRequest é actualizado;
ContentOutput é criado;
Asset é criado;
créditos são tratados correctamente, se aplicável;
Notification é criada, se aplicável;
Audit é registado, se aplicável.
```

Para `report_generation`:

```text id="r53hyq"
Report fica completed;
Asset é ligado ao Report;
falha marca Report como failed ou estado equivalente;
callback é idempotente.
```

Para `media_kit_generation`:

```text id="j6qbvp"
MediaKit fica generated/completed;
Asset é ligado ao MediaKit;
falha é reflectida correctamente;
callback é idempotente.
```

## Tarefas

```text id="e9vedp"
Criar checklist E2E funcional.
Criar ou adaptar script de teste E2E.
Executar cenários completed.
Executar cenários failed.
Executar cenário partially_completed.
Validar idempotência do callback.
Registar evidências em docs/fundamentos/resultados.
Actualizar matriz de validação do projecto, se existir.
```

## Critérios de aceitação

```text id="8h27le"
Loop completo validado com evidência.
Estados no Django confirmados.
Assets criados com metadata correcta.
Callbacks idempotentes confirmados.
Cenários failed não deixam estado inconsistente.
Relatório E2E actualizado.
```

---

# R-HARD-004 — Echo de template_key/template_id no content_generation

## Objectivo

Garantir que o renderer devolve ao Django informação suficiente para resolver o template usado.

## Problema

O renderer já escolhe templates e gera outputs, mas o Django pode precisar de `template_key` ou `template_id` no retorno para associar o output ao template correcto.

## Comportamento pretendido

Cada output de `content_generation` deve incluir:

```text id="xvu5gi"
template_key;
template_id, se recebido no envelope;
requested_template_key;
resolved_template_key;
used_fallback_template;
used_fallback_format;
```

## Tarefas

```text id="qff8cs"
Inspeccionar contrato actual do Backend Core para ContentOutput/Template.
Confirmar que campos adicionais não quebram callback.
Ler template_key/template_id de expected_outputs.
Propagar template_key/template_id para result.outputs[].
Garantir que fallback fica explícito em metadata.
Criar testes unitários.
Criar teste de integração POST /jobs.
Actualizar README e documento de estado.
```

## Critérios de aceitação

```text id="xfy819"
Output devolve template_key usado.
Output preserva template_id quando enviado.
Fallback fica explícito.
Callback continua compatível com Django.
Testes passam.
```

---

# R-HARD-005 — Preparar interface de storage para S3/R2

## Objectivo

Preparar o renderer para trocar storage local por object storage sem reescrever renderers.

## Nota importante

Esta tarefa **não exige migrar para S3/R2 já**. O foco é separar interface de storage de implementação local.

## Comportamento pretendido

```text id="em107x"
renderers dependem de interface StorageProvider;
LocalStorage implementa StorageProvider;
S3/R2 pode ser implementado depois;
metadata de Asset mantém contrato estável.
```

## Tarefas

```text id="r4nuda"
Criar interface StorageProvider.
Adaptar LocalStorage para implementar StorageProvider.
Centralizar tipo SaveBufferInput.
Centralizar tipo AssetMetadata.
Adicionar STORAGE_PROVIDER=local no env.
Validar que provider desconhecido falha no arranque.
Criar factory createStorageProvider(config).
Garantir compatibilidade com testes existentes.
Documentar futura implementação S3/R2.
```

## Critérios de aceitação

```text id="7ti1t6"
LocalStorage continua funcional.
Renderers não dependem de implementação concreta.
STORAGE_PROVIDER=local funciona.
Provider inválido falha com erro claro.
Contrato de Asset não muda.
Testes passam.
```

---

# R-HARD-006 — Implementar retry simples de callback com backoff

## Objectivo

Aumentar a resiliência quando o Django está temporariamente indisponível.

## Problema actual

O callback client usa timeout e tentativa única. Em caso de indisponibilidade momentânea, o renderer apenas loga a falha.

## Comportamento pretendido

```text id="26lw46"
callback tenta enviar;
se falhar por timeout/5xx/network, tenta novamente;
se falhar por 4xx, não insiste, salvo decisão explícita;
após esgotar tentativas, loga callback.delivery_failed;
nunca expõe token;
não bloqueia indefinidamente.
```

## Variáveis sugeridas

```text id="zu4b1t"
CALLBACK_MAX_ATTEMPTS=3
CALLBACK_RETRY_BASE_DELAY_MS=500
CALLBACK_RETRY_MAX_DELAY_MS=5000
```

## Tarefas

```text id="vymavw"
Adicionar env vars de retry.
Implementar backoff simples.
Diferenciar falhas retryable e non-retryable.
Retry em network error, timeout, 502, 503, 504.
Não retry em 400, 401, 403, 404, 422.
Adicionar logs por tentativa.
Criar testes de retry.
Garantir que token não aparece nos logs.
Actualizar README.
```

## Critérios de aceitação

```text id="b70puw"
Callback retry funciona em falha temporária.
4xx não gera retry indevido.
Timeout gera retry até ao limite.
Logs mostram tentativas sem segredos.
Testes passam.
```

---

# R-HARD-007 — Adicionar coverage Vitest

## Objectivo

Medir cobertura de testes para controlar regressões futuras.

## Problema actual

O coverage não está configurado.

## Abordagem sugerida

Usar:

```text id="syh747"
@vitest/coverage-v8
```

## Tarefas

```text id="v18jwt"
Instalar provider de coverage.
Configurar vitest.config.ts.
Adicionar script npm run test:coverage.
Definir thresholds iniciais realistas.
Gerar relatório coverage.
Documentar como executar.
Não falhar build por threshold demasiado agressivo na primeira versão.
```

## Threshold inicial sugerido

```text id="v81ejd"
lines: 70
functions: 65
branches: 55
statements: 70
```

Ajustar conforme cobertura real.

## Critérios de aceitação

```text id="x06bed"
npm run test:coverage executa.
Relatório coverage é gerado.
Thresholds iniciais configurados.
Documentação actualizada.
Não há regressão nos testes existentes.
```

---

# R-HARD-008 — Actualizar documentação de estado pós-hardening

## Objectivo

Manter documentação fiel ao estado real após as correcções.

## Documentos a actualizar

```text id="hv8vix"
README.md;
docs/fundamentos/02_estado_content_report_renderer.md;
docs/fundamentos/guia_e2e_backend_core.md;
docs/fundamentos/resultados/<relatorios_novos>.md.
```

## Tarefas

```text id="djxx95"
Actualizar README com callback background.
Actualizar README com retry de callback.
Actualizar README com storage provider.
Actualizar guia E2E com PostgreSQL.
Actualizar estado do renderer.
Registar validações executadas.
Registar pendências remanescentes.
Confirmar ausência de secrets.
```

## Critérios de aceitação

```text id="fzz3zh"
Documentação reflecte implementação real.
Pendências antigas são marcadas como resolvidas ou mantidas.
Novas pendências ficam claras.
Não existem secrets reais em documentação.
```

---

# 7. Ordem recomendada de execução

Executar nesta ordem:

```text id="dwaynp"
1. R-HARD-001 — Callback em background leve
2. R-HARD-006 — Retry simples de callback com backoff
3. R-HARD-004 — Echo de template_key/template_id
4. R-HARD-005 — Interface de storage para S3/R2
5. R-HARD-002 — Harness E2E com PostgreSQL
6. R-HARD-003 — Validação loop real Django → Renderer → Django
7. R-HARD-007 — Coverage Vitest
8. R-HARD-008 — Documentação final pós-hardening
```

Justificação:

```text id="j735fp"
Primeiro estabilizar o fluxo de callback.
Depois reforçar resiliência.
Depois alinhar contrato de content_generation.
Depois preparar storage.
Depois validar E2E real.
Por fim medir cobertura e actualizar documentação.
```

---

# 8. Critérios de aceitação da fase

Esta fase fica concluída quando:

```text id="wwaw82"
POST /jobs responde 202 antes do callback;
render/callback corre em background leve;
callback tem retry simples;
content_generation devolve template_key/template_id quando aplicável;
storage provider está abstraído;
E2E com PostgreSQL valida content/report/media kit;
Django cria Asset/ContentOutput/Report/MediaKit via callback;
coverage está configurado;
README e documento de estado estão actualizados;
build passa;
lint passa;
testes passam;
não há secrets nos logs/documentação.
```

---

# 9. Riscos

| ID           | Risco                                                         | Impacto | Mitigação                                                    |
| ------------ | ------------------------------------------------------------- | ------: | ------------------------------------------------------------ |
| RSK-HARD-001 | Background job falhar silenciosamente.                        |    Alto | Catch global, logs estruturados, testes de falha.            |
| RSK-HARD-002 | Retry duplicar callback e criar efeitos colaterais.           |    Alto | Confirmar idempotência no Django.                            |
| RSK-HARD-003 | PostgreSQL E2E exigir setup pesado.                           |   Médio | Docker Compose dedicado e checklist.                         |
| RSK-HARD-004 | Storage abstraction quebrar LocalStorage existente.           |   Médio | Manter testes antigos e adicionar factory.                   |
| RSK-HARD-005 | Coverage inicial bloquear evolução por thresholds agressivos. |   Baixo | Thresholds conservadores.                                    |
| RSK-HARD-006 | Echo de template_id não casar com modelos Django.             |   Médio | Confirmar contrato no backend_core antes de alterar payload. |

---

# 10. Resultado esperado

Ao concluir este backlog, o `content_renderer` deve passar de:

```text id="xry3lk"
MVP funcional com pendências técnicas
```

para:

```text id="4j43ix"
Serviço estabilizado para integração real controlada com o Backend Core
```

Estado esperado:

```text id="jsieoq"
Pronto para ambiente de integração: sim
Pronto para piloto técnico: sim
Pronto para produção: ainda depende de S3/R2, observabilidade e política operacional
```

---

# 11. Próximo passo após este backlog

Depois deste hardening, a próxima decisão deve ser uma destas:

```text id="3uqq7d"
1. Avançar para FastAPI Intelligence Engine;
2. Avançar para frontend mínimo de Campaign War Room;
3. Implementar storage S3/R2;
4. Melhorar qualidade visual dos templates.
```

Recomendação actual:

```text id="g5cj3l"
Após este hardening, avançar para FastAPI Intelligence Engine se o E2E Django ↔ Renderer estiver verde.
```
