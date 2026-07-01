"""Tests for the aggregated dependency healthcheck (OBS-STG-003).

Two layers:
  - the probe (`http_health_probe`) — response mapping, exercised with an
    injected fake opener (no real socket);
  - the aggregator (`check_dependencies`) and the HTTP endpoint — exercised with
    an injected fake prober (no real network), covering all-ok, a dependency
    down, timeout, misconfigured base URL and an invalid response.

No real token is used anywhere; the probe must never send ``X-Internal-Token``.
"""

import json
import urllib.error

import pytest
from rest_framework.test import APIClient

from apps.integrations_bridge import health
from apps.integrations_bridge.health import (
    DEGRADED,
    MISCONFIGURED,
    OK,
    UNAVAILABLE,
    UNKNOWN,
    check_dependencies,
    http_health_probe,
)

pytestmark = pytest.mark.django_db

URL = "/api/v1/system/health/dependencies/"


class _FakeResponse:
    """Minimal stand-in for an ``http.client.HTTPResponse``."""

    def __init__(self, status, body):
        self.status = status
        self._body = body.encode("utf-8") if isinstance(body, str) else body

    def read(self):
        return self._body


# --------------------------------------------------------------------------- #
# Probe — response mapping (fake opener, no real socket)
# --------------------------------------------------------------------------- #
class TestProbe:
    def test_ok_body_is_ok(self):
        def opener(request, timeout):
            return _FakeResponse(200, json.dumps({"status": "ok", "service": "ie"}))

        status, duration, detail = http_health_probe("http://ie:8001", 2, opener=opener)
        assert status == OK
        assert detail == ""
        assert duration >= 0

    def test_unexpected_body_is_degraded(self):
        def opener(request, timeout):
            return _FakeResponse(200, "not-json")

        status, _, detail = http_health_probe("http://ie:8001", 2, opener=opener)
        assert status == DEGRADED
        assert detail == "unexpected_body"

    def test_status_not_ok_is_degraded(self):
        def opener(request, timeout):
            return _FakeResponse(200, json.dumps({"status": "degraded"}))

        status, _, detail = http_health_probe("http://x", 2, opener=opener)
        assert status == DEGRADED
        assert detail == "unexpected_body"

    def test_non_2xx_response_object_is_degraded(self):
        def opener(request, timeout):
            return _FakeResponse(503, "")

        status, _, detail = http_health_probe("http://x", 2, opener=opener)
        assert status == DEGRADED
        assert detail == "http_503"

    def test_http_error_is_degraded(self):
        def opener(request, timeout):
            raise urllib.error.HTTPError("http://x/health", 502, "bad", {}, None)

        status, _, detail = http_health_probe("http://x", 2, opener=opener)
        assert status == DEGRADED
        assert detail == "http_502"

    def test_timeout_is_unavailable(self):
        def opener(request, timeout):
            raise TimeoutError()

        status, _, detail = http_health_probe("http://x", 2, opener=opener)
        assert status == UNAVAILABLE
        assert detail == "timeout"

    def test_connection_error_is_unavailable(self):
        def opener(request, timeout):
            raise urllib.error.URLError("connection refused")

        status, _, detail = http_health_probe("http://x", 2, opener=opener)
        assert status == UNAVAILABLE
        assert detail == "connection_error"

    def test_probe_sends_no_internal_token(self):
        captured = {}

        def opener(request, timeout):
            captured["headers"] = [k.lower() for k, _ in request.header_items()]
            return _FakeResponse(200, json.dumps({"status": "ok"}))

        http_health_probe("http://ie:8001", 2, opener=opener)
        assert "x-internal-token" not in captured["headers"]


# --------------------------------------------------------------------------- #
# Aggregator — overall + per-dependency status (fake prober, no network)
# --------------------------------------------------------------------------- #
class TestAggregator:
    def test_all_ok(self):
        report = check_dependencies(prober=lambda url, timeout: (OK, 5, ""))
        assert report["status"] == "ok"
        assert report["service"] == "backend_core"
        assert "checked_at" in report
        deps = report["dependencies"]
        assert deps["intelligence_engine"]["status"] == OK
        assert deps["content_renderer"]["status"] == OK
        assert deps["database"]["status"] == OK
        # URL is reduced to a non-sensitive marker; duration is always present.
        assert deps["intelligence_engine"]["url"] == "configured"
        for entry in deps.values():
            assert "duration_ms" in entry

    def test_intelligence_engine_unavailable_is_degraded_overall(self):
        def prober(url, timeout):
            if "8001" in url:
                return (UNAVAILABLE, 1, "connection_error")
            return (OK, 5, "")

        report = check_dependencies(prober=prober)
        assert report["dependencies"]["intelligence_engine"]["status"] == UNAVAILABLE
        assert report["dependencies"]["content_renderer"]["status"] == OK
        # One dependency down, others up → degraded (not unavailable, not 500).
        assert report["status"] == "degraded"

    def test_content_renderer_unavailable_is_degraded_overall(self):
        def prober(url, timeout):
            if "8002" in url:
                return (UNAVAILABLE, 1, "connection_error")
            return (OK, 5, "")

        report = check_dependencies(prober=prober)
        assert report["dependencies"]["content_renderer"]["status"] == UNAVAILABLE
        assert report["status"] == "degraded"

    def test_timeout_is_unavailable_for_dependency(self):
        def prober(url, timeout):
            if "8002" in url:
                return (UNAVAILABLE, int(timeout * 1000), "timeout")
            return (OK, 5, "")

        report = check_dependencies(prober=prober)
        renderer = report["dependencies"]["content_renderer"]
        assert renderer["status"] == UNAVAILABLE
        assert renderer["detail"] == "timeout"
        assert report["status"] == "degraded"

    def test_misconfigured_when_base_url_empty(self, settings):
        settings.INTELLIGENCE_ENGINE_BASE_URL = ""
        called = []

        def prober(url, timeout):
            called.append(url)
            return (OK, 1, "")

        report = check_dependencies(prober=prober)
        ie = report["dependencies"]["intelligence_engine"]
        assert ie["status"] == MISCONFIGURED
        assert ie["url"] == "not_configured"
        # The prober is NOT called for a misconfigured dependency.
        assert all("8001" not in url for url in called)
        # IE misconfigured, renderer + db ok → degraded overall.
        assert report["status"] == "degraded"

    def test_all_external_unavailable_is_unavailable(self):
        # Exclude the database (always up under django_db) so the aggregate can
        # reach the "none healthy → unavailable" branch.
        report = check_dependencies(
            prober=lambda url, timeout: (UNAVAILABLE, 1, "connection_error"),
            include_database=False,
        )
        assert report["status"] == "unavailable"

    def test_uses_configured_timeout(self, settings):
        settings.HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS = 0.5
        seen = []

        def prober(url, timeout):
            seen.append(timeout)
            return (OK, 1, "")

        check_dependencies(prober=prober)
        assert seen and all(t == 0.5 for t in seen)

    def test_probe_exception_does_not_break_aggregate(self):
        def boom(url, timeout):
            raise RuntimeError("boom")

        report = check_dependencies(prober=boom)
        assert report["dependencies"]["intelligence_engine"]["status"] == UNKNOWN
        # Aggregate still produced; database keeps it from being all-down.
        assert report["status"] in ("degraded", "unavailable")


# --------------------------------------------------------------------------- #
# Endpoint — auth + 200 contract
# --------------------------------------------------------------------------- #
class TestEndpoint:
    def test_requires_authentication(self):
        resp = APIClient().get(URL)
        assert resp.status_code == 401

    def test_forbidden_for_non_staff(self, make_user):
        user = make_user("plain@example.com")
        client = APIClient()
        client.force_authenticate(user=user)
        resp = client.get(URL)
        assert resp.status_code == 403

    def test_ok_for_staff(self, make_user, monkeypatch):
        staff = make_user("ops@example.com", is_staff=True)
        monkeypatch.setattr(
            "apps.integrations_bridge.views.check_dependencies",
            lambda: {
                "status": "ok",
                "service": "backend_core",
                "checked_at": "2026-06-25T00:00:00+00:00",
                "dependencies": {"intelligence_engine": {"status": "ok"}},
            },
        )
        client = APIClient()
        client.force_authenticate(user=staff)
        resp = client.get(URL)
        assert resp.status_code == 200
        assert resp.data["status"] == "ok"
        assert "dependencies" in resp.data

    def test_no_500_when_real_probe_fails(self, make_user, monkeypatch):
        """A failing real probe yields degraded/unavailable, never a 500."""
        staff = make_user("ops2@example.com", is_staff=True)

        def boom(base_url, timeout, *, opener=None):
            raise RuntimeError("network exploded")

        # Patch the module-level probe used by check_dependencies (no network).
        monkeypatch.setattr(health, "http_health_probe", boom)
        client = APIClient()
        client.force_authenticate(user=staff)
        resp = client.get(URL)
        assert resp.status_code == 200
        deps = resp.data["dependencies"]
        assert deps["intelligence_engine"]["status"] == UNKNOWN
        assert resp.data["status"] in ("degraded", "unavailable")
