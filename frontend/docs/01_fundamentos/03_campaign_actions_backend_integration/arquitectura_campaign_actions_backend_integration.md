# Arquitectura — Campaign Actions Backend Integration

> Fase: `03_campaign_actions_backend_integration`  
> Actualizado: 2026-07-01  
> Estado: implementação frontend concluída; validação E2E real bloqueada

## 1. Objectivo e fronteira

Esta fase substitui a antiga projecção browser-side de reports, media kits e content pack requests pela entidade persistente `CampaignAction` do Backend Core.

A fronteira obrigatória é:

```text
Frontend -> Backend Core -> serviços internos
```

O frontend não chama Intelligence Engine ou Content Renderer directamente e não envia credenciais internas.

## 2. Decisões de rollout

### DEC-01 — Histórico: corte temporal explícito

Foi escolhida a opção B:

- o Campaign Actions Panel mostra apenas CampaignActions persistentes;
- artefactos históricos sem CampaignAction continuam nos painéis proprietários;
- não existe backfill executado pelo browser;
- não existe dual-read, merge temporário ou feature flag de compatibilidade;
- CampaignActions reais já existentes na API permanecem visíveis.

O corte pode reduzir o histórico aparente do painel, mas não apaga dados.

### DEC-02 — Duas escritas

Para `content_pack`, `report_request` e `media_kit_request`:

```text
POST artefacto proprietário
  -> POST CampaignAction com related_*
```

Se a segunda escrita falhar, o frontend guarda o id do artefacto no estado de sucesso parcial, pesquisa por `campaign + recommendation_ref + action_type` e repete apenas o registo/link CampaignAction. Não há retry cego nem rollback destrutivo do artefacto.

### DEC-03 — Reviewed e dismiss

- uma decisão nova cria directamente `action_type=mark_reviewed` ou `action_type=dismiss`;
- dismiss exige `dismiss_reason`;
- numa operação sobre CampaignAction já identificada, o painel usa o endpoint semântico desse id;
- não existe persistência local ou metadata de artefacto como fonte de decisão.

### DEC-04 — Cardinalidade

Uma recommendation corresponde a `CampaignAction[]`. A deduplicação activa usa workspace + campaign + `recommendation_ref + action_type`; tipos diferentes podem coexistir.

## 3. Contrato persistente

O model frontend usa os nomes snake_case da API e representa:

```text
id, workspace, campaign,
recommendation_ref, recommendation_snapshot,
title, description, action_type, status, priority, source,
dismiss_reason, metadata,
related_content_pack_request, related_content_output,
related_report, related_media_kit,
created_by, completed_at, cancelled_at, created_at, updated_at
```

Enums:

| Campo | Valores |
| --- | --- |
| `action_type` | `content_pack`, `report_request`, `media_kit_request`, `manual_task`, `mark_reviewed`, `dismiss` |
| `status` | `pending`, `in_progress`, `completed`, `failed`, `dismissed`, `cancelled` |
| `priority` | `low`, `medium`, `high`, `urgent` |
| `source` | `recommendation`, `manual` |

`asset_request` não pertence ao contrato persistível.

Endpoints:

```text
GET/POST       /campaign-actions/
GET/PATCH      /campaign-actions/{id}/
POST           /campaign-actions/{id}/mark-reviewed/
POST           /campaign-actions/{id}/dismiss/
POST           /campaign-actions/{id}/cancel/
POST           /campaign-actions/{id}/complete/
```

Workspace é fornecido exclusivamente pelo cliente HTTP central; é removido defensivamente de bodies CampaignAction.

## 4. Read path

`CampaignActionsPanel` usa `useCampaignActions`, que executa um único GET paginado a `/campaign-actions/?campaign=...`.

O painel:

- não agrega endpoints proprietários;
- preserva `count`, `next`, `previous` e `results`;
- usa paginação visível de 25 registos;
- mantém loading, error, empty state e boundary própria na War Room;
- mostra campos canónicos, timestamps terminais, motivo de dismiss e FKs formais;
- trata FK null como artefacto indisponível/não ligado, sem fallback por metadata.

Reports, media kits, content outputs e content pack requests continuam nas respectivas entities/painéis.

## 5. Create path

### Sem artefacto

- `manual_task`: POST CampaignAction;
- `mark_reviewed`: POST CampaignAction, backend conclui como `completed`;
- `dismiss`: POST CampaignAction com motivo, backend conclui como `dismissed`.

### Com artefacto

| Action type | Primeiro POST | Relação no segundo POST |
| --- | --- | --- |
| `content_pack` | `/content-pack-requests/` | `related_content_pack_request` |
| `report_request` | `/reports/` | `related_report` |
| `media_kit_request` | `/media-kits/` | `related_media_kit` |

Os POST proprietários vivem nas respectivas entities. `campaign-action-api.ts` conhece apenas a API CampaignAction.

## 6. Matching e paginação exacta

O matching lê apenas `CampaignAction.recommendation_ref` top-level e agrupa todas as actions por ref.

Estados que bloqueiam nova action do mesmo tipo:

```text
pending | in_progress | completed
```

Estados que permitem nova tentativa:

```text
failed | dismissed | cancelled
```

O resumo por recommendation carrega até 100 items e explicita excedentes. Antes de criar, deduplicar ou recuperar concorrência, uma query exacta por ref + tipo carrega todas as páginas. O backend continua a autoridade final através da constraint de unicidade activa.

## 7. Recommendation snapshot

O snapshot é uma allowlist de:

```text
id, title, label, action, type, description, reason, priority, confidence
```

O builder:

- não copia o objecto intelligence completo;
- remove recursivamente chaves sensíveis conhecidas;
- limita profundidade, tamanho de colecções, campos e payload total;
- garante snapshot não vazio;
- normaliza priority, com default `medium`;
- limita `recommendation_ref` a 512 caracteres e prefere id da recommendation.

## 8. Reviewed, dismiss e lifecycle

O estado visual distingue reviewed (`mark_reviewed + completed`) de dismissed e cancelled.

No painel, a matriz exposta é:

| Estado actual | Operações |
| --- | --- |
| `pending` | complete, cancel, dismiss |
| `in_progress` | complete, cancel |
| `completed` | nenhuma |
| `failed` | retry como nova CampaignAction |
| `dismissed` | nenhuma |
| `cancelled` | nenhuma |

Não existe reopen. Retry de failed cria outro registo e preserva a action antiga.

## 9. Segurança e erros

O cliente central:

- injecta Bearer dinâmico e `X-Workspace-ID` através de providers;
- impede headers custom de substituir Authorization, workspace ou token interno;
- mapeia 400/422, 401, 403, 404, 502/503 e network errors para classes distintas;
- apresenta 403 como acesso negado;
- usa copy 404 neutra, sem reproduzir detalhes cross-workspace;
- não regista snapshot/payload integral em logs.

## 10. Testes

O projecto usa `node:test` nativo, sem dependências adicionais. Existem 14 testes para:

- labels/enums e priority;
- snapshot/ref defensivos;
- sanitização de workspace e headers;
- payloads reviewed/dismiss;
- matching múltiplo e deduplicação;
- reviewed/dismissed;
- lifecycle e retry-as-new;
- mapping de erros e copy 403/404;
- estrutura de partial success/retry sem recriação do artefacto.

Hooks React Query, dialogs montados e fetch real permanecem fora desta cobertura unitária.

## 11. Legado removido

O runtime actual não contém:

- agregação `Promise.allSettled` dos três endpoints;
- `RAW_STATUS_MAP`, `rawStatus`, `artifactKind` ou status `unknown`;
- id do artefacto usado como id CampaignAction;
- matching por `artifact.metadata.recommendation_ref`;
- `action_priority`/`action_description` em metadata;
- bloqueio global pelo primeiro match;
- copy de “operational artifacts” como fonte do painel.

`metadata` permanece apenas como campo auxiliar do contrato CampaignAction; não substitui campos canónicos nem relações.

## 12. Validação real e limites

A implementação passa lint, typecheck alternativo e 14 testes. O build completo é bloqueado no ambiente por `EPERM` ao escrever cache incremental/arrancar subprocessos Vite.

A validação E2E real do Prompt 13 ficou bloqueada:

- a porta 8000 servia uma API uvicorn alheia, não o Backend Core Django;
- schema/docs/admin esperados devolveram 404;
- o SQLite dev não pôde ser aberto;
- o browser integrado recusou localhost por política local.

Logo, esta arquitectura descreve o código implementado e testado estaticamente, não uma integração real certificada.
