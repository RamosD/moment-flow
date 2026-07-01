"""Billing routes (mounted under /api/v1/).

  - ``/plans/``                       public plan catalogue (read-only)
  - ``/billing/subscription/``        active subscription of the workspace
  - ``/billing/usage/``               aggregated usage for a period
  - ``/billing/credits/``             credit balance + recent ledger
  - ``/billing/webhooks/stripe/``     Stripe webhook (skeleton)
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ActiveSubscriptionView,
    CreditBalanceView,
    PeriodUsageView,
    PlanViewSet,
    StripeWebhookView,
)

app_name = "billing"

router = DefaultRouter()
router.register("plans", PlanViewSet, basename="plan")

urlpatterns = [
    path("billing/subscription/", ActiveSubscriptionView.as_view(), name="active-subscription"),
    path("billing/usage/", PeriodUsageView.as_view(), name="period-usage"),
    path("billing/credits/", CreditBalanceView.as_view(), name="credit-balance"),
    path("billing/webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
    *router.urls,
]
