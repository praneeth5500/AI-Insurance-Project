"""Producing a match set.

docs/04_BACKEND_ARCHITECTURE.md section 4:

    completed answers -> priorities -> product provider
      -> deterministic matching -> persisted run -> presentation-safe result

The matching itself lives in `app.matching`; this module's job is the
boundary. Three rules shape it:

* **A run is a record, not a working document.** Changing priorities produces
  a *new* run pointing back at the old one. Nothing here updates a stored
  result — CLAUDE.md rule 10, and the models refuse it at the mapper level if
  something tries.
* **Products come from a provider.** The synthetic catalogue and imported
  verified data reach the engine through one interface, so switching to real
  data is configuration rather than a rewrite.
* **The internal relevance value stays here.** It is persisted for audit and
  used to order; it is never placed on a response schema.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import service as analytics
from app.analytics.events import PRIORITY_CHANGED, RECOMMENDATION_GENERATED
from app.core.logging import log_fields
from app.db.types import new_id
from app.matching.eligibility import EXCLUSION_REASON_LABELS
from app.matching.engine import MatchResult, MatchSet, run_match
from app.matching.profile import UserProfile, build_profile
from app.matching.weights import EXPLANATION_VERSION, HEALTH_BETA_001
from app.products.catalogue import CATALOGUE_VERSION, get_product
from app.products.provenance import SYNTHETIC
from app.products.provider import ProviderProduct, SyntheticCatalogueProvider
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
    ELIGIBILITY_ELIGIBLE,
    ELIGIBILITY_EXCLUDED,
    PRESENTATION_BETA_MATCH_SET,
    STATUS_READY,
    FitComponent,
    RecommendationCandidate,
    RecommendationRun,
)
from app.recommendations.pricing_lookup import annual_prices_inr
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

    @property
    def exclusion_notes(self) -> list[str]:
        """Plain-language reasons some options were not offered."""
        return [
            EXCLUSION_REASON_LABELS[reason]
            for reason in self.run.exclusion_reasons_json
            if reason in EXCLUSION_REASON_LABELS
        ]


def _candidate_payload(result: MatchResult) -> dict[str, object]:
    """The presentation-ready summary stored on the candidate.

    Everything a card or detail page needs, frozen at the moment of the run,
    so a historical result renders exactly as it did then even if the
    catalogue has moved on since.
    """
    return {
        "insurerName": result.product.insurer_name,
        "productName": result.product.product_name,
        "sourceType": result.product.source_type,
        "versionLabel": result.product.version_label,
        "highlightFactors": list(result.highlights),
        "watchOut": _watch_out(result.product),
        "fits": [
            {
                "factor": scored.result.factor_key,
                "label": scored.result.label,
                "note": scored.result.note,
            }
            for scored in result.fits
        ],
    }


def _watch_out(product: ProviderProduct) -> str:
    """The one thing to be aware of.

    Authored per product for the synthetic catalogue. Verified products have
    none yet — and an empty string is the honest answer rather than a
    generated warning about a policy we have not read.
    """
    synthetic = get_product(product.reference)
    return synthetic.watch_out if synthetic else ""


async def _persist(
    db: AsyncSession, run: RecommendationRun, match_set: MatchSet
) -> list[RecommendationCandidate]:
    """Write the assessed products and their evidence.

    Excluded products are stored too, with no presentation order. They never
    reach a screen; they are what lets the run explain what it left out.

    Candidates are flushed before their fit components: there is no ORM
    relationship between the two tables, so nothing else would guarantee the
    rows the foreign key points at exist first.
    """
    candidates: list[RecommendationCandidate] = []
    components: list[tuple[RecommendationCandidate, MatchResult]] = []

    for index, result in enumerate(match_set.matched[:MAX_MATCH_COUNT]):
        candidate = RecommendationCandidate(
            # Assigned here, not left to the column default: the fit components
            # below reference it and defaults only run at flush time.
            id=new_id("rc"),
            recommendation_run_id=run.id,
            product_reference=result.product.reference,
            product_version_id=(
                result.product.reference if result.product.source_type != SYNTHETIC else None
            ),
            eligibility_status=ELIGIBILITY_ELIGIBLE,
            exclusion_reasons_json=[],
            internal_relevance_value=result.relevance,
            internal_order=index,
            presentation_order=index,
            reason_summary_json=_candidate_payload(result),
        )
        candidates.append(candidate)
        db.add(candidate)
        components.append((candidate, result))

    for result in match_set.excluded:
        excluded = RecommendationCandidate(
            recommendation_run_id=run.id,
            product_reference=result.product.reference,
            product_version_id=(
                result.product.reference if result.product.source_type != SYNTHETIC else None
            ),
            eligibility_status=ELIGIBILITY_EXCLUDED,
            exclusion_reasons_json=list(result.eligibility.reasons),
            internal_relevance_value=result.relevance,
            internal_order=None,
            presentation_order=None,
            reason_summary_json=_candidate_payload(result),
        )
        db.add(excluded)

    await db.flush()
    for candidate, result in components:
        _persist_fit_components(db, candidate, result)

    return candidates


def _persist_fit_components(
    db: AsyncSession, candidate: RecommendationCandidate, result: MatchResult
) -> None:
    for scored in result.fits:
        db.add(
            FitComponent(
                candidate_id=candidate.id,
                factor_key=scored.result.factor_key,
                normalized_score=scored.result.normalized_score,
                label=scored.result.label,
                user_priority_level=scored.priority_level,
                # Hard requirements remove the product outright, so no fit
                # dimension is ever one.
                hard_requirement=False,
                evidence_json=[item.as_json() for item in scored.result.evidence],
            )
        )


async def _load_products(db: AsyncSession) -> list[ProviderProduct]:
    """The catalogue to match against.

    Synthetic today. Swapping in `VerifiedCatalogueProvider` is the only
    change needed once verified data has been imported — which is why the
    engine never touches the catalogue directly.
    """
    provider = SyntheticCatalogueProvider()
    return await provider.list_products(domain="HEALTH")


async def _create(
    db: AsyncSession,
    *,
    user: User,
    session_id: str,
    questionnaire_version: str,
    domain: str,
    profile: UserProfile,
    previous_run_id: str | None,
) -> tuple[RecommendationRun, list[RecommendationCandidate]]:
    products = await _load_products(db)
    prices = await annual_prices_inr(db, [product.reference for product in products])
    match_set = run_match(products, profile, config=HEALTH_BETA_001, prices_inr=prices)

    run = RecommendationRun(
        user_id=user.id,
        questionnaire_session_id=session_id,
        previous_run_id=previous_run_id,
        domain=domain,
        questionnaire_version=questionnaire_version,
        scoring_version=match_set.scoring_version,
        explanation_version=EXPLANATION_VERSION,
        catalogue_version=CATALOGUE_VERSION,
        source_type=SYNTHETIC,
        presentation_mode=PRESENTATION_BETA_MATCH_SET,
        status=STATUS_READY,
        priorities_json=list(profile.priorities),
        excluded_count=len(match_set.excluded),
        exclusion_reasons_json=list(match_set.exclusion_reasons),
    )
    db.add(run)
    await db.flush()

    candidates = await _persist(db, run, match_set)
    await db.flush()
    await analytics.record_safely(
        db,
        name=RECOMMENDATION_GENERATED,
        user=user,
        properties={
            "domain": domain,
            "match_count": len(candidates),
            "excluded_count": len(match_set.excluded),
            "scoring_version": match_set.scoring_version,
        },
    )
    await db.commit()
    return run, candidates


async def create_run(db: AsyncSession, *, user: User, questionnaire_session_id: str) -> RunResult:
    """Turn a completed questionnaire into a match set."""
    state = await questionnaire_service.load_state(
        db, user=user, session_id=questionnaire_session_id
    )
    if state.session.status != STATUS_COMPLETED:
        raise QuestionnaireNotCompleteError

    profile = build_profile(state.answers)
    run, candidates = await _create(
        db,
        user=user,
        session_id=state.session.id,
        questionnaire_version=state.session.questionnaire_version,
        domain=state.session.domain,
        profile=profile,
        previous_run_id=None,
    )

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
        priorities=list(profile.priorities),
    )


async def _load_candidates(
    db: AsyncSession, run_id: str, *, presented_only: bool = True
) -> list[RecommendationCandidate]:
    query = select(RecommendationCandidate).where(
        RecommendationCandidate.recommendation_run_id == run_id
    )
    if presented_only:
        query = query.where(RecommendationCandidate.presentation_order.is_not(None))
    query = query.order_by(RecommendationCandidate.presentation_order)
    return list((await db.execute(query)).scalars().all())


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

    return RunResult(
        run=run,
        candidates=await _load_candidates(db, run.id),
        decision_profile=build_decision_profile(state.answers),
        # The priorities this run was produced with, not whatever the
        # questionnaire says now. A run explains itself.
        priorities=list(run.priorities_json),
    )


async def update_priorities(
    db: AsyncSession, *, user: User, run_id: str, priorities: list[str]
) -> tuple[RunResult, list[str]]:
    """Re-match against changed priorities, as a new run.

    docs/06_RECOMMENDATION_ENGINE.md section 10: update the structured
    priority, re-run deterministic matching, persist, let the UI reorder. What
    is persisted is a *new* run — section 11 freezes a completed one, and
    CLAUDE.md rule 10 forbids rewriting a result after the fact. The previous
    order comes back alongside so the UI can say what changed
    (docs/02_UX_UI_SPEC.md section 9).
    """
    before = await get_run(db, user=user, run_id=run_id)
    previous_order = [candidate.product_reference for candidate in before.candidates]

    state = await questionnaire_service.load_state(
        db, user=user, session_id=before.run.questionnaire_session_id
    )
    profile = build_profile({**state.answers, "priorities": priorities})

    run, candidates = await _create(
        db,
        user=user,
        session_id=before.run.questionnaire_session_id,
        questionnaire_version=before.run.questionnaire_version,
        domain=before.run.domain,
        profile=profile,
        previous_run_id=before.run.id,
    )

    await analytics.record_safely(
        db,
        name=PRIORITY_CHANGED,
        user=user,
        # How many, never which: a priority is something the reader told us
        # about themselves.
        properties={"domain": before.run.domain, "priority_count": len(priorities)},
    )
    await db.commit()

    logger.info(
        "recommendation_priorities_updated",
        extra=log_fields(
            event="recommendation_priorities_updated",
            user_id=user.id,
            resource_type="recommendation_run",
            resource_id=run.id,
        ),
    )

    return (
        RunResult(
            run=run,
            candidates=candidates,
            decision_profile=before.decision_profile,
            priorities=list(priorities),
        ),
        previous_order,
    )


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


async def candidate_in_run(
    db: AsyncSession, *, user: User, run_id: str, product_reference: str
) -> RecommendationCandidate | None:
    """One assessed option from a run, for the detail screen.

    The detail page shows the fit this run recorded rather than recomputing
    it, so a card and the page behind it can never disagree — and a run opened
    later shows what it said at the time.
    """
    run = (
        await db.execute(
            select(RecommendationRun).where(
                RecommendationRun.id == run_id, RecommendationRun.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if run is None:
        return None

    return (
        await db.execute(
            select(RecommendationCandidate).where(
                RecommendationCandidate.recommendation_run_id == run_id,
                RecommendationCandidate.product_reference == product_reference,
                RecommendationCandidate.presentation_order.is_not(None),
            )
        )
    ).scalar_one_or_none()


__all__ = [
    "MAX_COMPARISON",
    "MAX_MATCH_COUNT",
    "MIN_COMPARISON",
    "PRIMARY_MATCH_COUNT",
    "ComparisonResult",
    "RunResult",
    "candidate_in_run",
    "compare",
    "create_run",
    "get_run",
    "update_priorities",
]
