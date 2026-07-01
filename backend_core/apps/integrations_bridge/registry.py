"""Service registry: resolve which external service handles a given job type.

This is a thin, configuration-driven resolver. It maps each ``job_type`` to a
*provider* (``intelligence_engine`` / ``content_renderer`` / ``report_renderer``)
and resolves that provider's ``base_url`` and ``timeout`` from settings. No HTTP
happens here — see :mod:`apps.integrations_bridge.clients`.

Architectural boundary: Django only decides *where* a job goes and *whether* to
submit it (enabled / dry-run). The external service does the actual work.
"""

from dataclasses import dataclass

from django.conf import settings

# Canonical provider identifiers. These double as the stored
# ``ExternalJobReference.provider`` values, so keep them in sync with the model's
# ``Provider`` choices.
INTELLIGENCE_ENGINE = "intelligence_engine"
CONTENT_RENDERER = "content_renderer"
REPORT_RENDERER = "report_renderer"

# Job types supported in this phase (mirrors ExternalJobReference.JobType).
CONTENT_GENERATION = "content_generation"
CONTENT_PREVIEW = "content_preview"
REPORT_GENERATION = "report_generation"
MEDIA_KIT_GENERATION = "media_kit_generation"
METRICS_COLLECTION = "metrics_collection"
MOMENT_DETECTION = "moment_detection"
INSIGHT_GENERATION = "insight_generation"
RECOMMENDATION_GENERATION = "recommendation_generation"

# job_type -> provider.
JOB_TYPE_TO_PROVIDER = {
    CONTENT_GENERATION: CONTENT_RENDERER,
    CONTENT_PREVIEW: CONTENT_RENDERER,
    REPORT_GENERATION: REPORT_RENDERER,
    MEDIA_KIT_GENERATION: REPORT_RENDERER,
    METRICS_COLLECTION: INTELLIGENCE_ENGINE,
    MOMENT_DETECTION: INTELLIGENCE_ENGINE,
    INSIGHT_GENERATION: INTELLIGENCE_ENGINE,
    RECOMMENDATION_GENERATION: INTELLIGENCE_ENGINE,
}


class UnknownJobType(Exception):
    """Raised when a job_type has no provider mapping."""


class ServiceNotConfigured(Exception):
    """Raised when a resolved provider has no base URL configured."""


@dataclass(frozen=True)
class ServiceEndpoint:
    """Resolved endpoint for a provider."""

    provider: str
    base_url: str
    timeout: int


def _provider_settings():
    """Map provider -> (base_url, timeout) read freshly from settings.

    Read lazily (not at import time) so test overrides of settings take effect.
    """
    return {
        INTELLIGENCE_ENGINE: (
            settings.INTELLIGENCE_ENGINE_BASE_URL,
            settings.INTELLIGENCE_ENGINE_TIMEOUT_SECONDS,
        ),
        CONTENT_RENDERER: (
            settings.CONTENT_RENDERER_BASE_URL,
            settings.CONTENT_RENDERER_TIMEOUT_SECONDS,
        ),
        REPORT_RENDERER: (
            settings.REPORT_RENDERER_BASE_URL,
            settings.REPORT_RENDERER_TIMEOUT_SECONDS,
        ),
    }


def resolve_provider(job_type: str) -> str:
    """Return the provider responsible for ``job_type``.

    Raises ``UnknownJobType`` for an unmapped job type.
    """
    try:
        return JOB_TYPE_TO_PROVIDER[job_type]
    except KeyError as exc:
        raise UnknownJobType(f"No provider mapped for job_type '{job_type}'.") from exc


def resolve_service(job_type: str) -> ServiceEndpoint:
    """Resolve the ``ServiceEndpoint`` (provider + base_url + timeout) for a job.

    Raises ``UnknownJobType`` when the job type is unmapped and
    ``ServiceNotConfigured`` when the provider has no base URL configured.
    """
    provider = resolve_provider(job_type)
    base_url, timeout = _provider_settings()[provider]
    if not base_url:
        raise ServiceNotConfigured(
            f"Provider '{provider}' (job_type '{job_type}') has no base URL configured."
        )
    return ServiceEndpoint(provider=provider, base_url=base_url, timeout=int(timeout))


def callback_url() -> str:
    """Absolute callback URL the external service should call back to."""
    base = (settings.BACKEND_PUBLIC_BASE_URL or "").rstrip("/")
    path = settings.INTERNAL_CALLBACK_PATH or ""
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}"


# --------------------------------------------------------------------------- #
# Master switches (enabled / dry-run)
# --------------------------------------------------------------------------- #
def external_jobs_enabled() -> bool:
    """True when external submission is enabled at all."""
    return bool(settings.EXTERNAL_JOBS_ENABLED)


def external_jobs_dry_run() -> bool:
    """True when submission must be simulated (no real HTTP call)."""
    return bool(settings.EXTERNAL_JOBS_DRY_RUN)


def should_submit_externally() -> bool:
    """True only when a real external call should be made (enabled and not dry-run)."""
    return external_jobs_enabled() and not external_jobs_dry_run()
