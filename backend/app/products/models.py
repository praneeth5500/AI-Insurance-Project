"""Saved options.

`docs/11_BUILD_PLAN.md` Phase 7 asks for "save", but `docs/05_DATA_MODEL.md`
defines no table for it — recorded in `docs/SPEC_ISSUES.md`.

Kept as thin as possible: who saved what, and when. It deliberately does not
copy any product detail, so a saved option can never drift out of step with
the catalogue it points at.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import new_id, timestamp_column


class SavedProduct(Base):
    __tablename__ = "saved_products"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("sv"))
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    #: The synthetic product reference. Becomes a product_version_id in Phase 8.
    product_reference: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())

    __table_args__ = (
        # Saving twice is the same as saving once.
        UniqueConstraint("user_id", "product_reference", name="uq_saved_user_product"),
    )
