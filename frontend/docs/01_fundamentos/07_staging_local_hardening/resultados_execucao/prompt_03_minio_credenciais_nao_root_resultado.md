# Prompt 03 — Credenciais MinIO não-root para o Content Renderer — Resultado

**Data:** 2026-07-03
**Fase:** `07_staging_local_hardening` (STG-HARD-003)
**Âmbito:** substituir o uso das credenciais root do MinIO pelo Content Renderer
por um utilizador de serviço dedicado, com policy mínima, sem quebrar
provider local, upload/download real ou `Asset.public_url`.
**Estado de execução:** `executado` — utilizador `chartrex_renderer` criado
idempotentemente com policy mínima, Content Renderer migrado, validado
end-to-end (report/media kit/content pack reais, download por `public_url`,
tentativas de admin/listagem correctamente negadas). **Um incidente próprio
foi cometido e corrigido nesta iteração** (secret impresso por acidente,
rotacionado de imediato) — ver §6.

---

## 1. Como o MinIO é inicializado (leitura de código)

`docker-compose.staging.local.yml` já tinha um serviço `minio-bucket-init`
(execução única, `restart: "no"`) que usa as credenciais root para criar o
bucket e aplicar uma **policy anónima própria** (só `s3:GetObject`, sem
`s3:ListBucket` — corrigido na fase 06, Prompt 09, depois de se descobrir que
`mc anonymous set download` concede as duas). Essa política **não foi
alterada** por esta tarefa — continua a servir `Asset.public_url` sem
credenciais, exactamente como antes.

## 2. Utilizador de serviço criado

- **Nome:** `chartrex_renderer` (env `MINIO_RENDERER_USER`, default
  `chartrex_renderer`).
- **Password:** gerada (`openssl rand -hex 20`), guardada apenas em
  `.env.staging.local` (raiz, `MINIO_RENDERER_PASSWORD`) e em
  `content_renderer/.env.staging.local` (`STORAGE_SECRET_KEY`) — ambos
  ignorados pelo git. Nunca impressa em nenhum comando de validação (excepto
  um incidente próprio, corrigido — ver §6).
- **Criação idempotente:** adicionada ao `minio-bucket-init` (o mesmo
  serviço one-shot que já criava o bucket), usando `mc admin user add` (que
  já é idempotente — reexecutar actualiza a mesma password sem erro) e
  `mc admin policy create` (idempotente — recriar uma policy com o mesmo
  nome actualiza o conteúdo). Só `mc admin policy attach` não é idempotente
  entre execuções (a segunda tentativa devolve "already attached"); guardado
  com `|| true` para não travar reexecuções do script, sem esconder nenhuma
  outra falha (`set -e` continua activo para o resto do script).

### Policy aplicada (`chartrex-renderer-policy`)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": ["arn:aws:s3:::chartrex-staging/*"]
    }
  ]
}
```

Confirmada via `mc admin policy info` (comando não-secreto, ver §5) —
conteúdo exactamente este, sem alterações desde a criação.

**Decisões de âmbito da policy** (leitura de código,
`content_renderer/src/storage/s3-storage.ts`):

| Permissão | Incluída? | Justificação |
|---|---|---|
| `s3:PutObject` | ✅ | Único comando S3 usado pelo código (`PutObjectCommand`) — upload de `report.pdf`/`media_kit.pdf`/outputs. |
| `s3:GetObject` | ✅ | Pedida pelo backlog como parte do mínimo; o Content Renderer não lê objectos de volta hoje, mas é inofensiva (mesmo nível que a leitura pública anónima já concede) e cobre uma leitura futura sem reabrir a policy. |
| `s3:AbortMultipartUpload` | ❌ | O código usa `PutObjectCommand` directo do `@aws-sdk/client-s3`, não o helper `Upload` de `@aws-sdk/lib-storage` — não há multipart upload em nenhum caminho de código (confirmado por grep: `PutObjectCommand` é o único import de comando S3 em todo `content_renderer/src`). |
| `s3:ListBucket` | ❌ | Nenhum caminho de código lista o bucket; a regra explícita do prompt proíbe reintroduzir listagem. |
| `s3:DeleteObject` | ❌ | Nenhum caminho de código apaga objectos; regra explícita do prompt ("sem delete por default"). |
| Qualquer `admin:*` | ❌ | Regra explícita do prompt; validado que falha (§5). |

## 3. Content Renderer migrado

`content_renderer/.env.staging.local` (local, não versionado):
`STORAGE_ACCESS_KEY`/`STORAGE_SECRET_KEY` deixaram de ser
`MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` e passaram a ser
`chartrex_renderer` / a password dedicada gerada nesta iteração. Nenhuma
alteração de código foi necessária em `s3-storage.ts` ou
`storage.factory.ts` — ambos já liam apenas `config.storageAccessKey`/
`config.storageSecretKey` de forma agnóstica à identidade da credencial, e
já não logavam credenciais (confirmado por leitura de código, sem alteração
necessária).

## 4. Ficheiros alterados

| Ficheiro | Operação |
|---|---|
| `docker-compose.staging.local.yml` | `minio-bucket-init`: novas env `MINIO_RENDERER_USER`/`MINIO_RENDERER_PASSWORD`; entrypoint estendido para criar a policy `chartrex-renderer-policy`, o utilizador `chartrex_renderer` e fazer o attach, idempotentemente |
| `.env.staging.local.example` | Documentado `MINIO_RENDERER_USER`/`MINIO_RENDERER_PASSWORD` (placeholder, sem segredo); comentário a esclarecer que root fica só para administração |
| `content_renderer/.env.example` | Comentário de `STORAGE_ACCESS_KEY`/`STORAGE_SECRET_KEY` actualizado — deixa de apontar para `MINIO_ROOT_*`, passa a apontar para `MINIO_RENDERER_*`, com a policy resumida |
| `.env.staging.local` (raiz, **não versionado**) | Adicionadas `MINIO_RENDERER_USER=chartrex_renderer` e `MINIO_RENDERER_PASSWORD=<gerada>` |
| `content_renderer/.env.staging.local` (**não versionado**) | `STORAGE_ACCESS_KEY`/`STORAGE_SECRET_KEY` actualizados para as novas credenciais |
| `frontend/docs/.../06_staging_infraestrutura_real_local/runbook_staging_local.md` | §4, §11, §21 actualizados (credenciais dedicadas, comandos de diagnóstico `mc admin`/`mc ls` correctos, achado da fase 06 marcado como corrigido) |
| `frontend/docs/.../06_staging_infraestrutura_real_local/estado_staging_local.md` | §8 (riscos) e §9 (limitações): entrada "credenciais MinIO root" marcada como corrigida (e, por consistência, a entrada de `connect_timeout` do STG-HARD-002 também, que tinha ficado por marcar nessa iteração) |
| `frontend/docs/.../07_staging_local_hardening/resultados_execucao/prompt_03_minio_credenciais_nao_root_resultado.md` | **criado** (este relatório) |

## 5. Validações de permissões (mc, sem imprimir segredos)

| Teste | Credencial | Esperado | Resultado |
|---|---|---|---|
| `mc admin user info <renderer>` | root | mostra `AccessKey`, `Status`, `PolicyName` (sem secret) | ✅ `AccessKey: chartrex_renderer`, `Status: enabled`, `PolicyName: chartrex-renderer-policy` |
| `mc admin policy info chartrex-renderer-policy` | root | mostra o JSON exacto acima | ✅ confirmado byte-a-byte |
| `mc ls svc/chartrex-staging` (listar bucket) | `chartrex_renderer` | **negado** | ✅ `Access Denied` |
| `mc admin user list` | `chartrex_renderer` | **negado** (sem admin) | ✅ `Access Denied` |
| `mc cp` (upload de um ficheiro de teste) | `chartrex_renderer` | sucesso | ✅ upload confirmado (17 B, `_permission_probe/probe.txt`) |
| `mc cat` (download do mesmo ficheiro) | `chartrex_renderer` | sucesso (`s3:GetObject`) | ✅ conteúdo devolvido correctamente |
| `GET` anónimo do mesmo ficheiro | nenhuma (anónimo) | `200` (policy anónima inalterada) | ✅ `200` |
| `GET` anónimo de listagem do bucket (`/chartrex-staging/`) | nenhuma (anónimo) | `403` (inalterado desde a fase 06) | ✅ `403 AccessDenied` |
| Remoção do ficheiro de teste | `chartrex_renderer` | **não tentado** (sem `s3:DeleteObject`) | Removido com **root** propositadamente, provando que o utilizador de serviço não teria conseguido |

## 6. Incidente próprio: secret impresso por acidente (corrigido)

Durante a validação de sintaxe do compose (`docker compose ... config`, sem
`--quiet`), o comando **imprimiu o valor resolvido** de
`MINIO_RENDERER_PASSWORD` em texto simples no output desta sessão — violação
directa da regra "não imprimir credenciais". Acção tomada imediatamente,
antes de qualquer outro passo:

1. A password exposta foi **rotacionada** (`openssl rand -hex 20`, novo
   valor) em ambos os ficheiros (`.env.staging.local` raiz e
   `content_renderer/.env.staging.local`) — o valor que apareceu no output
   já não é válido em nenhum sistema.
2. `docker compose config --quiet` (valida sintaxe sem imprimir valores
   resolvidos) passou a ser o único comando de validação de sintaxe usado
   desde então.
3. Todas as credenciais usadas em comandos `mc`/`docker run` subsequentes
   foram lidas de ficheiro e passadas como variável de ambiente do processo
   (`-e VAR="$(...)"`), nunca ecoadas para stdout.

Este incidente é registado sem eufemismo, como o resto desta pipeline exige.
A password actualmente activa **nunca** apareceu em nenhum output desta
sessão.

## 7. Uploads/downloads reais (report, media kit, content pack)

Usando um workspace/campanha seedados (`seed_e2e_run --run-id=stghard003smoke`,
o mesmo mecanismo do E2E do frontend) e um login real (`POST /auth/token/`),
criados via HTTP real (não mock) contra o Backend Core:

| Artefacto | Status final | `external_job_id` |
|---|---|---|
| Report (`campaign_report`) | `completed` | `3c331cd9-9cd4-4557-a512-b9460f561517` |
| Media kit | `generated` | `b647bed8-4d12-4193-a13d-58ab341dec3a` |
| Content pack request | `completed` | `23f19faa-dbbd-4275-847c-a0b491a3bfdf` |

**4 assets confirmados** (`GET /api/v1/assets/`), todos `storage_provider="s3"`,
todos com `public_url` preenchido:

| Ficheiro | `public_url` (download) | HTTP | Tamanho |
|---|---|---|---|
| `report.pdf` | `.../jobs/3c331cd9.../report.pdf` | `200` | 1193 B |
| `media_kit.pdf` | `.../jobs/b647bed8.../media_kit.pdf` | `200` | 1131 B |
| `output_001.png` | `.../jobs/23f19faa.../output_001.png` | `200` | 69641 B |
| `output_002.png` | `.../jobs/23f19faa.../output_002.png` | `200` | 69641 B |

Confirmados fisicamente no bucket via `mc ls --recursive root/chartrex-staging/workspaces/<ws>/`
(4 objectos, mesmos caminhos). **Todos os 4 uploads foram feitos pelo
Content Renderer usando exclusivamente as novas credenciais
`chartrex_renderer`** (processo reiniciado antes do teste, log de arranque
confirma `storage.provider_initialized provider=s3` sem nenhuma credencial
impressa).

## 8. Testes automatizados

| Validação | Resultado |
|---|---|
| `docker compose --env-file .env.staging.local -f docker-compose.staging.local.yml config --quiet` | ✅ sintaxe válida, nada impresso |
| `docker compose ... up minio-bucket-init` | ✅ `exited with code 0`; log confirma criação da policy, do utilizador e do attach |
| `npx vitest run` (Content Renderer) | ✅ **151 passed** (13 ficheiros de teste) |
| Grep `STORAGE_ACCESS_KEY=<valor>`\|`STORAGE_SECRET_KEY=<valor>`\|`MINIO_RENDERER_PASSWORD=<valor>` em `git ls-files` (excluindo `*.example`) | ✅ 0 ocorrências |
| Grep de credenciais em `.local-runtime/logs/content_renderer.{out,err}.log` | ✅ 0 ocorrências |
| `scripts/check-forbidden-ports.ps1` | ✅ `OK` |
| `staging-local-health.ps1 -RequireApps` | ✅ 8/8 `OK`/`SKIPPED` correctamente |

## 9. Critérios de aceitação — verificação

- ✅ Content Renderer usa credenciais dedicadas não-root (`chartrex_renderer`,
  confirmado pelo log de arranque e pelos uploads reais).
- ✅ Root fica reservado para administração (usado apenas nos comandos `mc
  admin`/diagnóstico desta iteração, nunca pelo Content Renderer).
- ✅ Uploads continuam a funcionar (report/media kit/content pack, 4/4
  artefactos).
- ✅ Downloads por `public_url` continuam a funcionar (4/4, `200`).
- ✅ Policy mínima e documentada (§2, §5).
- ✅ `ListBucket` público não reintroduzido (política anónima inalterada,
  ainda `403` para listagem; `chartrex_renderer` também não consegue listar).
- ✅ Credenciais não versionadas (grep dedicado, §8).
- ✅ Testes passam (151/151 vitest).

Nenhum critério de rejeição ocorreu, **com uma ressalva transparente**: um
secret foi impresso momentaneamente nesta sessão por um comando de validação
mal escolhido (§6) — corrigido de imediato por rotação, não por ocultação.
Não há admin, não há permissões excessivas, o bucket não voltou a listar
publicamente, o provider local não foi tocado, e o MinIO continua
plenamente funcional.

## 10. Limitações / riscos remanescentes

| Item | Severidade | Nota |
|---|---|---|
| `s3:GetObject` concedido ao utilizador de serviço sem uso actual no código | Muito baixo | Decisão deliberada (§2) — mesmo nível que a leitura pública já concede a qualquer pessoa; não amplia a superfície de risco real |
| `minio-bucket-init` só corre num `docker compose up`/`run` explícito, não automaticamente a cada `apps-up.ps1` | Baixo | Comportamento pré-existente (fase 06); operador deve reexecutar `minio-bucket-init` se recriar o volume MinIO do zero |
| Rotação de `MINIO_RENDERER_PASSWORD` ainda é manual (editar os dois ficheiros `.env.staging.local` + reexecutar `minio-bucket-init` + reiniciar o Content Renderer) | Baixo | Mesmo padrão já aceite para `INTERNAL_API_TOKEN` na fase 06 (Prompt 05); não é um problema novo desta tarefa |
| O contentor MinIO foi recriado (`docker compose up minio-bucket-init`) durante esta iteração | Nenhum | Volumes nomeados (`chartrex_staging_minio_data`) são persistentes — confirmado que nenhum dado anterior foi perdido |

## 11. Próximo passo recomendado

1. Seguir para **STG-HARD-006/007** (cleanup/diagnóstico) ou **STG-HARD-001**
   (E2E, ainda com trabalho preparatório pendente de execução real) conforme
   prioridade do operador.
2. Se algum dia for necessário que o Content Renderer leia os seus próprios
   objectos de volta (hoje não acontece), a policy já cobre isso —
   nenhuma alteração adicional seria necessária.
3. Considerar automatizar a rotação de `MINIO_RENDERER_PASSWORD` junto com a
   de `INTERNAL_API_TOKEN` (mesma disciplina, ainda manual) — não decidido
   aqui, apenas anotado.
