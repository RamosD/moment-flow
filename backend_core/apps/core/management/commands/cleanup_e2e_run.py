"""Delete a namespaced, disposable E2E/smoke dataset by --run-id (STG-HARD-006).

Companion to ``seed_e2e_run``: everything that command (and the E2E/smoke flows
built on top of it) creates is namespaced by ``--run-id`` through two anchors —
the user's email (``e2e-{run_id}@example.local``) and the workspace's name
(``E2E Workspace {run_id}``). This command resolves those two anchors and
removes only what is reachable from them:

  - the ``Workspace`` itself (hard-deleted — see below);
  - everything that cascades from it in the database (Campaign, Artist, Track,
    CampaignAction, Report/ReportSection, MediaKit/MediaKitItem,
    ContentPackRequest, ContentOutput, Asset, WorkspaceMember, any
    workspace-scoped Role) — all of these use ``WorkspaceOwnedModel``, whose
    ``workspace`` FK is ``on_delete=CASCADE``;
  - ``ExternalJobReference`` and ``AuditEvent`` explicitly, *before* deleting
    the workspace — both point at ``workspace`` with ``on_delete=SET_NULL``,
    so a plain workspace delete would silently orphan them (leave the row,
    null the FK) instead of removing them;
  - the run's ``User`` row.

``Workspace`` (and Campaign/Artist/Track/Asset) are ``SoftDeleteModel``:  their
default manager's ``.delete()`` only sets ``deleted_at`` — it never removes a
row nor triggers a real cascade. This command deliberately uses
``Workspace.all_objects.filter(...).hard_delete()`` (the real, cascading
delete) — anything less would leave the data in Postgres, defeating the whole
point of a cleanup command.

Never touches system/global data: RBAC ``Permission``/``Role`` (system roles
have ``workspace=None``) and content ``Template``/``ContentPackTemplate``/
``ContentPack`` have no workspace FK at all and are seeded once, shared by
every workspace — this command's queries never reach them.

Safety:
  - ``--run-id`` must be non-empty (whitespace-only is rejected too).
  - A run-id that matches nothing is not an error — it prints
    ``"found": false`` and exits 0 (idempotent: cleaning up an already-clean
    or never-seeded run-id is a no-op, not a failure).
  - If both the workspace and the user exist but don't belong to each other
    (the workspace's ``created_by`` isn't the resolved user), the command
    refuses to guess and raises ``CommandError`` instead of deleting anything.
  - ``--dry-run`` prints counts and the resolved ``workspace_id`` and deletes
    nothing.
  - Without ``--dry-run``, an interactive confirmation (typing the exact
    run-id back) is required unless ``--yes`` is passed — mirroring the typed
    confirmation already used by ``scripts/staging-local-infra-reset.ps1``,
    at a much smaller (and reversible-by-reseeding) blast radius.
  - Output is a single JSON line with counts and ids only — never a secret
    (this command never touches ``E2E_PASSWORD``/tokens/MinIO credentials).
  - This command only ever deletes rows in whatever database
    ``settings.DATABASES["default"]`` points at (local dev/staging, per this
    project's own environment loading) — it has no notion of "production" or
    "cloud" and no code path that could reach one.
"""

import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.audit.models import AuditEvent
from apps.campaign_actions.models import CampaignAction
from apps.campaigns.models import Campaign
from apps.catalogue.models import Artist, Track
from apps.content.models import ContentOutput, ContentPackRequest
from apps.core.models import Asset
from apps.integrations_bridge.models import ExternalJobReference
from apps.reports.models import MediaKit, Report
from apps.workspaces.models import Workspace

User = get_user_model()


def _counts_for_workspace(workspace_id) -> dict:
    """Count every workspace-scoped row reachable from ``workspace_id``.

    Uses each model's unfiltered manager where one exists (``all_objects``)
    so a dry-run count is never quietly wrong about already-soft-deleted rows
    that a real cleanup would still hard-delete.
    """
    return {
        "campaigns": Campaign.all_objects.filter(workspace_id=workspace_id).count(),
        "artists": Artist.all_objects.filter(workspace_id=workspace_id).count(),
        "tracks": Track.all_objects.filter(workspace_id=workspace_id).count(),
        "campaign_actions": CampaignAction.objects.filter(workspace_id=workspace_id).count(),
        "reports": Report.objects.filter(workspace_id=workspace_id).count(),
        "media_kits": MediaKit.objects.filter(workspace_id=workspace_id).count(),
        "content_pack_requests": ContentPackRequest.objects.filter(
            workspace_id=workspace_id
        ).count(),
        "content_outputs": ContentOutput.objects.filter(workspace_id=workspace_id).count(),
        "external_jobs": ExternalJobReference.objects.filter(
            workspace_id=workspace_id
        ).count(),
        "audit_events": AuditEvent.objects.filter(workspace_id=workspace_id).count(),
        "assets": Asset.all_objects.filter(workspace_id=workspace_id).count(),
    }


class Command(BaseCommand):
    help = (
        "Delete the namespaced dataset created by seed_e2e_run/E2E for a single "
        "--run-id (workspace, artist(s), campaign(s), reports, media kits, "
        "content pack requests/outputs, campaign actions, external jobs, audit "
        "events, assets, the run's user). Never touches data outside this "
        "exact run-id's namespace, and never system/global RBAC or content "
        "template data. Prints one JSON line with counts and ids — never a "
        "secret."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--run-id",
            required=True,
            help="The exact --run-id originally passed to seed_e2e_run.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted (counts, workspace_id). Deletes nothing.",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip the interactive confirmation prompt (for CI/non-interactive use).",
        )

    def handle(self, *args, **options):
        run_id = (options["run_id"] or "").strip()
        if not run_id:
            raise CommandError(
                "--run-id must not be empty (refusing to guess a scope this wide)."
            )

        dry_run = options["dry_run"]
        skip_prompt = options["yes"]

        email = f"e2e-{run_id}@example.local"
        workspace_name = f"E2E Workspace {run_id}"

        workspace = Workspace.all_objects.filter(name=workspace_name).first()
        user = User.objects.filter(email=email).first()

        if workspace is None and user is None:
            self.stdout.write(
                json.dumps(
                    {"run_id": run_id, "found": False, "workspace_id": None, "counts": {}}
                )
            )
            return

        if (
            workspace is not None
            and user is not None
            and workspace.created_by_id != user.id
        ):
            raise CommandError(
                f"Safety check failed: workspace '{workspace_name}' was not created "
                f"by '{email}'. Refusing to guess which one is the real "
                "run-id owner — inspect manually, nothing was deleted."
            )

        workspace_id = str(workspace.id) if workspace is not None else None
        counts = _counts_for_workspace(workspace.id) if workspace is not None else {}
        counts["users"] = 1 if user is not None else 0

        if dry_run:
            self.stdout.write(
                json.dumps(
                    {
                        "run_id": run_id,
                        "found": True,
                        "dry_run": True,
                        "workspace_id": workspace_id,
                        "counts": counts,
                    }
                )
            )
            return

        if not skip_prompt:
            self.stdout.write(
                f"About to permanently delete the dataset for run-id '{run_id}':"
            )
            self.stdout.write(json.dumps(counts))
            answer = input(f"Type the run-id ('{run_id}') to confirm deletion: ")
            if answer.strip() != run_id:
                raise CommandError(
                    "Confirmation did not match the run-id. Aborted — nothing deleted."
                )

        with transaction.atomic():
            if workspace is not None:
                # Explicit first: these two point at workspace with SET_NULL,
                # so the workspace delete below would orphan (not remove) them.
                ExternalJobReference.objects.filter(workspace_id=workspace.id).delete()
                AuditEvent.objects.filter(workspace_id=workspace.id).delete()
                # Real delete, not the soft-delete default — cascades to every
                # WorkspaceOwnedModel row (Campaign, Artist, Track,
                # CampaignAction, Report(+sections), MediaKit(+items),
                # ContentPackRequest, ContentOutput, Asset, WorkspaceMember,
                # any workspace-scoped Role).
                Workspace.all_objects.filter(id=workspace.id).hard_delete()
            if user is not None:
                user.delete()

        self.stdout.write(
            json.dumps(
                {
                    "run_id": run_id,
                    "found": True,
                    "dry_run": False,
                    "workspace_id": workspace_id,
                    "counts": counts,
                }
            )
        )
