"""Builder for the Intelligence Engine campaign data bundle.

Assembles the request envelope the FastAPI Intelligence Engine expects for
``POST /intelligence/campaign`` from the Backend Core's real models. This is a
pure *adapter*: it reads product data and produces a JSON-safe ``dict``. It does
**not** call the engine (that is the client, BC-IE-003 / the service, BC-IE-005)
and never touches the renderer.

Shape follows the integration contract §7. The engine's ``data`` block is
permissive (``extra="allow"``), so enriching it later does not break the
contract; the *top-level* envelope is strict, so only the documented keys are
emitted there.

Performance: each related collection is fetched with a single ``.values()``
query (no per-row queries) and click stats use one aggregate query, so the
builder issues a bounded, constant number of queries (no N+1). Callers may
``select_related("artist", "track")`` on the campaign to save two FK lookups.
"""

import uuid
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

PAYLOAD_VERSION = "1.0"
ENTITY_TYPE = "campaign"
# Upper bound on list sizes so the payload stays bounded for busy campaigns.
MAX_ITEMS = 50


class WorkspaceMismatchError(Exception):
    """Raised when the campaign does not belong to the given workspace."""


# --------------------------------------------------------------------------- #
# JSON-safe helpers
# --------------------------------------------------------------------------- #
def _iso(value):
    """Serialize a date/datetime to ISO 8601, or ``None``."""
    return value.isoformat() if value is not None else None


def _id(value):
    """Serialize a UUID (or any id) to ``str``, or ``None``."""
    return str(value) if value is not None else None


def _num(value):
    """Serialize a Decimal/number to ``float``, or ``None``."""
    return float(value) if value is not None else None


def _date_only(value):
    """Serialize a date/datetime to a plain ISO *date* (no time), or ``None``.

    The engine's contract types ``content_outputs[].created_at`` as a ``date``
    (it only needs day-level granularity for windowing), but the source field
    is a ``DateTimeField``. Truncate instead of emitting a full datetime, which
    the engine's schema rejects (422 ``date_from_datetime_inexact``).
    """
    if value is None:
        return None
    if hasattr(value, "date"):
        value = value.date()
    return value.isoformat()


class CampaignIntelligencePayloadBuilder:
    """Build the ``/intelligence/campaign`` request envelope for one campaign.

    ``reference_date`` anchors the temporal click windows and is echoed in
    ``context.reference_date`` (defaults to today, UTC). ``request_id`` is
    generated when not supplied. The campaign/workspace ownership is validated up
    front (``WorkspaceMismatchError``).
    """

    def __init__(self, *, campaign, workspace, request_id=None, reference_date=None):
        if campaign.workspace_id != workspace.id:
            raise WorkspaceMismatchError(
                "Campaign does not belong to the given workspace."
            )
        self.campaign = campaign
        self.workspace = workspace
        self.request_id = request_id or uuid.uuid4().hex
        self.reference_date = reference_date or timezone.now().date()

    # ----------------------------------------------------------------- build #
    def build(self) -> dict:
        reports = self._reports()
        return {
            "payload_version": PAYLOAD_VERSION,
            "workspace_id": _id(self.workspace.id),
            "request_id": self.request_id,
            "entity": {"type": ENTITY_TYPE, "id": _id(self.campaign.id)},
            "context": {"reference_date": self.reference_date.isoformat()},
            "data": {
                "campaign": self._campaign(),
                "artist": self._artist(),
                "track": self._track(),
                "smart_link_stats": self._smart_link_stats(),
                "content_outputs": self._content_outputs(),
                # ``previous_reports`` is the canonical key the engine reads
                # (contract §7.1). ``reports`` is kept as an alias so consumers
                # that follow the backlog's wording (§7.3) also find the data.
                "previous_reports": reports,
                "reports": reports,
                "media_kits": self._media_kits(),
                "goals": self._goals(),
            },
        }

    # --------------------------------------------------------------- sections #
    def _campaign(self) -> dict:
        c = self.campaign
        return {
            "id": _id(c.id),
            "name": c.name,
            "campaign_type": c.campaign_type,
            "status": c.status,
            "start_date": _iso(c.start_date),
            "end_date": _iso(c.end_date),
            "primary_goal": c.primary_goal,
        }

    def _artist(self):
        artist = self.campaign.artist
        if artist is None:
            return None
        return {
            "id": _id(artist.id),
            "name": artist.name,
            "primary_genre": artist.primary_genre,
            "status": artist.status,
        }

    def _track(self):
        track = self.campaign.track
        if track is None:
            return None
        return {
            "id": _id(track.id),
            "title": track.title,
            "release_date": _iso(track.release_date),
            "track_type": track.track_type,
            "status": track.status,
        }

    def _smart_link_stats(self) -> dict:
        from apps.links.models import SmartLink, SmartLinkClick

        ref = self.reference_date
        window_7 = ref - timedelta(days=7)
        window_30 = ref - timedelta(days=30)

        # One aggregate query: lifetime total + two date-bounded windows.
        clicks = SmartLinkClick.objects.filter(
            workspace=self.workspace, campaign=self.campaign
        ).aggregate(
            total=Count("id"),
            last_7=Count(
                "id",
                filter=Q(clicked_at__date__gte=window_7, clicked_at__date__lte=ref),
            ),
            last_30=Count(
                "id",
                filter=Q(clicked_at__date__gte=window_30, clicked_at__date__lte=ref),
            ),
        )
        # One count query: active (non-soft-deleted) links for the campaign.
        active_links = SmartLink.objects.filter(
            workspace=self.workspace,
            campaign=self.campaign,
            status=SmartLink.Status.ACTIVE,
        ).count()

        return {
            "total_clicks": clicks["total"] or 0,
            "clicks_last_7_days": clicks["last_7"] or 0,
            "clicks_last_30_days": clicks["last_30"] or 0,
            "active_links": active_links,
        }

    def _content_outputs(self) -> list:
        from apps.content.models import ContentOutput

        rows = (
            ContentOutput.objects.filter(
                workspace=self.workspace, campaign=self.campaign
            )
            .order_by("-created_at")
            .values("id", "output_type", "status", "created_at")[:MAX_ITEMS]
        )
        return [
            {
                "id": _id(r["id"]),
                "output_type": r["output_type"],
                "status": r["status"],
                "created_at": _date_only(r["created_at"]),
            }
            for r in rows
        ]

    def _reports(self) -> list:
        from apps.reports.models import Report

        rows = (
            Report.objects.filter(workspace=self.workspace, campaign=self.campaign)
            .order_by("-created_at")
            .values("id", "report_type", "status", "period_end")[:MAX_ITEMS]
        )
        return [
            {
                "id": _id(r["id"]),
                "report_type": r["report_type"],
                "status": r["status"],
                "period_end": _iso(r["period_end"]),
            }
            for r in rows
        ]

    def _media_kits(self) -> list:
        from apps.reports.models import MediaKit

        rows = (
            MediaKit.objects.filter(workspace=self.workspace, campaign=self.campaign)
            .order_by("-created_at")
            .values("id", "status")[:MAX_ITEMS]
        )
        return [{"id": _id(r["id"]), "status": r["status"]} for r in rows]

    def _goals(self) -> list:
        rows = (
            self.campaign.goals.filter(workspace=self.workspace)
            .order_by("-created_at")
            .values(
                "goal_type", "status", "target_value", "current_value", "unit", "deadline"
            )[:MAX_ITEMS]
        )
        return [
            {
                "goal_type": r["goal_type"],
                "status": r["status"],
                "target_value": _num(r["target_value"]),
                "current_value": _num(r["current_value"]),
                "unit": r["unit"],
                "deadline": _iso(r["deadline"]),
            }
            for r in rows
        ]


def build_campaign_intelligence_payload(
    *, campaign, workspace, request_id=None, reference_date=None
) -> dict:
    """Convenience wrapper around :class:`CampaignIntelligencePayloadBuilder`."""
    return CampaignIntelligencePayloadBuilder(
        campaign=campaign,
        workspace=workspace,
        request_id=request_id,
        reference_date=reference_date,
    ).build()
