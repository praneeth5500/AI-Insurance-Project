"""Auth errors, in the standard envelope from docs/08_API_CONTRACTS.md."""

from __future__ import annotations

from app.core.errors import AppError


class NotAuthenticatedError(AppError):
    code = "UNAUTHENTICATED"
    http_status = 401
    retryable = False
    message = "Please sign in to continue."


class InvalidSignInLinkError(AppError):
    """Covers unknown, already-used, expired and revoked links alike.

    Deliberately one error: distinguishing them would tell an attacker which
    tokens exist. The frontend offers "request a new link" for all of them,
    which is the correct action in every case.
    """

    code = "SIGN_IN_LINK_INVALID"
    http_status = 400
    retryable = False
    message = "This sign-in link is no longer valid. Request a new one to continue."
