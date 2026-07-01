"""Tests for the `smoke_intelligence_engine` management command.

These run in the normal suite (NOT opt-in): the live Intelligence Engine is
replaced by a fake client, so no real network call happens. They verify the
command's config validation, the response-contract check, controlled failure
when the engine is unavailable, and that the internal token never appears in the
output. The opt-in pytest test (`test_intelligence_real_loop.py`) covers the real
loop end to end.
"""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.integrations_bridge.intelligence_sync import (
    IntelligenceEngineResponseError,
    IntelligenceEngineUnavailable,
    IntelligenceResult,
)

COMMAND = "smoke_intelligence_engine"
FACTORY = (
    "apps.campaigns.management.commands.smoke_intelligence_engine"
    ".build_intelligence_engine_client"
)

SMOKE_TOKEN = "smoke-token-do-not-log"


def _completed_envelope(workspace_id, request_id):
    return {
        "status": "completed",
        "engine": "intelligence_engine",
        "engine_version": "0.1.0",
        "request_id": request_id,
        "workspace_id": workspace_id,
        "result": {
            "analysis": {"campaign_health": "good"},
            "scores": {"priority_score": 48},
            "grade": "A",
            "moments": [{"type": "release_window"}],
            "recommendations": [{"action": "create_release_post"}],
            "summary": "Looking good.",
        },
        "explanations": [],
        "warnings": [],
        "metadata": {"payload_version": "1.0"},
    }


class _FakeClient:
    """Stands in for IntelligenceEngineClient; records what it was called with."""

    def __init__(self, *, result=None, raises=None):
        self._result = result
        self._raises = raises
        self.captured = None

    def post_campaign_intelligence(self, payload, *, workspace_id, request_id):
        self.captured = {
            "payload": payload,
            "workspace_id": workspace_id,
            "request_id": request_id,
        }
        if self._raises is not None:
            raise self._raises
        return self._result or IntelligenceResult.from_envelope(
            _completed_envelope(workspace_id, request_id)
        )


def _enable_real_loop(settings, token=SMOKE_TOKEN):
    settings.INTELLIGENCE_ENGINE_BASE_URL = "http://127.0.0.1:8001"
    settings.INTELLIGENCE_ENGINE_ENABLED = True
    settings.INTELLIGENCE_ENGINE_DRY_RUN = False
    settings.INTELLIGENCE_ENGINE_INTERNAL_TOKEN = token


# --------------------------------------------------------------------------- #
# Config validation (no client built — fails before any call)
# --------------------------------------------------------------------------- #
class TestConfigValidation:
    def test_disabled_engine_is_rejected(self, settings):
        _enable_real_loop(settings)
        settings.INTELLIGENCE_ENGINE_ENABLED = False
        with pytest.raises(CommandError, match="ENABLED is False"):
            call_command(COMMAND, stdout=StringIO())

    def test_dry_run_is_rejected(self, settings):
        _enable_real_loop(settings)
        settings.INTELLIGENCE_ENGINE_DRY_RUN = True
        with pytest.raises(CommandError, match="DRY_RUN is True"):
            call_command(COMMAND, stdout=StringIO())

    def test_empty_token_is_rejected(self, settings):
        _enable_real_loop(settings, token="")
        with pytest.raises(CommandError, match="is empty"):
            call_command(COMMAND, stdout=StringIO())

    def test_empty_base_url_is_rejected(self, settings):
        _enable_real_loop(settings)
        settings.INTELLIGENCE_ENGINE_BASE_URL = ""
        with pytest.raises(CommandError, match="BASE_URL is empty"):
            call_command(COMMAND, stdout=StringIO())

    def test_invalid_reference_date_is_rejected(self, settings):
        _enable_real_loop(settings)
        with pytest.raises(CommandError, match="Invalid --reference-date"):
            call_command(COMMAND, "--reference-date", "not-a-date", stdout=StringIO())


# --------------------------------------------------------------------------- #
# Success (fake client returns the six blocks)
# --------------------------------------------------------------------------- #
class TestSuccess:
    def test_reports_success_and_six_keys(self, settings, monkeypatch):
        _enable_real_loop(settings)
        fake = _FakeClient()
        monkeypatch.setattr(FACTORY, lambda: fake)

        out = StringIO()
        call_command(COMMAND, "--reference-date", "2026-06-25", stdout=out)
        output = out.getvalue()

        assert "smoke_ie ok" in output
        for key in ("analysis", "scores", "grade", "moments", "recommendations", "summary"):
            assert key in output
        assert '"grade": "A"' in output
        # The synthetic envelope is well-formed and carries the smoke identifiers.
        payload = fake.captured["payload"]
        assert payload["payload_version"] == "1.0"
        assert payload["entity"]["type"] == "campaign"
        assert fake.captured["workspace_id"] == "smoke-workspace"
        assert payload["context"]["reference_date"] == "2026-06-25"

    def test_token_never_printed(self, settings, monkeypatch):
        _enable_real_loop(settings)
        monkeypatch.setattr(FACTORY, lambda: _FakeClient())

        out, err = StringIO(), StringIO()
        call_command(COMMAND, stdout=out, stderr=err)

        assert SMOKE_TOKEN not in out.getvalue()
        assert SMOKE_TOKEN not in err.getvalue()
        # The redacted config line reports presence, not the value.
        assert "token=configured" in out.getvalue()

    def test_unexpected_status_is_reported(self, settings, monkeypatch):
        _enable_real_loop(settings)
        envelope = _completed_envelope("smoke-workspace", "req")
        envelope["status"] = "failed"
        fake = _FakeClient(result=IntelligenceResult.from_envelope(envelope))
        monkeypatch.setattr(FACTORY, lambda: fake)
        with pytest.raises(CommandError, match="Unexpected engine status"):
            call_command(COMMAND, stdout=StringIO())

    def test_missing_keys_is_reported(self, settings, monkeypatch):
        _enable_real_loop(settings)
        envelope = _completed_envelope("smoke-workspace", "req")
        del envelope["result"]["summary"]
        fake = _FakeClient(result=IntelligenceResult.from_envelope(envelope))
        monkeypatch.setattr(FACTORY, lambda: fake)
        with pytest.raises(CommandError, match="missing expected keys"):
            call_command(COMMAND, stdout=StringIO())


# --------------------------------------------------------------------------- #
# Controlled failure when the engine is unavailable
# --------------------------------------------------------------------------- #
class TestControlledFailure:
    def test_unavailable_is_controlled(self, settings, monkeypatch):
        _enable_real_loop(settings)
        fake = _FakeClient(raises=IntelligenceEngineUnavailable("engine down"))
        monkeypatch.setattr(FACTORY, lambda: fake)

        with pytest.raises(CommandError, match="Smoke failed") as excinfo:
            call_command(COMMAND, stdout=StringIO())
        # Controlled message, no token leaked.
        assert SMOKE_TOKEN not in str(excinfo.value)

    def test_http_error_is_controlled(self, settings, monkeypatch):
        _enable_real_loop(settings)
        fake = _FakeClient(
            raises=IntelligenceEngineResponseError(403, error_code="unauthorized_internal_request")
        )
        monkeypatch.setattr(FACTORY, lambda: fake)

        with pytest.raises(CommandError, match="HTTP 403"):
            call_command(COMMAND, stdout=StringIO())
