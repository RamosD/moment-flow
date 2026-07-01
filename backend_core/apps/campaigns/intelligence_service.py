"""Domain service: campaign intelligence (synchronous MVP).

Orchestrates the whole synchronous flow for one campaign:

    load campaign (workspace-scoped) → build payload → call Intelligence Engine
    → normalize result

Architectural placement: this is where the policy switches live. Mirroring the
asynchronous path (where ``services._submit_job`` honours ``EXTERNAL_JOBS_*``),
the synchronous switches ``INTELLIGENCE_ENGINE_ENABLED`` / ``INTELLIGENCE_ENGINE_
DRY_RUN`` are honoured **here**, not in the client (which stays a pure transport
layer) nor in the builder (which stays a pure adapter).

MVP scope (contract §10/§11): real-time response, **no snapshot persistence**, no
``ExternalJobReference``, no callbacks. The engine never persists; the Backend
Core stamps ``generated_at`` and returns the result inline.

Errors are mapped to a small set of typed service exceptions so the API layer
(BC-IE-006) can translate them to safe HTTP responses without leaking internals.
The internal token is never handled or logged here.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field

from django.conf import settings
from django.utils import timezone

from apps.integrations_bridge.intelligence_sync import (
    IntelligenceEngineProtocolError,
    IntelligenceEngineResponseError,
    IntelligenceEngineTimeout,
    IntelligenceEngineUnavailable,
    build_intelligence_engine_client,
)

from .intelligence_payload import build_campaign_intelligence_payload
from .models import Campaign

logger = logging.getLogger("campaigns.intelligence")

ENGINE_SOURCE = "engine"
DRY_RUN_SOURCE = "dry_run"


# --------------------------------------------------------------------------- #
# Typed service errors (mapped to HTTP by the API layer, BC-IE-006)
# --------------------------------------------------------------------------- #
class CampaignIntelligenceError(Exception):
    """Base class for campaign-intelligence service failures."""


class CampaignNotFoundError(CampaignIntelligenceError):
    """The campaign does not exist in the given workspace (or was deleted).

    Cross-workspace access collapses into this (never leaks existence) → 404.
    """


class IntelligenceDisabledError(CampaignIntelligenceError):
    """``INTELLIGENCE_ENGINE_ENABLED`` is False — the feature is turned off → 503."""


class IntelligenceUnavailableError(CampaignIntelligenceError):
    """Transient engine failure: timeout, unreachable or 5xx → 503 (retryable)."""


class IntelligenceUpstreamError(CampaignIntelligenceError):
    """Non-retryable engine failure: 4xx (token/payload/route) or bad body → 502.

    This signals a configuration/contract problem on our side or the engine's,
    not a problem with the end user's request, so it must not surface as a 4xx.
    """


# --------------------------------------------------------------------------- #
# Outcome
# --------------------------------------------------------------------------- #
@dataclass
class CampaignIntelligenceOutcome:
    """Normalized, JSON-safe result returned to the API layer.

    ``source`` is ``engine`` for a real call or ``dry_run`` for the stub.
    ``generated_at`` is stamped by the Backend Core (the engine returns ``null``
    by design — contract §8.1).
    """

    status: str
    source: str
    request_id: str
    workspace_id: str
    campaign_id: str
    result: dict
    engine: str = ""
    engine_version: str = ""
    explanations: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    generated_at: str = ""

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "source": self.source,
            "engine": self.engine,
            "engine_version": self.engine_version,
            "request_id": self.request_id,
            "workspace_id": self.workspace_id,
            "campaign_id": self.campaign_id,
            "result": self.result,
            "explanations": self.explanations,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "generated_at": self.generated_at,
        }


# Deterministic stub returned in dry-run (documented, no engine call).
def _dry_run_result() -> dict:
    return {
        "analysis": {},
        "scores": {},
        "grade": "unknown",
        "moments": [],
        "recommendations": [],
        "summary": "Dry-run: Intelligence Engine was not called.",
    }


class CampaignIntelligenceService:
    """Run the synchronous campaign-intelligence flow.

    ``campaign`` or ``campaign_id`` identifies the target; either way the campaign
    is (re)loaded scoped to ``workspace`` (with ``select_related`` for artist/
    track) so isolation is always enforced. ``client`` is injectable for tests;
    by default it is built from settings.
    """

    def __init__(
        self,
        *,
        workspace,
        campaign=None,
        campaign_id=None,
        request_id=None,
        reference_date=None,
        requested_by=None,
        client=None,
    ):
        self.workspace = workspace
        self._campaign_id = campaign_id or (campaign.id if campaign is not None else None)
        self.request_id = request_id or uuid.uuid4().hex
        self.reference_date = reference_date
        self.requested_by = requested_by
        self._client = client

    # ------------------------------------------------------------------- run #
    def run(self) -> CampaignIntelligenceOutcome:
        campaign = self._load_campaign()

        if not settings.INTELLIGENCE_ENGINE_ENABLED:
            self._log("disabled", campaign, level=logging.WARNING)
            raise IntelligenceDisabledError("Intelligence Engine is disabled.")

        payload = build_campaign_intelligence_payload(
            campaign=campaign,
            workspace=self.workspace,
            request_id=self.request_id,
            reference_date=self.reference_date,
        )

        if settings.INTELLIGENCE_ENGINE_DRY_RUN:
            self._log("dry_run", campaign)
            return self._dry_run_outcome(campaign)

        return self._call_engine(campaign, payload)

    # -------------------------------------------------------------- internals #
    def _load_campaign(self) -> Campaign:
        if self._campaign_id is None:
            raise ValueError("Either 'campaign' or 'campaign_id' must be provided.")
        campaign = (
            Campaign.objects.filter(workspace=self.workspace, id=self._campaign_id)
            .select_related("artist", "track")
            .first()
        )
        if campaign is None:
            logger.warning(
                "intelligence campaign_not_found request_id=%s workspace_id=%s campaign_id=%s",
                self.request_id, self.workspace.id, self._campaign_id,
            )
            raise CampaignNotFoundError("Campaign not found in this workspace.")
        return campaign

    def _call_engine(self, campaign, payload) -> CampaignIntelligenceOutcome:
        client = self._client or build_intelligence_engine_client()
        started = time.monotonic()

        def elapsed_ms():
            return int((time.monotonic() - started) * 1000)

        try:
            result = client.post_campaign_intelligence(
                payload, workspace_id=str(self.workspace.id), request_id=self.request_id
            )
        except (IntelligenceEngineTimeout, IntelligenceEngineUnavailable) as exc:
            self._log(
                "unavailable", campaign, level=logging.WARNING,
                error_type=type(exc).__name__, duration_ms=elapsed_ms(),
            )
            raise IntelligenceUnavailableError(
                "Intelligence Engine is temporarily unavailable."
            ) from exc
        except IntelligenceEngineResponseError as exc:
            if exc.is_server_error:
                self._log(
                    "server_error", campaign, level=logging.WARNING,
                    status=exc.status_code, error_code=exc.error_code,
                    duration_ms=elapsed_ms(),
                )
                raise IntelligenceUnavailableError(
                    "Intelligence Engine returned a server error."
                ) from exc
            self._log(
                "upstream_error", campaign, level=logging.ERROR,
                status=exc.status_code, error_code=exc.error_code,
                duration_ms=elapsed_ms(),
            )
            raise IntelligenceUpstreamError(
                "Intelligence Engine rejected the request."
            ) from exc
        except IntelligenceEngineProtocolError as exc:
            self._log(
                "protocol_error", campaign, level=logging.ERROR,
                error_type=type(exc).__name__, duration_ms=elapsed_ms(),
            )
            raise IntelligenceUpstreamError(
                "Intelligence Engine returned an unusable response."
            ) from exc

        self._log("ok", campaign, status=result.status, duration_ms=elapsed_ms())
        return CampaignIntelligenceOutcome(
            status=result.status,
            source=ENGINE_SOURCE,
            request_id=self.request_id,
            workspace_id=str(self.workspace.id),
            campaign_id=str(campaign.id),
            result=result.result,
            engine=result.engine,
            engine_version=result.engine_version,
            explanations=result.explanations,
            warnings=result.warnings,
            metadata=result.metadata,
            generated_at=timezone.now().isoformat(),
        )

    def _dry_run_outcome(self, campaign) -> CampaignIntelligenceOutcome:
        return CampaignIntelligenceOutcome(
            status="completed",
            source=DRY_RUN_SOURCE,
            request_id=self.request_id,
            workspace_id=str(self.workspace.id),
            campaign_id=str(campaign.id),
            result=_dry_run_result(),
            engine="",
            engine_version="",
            explanations=[],
            warnings=[
                {
                    "code": "dry_run",
                    "message": "INTELLIGENCE_ENGINE_DRY_RUN is enabled; no real call was made.",
                }
            ],
            metadata={"dry_run": True},
            generated_at=timezone.now().isoformat(),
        )

    def _log(self, event, campaign, *, level=logging.INFO, **extra):
        """Token-free structured log line with domain context."""
        fields = {
            "event": event,
            "request_id": self.request_id,
            "workspace_id": self.workspace.id,
            "campaign_id": campaign.id,
            **extra,
        }
        logger.log(level, "intelligence " + " ".join(f"{k}={v}" for k, v in fields.items()))


def get_campaign_intelligence(
    *,
    workspace,
    campaign=None,
    campaign_id=None,
    request_id=None,
    reference_date=None,
    requested_by=None,
    client=None,
) -> CampaignIntelligenceOutcome:
    """Convenience wrapper around :class:`CampaignIntelligenceService`."""
    return CampaignIntelligenceService(
        workspace=workspace,
        campaign=campaign,
        campaign_id=campaign_id,
        request_id=request_id,
        reference_date=reference_date,
        requested_by=requested_by,
        client=client,
    ).run()
