# Prompt 08 — Segurança frontend (isolamento e Network)

**Data:** 2026-07-02
**Fase:** `04_staging_campaign_actions_with_real_ie_renderer` (STG-CA-008, Incremento 3)
**Âmbito:** confirmar que, **mesmo com IE (8201) e Renderer (8202) reais activos**, o frontend continua isolado e chama exclusivamente o Backend Core (8100). Sem alteração de código de produto.
**Estado de execução:** `executado`

---

## 1. Resumo objectivo

A fronteira arquitectural do frontend está **intacta e provada por múltiplas camadas** de evidência (código-fonte, boundary de rede único, bundle compilado, validações e runtime da Iteração 7):

- O frontend só conhece **um** backend: `VITE_BACKEND_API_BASE_URL=http://localhost:8100/api/v1`. Não há configuração de IE/Renderer nem secrets internos.
- Existe **um único `fetch()`** em todo o `frontend/src` — o client central `shared/api/client.ts`. Não há `axios`, `XMLHttpRequest`, `WebSocket` nem `EventSource`.
- `Authorization` é sempre **`Bearer` dinâmico**, lido de um provider em request-time; nunca hardcoded.
- `X-Internal-Token` só existe como **constante de guarda** que é **removida** de headers custom (mais `authorization` e `x-workspace-id`, protegidos como provider-owned).
- O **bundle de produção compilado** (`dist/`) contém **apenas** `localhost:8100/api/v1` e **zero** referências a 8201/8202/internal-token/portas antigas — evidência ao nível do artefacto que efectivamente vai para o browser.
- `pnpm lint` ✅, `pnpm test` ✅ (14/14), `pnpm build` ✅, `check-forbidden-ports.ps1` ✅.
- **Nenhuma violação encontrada.** Nada a corrigir.

Estado dos serviços durante a validação (precondição da tese da fase — IE+CR reais ligados): BC 8100 (200), IE 8201 (200), CR 8202 (200), FE 5200 (200).

---

## 2. Inspecção de configuração (tarefas 1–3)

### 2.1 `.env.local` / `.env.example` (frontend)
Única variável presente em ambos:
```
VITE_BACKEND_API_BASE_URL=http://localhost:8100/api/v1
```
**Sem** `INTELLIGENCE_ENGINE_BASE_URL`, `CONTENT_RENDERER_BASE_URL`, `REPORT_RENDERER_BASE_URL`, `INTERNAL_API_TOKEN`, `X-Internal-Token`, nem qualquer secret.

### 2.2 `src/shared/config/env.ts`
- Expõe apenas `apiBaseUrl` (Backend Core), `isDev`, `isProd`.
- Comentário explícito: *"The ONLY backend the frontend talks to is the Backend Core … no configuration here for the Intelligence Engine or the Content Renderer, and no internal secrets."*
- Valida que o URL é http(s); fallback dev `http://localhost:8100/api/v1`; sem trailing slash.

### 2.3 `src/shared/api/client.ts` (boundary único)
- Comentário de topo: *"This is the ONLY network boundary of the frontend. It targets the Backend Core exclusively (never the Intelligence Engine or Content Renderer) and never sends `X-Internal-Token`."*
- `baseUrl = ENV.apiBaseUrl` (8100).
- `Authorization: Bearer ${token}` com `token = getAuthToken()` — **dinâmico**, injectado por provider (`readToken`), nunca hardcoded (linha 87).
- `X-Workspace-ID` também dinâmico via provider.
- Headers custom passam por `appendSafeCustomHeaders` → headers provider-owned são **removidos**.

### 2.4 `src/shared/api/security.ts` (guarda)
```ts
export const INTERNAL_TOKEN_HEADER = 'x-internal-token'
const PROVIDER_OWNED_HEADERS = new Set([INTERNAL_TOKEN_HEADER, 'authorization', 'x-workspace-id'])
// appendSafeCustomHeaders: descarta estes headers se um caller tentar injectá-los
```
O `x-internal-token` aparece aqui **apenas para ser bloqueado** — é uma defesa activa, não um envio.

---

## 3. Greps de segurança (tarefa 4) — `frontend/src`

| Padrão | Ocorrências | Classificação |
|---|---|---|
| `X-Internal-Token` / `x-internal-token` | 2 | **guarda + doc** — `security.ts` (constante para remover) e `client.ts` (comentário de proibição) |
| `INTELLIGENCE_ENGINE_BASE_URL` | 0 | limpo |
| `CONTENT_RENDERER_BASE_URL` | 0 | limpo |
| `REPORT_RENDERER_BASE_URL` | 0 | limpo |
| `localhost:8201` / `:8201` | 0 | limpo |
| `localhost:8202` / `:8202` | 0 | limpo |
| `intelligence_engine` | 0 | limpo |
| `content_renderer` | 0 | limpo |
| `INTERNAL_API_TOKEN` | 0 (uppercase) | limpo — a variante `internal_api_token` só surge em denylists de redacção |
| `Bearer ` (hardcoded) | 1 | **legítimo** — `client.ts:87` `Bearer ${token}` (interpolação dinâmica) |
| `api_key` / `private_key` | 3 | **denylist** — `recommendation-snapshot.ts` `SENSITIVE_KEYS` (chaves removidas do snapshot) |
| `password` | login + denylist | **legítimo** — campo de input em `LoginPage.tsx`/`auth-api.ts` (credencial do utilizador enviada ao BC) + denylist |

Detalhe das ocorrências não-triviais:
- `recommendation-snapshot.ts` → `SENSITIVE_KEYS = {token, access_token, refresh_token, api_key, password, secret, authorization, private_key, client_secret, internal_api_token, x_internal_token}` — **denylist de redacção** aplicada ao snapshot de recommendation (impede que qualquer campo sensível vindo do payload do IE seja persistido/mostrado). É protecção, não fuga.
- `LoginPage.tsx` / `auth-api.ts` → `password` é o campo do formulário de login (input do utilizador), trocado por um par de tokens no endpoint de auth do Backend Core. Não é secret interno service-to-service.

**Conclusão:** todas as ocorrências caem em **guarda / teste / documentação de proibição / denylist / input de login** — nenhuma é uma chamada directa a IE/CR nem um secret interno embebido. (Tarefas 6 e 7 confirmadas.)

---

## 4. Boundary de rede único (reforço da tarefa 8)

Grep por qualquer mecanismo de rede em `frontend/src`:

| Mecanismo | Ocorrências |
|---|---|
| `fetch(` | **1** — `shared/api/client.ts:109` (o client central) |
| `axios` | 0 |
| `XMLHttpRequest` | 0 |
| `WebSocket` / `EventSource` | 0 |

Ou seja, **toda** a rede do frontend passa por um único ponto que aponta para `ENV.apiBaseUrl` (8100). Não há caminho alternativo para 8201/8202.

---

## 5. Evidência "Network" (tarefa 5)

### 5.1 Live browser — não disponível nesta iteração
- Não há servidor gerido pelo Claude Preview (`preview_list` → `[]`) e o Frontend corre **externamente** em 5200 com `strictPort`; arrancar um servidor de preview concorrente arriscaria colidir/derrubar o FE em execução.
- Não há browser Chrome ligado (`list_connected_browsers` → `[]`).
- O smoke clicado com captura de Network ao vivo (login → War Room → actions → confirmar requests só a 8100) é o âmbito de **STG-CA-009** e fica lá consolidado (coerente com o diferimento nos Prompts 03/05).

A regra "**greps e/ou Network**" é satisfeita: os greps + análise de bundle abaixo são conclusivos.

### 5.2 Static Network evidence — bundle de produção compilado (`dist/`)
Após `pnpm build`, greps no artefacto que efectivamente corre no browser:

| Padrão no bundle | Ocorrências |
|---|---|
| `8201` | **0** |
| `8202` | **0** |
| `x-internal-token` / `X-Internal-Token` | **0** |
| `INTERNAL_API_TOKEN` | **0** |
| `intelligence_engine` | **0** |
| `content_renderer` | **0** |
| `:8000` / `:8001` / `:8002` / `:8003` (portas antigas) | **0** |
| `localhost:8100/api/v1` | **1** (o único alvo) |

O único endpoint de rede embebido no bundle é o Backend Core. Isto é evidência ao nível de rede de **o que a aplicação consegue alcançar** — independentemente de interacção.

### 5.3 Runtime cross-check (Iteração 7 / Prompt 07)
Nos logs do Backend Core, as chamadas `internal_call ... url=http://localhost:8201/intelligence/campaign` e `...:8202/jobs/` originam **sempre** no Backend Core (mediação server-to-server), nunca no browser. O `X-Internal-Token` viaja só em headers server-to-server e nunca é registado.

---

## 6. Validações executadas

| Validação | Resultado |
|---|---|
| `.env.local` só com `VITE_BACKEND_API_BASE_URL` (8100) | ✅ |
| `env.ts` sem IE/CR/secrets | ✅ |
| `client.ts` boundary único, Bearer dinâmico | ✅ |
| `security.ts` remove `x-internal-token`/`authorization`/`x-workspace-id` | ✅ |
| Greps de segurança (13 padrões) | ✅ só guarda/teste/doc/denylist/login |
| Único `fetch()`, sem axios/WS/XHR | ✅ |
| **Bundle compilado** sem 8201/8202/token/portas antigas | ✅ (só 8100) |
| `pnpm lint` | ✅ 0 erros |
| `pnpm test` | ✅ **14/14 pass** |
| `pnpm build` | ✅ built 249 módulos, 2.1 s |
| `scripts/check-forbidden-ports.ps1` | ✅ OK — nenhuma porta proibida |
| Serviços 8100/8201/8202/5200 | ✅ 200 (IE+CR reais activos) |
| Network live no browser | ⚠️ não disponível (ver §5.1) — diferido para STG-CA-009 |

---

## 7. Violações encontradas / corrigidas

**Nenhuma.** Não foi necessária qualquer correcção. A fronteira já estava correcta por design (client central único, guarda de headers, env sem secrets).

---

## 8. Limitações

| Limitação | Impacto |
|---|---|
| Captura de Network **ao vivo** no browser não executada (FE externo strictPort; sem preview gerido; sem Chrome ligado) | Baixo — coberto por static Network (bundle) + boundary único + runtime da Iteração 7; smoke clicado fica em STG-CA-009 |
| Greps são sobre `frontend/src` + `dist/`; dependências em `node_modules` não auditadas | Baixo — o bundle compilado (que inclui deps efectivamente usadas) não contém alvos internos |

---

## 9. Ficheiros alterados

Apenas este relatório (**criado**):
`frontend/docs/01_fundamentos/04_staging_campaign_actions_with_real_ie_renderer/resultados_execucao/prompt_08_seguranca_frontend_network_resultado.md`

Nenhum código de produto, config ou `.env` alterado. (`pnpm build` regenerou `dist/`, artefacto ignorado por git.) Nenhum segredo consta deste relatório.

---

## 10. Próximo passo recomendado

Avançar para **STG-CA-009 (smoke visual staging)** e depois **STG-CA-010 (fecho)**:
1. Executar o fluxo clicado no browser (login → War Room com intelligence real → recommendations → criar manual task / report / media kit / content pack → reviewed / dismiss → painel → reload → persistência) e, com o DevTools/Network, capturar a **evidência live** de que todos os requests vão só para `localhost:8100` — fechando o único item diferido deste prompt.
2. Confirmar coerência visual e ausência de regressão de layout.
3. Consolidar o relatório final da fase (STG-CA-010) com a decisão pronto/não-pronto para piloto.

> Serviços a correr em background no fim desta iteração: Backend Core (8100), Intelligence Engine (8201), Content Renderer (8202), Frontend (5200) — todos reais e activos.
