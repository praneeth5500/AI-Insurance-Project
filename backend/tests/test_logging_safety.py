"""Logging must not carry sensitive content (docs/09_AWS_DEPLOYMENT.md section 9)."""

from __future__ import annotations

import json
import logging
import sys

from app.core.logging import JsonFormatter, SafeFieldFilter, log_fields
from app.core.request_context import set_request_id


def _record(**fields: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request_completed",
        args=(),
        exc_info=None,
    )
    record.fields = fields
    return record


def test_disallowed_fields_are_dropped_before_formatting() -> None:
    record = _record(
        request_id="req_1",
        status_code=200,
        policy_text="the insured shall...",
        health_answer="pre-existing condition",
        magic_link_token="tok_secret",
    )

    SafeFieldFilter().filter(record)
    payload = json.loads(JsonFormatter().format(record))

    assert payload["request_id"] == "req_1"
    assert payload["status_code"] == 200
    assert "policy_text" not in payload
    assert "health_answer" not in payload
    assert "magic_link_token" not in payload


def test_allowed_operational_fields_survive() -> None:
    record = _record(
        request_id="req_2",
        user_id="usr_1",
        resource_type="policy",
        resource_id="pol_1",
        method="GET",
        path="/health/live",
        status_code=200,
        latency_ms=1.5,
        error_code=None,
        event="request_completed",
    )

    SafeFieldFilter().filter(record)
    payload = json.loads(JsonFormatter().format(record))

    assert payload["user_id"] == "usr_1"
    assert payload["latency_ms"] == 1.5
    assert payload["path"] == "/health/live"


def test_request_id_from_context_is_attached() -> None:
    set_request_id("req_ctx")
    record = _record(status_code=200)

    SafeFieldFilter().filter(record)
    payload = json.loads(JsonFormatter().format(record))

    assert payload["request_id"] == "req_ctx"


def test_exception_traceback_body_is_not_serialised() -> None:
    try:
        raise ValueError("postgres://user:password@host")
    except ValueError:
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="request_unhandled_error",
            args=(),
            exc_info=sys.exc_info(),
        )
        record.fields = {}

    formatted = JsonFormatter().format(record)

    assert "Traceback" not in formatted
    assert json.loads(formatted)["exception"] == "ValueError"


def test_log_fields_wraps_values_under_the_fields_key() -> None:
    assert log_fields(status_code=200) == {"fields": {"status_code": 200}}


def test_an_exception_message_is_withheld_outside_local() -> None:
    """A database or validation error quotes the value that caused it.

    That value is the user's — an email address, an answer, a line of policy
    wording — so deployed logs get the type and the request id only.
    """
    try:
        raise ValueError("duplicate key value violates unique constraint: beta@example.com")
    except ValueError:
        record = logging.LogRecord(
            name="app",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="unhandled_exception",
            args=(),
            exc_info=sys.exc_info(),
        )

    deployed = json.loads(JsonFormatter().format(record))
    assert deployed["exception"] == "ValueError"
    assert "exception_message" not in deployed
    assert "beta@example.com" not in json.dumps(deployed)

    local = json.loads(JsonFormatter(include_exception_message=True).format(record))
    assert "beta@example.com" in local["exception_message"]


def test_a_local_exception_message_is_bounded() -> None:
    """Even locally, a message is not an unbounded write into the log."""
    try:
        raise ValueError("x" * 5000)
    except ValueError:
        record = logging.LogRecord(
            name="app",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="unhandled_exception",
            args=(),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(JsonFormatter(include_exception_message=True).format(record))
    assert len(payload["exception_message"]) == 500
