# Prompt 09 — Segurança operacional local — Resultado

**Data:** 2026-07-03
**Fase:** `06_staging_infraestrutura_real_local` (STG-LOCAL-009)
**Âmbito:** validar fronteiras de segurança da stack staging local — frontend isolado, tokens internos, CORS, health endpoints, PostgreSQL, MinIO. Sem pentest agressivo, sem alterar permissões destrutivamente.
**Estado de execução:** `executado` — todas as verificações pedidas feitas contra a stack real (infra + 4 serviços aplicacionais activos), **2 violações reais encontradas e corrigidas** (MinIO permitia listagem anónima do bucket; PostgreSQL/MinIO publicados em `0.0.0.0`, alcançáveis por qualquer máquina na rede local, não só esta).

---

## 1. Ambiente usado

Infraestrutura (`docker-compose.staging.local.yml`, containers já activos
desde os Prompts 02–08) + 4 processos aplicacionais arrancados via
`scripts/staging-local-apps-up.ps1`: Backend Core (PostgreSQL,
`EXTERNAL_JOBS_DRY_RUN=false`), Intelligence Engine real
(`INTELLIGENCE_ENGINE_DRY_RUN=false`), Content Renderer (MinIO,
`STORAGE_PROVIDER=s3`), Frontend (Vite dev, `--host 127.0.0.1`).

## 2. Verificações feitas e resultados

### 2.1 Frontend

| Verificação | Método | Resultado |
|---|---|---|
| Bundle sem URLs de IE/Renderer | `npm run build` fresco + `grep -roE "8201|8202" dist/` | ✅ 0 ocorrências |
| Bundle sem `INTERNAL_API_TOKEN`/`X-Internal-Token` como valor | `grep -o` no bundle | ⚠️ 2 ocorrências — **classificadas como defensivas**: `INTERNAL_TOKEN_HEADER` (constante usada para **bloquear** o header, `shared/api/security.ts`) e a chave `internal_api_token`/`x_internal_token` na denylist de redacção (`SENSITIVE_KEYS`, `recommendation-snapshot.ts`) — nunca um valor real; confirmado por inspecção do código-fonte destes dois ficheiros |
| Nenhuma outra chamada de rede fora do `apiClient` | `grep -rn "fetch(\|axios\|XMLHttpRequest\|EventSource\|WebSocket" src/` | ✅ 0 ocorrências fora de `shared/api/client.ts` (só `refetch()` do React Query, que usa o mesmo client internamente) |
| `VITE_*` no bundle | `grep -roE "VITE_[A-Z_]+" dist/assets/*.js` | ✅ só `VITE_BACKEND_API_BASE_URL` |
| URL base cozida no bundle | `grep -roE "http://...api/v1"` | ✅ só `http://localhost:8100/api/v1` |

### 2.2 API client (`frontend/src/shared/api/`)

Confirmado por leitura de código (`client.ts`, `security.ts`):

- `Authorization` só é definido dinamicamente via `getAuthToken()` (provider injectável), nunca hardcoded.
- `X-Workspace-ID` idem, via `getWorkspaceId()`.
- `appendSafeCustomHeaders` remove activamente `x-internal-token`, `authorization`, `x-workspace-id` de qualquer header custom passado por um caller — estes três são "provider-owned" e nunca podem ser sobrepostos por chamadas individuais.
- Em dev, uma tentativa de definir um destes headers gera um `console.warn` (`[api] Blocked custom ...`) — visível, não silenciosa.

### 2.3 Backend Core

| Endpoint | Cenário | Resultado |
|---|---|---|
| `/api/v1/system/health/live/` | sem auth | ✅ `200`, público |
| `/api/v1/system/health/ready/` | sem auth | ✅ `200`, público |
| `/api/v1/system/health/dependencies/` | sem auth | ✅ `401` |
| `/api/v1/system/health/dependencies/` | utilizador autenticado, não-staff | ✅ `403` |
| `/api/v1/system/health/dependencies/` | token inválido/garbage | ✅ `401` (`token_not_valid`) |
| `/api/v1/system/health/dependencies/` | utilizador staff (`is_staff=True`, concedido temporariamente e revertido a seguir) | ✅ `200`, resposta reduzida a `status: ok/degraded` por dependência — **não expõe URLs internas completas nem credenciais** |
| `/api/v1/workspaces/` | sem auth | ✅ `401` |

### 2.4 Intelligence Engine

| Endpoint | Cenário | Resultado |
|---|---|---|
| `/health` | sem auth | ✅ `200`, público |
| `/intelligence/campaign` | sem `X-Internal-Token` | ✅ `403 unauthorized_internal_request` |
| `/intelligence/campaign` | `X-Internal-Token` errado | ✅ `403 unauthorized_internal_request` |

### 2.5 Content Renderer

| Endpoint | Cenário | Resultado |
|---|---|---|
| `/health` | sem auth | ✅ `200`, público |
| `/jobs` | sem `X-Internal-Token` | ✅ `403 unauthorized` |
| `/jobs` | `X-Internal-Token` errado | ✅ `403 unauthorized` |
| `ALLOW_INSECURE_EMPTY_TOKEN` | grep em `.env`/`.env.staging.local` activos | ✅ `false`/ausente — nunca `true` |

### 2.6 MinIO

| Verificação | Resultado |
|---|---|
| Credenciais não versionadas | ✅ confirmado (herdado do Prompt 05; `MINIO_ROOT_USER`/`_PASSWORD` só em `.env.staging.local`, ignorado) |
| `public_url` funciona (download anónimo) | ✅ `200`, PDF/PNG válidos |
| **Listagem pública do bucket** | 🔴 **VIOLAÇÃO ENCONTRADA** — ver §3.1. **Corrigida** nesta iteração. |
| Console/API admin exige auth | ✅ `GET /minio/admin/v3/info` sem auth → `403` |

### 2.7 PostgreSQL

| Verificação | Resultado |
|---|---|
| Credenciais não versionadas | ✅ confirmado (herdado dos Prompts 03/05) |
| Password em logs (aplicação + container) | ✅ 0 ocorrências, ver §4 |
| **Acesso local controlado** (bind de rede) | 🔴 **VIOLAÇÃO ENCONTRADA** — ver §3.2. **Corrigida** nesta iteração. |

### 2.8 CORS

| Verificação | Resultado |
|---|---|
| Preflight de `http://localhost:5200` (origem confiável) | ✅ `Access-Control-Allow-Origin: http://localhost:5200` |
| Preflight de `http://evil.example.com` (origem não confiável) | ✅ sem `Access-Control-Allow-Origin` no response — rejeitado |
| `CORS_ALLOWED_ORIGINS` nos `.env` activos | ✅ só `localhost:5200`/`127.0.0.1:5200`, nunca `*` |

## 3. Violações encontradas e corrigidas

### 3.1 MinIO — listagem anónima do bucket permitida (achado real, não hipotético)

**O que se esperava** (decisão documentada no Prompt 04): leitura anónima
**download-only, sem listagem**, para paridade com o provider `local`.

**O que se encontrou:** `mc anonymous set download` — o comando usado no
Prompt 04 para aplicar essa decisão — na verdade concede
`s3:GetObject` **e** `s3:ListBucket` + `s3:GetBucketLocation`:

```json
{"Statement":[
  {"Action":["s3:GetBucketLocation","s3:ListBucket"],"Effect":"Allow","Principal":{"AWS":["*"]},"Resource":["arn:aws:s3:::chartrex-staging"]},
  {"Action":["s3:GetObject"],"Effect":"Allow","Principal":{"AWS":["*"]},"Resource":["arn:aws:s3:::chartrex-staging/*"]}
],"Version":"2012-10-17"}
```

Confirmado ao vivo: `GET http://127.0.0.1:9000/chartrex-staging/` sem
nenhuma credencial devolvia `200` com a listagem XML completa de todos os
objectos do bucket (chaves, tamanhos, ETags — não conteúdo dos ficheiros,
mas enumeração completa da estrutura `workspaces/<id>/jobs/<id>/<ficheiro>`).
O nome "download" da política pré-definida do MinIO é enganador — não é
"download-only" como o Prompt 04 assumiu.

**Correcção aplicada:** política JSON própria, só `s3:GetObject`:

```json
{"Version":"2012-10-17","Statement":[
  {"Effect":"Allow","Principal":{"AWS":["*"]},"Action":["s3:GetObject"],"Resource":["arn:aws:s3:::chartrex-staging/*"]}
]}
```

Aplicada em runtime (`mc anonymous set-json`) e tornada **reproduzível**:
`docker-compose.staging.local.yml` → serviço `minio-bucket-init` já não usa
`mc anonymous set download`, usa esta política JSON própria. Revalidado
via `docker compose ... up -d` (recriação real dos containers, não só o
comando `mc` isolado):

| Teste | Antes | Depois |
|---|---|---|
| `GET /chartrex-staging/` (listagem) | `200`, XML completo | `403 AccessDenied` |
| `GET /chartrex-staging/<chave conhecida>` (download) | `200` | `200` (inalterado) |

### 3.2 PostgreSQL e MinIO publicados em `0.0.0.0` (achado real, não hipotético)

**O que se encontrou:** `docker port chartrex_staging_postgres` /
`chartrex_staging_minio` mostravam as três portas (5433, 9000, 9001)
publicadas em `0.0.0.0`/`[::]` — alcançáveis por **qualquer máquina na
mesma rede local** (Wi-Fi/LAN), não só a máquina do operador. Para uma
fase cuja premissa é staging **local, de uma única máquina**, isto é uma
superfície de exposição desnecessária: um PostgreSQL alcançável na rede
(mesmo exigindo password) e um bucket MinIO cujo `public_url` seria
descarregável por qualquer dispositivo na mesma rede, não só o operador.

**Correcção aplicada:** `docker-compose.staging.local.yml` — as três
portas passam a publicar explicitamente em `127.0.0.1`:

```diff
- "${POSTGRES_PORT:-5432}:5432"
+ "127.0.0.1:${POSTGRES_PORT:-5432}:5432"

- "${MINIO_API_PORT:-9000}:9000"
- "${MINIO_CONSOLE_PORT:-9001}:9001"
+ "127.0.0.1:${MINIO_API_PORT:-9000}:9000"
+ "127.0.0.1:${MINIO_CONSOLE_PORT:-9001}:9001"
```

Containers recriados (`docker compose up -d`) para aplicar a alteração —
`docker port` confirma agora `127.0.0.1:5433`/`127.0.0.1:9000`/
`127.0.0.1:9001`. Revalidado que os serviços aplicacionais (Backend Core,
Content Renderer) continuam a funcionar sem alteração própria — ambos já
ligavam via `127.0.0.1`, nunca via IP de rede.

## 4. Greps executados

| Grep | Âmbito | Resultado |
|---|---|---|
| `authorization: bearer <token>`, `x-internal-token: <valor>`, `password[:=]<valor>`, `private_key`, `api_key` | `.local-runtime/logs/{backend_core,intelligence_engine,content_renderer,frontend}.{out,err}.log` | ✅ 0 ocorrências nos 8 ficheiros |
| `password\|secret\|token` | `docker logs chartrex_staging_postgres` / `chartrex_staging_minio` (últimas 50 linhas) | ✅ 0 ocorrências |
| Repositório completo (`git ls-files`) por `INTERNAL_API_TOKEN=`, `SECRET_KEY=`, `DB_PASSWORD=`, `MINIO_ROOT_PASSWORD=`, `STORAGE_ACCESS_KEY=`, `STORAGE_SECRET_KEY=`, `E2E_PASSWORD=`, `STRIPE_*=` com valores não-placeholder | via `staging-local-quality-gate.ps1 -Only secrets_grep` (Prompt 07) | ✅ 884 ficheiros verificados, 0 suspeitos |
| `scripts/check-forbidden-ports.ps1` | repositório | ✅ OK |

**`E2E_PASSWORD` nunca impresso** nesta iteração — usado só via
`set -a && . env && set +a` (nunca `echo`/`Write-Output` do valor).

## 5. Pendências

- Verificação "Network apenas Backend Core" via **browser real** ou E2E
  automatizado não foi feita nesta iteração — a evidência usada foi
  análise de código-fonte (`client.ts`, `security.ts`) + grep do bundle
  `dist/`, que o próprio prompt permite como alternativa ("Network browser
  **ou** E2E"). A confirmação end-to-end via Playwright real fica para
  STG-LOCAL-008 (E2E local), ainda por fechar.
- Não foi feito pentest activo (scanners, fuzzing, brute-force) —
  explicitamente fora do âmbito ("Não executar pentest agressivo").
- A causa raiz do achado §3.1 (nome enganador da política `download` do
  MinIO) não foi documentada em nenhum lugar do ecossistema MinIO
  consultado por nós — vale a pena um comentário de aviso semelhante em
  qualquer documentação futura que volte a mencionar object storage local.

## 6. Riscos

| Risco | Severidade | Estado |
|---|---|---|
| Listagem pública do bucket MinIO expondo estrutura de chaves (workspace/job ids) | Alto (se não corrigido) | **Mitigado** — política corrigida e reproduzível via compose |
| PostgreSQL/MinIO alcançáveis por qualquer máquina na rede local | Médio-Alto (se não corrigido) | **Mitigado** — bind restrito a `127.0.0.1` |
| Ambos os achados eram invisíveis a uma leitura de código isolada — só apareceram com testes reais contra a stack a correr | — | Reforça a necessidade de validação por execução real, não só revisão de configuração, nas fases seguintes desta pipeline |
| `ALLOW_INSECURE_EMPTY_TOKEN` reintroduzido inadvertidamente no futuro | Baixo | Confirmado ausente/`false`; sem mecanismo automático que o impeça de ser activado manualmente — mitigação continua a ser revisão humana + os testes automatizados do Content Renderer (`env.test.ts`) |

## 7. Correcções (resumo)

| Ficheiro | Alteração |
|---|---|
| `docker-compose.staging.local.yml` | Política anónima do MinIO trocada de `mc anonymous set download` (GetObject+ListBucket) para uma política JSON própria (só GetObject); portas do PostgreSQL e MinIO passam a publicar em `127.0.0.1` explicitamente, não `0.0.0.0` |
| `frontend/docs/.../resultados_execucao/prompt_09_seguranca_local_resultado.md` | **criado** (este relatório) |

Nenhum ficheiro de código de produto foi alterado. Nenhuma permissão foi
alterada destrutivamente — as duas correcções **reduzem** acesso
(princípio do menor privilégio), nunca o aumentam.

## 8. Próximo passo recomendado

Avançar para **STG-LOCAL-008** (E2E local, ainda pendente desta pipeline —
ver estado consolidado nos relatórios anteriores): correr `pnpm test:e2e`
real contra a stack agora também mais restrita em rede (§3.2), confirmando
que a correcção de bind não quebra nenhum fluxo do frontend/Playwright
(deve ser transparente, já que tudo corre na mesma máquina via
`127.0.0.1`). A verificação "Network apenas Backend Core" pendente (§5)
deve ser fechada nesse prompt via o browser real do Playwright.
