"""Aggregated health of the Backend Core's technical dependencies (OBS-STG-003).

The Backend Core orchestrates two external technical services — the FastAPI
Intelligence Engine and the Content Renderer — plus its own database. This module
probes each one and returns a single normalized report so an operator can answer
"is everything up?" without opening the code.

Design rules (backlog OBS-STG-003 / risks OBS-RSK-002/004/005):
  - The external services expose a **public** ``GET /health`` (no auth), so the
    probe sends **no** ``X-Internal-Token`` — there is no secret to leak here.
  - A failing dependency never breaks the aggregate: every probe is wrapped and
    degrades to a per-dependency state instead of raising. The caller (view)
    always gets a report, never an unexpected 500.
  - Nothing sensitive is returned: the configured base URL is reduced to
    ``configured`` / ``not_configured`` and only safe, vocabulary-controlled
    ``detail`` strings (``timeout``, ``connection_error``, ``http_503`` …) appear.
  - The timeout is short and configurable (``HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS``)
    so the endpoint stays responsive even when a dependency hangs.
"""

import json
import logging
import socket
import time
import urllib.error
import urllib.request

from django.conf import settings
from django.db import connections
from django.utils import timezone

logger = logging.getLogger("integrations_bridge")

# Per-dependency states (backlog OBS-STG-003).
OK = "ok"
DEGRADED = "degraded"
UNAVAILABLE = "unavailable"
MISCONFIGURED = "misconfigured"
UNKNOWN = "unknown"

# Overall states (subset: ok | degraded | unavailable).
OVERALL_OK = "ok"
OVERALL_DEGRADED = "degraded"
OVERALL_UNAVAILABLE = "unavailable"

HEALTH_PATH = "/health"

# External technical dependencies probed via their public ``/health``.
# Each is ``(name, settings_attribute_with_base_url)``.
_EXTERNAL_DEPENDENCIES = (
    ("intelligence_engine", "INTELLIGENCE_ENGINE_BASE_URL"),
    ("content_renderer", "CONTENT_RENDERER_BASE_URL"),
)


def _ms(start) -> int:
    """Elapsed milliseconds since a ``time.monotonic()`` mark."""
    return int((time.monotonic() - start) * 1000)


def _default_opener(request, timeout):
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 (internal URL)


def http_health_probe(base_url, timeout, *, opener=None):
    """Probe a public ``GET <base_url>/health``.

    Returns ``(status, duration_ms, detail)`` and **never raises**. No internal
    token is sent — ``/health`` is public on both services. ``opener`` is for
    tests (a callable ``(request, timeout) -> response``); the default performs a
    real ``urlopen``.

    Mapping:
      - 2xx + JSON body ``{"status": "ok"}``        → ``ok``
      - 2xx but unexpected/invalid body             → ``degraded`` (``unexpected_body``)
      - any non-2xx HTTP response                   → ``degraded`` (``http_<code>``)
      - timeout                                     → ``unavailable`` (``timeout``)
      - connection error / DNS / down               → ``unavailable`` (``connection_error``)
      - unexpected probe error                      → ``unknown`` (``probe_error``)
    """
    url = base_url.rstrip("/") + HEALTH_PATH
    open_ = opener or _default_opener
    start = time.monotonic()
    try:
        # Deliberately NO X-Internal-Token header: /health is public.
        request = urllib.request.Request(url, method="GET")
        response = open_(request, timeout)
    except urllib.error.HTTPError as exc:
        # The service answered with a non-2xx: it is up but not healthy.
        return DEGRADED, _ms(start), f"http_{exc.code}"
    except (TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        if (
            isinstance(exc, TimeoutError)
            or isinstance(reason, (TimeoutError, socket.timeout))
        ):
            return UNAVAILABLE, _ms(start), "timeout"
        return UNAVAILABLE, _ms(start), "connection_error"
    except Exception:  # noqa: BLE001 — a probe must never raise.
        return UNKNOWN, _ms(start), "probe_error"

    duration = _ms(start)
    status_code = int(getattr(response, "status", None) or _getcode(response))
    raw = _safe_read(response)
    if not (200 <= status_code < 300):
        return DEGRADED, duration, f"http_{status_code}"
    body = _safe_json(raw)
    if isinstance(body, dict) and body.get("status") == "ok":
        return OK, duration, ""
    return DEGRADED, duration, "unexpected_body"


def _getcode(response) -> int:
    getcode = getattr(response, "getcode", None)
    return int(getcode()) if callable(getcode) else 200


def _safe_read(response) -> str:
    try:
        raw = response.read()
    except Exception:  # noqa: BLE001 — body is best-effort.
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw or "")


def _safe_json(raw):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def _check_database(alias="default"):
    """Probe the Backend Core database with a trivial ``SELECT 1``.

    Returns ``(status, duration_ms, detail)``. Never raises.
    """
    start = time.monotonic()
    try:
        connection = connections[alias]
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return OK, _ms(start), ""
    except Exception:  # noqa: BLE001 — defensive: report, never raise.
        return UNAVAILABLE, _ms(start), "connection_error"


def liveness_report() -> dict:
    """Trivial liveness signal: the process can handle a request at all.

    Deliberately checks NOTHING (no DB, no external service) — a process that
    can run this function is, by definition, alive. Never confuse this with
    readiness (below): a process can be alive while its database is down.
    """
    return {"status": OK, "service": "backend_core"}


def readiness_report() -> dict:
    """Minimal readiness signal: can this process serve real traffic?

    Checks only the database — almost every Backend Core endpoint needs it,
    so a DB outage genuinely means "not ready". The Intelligence Engine and
    the Content Renderer are deliberately EXCLUDED here: they are optional,
    per-request downstream calls (already surfaced as clear 502/503 on the
    affected endpoints, see ``apps.integrations_bridge.intelligence_sync`` and
    ``apps.integrations_bridge.services``), not a reason to mark the whole
    service "not ready". Their operational detail stays behind the
    staff-only aggregated endpoint (``check_dependencies``) — this endpoint
    is intentionally public (like the Intelligence Engine's and Content
    Renderer's own ``/health``) and exposes nothing beyond ok/not-ready.
    """
    db_status, _duration_ms, _detail = _check_database()
    return {"status": OK if db_status == OK else UNAVAILABLE, "service": "backend_core"}


def check_dependencies(*, timeout=None, prober=None, include_database=True) -> dict:
    """Probe the technical dependencies and return a normalized report.

    Never raises. Each external dependency is probed via its public ``/health``;
    a missing base URL is reported as ``misconfigured`` (the prober is not even
    called). The optional database check runs a trivial query.

    ``prober`` is injectable for tests (``(base_url, timeout) -> (status, ms,
    detail)``); it defaults to :func:`http_health_probe`. ``timeout`` defaults to
    ``settings.HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS``.

    The report shape is::

        {
          "status": "ok|degraded|unavailable",
          "service": "backend_core",
          "checked_at": "<iso>",
          "dependencies": {
            "intelligence_engine": {"status": "ok", "url": "configured", "duration_ms": 12},
            "content_renderer":    {"status": "ok", "url": "configured", "duration_ms": 18},
            "database":            {"status": "ok", "duration_ms": 1}
          }
        }
    """
    if timeout is None:
        timeout = settings.HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS
    probe = prober or http_health_probe

    dependencies: dict[str, dict] = {}
    for name, setting_name in _EXTERNAL_DEPENDENCIES:
        base_url = getattr(settings, setting_name, "") or ""
        if not base_url:
            dependencies[name] = {
                "status": MISCONFIGURED,
                "url": "not_configured",
                "duration_ms": 0,
                "detail": "base_url_not_configured",
            }
            continue
        try:
            status, duration_ms, detail = probe(base_url, timeout)
        except Exception:  # noqa: BLE001 — a failing probe must not break the aggregate.
            status, duration_ms, detail = UNKNOWN, 0, "probe_error"
        entry = {"status": status, "url": "configured", "duration_ms": duration_ms}
        if detail:
            entry["detail"] = detail
        dependencies[name] = entry

    if include_database:
        db_status, db_duration, db_detail = _check_database()
        db_entry = {"status": db_status, "duration_ms": db_duration}
        if db_detail:
            db_entry["detail"] = db_detail
        dependencies["database"] = db_entry

    report = {
        "status": _aggregate_status(dependencies),
        "service": "backend_core",
        "checked_at": timezone.now().isoformat(),
        "dependencies": dependencies,
    }
    _log_summary(report)
    return report


def _aggregate_status(dependencies) -> str:
    """Collapse per-dependency states into the overall status.

    all ok → ok · none ok → unavailable · otherwise → degraded.
    """
    statuses = [entry["status"] for entry in dependencies.values()]
    if not statuses:
        return OVERALL_OK
    healthy = [status == OK for status in statuses]
    if all(healthy):
        return OVERALL_OK
    if not any(healthy):
        return OVERALL_UNAVAILABLE
    return OVERALL_DEGRADED


def _log_summary(report) -> None:
    """One token-free, URL-free summary line (helps OBS-STG-006 correlation)."""
    parts = " ".join(
        f"{name}={entry['status']}" for name, entry in report["dependencies"].items()
    )
    logger.info("event=health_check overall=%s %s", report["status"], parts)
