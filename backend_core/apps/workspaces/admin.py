"""Django Admin for workspaces and members."""

from django.contrib import admin

from .models import Workspace, WorkspaceMember


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "workspace_type",
        "status",
        "created_by",
        "created_at",
        "deleted_at",
    )
    list_filter = ("workspace_type", "status")
    search_fields = ("name", "slug", "created_by__email")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)
    autocomplete_fields = ("created_by",)

    def get_queryset(self, request):
        # Show soft-deleted workspaces in the admin as well.
        return self.model.all_objects.all()


@admin.register(WorkspaceMember)
class WorkspaceMemberAdmin(admin.ModelAdmin):
    list_display = (
        "workspace",
        "user",
        "role",
        "role_key",
        "status",
        "joined_at",
        "created_at",
    )
    list_filter = ("status", "role_key")
    search_fields = ("workspace__name", "workspace__slug", "user__email")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    autocomplete_fields = ("workspace", "user", "role", "invited_by")
