"""Tests for integration settings, the service registry and the internal client.

No real HTTP happens: the client transport is injected via a fake ``opener``.
"""

import urllib.error

import pytest

from apps.integrations_bridge import registry
from apps.integrations_bridge.clients import (
    INTERNAL_TOKEN_HEADER,
    InternalClientTimeout,
    InternalHTTPError,
    InternalResponse,
    InternalServiceClient,
    InternalServiceUnavailable,
    InvalidJSONResponse,
)


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


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #
class TestSettings:
    def test_integration_settings_present(self, settings):
        for name in [
            "BACKEND_PUBLIC_BASE_URL",
            "INTELLIGENCE_ENGINE_BASE_URL",
            "INTELLIGENCE_ENGINE_TIMEOUT_SECONDS",
            "INTELLIGENCE_ENGINE_INTERNAL_TOKEN",
            "INTELLIGENCE_ENGINE_ENABLED",
            "INTELLIGENCE_ENGINE_DRY_RUN",
            "INTELLIGENCE_ENGINE_MAX_RETRIES",
            "INTELLIGENCE_ENGINE_RETRY_BACKOFF_SECONDS",
            "CONTENT_RENDERER_BASE_URL",
            "CONTENT_RENDERER_TIMEOUT_SECONDS",
            "REPORT_RENDERER_BASE_URL",
            "REPORT_RENDERER_TIMEOUT_SECONDS",
            "INTERNAL_CALLBACK_PATH",
            "EXTERNAL_JOBS_ENABLED",
            "EXTERNAL_JOBS_DRY_RUN",
        ]:
            assert hasattr(settings, name), name

    def test_timeouts_are_ints(self, settings):
        assert isinstance(settings.CONTENT_RENDERER_TIMEOUT_SECONDS, int)
        assert isinstance(settings.INTELLIGENCE_ENGINE_TIMEOUT_SECONDS, int)

    def test_switches_are_bool(self, settings):
        assert isinstance(settings.EXTERNAL_JOBS_ENABLED, bool)
        assert isinstance(settings.EXTERNAL_JOBS_DRY_RUN, bool)

    def test_intelligence_engine_switches_are_bool(self, settings):
        assert isinstance(settings.INTELLIGENCE_ENGINE_ENABLED, bool)
        assert isinstance(settings.INTELLIGENCE_ENGINE_DRY_RUN, bool)

    def test_intelligence_engine_token_defaults_to_shared_internal_token(self):
        """No second secret: when no per-service token is set, the engine token
        resolves to the shared INTERNAL_API_TOKEN (integration contract §5)."""
        # In the test environment neither env var is set, so both resolve to the
        # same (empty) shared default. The point is they are the same source.
        from django.conf import settings as dj_settings

        assert (
            dj_settings.INTELLIGENCE_ENGINE_INTERNAL_TOKEN
            == dj_settings.INTERNAL_API_TOKEN
        )


class TestIntelligenceEngineConfigGuard:
    """The production guard refuses an enabled engine with no token (not dry-run).

    Tests the pure helper directly so no settings reload / subprocess is needed.
    """

    @staticmethod
    def _guard(**kwargs):
        from config.settings import _require_secure_intelligence_engine_config

        return _require_secure_intelligence_engine_config(**kwargs)

    def test_production_enabled_no_token_raises(self):
        from django.core.exceptions import ImproperlyConfigured

        with pytest.raises(ImproperlyConfigured):
            self._guard(debug=False, enabled=True, dry_run=False, token="")

    def test_production_enabled_with_token_ok(self):
        # Should not raise.
        self._guard(debug=False, enabled=True, dry_run=False, token="secret")

    def test_production_dry_run_no_token_ok(self):
        # Dry-run makes no real call, so an empty token is safe.
        self._guard(debug=False, enabled=True, dry_run=True, token="")

    def test_production_disabled_no_token_ok(self):
        # Disabled engine never calls out, so an empty token is safe.
        self._guard(debug=False, enabled=False, dry_run=False, token="")

    def test_debug_enabled_no_token_ok(self):
        # Local development convenience: empty token allowed under DEBUG.
        self._guard(debug=True, enabled=True, dry_run=False, token="")


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
class TestRegistry:
    @pytest.mark.parametrize(
        "job_type,provider",
        [
            ("content_generation", registry.CONTENT_RENDERER),
            ("content_preview", registry.CONTENT_RENDERER),
            ("report_generation", registry.REPORT_RENDERER),
            ("media_kit_generation", registry.REPORT_RENDERER),
            ("metrics_collection", registry.INTELLIGENCE_ENGINE),
            ("moment_detection", registry.INTELLIGENCE_ENGINE),
            ("insight_generation", registry.INTELLIGENCE_ENGINE),
            ("recommendation_generation", registry.INTELLIGENCE_ENGINE),
        ],
    )
    def test_resolve_provider(self, job_type, provider):
        assert registry.resolve_provider(job_type) == provider

    def test_unknown_job_type_raises(self):
        with pytest.raises(registry.UnknownJobType):
            registry.resolve_provider("does_not_exist")

    def test_resolve_service_returns_url_and_timeout(self, settings):
        settings.CONTENT_RENDERER_BASE_URL = "http://renderer:9000"
        settings.CONTENT_RENDERER_TIMEOUT_SECONDS = 42
        endpoint = registry.resolve_service("content_generation")
        assert endpoint.provider == registry.CONTENT_RENDERER
        assert endpoint.base_url == "http://renderer:9000"
        assert endpoint.timeout == 42

    def test_service_not_configured_raises(self, settings):
        settings.INTELLIGENCE_ENGINE_BASE_URL = ""
        with pytest.raises(registry.ServiceNotConfigured):
            registry.resolve_service("metrics_collection")

    def test_callback_url_is_absolute(self, settings):
        settings.BACKEND_PUBLIC_BASE_URL = "http://localhost:8000/"
        settings.INTERNAL_CALLBACK_PATH = "/api/v1/internal/jobs/callback/"
        assert registry.callback_url() == (
            "http://localhost:8000/api/v1/internal/jobs/callback/"
        )

    def test_switches(self, settings):
        settings.EXTERNAL_JOBS_ENABLED = True
        settings.EXTERNAL_JOBS_DRY_RUN = False
        assert registry.should_submit_externally() is True

        settings.EXTERNAL_JOBS_DRY_RUN = True
        assert registry.external_jobs_dry_run() is True
        assert registry.should_submit_externally() is False

        settings.EXTERNAL_JOBS_DRY_RUN = False
        settings.EXTERNAL_JOBS_ENABLED = False
        assert registry.external_jobs_enabled() is False
        assert registry.should_submit_externally() is False


# --------------------------------------------------------------------------- #
# Internal client
# --------------------------------------------------------------------------- #
class TestClientHeaders:
    def test_build_headers_includes_all_mandatory(self):
        client = InternalServiceClient("http://svc", 10, internal_token="tok")
        headers = client.build_headers(
            workspace_id="ws-1", job_id="job-1", request_id="req-1"
        )
        assert headers[INTERNAL_TOKEN_HEADER] == "tok"
        assert headers["X-Workspace-ID"] == "ws-1"
        assert headers["X-Job-ID"] == "job-1"
        assert headers["X-Request-ID"] == "req-1"
        assert headers["Content-Type"] == "application/json"

    def test_post_json_sends_headers(self):
        capture = {}
        client = InternalServiceClient(
            "http://svc", 10, internal_token="tok",
            opener=opener_returning(body='{"ok": true}', capture=capture),
        )
        resp = client.post_json(
            "/render", {"a": 1}, workspace_id="ws-1", job_id="job-1", request_id="req-1"
        )
        assert isinstance(resp, InternalResponse)
        assert resp.data == {"ok": True}
        # urllib lowercases/normalizes header keys via .header_items()
        sent = dict(capture["request"].header_items())
        normalized = {k.lower(): v for k, v in sent.items()}
        assert normalized["x-internal-token"] == "tok"
        assert normalized["x-workspace-id"] == "ws-1"
        assert normalized["x-job-id"] == "job-1"
        assert normalized["x-request-id"] == "req-1"
        assert normalized["content-type"] == "application/json"
        assert capture["timeout"] == 10


class TestClientErrorHandling:
    def _client(self, opener):
        return InternalServiceClient("http://svc", 5, internal_token="tok", opener=opener)

    def _call(self, client):
        return client.post_json(
            "/x", {}, workspace_id="ws", job_id="job", request_id="req"
        )

    def test_success(self):
        client = self._client(opener_returning(body='{"v": 9}'))
        assert self._call(client).data == {"v": 9}

    def test_timeout(self):
        client = self._client(opener_raising(TimeoutError()))
        with pytest.raises(InternalClientTimeout):
            self._call(client)

    def test_http_error(self):
        err = urllib.error.HTTPError("http://svc/x", 500, "boom", {}, None)
        client = self._client(opener_raising(err))
        with pytest.raises(InternalHTTPError) as info:
            self._call(client)
        assert info.value.status_code == 500

    def test_service_unavailable(self):
        client = self._client(opener_raising(urllib.error.URLError("refused")))
        with pytest.raises(InternalServiceUnavailable):
            self._call(client)

    def test_invalid_json(self):
        client = self._client(opener_returning(body="not-json"))
        with pytest.raises(InvalidJSONResponse):
            self._call(client)

    def test_token_never_logged(self, caplog):
        import logging

        client = self._client(opener_returning(body="{}"))
        with caplog.at_level(logging.INFO, logger="integrations_bridge.client"):
            self._call(client)
        assert "tok" not in caplog.text
