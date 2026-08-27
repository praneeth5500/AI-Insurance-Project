"""Where analytics events are kept.

`docs/05_DATA_MODEL.md` has `audit_events` and `feedback` but no analytics
table — analytics usually goes to a third-party product, and no vendor is
chosen. Rather than pick one, events are written here behind a sink interface,
which keeps the beta's own data in the beta's own database and leaves the
vendor decision open. Recorded in `docs/SPEC_ISSUES.md`.

`properties_json` is not a free-form bag despite its type: only keys declared
for that event in `app.analytics.events` survive, and everything else is
dropped before the row is built. That is what makes "no sensitive answers in
analytics" a property of the system rather than a promise.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import new_id, timestamp_column


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("evt"))
    #: Nullable: an event can happen before anyone signs in.
    user_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Only declared keys reach this column.
    properties_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())

    __table_args__ = (Index("ix_analytics_events_name", "name", "created_at"),)
