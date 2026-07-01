"""Shared test fixtures.

Apps are built per-test through `create_app()` so each test runs against an
instance configured from its own (monkeypatched) environment, with settings
injected via `app.state` rather than a process-global singleton. The
`TestClient` is entered as a context manager so the lifespan (startup/shutdown)
actually runs.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app

# Non-secret fixture value used wherever a configured token is needed.
INTERNAL_TEST_TOKEN = "test-internal-token-not-a-real-secret"  # noqa: S105


@pytest.fixture
def internal_token() -> str:
    return INTERNAL_TEST_TOKEN


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Client for an app with no token configured (development defaults)."""
    get_settings.cache_clear()
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client
    get_settings.cache_clear()


@pytest.fixture
def client_with_token(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Client for an app with `INTERNAL_TEST_TOKEN` configured."""
    monkeypatch.setenv("INTERNAL_API_TOKEN", INTERNAL_TEST_TOKEN)
    get_settings.cache_clear()
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client
    get_settings.cache_clear()
