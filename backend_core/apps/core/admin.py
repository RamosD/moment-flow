"""Django Admin for core entities."""

from django.contrib import admin

from .models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        "file_name",
        "asset_type",
        "storage_provider",
        "workspace",
        "file_size_bytes",
        "created_by",
        "created_at",
        "deleted_at",
    )
    list_filter = ("asset_type", "storage_provider")
    search_fields = ("file_name", "storage_key", "checksum", "workspace__name")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)
    autocomplete_fields = ("workspace", "created_by", "updated_by")

    def get_queryset(self, request):
        # Include soft-deleted assets in the admin.
        return self.model.all_objects.all()
