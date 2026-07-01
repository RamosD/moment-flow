"""Operational smoke test for the Backend Core → Content Renderer leg.

OPT-IN by nature: run **manually** by an operator. It validates the renderer
configuration, probes the renderer's public ``GET /health`` and (by default)
submits one representative job to ``POST /jobs/``, verifying the **202**
acceptance. It writes **nothing** to the Backend Core database.

Scope — this command covers the **outbound leg** (health + token alignment + job
acceptance). The **full asynchronous loop** (renderer → callback → Django →
``ExternalJobReference`` updated → ``Asset`` created) is cross-process and is
validated by the existing E2E harness in the renderer repo; see the operational
checklist ``smoke_content_renderer.md``.

Security: the internal token is **never printed** (only ``configured`` /
``not_configured``) and the underlying client never logs it. The token travels
only in the ``X-Internal-Token`` header.

Usage::

    python manage.py smoke_content_renderer                 # health + submit (content_generation)
    python manage.py smoke_content_renderer --health-only   # just GET /health (no render triggered)
    python manage.py smoke_content_renderer --job-type report_generation
"""

import json
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.integrations_bridge import registry
from apps.integrations_bridge.clients import (
    InternalClientTimeout,
    InternalHTTPError,
    InternalServiceClient,
    InternalServiceUnavailable,
)
from apps.integrations_bridge.health import OK, http_health_probe
from apps.integrations_bridge.services import SUBMIT_PATH

# Acceptance status the renderer returns for an accepted job (CR-201).
ACCEPTED_STATUS_CODE = 202

_ENTITY_TYPE = {
    registry.CONTENT_GENERATION: "content_pack_request",
    registry.REPORT_GENERATION: "report",
    registry.MEDIA_KIT_GENERATION: "media_kit",
}


class Command(BaseCommand):
    help = (
        "Operational smoke test: probes the Content Renderer /health and "
        "(optionally) submits a job, verifying the 202 acceptance. No DB writes; "
        "the internal token is never printed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--job-type",
            default=registry.CONTENT_GENERATION,
            choices=[
                registry.CONTENT_GENERATION,
                registry.REPORT_GENERATION,
                registry.MEDIA_KIT_GENERATION,
            ],
            help="Job type to submit (default content_generation).",
        )
        parser.add_argument(
            "--health-only",
            action="store_true",
            help="Only probe GET /health; do not submit a job (no render triggered).",
        )

    def handle(self, *args, **options):
        job_type = options["job_type"]
        endpoint = self._resolve_and_validate(job_type)

        # 1) Health probe — public endpoint, NO token sent.
        status, duration_ms, detail = http_health_probe(
            endpoint.base_url, settings.HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS
        )
        self.stdout.write(
            f"smoke_renderer health provider={endpoint.provider} "
            f"base_url={endpoint.base_url} status={status} duration_ms={duration_ms}"
            + (f" detail={detail}" if detail else "")
        )
        if status != OK:
            raise CommandError(
                f"Renderer /health is '{status}'"
                + (f" ({detail})" if detail else "")
                + ". Smoke failed."
            )

        if options["health_only"]:
            self.stdout.write(self.style.SUCCESS("smoke_renderer ok (health-only)"))
            return

        # 2) Submit one job and verify the 202 acceptance.
        self._submit_and_verify(endpoint, job_type)

    # ------------------------------------------------------------------ config #
    def _resolve_and_validate(self, job_type):
        try:
            endpoint = registry.resolve_service(job_type)
        except registry.ServiceNotConfigured as exc:
            raise CommandError(f"{exc} Smoke failed.") from exc
        except registry.UnknownJobType as exc:  # pragma: no cover — guarded by choices
            raise CommandError(str(exc)) from exc

        token_state = "configured" if settings.INTERNAL_API_TOKEN else "not_configured"
        # Redacted config summary — the token value is NEVER printed.
        self.stdout.write(
            "smoke_renderer config "
            f"job_type={job_type} provider={endpoint.provider} "
            f"base_url={endpoint.base_url} token={token_state} "
            f"timeout_s={endpoint.timeout} "
            f"external_jobs_enabled={settings.EXTERNAL_JOBS_ENABLED} "
            f"external_jobs_dry_run={settings.EXTERNAL_JOBS_DRY_RUN}"
        )
        if not settings.INTERNAL_API_TOKEN:
            raise CommandError(
                "INTERNAL_API_TOKEN is empty — the renderer would reject the job "
                "with 403. Set the same token on both services. Smoke failed."
            )
        return endpoint

    # ------------------------------------------------------------------ submit #
    def _submit_and_verify(self, endpoint, job_type):
        job_id = uuid.uuid4().hex
        workspace_id = uuid.uuid4().hex
        request_id = uuid.uuid4().hex
        envelope = self._build_envelope(job_type, job_id, workspace_id, request_id)

        client = InternalServiceClient(endpoint.base_url, endpoint.timeout)
        self.stdout.write(
            f"smoke_renderer submit job_id={job_id} request_id={request_id} "
            f"job_type={job_type}"
        )
        try:
            response = client.post_json(
                SUBMIT_PATH,
                envelope,
                workspace_id=workspace_id,
                job_id=job_id,
                request_id=request_id,
            )
        except InternalHTTPError as exc:
            hint = " (token misaligned?)" if exc.status_code == 403 else ""
            raise CommandError(
                f"Renderer rejected the job with HTTP {exc.status_code}{hint}. "
                "Smoke failed."
            ) from exc
        except InternalClientTimeout as exc:
            raise CommandError(
                "Renderer timed out accepting the job. Smoke failed."
            ) from exc
        except InternalServiceUnavailable as exc:
            raise CommandError(
                "Renderer is unavailable (cannot submit the job). Smoke failed."
            ) from exc

        if response.status_code != ACCEPTED_STATUS_CODE:
            raise CommandError(
                f"Renderer accepted with HTTP {response.status_code} "
                f"(expected {ACCEPTED_STATUS_CODE}). Smoke failed."
            )

        ack = response.data or {}
        summary = {
            "status_code": response.status_code,
            "ack_status": ack.get("status"),
            "job_id": job_id,
            "job_type": job_type,
            "renderer": (ack.get("metadata") or {}).get("renderer"),
        }
        self.stdout.write(self.style.SUCCESS("smoke_renderer ok " + json.dumps(summary)))
        self.stdout.write(
            "note: the renderer renders in the background and will POST a callback; "
            "this command verifies only the 202 acceptance. The full callback loop "
            "(ExternalJobReference + Asset) is validated by the E2E harness — see "
            "the checklist."
        )

    # ----------------------------------------------------------------- payload #
    def _build_envelope(self, job_type, job_id, workspace_id, request_id):
        """A minimal, schema-valid envelope (synthetic — no DB, no real entity).

        Matches the renderer's strict envelope schema: exactly the eight top-level
        keys, a valid ``callback_url`` and an object ``payload``.
        """
        return {
            "job_id": job_id,
            "workspace_id": workspace_id,
            "request_id": request_id,
            "job_type": job_type,
            "callback_url": registry.callback_url(),
            "entity": {"type": _ENTITY_TYPE[job_type], "id": uuid.uuid4().hex},
            "payload_version": "1.0",
            "payload": self._payload_for(job_type),
        }

    @staticmethod
    def _payload_for(job_type):
        if job_type == registry.REPORT_GENERATION:
            return {
                "report_type": "weekly_growth",
                "title": "Smoke Report",
                "period_start": "2026-06-01",
                "period_end": "2026-06-07",
                "sections": [{"heading": "Highlights", "items": ["smoke ok"]}],
            }
        if job_type == registry.MEDIA_KIT_GENERATION:
            return {"artist": {"name": "Smoke Artist"}}
        # content_generation
        return {
            "campaign": {"name": "Smoke Campaign"},
            "artist": {"name": "Smoke Artist"},
            "track": {"title": "Smoke Track"},
            "content_pack": {"pack_key": "release_pack"},
            "expected_outputs": [
                {"output_type": "post", "format": "png", "required": True}
            ],
        }
