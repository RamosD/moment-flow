"""Seed a namespaced, disposable dataset for a single E2E test run.

Not for production or shared staging data: every object is scoped by
``--run-id`` (a short, unique token supplied by the caller, e.g. a UUID or a
CI run id) so parallel or repeated runs never collide and never need manual
cleanup between them — a fresh ``--run-id`` is a fresh, isolated namespace.

The password is never hardcoded, generated, or passed as an argument (which
would land in shell history / process listings) — it must come from the
``E2E_PASSWORD`` environment variable, exactly like every other secret in
this project (see ``backend_core/.env.example``).
"""

import json
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.campaigns.models import Campaign
from apps.catalogue.models import Artist
from apps.content.seeds import seed_content
from apps.rbac.seeds import seed_rbac
from apps.workspaces.services import create_workspace

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Create a disposable, namespaced user/workspace/artist/campaign for a "
        "single E2E run. Requires E2E_PASSWORD in the environment. Prints the "
        "created ids as a single JSON line on stdout."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--run-id",
            required=True,
            help="Short, unique token identifying this run (e.g. a UUID).",
        )

    def handle(self, *args, **options):
        run_id = options["run_id"]
        password = os.environ.get("E2E_PASSWORD")
        if not password:
            raise CommandError(
                "E2E_PASSWORD is not set. Refusing to invent or hardcode a "
                "password — export E2E_PASSWORD before running this command."
            )

        # Idempotent, cheap prerequisites (RBAC roles, system content packs) —
        # safe to call on every run, real or staging.
        seed_rbac()
        seed_content()

        email = f"e2e-{run_id}@example.local"
        user, _created = User.objects.get_or_create(
            email=email, defaults={"full_name": f"E2E Run {run_id}"}
        )
        user.set_password(password)
        user.is_active = True
        user.save()

        # Re-running with the same --run-id (e.g. a retried CI step) must
        # reuse the same namespace, not pile up duplicate workspaces.
        workspace = user.created_workspaces.filter(
            name=f"E2E Workspace {run_id}"
        ).first()
        if workspace is None:
            workspace = create_workspace(user=user, name=f"E2E Workspace {run_id}")

        artist, _ = Artist.objects.get_or_create(
            workspace=workspace,
            slug=f"e2e-artist-{run_id}",
            defaults={"name": f"E2E Artist {run_id}"},
        )
        campaign, _ = Campaign.objects.get_or_create(
            workspace=workspace,
            slug=f"e2e-campaign-{run_id}",
            defaults={
                "artist": artist,
                "name": f"E2E Campaign {run_id}",
                "status": Campaign.Status.ACTIVE,
            },
        )

        self.stdout.write(
            json.dumps(
                {
                    "run_id": run_id,
                    "email": email,
                    "workspace_id": str(workspace.id),
                    "workspace_name": workspace.name,
                    "artist_id": str(artist.id),
                    "campaign_id": str(campaign.id),
                }
            )
        )
