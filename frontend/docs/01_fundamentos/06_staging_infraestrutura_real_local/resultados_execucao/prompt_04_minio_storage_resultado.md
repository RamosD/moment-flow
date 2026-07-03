# Prompt 04 — Implementar MinIO storage — Resultado

**Data:** 2026-07-03
**Fase:** `06_staging_infraestrutura_real_local` (STG-LOCAL-004)
**Âmbito:** implementar e validar o provider S3-compatible/MinIO no Content
Renderer, usando o container MinIO da fase como object storage staging
local. Sem alterar Backend Core além do necessário para o smoke real.
**Estado de execução:** `executado` — provider `s3` implementado atrás da
mesma interface `StorageProvider`, 151/151 testes do Content Renderer
verdes (incluindo o provider `local` original, sem regressão), upload e
download reais validados nos três tipos de job
(`report_generation`/`media_kit_generation`/`content_generation`) contra o
MinIO do container, `Asset.public_url` preenchido e efectivamente
descarregável no Backend Core.

---

## 1. Nota sobre o caminho da pasta

Como nos prompts anteriores, os documentos desta execução foram criados em
`frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/`, a
pasta real do repositório.

## 2. Provider implementado

Decisão de nomenclatura: `STORAGE_PROVIDER=s3` (não `minio`). Justificação:
`backend_core/apps/core/models.py` já define `Asset.StorageProvider` com 4
opções (`local`, `s3`, `r2`, `gcs`) — MinIO é S3-compatible, por isso o
callback do Content Renderer reporta `storage_provider: 's3'`, reaproveitando
o valor de enum já existente em Django **sem exigir nenhuma alteração ao
Backend Core** (regra explícita do prompt: "Não alterar Backend Core
desnecessariamente se `Asset.public_url` já está implementado" — cumprida:
zero alterações a `backend_core/`).

| Camada | Ficheiro | Alteração |
|---|---|---|
| Contrato de tipos | `content_renderer/src/jobs/job.types.ts` | `AssetMetadata.storage_provider`: `'local'` → `'local' \| 's3'` |
| Contrato de tipos | `content_renderer/src/storage/storage.types.ts` | `StorageProviderName`: `'local'` → `'local' \| 's3'` |
| Config/env | `content_renderer/src/config/env.ts` | `KNOWN_STORAGE_PROVIDERS` inclui `s3`; nova função `validateStorageConfig` (fail-fast, só quando `STORAGE_PROVIDER=s3`); 7 novos campos em `AppConfig` |
| Provider | `content_renderer/src/storage/s3-storage.ts` (**novo**) | Implementa `StorageProvider` com `@aws-sdk/client-s3` (`PutObjectCommand`); aceita um `S3Client` injectável (parâmetro opcional) para testes unitários sem tocar na rede |
| Factory | `content_renderer/src/storage/storage.factory.ts` | Novo `case 's3'`; log de arranque sem credenciais (`endpoint`, `bucket`, `force_path_style` — nunca `access_key`/`secret_key`) |
| Dependência | `content_renderer/package.json` | `@aws-sdk/client-s3@^3.1079.0` adicionada |

O provider `local` (filesystem) **não foi alterado** e continua o default
(`STORAGE_PROVIDER=local` se a variável não for definida) — confirmado por
teste dedicado (`does not require S3 variables when STORAGE_PROVIDER=local`)
e pela suite completa a passar.

## 3. Variáveis de ambiente (sem valores)

Documentadas com comentários em `content_renderer/.env.example`. Todas as
quatro primeiras são **obrigatórias apenas quando `STORAGE_PROVIDER=s3`**
(o boot falha rápido, com `ConfigError`, se alguma faltar); são ignoradas
quando `STORAGE_PROVIDER=local`.

| Variável | Obrigatória com `s3`? | Default |
|---|---|---|
| `STORAGE_PROVIDER` | — | `local` |
| `STORAGE_ENDPOINT` | Sim | *(nenhum)* |
| `STORAGE_BUCKET` | Sim | *(nenhum)* |
| `STORAGE_ACCESS_KEY` | Sim | *(nenhum — nunca commitado)* |
| `STORAGE_SECRET_KEY` | Sim | *(nenhum — nunca commitado)* |
| `STORAGE_REGION` | Não | `us-east-1` (MinIO ignora o valor, mas o SDK exige que exista) |
| `STORAGE_FORCE_PATH_STYLE` | Não | `true` (necessário para MinIO/self-hosted) |
| `STORAGE_PUBLIC_BASE_URL` | Não | `"<STORAGE_ENDPOINT>/<STORAGE_BUCKET>"` (path-style) quando omitida |

## 4. Ficheiros criados/alterados

| Ficheiro | Operação |
|---|---|
| `content_renderer/src/storage/s3-storage.ts` | **criado** |
| `content_renderer/src/jobs/job.types.ts` | alterado (tipo `storage_provider`) |
| `content_renderer/src/storage/storage.types.ts` | alterado (`StorageProviderName`) |
| `content_renderer/src/config/env.ts` | alterado (novas variáveis + validação) |
| `content_renderer/src/storage/storage.factory.ts` | alterado (novo `case 's3'`) |
| `content_renderer/.env.example` | alterado (novas variáveis documentadas) |
| `content_renderer/package.json` / `package-lock.json` | alterado (`@aws-sdk/client-s3`) |
| `content_renderer/tests/storage.test.ts` | alterado + novo `describe` para o provider S3 |
| `content_renderer/tests/env.test.ts` | alterado (2 testes antigos assumiam `s3` rejeitado; 7 novos testes cobrem a validação `s3`) |
| `docker-compose.staging.local.yml` | alterado — `minio-bucket-init` passa a definir também `mc anonymous set download` no bucket (ver §7) |
| `content_renderer/.env.staging.local` | **criado**, ignorado pelo git (`STORAGE_PROVIDER=s3` apontando ao MinIO do container) |
| **`content_renderer/.gitignore`** | **corrigido** — ver §8, achado crítico não relacionado a features |
| `frontend/docs/.../06_staging_infraestrutura_real_local/arquitectura_staging_local.md` | actualizado (§13 riscos LOCAL-R05/R06, §15 decisões pendentes → fechadas) |
| `frontend/docs/.../resultados_execucao/prompt_04_minio_storage_resultado.md` | **criado** (este relatório) |

`backend_core/` **não foi alterado** nesta iteração — só o seu ficheiro de
env local (`backend_core/.env.staging.local`, já criado no Prompt 03) foi
ajustado para `EXTERNAL_JOBS_DRY_RUN=false` e ganhou o `INTERNAL_API_TOKEN`
partilhado, ambos fora de código versionado.

## 5. Testes

```text
npx tsc --noEmit        → sem erros
npx eslint .             → sem erros/avisos
npx vitest run           → 151/151 passed, 13/13 ficheiros
```

Novos testes (provider S3, `tests/storage.test.ts`): upload via
`PutObjectCommand` com metadata Django-compatível; checksum sha256 idêntico
ao provider local; mime/width/height explícitos; rejeição de path traversal
**sem** chamar o cliente S3; erro de upload embrulhado em
`StorageFailedError` **sem vazar credenciais** (asserção explícita:
`JSON.stringify(error.toJSON())` não contém nem a access key nem a secret
key); contrato `Asset` inalterado (mesmas 11 chaves); `createStorageProvider`
devolve um provider `s3` sem qualquer chamada de rede (construção do
`S3Client` é preguiçosa). Os testes usam um `S3Client` falso injectado
(`vi.fn`), sem tocar no MinIO real — validação unitária pura, rápida e
determinística.

Novos testes (`tests/env.test.ts`, `STORAGE_PROVIDER=s3`): aceita a
configuração completa com defaults corretos; honra
`STORAGE_PUBLIC_BASE_URL` explícito; honra `STORAGE_FORCE_PATH_STYLE=false`;
rejeita cada uma das 4 variáveis obrigatórias em falta, uma de cada vez
(`it.each`); confirma que `STORAGE_PROVIDER=local` não exige nenhuma delas.

Dois testes pré-existentes assumiam que `STORAGE_PROVIDER=s3` era
**rejeitado** — actualizados para usar `r2` (que continua não implementado)
como o caso "provider desconhecido", já que `s3` passou a ser válido por
desenho deste prompt.

**Flake não relacionado, confirmado e não corrigido por não ser desta
fase:** `tests/jobs.test.ts` falhou uma vez isoladamente
(`waitUntil: condition not met within timeout`, num teste de despacho de
`report_generation` em background) sob carga elevada da máquina (pytest do
Prompt 03 a correr em paralelo); re-executado isoladamente e em conjunto
logo a seguir, passou de forma consistente (151/151, duas vezes). Não toca
em storage.

## 6. Smoke real (todos os três tipos de job, contra o MinIO do container)

Infra usada: containers `chartrex_staging_postgres`/`chartrex_staging_minio`
(já activos desde os Prompts 02/03), Backend Core em
`127.0.0.1:8100` (`DB_ENGINE=postgres`, `EXTERNAL_JOBS_DRY_RUN=false`),
Content Renderer em `localhost:8202` (`STORAGE_PROVIDER=s3`, apontado ao
MinIO em `http://127.0.0.1:9000`), `INTERNAL_API_TOKEN` partilhado entre os
dois (gerado localmente, nunca commitado, nunca impresso).

| Job | Endpoint de criação | Resultado |
|---|---|---|
| `report_generation` | `POST /api/v1/reports/` | `status: completed`, `storage_asset` preenchido |
| `media_kit_generation` | `POST /api/v1/media-kits/` | `status: generated`, `storage_asset` preenchido |
| `content_generation` | `POST /api/v1/content-pack-requests/` | `status: completed`, 2 `content-outputs`, ambos com `storage_asset` |

Logs estruturados do Content Renderer confirmam o ciclo completo por job:
`job.accepted` → `job.scheduled` → `render.started` → `*.render_finished`
→ `render.completed` → `callback.started` → `callback.attempt_started` →
`callback.completed` (`http_status: 200`).

## 7. Evidência MinIO (upload e download reais)

```text
$ mc ls --recursive local/chartrex-staging
 64KiB  workspaces/<ws>/jobs/<job>/output_001.png
 64KiB  workspaces/<ws>/jobs/<job>/output_002.png
1.1KiB  workspaces/<ws>/jobs/<job>/media_kit.pdf
1.1KiB  workspaces/<ws>/jobs/<job>/report.pdf
```

Os 4 objectos esperados (1 report, 1 media kit, 2 content outputs) existem
de facto no bucket.

**Achado real durante a validação — bucket privado por default:** a
primeira tentativa de download via `Asset.public_url`
(`http://127.0.0.1:9000/chartrex-staging/...`) devolveu **`HTTP 403`** (XML
de erro do MinIO), porque um bucket MinIO novo não permite leitura anónima
por default — ao contrário do provider `local`, que já serve `/files/*` sem
qualquer autenticação. Isto teria violado o critério de aceitação "Download
por URL funciona" e o critério de rejeição "Deixar `public_url` vazio"
(vazio na prática, porque inacessível).

**Decisão tomada e documentada** (regra explícita do prompt: "Não expor
bucket com política insegura sem documentar"): apliquei
`mc anonymous set download local/chartrex-staging`, que concede **apenas
leitura** anónima (sem listagem do bucket, sem escrita, sem
delete) — o mínimo necessário para paridade com o comportamento já existente
do provider `local`. Este passo foi incorporado no serviço
`minio-bucket-init` do `docker-compose.staging.local.yml` (não é um comando
manual avulso — corre sempre que a infraestrutura é recriada). Documentado
como decisão explícita de **staging local, não de produção** tanto no
compose como em `arquitectura_staging_local.md` §13 (LOCAL-R05).

Após a política aplicada, os 4 objectos foram descarregados com sucesso:

| Objecto | Content-Type | Tamanho | HTTP |
|---|---|---|---|
| `report.pdf` | `application/pdf` | 1159 bytes | `200` |
| `media_kit.pdf` | `application/pdf` | 1127 bytes | `200` |
| `output_001.png` | `image/png` | 65418 bytes | `200` |
| `output_002.png` | `image/png` | 65418 bytes | `200` |

`report.pdf` foi ainda inspeccionado por assinatura de ficheiro
(`file`/`xxd`) e confirmado como PDF 1.7 real, não um placeholder.

## 8. Achado crítico não relacionado a features: `content_renderer/.gitignore` escondia `src/storage/` de todo o histórico do git

Ao correr `git status` para listar os ficheiros alterados por este prompt,
`content_renderer/src/storage/` não aparecia — nem os ficheiros novos, nem
as alterações aos existentes. Investigação (`git check-ignore -v`,
`git log -- content_renderer/src/storage/`) confirmou:

```text
content_renderer/.gitignore, linha 18 (antes): "storage/"
```

Este padrão **não estava ancorado à raiz** do `.gitignore` (que fica em
`content_renderer/`), pelo que o git o interpreta como "qualquer directoria
chamada `storage` em qualquer profundidade" — incluindo
`content_renderer/src/storage/`, a directoria que contém a própria
abstracção `StorageProvider` (`local-storage.ts`, `storage.factory.ts`,
`storage.types.ts`). `git log --all -- content_renderer/src/storage/`
devolveu **zero commits**: estes três ficheiros nunca foram versionados,
desde que foram criados (fases anteriores, R-HARD-005) — um bug pré-existente,
não introduzido nesta iteração, apenas descoberto por ela.

**Corrigido nesta iteração** (âmbito mínimo, sem tocar em mais nada):

```diff
- storage/
+ /storage/
```

O `/` inicial ancora o padrão à raiz de `content_renderer/`, continuando a
ignorar correctamente a directoria de storage local de runtime
(`content_renderer/storage/`, ficheiros gerados) sem voltar a apanhar
`src/storage/`. Confirmado com `git check-ignore -q` para os dois casos
depois da correcção — `content_renderer/storage` continua ignorado,
`content_renderer/src/storage/*.ts` deixa de estar. Isto significa que este
relatório inclui, pela primeira vez no repositório, `local-storage.ts` e
`storage.factory.ts` como ficheiros efectivamente versionáveis — não são
"criados" por este prompt, mas o seu estado de tracking foi corrigido por
ele.

## 9. Validações executadas

| Validação | Resultado |
|---|---|
| `npx tsc --noEmit` (Content Renderer) | ✅ sem erros |
| `npx eslint .` (Content Renderer) | ✅ sem erros/avisos |
| `npx vitest run` (Content Renderer) | ✅ 151/151 (13/13 ficheiros) |
| Smoke real `report_generation` | ✅ `completed`, asset em MinIO |
| Smoke real `media_kit_generation` | ✅ `generated`, asset em MinIO |
| Smoke real `content_generation` | ✅ `completed`, 2 outputs, ambos com asset em MinIO |
| `Asset.storage_provider` | ✅ `"s3"` |
| `Asset.storage_key` | ✅ `workspaces/<ws>/jobs/<job>/<file>` (mesmo layout do provider local) |
| `Asset.public_url` | ✅ preenchido, formato `http://127.0.0.1:9000/chartrex-staging/...` |
| Download real via `public_url` (4 objectos) | ✅ todos `HTTP 200`, tipos/tamanhos correctos |
| `mc ls --recursive` no bucket | ✅ 4 objectos confirmados fisicamente presentes |
| `scripts/check-forbidden-ports.ps1` | ✅ OK |
| Grep de `STORAGE_ACCESS_KEY=`/`STORAGE_SECRET_KEY=`/`INTERNAL_API_TOKEN=` seguidos de valor, em todos os ficheiros alterados neste prompt | ✅ 0 ocorrências — só nomes de variável, nunca valores |
| `git check-ignore -q content_renderer/.env.staging.local` | ✅ ignorado |
| `git status` após a correcção do `.gitignore` | ✅ `content_renderer/src/storage/` agora visível como código a rastrear |
| Provider `local` sem regressão | ✅ testes originais do `local-storage.ts` continuam a passar; `STORAGE_PROVIDER=local` continua default e não exige as variáveis S3 |

## 10. Limitações

- A política de leitura anónima (`mc anonymous set download`) é uma decisão
  explícita para **staging local**, não uma recomendação para produção — um
  ambiente de produção real exigiria `signed_url` com expiração ou um proxy
  autenticado; `signed_url` continua sem campo dedicado no Backend Core
  (decisão pendente, herdada da fase 05, fora do âmbito deste prompt).
- `STORAGE_REGION` é exigida pelo SDK da AWS mas o MinIO ignora o seu valor
  — mantido com um default inofensivo (`us-east-1`) para não introduzir
  fricção desnecessária.
- O checksum é calculado no cliente (sha256 sobre o buffer antes do
  upload), não a partir do `ETag` devolvido pelo MinIO — decisão consciente
  para manter o mesmo algoritmo/campo (`checksum`) usado pelo provider
  `local`, já que o `ETag` do S3 é MD5 apenas para uploads de parte única e
  não-MD5 para multipart.
- Este prompt não testou o cenário "MinIO down" (Content Renderer a falhar
  o upload) além do teste unitário com um cliente falho — a validação real
  desse cenário de falha pertence a STG-LOCAL-010 (observabilidade local).
- `content_renderer/src/storage/s3-storage.ts` foi implementado com um
  parâmetro `client?: S3Client` opcional para permitir injecção em testes.
  É a única concessão de design feita para testabilidade; não afecta o
  caminho de produção (a factory nunca o passa).

## 11. Riscos

| Risco | Situação após este prompt |
|---|---|
| LOCAL-R05 — `public_url` inacessível | **Resolvido**, ver §7 — bucket com leitura anónima documentada, download confirmado |
| LOCAL-R06 — Content Renderer quebra o modo local | **Não se materializou** — 151/151 testes verdes, incluindo os do provider `local` original |
| Bucket com leitura pública (decisão nova, não do backlog original) | **Aceite conscientemente para staging local**; documentado em 3 sítios (compose, arquitectura, este relatório) como não-replicável em produção sem decisão própria |
| `content_renderer/.gitignore` escondia código de produção do histórico do git | **Corrigido nesta iteração** — risco crítico pré-existente, agora eliminado; recomendo verificar se outras pastas do repositório têm o mesmo padrão de `.gitignore` não ancorado (fora do âmbito desta fase, mas vale a pena uma auditoria dedicada) |
| Credenciais MinIO (`STORAGE_ACCESS_KEY`/`STORAGE_SECRET_KEY`) reutilizam as credenciais "root" do MinIO | Aceitável para staging local descartável; criar credenciais dedicadas não-root ficaria para STG-LOCAL-005 (secrets), se considerado necessário |

## 12. Próximo passo recomendado

Avançar para **STG-LOCAL-005** (Prompt 05 do pipeline): formalizar o
mecanismo de secrets locais (nome de ficheiro único e documentado,
substituindo os `*.env.staging.local` ad-hoc criados nos Prompts 03/04por
convenção, validar rotação do `INTERNAL_API_TOKEN` partilhado entre os três
serviços, e confirmar que nenhum destes ficheiros ficou por gitignorar —
aproveitando o achado do §8 para, se fizer sentido, auditar outros
`.gitignore` do repositório pelo mesmo tipo de padrão não ancorado.
