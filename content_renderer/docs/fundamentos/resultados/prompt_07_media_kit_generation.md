# Relatório de Execução — Prompt 07: Media Kit Generation

- **Data:** 2026-06-22
- **Pipeline:** 07 — Media kit generation
- **Épico/Tarefas do backlog:** CR-701 (media_kit_generation simples / PDF ou HTML), CR-503 (callback), CR-602 (estratégia de fallback HTML reutilizada)
- **Serviço:** `content_renderer`
- **Localização:** `D:\Workspace\ChartRex\momentflow\content_renderer`

---

## 1. Prompt executado

Implementar o **renderer real mínimo** para jobs `media_kit_generation`: ler o
payload (artist, campaign/track opcionais, items, assets, smart links, branding,
metadata), gerar um **media kit simples** (capa, nome do artista, bio curta,
música/campanha, destaques, links, contactos/press, assets listados) em **PDF**
(reutilizando a estratégia do report) com **fallback HTML**, guardar no storage
local e enviar **callback** `completed` (ou `failed` em erro). Sem página
pública, sem editor visual, sem upload externo, sem vídeo, sem scraping, sem APIs
externas.

Backlog de referência: `docs/fundamentos/01_backlog_content_report_renderer.md`.

---

## 2. Objectivo

Fechar o ciclo de `media_kit_generation`:

```text
POST /jobs → valida payload (artist) → modelo de media kit → PDF (ou HTML) → storage local → callback Django
```

reutilizando o toolkit de documento já provado no report, com metadata de
`Asset` consumível pelo Django.

---

## 3. Ficheiros criados

- `src/renderers/shared/pdf-primitives.ts` — primitivas PDF puras (cor, sanitização
  WinAnsi, word-wrap, geometria A4) partilhadas.
- `src/renderers/shared/pdf-doc.ts` — `createPdfDoc` (builder com `pdf-lib` por
  import dinâmico: capa, headings, body, bullets, meta, footnote, paginação).
- `src/renderers/shared/html.ts` — `escapeHtml`, `safeCssColor`, `safeUrl` (só
  http/https/mailto).
- `src/renderers/media-kits/media-kit.model.ts` — schema Zod + `buildMediaKitModel`.
- `src/renderers/media-kits/media-kit.html.ts` — `renderMediaKitHtml`.
- `src/renderers/media-kits/media-kit.pdf.ts` — `renderMediaKitPdf` (usa `createPdfDoc`).
- `src/renderers/media-kits/media-kit-generation.renderer.ts` — renderer orquestrador.
- `tests/media-kit-generation.test.ts` — 13 testes (modelo/HTML, renderer unitário, integração).
- `docs/fundamentos/resultados/prompt_07_media_kit_generation.md` — este relatório.

---

## 4. Ficheiros alterados

| Ficheiro | Alteração |
| -------- | --------- |
| `src/renderers/media-kits/index.ts` | Barrel: re-exporta o renderer real; remove o placeholder simulado. |
| `src/renderers/reports/report.pdf.ts` | **Refactor de reutilização:** passa a usar `createPdfDoc` partilhado (mesma saída PDF; testes do report mantêm-se verdes). |
| `src/renderers/reports/report.html.ts` | Usa `escapeHtml`/`safeCssColor` partilhados (re-exporta `escapeHtml` por compatibilidade). |
| `tests/jobs.test.ts` | O teste de dispatch de `media_kit_generation` passa payload válido mínimo (`artist.name`). |

> O `report-generation.renderer.ts` e o seu modelo **não** foram alterados (apenas
> os builders PDF/HTML adoptaram o toolkit partilhado, sem mudança de
> comportamento — confirmado pelos testes do report).

---

## 5. Tipo de output gerado

| Modo (`REPORT_OUTPUT_FORMAT`) | Output | `mime_type` | `fallback_html` |
| ----------------------------- | ------ | ----------- | --------------- |
| `auto` (default) / `pdf`      | `media_kit.pdf` | `application/pdf` | `false` |
| `auto`/`pdf` **com falha de PDF** | `media_kit.html` | `text/html` | `true` |
| `html`                        | `media_kit.html` | `text/html` | `true` |

- **PDF** via `pdf-lib` (toolkit partilhado, pure JS, sem browser/Playwright):
  capa de marca com nome do artista + tagline, bio, “Featured” (música·campanha),
  Highlights (items), Links (smart links + artist.links), Contact (contact/press +
  email/management/…), Assets listados, e carimbo de geração.
- **HTML** standalone (CSS inline), tudo escapado; links só com esquemas seguros.
- `output_type: "media_kit"`, `template_key: "media_kit_cover"`.

Leitura do payload: `artist` (name/tagline/bio/contact/press/links), `campaign?`,
`track?`, `items[]` (highlights), `assets[]`, `smart_links` (array ou objecto),
`branding` (cor), `metadata`.

---

## 6. Comandos executados

```bash
npm run build                  # tsc -p tsconfig.json
npx vitest run                 # toda a suite
npm run lint                   # eslint .

# Smoke manual POST /jobs media_kit_generation (app real + callback HTTP local),
# 4 cenários: PDF rico, PDF mínimo, HTML fallback e payload inválido.
node smoke-media-kit.cjs       # script temporário, removido após verificação
```

---

## 7. Resultado das validações

| Validação | Resultado |
| --------- | --------- |
| `npm run build` (tsc) | ✅ Sem erros |
| `npm run lint` (eslint) | ✅ Sem erros |
| `npx vitest run` | ✅ **11 ficheiros, 92 testes** (13 novos) |
| Manual `POST /jobs media_kit_generation` | ✅ Ver abaixo |

**Saída do smoke manual:**

```text
[PDF rich]       http=202 result.status=completed callback.status=completed
                 file=media_kit.pdf  mime=application/pdf bytes=1617 head="%PDF-" exists=true fallback_html=false
[PDF minimal]    http=202 result.status=completed callback.status=completed
                 file=media_kit.pdf  mime=application/pdf bytes=1033 head="%PDF-" exists=true fallback_html=false
[HTML fallback]  http=202 result.status=completed callback.status=completed
                 file=media_kit.html mime=text/html      bytes=1912 head="<!DOC" exists=true fallback_html=true
[invalid payload] http=202 result.status=failed callback.status=failed
                 error.code=render_failed msg="Falha ao gerar o media kit." first={"code":"invalid_payload",...}
```

**Novos testes (13) cobrem:** rejeição sem nome de artista; payload mínimo (só
artist.name); normalização de payload rico (items/assets/links/contacts); HTML com
os dados + link seguro; bloqueio de `javascript:`; geração de PDF (mínimo e rico)
persistido (assinatura `%PDF-`); asset metadata compatível com Django; fallback
HTML; payload inválido → `failed`; falha de storage → `failed`; integração
`POST /jobs` callback `completed` com asset + ficheiro em disco; integração
callback `failed` em payload inválido.

---

## 8. Decisões tomadas

1. **Toolkit de documento partilhado.** Extraí `createPdfDoc` + primitivas
   PDF/HTML para `renderers/shared/` e adoptei-as no report (sem mudança de
   comportamento) e no media kit — “reutilizar a estratégia do report” feito de
   forma DRY, evitando duplicação. Os testes do report confirmam zero regressão.
2. **Regra de validade mínima.** O único requisito é **nome do artista**; payload
   sem artista → `invalid_payload` → `failed`. Assim “payload mínimo funciona”
   (só `artist.name`) e “payload com items funciona”.
3. **Reutilização de `REPORT_OUTPUT_FORMAT`.** O mesmo flag governa o formato de
   documento (report e media kit), evitando nova configuração e alterações ao
   report.
4. **Links seguros.** No HTML, URLs passam por `safeUrl` (só http/https/mailto);
   esquemas activos (`javascript:`) são renderizados como texto, não como `href`.
5. **Erros normalizados + callback genérico.** O dispatcher já envia callback por
   job_type; `aggregateRenderError` produz “Falha ao gerar o media kit.” com o erro
   real do output em `details.first_error`.
6. **Sem features proibidas.** Sem página pública, editor, upload externo, vídeo,
   scraping nem APIs externas — apenas apresentação dos dados recebidos.

---

## 9. Pendências

- **Hardening (Prompt 08)** — normalização de erros, partial success, timeouts,
  logs e robustez antes do teste com o Backend Core real.
- **Layout PDF avançado** (imagens/logos, capa desenhada, grelhas ricas) — fora do
  escopo.
- **Migração opcional do report** para `createPdfDoc` já foi feita; o
  `report.model`/renderer permanecem intactos.
- **Teste manual com Backend Core Django real** (CR-903) — pendente do Django em
  `localhost:8000` para confirmar `MediaKit` generated + `Asset`.

---

## 10. Próximo passo recomendado

Avançar para o **Pipeline 08 — Erros, partial success e hardening**: normalizar
códigos de erro, reforçar partial success do content, **aplicar `RENDER_TIMEOUT_SECONDS`
ao render** (hoje só o callback tem timeout), enriquecer os logs de ciclo de vida e
garantir que os `details` nunca expõem token/segredos — preparando o teste E2E com
o Backend Core real (CR-903).
