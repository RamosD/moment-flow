# Relatório de Execução — Prompt 05: Content Generation

- **Data:** 2026-06-22
- **Pipeline:** 05 — Content generation
- **Épico/Tarefas do backlog:** CR-501 (renderer de content_generation), CR-502 (packs iniciais), CR-503 (callback completed/failed), CR-802 (partial success)
- **Serviço:** `content_renderer`
- **Localização:** `D:\Workspace\ChartRex\momentflow\content_renderer`

---

## 1. Prompt executado

Implementar o **renderer real mínimo** para jobs `content_generation`: ler o
payload de domínio, escolher template por `template_key` (com fallback), resolver
formato/dimensão, gerar SVG, converter para **PNG** (Sharp), guardar no **storage
local** e devolver `result.outputs` no contrato esperado pelo Backend Core
(Django). Fechar o ciclo enviando **callback** `completed`, `partially_completed`
ou `failed`. Suportar os packs iniciais, fallback quando o pack é desconhecido ou
não há `expected_outputs`, e _partial success_. Sem PDF, sem vídeo, sem editor
visual, sem IA, sem chamar o Django real nos testes.

Backlog de referência: `docs/fundamentos/01_backlog_content_report_renderer.md`.

---

## 2. Objectivo

Tornar o `content_renderer` o primeiro serviço a **fechar o ciclo operacional
real** de `content_generation`:

```text
POST /jobs → render SVG → PNG (Sharp) → storage local → callback Django
```

gerando ficheiros reais, devolvendo metadata de `Asset` compatível com o Django e
reportando o resultado técnico (completed / partially_completed / failed) sem
decidir regras de produto (permissões, billing).

---

## 3. Ficheiros criados

- `src/renderers/content/content-generation.renderer.ts` — renderer real de
  `content_generation` (leitura de payload, selecção de template/format, render
  SVG→PNG, storage, outputs no contrato Django, packs, fallback, partial success,
  e `aggregateRenderError` para o callback failed).
- `tests/content-generation.test.ts` — 13 testes (unitários do renderer +
  integração `POST /jobs` com callback mockado).
- `docs/fundamentos/resultados/prompt_05_content_generation.md` — este relatório.

---

## 4. Ficheiros alterados

| Ficheiro | Alteração |
| -------- | --------- |
| `src/renderers/renderer.types.ts` | `RenderContext` passa a carregar `storage: LocalStorage` (além de `config` e `logger`). |
| `src/renderers/content/index.ts` | Barrel: re-exporta o renderer real (e `aggregateRenderError`) do novo ficheiro; substitui o placeholder simulado. |
| `src/jobs/job.service.ts` | Dispatcher passa a injectar `storage` no contexto e a **enviar o callback** (`completed`/`partially_completed`/`failed`) após o render; entrega de callback é best-effort e **não-fatal** (risco 14.5). Novas deps `storage` e `callbackClient`. |
| `src/app.ts` | `createApp` constrói `LocalStorage` + `CallbackClient` e injecta-os no `JobService`; novas opções `storage` e `callbackClient` para testes (sem HTTP real). |
| `src/jobs/job.controller.ts` | Removido o flag `simulated: true` do corpo do 202 (content é real agora); docstring actualizada. |
| `tests/jobs.test.ts` | `buildApp` usa storage em pasta temporária e injecta um callback mockado (não chama o Backend Core real nem polui o working dir). |

> Nota: os renderers `report_generation` e `media_kit_generation` continuam
> _placeholders_ simulados (Pipelines 06–07). O wiring de callback no dispatcher é
> genérico, mas só o `content_generation` produz assets reais nesta fase.

---

## 5. Packs suportados

| Content pack          | Template default     | Output type | `required` |
| --------------------- | -------------------- | ----------- | ---------- |
| `release_pack`        | `release_card`       | `post`      | ✅          |
| `milestone_pack`      | `milestone_card`     | `post`      | ✅          |
| `weekly_growth_pack`  | `weekly_growth_card` | `post`      | ✅          |
| `monthly_recap_pack`  | `generic_post`       | `post`      | ✅          |
| `auto_media_kit`      | `media_kit_cover`    | `cover`     | ⬜ (fallback simples) |
| _desconhecido / ausente_ | `generic_post`    | `post`      | ✅ (fallback) |

- O pack é extraído de `content_pack` como string ou objecto
  (`type`/`key`/`pack`/`pack_type`/`slug`).
- Quando o payload traz `expected_outputs`, estes **têm prioridade** sobre os
  defaults do pack; cada output escolhe o seu `template_key` (fallback via
  registry) e formato/dimensão.
- Sem `expected_outputs` **e** sem pack reconhecido → **1 output fallback**
  garantido (nunca zero outputs).

---

## 6. Outputs gerados

`result.outputs[]` segue o contrato do Django (CR-501):

```jsonc
{
  "output_type": "post",
  "format": "png",
  "status": "completed",        // ou "failed" (partial success)
  "title": "Aurora",
  "caption": "Summer Push",
  "cta": "Listen now",
  "required": true,
  "template_key": "release_card",
  "asset": {
    "storage_provider": "local",
    "bucket": "",
    "storage_key": "workspaces/<ws>/jobs/<job>/output_001.png",
    "file_name": "output_001.png",
    "mime_type": "image/png",
    "file_size_bytes": 50858,
    "width": 1080,
    "height": 1080,
    "duration_seconds": null,
    "checksum": "<sha256>"
  },
  "metadata": {
    "content_pack": "release_pack",
    "dimension": "post_1_1",
    "width": 1080, "height": 1080,
    "requested_template_key": "release_card",
    "used_fallback_template": false,
    "used_fallback_format": false,
    "smart_link_url": "https://chartrex.link/midnight"
  }
}
```

- **Outputs failed** (partial success) não têm `asset` e levam
  `metadata.error = { code, message }` (seguro: sem stack, sem segredos).
- **Regra de status geral:**
  - `completed` — todos os outputs gerados (sem falhas);
  - `partially_completed` — ≥1 gerado **e** ≥1 falhado;
  - `failed` — nenhum output gerado → callback `failed` com `result: null` e
    `error.code = render_failed` (detalhes seguros: `outputs_total`,
    `outputs_failed`, `first_error`).

---

## 7. Comandos executados

```bash
npm run build              # tsc -p tsconfig.json
npx vitest run             # toda a suite
npm run lint               # eslint .

# Smoke manual POST /jobs content_generation (app real + callback HTTP local):
node smoke-content.cjs     # script temporário, removido após verificação
```

O smoke arranca a app construída (`dist`), levanta um servidor HTTP local a fazer
de callback do Django, faz `POST /jobs` com `content_pack: release_pack` +
`expected_outputs`, e valida o 202, o callback recebido e os ficheiros em disco.

---

## 8. Resultado das validações

| Validação | Resultado |
| --------- | --------- |
| `npm run build` (tsc) | ✅ Sem erros |
| `npm run lint` (eslint) | ✅ Sem erros |
| `npx vitest run` | ✅ **9 ficheiros, 68 testes** (13 novos) |
| Manual `POST /jobs content_generation` | ✅ Ver abaixo |

**Saída do smoke manual:**

```text
HTTP status        : 202
result.status      : completed
outputs            : 2
callback token ok  : true
callback status    : completed
  output[0] type=post  status=completed tpl=release_card   dim=1080x1080 bytes=50858 mime=image/png fileExists=true pngSig=true
  output[1] type=story status=completed tpl=generic_story  dim=1080x1920 bytes=67373 mime=image/png fileExists=true pngSig=true
```

**Novos testes (13) cobrem:**
- `content_generation` gera ≥1 PNG real e o ficheiro existe no storage local;
- metadata de asset compatível com Django (storage_provider/bucket/mime/width/
  height/checksum/storage_key);
- `release_pack`, `milestone_pack`, `weekly_growth_pack`, `monthly_recap_pack`
  geram output com o template correcto;
- pack desconhecido usa fallback `generic_post`;
- `expected_outputs` vazio gera 1 output fallback;
- selecção de template + resolução de dimensão a partir de `expected_outputs`;
- partial success (1 completed + 1 failed → `partially_completed`, erro seguro);
- todos falham → `failed`;
- integração `POST /jobs`: callback `completed` com asset metadata + ficheiro em
  disco (assinatura PNG válida);
- integração `POST /jobs`: callback `failed` quando todos os outputs falham.

---

## 9. Decisões tomadas

1. **Callback no dispatcher (job.service), não no renderer.** O renderer devolve
   um `RenderResult` (status + outputs) puro e testável; o `JobService` decide o
   payload (`buildCompletedPayload` vs `buildFailedPayload`) e entrega-o. Mantém o
   renderer focado em gerar activos (risco 14.2).
2. **Entrega de callback não-fatal.** Falha de callback é logada
   (`callback.delivery_failed`) mas **não** descarta os ficheiros nem falha o HTTP
   202 — o Django reconcilia a partir dos assets persistidos (risco 14.5).
3. **`storage` no `RenderContext`.** Injecta-se o backend de storage no contexto
   (DI), o que mantém a interface storage-agnóstica e torna o partial/total
   failure testável injectando um storage que falha.
4. **Execução síncrona no pedido.** `dispatch → callback → 202` em vez de
   background, conforme a 1ª opção do CR-203: mais simples e determinístico para
   testes (o callback já foi entregue quando o 202 responde).
5. **Regra de status conservadora.** Qualquer falha com ≥1 sucesso →
   `partially_completed` (mais honesto para o Django do que esconder falhas de
   outputs opcionais sob `completed`).
6. **`output.format = "png"`** (formato de ficheiro, como no contrato Django); o
   formato social/dimensão (`post_1_1`, `story_9_16`, …) vai para `metadata.dimension`
   e para `asset.width/height`.
7. **Payload defensivo.** Helpers de coerção (`asRecord`/`asString`/`asBoolean`)
   tratam o payload como input não-confiável; aceita `content_pack` como string ou
   objecto e `templates` como array ou mapa (acoplamento mínimo — risco 14.1).
8. **Erros seguros.** `toSafeError` só expõe `code` + `message` (sem stack); o
   callback failed agrega `outputs_total`/`outputs_failed`/`first_error`.
9. **Testes sem Backend Core real.** `createApp` ganhou overrides `storage` e
   `callbackClient`; os testes usam pasta temporária e um callback mock que regista
   chamadas (restrição cumprida).

---

## 10. Pendências

- **`report_generation`** (PDF/HTML) — Pipeline 06 (CR-601/CR-602); continua
  simulado, mas o callback genérico já o cobre.
- **`media_kit_generation`** — Pipeline 07 (CR-701); idem.
- **Execução em background leve** (setImmediate/promise) caso renders fiquem
  pesados — hoje é síncrono curto (CR-203 aceita ambos).
- **Retry de callback** — fora do escopo; hoje é tentativa única com timeout.
- **Layout avançado** (wrapping de texto longo, logos/imagens, múltiplos cards
  por pack) — fora do escopo desta fase.
- **Teste manual com Backend Core Django real** (CR-903) — pendente do ambiente
  Django a correr em `localhost:8000` com o mesmo `INTERNAL_API_TOKEN`.

---

## 11. Próximo passo recomendado

Avançar para o **Pipeline 06 — Report generation** (CR-601/CR-602): gerar PDF
simples (ou fallback HTML) para `report_generation`, reutilizando o mesmo ciclo já
provado (`render → storage → callback`) e o `RenderContext` com `storage`. Em
paralelo, executar o **teste manual CR-903** ligando o `content_renderer` ao
Backend Core Django real para confirmar a criação de `ContentOutput`/`Asset` a
partir do callback `completed`.
