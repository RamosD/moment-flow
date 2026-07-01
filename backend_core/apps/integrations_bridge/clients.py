"""Reusable internal HTTP client for calling external technical services.

Used by Django to POST job payloads to the FastAPI Intelligence Engine / Content
Renderer / Report Renderer. Built on the standard library (``urllib``) so it
introduces no new dependency.

Design notes:
  - Every request carries the mandatory internal headers (``X-Internal-Token``,
    ``X-Workspace-ID``, ``X-Job-ID``, ``X-Request-ID``, ``Content-Type``).
  - The token is **never** logged. Logging records job/request ids and status
    only.
  - All failure modes are normalized to typed exceptions: timeout, HTTP error,
    service unavailable and invalid JSON.
  - The transport is injectable (``opener``) so tests never make a real call.
"""

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger("integrations_bridge.client")

INTERNAL_TOKEN_HEADER = "X-Internal-Token"
WORKSPACE_ID_HEADER = "X-Workspace-ID"
JOB_ID_HEADER = "X-Job-ID"
REQUEST_ID_HEADER = "X-Request-ID"


class InternalClientError(Exception):
    """Base class for all internal-client failures."""


class InternalClientTimeout(InternalClientError):
    """The external service did not respond within the timeout."""


class InternalServiceUnavailable(InternalClientError):
    """The external service could not be reached (connection error / DNS / down)."""


class InternalHTTPError(InternalClientError):
    """The external service responded with a non-2xx status."""

    def __init__(self, status_code, message="", body=""):
        self.status_code = status_code
        self.body = body
        super().__init__(message or f"HTTP {status_code} from external service.")


class InvalidJSONResponse(InternalClientError):
    """The external service responded with a body that is not valid JSON."""


@dataclass
class InternalResponse:
    """A normalized successful response."""

    status_code: int
    data: dict


class InternalServiceClient:
    """Minimal JSON-over-HTTP client for a single external service.

    ``opener`` is an optional callable ``(request, timeout) -> response`` used to
    inject a fake transport in tests. The default uses ``urllib.request.urlopen``.
    """

    def __init__(self, base_url, timeout, *, internal_token=None, opener=None):
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = int(timeout)
        # Default to the configured secret; callers may override for tests.
        self._internal_token = (
            internal_token if internal_token is not None else settings.INTERNAL_API_TOKEN
        )
        self._opener = opener or self._default_opener

    @staticmethod
    def _default_opener(request, timeout):
        return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 (internal URL)

    def build_headers(self, *, workspace_id, job_id, request_id) -> dict:
        """Build the mandatory internal headers for a request."""
        return {
            INTERNAL_TOKEN_HEADER: self._internal_token or "",
            WORKSPACE_ID_HEADER: str(workspace_id) if workspace_id else "",
            JOB_ID_HEADER: str(job_id) if job_id else "",
            REQUEST_ID_HEADER: str(request_id) if request_id else "",
            "Content-Type": "application/json",
        }

    def post_json(self, path, payload, *, workspace_id, job_id, request_id) -> InternalResponse:
        """POST ``payload`` as JSON to ``base_url + path`` with internal headers.

        Returns an :class:`InternalResponse` on a 2xx with a JSON body. Raises a
        typed :class:`InternalClientError` subclass on timeout, HTTP error,
        unreachable service or invalid JSON. The token is never logged.
        """
        url = f"{self.base_url}{path if path.startswith('/') else '/' + path}"
        body = json.dumps(payload or {}).encode("utf-8")
        headers = self.build_headers(
            workspace_id=workspace_id, job_id=job_id, request_id=request_id
        )
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")

        # Tracing log — job/request ids and target only, never the token/headers.
        logger.info(
            "internal_call start job_id=%s request_id=%s url=%s",
            job_id, request_id, url,
        )

        try:
            response = self._opener(request, self.timeout)
        except urllib.error.HTTPError as exc:
            # HTTPError is a subclass of URLError — handle it first.
            error_body = self._safe_read(exc)
            logger.warning(
                "internal_call http_error job_id=%s request_id=%s status=%s",
                job_id, request_id, exc.code,
            )
            raise InternalHTTPError(exc.code, body=error_body) from exc
        except (TimeoutError, OSError) as exc:
            # socket.timeout is TimeoutError on py3.10+; URLError wraps OSError.
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError) or isinstance(exc, TimeoutError):
                logger.warning(
                    "internal_call timeout job_id=%s request_id=%s", job_id, request_id
                )
                raise InternalClientTimeout(
                    "External service timed out."
                ) from exc
            logger.warning(
                "internal_call unavailable job_id=%s request_id=%s", job_id, request_id
            )
            raise InternalServiceUnavailable(
                "External service is unavailable."
            ) from exc

        status_code = self._status_of(response)
        raw = self._safe_read(response)
        try:
            data = json.loads(raw) if raw else {}
        except (ValueError, TypeError) as exc:
            logger.warning(
                "internal_call invalid_json job_id=%s request_id=%s", job_id, request_id
            )
            raise InvalidJSONResponse("External service returned invalid JSON.") from exc

        logger.info(
            "internal_call ok job_id=%s request_id=%s status=%s",
            job_id, request_id, status_code,
        )
        return InternalResponse(status_code=status_code, data=data)

    @staticmethod
    def _status_of(response) -> int:
        status = getattr(response, "status", None)
        if status is not None:
            return int(status)
        getcode = getattr(response, "getcode", None)
        return int(getcode()) if callable(getcode) else 200

    @staticmethod
    def _safe_read(response) -> str:
        try:
            raw = response.read()
        except Exception:  # noqa: BLE001 — body is best-effort
            return ""
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="replace")
        return str(raw or "")
