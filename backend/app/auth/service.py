"""Authentication use cases.

The flow (docs/11_BUILD_PLAN.md Phase 2):

    email entry -> allowlist check -> magic link -> session -> protected routes

Two rules shape almost every decision here:

1. **The response never reveals allowlist membership.** Requesting a link
   returns the same result whether or not the address is invited
   (docs/08_API_CONTRACTS.md section 1).
2. **Tokens are never logged and never stored in the clear.** Only digests are
   persisted (docs/09_AWS_DEPLOYMENT.md section 9).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import quote

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.auth import repository as repo
from app.auth.errors import InvalidSignInLinkError
from app.auth.models import (
    STATUS_ACTIVE,
    AuthIdentity,
    MagicLinkToken,
    Session,
)
from app.core.config import Settings
from app.core.logging import log_fields
from app.core.security import generate_token, hash_token, normalize_email
from app.db.types import utcnow
from app.integrations.email import EmailProvider
from app.users.models import User

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IssuedSession:
    """A session and the one-time token that addresses it.

    The identity is carried explicitly rather than reached through
    `user.auth_identity`: that relationship is lazily loaded, and touching it
    after the commit would attempt IO outside the async context.
    """

    session: Session
    token: str
    user: User
    identity: AuthIdentity


def build_magic_link(settings: Settings, token: str) -> str:
    """The URL emailed to the user. Route from docs/03_FRONTEND_ARCHITECTURE.md."""
    base = settings.frontend_base_url.rstrip("/")
    return f"{base}/auth/verify?token={quote(token)}"


async def request_magic_link(
    db: AsyncSession,
    settings: Settings,
    email_provider: EmailProvider,
    *,
    email: str,
) -> None:
    """Issue a sign-in link if the address is invited.

    Returns None either way. The caller must give the same response in both
    cases — an attacker must not be able to enumerate the beta allowlist.
    """
    normalized = normalize_email(email)
    identity = await repo.get_identity_by_email(db, normalized)

    if identity is None or not identity.can_sign_in:
        # Recorded so that repeated attempts against uninvited addresses are
        # visible, without storing the address itself.
        await audit.record_event(
            db,
            event_type=audit.MAGIC_LINK_REJECTED,
            resource_type="auth_identity",
            resource_id=identity.id if identity else None,
            metadata={"reason": "not_allowlisted"},
        )
        await db.commit()
        logger.info(
            "magic_link_rejected",
            extra=log_fields(event="magic_link_rejected", error_code="NOT_ALLOWLISTED"),
        )
        return

    token = generate_token()
    db.add(
        MagicLinkToken(
            auth_identity_id=identity.id,
            token_hash=hash_token(token),
            expires_at=utcnow() + timedelta(minutes=settings.magic_link_ttl_minutes),
        )
    )
    await audit.record_event(
        db,
        event_type=audit.MAGIC_LINK_REQUESTED,
        resource_type="auth_identity",
        resource_id=identity.id,
    )
    await db.commit()

    await email_provider.send_magic_link(
        email=identity.email, link=build_magic_link(settings, token)
    )
    logger.info("magic_link_issued", extra=log_fields(event="magic_link_issued"))


async def verify_magic_link(db: AsyncSession, settings: Settings, *, token: str) -> IssuedSession:
    """Exchange a magic-link token for a session.

    Raises InvalidSignInLinkError for unknown, expired, already-used and
    revoked links alike.
    """
    magic_link = await repo.get_magic_link_by_hash(db, hash_token(token))

    if magic_link is None:
        await _record_failed_sign_in(db, reason="unknown_token")
        raise InvalidSignInLinkError

    now = utcnow()
    if magic_link.consumed_at is not None:
        await _record_failed_sign_in(
            db, reason="token_already_used", identity_id=magic_link.auth_identity_id
        )
        raise InvalidSignInLinkError
    if magic_link.expires_at <= now:
        await _record_failed_sign_in(
            db, reason="token_expired", identity_id=magic_link.auth_identity_id
        )
        raise InvalidSignInLinkError

    identity = await db.get(AuthIdentity, magic_link.auth_identity_id)
    if identity is None or not identity.can_sign_in:
        # Access can be withdrawn between issuing a link and using it.
        await _record_failed_sign_in(
            db, reason="not_allowlisted", identity_id=magic_link.auth_identity_id
        )
        raise InvalidSignInLinkError

    # Single use: burn the token before the session exists, so a replay in
    # flight cannot mint a second session.
    magic_link.consumed_at = now

    user = await repo.get_user_by_identity(db, identity.id)
    if user is None:
        # First sign-in creates the domain user. The identity stays separate.
        user = User(auth_identity_id=identity.id)
        db.add(user)
        await db.flush()

    identity.status = STATUS_ACTIVE
    identity.last_login_at = now

    session_token = generate_token()
    session = Session(
        user_id=user.id,
        token_hash=hash_token(session_token),
        expires_at=now + timedelta(days=settings.session_ttl_days),
        last_seen_at=now,
    )
    db.add(session)
    await db.flush()

    await audit.record_event(
        db,
        event_type=audit.SIGN_IN_SUCCEEDED,
        resource_type="session",
        resource_id=session.id,
        user_id=user.id,
        metadata={"identity_id": identity.id},
    )
    await db.commit()

    logger.info(
        "sign_in_succeeded",
        extra=log_fields(event="sign_in_succeeded", user_id=user.id, resource_type="session"),
    )
    return IssuedSession(session=session, token=session_token, user=user, identity=identity)


async def resolve_session(db: AsyncSession, *, token: str) -> User | None:
    """Return the signed-in user for a session token, or None.

    Expired and revoked sessions resolve to None — a session row existing is
    never enough on its own.
    """
    session = await repo.get_session_by_hash(db, hash_token(token))
    if session is None:
        return None

    now = utcnow()
    if session.revoked_at is not None or session.expires_at <= now:
        return None

    user = await repo.get_user_with_identity(db, session.user_id)
    if user is None:
        return None

    # Access withdrawn after sign-in must take effect on the next request,
    # not at session expiry.
    if not user.auth_identity.can_sign_in:
        return None

    session.last_seen_at = now
    await db.commit()
    return user


async def sign_out(db: AsyncSession, *, token: str) -> None:
    """Revoke a session. Signing out twice is not an error."""
    session = await repo.get_session_by_hash(db, hash_token(token))
    if session is None or session.revoked_at is not None:
        return

    session.revoked_at = utcnow()
    await audit.record_event(
        db,
        event_type=audit.SIGNED_OUT,
        resource_type="session",
        resource_id=session.id,
        user_id=session.user_id,
    )
    await db.commit()
    logger.info("signed_out", extra=log_fields(event="signed_out", user_id=session.user_id))


async def _record_failed_sign_in(
    db: AsyncSession, *, reason: str, identity_id: str | None = None
) -> None:
    await audit.record_event(
        db,
        event_type=audit.SIGN_IN_FAILED,
        resource_type="auth_identity",
        resource_id=identity_id,
        metadata={"reason": reason},
    )
    await db.commit()
    logger.info(
        "sign_in_failed",
        extra=log_fields(event="sign_in_failed", error_code="SIGN_IN_LINK_INVALID"),
    )
