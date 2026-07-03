# Prompt 01 — Definir topologia local — Resultado

**Data:** 2026-07-02
**Fase:** `06_staging_infraestrutura_real_local` (STG-LOCAL-001)
**Âmbito:** documentar a topologia staging local-first, sem alterar código
runtime nem infraestrutura. Documento puro de arquitectura.
**Estado de execução:** `executado` — backlog e documentação da fase 05
lidos integralmente, arquitectura local-first documentada, relatório
criado.

---

## 1. Nota sobre o caminho da pasta

O prompt referenciava `frontend\docs\01_fundamentos\06_staging_infraestrutura_real\`
mas o repositório já tem a pasta criada como
`frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/`
(contém `01_backlog.md` e `02_prompts_staging_infra.md`, ambos existentes
antes desta execução). O próprio backlog admite esta alternativa como
recomendada (§13: "Se for criada pasta nova"). Os documentos desta execução
foram criados no caminho real e existente, não no caminho literal do
prompt, para não duplicar a fase numa segunda pasta.

## 2. Topologia local definida

Documentada em detalhe em
[`arquitectura_staging_local.md`](../arquitectura_staging_local.md). Resumo:

| Componente | Onde corre | Porta |
|---|---|---|
| Frontend Web | processo local (Vite) | 5200 (dev) / 5201 (preview) |
| Backend Core | processo local (Django) | 8100 |
| Intelligence Engine | processo local (Uvicorn) | 8201 (bind `127.0.0.1`) |
| Content Renderer | processo local (Node) | 8202 |
| PostgreSQL | **container Docker, volume persistente** | 5432 |
| MinIO S3 API | **container Docker, volume persistente** | 9000 |
| MinIO Console | **container Docker** (mesmo container/volume que o S3 API) | 9001 |

Decisões fechadas por este documento (secção 14 da arquitectura):
containers obrigatórios limitados a PostgreSQL e MinIO; serviços
aplicacionais como processos locais; portas aplicacionais inalteradas;
volumes nomeados e persistentes (não `tmpfs`); rede local via portas
publicadas no host; fronteira Frontend → Backend Core preservada sem
excepção; cloud fora de escopo sem excepção.

A arquitectura também documenta: ordem de arranque recomendada (containers
→ Backend Core → Intelligence Engine → Content Renderer → Frontend),
matriz de healthchecks (Docker + HTTP), árvore de dependências entre
componentes, rede local, fronteiras de segurança e a razão técnica para
PostgreSQL/MinIO serem containers enquanto os quatro serviços
aplicacionais permanecem processos locais.

## 3. Ficheiros criados/alterados

| Ficheiro | Operação |
|---|---|
| `frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/arquitectura_staging_local.md` | **criado** |
| `frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/resultados_execucao/prompt_01_topologia_local_resultado.md` | **criado** (este relatório) |

Nenhum ficheiro de código, configuração activa ou script foi alterado,
conforme a regra explícita do prompt ("Não alterar código runtime neste
prompt, salvo documentação").

## 4. Decisões tomadas

- Pasta de trabalho: `06_staging_infraestrutura_real_local` (já existente
  no repositório), não `06_staging_infraestrutura_real`.
- Containers obrigatórios: PostgreSQL e MinIO, com volumes persistentes
  nomeados (não `tmpfs`, diferente do padrão descartável usado em
  `content_renderer/docker-compose.e2e.yml`, que serve um propósito
  distinto — E2E efémero).
- Portas dos containers: 5432 (PostgreSQL), 9000 (MinIO S3 API), 9001
  (MinIO Console) — defaults oficiais das duas tecnologias, sem colisão com
  a lista de portas proibidas nem com o mapa de portas aplicacionais
  existente.
- Serviços aplicacionais permanecem processos locais nesta fase; a
  containerização é registada como opcional/futura, não como trabalho desta
  fase.
- O nível "staging pré-produção" definido pela fase 05 (que presumia DB e
  storage não-locais) é substituído, para efeitos desta fase, pelo nível
  "staging local formal" — inteiramente local, sem qualquer presunção de
  host remoto ou cloud.

## 5. Decisões explicitamente pendentes (não fechadas por este prompt)

Listadas em detalhe na secção 15 da arquitectura; resumo:

- Ficheiro concreto do Docker Compose de infraestrutura e o nome exacto dos
  volumes/variáveis de override de porta — STG-LOCAL-002.
- Nome do bucket MinIO de staging e forma de o criar — STG-LOCAL-002.
- Configuração real do Backend Core contra o PostgreSQL do container
  (migrations, seeds, smoke) — STG-LOCAL-003.
- Implementação do provider MinIO/S3-compatible no Content Renderer
  (`content_renderer/src/storage/storage.types.ts` só tem `local`
  implementado hoje) — STG-LOCAL-004.
- Mecanismo concreto de secrets locais (nome do ficheiro, forma de
  carregamento pelos 4 serviços + E2E) — STG-LOCAL-005.
- Scripts de arranque/paragem/health/reset — STG-LOCAL-006.
- Distinção entre endpoint interno e público do MinIO para `public_url`
  (risco LOCAL-R05) — STG-LOCAL-004.

## 6. Validações executadas

| Validação | Resultado |
|---|---|
| Leitura integral do backlog da fase 06 (`01_backlog.md`, 15 secções) | ✅ Confirma premissa local-first em §1, §5, §6, §7 |
| Leitura integral do pipeline de prompts (`02_prompts_staging_infra.md`) | ✅ Confirma escopo do Prompt 01 e dos 11 prompts seguintes |
| Leitura de `estado_staging_pre_producao.md` (fase 05) | ✅ Confirma as 3 pendências herdadas (DB, storage, secrets) que esta fase resolve em modo local |
| Leitura de `arquitectura_staging_pre_producao.md` (fase 05) | ✅ Base reutilizada para portas, fluxos, contrato `Asset.public_url`, guardas de arranque de secrets |
| Leitura de `resultados_execucao/prompt_11_fecho_pre_producao_resultado.md` (fase 05) | ✅ Confirma classificação `pronto_parcialmente_com_pendencias` e próximos passos |
| Leitura de `docs/configuracao/portas_projeto.md` | ✅ Confirma portas canónicas e lista de portas proibidas |
| Leitura de `backend_core/config/settings.py` (bloco `DATABASES`) | ✅ Confirma que `DB_ENGINE=postgres` com `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD` já é suportado, sem alteração de código necessária |
| Leitura de `backend_core/.env.example`, `content_renderer/.env.example` | ✅ Confirma nomes de variáveis existentes (`DB_*`, `INTERNAL_API_TOKEN`, `STORAGE_PROVIDER`) reutilizados na arquitectura, sem inventar nomes novos incompatíveis |
| Leitura de `content_renderer/src/storage/storage.types.ts` | ✅ Confirma que só `local` está implementado hoje — a interface `StorageProvider` está pronta para uma implementação MinIO/S3, mas essa implementação é STG-LOCAL-004, não este prompt |
| Leitura de `content_renderer/docker-compose.e2e.yml` | ✅ Usado como referência de sintaxe Compose já existente no repositório; a diferença de persistência (`tmpfs` vs. volume nomeado) está documentada explicitamente na arquitectura (§7) para não ser confundida com o alvo desta fase |
| `scripts/check-forbidden-ports.ps1` | ✅ `OK - nenhuma porta proibida encontrada em ficheiros activos` |
| Grep de `password\|secret\|token\|api_key\|private_key` (case-insensitive) em `arquitectura_staging_local.md` | ✅ Todas as ocorrências são nomes de variável/cabeçalho (`DB_PASSWORD`, `X-Internal-Token`, `STORAGE_ACCESS_KEY`, `ALLOW_INSECURE_EMPTY_TOKEN`, "secret store", "secrets locais") — nenhum valor real |
| Confirmação manual: nenhuma porta proibida (8000, 8001, 8002, 8003, 1420, 9011, 5173, 5174, 8080–8085) aparece na topologia (5200, 5201, 8100, 8201, 8202, 5432, 9000, 9001) | ✅ Confirmado por inspecção do mapa de portas |
| Confirmação manual: cloud (AWS, R2, GCS, Azure Blob, Kubernetes, secret store cloud) não é referenciado em nenhuma secção do documento, excepto para o listar explicitamente como fora de escopo | ✅ Confirmado por leitura integral do documento criado |
| Confirmação manual: regra "Frontend → Backend Core apenas" está explícita e repetida (secções 3, 4.1, 12) | ✅ Confirmado |

## 7. Riscos

Os 10 riscos do backlog (LOCAL-R01 a LOCAL-R10) foram todos incorporados na
arquitectura (secção 13), com a mitigação concreta prevista para esta
topologia e o prompt onde cada mitigação será implementada. Nenhum risco
novo foi identificado além dos já listados no backlog; o trabalho deste
prompt foi mapear cada risco a uma mitigação de topologia concreta, não
descobrir riscos novos.

O risco mais relevante para quem ler este documento sem o contexto completo
é **LOCAL-R09** (confundir "staging local formal" com "staging
pré-produção externo" ou produção) — mitigado ao reescrever, na secção 2 da
arquitectura, o nível intermédio de ambiente para deixar explícito que esta
fase corre inteiramente na máquina local, sem qualquer host remoto.

## 8. Próximo passo recomendado

Avançar para **STG-LOCAL-002** (Prompt 02 do pipeline): criar o Docker
Compose local mínimo (`docker-compose.staging.local.yml` ou equivalente)
com os serviços `postgres` e `minio`, volumes persistentes nomeados,
healthchecks, criação do bucket de staging e ficheiro de exemplo de env com
placeholders — sem secrets reais, sem containerizar os serviços
aplicacionais, conforme já decidido na secção 14 da arquitectura criada
neste prompt.
