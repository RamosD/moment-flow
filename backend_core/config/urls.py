"""URL configuration for the ChartRex Backend Core project.

API routes are versioned under ``/api/v1/``. The OpenAPI schema and interactive
documentation are served by drf-spectacular.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.links.urls import public_urlpatterns as links_public_urlpatterns

urlpatterns = [
    path("admin/", admin.site.urls),

    # Accounts and JWT authentication
    path("api/v1/auth/", include("apps.accounts.urls")),

    # Workspaces and multi-tenancy
    path("api/v1/", include("apps.workspaces.urls")),

    # Core entities (assets, …)
    path("api/v1/", include("apps.core.urls")),

    # Catalogue (artists, tracks, platform links)
    path("api/v1/", include("apps.catalogue.urls")),

    # Campaigns (campaigns, tracks, goals)
    path("api/v1/", include("apps.campaigns.urls")),

    # Persistent campaign actions
    path("api/v1/", include("apps.campaign_actions.urls")),

    # Content (templates, packs, requests, outputs)
    path("api/v1/", include("apps.content.urls")),

    # Smart links (authenticated management API)
    path("api/v1/", include("apps.links.urls")),

    # Billing (plans, subscriptions, usage, credits, Stripe webhook)
    path("api/v1/", include("apps.billing.urls")),

    # Reports and media kits
    path("api/v1/", include("apps.reports.urls")),

    # Notifications
    path("api/v1/", include("apps.notifications.urls")),

    # Integrations bridge (internal callbacks for external jobs)
    path("api/v1/", include("apps.integrations_bridge.urls")),

    # OpenAPI schema and documentation
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/v1/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # Public smart link resolution: /l/<slug>/
    *links_public_urlpatterns,
]
