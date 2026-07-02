"""End-to-end tests for report/media-kit generation callbacks (Prompt 07)."""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.core.models import Asset
from apps.integrations_bridge.models import ExternalJobReference
from apps.notifications.models import Notification
from apps.reports.models import MediaKit, Report
from apps.reports.services import (
    submit_media_kit_generation_job,
    submit_report_generation_job,
)

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


def _make_report_job(workspace, owner):
    report = Report.objects.create(
        workspace=workspace, report_type=Report.ReportType.MONTHLY_REPORT,
        title="June Recap", requested_by=owner,
    )
    submit_report_generation_job(report, requested_by=owner)
    job = ExternalJobReference.objects.get(
        related_entity_type="report", related_entity_id=str(report.id)
    )
    return report, job


def _make_media_kit_job(workspace, owner, artist):
    media_kit = MediaKit.objects.create(
        workspace=workspace, artist=artist, title="Press Kit", created_by=owner,
    )
    submit_media_kit_generation_job(media_kit, requested_by=owner)
    job = ExternalJobReference.objects.get(
        related_entity_type="media_kit", related_entity_id=str(media_kit.id)
    )
    return media_kit, job


def _asset_block(fmt="pdf", mime="application/pdf"):
    return {
        "title": "Generated", "format": fmt,
        "storage_provider": "s3", "bucket": "bucket", "storage_key": f"files/out.{fmt}",
        "file_name": f"out.{fmt}", "mime_type": mime,
        "file_size_bytes": 23456, "checksum": "deadbeef",
        "public_url": f"https://bucket.example.test/files/out.{fmt}",
    }


def _completed(job, workspace, entity_type, entity_id, result):
    return {
        "job_id": str(job.id),
        "workspace_id": str(workspace.id),
        "status": "completed",
        "entity": {"type": entity_type, "id": str(entity_id)},
        "result": result,
    }


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestReportCallback:
    def test_completed_links_asset_and_notifies(self, api, workspace, owner):
        report, job = _make_report_job(workspace, owner)
        resp = api.post(
            CALLBACK_URL,
            _completed(job, workspace, "report", report.id, {"asset": _asset_block()}),
            format="json", **_auth(),
        )
        assert resp.status_code == 200
        report.refresh_from_db()
        job.refresh_from_db()
        assert report.status == Report.Status.COMPLETED
        assert report.storage_asset_id is not None
        assert job.status == ExternalJobReference.Status.COMPLETED
        assert Asset.objects.filter(
            workspace=workspace, asset_type=Asset.AssetType.REPORT_PDF
        ).count() == 1
        assert report.storage_asset.public_url == "https://bucket.example.test/files/out.pdf"
        assert Notification.objects.filter(
            workspace=workspace,
            notification_type=Notification.NotificationType.REPORT_READY,
        ).count() == 1
        assert AuditEvent.objects.filter(action="report.completed").count() == 1

    def test_failed_records_error(self, api, workspace, owner):
        report, job = _make_report_job(workspace, owner)
        resp = api.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "workspace_id": str(workspace.id), "status": "failed",
             "error": {"code": "renderer_error", "message": "boom"}},
            format="json", **_auth(),
        )
        assert resp.status_code == 200
        report.refresh_from_db()
        assert report.status == Report.Status.FAILED
        assert report.metadata.get("error") == "boom"
        assert report.storage_asset_id is None
        assert Notification.objects.filter(
            workspace=workspace, related_entity_id=str(report.id)
        ).exists()
        assert AuditEvent.objects.filter(action="report.failed").count() == 1

    def test_duplicate_completed_is_idempotent(self, api, workspace, owner):
        report, job = _make_report_job(workspace, owner)
        payload = _completed(job, workspace, "report", report.id, {"asset": _asset_block()})
        api.post(CALLBACK_URL, payload, format="json", **_auth())
        api.post(CALLBACK_URL, payload, format="json", **_auth())
        assert Asset.objects.filter(
            workspace=workspace, asset_type=Asset.AssetType.REPORT_PDF
        ).count() == 1
        assert Notification.objects.filter(
            workspace=workspace,
            notification_type=Notification.NotificationType.REPORT_READY,
        ).count() == 1


# --------------------------------------------------------------------------- #
# Media kit
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestMediaKitCallback:
    def test_completed_links_asset_and_notifies(self, api, workspace, owner, make_artist):
        media_kit, job = _make_media_kit_job(workspace, owner, make_artist(workspace))
        resp = api.post(
            CALLBACK_URL,
            _completed(job, workspace, "media_kit", media_kit.id, {"asset": _asset_block()}),
            format="json", **_auth(),
        )
        assert resp.status_code == 200
        media_kit.refresh_from_db()
        job.refresh_from_db()
        assert media_kit.status == MediaKit.Status.GENERATED
        assert media_kit.storage_asset_id is not None
        assert job.status == ExternalJobReference.Status.COMPLETED
        assert Asset.objects.filter(
            workspace=workspace, asset_type=Asset.AssetType.MEDIA_KIT_ASSET
        ).count() == 1
        assert media_kit.storage_asset.public_url == "https://bucket.example.test/files/out.pdf"
        assert Notification.objects.filter(
            workspace=workspace,
            notification_type=Notification.NotificationType.MEDIA_KIT_READY,
        ).count() == 1
        assert AuditEvent.objects.filter(action="media_kit.completed").count() == 1

    def test_failed_is_traceable_in_metadata(self, api, workspace, owner, make_artist):
        media_kit, job = _make_media_kit_job(workspace, owner, make_artist(workspace))
        resp = api.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "workspace_id": str(workspace.id), "status": "failed",
             "error": {"message": "render error"}},
            format="json", **_auth(),
        )
        assert resp.status_code == 200
        media_kit.refresh_from_db()
        job.refresh_from_db()
        # MediaKit has no FAILED status — failure is recorded on metadata.
        assert media_kit.status == MediaKit.Status.DRAFT
        assert media_kit.metadata.get("generation_status") == "failed"
        assert media_kit.metadata.get("error") == "render error"
        assert job.status == ExternalJobReference.Status.FAILED
        assert AuditEvent.objects.filter(action="media_kit.failed").count() == 1
        assert Notification.objects.filter(
            workspace=workspace, related_entity_id=str(media_kit.id)
        ).exists()

    def test_duplicate_completed_is_idempotent(self, api, workspace, owner, make_artist):
        media_kit, job = _make_media_kit_job(workspace, owner, make_artist(workspace))
        payload = _completed(
            job, workspace, "media_kit", media_kit.id, {"asset": _asset_block()}
        )
        api.post(CALLBACK_URL, payload, format="json", **_auth())
        api.post(CALLBACK_URL, payload, format="json", **_auth())
        assert Asset.objects.filter(
            workspace=workspace, asset_type=Asset.AssetType.MEDIA_KIT_ASSET
        ).count() == 1
        assert Notification.objects.filter(
            workspace=workspace,
            notification_type=Notification.NotificationType.MEDIA_KIT_READY,
        ).count() == 1


# --------------------------------------------------------------------------- #
# Rejection
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestRejection:
    def test_wrong_workspace_rejected(self, api, workspace, owner):
        report, job = _make_report_job(workspace, owner)
        resp = api.post(
            CALLBACK_URL,
            {
                "job_id": str(job.id),
                "workspace_id": str(uuid.uuid4()),
                "status": "completed",
                "result": {"asset": _asset_block()},
            },
            format="json", **_auth(),
        )
        assert resp.status_code == 400
        report.refresh_from_db()
        assert report.status == Report.Status.QUEUED
        assert report.storage_asset_id is None

    def test_wrong_entity_rejected(self, api, workspace, owner):
        report, job = _make_report_job(workspace, owner)
        resp = api.post(
            CALLBACK_URL,
            {
                "job_id": str(job.id),
                "status": "completed",
                "entity": {"type": "media_kit", "id": str(report.id)},
            },
            format="json", **_auth(),
        )
        assert resp.status_code == 400

    def test_invalid_status_is_400(self, api, workspace, owner):
        report, job = _make_report_job(workspace, owner)
        resp = api.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "status": "not-a-status"},
            format="json", **_auth(),
        )
        assert resp.status_code == 400
