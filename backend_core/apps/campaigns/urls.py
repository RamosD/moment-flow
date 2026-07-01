"""Campaign routes (mounted under /api/v1/)."""

from rest_framework.routers import DefaultRouter

from .views import CampaignGoalViewSet, CampaignTrackViewSet, CampaignViewSet

app_name = "campaigns"

router = DefaultRouter()
router.register("campaigns", CampaignViewSet, basename="campaign")
router.register("campaign-tracks", CampaignTrackViewSet, basename="campaign-track")
router.register("campaign-goals", CampaignGoalViewSet, basename="campaign-goal")

urlpatterns = router.urls
