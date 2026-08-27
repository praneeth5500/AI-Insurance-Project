"""Database access for authentication."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Row, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.models import AuthIdentity, MagicLinkToken, Session
from app.users.models import User


async def get_identity_by_email(db: AsyncSession, email: str) -> AuthIdentity | None:
    result = await db.execute(select(AuthIdentity).where(AuthIdentity.email == email))
    return result.scalar_one_or_none()


async def get_magic_link_by_hash(db: AsyncSession, token_hash: str) -> MagicLinkToken | None:
    result = await db.execute(select(MagicLinkToken).where(MagicLinkToken.token_hash == token_hash))
    return result.scalar_one_or_none()


async def get_user_by_identity(db: AsyncSession, identity_id: str) -> User | None:
    result = await db.execute(select(User).where(User.auth_identity_id == identity_id))
    return result.scalar_one_or_none()


async def get_session_by_hash(db: AsyncSession, token_hash: str) -> Session | None:
    result = await db.execute(select(Session).where(Session.token_hash == token_hash))
    return result.scalar_one_or_none()


async def get_user_with_identity(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.auth_identity))
    )
    return result.scalar_one_or_none()


async def revoke_sessions_for_identity(db: AsyncSession, identity_id: str, *, at: datetime) -> int:
    """End every live session belonging to an identity. Returns how many."""
    live = await db.execute(
        select(Session).where(
            Session.user_id.in_(select(User.id).where(User.auth_identity_id == identity_id)),
            Session.revoked_at.is_(None),
            Session.expires_at > at,
        )
    )
    sessions = list(live.scalars())
    for session in sessions:
        session.revoked_at = at
    return len(sessions)


async def list_identities_with_session_counts(
    db: AsyncSession, *, at: datetime
) -> Sequence[Row[tuple[str, str, bool, datetime | None, int]]]:
    """Every identity, oldest invite first, with its live-session count.

    One query rather than a count per identity: a beta is small, but a query
    per row is the habit that makes the next screen slow. Rows are returned
    raw; `app.auth.allowlist` gives them their shape, which keeps the
    repository free of a domain import it would have to take back.
    """
    live_sessions = (
        select(User.auth_identity_id.label("identity_id"), func.count(Session.id).label("live"))
        .join(Session, Session.user_id == User.id)
        .where(Session.revoked_at.is_(None), Session.expires_at > at)
        .group_by(User.auth_identity_id)
        .subquery()
    )

    result = await db.execute(
        select(
            AuthIdentity.email,
            AuthIdentity.status,
            AuthIdentity.allowlisted,
            AuthIdentity.last_login_at,
            func.coalesce(live_sessions.c.live, 0),
        )
        .outerjoin(live_sessions, live_sessions.c.identity_id == AuthIdentity.id)
        .order_by(AuthIdentity.created_at, AuthIdentity.email)
    )
    return list(result.all())
