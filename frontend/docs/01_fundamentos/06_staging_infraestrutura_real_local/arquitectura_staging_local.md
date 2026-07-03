# Arquitectura — Staging Infraestrutura Real Local

> Fase: `06_staging_infraestrutura_real_local` (STG-LOCAL-012, fecho)
> Estado: **implementada e validada** — esta arquitectura deixou de ser só
> "alvo" (Prompt 01) e passa a descrever a stack **de facto implementada e
> validada** por esta fase; ver `estado_staging_local.md` para a decisão de
> prontidão consolidada (`pronto_para_staging_local_formal`).
> Data original: 2026-07-02 · Fecho: 2026-07-03
> Fonte: [`01_backlog.md`](01_backlog.md),
> `frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/estado_staging_pre_producao.md`,
> `frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/arquitectura_staging_pre_producao.md`,
> `frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/runbook_staging_pre_producao.md`,
> `frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/resultados_execucao/prompt_11_fecho_pre_producao_resultado.md`,
> [`docs/configuracao/portas_projeto.md`](../../../../docs/configuracao/portas_projeto.md),
> `backend_core/config/settings.py`, `backend_core/.env.example`,
> `content_renderer/.env.example`, `content_renderer/src/storage/storage.types.ts`,
> `content_renderer/docker-compose.e2e.yml`.

Este documento descreve a arquitectura **alvo local-first** desta fase: uma
stack staging que corre inteiramente na máquina local, com PostgreSQL e
MinIO como containers persistentes, substituindo SQLite e o storage
filesystem que a fase 05 deixou como pendências. Não descreve produção, não
descreve cloud e não introduz nova funcionalidade de produto.

---

## 1. Premissa obrigatória desta fase

```text
Toda a infraestrutura desta fase corre na máquina local.

- PostgreSQL em container local persistente;
- MinIO em container local persistente;
- Backend Core, Intelligence Engine, Content Renderer e Frontend em
  processos locais, salvo decisão técnica muito clara e justificada;
- sem AWS, R2, GCS, Azure Blob, Kubernetes ou qualquer serviço cloud;
- sem secret store cloud;
- sem CI/CD remoto obrigatório.
```

Esta premissa está reflectida no backlog da fase (`01_backlog.md` §1, §5, §6)
e é vinculativa para todos os documentos e prompts desta fase. Qualquer
desenho que introduza cloud, staging externo ou CI/CD remoto obrigatório é,
por definição, rejeitado por este documento.

**Nota sobre o nome da pasta:** o backlog admite duas alternativas —
`06_staging_infraestrutura_real_local` (recomendada) ou manter
`06_staging_infraestrutura_real` com o conteúdo explicitamente local-first.
A pasta já existe no repositório como `06_staging_infraestrutura_real_local`
(`01_backlog.md` e `02_prompts_staging_infra.md` já lá residem); este
documento e o relatório de execução seguem esse mesmo caminho.

---

## 2. Os quatro níveis de ambiente (actualizado face à fase 05)

A fase 05 definiu "staging pré-produção" como um nível que presumia DB e
storage **não-locais** (§1 de `arquitectura_staging_pre_producao.md`). Esta
fase substitui essa presunção: o nível intermédio entre "staging técnico" e
"produção" passa a ser alcançável **inteiramente em infraestrutura local**,
usando containers para as duas dependências que exigem persistência real
(PostgreSQL, MinIO).

| Nível | Descrição | DB | Storage | Secrets | Estado |
|---|---|---|---|---|---|
| **Dev local** | Developer único, tudo em `localhost`, arranque manual | SQLite | filesystem local do Content Renderer | placeholders partilhados manualmente | **existente** (fases 01–04) |
| **Staging técnico** | Quatro serviços a correr de forma reproduzível, IE e Renderer reais (sem dry-run) | SQLite ou PostgreSQL descartável | filesystem local | token partilhado, gerido manualmente | **validado** (fase 04) |
| **Staging local formal** | Ambiente reproduzível na máquina local, com PostgreSQL e MinIO em containers persistentes, secrets locais controlados, quality gate e E2E local | **PostgreSQL container local persistente** | **MinIO container local persistente** | ficheiro local ignorado pelo git, injectado por script/env, partilhado pelos serviços | **alcançado — validado pelos STG-LOCAL-001 a 012** (`estado_staging_local.md`: `pronto_para_staging_local_formal`) |
| **Produção** | SLA, alta disponibilidade, alertas, rotação automática de secrets, aprovação operacional, infraestrutura gerida/cloud | PostgreSQL gerido | object storage de produção | secret manager de produção | **fora de escopo** |

Diferença deliberada face à fase 05: onde `arquitectura_staging_pre_producao.md`
apontava para um "PostgreSQL dedicado" e um "object storage (provider a
decidir)" sem comprometer a topologia, esta fase fecha essa decisão como
**containers locais**, explicitamente excluindo qualquer provider cloud.

---

## 3. Componentes e responsabilidades

| Componente | Stack | Papel | Onde corre nesta fase |
|---|---|---|---|
| **Frontend Web** | Vite + React | UI; fala **exclusivamente** com o Backend Core | Processo local (`vite dev` / `vite preview`) |
| **Backend Core** | Django + DRF | Orquestrador; única fronteira que fala com IE/Renderer; dono do domínio (auth, RBAC, campanhas, CampaignActions, artefactos, jobs) | Processo local (`manage.py runserver`) |
| **Intelligence Engine** | FastAPI (stateless) | Diagnóstico síncrono de campanha; sem persistência, sem chamar outros serviços | Processo local (`uvicorn`) |
| **Content Renderer** | Node/Express | Geração assíncrona de artefactos (report/media kit/content pack) via jobs + callback | Processo local (`node`/`npm run dev`) |
| **PostgreSQL** | `postgres:16-alpine` (ou equivalente) | Persistência exclusiva do Backend Core; IE e Renderer não têm DB própria | **Container Docker local, volume persistente** |
| **MinIO** | `minio/minio` (ou equivalente) | Object storage S3-compatible para os outputs do Content Renderer (PDF/PNG/HTML) | **Container Docker local, volume persistente** |
| **Jobs / callbacks** | `ExternalJobReference` (Backend Core) ↔ `/jobs/` + callback (Content Renderer) | Ponte assíncrona entre a criação do artefacto e o resultado do render | Sem alteração de contrato |

**Regra inviolável, sem excepção nesta fase:** o Frontend Web só fala com o
Backend Core (`:8100/api/v1`). Nunca chama Intelligence Engine nem Content
Renderer directamente, e nunca envia `X-Internal-Token` — esse cabeçalho é
exclusivo de comunicação serviço-a-serviço (Backend Core → IE / Renderer, e
Content Renderer → Backend Core no callback). Esta regra é herdada,
inalterada, de `docs/configuracao/portas_projeto.md` §"Regras
arquitecturais (invioláveis)".

---

## 4. Topologia local-first

```text
Máquina local
│
├── Processos aplicacionais (locais, sem container)
│   ├── Frontend Web            → http://localhost:5200
│   ├── Backend Core            → http://localhost:8100/api/v1
│   ├── Intelligence Engine     → http://127.0.0.1:8201   (interno, nunca exposto ao frontend)
│   └── Content Renderer        → http://localhost:8202   (interno, nunca exposto ao frontend)
│
└── Containers Docker (infraestrutura obrigatória, persistente)
    ├── PostgreSQL               → localhost:5432
    │   └── volume persistente: chartrex_postgres_data
    └── MinIO
        ├── S3 API                → http://localhost:9000
        ├── Console                → http://localhost:9001
        └── volume persistente: chartrex_minio_data
```

### 4.1 Fluxos (inalterados de contrato face à fase 05)

```text
Frontend (5200)      --HTTP, Authorization: Bearer <jwt>, X-Workspace-ID-->  Backend Core (8100)
Backend Core (8100)  --POST /intelligence/campaign, X-Internal-Token-->      Intelligence Engine (127.0.0.1:8201)
Backend Core (8100)  --POST /jobs/, X-Internal-Token-->                      Content Renderer (8202)
Content Renderer     --grava output-->                                       MinIO (localhost:9000)
Content Renderer     --POST /api/v1/internal/jobs/callback/, X-Internal-Token-->  Backend Core (8100)
Backend Core (8100)  --SELECT/INSERT/UPDATE-->                               PostgreSQL (localhost:5432)
```

O único fluxo novo nesta fase é `Content Renderer → MinIO`; todos os outros
já existiam e não mudam de contrato (payloads, headers, endpoints).

---

## 5. Portas canónicas

Fonte de verdade herdada: [`docs/configuracao/portas_projeto.md`](../../../../docs/configuracao/portas_projeto.md).
As portas dos serviços aplicacionais **não mudam** nesta fase. As duas
portas novas (PostgreSQL, MinIO) seguem os defaults oficiais dessas
tecnologias e não colidem com o mapa existente.

| Serviço | Porta | Tipo | Exposição |
|---|---|---|---|
| Frontend Web (Vite dev) | 5200 | processo local | única entrada do utilizador |
| Frontend Preview (Vite build) | 5201 | processo local | idem, build de produção local |
| Backend Core | 8100 | processo local | exposta ao frontend (`/api/v1`) |
| Intelligence Engine | 8201 | processo local | **interna** — nunca exposta ao frontend |
| Content Renderer | 8202 | processo local | **interna** — só o endpoint de callback é chamado pelo Renderer para o Backend Core |
| PostgreSQL | 5432 | **container** | **interna** — só o Backend Core liga a `127.0.0.1:5432` |
| MinIO S3 API | 9000 | **container** | **interna** — só o Content Renderer liga directamente; o Backend Core nunca liga ao MinIO |
| MinIO Console | 9001 | **container** | uso administrativo/manual do operador local, não é chamada por nenhum serviço aplicacional |

**Portas proibidas** (validadas por `scripts/check-forbidden-ports.ps1`):
8000, 8001, 8002, 8003, 1420, 9011, 5173, 5174, 8080–8085. Nenhuma porta
usada nesta topologia (5200, 5201, 8100, 8201, 8202, 5432, 9000, 9001)
coincide com a lista proibida — confirmado por inspecção manual e pela
validação descrita em `resultados_execucao/prompt_01_topologia_local_resultado.md` §6.

**Override de portas:** os riscos LOCAL-R02/LOCAL-R03 do backlog (porta
5432 ou 9000/9001 já ocupada por outra instância na máquina do operador)
devem ser mitigados com variáveis de override (`POSTGRES_PORT`,
`MINIO_API_PORT`, `MINIO_CONSOLE_PORT`) quando o Docker Compose for criado
(STG-LOCAL-002). Este documento não fixa portas alternativas — só regista a
necessidade do override.

---

## 6. Containers obrigatórios: por que PostgreSQL e MinIO, e não os restantes

### 6.1 Por que PostgreSQL e MinIO devem ser containers locais persistentes

1. **Persistência multi-processo real.** SQLite não partilha linhas
   commitadas de forma fiável entre processos separados — o callback do
   Content Renderer corre num processo distinto do Backend Core, e a fase 05
   já identificou este ponto como motivo técnico para migrar
   (`arquitectura_staging_pre_producao.md` §5). Um container PostgreSQL com
   volume persistente resolve isto sem exigir uma instância gerida externa.
2. **Storage real, não filesystem do processo do Renderer.** O backlog desta
   fase proíbe explicitamente declarar staging local formal enquanto o
   filesystem local do Content Renderer continuar a ser o destino final dos
   artefactos (§10, critérios de rejeição). MinIO fornece uma API
   S3-compatible local, o que valida o contrato `StorageProvider` (upload,
   `public_url`, download) sem depender de um provider cloud.
3. **Reprodutibilidade sem depender de instalação manual na máquina do
   operador.** Um container com imagem fixa (`postgres:16-alpine`,
   `minio/minio`) e volume nomeado é arrancável/destruível de forma
   idêntica em qualquer máquina com Docker, ao contrário de uma instalação
   nativa de PostgreSQL/MinIO no sistema operativo do operador.
4. **Isolamento de dados de staging face a uma eventual instalação local de
   PostgreSQL do operador** (risco LOCAL-R02 do backlog) — o container usa
   um volume e, potencialmente, uma porta dedicados, sem misturar dados com
   outras bases de dados que possam já existir na máquina.

### 6.2 Por que os serviços aplicacionais não devem ser containerizados já

1. **Ciclo de iteração.** Frontend, Backend Core, Intelligence Engine e
   Content Renderer estão em desenvolvimento activo (hot reload, `vite dev`,
   `runserver`, `uvicorn --reload`, `npm run dev`). Containerizá-los agora
   introduziria fricção (rebuild de imagem a cada alteração) sem benefício
   correspondente nesta fase — o backlog é explícito: "fica fora do escopo
   containerizar todos os serviços aplicacionais, salvo se for claramente
   necessário e de baixo risco" (§5).
2. **Risco de containerizar cedo demais** já está identificado como
   LOCAL-R10 no backlog (§11), com mitigação explícita: "limitar containers
   obrigatórios a PostgreSQL e MinIO".
3. **Redução de variáveis por incremento.** Esta fase já introduz duas
   dependências novas (PostgreSQL, MinIO) e um mecanismo de secrets locais.
   Containerizar os quatro serviços aplicacionais ao mesmo tempo multiplica
   o número de coisas que podem falhar simultaneamente, dificultando
   diagnosticar qual mudança introduziu um problema.
4. **Nada no contrato actual exige containerização das aplicações** — os
   quatro serviços já leem toda a configuração por variável de ambiente
   (`python-decouple` no Backend Core, `pydantic-settings`/equivalente no IE,
   variáveis `process.env` no Content Renderer, `import.meta.env` no
   Frontend), pelo que apontar para PostgreSQL/MinIO em container é apenas
   uma questão de valores de configuração (`DB_HOST=127.0.0.1`,
   `STORAGE_ENDPOINT=http://127.0.0.1:9000`), não de arquitectura.

Containerizar os serviços aplicacionais fica registado como **opcional/futuro**
(backlog §6.2), a considerar apenas depois de a stack local com PostgreSQL e
MinIO estar estável e validada (STG-LOCAL-003 a 012).

---

## 7. Volumes persistentes

| Volume | Serviço | Conteúdo | Efeito de `docker compose down` (sem `-v`) | Efeito de reset destrutivo |
|---|---|---|---|---|
| `chartrex_postgres_data` (nome indicativo) | PostgreSQL | Ficheiros de dados do cluster PostgreSQL (`/var/lib/postgresql/data`) | Preservado — dados sobrevivem a parar/arrancar o container | Apagado apenas por comando de reset explicitamente destrutivo (STG-LOCAL-002/006) |
| `chartrex_minio_data` (nome indicativo) | MinIO | Objectos do(s) bucket(s) de staging (`/data`) | Preservado | Apagado apenas por comando de reset explicitamente destrutivo |

Diferença deliberada face ao `content_renderer/docker-compose.e2e.yml`
existente: aquele compose usa `tmpfs` porque o E2E é **descartável por
desenho** (dados de teste, harness efémero). Esta fase exige o oposto —
volumes nomeados e persistentes — porque o objectivo é validar que o
staging local sobrevive a reinícios, não recriar dados a cada execução
(critério de aceitação do backlog: "dados persistem após restart dos
containers").

O acumular de dados nestes volumes ao longo do tempo é um risco conhecido
(LOCAL-R08, §9 abaixo) e é mitigado por um comando de reset destrutivo
claramente separado dos comandos normais de arranque/paragem — a definir em
STG-LOCAL-002/006, não neste documento.

---

## 8. Ordem de arranque recomendada

```text
1. Containers de infraestrutura
   1.1 PostgreSQL (container) — aguardar healthcheck "healthy"
   1.2 MinIO (container) — aguardar healthcheck "healthy"
   1.3 Criação/confirmação do bucket de staging no MinIO

2. Backend Core (processo local)
   2.1 Confirmar DB_ENGINE=postgres e ligação a 127.0.0.1:5432
   2.2 python manage.py migrate
   2.3 python manage.py runserver 127.0.0.1:8100
   2.4 Confirmar /api/v1/system/health/ready/ → 200

3. Intelligence Engine (processo local)
   3.1 uvicorn ... --port 8201
   3.2 Confirmar GET http://127.0.0.1:8201/health → 200

4. Content Renderer (processo local)
   4.1 Confirmar STORAGE_ENDPOINT aponta para o MinIO local (localhost:9000)
   4.2 node/npm run dev — porta 8202
   4.3 Confirmar GET http://localhost:8202/health → 200

5. Frontend Web (processo local)
   5.1 vite dev — porta 5200
   5.2 Confirmar que VITE_BACKEND_API_BASE_URL aponta só para :8100/api/v1
```

Justificação da ordem: PostgreSQL e MinIO são dependências de arranque do
Backend Core e do Content Renderer respectivamente — arrancar os processos
aplicacionais antes dos containers estarem `healthy` produz falhas de
ligação na primeira migration/upload, não um sinal de erro claro. A
Intelligence Engine não depende de PostgreSQL nem de MinIO (é stateless),
por isso pode arrancar em qualquer momento antes do Backend Core precisar
de a chamar; mantém-se no passo 3 por ser o próximo consumidor síncrono do
Backend Core. O Frontend arranca por último por não ter nenhuma dependência
de arranque própria além de o Backend Core responder.

---

## 9. Healthchecks

| Alvo | Mecanismo | Público/interno | Cobre |
|---|---|---|---|
| PostgreSQL (container) | `pg_isready` (healthcheck Docker) | Interno ao Docker | Aceita ligações |
| MinIO (container) | `mc ready local` ou endpoint `/minio/health/live` (healthcheck Docker) | Interno ao Docker | Processo do MinIO responde |
| Backend Core | `GET /api/v1/system/health/live/` | Público | Processo vivo, sem dependências |
| Backend Core | `GET /api/v1/system/health/ready/` | Público | Só a base de dados (`SELECT 1` contra PostgreSQL) |
| Backend Core | `GET /api/v1/system/health/dependencies/` | Staff-only (`IsAdminUser`) | Agregado: IE + Content Renderer (via `/health` público) + DB |
| Intelligence Engine | `GET http://127.0.0.1:8201/health` | Público | Liveness (stateless) |
| Content Renderer | `GET http://localhost:8202/health` | Público | Liveness (não reporta MinIO nesta fase, salvo decisão futura de o incluir) |

Os healthchecks dos containers Docker (`pg_isready`, `mc ready`/`/minio/health/live`)
e os healthchecks HTTP dos serviços aplicacionais são mecanismos
independentes — o script de health local (STG-LOCAL-006) deve verificar
ambos, na ordem da secção 8, antes de declarar a stack "pronta".

---

## 10. Dependências entre componentes

```text
Frontend            depende de: Backend Core (via HTTP)
Backend Core         depende de: PostgreSQL (container), Intelligence Engine (opcional/degradável), Content Renderer (opcional/degradável)
Intelligence Engine   depende de: nada (stateless)
Content Renderer      depende de: MinIO (container), Backend Core (para o callback)
PostgreSQL             depende de: nada (raiz da árvore de arranque)
MinIO                  depende de: nada (raiz da árvore de arranque)
```

"Opcional/degradável" reflecte a decisão já validada na fase 05
(`arquitectura_staging_pre_producao.md` §9.1): o `readiness` do Backend Core
verifica **só** a base de dados — IE e Content Renderer em baixo não tornam
o Backend Core "not ready", porque a maior parte da API continua a
funcionar sem eles. Esta fase não altera essa decisão.

---

## 11. Rede local

```text
Processos aplicacionais  → ligam a 127.0.0.1:<porta> / localhost:<porta>
Containers Docker         → publicam portas no host via port mapping
                             (ex.: 5432:5432, 9000:9000, 9001:9001)
```

Não é necessária uma rede Docker dedicada partilhada com os serviços
aplicacionais, porque estes correm fora do Docker e acedem aos containers
pelas portas publicadas no `localhost` do host, exactamente como acedem
hoje a qualquer outro processo local. Os containers PostgreSQL e MinIO
podem partilhar uma rede Docker interna entre si (para o serviço auxiliar
`mc` de criação de bucket, por exemplo), mas essa rede é interna ao Compose
e não afecta a forma como os processos locais os alcançam.

Não há, nesta fase, qualquer necessidade de DNS interno, service mesh, ou
rede overlay — decisões desse tipo pertencem a um eventual cenário
multi-host, explicitamente fora de escopo (backlog §5).

---

## 12. Fronteiras de segurança

Herdadas, inalteradas, de `docs/configuracao/portas_projeto.md` e de
`arquitectura_staging_pre_producao.md` §2/§7, e reforçadas nesta fase com as
duas dependências novas:

1. **Frontend → Backend Core apenas.** O frontend nunca chama Intelligence
   Engine (`:8201`) nem Content Renderer (`:8202`) directamente, e nunca
   envia `X-Internal-Token`. Esta regra não muda com a introdução de
   PostgreSQL/MinIO — o frontend continua a não ter, nem precisar de ter,
   conhecimento de que essas dependências existem.
2. **`X-Internal-Token` é exclusivo de comunicação serviço-a-serviço.**
   Backend Core → IE, Backend Core → Content Renderer, Content Renderer →
   Backend Core (callback). Nunca no browser.
3. **O Backend Core nunca liga directamente ao MinIO.** Só o Content
   Renderer fala com o MinIO (upload) e devolve `public_url`/`storage_key`
   ao Backend Core via callback — o mesmo contrato `Asset.public_url` já
   fechado na fase 05 (STG-PRE-003), agnóstico de provider.
4. **Credenciais do PostgreSQL e do MinIO nunca em ficheiros versionados.**
   `DB_PASSWORD`, `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`,
   `STORAGE_ACCESS_KEY`/`STORAGE_SECRET_KEY` vivem exclusivamente num
   ficheiro local ignorado pelo git (mecanismo concreto a formalizar em
   STG-LOCAL-005) — este documento não define esse ficheiro nem os seus
   valores, só a exigência de que exista e esteja fora do controlo de
   versão.
5. **`ALLOW_INSECURE_EMPTY_TOKEN` continua proibido em staging local.**
   Herdado de `arquitectura_staging_pre_producao.md` §7 — é uma flag
   exclusiva de dev, nunca de staging local formal.
6. **Health detalhado continua staff-only.** `GET
   /api/v1/system/health/dependencies/` exige `IsAdminUser`; liveness/readiness
   continuam públicos e mínimos, sem expor detalhes de infraestrutura.
7. **Consola do MinIO (porta 9001) é uso administrativo/manual do operador
   local**, não uma dependência de nenhum fluxo aplicacional — não deve ser
   exposta além da máquina local nem referenciada em código de produto.

---

## 13. Riscos locais (STG-LOCAL-001)

| ID | Risco | Impacto | Mitigação nesta topologia |
|---|---|---|---|
| LOCAL-R01 | Docker indisponível ou instável na máquina do operador | Alto | Documentar Docker como pré-requisito explícito no runbook local (STG-LOCAL-011); se Docker não estiver disponível, declarar bloqueio sem fingir validação — nunca substituir por SQLite/filesystem para "passar" a fase |
| LOCAL-R02 | Porta 5432 já ocupada por outra instância PostgreSQL na máquina | Médio | Prever override documentado (`POSTGRES_PORT`) no Docker Compose (STG-LOCAL-002); esta topologia não fixa 5432 como único valor possível, só como default |
| LOCAL-R03 | Porta 9000/9001 já ocupada | Médio | Prever override documentado (`MINIO_API_PORT`, `MINIO_CONSOLE_PORT`) no Docker Compose (STG-LOCAL-002) |
| LOCAL-R04 | Secrets locais versionados por acidente (ex.: `.env.staging.local` commitado) | Crítico | `.gitignore` já cobre `.env`/`.env.*` globalmente (confirmado nesta iteração); qualquer ficheiro novo de secrets locais desta fase deve seguir o mesmo padrão de nome e ser validado por grep antes de cada commit relevante (STG-LOCAL-005) |
| LOCAL-R05 | `public_url` do MinIO não acessível pelo Backend Core/Frontend (endpoint interno vs. externo divergente) | Alto | **Resolvido no STG-LOCAL-004** (`resultados_execucao/prompt_04_minio_storage_resultado.md`): endpoint único (`http://127.0.0.1:9000`) para upload (Content Renderer) e download (`public_url`) nesta máquina única; o bucket `chartrex-staging` recebeu uma política `mc anonymous set download` explícita e documentada (leitura anónima, sem listagem, sem escrita) para que `public_url` seja descarregável sem credenciais — paridade deliberada com o provider `local`, que já era servido sem autenticação. Download real confirmado (`HTTP 200`, PDF/PNG válidos) |
| LOCAL-R06 | Content Renderer quebra o modo local antigo ao introduzir MinIO | Médio | **Validado no STG-LOCAL-004**: suite completa do Content Renderer (151/151, incluindo os testes originais do provider `local`) continua verde; `STORAGE_PROVIDER=local` continua o default e não exige nenhuma das variáveis novas de S3/MinIO |
| LOCAL-R07 | E2E instável por ordem de arranque incorrecta (containers não `healthy` antes dos processos aplicacionais) | Médio | Ordem de arranque e healthchecks definidos nas secções 8 e 9 deste documento; script de health (STG-LOCAL-006) deve bloquear o E2E até todos os healthchecks passarem |
| LOCAL-R08 | Dados acumulam indefinidamente nos volumes locais (`chartrex_postgres_data`, `chartrex_minio_data`) | Baixo | Comando de reset destrutivo, claramente separado de start/stop, a definir em STG-LOCAL-002/006 — não é parte deste documento de topologia |
| LOCAL-R09 | Confundir "staging local formal" com "staging pré-produção externo" ou produção | Alto | Este documento e o nível 3 da tabela da secção 2 são explícitos: staging local formal corre inteiramente na máquina local, com containers Docker, não com hosts remotos nem cloud |
| LOCAL-R10 | Containerizar os serviços aplicacionais cedo demais, antes de a base local estar estável | Médio | Secção 6.2 acima — containers obrigatórios limitados a PostgreSQL e MinIO nesta fase |

---

## 14. Decisões fechadas por este documento

```text
Containers obrigatórios: PostgreSQL, MinIO.
Serviços aplicacionais: processos locais (Frontend, Backend Core, IE, Content Renderer).
Portas aplicacionais: inalteradas face a docs/configuracao/portas_projeto.md.
Porta PostgreSQL: 5432 (default; override documentado a criar em STG-LOCAL-002).
Portas MinIO: 9000 (S3 API) e 9001 (Console) (default; override documentado a criar em STG-LOCAL-002).
Volumes: nomeados e persistentes para PostgreSQL e MinIO (não tmpfs, não descartáveis).
Rede: containers publicam portas no host; processos locais ligam via 127.0.0.1/localhost.
Fronteira Frontend → Backend Core: preservada sem excepção.
Cloud: fora de escopo nesta fase, sem qualquer excepção.
```

---

## 15. Decisões explicitamente pendentes (não fechadas por este documento)

Registadas para que não sejam decididas implicitamente num ficheiro local
sem documentação — cada uma pertence a um prompt posterior desta mesma fase:

| Decisão | Onde se fecha |
|---|---|
| Decisão | Estado |
|---|---|
| Ficheiro/mecanismo concreto do Docker Compose de infraestrutura | **Fechado — STG-LOCAL-002** (`docker-compose.staging.local.yml`) |
| Nome exacto do bucket MinIO de staging e forma de o criar | **Fechado — STG-LOCAL-002**: bucket `chartrex-staging`, criado pelo serviço auxiliar `minio-bucket-init` |
| Configuração real do Backend Core contra o PostgreSQL do container (migrations, seeds, smoke) | **Fechado — STG-LOCAL-003** (`resultados_execucao/prompt_03_postgresql_local_resultado.md`) |
| Implementação do provider MinIO/S3-compatible no Content Renderer | **Fechado — STG-LOCAL-004** (`resultados_execucao/prompt_04_minio_storage_resultado.md`) — `STORAGE_PROVIDER=s3`, reporta `storage_provider: 's3'` a Django (reaproveita `Asset.StorageProvider.S3`, sem novo valor de enum) |
| Mecanismo concreto de secrets locais (nome do ficheiro, forma de carregamento pelos 4 serviços + E2E) | **Fechado — STG-LOCAL-005** (`resultados_execucao/prompt_05_secrets_locais_resultado.md`) — `*.env.staging.local` por sítio, rotação de `INTERNAL_API_TOKEN` testada de facto |
| Scripts de arranque/paragem/health/reset | **Fechado — STG-LOCAL-006** (`resultados_execucao/prompt_06_scripts_locais_resultado.md`) — 2 bugs reais encontrados e corrigidos durante a validação |
| Quality gate local | **Fechado — STG-LOCAL-007** (`resultados_execucao/prompt_07_quality_gate_local_resultado.md`) — 9/9 etapas `PASS` numa execução completa real |
| Execução real do E2E contra a stack local | **Ver `resultados_execucao/prompt_12_fecho_staging_local_resultado.md`** — executado nesta iteração de fecho, ver esse relatório para o resultado (STG-LOCAL-008 nunca teve prompt próprio nesta pipeline) |
| Validação de segurança operacional local (greps, CORS, bundle) | **Fechado — STG-LOCAL-009** (`resultados_execucao/prompt_09_seguranca_local_resultado.md`) — 2 violações reais encontradas e corrigidas |
| Observabilidade local (destino de logs, troubleshooting) | **Fechado — STG-LOCAL-010** (`resultados_execucao/prompt_10_observabilidade_local_resultado.md`) — correlation-id validado ponta-a-ponta com fluxo real |
| Runbook local actualizado | **Fechado — STG-LOCAL-011** (`runbook_staging_local.md`, consolidado em 22 secções) |
| Fecho/classificação final da fase | **Este documento e STG-LOCAL-012** (`resultados_execucao/prompt_12_fecho_staging_local_resultado.md`) |
| Override de portas de PostgreSQL/MinIO (nomes exactos de variável) | **Fechado — STG-LOCAL-002/003**: `POSTGRES_PORT` materializou-se como necessário de facto nesta máquina (LOCAL-R02 real, não só hipotético — ver `resultados_execucao/prompt_03_postgresql_local_resultado.md` §10) |
| Endpoint interno vs. público do MinIO para `public_url` (risco LOCAL-R05) | **Fechado — STG-LOCAL-004**, ver acima |
| Política de leitura anónima do bucket MinIO | **Fechado — STG-LOCAL-004, corrigido no STG-LOCAL-009**: `mc anonymous set download` concedia `s3:ListBucket` além de `s3:GetObject` (achado real) — substituída por política JSON própria, só `s3:GetObject`. **Não replicar em produção** sem uma decisão própria de `signed_url`/bucket privado |
| Bind de rede dos containers (`0.0.0.0` vs `127.0.0.1`) | **Fechado — STG-LOCAL-009** (achado real): PostgreSQL/MinIO publicavam em `0.0.0.0`, alcançáveis por qualquer máquina na rede local; corrigido para `127.0.0.1` explícito |

---

## 16. Fora de escopo (nesta fase, sem excepção)

```text
- Cloud (AWS, R2, GCS, Azure Blob ou qualquer object storage/DB gerido externo);
- Secret store cloud;
- Kubernetes;
- Multi-host real, multi-região;
- CI/CD remoto obrigatório;
- Produção (SLA, alta disponibilidade, alertas, rotação automática de secrets);
- Containerização dos serviços aplicacionais, salvo necessidade clara e de baixo risco identificada em fase posterior;
- Novas funcionalidades de produto, billing, scheduler, workflow engine;
- Optimização de performance;
- Observabilidade empresarial completa.
```

---

## 17. Referências

- Backlog desta fase: [`01_backlog.md`](01_backlog.md)
- Pipeline de prompts: [`02_prompts_staging_infra.md`](02_prompts_staging_infra.md)
- Fase 05 — estado: `frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/estado_staging_pre_producao.md`
- Fase 05 — arquitectura: `frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/arquitectura_staging_pre_producao.md`
- Fase 05 — runbook: `frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/runbook_staging_pre_producao.md`
- Fase 05 — fecho: `frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/resultados_execucao/prompt_11_fecho_pre_producao_resultado.md`
- Mapa de portas: `docs/configuracao/portas_projeto.md`
- Padrão de PostgreSQL descartável já usado no repositório (referência de sintaxe, não de persistência): `content_renderer/docker-compose.e2e.yml`
- Abstracção de storage do Content Renderer: `content_renderer/src/storage/storage.types.ts`
- `.env.example` de cada serviço: `backend_core/.env.example`, `intelligence_engine/.env.example`, `content_renderer/.env.example`, `frontend/.env.example`
