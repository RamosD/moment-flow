"""Django Admin for the smart links domain."""

from django.contrib import admin

from .models import SmartLink, SmartLinkClick, SmartLinkDestination


class SmartLinkDestinationInline(admin.TabularInline):
    model = SmartLinkDestination
    extra = 0
    fields = ("platform", "label", "url", "sort_order", "is_active")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(SmartLink)
class SmartLinkAdmin(admin.ModelAdmin):
    list_display = (
        "slug",
        "title",
        "status",
        "campaign",
        "workspace",
        "branding_enabled",
        "created_at",
        "deleted_at",
    )
    list_filter = ("status", "branding_enabled")
    search_fields = ("slug", "title", "campaign__name", "workspace__name")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)
    autocomplete_fields = ("workspace", "campaign", "track", "artist", "created_by", "updated_by")
    inlines = (SmartLinkDestinationInline,)

    def get_queryset(self, request):
        return self.model.all_objects.all()


@admin.register(SmartLinkDestination)
class SmartLinkDestinationAdmin(admin.ModelAdmin):
    list_display = ("smart_link", "platform", "label", "sort_order", "is_active", "workspace")
    list_filter = ("platform", "is_active")
    search_fields = ("smart_link__slug", "label", "url")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("smart_link", "sort_order")
    autocomplete_fields = ("workspace", "smart_link")


@admin.register(SmartLinkClick)
class SmartLinkClickAdmin(admin.ModelAdmin):
    list_display = (
        "smart_link",
        "destination",
        "campaign",
        "device_type",
        "browser",
        "clicked_at",
    )
    list_filter = ("device_type", "browser")
    search_fields = ("smart_link__slug", "campaign__name")
    readonly_fields = tuple(f.name for f in SmartLinkClick._meta.fields)
    ordering = ("-clicked_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
