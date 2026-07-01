"""API tests for POST /api/v1/campaigns/{id}/intelligence/.

Auth, RBAC and workspace isolation are exercised against the real viewset. The
domain service is either driven through its real dry-run/disabled paths (no HTTP)
or monkeypatched to return a rich outcome / raise mapped errors.
"""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.campaigns.intelligence_service import (
    CampaignIntelligenceOutcome,
    CampaignNotFoundError,
    IntelligenceUnavailableError,
    IntelligenceUpstreamError,
)
from apps.campaigns.models import Campaign
from apps.campaigns.tests.conftest import ws_header

pytestmark = pytest.mark.django_db


def _make_campaign(workspace, artist, name="C1"):
    return Campaign.objects.create(
        workspace=workspace, artist=artist, name=name, slug=name.lower()
    )


def _url(campaign_id):
    return f"/api/v1/campaigns/{campaign_id}/intelligence/"


def _rich_outcome(campaign):
    return CampaignIntelligenceOutcome(
        status="completed",
        source="engine",
        request_id="req-1",
        workspace_id=str(campaign.workspace_id),
        campaign_id=str(campaign.id),
        result={
            "analysis": {"campaign_health": "good"},
            "scores": {"priority_score": 48},
            "grade": "A",
            "moments": [{"type": "release_window"}],
            "recommendations": [{"action": "create_release_post"}],
            "summary": "Looking good.",
        },
        engine="intelligence_engine",
        engine_version="0.1.0",
        explanations=[{"code": "campaign_readiness_score", "weight": 0.2}],
        warnings=[],
        metadata={"payload_version": "1.0"},
        generated_at="2026-06-25T00:00:00+00:00",
    )


# --------------------------------------------------------------------------- #
# Success
# --------------------------------------------------------------------------- #
class TestSuccess:
    def test_success_returns_engine_blocks(
        self, monkeypatch, client_for, owner, workspace, make_artist
    ):
        artist = make_artist(workspace)
        campaign = _make_campaign(workspace, artist)
        captured = {}

        def fake_service(*, workspace, campaign, requested_by):
            captured["workspace"] = workspace
            captured["campaign"] = campaign
            captured["requested_by"] = requested_by
            return _rich_outcome(campaign)

        monkeypatch.setattr(
            "apps.campaigns.views.get_campaign_intelligence", fake_service
        )

        client = client_for(owner)
        resp = client.post(_url(campaign.id), **ws_header(workspace))

        assert resp.status_code == 200
        body = resp.data
        assert body["source"] == "engine"
        assert body["generated_at"]
        for key in ("analysis", "scores", "grade", "moments", "recommendations", "summary"):
            assert key in body["result"], key
        assert body["result"]["grade"] == "A"
        assert "explanations" in body and "warnings" in body and "metadata" in body
        # The endpoint passed the scoped campaign and the authenticated user.
        assert captured["campaign"].id == campaign.id
        assert captured["workspace"].id == workspace.id
        assert captured["requested_by"] == owner

    def test_dry_run_real_path(
        self, settings, client_for, owner, workspace, make_artist
    ):
        settings.INTELLIGENCE_ENGINE_ENABLED = True
        settings.INTELLIGENCE_ENGINE_DRY_RUN = True
        artist = make_artist(workspace)
        campaign = _make_campaign(workspace, artist)

        resp = client_for(owner).post(_url(campaign.id), **ws_header(workspace))

        assert resp.status_code == 200
        assert resp.data["source"] == "dry_run"
        assert resp.data["warnings"][0]["code"] == "dry_run"
        # Result block keys are present even in dry-run.
        for key in ("analysis", "scores", "grade", "moments", "recommendations", "summary"):
            assert key in resp.data["result"], key


# --------------------------------------------------------------------------- #
# Auth / RBAC / workspace
# --------------------------------------------------------------------------- #
class TestAccessControl:
    def test_requires_authentication(self, workspace, make_artist):
        artist = make_artist(workspace)
        campaign = _make_campaign(workspace, artist)
        resp = APIClient().post(_url(campaign.id), **ws_header(workspace))
        assert resp.status_code == 401

    def test_permission_denied_without_view_perm(
        self, client_for, make_user, workspace, make_artist, add_member
    ):
        artist = make_artist(workspace)
        campaign = _make_campaign(workspace, artist)
        user = make_user("billing@example.com")
        add_member(workspace, user, "billing_admin")  # no campaigns:view

        resp = client_for(user).post(_url(campaign.id), **ws_header(workspace))
        assert resp.status_code == 403

    def test_missing_workspace_header_is_400(
        self, client_for, owner, workspace, make_artist
    ):
        artist = make_artist(workspace)
        campaign = _make_campaign(workspace, artist)
        resp = client_for(owner).post(_url(campaign.id))  # no X-Workspace-ID
        assert resp.status_code == 400

    def test_campaign_not_found(self, client_for, owner, workspace):
        resp = client_for(owner).post(_url(uuid.uuid4()), **ws_header(workspace))
        assert resp.status_code == 404

    def test_cross_workspace_is_not_found(
        self, client_for, owner, workspace, other_workspace, make_artist
    ):
        # Campaign lives in another workspace; requesting it under the caller's
        # workspace must 404 (never leak its existence).
        other_artist = make_artist(other_workspace)
        other_campaign = _make_campaign(other_workspace, other_artist, name="OtherC")
        resp = client_for(owner).post(
            _url(other_campaign.id), **ws_header(workspace)
        )
        assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Engine failures (mapped status codes)
# --------------------------------------------------------------------------- #
class TestEngineFailures:
    def _setup(self, make_artist, workspace):
        artist = make_artist(workspace)
        return _make_campaign(workspace, artist)

    def test_disabled_returns_503(
        self, settings, client_for, owner, workspace, make_artist
    ):
        settings.INTELLIGENCE_ENGINE_ENABLED = False
        campaign = self._setup(make_artist, workspace)
        resp = client_for(owner).post(_url(campaign.id), **ws_header(workspace))
        assert resp.status_code == 503
        assert resp.data["detail"].code == "intelligence_disabled"

    def test_unavailable_returns_503(
        self, monkeypatch, client_for, owner, workspace, make_artist
    ):
        campaign = self._setup(make_artist, workspace)

        def boom(**kwargs):
            raise IntelligenceUnavailableError("down")

        monkeypatch.setattr("apps.campaigns.views.get_campaign_intelligence", boom)
        resp = client_for(owner).post(_url(campaign.id), **ws_header(workspace))
        assert resp.status_code == 503

    def test_upstream_returns_502(
        self, monkeypatch, client_for, owner, workspace, make_artist
    ):
        campaign = self._setup(make_artist, workspace)

        def boom(**kwargs):
            raise IntelligenceUpstreamError("bad payload")

        monkeypatch.setattr("apps.campaigns.views.get_campaign_intelligence", boom)
        resp = client_for(owner).post(_url(campaign.id), **ws_header(workspace))
        assert resp.status_code == 502

    def test_service_not_found_returns_404(
        self, monkeypatch, client_for, owner, workspace, make_artist
    ):
        campaign = self._setup(make_artist, workspace)

        def boom(**kwargs):
            raise CampaignNotFoundError("gone")

        monkeypatch.setattr("apps.campaigns.views.get_campaign_intelligence", boom)
        resp = client_for(owner).post(_url(campaign.id), **ws_header(workspace))
        assert resp.status_code == 404
