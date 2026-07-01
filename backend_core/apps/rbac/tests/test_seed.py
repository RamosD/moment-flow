"""Tests for the idempotent RBAC seed."""

import pytest

from apps.rbac.models import Permission, Role, RolePermission
from apps.rbac.seeds import ALL_KEYS, ROLE_DEFINITIONS, seed_rbac


@pytest.mark.django_db
class TestSeed:
    def test_seed_creates_roles_and_permissions(self, rbac):
        assert Permission.objects.count() == len(ALL_KEYS)
        assert Role.objects.filter(is_system=True, workspace__isnull=True).count() == len(
            ROLE_DEFINITIONS
        )
        owner = Role.objects.get(workspace__isnull=True, key="owner")
        assert owner.permissions.count() == len(ALL_KEYS)

    def test_seed_is_idempotent(self, rbac):
        perms_before = Permission.objects.count()
        roles_before = Role.objects.count()
        links_before = RolePermission.objects.count()

        seed_rbac()  # run again

        assert Permission.objects.count() == perms_before
        assert Role.objects.count() == roles_before
        assert RolePermission.objects.count() == links_before
