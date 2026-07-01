"""Content pack request regression: valid creation, permission and tenant guards."""

import pytest

from apps.content.models import ContentPack, ContentPackRequest
from tests import factories
from tests.conftest import ws_header

REQUESTS_URL = "/api/v1/content-pack-requests/"


@pytest.fixture
def setup(db, seeded, add_member):
    """A workspace with an owner and an active global content pack."""
    workspace = factories.WorkspaceFactory()
    owner = factories.UserFactory()
    add_member(workspace, owner, "owner")
    pack = factories.ContentPackFactory(workspace=None, status=ContentPack.Status.ACTIVE)
    return workspace, owner, pack


@pytest.mark.django_db
class TestContentPackRequest:
    def test_valid_creation_is_queued(self, setup, auth_client):
        workspace, owner, pack = setup
        campaign = factories.CampaignFactory(workspace=workspace)
        resp = auth_client(owner).post(
            REQUESTS_URL,
            {"campaign": str(campaign.id), "content_pack": str(pack.id)},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 201
        request = ContentPackRequest.objects.get(id=resp.data["id"])
        assert request.status == ContentPackRequest.Status.QUEUED
        assert request.workspace_id == workspace.id
        assert request.requested_by_id == owner.id

    def test_blocked_without_permission(self, setup, auth_client, add_member):
        workspace, _owner, pack = setup
        viewer = factories.UserFactory()
        add_member(workspace, viewer, "viewer")  # no content:generate
        campaign = factories.CampaignFactory(workspace=workspace)
        resp = auth_client(viewer).post(
            REQUESTS_URL,
            {"campaign": str(campaign.id), "content_pack": str(pack.id)},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 403
        assert not ContentPackRequest.objects.filter(workspace=workspace).exists()

    def test_blocked_for_foreign_workspace_campaign(self, setup, auth_client):
        workspace, owner, pack = setup
        foreign_campaign = factories.CampaignFactory()  # different workspace
        resp = auth_client(owner).post(
            REQUESTS_URL,
            {"campaign": str(foreign_campaign.id), "content_pack": str(pack.id)},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 400
        assert "campaign" in resp.data
        assert not ContentPackRequest.objects.filter(workspace=workspace).exists()
