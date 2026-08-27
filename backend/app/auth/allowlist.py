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
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import repository as repo
from app.auth.models import STATUS_INVITED, STATUS_REVOKED, AuthIdentity
from app.core.logging import log_fields
from app.core.security import normalize_email
from app.db.types import utcnow

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


@dataclass(frozen=True)
class RevokeResult:
    #: Outcome per address, for the operator running the script.
    outcome: str
    sessions_revoked: int


async def revoke_access(db: AsyncSession, email: str) -> RevokeResult:
    """Withdraw one address's access and end its live sessions.

    `resolve_session` already re-checks `can_sign_in` on every request, so a
    revoked person is refused on their next request regardless. The sessions
    are ended explicitly anyway: the database should say what is true, and a
    later change to that check must not be able to quietly reopen access.
    """
    normalized = normalize_email(email)
    identity = await repo.get_identity_by_email(db, normalized)

    if identity is None:
        return RevokeResult(outcome="not_found", sessions_revoked=0)

    already = not identity.can_sign_in
    identity.allowlisted = False
    identity.status = STATUS_REVOKED

    revoked = await repo.revoke_sessions_for_identity(db, identity.id, at=utcnow())
    await db.commit()

    logger.info(
        "allowlist_revoked",
        extra=log_fields(
            event="allowlist_revoked",
            resource_type="auth_identity",
            resource_id=identity.id,
        ),
    )
    return RevokeResult(
        outcome="already_revoked" if already else "revoked", sessions_revoked=revoked
    )


@dataclass(frozen=True)
class RosterEntry:
    """One invited address, as the operator running the beta needs to see it.

    The email is here because the operator is the person who issued the invite
    and is entitled to know who holds one. It is printed to their terminal and
    never written to the application log.
    """

    email: str
    status: str
    allowlisted: bool
    last_login_at: datetime | None
    active_sessions: int


async def beta_roster(db: AsyncSession) -> list[RosterEntry]:
    """Every invited address and whether it has been used.

    Running a friends-and-family beta means knowing who was invited, who
    actually got in, and who never did — the last group is the one that tells
    you the sign-in mail is not arriving.
    """
    rows = await repo.list_identities_with_session_counts(db, at=utcnow())
    return [
        RosterEntry(
            email=email,
            status=status,
            allowlisted=allowlisted,
            last_login_at=last_login_at,
            active_sessions=live,
        )
        for email, status, allowlisted, last_login_at, live in rows
    ]
