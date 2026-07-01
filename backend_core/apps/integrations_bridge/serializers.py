"""Serializers for the integrations bridge."""

from rest_framework import serializers

from .models import ExternalJobReference


class ExternalJobReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalJobReference
        fields = (
            "id",
            "workspace",
            "job_type",
            "provider",
            "external_job_id",
            "related_entity_type",
            "related_entity_id",
            "status",
            "requested_by",
            "requested_at",
            "submitted_at",
            "started_at",
            "completed_at",
            "failed_at",
            "callback_received_at",
            "error_message",
            "request_id",
            "idempotency_key",
            "retry_count",
            "request_payload",
            "response_payload",
            "callback_payload",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CallbackEntitySerializer(serializers.Serializer):
    """The ``entity`` block of a callback (validated only when provided)."""

    type = serializers.CharField(required=False, allow_blank=True, default="")
    id = serializers.CharField(required=False, allow_blank=True, default="")


class JobCallbackSerializer(serializers.Serializer):
    """Normalized inbound payload for the internal job callback.

    The job is identified by ``job_id`` (or the legacy ``job``) or by
    ``(provider, external_job_id)``. ``workspace_id`` is **mandatory** and must
    match the job's workspace; ``entity`` is optional but, when present, must
    match the job (both validated in the view). The legacy ``error_message``
    string stays supported alongside the structured ``error`` object.
    """

    # Job identity (new + legacy alias).
    job_id = serializers.UUIDField(required=False)
    job = serializers.UUIDField(required=False)
    provider = serializers.CharField(required=False, allow_blank=True)
    external_job_id = serializers.CharField(required=False, allow_blank=True)

    # Mandatory for security: every callback must assert its workspace, which is
    # then matched against the job's workspace in the view.
    workspace_id = serializers.UUIDField(required=True)
    status = serializers.ChoiceField(choices=ExternalJobReference.Status.choices)
    entity = CallbackEntitySerializer(required=False)
    result = serializers.JSONField(required=False, allow_null=True)
    error = serializers.JSONField(required=False, allow_null=True)
    # Legacy flat error string (mapped to error_message when no error.message).
    error_message = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    metadata = serializers.JSONField(required=False, default=dict)

    def validate(self, attrs):
        if not (
            attrs.get("job") or attrs.get("job_id") or attrs.get("external_job_id")
        ):
            raise serializers.ValidationError(
                "Provide 'job_id' (or legacy 'job') or 'external_job_id'."
            )
        return attrs
