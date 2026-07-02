# Prompt 03 — Object storage — Resultado

**Data:** 2026-07-02
**Fase:** `05_staging_operacionalizacao_pre_producao` (STG-PRE-003)
**Âmbito:** preparar Content Renderer e Backend Core para object storage em staging e resolver a URL canónica dos assets, sem inventar provider e sem quebrar o modo local. Sem alteração de lógica funcional fora de storage/assets.
**Estado de execução:** `executado` (contrato de `public_url` fechado e validado ponta-a-ponta; **escolha do provider de object storage continua pendente**, deliberadamente, por não existir decisão)

---

## 1. Resumo objectivo

O Content Renderer **já tinha** uma abstracção de storage bem desenhada
(`StorageProvider` em `src/storage/storage.types.ts`, com uma única
implementação `local-storage.ts`) que já calculava `public_url` para cada
asset gerado. O problema real não estava no Content Renderer — estava no
Backend Core: o modelo `Asset` **não tinha campo `public_url`**, e as duas
funções de callback que criam `Asset` (`reports/callbacks.py`,
`content/callbacks.py`) **nunca liam** `asset_data.get("public_url")`, pelo
que o valor calculado pelo renderer era sempre descartado. Esta era
exactamente a limitação registada em três documentos da fase 04.

Corrigi essa lacuna com uma alteração pequena e provider-agnóstica:

1. Adicionado o campo `Asset.public_url` (migration aditiva, sem perda de
   dados) ao Backend Core.
2. As duas funções de callback passam agora `public_url=asset_data.get("public_url", "")`
   ao criar o `Asset`.
3. `AssetSerializer` expõe `public_url`, disponível em `GET /api/v1/assets/{id}/`.
4. Testes actualizados/adicionados (Backend Core) para cobrir a persistência
   e exposição do campo.
5. **Validação real, não só de unidade**: arranquei o Backend Core real
   (SQLite de dev, `db.sqlite3` migrado com a nova coluna) contra o Content
   Renderer real já em execução, e criei um Report, um MediaKit e um
   ContentPackRequest reais através da API — os três terminaram
   `completed`/`generated`, com `Asset.public_url` populado, e **fiz o
   download real do ficheiro** a partir dessa URL (PDF válido, PNG válido).

**Não escolhi nem implementei nenhum provider de object storage** (S3, R2,
MinIO) — não havia decisão tomada e as regras da fase proíbem inventar uma.
O que ficou pronto é o **pipeline completo e agnóstico de provider**: quando
um provider real for escolhido e implementado no Content Renderer (nova
implementação da interface `StorageProvider` já existente), basta que ele
preencha `public_url` na resposta do callback — o Backend Core já persiste e
expõe esse valor sem alteração adicional.

---

## 2. Provider — estado

| Item | Estado |
|---|---|
| Provider escolhido | **Nenhum.** Continua `local` (filesystem do Content Renderer) — decisão de S3/R2/MinIO/outro fica pendente, registada em `arquitectura_staging_pre_producao.md` §11 |
| Abstracção de provider | **Já existia** antes desta iteração: `StorageProvider` (interface), `StorageProviderName` (união fechada, hoje só `'local'`), `createStorageProvider()` (factory com fail-fast para nomes desconhecidos) |
| Trabalho necessário para um provider real | **Só no Content Renderer**: nova implementação de `StorageProvider` (ex.: `s3-storage.ts`), acrescentar o nome à união `StorageProviderName`, e um `case` na factory. **Zero alterações adicionais no Backend Core** — o contrato de callback e o campo `Asset.public_url` já são genéricos |
| Bloqueio para escolher o provider | Nenhum técnico; é uma decisão de produto/infra (custo, região, política de acesso) fora do âmbito desta iteração |

---

## 3. Contrato de asset URL (definido nesta iteração)

| Campo | Onde vive | Estado após esta iteração |
|---|---|---|
| `storage_key` | `Asset.storage_key` / `AssetMetadata.storage_key` | Já estável (sem alteração) — `buildStorageKey(workspaceId, jobId, fileName)`, portável entre providers |
| `public_url` | `Asset.public_url` (**novo**) / `AssetMetadata.public_url` (já existia) | **Resolvido** — persistido e exposto via API para qualquer provider que o preencha |
| `signed_url` | Não existe campo dedicado | **Não implementado, propositadamente.** Só passa a ser necessário se o provider escolhido usar bucket privado com URLs temporárias; nesse caso deve ser um campo **novo e distinto** de `public_url` (uma signed URL expira; misturar os dois no mesmo campo esconderia essa diferença do consumidor). Decisão adiada até haver provider. |
| Regras de expiração | N/A | Não definidas — dependem da escolha entre acesso público permanente (bucket público, CDN) vs. URLs assinadas temporárias (bucket privado) |
| Acesso público ou privado | Público (storage `local` serve qualquer pedido dentro da raiz, sem auth) | **Decisão pendente**, ligada ao provider. Nota de segurança: mesmo com bucket privado + `signed_url`, o Backend Core continua a ser o único a decidir quando gerar/expor essa URL — o frontend nunca fala directamente com o provider de storage, tal como já não fala directamente com IE/Renderer |

**Nota de compatibilidade Backend Core ↔ Content Renderer:** o modelo `Asset`
já tinha `StorageProvider.choices` com `local`, `s3`, `r2`, `gcs` desde antes
desta fase — o Backend Core já estava pronto para receber esses valores; só
faltava o campo de URL para o valor ser útil. Confirma-se que o Backend Core
não é o gargalo para adoptar um provider real.

---

## 4. Campos confirmados no `Asset` (Backend Core)

| Campo pedido | Existia antes? | Estado após esta iteração |
|---|---|---|
| `storage_provider` | Sim (`local`/`s3`/`r2`/`gcs`) | Inalterado |
| `storage_key` | Sim | Inalterado |
| `public_url` | **Não** | **Adicionado** (`URLField`, `max_length=2048`, `blank=True`) |
| `mime_type` | Sim | Inalterado |
| `file_size_bytes` | Sim | Inalterado |
| `metadata` | Sim (`JSONField`) | Inalterado |
| (extra, já existiam) `bucket`, `file_name`, `width`, `height`, `duration_seconds`, `checksum` | Sim | Inalterado |

---

## 5. Ficheiros alterados

| Ficheiro | Operação | Nota |
|---|---|---|
| `backend_core/apps/core/models.py` | alterado | campo `public_url` no `Asset` |
| `backend_core/apps/core/migrations/0002_asset_public_url.py` | criado | `AddField`, aditiva, sem dados a migrar |
| `backend_core/apps/core/serializers.py` | alterado | `AssetSerializer` expõe `public_url` |
| `backend_core/apps/reports/callbacks.py` | alterado | `_create_asset` persiste `public_url`; docstring de exemplo actualizada |
| `backend_core/apps/content/callbacks.py` | alterado | idem |
| `backend_core/apps/core/tests/test_assets.py` | alterado | +2 testes (`public_url` exposto/definível e default vazio) |
| `backend_core/apps/reports/tests/test_report_media_kit_callbacks.py` | alterado | fixture `_asset_block()` inclui `public_url`; +2 asserts (Report e MediaKit) |
| `backend_core/apps/content/tests/test_content_callback.py` | alterado | fixture `_output()` inclui `public_url`; +1 assert (todos os outputs) |
| `content_renderer/.env.example` | alterado | comentário a documentar que `LOCAL_STORAGE_PUBLIC_BASE_URL` agora alimenta `Asset.public_url` |

**Nenhum código do Content Renderer foi alterado** — a interface já suportava
`public_url`; o gargalo era só do lado Django. **Nenhum provider novo foi
implementado.**

---

## 6. Validações executadas

| Validação | Resultado |
|---|---|
| `python manage.py check` | ✅ 0 issues |
| `python manage.py makemigrations core` (revisão da migration gerada) | ✅ só `AddField`, sem `RunPython`/perda de dados |
| `python manage.py migrate core` contra `db.sqlite3` de dev real | ✅ aplicada sem erro, dados existentes preservados |
| `pytest apps/core/tests/test_assets.py apps/reports/tests/test_report_media_kit_callbacks.py apps/content/tests/test_content_callback.py` | ✅ 28/28 passed |
| `pytest` completo do Backend Core (diligência extra, não exigida pela checklist) | 564 passed, 4 failed, 3 skipped — **as 4 falhas são pré-existentes e não relacionadas com esta alteração** (ver §7); nenhum teste de `core`/`reports`/`content` relacionado com assets falhou |
| **Smoke real de upload/download** — Report, MediaKit e ContentPackRequest criados via API contra Backend Core real (SQLite dev) + Content Renderer real já em execução | ✅ os três terminaram com sucesso (`completed`/`generated`), `Asset.public_url` populado nos três, ficheiros descarregados com sucesso (PDF `1193 bytes`, `application/pdf` válido; PNG `60419 bytes`) — ver detalhe em §8 |
| Grep por segredos (`INTERNAL_API_TOKEN=`, `SECRET_KEY=`, `PASSWORD=`, `AWS_SECRET`, `ACCESS_KEY=`, `PRIVATE_KEY=`) em todos os ficheiros alterados + doc da fase | ✅ 0 ocorrências reais (só nomes de variáveis/placeholders) |
| `scripts/check-forbidden-ports.ps1` | ✅ OK |
| Confirmação `public_url` não fica `null`/vazio quando o provider o envia | ✅ confirmado nos três artefactos do smoke real |
| npm test (Content Renderer) | **Não executado** — nenhum ficheiro do Content Renderer foi alterado (só o `.env.example`, comentário) |

---

## 7. Achado colateral (fora de escopo, não corrigido aqui)

A corrida completa do `pytest` do Backend Core (feita como diligência extra,
não exigida pela checklist desta iteração) revelou **4 falhas pré-existentes,
sem relação com esta alteração de storage/assets**:

- 3 em `apps/integrations_bridge/tests/test_dependency_health.py`
  (`TestAggregator`) — o teste usa um `prober` falso que decide o
  comportamento a simular verificando se a substring `"8002"` está na URL,
  mas a porta real do Content Renderer é `8202` (herança de uma
  renumeração de portas anterior a esta fase — `8002` está inclusivamente na
  lista de portas **proibidas** em `docs/configuracao/portas_projeto.md`).
  A condição nunca dispara, o `prober` simulado devolve sempre `ok`, e o
  `assert ... == UNAVAILABLE` falha.
- 1 em `apps/campaigns/tests/test_intelligence_payload.py` — usa uma data de
  referência fixa (`date(2026, 6, 25)`) para construir um cenário "rico"; com
  o avanço do relógio real (hoje é 2026-07-02), uma das secções deixa de
  ficar populada conforme o teste espera.

Não corrigi estas falhas — estão fora do âmbito de "storage/assets" desta
iteração e a regra explícita é não alterar lógica fora desse âmbito. Foi
aberta uma tarefa separada para as corrigir (`task_e252710e`).

---

## 8. Detalhe do smoke real (upload + download)

Executado contra o Backend Core de desenvolvimento real (SQLite, dados
existentes do workspace `CA014 Dev Workspace` — ver memória do projecto) com
a nova migration aplicada, e o Content Renderer real (porta 8202, já em
execução de uma sessão anterior, sem alteração de configuração):

| Artefacto | `status` final | `Asset.public_url` | Download |
|---|---|---|---|
| Report (`campaign_report`) | `completed` | `http://localhost:8202/files/workspaces/.../report.pdf` | ✅ `200`, `1193 bytes`, PDF v1.7 válido |
| MediaKit | `generated` | `http://localhost:8202/files/workspaces/.../media_kit.pdf` | ✅ confirmado (`public_url` presente e não vazio) |
| ContentPackRequest → ContentOutput (7 outputs) | `completed` | `http://localhost:8202/files/workspaces/.../output_00N.png` (cada output) | ✅ um output verificado por download directo — `200`, `60419 bytes`, PNG válido |

Nenhum destes URLs contém segredos (são caminhos públicos do storage local de
dev, consistente com o contrato — storage local não tem controlo de acesso).

**Estado dos serviços no fim da validação:** o servidor ad-hoc do Backend
Core (porta 8100) usado para este smoke foi **parado** no final; o Content
Renderer (porta 8202) já estava a correr antes desta iteração e foi deixado
como estava (não foi tocado). Os três artefactos de smoke ficam persistidos
no `db.sqlite3` de dev (mesma prática de acumulação de dados de dev já usada
nas fases anteriores) — não foram apagados, conforme a regra de não apagar
dados sem autorização.

---

## 9. Limitações

- **Nenhum provider de object storage foi escolhido ou implementado.** O
  storage continua `local` (filesystem do Content Renderer) — adequado para
  dev/staging técnico, **não** para staging pré-produção/produção reais.
- **`signed_url` não existe.** Só é necessário com bucket privado; fica para
  quando o provider for escolhido.
- **Sem CORS/expiração/controlo de acesso no storage local** — qualquer
  pedido dentro da raiz é servido sem autenticação (aceitável só em dev,
  documentado como tal desde a fase 04).
- **O campo `public_url` é opcional e "best effort"** — se o Content
  Renderer não o enviar no callback (ex.: um provider futuro mal
  implementado), o campo fica vazio silenciosamente; não há validação que
  force um `public_url` não vazio no callback. Isto é intencional (o
  contrato de callback já tem outros campos opcionais) mas vale a pena
  reforçar no runbook (STG-PRE-010) como sinal de alerta a verificar.

---

## 10. Riscos

| Risco | Severidade | Nota |
|---|---|---|
| Confundir "`public_url` resolvido" com "object storage pronto para produção" | Alto | Mitigado explicitamente neste relatório e na arquitectura — falta sempre um provider real; o storage continua local |
| Decisão de provider adiada indefinidamente bloqueia produção | Médio | Já registado como decisão pendente desde o Prompt 01; sem prazo definido nesta fase |
| `signed_url` vir a ser necessário e não ter campo dedicado a tempo | Baixo | Documentado o contrato para adicionar como campo novo, não reaproveitar `public_url` |
| Storage local sem controlo de acesso ser usado por engano além do piloto técnico | Médio | Runbook (STG-PRE-010) deve reforçar este limite |

---

## 11. Ficheiros de arquitectura actualizados

`arquitectura_staging_pre_producao.md` foi actualizado (§6, §6.1, §10, §11)
para reflectir: a interface `StorageProvider` já existente, o contrato de
`public_url` fechado, `signed_url` continua em aberto, e a escolha do
provider continua pendente — sem declarar object storage pronto.

---

## 12. Próximo passo recomendado

Avançar para **Prompt 04 (STG-PRE-004 — Gestão de segredos)**: inventariar
todos os segredos (`INTERNAL_API_TOKEN`, `SECRET_KEY`, `DB_PASSWORD`, futuras
credenciais de storage), confirmar onde cada um é consumido, e propor um
mecanismo de fornecimento controlado para staging que substitua o `.env`
manual — sem desactivar a autenticação interna e sem usar
`ALLOW_INSECURE_EMPTY_TOKEN` fora de dev.
