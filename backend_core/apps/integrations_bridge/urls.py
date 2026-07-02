"""Integrations bridge routes (internal; mounted under /api/v1/)."""

from django.urls import path

from .views import (
    ExternalJobCallbackView,
    SystemDependencyHealthView,
    SystemLivenessView,
    SystemReadinessView,
)

app_name = "integrations_bridge"

urlpatterns = [
    path(
        "internal/jobs/callback/",
        ExternalJobCallbackView.as_view(),
        name="job-callback",
    ),
    # Aggregated dependency healthcheck (OBS-STG-003). Staff-only; exposes the
    # operational status of the Intelligence Engine, the Content Renderer and the
    # database. Full path: /api/v1/system/health/dependencies/.
    path(
        "system/health/dependencies/",
        SystemDependencyHealthView.as_view(),
        name="system-health-dependencies",
    ),
    # Liveness/readiness (STG-PRE-006). Public, like IE's/CR's own /health.
    path(
        "system/health/live/",
        SystemLivenessView.as_view(),
        name="system-health-live",
    ),
    path(
        "system/health/ready/",
        SystemReadinessView.as_view(),
        name="system-health-ready",
    ),
]
