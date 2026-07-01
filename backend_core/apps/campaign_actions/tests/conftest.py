"""Fixtures for CampaignAction tests."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.campaigns.models import Campaign
from apps.catalogue.models import Artist
from apps.rbac.seeds import seed_rbac
from apps.workspaces.services import create_workspace

User = get_user_model()


@pytest.fixture
def seeded(db):
    return seed_rbac()


@pytest.fixture
def owner(seeded):
    return User.objects.create_user(
        email="campaign-actions-owner@example.com",
        password="pass-12345",
    )


@pytest.fixture
def workspace(owner):
    return create_workspace(user=owner, name="Campaign Actions WS")


@pytest.fixture
def campaign(workspace):
    artist = Artist.objects.create(
        workspace=workspace,
        name="Campaign Actions Artist",
        slug="campaign-actions-artist",
    )
    return Campaign.objects.create(
        workspace=workspace,
        artist=artist,
        name="Campaign Actions Campaign",
        slug="campaign-actions-campaign",
    )


@pytest.fixture
def client_for_owner(owner):
    client = APIClient()
    client.force_authenticate(owner)
    return client


@pytest.fixture
def workspace_header(workspace):
    return {"HTTP_X_WORKSPACE_ID": str(workspace.id)}

