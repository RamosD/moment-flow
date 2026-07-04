# Prompt 06 — Auditoria de padrões `.gitignore` perigosos — Resultado

**Data:** 2026-07-03
**Fase:** `07_staging_local_hardening` (STG-HARD-008)
**Âmbito:** auditar todos os `.gitignore` do repositório à procura do mesmo
padrão que escondeu `content_renderer/src/storage/` na fase 06 (um
`storage/` não ancorado), sem corrigir nada por estética e sem tocar em
ignores necessários.
**Estado de execução:** `executado` — **nenhuma alteração foi necessária**.
Todos os `.gitignore` do repositório foram inspeccionados, todos os padrões
da lista pedida foram verificados com `git check-ignore`, e a única
correcção real deste tipo já tinha sido aplicada na fase 06
(`content_renderer/.gitignore`, `/storage/` ancorado). Este relatório
documenta o "não-achado" com a mesma disciplina que um achado real.

---

## 1. `.gitignore` encontrados

```text
./.gitignore
./backend_core/.gitignore
./backend_core/.pytest_cache/.gitignore   ← gerado automaticamente pelo pytest, dentro de uma pasta já ignorada
./backend_core/.ruff_cache/.gitignore     ← gerado automaticamente pelo ruff, dentro de uma pasta já ignorada
./content_renderer/.gitignore
./frontend/.gitignore
./intelligence_engine/.gitignore
./intelligence_engine/.pytest_cache/.gitignore  ← idem
./intelligence_engine/.ruff_cache/.gitignore    ← idem
```

Os 4 ficheiros `.pytest_cache/.gitignore` / `.ruff_cache/.gitignore` são
boilerplate automático dessas ferramentas (`# Created by pytest
automatically.` / `# Automatically created by ruff.`, conteúdo `*`), vivem
dentro de directórios já ignorados pelo `.gitignore` pai
(`.pytest_cache/`, `.ruff_cache/`), e não são versionados nem escritos por
este projecto — fora do âmbito de auditoria (não são "configuração
própria", são artefactos de ferramenta).

**5 ficheiros `.gitignore` de autoria do projecto foram auditados**: raiz,
`backend_core`, `content_renderer`, `frontend`, `intelligence_engine`.

## 2. Padrões da lista pedida, por ficheiro

| Ficheiro | `storage/` | `dist/` | `build/` | `logs/` | `data/` | `tmp/` | `cache/` | `output/` | `public/` | `assets/` |
|---|---|---|---|---|---|---|---|---|---|---|
| raiz | — | `dist` (não ancorado) | — | `logs` (não ancorado) | — | — | — | — | — | — |
| `backend_core` | — | — | — | — | — | — | — | — | — | — |
| `content_renderer` | **`/storage/` (ancorado — fase 06)** | `dist/` (não ancorado) | — | — | — | — | — | — | — | — |
| `frontend` | — | `dist` (não ancorado) | — | `logs` (não ancorado) | — | — | — | — | — | — |
| `intelligence_engine` | — | — | — | — | — | — | — | — | — | — |

`backend_core` e `intelligence_engine` não têm **nenhum** destes padrões —
só secrets, cache Python/Django, venv, SO/editor. `dist-ssr` (raiz,
`frontend`) e `media/`/`coverage/`/`e2e-logs/` (não pedidos explicitamente,
mas do mesmo género) foram incluídos na investigação por precaução — ver
§3.

## 3. Verificação por padrão suspeito (`git check-ignore`, antes/depois)

Metodologia: para cada padrão não ancorado encontrado, (a) procurei no
disco qualquer directório com esse nome exacto dentro de cada projecto
(`find -type d -iname <nome>`), e (b) confirmei com `git check-ignore -v`
se o caminho real correspondente está ignorado e se deveria estar.

### 3.1 `content_renderer` — `/storage/` (já corrigido na fase 06)

```text
$ git check-ignore -v content_renderer/src/storage/s3-storage.ts
(sem output, exit 1 — NÃO ignorado, correcto: é código-fonte)

$ git check-ignore -v content_renderer/storage
content_renderer/.gitignore:20:/storage/	content_renderer/storage
(ignorado, correcto: é armazenamento local em runtime, gerado)
```

**Confirmado**: o padrão `/storage/` (ancorado com `/` inicial, fase 06)
continua a distinguir correctamente `src/storage/` (código, visível) de
`storage/` na raiz do serviço (runtime, ignorado). Nenhuma acção
necessária — já resolvido.

### 3.2 `dist`/`dist-ssr` (raiz, `content_renderer`, `frontend`) — não ancorados, sem colisão actual

```text
$ find . -type d \( -name dist -o -name dist-ssr \) (excl. node_modules/venv/.git)
./content_renderer/dist
./frontend/dist
```

Só existem duas pastas `dist`, ambas na **raiz do respectivo serviço**,
ambas saída de build real (TypeScript/Vite):

```text
$ git check-ignore -v content_renderer/dist frontend/dist frontend/dist/assets
content_renderer/.gitignore:5:dist/	content_renderer/dist
frontend/.gitignore:11:dist	frontend/dist
frontend/.gitignore:11:dist	frontend/dist/assets
```

Nenhum `src/dist/` (ou equivalente aninhado) existe em nenhum dos dois
projectos — o padrão não ancorado não colide com nada hoje. **Não
corrigido**: não há evidência de perigo actual, e "ancorar por
precaução, sem uma colisão real" seria exactamente o tipo de correcção por
estética que este prompt proíbe explicitamente.

### 3.3 `logs` (raiz, `frontend`) — não ancorado, sem colisão actual

```text
$ find . -type d -name logs (excl. node_modules/venv/.git)
./.local-runtime/logs
```

Única pasta `logs` no repositório inteiro: dentro de `.local-runtime/`
(logs de execução dos scripts `staging-local-*.ps1`, já documentada e
intencionalmente ignorada). Nenhum código-fonte, em nenhum projecto, vive
dentro de uma pasta chamada `logs`. **Não corrigido** — sem colisão.

### 3.4 `media/` (`backend_core`) — não ancorado, sem colisão actual

Convenção Django (`MEDIA_ROOT`). Verificado que não existe nenhuma pasta
`apps/*/media/` de código:

```text
$ find backend_core -type d -iname media (excl. venv)
(vazio)

$ git check-ignore -v backend_core/media/somefile.png
backend_core/.gitignore:20:media/	backend_core/media/somefile.png
```

O padrão corresponde correctamente a um caminho hipotético
`backend_core/media/...` (a pasta ainda não existe em disco nesta
instalação local), sem colidir com nenhum ficheiro de código real. **Não
corrigido** — risco teórico (uma futura app Django chamada literalmente
`media`), não uma evidência actual; documentado aqui para que uma futura
auditoria saiba que isto já foi considerado.

### 3.5 `coverage/`, `e2e-logs/` (`content_renderer`) — não ancorados, sem colisão de código

```text
$ find content_renderer -type d -iname coverage -o -iname e2e-logs (excl. node_modules)
content_renderer/coverage
content_renderer/coverage/lcov-report/src/storage
content_renderer/coverage/src/storage
content_renderer/e2e-logs
```

`coverage/src/storage` e `coverage/lcov-report/src/storage` são **espelhos
do relatório de cobertura** (o `vitest`/`istanbul` reconstrói a árvore de
`src/` dentro do relatório HTML de cobertura para anotar cada ficheiro) —
não é código-fonte, é um artefacto gerado que *imita* o layout do código.
Confirmado ignorado correctamente:

```text
$ git check-ignore -v content_renderer/coverage content_renderer/e2e-logs
content_renderer/.gitignore:9:coverage/	content_renderer/coverage
content_renderer/.gitignore:23:e2e-logs/	content_renderer/e2e-logs
```

**Não corrigido** — nenhum código real nestes caminhos, apenas artefactos
gerados correctamente ignorados.

## 4. `git status --ignored` — varrimento geral

```text
!! .claude/
!! backend_core/.coverage
!! backend_core/schema.yml
!! content_renderer/.claude/
!! content_renderer/e2e-logs/
!! content_renderer/storage/
!! frontend/.claude/
!! frontend/.vite-dev.log
```

Todos os 8 itens são artefactos/ferramentas esperadas
(`.claude/`, `.coverage`, `schema.yml` gerado pelo drf-spectacular,
`e2e-logs/`, `storage/` runtime, log do Vite dev server) — **nenhum
ficheiro de código-fonte aparece nesta lista**.

## 5. Protecção de secrets (`.env`) — confirmada inalterada

Nenhum ficheiro `.gitignore`/`.env` foi tocado nesta iteração; verificado
na mesma, por disciplina (o prompt pede confirmação mesmo sem alteração):

```text
$ git check-ignore -v .env.staging.local backend_core/.env.staging.local \
    content_renderer/.env.staging.local intelligence_engine/.env.staging.local
→ todos ignorados (4/4)

$ git check-ignore -v .env.staging.local.example backend_core/.env.example \
    content_renderer/.env.example
→ nenhum ignorado (correcto — devem continuar rastreados)

$ git ls-files | grep "\.env.*example"
.env.staging.local.example
backend_core/.env.example
content_renderer/.env.e2e.example
content_renderer/.env.example
frontend/.env.example
intelligence_engine/.env.example
```

Todos os `.env.*.example` continuam rastreados; todos os `.env.staging.local`
reais continuam ignorados em todos os serviços.

## 6. Alterações feitas

**Nenhuma.** `git status --short` confirma zero alterações introduzidas
por esta iteração (para além dos ficheiros já pendentes de iterações
anteriores desta mesma fase, não relacionados). Justificação por padrão,
para cada candidato considerado, está em §3 — em nenhum caso havia uma
colisão real e demonstrável entre o padrão não ancorado e um caminho de
código-fonte, que é o limiar exigido por este prompt ("corrigir apenas
padrões perigosos com evidência").

## 7. Validações executadas

| Validação | Resultado |
|---|---|
| Localizar todos os `.gitignore` | ✅ 5 de autoria própria + 4 boilerplate de ferramenta (§1) |
| `git check-ignore -v` em todos os padrões suspeitos (`storage/`, `dist/`, `logs`, `media/`, `coverage/`, `e2e-logs/`) | ✅ §3, nenhuma colisão com código-fonte |
| `git status --ignored` | ✅ §4, nenhuma surpresa |
| `.env` reais continuam ignorados / `.env.example` continuam rastreados | ✅ §5 |
| `git status --short` sem ruído novo | ✅ §6 |
| `scripts/check-forbidden-ports.ps1` | ✅ `OK` |
| Grep de secrets | Não aplicável — nenhum ficheiro ignore/env foi tocado (regra do prompt: só exigido se algum for alterado) |

## 8. Critérios de aceitação — verificação

- ✅ Padrões perigosos auditados (todos os da lista pedida, em todos os
  `.gitignore` de autoria própria).
- ✅ Código-fonte não fica escondido por `.gitignore` — confirmado em
  todos os projectos, incluindo o caso já corrigido (`content_renderer`).
- ✅ Artefactos gerados continuam ignorados (`dist/`, `coverage/`,
  `e2e-logs/`, `storage/` runtime, `.coverage`, `schema.yml`, etc.).
- ✅ `.env` reais continuam ignorados; `.env.example` continuam
  rastreados.
- ✅ Alterações mínimas — zero, todas justificadas por ausência de
  evidência (§3).
- ✅ Relatório documenta achados **e não-achados** (esta secção e §3).

Nenhum critério de rejeição ocorreu: nenhum ignore necessário foi
removido, nenhum artefacto gerado passou a ser versionado, nenhuma
alteração foi feita sem evidência (porque nenhuma foi feita), nenhum
código-fonte ficou escondido, nenhum `.env` foi tocado, e o `git status`
não ganhou ruído nenhum.

## 9. Riscos remanescentes (documentados, não corrigidos — por desenho)

| Item | Severidade | Nota |
|---|---|---|
| `dist`/`dist-ssr` (raiz, `content_renderer`, `frontend`) continuam não ancorados | Muito baixa | Sem colisão actual (§3.2); ancorar preventivamente sem uma pasta `dist` aninhada real seria correcção por estética, explicitamente proibida |
| `logs` (raiz, `frontend`) continua não ancorado | Muito baixa | Sem colisão actual (§3.3); só existe `.local-runtime/logs`, já coberto por padrão dedicado |
| `media/` (`backend_core`) continua não ancorado | Muito baixa | Sem colisão actual (§3.4); risco só se uma futura app Django se chamar literalmente `media` |
| `.pytest_cache/.gitignore` / `.ruff_cache/.gitignore` não são geridos por este projecto | Nenhuma | Boilerplate de ferramenta, dentro de pastas já ignoradas — fora do âmbito de auditoria de configuração própria |

Nenhum destes é recomendado para correcção agora — ficam documentados para
que uma auditoria futura (se algum destes directórios vier a existir
aninhado sob `src/`) saiba que o risco já foi considerado e
conscientemente aceite, não esquecido.

## 10. Próximo passo recomendado

1. Nenhuma acção de código pendente desta tarefa — auditoria fechada sem
   alterações.
2. Se, no futuro, qualquer projecto desta stack criar uma pasta de código
   chamada literalmente `dist`, `logs`, `media`, `storage`, `build`,
   `cache`, `tmp`, `data`, `output`, `public` ou `assets` **fora** da raiz
   do serviço (ex.: `src/algo/dist/`), revalidar o padrão correspondente
   nesse momento — o risco é estrutural (nomes genéricos), não específico
   de uma alteração actual.
3. Seguir para **STG-HARD-009** (revalidação de segurança pós-hardening) ou
   **STG-HARD-010** (fecho da fase), conforme prioridade do operador.
