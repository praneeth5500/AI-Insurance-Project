"""Producing a match set.

The pipeline is a deliberately thin stand-in for the one in
docs/04_BACKEND_ARCHITECTURE.md section 4:

    completed answers -> priorities -> synthetic catalogue
      -> prototype ordering -> persisted run -> presentation-safe result

Hard eligibility filtering, fit evaluators and versioned weighting are Phase 9.
Nothing here computes a score that reaches the screen, and no LLM participates.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log_fields
from app.products.catalogue import CATALOGUE_VERSION, SyntheticProduct, all_products, get_product
from app.products.provenance import SYNTHETIC
from app.questionnaires import service as questionnaire_service
from app.questionnaires.models import STATUS_COMPLETED
from app.recommendations.comparison import (
    DimensionComparison,
    biggest_differences,
    build_dimensions,
    priority_dimensions,
)
from app.recommendations.errors import (
    ComparisonOptionNotInRunError,
    QuestionnaireNotCompleteError,
    RecommendationRunNotFoundError,
    TooFewComparisonsError,
    TooManyComparisonsError,
)
from app.recommendations.models import (
    PRESENTATION_BETA_MATCH_SET,
    STATUS_READY,
    RecommendationCandidate,
    RecommendationRun,
)
from app.recommendations.ordering import ORDERING_VERSION, order_products, strongest_fits
from app.recommendations.profile import build_decision_profile
from app.users.models import User

logger = logging.getLogger(__name__)

#: docs/01_PRODUCT_SPEC.md section 2.5: 5 primary options, then "see 5 more".
PRIMARY_MATCH_COUNT = 5
MAX_MATCH_COUNT = 10


@dataclass(frozen=True)
class RunResult:
    run: RecommendationRun
    candidates: list[RecommendationCandidate]
    decision_profile: list[str]
    priorities: list[str]


def _priorities_from(answers: dict[str, Any]) -> list[str]:
    chosen = answers.get("priorities")
    return [item for item in chosen if isinstance(item, str)] if isinstance(chosen, list) else []


def _candidate_payload(product: SyntheticProduct, priorities: list[str]) -> dict[str, Any]:
    return {
        "insurerName": product.insurer_name,
        "productName": product.product_name,
        "sourceType": product.source_type,
        "highlightFactors": strongest_fits(product, priorities),
        "watchOut": product.watch_out,
        "fits": [
            {"factor": fit.factor, "label": fit.label, "note": fit.note} for fit in product.fits
        ],
    }


async def _build_candidates(
    db: AsyncSession, run: RecommendationRun, priorities: list[str]
) -> list[RecommendationCandidate]:
    """Replace the run's candidates with a freshly ordered set."""
    await db.execute(
        delete(RecommendationCandidate).where(
            RecommendationCandidate.recommendation_run_id == run.id
        )
    )

    ordered = order_products(all_products(), priorities)[:MAX_MATCH_COUNT]
    candidates = [
        RecommendationCandidate(
            recommendation_run_id=run.id,
            product_reference=product.id,
            # Hard eligibility is Phase 9; every synthetic product is offered
            # and labelled as not yet assessed rather than as "eligible".
            eligibility_status="NOT_ASSESSED",
            presentation_order=index,
            reason_summary_json=_candidate_payload(product, priorities),
        )
        for index, product in enumerate(ordered)
    ]
    db.add_all(candidates)
    await db.flush()
    return candidates


async def create_run(db: AsyncSession, *, user: User, questionnaire_session_id: str) -> RunResult:
    """Turn a completed questionnaire into a match set."""
    state = await questionnaire_service.load_state(
        db, user=user, session_id=questionnaire_session_id
    )
    if state.session.status != STATUS_COMPLETED:
        raise QuestionnaireNotCompleteError

    priorities = _priorities_from(state.answers)

    run = RecommendationRun(
        user_id=user.id,
        questionnaire_session_id=state.session.id,
        domain=state.session.domain,
        questionnaire_version=state.session.questionnaire_version,
        scoring_version=ORDERING_VERSION,
        catalogue_version=CATALOGUE_VERSION,
        source_type=SYNTHETIC,
        presentation_mode=PRESENTATION_BETA_MATCH_SET,
        status=STATUS_READY,
    )
    db.add(run)
    await db.flush()

    candidates = await _build_candidates(db, run, priorities)
    await db.commit()

    logger.info(
        "recommendation_run_created",
        extra=log_fields(
            event="recommendation_run_created",
            user_id=user.id,
            resource_type="recommendation_run",
            resource_id=run.id,
        ),
    )
    return RunResult(
        run=run,
        candidates=candidates,
        decision_profile=build_decision_profile(state.answers),
        priorities=priorities,
    )


async def get_run(db: AsyncSession, *, user: User, run_id: str) -> RunResult:
    run = (
        await db.execute(
            select(RecommendationRun).where(
                RecommendationRun.id == run_id, RecommendationRun.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if run is None:
        raise RecommendationRunNotFoundError

    state = await questionnaire_service.load_state(
        db, user=user, session_id=run.questionnaire_session_id
    )
    candidates = list(
        (
            await db.execute(
                select(RecommendationCandidate)
                .where(RecommendationCandidate.recommendation_run_id == run.id)
                .order_by(RecommendationCandidate.presentation_order)
            )
        )
        .scalars()
        .all()
    )

    return RunResult(
        run=run,
        candidates=candidates,
        decision_profile=build_decision_profile(state.answers),
        priorities=_priorities_from(state.answers),
    )


async def update_priorities(
    db: AsyncSession, *, user: User, run_id: str, priorities: list[str]
) -> tuple[RunResult, list[str]]:
    """Reorder a run against changed priorities.

    docs/06_RECOMMENDATION_ENGINE.md section 10: update the structured
    priority, re-run deterministic matching, persist, let the UI reorder. The
    previous order is returned alongside so the UI can say *what* changed —
    docs/02_UX_UI_SPEC.md section 9 requires a changed priority to visibly
    explain why the results moved.
    """
    before = await get_run(db, user=user, run_id=run_id)
    previous_order = [candidate.product_reference for candidate in before.candidates]

    candidates = await _build_candidates(db, before.run, priorities)
    await db.commit()

    logger.info(
        "recommendation_priorities_updated",
        extra=log_fields(
            event="recommendation_priorities_updated",
            user_id=user.id,
            resource_type="recommendation_run",
            resource_id=run_id,
        ),
    )

    return (
        RunResult(
            run=before.run,
            candidates=candidates,
            decision_profile=before.decision_profile,
            priorities=priorities,
        ),
        previous_order,
    )


def product_for(candidate: RecommendationCandidate) -> SyntheticProduct | None:
    return get_product(candidate.product_reference)


#: docs/01_PRODUCT_SPEC.md section 2.7 and docs/02_UX_UI_SPEC.md section 10.
MIN_COMPARISON = 2
MAX_COMPARISON = 3


@dataclass(frozen=True)
class ComparisonResult:
    run: RecommendationRun
    options: list[RecommendationCandidate]
    priorities: list[str]
    differences: list[DimensionComparison]
    priority_view: list[DimensionComparison]
    all_dimensions: list[DimensionComparison]


async def compare(
    db: AsyncSession, *, user: User, run_id: str, product_references: list[str]
) -> ComparisonResult:
    """Compare 2 or 3 options from a run.

    The limit is enforced here rather than only in the UI: the beta checklist
    requires "Compare max 3", and a client is not the place to guarantee it.
    """
    # Deduplicate while preserving the order the user picked them in.
    references = list(dict.fromkeys(product_references))

    if len(references) < MIN_COMPARISON:
        raise TooFewComparisonsError
    if len(references) > MAX_COMPARISON:
        raise TooManyComparisonsError

    result = await get_run(db, user=user, run_id=run_id)
    by_reference = {candidate.product_reference: candidate for candidate in result.candidates}

    missing = [reference for reference in references if reference not in by_reference]
    if missing:
        raise ComparisonOptionNotInRunError

    options = [by_reference[reference] for reference in references]

    fits_by_product: dict[str, dict[str, tuple[str, str]]] = {
        candidate.product_reference: {
            entry["factor"]: (entry["label"], entry["note"])
            for entry in candidate.reason_summary_json.get("fits", [])
        }
        for candidate in options
    }

    dimensions = build_dimensions(fits_by_product, result.priorities)

    logger.info(
        "comparison_built",
        extra=log_fields(
            event="comparison_built",
            user_id=user.id,
            resource_type="recommendation_run",
            resource_id=run_id,
        ),
    )

    return ComparisonResult(
        run=result.run,
        options=options,
        priorities=result.priorities,
        differences=biggest_differences(dimensions),
        priority_view=priority_dimensions(dimensions),
        all_dimensions=dimensions,
    )
