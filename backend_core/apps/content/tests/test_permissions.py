"""RBAC enforcement on content endpoints."""

import pytest

from apps.content.models import ContentPack, ContentPackRequest
from apps.content.tests.conftest import ws_header

TEMPLATES_URL = "/api/v1/templates/"
REQUESTS_URL = "/api/v1/content-pack-requests/"


@pytest.mark.django_db
class TestContentPermissions:
    def test_viewer_can_view_catalogue(
        self, client_for, make_user, workspace, add_member
    ):
        viewer = make_user("viewer@example.com")
        add_member(workspace, viewer, "viewer")
        resp = client_for(viewer).get(TEMPLATES_URL, **ws_header(workspace))
        assert resp.status_code == 200

    def test_viewer_cannot_create_request(
        self, client_for, make_user, workspace, add_member, make_campaign
    ):
        viewer = make_user("viewer@example.com")
        add_member(workspace, viewer, "viewer")
        campaign = make_campaign(workspace)
        pack = ContentPack.objects.get(pack_key="release_pack")
        resp = client_for(viewer).post(
            REQUESTS_URL,
            {"campaign": str(campaign.id), "content_pack": str(pack.id)},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 403
        assert not ContentPackRequest.objects.filter(workspace=workspace).exists()

    def test_editor_can_create_request(
        self, client_for, make_user, workspace, add_member, make_campaign
    ):
        editor = make_user("editor@example.com")
        add_member(workspace, editor, "editor")
        campaign = make_campaign(workspace)
        pack = ContentPack.objects.get(pack_key="release_pack")
        resp = client_for(editor).post(
            REQUESTS_URL,
            {"campaign": str(campaign.id), "content_pack": str(pack.id)},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 201
        assert ContentPackRequest.objects.filter(workspace=workspace).count() == 1
