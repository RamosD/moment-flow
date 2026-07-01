"""Seed system templates and starter content packs (idempotent)."""

from django.core.management.base import BaseCommand

from apps.content.seeds import seed_content


class Command(BaseCommand):
    help = "Create or update system templates and starter content packs (idempotent)."

    def handle(self, *args, **options):
        result = seed_content()
        self.stdout.write(
            self.style.SUCCESS(
                f"Content seeded: {result['templates']} templates, "
                f"{result['packs']} packs."
            )
        )
