"""Migrate WorkspaceMember.role from free text to a FK to rbac.Role.

The previous ``role`` CharField is renamed to ``role_key`` (preserving its
value), a nullable ``role`` FK to ``rbac.Role`` is added, and existing rows are
linked to the matching system role (created on the fly if missing).
"""

import django.db.models.deletion
from django.db import migrations, models


def link_roles(apps, schema_editor):
    WorkspaceMember = apps.get_model("workspaces", "WorkspaceMember")
    Role = apps.get_model("rbac", "Role")
    for member in WorkspaceMember.objects.all():
        key = member.role_key or "viewer"
        role, _ = Role.objects.get_or_create(
            workspace=None,
            key=key,
            defaults={"name": key.replace("_", " ").title(), "is_system": True},
        )
        member.role = role
        member.save(update_fields=["role"])


def unlink_roles(apps, schema_editor):
    # Reverse is a no-op: dropping the FK column is handled by the schema reverse.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workspaces", "0001_initial"),
        ("rbac", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="workspacemember",
            old_name="role",
            new_name="role_key",
        ),
        migrations.AlterField(
            model_name="workspacemember",
            name="role_key",
            field=models.CharField(
                blank=True, default="viewer", max_length=50, verbose_name="role key"
            ),
        ),
        migrations.AddField(
            model_name="workspacemember",
            name="role",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="members",
                to="rbac.role",
                verbose_name="role",
            ),
        ),
        migrations.RunPython(link_roles, unlink_roles),
    ]
