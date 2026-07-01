"""django-filter FilterSets for the catalogue."""

import django_filters

from .models import Artist, Track, TrackPlatformLink


class ArtistFilter(django_filters.FilterSet):
    class Meta:
        model = Artist
        fields = ["status", "primary_genre", "country", "market", "language"]


class TrackFilter(django_filters.FilterSet):
    release_date_after = django_filters.DateFilter(
        field_name="release_date", lookup_expr="gte"
    )
    release_date_before = django_filters.DateFilter(
        field_name="release_date", lookup_expr="lte"
    )

    class Meta:
        model = Track
        fields = [
            "artist",
            "status",
            "track_type",
            "primary_genre",
            "language",
            "market",
        ]


class TrackPlatformLinkFilter(django_filters.FilterSet):
    class Meta:
        model = TrackPlatformLink
        fields = ["track", "platform", "status"]
