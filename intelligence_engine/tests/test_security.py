"""Security tests for X-Internal-Token (IE-002).

Uses the temporary `/internal/_debug/*` endpoints (app/api/internal_debug.py)
since no real internal endpoint exists yet — these are the routes the
`require_internal_token` dependency is actually wired into.
"""

import json
import logging

from fastapi.testclient import TestClient

from app.core.logging import JsonFormatter
from app.core.security import _tokens_match


def test_tokens_match_handles_non_ascii_configured_token_without_raising() -> None:
    """A non-ASCII token (e.g. set via env) must compare False, not raise.

    `hmac.compare_digest` raises TypeError on str operands containing
    non-ASCII; comparing UTF-8 bytes avoids that turning into a 500. HTTP
    headers themselves can't carry non-ASCII, so this is exercised at the
    unit level rather than through the client.
    """
    assert _tokens_match("ascii-token", "tøken-nøn-ascii") is False
    assert _tokens_match("tøken-nøn-ascii", "tøken-nøn-ascii") is True
    assert _tokens_match("", "tøken") is False


def test_protected_endpoint_accepts_correct_token(
    client_with_token: TestClient, internal_token: str
) -> None:
    response = client_with_token.get(
        "/internal/_debug/ping", headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "authenticated": True}


def test_protected_endpoint_rejects_missing_token(client_with_token: TestClient) -> None:
    response = client_with_token.get("/internal/_debug/ping")

    assert response.status_code == 403
    body = response.json()
    assert body["status"] == "failed"
    assert body["error"]["code"] == "unauthorized_internal_request"


def test_protected_endpoint_rejects_wrong_token(client_with_token: TestClient) -> None:
    response = client_with_token.get(
        "/internal/_debug/ping", headers={"X-Internal-Token": "definitely-wrong"}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "unauthorized_internal_request"


def test_protected_endpoint_rejects_everything_when_no_token_configured(
    client: TestClient,
) -> None:
    """Default fixture has INTERNAL_API_TOKEN="" (dev defaults) — no bypass."""
    response = client.get("/internal/_debug/ping", headers={"X-Internal-Token": "anything"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "unauthorized_internal_request"


def test_health_remains_public_when_token_is_configured(client_with_token: TestClient) -> None:
    response = client_with_token.get("/health")

    assert response.status_code == 200


def test_token_is_never_present_in_logs(client_with_token: TestClient, internal_token: str) -> None:
    """Capture every log record emitted during real requests and assert no
    token value (correct or wrong) leaks through — including via the JSON
    rendering used in production."""
    captured: list[logging.LogRecord] = []

    class _ListSink(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    sink = _ListSink()
    root = logging.getLogger()
    root.addHandler(sink)
    try:
        client_with_token.get("/internal/_debug/ping", headers={"X-Internal-Token": internal_token})
        client_with_token.get(
            "/internal/_debug/ping", headers={"X-Internal-Token": "wrong-secret-token"}
        )
    finally:
        root.removeHandler(sink)

    formatter = JsonFormatter()
    for record in captured:
        rendered = formatter.format(record)
        assert internal_token not in rendered
        assert "wrong-secret-token" not in rendered


def test_token_is_redacted_in_structured_json_output(internal_token: str) -> None:
    record = logging.LogRecord(
        name="intelligence_engine",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="some_event",
        args=(),
        exc_info=None,
    )
    record.internal_api_token = internal_token
    record.x_internal_token = internal_token

    line = JsonFormatter().format(record)
    payload = json.loads(line)

    assert internal_token not in line
    assert payload["internal_api_token"] == "[REDACTED]"
    assert payload["x_internal_token"] == "[REDACTED]"
