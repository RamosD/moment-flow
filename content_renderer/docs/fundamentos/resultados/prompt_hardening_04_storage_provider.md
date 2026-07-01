# Relatório de Execução — Hardening 04: Interface de storage para S3/R2 (R-HARD-005)

- **Serviço:** `content_renderer`
- **Data:** 2026-06-23
- **Backlog de referência:** [`03_backlog_hardening_pos_mvp_renderer.md`](../03_backlog_hardening_pos_mvp_renderer.md) → **R-HARD-005**

---

## 1. Prompt executado

Preparar a interface de storage para futura migração para S3/R2, mantendo o
`LocalStorage` funcional e **sem mudar** o contrato de `Asset`. Esta fase **não**
implementa S3/R2 nem adiciona SDK AWS/R2 — apenas cria uma abstracção limpa para
que os renderers não dependam da implementação local.

## 2. Objectivo

Separar **interface** de **implementação** de storage: introduzir
`StorageProvider`, fazer o `LocalStorage` implementá-lo, centralizar tipos, criar
a factory `createStorageProvider(config, logger)` e validar `STORAGE_PROVIDER` no
arranque — com os renderers a dependerem da abstracção, não do concreto.

## 3. Ficheiros criados

| Ficheiro | Propósito |
|---|---|
| `src/storage/storage.types.ts` | Tipos centralizados: `StorageProvider`, `LocalStorageProvider`, `SaveBufferInput`, `StorageProviderName`, re-export de `AssetMetadata`, e o type-guard `isLocalStorageProvider`. |
| `src/storage/storage.factory.ts` | `createStorageProvider(config, logger)` — selecciona o provider por `STORAGE_PROVIDER`; guarda defensiva para provider desconhecido. |
| `docs/fundamentos/resultados/prompt_hardening_04_storage_provider.md` | Este relatório. |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `src/storage/local-storage.ts` | `createLocalStorage` devolve `LocalStorageProvider` (`name:'local'` + `getPublicUrl`); `SaveBufferInput`/`LocalStorage` re-exportados dos tipos centralizados (compat). |
| `src/config/env.ts` | Novo `storageProvider` em `AppConfig` + `parseStorageProvider` (aceita `local`; desconhecido → `ConfigError` no arranque). |
| `src/renderers/renderer.types.ts` | `RenderContext.storage: StorageProvider` (deixa de depender do `LocalStorage` concreto). |
| `src/jobs/job.service.ts` | `JobServiceDeps.storage: StorageProvider`. |
| `src/http/routes.ts` | `RouteDeps.storage: StorageProvider`; `/files` só registado se `isLocalStorageProvider(storage)` e fora de produção. |
| `src/http/files.ts` | `createFileHandler(storage: LocalStorageProvider, …)`. |
| `src/app.ts` | Usa `createStorageProvider(config, log)`; `CreateAppOptions.storage: StorageProvider`. |
| `.env.example` | Documenta `STORAGE_PROVIDER=local`. |
| `tests/storage.test.ts` | Suite "storage provider abstraction" (6 testes). |
| `tests/env.test.ts` | Default `storageProvider` + rejeição de provider desconhecido. |
| `tests/{content,report,media-kit}-generation.test.ts`, `tests/background.test.ts`, `tests/hardening.test.ts` | Doubles de storage passam a expor `name` e `getPublicUrl` (continuam a implementar `LocalStorage`). |
| `README.md`, `docs/fundamentos/02_estado_content_report_renderer.md` | Tabela de config, secção de abstracção, estrutura, validações (136 testes), pendências e próximo passo. |

## 5. Nova interface de storage

```text
StorageProvider                         # abstracção que os renderers usam
  ├─ name: StorageProviderName          # 'local' (s3/r2 = futuro)
  ├─ buildStorageKey(ws, job, file)
  └─ saveBuffer(input) → AssetMetadata

LocalStorageProvider extends StorageProvider   # capacidades filesystem (dev)
  ├─ name: 'local'
  ├─ root
  ├─ resolveWithinRoot(rel) → string | null    # usado por GET /files/*
  └─ getPublicUrl(storageKey) → string
```

Tipos centralizados em `storage/storage.types.ts`: `StorageProvider`,
`LocalStorageProvider`, `SaveBufferInput`, `StorageProviderName`, e re-export de
`AssetMetadata` (contrato do `Asset` continua a ser owned por `jobs/job.types`).

## 6. Factory de storage

`createStorageProvider(config, logger): StorageProvider`:
- `STORAGE_PROVIDER=local` → `createLocalStorage(config)` (log
  `storage.provider_initialized`, sem secrets);
- valor desconhecido → `ConfigError` (defensivo; o loader de ambiente já rejeita
  no arranque, por isso o `default` é uma rede de segurança).

## 7. Compatibilidade com LocalStorage

- `createLocalStorage` mantém a mesma assinatura e comportamento; apenas passou a
  devolver `name:'local'` e `getPublicUrl` (a lógica de `public_url` já existia em
  `saveBuffer`, agora extraída para `getPublicUrl`).
- **Contrato de `Asset` inalterado** — teste dedicado verifica que as chaves de
  `AssetMetadata` se mantêm exactamente.
- `GET /files/*` continua funcional em desenvolvimento (testes `files.test.ts`
  inalterados e verdes), agora atrás de `isLocalStorageProvider`.

## 8. Testes criados/alterados

**`tests/storage.test.ts` (+6):** `LocalStorage` implementa `StorageProvider`;
`createStorageProvider(local)` funciona e persiste; `STORAGE_PROVIDER=local`
aceite; desconhecido falha no arranque; factory rejeita provider inválido
(guarda); contrato de `Asset` inalterado.
**`tests/env.test.ts` (+1):** default `local` + rejeição de `s3`.
**Doubles de storage** (4 decorators + 1 stub): passam a expor `name`/`getPublicUrl`.

## 9. Comandos executados

```bash
npm run build   # tsc -p tsconfig.json
npm run lint    # eslint .
npm test        # vitest run
```

## 10. Resultados

| Validação | Resultado |
|---|---|
| `npm run build` | ✅ Sem erros |
| `npm run lint` | ✅ Sem erros |
| `npm test` | ✅ **136 testes** em **13 ficheiros** (129 → 136; +7) |

Critérios de aceitação R-HARD-005:

- ✅ Renderers dependem de `StorageProvider` (via `RenderContext`).
- ✅ `LocalStorage` continua funcional.
- ✅ `STORAGE_PROVIDER=local` funciona.
- ✅ Provider inválido falha com erro claro (loader + factory).
- ✅ Contrato de `Asset` não muda.
- ✅ Endpoint `/files` continua funcional em desenvolvimento.
- ✅ Build, lint e testes passam.

## 11. Pendências

- **Implementação S3/R2** (futuro): adicionar `S3StorageProvider` à factory,
  alargar `StorageProviderName` e a validação, e (se necessário) `AssetMetadata.
  storage_provider`/`bucket` — fora do âmbito desta fase.
- **Sem SDK AWS/R2** adicionado (por desenho); credenciais reais serão tratadas na
  fase de migração.

## 12. Próximo passo recomendado

Avançar para **R-HARD-002 — Harness E2E com PostgreSQL**, preparando o ambiente
multi-processo fiável para validar o loop Django → Renderer → Django (criação de
`Asset`/`ContentOutput`/`Report`/`MediaKit` via callback).
