"""RBAC enforcement on campaign endpoints."""

import pytest

from apps.campaigns.models import Campaign
from apps.campaigns.tests.conftest import ws_header

CAMPAIGNS_URL = "/api/v1/campaigns/"


@pytest.mark.django_db
class TestCampaignPermissions:
    def _payload(self, artist):
        return {"artist": str(artist.id), "name": "RBAC C"}

    def test_viewer_can_list_but_not_create(
        self, client_for, make_user, workspace, make_artist, add_member
    ):
        viewer = make_user("viewer@example.com")
        add_member(workspace, viewer, "viewer")
        artist = make_artist(workspace)
        client = client_for(viewer)

        assert client.get(CAMPAIGNS_URL, **ws_header(workspace)).status_code == 200
        resp = client.post(
            CAMPAIGNS_URL, self._payload(artist), format="json", **ws_header(workspace)
        )
        assert resp.status_code == 403
        assert not Campaign.objects.filter(workspace=workspace).exists()

    def test_editor_can_create_but_not_delete(
        self, client_for, make_user, workspace, make_artist, add_member
    ):
        editor = make_user("editor@example.com")
        add_member(workspace, editor, "editor")
        artist = make_artist(workspace)
        client = client_for(editor)

        create = client.post(
            CAMPAIGNS_URL, self._payload(artist), format="json", **ws_header(workspace)
        )
        assert create.status_code == 201
        campaign_id = create.data["id"]

        delete = client.delete(
            f"{CAMPAIGNS_URL}{campaign_id}/", **ws_header(workspace)
        )
        assert delete.status_code == 403
        assert Campaign.objects.filter(id=campaign_id).exists()

    def test_owner_can_delete_campaign_soft(
        self, client_for, owner, workspace, make_artist
    ):
        artist = make_artist(workspace)
        client = client_for(owner)
        campaign_id = client.post(
            CAMPAIGNS_URL, self._payload(artist), format="json", **ws_header(workspace)
        ).data["id"]

        resp = client.delete(f"{CAMPAIGNS_URL}{campaign_id}/", **ws_header(workspace))
        assert resp.status_code == 204
        assert not Campaign.objects.filter(id=campaign_id).exists()
        assert Campaign.all_objects.filter(id=campaign_id).exists()
