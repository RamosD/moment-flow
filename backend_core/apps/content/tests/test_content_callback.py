"""End-to-end tests for the content_generation callback (Prompt 05).

Drives the real internal callback endpoint: request → job (dry-run) → callback →
outputs / assets / credits / usage / notification / audit.
"""

import uuid
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.billing.models import CreditLedgerEntry, UsageEvent
from apps.billing.services import get_credit_balance, grant_credits
from apps.content.models import ContentOutput, ContentPack, ContentPackRequest
from apps.content.services import create_content_pack_request
from apps.core.models import Asset
from apps.integrations_bridge.models import ExternalJobReference
from apps.notifications.models import Notification

CALLBACK_URL = "/api/v1/internal/jobs/callback/"
TOKEN = "internal-secret-token"


@pytest.fixture(autouse=True)
def _token(settings):
    settings.INTERNAL_API_TOKEN = TOKEN


@pytest.fixture
def api():
    return APIClient()


def _auth(token=TOKEN):
    return {"HTTP_X_INTERNAL_TOKEN": token}


def _paid_pack():
    return ContentPack.objects.create(
        pack_key="paid_pack",
        name="Paid Pack",
        pack_type=ContentPack.PackType.RELEASE_PACK,
        status=ContentPack.Status.ACTIVE,
        workspace=None,
        metadata={"credit_cost": "5"},
    )


def _make(workspace, owner, campaign, pack=None):
    request = create_content_pack_request(
        workspace=workspace,
        requested_by=owner,
        campaign=campaign,
        content_pack=pack or ContentPack.objects.get(pack_key="release_pack"),
    )
    job = ExternalJobReference.objects.get(
        related_entity_id=str(request.id),
        job_type=ExternalJobReference.JobType.CONTENT_GENERATION,
    )
    return request, job


def _output(output_type="post", template_key="system_post", status="completed",
            with_asset=True, required=True):
    data = {
        "output_type": output_type,
        "format": "png",
        "status": status,
        "title": f"{output_type} title",
        "caption": "caption",
        "cta": "Listen now",
        "template_key": template_key,
        "required": required,
        "metadata": {"k": "v"},
    }
    if with_asset and status == "completed":
        data["asset"] = {
            "storage_provider": "s3",
            "bucket": "bucket",
            "storage_key": f"outputs/{output_type}.png",
            "file_name": f"{output_type}.png",
            "mime_type": "image/png",
            "file_size_bytes": 12345,
            "width": 1080,
            "height": 1080,
            "checksum": "deadbeef",
        }
    return data


def _completed(job, workspace, request, outputs, status="completed"):
    return {
        "job_id": str(job.id),
        "workspace_id": str(workspace.id),
        "status": status,
        "entity": {"type": "content_pack_request", "id": str(request.id)},
        "result": {"outputs": outputs},
    }


@pytest.mark.django_db
class TestCompleted:
    def test_creates_outputs_assets_notification_audit(self, api, workspace, owner, make_campaign):
        request, job = _make(workspace, owner, make_campaign(workspace))
        outputs = [_output("post", "system_post"), _output("story", "system_story")]
        resp = api.post(
            CALLBACK_URL, _completed(job, workspace, request, outputs),
            format="json", **_auth(),
        )
        assert resp.status_code == 200

        request.refresh_from_db()
        job.refresh_from_db()
        assert request.status == ContentPackRequest.Status.COMPLETED
        assert request.completed_at is not None
        assert job.status == ExternalJobReference.Status.COMPLETED
        assert request.outputs.count() == 2
        assert request.outputs.filter(status=ContentOutput.Status.COMPLETED).count() == 2
        assert all(o.storage_asset_id is not None for o in request.outputs.all())
        assert Asset.objects.filter(
            workspace=workspace, asset_type=Asset.AssetType.GENERATED_OUTPUT
        ).count() == 2
        assert Notification.objects.filter(
            workspace=workspace,
            notification_type=Notification.NotificationType.CONTENT_READY,
        ).count() == 1
        assert AuditEvent.objects.filter(action="content_pack.completed").count() == 1
        assert UsageEvent.objects.filter(
            workspace=workspace, event_type=UsageEvent.EventType.CONTENT_PACK_GENERATED
        ).count() == 1

    def test_consumes_reserved_credits(self, api, workspace, owner, make_campaign):
        grant_credits(workspace, Decimal("10"), reason="seed")
        request, job = _make(workspace, owner, make_campaign(workspace), pack=_paid_pack())
        assert get_credit_balance(workspace) == Decimal("5")  # 10 - 5 reserved

        api.post(
            CALLBACK_URL, _completed(job, workspace, request, [_output()]),
            format="json", **_auth(),
        )
        # settle_reserved consume → available stays 5 (credits already left at reserve)
        assert get_credit_balance(workspace) == Decimal("5")
        assert CreditLedgerEntry.objects.filter(
            workspace=workspace,
            transaction_type=CreditLedgerEntry.TransactionType.CONSUME,
        ).exists()


@pytest.mark.django_db
class TestFailed:
    def test_failed_releases_credits_and_notifies(self, api, workspace, owner, make_campaign):
        grant_credits(workspace, Decimal("10"), reason="seed")
        request, job = _make(workspace, owner, make_campaign(workspace), pack=_paid_pack())
        assert get_credit_balance(workspace) == Decimal("5")

        resp = api.post(
            CALLBACK_URL,
            {
                "job_id": str(job.id),
                "workspace_id": str(workspace.id),
                "status": "failed",
                "error": {"code": "renderer_error", "message": "boom"},
            },
            format="json", **_auth(),
        )
        assert resp.status_code == 200

        request.refresh_from_db()
        job.refresh_from_db()
        assert request.status == ContentPackRequest.Status.FAILED
        assert request.error_message == "boom"
        assert job.status == ExternalJobReference.Status.FAILED
        # Released back to full balance.
        assert get_credit_balance(workspace) == Decimal("10")
        assert CreditLedgerEntry.objects.filter(
            workspace=workspace,
            transaction_type=CreditLedgerEntry.TransactionType.RELEASE,
        ).exists()
        assert Notification.objects.filter(
            workspace=workspace, related_entity_id=str(request.id)
        ).exists()
        assert AuditEvent.objects.filter(action="content_pack.failed").count() == 1


@pytest.mark.django_db
class TestIdempotency:
    def test_repeated_completed_no_duplicates(self, api, workspace, owner, make_campaign):
        request, job = _make(workspace, owner, make_campaign(workspace))
        payload = _completed(job, workspace, request, [_output()])
        first = api.post(CALLBACK_URL, payload, format="json", **_auth())
        second = api.post(CALLBACK_URL, payload, format="json", **_auth())
        assert first.status_code == 200
        assert second.status_code == 200

        assert request.outputs.count() == 1
        assert Asset.objects.filter(workspace=workspace).count() == 1
        assert Notification.objects.filter(
            workspace=workspace,
            notification_type=Notification.NotificationType.CONTENT_READY,
        ).count() == 1
        assert UsageEvent.objects.filter(
            workspace=workspace, event_type=UsageEvent.EventType.CONTENT_PACK_GENERATED
        ).count() == 1


@pytest.mark.django_db
class TestPartiallyCompleted:
    def test_mixed_outputs(self, api, workspace, owner, make_campaign):
        request, job = _make(workspace, owner, make_campaign(workspace))
        outputs = [
            _output("post", "system_post", status="completed"),
            _output("story", "system_story", status="failed", with_asset=False),
        ]
        resp = api.post(
            CALLBACK_URL,
            _completed(job, workspace, request, outputs, status="partially_completed"),
            format="json", **_auth(),
        )
        assert resp.status_code == 200

        request.refresh_from_db()
        job.refresh_from_db()
        assert request.status == ContentPackRequest.Status.PARTIALLY_COMPLETED
        assert job.status == ExternalJobReference.Status.PARTIALLY_COMPLETED
        assert request.outputs.filter(status=ContentOutput.Status.COMPLETED).count() == 1
        assert request.outputs.filter(status=ContentOutput.Status.FAILED).count() == 1
        # Only the completed output got an asset.
        assert Asset.objects.filter(workspace=workspace).count() == 1
        assert Notification.objects.filter(
            workspace=workspace,
            notification_type=Notification.NotificationType.CONTENT_READY,
        ).count() == 1

    def test_partial_consumes_when_required_succeeds(self, api, workspace, owner, make_campaign):
        grant_credits(workspace, Decimal("10"), reason="seed")
        request, job = _make(workspace, owner, make_campaign(workspace), pack=_paid_pack())
        outputs = [
            _output("post", "system_post", status="completed", required=True),
            _output("story", "system_story", status="failed", with_asset=False, required=True),
        ]
        api.post(
            CALLBACK_URL,
            _completed(job, workspace, request, outputs, status="partially_completed"),
            format="json", **_auth(),
        )
        # At least one required output succeeded → consume.
        assert get_credit_balance(workspace) == Decimal("5")
        assert CreditLedgerEntry.objects.filter(
            workspace=workspace,
            transaction_type=CreditLedgerEntry.TransactionType.CONSUME,
        ).exists()

    def test_partial_releases_when_all_required_fail(self, api, workspace, owner, make_campaign):
        grant_credits(workspace, Decimal("10"), reason="seed")
        request, job = _make(workspace, owner, make_campaign(workspace), pack=_paid_pack())
        outputs = [
            _output("post", "system_post", status="failed", with_asset=False, required=True),
        ]
        api.post(
            CALLBACK_URL,
            _completed(job, workspace, request, outputs, status="partially_completed"),
            format="json", **_auth(),
        )
        # No required output succeeded → release.
        assert get_credit_balance(workspace) == Decimal("10")


@pytest.mark.django_db
class TestCallbackRejection:
    def test_wrong_workspace_rejected_no_effects(self, api, workspace, owner, make_campaign):
        request, job = _make(workspace, owner, make_campaign(workspace))
        resp = api.post(
            CALLBACK_URL,
            {
                "job_id": str(job.id),
                "workspace_id": str(uuid.uuid4()),
                "status": "completed",
                "result": {"outputs": [_output()]},
            },
            format="json", **_auth(),
        )
        assert resp.status_code == 400
        request.refresh_from_db()
        assert request.status == ContentPackRequest.Status.QUEUED
        assert request.outputs.count() == 0
        assert Asset.objects.filter(workspace=workspace).count() == 0

    def test_wrong_entity_rejected(self, api, workspace, owner, make_campaign):
        request, job = _make(workspace, owner, make_campaign(workspace))
        resp = api.post(
            CALLBACK_URL,
            {
                "job_id": str(job.id),
                "status": "completed",
                "entity": {"type": "report", "id": str(request.id)},
            },
            format="json", **_auth(),
        )
        assert resp.status_code == 400
        request.refresh_from_db()
        assert request.status == ContentPackRequest.Status.QUEUED
