"""Recording audit events.

docs/04_BACKEND_ARCHITECTURE.md section 7 requires login events to be audited.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditEvent

# Authentication events.
MAGIC_LINK_REQUESTED = "auth.magic_link_requested"
MAGIC_LINK_REJECTED = "auth.magic_link_rejected"
SIGN_IN_SUCCEEDED = "auth.sign_in_succeeded"
SIGN_IN_FAILED = "auth.sign_in_failed"
SIGNED_OUT = "auth.signed_out"

#: Keys allowed in audit metadata. Anything else is dropped, so an email or a
#: token cannot reach the audit table by accident.
ALLOWED_METADATA_KEYS = frozenset({"reason", "outcome", "session_id", "identity_id"})


async def record_event(
    db: AsyncSession,
    *,
    event_type: str,
    resource_type: str,
    resource_id: str | None = None,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Append an audit row. The caller commits."""
    safe_metadata = {
        key: value for key, value in (metadata or {}).items() if key in ALLOWED_METADATA_KEYS
    }
    event = AuditEvent(
        user_id=user_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=safe_metadata,
    )
    db.add(event)
    return event
