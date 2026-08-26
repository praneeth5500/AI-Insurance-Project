"""Recommendation tables (docs/05_DATA_MODEL.md section 6).

A run is a **record of what we told someone, and why**. That framing decides
the shape of everything here:

* Every input that could change the answer is stored on the run — the
  questionnaire version, the scoring version, the catalogue version, the
  explanation version, the data mode. Reading a run six months later should
  not require guessing which engine produced it
  (docs/06_RECOMMENDATION_ENGINE.md section 11).
* Fit components hold the per-dimension judgement *and its evidence*, so the
  question "why did it say that?" has an answer that does not depend on
  re-running anything.
* **Runs are immutable.** CLAUDE.md rule 10: never rewrite historical
  recommendation results after the fact. Changing priorities creates a new
  run that points back at the one before it; the earlier run keeps saying
  exactly what it said at the time. A mapper-level guard turns an accidental
  in-place edit into an error rather than a silent rewrite.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Float, ForeignKey, Index, Integer, String, event, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Mapper, mapped_column
from sqlalchemy.orm.attributes import get_history

from app.db.base import Base
from app.db.types import new_id, timestamp_column

#: docs/08_API_CONTRACTS.md section 4 returns a presentation mode.
PRESENTATION_BETA_MATCH_SET = "BETA_MATCH_SET"

STATUS_READY = "READY"

ELIGIBILITY_ELIGIBLE = "ELIGIBLE"
ELIGIBILITY_EXCLUDED = "EXCLUDED"


class ImmutableRunError(RuntimeError):
    """Raised when something tries to change a stored recommendation result."""


class RecommendationRun(Base):
    __tablename__ = "recommendation_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("rr"))
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    questionnaire_session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("questionnaire_sessions.id", ondelete="CASCADE"), nullable=False
    )
    #: The run this one replaced, when the reader changed their priorities.
    #: The earlier run is untouched — this is the only link between them.
    previous_run_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("recommendation_runs.id", ondelete="SET NULL"), nullable=True
    )
    domain: Mapped[str] = mapped_column(String(16), nullable=False)
    questionnaire_version: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Which scoring configuration produced this result set.
    scoring_version: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Which wording the reader actually saw.
    explanation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Which product catalogue was used, so a result set can be explained.
    catalogue_version: Mapped[str] = mapped_column(String(64), nullable=False)
    #: SYNTHETIC while the catalogue is synthetic. Surfaced to the UI.
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    presentation_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default=PRESENTATION_BETA_MATCH_SET
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_READY)
    #: The reader's priorities at the moment this run was produced. Stored on
    #: the run rather than read back from the questionnaire, because the
    #: questionnaire can change and this run cannot.
    priorities_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    #: How many products were assessed and not offered, and why. A count and
    #: rule-level reasons — never a list of rejected products, which would
    #: imply an assessment we deliberately did not make.
    excluded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exclusion_reasons_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    #: When the result set was frozen. Equal to created_at today; separate
    #: because a run that becomes asynchronous later will freeze after it
    #: starts (docs/08_API_CONTRACTS.md returns PROCESSING first).
    frozen_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())

    __table_args__ = (Index("ix_recommendation_runs_user", "user_id"),)


class RecommendationCandidate(Base):
    """One product as assessed within a run.

    Excluded products are kept too, with no presentation order. They are never
    shown, but a run that cannot say what it left out cannot explain itself.
    """

    __tablename__ = "recommendation_candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("rc"))
    recommendation_run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("recommendation_runs.id", ondelete="CASCADE"), nullable=False
    )
    #: The provider reference — a synthetic product id, or a product version id
    #: for verified data.
    product_reference: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Set only for verified data, so a run can be traced to the exact wording
    #: it was matched against.
    product_version_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("product_versions.id", ondelete="SET NULL"), nullable=True
    )
    eligibility_status: Mapped[str] = mapped_column(String(24), nullable=False)
    #: Populated for excluded candidates. Internal rule codes.
    exclusion_reasons_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    #: docs/06_RECOMMENDATION_ENGINE.md section 7: the consumer UI never sees
    #: this. Stored so an ordering can be explained after the fact, and never
    #: placed on a response schema.
    internal_relevance_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    internal_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: Null for excluded candidates, which are not presented at all.
    presentation_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: Names, highlighted factors and the watch-out — the presentation-ready
    #: summary. The per-dimension reasoning lives in `fit_components`.
    reason_summary_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        Index("ix_recommendation_candidates_run", "recommendation_run_id", "presentation_order"),
    )


class FitComponent(Base):
    """One dimension's judgement, with what it was based on.

    docs/05_DATA_MODEL.md names this table and docs/06_RECOMMENDATION_ENGINE.md
    section 7 names its contents. It is the audit trail: given a component
    row, the label can be re-derived from the evidence without the engine.
    """

    __tablename__ = "fit_components"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("fc"))
    candidate_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("recommendation_candidates.id", ondelete="CASCADE"), nullable=False
    )
    factor_key: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Null when the dimension had no verified data. Null is not zero: a null
    #: score is left out of the relevance calculation entirely.
    normalized_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    label: Mapped[str] = mapped_column(String(24), nullable=False)
    #: BASELINE, TOP or MUST_HAVE at the time of the run.
    user_priority_level: Mapped[str] = mapped_column(String(16), nullable=False)
    #: Whether this dimension was a pass/fail requirement rather than a
    #: weighted preference. False for every fit dimension: hard requirements
    #: are handled by eligibility, which removes the product outright.
    hard_requirement: Mapped[bool] = mapped_column(nullable=False, default=False)
    #: The explanation evidence objects.
    evidence_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)

    __table_args__ = (Index("ix_fit_components_candidate", "candidate_id"),)


def _refuse_update(mapper: Mapper[Any], connection: Any, target: Any) -> None:
    """Turn an in-place edit of a stored result into a loud failure.

    This is an application-level guarantee, not a database one: it catches the
    realistic mistake — code that loads a candidate and adjusts it — which is
    exactly how a historical result gets quietly rewritten. A new run is
    always the right answer instead.
    """
    changed = [
        attribute.key
        for attribute in mapper.column_attrs
        if get_history(target, attribute.key).has_changes()
    ]
    if changed:
        raise ImmutableRunError(
            f"{type(target).__name__} is part of a completed recommendation run and cannot be "
            f"changed (attempted: {', '.join(sorted(changed))}). Create a new run instead."
        )


event.listen(RecommendationCandidate, "before_update", _refuse_update)
event.listen(FitComponent, "before_update", _refuse_update)
event.listen(RecommendationRun, "before_update", _refuse_update)
