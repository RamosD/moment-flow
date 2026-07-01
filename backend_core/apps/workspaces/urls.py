"""Workspace routes (mounted under /api/v1/)."""

from rest_framework.routers import DefaultRouter

from .views import WorkspaceMemberViewSet, WorkspaceViewSet

app_name = "workspaces"

router = DefaultRouter()
router.register("workspaces", WorkspaceViewSet, basename="workspace")
router.register("workspace-members", WorkspaceMemberViewSet, basename="workspace-member")

urlpatterns = router.urls
