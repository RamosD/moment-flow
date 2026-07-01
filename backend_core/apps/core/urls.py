"""Core routes (mounted under /api/v1/)."""

from rest_framework.routers import DefaultRouter

from .views import AssetViewSet

app_name = "core"

router = DefaultRouter()
router.register("assets", AssetViewSet, basename="asset")

urlpatterns = router.urls
