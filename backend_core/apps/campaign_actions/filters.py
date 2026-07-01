"""FilterSet for persistent campaign actions."""

from django_filters import rest_framework as filters

from .models import CampaignAction


class CampaignActionFilter(filters.FilterSet):
    class Meta:
        model = CampaignAction
        fields = {
            "campaign": ["exact"],
            "status": ["exact"],
            "action_type": ["exact"],
            "recommendation_ref": ["exact"],
            "source": ["exact"],
            "created_by": ["exact"],
        }

