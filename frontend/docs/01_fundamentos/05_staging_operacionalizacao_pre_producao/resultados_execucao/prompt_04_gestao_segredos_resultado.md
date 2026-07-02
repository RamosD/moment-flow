# Prompt 04 — Gestão de segredos — Resultado

**Data:** 2026-07-02
**Fase:** `05_staging_operacionalizacao_pre_producao` (STG-PRE-004)
**Âmbito:** formalizar a gestão de segredos para staging pré-produção — inventário, mecanismo de fornecimento, `.gitignore`, rotação. Sem desactivar autenticação interna, sem `ALLOW_INSECURE_EMPTY_TOKEN` em staging.
**Estado de execução:** `executado`, com um **incidente de exposição em tool output (não em repositório) detectado e remediado durante esta própria iteração** — ver §6.

---

## 1. Resumo objectivo

Inventariei todos os segredos dos quatro serviços, confirmei onde cada um é
consumido, e conclui que **não existe ainda nenhum mecanismo de CI/CD ou
secret store neste repositório** — não há `.github/workflows` nem
equivalente. O mecanismo actual (`.env` local não commitado) é adequado para
dev, mas fica registado como **decisão de infraestrutura pendente** para
staging pré-produção real (não invento uma plataforma que não existe).

Durante a validação encontrei e corrigi três problemas reais:

1. **Gap de `.gitignore`** em `backend_core` e `intelligence_engine`: só
   ignoravam `.env` exacto, não `.env.*` — ao contrário de `frontend` e
   `content_renderer`. Corrigido (mesma regra nos 4 serviços agora).
2. **Bug de robustez em `config/settings.py`**: `INTELLIGENCE_ENGINE_INTERNAL_TOKEN`
   com a chave presente-mas-vazia no `.env` não recaía no valor partilhado
   (`INTERNAL_API_TOKEN`) como o comentário prometia — ficava vazio, o que
   partiria silenciosamente a chamada síncrona ao Intelligence Engine.
   Corrigido no código e no comentário do `.env.example`.
3. **Incidente de exposição em tool output** (não em ficheiro versionado):
   um grep de validação meu, mal desenhado, imprimiu os valores reais de
   `SECRET_KEY` e `INTERNAL_API_TOKEN` do `backend_core/.env` de
   desenvolvimento local. Esse ficheiro nunca esteve no repositório (git
   confirma: nunca tracked, sempre ignorado). Como remediação imediata,
   rodei (rotacionei) os dois segredos nos três serviços, sem nunca voltar a
   imprimir os novos valores, e validei em runtime real que a rotação
   funciona ponta-a-ponta (login JWT, chamada síncrona Backend Core→
   Intelligence Engine, job assíncrono Backend Core→Content Renderer→
   callback). Ver §6 para o relato completo.

---

## 2. Inventário de secrets (sem valores)

| Secret | Definido em | Consumido por | Obrigatório? | Mecanismo actual |
|---|---|---|---|---|
| `INTERNAL_API_TOKEN` | `backend_core/.env`, `intelligence_engine/.env`, `content_renderer/.env` | Backend Core (envia), Intelligence Engine (valida), Content Renderer (valida + envia no callback) | Sim — deve ser **idêntico** nos três; vazio ⇒ todos os endpoints internos rejeitam tudo | `.env` local, não commitado |
| `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` | `backend_core/.env` (opcional) | Backend Core, só para chamadas ao Intelligence Engine | Não — quando ausente/vazio reutiliza `INTERNAL_API_TOKEN` (corrigido nesta iteração, ver §5) | `.env` local |
| `SECRET_KEY` | `backend_core/.env` | Backend Core (assinatura de sessão Django, JWT via SimpleJWT) | Sim, forte e único fora de dev | `.env` local |
| `DB_PASSWORD` | `backend_core/.env` (só `DB_ENGINE=postgres`) | Backend Core (ligação PostgreSQL) | Sim, quando `DB_ENGINE=postgres` | `.env` local |
| `STRIPE_WEBHOOK_SECRET` / `STRIPE_API_KEY` | `backend_core/.env` | Backend Core (billing, skeleton, fora do escopo funcional actual) | Não (billing ainda skeleton) | `.env` local |
| Credenciais de object storage (futuras) | Ainda não existem | Content Renderer, quando um provider real for escolhido | N/A ainda | **Não aplicável — nenhum provider escolhido (STG-PRE-003)** |
| Chaves de assinatura de URL (signed URL) | Ainda não existem | N/A | N/A | **Não aplicável — só seria necessário com bucket privado, decisão pendente (STG-PRE-003)** |
| Tokens de terceiros | Só `STRIPE_*` (acima); nenhum outro integrador externo tem credenciais no código | — | — | — |
| Credenciais de CI/CD | **Não aplicável — não existe pipeline de CI/CD neste repositório** (confirmado: sem `.github/workflows`, sem `.gitlab-ci.yml`, sem outro ficheiro de CI) | — | — | — |

**Nota sobre `ALLOW_INSECURE_EMPTY_TOKEN` (Content Renderer):** não é um
secret, é uma *flag* que desliga a exigência de token em dev. Confirmado
`false` por default no `.env.example`; a regra desta fase proíbe usá-la em
staging, e nada no código ou documentação a recomenda para esse fim.

---

## 3. Onde cada secret é consumido (por serviço)

| Serviço | Secrets que lê | Secrets que nunca deve ter |
|---|---|---|
| **Backend Core** | `SECRET_KEY`, `INTERNAL_API_TOKEN`, `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` (opcional), `DB_PASSWORD` (se Postgres), `STRIPE_*` | Nenhuma credencial de outro serviço (IE/CR não expõem segredos ao Backend Core além do token partilhado) |
| **Intelligence Engine** | `INTERNAL_API_TOKEN` (único secret) | `SECRET_KEY`, `DB_PASSWORD`, credenciais de storage — não faz sentido, é stateless e não tem DB |
| **Content Renderer** | `INTERNAL_API_TOKEN` (único secret hoje; credenciais de storage no futuro, quando houver provider) | `SECRET_KEY`, `DB_PASSWORD` — não tem DB própria |
| **Frontend** | **Nenhum.** Confirmado por grep (`git ls-files src \| grep INTERNAL_API_TOKEN\|SECRET_KEY\|DB_PASSWORD` → 0 ocorrências) | `INTERNAL_API_TOKEN`, `X-Internal-Token`, `DB_PASSWORD`, credenciais de storage, URLs internas de IE/Renderer — nenhum destes existe no bundle nem no código-fonte |
| **CI/CD** | **Não aplicável — não existe pipeline** | — |
| **Scripts de staging** | `content_renderer/scripts/run-e2e-*.ps1` já seguem um bom padrão: geram um token efémero aleatório (`[guid]::NewGuid()`) quando `INTERNAL_API_TOKEN` não está definido no ambiente, e usam `DB_PASSWORD` só com um default dev explícito (`chartrex_e2e_dev_only`, documentado como não-secreto) | Nenhum segredo hardcoded encontrado nestes scripts |

---

## 4. Mecanismo de fornecimento para staging — recomendação (sem infra escolhida)

**Não existe CI/CD neste repositório** (confirmei a ausência de
`.github/workflows` ou equivalente) e **não existe secret store
provisionado**. Não vou inventar uma escolha de plataforma que ninguém
decidiu. O que documento é:

| Opção | Estado | Nota |
|---|---|---|
| Variáveis de ambiente injectadas no processo no arranque (sem ficheiro) | **Recomendado como próximo passo mínimo**, já tem precedente no repositório (`run-e2e-*.ps1` fazem exactamente isto — `$env:INTERNAL_API_TOKEN = ...` antes de arrancar o processo) | Não requer nenhuma infraestrutura nova; só disciplina de arranque (nunca escrever o valor num ficheiro do repositório) |
| Secret store dedicado (ex.: Vault, AWS Secrets Manager, Azure Key Vault) | **Não escolhido, não provisionado** | Decisão de plataforma de deploy, fora do âmbito desta iteração |
| Variáveis de CI/deploy (ex.: GitHub Actions secrets) | **Não aplicável** — não existe pipeline de CI/CD | Só relevante quando um pipeline for criado |
| `.env` local não versionado, gerido manualmente por processo | **Estado actual, dev/staging técnico** | Adequado só para dev; não escala para staging pré-produção com múltiplos operadores |

**Recomendação concreta para staging pré-produção**, sem escolher
plataforma: continuar a injectar por variável de ambiente no arranque do
processo (não em ficheiro `.env` commitável), com o valor a vir de onde quer
que a infraestrutura de staging escolhida guarde segredos (gestor de
processos, orquestrador, ou secret store) — o mecanismo dos scripts E2E já
demonstra que a aplicação (Django/FastAPI/Node, todos via variáveis de
ambiente / `python-decouple` / `pydantic-settings`) já é agnóstica da origem
do valor. **Não há trabalho de código necessário** — só uma decisão
operacional de onde a variável é injectada em staging real.

---

## 5. `.env.example` — placeholders e correcções

| Ficheiro | Alteração | Motivo |
|---|---|---|
| `backend_core/.env.example` | Comentário de `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` reescrito; linha passa a **comentada** (`# INTELLIGENCE_ENGINE_INTERNAL_TOKEN=`) em vez de presente-e-vazia | O comentário antigo dizia "leave EMPTY to reuse the shared token", mas isso estava **errado** na prática (ver §6.2) — deixar a chave presente-e-vazia não activava o fallback |
| `content_renderer/.env.example` | Nenhuma alteração nesta iteração (já alterado no Prompt 03 para `LOCAL_STORAGE_PUBLIC_BASE_URL`) | Placeholders já seguros (`INTERNAL_API_TOKEN=` vazio, sem valor real) |
| `intelligence_engine/.env.example` | Nenhuma alteração de conteúdo (só o `.gitignore` do serviço, ver §7) | Já só tinha `INTERNAL_API_TOKEN=` vazio |
| `frontend/.env.example` | Nenhuma alteração | Já não continha nenhum secret; só `VITE_BACKEND_API_BASE_URL` |

Todos os placeholders restantes (`SECRET_KEY=change-me-to-a-long-random-string`,
`DB_PASSWORD=postgres`) já eram claramente não-reais (texto óbvio de
placeholder / valor genérico de exemplo, nunca um valor com aparência de
segredo real) — confirmado por grep, sem alteração necessária.

---

## 6. Violações encontradas e corrigidas

### 6.1 Incidente: valores reais impressos em tool output (não em repositório)

**O que aconteceu:** ao executar os greps de validação pedidos por esta
iteração, usei um padrão (`INTERNAL_API_TOKEN=` e `SECRET_KEY=`) sem excluir
explicitamente os ficheiros `.env` reais (só excluí `.example`/`README`). O
grep correu contra o `backend_core/.env` de desenvolvimento local e **imprimiu
os valores reais** de `SECRET_KEY` e `INTERNAL_API_TOKEN` no output da
ferramenta.

**Impacto real:** **nenhum no repositório** — `backend_core/.env` nunca foi
tracked pelo git (confirmado: `git ls-files` não o lista; `.gitignore`
sempre o cobriu). Os valores não chegaram a nenhum ficheiro versionado, log
persistente do serviço, nem documento desta fase. O único lugar onde os
valores apareceram foi no output de uma chamada de ferramenta desta sessão.

**Remediação executada imediatamente:**
1. Gerei novos valores para `SECRET_KEY` (Django, aleatório) e
   `INTERNAL_API_TOKEN` (hex de 32 bytes), usando o módulo `secrets` do
   Python, **sem nunca imprimir os valores** — a substituição nos três
   `.env` foi feita por um script que lê/escreve os ficheiros directamente.
2. Sincronizei o novo `INTERNAL_API_TOKEN` nos três `.env`
   (`backend_core`, `intelligence_engine`, `content_renderer`) e confirmei
   que são idênticos **comparando hashes SHA-256**, nunca os valores em si.
3. Reiniciei o Content Renderer (já estava a correr de uma sessão anterior)
   e arranquei Backend Core + Intelligence Engine para validar a rotação em
   runtime real:
   - Login JWT → `200` (confirma que o novo `SECRET_KEY` assina/valida
     tokens correctamente).
   - `POST /campaigns/{id}/intelligence/` (Backend Core → Intelligence
     Engine, síncrono, usa o token partilhado) → `200` com resultado real.
   - `POST /reports/` → job assíncrono Backend Core → Content Renderer →
     callback Content Renderer → Backend Core (usa o token partilhado nos
     dois sentidos) → `status=completed`.
4. Parei os processos ad-hoc (Backend Core, Intelligence Engine) no fim da
   validação; o Content Renderer ficou a correr (estado em que já estava
   antes desta iteração, agora com o token novo em memória).

**Nenhum valor foi impresso nesta remediação nem neste relatório.**

### 6.2 Bug de robustez: `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` vazio-mas-presente

Descoberto **como consequência directa** da rotação acima: ao limpar
`INTELLIGENCE_ENGINE_INTERNAL_TOKEN` para vazio (pensando que isso activava
o fallback documentado), a chamada síncrona ao Intelligence Engine passou a
falhar com `403 unauthorized_internal_request` → `502` no Backend Core.

**Causa raiz:** `python-decouple` devolve a **string vazia literal** quando a
chave existe no `.env` com nada a seguir ao `=`, e **não** aplica o
`default=` do Python nesse caso — só aplica o default quando a chave está
**totalmente ausente**. `config/settings.py` tinha:

```python
INTELLIGENCE_ENGINE_INTERNAL_TOKEN = config(
    "INTELLIGENCE_ENGINE_INTERNAL_TOKEN", default=INTERNAL_API_TOKEN
)
```

Isto só reutiliza `INTERNAL_API_TOKEN` quando a chave está ausente do
`.env`; com a chave presente-e-vazia, resolve para `""`. Esta é exactamente
a mesma armadilha já registada informalmente na fase 04 (nota de sessão:
"se `INTELLIGENCE_ENGINE_INTERNAL_TOKEN=` estiver vazio no .env, sobrepõe o
default para vazio") — mas nunca tinha sido corrigida no código nem no
`.env.example`.

**Correcção aplicada** (`backend_core/config/settings.py`):

```python
INTELLIGENCE_ENGINE_INTERNAL_TOKEN = (
    config("INTELLIGENCE_ENGINE_INTERNAL_TOKEN", default="") or INTERNAL_API_TOKEN
)
```

Com `default=""` explícito e o `or`, qualquer valor falsy (chave ausente OU
presente-e-vazia) resulta sempre em reutilizar `INTERNAL_API_TOKEN`. Validado:
- `manage.py shell`: com a chave ausente do `.env`, `INTELLIGENCE_ENGINE_INTERNAL_TOKEN == INTERNAL_API_TOKEN` → `True`.
- Com `INTELLIGENCE_ENGINE_INTERNAL_TOKEN=""` injectado via variável de
  ambiente do processo (simulando o cenário presente-e-vazio) → mesmo
  resultado, `True`, token não fica vazio.
- `.env.example` actualizado para comentar a linha por default e explicar a
  armadilha (ver §5), para que copiar o ficheiro nunca reproduza o bug.

### 6.3 `.gitignore` incompleto em 2 dos 4 serviços

`backend_core/.gitignore` e `intelligence_engine/.gitignore` só tinham
`.env` (correspondência exacta), sem `.env.*`. `frontend/.gitignore` e
`content_renderer/.gitignore` já tinham o padrão mais seguro (`.env`,
`.env.*`, `!.env.example`). Isto significa que, antes desta correcção, um
ficheiro como `backend_core/.env.staging` ou `intelligence_engine/.env.local`
**não seria ignorado** pelo git — risco latente de commit acidental.
Corrigido nos dois `.gitignore` para o mesmo padrão dos outros dois
serviços. Confirmado com `git check-ignore -v` que `.env.example` continua
tracked e `.env` continua ignorado nos dois serviços após a alteração.

---

## 7. Ficheiros alterados

| Ficheiro | Operação | Nota |
|---|---|---|
| `backend_core/.gitignore` | alterado | `.env` → `.env` + `.env.*` + `!.env.example` |
| `intelligence_engine/.gitignore` | alterado | idem |
| `backend_core/.env.example` | alterado | comentário/formato de `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` corrigido (linha comentada por default) |
| `backend_core/config/settings.py` | alterado | fallback robusto de `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` (§6.2) |
| `backend_core/.env` (não versionado) | **rotacionado** (fora do repositório) | `SECRET_KEY` e `INTERNAL_API_TOKEN` novos; `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` removido da linha (fallback aplica-se) |
| `intelligence_engine/.env` (não versionado) | **rotacionado** (fora do repositório) | `INTERNAL_API_TOKEN` sincronizado com o novo valor partilhado |
| `content_renderer/.env` (não versionado) | **rotacionado** (fora do repositório) | idem |
| `frontend/docs/.../arquitectura_staging_pre_producao.md` | alterado | §7 (secrets) e §11 (decisões pendentes) actualizados |

Nenhum ficheiro de produto (lógica de negócio) foi alterado além da correcção
de robustez em `config/settings.py`, que é estritamente sobre resolução de
configuração de segredo — dentro do âmbito desta iteração.

---

## 8. Greps de segurança executados

Todos executados com `git ls-files` (só ficheiros **tracked**, nunca `.env`
reais, que são sempre untracked):

| Padrão | Ocorrências | Classificação |
|---|---|---|
| `INTERNAL_API_TOKEN=` | ~20 | Todas placeholders (`<DEV_TOKEN>`, `<INTERNAL_API_TOKEN>`, vazio), docs de fase anteriores, ou `real-loop-token-123` (literal de teste em `test_intelligence_real_loop.py`, não um segredo real) |
| `SECRET_KEY=` | 6 | Todas `change-me-to-a-long-random-string` ou `<SECRET_KEY>` (placeholders) |
| `PASSWORD=` | ~10 | `DB_PASSWORD=postgres` (placeholder genérico), `chartrex_e2e_dev_only` (dev explícito e documentado como não-secreto), `PGPASSWORD='trust-mode-unused'` (idem) |
| `AWS_SECRET` | 0 | — |
| `ACCESS_KEY` | 0 | — |
| `PRIVATE_KEY` | 0 fora da denylist/docs de campos a redigir | — |
| `X-Internal-Token` | ~20 | Nome do header em código/docs/testes — nunca um valor |
| `Bearer [token real]` | 0 | — |
| `frontend/src` (todos os padrões acima) | 0 | Confirmado — frontend sem segredos internos |

**Nenhuma ocorrência real de segredo em ficheiro versionado.**

---

## 9. Documentação de rotação

### Como gerar um novo `INTERNAL_API_TOKEN`

```powershell
# PowerShell — 32 bytes aleatórios em hex
python -c "import secrets; open('token.tmp','w').write(secrets.token_hex(32))"
# ler o ficheiro para colar no .env de cada serviço, depois apagar token.tmp
# (nunca imprimir o valor num terminal partilhado ou log)
```

Ou, seguindo o padrão já existente em `content_renderer/scripts/run-e2e-localpg.ps1`:
gerar via `[guid]::NewGuid().ToString('N')` para um valor efémero em cenários
de teste/E2E.

### Onde colocar

O mesmo valor de `INTERNAL_API_TOKEN` tem de estar em **três** sítios:
`backend_core/.env`, `intelligence_engine/.env`, `content_renderer/.env`
(`INTELLIGENCE_ENGINE_INTERNAL_TOKEN` no Backend Core deve ficar **ausente**
para reutilizar o mesmo valor automaticamente — nunca definir com um valor
vazio, ver §6.2). Nunca escrever o valor em nenhum ficheiro versionado,
documento, log ou script de repositório.

### Como reiniciar os serviços após rotação

Nenhum dos três serviços recarrega `.env` a quente — é preciso reiniciar o
processo:
- **Backend Core:** parar o `runserver`/processo WSGI e arrancar de novo.
- **Intelligence Engine:** parar o `uvicorn` e arrancar de novo (mesmo em
  modo `--reload`, o `--reload` só observa alterações de código-fonte, não
  do `.env`).
- **Content Renderer:** parar o processo `tsx`/`node` e arrancar de novo
  (`npm run dev` ou `npm run build && npm start`); `tsx watch` também só
  observa ficheiros de código, não `.env`.

### Como validar que a rotação funcionou

1. `curl http://<ie-host>:8201/health` e `curl http://<cr-host>:8202/health`
   → `200` (liveness, não depende do token).
2. Chamada síncrona real: `POST /api/v1/campaigns/{id}/intelligence/` no
   Backend Core → `200` com `source=engine` (não `502`).
3. Job assíncrono real: criar um `Report`/`MediaKit`/`ContentPackRequest` →
   estado final `completed`/`generated` (não `queued` parado nem
   `ExternalJobReference.status=failed` por erro de autenticação).
4. Se algum destes falhar com `502`/`403`, o token está dessincronizado
   entre serviços — confirmar (sem imprimir valores) com hash:
   `sha256sum` do valor em cada `.env` deve ser idêntico entre os três.

### Como revogar

Não existe uma "lista de revogação" — o único mecanismo é **rotação**: gerar
um valor novo e substituir nos três serviços. Enquanto o valor antigo
estiver em qualquer um dos três `.env`, chamadas com o valor antigo deixam
de bater certo assim que **pelo menos um** dos serviços for actualizado
(nesse intervalo, chamadas inter-serviço falham com `403`/`502` até todos
os três estarem sincronizados — por isso a rotação deve ser feita com os
três serviços parados ou numa janela curta).

---

## 10. Pendências

- **Mecanismo de fornecimento de secrets para staging real continua por
  escolher** — depende de uma decisão de plataforma de deploy que ainda não
  foi tomada (sem CI/CD no repositório).
- **Rotação continua manual** — não há automação nem calendário de rotação
  definido; esta iteração documenta o procedimento mas não o agenda.
- **Credenciais de storage** continuam não-aplicável (sem provider
  escolhido, STG-PRE-003).
- **`ALLOW_INSECURE_EMPTY_TOKEN`** continua a existir no Content Renderer
  como *flag* de dev — não removido (é uma protecção útil para dev local
  sem token), mas deve ser destacado no runbook (STG-PRE-010) como algo a
  **nunca** activar em staging.

---

## 11. Riscos

| Risco | Severidade | Estado |
|---|---|---|
| Segredo de dev exposto em tool output desta sessão | Alto (se não corrigido) | **Mitigado** — rotacionado e validado em runtime; nunca esteve em ficheiro versionado |
| `INTELLIGENCE_ENGINE_INTERNAL_TOKEN` presente-e-vazio a quebrar silenciosamente a chamada síncrona | Alto (só descoberto por acidente nesta iteração) | **Mitigado** — corrigido no código, não só na documentação |
| `.gitignore` incompleto permitir commit acidental de `.env.staging`/`.env.local` | Médio | **Mitigado** — `.gitignore` alinhado nos 4 serviços |
| Falta de mecanismo formal de secret store para staging | Médio | **Presente, registado como decisão pendente** — depende de escolha de infraestrutura fora do âmbito desta fase |
| Rotação manual sem automação/calendário | Baixo | Presente, aceitável para o estádio actual (piloto técnico), a revisitar antes de produção |

---

## 12. Próximo passo recomendado

Avançar para **Prompt 05 (STG-PRE-005 — Correlation-id único ponta-a-ponta)**:
propagar um `X-Request-ID` (ou equivalente) desde o Backend Core até
Intelligence Engine, `CampaignAction`, artefacto, job e Content Renderer,
para que uma operação completa seja rastreável de ponta a ponta — lacuna já
identificada na fase 04 (OBS-L01/L02) e ainda presente.
