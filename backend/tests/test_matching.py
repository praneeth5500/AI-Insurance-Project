"""The matching engine (docs/11_BUILD_PLAN.md Phase 9).

The tests are grouped the way docs/06_RECOMMENDATION_ENGINE.md is written:
hard eligibility, then the evaluators, then weighting and relevance, then the
personas from docs/10_TESTING_AND_EVALS.md section 3.

What is being defended here is not "the numbers are right" — they are
product-test parameters, not insurance truth. It is that the engine never
pretends to know something it does not, and never changes its mind about a
result it already gave.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.db.types import utcnow
from app.matching import factors
from app.matching.eligibility import (
    AGE_OUTSIDE_RANGE,
    CHILDREN_EXCEEDED,
    COMPOSITION_UNSUPPORTED,
    NO_VERIFIED_FIT_DATA,
    assess,
)
from app.matching.engine import evaluate_product, run_match
from app.matching.evaluators import (
    evaluate_budget,
    evaluate_copay,
    evaluate_coverage,
    evaluate_hospital_flexibility,
    evaluate_network,
    evaluate_waiting_periods,
)
from app.matching.profile import UserProfile, build_profile
from app.matching.weights import BASELINE, HEALTH_BETA_001, MUST_HAVE, TOP
from app.products.catalogue import LAKH, all_products
from app.products.facts import CRITICAL_FACT_KEYS, HealthFacts
from app.products.freshness import DEFAULT_MAX_VERIFICATION_AGE, critical_facts_usable
from app.products.models import ProductFact
from app.products.provenance import SYNTHETIC
from app.products.provider import ProviderProduct, SyntheticCatalogueProvider


def facts(**overrides: object) -> HealthFacts:
    """A minimal, complete product to vary one fact at a time."""
    base: dict[str, object] = {
        "entry_age_min": 18,
        "entry_age_max": 65,
        "supported_compositions": ("just_me", "me_spouse", "me_family"),
        "sum_insured_options_inr": (5 * LAKH, 10 * LAKH),
        "copay_percent": 0,
        "ped_waiting_months": 24,
        "room_rule": "ANY_ROOM",
        "cashless_scope": "ANY_HOSPITAL",
        "sublimit_count": 0,
        "notable_exclusion_count": 3,
    }
    base.update(overrides)
    return HealthFacts.model_validate(base)


def product(reference: str = "sp_test", **overrides: object) -> ProviderProduct:
    return ProviderProduct(
        reference=reference,
        insurer_name="Test Assurance (demo)",
        product_name="Test Plan",
        domain="HEALTH",
        source_type=SYNTHETIC,
        version_label="test-001",
        facts=facts(**overrides).model_dump(),
    )


ADULT = UserProfile(applicant_age=34, cover_for="just_me")


# ------------------------------------------------------- hard eligibility --


def test_age_outside_the_entry_range_removes_the_product() -> None:
    """docs/06_RECOMMENDATION_ENGINE.md section 4: a hard failure."""
    result = assess(facts(entry_age_min=55, entry_age_max=80), ADULT)

    assert not result.eligible
    assert AGE_OUTSIDE_RANGE in result.reasons


def test_an_unsupported_family_composition_removes_the_product() -> None:
    result = assess(
        facts(supported_compositions=("just_me",)),
        UserProfile(applicant_age=34, cover_for="me_family"),
    )

    assert not result.eligible
    assert COMPOSITION_UNSUPPORTED in result.reasons


def test_more_children_than_the_policy_covers_removes_the_product() -> None:
    result = assess(
        facts(max_children=2),
        UserProfile(applicant_age=34, cover_for="me_family", children_count=4),
    )

    assert not result.eligible
    assert CHILDREN_EXCEEDED in result.reasons


def test_only_the_people_actually_covered_are_age_checked() -> None:
    """Buying cover for a parent must not be blocked by the buyer's own age.

    A senior product starting at 55 is exactly what a 40-year-old covering a
    68-year-old parent needs; gating on the buyer would remove the one option
    that fits.
    """
    buying_for_parents = UserProfile(applicant_age=40, oldest_parent_age=68, cover_for="my_parents")

    assert buying_for_parents.oldest_person_age == 68
    assert assess(
        facts(entry_age_min=55, entry_age_max=80, supported_compositions=("my_parents",)),
        buying_for_parents,
    ).eligible


def test_a_preference_mismatch_is_not_a_hard_failure() -> None:
    """section 4: a higher co-pay than wanted lowers fit, it does not remove.

    This is the distinction the whole module exists to hold. A reader who
    would rather not share a claim should still see the co-pay options, told
    plainly what they cost.
    """
    picky = UserProfile(applicant_age=34, cover_for="just_me", copay_tolerance="prefer_none")

    result = evaluate_product(product(copay_percent=30), picky)

    assert result.eligible
    copay = result.fit(factors.COPAY)
    assert copay is not None
    assert copay.label == "NEEDS_ATTENTION"


def test_an_excluded_product_records_why() -> None:
    result = assess(facts(entry_age_min=55, entry_age_max=80), ADULT)

    assert result.evidence
    kinds = {item.kind for item in result.evidence}
    assert {"PRODUCT_FACT", "USER_ANSWER", "RULE"} <= kinds


# ------------------------------------------------------- unknown is not zero --


@pytest.mark.parametrize(
    ("evaluator", "override"),
    [
        (evaluate_copay, {"copay_percent": None}),
        (evaluate_waiting_periods, {"ped_waiting_months": None}),
        (evaluate_hospital_flexibility, {"room_rule": None}),
        (evaluate_network, {"cashless_scope": None}),
    ],
)
def test_a_missing_fact_is_unverified_not_average(
    evaluator: object, override: dict[str, object]
) -> None:
    """docs/06_RECOMMENDATION_ENGINE.md section 8.

    Never convert unknown into a neutral score silently. "Silently" is the
    operative word: the label says it, and the evidence records the gap.
    """
    result = evaluator(facts(**override), ADULT)  # type: ignore[operator]

    assert result.label == "UNVERIFIED"
    assert result.normalized_score is None
    assert [item for item in result.evidence if item.kind == "DATA_GAP"]


def test_an_unverified_dimension_is_left_out_of_the_relevance_value() -> None:
    """It contributes to neither half of the fraction.

    Scoring it 0 would punish a product for our missing data; scoring it 0.5
    would invent a judgement. Leaving it out is the only honest option.
    """
    complete = evaluate_product(product(), ADULT)
    missing = evaluate_product(product(notable_exclusion_count=None), ADULT)

    exclusions = missing.fit(factors.EXCLUSIONS)
    assert exclusions is not None and exclusions.normalized_score is None

    # The remaining dimensions are identical and score identically, so the
    # average over what *is* known is unchanged.
    assert complete.relevance is not None and missing.relevance is not None
    assert complete.relevance == pytest.approx(missing.relevance)


def test_a_product_with_no_verified_fit_data_is_excluded_not_floated() -> None:
    empty = product(
        copay_percent=None,
        ped_waiting_months=None,
        room_rule=None,
        cashless_scope=None,
        sublimit_count=None,
        notable_exclusion_count=None,
    )
    # No desired cover either, so the coverage dimension has nothing to
    # measure against and every dimension is unknown.
    result = evaluate_product(empty, UserProfile(applicant_age=34, cover_for="just_me"))

    assert not result.eligible
    assert NO_VERIFIED_FIT_DATA in result.eligibility.reasons
    assert result.relevance is None


# ------------------------------------------------------------- evaluators --


def test_the_same_copay_is_judged_differently_for_different_readers() -> None:
    """Fit is about a person, not a product."""
    ten_percent = facts(copay_percent=10)

    picky = evaluate_copay(
        ten_percent, UserProfile(applicant_age=34, copay_tolerance="prefer_none")
    )
    relaxed = evaluate_copay(
        ten_percent, UserProfile(applicant_age=34, copay_tolerance="small_share_ok")
    )

    assert picky.label == "TRADE_OFF"
    assert relaxed.label == "GOOD"
    assert picky.normalized_score is not None and relaxed.normalized_score is not None
    assert picky.normalized_score < relaxed.normalized_score


def test_an_age_triggered_copay_says_it_does_not_apply_yet_but_will() -> None:
    result = evaluate_copay(
        facts(copay_percent=10, copay_applies_above_age=60),
        UserProfile(applicant_age=34, copay_tolerance="prefer_none"),
    )

    assert result.label == "GOOD"
    assert "60" in result.note


def test_declining_to_say_is_not_treated_as_no_condition() -> None:
    """A blank is not a negative.

    "I'd rather not say" leaves the waiting period judged as though it could
    apply, and the evidence records that it was a gap rather than an answer.
    """
    silent = UserProfile(
        applicant_age=34,
        broad_health_conditions="prefer_not_to_say",
        waiting_period_sensitivity="somewhat_important",
    )

    result = evaluate_waiting_periods(facts(ped_waiting_months=48), silent)

    assert result.label == "NEEDS_ATTENTION"
    assert [
        item
        for item in result.evidence
        if item.kind == "DATA_GAP" and item.key == "broad_health_conditions"
    ]


def test_a_capped_room_is_flagged_hardest_for_someone_wanting_a_private_room() -> None:
    capped = facts(room_rule="CAPPED_PERCENT", room_cap_percent=1)

    wants_private = evaluate_hospital_flexibility(
        capped, UserProfile(applicant_age=34, room_preference="private_room")
    )
    shared_is_fine = evaluate_hospital_flexibility(
        capped, UserProfile(applicant_age=34, room_preference="shared_is_fine")
    )

    assert wants_private.label == "NEEDS_ATTENTION"
    assert shared_is_fine.label == "GOOD"


def test_coverage_needs_a_target_before_it_can_be_judged() -> None:
    """ "I'm not sure yet" is not a cover level we can invent one for."""
    unsure = evaluate_coverage(facts(), UserProfile(applicant_age=34, desired_cover="not_sure"))
    stated = evaluate_coverage(facts(), UserProfile(applicant_age=34, desired_cover="up_to_5l"))

    assert unsure.label == "UNVERIFIED"
    assert stated.label == "STRONG"


def test_the_network_count_never_claims_local_coverage() -> None:
    """We hold a national count and nothing about the reader's area."""
    result = evaluate_network(
        facts(cashless_scope="NETWORK_ONLY", network_hospital_count=7000), ADULT
    )

    assert "nationally" in result.note
    assert any("not checked it against your area" in item.detail for item in result.evidence)


def test_budget_reports_a_gap_because_no_price_exists() -> None:
    """CLAUDE.md: never invent a premium.

    There is no price for any product, so the budget dimension is honestly
    unverified — for every reader, however much budget they gave.
    """
    result = evaluate_budget(facts(), UserProfile(applicant_age=34, approximate_budget_inr=20_000))

    assert result.label == "UNVERIFIED"
    assert result.normalized_score is None


def test_budget_is_evaluated_once_a_real_price_exists() -> None:
    """The branch is real code, not a stub waiting to be written."""
    profile = UserProfile(applicant_age=34, approximate_budget_inr=20_000)

    inside = evaluate_budget(facts(), profile, annual_premium_inr=15_000)
    outside = evaluate_budget(facts(), profile, annual_premium_inr=40_000)

    assert inside.label == "STRONG"
    assert outside.label == "NEEDS_ATTENTION"


# ------------------------------------------------- weighting and relevance --


def test_a_chosen_priority_weighs_more_than_a_baseline_dimension() -> None:
    """docs/06_RECOMMENDATION_ENGINE.md section 6."""
    result = evaluate_product(
        product(),
        UserProfile(applicant_age=34, cover_for="just_me", priorities=["low_copay"]),
    )

    weights = {scored.result.factor_key: scored for scored in result.fits}
    assert weights[factors.COPAY].priority_level == TOP
    assert weights[factors.SUBLIMITS].priority_level == BASELINE
    assert weights[factors.COPAY].weight == pytest.approx(
        weights[factors.SUBLIMITS].weight * HEALTH_BETA_001.top_priority_multiplier
    )


def test_the_weights_are_versioned_configuration_not_scattered_constants() -> None:
    assert HEALTH_BETA_001.version == "health-beta-001"
    assert HEALTH_BETA_001.weight_for(BASELINE) == 1.0
    assert HEALTH_BETA_001.weight_for(TOP) == 3.0


def test_nothing_currently_produces_a_must_have_priority() -> None:
    """The level exists because the specification names it.

    The health questionnaire has no way to mark a priority non-negotiable, so
    inventing one would be inventing a product decision. Recorded in
    docs/SPEC_ISSUES.md; this test fails the day that changes, which is the
    point.
    """
    every_priority = UserProfile(
        applicant_age=34,
        cover_for="just_me",
        priorities=["low_copay", "broad_coverage", "fewer_sublimits"],
    )

    result = evaluate_product(product(), every_priority)

    assert all(scored.priority_level != MUST_HAVE for scored in result.fits)


def test_the_relevance_value_never_reaches_a_response_schema() -> None:
    """docs/06_RECOMMENDATION_ENGINE.md section 7 and section 2.5 of the spec.

    Checked at the source: the engine's own result carries it, and the
    schemas module has no field that would carry it out.
    """
    from app.recommendations import schemas

    result = evaluate_product(product(), ADULT)
    assert result.relevance is not None

    fields = set(schemas.MatchView.model_fields) | set(schemas.RunView.model_fields)
    assert not fields & {"relevance", "score", "internal_relevance_value", "internal_order"}


# ----------------------------------------------------------- the personas --


async def synthetic_products() -> list[ProviderProduct]:
    return await SyntheticCatalogueProvider().list_products(domain="HEALTH")


PERSONA_A = {
    # docs/10_TESTING_AND_EVALS.md section 3: young salaried user, employer
    # cover, low co-pay a high priority.
    "applicant_age": 29,
    "cover_for": "just_me",
    "has_employer_cover": "yes",
    "desired_cover": "5l_to_10l",
    "copay_tolerance": "prefer_none",
    "room_preference": "shared_is_fine",
    "waiting_period_sensitivity": "somewhat_important",
    "priorities": ["low_copay"],
}

PERSONA_B = {
    # section 3: a parent-focused profile.
    "applicant_age": 41,
    "oldest_parent_age": 68,
    "cover_for": "my_parents",
    "desired_cover": "5l_to_10l",
    "copay_tolerance": "small_share_ok",
    "room_preference": "no_preference",
    "waiting_period_sensitivity": "as_soon_as_possible",
    "priorities": ["short_waiting_periods"],
}


async def test_persona_a_penalises_copay_heavy_products() -> None:
    match_set = run_match(await synthetic_products(), build_profile(PERSONA_A))

    order = [result.product.reference for result in match_set.matched]
    # Both carry a 20% co-pay, which this reader said they'd rather not have.
    assert order[-1] == "sp_northgate_value"
    assert "sp_orchard_senior" not in order


async def test_persona_a_excludes_products_they_cannot_buy() -> None:
    match_set = run_match(await synthetic_products(), build_profile(PERSONA_A))

    excluded = {result.product.reference for result in match_set.excluded}
    # Family-only cover, and a product that starts at 55.
    assert {"sp_harbourline_family", "sp_orchard_senior"} <= excluded
    assert COMPOSITION_UNSUPPORTED in match_set.exclusion_reasons
    assert AGE_OUTSIDE_RANGE in match_set.exclusion_reasons


async def test_persona_b_applies_age_eligibility_to_the_parent() -> None:
    match_set = run_match(await synthetic_products(), build_profile(PERSONA_B))

    matched = {result.product.reference for result in match_set.matched}
    # Only the two products that both accept a 68-year-old and can be taken
    # out for parents survive.
    assert matched == {"sp_orchard_senior", "sp_beacon_wide"}


async def test_persona_b_excludes_unsupported_family_configurations() -> None:
    match_set = run_match(await synthetic_products(), build_profile(PERSONA_B))

    for result in match_set.excluded:
        assert result.eligibility.reasons


async def test_a_priority_change_deterministically_changes_the_order() -> None:
    """docs/10_TESTING_AND_EVALS.md section 3."""
    products = await synthetic_products()

    copay_first = run_match(products, build_profile({**PERSONA_A, "priorities": ["low_copay"]}))
    coverage_first = run_match(
        products, build_profile({**PERSONA_A, "priorities": ["broad_coverage"]})
    )

    assert [result.product.reference for result in copay_first.matched] != [
        result.product.reference for result in coverage_first.matched
    ]


async def test_the_same_input_produces_the_same_structured_result() -> None:
    products = await synthetic_products()
    profile = build_profile(PERSONA_A)

    first = run_match(products, profile)
    second = run_match(products, profile)

    assert [
        (result.product.reference, result.relevance, result.highlights) for result in first.matched
    ] == [
        (result.product.reference, result.relevance, result.highlights) for result in second.matched
    ]


async def test_ties_break_stably_rather_than_shuffling() -> None:
    """A reader with no priorities still gets a fixed order."""
    products = await synthetic_products()
    profile = build_profile({"applicant_age": 34, "cover_for": "just_me"})

    assert [result.product.reference for result in run_match(products, profile).matched] == [
        result.product.reference for result in run_match(products, profile).matched
    ]


async def test_highlights_only_ever_name_a_genuine_strength() -> None:
    match_set = run_match(await synthetic_products(), build_profile(PERSONA_A))

    for result in match_set.matched:
        for factor in result.highlights:
            fit = result.fit(factor)
            assert fit is not None
            assert fit.label in ("STRONG", "GOOD")


async def test_highlights_lead_with_what_the_reader_said_mattered() -> None:
    match_set = run_match(
        await synthetic_products(),
        build_profile({**PERSONA_A, "priorities": ["fewer_sublimits", "low_copay"]}),
    )

    meridian = next(
        result for result in match_set.matched if result.product.reference == "sp_meridian_core"
    )
    assert meridian.highlights[0] == factors.SUBLIMITS


# ---------------------------------------------------------- stale product data --


def test_stale_critical_product_data_excludes_the_product() -> None:
    """docs/10_TESTING_AND_EVALS.md section 3, and section 4 of the engine spec.

    Enforced at the provider seam by the Phase 8 freshness rules, so a stale
    version never reaches the engine at all.
    """
    long_ago = utcnow() - DEFAULT_MAX_VERIFICATION_AGE - timedelta(days=1)
    stale = [
        ProductFact(
            product_version_id="pv_test",
            fact_key=key,
            value_json={"value": 1},
            verified_at=long_ago,
        )
        for key in CRITICAL_FACT_KEYS
    ]

    result = critical_facts_usable(stale, required_keys=set(CRITICAL_FACT_KEYS))

    assert not result.usable
    assert result.reason == "CRITICAL_FACT_STALE"


def test_facts_that_cannot_be_read_exclude_the_product() -> None:
    """A data problem must not become a wrong match."""
    broken = ProviderProduct(
        reference="sp_broken",
        insurer_name="Broken Assurance (demo)",
        product_name="Broken Plan",
        domain="HEALTH",
        source_type=SYNTHETIC,
        version_label="broken-001",
        facts={"entry_age_min": 18},
    )

    result = evaluate_product(broken, ADULT)

    assert not result.eligible
    assert result.fits == ()


# --------------------------------------------------------------- no LLM ----


def test_no_part_of_the_engine_reaches_for_a_model() -> None:
    """CLAUDE.md: never let the LLM generate the recommendation ranking.

    Structural rather than behavioural: an outage cannot change a score that
    no model was ever asked about.
    """
    import pkgutil

    import app.matching

    banned = ("openai", "anthropic", "httpx", "requests", "aiohttp", "llm")
    for module in pkgutil.iter_modules(app.matching.__path__):
        source = (
            (__import__("pathlib").Path(app.matching.__path__[0]) / f"{module.name}.py")
            .read_text()
            .lower()
        )
        for name in banned:
            assert f"import {name}" not in source


async def test_every_catalogue_product_parses_as_health_facts() -> None:
    """The fixtures and the schema cannot drift apart unnoticed."""
    for synthetic in all_products():
        assert set(CRITICAL_FACT_KEYS) <= set(synthetic.facts.model_dump())
