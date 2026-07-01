"""FilterSets for the notifications domain."""

from django_filters import rest_framework as filters

from .models import Notification


class NotificationFilter(filters.FilterSet):
    class Meta:
        model = Notification
        fields = {
            "status": ["exact"],
            "notification_type": ["exact"],
            "created_at": ["gte", "lte"],
        }
