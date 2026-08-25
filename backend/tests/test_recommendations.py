"""The mock recommendation experience (docs/11_BUILD_PLAN.md Phase 5)."""

from __future__ import annotations

import re

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.products.catalogue import CATALOGUE_VERSION, FACTOR_LABELS, all_products
from app.products.provenance import SYNTHETIC
from app.questionnaires import service as questionnaire_service
from app.recommendations import service
from app.recommendations.errors import QuestionnaireNotCompleteError, RecommendationRunNotFoundError
from app.recommendations.ordering import ORDERING_VERSION, order_products, strongest_fits
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
    from app.products.catalogue import SyntheticProduct

    fields = set(SyntheticProduct.model_fields)
    assert not fields & {"price", "premium", "amount", "cost", "currency"}

    # No currency symbol and no figure in any text a reader will see.
    # (The version string carries digits, which is why prose is checked, not
    # the whole serialised record.)
    prose: list[str] = []
    for product in all_products():
        prose.extend([product.insurer_name, product.product_name, product.watch_out])
        prose.extend(fit.note for fit in product.fits)

    for text in prose:
        assert "₹" not in text
        assert not re.search(r"\d", text), text


def test_every_insurer_name_is_marked_as_a_demo() -> None:
    """A screenshot of this build must not read as a real comparison."""
    assert all("(demo)" in product.insurer_name for product in all_products())


def test_every_product_has_exactly_one_watch_out() -> None:
    """docs/02_UX_UI_SPEC.md rule 4: trust requires discussing disadvantages."""
    assert all(product.watch_out.strip() for product in all_products())


def test_every_product_covers_every_fit_dimension() -> None:
    for product in all_products():
        assert {fit.factor for fit in product.fits} == set(FACTOR_LABELS)


def test_the_catalogue_makes_no_claim_it_cannot_support() -> None:
    text = " ".join(product.model_dump_json() for product in all_products()).lower()

    for forbidden in ("guarantee", "claim approved", "best policy", "we recommend", "cheapest"):
        assert forbidden not in text


def test_there_are_ten_products_so_see_five_more_is_real() -> None:
    assert len(all_products()) == service.MAX_MATCH_COUNT


# ------------------------------------------------------------------ ordering --


def test_ordering_is_deterministic() -> None:
    """docs/10_TESTING_AND_EVALS.md section 3: same input, same result."""
    priorities = ["low_copay", "short_waiting_periods"]

    first = [p.id for p in order_products(all_products(), priorities)]
    second = [p.id for p in order_products(all_products(), priorities)]

    assert first == second


def test_ordering_responds_to_the_priorities_chosen() -> None:
    budget_first = [p.id for p in order_products(all_products(), ["lower_premium"])]
    copay_first = [p.id for p in order_products(all_products(), ["low_copay"])]

    assert budget_first != copay_first
    # The cheapest-labelled demo product leads when budget is the priority.
    assert budget_first[0] == "sp_lantern_starter"


def test_ties_break_stably_rather_than_shuffling() -> None:
    """With no priorities every product ties, so order must still be fixed."""
    assert [p.id for p in order_products(all_products(), [])] == sorted(
        p.id for p in all_products()
    )


def test_unverified_data_is_not_treated_as_average() -> None:
    """docs/06_RECOMMENDATION_ENGINE.md section 8."""
    from app.recommendations.ordering import _LABEL_RANK

    assert _LABEL_RANK["UNVERIFIED"] == _LABEL_RANK["NEEDS_ATTENTION"] == 0
    assert _LABEL_RANK["UNVERIFIED"] < _LABEL_RANK["TRADE_OFF"]


def test_highlights_only_name_genuine_strengths() -> None:
    for product in all_products():
        for factor in strongest_fits(product, ["low_copay", "broad_coverage"]):
            fit = product.fit(factor)
            assert fit is not None
            assert fit.label in ("STRONG", "GOOD")


def test_highlights_lead_with_what_the_user_said_mattered() -> None:
    product = next(p for p in all_products() if p.id == "sp_meridian_core")

    highlights = strongest_fits(product, ["fewer_sublimits"])

    assert highlights[0] == "sublimits"


def test_at_most_three_highlights() -> None:
    for product in all_products():
        assert len(strongest_fits(product, ["low_copay"])) <= 3


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

    assert result.run.scoring_version == ORDERING_VERSION
    assert result.run.catalogue_version == CATALOGUE_VERSION
    assert result.run.source_type == SYNTHETIC
    assert result.run.presentation_mode == "BETA_MATCH_SET"


async def test_a_run_produces_ten_options_split_five_and_five(db: AsyncSession) -> None:
    user = await make_user(db)
    session_id = await completed_session(db, user)

    result = await service.create_run(db, user=user, questionnaire_session_id=session_id)
    view = RunView.of(result)

    assert len(view.matches) == 5
    assert len(view.additional_matches) == 5
    assert view.can_show_more is True


async def test_every_match_has_highlights_and_a_watch_out(db: AsyncSession) -> None:
    """docs/01_PRODUCT_SPEC.md section 2.5 card contract."""
    user = await make_user(db)
    session_id = await completed_session(db, user)

    view = RunView.of(await service.create_run(db, user=user, questionnaire_session_id=session_id))

    for match in view.matches + view.additional_matches:
        assert 1 <= len(match.highlights) <= 3
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
        db, user=user, run_id=run.run.id, priorities=["lower_premium"]
    )
    after = [c.product_reference for c in result.candidates]

    assert previous == before
    assert after != before
    assert after[0] == "sp_lantern_starter"


async def test_reverting_priorities_restores_the_original_order(db: AsyncSession) -> None:
    user = await make_user(db)
    session_id = await completed_session(db, user)
    run = await service.create_run(db, user=user, questionnaire_session_id=session_id)
    original = [c.product_reference for c in run.candidates]

    await service.update_priorities(db, user=user, run_id=run.run.id, priorities=["lower_premium"])
    restored, _ = await service.update_priorities(
        db, user=user, run_id=run.run.id, priorities=run.priorities
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

    assert len(references) == len(set(references)) == service.MAX_MATCH_COUNT


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
