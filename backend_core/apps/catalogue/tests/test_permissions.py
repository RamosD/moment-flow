"""RBAC enforcement on catalogue endpoints."""

import pytest

from apps.catalogue.models import Artist
from apps.catalogue.tests.conftest import ws_header

ARTISTS_URL = "/api/v1/artists/"


@pytest.mark.django_db
class TestArtistPermissions:
    def test_viewer_can_list_but_not_create(
        self, client_for, make_user, workspace, add_member
    ):
        viewer = make_user("viewer@example.com")
        add_member(workspace, viewer, "viewer")
        client = client_for(viewer)

        assert client.get(ARTISTS_URL, **ws_header(workspace)).status_code == 200

        resp = client.post(
            ARTISTS_URL, {"name": "Nope"}, format="json", **ws_header(workspace)
        )
        assert resp.status_code == 403
        assert not Artist.objects.filter(workspace=workspace, name="Nope").exists()

    def test_editor_can_create_but_not_delete(
        self, client_for, make_user, workspace, add_member
    ):
        editor = make_user("editor@example.com")
        add_member(workspace, editor, "editor")
        client = client_for(editor)

        create = client.post(
            ARTISTS_URL, {"name": "Editor Artist"}, format="json", **ws_header(workspace)
        )
        assert create.status_code == 201

        artist_id = create.data["id"]
        delete = client.delete(
            f"{ARTISTS_URL}{artist_id}/", **ws_header(workspace)
        )
        assert delete.status_code == 403
        assert Artist.objects.filter(id=artist_id).exists()

    def test_owner_can_delete_artist_soft(
        self, client_for, owner, workspace
    ):
        client = client_for(owner)
        artist_id = client.post(
            ARTISTS_URL, {"name": "Doomed"}, format="json", **ws_header(workspace)
        ).data["id"]

        resp = client.delete(f"{ARTISTS_URL}{artist_id}/", **ws_header(workspace))
        assert resp.status_code == 204
        assert not Artist.objects.filter(id=artist_id).exists()
        assert Artist.all_objects.filter(id=artist_id).exists()
