# Prompt 06 — Suporte a Mark Reviewed / Dismiss

> Fase: `02_campaign_actions_recommendation_to_execution`
> Backlog de referência: `01_backlog.md` (CA-010, CA-PDEC-005)
> Relatórios anteriores: prompt_01, prompt_02, prompt_03, prompt_04, prompt_05

---

## Execução 2026-06-30 (Iteração 01)

### Estado da execução

**Lacuna documentada — sem alterações runtime** (CA-010 confirmado como indisponível;
backend sem qualquer suporte a reviewed/dismissed; código existente já é honesto;
lint e build verdes; sem browser, conforme instrução).

### Resumo objectivo

Esta iteração executou investigação directa do Backend Core para confirmar se existe
suporte real a `mark_reviewed` ou `dismiss` para recommendations ou qualquer dos 3
artefactos que servem de base às Campaign Actions. O resultado é inequívoco:

**O Backend Core não suporta `reviewed` nem `dismissed` em nenhum contrato disponível.**

As reasons são múltiplas e complementares:

1. **Recommendations não são persistidas**: a intelligence do Backend Core recalcula
   as recommendations a cada chamada a `POST /campaigns/{id}/intelligence/`. Não
   existe tabela de recommendations, não há id persistente, não há endpoint de update
   para recommendations.

2. **Os 3 artefactos reais não têm status reviewed/dismissed**:
   - `Report.Status`: `QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`, `ARCHIVED` —
     sem `reviewed`, sem `dismissed`.
   - `MediaKit.Status`: `DRAFT`, `GENERATED`, `PUBLISHED`, `ARCHIVED` — sem
     `reviewed`, sem `dismissed`.
   - `ContentPackRequest.Status`: `DRAFT`, `QUEUED`, `PROCESSING`,
     `PARTIALLY_COMPLETED`, `COMPLETED`, `FAILED`, `CANCELLED`, `EXPIRED` — sem
     `reviewed`, sem `dismissed`.

3. **Sem viewset de acções custom**: nenhum dos 3 viewsets expõe acções Django REST
   Framework como `@action(detail=True)` para `mark_reviewed` ou `dismiss`. Os
   métodos HTTP disponíveis são: Reports (GET/POST/PATCH), MediaKits (GET/POST/PATCH),
   ContentPackRequests (GET/POST — **sem PATCH**).

4. **Sem app de actions/tasks**: o `config/urls.py` não regista nenhuma app de
   `campaign-actions`, `tasks`, `action-items`, `recommendations` nem nada equivalente.
   As apps activas são: accounts, workspaces, core, catalogue, campaigns, content,
   links, billing, reports, notifications, integrations_bridge.

### Decisão técnica (per backlog CA-010 + CA-PDEC-005)

O backlog especifica explicitamente:
> "Se não suportar: não persistir falso estado; mostrar a opção indisponível **ou**
> omitir a acção."

Decisão: **omitir as affordances** de Mark Reviewed / Dismiss.

Fundamento:
- Recommendations são transientes (recalculadas) — não há entidade backend a
  "marcar" nem id estável que sobreviva entre sessões.
- Mostrar botões disabled "Mark reviewed" / "Dismiss" sem poder persistir
  criaria expectativa de uma funcionalidade que não pode ser cumprida agora nem
  com workarounds de metadata (a recommendation referenciada pode desaparecer ou
  mudar de posição/título entre recálculos).
- A omissão é a forma mais honesta: não cria falsa expectativa, não exige UI
  de indisponibilidade que geraria confusão.

### Código existente já é honesto

O frontend já trata esta limitação correctamente desde o prompt_02/03:

**`entities/campaign-action/model.ts`** — `CAMPAIGN_ACTION_CAPABILITIES`:
```ts
mark_reviewed: {
  type: 'mark_reviewed',
  supported: false,
  endpoint: null,
  updatable: false,
  reason: 'Recommendations are recomputed, not persisted; review state cannot be stored.',
},
dismiss: {
  type: 'dismiss',
  supported: false,
  endpoint: null,
  updatable: false,
  reason: 'Recommendations are recomputed, not persisted; dismissal cannot be stored.',
},
```

**`features/campaign-actions/action-type-options.ts`** — `SUPPORTED_ACTION_TYPE_OPTIONS`
exclui `mark_reviewed` e `dismiss`; `ACTION_TYPE_OPTIONS` inclui-os com `disabled: true`
e "(unavailable)" no label.

**`features/campaign-actions/CreateActionFromRecommendationDialog.tsx`** — usa apenas
`SUPPORTED_ACTION_TYPE_OPTIONS` no Select de tipo de acção → estes tipos nunca aparecem
no modal de criação.

**`features/campaign-actions/recommendation-action-match.ts`** — `matchRecommendationAction`
só encontra acções cujo `recommendationRef` coincide e cujo tipo seja um dos 3 suportados
→ não pode devolver uma match com type `mark_reviewed` ou `dismiss` porque estes nunca
são criados.

### Ficheiros criados ou alterados

**Nenhum ficheiro de runtime foi alterado.** O código existente já é
suficientemente honesto. Esta iteração não introduz mocks, stubs, disabled buttons
adicionais nem estado falso.

Criado:
- `docs/.../resultados_execucao/prompt_06_reviewed_dismissed_resultado.md` (este
  ficheiro).

### Validações executadas e resultado

- ✅ `pnpm lint` → `eslint .` sem erros nem avisos (sem alterações, resultado
  idêntico ao prompt_05).
- ✅ `pnpm build` → `tsc -b && vite build`, 230 módulos transformados, 387ms, sem
  erros de tipo.
- ✅ Investigação directa do Backend Core:
  - `apps/reports/models.py` inspeccionado — sem `reviewed`/`dismissed`.
  - `apps/content/models.py` inspeccionado — sem `reviewed`/`dismissed`.
  - `apps/campaigns/models.py` inspeccionado — sem recomendações persistentes.
  - `apps/reports/views.py` inspeccionado — sem `@action` custom para reviewed/dismiss.
  - `apps/content/views.py` inspeccionado — sem `@action` custom para reviewed/dismiss.
  - `config/urls.py` inspeccionado — sem app de actions/tasks/recommendations.
- ✅ Greps de segurança: `internal-token` aparece apenas no guard do `apiClient`;
  sem referências a IE/Renderer em `src/`.
- ➖ Browser — **não usado**, conforme instrução.

### Fundamento adicional — por que não usar metadata como workaround

Uma alternativa possível seria gravar `{ reviewed: true, dismissed: true, dismiss_reason: "..." }` no `metadata` de um dos 3 artefactos. Esta abordagem foi **descartada** pelas seguintes razões:

1. **Sem entidade para guardar**: para gravar "reviewed" numa recommendation precisava
   de um artefacto backend associado a essa recommendation. Uma recommendation não tem
   id persistente nem artefacto associado por defeito.
2. **Criação forçada de artefacto para "marcar"**: criar um `Report` vazio apenas para
   guardar um estado de review seria fake persistence — exactamente o que o backlog
   proíbe ("não fingir persistência").
3. **Sem rastreabilidade**: o `recommendation_ref` que liga recommendation a artefacto
   já é best-effort; forçar a criação de um artefacto só para guardar estado de review
   não resolve o problema de rastreabilidade, adiciona ruído no painel de actions.

### Pendências, riscos e próximo passo recomendado

- **CA-010 (mark reviewed / dismiss) — confirmado indisponível**: requer backlog
  complementar no Backend Core (ver CA-PDEC-005 e CA-PDEC-006). Não implementável
  sem uma das seguintes alterações backend:
  - Entidade `Recommendation` persistida (nova tabela) com campo `status` / `dismissed_reason`.
  - Campo `reviewed`/`dismissed` num endpoint por campanha dedicado.
  - Endpoint de `campaign-actions` com `mark_reviewed`/`dismiss` como tipos suportados.
- **CA-PDEC-005 — resolvido como "não persistir"**: CA-PDEC-005 perguntava se
  "Mark Reviewed/Dismiss deve persistir?". Resposta: só persistir se Backend Core
  suportar. O Backend Core não suporta → não persistir. Decisão fechada.
- **CA-011 (ligar acções a outputs existentes)** — ainda não abordado; só possível
  via metadata hoje. Pendente.
- **CA-013 (doc de arquitectura)** e **CA-015 (relatório final da fase)** — por fazer.
- **CA-014 (validação integrada real)** — bloqueada até o utilizador solicitar
  iteração com browser habilitado.
- **Nota de produto (CA-PDEC-006)**: se rastreabilidade de reviewed/dismissed for
  requisito firme do piloto, backlog complementar no Backend Core é a única via honesta.
