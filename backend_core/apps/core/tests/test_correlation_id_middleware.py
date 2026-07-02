"""Correlation-id middleware tests (STG-PRE-005).

Exercises the full middleware stack via the Django test client (not a direct
unit call), so this proves the header really flows through request → response
for a real endpoint.
"""

import pytest

from apps.core.middleware import CORRELATION_ID_HEADER

ASSETS_URL = "/api/v1/assets/"
HDR = "HTTP_X_WORKSPACE_ID"


@pytest.mark.django_db
class TestCorrelationIdMiddleware:
    def test_generates_id_when_absent(self, client_a, workspace_a):
        resp = client_a.get(ASSETS_URL, **{HDR: str(workspace_a.id)})
        assert resp.status_code == 200
        correlation_id = resp.headers.get(CORRELATION_ID_HEADER)
        assert correlation_id
        assert len(correlation_id) == 32  # uuid4().hex

    def test_reuses_a_well_formed_incoming_id(self, client_a, workspace_a):
        resp = client_a.get(
            ASSETS_URL,
            **{HDR: str(workspace_a.id), "HTTP_X_REQUEST_ID": "my-upstream-id-123"},
        )
        assert resp.status_code == 200
        assert resp.headers.get(CORRELATION_ID_HEADER) == "my-upstream-id-123"

    def test_two_requests_without_header_get_different_ids(self, client_a, workspace_a):
        resp1 = client_a.get(ASSETS_URL, **{HDR: str(workspace_a.id)})
        resp2 = client_a.get(ASSETS_URL, **{HDR: str(workspace_a.id)})
        id1 = resp1.headers.get(CORRELATION_ID_HEADER)
        id2 = resp2.headers.get(CORRELATION_ID_HEADER)
        assert id1 and id2 and id1 != id2

    @pytest.mark.parametrize(
        "bad_id",
        [
            "id with spaces",
            "id/with/slashes",
            "a" * 65,  # over the 64-char bound
            "",
        ],
    )
    def test_rejects_malformed_incoming_id_and_generates_one(
        self, client_a, workspace_a, bad_id
    ):
        resp = client_a.get(
            ASSETS_URL,
            **{HDR: str(workspace_a.id), "HTTP_X_REQUEST_ID": bad_id},
        )
        assert resp.status_code == 200
        correlation_id = resp.headers.get(CORRELATION_ID_HEADER)
        assert correlation_id and correlation_id != bad_id
        assert len(correlation_id) == 32
