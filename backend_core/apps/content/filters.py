"""django-filter FilterSets for the content domain."""

import django_filters

from .models import (
    ContentOutput,
    ContentPack,
    ContentPackRequest,
    Template,
)


class TemplateFilter(django_filters.FilterSet):
    class Meta:
        model = Template
        fields = ["template_type", "status", "is_premium", "is_system"]


class ContentPackFilter(django_filters.FilterSet):
    class Meta:
        model = ContentPack
        fields = ["pack_type", "status", "is_premium"]


class ContentPackRequestFilter(django_filters.FilterSet):
    class Meta:
        model = ContentPackRequest
        fields = ["campaign", "content_pack", "status"]


class ContentOutputFilter(django_filters.FilterSet):
    class Meta:
        model = ContentOutput
        fields = ["campaign", "output_type", "status", "public_visibility"]
