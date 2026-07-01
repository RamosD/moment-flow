"""SmartLink/Destination CRUD, isolation, permissions and stats."""

import pytest

from apps.links.models import SmartLink, SmartLinkDestination
from apps.links.tests.conftest import ws_header

LINKS_URL = "/api/v1/smart-links/"
DEST_URL = "/api/v1/smart-link-destinations/"


def _results(response):
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


@pytest.mark.django_db
class TestSmartLinkCrud:
    def test_owner_creates_smart_link_for_campaign(
        self, client_for, owner, workspace, make_campaign
    ):
        campaign = make_campaign(workspace)
        resp = client_for(owner).post(
            LINKS_URL,
            {"campaign": str(campaign.id), "title": "My Release"},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 201
        assert resp.data["slug"] == "my-release"
        link = SmartLink.objects.get(id=resp.data["id"])
        assert link.workspace_id == workspace.id
        assert link.created_by_id == owner.id

    def test_smart_link_supports_multiple_destinations(
        self, client_for, owner, workspace, make_campaign, make_smart_link
    ):
        campaign = make_campaign(workspace)
        link = make_smart_link(workspace, campaign, "multi")
        client = client_for(owner)
        for platform, url in [
            ("youtube", "https://youtube.com/watch?v=x"),
            ("spotify", "https://open.spotify.com/track/x"),
        ]:
            resp = client.post(
                DEST_URL,
                {"smart_link": str(link.id), "platform": platform, "url": url},
                format="json",
                **ws_header(workspace),
            )
            assert resp.status_code == 201
        assert SmartLinkDestination.objects.filter(smart_link=link).count() == 2

    def test_destination_rejects_link_from_other_workspace(
        self, client_for, owner, workspace, other_workspace, make_campaign, make_smart_link
    ):
        foreign_campaign = make_campaign(other_workspace, name="F", slug="f")
        foreign_link = make_smart_link(other_workspace, foreign_campaign, "foreign")
        resp = client_for(owner).post(
            DEST_URL,
            {"smart_link": str(foreign_link.id), "platform": "website", "url": "https://x.com"},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 400
        assert "smart_link" in resp.data


@pytest.mark.django_db
class TestSmartLinkIsolationAndPermissions:
    def test_list_only_own_workspace_links(
        self, client_for, owner, workspace, other_owner, other_workspace,
        make_campaign, make_smart_link,
    ):
        make_smart_link(workspace, make_campaign(workspace), "mine")
        make_smart_link(
            other_workspace, make_campaign(other_workspace, name="O", slug="o"), "theirs"
        )
        resp = client_for(owner).get(LINKS_URL, **ws_header(workspace))
        slugs = {link["slug"] for link in _results(resp)}
        assert slugs == {"mine"}

    def test_viewer_cannot_create_link(
        self, client_for, make_user, workspace, add_member, make_campaign
    ):
        viewer = make_user("viewer@example.com")
        add_member(workspace, viewer, "viewer")
        campaign = make_campaign(workspace)
        resp = client_for(viewer).post(
            LINKS_URL, {"campaign": str(campaign.id), "title": "Nope"},
            format="json", **ws_header(workspace),
        )
        assert resp.status_code == 403

    def test_editor_can_create_link(
        self, client_for, make_user, workspace, add_member, make_campaign
    ):
        editor = make_user("editor@example.com")
        add_member(workspace, editor, "editor")
        campaign = make_campaign(workspace)
        resp = client_for(editor).post(
            LINKS_URL, {"campaign": str(campaign.id), "title": "Yes"},
            format="json", **ws_header(workspace),
        )
        assert resp.status_code == 201


@pytest.mark.django_db
class TestStats:
    def test_stats_endpoint(
        self, client_for, owner, workspace, make_campaign, make_smart_link, make_destination
    ):
        campaign = make_campaign(workspace)
        link = make_smart_link(workspace, campaign, "stats")
        dest = make_destination(workspace, link, "youtube", "https://youtube.com/x")
        # Generate a couple of clicks via the public endpoint.
        from rest_framework.test import APIClient

        public = APIClient()
        public.get(f"/l/{link.slug}/")  # destination null
        public.get(f"/l/{link.slug}/?destination={dest.id}")  # via destination

        resp = client_for(owner).get(f"{LINKS_URL}{link.id}/stats/", **ws_header(workspace))
        assert resp.status_code == 200
        assert resp.data["total_clicks"] == 2
        assert len(resp.data["by_day"]) >= 1
