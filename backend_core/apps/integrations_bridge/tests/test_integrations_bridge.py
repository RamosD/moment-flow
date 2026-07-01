"""ExternalJobReference creation and the token-protected internal callback."""

import pytest

from apps.integrations_bridge.models import ExternalJobReference
from apps.integrations_bridge.services import create_external_job_reference

CALLBACK_URL = "/api/v1/internal/jobs/callback/"
TOKEN = "internal-secret-token"


def _auth(token=TOKEN):
    return {"HTTP_X_INTERNAL_TOKEN": token}


@pytest.fixture
def job(workspace, owner):
    return create_external_job_reference(
        job_type=ExternalJobReference.JobType.REPORT_GENERATION,
        provider=ExternalJobReference.Provider.CONTENT_RENDERER,
        workspace=workspace,
        requested_by=owner,
        external_job_id="ext-123",
        related_entity_type="report",
        related_entity_id="r-1",
    )


@pytest.mark.django_db
class TestCreateExternalJobReference:
    def test_created_as_queued(self, job, workspace):
        assert job.status == ExternalJobReference.Status.QUEUED
        assert job.workspace_id == workspace.id
        assert job.related_entity_type == "report"


@pytest.mark.django_db
class TestCallbackAuth:
    def test_rejects_without_token(self, api_client, job, settings):
        settings.INTERNAL_API_TOKEN = TOKEN
        resp = api_client.post(
            CALLBACK_URL,
            {"job": str(job.id), "status": "completed"},
            format="json",
        )
        assert resp.status_code == 403
        job.refresh_from_db()
        assert job.status == ExternalJobReference.Status.QUEUED

    def test_rejects_wrong_token(self, api_client, job, settings):
        settings.INTERNAL_API_TOKEN = TOKEN
        resp = api_client.post(
            CALLBACK_URL,
            {"job": str(job.id), "status": "completed"},
            format="json",
            **_auth("wrong"),
        )
        assert resp.status_code == 403

    def test_rejects_when_token_not_configured(self, api_client, job, settings):
        settings.INTERNAL_API_TOKEN = ""
        resp = api_client.post(
            CALLBACK_URL,
            {"job": str(job.id), "status": "completed"},
            format="json",
            **_auth("anything"),
        )
        assert resp.status_code == 403


@pytest.mark.django_db
class TestCallbackUpdates:
    def test_valid_token_completes_job(self, api_client, job, settings):
        settings.INTERNAL_API_TOKEN = TOKEN
        resp = api_client.post(
            CALLBACK_URL,
            {"job": str(job.id), "workspace_id": str(job.workspace_id),
             "status": "completed", "metadata": {"pages": 3}},
            format="json",
            **_auth(),
        )
        assert resp.status_code == 200
        job.refresh_from_db()
        assert job.status == ExternalJobReference.Status.COMPLETED
        assert job.completed_at is not None
        assert job.metadata.get("pages") == 3

    def test_failure_sets_error(self, api_client, job, settings):
        settings.INTERNAL_API_TOKEN = TOKEN
        resp = api_client.post(
            CALLBACK_URL,
            {"job": str(job.id), "workspace_id": str(job.workspace_id),
             "status": "failed", "error_message": "boom"},
            format="json",
            **_auth(),
        )
        assert resp.status_code == 200
        job.refresh_from_db()
        assert job.status == ExternalJobReference.Status.FAILED
        assert job.failed_at is not None
        assert job.error_message == "boom"

    def test_resolve_by_external_job_id(self, api_client, job, settings):
        settings.INTERNAL_API_TOKEN = TOKEN
        resp = api_client.post(
            CALLBACK_URL,
            {
                "external_job_id": "ext-123",
                "provider": "content_renderer",
                "workspace_id": str(job.workspace_id),
                "status": "running",
            },
            format="json",
            **_auth(),
        )
        assert resp.status_code == 200
        job.refresh_from_db()
        assert job.status == ExternalJobReference.Status.RUNNING

    def test_terminal_state_cannot_transition(self, api_client, job, settings):
        settings.INTERNAL_API_TOKEN = TOKEN
        from apps.integrations_bridge.services import apply_job_callback

        apply_job_callback(job, status=ExternalJobReference.Status.COMPLETED)
        resp = api_client.post(
            CALLBACK_URL,
            {"job": str(job.id), "workspace_id": str(job.workspace_id),
             "status": "failed"},
            format="json",
            **_auth(),
        )
        assert resp.status_code == 409

    def test_unknown_job_returns_404(self, api_client, settings):
        settings.INTERNAL_API_TOKEN = TOKEN
        import uuid

        resp = api_client.post(
            CALLBACK_URL,
            {"job": str(uuid.uuid4()), "workspace_id": str(uuid.uuid4()),
             "status": "completed"},
            format="json",
            **_auth(),
        )
        assert resp.status_code == 404

    def test_missing_identifier_is_400(self, api_client, settings):
        settings.INTERNAL_API_TOKEN = TOKEN
        resp = api_client.post(
            CALLBACK_URL, {"status": "completed"}, format="json", **_auth()
        )
        assert resp.status_code == 400
