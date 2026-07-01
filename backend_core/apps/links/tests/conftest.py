"""Fixtures for smart links tests."""

import pytest
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from rest_framework.test import APIClient

from apps.campaigns.models import Campaign
from apps.catalogue.models import Artist
from apps.links.models import SmartLink, SmartLinkDestination
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
    return create_workspace(user=owner, name="Links WS")


@pytest.fixture
def other_owner(make_user):
    return make_user("owner2@example.com")


@pytest.fixture
def other_workspace(rbac, other_owner):
    return create_workspace(user=other_owner, name="Other WS")


@pytest.fixture
def make_campaign():
    def _make_campaign(workspace, name="Campaign", slug="campaign"):
        artist = Artist.objects.create(
            workspace=workspace, name=f"{name} Artist", slug=f"{slug}-artist"
        )
        return Campaign.objects.create(
            workspace=workspace, artist=artist, name=name, slug=slug
        )

    return _make_campaign


@pytest.fixture
def make_smart_link():
    def _make_smart_link(workspace, campaign, slug, status=SmartLink.Status.ACTIVE):
        return SmartLink.objects.create(
            workspace=workspace, campaign=campaign, slug=slug, title=slug, status=status
        )

    return _make_smart_link


@pytest.fixture
def make_destination():
    def _make_destination(workspace, smart_link, platform, url, sort_order=0, is_active=True):
        return SmartLinkDestination.objects.create(
            workspace=workspace,
            smart_link=smart_link,
            platform=platform,
            url=url,
            sort_order=sort_order,
            is_active=is_active,
        )

    return _make_destination


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
