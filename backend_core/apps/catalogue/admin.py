"""Django Admin for the catalogue."""

from django.contrib import admin

from .models import Artist, Track, TrackPlatformLink


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "workspace",
        "status",
        "primary_genre",
        "created_at",
        "deleted_at",
    )
    list_filter = ("status", "primary_genre", "country")
    search_fields = ("name", "slug", "primary_genre", "workspace__name")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)
    autocomplete_fields = ("workspace", "image_asset", "created_by", "updated_by")

    def get_queryset(self, request):
        return self.model.all_objects.all()


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "artist",
        "workspace",
        "track_type",
        "status",
        "release_date",
        "created_at",
        "deleted_at",
    )
    list_filter = ("status", "track_type", "primary_genre")
    search_fields = ("title", "slug", "artist__name", "workspace__name")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)
    autocomplete_fields = (
        "workspace",
        "artist",
        "cover_asset",
        "created_by",
        "updated_by",
    )

    def get_queryset(self, request):
        return self.model.all_objects.all()


@admin.register(TrackPlatformLink)
class TrackPlatformLinkAdmin(admin.ModelAdmin):
    list_display = (
        "track",
        "platform",
        "external_id",
        "status",
        "workspace",
        "last_validated_at",
        "created_at",
    )
    list_filter = ("platform", "status")
    search_fields = ("external_id", "url", "track__title", "workspace__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    autocomplete_fields = ("workspace", "track")
