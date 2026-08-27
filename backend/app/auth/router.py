"""Auth endpoints (docs/08_API_CONTRACTS.md sections 1 and 2)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.auth import service
from app.auth.cookies import clear_session_cookie, set_session_cookie
from app.auth.dependencies import AppSettings, CurrentUser, DbSession, session_token
from app.auth.schemas import (
    MagicLinkRequest,
    MagicLinkResponse,
    MeResponse,
    SignOutResponse,
    VerifyRequest,
)
from app.core.errors import RateLimitedError
from app.core.rate_limit import (
    MAGIC_LINK_PER_EMAIL,
    MAGIC_LINK_PER_IP,
    VERIFY_PER_IP,
    client_ip,
    limiter,
)
from app.integrations.email import EmailProvider, build_email_provider

router = APIRouter(tags=["auth"])


def get_email_provider(settings: AppSettings) -> EmailProvider:
    return build_email_provider(settings)


EmailSender = Annotated[EmailProvider, Depends(get_email_provider)]


@router.post(
    "/auth/request-magic-link",
    response_model=MagicLinkResponse,
    summary="Send a sign-in link if the address is invited",
)
async def request_magic_link(
    request: Request,
    payload: MagicLinkRequest,
    settings: AppSettings,
    db: DbSession,
    email_provider: EmailSender,
) -> MagicLinkResponse:
    """Always returns the same response.

    Revealing whether an address is on the allowlist would let anyone
    enumerate the beta's invited users, so the outcome is not disclosed.

    Limited twice over: per address, so a beta user cannot be flooded with
    sign-in mail sent by us; and per source, so one caller cannot spray many
    addresses. The email is normalised first, or `A@x.com` and `a@x.com` would
    be two separate buckets for one inbox.
    """
    email = str(payload.email).strip().lower()
    if not limiter.check(f"magic-link:email:{email}", MAGIC_LINK_PER_EMAIL):
        raise RateLimitedError
    if not limiter.check(f"magic-link:ip:{client_ip(request)}", MAGIC_LINK_PER_IP):
        raise RateLimitedError

    await service.request_magic_link(db, settings, email_provider, email=str(payload.email))
    return MagicLinkResponse()


@router.post(
    "/auth/verify",
    response_model=MeResponse,
    summary="Exchange a sign-in link for a session",
)
async def verify(
    request: Request,
    payload: VerifyRequest,
    response: Response,
    settings: AppSettings,
    db: DbSession,
) -> MeResponse:
    """Limited by volume, not because a token is guessable.

    A token carries 32 bytes of entropy, so a search is hopeless; the limit
    stops that search being free, and stops a stolen link being replayed at
    speed.
    """
    if not limiter.check(f"verify:ip:{client_ip(request)}", VERIFY_PER_IP):
        raise RateLimitedError

    issued = await service.verify_magic_link(db, settings, token=payload.token)
    set_session_cookie(response, settings, issued.token)
    return MeResponse(
        id=issued.user.id,
        email=issued.identity.email,
        has_profile=issued.user.has_profile,
        beta_access=True,
    )


@router.post(
    "/auth/sign-out",
    response_model=SignOutResponse,
    summary="Revoke the current session",
)
async def sign_out(
    request: Request,
    response: Response,
    settings: AppSettings,
    db: DbSession,
) -> SignOutResponse:
    """Idempotent: signing out without a session is not an error."""
    token = session_token(request, settings)
    if token:
        await service.sign_out(db, token=token)
    clear_session_cookie(response, settings)
    return SignOutResponse()


@router.get("/me", response_model=MeResponse, summary="The signed-in user")
async def me(user: CurrentUser) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=user.auth_identity.email,
        has_profile=user.has_profile,
        # Reaching this endpoint at all means the identity is allowlisted and
        # not revoked; resolve_session enforces both.
        beta_access=True,
    )
