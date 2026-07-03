# Prompt 07 — Quality gate local — Resultado

**Data:** 2026-07-03
**Fase:** `06_staging_infraestrutura_real_local` (STG-LOCAL-007)
**Âmbito:** criar um quality gate local, executável manualmente e reutilizável por CI futura, sem exigir CI/CD remoto nem cloud.
**Estado de execução:** `executado` — script criado, corrido de facto de ponta-a-ponta (não só por etapas isoladas), **9/9 etapas obrigatórias `PASS`**, modo opcional `-WithE2E` implementado e validado a bloquear correctamente sem a stack activa.

---

## 1. Inventário de comandos existentes (tarefa 1)

| Serviço | Comando | Onde vive |
|---|---|---|
| Backend Core | `python manage.py check` | `backend_core/` |
| Backend Core | `python -m pytest -q` (`pytest.ini`: `testpaths = apps tests`) | `backend_core/` |
| Intelligence Engine | `python -m pytest -q` (`pytest.ini`: `testpaths = tests`) | `intelligence_engine/` |
| Content Renderer | `npx tsc --noEmit`, `npx eslint .`, `npx vitest run` (`package.json`: `typecheck`/`lint`/`test`) | `content_renderer/` |
| Frontend | `pnpm test` (node `--test` nativo), `pnpm lint` (eslint), `pnpm build` (`tsc -b && vite build`) | `frontend/` |
| Portas proibidas | `scripts/check-forbidden-ports.ps1` | raiz |
| Secrets | Nenhum grep automatizado existia antes desta iteração — só greps manuais ad-hoc nos Prompts 04/05/06 | — |
| E2E | `pnpm test:e2e` (Playwright) | `frontend/` |

Nenhum comando pré-existente foi alterado — o gate só os invoca.

## 2. Script criado

`scripts/staging-local-quality-gate.ps1` (+ reaproveita `scripts/lib/staging-local-common.ps1` do Prompt 06). Corre, por defeito, **sem depender da stack Docker desta fase** — cada serviço usa a sua configuração de dev normal (`backend_core/.env`, SQLite por default), exactamente para poder ser reutilizado por uma CI futura sem alterações nem infraestrutura extra.

Cobertura (9 etapas obrigatórias + 1 opcional):

1. `backend_core_check` — `manage.py check`
2. `backend_core_pytest` — suite completa
3. `intelligence_engine_pytest` — suite completa
4. `content_renderer_typecheck` + `content_renderer_lint` + `content_renderer_test` — **âmbito alargado deliberadamente** face à lista mínima do prompt ("npm test Content Renderer"): typecheck e lint já corriam juntos com os testes em todos os fechos anteriores desta fase (Prompts 02–06), pelo que separá-los aqui seria reduzir cobertura face ao que já era prática consistente
5. `frontend_test` — testes de unidade
6. `frontend_lint`
7. `frontend_build`
8. `forbidden_ports` — `check-forbidden-ports.ps1`
9. `secrets_grep` — grep próprio sobre `git ls-files` (ver §3)
10. `e2e` (**opcional**, `-WithE2E`) — ver §5

Parâmetro `-Only <nome1,nome2,...>` permite correr um subconjunto durante desenvolvimento. Cada etapa reporta `[PASS]`/`[FAIL]`/`[SKIP]` explicitamente; a saída completa de qualquer comando falhado é sempre mostrada (nunca escondida nem redireccionada para `/dev/null`).

## 3. `secrets_grep` — desenho e iteração real

Grep próprio sobre `git ls-files` (só ficheiros **tracked**, nunca `.env` reais). Captura `KEY=valor` para `INTERNAL_API_TOKEN`, `SECRET_KEY`, `DB_PASSWORD`, `MINIO_ROOT_PASSWORD`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `E2E_PASSWORD`, `STRIPE_*`, e falha a etapa se algum valor não for reconhecido como placeholder óbvio. **Nunca imprime o valor encontrado** — só `ficheiro:linha`, para que o próprio gate nunca se torne um sítio que expõe um segredo real, mesmo no caso inesperado de um ter sido commitado.

Este desenho foi **iterado ao vivo contra o repositório real** (não escrito e assumido correcto): a primeira versão produziu **53 falsos positivos**; refinei a regex e a lista de marcadores seguros em 4 iterações sucessivas, cada uma validada por re-execução real, até chegar a **0 falsos positivos com 884 ficheiros verificados**:

| Iteração | Suspeitos | Causa corrigida |
|---|---|---|
| 1 | 53 | `STRIPE_[A-Z_]+` apanhava `HTTP_STRIPE_SIGNATURE=` como substring; sem tratamento de `""`/`''` vazios |
| 2 | 32 | Faltava reconhecer `<PLACEHOLDER>` entre parênteses angulares, e valores como `smoke-test-token` |
| 3 | 3 | Vírgula a cortar o valor a meio de um placeholder com espaço (`<definido, oculto>`); `;` de listas markdown a virar "valor" de 1 carácter; `***` (redacção) não reconhecido |
| 4 | **0** | Alternação `<[^...]*>` para placeholders com espaços/vírgulas internas, mais os 2 ajustes acima |

Documentado aqui porque é evidência directa de que o gate **não foi construído a mascarar falhas** — cada falso positivo foi investigado, a causa real confirmada por inspecção da linha exacta, e só então a regra ajustada.

## 4. Resultado da execução completa (real, não simulada)

```powershell
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-quality-gate.ps1
```

| Etapa | Estado | Duração |
|---|---|---|
| `backend_core_check` | PASS | 4.9s |
| `backend_core_pytest` | PASS | 674.7s (~11m15s) |
| `intelligence_engine_pytest` | PASS | 5.9s |
| `content_renderer_typecheck` | PASS | 76.3s |
| `content_renderer_lint` | PASS | 56.9s |
| `content_renderer_test` | PASS | 30.9s |
| `frontend_test` | PASS | 4.9s |
| `frontend_lint` | PASS | 77.5s |
| `frontend_build` | PASS | 26.2s |
| `forbidden_ports` | PASS | 31.5s |
| `secrets_grep` | PASS | 4.8s |
| `e2e` | SKIP | — (não pedido) |

**Duração total: 994.9s (~16m35s).** `backend_core_pytest` domina o tempo (~68% do total) — suite completa (~600+ testes) contra SQLite, incluindo testes que exercitam geração real de PDF/imagem em alguns fluxos.

Exit code final: `0`. Nenhuma etapa mascarada, nenhum `skip`/`xfail` usado para "passar" artificialmente — confirmado por leitura do output completo, não só do resumo.

## 5. Modo opcional com E2E

```powershell
$env:E2E_PASSWORD = '<definido pelo operador>'
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-quality-gate.ps1 -WithE2E
```

Antes de correr `pnpm test:e2e`, o gate invoca
`staging-local-health.ps1 -RequireApps` internamente. Validado nesta
iteração **sem** a stack activa: a etapa `e2e` falhou de forma clara e
imediata (`[FAIL] e2e — stack staging local não está totalmente activa`),
sem tentar correr o Playwright contra uma stack incompleta e sem mascarar
o problema como sucesso. A execução real do E2E com a stack totalmente
activa é o âmbito do **STG-LOCAL-008** (próximo prompt), não deste.

## 6. Saídas claras (tarefa 4)

Cada etapa: `[PASS]`/`[FAIL] — exit <n> (<Xs>)`. Resumo final em tabela
(`Format-Table`) com nome/estado/duração de todas as etapas, incluindo as
puladas. Mensagem final inequívoca: `RESULTADO: OK` ou `RESULTADO: FALHOU
— N etapa(s) falharam: <lista>`. Exit code do processo `0`/`1` reflecte o
resultado, verificável por qualquer CI futura via `$LASTEXITCODE`/`$?`.

## 7. Ficheiros criados/alterados

| Ficheiro | Operação |
|---|---|
| `scripts/staging-local-quality-gate.ps1` | **criado** |
| `frontend/docs/.../06_staging_infraestrutura_real_local/runbook_staging_local.md` | alterado — nova secção 8.1 "Quality gate local" |
| `frontend/docs/.../resultados_execucao/prompt_07_quality_gate_local_resultado.md` | **criado** (este relatório) |

Nenhum ficheiro de código de produto foi alterado. Nenhum comando existente
(`manage.py check`, `pytest`, `vitest`, `eslint`, `vite build`,
`check-forbidden-ports.ps1`) foi modificado — o gate só os invoca tal como
já existiam.

## 8. Validações executadas

| Validação | Resultado |
|---|---|
| Execução completa do gate (9 etapas obrigatórias) | ✅ 9/9 PASS, ver §4 |
| `-Only` com um único valor | ✅ correcto desde a primeira tentativa |
| `-Only` com lista separada por vírgulas | ⚠️→✅ falhou na primeira tentativa (nested `pwsh -File` não separa a lista); corrigido com split explícito dentro do script |
| Exit code não-zero em falha real | ✅ confirmado nas 4 iterações do `secrets_grep` com falsos positivos (§3) — cada uma terminou com exit 1 real |
| Grep de secrets nos 3 ficheiros alterados/criados nesta iteração | ✅ 0 valores reais |
| `-WithE2E` sem stack activa | ✅ falha clara, não mascarada |
| Confirmar não usa portas proibidas | ✅ etapa `forbidden_ports` do próprio gate passou |

## 9. Etapas opcionais

- `-WithE2E`: implementado, valida pré-condições reais (health de infra +
  4 apps), nunca corre "às cegas". Execução real com stack activa
  fica para STG-LOCAL-008.
- `-Only`: permite correr um subconjunto (ex.: só lint durante
  desenvolvimento), sem substituir a execução completa como gate formal.

## 10. Limitações

- `backend_core_pytest` (674.7s) domina a duração total — não paralelizado
  entre serviços nesta iteração (execução sequencial, mais simples de ler
  o output e diagnosticar falhas, à custa de tempo total). Paralelizar
  ficaria para uma iteração futura, se o tempo se tornar bloqueante.
- O gate corre contra `backend_core/.env` (SQLite) por defeito, não contra
  o PostgreSQL desta fase — decisão deliberada (§2: CI-ready, sem depender
  de Docker), mas significa que esta execução **não** é, por si só,
  evidência de que a suite passa contra PostgreSQL (isso já foi validado
  separadamente nos Prompts 03/04 com subconjuntos reais).
- `secrets_grep` usa um denylist de marcadores "seguros" mantido no
  script — um novo tipo legítimo de placeholder no futuro pode exigir
  ajustar a regex (documentado como processo iterativo no próprio §3, não
  escondido).

## 11. Riscos

| Risco | Situação após este prompt |
|---|---|
| Suite completa lenta (~16m35s) desencorajar execução frequente | Mitigado parcialmente por `-Only` para iteração rápida; gate completo continua recomendado antes de fechar uma fase |
| `secrets_grep` com falso-negativo (segredo real não reconhecido pelo padrão) | Baixo — o padrão cobre as 8 variáveis nomeadas explicitamente no prompt; segredos com nomes de variável diferentes não seriam apanhados (limitação conhecida, não nova) |
| `-WithE2E` nunca corrido com a stack real nesta iteração | Endereçado no próximo prompt (STG-LOCAL-008) |

## 12. Próximo passo recomendado

Avançar para **STG-LOCAL-008**: correr `pnpm test:e2e` de facto contra a
stack staging local totalmente activa (PostgreSQL, MinIO, Backend Core,
Intelligence Engine, Content Renderer, Frontend), validando o modo
`-WithE2E` do quality gate criado nesta iteração com um resultado real, não
só o bloqueio de pré-condição já validado aqui.
