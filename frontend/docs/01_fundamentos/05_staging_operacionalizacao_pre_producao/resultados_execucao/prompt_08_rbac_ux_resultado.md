# Prompt 08 — RBAC/UX mínimo — Resultado

**Data:** 2026-07-02
**Fase:** `05_staging_operacionalizacao_pre_producao` (STG-PRE-008)
**Âmbito:** validar (e, só onde seguro, melhorar) o RBAC/UX mínimo para o piloto pré-produção — affordances de escrita, honestidade de 403/404, sem inferir permissões no browser.
**Estado de execução:** `executado` — o contrato RBAC confirma que **não existem capabilities no frontend** (por desenho, documentado no próprio código); a arquitectura de erros já implementa correctamente o "backend é autoridade + UX honesta" que o backlog pedia. A única alteração de código foi uma melhoria pequena e segura de mensagens de falha em dois painéis que ainda não tinham sido tocados pelo Prompt 07.

---

## 1. Resumo objectivo

Esta fase confirma, mais do que implementa: o backlog previa duas hipóteses —
"se existirem capabilities reais, ocultar affordances" ou "se não existirem,
documentar a limitação e garantir 403 honesto". Inspeccionando o contrato e
o código, a segunda hipótese é a realidade actual do projecto, e já está
bem implementada:

- `GET /api/v1/auth/me/` (`MeView`/`UserSerializer`) devolve apenas o perfil
  (`id`, `email`, `full_name`, `is_staff`, …) — **nenhum campo de
  permissões, role ou capabilities**, nem por workspace nem global.
- O RBAC real vive inteiramente no Backend Core
  (`apps/rbac/permissions.py::HasWorkspacePermission`, `Role`/`Permission`/
  `RolePermission`), resolvido a partir do `X-Workspace-ID` + membership —
  nunca exposto ao frontend como uma lista de capabilities.
- `AuthProvider.tsx` já tem este comentário explícito no código (não escrito
  por mim, já existia): *"The Backend Core remains the source of truth for
  permissions; this only manages session presence, not business
  authorization (no RBAC here)."*
- Confirmado por grep: **zero** heurísticas de permissão no frontend
  (`isAdmin`, `canEdit`, `role ===`, `user.email === …`, etc.) — o único
  campo relacionado, `is_staff` (tipado em `entities/user/model.ts`), nunca
  é lido para decidir UI.

## 2. Contrato RBAC encontrado

| Camada | O que existe | O que NÃO existe |
|---|---|---|
| Backend — `auth/me` | Perfil do utilizador (sem workspace) | Permissões/roles/capabilities |
| Backend — RBAC | `Role`/`Permission`/`RolePermission`, `HasWorkspacePermission` por acção de view | Endpoint que exponha "as minhas permissões neste workspace" |
| Backend — `WorkspaceMember` | `role_key` exposto no endpoint de membros (para quem gere membros) | Um "meu papel" de leitura própria simplificada |
| Frontend | Nenhum estado de permissão | — |

Isto está conforme a regra do backlog **"não adicionar sistema RBAC novo se
não existir contrato"** — não foi inventado nenhum sistema de capabilities
no frontend.

## 3. Affordances de escrita mapeadas

| Affordance | Onde | Sempre visível? | Erro 403 tratado? |
|---|---|---|---|
| Create action | `CreateActionFromRecommendationDialog` | Sim | Sim — `resolveErrorPreset` → `Alert` inline |
| Mark reviewed / Complete | `CampaignActionLifecycleControls` | Sim (se estado permitir) | Sim — mesmo padrão |
| Dismiss | `DismissCampaignActionDialog` | Sim (se estado permitir) | Sim |
| Cancel | `CampaignActionLifecycleControls` (com `ConfirmDialog`) | Sim (se estado permitir) | Sim |
| Retry (como nova acção) | `CampaignActionLifecycleControls` | Sim (se acção `failed`) | Sim |

Todas passam por `resolveErrorPreset`/`ErrorState`, que já mapeia
`ForbiddenError` para "Access denied" e nunca finge sucesso. Não há
ocultação condicional de botões — é uma decisão consistente com "backend
continua autoridade" (o botão pode aparecer, mas a acção real só é honrada
pelo backend).

Achado relevante (já existente, não alterado): o fluxo de duas etapas
`useCreateActionFromRecommendation` (artefacto → CampaignAction) já trata o
caso em que a primeira chamada seria autorizada mas a segunda não —
`CampaignActionPartialSuccessError` mostra um aviso explícito ("Artifact
created; action not registered") em vez de reportar sucesso ou falhar
silenciosamente. Não precisou de alteração.

## 4. Tratamento de erros confirmado (400/401/403/404/502/503)

`shared/api/error-mapping.ts` + `shared/ui/states/error-presets.ts` +
`ErrorState.tsx` já cobrem os seis casos com telas dedicadas:

- `400/422` → `ValidationError` com `fieldErrors` inline por campo.
- `401` → `SessionExpired` (dedicado).
- `403` → `PermissionDenied` (dedicado, "Access denied" — nunca confundido com 404).
- `404` → `NotFoundState` (dedicado, mensagem genérica: *"This resource does
  not exist or is not available here."* — não distingue "não existe" de
  "existe mas não tens acesso", cumprindo simultaneamente "não esconder 403
  como 404" e "404 deve ser genérico").
- `502/503` → `ServiceUnavailable` com `onRetry`.

Confirmado nos testes de backend já existentes (re-executados nesta
sessão): `test_viewer_can_list_but_cannot_create` (403 real para o papel
`viewer`) e `test_detail_from_other_workspace_is_404` (404 genérico, sem
detalhe cross-workspace) — 5/5 passed.

## 5. Alteração de UX aplicada (Tarefa 7 do prompt)

O Prompt 07 (STG-PRE-007) só cobriu a visibilidade de falha de artefacto
**via `CampaignActionsPanel`** (`related_artifact_status`). Os painéis
dedicados `CampaignReportsPanel` e `CampaignMediaKitsPanel` — usados
directamente na War Room, fora do contexto de uma CampaignAction — ainda
não mostravam a causa da falha:

- **`CampaignMediaKitsPanel`**: um `MediaKit` sem estado `FAILED` próprio
  continuava a aparecer como `draft` mesmo com
  `metadata.generation_status === "failed"` já gravado — indistinguível de
  "ainda a processar". Corrigido: o badge mostra `failed` (derivado da
  metadata, mesma regra usada no backend/`CampaignActionSerializer`) e uma
  linha com a mensagem de erro.
- **`CampaignReportsPanel`**: `Report.status === "failed"` já aparecia
  correctamente, mas sem a mensagem de `metadata.error`. Adicionada.

Nenhum dos dois esconde ou substitui o estado real — apenas acrescenta
informação já existente na resposta da API que não estava a ser mostrada.

## 6. Validação real em browser (não só testes)

Com o Backend Core (`127.0.0.1:8100`) e o frontend (`preview_start`,
porta 5200) a correr, autentiquei como `ca014-dev@example.local`
(password efémera definida via shell, não persistida) e criei dois
registos de smoke no workspace CA014 (`Report` com `status=failed` e
`MediaKit` com `metadata.generation_status="failed"`, mesmo padrão de
dados de smoke já deixados por prompts anteriores nesta mesma War Room —
`STG09 smoke …`). Confirmado por inspecção do DOM real:

```text
"Iter8 Smoke Failed Report · Campaign Report · Renderer unavailable during submission (smoke test). · failed"
"Iter8 Smoke Failed Media Kit · 0 items · Renderer unavailable during submission (smoke test). · failed"
```

Sem erros na consola do browser. Login, navegação para a War Room e
renderização dos dois painéis com os novos textos confirmados ao vivo.

## 7. Ficheiros alterados

- `frontend/src/widgets/campaign-media-kits-panel/CampaignMediaKitsPanel.tsx` — `mediaKitDisplayStatus`/`mediaKitFailureMessage`.
- `frontend/src/widgets/campaign-reports-panel/CampaignReportsPanel.tsx` — `reportFailureMessage`.

Nenhuma alteração de backend nesta iteração (o contrato RBAC e o
tratamento de erros já estavam correctos; nada exigiu mudança de API).

## 8. Validações

- `npx tsc -b` (build) — sem erros.
- `npx eslint .` — sem avisos/erros.
- `npm test` (frontend) — 15/15 passed (inalterado; nenhum teste novo, a
  lógica acrescentada é trivial e já verificada ao vivo em browser real).
- `pytest apps/campaign_actions/tests/test_api.py -k "viewer or 404 or Access"` — 5/5 passed (403 honesto para `viewer`, 404 genérico cross-workspace).
- Grep de heurísticas inseguras de permissão no frontend (`isAdmin`,
  `canEdit`, `role ===`, `user.email ===`, …) — zero ocorrências; único
  campo relacionado (`is_staff`) nunca lido para decidir UI.
- Grep de bypass inseguro no backend (`is_superuser`, `.email ==`,
  `workspace.name ==`) — só usos legítimos do `is_superuser` nativo do
  Django (admin), nunca referenciado por `HasWorkspacePermission`.
- Smoke real em browser (secção 6) — sem falso sucesso, sem crash.

## 9. Limitações (documentadas, não corrigidas nesta fase)

- **Não existe endpoint "as minhas permissões neste workspace"** — se o
  produto decidir no futuro ocultar/desactivar affordances (em vez de
  confiar só no erro honesto pós-clique), isso exige um contrato novo no
  Backend Core primeiro (ex.: `GET /workspaces/{id}/members/me/` a devolver
  `role_key`+lista de `Permission.key`). Não implementado agora — o
  backlog proíbe explicitamente inventar isto sem decisão de produto.
  Enquanto isso, a UX actual (mostrar o botão, honrar o 403 no clique) é a
  abordagem segura recomendada pelo próprio backlog para este caso.
- **Retry (`Retry as new action`) fica sempre visível para uma acção
  `failed`**, mesmo que o utilizador não tenha permissão de escrita — o
  clique falha honestamente com 403; não há forma de o ocultar sem o
  contrato de capabilities acima.
- Dados de smoke (`Iter8 Smoke Failed Report`/`Media Kit`) ficam no
  workspace CA014 de dev, seguindo o mesmo padrão de artefactos de smoke
  já deixados por prompts anteriores (`STG09 smoke …`) — não são
  destrutivos nem tocam dados de outro workspace.

## 10. Riscos

- Sem capabilities no frontend, um utilizador sem permissão só descobre
  isso ao tentar a acção (UX ligeiramente pior que ocultar de antemão) —
  aceite como troca consciente nesta fase (nenhuma permissão inferida de
  forma insegura).
- A heurística `metadata.generation_status === "failed"` para `MediaKit`
  (usada agora em três sítios: `CampaignActionSerializer` no backend,
  `relatedArtifactStatusLabel` e agora `CampaignMediaKitsPanel`) é uma
  convenção, não um valor de enum garantido pelo schema — já assinalado
  como risco no relatório do Prompt 07 e na task de pesquisa
  `task_0dbdcedf`.

## 11. Próximo passo recomendado

1. Nenhuma acção urgente — o RBAC/UX mínimo para piloto está validado e
   conforme os critérios de aceitação do backlog.
2. Se o produto decidir investir em capabilities reais no frontend, o
   primeiro passo técnico é o contrato de "minhas permissões" no Backend
   Core (secção 9), não uma heurística no browser.
3. Seguir para STG-PRE-009 (E2E automatizado) conforme a ordem recomendada
   do backlog da fase.
