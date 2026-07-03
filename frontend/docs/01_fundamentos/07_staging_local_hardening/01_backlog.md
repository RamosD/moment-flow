# Backlog — Staging Local Hardening

> Fase: `07_staging_local_hardening`
> Estado: planeada
> Caminho recomendado: `frontend/docs/01_fundamentos/07_staging_local_hardening/01_backlog.md`
> Dependência anterior: `06_staging_infraestrutura_real_local` fechada como `pronto_para_staging_local_formal`
> Objectivo: endurecer a stack staging local formal, reduzindo riscos operacionais, estabilizando E2E, melhorando segurança de credenciais, timeout de DB, validação externa do runbook e preparando CI/CD real

---

# 1. Objectivo

Consolidar a stack staging local já funcional, atacando apenas os riscos e limitações remanescentes da fase 06.

A fase 07 não deve criar produto novo. Deve tornar o que já existe mais confiável, seguro, repetível e transferível.

---

# 2. Tese da fase

```text
A stack local já funciona. Agora deve deixar de depender de tolerância manual, sorte operacional e confiança implícita.
```

---

# 3. Estado de partida

A fase 06 entregou:

```text
- PostgreSQL local persistente em container;
- MinIO local persistente em container;
- Backend Core contra PostgreSQL;
- Content Renderer com provider S3-compatible/MinIO;
- Asset.public_url funcional;
- secrets locais ignorados pelo git;
- scripts locais de infra/apps/health/reset;
- quality gate local;
- segurança local validada;
- observabilidade local com correlation-id;
- runbook local consolidado;
- E2E real executado contra PostgreSQL + MinIO;
- estado final pronto_para_staging_local_formal.
```

Pendências que justificam esta fase:

```text
- E2E teve um flake pontual no passo de media kit;
- requests normais do Backend Core podem ficar pendurados se PostgreSQL cair;
- Content Renderer usa credenciais root do MinIO como access key;
- runbook ainda não foi validado por um segundo operador;
- existe quality gate local, mas ainda não CI/CD real;
- observabilidade local ainda é simples e sem agregação;
- resets/limpezas locais ainda dependem de disciplina operacional.
```

---

# 4. Fora do escopo

Não incluir nesta fase:

```text
- novas features de Campaign Actions;
- alterações de UX não relacionadas com estabilidade;
- produção;
- cloud;
- Kubernetes;
- observabilidade empresarial pesada;
- billing;
- multi-tenant avançado;
- deploy remoto;
- reescrita de scripts;
- containerização obrigatória dos serviços aplicacionais;
- mudança de arquitectura base.
```

---

# 5. Princípios da fase

```text
- endurecer sem expandir escopo;
- corrigir riscos reais observados;
- manter compatibilidade com dev local;
- não quebrar a stack staging local formal;
- não introduzir cloud por arrasto;
- não esconder flakes;
- não silenciar falhas;
- não baixar cobertura;
- manter documentação e execução alinhadas.
```

---

# 6. Backlog incremental

---

## STG-HARD-001 — Estabilizar E2E local

### Objectivo

Investigar e reduzir o flake observado no E2E local, especialmente no fluxo de criação de media kit.

### Contexto

Durante o fecho da fase 06, a primeira execução do E2E falhou no passo de media kit, ficando o diálogo em `Creating…` por timeout. Uma chamada directa à API respondeu rapidamente, e a segunda execução passou `12/12`.

### Tarefas

```text
- localizar teste Playwright responsável pela criação de media kit;
- inspeccionar waits, timeouts e selectors usados;
- verificar se o teste espera UI, rede, estado de backend ou callback de renderer;
- confirmar se o timeout é demasiado agressivo para a máquina local;
- adicionar waits explícitos baseados em estado real, não sleeps cegos;
- melhorar diagnóstico em falha:
  - screenshots;
  - trace;
  - logs por run-id;
  - correlation-id;
  - output de requests relevantes;
- executar E2E várias vezes seguidas;
- registar taxa de sucesso/falha;
- não remover cobertura.
```

### Critérios de aceitação

```text
- E2E passa em múltiplas execuções consecutivas;
- falhas, se ocorrerem, deixam evidência diagnóstica clara;
- media kit continua coberto;
- report/content pack/manual task continuam cobertos;
- Network apenas Backend Core continua validada;
- nenhum sleep arbitrário é introduzido como solução principal.
```

### Critérios de rejeição

```text
- remover o teste de media kit;
- aumentar timeout global sem diagnóstico;
- mascarar flake com retry cego sem evidência;
- transformar E2E em teste superficial;
- usar mocks ou dry_run;
- deixar de validar PostgreSQL/MinIO.
```

---

## STG-HARD-002 — Configurar timeout curto para PostgreSQL

### Objectivo

Evitar que pedidos normais do Backend Core fiquem pendurados por longos períodos quando PostgreSQL está indisponível.

### Contexto

Na fase 06, `/ready/` falhava rapidamente quando PostgreSQL caía, mas pedidos normais como `GET /workspaces/` podiam ficar pendurados por mais de dois minutos.

### Tarefas

```text
- inspeccionar config DATABASES em backend_core/config/settings.py;
- confirmar comportamento actual com PostgreSQL indisponível;
- adicionar connect_timeout curto apenas para PostgreSQL;
- manter SQLite/dev compatível;
- parametrizar timeout por env se fizer sentido;
- garantir valor default seguro para staging local;
- validar /ready/;
- validar pedido normal com PostgreSQL down;
- validar recuperação após PostgreSQL up;
- executar suite backend relevante;
- documentar no runbook.
```

### Critérios de aceitação

```text
- pedidos normais falham em tempo controlado quando PostgreSQL está down;
- /ready/ continua a falhar rapidamente;
- recuperação após restart do PostgreSQL funciona;
- SQLite/dev não quebra;
- testes backend passam;
- runbook documenta o comportamento.
```

### Critérios de rejeição

```text
- timeout aplicado de forma que quebra SQLite;
- timeout demasiado alto para diagnóstico;
- erro expõe credenciais;
- alteração quebra migrations/testes;
- esconder falha com retry infinito.
```

---

## STG-HARD-003 — Criar credenciais MinIO não-root

### Objectivo

Substituir o uso das credenciais root do MinIO pelo Content Renderer por credenciais dedicadas de serviço com permissões mínimas.

### Contexto

A fase 06 aceitou o uso de `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` como `STORAGE_ACCESS_KEY`/`STORAGE_SECRET_KEY` por ser staging local. Esta fase deve endurecer esse ponto.

### Tarefas

```text
- definir utilizador de serviço para Content Renderer;
- definir policy mínima:
  - PutObject;
  - GetObject;
  - possivelmente ListBucket apenas se tecnicamente necessário;
  - sem delete, salvo necessidade clara;
  - sem admin;
- actualizar minio-bucket-init para criar user/policy;
- actualizar content_renderer/.env.staging.local.example ou documentação;
- manter root apenas para administração local;
- validar upload de report/media kit/content pack;
- validar download via public_url;
- validar que credenciais root não são usadas pelo Content Renderer;
- validar que credenciais de serviço não conseguem operações administrativas.
```

### Critérios de aceitação

```text
- Content Renderer usa credenciais MinIO dedicadas;
- root fica reservado para administração;
- uploads continuam a funcionar;
- downloads por public_url continuam a funcionar;
- policy é mínima e documentada;
- secrets continuam ignorados pelo git.
```

### Critérios de rejeição

```text
- Content Renderer continuar a usar root sem justificação;
- policy permissiva demais;
- bucket ficar com listagem pública indevida;
- credenciais serem versionadas;
- quebrar provider local ou provider s3.
```

---

## STG-HARD-004 — Validar runbook por segundo operador

### Objectivo

Validar que o runbook da stack staging local pode ser seguido por alguém sem conhecimento tácito da implementação.

### Tarefas

```text
- escolher segundo operador;
- entregar apenas o runbook e pré-requisitos;
- pedir execução de:
  - start infra;
  - start apps;
  - health;
  - migrations/seeds se necessário;
  - smoke básico;
  - quality gate parcial ou completo;
  - E2E, se viável;
  - stop apps;
  - stop infra;
- registar dúvidas;
- registar comandos ambíguos;
- registar falhas;
- corrigir runbook;
- repetir validação dos passos corrigidos.
```

### Critérios de aceitação

```text
- segundo operador executa o runbook sem ajuda verbal crítica;
- ambiguidades ficam corrigidas;
- comandos principais funcionam;
- runbook não contém secrets;
- validação por terceiro fica registada.
```

### Critérios de rejeição

```text
- declarar validação sem segundo operador;
- orientar verbalmente e não actualizar o runbook;
- ignorar passos que falharam;
- registar secrets no relatório;
- deixar reset destrutivo ambíguo.
```

---

## STG-HARD-005 — Preparar CI/CD real com quality gate

### Objectivo

Criar uma primeira pipeline CI/CD real que reutilize o quality gate local, sem introduzir deploy remoto ou produção.

### Tarefas

```text
- identificar plataforma CI/CD disponível no repositório;
- se não existir, propor a mais compatível com o projecto;
- criar workflow mínimo, se a plataforma estiver clara;
- reutilizar scripts existentes sempre que possível;
- executar:
  - backend check;
  - backend tests;
  - intelligence engine tests;
  - content renderer typecheck/lint/test;
  - frontend test/lint/build;
  - forbidden ports;
  - secrets grep;
- deixar E2E como job manual/opcional se exigir stack local completa;
- garantir que secrets não são impressos;
- documentar limitações.
```

### Critérios de aceitação

```text
- existe workflow CI real ou bloqueio documentado;
- quality gate local é reutilizado ou espelhado;
- jobs falham correctamente;
- nenhuma etapa mascara erro;
- sem deploy automático;
- sem secrets no YAML;
- documentação actualizada.
```

### Critérios de rejeição

```text
- inventar CI/CD não suportado pelo repositório;
- hardcodar secrets;
- deploy automático;
- ignorar testes falhados;
- tornar E2E obrigatório sem stack disponível;
- duplicar lógica de quality gate sem necessidade.
```

---

## STG-HARD-006 — Melhorar cleanup de dados locais

### Objectivo

Reduzir acumulação de dados em PostgreSQL/MinIO durante execuções repetidas de smoke/E2E.

### Tarefas

```text
- inventariar dados criados por seed_e2e_run e E2E;
- confirmar namespace por run-id;
- criar comando seguro de cleanup por run-id;
- evitar limpeza global por defeito;
- impedir reset destrutivo acidental;
- documentar diferença entre:
  - cleanup por run-id;
  - stop infra;
  - reset destrutivo;
- validar cleanup sem apagar dados fora do run-id.
```

### Critérios de aceitação

```text
- existe cleanup seguro por run-id;
- dados de outras execuções não são apagados;
- MinIO e PostgreSQL são limpos de forma consistente;
- reset destrutivo continua separado;
- runbook actualizado.
```

### Critérios de rejeição

```text
- apagar volume inteiro como cleanup normal;
- apagar dados fora do run-id;
- cleanup sem confirmação;
- script com secrets;
- quebrar E2E.
```

---

## STG-HARD-007 — Reforçar diagnóstico E2E/artefactos

### Objectivo

Melhorar a capacidade de diagnosticar falhas E2E, especialmente em jobs assíncronos de Renderer/MinIO.

### Tarefas

```text
- garantir que cada E2E run tem run-id claro;
- garantir correlation-id nos fluxos críticos;
- guardar screenshot/trace em falha;
- guardar resumo de logs relevantes;
- incluir links ou caminhos para:
  - logs Backend Core;
  - logs Content Renderer;
  - logs Intelligence Engine;
  - objectos MinIO;
  - assets criados;
- melhorar mensagem de erro em timeout de job;
- actualizar runbook.
```

### Critérios de aceitação

```text
- falha E2E deixa evidência accionável;
- artefactos de teste são localizáveis por run-id;
- logs são correlacionáveis;
- diagnóstico não expõe secrets.
```

### Critérios de rejeição

```text
- logs com tokens;
- evidência espalhada sem referência;
- screenshots/traces nunca gerados;
- timeout sem contexto.
```

---

## STG-HARD-008 — Auditar padrões `.gitignore` perigosos

### Objectivo

Verificar se existe noutros pontos do repositório o mesmo padrão perigoso encontrado na fase 06, em que `storage/` não ancorado escondia código em `src/storage/`.

### Contexto

Durante a implementação do provider MinIO, foi descoberto que `content_renderer/.gitignore` escondia `src/storage/` por causa de um padrão `storage/` não ancorado. Esse problema foi corrigido ali, mas pode existir noutros `.gitignore`.

### Tarefas

```text
- localizar todos os ficheiros .gitignore;
- identificar padrões não ancorados potencialmente perigosos:
  - storage/;
  - dist/;
  - build/;
  - logs/;
  - data/;
  - tmp/;
  - cache/;
- verificar se escondem código-fonte acidentalmente;
- usar git check-ignore em paths suspeitos;
- corrigir apenas padrões claramente perigosos;
- não passar a versionar artefactos gerados;
- documentar achados.
```

### Critérios de aceitação

```text
- padrões perigosos auditados;
- falsos positivos evitados;
- código-fonte não fica escondido por .gitignore;
- artefactos gerados continuam ignorados;
- relatório documenta alterações.
```

### Critérios de rejeição

```text
- remover ignores necessários;
- passar a versionar storage/logs/build gerados;
- corrigir padrões sem evidência;
- ignorar achados claros.
```

---

## STG-HARD-009 — Revalidar segurança local após hardening

### Objectivo

Reexecutar validações de segurança depois das alterações de timeout, MinIO credentials, cleanup e CI.

### Tarefas

```text
- validar frontend bundle sem IE/Renderer URLs;
- validar Network apenas Backend Core;
- validar X-Internal-Token apenas server-to-server;
- validar health dependencies staff-only;
- validar MinIO sem listagem pública;
- validar credenciais MinIO não-root;
- validar PostgreSQL bind 127.0.0.1;
- validar logs sem secrets;
- validar greps de secrets;
- validar CORS.
```

### Critérios de aceitação

```text
- segurança local mantém-se ou melhora;
- nenhuma regressão de porta/bind;
- MinIO continua sem listagem pública;
- frontend continua isolado;
- logs continuam limpos.
```

### Critérios de rejeição

```text
- regressão para 0.0.0.0;
- bucket volta a listar publicamente;
- frontend chama IE/Renderer;
- token interno aparece no browser;
- secrets aparecem em logs ou ficheiros versionados.
```

---

## STG-HARD-010 — Fecho de hardening local

### Objectivo

Consolidar a fase 07 e decidir se o staging local formal ficou endurecido.

### Tarefas

```text
- ler todos os relatórios da fase 07;
- actualizar runbook;
- actualizar estado da fase;
- listar melhorias implementadas;
- listar riscos remanescentes;
- executar quality gate;
- executar E2E múltiplas vezes, se viável;
- executar segurança local;
- declarar estado final;
- definir próxima fase.
```

### Critérios de aceitação

```text
- estado final documentado;
- E2E estabilizado ou risco quantificado;
- timeout PostgreSQL tratado ou decisão justificada;
- credenciais MinIO endurecidas;
- runbook validado por terceiro ou pendência explicitamente aceite;
- CI/CD real criado ou bloqueio documentado;
- quality gate verde;
- produção não declarada.
```

### Critérios de rejeição

```text
- declarar hardening concluído ignorando flake;
- ignorar timeout PostgreSQL;
- manter MinIO root sem decisão;
- declarar validação por terceiro sem terceiro;
- criar CI insegura;
- mascarar falhas.
```

---

# 7. Critérios de aceitação da fase

A fase é aceite se:

```text
- E2E local fica mais estável ou o risco fica medido e diagnosticável;
- timeout PostgreSQL para pedidos normais é controlado ou decisão técnica documentada;
- Content Renderer deixa de usar credenciais root do MinIO ou há decisão explícita justificada;
- runbook é validado por segundo operador ou pendência é formalmente aceite;
- existe CI/CD real mínimo ou bloqueio concreto documentado;
- cleanup local por run-id existe ou decisão de adiar é justificada;
- segurança local é revalidada;
- quality gate passa;
- estado final é documentado;
- produção continua fora do escopo.
```

---

# 8. Critérios de rejeição da fase

A fase não é aceite se:

```text
- E2E continua flakey sem diagnóstico;
- timeout PostgreSQL continua pendente sem decisão;
- MinIO continua com credenciais root sem justificação;
- secrets aparecem em logs/docs/código;
- bucket volta a permitir listagem pública;
- PostgreSQL/MinIO voltam a bindar em 0.0.0.0;
- frontend chama IE/Renderer;
- runbook continua dependente de conhecimento tácito;
- CI/CD imprime secrets;
- produção é declarada pronta.
```

---

# 9. Riscos principais

| ID       | Risco                                                    | Impacto | Mitigação                                     |
| -------- | -------------------------------------------------------- | ------: | --------------------------------------------- |
| HARD-R01 | E2E flake persistente                                    |    Alto | medir taxa, melhorar waits e diagnóstico      |
| HARD-R02 | Timeout DB mal configurado quebra dev/testes             |    Alto | condicionar a PostgreSQL e validar SQLite     |
| HARD-R03 | Policy MinIO demasiado restritiva quebra upload/download |   Médio | testes reais de report/media/content          |
| HARD-R04 | Policy MinIO permissiva demais                           |    Alto | validar sem ListBucket público                |
| HARD-R05 | CI/CD criado com secrets expostos                        | Crítico | usar variáveis seguras e greps                |
| HARD-R06 | Segundo operador não disponível                          |   Médio | marcar pendência organizacional, não mascarar |
| HARD-R07 | Cleanup apaga dados indevidos                            |    Alto | limitar por run-id e exigir confirmação       |
| HARD-R08 | `.gitignore` auditado de forma agressiva demais          |   Médio | corrigir só com evidência                     |
| HARD-R09 | Scripts locais ficarem mais complexos que o necessário   |   Médio | manter comandos simples e documentados        |
| HARD-R10 | Fase virar pré-produção/cloud por arrasto                |    Alto | manter escopo local-only                      |

---

# 10. Ordem recomendada

```text
Incremento 0 — Estabilidade e segurança técnica
STG-HARD-001
STG-HARD-002
STG-HARD-003

Incremento 1 — Operação local
STG-HARD-006
STG-HARD-007
STG-HARD-008

Incremento 2 — Transferência e automação
STG-HARD-004
STG-HARD-005

Incremento 3 — Revalidação e fecho
STG-HARD-009
STG-HARD-010
```

---

# 11. Documentos esperados

```text
frontend/docs/01_fundamentos/07_staging_local_hardening/01_backlog.md
frontend/docs/01_fundamentos/07_staging_local_hardening/estado_hardening_local.md
frontend/docs/01_fundamentos/07_staging_local_hardening/resultados_execucao/
```

Documentos que podem ser actualizados pela fase:

```text
frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/runbook_staging_local.md
frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/estado_staging_local.md
```

A fase 07 pode actualizar documentos da fase 06 apenas quando estiver a corrigir ou complementar o runbook/estado operacional. Não deve reabrir a classificação da fase 06.

---

# 12. Resultado esperado

Ao fechar esta fase, o projecto deve sair de:

```text
staging local formal funcional
```

para:

```text
staging local formal endurecido, mais estável, mais seguro e mais transferível
```

Sem declarar produção.

---

# 13. Próximo passo

Gerar a pipeline de prompts para execução assistida por IA local desta fase.
