"""Idempotent seeding of system roles and base permissions.

Used both by the ``seed_rbac`` management command and by tests. Re-running is
safe: permissions and roles are upserted and each role's permission set is
reconciled to match the definitions below.
"""

from django.db import transaction

from .models import Permission, Role, RolePermission

# (key, human name) — domain is derived from the key prefix.
PERMISSIONS = [
    ("workspace:manage", "Manage workspace"),
    ("members:invite", "Invite members"),
    ("members:manage", "Manage members"),
    ("artists:view", "View artists"),
    ("artists:create", "Create artists"),
    ("artists:update", "Update artists"),
    ("artists:delete", "Delete artists"),
    ("tracks:view", "View tracks"),
    ("tracks:create", "Create tracks"),
    ("tracks:update", "Update tracks"),
    ("tracks:delete", "Delete tracks"),
    ("campaigns:view", "View campaigns"),
    ("campaigns:create", "Create campaigns"),
    ("campaigns:update", "Update campaigns"),
    ("campaigns:delete", "Delete campaigns"),
    ("content:view", "View content"),
    ("content:generate", "Generate content"),
    ("content:export", "Export content"),
    ("links:view", "View smart links"),
    ("links:create", "Create smart links"),
    ("links:update", "Update smart links"),
    ("links:delete", "Delete smart links"),
    ("reports:view", "View reports"),
    ("reports:generate", "Generate reports"),
    ("billing:view", "View billing"),
    ("billing:manage", "Manage billing"),
    ("branding:manage", "Manage branding"),
    ("api_keys:manage", "Manage API keys"),
]

ALL_KEYS = [key for key, _ in PERMISSIONS]

# Reusable bundles.
_PRODUCT_VIEW = [
    "artists:view",
    "tracks:view",
    "campaigns:view",
    "content:view",
    "links:view",
    "reports:view",
]
_EDITOR = _PRODUCT_VIEW + [
    "artists:create",
    "artists:update",
    "tracks:create",
    "tracks:update",
    "campaigns:create",
    "campaigns:update",
    "content:generate",
    "content:export",
    "links:create",
    "links:update",
]
_MANAGER = _EDITOR + [
    "members:invite",
    "reports:generate",
    "billing:view",
]
_ADMIN = sorted(
    set(ALL_KEYS) - {"workspace:manage", "billing:manage"}
)

# role key -> (name, description, permission keys)
ROLE_DEFINITIONS = {
    "owner": ("Owner", "Full control of the workspace.", list(ALL_KEYS)),
    "admin": ("Admin", "Manages members and product, excludes billing/workspace control.", _ADMIN),
    "manager": ("Manager", "Manages product and invites members.", sorted(set(_MANAGER))),
    "editor": ("Editor", "Creates and edits product content.", sorted(set(_EDITOR))),
    "viewer": ("Viewer", "Read-only access to product entities.", list(_PRODUCT_VIEW)),
    "billing_admin": (
        "Billing Admin",
        "Manages billing.",
        ["billing:view", "billing:manage", "reports:view"],
    ),
    "api_user": (
        "API User",
        "Programmatic access role.",
        [
            "content:view",
            "content:generate",
            "links:view",
            "reports:view",
            "api_keys:manage",
        ],
    ),
}


@transaction.atomic
def seed_rbac() -> dict:
    """Create/update system roles and permissions. Returns a summary dict."""
    permissions = {}
    for key, name in PERMISSIONS:
        domain = key.split(":", 1)[0]
        permission, _ = Permission.objects.update_or_create(
            key=key, defaults={"name": name, "domain": domain}
        )
        permissions[key] = permission

    roles_created = 0
    for role_key, (name, description, perm_keys) in ROLE_DEFINITIONS.items():
        role, created = Role.objects.update_or_create(
            workspace=None,
            key=role_key,
            defaults={"name": name, "description": description, "is_system": True},
        )
        roles_created += int(created)

        wanted = {permissions[k] for k in perm_keys}
        for permission in wanted:
            RolePermission.objects.get_or_create(role=role, permission=permission)
        # Reconcile: drop permissions no longer granted to this role.
        RolePermission.objects.filter(role=role).exclude(
            permission__in=wanted
        ).delete()

    return {
        "permissions": len(permissions),
        "roles": len(ROLE_DEFINITIONS),
        "roles_created": roles_created,
    }
