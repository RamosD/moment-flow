"""Unit tests for the campaign Intelligence Engine payload builder.

Build model graphs directly with the shared factories (no API/HTTP). The engine
is never called here — only the JSON-safe envelope is asserted.
"""

import json
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.campaigns.intelligence_payload import (
    CampaignIntelligencePayloadBuilder,
    WorkspaceMismatchError,
    build_campaign_intelligence_payload,
)
from apps.campaigns.models import CampaignGoal
from apps.links.models import SmartLink, SmartLinkClick
from apps.reports.models import MediaKit, Report
from tests import factories

pytestmark = pytest.mark.django_db


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _rich_campaign():
    """A campaign with a track and one row of each related entity."""
    workspace = factories.WorkspaceFactory()
    artist = factories.ArtistFactory(workspace=workspace, primary_genre="afrobeats")
    track = factories.TrackFactory(artist=artist, release_date=date(2026, 6, 25))
    campaign = factories.CampaignFactory(
        artist=artist,
        track=track,
        workspace=workspace,
        primary_goal="grow streams",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 12, 31),
    )
    return workspace, campaign


def _add_clicks(workspace, campaign, *, today, n_today=1, n_old=1, n_ancient=1):
    """Create a smart link + clicks across the 7d / 30d / older buckets.

    Anchored to ``today`` (not ``timezone.now()``): the payload builder buckets
    clicks relative to the ``reference_date`` the caller passes in, which in
    these tests is a fixed date, not real wall-clock time. Anchoring click
    timestamps to real "now" instead of that same fixed date made the buckets
    silently drift out of alignment as real time moved away from the fixed
    reference — the fix is to use the one anchor the test actually cares
    about.
    """
    link = factories.SmartLinkFactory(campaign=campaign, workspace=workspace)
    base = timezone.make_aware(datetime.combine(today, time(12, 0)))
    for _ in range(n_today):
        SmartLinkClick.objects.create(
            workspace=workspace, campaign=campaign, smart_link=link, clicked_at=base
        )
    for _ in range(n_old):  # within 30d, outside 7d
        SmartLinkClick.objects.create(
            workspace=workspace, campaign=campaign, smart_link=link,
            clicked_at=base - timedelta(days=10),
        )
    for _ in range(n_ancient):  # outside 30d
        SmartLinkClick.objects.create(
            workspace=workspace, campaign=campaign, smart_link=link,
            clicked_at=base - timedelta(days=40),
        )
    return link


# --------------------------------------------------------------------------- #
# Envelope structure
# --------------------------------------------------------------------------- #
class TestEnvelope:
    def test_top_level_envelope(self):
        workspace, campaign = _rich_campaign()
        payload = build_campaign_intelligence_payload(
            campaign=campaign, workspace=workspace, reference_date=date(2026, 6, 25)
        )
        assert payload["payload_version"] == "1.0"
        assert payload["workspace_id"] == str(workspace.id)
        assert payload["entity"] == {"type": "campaign", "id": str(campaign.id)}
        assert payload["context"]["reference_date"] == "2026-06-25"
        assert set(payload["data"]) >= {
            "campaign", "artist", "track", "smart_link_stats",
            "content_outputs", "previous_reports", "reports", "media_kits", "goals",
        }

    def test_request_id_generated_when_absent(self):
        workspace, campaign = _rich_campaign()
        payload = build_campaign_intelligence_payload(
            campaign=campaign, workspace=workspace
        )
        assert payload["request_id"]  # non-empty
        # Looks like a uuid4 hex (32 chars).
        assert len(payload["request_id"]) == 32

    def test_request_id_respected_when_given(self):
        workspace, campaign = _rich_campaign()
        rid = uuid.uuid4().hex
        payload = build_campaign_intelligence_payload(
            campaign=campaign, workspace=workspace, request_id=rid
        )
        assert payload["request_id"] == rid

    def test_reference_date_defaults_to_today(self):
        workspace, campaign = _rich_campaign()
        payload = build_campaign_intelligence_payload(
            campaign=campaign, workspace=workspace
        )
        assert payload["context"]["reference_date"] == timezone.now().date().isoformat()

    def test_reports_alias_matches_previous_reports(self):
        workspace, campaign = _rich_campaign()
        Report.objects.create(
            workspace=workspace, campaign=campaign,
            report_type=Report.ReportType.CAMPAIGN_REPORT, title="R1",
            status=Report.Status.COMPLETED, period_end=date(2026, 6, 20),
        )
        payload = build_campaign_intelligence_payload(
            campaign=campaign, workspace=workspace
        )
        assert payload["data"]["reports"] == payload["data"]["previous_reports"]
        assert len(payload["data"]["previous_reports"]) == 1


# --------------------------------------------------------------------------- #
# Rich campaign
# --------------------------------------------------------------------------- #
class TestRichCampaign:
    def test_all_sections_populated_and_json_safe(self):
        workspace, campaign = _rich_campaign()
        ref = date(2026, 6, 25)
        _add_clicks(workspace, campaign, today=ref)
        factories.SmartLinkFactory(
            campaign=campaign, workspace=workspace, status=SmartLink.Status.PAUSED
        )
        factories.ContentOutputFactory(campaign=campaign)
        Report.objects.create(
            workspace=workspace, campaign=campaign,
            report_type=Report.ReportType.CAMPAIGN_REPORT, title="R1",
            status=Report.Status.COMPLETED, period_end=date(2026, 6, 20),
        )
        MediaKit.objects.create(
            workspace=workspace, campaign=campaign, artist=campaign.artist,
            title="MK1", status=MediaKit.Status.PUBLISHED,
        )
        CampaignGoal.objects.create(
            workspace=workspace, campaign=campaign,
            goal_type=CampaignGoal.GoalType.CLICKS,
            target_value=Decimal("1000.00"), current_value=Decimal("250.00"),
            unit="clicks", deadline=date(2026, 9, 1),
        )

        payload = build_campaign_intelligence_payload(
            campaign=campaign, workspace=workspace, reference_date=ref
        )
        data = payload["data"]

        assert data["campaign"]["status"] == "active"
        assert data["campaign"]["start_date"] == "2026-06-01"
        assert data["artist"]["primary_genre"] == "afrobeats"
        assert data["track"]["release_date"] == "2026-06-25"
        assert data["smart_link_stats"] == {
            "total_clicks": 3,
            "clicks_last_7_days": 1,
            "clicks_last_30_days": 2,
            "active_links": 1,  # the paused link is excluded
        }
        assert data["content_outputs"][0]["output_type"] == "post"
        assert data["previous_reports"][0]["period_end"] == "2026-06-20"
        assert data["media_kits"][0]["status"] == "published"
        goal = data["goals"][0]
        assert goal["target_value"] == 1000.0 and isinstance(goal["target_value"], float)
        assert goal["deadline"] == "2026-09-01"

        # Whole payload must be JSON-serializable (UUID/date/Decimal handled).
        json.dumps(payload)

    def test_no_n_plus_one_with_many_related_rows(self, django_assert_max_num_queries):
        workspace, campaign = _rich_campaign()
        ref = date(2026, 6, 25)
        _add_clicks(workspace, campaign, today=ref, n_today=5, n_old=5, n_ancient=5)
        for _ in range(5):
            factories.ContentOutputFactory(campaign=campaign)
            factories.SmartLinkFactory(campaign=campaign, workspace=workspace)
            Report.objects.create(
                workspace=workspace, campaign=campaign,
                report_type=Report.ReportType.CAMPAIGN_REPORT, title="R",
                status=Report.Status.COMPLETED,
            )
            MediaKit.objects.create(
                workspace=workspace, campaign=campaign, artist=campaign.artist,
                title="MK", status=MediaKit.Status.GENERATED,
            )
            CampaignGoal.objects.create(
                workspace=workspace, campaign=campaign,
                goal_type=CampaignGoal.GoalType.VIEWS,
            )

        # Re-fetch so artist/track FKs are lazy (worst case). The query count is
        # bounded and independent of the number of related rows (no N+1):
        # artist + track + clicks-aggregate + active-links + outputs + reports +
        # media_kits + goals == 8 (with a small margin).
        campaign = type(campaign).objects.get(pk=campaign.pk)
        with django_assert_max_num_queries(9):
            build_campaign_intelligence_payload(
                campaign=campaign, workspace=workspace, reference_date=ref
            )


# --------------------------------------------------------------------------- #
# Sparse / missing data (must never raise)
# --------------------------------------------------------------------------- #
class TestSparseData:
    def test_minimal_campaign_without_track_or_relations(self):
        workspace = factories.WorkspaceFactory()
        artist = factories.ArtistFactory(workspace=workspace)
        campaign = factories.CampaignFactory(
            artist=artist, track=None, workspace=workspace
        )
        payload = build_campaign_intelligence_payload(
            campaign=campaign, workspace=workspace
        )
        data = payload["data"]
        assert data["track"] is None
        assert data["artist"]["id"] == str(artist.id)
        assert data["smart_link_stats"] == {
            "total_clicks": 0, "clicks_last_7_days": 0,
            "clicks_last_30_days": 0, "active_links": 0,
        }
        assert data["content_outputs"] == []
        assert data["previous_reports"] == []
        assert data["media_kits"] == []
        assert data["goals"] == []
        json.dumps(payload)

    def test_campaign_without_smart_links(self):
        workspace, campaign = _rich_campaign()
        factories.ContentOutputFactory(campaign=campaign)  # has other data
        payload = build_campaign_intelligence_payload(
            campaign=campaign, workspace=workspace
        )
        assert payload["data"]["smart_link_stats"]["active_links"] == 0
        assert payload["data"]["smart_link_stats"]["total_clicks"] == 0

    def test_campaign_without_content_outputs(self):
        workspace, campaign = _rich_campaign()
        _add_clicks(workspace, campaign, today=date(2026, 6, 25))
        payload = build_campaign_intelligence_payload(
            campaign=campaign, workspace=workspace
        )
        assert payload["data"]["content_outputs"] == []

    def test_campaign_without_reports_or_media_kits(self):
        workspace, campaign = _rich_campaign()
        factories.ContentOutputFactory(campaign=campaign)
        payload = build_campaign_intelligence_payload(
            campaign=campaign, workspace=workspace
        )
        assert payload["data"]["previous_reports"] == []
        assert payload["data"]["reports"] == []
        assert payload["data"]["media_kits"] == []


# --------------------------------------------------------------------------- #
# Isolation & validation
# --------------------------------------------------------------------------- #
class TestIsolationAndValidation:
    def test_workspace_mismatch_raises(self):
        workspace, campaign = _rich_campaign()
        other_workspace = factories.WorkspaceFactory()
        with pytest.raises(WorkspaceMismatchError):
            CampaignIntelligencePayloadBuilder(
                campaign=campaign, workspace=other_workspace
            )

    def test_other_campaign_data_is_not_leaked(self):
        workspace, campaign = _rich_campaign()
        # Another campaign in the SAME workspace with its own clicks/outputs.
        other_campaign = factories.CampaignFactory(
            artist=campaign.artist, workspace=workspace
        )
        _add_clicks(workspace, other_campaign, today=date(2026, 6, 25), n_today=3)
        factories.ContentOutputFactory(campaign=other_campaign)

        payload = build_campaign_intelligence_payload(
            campaign=campaign, workspace=workspace, reference_date=date(2026, 6, 25)
        )
        assert payload["data"]["smart_link_stats"]["total_clicks"] == 0
        assert payload["data"]["content_outputs"] == []
