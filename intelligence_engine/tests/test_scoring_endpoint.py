"""HTTP contract tests for POST /scoring/campaign (IE-005)."""

from fastapi.testclient import TestClient

PATH = "/scoring/campaign"

GOOD_PAYLOAD = {
    "payload_version": "1.0",
    "workspace_id": "ws-1",
    "request_id": "req-1",
    "entity": {"type": "campaign", "id": "campaign-1"},
    "context": {"reference_date": "2026-06-24"},
    "data": {
        "campaign": {
            "status": "active",
            "primary_goal": "grow",
            "start_date": "2026-06-01",
            "end_date": "2026-12-31",
        },
        "artist": {"name": "Nova"},
        "track": {"release_date": "2026-06-20"},
        "smart_link_stats": {
            "total_clicks": 2000,
            "clicks_last_7_days": 120,
            "clicks_last_30_days": 500,
            "active_links": 4,
        },
        "content_outputs": [{"status": "completed", "created_at": "2026-06-22"}],
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


def test_good_payload_returns_scores_grade_and_explanations(
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

    scores = body["result"]["scores"]
    for key in (
        "campaign_readiness_score",
        "momentum_score",
        "content_opportunity_score",
        "risk_score",
        "priority_score",
    ):
        assert isinstance(scores[key], int)
        assert 0 <= scores[key] <= 100
    assert body["result"]["grade"] in {"A", "B", "C", "D"}
    assert body["explanations"]


def test_insufficient_data_returns_nulls_and_warning_not_500(
    client_with_token: TestClient, internal_token: str
) -> None:
    response = client_with_token.post(
        PATH, json=MINIMAL_PAYLOAD, headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 200
    body = response.json()
    scores = body["result"]["scores"]
    assert all(value is None for value in scores.values())
    assert body["result"]["grade"] == "unknown"
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
    # smart_link_stats counters as non-numeric, content_outputs as a non-list:
    # validation must reject these cleanly, never reach the engine and 500.
    payload = {
        **MINIMAL_PAYLOAD,
        "data": {
            "smart_link_stats": {"total_clicks": "lots"},
            "content_outputs": {"not": "a list"},
        },
    }
    response = client_with_token.post(
        PATH, json=payload, headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_payload"


def test_bad_context_reference_date_is_warned_not_500(
    client_with_token: TestClient, internal_token: str
) -> None:
    payload = {
        **MINIMAL_PAYLOAD,
        "context": {"reference_date": "not-a-date"},
        "data": {"campaign": {"status": "active"}},
    }
    response = client_with_token.post(
        PATH, json=payload, headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 200
    assert any(w["code"] == "invalid_reference_date" for w in response.json()["warnings"])


def test_response_is_deterministic_over_http(
    client_with_token: TestClient, internal_token: str
) -> None:
    headers = {"X-Internal-Token": internal_token}
    first = client_with_token.post(PATH, json=GOOD_PAYLOAD, headers=headers).json()
    second = client_with_token.post(PATH, json=GOOD_PAYLOAD, headers=headers).json()

    assert first == second
