"""Recommendation tables (docs/05_DATA_MODEL.md section 6).

Phase 5 persists the run and its candidates so a result set has a stable URL
and appears on the home screen. Two things from the data model are
deliberately absent until Phase 9:

* `fit_components` — the per-factor evidence rows. In Phase 5 the fit labels
  are authored fixture content rather than computed evidence, so storing them
  as if they were evidence would misrepresent them. They live in
  `reason_summary_json` instead.
* Immutability. docs/06_RECOMMENDATION_ENGINE.md section 11 freezes a
  *completed* run; a Phase 5 run is an exploratory draft that the priority
  editor reorders in place, which section 10 explicitly allows.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import new_id, timestamp_column

#: docs/08_API_CONTRACTS.md section 4 returns a presentation mode.
PRESENTATION_BETA_MATCH_SET = "BETA_MATCH_SET"

STATUS_READY = "READY"


class RecommendationRun(Base):
    __tablename__ = "recommendation_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("rr"))
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    questionnaire_session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("questionnaire_sessions.id", ondelete="CASCADE"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(16), nullable=False)
    questionnaire_version: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Which ordering produced this result set. In Phase 5 this names the
    #: prototype ordering, never a scoring engine.
    scoring_version: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Which product catalogue was used, so a result set can be explained.
    catalogue_version: Mapped[str] = mapped_column(String(64), nullable=False)
    #: SYNTHETIC while the catalogue is synthetic. Surfaced to the UI.
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    presentation_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default=PRESENTATION_BETA_MATCH_SET
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_READY)
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = timestamp_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_recommendation_runs_user", "user_id"),)


class RecommendationCandidate(Base):
    """One matched option within a run."""

    __tablename__ = "recommendation_candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("rc"))
    recommendation_run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("recommendation_runs.id", ondelete="CASCADE"), nullable=False
    )
    #: The synthetic product id. Becomes a product_version_id in Phase 8.
    product_reference: Mapped[str] = mapped_column(String(64), nullable=False)
    eligibility_status: Mapped[str] = mapped_column(String(24), nullable=False)
    presentation_order: Mapped[int] = mapped_column(Integer, nullable=False)
    #: Fit labels, highlighted factors and the watch-out. Prototype content —
    #: see the module docstring.
    reason_summary_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        Index("ix_recommendation_candidates_run", "recommendation_run_id", "presentation_order"),
    )
