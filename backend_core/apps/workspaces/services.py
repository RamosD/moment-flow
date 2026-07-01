"""Service functions for the workspaces domain."""

from django.db import transaction
from django.utils.text import slugify
from django.utils.timezone import now

from .models import ROLE_OWNER, Workspace, WorkspaceMember


def generate_unique_slug(name: str) -> str:
    """Return a unique slug derived from ``name``.

    Uniqueness is checked against *all* rows (including soft-deleted) because the
    slug column carries a database-level unique constraint.
    """
    base = slugify(name) or "workspace"
    slug = base
    counter = 2
    while Workspace.all_objects.filter(slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def _system_role(key):
    """Return the system Role with ``key`` (or ``None`` if RBAC isn't seeded)."""
    from apps.rbac.models import Role

    return Role.objects.filter(workspace__isnull=True, key=key).first()


@transaction.atomic
def create_workspace(*, user, name, **fields) -> Workspace:
    """Create a workspace and make ``user`` its active owner member.

    The owner ``Role`` FK is set when RBAC has been seeded; ``role_key`` is always
    set so the membership remains resolvable even before seeding.
    """
    workspace = Workspace.objects.create(
        name=name,
        slug=generate_unique_slug(name),
        created_by=user,
        **fields,
    )
    WorkspaceMember.objects.create(
        workspace=workspace,
        user=user,
        role=_system_role(ROLE_OWNER),
        role_key=ROLE_OWNER,
        status=WorkspaceMember.Status.ACTIVE,
        invited_by=user,
        joined_at=now(),
    )

    from apps.audit.services import record_audit_event

    record_audit_event(
        action="workspace.created",
        workspace=workspace,
        actor_user=user,
        entity_type="workspace",
        entity_id=workspace.id,
        after_data={"name": workspace.name, "slug": workspace.slug},
    )
    return workspace
