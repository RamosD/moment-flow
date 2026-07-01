"""Service helpers for the catalogue domain."""

from django.utils.text import slugify


def generate_unique_slug(model, workspace, value: str) -> str:
    """Return a slug derived from ``value`` that is unique within ``workspace``.

    Uniqueness is checked against *all* rows (including soft-deleted) because the
    ``(workspace, slug)`` unique constraint applies at database level.
    """
    base = slugify(value) or "item"
    slug = base
    counter = 2
    while model.all_objects.filter(workspace=workspace, slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug
