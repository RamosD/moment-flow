"""Reports & media-kit routes (mounted under /api/v1/)."""

from rest_framework.routers import DefaultRouter

from .views import (
    MediaKitItemViewSet,
    MediaKitViewSet,
    ReportSectionViewSet,
    ReportViewSet,
)

app_name = "reports"

router = DefaultRouter()
router.register("reports", ReportViewSet, basename="report")
router.register("report-sections", ReportSectionViewSet, basename="report-section")
router.register("media-kits", MediaKitViewSet, basename="media-kit")
router.register("media-kit-items", MediaKitItemViewSet, basename="media-kit-item")

urlpatterns = router.urls
