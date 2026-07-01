"""Django Admin for the billing domain.

Usage and credit ledger entries are append-only records, so they are read-only in
the admin (no add/change/delete) to keep the audit trail trustworthy. Webhook
events are likewise read-only.
"""

from django.contrib import admin

from .models import (
    BillingWebhookEvent,
    CreditLedgerEntry,
    Plan,
    PlanFeature,
    Subscription,
    UsageEvent,
)


class PlanFeatureInline(admin.TabularInline):
    model = PlanFeature
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "plan_key",
        "name",
        "billing_interval",
        "base_price",
        "currency",
        "status",
        "is_public",
    )
    list_filter = ("status", "is_public", "billing_interval")
    search_fields = ("plan_key", "name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("base_price", "name")
    inlines = (PlanFeatureInline,)


@admin.register(PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = ("plan", "feature_key", "limit_value", "limit_unit", "is_enabled")
    list_filter = ("limit_unit", "is_enabled", "feature_key")
    search_fields = ("plan__plan_key", "feature_key")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("plan", "feature_key")
    autocomplete_fields = ("plan",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "workspace",
        "plan",
        "provider",
        "status",
        "current_period_end",
        "cancel_at_period_end",
        "created_at",
    )
    list_filter = ("status", "provider")
    search_fields = (
        "workspace__name",
        "plan__plan_key",
        "provider_subscription_id",
    )
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    autocomplete_fields = ("workspace", "plan")


class ReadOnlyAdmin(admin.ModelAdmin):
    """Append-only admin: visible and searchable but not editable."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UsageEvent)
class UsageEventAdmin(ReadOnlyAdmin):
    list_display = (
        "event_type",
        "workspace",
        "quantity",
        "cost_units",
        "billing_period",
        "created_at",
    )
    list_filter = ("event_type", "billing_period")
    search_fields = ("workspace__name", "event_type", "idempotency_key")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(CreditLedgerEntry)
class CreditLedgerEntryAdmin(ReadOnlyAdmin):
    list_display = (
        "transaction_type",
        "workspace",
        "amount",
        "balance_after",
        "reason",
        "created_at",
    )
    list_filter = ("transaction_type",)
    search_fields = ("workspace__name", "reason", "idempotency_key")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(BillingWebhookEvent)
class BillingWebhookEventAdmin(ReadOnlyAdmin):
    list_display = (
        "provider",
        "provider_event_id",
        "event_type",
        "status",
        "received_at",
        "processed_at",
    )
    list_filter = ("provider", "status", "event_type")
    search_fields = ("provider_event_id", "event_type")
    readonly_fields = ("id", "created_at", "updated_at", "received_at", "processed_at")
    ordering = ("-received_at",)
