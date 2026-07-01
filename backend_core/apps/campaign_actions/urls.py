"""Campaign-action routes mounted under /api/v1/."""

from rest_framework.routers import DefaultRouter

from .views import CampaignActionViewSet

app_name = "campaign_actions"

router = DefaultRouter()
router.register("campaign-actions", CampaignActionViewSet, basename="campaign-action")

urlpatterns = router.urls

