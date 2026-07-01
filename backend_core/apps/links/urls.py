"""Smart link routes.

Authenticated API routes are mounted under /api/v1/; the public resolution
endpoint is mounted at the project root as /l/<slug>/ (see config/urls.py).
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    PublicSmartLinkView,
    SmartLinkClickViewSet,
    SmartLinkDestinationViewSet,
    SmartLinkViewSet,
)

app_name = "links"

router = DefaultRouter()
router.register("smart-links", SmartLinkViewSet, basename="smart-link")
router.register(
    "smart-link-destinations", SmartLinkDestinationViewSet, basename="smart-link-destination"
)
router.register("smart-link-clicks", SmartLinkClickViewSet, basename="smart-link-click")

urlpatterns = router.urls

# Public, unauthenticated resolution endpoint.
public_urlpatterns = [
    path("l/<slug:slug>/", PublicSmartLinkView.as_view(), name="public-smart-link"),
]
