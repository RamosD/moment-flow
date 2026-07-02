"""Serializers for persistent campaign actions."""

import json

from django.db import transaction
from rest_framework import serializers

from .models import CampaignAction
from .services import (
    CampaignActionTransitionError,
    transition_campaign_action,
    validate_status_transition,
)

_ACTIVE_DUPLICATE_STATUSES = (
    CampaignAction.Status.PENDING,
    CampaignAction.Status.IN_PROGRESS,
    CampaignAction.Status.COMPLETED,
)

_SENSITIVE_SNAPSHOT_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "client_secret",
    "internal_api_token",
    "password",
    "passwd",
    "private_key",
    "refresh_token",
    "secret",
    "token",
}

_MAX_SNAPSHOT_BYTES = 64 * 1024

_RELATED_FIELD_LABELS = {
    "related_content_pack_request": "Related content pack request",
    "related_content_output": "Related content output",
    "related_report": "Related report",
    "related_media_kit": "Related media kit",
}

_ALLOWED_RELATED_FIELDS = {
    CampaignAction.ActionType.CONTENT_PACK: frozenset(
        {"related_content_pack_request", "related_content_output"}
    ),
    CampaignAction.ActionType.REPORT_REQUEST: frozenset({"related_report"}),
    CampaignAction.ActionType.MEDIA_KIT_REQUEST: frozenset({"related_media_kit"}),
    CampaignAction.ActionType.MANUAL_TASK: frozenset(),
    CampaignAction.ActionType.MARK_REVIEWED: frozenset(),
    CampaignAction.ActionType.DISMISS: frozenset(),
}


def _find_sensitive_key(value, path="recommendation_snapshot"):
    """Return the first sensitive JSON-key path, if one is present."""

    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            child_path = f"{path}.{key}"
            if normalized in _SENSITIVE_SNAPSHOT_KEYS:
                return child_path
            found = _find_sensitive_key(child, child_path)
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = _find_sensitive_key(child, f"{path}[{index}]")
            if found:
                return found
    return None


def _redact_sensitive_keys(value):
    """Redact sensitive keys defensively when representing legacy/direct data."""

    if isinstance(value, dict):
        redacted = {}
        for key, child in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            redacted[key] = (
                "[REDACTED]"
                if normalized in _SENSITIVE_SNAPSHOT_KEYS
                else _redact_sensitive_keys(child)
            )
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive_keys(child) for child in value]
    return value


def _related_artifact_status(action):
    """Surface the status of whichever artifact this action points to.

    The CampaignAction's own ``status`` is a separate, user-driven lifecycle
    (STG-PRE-007: not altered here) — this only exposes the *artifact's*
    generation outcome so a "queued"/"draft" artifact whose renderer job
    actually failed is diagnosable from this API without a second request.
    """
    if action.related_report_id and action.related_report:
        return {"type": "report", "status": action.related_report.status}
    if action.related_media_kit_id and action.related_media_kit:
        media_kit = action.related_media_kit
        status = media_kit.status
        if (media_kit.metadata or {}).get("generation_status") == "failed":
            # MediaKit has no dedicated FAILED status — a failed generation is
            # recorded on metadata instead (see reports.callbacks).
            status = "failed"
        return {"type": "media_kit", "status": status}
    if action.related_content_pack_request_id and action.related_content_pack_request:
        return {
            "type": "content_pack_request",
            "status": action.related_content_pack_request.status,
        }
    return None


class CampaignActionSerializer(serializers.ModelSerializer):
    """Read/write representation with tenant and campaign integrity checks."""

    related_artifact_status = serializers.SerializerMethodField()

    class Meta:
        model = CampaignAction
        fields = (
            "id",
            "workspace",
            "campaign",
            "recommendation_ref",
            "recommendation_snapshot",
            "title",
            "description",
            "action_type",
            "status",
            "priority",
            "source",
            "dismiss_reason",
            "metadata",
            "related_content_pack_request",
            "related_content_output",
            "related_report",
            "related_media_kit",
            "related_artifact_status",
            "created_by",
            "completed_at",
            "cancelled_at",
            "correlation_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "workspace",
            "created_by",
            "completed_at",
            "cancelled_at",
            "correlation_id",
            "created_at",
            "updated_at",
        )

    def get_related_artifact_status(self, obj):
        return _related_artifact_status(obj)

    @property
    def _active_workspace(self):
        request = self.context.get("request")
        return getattr(request, "workspace", None)

    def validate_recommendation_ref(self, value):
        return value.strip()

    def validate_dismiss_reason(self, value):
        return value.strip()

    def validate_recommendation_snapshot(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Must be a JSON object.")

        sensitive_path = _find_sensitive_key(value)
        if sensitive_path:
            raise serializers.ValidationError(
                f"Sensitive data is not allowed ({sensitive_path})."
            )

        try:
            encoded = json.dumps(
                value, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError("Must contain valid JSON data.") from exc

        if len(encoded) > _MAX_SNAPSHOT_BYTES:
            raise serializers.ValidationError(
                "Must not exceed 65536 bytes when JSON encoded."
            )
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["recommendation_snapshot"] = _redact_sensitive_keys(
            representation.get("recommendation_snapshot", {})
        )
        return representation

    def _effective_value(self, attrs, field_name):
        if field_name in attrs:
            return attrs[field_name]
        if self.instance is not None:
            return getattr(self.instance, field_name)
        return None

    @staticmethod
    def _add_error(errors, field_name, message):
        errors.setdefault(field_name, []).append(message)

    def _validate_related_object(
        self, errors, field_name, label, related_object, workspace, campaign
    ):
        if related_object is None:
            return
        if related_object.workspace_id != workspace.id:
            self._add_error(
                errors, field_name, f"{label} must belong to the active workspace."
            )
            return
        if related_object.campaign_id != campaign.id:
            self._add_error(
                errors, field_name, f"{label} must belong to the selected campaign."
            )

    def _validate_immutable_fields(self, attrs, errors):
        if self.instance is None:
            return
        for field_name in (
            "campaign",
            "recommendation_ref",
            "recommendation_snapshot",
            "action_type",
            "source",
        ):
            if field_name not in attrs:
                continue
            current = getattr(self.instance, field_name)
            if attrs[field_name] != current:
                self._add_error(errors, field_name, "This field cannot be changed.")

    def _validate_related_compatibility(self, errors, action_type, related_objects):
        allowed_fields = _ALLOWED_RELATED_FIELDS.get(action_type, frozenset())
        for field_name, related_object in related_objects.items():
            if related_object is not None and field_name not in allowed_fields:
                self._add_error(
                    errors,
                    field_name,
                    f"This relation is not compatible with action_type {action_type}.",
                )

        content_pack_request = related_objects["related_content_pack_request"]
        content_output = related_objects["related_content_output"]
        if (
            content_pack_request is not None
            and content_output is not None
            and content_output.content_pack_request_id is not None
            and content_output.content_pack_request_id != content_pack_request.id
        ):
            self._add_error(
                errors,
                "related_content_output",
                "Related content output belongs to a different content pack request.",
            )

    def _validate_duplicate(
        self, errors, workspace, campaign, recommendation_ref, action_type, status
    ):
        if not recommendation_ref or status not in _ACTIVE_DUPLICATE_STATUSES:
            return
        queryset = CampaignAction.objects.filter(
            workspace=workspace,
            campaign=campaign,
            recommendation_ref=recommendation_ref,
            action_type=action_type,
            status__in=_ACTIVE_DUPLICATE_STATUSES,
        )
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            self._add_error(
                errors,
                "recommendation_ref",
                "An active action of this type already exists for this recommendation.",
            )

    @transaction.atomic
    def create(self, validated_data):
        requested_status = validated_data.pop("status", None)
        action_type = validated_data["action_type"]
        status_was_provided = "status" in getattr(self, "initial_data", {})
        if not status_was_provided:
            if action_type == CampaignAction.ActionType.MARK_REVIEWED:
                requested_status = CampaignAction.Status.COMPLETED
            elif action_type == CampaignAction.ActionType.DISMISS:
                requested_status = CampaignAction.Status.DISMISSED
            else:
                requested_status = CampaignAction.Status.PENDING

        actor = validated_data.get("updated_by")
        dismiss_reason = validated_data.pop("dismiss_reason", "")
        instance = super().create(
            {
                **validated_data,
                "status": CampaignAction.Status.PENDING,
                "dismiss_reason": "",
            }
        )
        if requested_status != CampaignAction.Status.PENDING:
            return transition_campaign_action(
                instance,
                requested_status,
                actor=actor,
                dismiss_reason=dismiss_reason,
            )
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        requested_status = validated_data.pop("status", None)
        actor = validated_data.get("updated_by")
        dismiss_reason = validated_data.get(
            "dismiss_reason", instance.dismiss_reason
        )
        instance = super().update(instance, validated_data)
        if requested_status is not None:
            instance = transition_campaign_action(
                instance,
                requested_status,
                actor=actor,
                dismiss_reason=dismiss_reason,
            )
        return instance

    def validate(self, attrs):
        workspace = self._active_workspace
        if workspace is None:
            raise serializers.ValidationError(
                {"workspace": "Active workspace context is required."}
            )

        errors = {}
        campaign = self._effective_value(attrs, "campaign")
        action_type = self._effective_value(attrs, "action_type")
        status = (
            self._effective_value(attrs, "status") or CampaignAction.Status.PENDING
        )
        if self.instance is None and "status" not in getattr(self, "initial_data", {}):
            if action_type == CampaignAction.ActionType.MARK_REVIEWED:
                status = CampaignAction.Status.COMPLETED
            elif action_type == CampaignAction.ActionType.DISMISS:
                status = CampaignAction.Status.DISMISSED
        recommendation_ref = self._effective_value(attrs, "recommendation_ref") or ""
        recommendation_snapshot = (
            self._effective_value(attrs, "recommendation_snapshot") or {}
        )
        dismiss_reason = self._effective_value(attrs, "dismiss_reason") or ""

        if campaign is not None and campaign.workspace_id != workspace.id:
            self._add_error(
                errors, "campaign", "Campaign must belong to the active workspace."
            )

        self._validate_immutable_fields(attrs, errors)

        if action_type and action_type != CampaignAction.ActionType.MANUAL_TASK:
            if not recommendation_ref.strip():
                self._add_error(
                    errors,
                    "recommendation_ref",
                    "This field is required unless action_type is manual_task.",
                )
            if not recommendation_snapshot:
                self._add_error(
                    errors,
                    "recommendation_snapshot",
                    "A non-empty snapshot is required unless action_type is manual_task.",
                )

        if (
            action_type == CampaignAction.ActionType.DISMISS
            or status == CampaignAction.Status.DISMISSED
        ) and not dismiss_reason.strip():
            self._add_error(
                errors,
                "dismiss_reason",
                "This field is required for dismissed actions.",
            )

        if (
            action_type == CampaignAction.ActionType.DISMISS
            and status != CampaignAction.Status.DISMISSED
        ):
            self._add_error(
                errors,
                "status",
                "Actions of type dismiss must use status dismissed.",
            )
        if (
            action_type == CampaignAction.ActionType.MARK_REVIEWED
            and status != CampaignAction.Status.COMPLETED
        ):
            self._add_error(
                errors,
                "status",
                "Actions of type mark_reviewed must use status completed.",
            )

        if self.instance is not None and "status" in attrs:
            try:
                validate_status_transition(
                    self.instance.status,
                    status,
                    dismiss_reason=dismiss_reason,
                )
            except CampaignActionTransitionError as exc:
                self._add_error(errors, exc.field, str(exc))

        if campaign is not None and campaign.workspace_id == workspace.id:
            related_objects = {
                field_name: self._effective_value(attrs, field_name)
                for field_name in _RELATED_FIELD_LABELS
            }
            for field_name, related_object in related_objects.items():
                self._validate_related_object(
                    errors,
                    field_name,
                    _RELATED_FIELD_LABELS[field_name],
                    related_object,
                    workspace,
                    campaign,
                )

            self._validate_related_compatibility(
                errors,
                action_type,
                related_objects,
            )

            self._validate_duplicate(
                errors,
                workspace,
                campaign,
                recommendation_ref,
                action_type,
                status,
            )

        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class DismissCampaignActionSerializer(serializers.Serializer):
    """Payload for the semantic dismiss operation."""

    dismiss_reason = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )
