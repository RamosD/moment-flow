"""Django Admin for the reports/media-kit domain."""

from django.contrib import admin

from .models import MediaKit, MediaKitItem, Report, ReportSection


class ReportSectionInline(admin.TabularInline):
    model = ReportSection
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at")


class MediaKitItemInline(admin.TabularInline):
    model = MediaKitItem
    extra = 0
    autocomplete_fields = ("asset",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "report_type",
        "status",
        "workspace",
        "campaign",
        "artist",
        "requested_by",
        "created_at",
    )
    list_filter = ("status", "report_type")
    search_fields = ("title", "workspace__name", "campaign__name", "artist__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    autocomplete_fields = (
        "workspace",
        "campaign",
        "artist",
        "track",
        "requested_by",
        "storage_asset",
    )
    inlines = (ReportSectionInline,)


@admin.register(ReportSection)
class ReportSectionAdmin(admin.ModelAdmin):
    list_display = ("report", "section_key", "title", "sort_order", "created_at")
    list_filter = ("section_key",)
    search_fields = ("report__title", "section_key", "title")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("report", "sort_order")
    autocomplete_fields = ("workspace", "report")


@admin.register(MediaKit)
class MediaKitAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "public_visibility",
        "workspace",
        "artist",
        "created_by",
        "created_at",
    )
    list_filter = ("status", "public_visibility")
    search_fields = ("title", "workspace__name", "artist__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    autocomplete_fields = (
        "workspace",
        "artist",
        "campaign",
        "track",
        "storage_asset",
        "created_by",
    )
    inlines = (MediaKitItemInline,)


@admin.register(MediaKitItem)
class MediaKitItemAdmin(admin.ModelAdmin):
    list_display = ("media_kit", "item_type", "title", "sort_order", "created_at")
    list_filter = ("item_type",)
    search_fields = ("media_kit__title", "title")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("media_kit", "sort_order")
    autocomplete_fields = ("workspace", "media_kit", "asset")
