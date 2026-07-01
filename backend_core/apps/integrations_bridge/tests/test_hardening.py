"""Hardening: callback security, controlled retry, token-free logs, Admin."""

import logging
import uuid

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from rest_framework.test import APIClient

from apps.integrations_bridge.admin import ExternalJobReferenceAdmin
from apps.integrations_bridge.models import ExternalJobReference
from apps.integrations_bridge.services import (
    RetryNotAllowed,
    create_external_job_reference,
    retry_external_job,
)

CALLBACK_URL = "/api/v1/internal/jobs/callback/"
TOKEN = "internal-secret-token"
_S = ExternalJobReference.Status


@pytest.fixture(autouse=True)
def _token(settings):
    settings.INTERNAL_API_TOKEN = TOKEN


@pytest.fixture
def api():
    return APIClient()


def _auth(token=TOKEN):
    return {"HTTP_X_INTERNAL_TOKEN": token}


def _job(workspace, owner, status=_S.QUEUED):
    job = create_external_job_reference(
        job_type=ExternalJobReference.JobType.CONTENT_GENERATION,
        provider=ExternalJobReference.Provider.CONTENT_RENDERER,
        workspace=workspace, requested_by=owner,
        related_entity_type="content_pack_request",
        related_entity_id=str(uuid.uuid4()),
    )
    if status != _S.QUEUED:
        job.status = status
        job.save(update_fields=["status"])
    return job


# --------------------------------------------------------------------------- #
# Callback security
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestCallbackSecurity:
    def _post(self, api, payload, **headers):
        return api.post(CALLBACK_URL, payload, format="json", **headers)

    def test_no_token_403(self, api, workspace, owner):
        job = _job(workspace, owner)
        resp = self._post(api, {"job_id": str(job.id), "workspace_id": str(workspace.id),
                                "status": "completed"})
        assert resp.status_code == 403

    def test_wrong_token_403(self, api, workspace, owner):
        job = _job(workspace, owner)
        resp = self._post(api, {"job_id": str(job.id), "workspace_id": str(workspace.id),
                                "status": "completed"}, **_auth("wrong"))
        assert resp.status_code == 403

    def test_empty_configured_token_403(self, api, settings, workspace, owner):
        settings.INTERNAL_API_TOKEN = ""
        job = _job(workspace, owner)
        resp = self._post(api, {"job_id": str(job.id), "workspace_id": str(workspace.id),
                                "status": "completed"}, **_auth("anything"))
        assert resp.status_code == 403

    def test_missing_workspace_id_400(self, api, workspace, owner):
        job = _job(workspace, owner)
        resp = self._post(api, {"job_id": str(job.id), "status": "completed"}, **_auth())
        assert resp.status_code == 400
        job.refresh_from_db()
        assert job.status == _S.QUEUED

    def test_workspace_mismatch_400(self, api, workspace, owner):
        job = _job(workspace, owner)
        resp = self._post(api, {"job_id": str(job.id), "workspace_id": str(uuid.uuid4()),
                                "status": "completed"}, **_auth())
        assert resp.status_code == 400

    def test_entity_mismatch_400(self, api, workspace, owner):
        job = _job(workspace, owner)
        resp = self._post(api, {"job_id": str(job.id), "workspace_id": str(workspace.id),
                                "status": "completed",
                                "entity": {"type": "report", "id": str(uuid.uuid4())}}, **_auth())
        assert resp.status_code == 400


# --------------------------------------------------------------------------- #
# Controlled retry
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestRetry:
    @pytest.mark.parametrize("status", [_S.FAILED, _S.TIMEOUT, _S.CANCELLED, _S.EXPIRED])
    def test_retry_allowed(self, settings, status, workspace, owner):
        settings.EXTERNAL_JOBS_DRY_RUN = True
        job = _job(workspace, owner, status=status)
        new_job = retry_external_job(job, requested_by=owner)
        assert new_job.id != job.id
        assert new_job.retry_count == 1
        assert new_job.metadata.get("retried_from") == str(job.id)
        job.refresh_from_db()
        assert job.status == status  # original is preserved

    @pytest.mark.parametrize("status", [_S.QUEUED, _S.SUBMITTED, _S.RUNNING, _S.COMPLETED])
    def test_retry_blocked(self, status, workspace, owner):
        job = _job(workspace, owner, status=status)
        with pytest.raises(RetryNotAllowed):
            retry_external_job(job, requested_by=owner)


# --------------------------------------------------------------------------- #
# Token-free structured logs
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestLogging:
    def test_token_never_in_logs(self, api, caplog, workspace, owner):
        job = _job(workspace, owner)
        with caplog.at_level(logging.INFO, logger="integrations_bridge"):
            api.post(
                CALLBACK_URL,
                {"job_id": str(job.id), "workspace_id": str(workspace.id),
                 "status": "completed", "result": {"outputs": []}},
                format="json", **_auth(),
            )
        # Logging happened (job tracing) but the token never appears.
        assert "callback_received" in caplog.text
        assert TOKEN not in caplog.text


# --------------------------------------------------------------------------- #
# Admin
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestAdmin:
    def test_admin_config(self):
        admin = ExternalJobReferenceAdmin(ExternalJobReference, AdminSite())
        for f in ("status", "job_type", "provider", "workspace"):
            assert f in admin.list_filter
        for s in ("external_job_id", "related_entity_id", "request_id"):
            assert s in admin.search_fields
        for r in ("request_payload", "response_payload", "callback_payload", "request_id"):
            assert r in admin.readonly_fields

    def test_mark_cancelled_skips_terminal(self, workspace, owner):
        admin = ExternalJobReferenceAdmin(ExternalJobReference, AdminSite())
        non_terminal = _job(workspace, owner, status=_S.RUNNING)
        completed = _job(workspace, owner, status=_S.COMPLETED)

        request = RequestFactory().post("/admin/")
        request.session = {}
        request._messages = FallbackStorage(request)
        admin.mark_cancelled(request, ExternalJobReference.objects.all())

        non_terminal.refresh_from_db()
        completed.refresh_from_db()
        assert non_terminal.status == _S.CANCELLED
        assert completed.status == _S.COMPLETED  # terminal job untouched
