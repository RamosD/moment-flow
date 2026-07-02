"""Correlation-id middleware (STG-PRE-005).

Gives every request a single, opaque id that can be threaded through the
Intelligence Engine call, ``CampaignAction``/``Report``/``MediaKit``/
``ContentPackRequest`` creation, the ``ExternalJobReference`` it may spawn, the
Content Renderer job, and the callback back to the Backend Core — so one
operation can be traced end to end via logs, without replacing any existing
domain id (``action_id``, ``campaign_id``, ``job_id`` stay exactly what they
were).

The header is ``X-Request-ID`` — already the canonical inter-service header
used by ``apps.integrations_bridge`` towards the Intelligence Engine and the
Content Renderer (see ``clients.py``), so no new header vocabulary is
introduced.
"""

import re
import uuid

CORRELATION_ID_HEADER = "X-Request-ID"
_WSGI_HEADER_KEY = "HTTP_X_REQUEST_ID"

# Accept only a conservative, opaque charset from an upstream caller (letters,
# digits, hyphen, underscore) and a sane length bound. Anything else is
# discarded and a fresh id is generated instead — the correlation id must never
# become a vector for header/log injection or unbounded log line size.
_VALID_INCOMING_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _generate_correlation_id() -> str:
    return uuid.uuid4().hex


class CorrelationIdMiddleware:
    """Attach ``request.correlation_id`` and echo it back as a response header.

    Reuses an incoming ``X-Request-ID`` when present and well-formed (e.g. from
    a frontend build tool, load balancer or another upstream proxy); otherwise
    generates a new opaque id. Never reads or logs ``Authorization`` /
    ``X-Internal-Token`` — this middleware only touches the correlation header.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.META.get(_WSGI_HEADER_KEY, "")
        correlation_id = (
            incoming if _VALID_INCOMING_ID.match(incoming) else _generate_correlation_id()
        )
        request.correlation_id = correlation_id

        response = self.get_response(request)
        response[CORRELATION_ID_HEADER] = correlation_id
        return response
