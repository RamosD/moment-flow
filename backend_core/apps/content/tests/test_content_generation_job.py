"""ContentPackRequest → content_generation ExternalJobReference (Prompt 04)."""

import json
from decimal import Decimal

import pytest

import apps.integrations_bridge.services as bridge
from apps.audit.models import AuditEvent
from apps.billing.services import get_credit_balance, grant_credits
from apps.content.models import ContentPack, ContentPackRequest
from apps.content.payloads import build_content_generation_payload
from apps.content.services import (
    _submit_content_generation_job,
    create_content_pack_request,
)
from apps.integrations_bridge.clients import InternalServiceUnavailable
from apps.integrations_bridge.models import ExternalJobReference

CONTENT_GENERATION = ExternalJobReference.JobType.CONTENT_GENERATION


def _release_pack():
    return ContentPack.objects.get(pack_key="release_pack")


def _make_request(workspace, owner, campaign, pack=None):
    return create_content_pack_request(
        workspace=workspace,
        requested_by=owner,
        campaign=campaign,
        content_pack=pack or _release_pack(),
    )


@pytest.mark.django_db
class TestRequestCreatesJob:
    def test_request_is_created_and_queued(self, workspace, owner, make_campaign):
        request = _make_request(workspace, owner, make_campaign(workspace))
        assert ContentPackRequest.objects.filter(id=request.id).exists()
        assert request.status == ContentPackRequest.Status.QUEUED

    def test_request_creates_content_generation_job(self, workspace, owner, make_campaign):
        request = _make_request(workspace, owner, make_campaign(workspace))
        job = ExternalJobReference.objects.get(
            related_entity_type="content_pack_request", related_entity_id=str(request.id)
        )
        assert job.job_type == CONTENT_GENERATION
        assert job.provider == "content_renderer"  # resolved via the registry
        assert job.idempotency_key == f"content_generation:{request.id}"
        assert job.workspace_id == workspace.id
        # Request is linked back to the job.
        assert request.metadata.get("external_job_id") == str(job.id)

    def test_audit_job_submitted(self, workspace, owner, make_campaign):
        request = _make_request(workspace, owner, make_campaign(workspace))
        assert AuditEvent.objects.filter(
            action="content_pack.job_submitted",
            workspace=workspace,
            entity_id=str(request.id),
        ).exists()


@pytest.mark.django_db
class TestPayload:
    def test_payload_is_json_serializable(self, workspace, owner, make_campaign):
        request = _make_request(workspace, owner, make_campaign(workspace))
        payload = build_content_generation_payload(request)
        # Must not raise.
        json.dumps(payload)

    def test_payload_contains_expected_templates(self, workspace, owner, make_campaign):
        request = _make_request(workspace, owner, make_campaign(workspace))
        payload = build_content_generation_payload(request)
        keys = {t["template_key"] for t in payload["templates"]}
        assert keys == {"system_post", "system_story", "system_thumbnail"}
        assert len(payload["expected_outputs"]) == 3
        assert payload["entity"] == {
            "type": "content_pack_request", "id": str(request.id)
        }
        assert payload["content_pack"]["pack_key"] == "release_pack"

    def test_payload_has_no_secret_fields(self, workspace, owner, make_campaign):
        request = _make_request(workspace, owner, make_campaign(workspace))
        text = json.dumps(build_content_generation_payload(request)).lower()
        assert "token" not in text
        assert "password" not in text

    def test_stored_envelope_has_transport_fields(self, workspace, owner, make_campaign):
        request = _make_request(workspace, owner, make_campaign(workspace))
        job = ExternalJobReference.objects.get(related_entity_id=str(request.id))
        envelope = job.request_payload
        for key in (
            "job_id", "request_id", "workspace_id", "callback_url",
            "entity", "payload_version", "payload",
        ):
            assert key in envelope, key
        assert envelope["entity"]["type"] == "content_pack_request"
        assert envelope["payload"]["content_pack"]["pack_key"] == "release_pack"
        assert envelope["callback_url"].endswith("/api/v1/internal/jobs/callback/")


@pytest.mark.django_db
class TestDryRunAndIdempotency:
    def test_dry_run_marks_job_submitted_without_http(
        self, settings, workspace, owner, make_campaign
    ):
        # dry-run is the default (root conftest); be explicit anyway.
        settings.EXTERNAL_JOBS_ENABLED = True
        settings.EXTERNAL_JOBS_DRY_RUN = True
        request = _make_request(workspace, owner, make_campaign(workspace))
        job = ExternalJobReference.objects.get(related_entity_id=str(request.id))
        assert job.status == ExternalJobReference.Status.SUBMITTED
        assert job.response_payload == {"dry_run": True}

    def test_idempotency_no_duplicate_job(self, workspace, owner, make_campaign):
        request = _make_request(workspace, owner, make_campaign(workspace))
        # Re-submitting the same request must not create a second job.
        _submit_content_generation_job(request, owner)
        assert ExternalJobReference.objects.filter(
            idempotency_key=f"content_generation:{request.id}"
        ).count() == 1

    def test_disabled_keeps_job_queued(self, settings, workspace, owner, make_campaign):
        settings.EXTERNAL_JOBS_ENABLED = False
        request = _make_request(workspace, owner, make_campaign(workspace))
        job = ExternalJobReference.objects.get(related_entity_id=str(request.id))
        assert job.status == ExternalJobReference.Status.QUEUED


@pytest.mark.django_db
class TestSubmissionFailureTraceable:
    def test_client_failure_marks_job_failed_and_links(
        self, settings, monkeypatch, workspace, owner, make_campaign
    ):
        settings.EXTERNAL_JOBS_ENABLED = True
        settings.EXTERNAL_JOBS_DRY_RUN = False
        settings.CONTENT_RENDERER_BASE_URL = "http://renderer:8002"

        class DownClient:
            def __init__(self, *a, **k):
                pass

            def post_json(self, *a, **k):
                raise InternalServiceUnavailable("renderer down")

        monkeypatch.setattr(bridge, "InternalServiceClient", DownClient)

        request = _make_request(workspace, owner, make_campaign(workspace))
        job = ExternalJobReference.objects.get(related_entity_id=str(request.id))
        assert job.status == ExternalJobReference.Status.FAILED
        assert "renderer down" in job.error_message
        # Request preserved and linked — failure is traceable.
        assert ContentPackRequest.objects.filter(id=request.id).exists()
        assert request.metadata.get("external_job_id") == str(job.id)
        # STG-PRE-007: a submission-time failure (renderer never reached, so no
        # callback will ever arrive) must not leave the request stuck "queued".
        request.refresh_from_db()
        assert request.status == ContentPackRequest.Status.FAILED
        assert "renderer down" in request.error_message

    def test_unexpected_error_preserves_request(
        self, monkeypatch, workspace, owner, make_campaign
    ):
        def boom(**kwargs):
            raise RuntimeError("kaboom")

        monkeypatch.setattr(bridge, "create_and_submit_external_job", boom)
        request = _make_request(workspace, owner, make_campaign(workspace))
        # Request survives; the error is recorded; no job leaked.
        assert ContentPackRequest.objects.filter(id=request.id).exists()
        assert "kaboom" in request.metadata.get("job_submission_error", "")
        assert not ExternalJobReference.objects.filter(
            related_entity_id=str(request.id)
        ).exists()


@pytest.mark.django_db
class TestBillingAndIsolation:
    def test_credits_still_reserved(self, workspace, owner, make_campaign):
        pack = ContentPack.objects.create(
            pack_key="paid_pack",
            name="Paid Pack",
            pack_type=ContentPack.PackType.RELEASE_PACK,
            status=ContentPack.Status.ACTIVE,
            workspace=None,
            metadata={"credit_cost": "5"},
        )
        grant_credits(workspace, Decimal("10"), reason="test")
        _make_request(workspace, owner, make_campaign(workspace), pack=pack)
        # 10 granted - 5 reserved = 5 available.
        assert get_credit_balance(workspace) == Decimal("5")

    def test_job_belongs_to_request_workspace(self, workspace, owner, make_campaign):
        request = _make_request(workspace, owner, make_campaign(workspace))
        job = ExternalJobReference.objects.get(related_entity_id=str(request.id))
        assert job.workspace_id == workspace.id
        payload = build_content_generation_payload(request)
        assert payload["workspace_id"] == str(workspace.id)
