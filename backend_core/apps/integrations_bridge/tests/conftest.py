"""Fixtures for integrations-bridge tests."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.rbac.seeds import seed_rbac
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
    return make_user("bridge-owner@example.com")


@pytest.fixture
def workspace(seeded, owner):
    return create_workspace(user=owner, name="Bridge WS")


@pytest.fixture
def api_client():
    return APIClient()
