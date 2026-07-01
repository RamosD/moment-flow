"""Django Admin for the content domain."""

from django.contrib import admin

from .models import (
    ContentOutput,
    ContentPack,
    ContentPackRequest,
    ContentPackTemplate,
    Template,
    TemplateVersion,
)


class TemplateVersionInline(admin.TabularInline):
    model = TemplateVersion
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at")


class ContentPackTemplateInline(admin.TabularInline):
    model = ContentPackTemplate
    extra = 0
    autocomplete_fields = ("template",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = (
        "template_key",
        "name",
        "template_type",
        "status",
        "is_system",
        "is_premium",
        "workspace",
    )
    list_filter = ("template_type", "status", "is_system", "is_premium")
    search_fields = ("template_key", "name", "workspace__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("name",)
    autocomplete_fields = ("workspace", "created_by", "updated_by")
    inlines = (TemplateVersionInline,)


@admin.register(TemplateVersion)
class TemplateVersionAdmin(admin.ModelAdmin):
    list_display = ("template", "version", "renderer_type", "status", "created_at")
    list_filter = ("renderer_type", "status")
    search_fields = ("template__template_key", "version")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    autocomplete_fields = ("template", "created_by", "updated_by")


@admin.register(ContentPack)
class ContentPackAdmin(admin.ModelAdmin):
    list_display = (
        "pack_key",
        "name",
        "pack_type",
        "status",
        "is_premium",
        "workspace",
    )
    list_filter = ("pack_type", "status", "is_premium")
    search_fields = ("pack_key", "name", "workspace__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("name",)
    autocomplete_fields = ("workspace",)
    inlines = (ContentPackTemplateInline,)


@admin.register(ContentPackTemplate)
class ContentPackTemplateAdmin(admin.ModelAdmin):
    list_display = ("content_pack", "template", "output_type", "format", "required", "sort_order")
    list_filter = ("required",)
    search_fields = ("content_pack__pack_key", "template__template_key")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("content_pack", "sort_order")
    autocomplete_fields = ("content_pack", "template")


@admin.register(ContentPackRequest)
class ContentPackRequestAdmin(admin.ModelAdmin):
    list_display = (
        "content_pack",
        "campaign",
        "status",
        "workspace",
        "requested_by",
        "requested_at",
    )
    list_filter = ("status",)
    search_fields = ("content_pack__pack_key", "campaign__name", "workspace__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    autocomplete_fields = (
        "workspace",
        "campaign",
        "track",
        "artist",
        "content_pack",
        "requested_by",
    )


@admin.register(ContentOutput)
class ContentOutputAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "output_type",
        "status",
        "public_visibility",
        "campaign",
        "workspace",
        "created_at",
    )
    list_filter = ("status", "public_visibility", "output_type")
    search_fields = ("title", "campaign__name", "workspace__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    autocomplete_fields = (
        "workspace",
        "campaign",
        "track",
        "artist",
        "content_pack_request",
        "template",
        "template_version",
        "storage_asset",
        "created_by",
        "updated_by",
    )
