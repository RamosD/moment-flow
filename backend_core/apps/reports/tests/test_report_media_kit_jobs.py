"""Report / MediaKit → ExternalJobReference submission (Prompt 06)."""

import json

import pytest

import apps.integrations_bridge.services as bridge
from apps.audit.models import AuditEvent
from apps.billing.models import UsageEvent
from apps.integrations_bridge.clients import InternalServiceUnavailable
from apps.integrations_bridge.models import ExternalJobReference
from apps.reports.models import MediaKit, Report, ReportSection
from apps.reports.payloads import (
    build_media_kit_generation_payload,
    build_report_generation_payload,
)
from apps.reports.services import (
    submit_media_kit_generation_job,
    submit_report_generation_job,
)
from apps.reports.tests.conftest import ws_header

REPORTS_URL = "/api/v1/reports/"
MEDIA_KITS_URL = "/api/v1/media-kits/"


def _job_for(entity_type, entity_id):
    return ExternalJobReference.objects.get(
        related_entity_type=entity_type, related_entity_id=str(entity_id)
    )


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestReportJob:
    def test_create_report_creates_job(self, client_for, owner, workspace):
        resp = client_for(owner).post(
            REPORTS_URL,
            {"report_type": "monthly_report", "title": "June Recap"},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 201
        report = Report.objects.get(id=resp.data["id"])
        job = _job_for("report", report.id)
        assert job.job_type == ExternalJobReference.JobType.REPORT_GENERATION
        assert job.provider == "report_renderer"  # resolved via the registry
        assert job.idempotency_key == f"report_generation:{report.id}"
        assert job.workspace_id == workspace.id
        assert report.metadata.get("external_job_id") == str(job.id)
        assert UsageEvent.objects.filter(
            workspace=workspace, event_type=UsageEvent.EventType.REPORT_GENERATED
        ).exists()
        assert AuditEvent.objects.filter(
            action="report.job_submitted", entity_id=str(report.id)
        ).exists()

    def test_report_payload_is_json_serializable(self, owner, workspace, make_campaign):
        campaign = make_campaign(workspace)
        report = Report.objects.create(
            workspace=workspace,
            report_type=Report.ReportType.CAMPAIGN_REPORT,
            title="Campaign Report",
            campaign=campaign,
            artist=campaign.artist,
            requested_by=owner,
        )
        ReportSection.objects.create(
            workspace=workspace, report=report, section_key="overview",
            title="Overview", sort_order=0,
        )
        payload = build_report_generation_payload(report)
        json.dumps(payload)  # must not raise
        assert payload["entity"] == {"type": "report", "id": str(report.id)}
        assert payload["report_type"] == "campaign_report"
        assert {s["section_key"] for s in payload["sections"]} == {"overview"}
        assert payload["campaign"]["id"] == str(campaign.id)

    def test_report_dry_run_marks_submitted(self, settings, owner, workspace):
        settings.EXTERNAL_JOBS_ENABLED = True
        settings.EXTERNAL_JOBS_DRY_RUN = True
        report = Report.objects.create(
            workspace=workspace, report_type=Report.ReportType.WEEKLY_REPORT,
            title="R", requested_by=owner,
        )
        submit_report_generation_job(report, requested_by=owner)
        job = _job_for("report", report.id)
        assert job.status == ExternalJobReference.Status.SUBMITTED
        assert job.response_payload == {"dry_run": True}

    def test_report_idempotent(self, owner, workspace):
        report = Report.objects.create(
            workspace=workspace, report_type=Report.ReportType.WEEKLY_REPORT,
            title="R", requested_by=owner,
        )
        submit_report_generation_job(report, requested_by=owner)
        submit_report_generation_job(report, requested_by=owner)
        assert ExternalJobReference.objects.filter(
            idempotency_key=f"report_generation:{report.id}"
        ).count() == 1

    def test_report_submission_failure_is_traceable(
        self, settings, monkeypatch, owner, workspace
    ):
        settings.EXTERNAL_JOBS_ENABLED = True
        settings.EXTERNAL_JOBS_DRY_RUN = False
        settings.REPORT_RENDERER_BASE_URL = "http://renderer:8003"

        class DownClient:
            def __init__(self, *a, **k):
                pass

            def post_json(self, *a, **k):
                raise InternalServiceUnavailable("renderer down")

        monkeypatch.setattr(bridge, "InternalServiceClient", DownClient)

        report = Report.objects.create(
            workspace=workspace, report_type=Report.ReportType.WEEKLY_REPORT,
            title="R", requested_by=owner,
        )
        submit_report_generation_job(report, requested_by=owner)
        job = _job_for("report", report.id)
        assert job.status == ExternalJobReference.Status.FAILED
        assert "renderer down" in job.error_message
        report.refresh_from_db()
        assert report.metadata.get("external_job_id") == str(job.id)
        # STG-PRE-007: a submission-time failure (renderer never reached, so no
        # callback will ever arrive) must not leave the report stuck "queued".
        assert report.status == Report.Status.FAILED
        assert "renderer down" in report.metadata.get("error", "")


# --------------------------------------------------------------------------- #
# Media kit
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestMediaKitJob:
    def test_create_media_kit_creates_job(self, client_for, owner, workspace, make_artist):
        artist = make_artist(workspace)
        resp = client_for(owner).post(
            MEDIA_KITS_URL,
            {"artist": str(artist.id), "title": "Press Kit"},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 201
        media_kit = MediaKit.objects.get(id=resp.data["id"])
        job = _job_for("media_kit", media_kit.id)
        assert job.job_type == ExternalJobReference.JobType.MEDIA_KIT_GENERATION
        assert job.provider == "report_renderer"
        assert job.idempotency_key == f"media_kit_generation:{media_kit.id}"
        assert media_kit.metadata.get("external_job_id") == str(job.id)
        assert UsageEvent.objects.filter(
            workspace=workspace, event_type=UsageEvent.EventType.MEDIA_KIT_GENERATED
        ).exists()
        assert AuditEvent.objects.filter(
            action="media_kit.job_submitted", entity_id=str(media_kit.id)
        ).exists()

    def test_media_kit_payload_is_json_serializable(self, owner, workspace, make_artist):
        from apps.reports.models import MediaKitItem

        artist = make_artist(workspace)
        media_kit = MediaKit.objects.create(
            workspace=workspace, artist=artist, title="Kit", created_by=owner,
        )
        MediaKitItem.objects.create(
            workspace=workspace, media_kit=media_kit,
            item_type=MediaKitItem.ItemType.BIO, title="Bio", content="hello",
        )
        payload = build_media_kit_generation_payload(media_kit)
        json.dumps(payload)  # must not raise
        assert payload["entity"] == {"type": "media_kit", "id": str(media_kit.id)}
        assert payload["artist"]["id"] == str(artist.id)
        assert len(payload["items"]) == 1
        assert payload["items"][0]["item_type"] == "bio"

    def test_media_kit_dry_run_marks_submitted(self, settings, owner, workspace, make_artist):
        settings.EXTERNAL_JOBS_ENABLED = True
        settings.EXTERNAL_JOBS_DRY_RUN = True
        media_kit = MediaKit.objects.create(
            workspace=workspace, artist=make_artist(workspace), title="Kit",
            created_by=owner,
        )
        submit_media_kit_generation_job(media_kit, requested_by=owner)
        job = _job_for("media_kit", media_kit.id)
        assert job.status == ExternalJobReference.Status.SUBMITTED

    def test_media_kit_idempotent(self, owner, workspace, make_artist):
        media_kit = MediaKit.objects.create(
            workspace=workspace, artist=make_artist(workspace), title="Kit",
            created_by=owner,
        )
        submit_media_kit_generation_job(media_kit, requested_by=owner)
        submit_media_kit_generation_job(media_kit, requested_by=owner)
        assert ExternalJobReference.objects.filter(
            idempotency_key=f"media_kit_generation:{media_kit.id}"
        ).count() == 1

    def test_media_kit_submission_failure_is_traceable(
        self, settings, monkeypatch, owner, workspace, make_artist
    ):
        settings.EXTERNAL_JOBS_ENABLED = True
        settings.EXTERNAL_JOBS_DRY_RUN = False
        settings.REPORT_RENDERER_BASE_URL = "http://renderer:8003"

        class DownClient:
            def __init__(self, *a, **k):
                pass

            def post_json(self, *a, **k):
                raise InternalServiceUnavailable("renderer down")

        monkeypatch.setattr(bridge, "InternalServiceClient", DownClient)

        media_kit = MediaKit.objects.create(
            workspace=workspace, artist=make_artist(workspace), title="Kit",
            created_by=owner,
        )
        submit_media_kit_generation_job(media_kit, requested_by=owner)
        job = _job_for("media_kit", media_kit.id)
        assert job.status == ExternalJobReference.Status.FAILED
        media_kit.refresh_from_db()
        # MediaKit has no FAILED status of its own (STG-PRE-007) — a
        # submission-time failure (no callback will ever arrive) must still be
        # traceable via metadata, same as a real callback failure.
        assert media_kit.status == MediaKit.Status.DRAFT
        assert media_kit.metadata.get("generation_status") == "failed"
        assert "renderer down" in media_kit.metadata.get("error", "")


# --------------------------------------------------------------------------- #
# Isolation
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestIsolation:
    def test_report_job_belongs_to_workspace(self, owner, workspace):
        report = Report.objects.create(
            workspace=workspace, report_type=Report.ReportType.WEEKLY_REPORT,
            title="R", requested_by=owner,
        )
        submit_report_generation_job(report, requested_by=owner)
        job = _job_for("report", report.id)
        assert job.workspace_id == workspace.id
        assert build_report_generation_payload(report)["workspace_id"] == str(workspace.id)
