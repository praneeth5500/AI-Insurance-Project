"""Request-scoped authentication dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.auth.errors import NotAuthenticatedError
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.users.models import User

DbSession = Annotated[AsyncSession, Depends(get_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def session_token(request: Request, settings: AppSettings) -> str | None:
    return request.cookies.get(settings.session_cookie_name)


async def get_current_user_optional(
    request: Request, settings: AppSettings, db: DbSession
) -> User | None:
    token = session_token(request, settings)
    if not token:
        return None
    return await service.resolve_session(db, token=token)


async def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    """Require a signed-in user. Every protected route depends on this."""
    if user is None:
        raise NotAuthenticatedError
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
