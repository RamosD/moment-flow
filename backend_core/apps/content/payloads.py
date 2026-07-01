"""Builders for external-renderer payloads (content generation).

``build_content_generation_payload`` produces the **domain** payload for a
``ContentPackRequest``. It is passed as the ``payload`` of
``create_and_submit_external_job``; the integrations-bridge envelope then wraps it
with the transport fields (``job_id``, ``request_id``, ``workspace_id``,
``callback_url``, ``entity``, ``payload_version``). The full contract sent to the
Content Renderer therefore contains every field the renderer needs.

No rendering happens here. No secrets, tokens or private data are included — only
the product context the renderer needs to generate outputs.
"""

from django.conf import settings

from .models import Template, TemplateVersion

PAYLOAD_VERSION = "1.0"


def _iso(value):
    return value.isoformat() if value is not None else None


def _campaign_block(campaign) -> dict:
    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "slug": campaign.slug,
        "campaign_type": campaign.campaign_type,
        "status": campaign.status,
        "primary_goal": campaign.primary_goal,
        "start_date": _iso(campaign.start_date),
        "end_date": _iso(campaign.end_date),
    }


def _artist_block(artist) -> dict | None:
    if artist is None:
        return None
    return {
        "id": str(artist.id),
        "name": artist.name,
        "slug": artist.slug,
        "primary_genre": artist.primary_genre,
        "country": artist.country,
        "language": artist.language,
    }


def _track_block(track) -> dict | None:
    if track is None:
        return None
    return {
        "id": str(track.id),
        "title": track.title,
        "slug": track.slug,
        "track_type": track.track_type,
        "release_date": _iso(track.release_date),
    }


def _pack_block(pack) -> dict:
    return {
        "id": str(pack.id),
        "pack_key": pack.pack_key,
        "name": pack.name,
        "pack_type": pack.pack_type,
    }


def _templates_and_outputs(pack):
    """Return (templates, expected_outputs) for the pack's active templates."""
    templates, expected_outputs = [], []
    pack_templates = (
        pack.pack_templates.select_related("template")
        .all()
        .order_by("sort_order", "created_at")
    )
    for pt in pack_templates:
        tmpl = pt.template
        if tmpl.status != Template.Status.ACTIVE:
            continue
        active_version = (
            tmpl.versions.filter(status=TemplateVersion.Status.ACTIVE)
            .order_by("-created_at")
            .first()
        )
        templates.append(
            {
                "template_key": tmpl.template_key,
                "template_type": tmpl.template_type,
                "output_type": pt.output_type,
                "format": pt.format,
                "required": pt.required,
                "sort_order": pt.sort_order,
                "renderer_type": active_version.renderer_type if active_version else None,
                "template_version": active_version.version if active_version else None,
            }
        )
        expected_outputs.append(
            {
                "output_type": pt.output_type,
                "format": pt.format,
                "required": pt.required,
            }
        )
    return templates, expected_outputs


def _branding_block(workspace) -> dict:
    """Best-effort, non-sensitive branding (WorkspaceBranding does not exist yet)."""
    branding = {"workspace_name": workspace.name}
    declared = (workspace.metadata or {}).get("branding")
    if isinstance(declared, dict):
        # Only copy primitive, non-sensitive values.
        for key in ("primary_color", "secondary_color", "font_family", "logo_url"):
            if key in declared:
                branding[key] = declared[key]
    return branding


def _smart_link_block(workspace, campaign) -> dict | None:
    """Return the first active smart link for the campaign, if any (best-effort)."""
    try:
        from apps.links.models import SmartLink
    except ImportError:
        return None
    link = (
        SmartLink.objects.filter(
            workspace=workspace, campaign=campaign, status=SmartLink.Status.ACTIVE
        )
        .order_by("created_at")
        .first()
    )
    if link is None:
        return None
    base = (settings.BACKEND_PUBLIC_BASE_URL or "").rstrip("/")
    return {
        "id": str(link.id),
        "slug": link.slug,
        "url": f"{base}/l/{link.slug}/",
    }


def _billing_context(request) -> dict:
    """Non-sensitive billing context (no balances, no secrets)."""
    cost = (request.content_pack.metadata or {}).get("credit_cost", 0) or 0
    return {
        "credit_cost": str(cost),
        "credits_reserved": bool(cost and float(cost) > 0),
        "usage_event_id": str(request.usage_event_id) if request.usage_event_id else None,
    }


def build_content_generation_payload(request) -> dict:
    """Build the domain payload for a content_generation job from a request."""
    workspace = request.workspace
    campaign = request.campaign
    artist = request.artist or campaign.artist
    track = request.track or campaign.track
    pack = request.content_pack

    templates, expected_outputs = _templates_and_outputs(pack)

    return {
        "payload_version": PAYLOAD_VERSION,
        "entity": {"type": "content_pack_request", "id": str(request.id)},
        "workspace_id": str(workspace.id),
        "campaign": _campaign_block(campaign),
        "artist": _artist_block(artist),
        "track": _track_block(track),
        "content_pack": _pack_block(pack),
        "templates": templates,
        "expected_outputs": expected_outputs,
        "branding": _branding_block(workspace),
        "smart_link": _smart_link_block(workspace, campaign),
        "billing_context": _billing_context(request),
        "metadata": dict(request.metadata or {}),
    }
