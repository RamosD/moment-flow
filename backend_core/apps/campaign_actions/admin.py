from django.contrib import admin

from .models import CampaignAction


@admin.register(CampaignAction)
class CampaignActionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "action_type",
        "status",
        "priority",
        "campaign",
        "workspace",
        "created_at",
    )
    list_filter = ("action_type", "status", "priority", "source")
    search_fields = ("title", "recommendation_ref", "campaign__name")
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = (
        "workspace",
        "campaign",
        "created_by",
        "updated_by",
        "related_content_pack_request",
        "related_content_output",
        "related_report",
        "related_media_kit",
    )

