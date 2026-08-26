"""The recommendation experience end to end.

The engine itself is tested in `test_matching.py`. What is checked here is the
boundary around it: what a run records, what reaches a response, and what
happens to a stored run when the reader changes their mind.
"""

from __future__ import annotations

import re

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.matching.engine import run_match
from app.matching.factors import FACTOR_LABELS
from app.matching.profile import build_profile
from app.matching.weights import EXPLANATION_VERSION, SCORING_VERSION
from app.products.catalogue import CATALOGUE_VERSION, SyntheticProduct, all_products
from app.products.facts import HealthFacts
from app.products.provenance import SYNTHETIC
from app.products.provider import SyntheticCatalogueProvider
from app.questionnaires import service as questionnaire_service
from app.recommendations import service
from app.recommendations.errors import QuestionnaireNotCompleteError, RecommendationRunNotFoundError
from app.recommendations.profile import build_decision_profile
from app.recommendations.schemas import RunView
from app.users.models import User
from tests.test_questionnaire import JUST_ME_ANSWERS, answer_all, make_user


async def completed_session(
    db: AsyncSession, user: User, answers: dict[str, object] | None = None
) -> str:
    session = await questionnaire_service.start_or_resume(db, user=user, domain="HEALTH")
    await answer_all(db, user, session.id, {**JUST_ME_ANSWERS, **(answers or {})})
    await questionnaire_service.complete(db, user=user, session_id=session.id)
    return session.id


# ------------------------------------------------------- the demo catalogue --


def test_the_catalogue_is_labelled_synthetic() -> None:
    """docs/06_RECOMMENDATION_ENGINE.md section 3: every record is labelled."""
    assert all(product.source_type == SYNTHETIC for product in all_products())


def test_no_product_carries_a_premium() -> None:
    """CLAUDE.md: never invent a premium.

    Checked structurally: the word "premium" legitimately appears in prose
    that explains the concept ("a low premium can cost more when you claim"),
    so what matters is that no product holds a price *amount*.
    """
    fields = set(SyntheticProduct.model_fields)
    assert not fields & {"price", "premium", "amount", "cost", "currency"}

    # No currency symbol and no figure in any text a reader will see.
    # (The version string carries digits, which is why prose is checked, not
    # the whole serialised record.)
    facts_fields = set(HealthFacts.model_fields)
    assert not facts_fields & {"price", "premium", "amount", "cost", "currency"}

    # No currency symbol and no figure in any text a reader will see.
    # (The version string carries digits, which is why prose is checked, not
    # the whole serialised record.)
    for product in all_products():
        for text in (product.insurer_name, product.product_name, product.watch_out):
            assert "₹" not in text
            assert not re.search(r"\d", text), text


def test_every_insurer_name_is_marked_as_a_demo() -> None:
    """A screenshot of this build must not read as a real comparison."""
    assert all("(demo)" in product.insurer_name for product in all_products())


def test_every_product_has_exactly_one_watch_out() -> None:
    """docs/02_UX_UI_SPEC.md rule 4: trust requires discussing disadvantages."""
    assert all(product.watch_out.strip() for product in all_products())


async def test_every_product_is_assessed_on_every_fit_dimension() -> None:
    """A dimension is always reported, even when the answer is "we don't know"."""
    products = await SyntheticCatalogueProvider().list_products(domain="HEALTH")
    profile = build_profile(JUST_ME_ANSWERS)

    for result in run_match(products, profile).matched:
        assert {scored.result.factor_key for scored in result.fits} == set(FACTOR_LABELS)


def test_the_catalogue_makes_no_claim_it_cannot_support() -> None:
    text = " ".join(product.model_dump_json() for product in all_products()).lower()

    for forbidden in ("guarantee", "claim approved", "best policy", "we recommend", "cheapest"):
        assert forbidden not in text


def test_there_are_ten_products_so_see_five_more_is_real() -> None:
    assert len(all_products()) == service.MAX_MATCH_COUNT


# ---------------------------------------------------------- decision profile --


def test_the_profile_is_a_synthesis_not_a_form_dump() -> None:
    lines = build_decision_profile(JUST_ME_ANSWERS)

    assert lines
    # Field names and stored values never appear.
    joined = " ".join(lines)
    assert "cover_for" not in joined
    assert "just_me" not in joined


def test_the_profile_states_nothing_that_was_not_answered() -> None:
    lines = build_decision_profile({"applicant_age": 30})

    assert all("employer" not in line for line in lines)
    assert all("priorities" not in line.lower() for line in lines)


def test_a_health_condition_is_reflected_without_naming_anything() -> None:
    lines = build_decision_profile({**JUST_ME_ANSWERS, "broad_health_conditions": "yes"})

    condition_lines = [line for line in lines if "ongoing condition" in line]
    assert len(condition_lines) == 1
    assert "diagnos" not in condition_lines[0].lower()


def test_declining_to_answer_produces_no_line() -> None:
    lines = build_decision_profile(
        {**JUST_ME_ANSWERS, "broad_health_conditions": "prefer_not_to_say"}
    )

    assert all("ongoing condition" not in line for line in lines)


# ------------------------------------------------------------------- runs ----


async def test_a_run_requires_a_completed_questionnaire(db: AsyncSession) -> None:
    user = await make_user(db)
    session = await questionnaire_service.start_or_resume(db, user=user, domain="HEALTH")

    with pytest.raises(QuestionnaireNotCompleteError):
        await service.create_run(db, user=user, questionnaire_session_id=session.id)


async def test_a_run_records_what_produced_it(db: AsyncSession) -> None:
    user = await make_user(db)
    session_id = await completed_session(db, user)

    result = await service.create_run(db, user=user, questionnaire_session_id=session_id)

    assert result.run.scoring_version == SCORING_VERSION
    assert result.run.explanation_version == EXPLANATION_VERSION
    assert result.run.catalogue_version == CATALOGUE_VERSION
    assert result.run.source_type == SYNTHETIC
    assert result.run.presentation_mode == "BETA_MATCH_SET"


async def test_a_run_shows_five_primary_options_then_the_rest(db: AsyncSession) -> None:
    """docs/01_PRODUCT_SPEC.md section 2.5: 5, then "see more", up to 10.

    Fewer than 10 reach the screen because two of the demo products cannot be
    bought by this reader at all — a 34-year-old insuring only themselves —
    and hard eligibility removes them rather than ranking them low.
    """
    user = await make_user(db)
    session_id = await completed_session(db, user)

    result = await service.create_run(db, user=user, questionnaire_session_id=session_id)
    view = RunView.of(result)

    assert len(view.matches) == 5
    assert view.can_show_more is True
    assert len(view.matches) + len(view.additional_matches) == 8
    assert view.excluded_count == 2


async def test_a_run_says_why_options_were_not_offered(db: AsyncSession) -> None:
    """An option removed without explanation looks like an option that
    doesn't exist. The reader is told the rule, never the product."""
    user = await make_user(db)
    session_id = await completed_session(db, user)

    view = RunView.of(await service.create_run(db, user=user, questionnaire_session_id=session_id))

    assert view.excluded_count == 2
    assert view.exclusion_notes
    joined = " ".join(view.exclusion_notes).lower()
    # Rules, not products.
    assert "demo" not in joined
    assert all("sp_" not in note for note in view.exclusion_notes)


async def test_every_match_has_highlights_and_a_watch_out(db: AsyncSession) -> None:
    """docs/01_PRODUCT_SPEC.md section 2.5 card contract."""
    user = await make_user(db)
    session_id = await completed_session(db, user)

    view = RunView.of(await service.create_run(db, user=user, questionnaire_session_id=session_id))

    for match in view.matches + view.additional_matches:
        assert len(match.highlights) <= 3
        assert match.watch_out.strip()
        assert match.fits


async def test_no_overall_score_reaches_the_response(db: AsyncSession) -> None:
    """docs/01_PRODUCT_SPEC.md section 2.5: no 0-100 consumer score."""
    user = await make_user(db)
    session_id = await completed_session(db, user)

    view = RunView.of(await service.create_run(db, user=user, questionnaire_session_id=session_id))
    serialized = view.model_dump_json().lower()

    for forbidden in ("score", "relevance", "rating", "rank"):
        assert forbidden not in serialized


async def test_every_match_reports_that_no_price_is_available(db: AsyncSession) -> None:
    user = await make_user(db)
    session_id = await completed_session(db, user)

    view = RunView.of(await service.create_run(db, user=user, questionnaire_session_id=session_id))

    for match in view.matches:
        assert match.price.state == "UNAVAILABLE"
        assert match.price.amount is None
        assert "demo products" in match.price.explanation


async def test_the_same_answers_produce_the_same_order(db: AsyncSession) -> None:
    user = await make_user(db)
    session_id = await completed_session(db, user)

    first = await service.create_run(db, user=user, questionnaire_session_id=session_id)
    second = await service.create_run(db, user=user, questionnaire_session_id=session_id)

    assert [c.product_reference for c in first.candidates] == [
        c.product_reference for c in second.candidates
    ]


# -------------------------------------------------------- priority editing --


async def test_changing_priorities_reorders_deterministically(db: AsyncSession) -> None:
    user = await make_user(db)
    session_id = await completed_session(db, user)
    run = await service.create_run(db, user=user, questionnaire_session_id=session_id)
    before = [c.product_reference for c in run.candidates]

    result, previous = await service.update_priorities(
        db, user=user, run_id=run.run.id, priorities=["broad_coverage"]
    )
    after = [c.product_reference for c in result.candidates]

    assert previous == before
    assert after != before

    # The reader now says broad coverage matters most, so the product whose
    # cover tops out well above their target rises, and the one that tops out
    # well below it stops leading. Neither jumps straight to the top: a top
    # priority is weighted more heavily, not treated as the only thing that
    # counts (docs/06_RECOMMENDATION_ENGINE.md section 6).
    assert after.index("sp_beacon_wide") < before.index("sp_beacon_wide")
    assert before[0] == "sp_alderwood_essential"
    assert after[0] != "sp_alderwood_essential"


async def test_changing_priorities_creates_a_new_run_and_leaves_the_old_one(
    db: AsyncSession,
) -> None:
    """CLAUDE.md rule 10: never rewrite a historical result.

    docs/06_RECOMMENDATION_ENGINE.md section 11 freezes a completed run, so a
    changed priority produces a new one that points back at it.
    """
    user = await make_user(db)
    session_id = await completed_session(db, user)
    first = await service.create_run(db, user=user, questionnaire_session_id=session_id)
    original_order = [c.product_reference for c in first.candidates]
    original_priorities = list(first.run.priorities_json)

    second, _ = await service.update_priorities(
        db, user=user, run_id=first.run.id, priorities=["broad_coverage"]
    )

    assert second.run.id != first.run.id
    assert second.run.previous_run_id == first.run.id

    # The earlier run still says exactly what it said, read fresh from the
    # database rather than from the objects still in memory.
    first_run_id = first.run.id
    for stored in (first.run, *first.candidates):
        db.expire(stored)
    reread = await service.get_run(db, user=user, run_id=first_run_id)
    assert [c.product_reference for c in reread.candidates] == original_order
    assert list(reread.run.priorities_json) == original_priorities


async def test_a_stored_result_cannot_be_edited_in_place(db: AsyncSession) -> None:
    """The guard exists because this is exactly how history gets rewritten."""
    from app.recommendations.models import ImmutableRunError

    user = await make_user(db)
    session_id = await completed_session(db, user)
    run = await service.create_run(db, user=user, questionnaire_session_id=session_id)

    candidate = run.candidates[0]
    candidate.presentation_order = 99

    with pytest.raises(ImmutableRunError):
        await db.flush()

    db.rollback  # noqa: B018 - the rollback below is what matters
    await db.rollback()


async def test_a_run_records_the_priorities_it_was_produced_with(db: AsyncSession) -> None:
    """A run explains itself without consulting the questionnaire.

    The questionnaire can change; the run cannot.
    """
    user = await make_user(db)
    session_id = await completed_session(db, user)
    first = await service.create_run(db, user=user, questionnaire_session_id=session_id)

    second, _ = await service.update_priorities(
        db, user=user, run_id=first.run.id, priorities=["broad_coverage"]
    )

    assert list(first.run.priorities_json) == JUST_ME_ANSWERS["priorities"]
    assert list(second.run.priorities_json) == ["broad_coverage"]


async def test_every_fit_component_is_persisted_with_its_evidence(db: AsyncSession) -> None:
    """docs/05_DATA_MODEL.md fit_components, section 7's evidence object."""
    from sqlalchemy import select

    from app.recommendations.models import FitComponent

    user = await make_user(db)
    session_id = await completed_session(db, user)
    run = await service.create_run(db, user=user, questionnaire_session_id=session_id)

    components = list(
        (
            await db.execute(
                select(FitComponent).where(FitComponent.candidate_id == run.candidates[0].id)
            )
        )
        .scalars()
        .all()
    )

    assert {component.factor_key for component in components} == set(FACTOR_LABELS)
    for component in components:
        assert component.evidence_json
        assert component.user_priority_level in ("BASELINE", "TOP", "MUST_HAVE")
        # An unverified dimension keeps a null score rather than a zero.
        if component.label == "UNVERIFIED":
            assert component.normalized_score is None


async def test_reverting_priorities_restores_the_original_order(db: AsyncSession) -> None:
    """Deterministic means reversible: the same priorities, the same answer."""
    user = await make_user(db)
    session_id = await completed_session(db, user)
    run = await service.create_run(db, user=user, questionnaire_session_id=session_id)
    original = [c.product_reference for c in run.candidates]

    changed, _ = await service.update_priorities(
        db, user=user, run_id=run.run.id, priorities=["broad_coverage"]
    )
    restored, _ = await service.update_priorities(
        db, user=user, run_id=changed.run.id, priorities=run.priorities
    )

    assert [c.product_reference for c in restored.candidates] == original


async def test_reordering_never_loses_or_duplicates_an_option(db: AsyncSession) -> None:
    user = await make_user(db)
    session_id = await completed_session(db, user)
    run = await service.create_run(db, user=user, questionnaire_session_id=session_id)

    result, _ = await service.update_priorities(
        db, user=user, run_id=run.run.id, priorities=["broad_coverage", "fewer_sublimits"]
    )
    references = [c.product_reference for c in result.candidates]

    assert len(references) == len(set(references))
    assert set(references) == {c.product_reference for c in run.candidates}


# ------------------------------------------------------------ authorization --


async def test_one_user_cannot_read_another_users_run(db: AsyncSession) -> None:
    owner = await make_user(db, "owner@example.com")
    intruder = await make_user(db, "intruder@example.com")
    session_id = await completed_session(db, owner)
    run = await service.create_run(db, user=owner, questionnaire_session_id=session_id)

    with pytest.raises(RecommendationRunNotFoundError):
        await service.get_run(db, user=intruder, run_id=run.run.id)


async def test_one_user_cannot_reorder_another_users_run(db: AsyncSession) -> None:
    owner = await make_user(db, "owner@example.com")
    intruder = await make_user(db, "intruder@example.com")
    session_id = await completed_session(db, owner)
    run = await service.create_run(db, user=owner, questionnaire_session_id=session_id)

    with pytest.raises(RecommendationRunNotFoundError):
        await service.update_priorities(
            db, user=intruder, run_id=run.run.id, priorities=["low_copay"]
        )


async def test_card_highlights_lead_with_the_reader_s_priority(db: AsyncSession) -> None:
    """Regression: the ordering strongest_fits produces must survive.

    Filtering the full fit list by membership would silently restore catalogue
    order and put a strength the reader never mentioned first.
    """
    user = await make_user(db)
    session_id = await completed_session(db, user, {"priorities": ["fewer_sublimits", "low_copay"]})

    view = RunView.of(await service.create_run(db, user=user, questionnaire_session_id=session_id))
    meridian = next(
        match
        for match in view.matches + view.additional_matches
        if match.product_reference == "sp_meridian_core"
    )

    assert meridian.highlights[0].factor == "sublimits"
