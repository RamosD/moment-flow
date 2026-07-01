"""End-to-end driver: real Content/Report Renderer ↔ real Backend Core (Django).

This script lives in the renderer repo so the backend stays untouched. It boots
the Django ORM (read from ``BACKEND_CORE_DIR``), creates the minimal product
entities for each scenario, seeds a *committed* ``ExternalJobReference`` via the
bridge in DRY-RUN (so the job exists without Django itself calling the renderer),
then plays the *submitter* role: it POSTs the exact Django envelope to the running
renderer (:8202). The renderer renders a real file and calls back to the running
Django server (:8100), which creates the ``Asset`` and updates the entity.

Why DRY-RUN to seed the job: it commits the job row before the callback arrives
and avoids the synchronous-renderer race where Django's own submit would
overwrite the job status set by the callback. The render + callback + Asset
creation are entirely REAL. (Documented fallback — see the E2E guide.)

Prerequisites (started by the caller):
  - renderer on http://localhost:8202 (same INTERNAL_API_TOKEN)
  - Django runserver on http://localhost:8100 (same INTERNAL_API_TOKEN,
    EXTERNAL_JOBS_ENABLED=true, EXTERNAL_JOBS_DRY_RUN=false,
    *_RENDERER_BASE_URL=http://localhost:8202)

Env:
  BACKEND_CORE_DIR   absolute path to backend_core (default: ../../backend_core)
  INTERNAL_API_TOKEN shared internal token
  RENDERER_JOBS_URL  default http://localhost:8202/jobs/
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.environ.get(
    "BACKEND_CORE_DIR", os.path.abspath(os.path.join(HERE, "..", "..", "backend_core"))
)
TOKEN = os.environ.get("INTERNAL_API_TOKEN", "")
RENDERER_JOBS_URL = os.environ.get("RENDERER_JOBS_URL", "http://localhost:8202/jobs/")

sys.path.insert(0, BACKEND_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

# Seed the job without Django calling the renderer itself (we play submitter).
settings.EXTERNAL_JOBS_ENABLED = True
settings.EXTERNAL_JOBS_DRY_RUN = True
if TOKEN:
    settings.INTERNAL_API_TOKEN = TOKEN

from apps.campaigns.models import Campaign  # noqa: E402
from apps.catalogue.models import Artist  # noqa: E402
from apps.content.models import ContentOutput, ContentPack, ContentPackRequest  # noqa: E402
from apps.content.services import create_content_pack_request  # noqa: E402
from apps.core.models import Asset  # noqa: E402
from apps.integrations_bridge.models import ExternalJobReference  # noqa: E402
from apps.rbac.seeds import seed_rbac  # noqa: E402
from apps.reports.models import MediaKit, Report  # noqa: E402
from apps.reports.services import (  # noqa: E402
    submit_media_kit_generation_job,
    submit_report_generation_job,
)
from apps.workspaces.services import create_workspace  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

User = get_user_model()


def post_envelope(envelope: dict) -> tuple[int, dict]:
    """POST the Django envelope to the renderer with the internal headers."""
    body = json.dumps(envelope).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Internal-Token": TOKEN,
        "X-Workspace-ID": str(envelope["workspace_id"]),
        "X-Job-ID": str(envelope["job_id"]),
        "X-Request-ID": str(envelope["request_id"]),
    }
    req = urllib.request.Request(RENDERER_JOBS_URL, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:  # noqa: PERF203
        return exc.code, {"error": exc.read().decode("utf-8", "replace")}


def probe_callback(envelope: dict) -> int:
    """Non-mutating probe: POST an idempotent same-status callback to Django.

    Returns the HTTP status. 200 => the server can see the committed job;
    404 => the server cannot resolve the job (cross-process visibility).
    """
    body = json.dumps(
        {
            "job_id": envelope["job_id"],
            "workspace_id": envelope["workspace_id"],
            "status": "submitted",
            "entity": envelope["entity"],
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-Internal-Token": TOKEN}
    req = urllib.request.Request(
        envelope["callback_url"], data=body, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def wait_for(predicate, timeout: float = 20.0, interval: float = 0.3) -> bool:
    """Poll ``predicate`` until it returns truthy or ``timeout`` elapses.

    The renderer now answers 202 and runs render + callback in the background
    (R-HARD-001), so the callback lands AFTER the POST returns. The harness must
    poll the entity state rather than rely on a fixed sleep.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def _render_error(resp: dict):
    outputs = (resp.get("result") or {}).get("outputs") or []
    if outputs:
        return (outputs[0].get("metadata") or {}).get("error")
    return resp.get("error")


def asset_summary(asset: Asset | None) -> dict | None:
    if asset is None:
        return None
    return {
        "storage_provider": asset.storage_provider,
        "bucket": asset.bucket,
        "storage_key": asset.storage_key,
        "file_name": asset.file_name,
        "mime_type": asset.mime_type,
        "file_size_bytes": asset.file_size_bytes,
        "checksum_present": bool(asset.checksum),
        "metadata_keys": sorted((asset.metadata or {}).keys()),
    }


def run_report(owner, workspace) -> dict:
    report = Report.objects.create(
        workspace=workspace,
        report_type=Report.ReportType.WEEKLY_REPORT,
        title="E2E Weekly Report",
        requested_by=owner,
    )
    submit_report_generation_job(report, requested_by=owner)
    job = ExternalJobReference.objects.get(
        related_entity_type="report", related_entity_id=str(report.id)
    )
    # Let the just-committed job become visible to the server process before the
    # renderer (synchronous) calls back across the process boundary.
    time.sleep(0.25)
    probe = probe_callback(job.request_payload)
    http_status, resp = post_envelope(job.request_payload)

    # Background callback (R-HARD-001): poll until the Report is finalised.
    def _report_done() -> bool:
        report.refresh_from_db()
        return (
            report.status == Report.Status.COMPLETED
            and report.storage_asset_id is not None
        )

    wait_for(_report_done)
    report.refresh_from_db()
    job.refresh_from_db()
    return {
        "scenario": "report_generation",
        "direct_probe_status": probe,
        "renderer_http_status": http_status,
        "renderer_result_status": (resp.get("result") or {}).get("status"),
        "render_error": _render_error(resp),
        "report_status": report.status,
        "job_status": job.status,
        "asset": asset_summary(report.storage_asset),
        "ok": report.status == Report.Status.COMPLETED and report.storage_asset_id is not None,
    }


def run_media_kit(owner, workspace) -> dict:
    artist = Artist.objects.create(
        workspace=workspace, name="E2E Nova", slug=f"e2e-nova-{uuid.uuid4().hex[:6]}"
    )
    media_kit = MediaKit.objects.create(
        workspace=workspace, artist=artist, title="E2E Press Kit", created_by=owner
    )
    submit_media_kit_generation_job(media_kit, requested_by=owner)
    job = ExternalJobReference.objects.get(
        related_entity_type="media_kit", related_entity_id=str(media_kit.id)
    )
    time.sleep(0.25)
    http_status, resp = post_envelope(job.request_payload)

    # Background callback (R-HARD-001): poll until the MediaKit is finalised.
    def _media_kit_done() -> bool:
        media_kit.refresh_from_db()
        return (
            media_kit.status == MediaKit.Status.GENERATED
            and media_kit.storage_asset_id is not None
        )

    wait_for(_media_kit_done)
    media_kit.refresh_from_db()
    job.refresh_from_db()
    return {
        "scenario": "media_kit_generation",
        "renderer_http_status": http_status,
        "renderer_result_status": (resp.get("result") or {}).get("status"),
        "render_error": _render_error(resp),
        "media_kit_status": media_kit.status,
        "job_status": job.status,
        "asset": asset_summary(media_kit.storage_asset),
        "ok": media_kit.status == MediaKit.Status.GENERATED
        and media_kit.storage_asset_id is not None,
    }


def _invalid_payload_envelope(envelope: dict) -> dict:
    """Deep-copy an envelope and blank its payload to force a controlled render
    failure (the renderer genuinely fails an empty report/media-kit payload and
    emits a real ``failed`` callback)."""
    bad = json.loads(json.dumps(envelope))
    bad["payload"] = {}
    return bad


def run_content(owner, workspace) -> dict:
    """Scenario 1 (completed) + Scenario 8 (idempotency) for content_generation."""
    artist = Artist.objects.create(
        workspace=workspace, name="E2E Content Artist", slug=f"e2e-cart-{uuid.uuid4().hex[:6]}"
    )
    campaign = Campaign.objects.create(
        workspace=workspace, artist=artist, name="E2E Campaign", slug=f"e2e-camp-{uuid.uuid4().hex[:6]}"
    )
    request = create_content_pack_request(
        workspace=workspace,
        requested_by=owner,
        campaign=campaign,
        content_pack=ContentPack.objects.get(pack_key="release_pack"),
        artist=artist,
    )
    job = ExternalJobReference.objects.get(
        related_entity_type="content_pack_request",
        related_entity_id=str(request.id),
        job_type=ExternalJobReference.JobType.CONTENT_GENERATION,
    )
    time.sleep(0.25)
    http_status, resp = post_envelope(job.request_payload)

    def _content_done() -> bool:
        request.refresh_from_db()
        return (
            request.status
            in (
                ContentPackRequest.Status.COMPLETED,
                ContentPackRequest.Status.PARTIALLY_COMPLETED,
            )
            and request.outputs.exists()
        )

    wait_for(_content_done)
    request.refresh_from_db()
    job.refresh_from_db()

    def _content_asset_ids() -> list[str]:
        return sorted(
            str(o.storage_asset_id) for o in request.outputs.all() if o.storage_asset_id
        )

    outputs_first = request.outputs.count()
    assets_first = _content_asset_ids()
    first_output = request.outputs.first()

    # Scenario 8 — idempotency: re-deliver the same job; expect NO new rows.
    t0 = job.updated_at
    post_envelope(job.request_payload)

    def _second_processed() -> bool:
        job.refresh_from_db()
        return job.updated_at != t0

    wait_for(_second_processed, timeout=10.0)
    outputs_second = request.outputs.count()
    assets_second = _content_asset_ids()
    no_dup = outputs_first == outputs_second and assets_first == assets_second

    return {
        "scenario": "content_generation (completed + idempotency)",
        "job_id": str(job.id),
        "renderer_http_status": http_status,
        "renderer_result_status": (resp.get("result") or {}).get("status"),
        "render_error": _render_error(resp),
        "request_status": request.status,
        "job_status": job.status,
        "outputs_count": outputs_first,
        "asset": asset_summary(first_output.storage_asset if first_output else None),
        "idempotency": {
            "outputs_before": outputs_first,
            "outputs_after": outputs_second,
            "assets_before": assets_first,
            "assets_after": assets_second,
            "no_duplicates": no_dup,
        },
        "ok": (
            request.status == ContentPackRequest.Status.COMPLETED
            and request.outputs.filter(status=ContentOutput.Status.COMPLETED).exists()
            and no_dup
        ),
    }


def run_report_failed(owner, workspace) -> dict:
    """Scenario 5 — report_generation failed via a controlled invalid payload."""
    report = Report.objects.create(
        workspace=workspace,
        report_type=Report.ReportType.WEEKLY_REPORT,
        title="E2E Failing Report",
        requested_by=owner,
    )
    submit_report_generation_job(report, requested_by=owner)
    job = ExternalJobReference.objects.get(
        related_entity_type="report", related_entity_id=str(report.id)
    )
    time.sleep(0.25)
    http_status, resp = post_envelope(_invalid_payload_envelope(job.request_payload))

    def _report_failed() -> bool:
        report.refresh_from_db()
        return report.status == Report.Status.FAILED

    wait_for(_report_failed)
    report.refresh_from_db()
    job.refresh_from_db()
    return {
        "scenario": "report_generation failed (invalid payload)",
        "job_id": str(job.id),
        "renderer_http_status": http_status,
        "report_status": report.status,
        "job_status": job.status,
        "asset_linked": report.storage_asset_id is not None,
        "ok": report.status == Report.Status.FAILED and report.storage_asset_id is None,
    }


def run_media_kit_failed(owner, workspace) -> dict:
    """Scenario 7 — media_kit_generation failed via a controlled invalid payload.

    MediaKit has no FAILED status; a failed callback must leave it NON-generated
    (consistent), with the job marked failed and no asset linked.
    """
    artist = Artist.objects.create(
        workspace=workspace, name="E2E MK Fail", slug=f"e2e-mkf-{uuid.uuid4().hex[:6]}"
    )
    media_kit = MediaKit.objects.create(
        workspace=workspace, artist=artist, title="E2E Failing Kit", created_by=owner
    )
    submit_media_kit_generation_job(media_kit, requested_by=owner)
    job = ExternalJobReference.objects.get(
        related_entity_type="media_kit", related_entity_id=str(media_kit.id)
    )
    time.sleep(0.25)
    http_status, resp = post_envelope(_invalid_payload_envelope(job.request_payload))

    def _job_failed() -> bool:
        job.refresh_from_db()
        return job.status == ExternalJobReference.Status.FAILED

    wait_for(_job_failed)
    media_kit.refresh_from_db()
    job.refresh_from_db()
    return {
        "scenario": "media_kit_generation failed (invalid payload)",
        "job_id": str(job.id),
        "renderer_http_status": http_status,
        "media_kit_status": media_kit.status,
        "job_status": job.status,
        "asset_linked": media_kit.storage_asset_id is not None,
        "ok": (
            job.status == ExternalJobReference.Status.FAILED
            and media_kit.status != MediaKit.Status.GENERATED
            and media_kit.storage_asset_id is None
        ),
    }


def main() -> int:
    if not TOKEN:
        print(json.dumps({"error": "INTERNAL_API_TOKEN not set"}))
        return 2

    seed_rbac()
    suffix = uuid.uuid4().hex[:8]
    owner = User.objects.create_user(
        email=f"e2e-{suffix}@example.com", password="e2e-pass-12345"
    )
    workspace = create_workspace(user=owner, name=f"E2E WS {suffix}")

    results = []
    for runner in (
        run_content,
        run_report,
        run_report_failed,
        run_media_kit,
        run_media_kit_failed,
    ):
        try:
            results.append(runner(owner, workspace))
        except Exception as exc:  # noqa: BLE001
            results.append({"scenario": runner.__name__, "error": repr(exc), "ok": False})

    print(json.dumps({"results": results}, indent=2))
    return 0 if all(r.get("ok") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
