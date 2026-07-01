# Prompt 10 — Avaliar impacto frontend

## Execução de 2026-07-01 07:23 (Atlantic/Cape_Verde)

### Estado da execução

`executado`

### Resumo objectivo

Foi comparada a CampaignAction API persistente do Backend Core com a
implementação actual da Campaign War Room. A análise confirmou que o frontend
ainda representa CampaignAction como uma projecção best-effort sobre
ContentPackRequest, Report e MediaKit:

- lista três endpoints e agrega os resultados no browser;
- usa o id e status dos artefactos como identidade/lifecycle da action;
- grava `recommendation_ref`, source, title, description e priority em metadata;
- faz matching pelo primeiro `recommendation_ref` encontrado;
- cria directamente os artefactos, sem persistir uma CampaignAction;
- mantém manual task, mark reviewed e dismiss indisponíveis pela antiga lacuna
  backend.

Foi criado um backlog frontend incremental para substituir esse desenho pelo
contrato real `/api/v1/campaign-actions/`. O plano cobre entity/DTO, API hooks,
paginação, diálogo, painel, recommendation state, reviewed/dismiss,
anti-duplicação, lifecycle, related artefacts, RBAC, segurança, testes e
validação real.

O backlog regista como gate de rollout a decisão sobre histórico. Um cutover
directo esconderia artefactos antigos que têm apenas
`metadata.recommendation_ref`, porque o Backend Core ainda não executou backfill
para CampaignAction.

Não foi alterado código runtime frontend ou backend.

### Ficheiros criados ou alterados

- Criado
  `frontend/docs/01_fundamentos/03_campaign_actions_backend_integration/01_backlog.md`.
- Criado este registo em
  `backend_core/docs/campaign_actions/resultados_execucao/prompt_10_avaliar_impacto_frontend_resultado.md`.

### Validações executadas e resultado

- Backlog backend, arquitectura CampaignAction e relatórios anteriores: lidos.
- Implementação actual inspeccionada em:
  - `src/entities/campaign-action/`;
  - `src/features/campaign-actions/`;
  - `src/widgets/campaign-actions-panel/`;
  - `CampaignWarRoomPage`, recommendation widgets e API client partilhado;
  - documentação/estado da fase frontend anterior.
- Implementação backend confrontada com serializers, viewset, filters e serviço
  de transições reais.
- Existência do novo backlog frontend: confirmada.
- Cobertura automática dos tópicos obrigatórios, endpoints, quatro relações,
  deduplicação, componentes afectados e itens incrementais: passou.
- Pesquisa por padrões de JWT, API key, Bearer token e credenciais atribuídas:
  nenhum secret real detectado.
- Browser: não usado.
- `python manage.py check`: não executado, porque nenhum runtime backend foi
  tocado.
- Build/lint frontend: não executados, porque nenhum código frontend foi
  alterado.

### Pendências, riscos ou próximo passo recomendado

- Decidir antes do cutover entre backfill backend, corte temporal explícito ou
  compatibilidade temporária com feature flag. Dual-read indefinido não é
  recomendado.
- Definir recuperação de sucesso parcial no fluxo de duas escritas: artefacto
  proprietário primeiro, CampaignAction relacionada depois.
- O frontend não tem actualmente test runner ou testes automatizados; o backlog
  separa a introdução de tooling do trabalho funcional.
- `recommendation_ref` passa a ser persistente na CampaignAction, mas continua
  opaca e pode ser derivada de dados instáveis quando a intelligence não fornece
  id.
- A paginação pode causar falso “não existe action” se matching/deduplicação
  depender apenas da primeira página; o backlog exige filtro exacto por ref.
- O frontend deve suportar múltiplas actions de tipos diferentes por
  recommendation; o match único actual não corresponde à regra backend.
- `asset_request` continua futuro e não deve ser apresentado como automatizado.
- Próximo passo recomendado: executar `FE-CAI-001 — Congelar contrato e rollout`
  e só depois iniciar a remodelação da entity/read path.
