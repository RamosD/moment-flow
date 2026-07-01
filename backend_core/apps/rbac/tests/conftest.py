"""Shared fixtures for RBAC tests."""

import pytest
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from apps.rbac.models import Role
from apps.rbac.seeds import seed_rbac
from apps.workspaces.models import WorkspaceMember
from apps.workspaces.services import create_workspace

User = get_user_model()


@pytest.fixture
def rbac(db):
    """Seed system roles and permissions for the test database."""
    return seed_rbac()


@pytest.fixture
def make_user(db):
    def _make_user(email, password="pass-12345", **extra):
        return User.objects.create_user(email=email, password=password, **extra)

    return _make_user


@pytest.fixture
def owner(make_user):
    return make_user("owner@example.com")


@pytest.fixture
def workspace(rbac, owner):
    """A workspace whose creator (``owner``) is the active owner member."""
    return create_workspace(user=owner, name="RBAC WS")


@pytest.fixture
def add_member():
    """Return a helper that adds ``user`` to ``workspace`` with a system role."""

    def _add_member(workspace, user, role_key, status=WorkspaceMember.Status.ACTIVE):
        role = Role.objects.get(workspace__isnull=True, key=role_key)
        return WorkspaceMember.objects.create(
            workspace=workspace,
            user=user,
            role=role,
            role_key=role_key,
            status=status,
            joined_at=now(),
        )

    return _add_member
