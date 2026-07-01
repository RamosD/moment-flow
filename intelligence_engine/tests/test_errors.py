"""Normalised error-contract tests (IE-002).

Verifies the common error shape from the backlog (section 6.5):
    {"status": "failed", "error": {"code", "message", "details"}, "metadata": {...}}
for the codes reachable through HTTP in this phase: not_found,
unauthorized_internal_request, invalid_payload, internal_error.
"""

from fastapi.testclient import TestClient


def _assert_error_envelope(body: dict, code: str) -> None:
    assert body["status"] == "failed"
    assert body["error"]["code"] == code
    assert "message" in body["error"]
    assert "details" in body["error"]
    assert body["metadata"]["engine"] == "intelligence_engine"
    assert body["metadata"]["engine_version"] == "0.1.0"


def test_unknown_route_returns_normalised_not_found(client: TestClient) -> None:
    response = client.get("/this-route-does-not-exist")

    assert response.status_code == 404
    _assert_error_envelope(response.json(), "not_found")


def test_wrong_method_is_not_labelled_internal_error(client_with_token: TestClient) -> None:
    """A 405 must keep its status and a client-error code, not internal_error."""
    response = client_with_token.post("/health")

    assert response.status_code == 405
    _assert_error_envelope(response.json(), "invalid_payload")


def test_missing_token_returns_normalised_unauthorized(client: TestClient) -> None:
    response = client.get("/internal/_debug/ping")

    assert response.status_code == 403
    _assert_error_envelope(response.json(), "unauthorized_internal_request")


def test_invalid_payload_returns_normalised_422(
    client_with_token: TestClient, internal_token: str
) -> None:
    response = client_with_token.post(
        "/internal/_debug/echo",
        headers={"X-Internal-Token": internal_token},
        json={},
    )

    assert response.status_code == 422
    body = response.json()
    _assert_error_envelope(body, "invalid_payload")
    assert body["error"]["details"]["errors"]


def test_unexpected_exception_returns_normalised_500_without_stack_trace(
    client_with_token: TestClient, internal_token: str
) -> None:
    response = client_with_token.get(
        "/internal/_debug/boom", headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 500
    body = response.json()
    _assert_error_envelope(body, "internal_error")

    rendered = response.text
    assert "RuntimeError" not in rendered
    assert "Traceback" not in rendered
    assert "internal_debug.py" not in rendered
