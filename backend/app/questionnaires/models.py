"""Questionnaire tables (docs/05_DATA_MODEL.md sections 2 and 3)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import new_id, timestamp_column

STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_COMPLETED = "COMPLETED"


class QuestionnaireSession(Base):
    """One person's pass through one questionnaire version.

    The version is recorded on the session, so a completed session can always
    be replayed against the exact questions that produced it
    (docs/04_BACKEND_ARCHITECTURE.md section 9).
    """

    __tablename__ = "questionnaire_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("qs"))
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(16), nullable=False)
    questionnaire_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_IN_PROGRESS)
    started_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = timestamp_column(nullable=True)

    __table_args__ = (Index("ix_questionnaire_sessions_user_domain", "user_id", "domain"),)


class QuestionnaireAnswer(Base):
    """A single answer.

    `sensitive` mirrors the question definition
    (docs/05_DATA_MODEL.md section 2: "Sensitive fields must be flagged in
    metadata"), so anything reading answers can tell what must never be logged
    or sent to analytics without consulting the definition.
    """

    __tablename__ = "questionnaire_answers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("qa"))
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("questionnaire_sessions.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[str] = mapped_column(String(64), nullable=False)
    answer_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = timestamp_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        # One answer per question per session: re-answering updates in place,
        # so the draft never accumulates conflicting values.
        UniqueConstraint("session_id", "question_id", name="uq_answer_session_question"),
    )


class PriorityProfile(Base):
    """The user's chosen priorities for one session (docs/05_DATA_MODEL.md section 3)."""

    __tablename__ = "priority_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("pp"))
    questionnaire_session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("questionnaire_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    domain: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())


class PriorityItem(Base):
    """One chosen priority.

    `rank_order` preserves the order they were chosen in. Weighting lives in
    versioned scoring configuration, not here
    (docs/06_RECOMMENDATION_ENGINE.md section 6).
    """

    __tablename__ = "priority_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("pi"))
    priority_profile_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("priority_profiles.id", ondelete="CASCADE"), nullable=False
    )
    factor_key: Mapped[str] = mapped_column(String(64), nullable=False)
    priority_level: Mapped[str] = mapped_column(String(16), nullable=False)
    rank_order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("priority_profile_id", "factor_key", name="uq_priority_profile_factor"),
    )
