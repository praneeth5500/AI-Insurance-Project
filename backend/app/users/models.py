"""The `users` table from docs/05_DATA_MODEL.md section 1."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import new_id, timestamp_column

if TYPE_CHECKING:
    from app.auth.models import AuthIdentity


class User(Base):
    """A person using the product.

    One row per auth identity. Household members, vehicles and policies hang
    off this in later phases; the auth identity stays purely about sign-in.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("usr"))
    auth_identity_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("auth_identities.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = timestamp_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # lazy="raise" — see the note on AuthIdentity.user. Callers must eager
    # load (selectinload) or carry the identity explicitly.
    auth_identity: Mapped[AuthIdentity] = relationship(back_populates="user", lazy="raise")

    @property
    def has_profile(self) -> bool:
        """Whether the user has completed a domain profile.

        Profiles arrive in Phase 3; until then this is honestly False rather
        than a placeholder True.
        """
        return self.display_name is not None
