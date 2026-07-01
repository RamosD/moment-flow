"""django-filter FilterSets for the smart links domain."""

import django_filters

from .models import SmartLink, SmartLinkClick, SmartLinkDestination


class SmartLinkFilter(django_filters.FilterSet):
    class Meta:
        model = SmartLink
        fields = ["campaign", "track", "artist", "status"]


class SmartLinkDestinationFilter(django_filters.FilterSet):
    class Meta:
        model = SmartLinkDestination
        fields = ["smart_link", "platform", "is_active"]


class SmartLinkClickFilter(django_filters.FilterSet):
    class Meta:
        model = SmartLinkClick
        fields = ["smart_link", "destination", "campaign"]
