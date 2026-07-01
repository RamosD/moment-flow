"""HTTP contract tests for POST /moments/detect (IE-007)."""

from fastapi.testclient import TestClient

PATH = "/moments/detect"

GOOD_PAYLOAD = {
    "payload_version": "1.0",
    "workspace_id": "ws-1",
    "request_id": "req-1",
    "entity": {"type": "campaign", "id": "campaign-1"},
    "context": {"reference_date": "2026-06-24"},
    "data": {
        "campaign": {"status": "active", "campaign_type": "single_release"},
        "track": {"release_date": "2026-06-25"},
        "smart_link_stats": {"total_clicks": 1500, "clicks_last_7_days": 25},
    },
}

MINIMAL_PAYLOAD = {
    "payload_version": "1.0",
    "workspace_id": "ws-1",
    "request_id": "req-1",
    "entity": {"type": "campaign", "id": "campaign-1"},
}


def test_requires_internal_token(client_with_token: TestClient) -> None:
    response = client_with_token.post(PATH, json=GOOD_PAYLOAD)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "unauthorized_internal_request"


def test_good_payload_returns_moments(client_with_token: TestClient, internal_token: str) -> None:
    response = client_with_token.post(
        PATH, json=GOOD_PAYLOAD, headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    moments = body["result"]["moments"]
    assert moments

    types = {m["type"] for m in moments}
    assert "release_window" in types
    for moment in moments:
        assert moment["type"]
        assert moment["severity"] in {"low", "medium", "high"}
        assert 0.0 <= moment["confidence"] <= 1.0
        assert moment["summary"]
        assert moment["recommended_action"]


def test_insufficient_data_returns_empty_with_warning_not_500(
    client_with_token: TestClient, internal_token: str
) -> None:
    response = client_with_token.post(
        PATH, json=MINIMAL_PAYLOAD, headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["moments"] == []
    assert any(w["code"] == "insufficient_data" for w in body["warnings"])


def test_invalid_entity_type_is_rejected(
    client_with_token: TestClient, internal_token: str
) -> None:
    payload = {**MINIMAL_PAYLOAD, "entity": {"type": "planet", "id": "x"}}
    response = client_with_token.post(
        PATH, json=payload, headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_payload"


def test_malformed_data_types_yield_422_not_500(
    client_with_token: TestClient, internal_token: str
) -> None:
    payload = {
        **MINIMAL_PAYLOAD,
        "data": {"smart_link_stats": {"clicks_last_7_days": "lots"}, "content_outputs": {"x": 1}},
    }
    response = client_with_token.post(
        PATH, json=payload, headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_payload"


def test_response_is_deterministic_over_http(
    client_with_token: TestClient, internal_token: str
) -> None:
    headers = {"X-Internal-Token": internal_token}
    first = client_with_token.post(PATH, json=GOOD_PAYLOAD, headers=headers).json()
    second = client_with_token.post(PATH, json=GOOD_PAYLOAD, headers=headers).json()

    assert first == second
