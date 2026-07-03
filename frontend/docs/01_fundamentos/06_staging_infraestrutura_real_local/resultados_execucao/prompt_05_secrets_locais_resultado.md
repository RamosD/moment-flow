# Prompt 05 — Formalizar secrets locais — Resultado

**Data:** 2026-07-03
**Fase:** `06_staging_infraestrutura_real_local` (STG-LOCAL-005)
**Âmbito:** formalizar o mecanismo local de secrets para toda a stack
(infraestrutura + 4 serviços + E2E), validar rotação real do
`INTERNAL_API_TOKEN` e as falhas seguras. Sem secret store cloud, sem
CI/CD remoto.
**Estado de execução:** `executado` — mecanismo `*.env.staging.local`
consolidado nos 3 serviços com secrets + raiz (infra), rotação real
validada ponta-a-ponta (chamada síncrona ao Intelligence Engine real +
callback assíncrono do Content Renderer via MinIO), dessincronização
simulada e recuperada, IE/CR confirmados a rejeitar token ausente/errado,
greps de segurança limpos.

---

## 1. Resumo objectivo

Não existe ainda CI/CD nem secret store neste repositório (confirmado na
fase 05, `prompt_04_gestao_segredos_resultado.md` — continua verdade, sem
`.github/workflows` nem equivalente). Esta iteração **não inventa** essa
infraestrutura; formaliza o que já vinha a ser usado ad-hoc nos Prompts 02–04
desta fase (ficheiros `*.env.staging.local`, um por serviço com secrets +
um na raiz para a infraestrutura Docker) num mecanismo único, documentado,
com nomes e localizações consistentes, e valida-o com uma rotação real do
`INTERNAL_API_TOKEN` — não apenas revisão de código.

## 2. Mecanismo local definido

**Um ficheiro `*.env.staging.local` por sítio que precisa de secrets,
sempre com o mesmo nome, sempre ignorado pelo git pelo padrão já existente
(`.env.*`), nunca com `.env.staging.local.example` correspondente exigido
(exceto na raiz, onde já existia desde o Prompt 02):**

| Sítio | Ficheiro | Estado nesta iteração |
|---|---|---|
| Infraestrutura Docker (PostgreSQL + MinIO) | `.env.staging.local` (raiz) | **Criado nesta iteração** — antes dependia só dos defaults inline do compose; agora é um ficheiro real, explícito, com os mesmos valores já em uso |
| Backend Core | `backend_core/.env.staging.local` | Já existia (Prompt 03); **token rotacionado** nesta iteração |
| Intelligence Engine | `intelligence_engine/.env.staging.local` | **Criado nesta iteração** (serviço ainda não tinha sido arrancado no pipeline local até agora) |
| Content Renderer | `content_renderer/.env.staging.local` | Já existia (Prompt 04); **token rotacionado** nesta iteração |
| Frontend | *(nenhum)* | Confirmado sem necessidade — o frontend não tem nenhum secret (§7) |
| Playwright E2E | *(nenhum ficheiro próprio)* | Lê `E2E_PASSWORD`/`E2E_RUN_ID`/etc. de `process.env` directamente (`frontend/e2e/global-setup.ts`) — compatível por desenho com o mesmo `E2E_PASSWORD` já presente em `backend_core/.env.staging.local`, ver §3 |

**Como carregar:** nenhum dos quatro serviços lê `*.env.staging.local`
automaticamente por nome (o `python-decouple` do Backend Core e o
`pydantic-settings` do Intelligence Engine só procuram um ficheiro chamado
exactamente `.env`; o `dotenv` do Content Renderer, o mesmo). O mecanismo
usa precedência de variável de ambiente do processo sobre o ficheiro
`.env` versionável — confirmado por leitura de código nas três linguagens
(`decouple.Config.get`, pydantic-settings, `dotenv.config()` não
sobrepõe `process.env` já definido) — pelo que o padrão de arranque é:

```bash
# Padrão usado em todos os serviços Python/Node desta fase:
set -a && . ./<serviço>/.env.staging.local && set +a && <comando de arranque>
```

```powershell
# Docker Compose (raiz) — --env-file é obrigatório para os overrides de
# porta se aplicarem (env_file: dentro do compose só afecta o processo do
# container, não a interpolação ${VAR} do próprio compose — achado
# documentado no compose desde esta iteração):
docker compose --env-file .env.staging.local -f docker-compose.staging.local.yml <comando>
```

Este mecanismo é **compatível, sem alteração de código, com os seis
alvos exigidos pela tarefa 3**:

1. **Docker Compose infra** — `--env-file .env.staging.local` (raiz).
2. **Backend Core** — `set -a && . backend_core/.env.staging.local && set +a`.
3. **Intelligence Engine** — mesmo padrão, `pydantic-settings` já dá
   prioridade a `os.environ`.
4. **Content Renderer** — mesmo padrão, `dotenv.config()` não sobrepõe
   variáveis já presentes em `process.env`.
5. **Frontend** — não aplicável (sem secrets).
6. **Playwright E2E** — herda `process.env` do processo que invoca
   `pnpm test:e2e`; basta ter feito `source` do
   `backend_core/.env.staging.local` (que já contém `E2E_PASSWORD`) antes
   de correr o Playwright.

## 3. Inventário de secrets (sem valores)

| Secret | Definido em | Consumido por | Obrigatório? |
|---|---|---|---|
| `INTERNAL_API_TOKEN` | `backend_core/.env.staging.local`, `intelligence_engine/.env.staging.local`, `content_renderer/.env.staging.local` | Backend Core (envia), Intelligence Engine (valida), Content Renderer (valida + envia no callback) | Sim — deve ser **byte-a-byte idêntico** nos três; vazio ⇒ todos os endpoints internos rejeitam tudo |
| `SECRET_KEY` | `backend_core/.env.staging.local` (herda o default de dev de `config/settings.py` se ausente — nunca definido explicitamente nesta iteração, não foi necessário) | Backend Core (assinatura JWT/sessão Django) | Sim, forte e único fora de dev |
| `DB_PASSWORD` | `.env.staging.local` (raiz, container), `backend_core/.env.staging.local` (cliente) | PostgreSQL (container), Backend Core (ligação) | Sim, quando `DB_ENGINE=postgres` |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | `.env.staging.local` (raiz) | Container MinIO; reutilizadas como `STORAGE_ACCESS_KEY`/`STORAGE_SECRET_KEY` do Content Renderer | Sim |
| `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY` | `content_renderer/.env.staging.local` | Content Renderer (upload para MinIO) | Sim, quando `STORAGE_PROVIDER=s3` |
| `E2E_PASSWORD` | `backend_core/.env.staging.local` | `seed_e2e_run` (Backend Core), Playwright (`frontend/e2e/global-setup.ts`) | Sim, para correr E2E ou `seed_e2e_run` |
| `STRIPE_WEBHOOK_SECRET` / `STRIPE_API_KEY` | `backend_core/.env.example` (vazias por default) | Backend Core (billing, skeleton) | Não — billing continua skeleton, fora do escopo funcional desta fase; confirmado vazio em todos os `.env.staging.local` criados |

**Nota:** `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` (token dedicado opcional do
Backend Core para o IE) foi deliberadamente deixado **ausente** de
`backend_core/.env.staging.local` nas três iterações desta fase — isso
activa o *fallback* já corrigido na fase 05 (`config/settings.py`, reutiliza
`INTERNAL_API_TOKEN`), evitando duplicar o mesmo segredo em duas variáveis.

## 4. `.env.example` — revisão

Todos os quatro `.env.example` de serviço já documentavam os seus secrets
com placeholders seguros **antes** desta iteração (`backend_core` desde
sempre, `content_renderer` actualizado no Prompt 04 com `STORAGE_*`,
`intelligence_engine` inalterado desde a fase 05, `frontend` nunca teve
nenhum). Confirmado por leitura integral dos quatro ficheiros — **nenhuma
alteração foi necessária**. O `.env.staging.local.example` da raiz (criado
no Prompt 02) já cobria `POSTGRES_*`/`MINIO_*`/`STORAGE_BUCKET`; também sem
alterações.

## 5. `.gitignore` — validação

| Serviço/local | Padrão | Estado |
|---|---|---|
| Raiz | `.env`, `.env.*`, `!.env.example`, `!.env.staging.local.example` | ✅ (Prompt 02) |
| `backend_core/.gitignore` | `.env`, `.env.*`, `!.env.example` | ✅ (corrigido na fase 05, STG-PRE-004) |
| `intelligence_engine/.gitignore` | `.env`, `.env.*`, `!.env.example` | ✅ (corrigido na fase 05, STG-PRE-004) |
| `content_renderer/.gitignore` | `.env`, `.env.*`, `!.env.example`, `!.env.e2e.example` | ✅ (já correcto antes da fase 05) |
| `frontend/.gitignore` | `.env`, `.env.*`, `!.env.example` | ✅ (já correcto antes da fase 05) |

Confirmado nesta iteração com `git check-ignore -q` para **todos** os
ficheiros reais existentes (`.env.staging.local` × 4, `backend_core/.env`,
`intelligence_engine/.env`, `content_renderer/.env`,
`frontend/.env.local`) — os 8 devolveram `ignored`. `git ls-files | grep
"\.env\."` (excluindo `.example`) devolveu **zero** resultados — nenhum
ficheiro de secrets real está, nem alguma vez esteve, versionado.

## 6. Rotação testada (INTERNAL_API_TOKEN)

1. **Gerado** um novo valor (`secrets.token_urlsafe(32)`, Python) e escrito
   directamente nos três ficheiros
   (`backend_core`/`intelligence_engine`/`content_renderer`
   `.env.staging.local`) por um script que nunca imprime o valor.
2. **Confirmada a sincronização** comparando **hashes SHA-256** dos três
   valores (nunca os valores em si) → `all_match=True`.
3. **Reiniciados os três serviços** (`Stop-Process` + arranque limpo),
   confirmado um único processo a ocupar cada porta (`8100`/`8201`/`8202`)
   antes de continuar — lição já registada nos Prompts 03/04 desta fase
   sobre processos órfãos a mascarar resultados.
4. **Testado o IE real** (`INTELLIGENCE_ENGINE_DRY_RUN=false`, ligado pela
   primeira vez nesta fase): `POST
   /api/v1/campaigns/{id}/intelligence/` no Backend Core → **`200`**,
   `"source":"engine"`, `"engine":"intelligence_engine"`, resultado real
   (scores, grade, recomendações) — não um stub.
5. **Testado o callback do Content Renderer real**: `POST /api/v1/reports/`
   → job assíncrono → Content Renderer renderiza e chama o callback com o
   token rotacionado → Backend Core aceita (`callback_processed`,
   `status=completed`) → `Report.status="completed"`,
   `storage_asset` preenchido (mesmo padrão já validado no Prompt 04, agora
   com o token novo).

**Nenhum valor de token foi impresso em nenhum momento desta rotação.**

## 7. Falhas seguras testadas

| Cenário | Alvo | Resultado |
|---|---|---|
| Token ausente | `POST http://localhost:8202/jobs` (Content Renderer), sem `X-Internal-Token` | `403 unauthorized` |
| Token errado | idem, com um valor arbitrário | `403 unauthorized` |
| Token ausente | `POST http://127.0.0.1:8201/intelligence/campaign` (Intelligence Engine), sem `X-Internal-Token` | `403 unauthorized_internal_request` |
| Token errado | idem, com um valor arbitrário | `403 unauthorized_internal_request` |
| **Dessincronização real entre serviços** (não só um valor arbitrário) | Alterei **só** o `INTERNAL_API_TOKEN` do Intelligence Engine para um valor diferente do dos outros dois, reiniciei o IE, e chamei o fluxo síncrono real a partir do Backend Core | **`502`**, `{"detail":"Campaign intelligence could not be retrieved from the engine."}` — falha controlada, sem stack trace, sem eco do token, sem crash do Backend Core |
| **Recuperação após ressincronizar** | Restaurei o token do IE para o valor partilhado correcto, reiniciei, repeti a chamada | **`200`**, resultado real — confirma que a causa era exactamente a dessincronização, e que resolvê-la resolve o sintoma |
| `ALLOW_INSECURE_EMPTY_TOKEN` | Grep nos 4 ficheiros `*.env.staging.local` | **Ausente dos quatro** — nunca definido, nunca `true`; o default do Content Renderer continua `false` (`.env.example`) |
| Token vazio em staging local | Nenhum dos quatro `.env.staging.local` tem `INTERNAL_API_TOKEN` vazio | Confirmado — todos os três serviços que o exigem têm-no preenchido e sincronizado |

Cobertura complementar já existente na suite automática do Content Renderer
(`tests/env.test.ts`, não re-executada individualmente nesta iteração por
já fazer parte da suite completa validada no Prompt 04): rejeita token
vazio em produção sempre, rejeita em desenvolvimento sem
`ALLOW_INSECURE_EMPTY_TOKEN=true`, aceita em teste.

## 8. Ficheiros criados/alterados

| Ficheiro | Operação |
|---|---|
| `.env.staging.local` (raiz) | **criado**, ignorado pelo git — infra Docker explícita (antes só defaults inline do compose) |
| `intelligence_engine/.env.staging.local` | **criado**, ignorado pelo git |
| `backend_core/.env.staging.local` | alterado (rotação do token; comentários actualizados; `INTELLIGENCE_ENGINE_DRY_RUN`/`EXTERNAL_JOBS_DRY_RUN` ambos `false` para a validação real) |
| `content_renderer/.env.staging.local` | alterado (rotação do token) |
| `docker-compose.staging.local.yml` | alterado — comentário novo a explicar a exigência de `--env-file` para os overrides de porta |
| `frontend/docs/.../resultados_execucao/prompt_05_secrets_locais_resultado.md` | **criado** (este relatório) |

Nenhum ficheiro de código de produto foi alterado. Nenhum `.env.example`
precisou de alteração (§4).

## 9. Greps de segurança executados

| Grep | Âmbito | Resultado |
|---|---|---|
| `INTERNAL_API_TOKEN=[A-Za-z0-9_-]{10,}` | `git ls-files` (todo o repositório versionado) | 12 ficheiros — todos placeholders/valores de teste já classificados na fase 05 (`real-loop-token-123`, `e2e-shared-token-change-me`, `<INTERNAL_API_TOKEN>`, docs históricos); confirmado individualmente nos dois casos com valor concreto |
| `SECRET_KEY=[A-Za-z0-9_-]{10,}` (excluindo o placeholder conhecido) | `git ls-files` | 0 ocorrências |
| `DB_PASSWORD\|MINIO_ROOT_PASSWORD\|STORAGE_SECRET_KEY\|STORAGE_ACCESS_KEY` com valor | `git ls-files` | Só `postgres` e `chartrex_e2e_dev_only` — placeholders genéricos já documentados como não-secretos desde a fase 05 |
| `ALLOW_INSECURE_EMPTY_TOKEN` | 4× `*.env.staging.local` | Ausente dos quatro |
| `INTERNAL_API_TOKEN`, `X-Internal-Token` | `frontend/src` | 4 ocorrências, todas **defensivas**: `INTERNAL_TOKEN_HEADER` (constante usada para **bloquear activamente** o header antes de sair do browser, `shared/api/security.ts`), `internal_api_token`/`x_internal_token` (chaves na denylist de redacção `SENSITIVE_KEYS`, `recommendation-snapshot.ts`) — nunca um valor |
| `internal_api_token`, `x-internal-token` | `frontend/dist` (build fresco, `npm run build`) | 1 ocorrência cada, **as mesmas duas constantes/denylist acima**, compiladas — confirmado com `grep -o` que a correspondência é a string da chave, não um valor |
| `VITE_[A-Z_]+` | `frontend/dist` | Só `VITE_BACKEND_API_BASE_URL` |
| `:8201`, `:8202` | `frontend/dist` | 0 ocorrências — o bundle nunca referencia Intelligence Engine nem Content Renderer |
| URL base preenchida no bundle | `frontend/dist` | Só `http://localhost:8100/api/v1` |

**Nenhuma ocorrência real de segredo em nenhum ficheiro versionado nem no
bundle do frontend.**

## 10. Outras validações executadas

| Validação | Resultado |
|---|---|
| `python manage.py check` (Backend Core, contra PostgreSQL) | ✅ 0 issues |
| Health Backend Core (`/api/v1/system/health/live/`) | ✅ `200` |
| Health Intelligence Engine (`/health`) | ✅ `200` |
| Health Content Renderer (`/health`) | ✅ `200` |
| Smoke intelligence real (síncrono, token rotacionado) | ✅ `200`, `source=engine` |
| Smoke renderer callback real (assíncrono, token rotacionado, upload MinIO) | ✅ `status=completed`, `storage_asset` preenchido |
| `scripts/check-forbidden-ports.ps1` | ✅ OK |
| `git check-ignore -q` para os 8 ficheiros de secrets reais do repositório | ✅ todos ignorados |
| `git ls-files \| grep "\.env\."` (excluindo `.example`) | ✅ 0 resultados |

## 11. Limitações

- **Mecanismo de fornecimento para um eventual staging não-local continua
  por escolher** — decisão de infraestrutura fora do âmbito desta fase
  (herdado da fase 05, reafirmado aqui: não existe CI/CD nem secret store
  neste repositório).
- **Rotação continua manual**, sem calendário nem automação — esta
  iteração documenta e valida o procedimento, não o agenda.
- **Credenciais MinIO reutilizam a conta "root"** do container
  (`MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` = `STORAGE_ACCESS_KEY`/`STORAGE_SECRET_KEY`)
  — criar uma credencial dedicada não-root ficaria como melhoria futura, não
  bloqueante para staging local.
- **`STRIPE_*` continua fora do escopo funcional** — confirmado vazio, não
  testado (billing ainda skeleton).
- O `.env.staging.local` da raiz define credenciais **idênticas** às que já
  estavam em uso desde o Prompt 02 (não rotacionadas nesta iteração,
  porque `DB_PASSWORD`/`MINIO_ROOT_PASSWORD` já estavam persistidos no
  estado dos containers desde então; rotacioná-los exigiria também `ALTER
  ROLE`/reconfiguração do MinIO, fora do âmbito desta tarefa, que pede
  explicitamente rotação do `INTERNAL_API_TOKEN`, não dos outros secrets).

## 12. Riscos

| Risco | Situação após este prompt |
|---|---|
| LOCAL-R04 — Secrets locais versionados por acidente | **Confirmado mitigado** — 8/8 ficheiros reais ignorados, 0 ocorrências em `git ls-files` |
| Token dessincronizado entre serviços sem sinal claro | **Validado** — produz `502` controlado no Backend Core, sem crash, com mensagem genérica sem detalhe interno; recuperável ao ressincronizar |
| Rotação manual sujeita a esquecimento de reiniciar um dos três serviços | Documentado explicitamente (§6, passo 3) — nenhum dos três recarrega `.env` a quente |
| Confundir o `.env.staging.local` da raiz com gestão de secrets dos containers de produção | Mitigado pela nomenclatura consistente e pelos comentários em cada ficheiro, todos a apontar para esta fase como local-only |

## 13. Próximo passo recomendado

Avançar para **STG-LOCAL-006** (Prompt 06 do pipeline): criar scripts de
arranque/paragem/health/reset que leiam este mecanismo de secrets
(`*.env.staging.local`) de forma automática — hoje o `source`/`set -a` é
feito manualmente a cada comando; os scripts devem encapsular esse padrão
para start/stop/health de toda a stack (containers + processos
aplicacionais) com um único comando por acção, mantendo o reset destrutivo
claramente separado.
