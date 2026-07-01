"""Normalised error model for the Intelligence Engine.

Mirrors the common error contract from the backlog
(docs/gestao/fundamentos/backlog.md, section 6.5):

    {
      "status": "failed",
      "error": {"code": "...", "message": "...", "details": {}},
      "metadata": {"engine": "intelligence_engine", "engine_version": "0.1.0"}
    }

All five MVP error codes are defined here (IE-002): `invalid_payload`,
`unauthorized_internal_request`, `not_found`, `internal_error` and
`config_error`. The FastAPI exception handlers that turn these (and
unexpected/unmapped exceptions) into HTTP responses live in `app/main.py`.
"""

from typing import Any, Literal

ErrorCode = Literal[
    "invalid_payload",
    "unauthorized_internal_request",
    "not_found",
    "internal_error",
    "config_error",
    # Lifecycle code (not a "business" error): the endpoint's contract exists
    # but its engine is not implemented yet. Mirrors the renderer's
    # foundation-phase `not_implemented`. Removed once IE-004+ fills the
    # engines in.
    "not_implemented",
]


class AppError(Exception):
    """Base class for operational errors with a stable machine-readable code."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

    def to_response_body(self, *, engine: str, engine_version: str) -> dict[str, Any]:
        return {
            "status": "failed",
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
            "metadata": {
                "engine": engine,
                "engine_version": engine_version,
            },
        }


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found.", details: dict[str, Any] | None = None) -> None:
        super().__init__("not_found", message, 404, details)


class InternalError(AppError):
    def __init__(
        self,
        message: str = "Unexpected internal error.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__("internal_error", message, 500, details)


class InvalidPayloadError(AppError):
    """Request body/query failed validation (HTTP 422, FastAPI convention)."""

    def __init__(
        self,
        message: str = "Invalid payload.",
        details: dict[str, Any] | None = None,
        status_code: int = 422,
    ) -> None:
        super().__init__("invalid_payload", message, status_code, details)


class UnauthorizedInternalRequestError(AppError):
    """Missing or invalid X-Internal-Token on a protected internal endpoint (HTTP 403)."""

    def __init__(
        self,
        message: str = "Invalid or missing internal token.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__("unauthorized_internal_request", message, 403, details)


class ConfigError(AppError):
    """Invalid or missing configuration, fatal at boot (HTTP 500 if ever surfaced)."""

    def __init__(
        self,
        message: str = "Invalid configuration.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__("config_error", message, 500, details)


class NotImplementedYetError(AppError):
    """Contract is defined but the engine is not implemented yet (HTTP 501).

    Used by the IE-003 endpoint stubs: the request is validated against the
    real contract, but the engine logic lands in IE-004+. Named with a `Yet`
    suffix to avoid shadowing the built-in `NotImplementedError`.
    """

    def __init__(self, feature: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            "not_implemented",
            f"Not implemented yet: {feature}",
            501,
            {"feature": feature, **(details or {})},
        )
