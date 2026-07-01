"""Endpoint-level RBAC: member management and workspace mutation."""

import pytest
from rest_framework.test import APIClient

from apps.workspaces.models import WorkspaceMember

MEMBERS_URL = "/api/v1/workspace-members/"
HDR = "HTTP_X_WORKSPACE_ID"


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestMemberManagementRBAC:
    def test_owner_can_invite_member(self, workspace, owner, make_user):
        newbie = make_user("newbie@example.com")
        resp = client_for(owner).post(
            MEMBERS_URL,
            {"user": str(newbie.id), "role_key": "editor"},
            format="json",
            **{HDR: str(workspace.id)},
        )
        assert resp.status_code == 201
        member = WorkspaceMember.objects.get(workspace=workspace, user=newbie)
        assert member.role_key == "editor"
        assert member.role.key == "editor"
        assert member.invited_by_id == owner.id

    def test_viewer_cannot_invite_member(self, workspace, make_user, add_member):
        viewer = make_user("viewer@example.com")
        add_member(workspace, viewer, "viewer")
        target = make_user("target@example.com")
        resp = client_for(viewer).post(
            MEMBERS_URL,
            {"user": str(target.id), "role_key": "viewer"},
            format="json",
            **{HDR: str(workspace.id)},
        )
        assert resp.status_code == 403
        assert not WorkspaceMember.objects.filter(
            workspace=workspace, user=target
        ).exists()

    def test_editor_cannot_invite_member(self, workspace, make_user, add_member):
        editor = make_user("editor@example.com")
        add_member(workspace, editor, "editor")
        target = make_user("target2@example.com")
        resp = client_for(editor).post(
            MEMBERS_URL,
            {"user": str(target.id), "role_key": "viewer"},
            format="json",
            **{HDR: str(workspace.id)},
        )
        assert resp.status_code == 403

    def test_admin_can_update_member_role(self, workspace, make_user, add_member):
        admin = make_user("admin@example.com")
        add_member(workspace, admin, "admin")
        member_user = make_user("member@example.com")
        member = add_member(workspace, member_user, "viewer")
        resp = client_for(admin).patch(
            f"{MEMBERS_URL}{member.id}/",
            {"role_key": "editor"},
            format="json",
            **{HDR: str(workspace.id)},
        )
        assert resp.status_code == 200
        member.refresh_from_db()
        assert member.role_key == "editor"
        assert member.role.key == "editor"

    def test_listing_requires_workspace_header(self, workspace, owner):
        resp = client_for(owner).get(MEMBERS_URL)
        assert resp.status_code == 400

    def test_member_can_list_with_header(self, workspace, owner):
        resp = client_for(owner).get(MEMBERS_URL, **{HDR: str(workspace.id)})
        assert resp.status_code == 200

    def test_non_member_cannot_list(self, workspace, make_user):
        outsider = make_user("outsider@example.com")
        resp = client_for(outsider).get(MEMBERS_URL, **{HDR: str(workspace.id)})
        assert resp.status_code == 403


@pytest.mark.django_db
class TestWorkspaceMutationRBAC:
    def test_owner_can_update_workspace(self, workspace, owner):
        resp = client_for(owner).patch(
            f"/api/v1/workspaces/{workspace.id}/",
            {"name": "Renamed WS"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["name"] == "Renamed WS"

    def test_viewer_cannot_update_workspace(self, workspace, make_user, add_member):
        viewer = make_user("viewer3@example.com")
        add_member(workspace, viewer, "viewer")
        resp = client_for(viewer).patch(
            f"/api/v1/workspaces/{workspace.id}/",
            {"name": "Hacked"},
            format="json",
        )
        assert resp.status_code == 403
        workspace.refresh_from_db()
        assert workspace.name != "Hacked"
