"""Recommendation payloads (docs/08_API_CONTRACTS.md section 4).

Two things are deliberately absent from every response:

* **any overall score.** docs/01_PRODUCT_SPEC.md section 2.5 forbids a 0–100
  consumer score, and the prototype ordering's internal value never leaves the
  server (docs/06_RECOMMENDATION_ENGINE.md section 7).
* **any premium.** The synthetic catalogue carries no price, and the price
  state says so rather than showing an invented number.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.core.schema import ApiModel
from app.matching.factors import FACTOR_LABELS, FitLabel
from app.recommendations.comparison import DimensionComparison
from app.recommendations.models import RecommendationCandidate
from app.recommendations.service import PRIMARY_MATCH_COUNT, ComparisonResult, RunResult

#: docs/01_PRODUCT_SPEC.md section 7 pricing states, plus the honest fourth
#: case: there is no price to show at all.
PriceState = Literal["INDICATIVE", "QUOTED", "FINAL", "UNAVAILABLE"]


class FitView(ApiModel):
    factor: str
    label: str
    fit: FitLabel
    note: str


class PriceView(ApiModel):
    """Never a bare number.

    docs/12_BETA_CHECKLIST.md requires every displayed premium to carry a
    state, a source and a timestamp. Synthetic products have no price, so the
    state is UNAVAILABLE and the UI says why.
    """

    state: PriceState
    amount: int | None = None
    currency: str | None = None
    source_type: str
    generated_at: datetime | None = None
    explanation: str


class MatchView(ApiModel):
    id: str
    product_reference: str
    insurer_name: str
    product_name: str
    #: SYNTHETIC for every Phase 5 product.
    source_type: str
    presentation_order: int
    eligibility_status: str
    #: The 3 strongest fit areas, as labels the reader can act on.
    highlights: list[FitView]
    #: Exactly one, always present.
    watch_out: str
    #: The full category fit, shown under "Why this matches".
    fits: list[FitView]
    price: PriceView

    @classmethod
    def of(cls, candidate: RecommendationCandidate) -> MatchView:
        payload = candidate.reason_summary_json
        fits_raw = payload.get("fits", [])
        highlight_factors = payload.get("highlightFactors", [])

        def to_view(entry: dict[str, str]) -> FitView:
            factor = entry["factor"]
            return FitView(
                factor=factor,
                label=FACTOR_LABELS.get(factor, factor),
                fit=entry["label"],
                note=entry["note"],
            )

        fits = [to_view(entry) for entry in fits_raw]
        by_factor = {fit.factor: fit for fit in fits}

        return cls(
            id=candidate.id,
            product_reference=candidate.product_reference,
            insurer_name=payload.get("insurerName", ""),
            product_name=payload.get("productName", ""),
            source_type=payload.get("sourceType", "SYNTHETIC"),
            presentation_order=candidate.presentation_order or 0,
            eligibility_status=candidate.eligibility_status,
            # Ordered by highlightFactors, not catalogue order: strongest_fits
            # puts the reader's own priorities first and that must survive.
            highlights=[by_factor[factor] for factor in highlight_factors if factor in by_factor],
            watch_out=payload.get("watchOut", ""),
            fits=fits,
            price=PriceView(
                state="UNAVAILABLE",
                source_type=payload.get("sourceType", "SYNTHETIC"),
                explanation=(
                    "These are demo products, so there is no price to show. "
                    "Real prices come from the insurer, never from us."
                ),
            ),
        )


class PriorityView(ApiModel):
    factor: str
    label: str
    level: str


class RunView(ApiModel):
    id: str
    status: str
    presentation_mode: str
    #: SYNTHETIC while the catalogue is synthetic — the UI labels the screen.
    source_type: str
    questionnaire_version: str
    #: Names the prototype ordering, not a scoring engine.
    scoring_version: str
    catalogue_version: str
    created_at: datetime
    #: "What we learned about you" — one statement per line.
    decision_profile: list[str]
    priorities: list[str]
    #: The first 5. docs/01_PRODUCT_SPEC.md section 2.5.
    matches: list[MatchView]
    #: The remaining 5, revealed by "See 5 more matches".
    additional_matches: list[MatchView]
    can_show_more: bool
    #: Product references that moved after a priority change, so the UI can
    #: explain why the order is different.
    reordered: list[str] = []
    #: The run this one replaced. A priority change creates a new run rather
    #: than editing the old one (docs/06_RECOMMENDATION_ENGINE.md section 11).
    previous_run_id: str | None = None
    #: How many products were assessed and not offered, and the rules that
    #: ruled them out. A count and reasons, never a list of rejected products:
    #: naming them would imply an assessment we deliberately did not make.
    excluded_count: int = 0
    exclusion_notes: list[str] = []

    @classmethod
    def of(cls, result: RunResult, *, reordered: list[str] | None = None) -> RunView:
        views = [MatchView.of(candidate) for candidate in result.candidates]
        return cls(
            id=result.run.id,
            status=result.run.status,
            presentation_mode=result.run.presentation_mode,
            source_type=result.run.source_type,
            questionnaire_version=result.run.questionnaire_version,
            scoring_version=result.run.scoring_version,
            catalogue_version=result.run.catalogue_version,
            created_at=result.run.created_at,
            decision_profile=result.decision_profile,
            priorities=result.priorities,
            matches=views[:PRIMARY_MATCH_COUNT],
            additional_matches=views[PRIMARY_MATCH_COUNT:],
            can_show_more=len(views) > PRIMARY_MATCH_COUNT,
            reordered=reordered or [],
            previous_run_id=result.run.previous_run_id,
            excluded_count=result.run.excluded_count,
            exclusion_notes=result.exclusion_notes,
        )


class CreateRunRequest(ApiModel):
    questionnaire_session_id: str


class UpdatePrioritiesRequest(ApiModel):
    """docs/08_API_CONTRACTS.md section 4 sends factor/level pairs.

    The client sends the chosen priority keys. Levels are derived rather than
    sent: the questionnaire's model is "up to three things that matter most",
    so a listed priority is TOP and everything else is BASELINE
    (`app.matching.weights`). A client cannot set its own weights.
    """

    priorities: list[str]


class DimensionView(ApiModel):
    """One fit dimension across the compared options.

    `values` and `notes` are keyed by product reference. No numeric spread is
    exposed: how far apart the labels are decides the order, and the order is
    the answer — a difference "size" on screen would be a score by another
    name.
    """

    factor: str
    label: str
    values: dict[str, FitLabel]
    notes: dict[str, str]
    differs: bool
    is_priority: bool


class ComparisonOptionView(ApiModel):
    product_reference: str
    insurer_name: str
    product_name: str
    source_type: str
    watch_out: str


class ComparisonView(ApiModel):
    """docs/02_UX_UI_SPEC.md section 10 order: differences, priorities, details."""

    run_id: str
    source_type: str
    options: list[ComparisonOptionView]
    priorities: list[str]
    biggest_differences: list[DimensionView]
    your_priorities: list[DimensionView]
    all_details: list[DimensionView]

    @classmethod
    def of(cls, result: ComparisonResult) -> ComparisonView:
        def dimension(entry: DimensionComparison) -> DimensionView:
            return DimensionView(
                factor=entry.factor,
                label=entry.label,
                values=entry.values,
                notes=entry.notes,
                differs=entry.differs,
                is_priority=entry.is_priority,
            )

        return cls(
            run_id=result.run.id,
            source_type=result.run.source_type,
            options=[
                ComparisonOptionView(
                    product_reference=candidate.product_reference,
                    insurer_name=candidate.reason_summary_json.get("insurerName", ""),
                    product_name=candidate.reason_summary_json.get("productName", ""),
                    source_type=candidate.reason_summary_json.get("sourceType", "SYNTHETIC"),
                    watch_out=candidate.reason_summary_json.get("watchOut", ""),
                )
                for candidate in result.options
            ],
            priorities=result.priorities,
            biggest_differences=[dimension(entry) for entry in result.differences],
            your_priorities=[dimension(entry) for entry in result.priority_view],
            all_details=[dimension(entry) for entry in result.all_dimensions],
        )


class CreateComparisonRequest(ApiModel):
    """docs/08_API_CONTRACTS.md section 6.

    The contract names `productVersionIds`. Product versions arrive in
    Phase 8; until then the identifiers are synthetic product references, so
    the field is named for what it actually carries. Recorded in
    docs/SPEC_ISSUES.md.
    """

    recommendation_run_id: str
    product_references: list[str]
