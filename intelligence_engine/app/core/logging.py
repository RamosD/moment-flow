"""Structured JSON logging for the Intelligence Engine.

Mirrors the approach used by the content_renderer logger (one JSON object per
line, secrets redacted by key name) but built on Python's stdlib `logging` so
it composes with Uvicorn's own loggers.

Sensitive keys (token, secret, password, authorization, api_key, credential)
are redacted recursively from the `extra` fields of every record. Callers
should still avoid passing secrets to `extra` in the first place — redaction
is defence-in-depth, not the primary control.
"""

import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

from app.constants import SERVICE_NAME

REDACTED = "[REDACTED]"
MAX_REDACT_DEPTH = 8
SENSITIVE_KEY_PATTERN = re.compile(
    r"token|secret|password|authorization|api[-_]?key|credential", re.IGNORECASE
)

# Uvicorn installs its own (plain-text) handlers on these loggers. We strip
# them and let the records propagate to the root JSON handler so every line —
# ours and the server's — is a single structured format.
_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")

# Attributes that are part of the standard LogRecord and must not be treated
# as caller-supplied "extra" fields when serialising.
_STANDARD_RECORD_ATTRS = set(logging.LogRecord(__name__, 0, "", 0, "", None, None).__dict__.keys())


def redact(value: Any, depth: int = 0) -> Any:
    if depth >= MAX_REDACT_DEPTH:
        return value
    if isinstance(value, list):
        return [redact(item, depth + 1) for item in value]
    if isinstance(value, dict):
        return {
            key: REDACTED if SENSITIVE_KEY_PATTERN.search(str(key)) else redact(val, depth + 1)
            for key, val in value.items()
        }
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname.lower(),
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "msg": record.getMessage(),
            "service": SERVICE_NAME,
            "logger": record.name,
        }

        # Caller-supplied `extra` fields (anything not part of a standard
        # LogRecord). Merged raw here, then redacted once together with the
        # rest of the payload below.
        for key, val in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS and key != "message":
                payload[key] = val

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(redact(payload), default=str)


def configure_logging(level: str = "INFO") -> None:
    """Route all logging through a single JSON handler on the root logger.

    Uvicorn's own loggers are stripped of their plain-text handlers and set to
    propagate, so server logs (startup, access, errors) share the same
    structured format as application logs. Idempotent: safe to call more than
    once (e.g. once per app instance in tests).
    """
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    for name in _UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True


def get_logger(name: str = SERVICE_NAME) -> logging.Logger:
    return logging.getLogger(name)
