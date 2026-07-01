"""HTTP contract tests for POST /analysis/campaign (IE-004)."""

from fastapi.testclient import TestClient

PATH = "/analysis/campaign"

GOOD_PAYLOAD = {
    "payload_version": "1.0",
    "workspace_id": "ws-1",
    "request_id": "req-1",
    "entity": {"type": "campaign", "id": "campaign-1"},
    "context": {"reference_date": "2026-06-24"},
    "data": {
        "campaign": {"status": "active"},
        "content_outputs": [{"status": "completed", "created_at": "2026-06-20"}],
        "smart_link_stats": {"total_clicks": 500, "clicks_last_7_days": 40},
        "previous_reports": [{"status": "completed", "period_end": "2026-06-10"}],
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


def test_good_payload_returns_structured_analysis(
    client_with_token: TestClient, internal_token: str
) -> None:
    response = client_with_token.post(
        PATH, json=GOOD_PAYLOAD, headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["engine"] == "intelligence_engine"
    assert body["request_id"] == "req-1"
    assert body["workspace_id"] == "ws-1"
    result = body["result"]
    assert result["campaign_health"] == "good"
    assert result["strengths"]
    assert isinstance(result["opportunities"], list)
    assert body["explanations"]


def test_minimal_payload_is_handled_with_warning_not_500(
    client_with_token: TestClient, internal_token: str
) -> None:
    response = client_with_token.post(
        PATH, json=MINIMAL_PAYLOAD, headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["campaign_health"] == "unknown"
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


def test_contradictory_data_warns_without_500(
    client_with_token: TestClient, internal_token: str
) -> None:
    payload = {
        **MINIMAL_PAYLOAD,
        "data": {
            "campaign": {"status": "active", "start_date": "2026-06-10", "end_date": "2026-06-01"}
        },
    }
    response = client_with_token.post(
        PATH, json=payload, headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 200
    codes = {w["code"] for w in response.json()["warnings"]}
    assert "inconsistent_campaign_dates" in codes


def test_response_is_deterministic_over_http(
    client_with_token: TestClient, internal_token: str
) -> None:
    headers = {"X-Internal-Token": internal_token}
    first = client_with_token.post(PATH, json=GOOD_PAYLOAD, headers=headers).json()
    second = client_with_token.post(PATH, json=GOOD_PAYLOAD, headers=headers).json()

    assert first == second
