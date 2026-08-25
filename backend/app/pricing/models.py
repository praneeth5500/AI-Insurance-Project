"""The `product_prices` table (docs/05_DATA_MODEL.md section 5).

Every column that makes a price safe to show is NOT NULL: status, source type,
source name and `generated_at`. The data model ends with "Never display a
price record without source/status/timestamp", and the cheapest way to keep
that promise is to make a row without them impossible to store.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import new_id, timestamp_column

#: docs/01_PRODUCT_SPEC.md section 7.
STATUS_INDICATIVE = "INDICATIVE"
STATUS_QUOTED = "QUOTED"
STATUS_FINAL = "FINAL"
PRICE_STATUSES = (STATUS_INDICATIVE, STATUS_QUOTED, STATUS_FINAL)


class ProductPrice(Base):
    __tablename__ = "product_prices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("pp"))
    product_version_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("product_versions.id", ondelete="CASCADE"), nullable=False
    )

    #: INDICATIVE (before underwriting) | QUOTED (formal, with a reference)
    #: | FINAL (confirmed for issuance, only when genuinely available).
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    #: Stored in the smallest unit (paise) so no rounding is introduced by us.
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    billing_period: Mapped[str] = mapped_column(String(16), nullable=False)

    #: Null means "we do not know", which is shown as unknown rather than
    #: assumed either way (docs/12_BETA_CHECKLIST.md: taxes/fees state
    #: captured if known).
    taxes_included: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fees_included: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_name: Mapped[str] = mapped_column(String(300), nullable=False)
    #: The insurer's own quote reference, when there is one.
    source_quote_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    generated_at: Mapped[datetime] = timestamp_column(nullable=False)
    #: When a quote stops being valid. Past this the price is not shown.
    valid_until: Mapped[datetime | None] = timestamp_column(nullable=True)
    underwriting_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    #: What the figure assumed — age, cover, city. Shown alongside it, so an
    #: indicative price is never read as a personal quote.
    assumptions_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    #: Identifies the request that produced a quote, so it can be matched back.
    request_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())

    __table_args__ = (Index("ix_product_prices_version_status", "product_version_id", "status"),)
