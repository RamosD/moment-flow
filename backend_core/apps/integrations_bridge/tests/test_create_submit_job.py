"""Tests for create_and_submit_external_job, idempotency and retry."""

import pytest

from apps.integrations_bridge import services
from apps.integrations_bridge.clients import (
    InternalClientTimeout,
    InternalHTTPError,
    InternalResponse,
)
from apps.integrations_bridge.models import ExternalJobReference

JOB_TYPE = ExternalJobReference.JobType.CONTENT_GENERATION


# --------------------------------------------------------------------------- #
# Fake internal client
# --------------------------------------------------------------------------- #
class FakeClient:
    """Records the last submission and returns/raises a configured outcome."""

    last = {}

    def __init__(self, base_url, timeout):
        self.base_url = base_url
        self.timeout = timeout

    def post_json(self, path, payload, *, workspace_id, job_id, request_id):
        FakeClient.last = {
            "path": path,
            "payload": payload,
            "workspace_id": workspace_id,
            "job_id": job_id,
            "request_id": request_id,
        }
        return InternalResponse(status_code=200, data={"external_job_id": "ext-77"})


def patch_client(monkeypatch, client_factory):
    monkeypatch.setattr(services, "InternalServiceClient", client_factory)


@pytest.fixture
def enabled_real(settings):
    settings.EXTERNAL_JOBS_ENABLED = True
    settings.EXTERNAL_JOBS_DRY_RUN = False
    settings.CONTENT_RENDERER_BASE_URL = "http://renderer:8002"
    settings.CONTENT_RENDERER_TIMEOUT_SECONDS = 30


def _create(workspace, owner, **kw):
    return services.create_and_submit_external_job(
        workspace=workspace,
        job_type=JOB_TYPE,
        related_entity_type="content_pack_request",
        related_entity_id=kw.pop("entity_id", "cpr-1"),
        requested_by=owner,
        payload=kw.pop("payload", {"x": 1}),
        **kw,
    )


@pytest.mark.django_db
class TestCreate:
    def test_job_created_before_call_and_queued_when_disabled(self, settings, workspace, owner):
        settings.EXTERNAL_JOBS_ENABLED = False
        job, created = _create(workspace, owner)
        assert created is True
        assert job.pk is not None
        assert job.status == ExternalJobReference.Status.QUEUED
        assert job.provider == "content_renderer"  # resolved via registry
        assert job.request_id
        assert job.request_payload["payload_version"] == "1.0"
        assert job.request_payload["callback_url"].endswith(
            "/api/v1/internal/jobs/callback/"
        )

    def test_dry_run_marks_submitted_without_calling(self, settings, workspace, owner, monkeypatch):
        settings.EXTERNAL_JOBS_ENABLED = True
        settings.EXTERNAL_JOBS_DRY_RUN = True

        def _boom(*a, **k):
            raise AssertionError("client must not be built in dry-run")

        patch_client(monkeypatch, _boom)
        job, created = _create(workspace, owner)
        assert created is True
        assert job.status == ExternalJobReference.Status.SUBMITTED
        assert job.submitted_at is not None
        assert job.response_payload == {"dry_run": True}

    def test_real_submission_with_mocked_client(self, enabled_real, workspace, owner, monkeypatch):
        patch_client(monkeypatch, FakeClient)
        job, created = _create(workspace, owner)
        assert job.status == ExternalJobReference.Status.SUBMITTED
        assert job.external_job_id == "ext-77"
        assert job.response_payload == {"external_job_id": "ext-77"}
        # The mandatory ids reached the client.
        assert FakeClient.last["job_id"] == job.id
        assert FakeClient.last["request_id"] == job.request_id
        assert FakeClient.last["workspace_id"] == workspace.id

    def test_explicit_request_id_is_reused_not_generated(self, settings, workspace, owner):
        """STG-PRE-005: an explicit request_id (the caller's correlation id)
        becomes the job's own request_id instead of a freshly generated one."""
        settings.EXTERNAL_JOBS_ENABLED = False
        job, _created = _create(workspace, owner, request_id="corr-abc123")
        assert job.request_id == "corr-abc123"

    def test_request_id_still_generated_when_omitted(self, settings, workspace, owner):
        """Backward compatible: callers that don't pass request_id (retries,
        management commands) keep getting a freshly generated one."""
        settings.EXTERNAL_JOBS_ENABLED = False
        job, _created = _create(workspace, owner)
        assert job.request_id  # non-empty
        job2, _created2 = _create(workspace, owner, entity_id="cpr-2")
        assert job2.request_id != job.request_id

    def test_explicit_request_id_reaches_the_external_client(
        self, enabled_real, workspace, owner, monkeypatch
    ):
        patch_client(monkeypatch, FakeClient)
        job, _created = _create(workspace, owner, request_id="corr-xyz789")
        assert job.request_id == "corr-xyz789"
        assert FakeClient.last["request_id"] == "corr-xyz789"
        assert job.request_payload["request_id"] == "corr-xyz789"

    def test_timeout_marks_timeout_status(self, enabled_real, workspace, owner, monkeypatch):
        class TimeoutClient(FakeClient):
            def post_json(self, *a, **k):
                raise InternalClientTimeout("timed out")

        patch_client(monkeypatch, TimeoutClient)
        job, _ = _create(workspace, owner)
        assert job.status == ExternalJobReference.Status.TIMEOUT
        assert "timed out" in job.error_message
        # Job persisted despite the failure.
        assert ExternalJobReference.objects.filter(pk=job.pk).exists()

    def test_http_error_marks_failed_and_traceable(
        self, enabled_real, workspace, owner, monkeypatch
    ):
        class ErrClient(FakeClient):
            def post_json(self, *a, **k):
                raise InternalHTTPError(500, body='{"detail": "renderer down"}')

        patch_client(monkeypatch, ErrClient)
        job, _ = _create(workspace, owner)
        assert job.status == ExternalJobReference.Status.FAILED
        assert job.failed_at is not None
        assert job.response_payload.get("error")


@pytest.mark.django_db
class TestIdempotency:
    def test_repeated_request_reuses_active_job(self, settings, workspace, owner):
        settings.EXTERNAL_JOBS_ENABLED = False  # stays queued (non-terminal)
        job1, created1 = _create(workspace, owner, entity_id="cpr-9")
        job2, created2 = _create(workspace, owner, entity_id="cpr-9")
        assert created1 is True
        assert created2 is False
        assert job1.id == job2.id
        assert (
            ExternalJobReference.objects.filter(
                idempotency_key="content_generation:cpr-9"
            ).count()
            == 1
        )

    def test_custom_idempotency_key_respected(self, settings, workspace, owner):
        settings.EXTERNAL_JOBS_ENABLED = False
        job, _ = _create(workspace, owner, idempotency_key="custom:abc")
        assert job.idempotency_key == "custom:abc"


@pytest.mark.django_db
class TestRetry:
    def test_retry_only_from_retryable_state(self, settings, workspace, owner):
        settings.EXTERNAL_JOBS_ENABLED = False
        job, _ = _create(workspace, owner)  # queued (non-retryable)
        with pytest.raises(services.RetryNotAllowed):
            services.retry_external_job(job, requested_by=owner)

    def test_retry_creates_new_job_without_overwriting(self, settings, workspace, owner):
        settings.EXTERNAL_JOBS_ENABLED = True
        settings.EXTERNAL_JOBS_DRY_RUN = True
        job, _ = _create(workspace, owner)
        # Force a retryable terminal state.
        job.status = ExternalJobReference.Status.FAILED
        job.save(update_fields=["status"])

        new_job = services.retry_external_job(job, requested_by=owner)
        assert new_job.id != job.id
        assert new_job.retry_count == 1
        assert new_job.metadata.get("retried_from") == str(job.id)
        # Old job is preserved exactly.
        job.refresh_from_db()
        assert job.status == ExternalJobReference.Status.FAILED
        assert ExternalJobReference.objects.filter(
            idempotency_key=job.idempotency_key
        ).count() == 2


@pytest.mark.django_db
class TestAuditAndQueryset:
    def test_submission_creates_audit_event(self, settings, workspace, owner):
        settings.EXTERNAL_JOBS_ENABLED = True
        settings.EXTERNAL_JOBS_DRY_RUN = True
        from apps.audit.models import AuditEvent

        job, _ = _create(workspace, owner)
        assert AuditEvent.objects.filter(
            action="external_job.submitted", workspace=workspace
        ).exists()
