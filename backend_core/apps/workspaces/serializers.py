"""Serializers for Workspace and WorkspaceMember."""

from rest_framework import serializers

from .models import Workspace, WorkspaceMember


class WorkspaceSerializer(serializers.ModelSerializer):
    """Read/create representation of a workspace.

    ``slug``, ``created_by`` and ``status`` are managed by the server. The slug
    is auto-generated from the name.
    """

    class Meta:
        model = Workspace
        fields = (
            "id",
            "name",
            "slug",
            "workspace_type",
            "country",
            "market",
            "default_language",
            "timezone",
            "status",
            "created_by",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        )


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    """Representation of a workspace membership."""

    class Meta:
        model = WorkspaceMember
        fields = (
            "id",
            "workspace",
            "user",
            "role",
            "role_key",
            "status",
            "invited_by",
            "joined_at",
            "created_at",
            "updated_at",
        )
        # ``workspace`` is taken from the X-Workspace-ID context and ``role`` is
        # resolved server-side from ``role_key``.
        read_only_fields = (
            "id",
            "workspace",
            "role",
            "invited_by",
            "joined_at",
            "created_at",
            "updated_at",
        )
