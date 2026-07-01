# Prompt 08 — Documentar contrato Backend

## Execução de 2026-07-01 07:03 (Atlantic/Cape_Verde)

### Estado da execução

`executado`

### Resumo objectivo

Foi criado o documento de arquitectura e contrato da API CampaignAction com
base no código, migration, schema e testes actualmente implementados no Backend
Core. O documento descreve o model persistente, enums, lifecycle, endpoints,
payloads, filtros, paginação, RBAC, workspace scoping, validações
cross-workspace/cross-campaign, recommendations e relações com artefactos reais.

Ficou explicitamente registado que CampaignAction:

- é uma API pública autenticada do Backend Core;
- usa JWT e `X-Workspace-ID`;
- não usa `X-Internal-Token`;
- não chama Intelligence Engine nem renderers directamente;
- não cria automaticamente ContentPackRequest, ContentOutput, Report ou
  MediaKit.

Não foi alterado código runtime.

### Ficheiros criados ou alterados

- Criado `docs/campaign_actions/arquitectura_campaign_actions_backend.md`.
- Criado este registo em
  `docs/campaign_actions/resultados_execucao/prompt_08_documentar_contrato_backend_resultado.md`.

### Validações executadas e resultado

- Leitura do backlog, dos relatórios anteriores e da implementação actual:
  concluída.
- Verificação da existência do documento: passou.
- Verificação automática da presença das secções e termos contratuais
  obrigatórios, incluindo endpoints, recommendation fields, quatro relações de
  artefactos, operações semânticas e fronteira de segurança: passou.
- Geração e validação temporária do OpenAPI com o comando existente do projecto:
  passou; foram confirmados collection, detail e os endpoints `mark-reviewed`,
  `dismiss`, `cancel` e `complete`.
- Pesquisa por padrões de credenciais reais (JWT, API key, Bearer token e
  atribuições concretas de token/secret/password): nenhum valor real detectado.
  As referências a nomes de headers e secrets são exclusivamente proibições e
  documentação de segurança.
- `python manage.py check`: não executado, porque apenas documentação foi
  alterada e nenhum import ou ficheiro runtime foi afectado.
- Browser/servidor: não usados.

### Pendências, riscos ou próximo passo recomendado

- A migration continua por aplicar ao `db.sqlite3` local deste workspace devido
  à limitação de escrita já registada; foi validada em bases SQLite de teste e
  in-memory.
- Não existe backfill das antigas Campaign Actions projectadas sobre artefactos.
- Não existe sincronização automática entre o lifecycle da CampaignAction e o
  status dos artefactos relacionados.
- AuditEvent ainda não está integrado.
- A constraint parcial deve ser exercitada em PostgreSQL/CI ou staging.
- A suite global do Backend Core não foi executada nesta etapa documental; a
  suite dedicada da app mantém o último resultado registado de 56 testes
  aprovados.
- Próximo passo recomendado: validar e implementar a adaptação do frontend ao
  contrato persistente, incluindo paginação, mapeamento snake_case, criação de
  artefactos nos endpoints proprietários e plano de corte/backfill.
