"""Asset API tests: creation, workspace isolation and soft delete."""

import pytest

from apps.core.models import Asset

ASSETS_URL = "/api/v1/assets/"
HDR = "HTTP_X_WORKSPACE_ID"


def _results(response):
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


def _ws(workspace):
    return {HDR: str(workspace.id)}


@pytest.mark.django_db
class TestAssetCreation:
    def test_authenticated_member_creates_asset(self, client_a, user_a, workspace_a):
        resp = client_a.post(
            ASSETS_URL,
            {"asset_type": "logo", "file_name": "logo.png"},
            format="json",
            **_ws(workspace_a),
        )
        assert resp.status_code == 201
        asset = Asset.objects.get(id=resp.data["id"])
        assert asset.workspace_id == workspace_a.id
        assert asset.created_by_id == user_a.id
        assert asset.asset_type == "logo"

    def test_anonymous_is_rejected(self, workspace_a):
        from rest_framework.test import APIClient

        resp = APIClient().get(ASSETS_URL, **_ws(workspace_a))
        assert resp.status_code == 401

    def test_missing_workspace_header_is_rejected(self, client_a, workspace_a):
        resp = client_a.get(ASSETS_URL)
        assert resp.status_code == 400


@pytest.mark.django_db
class TestAssetIsolation:
    def _create_asset(self, client, workspace, name):
        return client.post(
            ASSETS_URL,
            {"asset_type": "cover", "file_name": name},
            format="json",
            **_ws(workspace),
        )

    def test_list_returns_only_active_workspace_assets(
        self, client_a, client_b, workspace_a, workspace_b
    ):
        self._create_asset(client_a, workspace_a, "a.png")
        self._create_asset(client_b, workspace_b, "b.png")

        resp_a = client_a.get(ASSETS_URL, **_ws(workspace_a))
        names_a = {a["file_name"] for a in _results(resp_a)}
        assert names_a == {"a.png"}

        resp_b = client_b.get(ASSETS_URL, **_ws(workspace_b))
        names_b = {a["file_name"] for a in _results(resp_b)}
        assert names_b == {"b.png"}

    def test_non_member_cannot_access_workspace_assets(
        self, client_a, workspace_b
    ):
        # Alice is not a member of Bob's workspace.
        resp = client_a.get(ASSETS_URL, **_ws(workspace_b))
        assert resp.status_code == 403

    def test_cannot_retrieve_asset_from_other_workspace(
        self, client_a, client_b, workspace_a, workspace_b
    ):
        created = self._create_asset(client_b, workspace_b, "secret.png")
        asset_id = created.data["id"]
        # Alice asks for Bob's asset using her own workspace context.
        resp = client_a.get(f"{ASSETS_URL}{asset_id}/", **_ws(workspace_a))
        assert resp.status_code == 404


@pytest.mark.django_db
class TestAssetSoftDelete:
    def test_delete_soft_deletes_and_hides_asset(self, client_a, workspace_a):
        created = client_a.post(
            ASSETS_URL,
            {"asset_type": "other", "file_name": "tmp.bin"},
            format="json",
            **_ws(workspace_a),
        )
        asset_id = created.data["id"]

        resp = client_a.delete(f"{ASSETS_URL}{asset_id}/", **_ws(workspace_a))
        assert resp.status_code == 204

        # Hidden from the API and default manager, but retained in all_objects.
        listing = client_a.get(ASSETS_URL, **_ws(workspace_a))
        assert all(a["id"] != asset_id for a in _results(listing))
        assert not Asset.objects.filter(id=asset_id).exists()
        assert Asset.all_objects.filter(id=asset_id).exists()

    def test_filter_by_asset_type(self, client_a, workspace_a):
        client_a.post(
            ASSETS_URL,
            {"asset_type": "logo", "file_name": "l.png"},
            format="json",
            **_ws(workspace_a),
        )
        client_a.post(
            ASSETS_URL,
            {"asset_type": "cover", "file_name": "c.png"},
            format="json",
            **_ws(workspace_a),
        )
        resp = client_a.get(f"{ASSETS_URL}?asset_type=logo", **_ws(workspace_a))
        names = {a["file_name"] for a in _results(resp)}
        assert names == {"l.png"}
