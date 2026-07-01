"""Tests for the synchronous Intelligence Engine client.

No real HTTP happens: the inner client's transport is injected via a fake
``opener``. Covers success, the IE response normalization, every error mode and
the token-never-logged guarantee.
"""

import io
import json
import logging
import urllib.error

import pytest

from apps.integrations_bridge.intelligence_sync import (
    CAMPAIGN_INTELLIGENCE_PATH,
    IntelligenceEngineClient,
    IntelligenceEngineProtocolError,
    IntelligenceEngineResponseError,
    IntelligenceEngineTimeout,
    IntelligenceEngineUnavailable,
    IntelligenceResult,
    build_intelligence_engine_client,
)

TOKEN = "super-secret-token"


# --------------------------------------------------------------------------- #
# Fake transport helpers
# --------------------------------------------------------------------------- #
class FakeResponse:
    def __init__(self, body="{}", status=200):
        self._body = body.encode() if isinstance(body, str) else body
        self.status = status

    def read(self):
        return self._body


def opener_returning(body="{}", status=200, capture=None):
    def _opener(request, timeout):
        if capture is not None:
            capture["request"] = request
            capture["timeout"] = timeout
        return FakeResponse(body=body, status=status)

    return _opener


def opener_raising(exc):
    def _opener(request, timeout):
        raise exc

    return _opener


def opener_http_error(status, body):
    def _opener(request, timeout):
        raise urllib.error.HTTPError(
            getattr(request, "full_url", "http://svc"),
            status,
            "err",
            {},
            io.BytesIO(body.encode() if isinstance(body, str) else body),
        )

    return _opener


class SequenceOpener:
    """Opener that applies a sequence of behaviours and counts calls.

    Each behaviour is itself an opener (``opener_returning`` / ``opener_raising``
    / ``opener_http_error``). The last behaviour repeats once exhausted.
    """

    def __init__(self, behaviours):
        self.behaviours = list(behaviours)
        self.calls = 0

    def __call__(self, request, timeout):
        self.calls += 1
        behaviour = self.behaviours[min(self.calls - 1, len(self.behaviours) - 1)]
        return behaviour(request, timeout)


def _completed_envelope(**overrides):
    envelope = {
        "status": "completed",
        "engine": "intelligence_engine",
        "engine_version": "0.1.0",
        "request_id": "req-1",
        "workspace_id": "ws-1",
        "result": {
            "analysis": {"campaign_health": "good"},
            "scores": {"priority_score": 48},
            "grade": "A",
            "moments": [{"type": "release_window"}],
            "recommendations": [{"action": "create_release_post"}],
            "summary": "All good.",
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


def _client(opener):
    return IntelligenceEngineClient(
        "http://intelligence:8001", 7, internal_token=TOKEN, opener=opener
    )


def _call(client, capture=None):
    return client.post_campaign_intelligence(
        {"payload_version": "1.0", "workspace_id": "ws-1"},
        workspace_id="ws-1",
        request_id="req-1",
    )


# --------------------------------------------------------------------------- #
# Success
# --------------------------------------------------------------------------- #
class TestSuccess:
    def test_returns_normalized_result(self):
        client = _client(opener_returning(body=json.dumps(_completed_envelope())))
        result = _call(client)
        assert isinstance(result, IntelligenceResult)
        assert result.status == "completed"
        assert result.engine_version == "0.1.0"
        assert result.result["grade"] == "A"
        assert result.result["scores"]["priority_score"] == 48
        assert result.raw["status"] == "completed"

    def test_sends_internal_headers_and_target_path(self):
        capture = {}
        client = _client(
            opener_returning(body=json.dumps(_completed_envelope()), capture=capture)
        )
        _call(client)
        request = capture["request"]
        # Target path is the named sync endpoint.
        assert request.full_url.endswith(CAMPAIGN_INTELLIGENCE_PATH)
        sent = {k.lower(): v for k, v in request.header_items()}
        assert sent["x-internal-token"] == TOKEN
        assert sent["x-workspace-id"] == "ws-1"
        assert sent["x-request-id"] == "req-1"
        assert sent["content-type"] == "application/json"

    def test_applies_configured_timeout(self):
        capture = {}
        client = _client(
            opener_returning(body=json.dumps(_completed_envelope()), capture=capture)
        )
        _call(client)
        assert capture["timeout"] == 7

    def test_warnings_and_unknown_scores_passthrough(self):
        envelope = _completed_envelope(
            result={"scores": {"priority_score": None}, "grade": "unknown"},
            warnings=[{"code": "insufficient_data", "message": "…"}],
        )
        client = _client(opener_returning(body=json.dumps(envelope)))
        result = _call(client)
        assert result.warnings[0]["code"] == "insufficient_data"
        assert result.result["grade"] == "unknown"


# --------------------------------------------------------------------------- #
# Protocol errors (bad/unusable 200 bodies)
# --------------------------------------------------------------------------- #
class TestProtocolErrors:
    def test_invalid_json(self):
        client = _client(opener_returning(body="not-json"))
        with pytest.raises(IntelligenceEngineProtocolError):
            _call(client)

    def test_unexpected_status(self):
        client = _client(opener_returning(body=json.dumps({"status": "weird"})))
        with pytest.raises(IntelligenceEngineProtocolError):
            _call(client)

    def test_non_object_body(self):
        client = _client(opener_returning(body=json.dumps([1, 2, 3])))
        with pytest.raises(IntelligenceEngineProtocolError):
            _call(client)


# --------------------------------------------------------------------------- #
# HTTP error envelopes (non-2xx)
# --------------------------------------------------------------------------- #
class TestHTTPErrors:
    def test_403_unauthorized(self):
        client = _client(
            opener_http_error(403, _error_envelope("unauthorized_internal_request"))
        )
        with pytest.raises(IntelligenceEngineResponseError) as info:
            _call(client)
        assert info.value.status_code == 403
        assert info.value.error_code == "unauthorized_internal_request"
        assert info.value.is_client_error is True
        assert info.value.is_server_error is False

    def test_422_invalid_payload(self):
        client = _client(opener_http_error(422, _error_envelope("invalid_payload")))
        with pytest.raises(IntelligenceEngineResponseError) as info:
            _call(client)
        assert info.value.status_code == 422
        assert info.value.error_code == "invalid_payload"
        assert info.value.is_client_error is True

    def test_400_bad_request(self):
        client = _client(opener_http_error(400, _error_envelope("invalid_payload")))
        with pytest.raises(IntelligenceEngineResponseError) as info:
            _call(client)
        assert info.value.is_client_error is True

    def test_500_internal_error(self):
        client = _client(opener_http_error(500, _error_envelope("internal_error")))
        with pytest.raises(IntelligenceEngineResponseError) as info:
            _call(client)
        assert info.value.status_code == 500
        assert info.value.error_code == "internal_error"
        assert info.value.is_server_error is True
        assert info.value.is_client_error is False

    def test_http_error_with_unparseable_body_still_typed(self):
        client = _client(opener_http_error(500, "<html>boom</html>"))
        with pytest.raises(IntelligenceEngineResponseError) as info:
            _call(client)
        assert info.value.status_code == 500
        # Falls back to a safe default code, never the raw body.
        assert info.value.error_code == "http_error"


# --------------------------------------------------------------------------- #
# Transport failures
# --------------------------------------------------------------------------- #
class TestTransportFailures:
    def test_timeout(self):
        client = _client(opener_raising(TimeoutError()))
        with pytest.raises(IntelligenceEngineTimeout):
            _call(client)

    def test_service_unavailable(self):
        client = _client(opener_raising(urllib.error.URLError("refused")))
        with pytest.raises(IntelligenceEngineUnavailable):
            _call(client)

    def test_no_base_url_is_unavailable(self):
        client = IntelligenceEngineClient("", 7, internal_token=TOKEN, opener=opener_returning())
        with pytest.raises(IntelligenceEngineUnavailable):
            _call(client)


# --------------------------------------------------------------------------- #
# Security / observability
# --------------------------------------------------------------------------- #
class TestSecurityAndLogging:
    def test_token_never_logged_on_success(self, caplog):
        client = _client(opener_returning(body=json.dumps(_completed_envelope())))
        with caplog.at_level(logging.INFO):
            _call(client)
        assert TOKEN not in caplog.text

    def test_token_never_logged_on_error(self, caplog):
        client = _client(opener_http_error(403, _error_envelope("unauthorized_internal_request")))
        with caplog.at_level(logging.INFO):
            with pytest.raises(IntelligenceEngineResponseError):
                _call(client)
        assert TOKEN not in caplog.text

    def test_token_absent_from_error_message(self):
        client = _client(opener_http_error(500, _error_envelope("internal_error")))
        with pytest.raises(IntelligenceEngineResponseError) as info:
            _call(client)
        assert TOKEN not in str(info.value)

    def test_logs_request_and_workspace_ids(self, caplog):
        client = _client(opener_returning(body=json.dumps(_completed_envelope())))
        with caplog.at_level(logging.INFO, logger="integrations_bridge.intelligence"):
            _call(client)
        assert "request_id=req-1" in caplog.text
        assert "workspace_id=ws-1" in caplog.text


# --------------------------------------------------------------------------- #
# Retry policy (transient-only)
# --------------------------------------------------------------------------- #
class TestRetry:
    def _retry_client(self, opener, *, max_retries):
        # retry_backoff=0 → no real sleep in tests.
        return IntelligenceEngineClient(
            "http://intelligence:8001", 7,
            internal_token=TOKEN, opener=opener,
            max_retries=max_retries, retry_backoff=0,
        )

    def test_no_retry_by_default(self):
        opener = SequenceOpener([opener_http_error(500, _error_envelope("internal_error"))])
        client = IntelligenceEngineClient(
            "http://svc", 7, internal_token=TOKEN, opener=opener
        )  # default max_retries=0
        with pytest.raises(IntelligenceEngineResponseError):
            _call(client)
        assert opener.calls == 1

    def test_5xx_retried_then_raises(self):
        opener = SequenceOpener([opener_http_error(500, _error_envelope("internal_error"))])
        client = self._retry_client(opener, max_retries=2)
        with pytest.raises(IntelligenceEngineResponseError):
            _call(client)
        assert opener.calls == 3  # 1 + 2 retries

    def test_timeout_retried_then_raises(self):
        opener = SequenceOpener([opener_raising(TimeoutError())])
        client = self._retry_client(opener, max_retries=1)
        with pytest.raises(IntelligenceEngineTimeout):
            _call(client)
        assert opener.calls == 2

    def test_unavailable_retried_then_raises(self):
        opener = SequenceOpener([opener_raising(urllib.error.URLError("refused"))])
        client = self._retry_client(opener, max_retries=1)
        with pytest.raises(IntelligenceEngineUnavailable):
            _call(client)
        assert opener.calls == 2

    def test_success_after_transient_failure(self):
        opener = SequenceOpener([
            opener_http_error(503, _error_envelope("internal_error")),
            opener_returning(body=json.dumps(_completed_envelope())),
        ])
        client = self._retry_client(opener, max_retries=2)
        result = _call(client)
        assert result.status == "completed"
        assert opener.calls == 2  # failed once, then succeeded

    def test_4xx_not_retried(self):
        opener = SequenceOpener([opener_http_error(422, _error_envelope("invalid_payload"))])
        client = self._retry_client(opener, max_retries=3)
        with pytest.raises(IntelligenceEngineResponseError) as info:
            _call(client)
        assert info.value.status_code == 422
        assert opener.calls == 1  # 4xx is never retried

    def test_protocol_error_not_retried(self):
        opener = SequenceOpener([opener_returning(body="not-json")])
        client = self._retry_client(opener, max_retries=3)
        with pytest.raises(IntelligenceEngineProtocolError):
            _call(client)
        assert opener.calls == 1  # unusable body is deterministic, never retried


# --------------------------------------------------------------------------- #
# Factory (reads settings)
# --------------------------------------------------------------------------- #
class TestFactory:
    def test_uses_intelligence_engine_settings(self, settings):
        settings.INTELLIGENCE_ENGINE_BASE_URL = "http://ie:9001"
        settings.INTELLIGENCE_ENGINE_TIMEOUT_SECONDS = 13
        settings.INTELLIGENCE_ENGINE_INTERNAL_TOKEN = "factory-token"
        settings.INTELLIGENCE_ENGINE_MAX_RETRIES = 2
        settings.INTELLIGENCE_ENGINE_RETRY_BACKOFF_SECONDS = 0.0
        capture = {}
        client = build_intelligence_engine_client(
            opener=opener_returning(body=json.dumps(_completed_envelope()), capture=capture)
        )
        assert client.base_url == "http://ie:9001"
        assert client.timeout == 13
        assert client.max_retries == 2
        assert client.retry_backoff == 0.0
        _call(client)
        sent = {k.lower(): v for k, v in capture["request"].header_items()}
        assert sent["x-internal-token"] == "factory-token"
        assert capture["timeout"] == 13
