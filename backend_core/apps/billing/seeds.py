"""Idempotent seeding of initial plans and their features.

Used by the ``seed_billing`` management command and by tests. Re-running is safe:
plans are upserted on ``plan_key`` and each plan's feature set is reconciled to
match the definitions below.

Feature limit conventions (``limit_value`` / ``limit_unit``):
  - ``None`` value on an enabled feature means *unlimited*.
  - boolean-style features use ``LimitUnit.BOOLEAN`` and ``is_enabled``.
  - per-month features use ``LimitUnit.PER_MONTH``; storage uses ``GIGABYTE``.
"""

from decimal import Decimal

from django.db import transaction

from .models import Plan, PlanFeature

C = PlanFeature.LimitUnit.COUNT
PM = PlanFeature.LimitUnit.PER_MONTH
GB = PlanFeature.LimitUnit.GIGABYTE
BOOL = PlanFeature.LimitUnit.BOOLEAN

# Catalogue of feature keys, with their default unit. The unit is shared across
# all plans; only the per-plan value/enabled differs.
FEATURE_UNITS = {
    "artists_limit": C,
    "tracks_limit": C,
    "campaigns_limit": C,
    "content_packs_per_month": PM,
    "smart_links_limit": C,
    "reports_per_month": PM,
    "storage_gb": GB,
    "watermark_removal": BOOL,
    "custom_branding": BOOL,
}

# plan_key -> dict(name, description, base_price, billing_interval, is_public,
#                  features={feature_key: (limit_value, is_enabled)})
# A limit_value of None on an enabled feature means unlimited.
PLANS = {
    "trial": {
        "name": "Trial",
        "description": "Free time-limited trial.",
        "base_price": Decimal("0"),
        "billing_interval": Plan.BillingInterval.MONTH,
        "is_public": True,
        "features": {
            "artists_limit": (1, True),
            "tracks_limit": (3, True),
            "campaigns_limit": (1, True),
            "content_packs_per_month": (2, True),
            "smart_links_limit": (3, True),
            "reports_per_month": (1, True),
            "storage_gb": (1, True),
            "watermark_removal": (None, False),
            "custom_branding": (None, False),
        },
    },
    "artist_starter": {
        "name": "Artist Starter",
        "description": "For independent artists getting started.",
        "base_price": Decimal("9"),
        "billing_interval": Plan.BillingInterval.MONTH,
        "is_public": True,
        "features": {
            "artists_limit": (1, True),
            "tracks_limit": (15, True),
            "campaigns_limit": (3, True),
            "content_packs_per_month": (8, True),
            "smart_links_limit": (10, True),
            "reports_per_month": (4, True),
            "storage_gb": (5, True),
            "watermark_removal": (None, False),
            "custom_branding": (None, False),
        },
    },
    "artist_growth": {
        "name": "Artist Growth",
        "description": "For growing artists who ship often.",
        "base_price": Decimal("29"),
        "billing_interval": Plan.BillingInterval.MONTH,
        "is_public": True,
        "features": {
            "artists_limit": (3, True),
            "tracks_limit": (60, True),
            "campaigns_limit": (10, True),
            "content_packs_per_month": (30, True),
            "smart_links_limit": (50, True),
            "reports_per_month": (15, True),
            "storage_gb": (25, True),
            "watermark_removal": (None, True),
            "custom_branding": (None, False),
        },
    },
    "manager": {
        "name": "Manager",
        "description": "For managers handling several artists.",
        "base_price": Decimal("79"),
        "billing_interval": Plan.BillingInterval.MONTH,
        "is_public": True,
        "features": {
            "artists_limit": (15, True),
            "tracks_limit": (300, True),
            "campaigns_limit": (40, True),
            "content_packs_per_month": (120, True),
            "smart_links_limit": (200, True),
            "reports_per_month": (60, True),
            "storage_gb": (100, True),
            "watermark_removal": (None, True),
            "custom_branding": (None, True),
        },
    },
    "label_agency": {
        "name": "Label / Agency",
        "description": "For labels and agencies with large rosters.",
        "base_price": Decimal("249"),
        "billing_interval": Plan.BillingInterval.MONTH,
        "is_public": True,
        "features": {
            "artists_limit": (100, True),
            "tracks_limit": (2000, True),
            "campaigns_limit": (200, True),
            "content_packs_per_month": (600, True),
            "smart_links_limit": (1000, True),
            "reports_per_month": (300, True),
            "storage_gb": (500, True),
            "watermark_removal": (None, True),
            "custom_branding": (None, True),
        },
    },
    "white_label": {
        "name": "White Label",
        "description": "Fully branded white-label deployment.",
        "base_price": Decimal("599"),
        "billing_interval": Plan.BillingInterval.MONTH,
        "is_public": False,
        "features": {
            "artists_limit": (None, True),
            "tracks_limit": (None, True),
            "campaigns_limit": (None, True),
            "content_packs_per_month": (None, True),
            "smart_links_limit": (None, True),
            "reports_per_month": (None, True),
            "storage_gb": (2000, True),
            "watermark_removal": (None, True),
            "custom_branding": (None, True),
        },
    },
    "enterprise": {
        "name": "Enterprise",
        "description": "Custom enterprise plan (manual, unlimited).",
        "base_price": Decimal("0"),
        "billing_interval": Plan.BillingInterval.CUSTOM,
        "is_public": False,
        "features": {
            "artists_limit": (None, True),
            "tracks_limit": (None, True),
            "campaigns_limit": (None, True),
            "content_packs_per_month": (None, True),
            "smart_links_limit": (None, True),
            "reports_per_month": (None, True),
            "storage_gb": (None, True),
            "watermark_removal": (None, True),
            "custom_branding": (None, True),
        },
    },
}


@transaction.atomic
def seed_billing() -> dict:
    """Create or update the initial plans and their features. Idempotent."""
    feature_count = 0
    for plan_key, spec in PLANS.items():
        plan, _ = Plan.objects.update_or_create(
            plan_key=plan_key,
            defaults={
                "name": spec["name"],
                "description": spec["description"],
                "base_price": spec["base_price"],
                "billing_interval": spec["billing_interval"],
                "currency": "USD",
                "status": Plan.Status.ACTIVE,
                "is_public": spec["is_public"],
            },
        )
        for feature_key, (limit_value, is_enabled) in spec["features"].items():
            PlanFeature.objects.update_or_create(
                plan=plan,
                feature_key=feature_key,
                defaults={
                    "limit_value": limit_value,
                    "limit_unit": FEATURE_UNITS[feature_key],
                    "is_enabled": is_enabled,
                },
            )
            feature_count += 1

    return {"plans": len(PLANS), "features": feature_count}
