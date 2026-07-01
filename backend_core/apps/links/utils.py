"""Light tracking helpers for smart link clicks.

Privacy: raw IP addresses are never stored. The client IP and user-agent are
hashed (salted with SECRET_KEY); store an empty string when unavailable. No
advanced analytics, no GeoIP, no cookies/pixels.
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


def ip_hash(request) -> str:
    return _hash(client_ip(request))


def user_agent(request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")


def user_agent_hash(request) -> str:
    return _hash(user_agent(request))


def parse_device_and_browser(ua: str):
    """Return a coarse ``(device_type, browser)`` from the user-agent string."""
    ua_l = (ua or "").lower()
    if not ua_l:
        return "", ""

    if "ipad" in ua_l or "tablet" in ua_l:
        device = "tablet"
    elif "mobile" in ua_l or "iphone" in ua_l or "android" in ua_l:
        device = "mobile"
    else:
        device = "desktop"

    if "edg" in ua_l:
        browser = "edge"
    elif "firefox" in ua_l:
        browser = "firefox"
    elif "chrome" in ua_l or "crios" in ua_l:
        browser = "chrome"
    elif "safari" in ua_l:
        browser = "safari"
    else:
        browser = "other"

    return device, browser
