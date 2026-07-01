"""Tests for the `smoke_content_renderer` management command.

These run in the normal suite (NOT opt-in): the renderer is replaced by a fake
HTTP client and a fake health probe, so no real network call happens. They verify
config validation, the health gate, the 202-acceptance check, controlled failures
(unavailable / timeout / 403 / unexpected status) and that the internal token
never appears in the output. The full callback loop is validated by the E2E
harness / checklist, not here.
"""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.integrations_bridge.clients import (
    InternalClientTimeout,
    InternalHTTPError,
    InternalResponse,
    InternalServiceUnavailable,
)
from apps.integrations_bridge.health import OK, UNAVAILABLE

COMMAND = "smoke_content_renderer"
MODULE = "apps.integrations_bridge.management.commands.smoke_content_renderer"

SMOKE_TOKEN = "renderer-token-do-not-log"


def _fake_probe(result):
    return lambda base_url, timeout: result


def _fake_client_class(*, response=None, raises=None, calls=None):
    class _FakeClient:
        def __init__(self, base_url, timeout):
            self.base_url = base_url
            self.timeout = timeout

        def post_json(self, path, payload, *, workspace_id, job_id, request_id):
            if calls is not None:
                calls.append(
                    {
                        "path": path,
                        "payload": payload,
                        "workspace_id": workspace_id,
                        "job_id": job_id,
                        "request_id": request_id,
                    }
                )
            if raises is not None:
                raise raises
            return response

    return _FakeClient


def _accepted_response():
    return InternalResponse(
        status_code=202,
        data={
            "status": "accepted",
            "job_id": "x",
            "metadata": {"renderer": "content_renderer", "renderer_version": "0.1.0"},
        },
    )


def _configure(settings, token=SMOKE_TOKEN):
    settings.CONTENT_RENDERER_BASE_URL = "http://127.0.0.1:8002"
    settings.INTERNAL_API_TOKEN = token


# --------------------------------------------------------------------------- #
# Config validation
# --------------------------------------------------------------------------- #
class TestConfigValidation:
    def test_empty_token_is_rejected(self, settings, monkeypatch):
        _configure(settings, token="")
        monkeypatch.setattr(f"{MODULE}.http_health_probe", _fake_probe((OK, 1, "")))
        with pytest.raises(CommandError, match="INTERNAL_API_TOKEN is empty"):
            call_command(COMMAND, stdout=StringIO())

    def test_unconfigured_base_url_is_rejected(self, settings):
        _configure(settings)
        settings.CONTENT_RENDERER_BASE_URL = ""
        with pytest.raises(CommandError, match="no base URL"):
            call_command(COMMAND, stdout=StringIO())


# --------------------------------------------------------------------------- #
# Health gate
# --------------------------------------------------------------------------- #
class TestHealthGate:
    def test_health_only_success_does_not_submit(self, settings, monkeypatch):
        _configure(settings)
        monkeypatch.setattr(f"{MODULE}.http_health_probe", _fake_probe((OK, 3, "")))
        calls = []
        monkeypatch.setattr(f"{MODULE}.InternalServiceClient", _fake_client_class(calls=calls))

        out = StringIO()
        call_command(COMMAND, "--health-only", stdout=out)
        assert "smoke_renderer ok (health-only)" in out.getvalue()
        assert calls == []  # no submission happened

    def test_health_unavailable_is_controlled(self, settings, monkeypatch):
        _configure(settings)
        monkeypatch.setattr(
            f"{MODULE}.http_health_probe", _fake_probe((UNAVAILABLE, 1, "connection_error"))
        )
        with pytest.raises(CommandError, match="Smoke failed"):
            call_command(COMMAND, stdout=StringIO())


# --------------------------------------------------------------------------- #
# Submission / 202 acceptance
# --------------------------------------------------------------------------- #
class TestSubmission:
    def test_submit_202_succeeds(self, settings, monkeypatch):
        _configure(settings)
        calls = []
        monkeypatch.setattr(f"{MODULE}.http_health_probe", _fake_probe((OK, 2, "")))
        monkeypatch.setattr(
            f"{MODULE}.InternalServiceClient",
            _fake_client_class(response=_accepted_response(), calls=calls),
        )

        out = StringIO()
        call_command(COMMAND, stdout=out)
        output = out.getvalue()
        assert "smoke_renderer ok" in output
        assert '"status_code": 202' in output
        assert '"ack_status": "accepted"' in output
        # A single, schema-valid envelope was submitted with consistent ids.
        assert len(calls) == 1
        envelope = calls[0]["payload"]
        assert set(envelope) == {
            "job_id", "workspace_id", "request_id", "job_type",
            "callback_url", "entity", "payload_version", "payload",
        }
        assert envelope["job_id"] == calls[0]["job_id"]
        assert envelope["workspace_id"] == calls[0]["workspace_id"]
        assert envelope["job_type"] == "content_generation"

    def test_token_never_printed(self, settings, monkeypatch):
        _configure(settings)
        monkeypatch.setattr(f"{MODULE}.http_health_probe", _fake_probe((OK, 2, "")))
        monkeypatch.setattr(
            f"{MODULE}.InternalServiceClient",
            _fake_client_class(response=_accepted_response()),
        )
        out, err = StringIO(), StringIO()
        call_command(COMMAND, stdout=out, stderr=err)
        assert SMOKE_TOKEN not in out.getvalue()
        assert SMOKE_TOKEN not in err.getvalue()
        assert "token=configured" in out.getvalue()

    def test_unexpected_2xx_status_is_reported(self, settings, monkeypatch):
        _configure(settings)
        monkeypatch.setattr(f"{MODULE}.http_health_probe", _fake_probe((OK, 2, "")))
        monkeypatch.setattr(
            f"{MODULE}.InternalServiceClient",
            _fake_client_class(response=InternalResponse(status_code=200, data={})),
        )
        with pytest.raises(CommandError, match="expected 202"):
            call_command(COMMAND, stdout=StringIO())

    def test_report_generation_job_type(self, settings, monkeypatch):
        # report_generation resolves the REPORT_RENDERER endpoint.
        settings.REPORT_RENDERER_BASE_URL = "http://127.0.0.1:8002"
        settings.INTERNAL_API_TOKEN = SMOKE_TOKEN
        calls = []
        monkeypatch.setattr(f"{MODULE}.http_health_probe", _fake_probe((OK, 2, "")))
        monkeypatch.setattr(
            f"{MODULE}.InternalServiceClient",
            _fake_client_class(response=_accepted_response(), calls=calls),
        )
        call_command(COMMAND, "--job-type", "report_generation", stdout=StringIO())
        assert calls[0]["payload"]["job_type"] == "report_generation"
        assert calls[0]["payload"]["entity"]["type"] == "report"


# --------------------------------------------------------------------------- #
# Controlled failures on submission
# --------------------------------------------------------------------------- #
class TestControlledFailure:
    def test_403_token_misaligned(self, settings, monkeypatch):
        _configure(settings)
        monkeypatch.setattr(f"{MODULE}.http_health_probe", _fake_probe((OK, 2, "")))
        monkeypatch.setattr(
            f"{MODULE}.InternalServiceClient",
            _fake_client_class(raises=InternalHTTPError(403, body="forbidden")),
        )
        with pytest.raises(CommandError, match="HTTP 403"):
            call_command(COMMAND, stdout=StringIO())

    def test_unavailable_is_controlled(self, settings, monkeypatch):
        _configure(settings)
        monkeypatch.setattr(f"{MODULE}.http_health_probe", _fake_probe((OK, 2, "")))
        monkeypatch.setattr(
            f"{MODULE}.InternalServiceClient",
            _fake_client_class(raises=InternalServiceUnavailable("down")),
        )
        with pytest.raises(CommandError, match="unavailable"):
            call_command(COMMAND, stdout=StringIO())

    def test_timeout_is_controlled(self, settings, monkeypatch):
        _configure(settings)
        monkeypatch.setattr(f"{MODULE}.http_health_probe", _fake_probe((OK, 2, "")))
        monkeypatch.setattr(
            f"{MODULE}.InternalServiceClient",
            _fake_client_class(raises=InternalClientTimeout("slow")),
        )
        with pytest.raises(CommandError, match="timed out"):
            call_command(COMMAND, stdout=StringIO())
