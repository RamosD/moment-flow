"""State-transition rules for persistent campaign actions."""

from django.db import transaction
from django.utils.timezone import now

from .models import CampaignAction

ALLOWED_STATUS_TRANSITIONS = {
    CampaignAction.Status.PENDING: frozenset(
        {
            CampaignAction.Status.IN_PROGRESS,
            CampaignAction.Status.COMPLETED,
            CampaignAction.Status.FAILED,
            CampaignAction.Status.DISMISSED,
            CampaignAction.Status.CANCELLED,
        }
    ),
    CampaignAction.Status.IN_PROGRESS: frozenset(
        {
            CampaignAction.Status.COMPLETED,
            CampaignAction.Status.FAILED,
            CampaignAction.Status.CANCELLED,
        }
    ),
    CampaignAction.Status.COMPLETED: frozenset(),
    CampaignAction.Status.FAILED: frozenset(),
    CampaignAction.Status.DISMISSED: frozenset(),
    CampaignAction.Status.CANCELLED: frozenset(),
}


class CampaignActionTransitionError(ValueError):
    """A requested state transition violates the CampaignAction lifecycle."""

    def __init__(self, message, *, field="status"):
        super().__init__(message)
        self.field = field


def validate_status_transition(current_status, target_status, *, dismiss_reason=""):
    """Validate a transition without mutating an action.

    Repeating the current status is idempotent. Failed/completed/dismissed/
    cancelled are terminal; a retry after failure is represented by a new
    CampaignAction, matching the active-duplicate rule.
    """

    valid_statuses = set(CampaignAction.Status.values)
    if target_status not in valid_statuses:
        raise CampaignActionTransitionError("Invalid CampaignAction status.")

    if target_status == CampaignAction.Status.DISMISSED and not dismiss_reason.strip():
        raise CampaignActionTransitionError(
            "A dismiss reason is required for dismissed actions.",
            field="dismiss_reason",
        )

    if target_status == current_status:
        return

    allowed = ALLOWED_STATUS_TRANSITIONS.get(current_status, frozenset())
    if target_status not in allowed:
        raise CampaignActionTransitionError(
            f"Transition from {current_status} to {target_status} is not allowed."
        )


@transaction.atomic
def transition_campaign_action(
    action,
    target_status,
    *,
    actor=None,
    dismiss_reason="",
):
    """Lock and transition an action, maintaining terminal timestamps."""

    locked = CampaignAction.objects.select_for_update().get(pk=action.pk)
    normalized_reason = dismiss_reason.strip()
    validate_status_transition(
        locked.status,
        target_status,
        dismiss_reason=normalized_reason or locked.dismiss_reason,
    )

    fields = {"status", "updated_at"}
    locked.status = target_status

    if target_status == CampaignAction.Status.COMPLETED:
        if locked.completed_at is None:
            locked.completed_at = now()
            fields.add("completed_at")
        if locked.cancelled_at is not None:
            locked.cancelled_at = None
            fields.add("cancelled_at")
        if locked.dismiss_reason:
            locked.dismiss_reason = ""
            fields.add("dismiss_reason")
    elif target_status == CampaignAction.Status.CANCELLED:
        if locked.cancelled_at is None:
            locked.cancelled_at = now()
            fields.add("cancelled_at")
        if locked.completed_at is not None:
            locked.completed_at = None
            fields.add("completed_at")
        if locked.dismiss_reason:
            locked.dismiss_reason = ""
            fields.add("dismiss_reason")
    elif target_status == CampaignAction.Status.DISMISSED:
        reason = normalized_reason or locked.dismiss_reason.strip()
        if locked.dismiss_reason != reason:
            locked.dismiss_reason = reason
            fields.add("dismiss_reason")
        if locked.completed_at is not None:
            locked.completed_at = None
            fields.add("completed_at")
        if locked.cancelled_at is not None:
            locked.cancelled_at = None
            fields.add("cancelled_at")
    else:
        if locked.completed_at is not None:
            locked.completed_at = None
            fields.add("completed_at")
        if locked.cancelled_at is not None:
            locked.cancelled_at = None
            fields.add("cancelled_at")
        if locked.dismiss_reason:
            locked.dismiss_reason = ""
            fields.add("dismiss_reason")

    if actor is not None and locked.updated_by_id != actor.id:
        locked.updated_by = actor
        fields.add("updated_by")

    locked.save(update_fields=sorted(fields))
    return locked
