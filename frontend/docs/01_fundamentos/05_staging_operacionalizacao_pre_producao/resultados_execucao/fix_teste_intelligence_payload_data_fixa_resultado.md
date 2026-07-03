# Fix — `test_intelligence_payload.py` data fixa desactualizada — Resultado

**Data:** 2026-07-02
**Ficheiro:** `backend_core/apps/campaigns/tests/test_intelligence_payload.py`
**Teste:** `TestRichCampaign::test_all_sections_populated_and_json_safe`
**Estado da execução:** `resolvido` — a única falha pré-existente e conhecida da suite backend (rastreada nos relatórios da fase 05 desde o Prompt 03, task `task_1d40d090`) está corrigida. A suite completa do Backend Core passa agora a 100%.

---

## 1. Causa raiz

O teste **não** falhava por a data `date(2026, 6, 25)` ter "expirado" em
sentido literal — falhava porque a fixture auxiliar `_add_clicks` **ignorava
o próprio parâmetro que recebia**.

```python
def _add_clicks(workspace, campaign, *, today, n_today=1, n_old=1, n_ancient=1):
    """Create a smart link + clicks across the 7d / 30d / older buckets."""
    link = factories.SmartLinkFactory(campaign=campaign, workspace=workspace)
    base = timezone.now()          # <-- "today" nunca é lido aqui
```

Todos os call sites passavam `today=ref` (com `ref = date(2026, 6, 25)`),
mas o corpo da função usava sempre `timezone.now()` — a hora real do
relógio da máquina — para gerar os `clicked_at` dos cliques de teste.

Entretanto, `build_campaign_intelligence_payload(..., reference_date=ref)`
agrega os cliques em janelas de 7/30 dias **ancoradas em `ref`**
(`apps/campaigns/intelligence_payload.py::_smart_link_stats`, filtro
`clicked_at__date__lte=ref` / `__gte=window_7|window_30`).

Resultado: os cliques eram criados relativos ao relógio real (que avança
todos os dias), mas contados relativos a uma âncora fixa (`ref`) que fica
cada vez mais distante do relógio real. À medida que a data real se afasta
de `2026-06-25`, os três cliques (`today`, `-10 dias`, `-40 dias`, todos
relativos ao relógio real) deixam de cair nos buckets que o teste espera
relativamente a `ref`, e a asserção de `clicks_last_30_days` (a mais
sensível ao desalinhamento, por ter uma janela mais estreita relativa ao
desvio acumulado) começa a falhar — exactamente o sintoma reportado:
`{'clicks_last_30_days': 1} != {'clicks_last_30_days': 2}`.

**Não é um bug de produto.** `_smart_link_stats` está correcto — agrega
sempre relativamente ao `reference_date` que lhe é passado, tal como
documentado. O bug estava inteiramente na fixture de teste, que prometia
(pelo nome do parâmetro `today`) ancorar os cliques a uma data controlada e
não cumpria essa promessa.

---

## 2. Ficheiros alterados

Só um ficheiro, só a fixture auxiliar — nenhuma alteração de produto:

| Ficheiro | Alteração |
|---|---|
| `backend_core/apps/campaigns/tests/test_intelligence_payload.py` | `_add_clicks` passa a ancorar `clicked_at` em `today` (o parâmetro que já recebia) em vez de `timezone.now()`; import de `datetime`/`time` acrescentado |

Nenhum ficheiro de produto (`intelligence_payload.py`, models, settings) foi
tocado.

---

## 3. Resumo da correcção

```python
def _add_clicks(workspace, campaign, *, today, n_today=1, n_old=1, n_ancient=1):
    """Create a smart link + clicks across the 7d / 30d / older buckets.

    Anchored to ``today`` (not ``timezone.now()``): the payload builder buckets
    clicks relative to the ``reference_date`` the caller passes in, which in
    these tests is a fixed date, not real wall-clock time. Anchoring click
    timestamps to real "now" instead of that same fixed date made the buckets
    silently drift out of alignment as real time moved away from the fixed
    reference — the fix is to use the one anchor the test actually cares
    about.
    """
    link = factories.SmartLinkFactory(campaign=campaign, workspace=workspace)
    base = timezone.make_aware(datetime.combine(today, time(12, 0)))
    ...
```

**Porque isto não é "trocar uma data fixa por outra data fixa que vai
voltar a expirar":** `date(2026, 6, 25)` continua a ser o valor literal
usado, mas deixou de ter qualquer relação com o relógio real em qualquer
ponto do teste — tanto a criação dos cliques como a agregação do payload
passam a estar ancoradas ao **mesmo** valor (`ref`/`today`), que é passado
explicitamente pelo próprio teste, não derivado de `timezone.now()`. O
teste é agora determinístico para qualquer data em que corra, incluindo
daqui a 10 anos — não porque a data deixou de ser "antiga", mas porque
deixou de ser comparada com o relógio real.

Alternativas consideradas e descartadas:
- **Congelar o relógio (`freezegun`/similar):** não existe já nenhuma
  dependência deste tipo no projecto (`requirements.txt` confirmado); a
  regra do prompt pede para não introduzir dependência nova havendo
  alternativa simples no código actual — e havia (o próprio parâmetro
  `today`, já aceite mas não usado).
- **Derivar `ref` de `timezone.now()` no teste** (ex.: `ref = timezone.now().date()`):
  funcionaria para este teste em isolamento, mas obrigaria a recalcular
  todas as datas dependentes de `ref` na fixture rica (`release_date`,
  `start_date`/`end_date`, `period_end`, `deadline` do goal) para
  permanecerem coerentes entre si — mais mudança do que o necessário para
  corrigir a causa raiz real, que era especificamente a fixture de cliques
  ignorar o seu próprio parâmetro.

---

## 4. Comandos executados

```bash
cd backend_core
source venv/Scripts/activate

pytest "apps/campaigns/tests/test_intelligence_payload.py::TestRichCampaign::test_all_sections_populated_and_json_safe"
pytest apps/campaigns/tests/test_intelligence_payload.py
pytest apps/campaigns
python manage.py check
pytest -q   # suite completa
```

---

## 5. Resultados dos testes

| Comando | Resultado |
|---|---|
| `pytest ...::test_all_sections_populated_and_json_safe` | ✅ **1 passed** |
| `pytest apps/campaigns/tests/test_intelligence_payload.py` | ✅ **13 passed** (ficheiro completo) |
| `pytest apps/campaigns` | ✅ **78 passed, 3 skipped** (skips são os já esperados — `test_intelligence_real_loop.py`, exigem `RUN_REAL_IE=1` com o Intelligence Engine real a correr; não relacionados) |
| `python manage.py check` | ✅ 0 issues |
| `pytest -q` (suite completa do Backend Core) | ✅ **599 passed, 0 failed, 3 skipped** (11m11s) — antes desta correcção: 598 passed, **1 failed**, 3 skipped |

Nenhum outro ficheiro de `apps/campaigns/tests/` exibe o mesmo padrão de
fragilidade (datas fixas comparadas contra `timezone.now()`) — os restantes
usos de `date(2026, ...)` nesse directório (`test_intelligence_integration.py`,
`test_intelligence_real_loop.py`) são valores de campo estáticos
(`release_date`, `period_end`, `start_date`/`end_date`), nunca comparados
com o relógio real, pelo que não foram alterados.

---

## 6. Riscos ou limitações restantes

- Nenhum. A suite completa do Backend Core está agora **100% verde**
  (599/599 testes executáveis; os 3 `skipped` são condicionais por desenho,
  exigem infraestrutura externa — Intelligence Engine real — não uma
  falha).
- A correcção não introduz nenhuma dependência nova nem altera o contrato
  público de `_add_clicks` (a assinatura da função é idêntica; só o corpo
  passou a honrar o parâmetro que já existia).
- Risco residual, muito baixo: se algum teste futuro voltar a introduzir
  `timezone.now()` numa fixture que deveria estar ancorada a um
  `reference_date` explícito, o mesmo padrão de bug pode reaparecer noutro
  sítio. Não há guarda automática contra isto (ex.: um lint que proíba
  `timezone.now()` em `tests/`) — não foi pedido nem é proporcional
  introduzir um agora.

---

## 7. Conclusão

**A falha pré-existente ficou resolvida**, com causa raiz identificada e
corrigida na fixture de teste (não no produto), sem enfraquecer nenhuma
asserção, sem remover cobertura, sem `skip`/`xfail`, e sem introduzir uma
nova data fixa que volte a expirar. A suite completa do Backend Core passa
agora sem nenhuma falha conhecida.
