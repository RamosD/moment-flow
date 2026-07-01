"""Service helpers for the campaigns domain."""

from django.utils.text import slugify


def generate_unique_slug(model, workspace, value: str) -> str:
    """Return a slug derived from ``value`` unique within ``workspace``.

    Checks against ``all_objects`` so soft-deleted rows don't collide with the
    ``(workspace, slug)`` database constraint.
    """
    base = slugify(value) or "campaign"
    slug = base
    counter = 2
    while model.all_objects.filter(workspace=workspace, slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug
