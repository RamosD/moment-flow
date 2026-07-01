"""Builders for external-renderer payloads (report / media-kit generation).

Each builder returns the **domain** payload for an entity. It is passed as the
``payload`` of ``create_and_submit_external_job``; the integrations-bridge
envelope then wraps it with the transport fields (``job_id``, ``request_id``,
``workspace_id``, ``callback_url``, ``entity``, ``payload_version``), so the full
contract sent to the Report Renderer contains every required field.

No rendering happens here. No secrets are included — only the product context the
renderer needs.
"""

PAYLOAD_VERSION = "1.0"


def _iso(value):
    return value.isoformat() if value is not None else None


def _campaign_block(campaign):
    if campaign is None:
        return None
    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "slug": campaign.slug,
        "campaign_type": campaign.campaign_type,
        "status": campaign.status,
    }


def _artist_block(artist):
    if artist is None:
        return None
    return {
        "id": str(artist.id),
        "name": artist.name,
        "slug": artist.slug,
        "primary_genre": artist.primary_genre,
        "country": artist.country,
    }


def _track_block(track):
    if track is None:
        return None
    return {
        "id": str(track.id),
        "title": track.title,
        "slug": track.slug,
        "track_type": track.track_type,
        "release_date": _iso(track.release_date),
    }


def _branding_block(workspace):
    """Best-effort, non-sensitive branding (WorkspaceBranding does not exist yet)."""
    branding = {"workspace_name": workspace.name}
    declared = (workspace.metadata or {}).get("branding")
    if isinstance(declared, dict):
        for key in ("primary_color", "secondary_color", "font_family", "logo_url"):
            if key in declared:
                branding[key] = declared[key]
    return branding


def _smart_link_stats(workspace, campaign):
    """Basic click stats per active smart link of the campaign (best-effort)."""
    if campaign is None:
        return []
    try:
        from django.db.models import Count

        from apps.links.models import SmartLink
    except ImportError:
        return []
    links = (
        SmartLink.objects.filter(
            workspace=workspace, campaign=campaign, status=SmartLink.Status.ACTIVE
        )
        .annotate(total_clicks=Count("clicks"))
        .order_by("created_at")
    )
    return [
        {"slug": link.slug, "total_clicks": link.total_clicks} for link in links
    ]


def _active_smart_links(workspace, artist):
    """Active smart links for the artist (best-effort)."""
    if artist is None:
        return []
    try:
        from django.conf import settings

        from apps.links.models import SmartLink
    except ImportError:
        return []
    base = (settings.BACKEND_PUBLIC_BASE_URL or "").rstrip("/")
    links = SmartLink.objects.filter(
        workspace=workspace, artist=artist, status=SmartLink.Status.ACTIVE
    ).order_by("created_at")
    return [{"slug": link.slug, "url": f"{base}/l/{link.slug}/"} for link in links]


def _related_outputs(report):
    """Content outputs for the report's campaign (best-effort)."""
    if report.campaign_id is None:
        return []
    try:
        from apps.content.models import ContentOutput
    except ImportError:
        return []
    outputs = ContentOutput.objects.filter(
        workspace=report.workspace, campaign=report.campaign
    ).order_by("created_at")[:50]
    return [
        {"id": str(o.id), "output_type": o.output_type, "status": o.status}
        for o in outputs
    ]


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def _report_sections(report):
    return [
        {
            "section_key": section.section_key,
            "title": section.title,
            "sort_order": section.sort_order,
        }
        for section in report.sections.all().order_by("sort_order", "created_at")
    ]


def build_report_generation_payload(report) -> dict:
    """Build the domain payload for a ``report_generation`` job."""
    workspace = report.workspace
    return {
        "payload_version": PAYLOAD_VERSION,
        "entity": {"type": "report", "id": str(report.id)},
        "workspace_id": str(workspace.id),
        "report_type": report.report_type,
        "title": report.title,
        "period_start": _iso(report.period_start),
        "period_end": _iso(report.period_end),
        "campaign": _campaign_block(report.campaign),
        "artist": _artist_block(report.artist),
        "track": _track_block(report.track),
        "sections": _report_sections(report),
        "related_outputs": _related_outputs(report),
        "smart_link_stats": _smart_link_stats(workspace, report.campaign),
        "branding": _branding_block(workspace),
        "metadata": dict(report.metadata or {}),
    }


# --------------------------------------------------------------------------- #
# Media kit
# --------------------------------------------------------------------------- #
def _media_kit_items(media_kit):
    return [
        {
            "item_type": item.item_type,
            "title": item.title,
            "content": item.content,
            "sort_order": item.sort_order,
            "asset_id": str(item.asset_id) if item.asset_id else None,
        }
        for item in media_kit.items.all().order_by("sort_order", "created_at")
    ]


def _media_kit_assets(media_kit):
    """Collect the (non-sensitive) asset references used by the media kit."""
    assets = {}

    def _add(asset):
        if asset is None or str(asset.id) in assets:
            return
        assets[str(asset.id)] = {
            "id": str(asset.id),
            "asset_type": asset.asset_type,
            "storage_provider": asset.storage_provider,
            "storage_key": asset.storage_key,
            "file_name": asset.file_name,
            "mime_type": asset.mime_type,
        }

    _add(media_kit.storage_asset)
    if media_kit.artist_id and media_kit.artist.image_asset_id:
        _add(media_kit.artist.image_asset)
    for item in media_kit.items.select_related("asset").all():
        _add(item.asset)
    return list(assets.values())


def build_media_kit_generation_payload(media_kit) -> dict:
    """Build the domain payload for a ``media_kit_generation`` job."""
    workspace = media_kit.workspace
    return {
        "payload_version": PAYLOAD_VERSION,
        "entity": {"type": "media_kit", "id": str(media_kit.id)},
        "workspace_id": str(workspace.id),
        "title": media_kit.title,
        "artist": _artist_block(media_kit.artist),
        "campaign": _campaign_block(media_kit.campaign),
        "track": _track_block(media_kit.track),
        "items": _media_kit_items(media_kit),
        "assets": _media_kit_assets(media_kit),
        "smart_links": _active_smart_links(workspace, media_kit.artist),
        "branding": _branding_block(workspace),
        "metadata": dict(media_kit.metadata or {}),
    }
