"""Tests for the normalized callback, the dispatcher and callback idempotency."""

import uuid

import pytest

from apps.audit.models import AuditEvent
from apps.integrations_bridge.models import ExternalJobReference
from apps.integrations_bridge.services import create_external_job_reference

CALLBACK_URL = "/api/v1/internal/jobs/callback/"
TOKEN = "internal-secret-token"
_JT = ExternalJobReference.JobType


def _auth(token=TOKEN):
    return {"HTTP_X_INTERNAL_TOKEN": token}


def make_job(workspace, owner, job_type, *, provider=ExternalJobReference.Provider.CONTENT_RENDERER,
             entity_type="content_pack_request", entity_id="cpr-1"):
    return create_external_job_reference(
        job_type=job_type,
        provider=provider,
        workspace=workspace,
        requested_by=owner,
        related_entity_type=entity_type,
        related_entity_id=entity_id,
    )


@pytest.fixture(autouse=True)
def _token(settings):
    settings.INTERNAL_API_TOKEN = TOKEN


@pytest.mark.django_db
class TestCallbackValidationAndDispatch:
    def test_valid_completed_dispatches_and_records(self, api_client, workspace, owner):
        # metrics_collection keeps the thin placeholder handler (content/report/
        # media_kit now have real product effects, covered by their app tests).
        job = make_job(
            workspace, owner, ExternalJobReference.JobType.METRICS_COLLECTION,
            entity_type="campaign", entity_id="camp-1",
        )
        resp = api_client.post(
            CALLBACK_URL,
            {
                "job_id": str(job.id),
                "workspace_id": str(workspace.id),
                "status": "completed",
                "entity": {"type": "campaign", "id": "camp-1"},
                "result": {"snapshots": 3},
            },
            format="json",
            **_auth(),
        )
        assert resp.status_code == 200
        job.refresh_from_db()
        assert job.status == ExternalJobReference.Status.COMPLETED
        assert job.completed_at is not None
        assert job.callback_received_at is not None
        assert job.callback_payload.get("result") == {"snapshots": 3}
        assert AuditEvent.objects.filter(
            action="metrics_collection.callback_received"
        ).count() == 1

    def test_workspace_mismatch_rejected(self, api_client, workspace, owner):
        job = make_job(workspace, owner, ExternalJobReference.JobType.CONTENT_GENERATION)
        resp = api_client.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "workspace_id": str(uuid.uuid4()), "status": "completed"},
            format="json",
            **_auth(),
        )
        assert resp.status_code == 400
        job.refresh_from_db()
        assert job.status == ExternalJobReference.Status.QUEUED

    def test_entity_type_mismatch_rejected(self, api_client, workspace, owner):
        job = make_job(workspace, owner, ExternalJobReference.JobType.CONTENT_GENERATION)
        resp = api_client.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "status": "completed",
             "entity": {"type": "report", "id": "cpr-1"}},
            format="json",
            **_auth(),
        )
        assert resp.status_code == 400

    def test_entity_id_mismatch_rejected(self, api_client, workspace, owner):
        job = make_job(workspace, owner, ExternalJobReference.JobType.CONTENT_GENERATION)
        resp = api_client.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "status": "completed",
             "entity": {"type": "content_pack_request", "id": "other"}},
            format="json",
            **_auth(),
        )
        assert resp.status_code == 400

    def test_invalid_status_is_400(self, api_client, workspace, owner):
        job = make_job(workspace, owner, ExternalJobReference.JobType.CONTENT_GENERATION)
        resp = api_client.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "status": "not-a-status"},
            format="json",
            **_auth(),
        )
        assert resp.status_code == 400

    def test_unknown_job_returns_404(self, api_client):
        resp = api_client.post(
            CALLBACK_URL,
            {"job_id": str(uuid.uuid4()), "workspace_id": str(uuid.uuid4()),
             "status": "completed"},
            format="json",
            **_auth(),
        )
        assert resp.status_code == 404


@pytest.mark.django_db
class TestCallbackSecurity:
    def test_no_token_403(self, api_client, workspace, owner):
        job = make_job(workspace, owner, ExternalJobReference.JobType.CONTENT_GENERATION)
        resp = api_client.post(
            CALLBACK_URL, {"job_id": str(job.id), "status": "completed"}, format="json"
        )
        assert resp.status_code == 403

    def test_wrong_token_403(self, api_client, workspace, owner):
        job = make_job(workspace, owner, ExternalJobReference.JobType.CONTENT_GENERATION)
        resp = api_client.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "status": "completed"},
            format="json",
            **_auth("wrong"),
        )
        assert resp.status_code == 403

    def test_empty_configured_token_403(self, api_client, settings, workspace, owner):
        settings.INTERNAL_API_TOKEN = ""
        job = make_job(workspace, owner, ExternalJobReference.JobType.CONTENT_GENERATION)
        resp = api_client.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "status": "completed"},
            format="json",
            **_auth("anything"),
        )
        assert resp.status_code == 403


@pytest.mark.django_db
class TestCallbackIdempotency:
    def test_duplicate_completed_no_repeat_effects(self, api_client, workspace, owner):
        # metrics_collection keeps the thin placeholder handler.
        job = make_job(
            workspace, owner, ExternalJobReference.JobType.METRICS_COLLECTION,
            entity_type="campaign", entity_id="camp-1",
        )
        payload = {"job_id": str(job.id), "workspace_id": str(workspace.id),
                   "status": "completed"}
        first = api_client.post(CALLBACK_URL, payload, format="json", **_auth())
        second = api_client.post(CALLBACK_URL, payload, format="json", **_auth())
        assert first.status_code == 200
        assert second.status_code == 200
        assert AuditEvent.objects.filter(
            action="metrics_collection.callback_received"
        ).count() == 1

    def test_duplicate_failed_no_repeat_effects(self, api_client, workspace, owner):
        job = make_job(
            workspace, owner, ExternalJobReference.JobType.METRICS_COLLECTION,
            entity_type="campaign", entity_id="camp-1",
        )
        payload = {"job_id": str(job.id), "workspace_id": str(workspace.id),
                   "status": "failed", "error": {"code": "x", "message": "boom"}}
        first = api_client.post(CALLBACK_URL, payload, format="json", **_auth())
        second = api_client.post(CALLBACK_URL, payload, format="json", **_auth())
        assert first.status_code == 200
        assert second.status_code == 200
        job.refresh_from_db()
        assert job.status == ExternalJobReference.Status.FAILED
        assert job.error_message == "boom"
        assert AuditEvent.objects.filter(
            action="metrics_collection.callback_received"
        ).count() == 1

    def test_terminal_then_incompatible_409(self, api_client, workspace, owner):
        job = make_job(workspace, owner, ExternalJobReference.JobType.CONTENT_GENERATION)
        ws = str(workspace.id)
        api_client.post(
            CALLBACK_URL, {"job_id": str(job.id), "workspace_id": ws, "status": "completed"},
            format="json", **_auth(),
        )
        resp = api_client.post(
            CALLBACK_URL, {"job_id": str(job.id), "workspace_id": ws, "status": "failed"},
            format="json", **_auth(),
        )
        assert resp.status_code == 409


@pytest.mark.django_db
class TestPlaceholderHandlers:
    @pytest.mark.parametrize(
        "job_type,action",
        [
            (_JT.METRICS_COLLECTION, "metrics_collection.callback_received"),
            (_JT.MOMENT_DETECTION, "moment_detection.callback_received"),
            (_JT.INSIGHT_GENERATION, "insight_generation.callback_received"),
            (_JT.RECOMMENDATION_GENERATION, "recommendation_generation.callback_received"),
        ],
    )
    def test_placeholder_stores_callback_and_audits(
        self, api_client, workspace, owner, job_type, action
    ):
        job = make_job(
            workspace, owner, job_type,
            provider=ExternalJobReference.Provider.INTELLIGENCE_ENGINE,
            entity_type="campaign", entity_id="camp-1",
        )
        resp = api_client.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "workspace_id": str(workspace.id),
             "status": "completed", "result": {"snapshots": 10}},
            format="json",
            **_auth(),
        )
        assert resp.status_code == 200
        job.refresh_from_db()
        assert job.status == ExternalJobReference.Status.COMPLETED
        assert job.callback_payload.get("result") == {"snapshots": 10}
        assert AuditEvent.objects.filter(action=action).count() == 1

    def test_unknown_job_type_does_not_break(self, api_client, workspace, owner):
        # video_rendering has no dedicated handler → safe fallback.
        job = make_job(
            workspace, owner, ExternalJobReference.JobType.VIDEO_RENDERING,
            provider=ExternalJobReference.Provider.VIDEO_RENDERER,
        )
        resp = api_client.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "workspace_id": str(workspace.id),
             "status": "completed"},
            format="json",
            **_auth(),
        )
        assert resp.status_code == 200
        job.refresh_from_db()
        assert job.status == ExternalJobReference.Status.COMPLETED
        assert AuditEvent.objects.filter(
            action="video_rendering.callback_unhandled"
        ).count() == 1
