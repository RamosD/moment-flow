"""Privacy helpers for audit records.

Raw IP addresses are never stored. The client IP and user-agent are hashed
(salted with ``SECRET_KEY``); an empty string is stored when unavailable.
"""

import hashlib

from django.conf import settings


def _hash(value: str) -> str:
    if not value:
        return ""
    salted = f"{settings.SECRET_KEY}:{value}".encode()
    return hashlib.sha256(salted).hexdigest()


def client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def ip_address_hash(request) -> str:
    return _hash(client_ip(request))


def user_agent_hash(request) -> str:
    return _hash(request.META.get("HTTP_USER_AGENT", ""))
