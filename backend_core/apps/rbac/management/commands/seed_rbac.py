"""Seed system roles and base permissions (idempotent)."""

from django.core.management.base import BaseCommand

from apps.rbac.seeds import seed_rbac


class Command(BaseCommand):
    help = "Create or update system roles and base permissions (idempotent)."

    def handle(self, *args, **options):
        result = seed_rbac()
        self.stdout.write(
            self.style.SUCCESS(
                "RBAC seeded: "
                f"{result['permissions']} permissions, "
                f"{result['roles']} roles "
                f"({result['roles_created']} created)."
            )
        )
