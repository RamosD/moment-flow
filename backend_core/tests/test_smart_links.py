"""Smart link regression: creation, destinations, click tracking and paused links."""

import pytest

from apps.links.models import SmartLink, SmartLinkClick, SmartLinkDestination
from tests import factories
from tests.conftest import ws_header

SMART_LINKS_URL = "/api/v1/smart-links/"
DESTINATIONS_URL = "/api/v1/smart-link-destinations/"


def _results(response):
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


@pytest.fixture
def owned_workspace(db, seeded, add_member):
    workspace = factories.WorkspaceFactory()
    owner = factories.UserFactory()
    add_member(workspace, owner, "owner")
    return workspace, owner


@pytest.mark.django_db
class TestSmartLinkCreation:
    def test_owner_creates_smart_link(self, owned_workspace, auth_client):
        workspace, owner = owned_workspace
        campaign = factories.CampaignFactory(workspace=workspace)
        resp = auth_client(owner).post(
            SMART_LINKS_URL,
            {"campaign": str(campaign.id), "title": "Listen Now"},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 201
        link = SmartLink.objects.get(id=resp.data["id"])
        assert link.workspace_id == workspace.id
        assert link.slug  # auto-generated

    def test_add_destination(self, owned_workspace, auth_client):
        workspace, owner = owned_workspace
        link = factories.SmartLinkFactory(workspace=workspace)
        resp = auth_client(owner).post(
            DESTINATIONS_URL,
            {
                "smart_link": str(link.id),
                "platform": "youtube",
                "url": "https://youtube.com/watch?v=abc",
                "sort_order": 0,
            },
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 201
        assert SmartLinkDestination.objects.filter(smart_link=link).count() == 1


@pytest.mark.django_db
class TestPublicResolution:
    def test_click_is_recorded_on_redirect(self, db, api_client):
        link = factories.SmartLinkFactory(status=SmartLink.Status.ACTIVE)
        destination = factories.SmartLinkDestinationFactory(
            smart_link=link, workspace=link.workspace
        )
        resp = api_client.get(f"/l/{link.slug}/?destination={destination.id}")
        assert resp.status_code == 302
        assert resp.url == destination.url
        assert SmartLinkClick.objects.filter(
            smart_link=link, destination=destination
        ).count() == 1

    def test_click_recorded_without_explicit_destination(self, db, api_client):
        link = factories.SmartLinkFactory(status=SmartLink.Status.ACTIVE)
        factories.SmartLinkDestinationFactory(smart_link=link, workspace=link.workspace)
        resp = api_client.get(f"/l/{link.slug}/")
        assert resp.status_code == 200
        assert SmartLinkClick.objects.filter(smart_link=link).count() == 1

    def test_paused_link_does_not_resolve(self, db, api_client):
        link = factories.SmartLinkFactory(status=SmartLink.Status.PAUSED)
        resp = api_client.get(f"/l/{link.slug}/")
        assert resp.status_code == 404
        assert SmartLinkClick.objects.filter(smart_link=link).count() == 0
