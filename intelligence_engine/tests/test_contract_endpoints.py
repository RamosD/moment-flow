"""HTTP contract tests for the engine endpoints (IE-003 → IE-008).

The point of these tests is the *contract*: auth is enforced, valid payloads
pass validation, invalid payloads are rejected with the normalised error
envelope, and OpenAPI reflects all of it. All engine endpoints are now
implemented (IE-004 → IE-008) and return a completed 200 response.
"""

import pytest
from fastapi.testclient import TestClient

IMPLEMENTED_ENDPOINTS = [
    "/analysis/campaign",
    "/scoring/campaign",
    "/recommendations/campaign",
    "/moments/detect",
    "/intelligence/campaign",
]
ENDPOINTS = IMPLEMENTED_ENDPOINTS

VALID_ENVELOPE = {
    "payload_version": "1.0",
    "workspace_id": "ws-1",
    "request_id": "req-1",
    "entity": {"type": "campaign", "id": "campaign-1"},
}


def _assert_error_envelope(body: dict, code: str) -> None:
    assert body["status"] == "failed"
    assert body["error"]["code"] == code
    assert body["metadata"]["engine"] == "intelligence_engine"
    assert body["metadata"]["engine_version"] == "0.1.0"


@pytest.mark.parametrize("path", ENDPOINTS)
def test_endpoint_requires_internal_token(client_with_token: TestClient, path: str) -> None:
    response = client_with_token.post(path, json=VALID_ENVELOPE)

    assert response.status_code == 403
    _assert_error_envelope(response.json(), "unauthorized_internal_request")


@pytest.mark.parametrize("path", IMPLEMENTED_ENDPOINTS)
def test_implemented_endpoint_returns_completed_response(
    client_with_token: TestClient, internal_token: str, path: str
) -> None:
    response = client_with_token.post(
        path, json=VALID_ENVELOPE, headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


@pytest.mark.parametrize("path", ENDPOINTS)
def test_invalid_entity_type_is_rejected_normalised(
    client_with_token: TestClient, internal_token: str, path: str
) -> None:
    payload = {**VALID_ENVELOPE, "entity": {"type": "planet", "id": "x"}}
    response = client_with_token.post(
        path, json=payload, headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 422
    _assert_error_envelope(response.json(), "invalid_payload")


def test_bad_payload_version_is_rejected_normalised_not_500(
    client_with_token: TestClient, internal_token: str
) -> None:
    """Regression: a custom-validator ValueError must serialise to a clean 422."""
    payload = {**VALID_ENVELOPE, "payload_version": "2.0"}
    response = client_with_token.post(
        "/analysis/campaign", json=payload, headers={"X-Internal-Token": internal_token}
    )

    assert response.status_code == 422
    body = response.json()
    _assert_error_envelope(body, "invalid_payload")
    # The offending field is reported, and the body is fully JSON-serialisable.
    locs = [tuple(err["loc"]) for err in body["error"]["details"]["errors"]]
    assert ("body", "payload_version") in locs


def test_openapi_reflects_contracts(client_with_token: TestClient) -> None:
    spec = client_with_token.get("/openapi.json").json()

    for path in ENDPOINTS:
        assert path in spec["paths"], f"missing path {path}"
        operation = spec["paths"][path]["post"]
        # Every endpoint documents success (200) and the auth/validation errors.
        for status_code in ("200", "403", "422"):
            assert status_code in operation["responses"]

    # No endpoint advertises the lifecycle 501 any more — all engines are live.
    for path in IMPLEMENTED_ENDPOINTS:
        assert "501" not in spec["paths"][path]["post"]["responses"]

    schemas = spec["components"]["schemas"]
    for name in (
        "CampaignAnalysisRequest",
        "ScoringRequest",
        "RecommendationsRequest",
        "MomentsRequest",
        "IntelligenceCampaignRequest",
        "EntityRef",
        "ErrorResponse",
        "Recommendation",
        "Moment",
        "ScoreSet",
    ):
        assert name in schemas, f"missing schema {name}"
