"""Service helpers for creating notifications.

Notifications are normally created by the system (e.g. when a report finishes),
not by end users via the API. ``create_notification`` is the sanctioned entry
point used by other apps and by tests.
"""

from .models import Notification


def create_notification(
    *,
    workspace,
    title,
    notification_type=Notification.NotificationType.SYSTEM,
    message="",
    user=None,
    related_entity_type="",
    related_entity_id="",
    metadata=None,
) -> Notification:
    """Create an in-app notification for a user (or a workspace-wide broadcast)."""
    return Notification.objects.create(
        workspace=workspace,
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        related_entity_type=related_entity_type,
        related_entity_id=str(related_entity_id) if related_entity_id else "",
        status=Notification.Status.UNREAD,
        metadata=metadata or {},
    )
