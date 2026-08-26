"""The matching engine.

docs/06_RECOMMENDATION_ENGINE.md section 2 fixes the pipeline, and this module
runs it end to end:

    user facts + priorities + product facts
      -> hard eligibility
      -> fit evaluators
      -> priority weighting
      -> internal relevance value
      -> matched option set

Four properties are load-bearing, and each has tests:

* **Deterministic.** The same answers, priorities and product facts always
  produce the same result, including the order. Ties break on the product
  reference so nothing shuffles between requests.
* **No LLM.** Not here and not upstream. CLAUDE.md: the model never generates
  the ranking. The evidence objects this produces are what an explanation
  model will later be *given*, not something it may replace.
* **Unknown never becomes average.** A dimension with no verified fact scores
  `None` and is left out of both halves of the relevance fraction. A product
  with no verified fit data at all is excluded rather than floated on
  emptiness.
* **The internal value never leaves the server.** It is persisted for audit
  and used for ordering; `docs/01_PRODUCT_SPEC.md` section 2.5 forbids showing
  a consumer score, so nothing here reaches a response schema.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.matching import factors
from app.matching.eligibility import (
    CRITICAL_DATA_UNUSABLE,
    NO_VERIFIED_FIT_DATA,
    EligibilityResult,
    assess,
)
from app.matching.evaluators import EVALUATORS, FitResult, evaluate_budget
from app.matching.factors import PRIORITY_TO_FACTOR
from app.matching.profile import UserProfile
from app.matching.weights import BASELINE, HEALTH_BETA_001, TOP, PriorityLevel, ScoringConfig
from app.products.facts import FactsUnusableError, HealthFacts, parse_health_facts
from app.products.provider import ProviderProduct

#: How many strengths a match card headlines
#: (docs/01_PRODUCT_SPEC.md section 2.5).
HIGHLIGHT_COUNT = 3

#: Only a genuine strength is ever called one.
_HIGHLIGHT_LABELS = ("STRONG", "GOOD")

#: Ordering value for each label, used to pick which strengths to headline.
_LABEL_RANK: dict[str, int] = {
    "STRONG": 3,
    "GOOD": 2,
    "TRADE_OFF": 1,
    "NEEDS_ATTENTION": 0,
    "UNVERIFIED": 0,
}


@dataclass(frozen=True)
class ScoredFit:
    """A fit result together with the weight it carried for this reader."""

    result: FitResult
    priority_level: PriorityLevel
    weight: float


@dataclass(frozen=True)
class MatchResult:
    """One product, assessed for one person."""

    product: ProviderProduct
    eligibility: EligibilityResult
    fits: tuple[ScoredFit, ...]
    #: 0..1. `None` when nothing could be assessed. Internal — see the module
    #: docstring.
    relevance: float | None
    #: The factors to headline, strongest first, the reader's own priorities
    #: ahead of everything else.
    highlights: tuple[str, ...]

    @property
    def eligible(self) -> bool:
        return self.eligibility.eligible

    def fit(self, factor_key: str) -> FitResult | None:
        return next((s.result for s in self.fits if s.result.factor_key == factor_key), None)


@dataclass(frozen=True)
class MatchSet:
    """Everything one run of the engine produced."""

    scoring_version: str
    matched: tuple[MatchResult, ...]
    excluded: tuple[MatchResult, ...]

    @property
    def exclusion_reasons(self) -> tuple[str, ...]:
        """Distinct reasons, in a stable order, for telling the reader why."""
        seen: list[str] = []
        for result in self.excluded:
            for reason in result.eligibility.reasons:
                if reason not in seen:
                    seen.append(reason)
        return tuple(seen)


def _priority_levels(profile: UserProfile) -> dict[str, PriorityLevel]:
    """Which dimensions this reader said mattered.

    docs/06_RECOMMENDATION_ENGINE.md section 6: the chosen top priorities get
    stronger weight, everything verified keeps the baseline. Nothing is
    inferred about priorities they did not choose.
    """
    levels: dict[str, PriorityLevel] = dict.fromkeys(factors.FACTOR_ORDER, BASELINE)
    for priority in profile.priorities:
        factor = PRIORITY_TO_FACTOR.get(priority)
        if factor is not None:
            levels[factor] = TOP
    return levels


def _relevance(scored: tuple[ScoredFit, ...]) -> float | None:
    """docs/06_RECOMMENDATION_ENGINE.md section 8.

        sum(factor_score × factor_weight) / sum(applicable_factor_weights)

    "Applicable" means *has verified data*. A dimension we could not assess
    contributes to neither the numerator nor the denominator, so it cannot
    drag a product down or prop one up.
    """
    usable = [item for item in scored if item.result.normalized_score is not None]
    if not usable:
        return None

    denominator = sum(item.weight for item in usable)
    if denominator == 0:
        return None

    numerator = sum((item.result.normalized_score or 0.0) * item.weight for item in usable)
    return numerator / denominator


def _highlights(scored: tuple[ScoredFit, ...], profile: UserProfile) -> tuple[str, ...]:
    """The strengths worth putting on the card.

    Ordered by the reader's own priority list first, then by how strong the
    fit is. A card should answer *their* question, not show the product's best
    angle.
    """
    chosen_rank = {
        factor: index
        for index, priority in enumerate(profile.priorities)
        if (factor := PRIORITY_TO_FACTOR.get(priority)) is not None
    }
    unchosen = len(profile.priorities) + 1

    candidates = [item.result for item in scored if item.result.label in _HIGHLIGHT_LABELS]
    candidates.sort(
        key=lambda result: (
            chosen_rank.get(result.factor_key, unchosen),
            -_LABEL_RANK[result.label],
            result.factor_key,
        )
    )
    return tuple(result.factor_key for result in candidates[:HIGHLIGHT_COUNT])


def evaluate_product(
    product: ProviderProduct,
    profile: UserProfile,
    *,
    config: ScoringConfig = HEALTH_BETA_001,
    annual_premium_inr: int | None = None,
) -> MatchResult:
    """Assess one product for one person."""
    try:
        facts = parse_health_facts(product.facts)
    except FactsUnusableError:
        # The facts we hold cannot be read as a health product. That is a data
        # problem, and the honest response is to withhold the product rather
        # than match on whatever parsed.
        return MatchResult(
            product=product,
            eligibility=EligibilityResult(
                status="EXCLUDED", reasons=(CRITICAL_DATA_UNUSABLE,), evidence=()
            ),
            fits=(),
            relevance=None,
            highlights=(),
        )

    eligibility = assess(facts, profile)
    scored = _score_fits(facts, profile, config=config, annual_premium_inr=annual_premium_inr)
    relevance = _relevance(scored)

    if eligibility.eligible and relevance is None:
        # Nothing could be assessed. Section 8 forbids letting that pass as a
        # neutral result, so the product leaves the match set.
        eligibility = EligibilityResult(
            status="EXCLUDED",
            reasons=(NO_VERIFIED_FIT_DATA,),
            evidence=eligibility.evidence,
        )

    return MatchResult(
        product=product,
        eligibility=eligibility,
        fits=scored,
        relevance=relevance,
        highlights=_highlights(scored, profile) if eligibility.eligible else (),
    )


def _score_fits(
    facts: HealthFacts,
    profile: UserProfile,
    *,
    config: ScoringConfig,
    annual_premium_inr: int | None,
) -> tuple[ScoredFit, ...]:
    levels = _priority_levels(profile)
    results = [evaluator(facts, profile) for evaluator in EVALUATORS]
    results.append(evaluate_budget(facts, profile, annual_premium_inr=annual_premium_inr))

    by_factor = {result.factor_key: result for result in results}
    ordered = [by_factor[key] for key in factors.FACTOR_ORDER if key in by_factor]

    return tuple(
        ScoredFit(
            result=result,
            priority_level=levels[result.factor_key],
            weight=config.weight_for(levels[result.factor_key]),
        )
        for result in ordered
    )


def run_match(
    products: list[ProviderProduct],
    profile: UserProfile,
    *,
    config: ScoringConfig = HEALTH_BETA_001,
    prices_inr: dict[str, int] | None = None,
) -> MatchSet:
    """Assess a catalogue for one person and order what is left.

    Ordering is by internal relevance, descending, with the product reference
    as the tiebreak so the result is stable across identical requests.
    """
    prices = prices_inr or {}
    assessed = [
        evaluate_product(
            product,
            profile,
            config=config,
            annual_premium_inr=prices.get(product.reference),
        )
        for product in products
    ]

    matched = [result for result in assessed if result.eligible]
    excluded = [result for result in assessed if not result.eligible]

    matched.sort(key=lambda result: (-(result.relevance or 0.0), result.product.reference))
    excluded.sort(key=lambda result: result.product.reference)

    return MatchSet(
        scoring_version=config.version,
        matched=tuple(matched),
        excluded=tuple(excluded),
    )
