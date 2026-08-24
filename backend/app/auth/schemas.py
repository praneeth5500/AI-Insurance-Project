"""Auth request and response payloads (docs/08_API_CONTRACTS.md sections 1-2)."""

from __future__ import annotations

from pydantic import EmailStr

from app.core.schema import ApiModel


class MagicLinkRequest(ApiModel):
    email: EmailStr


class MagicLinkResponse(ApiModel):
    """Deliberately contentless.

    The same response is returned whether or not the address is on the
    allowlist, so the endpoint cannot be used to enumerate invited users.
    """

    status: str = "SENT_IF_ELIGIBLE"


class VerifyRequest(ApiModel):
    token: str


class MeResponse(ApiModel):
    """Shape fixed by docs/08_API_CONTRACTS.md section 2."""

    id: str
    email: EmailStr
    has_profile: bool
    beta_access: bool


class SignOutResponse(ApiModel):
    status: str = "SIGNED_OUT"
