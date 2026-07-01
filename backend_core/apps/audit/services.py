"""Audit service: the single sanctioned way to write an ``AuditEvent``.

``record_audit_event`` is intentionally permissive about its inputs so callers in
any layer (services or views) can use it. When a ``request`` is supplied, the
actor IP/user-agent are hashed automatically; otherwise those fields stay empty.
"""

from .models import AuditEvent
from .utils import ip_address_hash, user_agent_hash


def record_audit_event(
    *,
    action,
    workspace=None,
    actor_user=None,
    actor_type=None,
    entity_type="",
    entity_id="",
    before_data=None,
    after_data=None,
    request=None,
    ip_hash="",
    ua_hash="",
    metadata=None,
) -> AuditEvent:
    """Create an immutable audit record.

    ``actor_type`` defaults to ``user`` when an ``actor_user`` is given, otherwise
    ``system``. When ``request`` is provided, IP/user-agent hashes are derived
    from it (raw values are never stored).
    """
    if request is not None:
        ip_hash = ip_hash or ip_address_hash(request)
        ua_hash = ua_hash or user_agent_hash(request)

    if actor_type is None:
        actor_type = (
            AuditEvent.ActorType.USER
            if actor_user is not None
            else AuditEvent.ActorType.SYSTEM
        )

    return AuditEvent.objects.create(
        action=action,
        workspace=workspace,
        actor_user=actor_user,
        actor_type=actor_type,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else "",
        before_data=before_data or {},
        after_data=after_data or {},
        ip_address_hash=ip_hash,
        user_agent_hash=ua_hash,
        metadata=metadata or {},
    )
