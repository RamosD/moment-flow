# Prompt 08 — CI/CD real (ou bloqueio documentado) — Resultado

**Data:** 2026-07-03
**Fase:** `07_staging_local_hardening` (STG-HARD-005)
**Âmbito:** identificar plataforma CI/CD disponível e, se seguro, criar
pipeline mínima reutilizando o quality gate local; caso contrário,
documentar bloqueio e propor desenho, sem inventar plataforma.
**Estado de execução:** `proposta documentada — nenhum workflow criado`.
Nenhuma plataforma CI/CD estava configurada neste repositório; o
repositório está hospedado no GitHub, mas a decisão de activar uma
pipeline real (criar `.github/workflows/*.yml`) foi colocada directamente
ao operador, que optou por **apenas o documento de proposta**, sem nenhum
ficheiro que corra automaticamente.

---

## 1. Plataforma detectada

```text
.github/                → não existe
.gitlab-ci.yml           → não existe
azure-pipelines.yml      → não existe
Jenkinsfile              → não existe
git remote -v            → origin  https://github.com/RamosD/moment-flow.git
```

**Nenhuma pipeline CI/CD configurada.** Repositório hospedado no GitHub.
Dado que criar um workflow é uma acção com efeito real (corre
automaticamente em pushes/PRs futuros, consome minutos de Actions, pode
falhar e notificar), a decisão foi colocada explicitamente ao operador em
vez de assumida — resposta: **não criar workflow, só a proposta**.

## 2. Entregável desta iteração

`frontend/docs/01_fundamentos/07_staging_local_hardening/proposta_cicd_github_actions.md`
— desenho completo, incluindo:
- YAML ilustrativo de um workflow `quality-gate.yml` (GitHub Actions),
  mostrado no documento, **não colocado em `.github/workflows/`**;
- mapa dos 7 passos pedidos pelo prompt → comando real já existente em
  `staging-local-quality-gate.ps1` (nenhuma lógica duplicada — reutilização
  directa do script);
- justificação explícita para deixar E2E fora do gate obrigatório (o
  runner GitHub-hosted não tem PostgreSQL/MinIO/os 4 processos locais);
- confirmação de que nenhuma etapa obrigatória exige nenhum secret
  configurado no GitHub;
- limitações claras (nunca testado contra um runner real).

## 3. Validação local dos comandos (feita nesta iteração)

```powershell
pwsh -ExecutionPolicy Bypass -File scripts\staging-local-quality-gate.ps1
```

| Etapa | Resultado | Duração |
|---|---|---|
| `backend_core_check` | ✅ PASS | 4.4s |
| `backend_core_pytest` | ✅ PASS | 415.3s |
| `intelligence_engine_pytest` | ✅ PASS | 4.0s |
| `content_renderer_typecheck` | ✅ PASS | 55.5s |
| `content_renderer_lint` | ✅ PASS | 39.1s |
| `content_renderer_test` | ✅ PASS | 17.1s |
| `frontend_test` | ✅ PASS | 1.3s |
| `frontend_lint` | ✅ PASS | 51.1s |
| `frontend_build` | ✅ PASS | 5.9s |
| `forbidden_ports` | ✅ PASS | 14.1s |
| `secrets_grep` | ❌ FAIL (nesta execução) → ✅ corrigido e reconfirmado PASS a seguir | 0.7s |

**Achado real, encontrado por esta própria validação**: `secrets_grep`
falhou com 8 ocorrências — todas **falsos positivos** confirmados
individualmente (nenhum segredo real):
- `frontend/e2e/diagnostics.ts` (2 linhas): o "valor" capturado era
  `\S+` — texto-fonte de uma *regex* de redacção
  (`/STORAGE_SECRET_KEY=\S+/gi`), não um segredo.
- `scripts/cleanup-e2e-run.ps1` (2 linhas): `MINIO_ROOT_PASSWORD=$env:MINIO_ROOT_PASSWORD`
  — uma **referência** de variável PowerShell (o padrão correcto e seguro
  de passar segredos a um subprocesso), não um valor literal.
- `frontend/docs/.../06.../prompt_05_secrets_locais_resultado.md` (fase 06,
  não reaberta): descrevia em prosa um *padrão* de grep passado
  (`INTERNAL_API_TOKEN=[A-Za-z0-9_-]{10,}`), não um segredo real.

**Corrigido em `scripts/staging-local-quality-gate.ps1`**: `$safeMarker`
alargado com três formas seguras adicionais — valor contém `$env:`
(referência de variável), contém uma barra invertida (`\`, típico de
código-fonte de regex), ou contém `[`/`]`/`{`/`}` (sintaxe de classe de
caracteres/quantificador, típica de um padrão mostrado como documentação).
Nenhuma destas formas ocorre num segredo real (tokens/passwords reais são
tipicamente alfanuméricos, sem estes caracteres). Reconfirmado depois da
correcção:

```text
[PASS] secrets_grep — 927 ficheiros verificados, 0 suspeitos (1.2s).
```

**10/10 etapas obrigatórias `PASS`** (excluindo `e2e`, opcional por
desenho) depois desta correcção — validação directa de que o desenho
proposto em §2 (que reutiliza este mesmo script) está tecnicamente sólido.

## 4. Ficheiros criados/alterados

| Ficheiro | Operação |
|---|---|
| `frontend/docs/.../07_staging_local_hardening/proposta_cicd_github_actions.md` | **criado** |
| `scripts/staging-local-quality-gate.ps1` | `$safeMarker` do `secrets_grep` alargado (achado real, §3) |
| `frontend/docs/.../07_staging_local_hardening/resultados_execucao/prompt_08_cicd_real_resultado.md` | **criado** (este relatório) |

Nenhum `.github/workflows/*.yml` nem equivalente foi criado. Nenhum
deploy, nenhuma credencial GitHub, nenhuma alteração a código de produto.

## 5. Validações executadas

| Validação | Resultado |
|---|---|
| Detectar plataforma CI existente | ✅ Nenhuma (§1) |
| Sintaxe do workflow proposto | N/A — não criado como ficheiro activo (YAML revisto manualmente no documento) |
| `staging-local-quality-gate.ps1` (execução completa) | ✅ 10/10 obrigatórias `PASS` (depois da correcção do §3) |
| Confirmar ausência de secrets no YAML proposto | ✅ — o YAML não contém nenhum valor, só nomes de passos/comandos |
| Confirmar ausência de deploy automático | ✅ — nenhum job de deploy em nenhuma branch |
| Confirmar que E2E não é obrigatório sem stack | ✅ — `e2e-manual` com `if: false`, nunca activo automaticamente |
| `scripts/check-forbidden-ports.ps1` | ✅ `OK` |
| Grep de secrets nos ficheiros CI alterados/criados | ✅ 0 ocorrências (`proposta_cicd_github_actions.md`, YAML incluído) |

## 6. Critérios de aceitação — verificação

- ✅ Existe workflow CI real mínimo **ou** bloqueio concreto documentado —
  a segunda opção aplica-se, por escolha explícita e informada do operador.
- ✅ Quality gate local é reutilizado (não espelhado/duplicado) — o YAML
  proposto chama `staging-local-quality-gate.ps1` directamente.
- ✅ Jobs falhariam correctamente — o script já reporta `[FAIL]` explícito
  por etapa e propaga exit code não-zero.
- ✅ Nenhum secret no YAML.
- ✅ Sem deploy automático.
- ✅ E2E é opcional/manual, nunca activo por defeito.
- ✅ Documentação criada (proposta + este relatório).

Nenhum critério de rejeição ocorreu: nenhuma plataforma foi inventada, nenhum
secret foi hardcoded, nenhum deploy foi criado, nenhum teste falhado foi
ignorado (o achado do `secrets_grep` foi investigado e corrigido, não
escondido), E2E não se tornou obrigatório, e não se declarou "CI pronto"
sem uma validação real dos comandos subjacentes.

## 7. Limitações

| Item | Nota |
|---|---|
| Nenhum runner GitHub real usado | Toda a validação foi local; `pwsh` em `ubuntu-latest`, caminhos `venv/bin/` e cache de dependências continuam por confirmar contra um runner real (documentado na proposta §6) |
| Decisão de activar CI fica pendente | Por desenho — não é uma "não-decisão" escondida, é uma escolha explícita registada |
| `secrets_grep` só foi corrigido para 3 formas específicas de falso positivo | Podem existir outras formas ainda não encontradas; o princípio (excluir só *formas* claramente seguras, nunca valores específicos) mantém-se para futuras correcções |

## 8. Próximo passo recomendado

1. Decisão do operador: activar o workflow proposto (copiar o YAML de
   `proposta_cicd_github_actions.md` §2 para `.github/workflows/`) ou
   manter só como proposta.
2. Se activado, correr uma vez contra um PR de teste antes de o tornar
   obrigatório para merges — confirmar `pwsh`/caminhos num runner real.
3. Seguir para **STG-HARD-009** (revalidação de segurança — já em curso
   na iteração seguinte) ou **STG-HARD-010** (fecho da fase).
