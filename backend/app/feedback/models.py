"""Beta feedback (docs/05_DATA_MODEL.md section 10).

The one place in this product where free text is deliberately stored, because
the whole point is what someone chose to say. So it is bounded, it is scoped
to a context, and — unlike everything else the reader writes — it is the only
field a human is expected to read.

`rating` is separate from `comment` because the useful questions are different:
"was this helpful" is countable, "what was confusing" is not.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import new_id, timestamp_column

#: Where the feedback was left. Kept to a known set so feedback can be
#: grouped, and so a context string cannot become a second free-text field.
CONTEXT_RECOMMENDATION = "RECOMMENDATION"
CONTEXT_COMPARISON = "COMPARISON"
CONTEXT_PRODUCT = "PRODUCT"
CONTEXT_DECODER = "DECODER"
CONTEXT_QA_ANSWER = "QA_ANSWER"
CONTEXT_CLAIMS = "CLAIMS"
CONTEXT_GENERAL = "GENERAL"

CONTEXT_TYPES = (
    CONTEXT_RECOMMENDATION,
    CONTEXT_COMPARISON,
    CONTEXT_PRODUCT,
    CONTEXT_DECODER,
    CONTEXT_QA_ANSWER,
    CONTEXT_CLAIMS,
    CONTEXT_GENERAL,
)

#: "Was this helpful" — the beta checklist's helpfulness signal.
RATING_HELPFUL = 1
RATING_NOT_HELPFUL = -1


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("fb"))
    #: Nullable per the data model: feedback can outlive an account.
    user_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    context_type: Mapped[str] = mapped_column(String(32), nullable=False)
    #: The run, policy or product it was about. An identifier we generated.
    context_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    #: 1 or -1. Null when someone left only a comment.
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())

    __table_args__ = (Index("ix_feedback_context", "context_type", "created_at"),)
