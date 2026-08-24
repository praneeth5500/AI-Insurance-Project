"""Auth tables.

`auth_identities` follows docs/05_DATA_MODEL.md section 1.
`magic_link_tokens` and `sessions` are not in that logical model — it does not
describe the storage the magic-link flow needs — so they are introduced here
and recorded in docs/SPEC_ISSUES.md.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import new_id, timestamp_column

if TYPE_CHECKING:
    from app.users.models import User

#: INVITED  — on the allowlist, never signed in.
#: ACTIVE   — has signed in at least once.
#: REVOKED  — access withdrawn; cannot sign in or hold a session.
IdentityStatus = str

STATUS_INVITED = "INVITED"
STATUS_ACTIVE = "ACTIVE"
STATUS_REVOKED = "REVOKED"

PROVIDER_MAGIC_LINK = "MAGIC_LINK"


class AuthIdentity(Base):
    __tablename__ = "auth_identities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("aid"))
    #: Stored lowercase; uniqueness is therefore case-insensitive in practice.
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default=PROVIDER_MAGIC_LINK)
    #: Identifier from an external auth provider, once one is chosen
    #: (docs/13_DECISIONS_AND_OPEN_ITEMS.md open item 1).
    provider_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    allowlisted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[IdentityStatus] = mapped_column(
        String(16), nullable=False, default=STATUS_INVITED
    )
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())
    last_login_at: Mapped[datetime | None] = timestamp_column(nullable=True)

    # lazy="raise": traversing this without eager loading raises immediately
    # instead of attempting IO. Under async SQLAlchemy an implicit lazy load
    # either fails with MissingGreenlet or silently succeeds from the weak
    # identity map depending on garbage collection — a bug that reproduces
    # only sometimes. Failing loudly makes it deterministic.
    user: Mapped[User | None] = relationship(
        back_populates="auth_identity", uselist=False, lazy="raise"
    )

    @property
    def can_sign_in(self) -> bool:
        return self.allowlisted and self.status != STATUS_REVOKED


class MagicLinkToken(Base):
    """A single-use, expiring sign-in token.

    Only the SHA-256 digest is stored, so the table cannot be replayed.
    """

    __tablename__ = "magic_link_tokens"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("mlt"))
    auth_identity_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("auth_identities.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = timestamp_column(nullable=False)
    #: Set the first time the token is exchanged. A second attempt is rejected.
    consumed_at: Mapped[datetime | None] = timestamp_column(nullable=True)
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())

    __table_args__ = (Index("ix_magic_link_tokens_identity", "auth_identity_id"),)


class Session(Base):
    """A signed-in session. Revocable, which is why it is a row and not a JWT."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ses"))
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = timestamp_column(nullable=False)
    revoked_at: Mapped[datetime | None] = timestamp_column(nullable=True)
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())
    last_seen_at: Mapped[datetime | None] = timestamp_column(nullable=True)

    __table_args__ = (Index("ix_sessions_user", "user_id"),)
