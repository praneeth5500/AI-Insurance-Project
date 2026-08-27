"""Recording an analytics event, safely.

One function does the work, and it is the only way an event is written. That
matters: the rule "never put sensitive answer content into analytics" is only
enforceable if there is a single place where enforcement can live.

What it does, in order:

1. refuses an event nobody declared;
2. drops every property key not declared for that event;
3. refuses values that are not primitives, and truncates strings;
4. writes the row.

Step 2 is the load-bearing one. A `question_answered` event may carry
`question_id` and `stage`; if a caller passes `value`, it is dropped rather
than stored — so the failure mode of a careless call site is a missing
property, never a leaked answer.

Recording never raises into the caller's path. A failed analytics write must
not fail a questionnaire submission: the point of the measurement is to
observe the product, not to become a way to break it.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.events import UnknownEventError, definition_for
from app.analytics.models import AnalyticsEvent
from app.core.logging import log_fields
from app.users.models import User

logger = logging.getLogger(__name__)

#: Strings are bounded so a property cannot become a smuggling channel for
#: free text. Every declared string property is an identifier or a short
#: enum value; nothing legitimate approaches this.
MAX_VALUE_LENGTH = 64


def sanitize(name: str, properties: dict[str, Any] | None) -> dict[str, Any]:
    """Keep only what this event is allowed to carry.

    Exposed separately from `record` so the rule can be tested directly, and
    so a caller that wants to know what would be stored can ask.
    """
    definition = definition_for(name)
    if not properties:
        return {}

    clean: dict[str, Any] = {}
    for key, value in properties.items():
        if key not in definition.allowed_properties:
            # Dropped, not stored under another name. An undeclared key is
            # either a mistake or an attempt to record something we decided
            # not to record; both are handled the same way.
            continue
        if isinstance(value, bool | int | float):
            clean[key] = value
        elif isinstance(value, str):
            clean[key] = value[:MAX_VALUE_LENGTH]
        # Anything else — a dict, a list, an object — is dropped. Structured
        # values are how answer payloads travel, and none of these events
        # needs one.
    return clean


async def record(
    db: AsyncSession,
    *,
    name: str,
    user: User | None = None,
    properties: dict[str, Any] | None = None,
) -> AnalyticsEvent | None:
    """Write one event. Returns None if it could not be recorded.

    Deliberately does not commit: the event joins the caller's transaction, so
    an event describing something that was rolled back is rolled back too.
    """
    try:
        clean = sanitize(name, properties)
    except UnknownEventError:
        logger.warning(
            "analytics_unknown_event",
            extra=log_fields(event="analytics_unknown_event"),
        )
        return None

    event = AnalyticsEvent(
        user_id=user.id if user is not None else None,
        name=name,
        properties_json=clean,
    )
    db.add(event)
    return event


async def record_safely(
    db: AsyncSession,
    *,
    name: str,
    user: User | None = None,
    properties: dict[str, Any] | None = None,
) -> None:
    """Record, swallowing anything that goes wrong.

    For call sites where measurement must never affect the outcome — a
    questionnaire submission should not fail because an event could not be
    written.
    """
    try:
        await record(db, name=name, user=user, properties=properties)
    except Exception:  # noqa: BLE001 - deliberately broad; see the docstring
        logger.warning("analytics_write_failed", extra=log_fields(event="analytics_write_failed"))
