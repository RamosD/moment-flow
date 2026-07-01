"""Fixtures for core (Asset) tests."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.workspaces.services import create_workspace

User = get_user_model()


@pytest.fixture
def make_user(db):
    def _make_user(email, password="pass-12345", **extra):
        return User.objects.create_user(email=email, password=password, **extra)

    return _make_user


@pytest.fixture
def user_a(make_user):
    return make_user("alice@example.com")


@pytest.fixture
def user_b(make_user):
    return make_user("bob@example.com")


@pytest.fixture
def workspace_a(user_a):
    return create_workspace(user=user_a, name="Alice WS")


@pytest.fixture
def workspace_b(user_b):
    return create_workspace(user=user_b, name="Bob WS")


@pytest.fixture
def client_a(user_a):
    client = APIClient()
    client.force_authenticate(user=user_a)
    return client


@pytest.fixture
def client_b(user_b):
    client = APIClient()
    client.force_authenticate(user=user_b)
    return client
