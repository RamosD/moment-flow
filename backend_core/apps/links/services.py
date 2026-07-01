"""Service helpers for the smart links domain."""

from django.utils.text import slugify


def generate_unique_slug(model, value: str) -> str:
    """Return a globally-unique slug for ``value``.

    Smart link slugs must be globally unique because the public URL
    (``/l/<slug>/``) carries no workspace context. Checked against ``all_objects``
    so soft-deleted links don't free up a slug that still occupies the DB
    constraint.
    """
    base = slugify(value) or "link"
    slug = base
    counter = 2
    while model.all_objects.filter(slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug
