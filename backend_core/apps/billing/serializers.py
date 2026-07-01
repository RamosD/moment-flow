"""Serializers for the billing domain (read-oriented)."""

from rest_framework import serializers

from .models import (
    CreditLedgerEntry,
    Plan,
    PlanFeature,
    Subscription,
    UsageEvent,
)


class PlanFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanFeature
        fields = (
            "id",
            "feature_key",
            "limit_value",
            "limit_unit",
            "is_enabled",
            "metadata",
        )
        read_only_fields = fields


class PlanSerializer(serializers.ModelSerializer):
    features = PlanFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = Plan
        fields = (
            "id",
            "plan_key",
            "name",
            "description",
            "billing_interval",
            "base_price",
            "currency",
            "status",
            "is_public",
            "features",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "workspace",
            "plan",
            "provider",
            "provider_subscription_id",
            "status",
            "current_period_start",
            "current_period_end",
            "trial_start",
            "trial_end",
            "cancel_at_period_end",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class UsageEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageEvent
        fields = (
            "id",
            "workspace",
            "event_type",
            "quantity",
            "unit",
            "related_entity_type",
            "related_entity_id",
            "cost_units",
            "billing_period",
            "idempotency_key",
            "metadata",
            "created_at",
        )
        read_only_fields = fields


class CreditLedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditLedgerEntry
        fields = (
            "id",
            "workspace",
            "transaction_type",
            "amount",
            "balance_after",
            "reason",
            "related_entity_type",
            "related_entity_id",
            "idempotency_key",
            "metadata",
            "created_at",
        )
        read_only_fields = fields
