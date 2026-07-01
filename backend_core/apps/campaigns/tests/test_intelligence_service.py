"""Unit tests for the campaign intelligence domain service.

The Intelligence Engine client is injected (a stub or a client raising the real
typed errors), so no HTTP happens. Covers success, not-found, cross-workspace
isolation, disabled, dry-run and every client error mapping.
"""

import uuid

import pytest

from apps.campaigns.intelligence_service import (
    CampaignIntelligenceService,
    CampaignNotFoundError,
    IntelligenceDisabledError,
    IntelligenceUnavailableError,
    IntelligenceUpstreamError,
    get_campaign_intelligence,
)
from apps.integrations_bridge.intelligence_sync import (
    IntelligenceEngineProtocolError,
    IntelligenceEngineResponseError,
    IntelligenceEngineTimeout,
    IntelligenceEngineUnavailable,
    IntelligenceResult,
)
from tests import factories

pytestmark = pytest.mark.django_db


# --------------------------------------------------------------------------- #
# Stub client
# --------------------------------------------------------------------------- #
class StubClient:
    def __init__(self, *, result=None, exc=None):
        self._result = result
        self._exc = exc
        self.calls = []

    def post_campaign_intelligence(self, payload, *, workspace_id, request_id):
        self.calls.append(
            {"payload": payload, "workspace_id": workspace_id, "request_id": request_id}
        )
        if self._exc is not None:
            raise self._exc
        return self._result


def _ok_result():
    return IntelligenceResult(
        status="completed",
        engine="intelligence_engine",
        engine_version="0.1.0",
        request_id="echoed",
        workspace_id="echoed",
        result={
            "analysis": {"campaign_health": "good"},
            "scores": {"priority_score": 48},
            "grade": "A",
            "moments": [],
            "recommendations": [],
            "summary": "ok",
        },
        explanations=[{"code": "x", "weight": 0.2}],
        warnings=[],
        metadata={"generated_at": None, "payload_version": "1.0"},
        raw={},
    )


# --------------------------------------------------------------------------- #
# Success
# --------------------------------------------------------------------------- #
class TestSuccess:
    def test_returns_engine_outcome(self):
        campaign = factories.CampaignFactory()
        client = StubClient(result=_ok_result())
        outcome = get_campaign_intelligence(
            workspace=campaign.workspace, campaign=campaign, client=client
        )
        assert outcome.source == "engine"
        assert outcome.status == "completed"
        assert outcome.result["grade"] == "A"
        assert outcome.engine_version == "0.1.0"
        assert outcome.campaign_id == str(campaign.id)
        # generated_at is stamped by Django (engine returns null).
        assert outcome.generated_at

    def test_propagates_request_id_and_workspace(self):
        campaign = factories.CampaignFactory()
        rid = uuid.uuid4().hex
        client = StubClient(result=_ok_result())
        outcome = get_campaign_intelligence(
            workspace=campaign.workspace, campaign=campaign,
            request_id=rid, client=client,
        )
        assert outcome.request_id == rid
        call = client.calls[0]
        assert call["request_id"] == rid
        assert call["workspace_id"] == str(campaign.workspace.id)
        # The built payload carries the same identifiers.
        assert call["payload"]["request_id"] == rid
        assert call["payload"]["workspace_id"] == str(campaign.workspace.id)
        assert call["payload"]["entity"] == {"type": "campaign", "id": str(campaign.id)}

    def test_as_dict_shape(self):
        campaign = factories.CampaignFactory()
        outcome = get_campaign_intelligence(
            workspace=campaign.workspace, campaign=campaign,
            client=StubClient(result=_ok_result()),
        )
        d = outcome.as_dict()
        assert set(d) == {
            "status", "source", "engine", "engine_version", "request_id",
            "workspace_id", "campaign_id", "result", "explanations",
            "warnings", "metadata", "generated_at",
        }

    def test_accepts_campaign_id(self):
        campaign = factories.CampaignFactory()
        outcome = get_campaign_intelligence(
            workspace=campaign.workspace, campaign_id=campaign.id,
            client=StubClient(result=_ok_result()),
        )
        assert outcome.campaign_id == str(campaign.id)


# --------------------------------------------------------------------------- #
# Loading / isolation
# --------------------------------------------------------------------------- #
class TestLoadingAndIsolation:
    def test_missing_campaign_raises_not_found(self):
        workspace = factories.WorkspaceFactory()
        with pytest.raises(CampaignNotFoundError):
            get_campaign_intelligence(
                workspace=workspace, campaign_id=uuid.uuid4(),
                client=StubClient(result=_ok_result()),
            )

    def test_cross_workspace_is_not_found(self):
        campaign = factories.CampaignFactory()
        other_workspace = factories.WorkspaceFactory()
        with pytest.raises(CampaignNotFoundError):
            get_campaign_intelligence(
                workspace=other_workspace, campaign_id=campaign.id,
                client=StubClient(result=_ok_result()),
            )

    def test_soft_deleted_campaign_is_not_found(self):
        campaign = factories.CampaignFactory()
        campaign.soft_delete()
        with pytest.raises(CampaignNotFoundError):
            get_campaign_intelligence(
                workspace=campaign.workspace, campaign_id=campaign.id,
                client=StubClient(result=_ok_result()),
            )

    def test_missing_identifier_raises_value_error(self):
        workspace = factories.WorkspaceFactory()
        with pytest.raises(ValueError):
            CampaignIntelligenceService(workspace=workspace).run()


# --------------------------------------------------------------------------- #
# Switches
# --------------------------------------------------------------------------- #
class TestSwitches:
    def test_disabled_raises_and_does_not_call_client(self, settings):
        settings.INTELLIGENCE_ENGINE_ENABLED = False
        campaign = factories.CampaignFactory()
        client = StubClient(result=_ok_result())
        with pytest.raises(IntelligenceDisabledError):
            get_campaign_intelligence(
                workspace=campaign.workspace, campaign=campaign, client=client
            )
        assert client.calls == []

    def test_dry_run_returns_stub_without_calling_client(self, settings):
        settings.INTELLIGENCE_ENGINE_ENABLED = True
        settings.INTELLIGENCE_ENGINE_DRY_RUN = True
        campaign = factories.CampaignFactory()
        client = StubClient(result=_ok_result())
        outcome = get_campaign_intelligence(
            workspace=campaign.workspace, campaign=campaign, client=client
        )
        assert outcome.source == "dry_run"
        assert outcome.status == "completed"
        assert outcome.warnings[0]["code"] == "dry_run"
        assert outcome.metadata == {"dry_run": True}
        assert client.calls == []  # no real call


# --------------------------------------------------------------------------- #
# Client error mapping
# --------------------------------------------------------------------------- #
class TestErrorMapping:
    def _run(self, exc):
        campaign = factories.CampaignFactory()
        return get_campaign_intelligence(
            workspace=campaign.workspace, campaign=campaign,
            client=StubClient(exc=exc),
        )

    def test_timeout_maps_to_unavailable(self):
        with pytest.raises(IntelligenceUnavailableError):
            self._run(IntelligenceEngineTimeout("t"))

    def test_unavailable_maps_to_unavailable(self):
        with pytest.raises(IntelligenceUnavailableError):
            self._run(IntelligenceEngineUnavailable("u"))

    def test_500_maps_to_unavailable(self):
        with pytest.raises(IntelligenceUnavailableError):
            self._run(IntelligenceEngineResponseError(500, error_code="internal_error"))

    def test_403_maps_to_upstream(self):
        with pytest.raises(IntelligenceUpstreamError):
            self._run(
                IntelligenceEngineResponseError(403, error_code="unauthorized_internal_request")
            )

    def test_422_maps_to_upstream(self):
        with pytest.raises(IntelligenceUpstreamError):
            self._run(IntelligenceEngineResponseError(422, error_code="invalid_payload"))

    def test_protocol_error_maps_to_upstream(self):
        with pytest.raises(IntelligenceUpstreamError):
            self._run(IntelligenceEngineProtocolError("bad json"))


# --------------------------------------------------------------------------- #
# Logging / security
# --------------------------------------------------------------------------- #
class TestLogging:
    def test_token_not_in_logs(self, settings, caplog):
        settings.INTELLIGENCE_ENGINE_INTERNAL_TOKEN = "super-secret-token"
        campaign = factories.CampaignFactory()
        with caplog.at_level("INFO"):
            get_campaign_intelligence(
                workspace=campaign.workspace, campaign=campaign,
                client=StubClient(result=_ok_result()),
            )
        assert "super-secret-token" not in caplog.text

    def test_logs_domain_context(self, caplog):
        campaign = factories.CampaignFactory()
        with caplog.at_level("INFO", logger="campaigns.intelligence"):
            get_campaign_intelligence(
                workspace=campaign.workspace, campaign=campaign,
                client=StubClient(result=_ok_result()),
            )
        assert f"campaign_id={campaign.id}" in caplog.text
        assert "event=ok" in caplog.text
