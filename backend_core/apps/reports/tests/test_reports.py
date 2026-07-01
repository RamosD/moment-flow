"""Report and ReportSection: creation, sections, usage, isolation, permissions."""

import pytest

from apps.billing.models import UsageEvent
from apps.reports.models import Report, ReportSection
from apps.reports.tests.conftest import ws_header

REPORTS_URL = "/api/v1/reports/"
SECTIONS_URL = "/api/v1/report-sections/"


def _results(response):
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


@pytest.mark.django_db
class TestReportCreation:
    def test_create_report_is_queued(self, client_for, owner, workspace):
        resp = client_for(owner).post(
            REPORTS_URL,
            {"report_type": "monthly_report", "title": "June Recap"},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 201
        report = Report.objects.get(id=resp.data["id"])
        assert report.status == Report.Status.QUEUED
        assert report.workspace_id == workspace.id
        assert report.requested_by_id == owner.id

    def test_create_report_records_usage_event(self, client_for, owner, workspace):
        client_for(owner).post(
            REPORTS_URL,
            {"report_type": "campaign_report", "title": "X"},
            format="json",
            **ws_header(workspace),
        )
        assert UsageEvent.objects.filter(
            workspace=workspace, event_type=UsageEvent.EventType.REPORT_GENERATED
        ).exists()

    def test_rejects_campaign_from_other_workspace(
        self, client_for, owner, workspace, other_workspace, make_campaign
    ):
        foreign = make_campaign(other_workspace, name="F", slug="f")
        resp = client_for(owner).post(
            REPORTS_URL,
            {"report_type": "campaign_report", "title": "X", "campaign": str(foreign.id)},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 400
        assert "campaign" in resp.data


@pytest.mark.django_db
class TestReportSections:
    def test_report_can_have_sections(self, client_for, owner, workspace):
        report = Report.objects.create(
            workspace=workspace, report_type=Report.ReportType.WEEKLY_REPORT, title="R"
        )
        resp = client_for(owner).post(
            SECTIONS_URL,
            {
                "report": str(report.id),
                "section_key": "overview",
                "title": "Overview",
                "sort_order": 0,
                "content_json": {"summary": "ok"},
            },
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 201
        section = ReportSection.objects.get(id=resp.data["id"])
        assert section.report_id == report.id
        assert section.workspace_id == workspace.id

    def test_sections_listed_filtered_by_report(self, client_for, owner, workspace):
        report = Report.objects.create(
            workspace=workspace, report_type=Report.ReportType.WEEKLY_REPORT, title="R"
        )
        ReportSection.objects.create(
            workspace=workspace, report=report, section_key="a"
        )
        resp = client_for(owner).get(
            f"{SECTIONS_URL}?report={report.id}", **ws_header(workspace)
        )
        assert resp.status_code == 200
        assert len(_results(resp)) == 1


@pytest.mark.django_db
class TestReportIsolationAndPermissions:
    def test_reports_isolated_per_workspace(
        self, client_for, owner, workspace, other_owner, other_workspace
    ):
        Report.objects.create(
            workspace=workspace, report_type=Report.ReportType.WEEKLY_REPORT, title="R"
        )
        resp = client_for(other_owner).get(REPORTS_URL, **ws_header(other_workspace))
        assert resp.status_code == 200
        assert _results(resp) == []

    def test_editor_cannot_generate_but_can_view(
        self, client_for, make_user, workspace, add_member
    ):
        editor = make_user("editor@example.com")
        add_member(workspace, editor, "editor")
        client = client_for(editor)

        create = client.post(
            REPORTS_URL,
            {"report_type": "weekly_report", "title": "X"},
            format="json",
            **ws_header(workspace),
        )
        assert create.status_code == 403

        listing = client.get(REPORTS_URL, **ws_header(workspace))
        assert listing.status_code == 200

    def test_non_member_is_blocked(
        self, client_for, other_owner, workspace
    ):
        resp = client_for(other_owner).get(REPORTS_URL, **ws_header(workspace))
        assert resp.status_code == 403
