"""Public resolution + click tracking."""

import pytest
from rest_framework.test import APIClient

from apps.content.models import ContentOutput, Template
from apps.links.models import SmartLink, SmartLinkClick

VIDEO_URL = "https://youtube.com/watch?v=x"


@pytest.fixture
def public_client():
    return APIClient()


@pytest.mark.django_db
class TestPublicResolution:
    def test_active_link_without_choice_returns_destinations(
        self, public_client, workspace, make_campaign, make_smart_link, make_destination
    ):
        link = make_smart_link(workspace, make_campaign(workspace), "open")
        make_destination(workspace, link, "youtube", VIDEO_URL, sort_order=0)
        make_destination(workspace, link, "spotify", "https://open.spotify.com/x", sort_order=1)

        resp = public_client.get(f"/l/{link.slug}/")
        assert resp.status_code == 200
        assert len(resp.data["destinations"]) == 2
        # A click (open) was recorded with no destination.
        click = SmartLinkClick.objects.get(smart_link=link)
        assert click.destination is None
        assert click.campaign_id == link.campaign_id

    def test_explicit_destination_redirects_and_records_click(
        self, public_client, workspace, make_campaign, make_smart_link, make_destination
    ):
        link = make_smart_link(workspace, make_campaign(workspace), "go")
        dest = make_destination(workspace, link, "youtube", VIDEO_URL)
        resp = public_client.get(f"/l/{link.slug}/?destination={dest.id}")
        assert resp.status_code == 302
        assert resp["Location"] == VIDEO_URL
        click = SmartLinkClick.objects.get(smart_link=link)
        assert click.destination_id == dest.id

    def test_paused_link_does_not_resolve(
        self, public_client, workspace, make_campaign, make_smart_link
    ):
        link = make_smart_link(
            workspace, make_campaign(workspace), "paused", status=SmartLink.Status.PAUSED
        )
        resp = public_client.get(f"/l/{link.slug}/")
        assert resp.status_code == 404
        assert not SmartLinkClick.objects.filter(smart_link=link).exists()

    def test_click_does_not_store_raw_ip(
        self, public_client, workspace, make_campaign, make_smart_link
    ):
        link = make_smart_link(workspace, make_campaign(workspace), "priv")
        public_client.get(f"/l/{link.slug}/", REMOTE_ADDR="203.0.113.7")
        click = SmartLinkClick.objects.get(smart_link=link)
        assert click.ip_hash and "203.0.113.7" not in click.ip_hash
        assert len(click.ip_hash) == 64  # sha256 hex

    def test_content_output_association_via_query(
        self, public_client, workspace, make_campaign, make_smart_link
    ):
        campaign = make_campaign(workspace)
        link = make_smart_link(workspace, campaign, "co")
        template = Template.objects.create(
            workspace=workspace,
            template_key="ws_tpl",
            name="WS",
            template_type=Template.TemplateType.POST,
            status=Template.Status.ACTIVE,
        )
        output = ContentOutput.objects.create(
            workspace=workspace, campaign=campaign, template=template, output_type="post"
        )
        public_client.get(f"/l/{link.slug}/?content_output={output.id}")
        click = SmartLinkClick.objects.get(smart_link=link)
        assert click.content_output_id == output.id

    def test_unknown_slug_returns_404(self, public_client):
        assert public_client.get("/l/does-not-exist/").status_code == 404
