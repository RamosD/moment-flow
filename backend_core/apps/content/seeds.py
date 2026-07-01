"""Idempotent seeding of system templates and starter content packs.

Used by the ``seed_content`` management command and by tests. Re-running is safe
(upserts on the natural keys).
"""

from django.db import transaction

from .models import (
    ContentPack,
    ContentPackTemplate,
    Template,
    TemplateVersion,
)

# template_key -> (name, template_type)
TEMPLATES = {
    "system_post": ("System Post", Template.TemplateType.POST),
    "system_story": ("System Story", Template.TemplateType.STORY),
    "system_carousel": ("System Carousel", Template.TemplateType.CAROUSEL),
    "system_thumbnail": ("System Thumbnail", Template.TemplateType.THUMBNAIL),
    "system_report": ("System Report", Template.TemplateType.REPORT),
    "system_media_kit": ("System Media Kit", Template.TemplateType.MEDIA_KIT),
}

# pack_key -> (name, pack_type, [(template_key, output_type, format), ...])
PACKS = {
    "release_pack": (
        "Release Pack",
        ContentPack.PackType.RELEASE_PACK,
        [
            ("system_post", "post", "png"),
            ("system_story", "story", "png"),
            ("system_thumbnail", "thumbnail", "png"),
        ],
    ),
    "milestone_pack": (
        "Milestone Pack",
        ContentPack.PackType.MILESTONE_PACK,
        [
            ("system_post", "post", "png"),
            ("system_carousel", "carousel", "png"),
        ],
    ),
    "weekly_growth_pack": (
        "Weekly Growth Pack",
        ContentPack.PackType.WEEKLY_GROWTH_PACK,
        [
            ("system_post", "post", "png"),
            ("system_story", "story", "png"),
        ],
    ),
    "auto_media_kit": (
        "Auto Media Kit",
        ContentPack.PackType.AUTO_MEDIA_KIT,
        [
            ("system_media_kit", "media_kit", "pdf"),
            ("system_report", "report", "pdf"),
        ],
    ),
}


@transaction.atomic
def seed_content() -> dict:
    templates = {}
    for key, (name, template_type) in TEMPLATES.items():
        template, _ = Template.objects.update_or_create(
            template_key=key,
            defaults={
                "name": name,
                "template_type": template_type,
                "is_system": True,
                "status": Template.Status.ACTIVE,
                "workspace": None,
            },
        )
        TemplateVersion.objects.update_or_create(
            template=template,
            version="1.0.0",
            defaults={
                "renderer_type": TemplateVersion.RendererType.HTML_SVG,
                "manifest": {},
                "required_props": [],
                "supported_formats": ["png", "pdf"],
                "status": TemplateVersion.Status.ACTIVE,
            },
        )
        templates[key] = template

    for pack_key, (name, pack_type, items) in PACKS.items():
        pack, _ = ContentPack.objects.update_or_create(
            pack_key=pack_key,
            defaults={
                "name": name,
                "pack_type": pack_type,
                "status": ContentPack.Status.ACTIVE,
                "workspace": None,
            },
        )
        for index, (template_key, output_type, fmt) in enumerate(items):
            ContentPackTemplate.objects.update_or_create(
                content_pack=pack,
                template=templates[template_key],
                output_type=output_type,
                defaults={"format": fmt, "required": True, "sort_order": index},
            )

    return {"templates": len(TEMPLATES), "packs": len(PACKS)}
