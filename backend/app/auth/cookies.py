"""Session cookie handling.

The session token lives in an httpOnly cookie so that page scripts cannot read
it. `SameSite=Lax` is correct for this deployment shape: the API and the app
are the same site (different subdomains in a deployed environment, different
ports locally), so the cookie is sent on same-site requests but not on
cross-site ones.
"""

from __future__ import annotations

from fastapi import Response

from app.core.config import Settings


def set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
        domain=settings.session_cookie_domain,
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
        domain=settings.session_cookie_domain,
    )
