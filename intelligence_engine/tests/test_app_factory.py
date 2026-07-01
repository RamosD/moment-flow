"""Application-factory tests (IE-002 hardening).

Covers environment-specific wiring that the factory makes testable:
production must not expose the temporary debug routes, and an invalid
production configuration must stop the app from being built at all.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.errors import ConfigError
from app.main import create_app

PROD_TOKEN = "prod-token-not-a-real-secret"  # noqa: S105


def test_health_is_available_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("INTERNAL_API_TOKEN", PROD_TOKEN)
    get_settings.cache_clear()
    try:
        with TestClient(create_app(), raise_server_exceptions=False) as client:
            assert client.get("/health").status_code == 200
    finally:
        get_settings.cache_clear()


def test_debug_routes_are_not_mounted_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("INTERNAL_API_TOKEN", PROD_TOKEN)
    get_settings.cache_clear()
    try:
        with TestClient(create_app(), raise_server_exceptions=False) as client:
            # Even with the correct token, the route simply does not exist.
            response = client.get("/internal/_debug/ping", headers={"X-Internal-Token": PROD_TOKEN})
            assert response.status_code == 404
            assert response.json()["error"]["code"] == "not_found"
    finally:
        get_settings.cache_clear()


def test_debug_routes_are_mounted_outside_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("INTERNAL_API_TOKEN", PROD_TOKEN)
    get_settings.cache_clear()
    try:
        with TestClient(create_app(), raise_server_exceptions=False) as client:
            response = client.get("/internal/_debug/ping", headers={"X-Internal-Token": PROD_TOKEN})
            assert response.status_code == 200
    finally:
        get_settings.cache_clear()


def test_create_app_blocks_boot_in_production_without_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "")
    get_settings.cache_clear()
    try:
        with pytest.raises(ConfigError):
            create_app()
    finally:
        get_settings.cache_clear()
