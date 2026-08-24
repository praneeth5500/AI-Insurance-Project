"""Structured logging.

docs/09_AWS_DEPLOYMENT.md section 9 allows request id, user id, resource id,
status, latency and error code — and forbids policy text, health answers, raw
documents and magic-link tokens. Log records therefore carry an explicit
allow-listed ``extra`` payload; free-form message strings must never be built
from user content.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from app.core.request_context import get_request_id

#: The only structured fields permitted on a log record.
ALLOWED_LOG_FIELDS = frozenset(
    {
        "request_id",
        "user_id",
        "resource_type",
        "resource_id",
        "method",
        "path",
        "status_code",
        "latency_ms",
        "error_code",
        "event",
    }
)


class SafeFieldFilter(logging.Filter):
    """Drop any structured field that is not explicitly allow-listed."""

    def filter(self, record: logging.LogRecord) -> bool:
        fields: dict[str, Any] = getattr(record, "fields", {}) or {}
        record.fields = {k: v for k, v in fields.items() if k in ALLOWED_LOG_FIELDS}
        return True


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per line so CloudWatch can index it."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = get_request_id()
        if request_id is not None:
            payload["request_id"] = request_id
        payload.update(getattr(record, "fields", {}))
        if record.exc_info:
            # Type/message only — never the traceback body, which can quote input.
            exc_type, exc_value, _ = record.exc_info
            payload["exception"] = getattr(exc_type, "__name__", "Exception")
            payload["exception_message"] = str(exc_value)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON formatter and safe-field filter on the root logger."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(SafeFieldFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # uvicorn's own access log would duplicate our request log line.
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False


def log_fields(**fields: Any) -> dict[str, Any]:
    """Build the ``extra`` dict for a log call."""
    return {"fields": fields}
