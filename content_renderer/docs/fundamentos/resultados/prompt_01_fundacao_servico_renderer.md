# Relatório de Execução — Prompt 01: Fundação do Serviço Renderer

- **Data:** 2026-06-22
- **Pipeline:** 01 — Fundação do serviço renderer
- **Épico/Tarefas do backlog:** CR-001 (projecto), CR-002 (configuração por ambiente), CR-003 (logger estruturado)
- **Serviço:** `content_renderer`
- **Localização:** `D:\Workspace\ChartRex\momentflow\content_renderer`

---

## 1. Prompt executado

Criar a fundação técnica do serviço **Content/Report Renderer**, separado do
`backend_core` Django, responsável por receber jobs, gerar activos mínimos e
devolver callback ao Django. Esta primeira fase cobre apenas a fundação:
inicializar o projecto Node.js + TypeScript, configurar `package.json` e
`tsconfig.json`, criar a estrutura `src/`, o endpoint `GET /health`, o
`.env.example`, o loader e validação de ambiente, o logger estruturado (sem
expor o token), o `README.md` inicial e testes mínimos. **Sem** implementar
`POST /jobs`, renderização real, callback real, vídeo/Remotion/FFmpeg, nem
autenticação/RBAC/billing próprios.

Backlog de referência: `docs/fundamentos/01_backlog_content_report_renderer.md`.

---

## 2. Objectivo

Estabelecer uma base técnica funcional, simples e confiável para o renderer, que
arranque localmente e exponha um healthcheck, com toda a estrutura de pastas e
módulos (scaffold) pronta para as fases seguintes, respeitando a tese
arquitectural: **o Django governa o produto; o renderer apenas gera activos**.

---

## 3. Ficheiros criados

### Configuração de projecto (raiz)

- `package.json` — metadados, scripts e dependências.
- `tsconfig.json` — configuração TypeScript (strict, NodeNext, output `dist/`).
- `eslint.config.mjs` — ESLint flat config (ESLint 10 + typescript-eslint).
- `vitest.config.ts` — configuração de testes.
- `.env.example` — template de ambiente com as variáveis mínimas.
- `.gitignore` — ignora `node_modules/`, `dist/`, `.env`, `storage/`, etc.
- `README.md` — instalação, scripts, `.env`, healthcheck, estrutura, limitações.

### Código-fonte (`src/`)

- `src/app.ts` — factory pura da app Express (testável).
- `src/server.ts` — entrypoint: carrega config, faz `listen`, graceful shutdown.
- `src/constants.ts` — `RENDERER_NAME`, `RENDERER_VERSION`.
- `src/config/env.ts` — loader e validação de ambiente (CR-002).
- `src/logging/logger.ts` — logger estruturado JSON com redacção de segredos (CR-003).
- `src/errors/errors.ts` — modelo de erros normalizado (`AppError` + códigos CR-801).
- `src/http/routes.ts` — router com `GET /health`.
- `src/http/middleware.ts` — request-context logging + error handler + 404.
- `src/jobs/job.types.ts` — tipos do envelope, job types suportados, callback.
- `src/jobs/job.schema.ts` — schema Zod do envelope (CR-103).
- `src/jobs/job.service.ts` — dispatcher por `job_type` (scaffold, CR-202).
- `src/jobs/job.controller.ts` — handler `POST /jobs` (scaffold, **não ligado**).
- `src/renderers/renderer.types.ts` — `RenderContext` / `Renderer`.
- `src/renderers/content/index.ts` — renderer `content_generation` (scaffold).
- `src/renderers/reports/index.ts` — renderer `report_generation` (scaffold).
- `src/renderers/media-kits/index.ts` — renderer `media_kit_generation` (scaffold).
- `src/templates/registry.ts` — registry de templates (scaffold, CR-401).
- `src/storage/local-storage.ts` — storage local (scaffold, CR-301).
- `src/callbacks/callback.client.ts` — cliente de callback (scaffold, CR-503).

### Testes (`tests/`)

- `tests/health.test.ts` — `GET /health` devolve 200 + 404 normalizado.
- `tests/env.test.ts` — loader de ambiente, incluindo rejeição de token vazio em production.
- `tests/logger.test.ts` — redacção: o logger nunca imprime o token.

### Documentação

- `docs/fundamentos/resultados/prompt_01_fundacao_servico_renderer.md` — este relatório.

---

## 4. Ficheiros alterados

Nenhum ficheiro pré-existente do repositório foi modificado. Antes desta
execução existiam apenas `docs/` (backlog + placeholder de prompts) e
`.claude/settings.local.json`, que permanecem intactos.

Durante a própria execução, três ficheiros recém-criados foram iterados para
acomodar as versões major instaladas e melhorar a higiene dos logs:

- `tsconfig.json` — `moduleResolution`/`module` ajustados para `NodeNext`
  (TypeScript 6 deprecou `node10`).
- `src/config/env.ts` — helper interno renomeado (`requireString` →
  `stringOrDefault`, removido parâmetro não usado) e `dotenv` em modo `quiet`.
- `src/server.ts` — campo de log `insecure_token_mode` → `insecure_mode` (para
  não ser redigido pela regra de segredos e manter o sinal operacional visível).

---

## 5. Dependências instaladas

### Runtime (`dependencies`)

| Pacote    | Versão     | Uso                                  |
| --------- | ---------- | ------------------------------------ |
| `express` | `^5.2.1`   | Servidor HTTP                        |
| `zod`     | `^4.4.3`   | Schema do envelope de job (CR-103)   |
| `dotenv`  | `^17.4.2`  | Carregamento de `.env`               |

### Desenvolvimento (`devDependencies`)

| Pacote               | Versão      | Uso                          |
| -------------------- | ----------- | ---------------------------- |
| `typescript`         | `^6.0.3`    | Compilador / typecheck       |
| `tsx`                | `^4.22.4`   | Execução em dev (`dev`)      |
| `vitest`             | `^4.1.9`    | Runner de testes             |
| `supertest`          | `^7.2.2`    | Testes HTTP do `/health`     |
| `@types/express`     | `^5.0.6`    | Tipos                        |
| `@types/node`        | `^26.0.0`   | Tipos                        |
| `@types/supertest`   | `^7.2.0`    | Tipos                        |
| `eslint`             | `^10.5.0`   | Linter                       |
| `@eslint/js`         | `^10.0.1`   | Regras base ESLint           |
| `typescript-eslint`  | `^8.61.1`   | Integração TS no ESLint      |
| `globals`            | `^17.6.0`   | Globals Node para o ESLint   |

> Sem dependências pesadas (sem Sharp, Playwright, Remotion, FFmpeg) — alinhado
> com a restrição da fase de fundação.

---

## 6. Scripts disponíveis

| Script               | Comando                | Descrição                          |
| -------------------- | ---------------------- | ---------------------------------- |
| `npm run dev`        | `tsx watch src/server.ts` | Arranque em watch                |
| `npm run build`      | `tsc -p tsconfig.json` | Compila para `dist/`               |
| `npm start`          | `node dist/server.js`  | Corre o build                      |
| `npm test`           | `vitest run`           | Testes (one-shot)                  |
| `npm run test:watch` | `vitest`               | Testes em watch                    |
| `npm run lint`       | `eslint .`             | Lint                               |
| `npm run typecheck`  | `tsc --noEmit`         | Verificação de tipos               |

---

## 7. Comandos executados

```bash
# Versões
node -v            # v22.14.0
npm -v             # 10.9.2

# Instalação
npm install express zod dotenv
npm install -D typescript tsx vitest supertest @types/express @types/node \
  @types/supertest eslint @eslint/js typescript-eslint globals

# Validações
npm run build      # tsc
npm run lint       # eslint .
npm test           # vitest run

# Arranque local + healthcheck
INTERNAL_API_TOKEN=local-dev-token NODE_ENV=development PORT=8002 node dist/server.js
curl http://localhost:8002/health        # 200
curl http://localhost:8002/nope          # 404

# Smoke test da regra de token em produção
NODE_ENV=production INTERNAL_API_TOKEN= node dist/server.js   # exit code 1
```

---

## 8. Resultado das validações

| Validação                                   | Resultado |
| ------------------------------------------- | --------- |
| `npm install`                               | ✅ 0 vulnerabilidades |
| `npm run build` (tsc)                       | ✅ Sem erros |
| `npm run lint` (eslint)                     | ✅ Sem erros |
| `npm test` (vitest)                         | ✅ 3 ficheiros, **14 testes** passados |
| Arranque local                              | ✅ `server.started` na porta 8002 |
| `GET /health`                               | ✅ HTTP **200** com identidade do serviço |
| Rota desconhecida                           | ✅ HTTP **404** normalizado (`code: not_found`) |
| Production rejeita token vazio              | ✅ Log `config.invalid` + **exit code 1** |
| Logger não expõe `INTERNAL_API_TOKEN`       | ✅ Token nunca aparece nos logs; chaves sensíveis → `[REDACTED]` |

Exemplo de log de arranque (token não presente, sinal de modo visível):

```json
{"level":"info","time":"2026-06-22T12:58:20.735Z","msg":"server.started","service":"content_renderer","version":"0.1.0","port":8002,"node_env":"development","insecure_mode":false}
```

Resposta do healthcheck:

```json
{"status":"ok","service":"content_renderer","version":"0.1.0","uptime_seconds":3,"timestamp":"2026-06-22T12:58:23.855Z"}
```

---

## 9. Decisões tomadas

1. **Localização:** a pasta `content_renderer` já existia (é a raiz de trabalho);
   o projecto Node.js foi inicializado directamente nela.
2. **Framework HTTP:** Express (recomendado no backlog) pela simplicidade. As
   dependências resolveram para majors actuais (Express 5, Zod 4, TypeScript 6,
   ESLint 10) — mantidas por serem stable e mais à prova de futuro; o código foi
   ajustado onde a API mudou.
3. **Módulos:** CommonJS via `module/moduleResolution: NodeNext` (TS 6 deprecou
   `node10`); o pacote não é `type: module`, logo o emit é CommonJS.
4. **Logger próprio (zero-dependency) em vez de Pino:** escolhido para garantir
   redacção **recursiva** de chaves sensíveis (`token`, `secret`, `authorization`,
   `api_key`, …) com total controlo e sem dependência adicional. A interface
   permite trocar por Pino mais tarde sem alterar call sites.
5. **Modo inseguro local explícito:** em `development`, token vazio só é aceite
   com `ALLOW_INSECURE_EMPTY_TOKEN=true`; em `test` é permitido para a suite
   correr sem segredos; em `production` é sempre rejeitado.
6. **`env.ts` como função pura (`loadConfig(source)`):** facilita testes e evita
   efeitos colaterais no import durante os testes.
7. **Scaffolds inertes:** controller, service/dispatcher, renderers, registry,
   storage e callback client foram criados com a interface final mas lançam
   `NotImplementedError` (HTTP 501), deixando claro o ponto de integração das
   próximas fases sem implementar comportamento real.
8. **`POST /jobs` não registado:** apenas o `GET /health` está ligado ao router,
   respeitando a restrição da fase.

---

## 10. Pendências

Tudo o que está fora do escopo desta fase permanece pendente para os próximos
pipelines:

- **Pipeline 02:** middleware de auth interna (`X-Internal-Token`), validação de
  headers vs body, schema aplicado e endpoint `POST /jobs` (CR-101/102/103/201).
- **Pipeline 03:** storage local real (escrita, checksum, mime) e callback client
  real (fetch + timeout + retry) (CR-301/302/503).
- **Pipeline 04:** template engine e render SVG → PNG com Sharp (CR-401/402/403).
- **Pipelines 05–07:** `content_generation`, `report_generation`,
  `media_kit_generation` reais.
- **Pipelines 08–10:** erros/partial success, testes E2E com callback mockado,
  teste manual com o Backend Core e documentação de estado
  (`02_estado_content_report_renderer.md`).
- `storage/` local continua a ser **apenas dev** — não é storage de produção.

---

## 11. Próximo passo recomendado

Avançar para o **Pipeline 02 — Segurança, schema e endpoint de jobs**:

1. Implementar o middleware de autenticação interna (`X-Internal-Token`) com
   comparação segura e rejeição de token ausente/errado/vazio.
2. Validar a consistência entre headers (`X-Workspace-ID`, `X-Job-ID`,
   `X-Request-ID`) e o body.
3. Ligar o `jobEnvelopeSchema` (Zod) ao handler e registar `POST /jobs`,
   respondendo `202` quando o job é aceite e despachando para o dispatcher.

Critério de pronto do próximo passo: `POST /jobs` aceita `content_generation`
válido (202), rejeita token inválido (403) e payload inválido (400), com testes
a cobrir cada caso.
