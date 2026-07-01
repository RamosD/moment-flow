# Relatório de execução — Prompt 11: Reports, Media Kits e Notifications

- **Pipeline / Backlog:** Pipeline 10 — Reports, Media Kits e Notifications (BCORE-1001, 1002, 1101)
- **Data:** 2026-06-21
- **Projecto:** `D:\Workspace\ChartRex\momentflow\backend_core`

---

## 1. Prompt executado

Implementar entidades core para relatórios, media kits e notificações internas,
sem renderer avançado. Criar `apps.reports` com `Report`, `ReportSection`,
`MediaKit` e `MediaKitItem` (serializers, filters, viewsets, `reports:view` /
`reports:generate`, usage event na criação); criar `apps.notifications` com
`Notification` (estados unread/read/dismissed/archived), endpoint de listagem e de
marcação como lida; registar tudo no Admin; e testes de criação, secções/itens,
permissões, isolamento por workspace e usage events.

## 2. Objectivo

Relatórios e media kits são críticos para o valor B2B. O Django é dono dos
**pedidos, estados, histórico e permissões**; a geração real de PDF/ZIP fica para
um renderer/worker futuro. As notificações dão a base in-app (sem email, sem
digest). Tudo multi-tenant e com permissões respeitadas.

## 3. Ficheiros criados

| Ficheiro | Descrição |
|---|---|
| `apps/reports/__init__.py`, `apps/reports/apps.py` | App `apps.reports` |
| `apps/reports/models.py` | `Report`, `ReportSection`, `MediaKit`, `MediaKitItem` |
| `apps/reports/services.py` | Hook de billing (usage `report_generated`/`media_kit_generated`, guardado) |
| `apps/reports/serializers.py` | Serializers + validação cross-workspace dos FKs |
| `apps/reports/filters.py` | FilterSets (report, section, media kit, item) |
| `apps/reports/views.py` | Viewsets RBAC (`reports:view`/`reports:generate`) |
| `apps/reports/urls.py` | Router DRF (`/reports/`, `/report-sections/`, `/media-kits/`, `/media-kit-items/`) |
| `apps/reports/admin.py` | Admin com inlines (secções, itens) |
| `apps/reports/migrations/0001_initial.py` | Migration inicial |
| `apps/reports/tests/conftest.py` | Fixtures (rbac, workspaces, artistas, campanhas) |
| `apps/reports/tests/test_reports.py` | Report + secções, usage, isolamento, permissões |
| `apps/reports/tests/test_media_kits.py` | Media kit + itens, usage, isolamento, permissões |
| `apps/notifications/__init__.py`, `apps/notifications/apps.py` | App `apps.notifications` |
| `apps/notifications/models.py` | `Notification` |
| `apps/notifications/services.py` | `create_notification` (entrada sancionada) |
| `apps/notifications/serializers.py` | `NotificationSerializer` |
| `apps/notifications/filters.py` | `NotificationFilter` |
| `apps/notifications/views.py` | Viewset read-only + acções `read` / `read-all` |
| `apps/notifications/urls.py` | Router DRF (`/notifications/`) |
| `apps/notifications/admin.py` | Admin de notificações |
| `apps/notifications/migrations/0001_initial.py` | Migration inicial |
| `apps/notifications/tests/conftest.py` | Fixtures (rbac, workspaces, membros) |
| `apps/notifications/tests/test_notifications.py` | Criação, listagem, mark-read, broadcast, isolamento, acesso |
| `docs/.../resultados/prompt_11_reports_media_kits_notifications.md` | Este relatório |

## 4. Ficheiros alterados

| Ficheiro | Alteração |
|---|---|
| `config/settings.py` | `"apps.reports"` e `"apps.notifications"` em `INSTALLED_APPS` |
| `config/urls.py` | Rotas de reports e notifications montadas em `api/v1/` |

## 5. Migrations criadas

```text
apps/reports/migrations/0001_initial.py
    + Report (FKs nullable campaign/artist/track/requested_by/storage_asset;
      índices workspace+status / workspace+report_type / campaign)
    + ReportSection (FK report; unique report+section_key; índice workspace)
    + MediaKit (FK artist; FKs nullable campaign/track/storage_asset/created_by;
      índices workspace+status / artist)
    + MediaKitItem (FK media_kit; FK nullable asset; índices workspace / media_kit)

apps/notifications/migrations/0001_initial.py
    + Notification (FK workspace; FK nullable user; estados unread/read/dismissed/
      archived; índices workspace+status / workspace+user)
```

`makemigrations --check --dry-run` confirma **No changes detected**; nenhuma
migration anterior foi alterada.

## 6. Comandos executados

```powershell
python manage.py makemigrations reports notifications   # 0001_initial em cada app
python manage.py migrate                                # aplica reports.0001 e notifications.0001
python manage.py check                                  # 0 issues
python manage.py makemigrations --check --dry-run        # No changes detected
python -m pytest -q                                     # 181 passed
ruff check .                                            # All checks passed!
python manage.py spectacular --file schema.yml          # 0 errors
```

## 7. Resultado das validações

| Validação | Resultado |
|---|---|
| `makemigrations` / `migrate` | OK — `reports.0001_initial` e `notifications.0001_initial` aplicadas |
| `manage.py check` | OK — `System check identified no issues (0 silenced)` |
| `makemigrations --check` | OK — `No changes detected` |
| `pytest` | **181 passed** (159 anteriores + **22 novos**) — 0 regressões |
| `ruff check .` | OK — `All checks passed!` |
| OpenAPI (`spectacular`) | OK — **0 erros** (2 warnings benignos: hint do `PublicSmartLinkSerializer` e colisão de enums `status`) |

**Nota benigna:** persiste o `UserWarning` do WhiteNoise sobre `staticfiles/`.

## 8. Decisões tomadas

- **Sem soft delete; `archived` é estado:** os campos especificados não incluem
  `deleted_at`. `Report` e `MediaKit` arquivam-se via `status`; os viewsets
  expõem `get/post/patch` (sem `DELETE`). Secções e itens (sub-entidades) mantêm
  o `ModelViewSet` completo, podendo ser removidos.
- **Permissões partilhadas reports:**` Report`, `ReportSection`, `MediaKit` e
  `MediaKitItem` usam o mesmo conjunto `reports:view` (ler) / `reports:generate`
  (criar/alterar). Confirma-se nos testes: *editor* (tem `reports:view`, não tem
  `reports:generate`) **lista** mas **não cria** (403); *viewer* idem; *owner*
  cria (201).
- **Hook de billing guardado:** `record_report_created` / `record_media_kit_created`
  registam `UsageEvent` (`report_generated` / `media_kit_generated`) via
  `record_creation_usage`, com `import` protegido por `try/except ImportError` e
  *event types* como strings — a app reports não falha se billing for removida.
  Idempotente por entidade (chave derivada do `id`).
- **Integridade cross-workspace nos serializers:** todos os FKs (campaign, artist,
  track, asset, report/media_kit pai) são validados contra o workspace activo
  (`X-Workspace-ID`), devolvendo 400 com mensagem clara.
- **Notificações — modelo de visibilidade:** `user` nullable → uma notificação é
  dirigida a um utilizador **ou** um *broadcast* do workspace (`user` null). O
  queryset devolve `user=request.user OR user__isnull=True`; um membro não vê
  notificações dirigidas a outro utilizador, mas vê os broadcasts.
- **Notificações criadas pelo sistema:** a API é read-only + acções `read`
  (detail, marca lida com `read_at`) e `read-all` (marca todas as não lidas). A
  criação é feita por `create_notification` (serviço sancionado para outras apps e
  testes), evitando *spoofing* de notificações via API.
- **Acesso por membership:** as notificações não têm permissão RBAC própria no
  catálogo, por isso são gated por `IsWorkspaceMember` — não-membro recebe 403.

## 9. Pendências

- **Renderer real (PDF/ZIP):** fora do escopo — `Report`/`MediaKit` nascem em
  estado não-terminal e o `storage_asset` será anexado depois por um worker
  externo (à semelhança do *content* bridge). Sem geração real.
- **Página pública de media kit:** não implementada (restrição) — `public_visibility`
  existe como campo, mas não há endpoint público nem UI.
- **Email / digest de notificações:** intencionalmente **não** implementados
  (restrição). Sem provider de email, sem agregação periódica.
- **`NotificationPreference` (BCORE-1102, P1):** preferências por utilizador ficam
  para depois.
- **Emissão automática de notificações:** o serviço `create_notification` existe,
  mas ainda **não está ligado** a eventos (ex.: report `completed` →
  `report_ready`); ligar quando houver callbacks do renderer.
- **`ReportSection`/`MediaKitItem` nested routes:** expostos como recursos
  top-level filtráveis por pai (não há rotas verdadeiramente aninhadas).
- **`collectstatic`** continua por correr (warning benigno do WhiteNoise).

## 10. Próximo passo recomendado

Avançar para **Pipeline 11 — Audit, Admin e Integrations bridge**
(BCORE-1201, 1301, 1302): criar `apps.audit` (`AuditEvent` + `record_audit_event`,
Admin read-only) cobrindo as acções já existentes (`report.requested`,
`media_kit.created`, `credits.*`, `billing.plan_changed`, …) e `apps.integrations_bridge`
(`ExternalJobReference` + callback interno autenticado por `X-Internal-Token`)
para orquestrar o renderer/worker que concretiza a geração de relatórios e media
kits aqui deixada em estado *queued*. Em paralelo, ligar `create_notification` aos
callbacks de conclusão (report/media kit → `report_ready`/`media_kit_ready`).
