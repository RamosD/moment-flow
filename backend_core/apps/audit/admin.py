"""Django Admin for audit events — strictly read-only.

Audit events are immutable: the admin cannot add, change or delete them, so the
trail can be trusted. Every field is read-only.
"""

from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "action",
        "actor_type",
        "actor_user",
        "workspace",
        "entity_type",
        "entity_id",
        "created_at",
    )
    list_filter = ("actor_type", "action", "entity_type")
    search_fields = (
        "action",
        "entity_type",
        "entity_id",
        "workspace__name",
        "actor_user__email",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "action",
        "actor_type",
        "actor_user",
        "workspace",
        "entity_type",
        "entity_id",
        "before_data",
        "after_data",
        "ip_address_hash",
        "user_agent_hash",
        "metadata",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
