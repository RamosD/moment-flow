# Proposta de CI/CD real — GitHub Actions (STG-HARD-005)

**Estado:** `proposta — nenhum workflow criado`. Este documento é uma
**proposta de desenho**, não uma pipeline activa. Por decisão explícita
do operador nesta iteração, **nenhum ficheiro `.github/workflows/*.yml`
foi criado** — o YAML abaixo é ilustrativo, para revisão, não algo que
corra automaticamente em nenhum push/PR enquanto não for
deliberadamente adoptado.

---

## 1. Plataforma detectada

```text
$ find .github -type f          → não existe
$ ls .gitlab-ci.yml              → não existe
$ ls azure-pipelines.yml         → não existe
$ find . -iname Jenkinsfile      → não existe
$ git remote -v
origin  https://github.com/RamosD/moment-flow.git
```

**Nenhuma pipeline CI/CD está configurada neste repositório.** O
repositório está hospedado no GitHub, o que torna o **GitHub Actions** a
plataforma sem custo adicional, sem novo serviço a provisionar, e sem
nenhuma "invenção" de plataforma não relacionada — mas a decisão de a
activar de facto **não foi tomada nesta iteração**, por escolha explícita
do operador (perguntado directamente, dado o peso de criar um ficheiro que
passaria a correr automaticamente em cada push/PR). Este documento fica
como a proposta concreta para essa decisão, quando for tomada.

## 2. Desenho proposto (ilustrativo — não activo)

```yaml
# .github/workflows/quality-gate.yml (PROPOSTA — não criado neste repositório)
name: Quality Gate

on:
  push:
    branches: [main]
  pull_request:

jobs:
  quality-gate:
    # ubuntu-latest inclui `pwsh` (PowerShell 7) pré-instalado — permite
    # reutilizar scripts\staging-local-quality-gate.ps1 tal como está, sem
    # reescrever a lógica por serviço. Não testado nesta iteração contra um
    # runner real (ver §6, limitações) — assunção de alta confiança, não
    # facto verificado.
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: 'pip'
          cache-dependency-path: |
            backend_core/requirements.txt
            intelligence_engine/requirements.txt

      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - uses: pnpm/action-setup@v4
        with:
          version: 11.9.0

      - name: Instalar dependências — backend_core
        run: |
          python -m venv backend_core/venv
          backend_core/venv/bin/pip install -r backend_core/requirements.txt

      - name: Instalar dependências — intelligence_engine
        run: |
          python -m venv intelligence_engine/venv
          intelligence_engine/venv/bin/pip install -r intelligence_engine/requirements.txt

      - name: Instalar dependências — content_renderer
        run: npm ci
        working-directory: content_renderer

      - name: Instalar dependências — frontend
        run: pnpm install --frozen-lockfile
        working-directory: frontend

      - name: Quality gate (reutiliza staging-local-quality-gate.ps1)
        shell: pwsh
        run: pwsh -ExecutionPolicy Bypass -File scripts/staging-local-quality-gate.ps1

  # E2E fica FORA do gate obrigatório — ver §4. Job manual/opcional,
  # nunca correndo automaticamente em push/PR, porque o runner GitHub-hosted
  # não tem PostgreSQL/MinIO/os 4 processos aplicacionais desta stack.
  e2e-manual:
    if: false  # nunca corre automaticamente — activação manual explícita, se/quando a stack estiver disponível no runner
    runs-on: ubuntu-latest
    steps:
      - run: echo "E2E requer a stack staging local completa (Docker + 4 processos) — não disponível neste runner. Ver runbook secção 12."
```

**Nota sobre `venv` no Linux**: o layout `venv/Scripts/python.exe`
(Windows) usado pelos scripts locais torna-se `venv/bin/python` num runner
Linux — o YAML acima já reflecte isso; `staging-local-quality-gate.ps1`
**não** precisaria de alteração porque já resolve os caminhos via
`Join-Path`, que é multiplataforma no PowerShell 7 — mas isto **não foi
testado** (§6).

## 3. Mapa: passos pedidos pelo prompt → comando real (já existente)

| Passo pedido | Comando (via `staging-local-quality-gate.ps1`) | Precisa de secrets? |
|---|---|---|
| `backend_core_check` | `venv/bin/python manage.py check` | Não — corre contra `backend_core/.env` de dev (SQLite), não `.env.staging.local` |
| `backend_core_pytest` | `venv/bin/python -m pytest -q` | Não |
| `intelligence_engine_pytest` | `venv/bin/python -m pytest -q` | Não |
| Content Renderer typecheck/lint/test | `npx tsc --noEmit` + `npx eslint .` + `npx vitest run` | Não |
| Frontend test/lint/build | `pnpm test` + `pnpm lint` + `pnpm build` | Não |
| `forbidden_ports` | `scripts/check-forbidden-ports.ps1` | Não |
| `secrets_grep` | Grep interno sobre `git ls-files` (padrão já implementado no script) | Não |

**Nenhuma etapa obrigatória precisa de um único secret configurado no
GitHub** — todas correm contra a configuração de dev normal de cada
serviço, exactamente como `staging-local-quality-gate.ps1` já garante hoje
(ver o próprio cabeçalho do script). Isto satisfaz directamente a regra
"sem secrets hardcoded" e "E2E não deve ser obrigatório sem stack".

## 4. E2E — deliberadamente fora do gate obrigatório

O runner GitHub-hosted `ubuntu-latest` **não tem** PostgreSQL, MinIO, nem
os 4 processos aplicacionais desta stack a correr — só o próprio
`staging-local-health.ps1 -RequireApps` já falharia de imediato (como
falha localmente quando a stack não está activa — comportamento
correcto, não um bug). Tornar E2E obrigatório neste CI exigiria:
- Subir PostgreSQL/MinIO como *services* do próprio workflow (viável,
  GitHub Actions suporta `services:` com imagens Docker);
- Arrancar os 4 processos aplicacionais dentro do runner;
- Gerir `.env.staging.local` de cada serviço só com **GitHub Secrets**
  (nunca hardcoded no YAML).

Nada disto foi feito nesta iteração — ficaria como uma extensão futura
explícita do `e2e-manual` acima (hoje `if: false`, nunca activo), não uma
"invenção" a caminho deste prompt. **Nunca se declara "E2E pronto para
CI"** sem essa validação real, futura, dedicada.

## 5. Validação local dos comandos (feita nesta iteração)

```powershell
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-quality-gate.ps1
```

Corrido de facto, sem `-WithE2E` (exactamente o âmbito do gate obrigatório
proposto acima) — ver §7 para o resultado. Isto é a validação mais
próxima possível de "os comandos que o CI vai executar", sem ainda ter um
runner GitHub real disponível para confirmar o ambiente Linux
especificamente (§6).

## 6. Limitações desta proposta

| Item | Nota |
|---|---|
| Nenhum workflow foi criado | Decisão explícita do operador nesta iteração — ver preâmbulo |
| `pwsh` em `ubuntu-latest` | Alta confiança (documentado pelo próprio GitHub como parte do toolset default dos runners hospedados), **não testado contra um runner real** nesta iteração |
| `venv/bin/python` vs `venv/Scripts/python.exe` | O YAML proposto já usa o caminho Linux; os scripts locais (`.ps1`) resolvem caminhos via `Join-Path`, portável — mas nunca corrido de facto num runner Linux |
| Cache de dependências | Desenhada (`actions/setup-python` com `cache: pip`, `pnpm/action-setup` + lockfile do pnpm, `npm ci` com `package-lock.json` do content_renderer) — não testada em execução real (não há execução real ainda) |
| Sem deploy | Nenhum job de deploy existe nesta proposta, em nenhuma branch |
| Sem produção | Nada aqui assume nem cria ambiente de produção |

## 7. Ficheiros criados/alterados

| Ficheiro | Operação |
|---|---|
| `frontend/docs/.../07_staging_local_hardening/proposta_cicd_github_actions.md` | **criado** (este documento) |
| `frontend/docs/.../07_staging_local_hardening/resultados_execucao/prompt_08_cicd_real_resultado.md` | **criado** (relatório desta iteração) |

Nenhum `.github/workflows/*.yml`, `.gitlab-ci.yml`, ou equivalente foi
criado. Nenhum script de produto foi alterado.

## 8. Próximo passo recomendado

1. Decisão explícita do operador: activar este workflow (criar
   `.github/workflows/quality-gate.yml` a partir do YAML de §2) ou manter
   como proposta indefinidamente.
2. Se activado: correr uma vez num PR de teste, confirmar que os 9
   passos correm e falham correctamente num runner real (o achado mais
   provável: `pwsh`/caminhos de venv Linux podem precisar de um ajuste
   pontual, apesar da alta confiança de que funcionam como estão).
3. Só depois de o gate obrigatório estar a correr de forma fiável em CI,
   considerar estender para um job E2E manual real (services PostgreSQL/
   MinIO + GitHub Secrets) — não antes.
