# Prompt 09 — Revalidação de segurança local pós-hardening — Resultado

**Data:** 2026-07-03
**Fase:** `07_staging_local_hardening` (STG-HARD-009)
**Âmbito:** revalidar a segurança local depois de todo o hardening desta
fase (timeout PostgreSQL, credenciais MinIO não-root, cleanup por run-id,
diagnóstico E2E, proposta de CI/CD), confirmando que nada foi
reintroduzido nem regrediu.
**Estado de execução:** `executado` — todas as verificações pedidas
corridas contra a stack real (containers + 4 processos aplicacionais
activos), com evidência directa (não só leitura de código) em todos os
pontos onde isso foi viável. **Nenhuma regressão encontrada.** Um achado
adjacente (não de segurança do produto, mas do próprio gate de segurança)
foi corrigido na iteração anterior (STG-HARD-005) e reconfirmado aqui.

---

## 1. Frontend — build fresco e bundle

```powershell
cd frontend; rm -rf dist; pnpm build
```

`✓ built in 1.04s` (`dist/assets/index-DBwMp9Ay.js`, 394.89 kB).

| Verificação | Resultado |
|---|---|
| `grep -rE "8201|8202" dist/` | ✅ 0 ocorrências |
| URLs externas no bundle (`grep -oE "https?://..."`) | `http://localhost:8100` (Backend Core, esperado) + `w3.org`/`react.dev`/`reactrouter.com` (comentários de licença/docs do próprio React, inofensivos) — **nenhuma outra** |
| `INTERNAL_API_TOKEN`/`X-Internal-Token` no bundle | 2 ocorrências, **ambas confirmadas como o mecanismo de bloqueio/redacção em si**, nunca um valor — ver §1.1 |

### 1.1 As duas ocorrências de "token" no bundle, investigadas

```js
// Set(['x-internal-token','authorization','x-workspace-id'])
// Set(['api_key','password','secret','authorization','private_key','client_secret','internal_api_token','x_internal_token'])
```

Confirmado por leitura do código-fonte não minificado
(`frontend/src/shared/api/security.ts`):

```ts
const PROVIDER_OWNED_HEADERS = new Set([
  INTERNAL_TOKEN_HEADER,  // 'x-internal-token'
  'authorization',
  'x-workspace-id',
])
// appendSafeCustomHeaders(): qualquer header chamador com um destes nomes
// é descartado (onBlockedProviderHeader), nunca aplicado ao pedido real.
```

A segunda lista (em `recommendation-snapshot.ts`) é uma denylist de nomes
de campo para redacção de snapshots — mesma natureza: só nomes, nunca
valores. **Ambas são o mecanismo de defesa em si, não uma fuga.**

## 2. Network apenas Backend Core

Validado via **E2E real** (não só análise estática), contra a stack
totalmente activa:

```text
ok 12 [chromium] › the frontend only ever talked to the Backend Core (2ms)
```

O teste usa um listener real (`page.on('request')`) activo durante toda a
sessão do browser (login, War Room, criação das 4 acções, mark reviewed,
dismiss, reload), comparando cada pedido contra as portas proibidas
(`8201`, `8202`) e os hosts permitidos. **12/12 `PASS`** na execução
completa (§ da mesma sessão, ver também `prompt_07_...md` §4).

## 3. API client — comportamento dinâmico confirmado por código

```ts
// client.ts
if (token) headers.set('Authorization', `Bearer ${token}`)      // linha 87
if (workspaceId) headers.set('X-Workspace-ID', workspaceId)     // linha 91
```

`token`/`workspaceId` vêm de estado em memória (nunca hardcoded, nunca
persistidos em `localStorage` como valor de header fixo); `X-Internal-Token`
nunca é definido em nenhum ponto do código do frontend — só existe como
**nome bloqueado** em `security.ts` (§1.1).

## 4. Backend Core — endpoints públicos vs. protegidos

| Endpoint | Sem auth | Auth válida, não-staff | Nota |
|---|---|---|---|
| `GET /api/v1/system/health/live/` | `200` | — | Público, por desenho |
| `GET /api/v1/system/health/ready/` | `200` | — | Público, por desenho |
| `GET /api/v1/system/health/dependencies/` | `401` | `403` | Staff-only — os dois estados testados de facto |
| `GET /api/v1/workspaces/` (endpoint normal) | `401` | — | — |
| `GET /api/v1/workspaces/` com token inválido | `401` | — | — |

## 5. Intelligence Engine / Content Renderer

| Serviço | `/health` (sem token) | Endpoint interno, sem token | Endpoint interno, token errado |
|---|---|---|---|
| Intelligence Engine | `200` | `403` (`POST /recommendations/campaign`) | `403` |
| Content Renderer | `200` | `403` (`POST /jobs`) | `403` |

`ALLOW_INSECURE_EMPTY_TOKEN` confirmado **ausente** dos 3
`.env.staging.local` de serviço (default seguro = `false`/rejeita tudo).

## 6. MinIO

| Verificação | Resultado |
|---|---|
| Download anónimo de um objecto real e conhecido (`public_url` de um asset criado no E2E desta sessão) | `200` |
| Listagem pública do bucket (`GET /chartrex-staging/`) | `403` |
| Upload com credencial não-root (`chartrex_renderer`) | ✅ sucedido |
| Listagem do bucket com a mesma credencial não-root | `Access Denied` |
| Operação admin (`mc admin user list`) com a mesma credencial | `Access Denied` |

Nenhuma regressão face ao hardening do STG-HARD-003 — o utilizador de
serviço continua sem `s3:ListBucket`/admin; a política anónima continua
só `s3:GetObject`.

## 7. Bind PostgreSQL/MinIO

```text
$ docker port chartrex_staging_postgres
5432/tcp -> 127.0.0.1:5433
$ docker port chartrex_staging_minio
9000/tcp -> 127.0.0.1:9000
9001/tcp -> 127.0.0.1:9001
```

**Nenhuma das três portas publica em `0.0.0.0`** — a correcção do
STG-LOCAL-009 (fase 06) continua em vigor, não regrediu.

## 8. Logs e ficheiros versionados — greps de secrets

| Grep | Âmbito | Resultado |
|---|---|---|
| `Authorization: Bearer <token>`, `X-Internal-Token: <valor>`, `DB_PASSWORD=`, `STORAGE_SECRET_KEY=`, `E2E_PASSWORD=`, `MINIO_ROOT_PASSWORD=`, `MINIO_RENDERER_PASSWORD=` | `.local-runtime/logs/*.log` (4 ficheiros dos serviços activos) | ✅ 0 ocorrências |
| `scripts/staging-local-quality-gate.ps1 -Only secrets_grep` | `git ls-files` (927 ficheiros versionados) | ✅ `PASS` — 0 suspeitos |
| `scripts/check-forbidden-ports.ps1` | Repositório | ✅ `OK` |

### 8.1 Nota sobre o `secrets_grep` do próprio quality gate

Esta mesma etapa tinha falhado momentos antes desta revalidação (durante a
iteração STG-HARD-005, ao correr o gate completo) com 8 ocorrências — **as
8 confirmadas, uma a uma, como falsos positivos** (código-fonte de regex
de redacção, referências de variável PowerShell `$env:...`, e um padrão de
grep documentado em prosa num relatório da fase 06 — nunca um segredo
real). Corrigido nessa iteração (`$safeMarker` alargado em
`staging-local-quality-gate.ps1`) e **reconfirmado aqui, de novo, depois
de todo o hardening desta fase**: `927 ficheiros verificados, 0
suspeitos`. Documentado com detalhe em
`resultados_execucao/prompt_08_cicd_real_resultado.md` §3 — não repetido
por extenso aqui para não duplicar, só reconfirmado como ainda válido.

## 9. Critérios de aceitação — verificação

- ✅ Frontend isolado (bundle sem `8201`/`8202`, único host externo
  `localhost:8100`).
- ✅ Network apenas Backend Core confirmada **por E2E real**, não só
  justificação de código.
- ✅ Tokens internos só server-to-server (`X-Internal-Token` bloqueado no
  browser por desenho, nunca definido pelo código do frontend).
- ✅ MinIO sem `ListBucket` público (`403`, confirmado de novo).
- ✅ PostgreSQL/MinIO bindados em `127.0.0.1` (as três portas).
- ✅ Credenciais MinIO não-root validadas (upload sim, listagem/admin não).
- ✅ Logs sem secrets.
- ✅ Greps passam (`secrets_grep`, `check-forbidden-ports.ps1`).

Nenhum critério de rejeição ocorreu: nenhuma regressão para `0.0.0.0`,
bucket continua sem listagem pública, frontend não chama IE/Renderer,
nenhum token interno chega ao browser, nenhum secret em logs/docs/código,
`/dependencies/` continua staff-only, `ALLOW_INSECURE_EMPTY_TOKEN` continua
inactivo em todos os serviços.

## 10. Riscos remanescentes

Sem riscos novos encontrados nesta revalidação. Os riscos já conhecidos e
documentados em iterações anteriores desta fase (caminho de erro HTTP a
~31s em vez de ~5s sob `DEBUG=True`, validação por terceiro ainda
pendente) mantêm-se, sem alteração de severidade.

## 11. Próximo passo recomendado

1. Seguir para **STG-HARD-010** (fecho da fase 07) — esta é a última
   revalidação técnica pendente antes do fecho.
2. Nenhuma acção de segurança adicional identificada como necessária.
