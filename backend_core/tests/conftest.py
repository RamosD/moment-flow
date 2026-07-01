"""Shared fixtures for the cross-cutting regression suite.

These complement (do not replace) the per-app test suites under ``apps/*/tests``.
They lean on the factories in ``tests.factories`` and the real seed commands so
RBAC roles and billing plans exist.
"""

import pytest
from django.utils.timezone import now
from rest_framework.test import APIClient

from apps.billing.seeds import seed_billing
from apps.rbac.models import Role
from apps.rbac.seeds import seed_rbac
from apps.workspaces.models import WorkspaceMember

WORKSPACE_ID_HEADER = "HTTP_X_WORKSPACE_ID"


def ws_header(workspace):
    """Return request kwargs carrying the active-workspace header."""
    return {WORKSPACE_ID_HEADER: str(workspace.id)}


@pytest.fixture
def seeded(db):
    """Seed system roles/permissions and the billing plan catalogue."""
    seed_rbac()
    seed_billing()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client():
    """Return a callable that yields an APIClient authenticated as ``user``."""

    def _auth_client(user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    return _auth_client


@pytest.fixture
def add_member(seeded):
    """Add ``user`` to ``workspace`` with a seeded system role by key."""

    def _add_member(workspace, user, role_key="viewer", status=WorkspaceMember.Status.ACTIVE):
        role = Role.objects.filter(workspace__isnull=True, key=role_key).first()
        member, _ = WorkspaceMember.objects.get_or_create(
            workspace=workspace,
            user=user,
            defaults={
                "role": role,
                "role_key": role_key,
                "status": status,
                "joined_at": now(),
            },
        )
        return member

    return _add_member
