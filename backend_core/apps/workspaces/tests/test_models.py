"""Model/service level tests: owner membership, uniqueness, soft delete."""

import pytest
from django.db import IntegrityError

from apps.workspaces.models import ROLE_OWNER, Workspace, WorkspaceMember
from apps.workspaces.services import create_workspace


@pytest.mark.django_db
class TestWorkspaceService:
    def test_create_workspace_sets_owner_membership(self, user_a):
        workspace = create_workspace(user=user_a, name="My Label")
        assert workspace.created_by == user_a
        assert workspace.slug == "my-label"
        member = WorkspaceMember.objects.get(workspace=workspace, user=user_a)
        assert member.role_key == ROLE_OWNER
        assert member.status == WorkspaceMember.Status.ACTIVE

    def test_unique_member_per_workspace(self, user_a):
        workspace = create_workspace(user=user_a, name="My Label")
        with pytest.raises(IntegrityError):
            WorkspaceMember.objects.create(workspace=workspace, user=user_a)


@pytest.mark.django_db
class TestSoftDelete:
    def test_soft_deleted_workspace_hidden_from_default_manager(self, user_a):
        workspace = create_workspace(user=user_a, name="Temp WS")
        workspace.soft_delete()
        assert not Workspace.objects.filter(pk=workspace.pk).exists()
        assert Workspace.all_objects.filter(pk=workspace.pk).exists()
        assert workspace.is_deleted is True
