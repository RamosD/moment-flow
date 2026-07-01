"""Content routes (mounted under /api/v1/)."""

from rest_framework.routers import DefaultRouter

from .views import (
    ContentOutputViewSet,
    ContentPackRequestViewSet,
    ContentPackTemplateViewSet,
    ContentPackViewSet,
    TemplateVersionViewSet,
    TemplateViewSet,
)

app_name = "content"

router = DefaultRouter()
router.register("templates", TemplateViewSet, basename="template")
router.register("template-versions", TemplateVersionViewSet, basename="template-version")
router.register("content-packs", ContentPackViewSet, basename="content-pack")
router.register(
    "content-pack-templates", ContentPackTemplateViewSet, basename="content-pack-template"
)
router.register(
    "content-pack-requests", ContentPackRequestViewSet, basename="content-pack-request"
)
router.register("content-outputs", ContentOutputViewSet, basename="content-output")

urlpatterns = router.urls
