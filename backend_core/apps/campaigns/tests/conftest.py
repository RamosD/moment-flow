"""Fixtures for campaigns tests."""

import pytest
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from rest_framework.test import APIClient

from apps.catalogue.models import Artist, Track
from apps.rbac.models import Role
from apps.rbac.seeds import seed_rbac
from apps.workspaces.models import WorkspaceMember
from apps.workspaces.services import create_workspace

User = get_user_model()


@pytest.fixture
def rbac(db):
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
    return create_workspace(user=owner, name="Campaign WS")


@pytest.fixture
def other_owner(make_user):
    return make_user("owner2@example.com")


@pytest.fixture
def other_workspace(rbac, other_owner):
    return create_workspace(user=other_owner, name="Other WS")


@pytest.fixture
def make_artist():
    def _make_artist(workspace, name="Artist", slug=None):
        return Artist.objects.create(
            workspace=workspace, name=name, slug=slug or name.lower()
        )

    return _make_artist


@pytest.fixture
def make_track():
    def _make_track(workspace, artist, title="Track", slug=None):
        return Track.objects.create(
            workspace=workspace,
            artist=artist,
            title=title,
            slug=slug or title.lower(),
        )

    return _make_track


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
