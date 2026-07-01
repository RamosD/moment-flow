"""Billing services: subscriptions, features/limits, usage and the credit ledger.

These functions are the *only* sanctioned way to mutate usage and credits. They
are idempotent where it matters so retries never double-count or double-charge:

  - ``record_usage_event`` is idempotent on ``(workspace, idempotency_key)``.
  - every credit operation is idempotent on ``(workspace, idempotency_key)`` and
    writes an append-only ledger entry whose ``balance_after`` denormalizes the
    available balance (also reconstructible by summing ``amount``).

Credit model (single *available* balance):
  - grant / purchase / refund / release  → positive delta (credits available go up)
  - reserve / consume / expiration        → negative delta (credits available go down)
  - adjustment                            → caller-signed delta

Reserve → settle flow: ``reserve_credits`` holds credits by removing them from
the available balance. On success call ``consume_credits(..., settle_reserved=True)``
which records a finalization with a zero delta (the credits already left at
reserve time). On failure call ``release_reserved_credits`` to return them.
"""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Count, Sum
from django.utils.timezone import now

from .exceptions import InsufficientCredits, QuotaExceeded
from .models import (
    CreditLedgerEntry,
    PlanFeature,
    Subscription,
    UsageEvent,
)

ZERO = Decimal("0")


def current_billing_period() -> str:
    """Return the coarse billing-period bucket for *now* (``YYYY-MM``)."""
    return now().strftime("%Y-%m")


def _as_decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


# --------------------------------------------------------------------------- #
# Subscriptions / plan features
# --------------------------------------------------------------------------- #
def get_active_subscription(workspace):
    """Return the workspace's active (or trialing) subscription, or ``None``.

    "Active" means any of ``Subscription.ACTIVE_STATUSES``. The most recently
    created qualifying subscription wins.
    """
    return (
        Subscription.objects.filter(
            workspace=workspace, status__in=Subscription.ACTIVE_STATUSES
        )
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )


def _active_plan_feature(workspace, feature_key):
    """Return the ``PlanFeature`` for ``feature_key`` on the active plan, or None."""
    subscription = get_active_subscription(workspace)
    if subscription is None:
        return None
    return PlanFeature.objects.filter(
        plan=subscription.plan, feature_key=feature_key
    ).first()


def workspace_has_feature(workspace, feature_key) -> bool:
    """True when the workspace's active plan enables ``feature_key``."""
    feature = _active_plan_feature(workspace, feature_key)
    return bool(feature and feature.is_enabled)


def get_plan_limit(workspace, feature_key):
    """Return the numeric limit for ``feature_key`` on the active plan.

    Returns:
      - the ``limit_value`` when the feature exists and is enabled;
      - ``0`` when the feature exists but is disabled (effectively blocks);
      - ``None`` when there is no active subscription, the feature is not defined,
        or the limit is unlimited (``limit_value`` is null).

    A ``None`` result means "do not enforce a numeric limit" — callers fail open.
    """
    feature = _active_plan_feature(workspace, feature_key)
    if feature is None:
        return None
    if not feature.is_enabled:
        return 0
    return feature.limit_value


def change_subscription_plan(workspace, new_plan, *, actor_user=None):
    """Move the workspace's active subscription to ``new_plan`` and audit it.

    Returns the updated subscription, or ``None`` when there is no active
    subscription. A no-op (same plan) is not audited. This is the sanctioned entry
    point for plan changes (there is no public plan-change endpoint yet).
    """
    subscription = get_active_subscription(workspace)
    if subscription is None or subscription.plan_id == new_plan.id:
        return subscription

    old_plan = subscription.plan
    subscription.plan = new_plan
    subscription.save(update_fields=["plan", "updated_at"])

    try:
        from apps.audit.services import record_audit_event

        record_audit_event(
            action="billing.plan_changed",
            workspace=workspace,
            actor_user=actor_user,
            actor_type=None if actor_user else "system",
            entity_type="subscription",
            entity_id=subscription.id,
            before_data={"plan": old_plan.plan_key},
            after_data={"plan": new_plan.plan_key},
        )
    except ImportError:
        pass
    return subscription


# --------------------------------------------------------------------------- #
# Usage events
# --------------------------------------------------------------------------- #
@transaction.atomic
def record_usage_event(
    *,
    workspace,
    event_type,
    quantity=1,
    unit="",
    related_entity_type="",
    related_entity_id="",
    cost_units=0,
    billing_period=None,
    idempotency_key="",
    metadata=None,
):
    """Record a usage event idempotently.

    Returns ``(event, created)``. When ``idempotency_key`` is supplied and an
    event already exists for ``(workspace, idempotency_key)``, the existing event
    is returned with ``created=False`` (no duplicate, no double count).
    """
    if idempotency_key:
        existing = UsageEvent.objects.filter(
            workspace=workspace, idempotency_key=idempotency_key
        ).first()
        if existing is not None:
            return existing, False

    fields = {
        "workspace": workspace,
        "event_type": event_type,
        "quantity": _as_decimal(quantity),
        "unit": unit,
        "related_entity_type": related_entity_type,
        "related_entity_id": str(related_entity_id) if related_entity_id else "",
        "cost_units": _as_decimal(cost_units),
        "billing_period": billing_period or current_billing_period(),
        "idempotency_key": idempotency_key,
        "metadata": metadata or {},
    }
    try:
        with transaction.atomic():
            event = UsageEvent.objects.create(**fields)
        return event, True
    except IntegrityError:
        # Concurrent insert with the same idempotency key — return the winner.
        existing = UsageEvent.objects.filter(
            workspace=workspace, idempotency_key=idempotency_key
        ).first()
        if existing is not None:
            return existing, False
        raise


def record_creation_usage(workspace, event_type, entity_type, entity_id, *, metadata=None):
    """Record a one-per-entity creation usage event idempotently.

    The idempotency key is derived from the entity id, so a retry for the same
    entity never double-counts. Convenience wrapper around ``record_usage_event``
    for the common "X created" meters.
    """
    return record_usage_event(
        workspace=workspace,
        event_type=event_type,
        related_entity_type=entity_type,
        related_entity_id=str(entity_id),
        idempotency_key=f"{event_type}:{entity_id}",
        metadata=metadata,
    )


def get_period_usage(workspace, billing_period=None):
    """Aggregate usage for a workspace within a billing period.

    Returns a list of ``{event_type, total_quantity, total_cost, events}`` dicts.
    """
    period = billing_period or current_billing_period()
    rows = (
        UsageEvent.objects.filter(workspace=workspace, billing_period=period)
        .values("event_type")
        .annotate(
            total_quantity=Sum("quantity"),
            total_cost=Sum("cost_units"),
            events=Count("id"),
        )
        .order_by("event_type")
    )
    return list(rows)


# --------------------------------------------------------------------------- #
# Credit ledger
# --------------------------------------------------------------------------- #
def get_credit_balance(workspace) -> Decimal:
    """Return the current available credit balance (sum of all ledger amounts)."""
    total = CreditLedgerEntry.objects.filter(workspace=workspace).aggregate(
        total=Sum("amount")
    )["total"]
    return total if total is not None else ZERO


@transaction.atomic
def _record_ledger_entry(
    *,
    workspace,
    transaction_type,
    delta,
    reason="",
    related_entity_type="",
    related_entity_id="",
    idempotency_key="",
    metadata=None,
):
    """Append a ledger entry idempotently and return ``(entry, created)``.

    ``delta`` is the signed change to the available balance. Idempotency is keyed
    on ``(workspace, idempotency_key)``: a replay returns the existing entry
    untouched so credits are never moved twice.
    """
    delta = _as_decimal(delta)

    if idempotency_key:
        existing = CreditLedgerEntry.objects.filter(
            workspace=workspace, idempotency_key=idempotency_key
        ).first()
        if existing is not None:
            return existing, False

    new_balance = get_credit_balance(workspace) + delta
    fields = {
        "workspace": workspace,
        "transaction_type": transaction_type,
        "amount": delta,
        "balance_after": new_balance,
        "reason": reason,
        "related_entity_type": related_entity_type,
        "related_entity_id": str(related_entity_id) if related_entity_id else "",
        "idempotency_key": idempotency_key,
        "metadata": metadata or {},
    }
    try:
        with transaction.atomic():
            entry = CreditLedgerEntry.objects.create(**fields)
        return entry, True
    except IntegrityError:
        existing = CreditLedgerEntry.objects.filter(
            workspace=workspace, idempotency_key=idempotency_key
        ).first()
        if existing is not None:
            return existing, False
        raise


def _record_credit_audit(action, workspace, entry, actor_user=None):
    """Audit a credit movement (best effort; never breaks the ledger write)."""
    try:
        from apps.audit.services import record_audit_event
    except ImportError:
        return
    record_audit_event(
        action=action,
        workspace=workspace,
        actor_user=actor_user,
        actor_type=None if actor_user else "system",
        entity_type="credit_ledger_entry",
        entity_id=entry.id,
        after_data={
            "amount": str(entry.amount),
            "balance_after": str(entry.balance_after),
        },
    )


def grant_credits(workspace, amount, *, reason="", idempotency_key="", metadata=None,
                  related_entity_type="", related_entity_id="", actor_user=None):
    """Grant (add) ``amount`` credits to the workspace."""
    amount = _as_decimal(amount)
    if amount <= ZERO:
        raise ValueError("grant amount must be positive")
    entry, created = _record_ledger_entry(
        workspace=workspace,
        transaction_type=CreditLedgerEntry.TransactionType.GRANT,
        delta=amount,
        reason=reason,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        idempotency_key=idempotency_key,
        metadata=metadata,
    )
    if created:
        _record_credit_audit("credits.granted", workspace, entry, actor_user)
    return entry, created


def purchase_credits(workspace, amount, *, reason="", idempotency_key="", metadata=None):
    """Record a credit purchase (positive delta)."""
    amount = _as_decimal(amount)
    if amount <= ZERO:
        raise ValueError("purchase amount must be positive")
    return _record_ledger_entry(
        workspace=workspace,
        transaction_type=CreditLedgerEntry.TransactionType.PURCHASE,
        delta=amount,
        reason=reason,
        idempotency_key=idempotency_key,
        metadata=metadata,
    )


def reserve_credits(workspace, amount, *, reason="", idempotency_key="", metadata=None,
                    related_entity_type="", related_entity_id=""):
    """Reserve (hold) ``amount`` credits, removing them from the available balance.

    Raises ``InsufficientCredits`` when the available balance is too low.
    """
    amount = _as_decimal(amount)
    if amount <= ZERO:
        raise ValueError("reserve amount must be positive")

    if idempotency_key:
        existing = CreditLedgerEntry.objects.filter(
            workspace=workspace, idempotency_key=idempotency_key
        ).first()
        if existing is not None:
            return existing, False

    if get_credit_balance(workspace) < amount:
        raise InsufficientCredits(
            f"Not enough credits to reserve {amount}. "
            f"Available balance: {get_credit_balance(workspace)}."
        )
    return _record_ledger_entry(
        workspace=workspace,
        transaction_type=CreditLedgerEntry.TransactionType.RESERVE,
        delta=-amount,
        reason=reason,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        idempotency_key=idempotency_key,
        metadata=metadata,
    )


def consume_credits(workspace, amount, *, settle_reserved=False, reason="",
                    idempotency_key="", metadata=None, related_entity_type="",
                    related_entity_id=""):
    """Consume ``amount`` credits.

    With ``settle_reserved=True`` this finalizes a prior reservation: the credits
    already left the available balance at reserve time, so the delta is zero.
    Otherwise it deducts ``amount`` directly from the available balance (raising
    ``InsufficientCredits`` if too low).
    """
    amount = _as_decimal(amount)
    if amount <= ZERO:
        raise ValueError("consume amount must be positive")

    if settle_reserved:
        delta = ZERO
    else:
        if idempotency_key:
            existing = CreditLedgerEntry.objects.filter(
                workspace=workspace, idempotency_key=idempotency_key
            ).first()
            if existing is not None:
                return existing, False
        if get_credit_balance(workspace) < amount:
            raise InsufficientCredits(
                f"Not enough credits to consume {amount}. "
                f"Available balance: {get_credit_balance(workspace)}."
            )
        delta = -amount

    meta = dict(metadata or {})
    meta.setdefault("consumed_amount", str(amount))
    entry, created = _record_ledger_entry(
        workspace=workspace,
        transaction_type=CreditLedgerEntry.TransactionType.CONSUME,
        delta=delta,
        reason=reason,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        idempotency_key=idempotency_key,
        metadata=meta,
    )
    if created:
        _record_credit_audit("credits.consumed", workspace, entry)
    return entry, created


def release_reserved_credits(workspace, amount, *, reason="", idempotency_key="",
                             metadata=None, related_entity_type="",
                             related_entity_id=""):
    """Release a previously reserved ``amount`` back to the available balance."""
    amount = _as_decimal(amount)
    if amount <= ZERO:
        raise ValueError("release amount must be positive")
    return _record_ledger_entry(
        workspace=workspace,
        transaction_type=CreditLedgerEntry.TransactionType.RELEASE,
        delta=amount,
        reason=reason,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        idempotency_key=idempotency_key,
        metadata=metadata,
    )


def refund_credits(workspace, amount, *, reason="", idempotency_key="", metadata=None,
                   related_entity_type="", related_entity_id=""):
    """Refund ``amount`` credits back to the available balance (e.g. after a failure)."""
    amount = _as_decimal(amount)
    if amount <= ZERO:
        raise ValueError("refund amount must be positive")
    return _record_ledger_entry(
        workspace=workspace,
        transaction_type=CreditLedgerEntry.TransactionType.REFUND,
        delta=amount,
        reason=reason,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        idempotency_key=idempotency_key,
        metadata=metadata,
    )


# --------------------------------------------------------------------------- #
# Quota enforcement
# --------------------------------------------------------------------------- #
def _count_artists(workspace):
    from apps.catalogue.models import Artist

    return (
        Artist.objects.filter(workspace=workspace)
        .exclude(status=Artist.Status.ARCHIVED)
        .count()
    )


def _count_tracks(workspace):
    from apps.catalogue.models import Track

    return (
        Track.objects.filter(workspace=workspace)
        .exclude(status=Track.Status.ARCHIVED)
        .count()
    )


def _count_campaigns(workspace):
    from apps.campaigns.models import Campaign

    return (
        Campaign.objects.filter(workspace=workspace)
        .exclude(status=Campaign.Status.ARCHIVED)
        .count()
    )


def _count_smart_links(workspace):
    from apps.links.models import SmartLink

    return (
        SmartLink.objects.filter(workspace=workspace)
        .exclude(status=SmartLink.Status.ARCHIVED)
        .count()
    )


def _count_usage_this_period(workspace, event_type):
    return UsageEvent.objects.filter(
        workspace=workspace,
        event_type=event_type,
        billing_period=current_billing_period(),
    ).count()


def _count_content_packs_this_period(workspace):
    return _count_usage_this_period(
        workspace, UsageEvent.EventType.CONTENT_PACK_REQUESTED
    )


def _count_reports_this_period(workspace):
    return _count_usage_this_period(workspace, UsageEvent.EventType.REPORT_GENERATED)


# feature_key -> callable(workspace) -> current usage count (or None to skip).
USAGE_COUNTERS = {
    "artists_limit": _count_artists,
    "tracks_limit": _count_tracks,
    "campaigns_limit": _count_campaigns,
    "smart_links_limit": _count_smart_links,
    "content_packs_per_month": _count_content_packs_this_period,
    "reports_per_month": _count_reports_this_period,
}


def count_current_usage(workspace, feature_key):
    """Return the workspace's current usage for ``feature_key`` (or ``None``)."""
    counter = USAGE_COUNTERS.get(feature_key)
    if counter is None:
        return None
    return counter(workspace)


def check_workspace_limit(workspace, feature_key, *, increment=1, current_count=None):
    """Raise ``QuotaExceeded`` when one more unit would exceed the plan limit.

    Fails open (no exception) when there is no active subscription, no limit is
    defined for the feature, or the limit is unlimited — never blocking a flow
    silently or without a configured plan. When it does block, the message names
    the feature, the plan and the current/limit counts.
    """
    limit = get_plan_limit(workspace, feature_key)
    if limit is None:
        return  # unlimited or no enforceable limit

    if current_count is None:
        current_count = count_current_usage(workspace, feature_key)
    if current_count is None:
        return  # cannot determine usage for this feature — skip

    if current_count + increment > limit:
        subscription = get_active_subscription(workspace)
        plan_key = subscription.plan.plan_key if subscription else "unknown"
        raise QuotaExceeded(
            f"Plan limit reached for '{feature_key}' on plan '{plan_key}': "
            f"{current_count}/{limit} used. Upgrade your plan to continue."
        )
