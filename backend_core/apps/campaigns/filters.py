"""django-filter FilterSets for the campaigns domain."""

import django_filters

from .models import Campaign, CampaignGoal, CampaignTrack


class CampaignFilter(django_filters.FilterSet):
    start_date_after = django_filters.DateFilter(
        field_name="start_date", lookup_expr="gte"
    )
    start_date_before = django_filters.DateFilter(
        field_name="start_date", lookup_expr="lte"
    )

    class Meta:
        model = Campaign
        fields = ["artist", "track", "status", "campaign_type"]


class CampaignTrackFilter(django_filters.FilterSet):
    class Meta:
        model = CampaignTrack
        fields = ["campaign", "track", "role"]


class CampaignGoalFilter(django_filters.FilterSet):
    class Meta:
        model = CampaignGoal
        fields = ["campaign", "goal_type", "status"]
