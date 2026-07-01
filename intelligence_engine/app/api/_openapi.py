"""Shared OpenAPI documentation fragments for the internal endpoints."""

from app.schemas.responses import ErrorResponse

# Failure modes documented on every implemented, token-protected endpoint.
IMPLEMENTED_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    403: {"model": ErrorResponse, "description": "Missing or invalid X-Internal-Token."},
    422: {"model": ErrorResponse, "description": "Payload failed validation."},
}

# Same, plus the lifecycle 501 used by endpoints whose engine is still a stub.
INTERNAL_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    **IMPLEMENTED_ERROR_RESPONSES,
    501: {"model": ErrorResponse, "description": "Engine not implemented yet (IE-004+)."},
}
