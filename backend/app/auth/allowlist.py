"""Beta allowlist management.

Access is invite-only (docs/01_PRODUCT_SPEC.md section 6). An invite is an
`auth_identities` row with `allowlisted = true`; there is no self-service
sign-up path anywhere in the API.

The specification does not say *how* invites are issued, so this is deliberately
the smallest mechanism that works: a configured list of addresses, applied by
an operator running `make seed-allowlist`. Nothing grants access implicitly.
See docs/PHASE_2_NOTES.md — an admin UI is a product decision, not one to guess.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import repository as repo
from app.auth.models import STATUS_INVITED, AuthIdentity
from app.core.logging import log_fields
from app.core.security import normalize_email

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SeedResult:
    invited: int
    already_invited: int
    reinstated: int


async def grant_access(db: AsyncSession, email: str) -> str:
    """Invite one address. Returns the outcome for reporting."""
    normalized = normalize_email(email)
    identity = await repo.get_identity_by_email(db, normalized)

    if identity is None:
        db.add(AuthIdentity(email=normalized, allowlisted=True, status=STATUS_INVITED))
        return "invited"

    if identity.allowlisted and identity.can_sign_in:
        return "already_invited"

    # Reinstating a revoked identity keeps its history rather than duplicating it.
    identity.allowlisted = True
    if not identity.can_sign_in:
        identity.status = STATUS_INVITED
    return "reinstated"


async def seed_allowlist(db: AsyncSession, emails: list[str]) -> SeedResult:
    """Apply a list of invites. Idempotent."""
    counts = {"invited": 0, "already_invited": 0, "reinstated": 0}
    for email in emails:
        counts[await grant_access(db, email)] += 1
    await db.commit()

    result = SeedResult(**counts)
    # Counts only: an invited address is personal data and does not go to logs.
    logger.info(
        "allowlist_seeded",
        extra=log_fields(event="allowlist_seeded", resource_type="auth_identity"),
    )
    return result
