"""Service-level RBAC checks per role."""

import pytest
from rest_framework.exceptions import PermissionDenied

from apps.rbac.services import (
    get_user_workspace_role,
    require_workspace_permission,
    user_has_permission,
)


@pytest.mark.django_db
class TestRolePermissions:
    def test_owner_has_everything(self, workspace, owner):
        for perm in [
            "workspace:manage",
            "billing:manage",
            "members:manage",
            "artists:delete",
            "api_keys:manage",
        ]:
            assert user_has_permission(owner, workspace, perm)

    def test_viewer_is_read_only(self, workspace, make_user, add_member):
        viewer = make_user("viewer@example.com")
        add_member(workspace, viewer, "viewer")
        assert user_has_permission(viewer, workspace, "artists:view")
        assert not user_has_permission(viewer, workspace, "artists:create")
        assert not user_has_permission(viewer, workspace, "content:generate")
        assert not user_has_permission(viewer, workspace, "members:invite")

    def test_editor_writes_but_no_delete_or_members(self, workspace, make_user, add_member):
        editor = make_user("editor@example.com")
        add_member(workspace, editor, "editor")
        assert user_has_permission(editor, workspace, "artists:create")
        assert user_has_permission(editor, workspace, "content:generate")
        assert not user_has_permission(editor, workspace, "artists:delete")
        assert not user_has_permission(editor, workspace, "members:invite")
        assert not user_has_permission(editor, workspace, "billing:manage")

    def test_admin_manages_members_not_billing_or_workspace(
        self, workspace, make_user, add_member
    ):
        admin = make_user("admin@example.com")
        add_member(workspace, admin, "admin")
        assert user_has_permission(admin, workspace, "members:manage")
        assert user_has_permission(admin, workspace, "artists:delete")
        assert not user_has_permission(admin, workspace, "billing:manage")
        assert not user_has_permission(admin, workspace, "workspace:manage")

    def test_billing_admin_manages_billing_only(self, workspace, make_user, add_member):
        billing = make_user("billing@example.com")
        add_member(workspace, billing, "billing_admin")
        assert user_has_permission(billing, workspace, "billing:view")
        assert user_has_permission(billing, workspace, "billing:manage")
        assert not user_has_permission(billing, workspace, "artists:create")
        assert not user_has_permission(billing, workspace, "members:manage")

    def test_non_member_has_no_role_and_no_permission(self, workspace, make_user):
        outsider = make_user("outsider@example.com")
        assert get_user_workspace_role(outsider, workspace) is None
        assert not user_has_permission(outsider, workspace, "artists:view")

    def test_require_workspace_permission_raises_for_viewer(
        self, workspace, make_user, add_member
    ):
        viewer = make_user("viewer2@example.com")
        add_member(workspace, viewer, "viewer")
        with pytest.raises(PermissionDenied):
            require_workspace_permission(viewer, workspace, "artists:create")
