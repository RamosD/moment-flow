"""Authentication for internal service-to-service endpoints.

Internal callbacks (FastAPI/renderer/workers) authenticate with a shared secret
carried in the ``X-Internal-Token`` header, compared against
``settings.INTERNAL_API_TOKEN`` in constant time. When the token is not
configured, every call is rejected (safe default — no token is ever valid).
"""

import hmac
import logging

from django.conf import settings
from rest_framework.permissions import BasePermission

logger = logging.getLogger("integrations_bridge")

INTERNAL_TOKEN_HEADER = "X-Internal-Token"


class IsInternalService(BasePermission):
    message = "Invalid or missing internal token."

    def has_permission(self, request, view):
        expected = settings.INTERNAL_API_TOKEN
        if not expected:
            # No token configured → every call is rejected (safe default).
            logger.warning("event=callback_rejected reason=internal_token_not_configured")
            return False
        provided = request.headers.get(INTERNAL_TOKEN_HEADER, "")
        ok = bool(provided) and hmac.compare_digest(str(provided), str(expected))
        if not ok:
            # Never log the provided/expected token value.
            logger.warning("event=callback_rejected reason=invalid_token")
        return ok
