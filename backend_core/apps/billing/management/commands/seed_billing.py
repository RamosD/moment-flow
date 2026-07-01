"""Seed initial billing plans and their features (idempotent)."""

from django.core.management.base import BaseCommand

from apps.billing.seeds import seed_billing


class Command(BaseCommand):
    help = "Create or update the initial billing plans and features (idempotent)."

    def handle(self, *args, **options):
        result = seed_billing()
        self.stdout.write(
            self.style.SUCCESS(
                f"Billing seeded: {result['plans']} plans, "
                f"{result['features']} features."
            )
        )
