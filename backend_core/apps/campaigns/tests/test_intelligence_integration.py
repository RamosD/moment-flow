"""End-to-end integration tests for campaign intelligence (HTTP mocked).

Unlike the unit tests (which stub the service or the client in isolation), these
drive the **full stack** through the public API:

    POST /api/v1/campaigns/{id}/intelligence/
      → CampaignViewSet (auth + RBAC + workspace)
      → CampaignIntelligenceService (real)
      → CampaignIntelligencePayloadBuilder (real, reads real models)
      → IntelligenceEngineClient (real) → **fake HTTP transport (opener)**
      → normalized response

Only the HTTP transport is mocked: the factory ``build_intelligence_engine_client``
is monkeypatched to return a real client wired to a capturing ``opener``, so the
exact outbound payload and headers can be asserted against the contract.
"""

import io
import json
import logging
import urllib.error
from datetime import date

import pytest

from apps.campaigns.models import Campaign, CampaignGoal
from apps.campaigns.tests.conftest import ws_header
from apps.links.models import SmartLink, SmartLinkClick
from apps.reports.models import MediaKit, Report
from tests import factories

pytestmark = pytest.mark.django_db

TOKEN = "e2e-secret-token"
URL_HOST = "http://intelligence:8001"


# --------------------------------------------------------------------------- #
# Fake HTTP transport
# --------------------------------------------------------------------------- #
class FakeResponse:
    def __init__(self, body="{}", status=200):
        self._body = body.encode() if isinstance(body, str) else body
        self.status = status

    def read(self):
        return self._body


class CapturingOpener:
    """Captures the outbound request, then returns a body or raises ``exc``."""

    def __init__(self, *, body=None, status=200, exc=None):
        self.body = body if body is not None else "{}"
        self.status = status
        self.exc = exc
        self.request = None
        self.timeout = None
        self.calls = 0

    def __call__(self, request, timeout):
        self.calls += 1
        self.request = request
        self.timeout = timeout
        if self.exc is not None:
            raise self.exc
        return FakeResponse(self.body, self.status)

    # Convenience accessors for assertions.
    def sent_payload(self):
        return json.loads(self.request.data.decode("utf-8"))

    def sent_headers(self):
        return {k.lower(): v for k, v in self.request.header_items()}


def _http_error(status, body):
    return urllib.error.HTTPError(
        f"{URL_HOST}/intelligence/campaign", status, "err", {},
        io.BytesIO(body.encode() if isinstance(body, str) else body),
    )


def _install_engine(monkeypatch, opener, *, timeout=5):
    """Swap only the transport: real client + builder + service, fake opener."""
    from apps.integrations_bridge.intelligence_sync import IntelligenceEngineClient

    def factory(**_kwargs):
        return IntelligenceEngineClient(
            URL_HOST, timeout, internal_token=TOKEN, opener=opener,
            max_retries=0, retry_backoff=0,
        )

    monkeypatch.setattr(
        "apps.campaigns.intelligence_service.build_intelligence_engine_client",
        factory,
    )


# --------------------------------------------------------------------------- #
# Engine envelopes
# --------------------------------------------------------------------------- #
def _completed_envelope(**overrides):
    envelope = {
        "status": "completed",
        "engine": "intelligence_engine",
        "engine_version": "0.1.0",
        "request_id": "echoed-by-engine",
        "workspace_id": "echoed-by-engine",
        "result": {
            "analysis": {"campaign_health": "good", "summary": "…"},
            "scores": {"campaign_readiness_score": 100, "priority_score": 48},
            "grade": "A",
            "moments": [{"type": "release_window", "severity": "high"}],
            "recommendations": [{"action": "create_release_post", "priority": "high"}],
            "summary": "Campaign health 'good', grade A.",
        },
        "explanations": [{"code": "campaign_readiness_score", "weight": 0.2}],
        "warnings": [],
        "metadata": {"generated_at": None, "payload_version": "1.0"},
    }
    envelope.update(overrides)
    return envelope


def _error_envelope(code, message="bad"):
    return json.dumps(
        {
            "status": "failed",
            "error": {"code": code, "message": message, "details": {}},
            "metadata": {"engine": "intelligence_engine", "engine_version": "0.1.0"},
        }
    )


# --------------------------------------------------------------------------- #
# Test data + request helpers
# --------------------------------------------------------------------------- #
def _campaign_with_data(workspace, artist):
    track = factories.TrackFactory(artist=artist, release_date=date(2026, 6, 25))
    campaign = Campaign.objects.create(
        workspace=workspace, artist=artist, track=track, name="E2E", slug="e2e",
        primary_goal="grow",
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
    return campaign


def _url(campaign_id):
    return f"/api/v1/campaigns/{campaign_id}/intelligence/"


def _post(client, campaign, workspace):
    return client.post(_url(campaign.id), **ws_header(workspace))


# --------------------------------------------------------------------------- #
# Success — full completed response + outbound payload/headers
# --------------------------------------------------------------------------- #
class TestCompletedFlow:
    def test_completed_full_response_and_outbound_contract(
        self, monkeypatch, client_for, owner, workspace, make_artist
    ):
        artist = make_artist(workspace)
        campaign = _campaign_with_data(workspace, artist)
        opener = CapturingOpener(body=json.dumps(_completed_envelope()))
        _install_engine(monkeypatch, opener)

        resp = _post(client_for(owner), campaign, workspace)

        # --- response: all engine blocks present ---
        assert resp.status_code == 200
        body = resp.data
        assert body["source"] == "engine"
        assert body["engine_version"] == "0.1.0"
        assert body["generated_at"]
        result = body["result"]
        for key in ("analysis", "scores", "grade", "moments", "recommendations", "summary"):
            assert key in result, key
        assert result["grade"] == "A"
        assert body["explanations"] and "warnings" in body and "metadata" in body

        # --- the engine was actually called exactly once over the fake transport ---
        assert opener.calls == 1
        assert opener.timeout == 5  # configured timeout applied

        # --- outbound headers (internal auth + correlation) ---
        headers = opener.sent_headers()
        assert headers["x-internal-token"] == TOKEN
        assert headers["x-workspace-id"] == str(workspace.id)
        assert headers["content-type"] == "application/json"

        # --- outbound payload is contract-compatible (§7) ---
        payload = opener.sent_payload()
        assert payload["payload_version"] == "1.0"
        assert payload["workspace_id"] == str(workspace.id)
        assert payload["entity"] == {"type": "campaign", "id": str(campaign.id)}
        assert "reference_date" in payload["context"]
        assert set(payload["data"]) >= {
            "campaign", "artist", "track", "smart_link_stats",
            "content_outputs", "previous_reports", "reports", "media_kits", "goals",
        }
        assert payload["data"]["campaign"]["id"] == str(campaign.id)
        assert payload["data"]["smart_link_stats"]["active_links"] == 1
        assert payload["data"]["previous_reports"]  # non-empty

        # --- request_id consistent across body, header and response ---
        rid = payload["request_id"]
        assert rid and headers["x-request-id"] == rid
        assert body["request_id"] == rid

    def test_warnings_unknown_scores_and_wait_for_more_data(
        self, monkeypatch, client_for, owner, workspace, make_artist
    ):
        artist = make_artist(workspace)
        campaign = Campaign.objects.create(
            workspace=workspace, artist=artist, name="Min", slug="min"
        )
        envelope = _completed_envelope(
            result={
                "analysis": {"campaign_health": "unknown"},
                "scores": {"priority_score": None, "campaign_readiness_score": None},
                "grade": "unknown",
                "moments": [],
                "recommendations": [{"action": "wait_for_more_data", "priority": "low"}],
                "summary": "Insufficient data.",
            },
            warnings=[{"code": "insufficient_data", "message": "…"}],
        )
        opener = CapturingOpener(body=json.dumps(envelope))
        _install_engine(monkeypatch, opener)

        resp = _post(client_for(owner), campaign, workspace)

        assert resp.status_code == 200
        result = resp.data["result"]
        assert result["grade"] == "unknown"
        assert result["scores"]["priority_score"] is None
        assert result["recommendations"][0]["action"] == "wait_for_more_data"
        assert resp.data["warnings"][0]["code"] == "insufficient_data"
        # Minimal campaign still produces a contract-valid payload (track is null).
        assert opener.sent_payload()["data"]["track"] is None


# --------------------------------------------------------------------------- #
# Failure modes — mapped end-to-end to HTTP status
# --------------------------------------------------------------------------- #
class TestFailureModes:
    def _campaign(self, workspace, make_artist):
        artist = make_artist(workspace)
        return Campaign.objects.create(
            workspace=workspace, artist=artist, name="F", slug="f"
        )

    def test_timeout_returns_503(
        self, monkeypatch, client_for, owner, workspace, make_artist
    ):
        campaign = self._campaign(workspace, make_artist)
        _install_engine(monkeypatch, CapturingOpener(exc=TimeoutError()))
        assert _post(client_for(owner), campaign, workspace).status_code == 503

    def test_connection_refused_returns_503(
        self, monkeypatch, client_for, owner, workspace, make_artist
    ):
        campaign = self._campaign(workspace, make_artist)
        _install_engine(
            monkeypatch, CapturingOpener(exc=urllib.error.URLError("refused"))
        )
        assert _post(client_for(owner), campaign, workspace).status_code == 503

    def test_403_returns_502(
        self, monkeypatch, client_for, owner, workspace, make_artist
    ):
        campaign = self._campaign(workspace, make_artist)
        _install_engine(
            monkeypatch,
            CapturingOpener(exc=_http_error(403, _error_envelope("unauthorized_internal_request"))),
        )
        assert _post(client_for(owner), campaign, workspace).status_code == 502

    def test_422_returns_502(
        self, monkeypatch, client_for, owner, workspace, make_artist
    ):
        campaign = self._campaign(workspace, make_artist)
        _install_engine(
            monkeypatch,
            CapturingOpener(exc=_http_error(422, _error_envelope("invalid_payload"))),
        )
        assert _post(client_for(owner), campaign, workspace).status_code == 502

    def test_5xx_returns_503(
        self, monkeypatch, client_for, owner, workspace, make_artist
    ):
        campaign = self._campaign(workspace, make_artist)
        _install_engine(
            monkeypatch,
            CapturingOpener(exc=_http_error(500, _error_envelope("internal_error"))),
        )
        assert _post(client_for(owner), campaign, workspace).status_code == 503

    def test_invalid_json_returns_502(
        self, monkeypatch, client_for, owner, workspace, make_artist
    ):
        campaign = self._campaign(workspace, make_artist)
        _install_engine(monkeypatch, CapturingOpener(body="not-json"))
        assert _post(client_for(owner), campaign, workspace).status_code == 502


# --------------------------------------------------------------------------- #
# Switches — no HTTP call
# --------------------------------------------------------------------------- #
class TestSwitches:
    def test_disabled_returns_503_without_http(
        self, settings, monkeypatch, client_for, owner, workspace, make_artist
    ):
        settings.INTELLIGENCE_ENGINE_ENABLED = False
        artist = make_artist(workspace)
        campaign = Campaign.objects.create(
            workspace=workspace, artist=artist, name="D", slug="d"
        )
        opener = CapturingOpener(body=json.dumps(_completed_envelope()))
        _install_engine(monkeypatch, opener)
        resp = _post(client_for(owner), campaign, workspace)
        assert resp.status_code == 503
        assert opener.calls == 0  # never reaches the transport

    def test_dry_run_returns_stub_without_http(
        self, settings, monkeypatch, client_for, owner, workspace, make_artist
    ):
        settings.INTELLIGENCE_ENGINE_ENABLED = True
        settings.INTELLIGENCE_ENGINE_DRY_RUN = True
        artist = make_artist(workspace)
        campaign = _campaign_with_data(workspace, artist)
        opener = CapturingOpener(body=json.dumps(_completed_envelope()))
        _install_engine(monkeypatch, opener)
        resp = _post(client_for(owner), campaign, workspace)
        assert resp.status_code == 200
        assert resp.data["source"] == "dry_run"
        assert opener.calls == 0  # builder ran, but no real call


# --------------------------------------------------------------------------- #
# RBAC / workspace still enforced through the full stack
# --------------------------------------------------------------------------- #
class TestAccessControlStillEnforced:
    def test_permission_denied_without_view(
        self, monkeypatch, client_for, make_user, workspace, make_artist, add_member
    ):
        artist = make_artist(workspace)
        campaign = Campaign.objects.create(
            workspace=workspace, artist=artist, name="P", slug="p"
        )
        opener = CapturingOpener(body=json.dumps(_completed_envelope()))
        _install_engine(monkeypatch, opener)
        user = make_user("nobody@example.com")
        add_member(workspace, user, "billing_admin")  # no campaigns:view
        resp = _post(client_for(user), campaign, workspace)
        assert resp.status_code == 403
        assert opener.calls == 0

    def test_cross_workspace_is_404(
        self, monkeypatch, client_for, owner, workspace, other_workspace, make_artist
    ):
        other_artist = make_artist(other_workspace)
        other_campaign = Campaign.objects.create(
            workspace=other_workspace, artist=other_artist, name="X", slug="x"
        )
        opener = CapturingOpener(body=json.dumps(_completed_envelope()))
        _install_engine(monkeypatch, opener)
        resp = client_for(owner).post(_url(other_campaign.id), **ws_header(workspace))
        assert resp.status_code == 404
        assert opener.calls == 0


# --------------------------------------------------------------------------- #
# Security / observability
# --------------------------------------------------------------------------- #
class TestSecurity:
    def test_token_not_in_logs_and_ids_present(
        self, monkeypatch, caplog, client_for, owner, workspace, make_artist
    ):
        artist = make_artist(workspace)
        campaign = _campaign_with_data(workspace, artist)
        _install_engine(
            monkeypatch, CapturingOpener(body=json.dumps(_completed_envelope()))
        )
        with caplog.at_level(logging.INFO):
            resp = _post(client_for(owner), campaign, workspace)
        assert resp.status_code == 200
        # The shared secret never appears in any log line.
        assert TOKEN not in caplog.text
        # Correlation fields are present for diagnosis.
        assert f"workspace_id={workspace.id}" in caplog.text
        assert f"campaign_id={campaign.id}" in caplog.text
