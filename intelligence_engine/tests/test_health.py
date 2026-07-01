from fastapi.testclient import TestClient


def test_health_returns_200_with_service_identification(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "intelligence_engine"
    assert body["version"] == "0.1.0"
    assert "timestamp" in body


def test_health_does_not_require_internal_token(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
