"""
Django settings for the ChartRex Backend Core project.

Architectural rule: Django governs the product; FastAPI calculates and executes.

Configuration is loaded from the environment via python-decouple so that no
secret is hardcoded. See `.env.example` for the supported variables. Sensible
defaults are provided so the project boots out of the box for local development.

For the full list of settings, see
https://docs.djangoproject.com/en/6.0/ref/settings/
"""

from datetime import timedelta
from pathlib import Path

from corsheaders.defaults import default_headers
from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Security
# https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: set a strong, unique SECRET_KEY via the environment in
# production. The default below is for local development only.
SECRET_KEY = config(
    "SECRET_KEY",
    default="django-insecure-dev-only-change-me",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "drf_spectacular",
    "corsheaders",

    # Local apps
    "apps.core",
    "apps.accounts",
    "apps.workspaces",
    "apps.rbac",
    "apps.catalogue",
    "apps.campaigns",
    "apps.campaign_actions",
    "apps.content",
    "apps.links",
    "apps.billing",
    "apps.reports",
    "apps.notifications",
    "apps.audit",
    "apps.integrations_bridge",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise must come right after SecurityMiddleware.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # Correlation-id (STG-PRE-005): attach request.correlation_id as early as
    # possible so every later middleware/view can rely on it being present.
    "apps.core.middleware.CorrelationIdMiddleware",
    # CORS must come before CommonMiddleware (and as high as possible).
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# CORS
# https://github.com/adamchainz/django-cors-headers
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5200,http://127.0.0.1:5200",
    cast=Csv(),
)
# Multi-tenancy header sent by the frontend on every workspace-scoped
# request; not in django-cors-headers' default allow-list, so the browser
# blocks the real request after preflight without this.
CORS_ALLOW_HEADERS = [*default_headers, "x-workspace-id"]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
# Defaults to SQLite for local development. Set DB_ENGINE=postgres to use
# PostgreSQL (psycopg is already installed).

# Short, configurable connect timeout for PostgreSQL only (STG-HARD-002).
# Without it, a request that needs a fresh connection (Django opens one per
# request by default — CONN_MAX_AGE is unset/0 here) can hang for minutes if
# PostgreSQL is unreachable (observed in fase 06, prompt_10 §6.1): stopping the
# container leaves the host port in a state where the OS silently drops the
# connection attempt instead of refusing it immediately, so only an
# application-level timeout bounds the wait. `/ready/`'s own DB probe
# (`apps.integrations_bridge.health._check_database`) reuses this same
# `default` connection, so it is protected by the same bound — this setting is
# irrelevant to SQLite, which has no TCP connection to hang on.
DB_CONNECT_TIMEOUT_SECONDS = config("DB_CONNECT_TIMEOUT_SECONDS", default=5, cast=int)

if config("DB_ENGINE", default="sqlite") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER"),
            "PASSWORD": config("DB_PASSWORD"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
            "OPTIONS": {
                "connect_timeout": DB_CONNECT_TIMEOUT_SECONDS,
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Authentication
# Custom user model is email-based (no username). Must be set before the first
# migration that creates the accounts app.

AUTH_USER_MODEL = "accounts.User"


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Django REST Framework
# https://www.django-rest-framework.org/

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 25,
}


# SimpleJWT
# https://django-rest-framework-simplejwt.readthedocs.io/
# Minimal configuration; custom authentication is intentionally not implemented
# at this stage.

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("ACCESS_TOKEN_LIFETIME_MINUTES", default=60, cast=int)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("REFRESH_TOKEN_LIFETIME_DAYS", default=7, cast=int)
    ),
}


# drf-spectacular (OpenAPI schema)
# https://drf-spectacular.readthedocs.io/

SPECTACULAR_SETTINGS = {
    "TITLE": "ChartRex Backend Core API",
    "DESCRIPTION": "Core API governing the ChartRex platform.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Pin stable component names for the two "status" enums that cannot be
    # auto-named from a single model: one is shared by Template/TemplateVersion/
    # ContentPack, the other is surfaced by the plain job-callback serializer.
    # Values are matched by their member set; a future model change simply falls
    # back to the auto name (never an error).
    "ENUM_NAME_OVERRIDES": {
        "ContentCatalogueStatusEnum": [
            ("draft", "Draft"),
            ("active", "Active"),
            ("deprecated", "Deprecated"),
            ("archived", "Archived"),
        ],
        "ExternalJobStatusEnum": [
            ("queued", "Queued"),
            ("submitted", "Submitted"),
            ("running", "Running"),
            ("completed", "Completed"),
            ("partially_completed", "Partially completed"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
            ("expired", "Expired"),
            ("timeout", "Timeout"),
        ],
        "SmartLinkPlatformEnum": [
            ("youtube", "YouTube"),
            ("spotify", "Spotify"),
            ("apple_music", "Apple Music"),
            ("deezer", "Deezer"),
            ("audiomack", "Audiomack"),
            ("soundcloud", "SoundCloud"),
            ("boomplay", "Boomplay"),
            ("instagram", "Instagram"),
            ("tiktok", "TikTok"),
            ("website", "Website"),
            ("custom", "Custom"),
        ],
    },
}


# Billing / Stripe
# https://stripe.com/docs/webhooks/signatures
# No secrets are hardcoded. When STRIPE_WEBHOOK_SECRET is unset, the webhook
# endpoint still accepts and stores events but cannot verify signatures (a clear
# limitation documented in the billing app). Real checkout is intentionally not
# implemented at this stage (skeleton only).
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_API_KEY = config("STRIPE_API_KEY", default="")


# Internal service-to-service API
# Shared secret used to authenticate internal callbacks from FastAPI/renderer/
# workers (header ``X-Internal-Token``). When empty, internal endpoints reject all
# calls (safe default — no token is ever valid). Never hardcode a real token.
# NOTE: this value is a secret — never log it, never expose it in the OpenAPI
# schema or in execution reports.
INTERNAL_API_TOKEN = config("INTERNAL_API_TOKEN", default="")


# External technical services (FastAPI Intelligence Engine / Content Renderer /
# Report Renderer). Django orchestrates; these services calculate and render.
# Base URLs and timeouts are environment-driven (no secrets here). When the
# services are not yet running, keep ``EXTERNAL_JOBS_DRY_RUN=True`` (simulate
# submission) or ``EXTERNAL_JOBS_ENABLED=False`` (stay queued) so the product
# keeps working without them.
BACKEND_PUBLIC_BASE_URL = config(
    "BACKEND_PUBLIC_BASE_URL", default="http://localhost:8100"
)

# Default is 127.0.0.1, not "localhost" (STG-PRE-006): on Windows dev
# machines, "localhost" resolves to both ::1 and 127.0.0.1, and uvicorn's own
# default bind (127.0.0.1-only, IPv4) does not answer on ::1 — every call
# then burns the full request timeout on the IPv6 attempt before falling
# back to IPv4, silently doubling latency for both the aggregated healthcheck
# and real synchronous intelligence calls whenever the engine is unreachable.
# 127.0.0.1 sidesteps the ambiguity entirely; override via env if the engine
# is genuinely reachable only via a hostname (e.g. a real staging host).
INTELLIGENCE_ENGINE_BASE_URL = config(
    "INTELLIGENCE_ENGINE_BASE_URL", default="http://127.0.0.1:8201"
)
# The contract's synchronous round-trip is sub-millisecond on the engine side, so
# wall time is dominated by network/serialization. 10s is an ample margin for an
# internal call (integration contract §9.1 suggests 5–10s); override per env.
INTELLIGENCE_ENGINE_TIMEOUT_SECONDS = config(
    "INTELLIGENCE_ENGINE_TIMEOUT_SECONDS", default=10, cast=int
)
# Internal token used to authenticate synchronous calls to the Intelligence
# Engine (header ``X-Internal-Token``). By default it REUSES the shared
# ``INTERNAL_API_TOKEN`` — the same secret the engine reads on its side (see the
# integration contract §5), so there is no second secret to manage. Set
# ``INTELLIGENCE_ENGINE_INTERNAL_TOKEN`` explicitly only if a per-service token is
# ever required. NOTE: this value is a secret — never log it, never expose it in
# the OpenAPI schema or in execution reports.
# ``or INTERNAL_API_TOKEN`` (rather than relying only on ``default=``) is
# deliberate: python-decouple returns a literal empty string — not the
# default — when the key is PRESENT in .env with nothing after ``=``. Without
# this, a stray ``INTELLIGENCE_ENGINE_INTERNAL_TOKEN=`` line would silently
# resolve to an empty token instead of reusing the shared one (STG-PRE-004).
INTELLIGENCE_ENGINE_INTERNAL_TOKEN = (
    config("INTELLIGENCE_ENGINE_INTERNAL_TOKEN", default="") or INTERNAL_API_TOKEN
)
# Master switches for the SYNCHRONOUS Intelligence Engine path. These are
# intentionally independent from the asynchronous ``EXTERNAL_JOBS_*`` switches
# (which govern ``/jobs/`` submission + callback): the sync insight path can be
# toggled without affecting the renderers' job pipeline.
#   INTELLIGENCE_ENGINE_ENABLED=False → the synchronous client is not called.
#   INTELLIGENCE_ENGINE_DRY_RUN=True  → a deterministic stub is returned (no HTTP).
INTELLIGENCE_ENGINE_ENABLED = config(
    "INTELLIGENCE_ENGINE_ENABLED", default=True, cast=bool
)
INTELLIGENCE_ENGINE_DRY_RUN = config(
    "INTELLIGENCE_ENGINE_DRY_RUN", default=False, cast=bool
)
# Minimal retry policy for the SYNCHRONOUS engine call. The engine is stateless
# and deterministic, so retries are safe — but they happen inside the user's HTTP
# request, so keep them small. Retries apply ONLY to transient failures (timeout,
# unreachable, 5xx); 4xx and unusable bodies are NEVER retried (contract §9.2).
#   INTELLIGENCE_ENGINE_MAX_RETRIES         → extra attempts after the first.
#   INTELLIGENCE_ENGINE_RETRY_BACKOFF_SECONDS → linear backoff base between tries.
INTELLIGENCE_ENGINE_MAX_RETRIES = config(
    "INTELLIGENCE_ENGINE_MAX_RETRIES", default=1, cast=int
)
INTELLIGENCE_ENGINE_RETRY_BACKOFF_SECONDS = config(
    "INTELLIGENCE_ENGINE_RETRY_BACKOFF_SECONDS", default=0.5, cast=float
)

CONTENT_RENDERER_BASE_URL = config(
    "CONTENT_RENDERER_BASE_URL", default="http://localhost:8202"
)
CONTENT_RENDERER_TIMEOUT_SECONDS = config(
    "CONTENT_RENDERER_TIMEOUT_SECONDS", default=30, cast=int
)

REPORT_RENDERER_BASE_URL = config(
    "REPORT_RENDERER_BASE_URL", default="http://localhost:8202"
)
REPORT_RENDERER_TIMEOUT_SECONDS = config(
    "REPORT_RENDERER_TIMEOUT_SECONDS", default=30, cast=int
)

# Path the external services call back to (joined with BACKEND_PUBLIC_BASE_URL to
# form the absolute callback URL in outbound payloads).
INTERNAL_CALLBACK_PATH = config(
    "INTERNAL_CALLBACK_PATH", default="/api/v1/internal/jobs/callback/"
)

# Master switches for external job submission.
#   EXTERNAL_JOBS_ENABLED=False  → jobs are created but stay queued (no call).
#   EXTERNAL_JOBS_DRY_RUN=True   → submission is simulated (no real HTTP call).
EXTERNAL_JOBS_ENABLED = config("EXTERNAL_JOBS_ENABLED", default=True, cast=bool)
EXTERNAL_JOBS_DRY_RUN = config("EXTERNAL_JOBS_DRY_RUN", default=False, cast=bool)

# Aggregated dependency healthcheck (OBS-STG-003). Short, fail-fast timeout used
# when probing the external services' PUBLIC ``GET /health`` (no token is sent).
# Kept low so the aggregated endpoint stays responsive even when a dependency is
# hung; configurable per environment. Float allows sub-second values.
HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS = config(
    "HEALTHCHECK_DEPENDENCY_TIMEOUT_SECONDS", default=2.0, cast=float
)


def _require_secure_intelligence_engine_config(*, debug, enabled, dry_run, token):
    """Refuse to boot with an insecure Intelligence Engine configuration.

    Outside ``DEBUG`` (i.e. production), if the engine is enabled and will make
    real calls (not dry-run) without an internal token, every call would be
    rejected by the engine (403 ``unauthorized_internal_request``) at runtime.
    Fail fast at startup instead of failing silently later. In ``DEBUG`` an empty
    token is allowed (local development convenience). Kept as a small pure helper
    so it can be unit-tested directly.
    """
    if not debug and enabled and not dry_run and not token:
        raise ImproperlyConfigured(
            "Intelligence Engine is configured for real calls "
            "(INTELLIGENCE_ENGINE_ENABLED=True, INTELLIGENCE_ENGINE_DRY_RUN=False) "
            "but no internal token is set (INTELLIGENCE_ENGINE_INTERNAL_TOKEN / "
            "INTERNAL_API_TOKEN is empty) while DEBUG=False. Set the token, enable "
            "dry-run, or disable the Intelligence Engine."
        )


_require_secure_intelligence_engine_config(
    debug=DEBUG,
    enabled=INTELLIGENCE_ENGINE_ENABLED,
    dry_run=INTELLIGENCE_ENGINE_DRY_RUN,
    token=INTELLIGENCE_ENGINE_INTERNAL_TOKEN,
)


# Logging (OBS-STG-006)
# Minimal, consistent structured logging so the inter-service correlation lines
# actually surface: without an explicit config the project's INFO logs would not
# be emitted (Python's last-resort handler only emits WARNING and above). The
# emitters never log the internal token or full payloads — they log small
# identifier fields (request_id / workspace_id / campaign_id / job_id /
# external_job_id / provider / status / duration_ms / error_type). ``propagate``
# is kept enabled so test log capture (caplog) keeps working, and
# ``disable_existing_loggers`` is False so Django's own loggers are untouched.
LOG_LEVEL = config("LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
    },
    "loggers": {
        # Inter-service flows: IE sync client, renderer job submission/callbacks
        # and the aggregated healthcheck. The children
        # ``integrations_bridge.client`` and ``integrations_bridge.intelligence``
        # inherit this level and handler via propagation.
        "integrations_bridge": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        # Campaign intelligence service: request_id / workspace_id / campaign_id /
        # status / duration_ms / error_type.
        "campaigns.intelligence": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        # Creation events for CampaignAction / Report / MediaKit /
        # ContentPackRequest (STG-PRE-005): action_id/report_id/media_kit_id/
        # content_pack_request_id + workspace_id + correlation_id. The children
        # ``campaign_actions.views``, ``reports.views``, ``content.services``
        # inherit level and handler via propagation.
        "campaign_actions": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "reports": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "content": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
    },
}


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/
# WhiteNoise serves compressed, hashed static files in production. During local
# development (DEBUG=True) the standard storage is used to avoid requiring a
# collectstatic run.

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}


# Default primary key field type
# https://docs.djangoproject.com/en/6.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
