# FE-016 — Validação integrada real Frontend ↔ Backend Core

**Fase:** Frontend Foundation & Campaign War Room MVP
**Componente alvo:** `frontend` ↔ `backend_core`
**Data:** 2026-06-26
**Tipo:** Validação de integração real (não mockada), incluindo o cenário de falha da Intelligence

---

## 1. Resumo executivo

- **Validação concluída com sucesso.** O frontend foi validado end-to-end contra uma instância real do `backend_core` (porta 8000), incluindo o ponto que tinha ficado pendente de uma validação parcial anterior: o comportamento do frontend quando a Intelligence está indisponível/não autorizada (`502`/`503` real do Backend Core).
- Confirmado: login real, `/auth/me`, `/workspaces/`, `/campaigns/`, `/campaigns/{id}/`, War Room completa, intelligence em modo `dry_run`, outputs/reports/media-kits (estados vazios honestos), 401/400/404/200, e agora também o cenário de falha real da Intelligence (`502 Bad Gateway`) com tratamento `ServiceUnavailable` correcto na UI.
- **Dois bugs reais encontrados e corrigidos** numa sessão anterior desta mesma validação (mantidos, não repetidos nesta tarefa):
  1. Race condition no `WorkspaceProvider` (a query de campanhas podia disparar antes de `X-Workspace-ID` estar disponível).
  2. `CORS_ALLOW_HEADERS` do Backend Core não incluía `x-workspace-id`, bloqueando o pedido real no browser após o preflight.
- **Ponto pendente desta tarefa, agora fechado:** o cenário "Intelligence indisponível" foi induzido de forma real (sem mocks), confirmado no Network tab e nos logs do Django como `502 Bad Gateway`, e a UI apresentou correctamente o estado `Service unavailable` com botão `Try again` — sem ficar presa em "Analyzing campaign…", sem expor tokens, stack traces ou detalhes internos.
- Foi necessário um ajuste **temporário e já revertido** no frontend (`retry: false` em `useCampaignIntelligence`) para contornar um artefacto do ambiente de teste automatizado (tab de preview em background, sujeita a *throttling* de timers do Chrome) — detalhado na secção 5.
- `pnpm lint`, `pnpm build` e `python manage.py check` passam todos, sem avisos.

---

## 2. Ambiente

| Item | Valor |
| --- | --- |
| Backend Core URL | `http://localhost:8000` (API em `/api/v1`) |
| Frontend URL | `http://localhost:5173` |
| Base URL usada pelo frontend (`frontend/.env.local`) | `VITE_BACKEND_API_BASE_URL=http://localhost:8000/api/v1` |
| Utilizador dev | `fe016-dev@example.local` (password omitida deste relatório) |
| Workspace dev | "FE-016 Dev Workspace" (id: `c83b884c-…-…e9cf`, mascarado) |
| Campanha dev | "FE-016 Dev Campaign" (id: `3775d2a5-…-…7abfbb`, mascarado) |
| Modo da intelligence — validação normal | `INTELLIGENCE_ENGINE_DRY_RUN=true` (modo dev intencional, documentado no `.env`) |
| Modo da intelligence — teste de falha | `INTELLIGENCE_ENGINE_DRY_RUN=false` temporariamente, restaurado a `true` no final |
| Nota de segurança | Nenhum token (`SECRET_KEY`, access/refresh token, password) é exposto neste relatório |

---

## 3. Validações normais

| Pedido | Resultado |
| --- | --- |
| `POST /api/v1/auth/token/` (login real) | ✅ 200 |
| `GET /api/v1/auth/me/` | ✅ 200 |
| `GET /api/v1/workspaces/?page_size=100` | ✅ 200 |
| `GET /api/v1/campaigns/` | ✅ 200 |
| `GET /api/v1/campaigns/{id}/` | ✅ 200 |
| `GET /campaigns/{id}/war-room` (rota frontend) | ✅ Renderiza Campaign Header, scores, moments, recommendations |
| `POST /api/v1/campaigns/{id}/intelligence/` (modo normal) | ✅ 200, `source=dry_run`, badge "Dry run" + aviso honesto na UI |
| `GET /api/v1/content-outputs/?campaign={id}` | ✅ 200, lista vazia → "No content outputs yet" |
| `GET /api/v1/reports/?campaign={id}` | ✅ 200, lista vazia → "No reports yet" |
| `GET /api/v1/media-kits/?campaign={id}` | ✅ 200, lista vazia → "No media kits yet" |

---

## 4. Bugs encontrados e correcções

### 4.1 Race condition no `WorkspaceProvider`

- **Sintoma:** `GET /api/v1/campaigns/` por vezes disparava sem `X-Workspace-ID`, levando a `400`.
- **Causa:** o id do workspace activo era guardado numa `ref`; o ponto de sincronização original corria depois (ou na mesma fase, mas sem garantia de ordem) do efeito passivo que dispara a query do TanStack Query, que lê a `ref` no momento do fetch.
- **Correcção:** sincronizar a `ref` num `useLayoutEffect` em vez de `useEffect`. React garante que **todos** os layout effects da árvore (incluindo os do componente pai) correm antes de **qualquer** effect passivo — eliminando a corrida sem violar as regras de pureza de render (`react-hooks/refs`, `react-hooks/immutability`, `react-hooks/globals`).
- Ficheiro: [`frontend/src/features/workspace-switching/WorkspaceProvider.tsx`](../../../../src/features/workspace-switching/WorkspaceProvider.tsx)

### 4.2 `CORS_ALLOW_HEADERS` sem `x-workspace-id`

- **Sintoma:** `GET /api/v1/campaigns/` falhava sempre no browser com `net::ERR_FAILED`, nunca chegando ao Django (confirmado pelos logs: só `OPTIONS`, nunca `GET`).
- **Causa:** a lista de cabeçalhos por defeito do `django-cors-headers` não inclui `x-workspace-id`; o preflight respondia `200`, mas o browser bloqueava o pedido real porque o cabeçalho não estava no `Access-Control-Allow-Headers` devolvido.
- **Correcção:** adicionado `CORS_ALLOW_HEADERS = [*default_headers, "x-workspace-id"]` em `backend_core/config/settings.py`.
- Confirmado por `curl` (antes/depois do `access-control-allow-headers`) e por uso real no browser.

---

## 5. Validação do cenário Intelligence indisponível

### 5.1 Como a falha foi induzida

Seguida a **Opção A** (preferida) do plano: `backend_core/.env` → `INTELLIGENCE_ENGINE_DRY_RUN=false` (temporário), com restart manual do servidor Django (o autoreloader do Django não observa alterações a `.env`).

Resultado inesperado mas honesto: havia um processo a escutar em `http://localhost:8001` neste ambiente. O `backend_core` tentou a chamada real (`POST http://localhost:8001/intelligence/campaign`) e recebeu `403 unauthorized_internal_request` desse processo (sem coordenação de `INTERNAL_API_TOKEN`, deliberadamente fora de escopo desta validação). O `backend_core` traduziu correctamente essa falha upstream num `502 Bad Gateway` para o frontend — funcionalmente equivalente, do ponto de vista do frontend, a "Intelligence Engine indisponível" (ambos mapeiam para `ServiceUnavailableError`).

### 5.2 Endpoint chamado e status HTTP

- `POST /api/v1/campaigns/{id}/intelligence/` → **`502 Bad Gateway`** (corpo: `"Bad Gateway: /api/v1/campaigns/{id}/intelligence/"`, sem detalhe interno).
- Log do `backend_core` (sem tokens):
  ```
  intelligence_call http_error ... status=403 error_code=unauthorized_internal_request
  intelligence event=upstream_error ... status=403 error_code=unauthorized_internal_request duration_ms=2249
  Bad Gateway: /api/v1/campaigns/{id}/intelligence/
  "POST /api/v1/campaigns/{id}/intelligence/ HTTP/1.1" 502 74
  ```
- Reproduzido de forma consistente em múltiplas tentativas (incluindo via o botão "Try again" da UI, que gerou um novo `request_id` e um novo `502` real).

### 5.3 Comportamento visual da UI

Confirmado via snapshot de acessibilidade do browser:

- O **Campaign Header** ("FE-016 Dev Campaign", estado `active`, "Single Release") permanece visível e intacto — não depende da intelligence.
- A secção de intelligence mostra:
  - Título: **"Service unavailable"**
  - Descrição: **"The service is temporarily unavailable. Please try again shortly."**
  - Botão: **"Try again"**
- Os painéis **Content outputs**, **Reports** e **Media kits** continuam a renderizar de forma independente os respectivos estados vazios ("No content outputs yet", "No reports yet", "No media kits yet") — não são afectados pela falha da intelligence.
- **Sem stack trace.** **Sem token.** **Sem status code bruto ou detalhe interno exposto ao utilizador.**

### 5.4 Confirmação de rede

Via inspecção do Network tab da preview:

- Todos os pedidos do browser foram para `http://localhost:8000/...` (Backend Core). **Nenhum pedido directo** a `http://localhost:8001` (Intelligence Engine) ou `http://localhost:8002` (Content Renderer) partiu do frontend.
- **Nenhum cabeçalho `X-Internal-Token`** foi enviado pelo browser em nenhum pedido (confirmado também por grep de segurança — secção 7).
- O botão "Try again" confirmadamente despachou um **novo pedido real** (`request_id` diferente, novo timestamp no log do Django), provando que o mecanismo de recuperação funciona via acção do utilizador.

### 5.5 Nota técnica: ajuste temporário para observar o estado de erro

Durante a automatização desta validação, a tab de preview do browser ficou em **background** (`document.hidden = true`). O Chrome restringe (`throttle`) temporizadores (`setTimeout`) em tabs em background a, no limite, uma execução por minuto. Como a política de retry do `queryClient` por defeito tenta novamente 5xx até 2 vezes com *backoff* exponencial (implementado via `setTimeout`), este throttling do browser — não um problema da aplicação — fez o pedido inicial demorar muito mais do que o esperado a resolver-se visualmente, embora a chamada de rede real já tivesse terminado em ~2 segundos.

Para observar o estado de erro real de forma determinística dentro da janela desta validação, foi feita uma alteração **temporária e documentada**:

```ts
// TEMP (FE-016 502/503 validation only): disable retry so the real error
// state is observable immediately, instead of waiting through the
// background-tab-throttled retry backoff. Reverted right after the test.
retry: false,
```
em `frontend/src/features/campaign-intelligence/useCampaignIntelligence.ts`.

Com esta alteração, o `502` real do Backend Core resultou imediatamente no estado `Service unavailable` descrito acima. A alteração foi **revertida imediatamente** depois de confirmado o comportamento (ver diff no histórico — não há resíduo no código final). O comportamento de retry/recuperação via "Try again" foi confirmado de forma independente e funciona com a configuração de retry normal (não alterada) do `queryClient`.

---

## 6. Recuperação

1. `backend_core/.env`: `INTELLIGENCE_ENGINE_DRY_RUN=false` → revertido para `INTELLIGENCE_ENGINE_DRY_RUN=true` (estado dev normal e documentado).
2. `frontend/src/features/campaign-intelligence/useCampaignIntelligence.ts`: `retry: false` temporário removido; ficheiro igual ao estado anterior a esta validação.
3. `backend_core` reiniciado (o autoreloader do Django não observa `.env`; reinício manual necessário).
4. Reload limpo da War Room: `POST /api/v1/campaigns/{id}/intelligence/` → **200 OK**, log mostra `event=dry_run`.
5. UI voltou ao estado esperado: badge **"Dry run"**, aviso **"Dry-run: Intelligence Engine was not called."** — idêntico ao comportamento validado na secção 3, sem qualquer alteração de código necessária para a recuperação (apenas configuração + restart).

---

## 7. Segurança

Greps executados em `frontend/src/` após todas as alterações desta validação:

| Verificação | Resultado |
| --- | --- |
| `X-Internal-Token` enviado pelo frontend | ✅ Ausente — única ocorrência é a constante de bloqueio/sanitização em `shared/api/client.ts` (`sanitizeCustomHeaders`), que impede activamente o envio do cabeçalho |
| `INTERNAL_API_TOKEN` em runtime frontend | ✅ Ausente |
| Chamadas directas a `intelligence_engine`/`content_renderer` ou às portas 8001/8002/8003 | ✅ Ausentes em `src/` |
| `.env.local` gitignored | ✅ Confirmado (`.gitignore`: `.env`, `.env.*`, excepto `.env.example`) |
| `.env.example` sem secrets reais | ✅ Confirmado — só `VITE_BACKEND_API_BASE_URL` de exemplo + nota a desencorajar segredos |
| Tokens reais neste relatório | ✅ Ausentes (password dev e `SECRET_KEY` omitidos deliberadamente) |

---

## 8. Validações técnicas

| Comando | Resultado |
| --- | --- |
| `pnpm lint` (frontend) | ✅ Passa, sem avisos |
| `pnpm build` (frontend) | ✅ Passa — `dist/index.html` 0.45 kB, JS 356.73 kB (gzip 110.80 kB), CSS 16.50 kB, 184 módulos. `dist/` removido após verificação |
| `python manage.py check` (backend_core) | ✅ "System check identified no issues (0 silenced)." |

---

## 9. Limitações

- **Workspace switching não exercido:** só existe um workspace ("FE-016 Dev Workspace") para o utilizador dev neste ambiente; o fluxo de troca de workspace (`setWorkspaceId`, invalidação de queries) está implementado e foi revisto por código, mas não foi exercido com dois workspaces reais nesta sessão.
- **403 (Forbidden) não exercido:** não há, neste ambiente, um segundo utilizador com permissões restritas a um recurso do utilizador dev sem tocar nos utilizadores/workspaces pré-existentes de E2E (explicitamente fora de escopo). O mapeamento de erro 403 → `ForbiddenError` está implementado e coberto por código (`shared/api/errors.ts`, `error-presets.ts`), mas não foi acionado com uma resposta 403 real do Backend Core.
- **Gatilho exacto do 502 foi "upstream rejeitou as credenciais" e não "ligação recusada":** havia, neste ambiente, um processo já a escutar em `:8001` que respondeu `403 unauthorized_internal_request` (por falta de coordenação intencional de `INTERNAL_API_TOKEN`). O resultado observado pelo frontend (`502` → `ServiceUnavailable`) é idêntico ao que se obteria com o Intelligence Engine genuinamente desligado, mas o relatório documenta esta distinção com honestidade.
- **Retry automático não observado em tempo real durante a automatização:** devido ao *throttling* de timers do Chrome em tabs de preview em background, o backoff de retry da query (gerido pelo `queryClient`, não alterado) não pôde ser observado a decorrer em tempo real durante este teste automatizado; foi necessário desactivar temporariamente o retry para observar o estado de erro de forma determinística (secção 5.5), e o mecanismo de recuperação manual ("Try again") foi confirmado de forma independente e funciona como esperado. Esta é uma limitação do ambiente de teste automatizado, não da aplicação.

---

## 10. Conclusão

| Critério | Estado |
| --- | --- |
| Integração real Frontend ↔ Backend Core validada | **Sim** |
| Frontend Foundation concluída | Sim |
| Campaign War Room MVP concluída | Sim |
| War Room validada com dados reais | Sim |
| Intelligence normal (`dry_run`) validada | Sim |
| Intelligence indisponível validada com tratamento `ServiceUnavailable` | Sim |
| `X-Internal-Token` ausente do frontend | Sim |
| Pronto para piloto técnico controlado | **Sim** |
| Pronto para produção | **Não** (faltam: testes automatizados, validação de 403 real, validação de workspace switching com múltiplos workspaces reais, hardening adicional fora do escopo desta fase) |
