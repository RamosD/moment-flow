"""ContentPackRequest service/flow and ContentOutput entity tests."""

import pytest

from apps.content.models import (
    ContentOutput,
    ContentPack,
    ContentPackRequest,
    Template,
)
from apps.content.tests.conftest import ws_header

REQUESTS_URL = "/api/v1/content-pack-requests/"
OUTPUTS_URL = "/api/v1/content-outputs/"


def _results(response):
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


@pytest.mark.django_db
class TestContentPackRequest:
    def test_create_request_for_campaign_is_queued(
        self, client_for, owner, workspace, make_campaign
    ):
        campaign = make_campaign(workspace)
        pack = ContentPack.objects.get(pack_key="release_pack")
        resp = client_for(owner).post(
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

    def test_rejects_campaign_from_other_workspace(
        self, client_for, owner, workspace, other_workspace, make_campaign
    ):
        foreign_campaign = make_campaign(other_workspace, name="F", slug="f")
        pack = ContentPack.objects.get(pack_key="release_pack")
        resp = client_for(owner).post(
            REQUESTS_URL,
            {"campaign": str(foreign_campaign.id), "content_pack": str(pack.id)},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 400
        assert "campaign" in resp.data

    def test_rejects_inactive_pack(
        self, client_for, owner, workspace, make_campaign
    ):
        campaign = make_campaign(workspace)
        draft_pack = ContentPack.objects.create(
            pack_key="draft_pack",
            name="Draft Pack",
            pack_type=ContentPack.PackType.RELEASE_PACK,
            status=ContentPack.Status.DRAFT,
            workspace=None,
        )
        resp = client_for(owner).post(
            REQUESTS_URL,
            {"campaign": str(campaign.id), "content_pack": str(draft_pack.id)},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 400
        assert "content_pack" in resp.data

    def test_isolation_requests_not_shared(
        self, client_for, owner, workspace, other_owner, other_workspace, make_campaign
    ):
        campaign = make_campaign(workspace)
        pack = ContentPack.objects.get(pack_key="release_pack")
        client_for(owner).post(
            REQUESTS_URL,
            {"campaign": str(campaign.id), "content_pack": str(pack.id)},
            format="json",
            **ws_header(workspace),
        )
        resp = client_for(other_owner).get(REQUESTS_URL, **ws_header(other_workspace))
        assert resp.status_code == 200
        assert _results(resp) == []


@pytest.mark.django_db
class TestContentOutput:
    def test_output_can_exist_as_core_entity(
        self, client_for, owner, workspace, make_campaign
    ):
        campaign = make_campaign(workspace)
        template = Template.objects.get(template_key="system_post")
        resp = client_for(owner).post(
            OUTPUTS_URL,
            {
                "campaign": str(campaign.id),
                "template": str(template.id),
                "output_type": "post",
                "title": "Launch Post",
            },
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 201
        output = ContentOutput.objects.get(id=resp.data["id"])
        assert output.workspace_id == workspace.id
        assert output.created_by_id == owner.id
        assert output.status == ContentOutput.Status.QUEUED
        assert output.public_visibility == ContentOutput.Visibility.PRIVATE

    def test_export_action_is_placeholder(
        self, client_for, owner, workspace, make_campaign
    ):
        campaign = make_campaign(workspace)
        template = Template.objects.get(template_key="system_post")
        output_id = client_for(owner).post(
            OUTPUTS_URL,
            {"campaign": str(campaign.id), "template": str(template.id), "output_type": "post"},
            format="json",
            **ws_header(workspace),
        ).data["id"]

        resp = client_for(owner).post(
            f"{OUTPUTS_URL}{output_id}/export/", **ws_header(workspace)
        )
        assert resp.status_code == 200
        assert resp.data["export"] == "placeholder"
