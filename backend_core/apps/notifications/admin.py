"""Django Admin for notifications."""

from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "notification_type",
        "status",
        "workspace",
        "user",
        "read_at",
        "created_at",
    )
    list_filter = ("status", "notification_type")
    search_fields = ("title", "message", "workspace__name", "user__email")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    autocomplete_fields = ("workspace", "user")
