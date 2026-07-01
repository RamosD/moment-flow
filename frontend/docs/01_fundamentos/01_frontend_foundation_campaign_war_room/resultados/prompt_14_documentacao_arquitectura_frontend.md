# FE-014 — Documentar arquitectura frontend

**Fase:** Frontend Foundation & Campaign War Room MVP
**Componente alvo:** `frontend`
**Data:** 2026-06-26
**Tipo:** Documentação

---

## 0. Sumário executivo

- Criado `arquitectura_frontend.md` em `frontend/docs/01_fundamentos/01_frontend_foundation_campaign_war_room/arquitectura_frontend.md`.
- O documento foi escrito após inspecção directa da estrutura final de `src/` (não a partir do backlog/relatórios apenas) e dos ficheiros-chave que definem a arquitectura: `shared/api/client.ts`, `shared/api/providers.ts`, `app/providers/queryClient.ts`, `app/router/routes.tsx`, `shared/config/env.ts`, `features/auth/AuthProvider.tsx`, `features/auth/token-storage.ts`, `features/workspace-switching/WorkspaceProvider.tsx`, `shared/ui/states/index.ts`, `entities/campaign/intelligence.ts`.
- Cobre: stack, scripts, estrutura de pastas real, regras de dependência (FSD) com exemplos concretos do código, API client, auth/sessão, workspace, routing, server state (TanStack Query), UI foundation, Campaign War Room, tratamento de erros, decisões tomadas, limitações honestas, e uma lista explícita de "o que não fazer".
- Inclui secções práticas "como evoluir": adicionar entidade, adicionar feature, criar página.
- Reforça de forma explícita e repetida: frontend só chama Backend Core; nunca chama Intelligence Engine; nunca chama Content Renderer; `X-Internal-Token` nunca pertence ao frontend (e é activamente bloqueado pelo cliente HTTP).
- Verificado (grep) que o documento não contém tokens, segredos ou padrões de credenciais.

---

## 1. Processo seguido

1. Lido o backlog completo (`01_backlog.md`), com foco nas secções 5 (stack), 6 (estrutura/regras de dependência), 7 (contratos API), 8 (UX War Room) e no histórico de decisões pendentes (§13) e riscos (§12).
2. Listados todos os ficheiros reais em `src/` (`find src -type f`) para que a estrutura documentada reflicta o estado actual, não o estado planeado.
3. Lido `package.json` para confirmar scripts e dependências instaladas (vs. apenas recomendadas no backlog).
4. Lidos os ficheiros-chave de cada camada (API client, providers injectáveis, query client, router, auth, workspace, estados de UI, tipos de intelligence) para documentar o comportamento real, com excertos onde ajuda a clareza (sem copiar código extensivamente).
5. Escrito `arquitectura_frontend.md` com 17 secções, da regra fundamental do ecossistema até "o que não fazer".
6. Validado com grep que não há tokens/segredos no documento.

Não foram alterados ficheiros de runtime nesta tarefa — apenas documentação.

---

## 2. Conteúdo do documento (mapeamento aos critérios pedidos)

| Secção pedida | Onde está no documento |
| --- | --- |
| Stack | §2 |
| Scripts | §2 (subsecção) |
| Estrutura de pastas | §3 (reflecte `src/` real, não o esboço do backlog) |
| Regras de dependência | §4, com exemplos concretos do código (`useCampaign`, `CampaignIntelligencePanel`, `shared/api/providers.ts`) |
| API client | §5 |
| Auth/session | §7 |
| Workspace | §8 |
| Routing | §9 |
| Server state (TanStack Query) | §10 |
| UI foundation | §11 |
| Campaign War Room | §12 |
| Tratamento de erros | §13 |
| Decisões tomadas | §15 |
| Limitações | §16 |
| O que não fazer | §17 |
| Não chamar IE/Renderer directamente | §1 (regra fundamental, reforçada em §5 e §17) |
| `X-Internal-Token` nunca no frontend | §1 e §5 (mecanismo de bloqueio activo no cliente) |
| Como adicionar nova feature | §14.2 |
| Como adicionar nova entidade | §14.1 |
| Como criar nova página | §14.3 |

---

## 3. Ficheiros criados/alterados

**Criado:**
- `frontend/docs/01_fundamentos/01_frontend_foundation_campaign_war_room/arquitectura_frontend.md`
- `frontend/docs/01_fundamentos/01_frontend_foundation_campaign_war_room/resultados/prompt_14_documentacao_arquitectura_frontend.md` (este relatório)

Nenhum ficheiro de código/runtime foi alterado.

---

## 4. Decisões tomadas nesta tarefa

- Documentar a estrutura **real** observada em `src/` em vez de transcrever o esboço do backlog (que difere ligeiramente — ex.: `pages/ui-kit`, `pages/settings`, `widgets/app-shell` como placeholder, `entities/workspace`/`user`/`artist`/`track` com consumo parcial), para que o documento seja fiável para próximos prompts.
- Incluir excertos de código mínimos (não ficheiros completos) só onde ilustram uma regra não-óbvia (ex.: o padrão de providers injectáveis, o despacho automático do `ErrorState`).
- Reaproveitar a tabela de mapeamento de erros já validada no relatório FE-013 em vez de redefini-la, garantindo consistência entre os dois documentos.
- Listar explicitamente as limitações conhecidas (refresh token em localStorage, sem retry transparente, tipos best-effort de intelligence, sem testes, sem RBAC, não production-ready) em vez de omitir para parecer mais "completo" — alinhado com a regra de honestidade da fase.

---

## 5. Validações

| Verificação | Resultado |
| --- | --- |
| `arquitectura_frontend.md` existe no caminho pedido | ✅ |
| Documento explica a estrutura real do frontend | ✅ §3 |
| Documento explica como evoluir (feature/entidade/página) | ✅ §14 |
| Documento explica a regra de não chamar IE/Renderer directamente | ✅ §1 |
| Documento não contém secrets/tokens | ✅ grep sem resultados |
| Esta tarefa é apenas documentação — não corre build/lint (sem alterações de código) | ✅ (não aplicável) |

---

## 6. Critérios de aceitação — verificação

| Critério (FE-014) | Estado |
| --- | --- |
| `arquitectura_frontend.md` existe | ✅ |
| Documento explica a estrutura | ✅ |
| Documento explica como evoluir o frontend | ✅ |
| Documento explica regra de não chamar IE/Renderer directamente | ✅ |
| Documento não contém secrets | ✅ |
| Relatório lista ficheiros criados/alterados, decisões e próximo passo | ✅ (este documento) |

---

## 7. Próximo passo recomendado

**FE-015 — Validação final e estado da fase** (recomendado: sonnet, conforme backlog §17):
- Correr `pnpm build` e `pnpm lint` como validação final da fase completa.
- Validar arranque local (`pnpm dev`) e navegação básica entre todas as rotas.
- Criar `estado_frontend_foundation_campaign_war_room.md` com estado honesto (pronto para piloto técnico: sim; pronto para produção: não) e lacunas conhecidas.
- Criar o relatório final `resultados/prompt_final_frontend_foundation_campaign_war_room.md`, fechando a fase.
