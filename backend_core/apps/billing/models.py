"""Billing models: plans, features, subscriptions, usage, credits and webhooks.

Billing is a core Django responsibility. The goal at this stage is to measure
usage early and control per-workspace limits with a *safe and idempotent*
structure — not to ship a full Stripe checkout. Money never moves twice: usage
events and credit ledger entries are idempotent on ``idempotency_key`` and the
Stripe webhook log is idempotent on ``provider_event_id``.

Design notes:
  - ``Plan`` / ``PlanFeature`` are a global catalogue (not workspace-owned).
  - ``Subscription`` links a workspace to a plan; one *active-ish* subscription
    per workspace is expected (enforced softly in services, not at DB level so
    history can be retained).
  - ``UsageEvent`` is an append-only meter. ``CreditLedgerEntry`` is an
    append-only ledger; balance is reconstructible by summing ``amount`` and is
    also denormalized into ``balance_after`` for cheap reads.
"""

from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel, WorkspaceOwnedModel


class Plan(BaseModel):
    """A commercial plan (global catalogue, not workspace-owned)."""

    class BillingInterval(models.TextChoices):
        MONTH = "month", _("Monthly")
        YEAR = "year", _("Yearly")
        ONE_TIME = "one_time", _("One-time")
        CUSTOM = "custom", _("Custom")

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        HIDDEN = "hidden", _("Hidden")
        DEPRECATED = "deprecated", _("Deprecated")
        ARCHIVED = "archived", _("Archived")

    plan_key = models.SlugField(_("plan key"), max_length=80, unique=True)
    name = models.CharField(_("name"), max_length=150)
    description = models.TextField(_("description"), blank=True)
    billing_interval = models.CharField(
        _("billing interval"),
        max_length=20,
        choices=BillingInterval.choices,
        default=BillingInterval.MONTH,
    )
    base_price = models.DecimalField(
        _("base price"), max_digits=12, decimal_places=2, default=0
    )
    currency = models.CharField(_("currency"), max_length=3, default="USD")
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    is_public = models.BooleanField(_("public"), default=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("plan")
        verbose_name_plural = _("plans")
        ordering = ["base_price", "name"]
        indexes = [models.Index(fields=["status", "is_public"])]

    def __str__(self):
        return self.plan_key


class PlanFeature(BaseModel):
    """A feature / limit attached to a plan (e.g. ``artists_limit = 5``).

    ``limit_value`` is nullable; a null limit on an enabled feature means
    *unlimited*. Boolean-style features (e.g. ``watermark_removal``) use
    ``is_enabled`` and leave ``limit_value`` null.
    """

    class LimitUnit(models.TextChoices):
        COUNT = "count", _("Count")
        PER_MONTH = "per_month", _("Per month")
        GIGABYTE = "gb", _("Gigabyte")
        BOOLEAN = "boolean", _("Boolean")
        CREDITS = "credits", _("Credits")

    plan = models.ForeignKey(
        Plan,
        verbose_name=_("plan"),
        on_delete=models.CASCADE,
        related_name="features",
    )
    feature_key = models.SlugField(_("feature key"), max_length=80)
    limit_value = models.BigIntegerField(_("limit value"), null=True, blank=True)
    limit_unit = models.CharField(
        _("limit unit"),
        max_length=20,
        choices=LimitUnit.choices,
        default=LimitUnit.COUNT,
    )
    is_enabled = models.BooleanField(_("enabled"), default=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("plan feature")
        verbose_name_plural = _("plan features")
        ordering = ["plan", "feature_key"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "feature_key"], name="unique_plan_feature"
            )
        ]

    def __str__(self):
        return f"{self.plan.plan_key}:{self.feature_key}"


class Subscription(BaseModel, WorkspaceOwnedModel):
    """A workspace's subscription to a plan."""

    class Provider(models.TextChoices):
        MANUAL = "manual", _("Manual")
        STRIPE = "stripe", _("Stripe")
        TRIAL = "trial", _("Trial")

    class Status(models.TextChoices):
        TRIALING = "trialing", _("Trialing")
        ACTIVE = "active", _("Active")
        PAST_DUE = "past_due", _("Past due")
        CANCELLED = "cancelled", _("Cancelled")
        UNPAID = "unpaid", _("Unpaid")
        PAUSED = "paused", _("Paused")
        ENTERPRISE_MANUAL = "enterprise_manual", _("Enterprise (manual)")

    # Statuses that grant the workspace access to the plan's features/limits.
    ACTIVE_STATUSES = (
        Status.TRIALING,
        Status.ACTIVE,
        Status.PAST_DUE,
        Status.ENTERPRISE_MANUAL,
    )

    plan = models.ForeignKey(
        Plan,
        verbose_name=_("plan"),
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    provider = models.CharField(
        _("provider"),
        max_length=20,
        choices=Provider.choices,
        default=Provider.MANUAL,
    )
    provider_subscription_id = models.CharField(
        _("provider subscription id"), max_length=255, blank=True
    )
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.TRIALING
    )
    current_period_start = models.DateTimeField(
        _("current period start"), null=True, blank=True
    )
    current_period_end = models.DateTimeField(
        _("current period end"), null=True, blank=True
    )
    trial_start = models.DateTimeField(_("trial start"), null=True, blank=True)
    trial_end = models.DateTimeField(_("trial end"), null=True, blank=True)
    cancel_at_period_end = models.BooleanField(
        _("cancel at period end"), default=False
    )
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("subscription")
        verbose_name_plural = _("subscriptions")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_subscription_id"],
                condition=~models.Q(provider_subscription_id=""),
                name="unique_provider_subscription_id",
            )
        ]
        indexes = [
            models.Index(fields=["workspace", "status"]),
        ]

    def __str__(self):
        return f"{self.workspace_id} → {self.plan_id} ({self.status})"

    @property
    def is_active(self) -> bool:
        return self.status in self.ACTIVE_STATUSES


class UsageEvent(BaseModel, WorkspaceOwnedModel):
    """An append-only meter of platform usage, idempotent per workspace.

    ``idempotency_key`` (when provided) is unique per workspace, so retries of the
    same logical action do not double-count. ``billing_period`` is a coarse bucket
    such as ``2026-06`` to allow cheap per-period aggregation.
    """

    class EventType(models.TextChoices):
        ARTIST_CREATED = "artist_created", _("Artist created")
        TRACK_CREATED = "track_created", _("Track created")
        TRACK_MONITORED = "track_monitored", _("Track monitored")
        CAMPAIGN_CREATED = "campaign_created", _("Campaign created")
        CONTENT_PACK_REQUESTED = "content_pack_requested", _("Content pack requested")
        CONTENT_PACK_GENERATED = "content_pack_generated", _("Content pack generated")
        CONTENT_OUTPUT_CREATED = "content_output_created", _("Content output created")
        SMART_LINK_CREATED = "smart_link_created", _("Smart link created")
        SMART_LINK_CLICKED = "smart_link_clicked", _("Smart link clicked")
        REPORT_GENERATED = "report_generated", _("Report generated")
        MEDIA_KIT_GENERATED = "media_kit_generated", _("Media kit generated")

    event_type = models.CharField(_("event type"), max_length=40)
    quantity = models.DecimalField(
        _("quantity"), max_digits=20, decimal_places=4, default=1
    )
    unit = models.CharField(_("unit"), max_length=40, blank=True)
    related_entity_type = models.CharField(
        _("related entity type"), max_length=80, blank=True
    )
    related_entity_id = models.CharField(
        _("related entity id"), max_length=64, blank=True
    )
    cost_units = models.DecimalField(
        _("cost units"), max_digits=20, decimal_places=4, default=0
    )
    billing_period = models.CharField(_("billing period"), max_length=7, blank=True)
    idempotency_key = models.CharField(
        _("idempotency key"), max_length=255, blank=True
    )
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("usage event")
        verbose_name_plural = _("usage events")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="unique_usage_idempotency_key_per_workspace",
            )
        ]
        indexes = [
            models.Index(fields=["workspace", "event_type"]),
            models.Index(fields=["workspace", "billing_period"]),
        ]

    def __str__(self):
        return f"{self.event_type} x{self.quantity} ({self.workspace_id})"


class CreditLedgerEntry(BaseModel, WorkspaceOwnedModel):
    """An append-only credit ledger entry.

    The signed ``amount`` convention: positive entries add available credits
    (grant/release/refund/purchase/adjustment up), negative entries subtract
    (reserve/consume/expiration/adjustment down). ``balance_after`` denormalizes
    the running available balance for cheap reads; it is also reconstructible by
    summing ``amount``. Idempotent per workspace on ``idempotency_key``.
    """

    class TransactionType(models.TextChoices):
        GRANT = "grant", _("Grant")
        RESERVE = "reserve", _("Reserve")
        CONSUME = "consume", _("Consume")
        RELEASE = "release", _("Release")
        REFUND = "refund", _("Refund")
        ADJUSTMENT = "adjustment", _("Adjustment")
        EXPIRATION = "expiration", _("Expiration")
        PURCHASE = "purchase", _("Purchase")

    transaction_type = models.CharField(
        _("transaction type"), max_length=20, choices=TransactionType.choices
    )
    amount = models.DecimalField(_("amount"), max_digits=20, decimal_places=4)
    balance_after = models.DecimalField(
        _("balance after"), max_digits=20, decimal_places=4
    )
    reason = models.CharField(_("reason"), max_length=255, blank=True)
    related_entity_type = models.CharField(
        _("related entity type"), max_length=80, blank=True
    )
    related_entity_id = models.CharField(
        _("related entity id"), max_length=64, blank=True
    )
    idempotency_key = models.CharField(
        _("idempotency key"), max_length=255, blank=True
    )
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("credit ledger entry")
        verbose_name_plural = _("credit ledger entries")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="unique_credit_idempotency_key_per_workspace",
            )
        ]
        indexes = [
            models.Index(fields=["workspace", "transaction_type"]),
        ]

    def __str__(self):
        return f"{self.transaction_type} {self.amount} ({self.workspace_id})"


class BillingWebhookEvent(BaseModel):
    """An inbound provider webhook (Stripe), logged idempotently.

    Idempotency is enforced on ``(provider, provider_event_id)`` so a duplicate
    delivery (Stripe retries) is never reprocessed. The raw ``payload`` is kept
    for audit/replay.
    """

    class Provider(models.TextChoices):
        STRIPE = "stripe", _("Stripe")

    class Status(models.TextChoices):
        RECEIVED = "received", _("Received")
        PROCESSED = "processed", _("Processed")
        IGNORED = "ignored", _("Ignored")
        FAILED = "failed", _("Failed")
        DUPLICATE = "duplicate", _("Duplicate")

    provider = models.CharField(
        _("provider"),
        max_length=20,
        choices=Provider.choices,
        default=Provider.STRIPE,
    )
    provider_event_id = models.CharField(_("provider event id"), max_length=255)
    event_type = models.CharField(_("event type"), max_length=120, blank=True)
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.RECEIVED
    )
    received_at = models.DateTimeField(_("received at"), default=now)
    processed_at = models.DateTimeField(_("processed at"), null=True, blank=True)
    payload = models.JSONField(_("payload"), default=dict, blank=True)
    error_message = models.TextField(_("error message"), blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("billing webhook event")
        verbose_name_plural = _("billing webhook events")
        ordering = ["-received_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_event_id"],
                name="unique_provider_event_id",
            )
        ]
        indexes = [
            models.Index(fields=["provider", "event_type"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.provider}:{self.provider_event_id} ({self.status})"
