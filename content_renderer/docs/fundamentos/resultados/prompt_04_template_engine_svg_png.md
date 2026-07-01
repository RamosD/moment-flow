# Relatório de Execução — Prompt 04: Template Engine e Render SVG → PNG

- **Data:** 2026-06-22
- **Pipeline:** 04 — Template engine e renderização SVG → PNG
- **Épico/Tarefas do backlog:** CR-401 (registry de templates), CR-402 (render SVG → PNG), CR-403 (dimensões)
- **Serviço:** `content_renderer`
- **Localização:** `D:\Workspace\ChartRex\momentflow\content_renderer`

---

## 1. Prompt executado

Implementar o **template engine mínimo** e a **renderização inicial de imagens
estáticas** via SVG convertido para PNG, sem editor visual, sem browser, sem
vídeo e sem PDF. Inclui registry de templates (resolução + fallback + metadados
de formato/dimensão), renderer SVG (título, subtítulo, artista, faixa, campanha,
métrica/milestone, brand color, fundo), conversão para PNG com Sharp, suporte às
quatro dimensões, sanitização de texto e testes.

Backlog de referência: `docs/fundamentos/01_backlog_content_report_renderer.md`.

---

## 2. Objectivo

Dar ao renderer a capacidade de **gerar imagens reais** (PNG) a partir de
templates simples e dados de domínio, com dimensões corretas por formato e
fallbacks seguros — mantendo o render independente de browser e sem assets
remotos nem IA.

---

## 3. Ficheiros criados

- `src/templates/dimensions.ts` — formatos suportados, `FORMAT_DIMENSIONS`, `resolveOutputDimensions`.
- `src/templates/svg.ts` — `buildSvg`, `renderSvgToPng`, `sanitizeTextForSvg`, `sanitizeColor`.
- `tests/templates.test.ts` — testes do registry, SVG, sanitização, dimensões e PNG.
- `docs/fundamentos/resultados/prompt_04_template_engine_svg_png.md` — este relatório.

---

## 4. Ficheiros alterados

| Ficheiro | Alteração |
| -------- | --------- |
| `src/templates/registry.ts` | Reescrito: definições de template (formato default + `buildSpec`), `resolveTemplate` (com fallback), `renderTemplate` (SVG → PNG). |
| `package.json` / `package-lock.json` | Nova dependência `sharp ^0.35.2`. |
| `README.md` | Secção do template engine, stack (Sharp), estrutura e limitações/próximos passos. |

> O renderer `renderers/content/index.ts` **não** foi alterado: o engine é
> entregue e testado isoladamente; o encadeamento no fluxo de job é o próximo
> pipeline.

---

## 5. Templates suportados

| `template_key`        | Formato default | Badge          |
| --------------------- | --------------- | -------------- |
| `generic_post`        | `post_1_1`      | —              |
| `generic_story`       | `story_9_16`    | —              |
| `milestone_card`      | `post_1_1`      | `MILESTONE`    |
| `weekly_growth_card`  | `post_1_1`      | `WEEKLY GROWTH`|
| `release_card`        | `post_1_1`      | `NEW RELEASE`  |
| `report_cover`        | `post_4_5`      | `REPORT`       |
| `media_kit_cover`     | `post_4_5`      | `MEDIA KIT`    |

- Fallback de template desconhecido → `generic_post`.
- O SVG suporta: `title`, `subtitle`, `artistName`, `trackTitle`, `campaignName`,
  `metric`/milestone, `brandColor` (sanitizado) e fundo simples.

---

## 6. Formatos suportados

| Formato          | Largura × Altura |
| ---------------- | ---------------- |
| `post_1_1`       | 1080 × 1080      |
| `post_4_5`       | 1080 × 1350      |
| `story_9_16`     | 1080 × 1920      |
| `thumbnail_16_9` | 1280 × 720       |

Formato desconhecido/ausente → fallback seguro `post_1_1` (1080 × 1080), com
`usedFallback: true`.

**Funções reutilizáveis** (pedidas no prompt): `buildSvg`, `renderSvgToPng`,
`resolveOutputDimensions`, `sanitizeTextForSvg` (+ extra `sanitizeColor`,
`renderTemplate`, `resolveTemplate`).

---

## 7. Comandos executados

```bash
npm install sharp          # rasterização SVG → PNG (libvips, sem browser)
npm run build              # tsc
npm run lint               # eslint .
npx vitest run             # testes

# Smoke manual (dist) — renderTemplate por formato + fallback
node -e "... renderTemplate + sharp().metadata() ..."
# release_card/post_1_1        -> 1080x1080
# milestone_card/story_9_16    -> 1080x1920
# report_cover/thumbnail_16_9  -> 1280x720
# unknown_key/unknown_format   -> generic_post / post_1_1 (fallback)
```

---

## 8. Resultado das validações

| Validação | Resultado |
| --------- | --------- |
| `npm run build` (tsc) | ✅ Sem erros |
| `npm run lint` (eslint) | ✅ Sem erros |
| `npx vitest run` | ✅ 8 ficheiros, **55 testes** (18 novos) |
| Smoke `renderTemplate` por formato | ✅ PNG 1080×1080 / 1080×1920 / 1280×720 |
| Smoke fallback (template + formato) | ✅ `generic_post` / `post_1_1` |
| Render sem browser | ✅ Sharp (libvips), zero dependências de browser |

**Novos testes (18) cobrem:** template_key válido; cada key do catálogo resolve
para si mesma; fallback de template desconhecido/ausente; `sanitizeTextForSvg`
(escape XML, remoção de controlos, clamp de tamanho); `sanitizeColor` (hex/named
ok, injecção rejeitada); `buildSvg` contém título + SVG bem-formado; título
malicioso é escapado; campos opcionais presentes; dimensões corretas por formato;
formato desconhecido usa fallback; PNG real gerado (assinatura + metadata Sharp);
`renderTemplate` produz PNG nas dimensões exactas de cada formato; fallback de
template e de formato em `renderTemplate`.

---

## 9. Decisões tomadas

1. **Sharp (libvips) em vez de browser:** rasteriza SVG → PNG sem Playwright nem
   headless browser, cumprindo “render não depende de browser”.
2. **Dimensões forçadas no PNG:** `renderSvgToPng` aplica `resize(w, h, { fit: 'fill' })`
   como garantia de exactidão (o SVG já é autorado no tamanho-alvo).
3. **Sanitização em camadas:** `sanitizeTextForSvg` (remove controlos, colapsa
   espaços, limita tamanho, escapa `& < > " '`) e `sanitizeColor` (só hex/named,
   senão fallback) — evita SVG inválido e injecção em atributos.
4. **Fonte do sistema (sans-serif):** sem fontes embebidas nem assets remotos; o
   texto usa `Arial, Helvetica, sans-serif`. Os testes verificam o **SVG** (string),
   independentes da fonte instalada.
5. **Fonte de fundo ASCII no código:** o separador de linha e o regex de controlos
   foram escritos em ASCII puro (regex via string escapada) para evitar bytes de
   controlo no código-fonte.
6. **Engine desacoplado do fluxo de job:** `renderTemplate` é a API pública pronta
   a usar; o `renderers/content` continua simulado e a integração
   (background → render → storage → callback) fica para o Pipeline 05 (CR-203/CR-501),
   respeitando “não implementar renderização real ainda” no fluxo de job e evitando
   misturar escopos.

---

## 10. Pendências

- **Integração no `POST /jobs`:** ler o payload do job, escolher template/formato,
  `renderTemplate` → `storage.saveBuffer` → `callbackClient.send` em background
  (CR-203 / CR-501).
- **PDF/HTML** para report e media kit — Pipelines 06–07.
- **Layout avançado** (wrapping de texto longo, imagens/logos, múltiplas linhas) —
  fora do escopo desta fase.
- O `result` do `POST /jobs` continua **simulado** (`simulated: true`).

---

## 11. Próximo passo recomendado

Avançar para o **Pipeline 05 — Content generation**, ligando o ciclo real:

1. Mapear o payload `content_generation` (campaign, artist, track, content_pack,
   templates, `expected_outputs`) para `TemplateContent` + `template_key` + `format`.
2. Para cada `expected_output`: `renderTemplate` → `storage.saveBuffer` →
   acumular `result.outputs` com a metadata de `Asset`.
3. Responder **202** e, em background leve, enviar callback `completed`
   (ou `partially_completed`/`failed`) com o contrato do Django.

Critério de pronto: um `content_generation` válido gera pelo menos um PNG real no
storage local, acessível via `/files`, e dispara callback `completed` com a
metadata de asset compatível com o Django.
