# Relatório de Execução — Hardening 03: Echo de template_key/template_id (R-HARD-004)

- **Serviço:** `content_renderer`
- **Data:** 2026-06-23
- **Backlog de referência:** [`03_backlog_hardening_pos_mvp_renderer.md`](../03_backlog_hardening_pos_mvp_renderer.md) → **R-HARD-004**

---

## 1. Prompt executado

Garantir que o `content_generation` devolve `template_key`/`template_id` e
metadados de resolução de template de forma **explícita** e **compatível** com o
Backend Core (Django), sem quebrar payloads antigos, sem alterar geração visual,
sem criar templates novos e **sem inventar** `template_id`.

## 2. Objectivo

Facilitar a associação dos outputs ao `Template`/`ContentOutput` no Django,
expondo: o template realmente usado, o pedido original, o resultado da resolução,
e os _flags_ de fallback de template e de formato — de forma aditiva
(retrocompatível) e sem secrets na `metadata`.

## 3. Ficheiros criados

| Ficheiro | Propósito |
|---|---|
| `docs/fundamentos/resultados/prompt_hardening_03_template_echo.md` | Este relatório. |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `src/jobs/job.types.ts` | `RenderOutput` ganha `template_id?: string` (ecoado, nunca inventado). |
| `src/renderers/content/content-generation.renderer.ts` | `OutputSpec.template_id`; leitura de `template_id` em `expected_outputs[]` (e aliases `template_uuid`/`id`) e em `templates[]`; resolução de template/dimensões _up-front_; metadados de resolução partilhados pelos caminhos de sucesso e falha; `template_key` do output falhado passa a ser o **resolvido** (valor compatível com o Django). |
| `tests/content-generation.test.ts` | Nova suite "template echo (R-HARD-004)" (8 testes unit) + 1 teste de integração (callback). |
| `README.md` | Contrato de output de `content_generation` + tabela "Echo de template (R-HARD-004)". |
| `docs/fundamentos/02_estado_content_report_renderer.md` | Features, contratos, validações (129 testes), pendências e próximo passo. |

## 5. Campos adicionados ao output

**Topo do output:**

| Campo | Regra |
|---|---|
| `template_key` | template **realmente usado** (resolvido pelo registry). Já existia; mantido. No output **falhado** passa a ser o valor **resolvido** (nunca uma chave desconhecida). |
| `template_id` | id **ecoado** do pedido (`templates[]` ou `expected_outputs[]`). Só presente quando recebido — **nunca inventado**. |

**`metadata` (aditivo):**

| Campo | Significado |
|---|---|
| `requested_template_key` | `template_key` original do pedido (preservado mesmo se desconhecido). |
| `requested_template_id` | `template_id` original, se enviado. |
| `resolved_template_key` | template resolvido pelo registry. |
| `used_fallback_template` | `true` se o `template_key` pedido não existe (→ `generic_post`). |
| `used_fallback_format` | `true` se o `format`/`dimension` pedido não existe (→ `post_1_1`). |
| `dimension` / `width` / `height` | formato resolvido e dimensões (px). |

`template_id`/`requested_template_id` só aparecem quando recebidos. Os mesmos
campos de resolução acompanham também outputs **falhados**.

## 6. Compatibilidade com Django

- O `backend_core` **não** está neste repositório; a referência é o guia E2E
  ([`guia_e2e_backend_core.md`](../guia_e2e_backend_core.md)), que confirma:
  _"o Django resolve o `Template` de cada output por `template_key`/`template_id`
  ou, em fallback, por `output_type` ligado ao `content_pack`"_.
- Por isso `template_key` e `template_id` ficam no **topo** do output (onde o
  Django os lê); os restantes campos são `metadata` **aditiva**.
- Alterações **aditivas** e retrocompatíveis: nenhum campo existente foi removido
  ou renomeado; payloads antigos (sem `template_id`) continuam válidos
  (`template_id` ausente, sem `requested_template_id`).
- `callback.payload.ts` **não** precisou de alteração: a forma de content
  (`result.outputs[]`) já encaminha os outputs tal como produzidos.

## 7. Testes criados/alterados

**`tests/content-generation.test.ts` — suite "template echo (R-HARD-004)" (unit):**
- preserva `template_key` válido (topo + `requested`/`resolved` na metadata);
- ecoa `template_id` vindo de `expected_outputs[]`;
- preserva `template_id` vindo de `templates[]` (override);
- fallback de template desconhecido fica explícito (`used_fallback_template:true`,
  `resolved_template_key:generic_post`, `template_key` topo = resolvido);
- fallback de formato desconhecido fica explícito (`used_fallback_format:true`,
  `dimension:post_1_1`);
- output **sem** `template_id` continua válido (id não inventado);
- output **falhado** também carrega os campos de echo;
- `metadata` não contém dados sensíveis (sem chaves token/secret/…; sem o token).

**Integração (callback):** `callback output carries template_key/template_id and
resolution metadata` — confirma a compatibilidade através do callback.

## 8. Comandos executados

```bash
npm run build   # tsc -p tsconfig.json
npm run lint    # eslint .
npm test        # vitest run
```

## 9. Resultados

| Validação | Resultado |
|---|---|
| `npm run build` | ✅ Sem erros |
| `npm run lint` | ✅ Sem erros |
| `npm test` | ✅ **129 testes** em **13 ficheiros** (120 → 129; +9) |

Critérios de aceitação R-HARD-004:

- ✅ `content_generation` devolve o `template_key` usado.
- ✅ `content_generation` preserva o `template_id` quando recebido (sem inventar).
- ✅ Fallback de template fica explícito (`used_fallback_template`).
- ✅ Fallback de formato fica explícito (`used_fallback_format`).
- ✅ Callback continua compatível com o Django (campos aditivos).
- ✅ Build, lint e testes passam.

## 10. Pendências

- **Confirmação no Django real:** validar, no E2E com PostgreSQL (R-HARD-002/003),
  que o Django consome `template_id` no topo do output sem regressões — o contrato
  foi seguido a partir do guia, mas o `backend_core` não está neste repositório.
- **`report_generation`/`media_kit_generation`** não foram alterados (fora do
  âmbito); o echo de template aplica-se só a `content_generation`.

## 11. Próximo passo recomendado

Avançar para **R-HARD-005 — Preparar a interface de storage para S3/R2**
(`StorageProvider` + factory), mantendo o `LocalStorage` funcional e o contrato de
`Asset` inalterado, antes do harness E2E com PostgreSQL.
