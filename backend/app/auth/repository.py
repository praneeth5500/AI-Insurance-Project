"""Database access for authentication."""

from __future__ import annotations

from sqlalchemy import select
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
