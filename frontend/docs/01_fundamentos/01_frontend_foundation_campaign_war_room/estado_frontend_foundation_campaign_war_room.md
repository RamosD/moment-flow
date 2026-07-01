# Estado da fase — Frontend Foundation & Campaign War Room MVP

**Componente:** `frontend`
**Data de fecho da fase:** 2026-06-26
**Última actualização:** 2026-06-30 (FE-016 — validação integrada real concluída)
**Fase:** FE-001 a FE-016 (backlog completo)

---

## 1. Resumo executivo

A fase está **concluída**: existe uma fundação de frontend modular (Feature-Sliced Design), o frontend consome exclusivamente o Backend Core, e a primeira experiência de produto — **Campaign War Room MVP** — está implementada, funcional, e **validada com dados reais** contra uma instância real do `backend_core` (FE-016).

`pnpm build` e `pnpm lint` passam sem avisos. `python manage.py check` passa sem issues. A validação integrada real (FE-016) confirmou login, workspaces, campanhas, War Room, intelligence em modo `dry_run`, cenário de falha `502 Bad Gateway` com tratamento `ServiceUnavailable` correcto, e recuperação — tudo contra o Backend Core real em `localhost:8000`, sem mocks.

Dois bugs reais foram encontrados e corrigidos durante a validação (FE-016): race condition no `WorkspaceProvider` e `CORS_ALLOW_HEADERS` sem `x-workspace-id`. Não há `X-Internal-Token`, segredos reais, ou chamadas directas ao Intelligence Engine / Content Renderer em lado nenhum do código.

**Estado:** pronto para piloto técnico controlado · **não** pronto para produção.

---

## 2. Escopo entregue

Conforme backlog §4.1, entregue nesta fase:

- Estrutura modular escalável (`app/shared/entities/features/widgets/pages`).
- Routing base (`react-router-dom`, rotas protegidas).
- App shell (`RootLayout`) e providers globais (`AppProviders`).
- API client central, tipado, com normalização de erros.
- Configuração de ambiente (`VITE_BACKEND_API_BASE_URL`).
- Auth/session foundation (login, logout, refresh, sessão expirada).
- Workspace context foundation (`X-Workspace-ID`, troca de workspace).
- Design system mínimo + componentes UI base.
- Estados loading/error/empty/sessão/permissões/workspace transversais.
- Tipos TypeScript para os contratos consumidos (defensivos onde o backend ainda é instável).
- Páginas de campanhas (lista, detalhe) e Campaign War Room MVP.
- Consumo do endpoint de intelligence (`POST /campaigns/{id}/intelligence/`).
- Visualização de scores, grade, moments, recommendations, warnings, explanations.
- Painéis de content outputs, reports e media kits (dados reais via Backend Core).
- Documentação de arquitectura (`arquitectura_frontend.md`).
- Validação build/lint e relatório final (FE-015).
- **Validação integrada real Frontend ↔ Backend Core, incluindo cenário de falha Intelligence (FE-016).**

Fora de escopo (backlog §4.2) — **não implementado, como esperado**: SSR, billing UI, edição/criação completa de campanhas, upload de media, geração real de assets, dashboards avançados, i18n avançado, testes E2E, deploy de produção. Nenhum destes foi necessário ou tentado nesta fase.

---

## 3. Estrutura criada

```text
src/
  app/        providers, router, layouts, config
  shared/     api, ui (+ states transversais), config, lib, types, styles
  entities/   campaign, content-output, report, media-kit, workspace, user, artist, track
  features/   auth, workspace-switching, campaign-intelligence
              (+ placeholders: campaign-actions, asset-generation-status, report-status)
  widgets/    campaign-header, campaign-score-card, campaign-moments-panel,
              campaign-recommendations-panel, campaign-assets-panel,
              campaign-reports-panel, campaign-media-kits-panel
              (+ placeholder: app-shell)
  pages/      dashboard, campaigns, campaign-detail, campaign-war-room,
              login, settings, not-found, ui-kit
```

Detalhe completo, com regras de dependência e exemplos de código, em [arquitectura_frontend.md](arquitectura_frontend.md).

---

## 4. Dependências instaladas

```text
react ^19.2.7
react-dom ^19.2.7
react-router-dom ^7.18.0
@tanstack/react-query ^5.101.1
```

Dev: `typescript ~6.0.2`, `vite ^8.1.0`, `eslint ^10.5.0` + `typescript-eslint ^8.61.0` + plugins React.

**Não instaladas** (decisão deliberada, sem necessidade comprovada nesta fase): `zod`, `react-hook-form`, `zustand`, `date-fns`, `tailwindcss`, framework de testes (Vitest/Playwright/Cypress).

---

## 5. Rotas

```text
/login                                       — público
/  (ProtectedRoute → RootLayout)
  ├─ /                                       — DashboardPage
  ├─ /campaigns                              — CampaignsPage
  ├─ /campaigns/:campaignId                  — CampaignDetailPage
  ├─ /campaigns/:campaignId/war-room          — CampaignWarRoomPage
  ├─ /settings                               — SettingsPage (placeholder)
  ├─ /ui-kit                                  — UiKitPage (demo dos componentes shared/ui)
  └─ *                                        — NotFoundPage
```

Validado em FE-016 com Backend Core real: sem sessão `/` redirecciona para `/login`; com sessão válida a War Room abre e carrega dados reais.

---

## 6. Auth / sessão

- Access token em memória; refresh token persistido em `localStorage` (limitação aceite — ver §9).
- `AuthProvider` gere estados `loading | authenticated | unauthenticated` + flag `sessionExpired`.
- `ProtectedRoute` redirecciona para `/login` quando não autenticado.
- 401 numa chamada autenticada limpa a sessão globalmente e marca `sessionExpired` → login mostra "Your session has expired."
- **Validado em FE-016 com Backend Core real:** `POST /api/v1/auth/token/` → 200 OK, tokens reais emitidos; `GET /api/v1/auth/me/` → 200 OK. Sessão estabelecida e mantida durante toda a sessão de validação. Sem erros de runtime ou exposição de detalhes internos.
- Sem RBAC no frontend — o Backend Core continua a ser a única fonte de permissões.

---

## 7. Workspace

- `WorkspaceProvider` carrega workspaces do utilizador autenticado, resolve o activo (preferência persistida, fallback ao primeiro), injecta `X-Workspace-ID` em todas as chamadas via provider registado.
- Troca de workspace invalida as queries dependentes (mantém apenas a lista de workspaces em cache).
- Sem workspace activo, as páginas relevantes mostram `WorkspaceRequiredState` (não um erro genérico).
- **Validado em FE-016 com Backend Core real:** `GET /api/v1/workspaces/?page_size=100` → 200 OK. Workspace activo resolvido, `X-Workspace-ID` injectado correctamente. Race condition encontrada e corrigida (sincronização da ref movida para `useLayoutEffect`).
- Troca de workspace com múltiplos workspaces reais não exercida (só existe um workspace dev neste ambiente; comportamento de troca está implementado e foi revisto por código).

---

## 8. API client

- Porta única de rede: `shared/api/client.ts`, aponta exclusivamente a `VITE_BACKEND_API_BASE_URL`.
- Injecta `Authorization: Bearer` e `X-Workspace-ID` via providers registados; **bloqueia activamente** qualquer tentativa de enviar `X-Internal-Token`.
- Normaliza erros HTTP em `ApiError` + 6 subclasses (`Unauthorized/Forbidden/NotFound/Validation/ServiceUnavailable/Network`).
- **Validado em FE-016 com tráfego real:** todos os pedidos observados na rede do browser foram exclusivamente para `localhost:8000` (Backend Core). Nenhuma chamada ao Intelligence Engine (`:8001`) ou Content Renderer (`:8002`). Nenhum header `X-Internal-Token` enviado. 502 real mapeado correctamente para `ServiceUnavailableError` → UI "Service unavailable".

---

## 9. Campaign War Room

- `pages/campaign-war-room/CampaignWarRoomPage.tsx` compõe: breadcrumb, `CampaignHeader`, `IntelligenceSummary` + `WarningsPanel`, `CampaignScoreCard`, `CampaignMomentsPanel`, `CampaignRecommendationsPanel`, `ExplanationsPanel`, e os painéis de `Assets`/`Reports`/`Media Kits`.
- Falhas parciais não bloqueiam a página toda: se só a intelligence falhar, o header e os painéis de outputs continuam visíveis.
- Tipos de `result.scores`/`moments`/`recommendations` são defensivos (campos opcionais + index signature), reflectindo um schema OpenAPI ainda livre nesse ponto (ver limitação FE-PDEC-005).
- **Validada em FE-016 com dados reais:** War Room abre com campanha "FE-016 Dev Campaign", Campaign Header visível, intelligence em `source=dry_run` com badge "Dry run" e aviso honesto, Content Outputs/Reports/Media Kits com estados vazios honestos. Cenário de falha (502) validado: Campaign Header permanece visível, intelligence mostra "Service unavailable" com "Try again", painéis de outputs continuam independentes.

---

## 10. Validações executadas

| Verificação | Comando/Acção | Resultado |
| --- | --- | --- |
| Build | `pnpm build` (`tsc -b && vite build`) | ✅ Passa. `dist/index.html` 0.45 kB, JS 356.73 kB (gzip 110.80 kB), CSS 16.50 kB. 184 módulos. `dist/` removido após verificação. |
| Lint | `pnpm lint` (`eslint .`) | ✅ Passa, exit 0, sem avisos. |
| Backend check | `python manage.py check` | ✅ "System check identified no issues (0 silenced)." |
| Testes automatizados | — | Não existem (decisão FE-PDEC-004). Não aplicável. |
| Arranque local | `pnpm dev` via preview server (porta 5173) | ✅ App sobe sem erros de runtime. |
| Login real | `POST /api/v1/auth/token/` | ✅ 200 OK. Sessão real estabelecida. |
| Auth me | `GET /api/v1/auth/me/` | ✅ 200 OK. |
| Workspaces | `GET /api/v1/workspaces/?page_size=100` | ✅ 200 OK. Workspace activo resolvido. |
| Campanhas | `GET /api/v1/campaigns/` | ✅ 200 OK (após correcção de race condition + CORS). |
| Detalhe campanha | `GET /api/v1/campaigns/{id}/` | ✅ 200 OK. |
| War Room | `/campaigns/{id}/war-room` | ✅ Renderiza Campaign Header, scores, moments, recommendations. |
| Intelligence (normal) | `POST /api/v1/campaigns/{id}/intelligence/` | ✅ 200 OK, `source=dry_run`, badge + aviso honestos. |
| Intelligence (falha) | `POST /api/v1/campaigns/{id}/intelligence/` com upstream indisponível | ✅ 502 Bad Gateway → UI mostra "Service unavailable" com "Try again". Campaign Header e outputs independentes. |
| Retry manual | Clique em "Try again" | ✅ Novo request real ao Backend Core (request_id distinto confirmado nos logs Django). |
| Recuperação | `.env` revertido + backend reiniciado + reload | ✅ 200 OK, `event=dry_run`, UI no estado normal. |
| Content Outputs | `GET /api/v1/content-outputs/?campaign={id}` | ✅ 200 OK, lista vazia → "No content outputs yet". |
| Reports | `GET /api/v1/reports/?campaign={id}` | ✅ 200 OK, lista vazia → "No reports yet". |
| Media Kits | `GET /api/v1/media-kits/?campaign={id}` | ✅ 200 OK, lista vazia → "No media kits yet". |
| Segurança: `X-Internal-Token` | Grep `src/` + inspecção de rede real | ✅ Ausente do tráfego; única referência é o código de bloqueio/sanitização em `shared/api/client.ts`. |
| Segurança: chamadas directas IE/Renderer | Grep `src/` + inspecção de rede real | ✅ Zero ocorrências de chamadas directas. Todos os pedidos do browser foram a `:8000`. |

> Dois bugs reais foram encontrados e corrigidos durante a validação (FE-016) — ver relatório [`resultados/prompt_16_validacao_integrada_backend_core_real.md`](resultados/prompt_16_validacao_integrada_backend_core_real.md).

---

## 11. Limitações

- Refresh token persistido em `localStorage` — exposto a XSS; aceite para piloto controlado, não para produção (FE-PDEC-003).
- Sem refresh-and-retry transparente: um 401 numa chamada autenticada termina a sessão directamente, sem tentar renovar e repetir o pedido original.
- Tipos de intelligence (`scores`/`moments`/`recommendations`) são best-effort — o schema do Intelligence Engine ainda define esses campos como objectos/arrays livres (FE-PDEC-005).
- Sem testes automatizados (unit/integration/E2E).
- Sem RBAC no frontend, sem i18n, sem observabilidade/tracking de erros em produção.
- Sem validação cross-browser ou de performance.
- Workspace switching com múltiplos workspaces reais não exercido nesta sessão (só existe um workspace dev; fluxo está implementado e revisto por código).
- 403 (Forbidden) real não exercido (sem segundo utilizador com permissões restritas no ambiente dev; mapeamento de erro está implementado e coberto por código).
- Gatilho do 502 foi "upstream rejeitou credenciais" (`403 unauthorized_internal_request` do processo em `:8001`), não "ligação recusada" — resultado observado pelo frontend (`502 → ServiceUnavailable`) é idêntico, mas documentado com honestidade no relatório FE-016.
- Retry automático do TanStack Query não observado em tempo real durante a validação automatizada (Chrome throttle de timers em tabs background); comportamento de retry via "Try again" manual confirmado e funcional.

---

## 12. Riscos

| Risco | Estado | Nota |
| --- | --- | --- |
| Contratos reais do Backend Core diferirem do assumido (FE-RSK-004) | **Mitigado** | Confirmado via OpenAPI schema (FE-001) + validação real com dados reais em FE-016. Dois divergências (race condition + CORS) encontradas e corrigidas. |
| `X-Internal-Token` ir parar ao browser (FE-RSK-003) | Mitigado | Bloqueio activo no cliente + grep limpo + inspecção de rede real em FE-016. Reverificar sempre que `client.ts` for alterado. |
| Erros 502/503 do ecossistema não tratados na UI (FE-RSK-009) | **Mitigado** | Validado com 502 real do Backend Core em FE-016: `ServiceUnavailableError` → "Service unavailable" + "Try again". |
| Frontend declarar piloto sem validar com Backend Core real (FE-RSK-010) | **Fechado** | Validação integrada real concluída em FE-016 (2026-06-26): login, workspaces, campanhas, War Room, intelligence normal, cenário 502, retry e recuperação — todos com Backend Core real em `:8000`. |
| Auth/workspace subestimados (FE-RSK-005) | Mitigado | Providers dedicados desde o início (FE-007/FE-008); race condition encontrada e corrigida em FE-016. |
| Versões recentes de React/Vite/TS causarem incompatibilidades (FE-RSK-008) | Mitigado | Build/lint validados em cada prompt; sem incompatibilidades encontradas. |

---

## 13. Pronto para piloto técnico?

**Sim.** A fundação está completa, modular, e validada ponta-a-ponta com Backend Core real (FE-016): login real, workspaces, War Room com dados reais, cenário de falha da intelligence com tratamento correcto (`ServiceUnavailable`), e recuperação. FE-RSK-010 fechado.

## 14. Pronto para produção?

**Não.** Faltam, no mínimo (backlog §15.2): UX refinada, testes E2E, refresh-and-retry transparente, observabilidade/tracking de erros, feature flags maduras, deploy, gestão segura de ambiente (segredos fora de `.env` local), validação cross-browser, performance budget.

---

## 15. Próximos passos

1. Avaliar a próxima fase entre as opções do backlog §15.1: campaign actions, geração de content packs a partir de recomendações, UI completa de reports/media kits, dashboard executivo, hardening visual, testes E2E, deploy de staging.
2. Se avançar para produção: mover refresh token para cookie `httpOnly`/`Secure`/`SameSite`, implementar refresh-and-retry transparente, adicionar testes (mínimo: Vitest para hooks/lógica crítica), e observabilidade de erros no browser.
3. Reavaliar tipos de `CampaignIntelligenceResult` (scores/moments/recommendations) quando o contrato do Intelligence Engine estabilizar (FE-PDEC-005).
4. Exercitar workspace switching com múltiplos workspaces reais quando o ambiente de piloto o permitir.
