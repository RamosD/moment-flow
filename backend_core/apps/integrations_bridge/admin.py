"""Django Admin for external job references — for operational investigation.

States are driven by external callbacks, so payloads and lifecycle timestamps are
read-only. A single safe action is offered: cancelling *non-terminal* jobs (a
local-only transition; it never calls an external service).
"""

from django.contrib import admin
from django.utils.timezone import now

from .models import ExternalJobReference


@admin.register(ExternalJobReference)
class ExternalJobReferenceAdmin(admin.ModelAdmin):
    list_display = (
        "job_type",
        "provider",
        "status",
        "workspace",
        "external_job_id",
        "related_entity_type",
        "related_entity_id",
        "request_id",
        "retry_count",
        "requested_at",
        "completed_at",
    )
    list_filter = ("status", "job_type", "provider", "workspace")
    search_fields = (
        "external_job_id",
        "related_entity_type",
        "related_entity_id",
        "request_id",
        "workspace__name",
    )
    readonly_fields = (
        "id",
        "request_id",
        "idempotency_key",
        "retry_count",
        "requested_at",
        "submitted_at",
        "started_at",
        "completed_at",
        "failed_at",
        "callback_received_at",
        "request_payload",
        "response_payload",
        "callback_payload",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    autocomplete_fields = ("workspace", "requested_by")
    actions = ["mark_cancelled"]

    @admin.action(description="Cancel selected non-terminal jobs")
    def mark_cancelled(self, request, queryset):
        """Cancel only non-terminal jobs (local transition; no external call)."""
        cancellable = queryset.exclude(
            status__in=ExternalJobReference.TERMINAL_STATUSES
        )
        updated = cancellable.update(
            status=ExternalJobReference.Status.CANCELLED, failed_at=now()
        )
        self.message_user(
            request, f"{updated} job(s) cancelled (terminal jobs were skipped)."
        )
