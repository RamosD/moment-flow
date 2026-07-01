"""Catalogue routes (mounted under /api/v1/)."""

from rest_framework.routers import DefaultRouter

from .views import ArtistViewSet, TrackPlatformLinkViewSet, TrackViewSet

app_name = "catalogue"

router = DefaultRouter()
router.register("artists", ArtistViewSet, basename="artist")
router.register("tracks", TrackViewSet, basename="track")
router.register(
    "track-platform-links", TrackPlatformLinkViewSet, basename="track-platform-link"
)

urlpatterns = router.urls
