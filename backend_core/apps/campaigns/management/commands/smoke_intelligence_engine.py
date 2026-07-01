"""Operational smoke test for the Backend Core ↔ Intelligence Engine loop.

OPT-IN by nature: it is run **manually** by an operator (not part of the test
suite). It validates the current settings, builds a small representative payload
and calls the **live** Intelligence Engine through the real client, confirming the
response carries ``analysis``, ``scores``, ``grade``, ``moments``,
``recommendations`` and ``summary``. It writes **nothing** to the database.

This complements the opt-in pytest test
``apps/campaigns/tests/test_intelligence_real_loop.py`` (which exercises the full
builder + service + Django endpoint against a live engine and needs a test DB).
The command is the zero-setup, DB-free connectivity/contract/config check meant
for local or staging operation and the runbook.

Security: the internal token is **never printed** — only ``configured`` /
``not_configured``. The underlying client never logs the token either.

Usage::

    # with the Intelligence Engine running and settings pointing at it
    python manage.py smoke_intelligence_engine
    python manage.py smoke_intelligence_engine --reference-date 2026-06-25
"""

import json
import uuid
from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.integrations_bridge.intelligence_sync import (
    IntelligenceEngineError,
    IntelligenceEngineResponseError,
    build_intelligence_engine_client,
)

# The composed endpoint always returns these six blocks on a 200/completed
# response (Intelligence Engine contract §8.1).
RESULT_KEYS = ("analysis", "scores", "grade", "moments", "recommendations", "summary")

SMOKE_WORKSPACE_ID = "smoke-workspace"
SMOKE_CAMPAIGN_ID = "smoke-campaign"


class Command(BaseCommand):
    help = (
        "Operational smoke test: calls the live Intelligence Engine with a "
        "representative payload and verifies the response contract. No DB writes; "
        "the internal token is never printed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reference-date",
            default=None,
            help="ISO date (YYYY-MM-DD) anchoring recency rules. Defaults to today (UTC).",
        )

    def handle(self, *args, **options):
        self._validate_config()
        reference_date = self._resolve_reference_date(options["reference_date"])

        request_id = uuid.uuid4().hex
        payload = self._build_payload(reference_date, request_id)

        client = build_intelligence_engine_client()
        self.stdout.write(
            f"smoke_ie start request_id={request_id} "
            f"base_url={settings.INTELLIGENCE_ENGINE_BASE_URL}"
        )

        try:
            result = client.post_campaign_intelligence(
                payload, workspace_id=SMOKE_WORKSPACE_ID, request_id=request_id
            )
        except IntelligenceEngineResponseError as exc:
            # 4xx/5xx from the engine — controlled failure, no traceback, no token.
            raise CommandError(
                f"Intelligence Engine returned HTTP {exc.status_code} "
                f"({exc.error_code}). Smoke failed."
            ) from exc
        except IntelligenceEngineError as exc:
            # timeout / unavailable / unusable body — controlled failure.
            raise CommandError(
                f"Intelligence Engine call failed ({type(exc).__name__}): {exc} "
                "Smoke failed."
            ) from exc

        self._verify_and_report(result, request_id)

    # ------------------------------------------------------------------ config #
    def _validate_config(self):
        """Fail fast (and clearly) on a configuration that cannot run a real loop."""
        token_state = (
            "configured" if settings.INTELLIGENCE_ENGINE_INTERNAL_TOKEN else "not_configured"
        )
        # Redacted config summary — the token value is NEVER printed.
        self.stdout.write(
            "smoke_ie config "
            f"base_url={settings.INTELLIGENCE_ENGINE_BASE_URL or '(empty)'} "
            f"enabled={settings.INTELLIGENCE_ENGINE_ENABLED} "
            f"dry_run={settings.INTELLIGENCE_ENGINE_DRY_RUN} "
            f"token={token_state} "
            f"timeout_s={settings.INTELLIGENCE_ENGINE_TIMEOUT_SECONDS}"
        )

        problems = []
        if not settings.INTELLIGENCE_ENGINE_BASE_URL:
            problems.append("INTELLIGENCE_ENGINE_BASE_URL is empty")
        if not settings.INTELLIGENCE_ENGINE_ENABLED:
            problems.append(
                "INTELLIGENCE_ENGINE_ENABLED is False (enable it to run the real loop)"
            )
        if settings.INTELLIGENCE_ENGINE_DRY_RUN:
            problems.append(
                "INTELLIGENCE_ENGINE_DRY_RUN is True (set it to False for a real smoke)"
            )
        if not settings.INTELLIGENCE_ENGINE_INTERNAL_TOKEN:
            problems.append(
                "INTELLIGENCE_ENGINE_INTERNAL_TOKEN / INTERNAL_API_TOKEN is empty "
                "(the engine would reject the call with 403)"
            )
        if problems:
            raise CommandError(
                "Cannot run the Intelligence Engine smoke — " + "; ".join(problems) + "."
            )

    @staticmethod
    def _resolve_reference_date(raw):
        if not raw:
            return timezone.now().date()
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise CommandError(
                f"Invalid --reference-date '{raw}' (expected YYYY-MM-DD)."
            ) from exc

    # ----------------------------------------------------------------- payload #
    def _build_payload(self, reference_date, request_id):
        """A small, representative envelope (synthetic — no DB, no real campaign).

        Deliberately minimal: the full ORM→payload builder is exercised by the
        opt-in pytest test. This is just enough for the engine to return all six
        result blocks so the contract can be verified.
        """
        return {
            "payload_version": "1.0",
            "workspace_id": SMOKE_WORKSPACE_ID,
            "request_id": request_id,
            "entity": {"type": "campaign", "id": SMOKE_CAMPAIGN_ID},
            "context": {"reference_date": reference_date.isoformat()},
            "data": {
                "campaign": {
                    "status": "active",
                    "campaign_type": "single_release",
                    "primary_goal": "grow",
                    "start_date": (reference_date - timedelta(days=14)).isoformat(),
                    "end_date": (reference_date + timedelta(days=90)).isoformat(),
                },
                "artist": {"name": "Smoke Artist"},
                "track": {"release_date": reference_date.isoformat()},
                "smart_link_stats": {
                    "total_clicks": 1200,
                    "clicks_last_7_days": 90,
                    "clicks_last_30_days": 300,
                    "active_links": 2,
                },
                "content_outputs": [
                    {"status": "completed", "created_at": reference_date.isoformat()}
                ],
                "media_kits": [{"status": "published"}],
            },
        }

    # ------------------------------------------------------------------ report #
    def _verify_and_report(self, result, request_id):
        if result.status != "completed":
            raise CommandError(
                f"Unexpected engine status '{result.status}' (expected 'completed')."
            )
        missing = [key for key in RESULT_KEYS if key not in (result.result or {})]
        if missing:
            raise CommandError(
                "Engine response is missing expected keys: " + ", ".join(missing) + "."
            )

        summary = {
            "status": result.status,
            "engine": result.engine,
            "engine_version": result.engine_version,
            "request_id": request_id,
            "keys_present": list(RESULT_KEYS),
            "grade": (result.result or {}).get("grade"),
            "moments": len((result.result or {}).get("moments") or []),
            "recommendations": len((result.result or {}).get("recommendations") or []),
            "warnings": len(result.warnings or []),
        }
        self.stdout.write(self.style.SUCCESS("smoke_ie ok " + json.dumps(summary)))
