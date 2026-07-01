"""Internal authentication for protected endpoints (IE-002).

`GET /health` stays public. Every other internal endpoint should depend on
`require_internal_token`, which validates the `X-Internal-Token` header
against the configured token using a constant-time comparison.

The configured token is read from `request.app.state.settings` (populated by
`app.main.create_app`), so the check always reflects the settings of the app
instance handling the request rather than a process-global singleton.

If no token is configured (only possible outside production — see
`app.core.config`), every request is rejected: an unconfigured token must
never be treated as "open access".
"""

import hmac

from fastapi import Header, Request

from app.core.config import Settings
from app.core.errors import UnauthorizedInternalRequestError

INTERNAL_TOKEN_HEADER = "X-Internal-Token"


def _tokens_match(provided: str, configured: str) -> bool:
    if not configured or not provided:
        return False
    # Compare UTF-8 bytes (not str): `hmac.compare_digest` rejects str inputs
    # containing non-ASCII characters with a TypeError, which would otherwise
    # surface as a 500 instead of a clean 403.
    return hmac.compare_digest(provided.encode("utf-8"), configured.encode("utf-8"))


async def require_internal_token(
    request: Request,
    x_internal_token: str | None = Header(default=None, alias=INTERNAL_TOKEN_HEADER),
) -> None:
    """FastAPI dependency enforcing the internal service-to-service contract.

    Raises `UnauthorizedInternalRequestError` (-> HTTP 403) when the header is
    missing, empty, or does not match the configured token. The token value
    itself is never included in the error details or in any log record.
    """
    settings: Settings = request.app.state.settings
    if not _tokens_match(x_internal_token or "", settings.internal_api_token):
        raise UnauthorizedInternalRequestError()
