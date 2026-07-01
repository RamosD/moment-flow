"""Synchronous client for the FastAPI Intelligence Engine (``/intelligence/campaign``).

The Intelligence Engine MVP is **synchronous**: the Backend Core POSTs a campaign
data bundle and the engine returns the full diagnostic (analysis, scores,
moments, recommendations, summary) inline in the HTTP response. This is the
sync-first path described in the integration contract §3/§10 — it does **not**
use ``ExternalJobReference``, ``/jobs/`` or callbacks (that asynchronous
scaffolding stays untouched for future heavy work).

Design:
  - Transport is **reused** from :class:`InternalServiceClient` (same urllib JSON
    client, same mandatory internal headers, same token-free logging). This
    wrapper only adds the *named endpoint*, the IE response-envelope
    normalization, and IE-specific typed errors.
  - The token travels only in the ``X-Internal-Token`` header (handled by the
    inner client) and is **never logged** nor included in exception messages.
  - ``INTELLIGENCE_ENGINE_ENABLED`` / ``INTELLIGENCE_ENGINE_DRY_RUN`` are **not**
    consulted here: following the project pattern (the async ``EXTERNAL_JOBS_*``
    switches are honoured in ``services._submit_job``, not in ``clients``), those
    policy switches belong to the domain service (BC-IE-005). This client is a
    pure transport + normalization layer.
"""

import json
import logging
import time
from dataclasses import dataclass, field

from django.conf import settings

from .clients import (
    InternalClientTimeout,
    InternalHTTPError,
    InternalServiceClient,
    InternalServiceUnavailable,
    InvalidJSONResponse,
)

logger = logging.getLogger("integrations_bridge.intelligence")

# Named synchronous endpoint on the Intelligence Engine (integration contract §4).
CAMPAIGN_INTELLIGENCE_PATH = "/intelligence/campaign"

# The only ``status`` the engine returns on a successful (200) response — even an
# "insufficient data" result is ``completed`` with warnings (contract §8.1).
COMPLETED_STATUS = "completed"


# --------------------------------------------------------------------------- #
# Typed errors
# --------------------------------------------------------------------------- #
class IntelligenceEngineError(Exception):
    """Base class for all Intelligence Engine (sync) client failures."""


class IntelligenceEngineTimeout(IntelligenceEngineError):
    """The engine did not respond within the configured timeout (retryable)."""


class IntelligenceEngineUnavailable(IntelligenceEngineError):
    """The engine could not be reached / is not configured (retryable)."""


class IntelligenceEngineProtocolError(IntelligenceEngineError):
    """The engine responded but the body is unusable.

    Covers invalid JSON, a non-object body, or a 200 with an unexpected
    ``status`` (anything other than ``completed``). Not retryable — investigate.
    """


class IntelligenceEngineResponseError(IntelligenceEngineError):
    """The engine returned a normalized error envelope (non-2xx).

    Carries the HTTP ``status_code`` and the engine's ``error_code`` so the
    caller can decide how to map/retry. ``is_client_error`` (4xx) must **not** be
    retried; ``is_server_error`` (5xx) may be retried cautiously (contract §9.2).
    The raw response body is never stored, to avoid leaking anything sensitive.
    """

    def __init__(self, status_code, error_code="", message=""):
        self.status_code = int(status_code)
        self.error_code = error_code or "http_error"
        # A short, safe message — the engine never returns a stack trace in the
        # body (contract §8.2) and the token only travels in headers.
        super().__init__(
            message
            or f"Intelligence Engine returned HTTP {self.status_code} ({self.error_code})."
        )

    @property
    def is_client_error(self) -> bool:
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        return 500 <= self.status_code < 600


# --------------------------------------------------------------------------- #
# Normalized successful result
# --------------------------------------------------------------------------- #
@dataclass
class IntelligenceResult:
    """A normalized successful response from ``POST /intelligence/campaign``.

    ``result`` is the engine's ``{analysis, scores, grade, moments,
    recommendations, summary}`` block; ``raw`` keeps the full envelope for
    forward compatibility. ``metadata.generated_at`` is ``null`` by design on the
    engine side — timestamping is the Backend Core's responsibility (the domain
    service stamps it).
    """

    status: str
    engine: str
    engine_version: str
    request_id: str
    workspace_id: str
    result: dict
    explanations: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_envelope(cls, data: dict) -> "IntelligenceResult":
        return cls(
            status=data.get("status", ""),
            engine=data.get("engine", ""),
            engine_version=data.get("engine_version", ""),
            request_id=data.get("request_id", ""),
            workspace_id=data.get("workspace_id", ""),
            result=data.get("result") or {},
            explanations=data.get("explanations") or [],
            warnings=data.get("warnings") or [],
            metadata=data.get("metadata") or {},
            raw=data,
        )


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #
class IntelligenceEngineClient:
    """Small synchronous client for the Intelligence Engine.

    Wraps :class:`InternalServiceClient` for transport and adds the named
    endpoint + response normalization. ``opener`` is forwarded to the inner
    client so tests can inject a fake transport (no real HTTP).
    """

    def __init__(
        self,
        base_url,
        timeout,
        *,
        internal_token=None,
        opener=None,
        max_retries=0,
        retry_backoff=0.0,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = int(timeout)
        # Retries apply only to transient failures; never to 4xx / unusable bodies.
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff = max(0.0, float(retry_backoff))
        self._client = InternalServiceClient(
            self.base_url,
            self.timeout,
            internal_token=internal_token,
            opener=opener,
        )

    def post_campaign_intelligence(
        self, payload, *, workspace_id, request_id
    ) -> IntelligenceResult:
        """POST a campaign data bundle and return the normalized result.

        ``payload`` is the already-built request envelope (the payload builder is
        a separate concern — BC-IE-004). Sends the mandatory internal headers
        (``X-Internal-Token``, ``X-Workspace-ID``, ``X-Request-ID``; ``X-Job-ID``
        is empty/ignored on the sync path) and applies the configured timeout.

        Transient failures (timeout, unreachable, 5xx) are retried up to
        ``max_retries`` times with a short linear backoff; 4xx and unusable
        bodies are raised immediately (never retried). Raises a typed
        :class:`IntelligenceEngineError` subclass. The token never appears in logs
        or error messages.
        """
        if not self.base_url:
            # No URL configured: treat as unavailable (the domain service should
            # normally gate this via INTELLIGENCE_ENGINE_ENABLED before calling).
            logger.warning(
                "intelligence_call unavailable request_id=%s workspace_id=%s reason=no_base_url",
                request_id, workspace_id,
            )
            raise IntelligenceEngineUnavailable("Intelligence Engine base URL is not configured.")

        attempts = self.max_retries + 1
        last_exc = None
        for attempt in range(1, attempts + 1):
            try:
                return self._attempt(
                    payload, workspace_id=workspace_id, request_id=request_id
                )
            except (IntelligenceEngineTimeout, IntelligenceEngineUnavailable) as exc:
                last_exc = exc  # transient → retryable
            except IntelligenceEngineResponseError as exc:
                if not exc.is_server_error:
                    raise  # 4xx (403/404/422) → contract/config error, never retry
                last_exc = exc  # 5xx → transient, retryable
            # IntelligenceEngineProtocolError is intentionally NOT caught here:
            # an unusable body is deterministic, so it propagates without retry.

            if attempt < attempts:
                logger.warning(
                    "intelligence_call retry request_id=%s workspace_id=%s "
                    "attempt=%s of=%s reason=%s",
                    request_id, workspace_id, attempt, attempts,
                    type(last_exc).__name__,
                )
                if self.retry_backoff:
                    time.sleep(self.retry_backoff * attempt)

        raise last_exc

    def _attempt(self, payload, *, workspace_id, request_id) -> IntelligenceResult:
        """A single POST attempt: transport + normalization (no retry)."""
        logger.info(
            "intelligence_call start request_id=%s workspace_id=%s",
            request_id, workspace_id,
        )

        try:
            response = self._client.post_json(
                CAMPAIGN_INTELLIGENCE_PATH,
                payload,
                workspace_id=workspace_id,
                job_id=None,
                request_id=request_id,
            )
        except InternalClientTimeout as exc:
            logger.warning(
                "intelligence_call timeout request_id=%s workspace_id=%s",
                request_id, workspace_id,
            )
            raise IntelligenceEngineTimeout("Intelligence Engine timed out.") from exc
        except InternalServiceUnavailable as exc:
            logger.warning(
                "intelligence_call unavailable request_id=%s workspace_id=%s",
                request_id, workspace_id,
            )
            raise IntelligenceEngineUnavailable(
                "Intelligence Engine is unavailable."
            ) from exc
        except InternalHTTPError as exc:
            error_code, message = self._parse_error_body(exc.body)
            logger.warning(
                "intelligence_call http_error request_id=%s workspace_id=%s "
                "status=%s error_code=%s",
                request_id, workspace_id, exc.status_code, error_code,
            )
            raise IntelligenceEngineResponseError(
                exc.status_code, error_code=error_code, message=message
            ) from exc
        except InvalidJSONResponse as exc:
            logger.warning(
                "intelligence_call invalid_json request_id=%s workspace_id=%s",
                request_id, workspace_id,
            )
            raise IntelligenceEngineProtocolError(
                "Intelligence Engine returned invalid JSON."
            ) from exc

        data = response.data
        if not isinstance(data, dict):
            logger.warning(
                "intelligence_call bad_body request_id=%s workspace_id=%s",
                request_id, workspace_id,
            )
            raise IntelligenceEngineProtocolError(
                "Intelligence Engine returned a non-object body."
            )

        status = data.get("status")
        if status != COMPLETED_STATUS:
            logger.warning(
                "intelligence_call unexpected_status request_id=%s workspace_id=%s status=%s",
                request_id, workspace_id, status,
            )
            raise IntelligenceEngineProtocolError(
                f"Intelligence Engine returned unexpected status '{status}'."
            )

        logger.info(
            "intelligence_call ok request_id=%s workspace_id=%s status=%s",
            request_id, workspace_id, status,
        )
        return IntelligenceResult.from_envelope(data)

    @staticmethod
    def _parse_error_body(body):
        """Extract ``(error_code, message)`` from the engine's error envelope.

        The engine returns ``{"status":"failed","error":{"code","message",...}}``
        (contract §8.2). Best-effort: never raises, never returns secrets, never
        echoes the raw body.
        """
        if not body:
            return "", ""
        try:
            parsed = json.loads(body)
        except (ValueError, TypeError):
            return "", ""
        if not isinstance(parsed, dict):
            return "", ""
        error = parsed.get("error")
        if not isinstance(error, dict):
            return "", ""
        code = error.get("code") or ""
        message = error.get("message") or ""
        return str(code), str(message)


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #
def build_intelligence_engine_client(*, opener=None) -> IntelligenceEngineClient:
    """Build a client from settings.

    Reads ``INTELLIGENCE_ENGINE_BASE_URL``, ``INTELLIGENCE_ENGINE_TIMEOUT_SECONDS``,
    ``INTELLIGENCE_ENGINE_INTERNAL_TOKEN`` (which itself defaults to the shared
    ``INTERNAL_API_TOKEN``) and the retry policy
    (``INTELLIGENCE_ENGINE_MAX_RETRIES`` / ``..._RETRY_BACKOFF_SECONDS``).
    ``opener`` is for tests only.
    """
    return IntelligenceEngineClient(
        settings.INTELLIGENCE_ENGINE_BASE_URL,
        settings.INTELLIGENCE_ENGINE_TIMEOUT_SECONDS,
        internal_token=settings.INTELLIGENCE_ENGINE_INTERNAL_TOKEN,
        opener=opener,
        max_retries=settings.INTELLIGENCE_ENGINE_MAX_RETRIES,
        retry_backoff=settings.INTELLIGENCE_ENGINE_RETRY_BACKOFF_SECONDS,
    )
