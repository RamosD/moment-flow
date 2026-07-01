# Resultado — Prompt 13: validação da integração real

## Execução de 2026-07-01 19:14:20 -01:00

**Estado da execução:** `bloqueado`

### Resumo objectivo

A validação frontend ↔ Backend Core não pôde ser declarada bem-sucedida porque `localhost:8000` não está a servir este Backend Core. A porta responde com `server: uvicorn` e uma API alheia; `/api/v1/schema/`, `/api/v1/docs/` e `/admin/` devolvem 404. Isto confirma precisamente o cenário de serviço FastAPI/uvicorn errado que o prompt exigia excluir.

O frontend em `localhost:5173` respondeu HTTP 200, com título `Control Tower`, `/@vite/client` e `/src/main.tsx`, confirmando uma aplicação Vite activa. A configuração local contém exactamente:

```text
VITE_BACKEND_API_BASE_URL=http://localhost:8000/api/v1
```

Consequentemente, o frontend activo aponta para o serviço errado na porta 8000 e não pode executar login nem CampaignAction E2E real.

O browser integrado foi inicializado, mas a sua política local recusou navegação para os URLs localhost desta validação. Não foi usado outro mecanismo de automação para contornar essa política. A evidência HTTP pública foi recolhida por linha de comandos.

Foi feita uma única tentativa controlada de arrancar os serviços:

- Vite gerido pela execução falhou ao carregar a configuração com `spawn EPERM`; apesar disso, já existia/respondeu uma instância Vite em 5173 cuja proveniência não foi controlada por esta execução.
- Django passou `manage.py check`, mas não conseguiu abrir `backend_core/db.sqlite3`, inclusive em modo read-only (`OperationalError: unable to open database file`). O processo de runserver não abriu a porta e foi encerrado.

Sem Backend Core e base de dados acessíveis não foi possível confirmar utilizador, workspace, campaign, recommendations ou content pack activo, nem efectuar escritas reais.

### Matriz de validação real

| Validação | Resultado |
| --- | --- |
| `GET /api/v1/schema/` = 200 | Bloqueado: 404 do serviço uvicorn errado |
| `GET /api/v1/docs/` = 200 | Bloqueado: 404 do serviço uvicorn errado |
| `/admin/` Django existe | Bloqueado: 404 do serviço uvicorn errado |
| Frontend Vite em 5173 | Confirmado por HTTP 200 e assets Vite |
| Configuração Backend Core URL | Confirmada em `.env.local` |
| Login/workspace/campaign/War Room | Não executado: Backend Core indisponível |
| CampaignActionsPanel real | Não executado |
| Manual task / reviewed / dismiss | Não executado |
| Report / media kit / content pack action | Não executado |
| `related_*`, reload e persistência | Não executado |
| Deduplicação e múltiplos tipos | Não executado em ambiente real |
| 400/401/403/404/cross-workspace reais | Não executado contra Backend Core |
| Browser visual/network | Bloqueado pela política local do browser |

### Evidência disponível sem mocks

- O read path do painel referencia exclusivamente `CAMPAIGN_ACTIONS_PATH = '/campaign-actions/'` através da entity CampaignAction.
- A entity CampaignAction não contém chamadas a `/content-pack-requests/`, `/reports/` ou `/media-kits/`.
- Esses endpoints proprietários permanecem apenas nas respectivas entities e são usados para criação dos artefactos antes do POST CampaignAction.
- O código contém GET/POST/PATCH e endpoints semânticos CampaignAction esperados.
- Esta evidência é estática e automatizada; não substitui Network/API real, que permanece pendente.

### Ficheiros criados ou alterados

- Criado `frontend/docs/01_fundamentos/03_campaign_actions_backend_integration/resultados_execucao/prompt_13_validar_integracao_real_resultado.md`.
- Nenhum ficheiro runtime frontend ou backend foi alterado nesta iteração.
- Nenhum dado backend foi criado ou alterado.

### Validações executadas e resultado

- Browser integrado: conexão estabelecida, mas navegação localhost recusada pela política local.
- HTTP `localhost:5173/`: 200; Vite/Control Tower confirmado.
- HTTP `localhost:8000/`: serviço uvicorn alheio confirmado.
- HTTP schema/docs/admin em 8000: 404.
- `backend_core/venv/Scripts/python.exe manage.py check`: passou, zero issues.
- Acesso Django/SQLite e sqlite3 read-only: falhou com `unable to open database file`.
- `pnpm test`: passou; 14 testes, 14 passed, 0 failed.
- `pnpm lint`: passou, exit code 0.
- `pnpm build`: bloqueado por `TS5033 EPERM` ao escrever `node_modules/.tmp/tsconfig.*.tsbuildinfo`.
- Typecheck alternativo app/node, com build info em `%TEMP%`: passou sem erros.
- Greps por `X-Internal-Token`, `INTERNAL_API_TOKEN`, `intelligence_engine`, `content_renderer`, `localhost:8001`, `localhost:8002`, Bearer, `api_key`, `password` e `private_key`: executados.
- Não existem IE/Renderer/portas internas nem Bearer hardcoded. As ocorrências restantes são guards/denylist, token dinâmico central, formulário de login e dados sintéticos de teste.
- Grep de endpoints: CampaignAction usa `/campaign-actions/`; endpoints proprietários não alimentam a entity/painel CampaignAction.
- `git diff --check`: passou; apenas avisos informativos LF/CRLF.
- Relatório revisto: não contém tokens, passwords ou outros secrets.

### Pendências, riscos ou próximo passo recomendado

- Libertar ou reconfigurar `localhost:8000` para que a porta seja ocupada pelo Django Backend Core, não pelo serviço uvicorn alheio.
- Corrigir o acesso do ambiente a `backend_core/db.sqlite3` ou configurar uma base de dados dev funcional.
- Arrancar Backend Core e confirmar schema/docs/admin antes de repetir qualquer login.
- Disponibilizar user, workspace, campaign, recommendations e content pack activo sem incluir credenciais no relatório.
- Executar novamente toda a matriz browser/Network deste prompt: criação dos seis tipos/decisões aplicáveis, relações, reload, deduplicação, múltiplos tipos e erros HTTP reais.
- Repetir num ambiente onde o browser integrado aceite localhost e onde Vite possa arrancar sem `spawn EPERM`.
- Até essa repetição, a integração real permanece **não validada**; apenas código, testes e contrato estático estão validados.
