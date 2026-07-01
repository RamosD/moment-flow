"""Fixtures for notification tests."""

import pytest
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from rest_framework.test import APIClient

from apps.rbac.models import Role
from apps.rbac.seeds import seed_rbac
from apps.workspaces.models import WorkspaceMember
from apps.workspaces.services import create_workspace

User = get_user_model()


@pytest.fixture
def seeded(db):
    return seed_rbac()


@pytest.fixture
def make_user(db):
    def _make_user(email, password="pass-12345", **extra):
        return User.objects.create_user(email=email, password=password, **extra)

    return _make_user


@pytest.fixture
def owner(make_user):
    return make_user("notif-owner@example.com")


@pytest.fixture
def workspace(seeded, owner):
    return create_workspace(user=owner, name="Notif WS")


@pytest.fixture
def other_owner(make_user):
    return make_user("notif-owner2@example.com")


@pytest.fixture
def other_workspace(seeded, other_owner):
    return create_workspace(user=other_owner, name="Other Notif WS")


@pytest.fixture
def add_member():
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


@pytest.fixture
def client_for():
    def _client_for(user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    return _client_for


def ws_header(workspace):
    return {"HTTP_X_WORKSPACE_ID": str(workspace.id)}
