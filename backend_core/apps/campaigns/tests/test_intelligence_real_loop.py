"""Real-loop validation: Backend Core → live Intelligence Engine (no mocks).

OPT-IN. Skipped unless ``RUN_REAL_IE=1`` is set, because it requires the FastAPI
Intelligence Engine running and reachable. Drives the real stack
(service → builder → real client → real HTTP) against the live engine.

How to run (see prompt_09 report for the full checklist):

    # 1) start the engine (separate terminal), with a known token
    cd intelligence_engine
    INTERNAL_API_TOKEN=real-loop-token-123 APP_ENV=development \
        venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8201

    # 2) run this test pointed at it
    cd backend_core
    RUN_REAL_IE=1 REAL_IE_BASE_URL=http://127.0.0.1:8201 \
        REAL_IE_TOKEN=real-loop-token-123 \
        venv/Scripts/python.exe -m pytest apps/campaigns/tests/test_intelligence_real_loop.py -q
"""

import logging
import os
from datetime import date

import pytest

from apps.campaigns.intelligence_service import (
    IntelligenceUnavailableError,
    get_campaign_intelligence,
)
from apps.campaigns.models import Campaign, CampaignGoal
from apps.links.models import SmartLink, SmartLinkClick
from apps.reports.models import MediaKit, Report
from tests import factories

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(
        not os.environ.get("RUN_REAL_IE"),
        reason="Set RUN_REAL_IE=1 with the Intelligence Engine running to enable.",
    ),
]

BASE_URL = os.environ.get("REAL_IE_BASE_URL", "http://127.0.0.1:8201")
TOKEN = os.environ.get("REAL_IE_TOKEN", "real-loop-token-123")


def _rich_campaign():
    workspace = factories.WorkspaceFactory()
    artist = factories.ArtistFactory(workspace=workspace, primary_genre="afrobeats")
    track = factories.TrackFactory(artist=artist, release_date=date(2026, 6, 25))
    campaign = Campaign.objects.create(
        workspace=workspace, artist=artist, track=track, name="Real Loop",
        slug="real-loop", status=Campaign.Status.ACTIVE, primary_goal="grow",
        start_date=date(2026, 6, 1), end_date=date(2026, 12, 31),
    )
    link = factories.SmartLinkFactory(
        campaign=campaign, workspace=workspace, status=SmartLink.Status.ACTIVE
    )
    SmartLinkClick.objects.create(
        workspace=workspace, campaign=campaign, smart_link=link
    )
    factories.ContentOutputFactory(campaign=campaign)
    Report.objects.create(
        workspace=workspace, campaign=campaign,
        report_type=Report.ReportType.CAMPAIGN_REPORT, title="R",
        status=Report.Status.COMPLETED, period_end=date(2026, 6, 20),
    )
    MediaKit.objects.create(
        workspace=workspace, campaign=campaign, artist=artist,
        title="MK", status=MediaKit.Status.PUBLISHED,
    )
    CampaignGoal.objects.create(
        workspace=workspace, campaign=campaign, goal_type=CampaignGoal.GoalType.CLICKS,
    )
    return workspace, campaign


def _point_at_live_engine(settings):
    settings.INTELLIGENCE_ENGINE_BASE_URL = BASE_URL
    settings.INTELLIGENCE_ENGINE_INTERNAL_TOKEN = TOKEN
    settings.INTELLIGENCE_ENGINE_ENABLED = True
    settings.INTELLIGENCE_ENGINE_DRY_RUN = False
    settings.INTELLIGENCE_ENGINE_MAX_RETRIES = 0


def test_real_loop_returns_intelligence(settings, caplog):
    _point_at_live_engine(settings)
    workspace, campaign = _rich_campaign()

    with caplog.at_level(logging.INFO):
        outcome = get_campaign_intelligence(
            workspace=workspace, campaign=campaign, reference_date=date(2026, 6, 25)
        )

    assert outcome.source == "engine"
    assert outcome.status == "completed"
    assert outcome.engine == "intelligence_engine"
    assert outcome.generated_at  # stamped by Django
    for key in ("analysis", "scores", "grade", "moments", "recommendations", "summary"):
        assert key in outcome.result, key
    # The shared secret must never appear in any log line.
    assert TOKEN not in caplog.text


def test_real_loop_unavailable_is_controlled(settings):
    # Point at a closed port → the engine is unreachable; must fail gracefully.
    settings.INTELLIGENCE_ENGINE_BASE_URL = "http://127.0.0.1:8009"
    settings.INTELLIGENCE_ENGINE_INTERNAL_TOKEN = TOKEN
    settings.INTELLIGENCE_ENGINE_ENABLED = True
    settings.INTELLIGENCE_ENGINE_DRY_RUN = False
    settings.INTELLIGENCE_ENGINE_MAX_RETRIES = 0
    workspace, campaign = _rich_campaign()

    with pytest.raises(IntelligenceUnavailableError):
        get_campaign_intelligence(workspace=workspace, campaign=campaign)


def test_real_loop_via_django_http_endpoint(settings, client_for, owner, caplog):
    """Drives the real ``POST /api/v1/campaigns/{id}/intelligence/`` endpoint
    (auth + RBAC + service + builder + real HTTP) against the live engine.
    """
    from django.utils.timezone import now

    from apps.rbac.models import Role
    from apps.rbac.seeds import seed_rbac
    from apps.workspaces.models import WorkspaceMember

    _point_at_live_engine(settings)
    workspace, campaign = _rich_campaign()
    seed_rbac()
    role = Role.objects.get(workspace__isnull=True, key="owner")
    WorkspaceMember.objects.create(
        workspace=workspace, user=owner, role=role, role_key="owner",
        status=WorkspaceMember.Status.ACTIVE, joined_at=now(),
    )

    with caplog.at_level(logging.INFO):
        resp = client_for(owner).post(
            f"/api/v1/campaigns/{campaign.id}/intelligence/",
            **{"HTTP_X_WORKSPACE_ID": str(workspace.id)},
        )

    assert resp.status_code == 200
    body = resp.data
    assert body["source"] == "engine"
    for key in ("analysis", "scores", "grade", "moments", "recommendations", "summary"):
        assert key in body["result"], key
    assert TOKEN not in caplog.text
