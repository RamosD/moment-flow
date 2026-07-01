"""End-to-end integration tests: product API → external job → callback → effects.

These drive the *real* HTTP surface (product endpoints + the internal callback
endpoint) to validate the full orchestration cycle for Content Packs, Reports and
Media Kits, plus callback security and the dry-run / disabled switches. No FastAPI
or renderer is involved — submission runs in dry-run and callbacks are simulated.
"""

import uuid
from decimal import Decimal

import pytest

from apps.audit.models import AuditEvent
from apps.billing.models import CreditLedgerEntry, UsageEvent
from apps.billing.services import get_credit_balance, grant_credits
from apps.content.models import ContentOutput, ContentPack, ContentPackRequest
from apps.content.seeds import seed_content
from apps.core.models import Asset
from apps.integrations_bridge.models import ExternalJobReference
from apps.notifications.models import Notification
from apps.reports.models import MediaKit, Report
from tests import factories
from tests.conftest import ws_header

CALLBACK_URL = "/api/v1/internal/jobs/callback/"
REQUESTS_URL = "/api/v1/content-pack-requests/"
REPORTS_URL = "/api/v1/reports/"
MEDIA_KITS_URL = "/api/v1/media-kits/"
TOKEN = "internal-secret-token"


@pytest.fixture(autouse=True)
def _token(settings):
    settings.INTERNAL_API_TOKEN = TOKEN


def _internal(token=TOKEN):
    return {"HTTP_X_INTERNAL_TOKEN": token}


def _bootstrap(add_member):
    """A seeded workspace with an owner and a catalogue graph."""
    seed_content()
    workspace = factories.WorkspaceFactory()
    owner = factories.UserFactory()
    add_member(workspace, owner, "owner")
    artist = factories.ArtistFactory(workspace=workspace)
    track = factories.TrackFactory(artist=artist)
    campaign = factories.CampaignFactory(artist=artist)
    return workspace, owner, artist, track, campaign


def _paid_pack(cost="5"):
    return factories.ContentPackFactory(
        workspace=None, status=ContentPack.Status.ACTIVE, metadata={"credit_cost": cost}
    )


def _output(output_type="post", template_key="system_post", status="completed"):
    data = {
        "output_type": output_type, "format": "png", "status": status,
        "title": output_type, "required": True, "template_key": template_key,
    }
    if status == "completed":
        data["asset"] = {
            "storage_provider": "s3", "bucket": "b",
            "storage_key": f"k/{output_type}.png", "file_name": f"{output_type}.png",
            "mime_type": "image/png", "file_size_bytes": 1000, "checksum": "abc",
        }
    return data


def _asset_block():
    return {
        "title": "Out", "format": "pdf", "storage_provider": "s3", "bucket": "b",
        "storage_key": "k/out.pdf", "file_name": "out.pdf",
        "mime_type": "application/pdf", "file_size_bytes": 2000, "checksum": "abc",
    }


def _create_content_request(auth_client, owner, workspace, campaign, pack):
    resp = auth_client(owner).post(
        REQUESTS_URL,
        {"campaign": str(campaign.id), "content_pack": str(pack.id)},
        format="json", **ws_header(workspace),
    )
    assert resp.status_code == 201, resp.data
    request = ContentPackRequest.objects.get(id=resp.data["id"])
    job = ExternalJobReference.objects.get(
        related_entity_type="content_pack_request", related_entity_id=str(request.id)
    )
    return request, job


# --------------------------------------------------------------------------- #
# Content Pack — full lifecycle
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestContentPackE2E:
    def test_completed_lifecycle_and_idempotency(self, auth_client, api_client, add_member):
        workspace, owner, _artist, _track, campaign = _bootstrap(add_member)
        pack = _paid_pack("5")
        grant_credits(workspace, Decimal("10"), reason="seed")

        request, job = _create_content_request(auth_client, owner, workspace, campaign, pack)
        # The job was opened (dry-run → submitted) and credits reserved.
        assert job.job_type == ExternalJobReference.JobType.CONTENT_GENERATION
        assert job.status == ExternalJobReference.Status.SUBMITTED
        assert get_credit_balance(workspace) == Decimal("5")
        assert UsageEvent.objects.filter(
            workspace=workspace, event_type=UsageEvent.EventType.CONTENT_PACK_REQUESTED
        ).exists()

        payload = {
            "job_id": str(job.id), "workspace_id": str(workspace.id),
            "status": "completed",
            "entity": {"type": "content_pack_request", "id": str(request.id)},
            "result": {"outputs": [_output("post"), _output("story", "system_story")]},
        }
        resp = api_client.post(CALLBACK_URL, payload, format="json", **_internal())
        assert resp.status_code == 200

        request.refresh_from_db()
        assert request.status == ContentPackRequest.Status.COMPLETED
        assert request.outputs.count() == 2
        assert all(o.storage_asset_id for o in request.outputs.all())
        assert Asset.objects.filter(
            workspace=workspace, asset_type=Asset.AssetType.GENERATED_OUTPUT
        ).count() == 2
        # Reserved credits settled (available unchanged at 5).
        assert get_credit_balance(workspace) == Decimal("5")
        assert CreditLedgerEntry.objects.filter(
            workspace=workspace, transaction_type=CreditLedgerEntry.TransactionType.CONSUME
        ).exists()
        assert UsageEvent.objects.filter(
            workspace=workspace, event_type=UsageEvent.EventType.CONTENT_PACK_GENERATED
        ).count() == 1
        assert Notification.objects.filter(
            workspace=workspace, notification_type=Notification.NotificationType.CONTENT_READY
        ).count() == 1
        assert AuditEvent.objects.filter(action="content_pack.completed").count() == 1

        # Replaying the callback changes nothing (idempotent).
        api_client.post(CALLBACK_URL, payload, format="json", **_internal())
        assert ContentOutput.objects.filter(content_pack_request=request).count() == 2
        assert Asset.objects.filter(workspace=workspace).count() == 2
        assert Notification.objects.filter(
            workspace=workspace, notification_type=Notification.NotificationType.CONTENT_READY
        ).count() == 1
        assert UsageEvent.objects.filter(
            workspace=workspace, event_type=UsageEvent.EventType.CONTENT_PACK_GENERATED
        ).count() == 1
        assert get_credit_balance(workspace) == Decimal("5")

    def test_failed_releases_credits(self, auth_client, api_client, add_member):
        workspace, owner, _artist, _track, campaign = _bootstrap(add_member)
        pack = _paid_pack("5")
        grant_credits(workspace, Decimal("10"), reason="seed")

        request, job = _create_content_request(auth_client, owner, workspace, campaign, pack)
        assert get_credit_balance(workspace) == Decimal("5")  # reserved

        resp = api_client.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "workspace_id": str(workspace.id), "status": "failed",
             "error": {"code": "renderer_error", "message": "boom"}},
            format="json", **_internal(),
        )
        assert resp.status_code == 200
        request.refresh_from_db()
        assert request.status == ContentPackRequest.Status.FAILED
        # Reserved credits released back.
        assert get_credit_balance(workspace) == Decimal("10")
        assert CreditLedgerEntry.objects.filter(
            workspace=workspace, transaction_type=CreditLedgerEntry.TransactionType.RELEASE
        ).exists()
        assert AuditEvent.objects.filter(action="content_pack.failed").count() == 1
        assert Notification.objects.filter(
            workspace=workspace, related_entity_id=str(request.id)
        ).exists()


# --------------------------------------------------------------------------- #
# Report — full lifecycle
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestReportE2E:
    def test_completed_lifecycle_and_idempotency(self, auth_client, api_client, add_member):
        workspace, owner, _a, _t, _c = _bootstrap(add_member)
        resp = auth_client(owner).post(
            REPORTS_URL, {"report_type": "monthly_report", "title": "June"},
            format="json", **ws_header(workspace),
        )
        assert resp.status_code == 201
        report = Report.objects.get(id=resp.data["id"])
        job = ExternalJobReference.objects.get(
            related_entity_type="report", related_entity_id=str(report.id)
        )
        assert job.job_type == ExternalJobReference.JobType.REPORT_GENERATION

        payload = {
            "job_id": str(job.id), "workspace_id": str(workspace.id), "status": "completed",
            "entity": {"type": "report", "id": str(report.id)},
            "result": {"asset": _asset_block()},
        }
        resp = api_client.post(CALLBACK_URL, payload, format="json", **_internal())
        assert resp.status_code == 200
        report.refresh_from_db()
        assert report.status == Report.Status.COMPLETED
        assert report.storage_asset_id is not None
        assert Asset.objects.filter(
            workspace=workspace, asset_type=Asset.AssetType.REPORT_PDF
        ).count() == 1
        assert Notification.objects.filter(
            workspace=workspace, notification_type=Notification.NotificationType.REPORT_READY
        ).count() == 1
        assert AuditEvent.objects.filter(action="report.completed").count() == 1

        # Idempotent replay.
        api_client.post(CALLBACK_URL, payload, format="json", **_internal())
        assert Asset.objects.filter(
            workspace=workspace, asset_type=Asset.AssetType.REPORT_PDF
        ).count() == 1


# --------------------------------------------------------------------------- #
# Media Kit — full lifecycle
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestMediaKitE2E:
    def test_completed_lifecycle(self, auth_client, api_client, add_member):
        workspace, owner, artist, _t, _c = _bootstrap(add_member)
        resp = auth_client(owner).post(
            MEDIA_KITS_URL, {"artist": str(artist.id), "title": "Kit"},
            format="json", **ws_header(workspace),
        )
        assert resp.status_code == 201
        media_kit = MediaKit.objects.get(id=resp.data["id"])
        job = ExternalJobReference.objects.get(
            related_entity_type="media_kit", related_entity_id=str(media_kit.id)
        )
        assert job.job_type == ExternalJobReference.JobType.MEDIA_KIT_GENERATION

        resp = api_client.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "workspace_id": str(workspace.id), "status": "completed",
             "entity": {"type": "media_kit", "id": str(media_kit.id)},
             "result": {"asset": _asset_block()}},
            format="json", **_internal(),
        )
        assert resp.status_code == 200
        media_kit.refresh_from_db()
        assert media_kit.status == MediaKit.Status.GENERATED
        assert media_kit.storage_asset_id is not None
        assert Asset.objects.filter(
            workspace=workspace, asset_type=Asset.AssetType.MEDIA_KIT_ASSET
        ).count() == 1
        assert Notification.objects.filter(
            workspace=workspace,
            notification_type=Notification.NotificationType.MEDIA_KIT_READY,
        ).count() == 1
        assert AuditEvent.objects.filter(action="media_kit.completed").count() == 1


# --------------------------------------------------------------------------- #
# Callback security (end-to-end)
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestCallbackSecurityE2E:
    @pytest.fixture
    def job_for(self, auth_client, add_member):
        workspace, owner, _a, _t, campaign = _bootstrap(add_member)
        pack = ContentPack.objects.get(pack_key="release_pack")
        request, job = _create_content_request(auth_client, owner, workspace, campaign, pack)
        return workspace, request, job

    def test_no_token(self, api_client, job_for):
        workspace, request, job = job_for
        resp = api_client.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "workspace_id": str(workspace.id), "status": "completed"},
            format="json",
        )
        assert resp.status_code == 403

    def test_wrong_token(self, api_client, job_for):
        workspace, request, job = job_for
        resp = api_client.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "workspace_id": str(workspace.id), "status": "completed"},
            format="json", **_internal("nope"),
        )
        assert resp.status_code == 403

    def test_workspace_mismatch(self, api_client, job_for):
        _ws, request, job = job_for
        resp = api_client.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "workspace_id": str(uuid.uuid4()), "status": "completed"},
            format="json", **_internal(),
        )
        assert resp.status_code == 400

    def test_entity_mismatch(self, api_client, job_for):
        workspace, request, job = job_for
        resp = api_client.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "workspace_id": str(workspace.id), "status": "completed",
             "entity": {"type": "report", "id": str(request.id)}},
            format="json", **_internal(),
        )
        assert resp.status_code == 400

    def test_invalid_payload(self, api_client, job_for):
        workspace, request, job = job_for
        resp = api_client.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "workspace_id": str(workspace.id), "status": "bogus"},
            format="json", **_internal(),
        )
        assert resp.status_code == 400

    def test_terminal_job_conflict(self, api_client, job_for):
        workspace, request, job = job_for
        ok = {"job_id": str(job.id), "workspace_id": str(workspace.id), "status": "completed",
              "result": {"outputs": []}}
        assert api_client.post(CALLBACK_URL, ok, format="json", **_internal()).status_code == 200
        conflict = {"job_id": str(job.id), "workspace_id": str(workspace.id), "status": "failed"}
        resp = api_client.post(CALLBACK_URL, conflict, format="json", **_internal())
        assert resp.status_code == 409


# --------------------------------------------------------------------------- #
# Dry-run / disabled switches
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestSubmissionSwitches:
    def test_dry_run_marks_submitted(self, settings, auth_client, add_member):
        settings.EXTERNAL_JOBS_ENABLED = True
        settings.EXTERNAL_JOBS_DRY_RUN = True
        workspace, owner, _a, _t, campaign = _bootstrap(add_member)
        pack = ContentPack.objects.get(pack_key="release_pack")
        _request, job = _create_content_request(auth_client, owner, workspace, campaign, pack)
        assert job.status == ExternalJobReference.Status.SUBMITTED
        assert job.response_payload == {"dry_run": True}

    def test_disabled_keeps_queued(self, settings, auth_client, add_member):
        settings.EXTERNAL_JOBS_ENABLED = False
        workspace, owner, _a, _t, campaign = _bootstrap(add_member)
        pack = ContentPack.objects.get(pack_key="release_pack")
        _request, job = _create_content_request(auth_client, owner, workspace, campaign, pack)
        assert job.status == ExternalJobReference.Status.QUEUED
