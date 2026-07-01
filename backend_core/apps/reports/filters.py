"""FilterSets for the reports/media-kit domain."""

from django_filters import rest_framework as filters

from .models import MediaKit, MediaKitItem, Report, ReportSection


class ReportFilter(filters.FilterSet):
    class Meta:
        model = Report
        fields = {
            "status": ["exact"],
            "report_type": ["exact"],
            "campaign": ["exact"],
            "artist": ["exact"],
            "track": ["exact"],
            "created_at": ["gte", "lte"],
        }


class ReportSectionFilter(filters.FilterSet):
    class Meta:
        model = ReportSection
        fields = {
            "report": ["exact"],
            "section_key": ["exact"],
        }


class MediaKitFilter(filters.FilterSet):
    class Meta:
        model = MediaKit
        fields = {
            "status": ["exact"],
            "public_visibility": ["exact"],
            "artist": ["exact"],
            "campaign": ["exact"],
            "track": ["exact"],
            "created_at": ["gte", "lte"],
        }


class MediaKitItemFilter(filters.FilterSet):
    class Meta:
        model = MediaKitItem
        fields = {
            "media_kit": ["exact"],
            "item_type": ["exact"],
        }
