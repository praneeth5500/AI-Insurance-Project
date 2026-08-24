"""The Phase 2 sign-in flow, end to end through the API.

Mirrors the critical auth flow in docs/10_TESTING_AND_EVALS.md section 2:

    allowlisted email -> magic link -> session -> home
"""

from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditEvent
from app.auth.allowlist import grant_access
from app.auth.models import STATUS_ACTIVE, STATUS_REVOKED, AuthIdentity, MagicLinkToken, Session
from app.auth.router import get_email_provider
from app.core.config import Settings
from app.core.security import hash_token
from app.db.types import utcnow
from app.integrations.email import DevFileEmailProvider

INVITED = "invited@example.com"
UNINVITED = "stranger@example.com"


class RecordingEmailProvider:
    """Captures the link instead of delivering it."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_magic_link(self, *, email: str, link: str) -> None:
        self.sent.append((email, link))

    @property
    def last_token(self) -> str:
        match = re.search(r"token=([^&]+)$", self.sent[-1][1])
        assert match is not None
        return match.group(1)


@pytest.fixture
def email_provider(app: object) -> RecordingEmailProvider:
    provider = RecordingEmailProvider()
    app.dependency_overrides[get_email_provider] = lambda: provider  # type: ignore[attr-defined]
    return provider


@pytest.fixture
async def invited(db: AsyncSession) -> AuthIdentity:
    await grant_access(db, INVITED)
    await db.commit()
    identity = (
        await db.execute(select(AuthIdentity).where(AuthIdentity.email == INVITED))
    ).scalar_one()
    return identity


async def sign_in(api: AsyncClient, email_provider: RecordingEmailProvider, email: str) -> str:
    """Complete the flow and return the session cookie value."""
    await api.post("/api/v1/auth/request-magic-link", json={"email": email})
    response = await api.post("/api/v1/auth/verify", json={"token": email_provider.last_token})
    assert response.status_code == 200
    return response.cookies["insurance_session"]


# --------------------------------------------------------------- happy path --


async def test_allowlisted_user_can_sign_in_and_reach_a_protected_endpoint(
    api: AsyncClient, email_provider: RecordingEmailProvider, invited: AuthIdentity
) -> None:
    await api.post("/api/v1/auth/request-magic-link", json={"email": INVITED})
    assert len(email_provider.sent) == 1

    verify = await api.post("/api/v1/auth/verify", json={"token": email_provider.last_token})

    assert verify.status_code == 200
    body = verify.json()
    assert body["email"] == INVITED
    assert body["betaAccess"] is True
    assert body["hasProfile"] is False
    assert body["id"].startswith("usr_")

    me = await api.get("/api/v1/me")
    assert me.status_code == 200
    assert me.json()["email"] == INVITED


async def test_sign_in_creates_a_user_separate_from_the_auth_identity(
    api: AsyncClient,
    db: AsyncSession,
    email_provider: RecordingEmailProvider,
    invited: AuthIdentity,
) -> None:
    await sign_in(api, email_provider, INVITED)

    await db.refresh(invited)
    assert invited.status == STATUS_ACTIVE
    assert invited.last_login_at is not None

    # docs/01_PRODUCT_SPEC.md section 6: the domain profile is a separate row.
    from app.users.models import User

    user = (await db.execute(select(User))).scalar_one()
    assert user.auth_identity_id == invited.id
    assert user.id != invited.id


async def test_signing_in_twice_reuses_the_same_user(
    api: AsyncClient,
    db: AsyncSession,
    email_provider: RecordingEmailProvider,
    invited: AuthIdentity,
) -> None:
    first = await sign_in(api, email_provider, INVITED)
    second = await sign_in(api, email_provider, INVITED)

    from app.users.models import User

    assert len((await db.execute(select(User))).scalars().all()) == 1
    # Each sign-in mints its own session.
    assert first != second


# ------------------------------------------------------------- the allowlist --


async def test_uninvited_email_is_not_sent_a_link(
    api: AsyncClient, email_provider: RecordingEmailProvider
) -> None:
    response = await api.post("/api/v1/auth/request-magic-link", json={"email": UNINVITED})

    assert response.status_code == 200
    assert email_provider.sent == []


async def test_the_response_does_not_reveal_allowlist_membership(
    api: AsyncClient, email_provider: RecordingEmailProvider, invited: AuthIdentity
) -> None:
    """docs/08_API_CONTRACTS.md section 1: the response must be generic."""
    invited_response = await api.post("/api/v1/auth/request-magic-link", json={"email": INVITED})
    uninvited_response = await api.post(
        "/api/v1/auth/request-magic-link", json={"email": UNINVITED}
    )

    assert invited_response.status_code == uninvited_response.status_code
    assert invited_response.json() == uninvited_response.json()


async def test_revoked_identity_cannot_sign_in(
    api: AsyncClient,
    db: AsyncSession,
    email_provider: RecordingEmailProvider,
    invited: AuthIdentity,
) -> None:
    invited.status = STATUS_REVOKED
    await db.commit()

    await api.post("/api/v1/auth/request-magic-link", json={"email": INVITED})

    assert email_provider.sent == []


async def test_revoking_access_ends_an_existing_session_immediately(
    api: AsyncClient,
    db: AsyncSession,
    email_provider: RecordingEmailProvider,
    invited: AuthIdentity,
) -> None:
    """Withdrawn access must not wait for the session to expire."""
    await sign_in(api, email_provider, INVITED)
    assert (await api.get("/api/v1/me")).status_code == 200

    invited.status = STATUS_REVOKED
    await db.commit()

    assert (await api.get("/api/v1/me")).status_code == 401


# ------------------------------------------------------------ link handling --


async def test_a_magic_link_works_only_once(
    api: AsyncClient, email_provider: RecordingEmailProvider, invited: AuthIdentity
) -> None:
    await api.post("/api/v1/auth/request-magic-link", json={"email": INVITED})
    token = email_provider.last_token

    assert (await api.post("/api/v1/auth/verify", json={"token": token})).status_code == 200

    replay = await api.post("/api/v1/auth/verify", json={"token": token})
    assert replay.status_code == 400
    assert replay.json()["error"]["code"] == "SIGN_IN_LINK_INVALID"


async def test_an_expired_magic_link_is_rejected(
    api: AsyncClient,
    db: AsyncSession,
    email_provider: RecordingEmailProvider,
    invited: AuthIdentity,
) -> None:
    await api.post("/api/v1/auth/request-magic-link", json={"email": INVITED})
    token = email_provider.last_token

    stored = (
        await db.execute(
            select(MagicLinkToken).where(MagicLinkToken.token_hash == hash_token(token))
        )
    ).scalar_one()
    stored.expires_at = utcnow() - timedelta(seconds=1)
    await db.commit()

    response = await api.post("/api/v1/auth/verify", json={"token": token})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SIGN_IN_LINK_INVALID"


async def test_an_unknown_token_is_rejected_with_the_same_error(api: AsyncClient) -> None:
    """Unknown, used and expired links are indistinguishable to a caller."""
    response = await api.post("/api/v1/auth/verify", json={"token": "not-a-real-token"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SIGN_IN_LINK_INVALID"


async def test_tokens_are_never_stored_in_the_clear(
    api: AsyncClient,
    db: AsyncSession,
    email_provider: RecordingEmailProvider,
    invited: AuthIdentity,
) -> None:
    await api.post("/api/v1/auth/request-magic-link", json={"email": INVITED})
    token = email_provider.last_token

    stored = (await db.execute(select(MagicLinkToken))).scalar_one()
    assert stored.token_hash != token
    assert stored.token_hash == hash_token(token)


# ----------------------------------------------------------------- sessions --


async def test_protected_endpoint_rejects_an_anonymous_request(api: AsyncClient) -> None:
    response = await api.get("/api/v1/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_protected_endpoint_rejects_a_forged_cookie(api: AsyncClient) -> None:
    api.cookies.set("insurance_session", "made-up")

    assert (await api.get("/api/v1/me")).status_code == 401


async def test_an_expired_session_is_rejected(
    api: AsyncClient,
    db: AsyncSession,
    email_provider: RecordingEmailProvider,
    invited: AuthIdentity,
) -> None:
    token = await sign_in(api, email_provider, INVITED)

    session = (
        await db.execute(select(Session).where(Session.token_hash == hash_token(token)))
    ).scalar_one()
    session.expires_at = utcnow() - timedelta(seconds=1)
    await db.commit()

    assert (await api.get("/api/v1/me")).status_code == 401


async def test_sign_out_revokes_the_session(
    api: AsyncClient,
    db: AsyncSession,
    email_provider: RecordingEmailProvider,
    invited: AuthIdentity,
) -> None:
    token = await sign_in(api, email_provider, INVITED)
    assert (await api.get("/api/v1/me")).status_code == 200

    signed_out = await api.post("/api/v1/auth/sign-out")
    assert signed_out.status_code == 200

    session = (
        await db.execute(select(Session).where(Session.token_hash == hash_token(token)))
    ).scalar_one()
    assert session.revoked_at is not None

    # The cookie is cleared, and the token would not work even if replayed.
    assert (await api.get("/api/v1/me")).status_code == 401
    api.cookies.set("insurance_session", token)
    assert (await api.get("/api/v1/me")).status_code == 401


async def test_sign_out_without_a_session_is_not_an_error(api: AsyncClient) -> None:
    assert (await api.post("/api/v1/auth/sign-out")).status_code == 200


async def test_session_cookie_is_http_only_and_lax(
    api: AsyncClient, email_provider: RecordingEmailProvider, invited: AuthIdentity
) -> None:
    await api.post("/api/v1/auth/request-magic-link", json={"email": INVITED})
    response = await api.post("/api/v1/auth/verify", json={"token": email_provider.last_token})

    set_cookie = response.headers["set-cookie"]
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie.lower().replace("samesite=lax", "SameSite=lax")
    assert "Path=/" in set_cookie


# -------------------------------------------------------------------- audit --


async def test_sign_in_and_sign_out_are_audited_without_personal_data(
    api: AsyncClient,
    db: AsyncSession,
    email_provider: RecordingEmailProvider,
    invited: AuthIdentity,
) -> None:
    """docs/04_BACKEND_ARCHITECTURE.md section 7 requires login events audited."""
    await sign_in(api, email_provider, INVITED)
    await api.post("/api/v1/auth/sign-out")

    events = (await db.execute(select(AuditEvent))).scalars().all()
    types = {event.event_type for event in events}
    assert "auth.magic_link_requested" in types
    assert "auth.sign_in_succeeded" in types
    assert "auth.signed_out" in types

    # docs/05_DATA_MODEL.md section 10: no sensitive content in audit metadata.
    for event in events:
        serialized = str(event.metadata_json)
        assert INVITED not in serialized
        assert "token" not in serialized


async def test_a_rejected_request_is_audited(
    api: AsyncClient, db: AsyncSession, email_provider: RecordingEmailProvider
) -> None:
    await api.post("/api/v1/auth/request-magic-link", json={"email": UNINVITED})

    events = (await db.execute(select(AuditEvent))).scalars().all()
    assert [event.event_type for event in events] == ["auth.magic_link_rejected"]


# ------------------------------------------------------------- adapter rules --


async def test_dev_email_adapter_refuses_to_run_outside_local() -> None:
    """A development stub must never silently swallow real invites."""
    with pytest.raises(RuntimeError, match="APP_ENV=local only"):
        DevFileEmailProvider(Settings(app_env="staging", database_url="postgresql+asyncpg://x/y"))


async def test_dev_email_adapter_writes_the_link_to_a_file_not_the_log(
    tmp_path: Path,
) -> None:
    provider = DevFileEmailProvider(Settings(app_env="local"), path=tmp_path / "links.log")

    await provider.send_magic_link(email=INVITED, link="http://localhost:3000/auth/verify?token=x")

    assert "token=x" in (tmp_path / "links.log").read_text()


async def test_full_flow_against_the_real_per_request_session_wiring(
    live_api: AsyncClient,
    db: AsyncSession,
    email_provider: RecordingEmailProvider,
    invited: AuthIdentity,
) -> None:
    """Regression: sign-in must not touch a lazily loaded relationship.

    Every request here gets its own database session, as in production. An
    earlier version built the verify response from `user.auth_identity`, which
    triggers IO outside the async context and returned a 500 — a failure the
    shared-session fixture could not reproduce, because its identity map was
    already warm.
    """
    await db.commit()  # make the invited identity visible to other sessions

    request = await live_api.post("/api/v1/auth/request-magic-link", json={"email": INVITED})
    assert request.status_code == 200

    verify = await live_api.post("/api/v1/auth/verify", json={"token": email_provider.last_token})
    assert verify.status_code == 200, verify.text
    assert verify.json()["email"] == INVITED

    me = await live_api.get("/api/v1/me")
    assert me.status_code == 200
    assert me.json()["email"] == INVITED

    assert (await live_api.post("/api/v1/auth/sign-out")).status_code == 200
    assert (await live_api.get("/api/v1/me")).status_code == 401
