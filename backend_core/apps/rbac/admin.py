"""Django Admin for RBAC entities."""

from django.contrib import admin

from .models import Permission, Role, RolePermission


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0
    autocomplete_fields = ("permission",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "domain", "created_at")
    list_filter = ("domain",)
    search_fields = ("key", "name", "domain")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("key",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "is_system", "workspace", "created_at")
    list_filter = ("is_system",)
    search_fields = ("key", "name", "workspace__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("key",)
    inlines = (RolePermissionInline,)


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "permission", "created_at")
    search_fields = ("role__key", "permission__key")
    autocomplete_fields = ("role", "permission")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
