"""Django Admin for the campaigns domain."""

from django.contrib import admin

from .models import Campaign, CampaignGoal, CampaignTrack


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "artist",
        "workspace",
        "campaign_type",
        "status",
        "start_date",
        "created_at",
        "deleted_at",
    )
    list_filter = ("status", "campaign_type")
    search_fields = ("name", "slug", "artist__name", "workspace__name")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)
    autocomplete_fields = ("workspace", "artist", "track", "created_by", "updated_by")

    def get_queryset(self, request):
        return self.model.all_objects.all()


@admin.register(CampaignTrack)
class CampaignTrackAdmin(admin.ModelAdmin):
    list_display = ("campaign", "track", "role", "workspace", "created_at")
    list_filter = ("role",)
    search_fields = ("campaign__name", "track__title", "workspace__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    autocomplete_fields = ("workspace", "campaign", "track")


@admin.register(CampaignGoal)
class CampaignGoalAdmin(admin.ModelAdmin):
    list_display = (
        "campaign",
        "goal_type",
        "target_value",
        "current_value",
        "status",
        "deadline",
        "created_at",
    )
    list_filter = ("goal_type", "status")
    search_fields = ("campaign__name", "workspace__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    autocomplete_fields = ("workspace", "campaign")
