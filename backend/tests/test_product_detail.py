"""The product detail screen.

Phase 9 splits the page in two. The sections state the policy's **facts**;
the fit block above them says what those facts mean for one reader, and only
exists inside a recommendation run. Opening an option outside a run shows the
facts and says why there is no personal assessment — rather than inventing a
user-independent "fit".
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.products import service
from app.products.catalogue import all_products
from app.products.errors import ProductNotFoundError
from app.products.schemas import ProductDetailView
from app.products.sections import (
    FACTOR_EXAMPLES,
    SECTION_DEFINITIONS,
    build_policy_sections,
)
from app.questionnaires import service as questionnaire_service
from app.recommendations import service as recommendation_service
from app.users.models import User
from tests.test_questionnaire import JUST_ME_ANSWERS, answer_all, make_user

REFERENCE = "sp_meridian_core"


async def run_for(db: AsyncSession, user: User, priorities: list[str] | None = None) -> str:
    """A completed questionnaire and the run it produced."""
    session = await questionnaire_service.start_or_resume(db, user=user, domain="HEALTH")
    answers = dict(JUST_ME_ANSWERS)
    if priorities is not None:
        answers["priorities"] = priorities
    await answer_all(db, user, session.id, answers)
    await questionnaire_service.complete(db, user=user, session_id=session.id)
    result = await recommendation_service.create_run(
        db, user=user, questionnaire_session_id=session.id
    )
    return result.run.id


async def detail_view(
    db: AsyncSession,
    reference: str = REFERENCE,
    priorities: list[str] | None = None,
    email: str = "reader@example.com",
) -> ProductDetailView:
    user = await make_user(db, email)
    run_id = await run_for(db, user, priorities)
    detail = await service.get_detail(db, user=user, product_reference=reference, run_id=run_id)
    return ProductDetailView.of(detail)


# --------------------------------------------------------------- sections ---


def test_sections_match_the_specification() -> None:
    """docs/01_PRODUCT_SPEC.md section 2.8."""
    labels = [label for _, label, _ in SECTION_DEFINITIONS]

    assert labels == [
        "Your Cover",
        "Your Costs",
        "Waiting Periods",
        "Important Limits",
        "Not Covered",
        "Claims",
    ]


def test_every_product_produces_every_section() -> None:
    for product in all_products():
        sections = build_policy_sections(product.facts)
        assert [section.label for section in sections] == [
            label for _, label, _ in SECTION_DEFINITIONS
        ]


def test_sections_state_facts_rather_than_judgements() -> None:
    """A fact is true for everyone; a fit is true for one person.

    The sections must not borrow the reader-relative wording — "which matters
    less given a shared room suits you" belongs above them, not in a statement
    of what the policy does.
    """
    product = next(p for p in all_products() if p.id == REFERENCE)
    sections = build_policy_sections(product.facts)

    values = [fact.value for section in sections for fact in section.facts]
    assert values
    for value in values:
        assert " you said" not in value
        assert "you're aiming for" not in value


def test_a_missing_fact_is_stated_as_missing_not_omitted() -> None:
    """A blank section reads as "nothing to worry about". It isn't."""
    lantern = next(p for p in all_products() if p.id == "sp_lantern_starter")

    values = " ".join(
        fact.value for section in build_policy_sections(lantern.facts) for fact in section.facts
    )

    assert "No verified exclusions list is recorded" in values


def test_no_section_invents_a_figure_the_facts_do_not_hold() -> None:
    """Every number on the page traces to a recorded fact."""
    product = next(p for p in all_products() if p.id == REFERENCE)
    facts = product.facts
    allowed = {
        str(facts.copay_percent),
        str(facts.ped_waiting_months),
        str(facts.specific_treatment_waiting_months),
        str(facts.initial_waiting_days),
        str(facts.room_cap_percent),
        str(facts.sublimit_count),
        str(facts.notable_exclusion_count),
        f"{facts.network_hospital_count:,}",
        *(str(amount // 100_000) for amount in facts.sum_insured_options_inr),
    }

    import re

    for section in build_policy_sections(facts):
        for fact in section.facts:
            for number in re.findall(r"\d[\d,]*", fact.value):
                assert number in allowed, f"{fact.key}: {number}"


def test_every_fact_offers_an_example() -> None:
    """docs/01_PRODUCT_SPEC.md section 2.8: "Explain with example"."""
    for product in all_products():
        for section in build_policy_sections(product.facts):
            for fact in section.facts:
                assert fact.example, f"{product.id}/{fact.key}"


def test_examples_are_hypothetical_not_claims_about_the_product() -> None:
    """docs/12_BETA_CHECKLIST.md: examples clearly labeled as examples."""
    for example in FACTOR_EXAMPLES.values():
        assert any(
            marker in example.lower()
            for marker in ("if ", "usually", "can ", "means", "two policies")
        ), example
        # Never asserted of this policy.
        assert "this policy pays" not in example.lower()


# ----------------------------------------------------------------- sources --


def test_no_synthetic_fact_claims_to_have_a_source() -> None:
    """A fabricated citation is release-blocking
    (docs/10_TESTING_AND_EVALS.md section 8)."""
    for product in all_products():
        for section in build_policy_sections(product.facts):
            for fact in section.facts:
                assert fact.has_source is False
                assert fact.source_note


async def test_the_source_documents_section_explains_its_emptiness(
    db: AsyncSession,
) -> None:
    view = await detail_view(db)

    assert view.source_documents == []
    assert "demo product" in view.source_documents_note


async def test_provenance_travels_with_the_response(db: AsyncSession) -> None:
    """docs/08_API_CONTRACTS.md section 5: include source/provenance metadata."""
    view = await detail_view(db)

    assert view.provenance.source_type == "SYNTHETIC"
    assert view.provenance.verified_at is None
    assert "synthetic" in view.provenance.explanation.lower()


# ------------------------------------------------------------------- hero ---


async def test_the_hero_carries_three_strengths_and_one_trade_off(
    db: AsyncSession,
) -> None:
    """docs/02_UX_UI_SPEC.md section 11."""
    view = await detail_view(db)

    assert 1 <= len(view.highlights) <= 3
    assert view.watch_out.strip()


async def test_highlights_follow_the_reader_s_priorities(db: AsyncSession) -> None:
    copay_first = await detail_view(db, priorities=["low_copay"], email="a@example.com")
    sublimits_first = await detail_view(db, priorities=["fewer_sublimits"], email="b@example.com")

    assert copay_first.highlights[0].factor == "copay"
    assert sublimits_first.highlights[0].factor == "sublimits"


async def test_the_page_shows_the_fit_the_run_recorded(db: AsyncSession) -> None:
    """A card and the page behind it must never disagree."""
    user = await make_user(db)
    run_id = await run_for(db, user)

    run = await recommendation_service.get_run(db, user=user, run_id=run_id)
    candidate = next(c for c in run.candidates if c.product_reference == REFERENCE)

    detail = await service.get_detail(db, user=user, product_reference=REFERENCE, run_id=run_id)
    view = ProductDetailView.of(detail)

    assert [fit.fit for fit in view.fits] == [
        entry["label"] for entry in candidate.reason_summary_json["fits"]
    ]
    assert [fit.factor for fit in view.highlights] == candidate.reason_summary_json[
        "highlightFactors"
    ]


async def test_without_a_run_the_page_states_facts_and_says_so(db: AsyncSession) -> None:
    """Fit is a judgement about a person. Outside a run there is no person."""
    user = await make_user(db)

    detail = await service.get_detail(db, user=user, product_reference=REFERENCE)
    view = ProductDetailView.of(detail)

    assert view.fits == []
    assert view.highlights == []
    assert view.fit_context_note is not None
    assert view.sections


async def test_another_users_run_cannot_supply_the_fit(db: AsyncSession) -> None:
    owner = await make_user(db, "owner@example.com")
    intruder = await make_user(db, "intruder@example.com")
    run_id = await run_for(db, owner)

    detail = await service.get_detail(db, user=intruder, product_reference=REFERENCE, run_id=run_id)

    assert detail.fits == []


async def test_no_overall_score_appears(db: AsyncSession) -> None:
    view = await detail_view(db)
    serialized = view.model_dump_json().lower()

    for forbidden in ("score", "rank", "rating", "best policy", "guarantee"):
        assert forbidden not in serialized


async def test_no_premium_appears(db: AsyncSession) -> None:
    """CLAUDE.md: never invent a premium.

    A cover amount is not a premium — it is the most important fact a policy
    has, and the questionnaire asks the reader for one in the same units. What
    must never appear is a *price*: what the policy costs. So the budget fact
    says there isn't one, and no fact quotes a cost per year or month.
    """
    view = await detail_view(db)

    facts = {fact.key: fact.value for section in view.sections for fact in section.facts}

    assert "No price is recorded" in facts["budget"]
    for key, value in facts.items():
        lowered = value.lower()
        assert "per year" not in lowered, key
        assert "per month" not in lowered, key
        assert "premium is" not in lowered, key


# ------------------------------------------------------------------ saving --


async def test_saving_is_idempotent(db: AsyncSession) -> None:
    user = await make_user(db)

    await service.save(db, user=user, product_reference=REFERENCE)
    await service.save(db, user=user, product_reference=REFERENCE)

    assert await service.list_saved(db, user=user) == [REFERENCE]


async def test_saving_survives_a_reload(db: AsyncSession) -> None:
    user = await make_user(db)
    await service.save(db, user=user, product_reference=REFERENCE)

    detail = await service.get_detail(db, user=user, product_reference=REFERENCE)

    assert detail.saved is True


async def test_unsaving_what_was_never_saved_is_not_an_error(db: AsyncSession) -> None:
    user = await make_user(db)

    assert await service.unsave(db, user=user, product_reference=REFERENCE) is False


async def test_saves_are_private_to_the_user(db: AsyncSession) -> None:
    owner = await make_user(db, "owner@example.com")
    other = await make_user(db, "other@example.com")
    await service.save(db, user=owner, product_reference=REFERENCE)

    assert await service.list_saved(db, user=other) == []
    other_detail = await service.get_detail(db, user=other, product_reference=REFERENCE)
    assert other_detail.saved is False


async def test_an_unknown_product_cannot_be_saved(db: AsyncSession) -> None:
    user = await make_user(db)

    with pytest.raises(ProductNotFoundError):
        await service.save(db, user=user, product_reference="sp_not_real")


async def test_an_unknown_product_has_no_detail(db: AsyncSession) -> None:
    user = await make_user(db)

    with pytest.raises(ProductNotFoundError):
        await service.get_detail(db, user=user, product_reference="sp_not_real")


# ------------------------------------------------------------ authorization --


async def test_the_endpoints_require_a_session(api: AsyncClient) -> None:
    assert (await api.get(f"/api/v1/products/{REFERENCE}")).status_code == 401
    assert (await api.put(f"/api/v1/products/{REFERENCE}/saved")).status_code == 401
    assert (await api.delete(f"/api/v1/products/{REFERENCE}/saved")).status_code == 401
