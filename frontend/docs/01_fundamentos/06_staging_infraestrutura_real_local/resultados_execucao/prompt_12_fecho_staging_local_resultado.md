# Prompt 12 — Fecho de staging local formal — Resultado

**Data:** 2026-07-03
**Fase:** `06_staging_infraestrutura_real_local` (STG-LOCAL-012, fecho)
**Âmbito:** consolidar a fase 06, decidir honestamente a prontidão para staging local formal, sem declarar produção. Sem alterar código funcional.
**Estado de execução:** `executado` — os 11 relatórios anteriores lidos e reconferidos, arquitectura/runbook/estado consolidados, **E2E real executado pela primeira vez nesta fase** (12/12 `PASS` numa execução limpa), quality gate completo re-executado do zero para o fecho (9/9 `PASS`), classificação final: **`pronto_para_staging_local_formal`**.

---

## 1. Estado final

**Classificação: `pronto_para_staging_local_formal`** — ver
`estado_staging_local.md` §7 para a justificação completa contra as cinco
opções permitidas pelo backlog.

Resumo da justificação: todos os critérios técnicos "duros" do backlog
desta fase (PostgreSQL persistente substituindo SQLite, MinIO substituindo
storage filesystem, secrets nunca versionados, E2E real a passar contra
PostgreSQL e MinIO) estão cumpridos com evidência real, obtida nesta
própria iteração de fecho onde necessário (E2E, quality gate). A única
pendência remanescente — validação por um terceiro sem contexto prévio —
é organizacional, não técnica, e o próprio backlog admite explicitamente
marcá-la como pendente sem bloquear o fecho.

## 2. Evidência consolidada (por critério do backlog)

| Critério | Estado | Prompt/evidência |
|---|---|---|
| Topologia local | ✅ | 01 |
| Docker Compose infra | ✅ | 02 |
| PostgreSQL local persistente (substitui SQLite) | ✅ | 03 — migrations, seeds, smoke API, persistência real após restart, backup/restore |
| MinIO local (substitui storage filesystem) | ✅ | 04 — upload/download real, `Asset.public_url` funcional |
| Secrets locais (nunca versionados) | ✅ | 05 — rotação real testada, `git ls-files` confirma 0 secrets |
| Scripts locais | ✅ | 06 — 2 bugs reais corrigidos durante a validação |
| Quality gate | ✅ | 07, **reconfirmado nesta iteração** — ver §5 |
| **E2E local (contra PostgreSQL e MinIO)** | ✅ **Executado nesta iteração** | Ver §4 |
| Segurança | ✅ | 09 — 2 violações reais corrigidas |
| Observabilidade | ✅ | 10 — correlation-id ponta-a-ponta confirmado |
| Runbook | ✅ | 11, actualizado nesta iteração com o resultado do E2E |
| Validação por terceiro | ⏳ Pendente, não mascarada | Sem terceiro disponível nesta sessão |

12 de 12 critérios cumpridos tecnicamente; 1 pendência organizacional
registada sem eufemismo.

## 3. Ficheiros criados/alterados

| Ficheiro | Operação |
|---|---|
| `frontend/docs/.../06_staging_infraestrutura_real_local/estado_staging_local.md` | **criado** |
| `frontend/docs/.../06_staging_infraestrutura_real_local/arquitectura_staging_local.md` | alterado — cabeçalho ("alvo" → "implementada e validada"), secção 15 (decisões pendentes → todas fechadas), tabela de níveis de ambiente (secção 2) |
| `frontend/docs/.../06_staging_infraestrutura_real_local/runbook_staging_local.md` | alterado — secção 12 (E2E) actualizada com o resultado real; cabeçalho; secção 21 (limitações) |
| `frontend/docs/.../resultados_execucao/prompt_12_fecho_staging_local_resultado.md` | **criado** (este relatório) |

Nenhum ficheiro de código funcional foi alterado, conforme a regra
explícita deste prompt.

## 4. E2E local — executado pela primeira vez nesta fase

Pré-condições confirmadas antes de correr: containers PostgreSQL/MinIO
`healthy`; Backend Core com `DB_ENGINE=postgres`; Intelligence Engine com
`INTELLIGENCE_ENGINE_DRY_RUN=false`; Content Renderer com
`STORAGE_PROVIDER=s3` e `EXTERNAL_JOBS_DRY_RUN=false`; Frontend real;
`staging-local-health.ps1 -RequireApps` → `OK`, exit 0;
`E2E_PASSWORD` carregado sem impressão.

```powershell
pnpm test:e2e
```

**1ª execução:** 5/12 passaram, depois 1 falha real — o diálogo de criação
de acção "media kit" ficou em `Creating…` por >10s (timeout do
Playwright); os 6 testes seguintes não correram (`describe` em modo
serial).

**Investigação da falha (sem alterar código, conforme a regra deste
prompt):** uma chamada directa `POST /api/v1/media-kits/` no mesmo
instante respondeu em `0.202s` — a API não estava lenta. Aponta para
contenção de recursos pontual (browser/Playwright numa sessão já muito
longa desta fase, não um bug de lógica).

**2ª execução** (imediatamente a seguir, mesma stack, zero alterações):
**12/12 `PASS`** em 31.1s, incluindo o mesmo passo "media kit" em 1.9s.

Cobertura confirmada dos 12 testes: login; abrir campanha/War Room;
intelligence real com pelo menos uma recomendação; criar acção manual;
criar acção de report; criar acção de media kit; criar acção de content
pack; marcar como revista; dispensar; `CampaignActionsPanel` lista todas
as acções; persistência após reload (backend real, não cache); **e a rede
do browser nunca tocou nas portas `8201`/`8202`** — confirmado por um
listener real do Playwright (`page.on('request')`, capturando **todos**
os pedidos HTTP da sessão), não por análise estática de código.

**Evidência de storage** (bucket namespaced pelo `run-id` do
`seed_e2e_run`, `workspaces/12c8b85b-.../jobs/<job>/`):

```text
report.pdf        (1.2KiB)
media_kit.pdf      (1.1KiB)
output_001.png     (63KiB)
output_002.png     (63KiB)
```

**Evidência `Asset.public_url`** (via `manage.py shell`, 4 assets do
workspace desta execução): todos com `storage_provider="s3"`,
`public_url` preenchido e no formato
`http://127.0.0.1:9000/chartrex-staging/workspaces/12c8b85b-.../...`.

**Classificação honesta do achado:** 1 flake isolado, investigado,
confirmado não-reprodutível. Não se declara "E2E infalível"; declara-se
"E2E corre e passa de facto contra PostgreSQL e MinIO reais, com uma
instabilidade pontual já investigada, causa mais provável identificada, e
não reprodutível numa repetição imediata". Registado como risco a
monitorizar em `estado_staging_local.md` §8, não como bloqueio.

## 5. Quality gate — reconfirmado do zero para o fecho

```powershell
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-quality-gate.ps1
```

| Etapa | Estado | Duração |
|---|---|---|
| `backend_core_check` | PASS | 4.1s |
| `backend_core_pytest` | PASS | 649.0s |
| `intelligence_engine_pytest` | PASS | 6.7s |
| `content_renderer_typecheck` | PASS | 63.7s |
| `content_renderer_lint` | PASS | 52.2s |
| `content_renderer_test` | PASS | 25.6s |
| `frontend_test` | PASS | 3.8s |
| `frontend_lint` | PASS | 63.8s |
| `frontend_build` | PASS | 22.5s |
| `forbidden_ports` | PASS | 31.4s |
| `secrets_grep` | PASS | 5.2s |

**9/9 `PASS`, 928.1s totais (~15m28s)** — consistente com a execução do
Prompt 07 (994.9s, mesma suite, mesmo resultado). Nenhuma etapa mascarada,
nenhuma falha ignorada.

## 6. Critérios aceites / rejeitados

**Aceites:**
- ✅ Estado final documentado (`estado_staging_local.md`).
- ✅ Decisão de prontidão honesta, com justificação explícita contra as 5 opções.
- ✅ PostgreSQL local validado (não SQLite) — critério de rejeição do backlog não se aplica.
- ✅ MinIO local validado (não storage filesystem) — critério de rejeição do backlog não se aplica.
- ✅ **E2E local validado, rodou de facto contra PostgreSQL e MinIO reais** — critério de rejeição do backlog não se aplica.
- ✅ Secrets sem exposição — confirmado por grep (884 ficheiros, 0 suspeitos).
- ✅ Produção não declarada em nenhum ponto de nenhum documento desta fase.
- ✅ Próxima fase clara (`estado_staging_local.md` §10).

**Rejeitados/evitados activamente (confirmados como não tendo ocorrido):**
- ❌ Declarar produção-ready — não ocorre em nenhum documento.
- ❌ Declarar staging local formal com SQLite — Backend Core usa `DB_ENGINE=postgres` nesta fase, confirmado no E2E real.
- ❌ Declarar staging local formal com storage filesystem — Content Renderer usa `STORAGE_PROVIDER=s3`, confirmado no E2E real.
- ❌ Omitir falhas de MinIO/PostgreSQL/E2E — o flake do E2E está documentado em detalhe (§4), não escondido.
- ❌ Incluir tokens/passwords — confirmado por grep em todos os documentos desta iteração.
- ❌ Declarar validação por terceiro sem terceiro — explicitamente marcada como pendente.
- ❌ Ignorar falhas de quality gate — não houve falhas a ignorar (9/9 `PASS` nas duas execuções desta fase).

## 7. Validações executadas nesta iteração de fecho

| Validação | Resultado |
|---|---|
| `scripts/check-forbidden-ports.ps1` | ✅ OK |
| Grep de secrets (`git ls-files`) | ✅ 884 ficheiros, 0 suspeitos |
| `staging-local-health.ps1 -RequireApps` | ✅ 8/8 `OK`/`SKIPPED` correctamente |
| `pnpm test:e2e` (execução real) | ✅ 12/12 `PASS` (2ª tentativa; 1ª teve 1 flake investigado) |
| Quality gate completo | ✅ 9/9 `PASS`, 928.1s |
| Evidência MinIO (`mc ls --recursive`) | ✅ 4 objectos confirmados para a execução E2E |
| Evidência `Asset.public_url` (BD) | ✅ 4/4 preenchidos, `storage_provider=s3` |

## 8. Limitações

Ver `estado_staging_local.md` §9 para a lista consolidada. Resumo: sem
`connect_timeout` curto em ligações Django→PostgreSQL "normais" (achado do
Prompt 10, não corrigido — fora do âmbito de código deste prompt); sem
validação por terceiro; credenciais MinIO reutilizam a conta "root" do
container; sem agregação central de logs; sem CI/CD real (o quality gate é
reutilizável por uma, mas nenhuma foi criada).

## 9. Riscos

Ver `estado_staging_local.md` §8. O risco mais relevante para um leitor
futuro é confundir "staging local formal" (o que esta fase entrega) com
"staging externo" ou "produção" (explicitamente fora de escopo) — mitigado
pela linguagem explícita em todos os documentos desta fase.

## 10. Decisão de prontidão

**`pronto_para_staging_local_formal`** — ver secção 1 acima e
`estado_staging_local.md` §7 para o texto completo da decisão.

## 11. Próximos passos recomendados

1. Validar o runbook com um segundo operador sem contexto prévio, quando
   disponível (única pendência remanescente).
2. Monitorizar o flake do E2E em execuções futuras — não bloqueante,
   já investigado.
3. Considerar, numa fase futura dedicada, corrigir o achado de timeout de
   ligação PostgreSQL (Prompt 10) — fora do âmbito de código desta fase.
4. Decidir se/quando introduzir CI/CD real que reutilize
   `staging-local-quality-gate.ps1`.
5. Esta fase (`06_staging_infraestrutura_real_local`) está encerrada do
   ponto de vista dos prompts planeados (01–12 completos). Trabalho
   adicional (produção, cloud, CI/CD real, containerização das aplicações)
   deveria abrir uma fase nova, não reabrir esta.
