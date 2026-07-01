"""Light helpers for the catalogue domain.

Deep platform validation and metrics collection belong to FastAPI. Here we only
do best-effort parsing — notably extracting a YouTube video id from a URL.
"""

import re
from urllib.parse import parse_qs, urlparse

_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_PATH_PREFIXES = ("/shorts/", "/embed/", "/v/", "/live/")


def _clean(video_id):
    return video_id if video_id and _VIDEO_ID_RE.match(video_id) else None


def extract_youtube_video_id(url: str):
    """Return the 11-char YouTube video id from ``url`` or ``None``.

    Recognizes ``watch?v=``, ``youtu.be/<id>``, ``/shorts/<id>``, ``/embed/<id>``,
    ``/v/<id>`` and ``/live/<id>`` forms.
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    host = (parsed.netloc or "").lower()
    if host not in _YOUTUBE_HOSTS:
        return None

    if host == "youtu.be":
        return _clean(parsed.path.lstrip("/").split("/")[0])

    if parsed.path == "/watch":
        values = parse_qs(parsed.query).get("v")
        return _clean(values[0]) if values else None

    for prefix in _PATH_PREFIXES:
        if parsed.path.startswith(prefix):
            return _clean(parsed.path[len(prefix):].split("/")[0])

    return None


def is_youtube_url(url: str) -> bool:
    try:
        return (urlparse(url).netloc or "").lower() in _YOUTUBE_HOSTS
    except ValueError:
        return False
