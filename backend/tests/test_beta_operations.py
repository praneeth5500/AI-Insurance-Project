"""Phase 17: the operator surface for running a friends-and-family beta.

`docs/11_BUILD_PLAN.md` Phase 17 is an activity, not a feature — invite a few
people, watch where they get confused, expand slowly. What code has to provide
is the ability to run it: issue an invite, take one back, and see who has
actually got in. Anything beyond that (an admin UI, self-service sign-up) is a
product decision and is not invented here.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import pytest
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.allowlist import beta_roster, revoke_access, seed_allowlist
from app.auth.models import STATUS_ACTIVE, STATUS_REVOKED, AuthIdentity, Session
from app.db.types import new_id, utcnow
from app.users.models import User


async def _signed_in(db: AsyncSession, email: str, *, sessions: int = 1) -> AuthIdentity:
    """An identity that has been invited and has signed in."""
    await seed_allowlist(db, [email])
    identity = (await db.execute(_by_email(email))).scalar_one()
    identity.status = STATUS_ACTIVE
    identity.last_login_at = utcnow()

    user = User(id=new_id("usr"), auth_identity_id=identity.id)
    db.add(user)
    await db.flush()

    for index in range(sessions):
        db.add(
            Session(
                user_id=user.id,
                token_hash=f"hash-{identity.id}-{index}",
                expires_at=utcnow() + timedelta(days=14),
            )
        )
    await db.commit()
    return identity


def _by_email(email: str) -> Select[tuple[AuthIdentity]]:
    return select(AuthIdentity).where(AuthIdentity.email == email)


async def test_revoking_access_ends_live_sessions(db: AsyncSession) -> None:
    """Access must stop now, not whenever the cookie happens to expire."""
    identity = await _signed_in(db, "leaving@example.com", sessions=2)

    result = await revoke_access(db, "leaving@example.com")

    assert result.outcome == "revoked"
    assert result.sessions_revoked == 2

    await db.refresh(identity)
    assert identity.allowlisted is False
    assert identity.status == STATUS_REVOKED
    assert identity.can_sign_in is False

    sessions = (await db.execute(_sessions_for(identity.id))).scalars().all()
    assert all(session.revoked_at is not None for session in sessions)


def _sessions_for(identity_id: str) -> Select[tuple[Session]]:
    return select(Session).where(
        Session.user_id.in_(select(User.id).where(User.auth_identity_id == identity_id))
    )


async def test_revoking_is_idempotent(db: AsyncSession) -> None:
    await _signed_in(db, "twice@example.com")

    assert (await revoke_access(db, "twice@example.com")).outcome == "revoked"
    second = await revoke_access(db, "twice@example.com")
    assert second.outcome == "already_revoked"
    assert second.sessions_revoked == 0


async def test_revoking_an_unknown_address_is_not_an_error(db: AsyncSession) -> None:
    """An operator typo must not create a row, or a stack trace."""
    result = await revoke_access(db, "never-invited@example.com")

    assert result.outcome == "not_found"
    assert (await db.execute(_by_email("never-invited@example.com"))).scalar_one_or_none() is None


async def test_revoking_is_case_insensitive(db: AsyncSession) -> None:
    """The operator types the address as they remember it, not as stored."""
    await _signed_in(db, "mixed@example.com")

    assert (await revoke_access(db, "MiXeD@Example.COM")).outcome == "revoked"


async def test_a_revoked_address_can_be_reinstated(db: AsyncSession) -> None:
    """Someone removed by mistake gets their history back, not a second row."""
    identity = await _signed_in(db, "back@example.com")
    await revoke_access(db, "back@example.com")

    result = await seed_allowlist(db, ["back@example.com"])

    assert result.reinstated == 1
    await db.refresh(identity)
    assert identity.can_sign_in is True


async def test_reinstating_does_not_resurrect_the_old_sessions(db: AsyncSession) -> None:
    """Access came back; the browser session that was ended did not.

    A revoked session is revoked for good — otherwise taking access away and
    giving it back would silently re-admit whoever was holding that cookie,
    including whoever it was taken away from.
    """
    identity = await _signed_in(db, "cookie@example.com", sessions=1)
    await revoke_access(db, "cookie@example.com")
    await seed_allowlist(db, ["cookie@example.com"])

    sessions = (await db.execute(_sessions_for(identity.id))).scalars().all()
    assert all(session.revoked_at is not None for session in sessions)


async def test_the_roster_separates_invited_from_signed_in(db: AsyncSession) -> None:
    """The address that never signs in is the one worth chasing."""
    await _signed_in(db, "used@example.com", sessions=2)
    await seed_allowlist(db, ["unused@example.com"])

    roster = {entry.email: entry for entry in await beta_roster(db)}

    assert roster["used@example.com"].last_login_at is not None
    assert roster["used@example.com"].active_sessions == 2
    assert roster["unused@example.com"].last_login_at is None
    assert roster["unused@example.com"].active_sessions == 0


async def test_the_roster_shows_a_revoked_invite_as_revoked(db: AsyncSession) -> None:
    await _signed_in(db, "gone@example.com")
    await revoke_access(db, "gone@example.com")

    entry = next(e for e in await beta_roster(db) if e.email == "gone@example.com")

    assert entry.status == STATUS_REVOKED
    assert entry.allowlisted is False
    assert entry.active_sessions == 0


async def test_an_expired_session_does_not_count_as_active(db: AsyncSession) -> None:
    """Otherwise the roster would overstate who is actually using the beta."""
    identity = await _signed_in(db, "stale@example.com", sessions=0)
    user = (await db.execute(_user_for(identity.id))).scalar_one()
    db.add(
        Session(
            user_id=user.id,
            token_hash="expired-hash",
            expires_at=utcnow() - timedelta(days=1),
        )
    )
    await db.commit()

    entry = next(e for e in await beta_roster(db) if e.email == "stale@example.com")
    assert entry.active_sessions == 0


def _user_for(identity_id: str) -> Select[tuple[User]]:
    return select(User).where(User.auth_identity_id == identity_id)


async def test_no_invited_address_reaches_the_application_log(
    db: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    """An invited address is personal data; only counts and ids are logged."""
    with caplog.at_level(logging.DEBUG):
        await seed_allowlist(db, ["private@example.com"])
        await revoke_access(db, "private@example.com")

    assert caplog.records, "expected the allowlist operations to log something"
    for record in caplog.records:
        assert "private@example.com" not in record.getMessage()
        assert "private@example.com" not in str(getattr(record, "fields", {}))
