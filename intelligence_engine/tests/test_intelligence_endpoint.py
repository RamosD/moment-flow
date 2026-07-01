"""HTTP contract tests for POST /intelligence/campaign (IE-008)."""

from fastapi.testclient import TestClient

PATH = "/intelligence/campaign"

GOOD_PAYLOAD = {
    "payload_version": "1.0",
    "workspace_id": "ws-1",
    "request_id": "req-1",
    "entity": {"type": "campaign", "id": "campaign-1"},
    "context": {"reference_date": "2026-06-24"},
    "data": {
        "campaign": {"status": "active", "campaign_type": "single_release"},
        "artist": {"name": "Nova"},
        "track": {"release_date": "2026-06-25"},
        "smart_link_stats": {"total_clicks": 1500, "clicks_last_7_days": 25},
        "content_outputs": [{"status": "completed", "created_at": "2026-06-22"}],
        "media_kits": [{"status": "published"}],
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


def test_good_payload_returns_full_composite(
    client_with_token: TestClient, internal_token: str
) -> None:
    response = client_with_token.post(
        PATH, json=GOOD_PAYLOAD, headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"

    result = body["result"]
    # All four sections plus the summary are present.
    assert "campaign_health" in result["analysis"]
    assert set(result["scores"]) >= {
        "campaign_readiness_score",
        "momentum_score",
        "content_opportunity_score",
        "risk_score",
        "priority_score",
    }
    assert result["grade"] in {"A", "B", "C", "D", "unknown"}
    assert isinstance(result["moments"], list) and result["moments"]
    assert isinstance(result["recommendations"], list) and result["recommendations"]
    assert result["summary"]

    # Consolidated envelope lists are present.
    assert isinstance(body["explanations"], list) and body["explanations"]
    assert isinstance(body["warnings"], list)


def test_insufficient_data_is_handled_without_500(
    client_with_token: TestClient, internal_token: str
) -> None:
    response = client_with_token.post(
        PATH, json=MINIMAL_PAYLOAD, headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["grade"] == "unknown"
    assert body["result"]["moments"] == []
    actions = [r["action"] for r in body["result"]["recommendations"]]
    assert actions == ["wait_for_more_data"]
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
        "data": {"smart_link_stats": {"total_clicks": "many"}, "content_outputs": {"x": 1}},
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
