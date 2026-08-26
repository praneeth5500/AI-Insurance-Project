"""Comparing options (docs/11_BUILD_PLAN.md Phase 6)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.matching.factors import FACTOR_LABELS
from app.recommendations import service
from app.recommendations.comparison import (
    MAX_DIFFERENCES,
    biggest_differences,
    build_dimensions,
    priority_dimensions,
)
from app.recommendations.errors import (
    ComparisonOptionNotInRunError,
    TooFewComparisonsError,
    TooManyComparisonsError,
)
from app.recommendations.schemas import ComparisonView
from app.users.models import User
from tests.test_questionnaire import make_user
from tests.test_recommendations import completed_session


async def run_with_options(db: AsyncSession, user: User) -> tuple[str, list[str]]:
    session_id = await completed_session(db, user)
    result = await service.create_run(db, user=user, questionnaire_session_id=session_id)
    return result.run.id, [c.product_reference for c in result.candidates]


# ------------------------------------------------------------- the limits ---


async def test_two_options_can_be_compared(db: AsyncSession) -> None:
    user = await make_user(db)
    run_id, refs = await run_with_options(db, user)

    result = await service.compare(db, user=user, run_id=run_id, product_references=refs[:2])

    assert len(result.options) == 2


async def test_three_options_can_be_compared(db: AsyncSession) -> None:
    user = await make_user(db)
    run_id, refs = await run_with_options(db, user)

    result = await service.compare(db, user=user, run_id=run_id, product_references=refs[:3])

    assert len(result.options) == 3


async def test_more_than_three_is_rejected_by_the_server(db: AsyncSession) -> None:
    """docs/12_BETA_CHECKLIST.md: compare max 3. Not only a UI rule."""
    user = await make_user(db)
    run_id, refs = await run_with_options(db, user)

    with pytest.raises(TooManyComparisonsError):
        await service.compare(db, user=user, run_id=run_id, product_references=refs[:4])


async def test_fewer_than_two_is_rejected(db: AsyncSession) -> None:
    user = await make_user(db)
    run_id, refs = await run_with_options(db, user)

    with pytest.raises(TooFewComparisonsError):
        await service.compare(db, user=user, run_id=run_id, product_references=refs[:1])


async def test_duplicates_do_not_inflate_the_count(db: AsyncSession) -> None:
    user = await make_user(db)
    run_id, refs = await run_with_options(db, user)

    with pytest.raises(TooFewComparisonsError):
        await service.compare(db, user=user, run_id=run_id, product_references=[refs[0], refs[0]])


async def test_an_option_outside_the_run_is_rejected(db: AsyncSession) -> None:
    user = await make_user(db)
    run_id, refs = await run_with_options(db, user)

    with pytest.raises(ComparisonOptionNotInRunError):
        await service.compare(
            db, user=user, run_id=run_id, product_references=[refs[0], "sp_not_real"]
        )


async def test_one_user_cannot_compare_another_users_run(db: AsyncSession) -> None:
    owner = await make_user(db, "owner@example.com")
    intruder = await make_user(db, "intruder@example.com")
    run_id, refs = await run_with_options(db, owner)

    from app.recommendations.errors import RecommendationRunNotFoundError

    with pytest.raises(RecommendationRunNotFoundError):
        await service.compare(db, user=intruder, run_id=run_id, product_references=refs[:2])


# --------------------------------------------------------- what is compared --


def _fits(**products: dict[str, tuple[str, str]]) -> dict[str, dict[str, tuple[str, str]]]:
    return dict(products)


def test_a_dimension_where_all_agree_is_not_a_difference() -> None:
    dimensions = build_dimensions(
        _fits(
            a={"copay": ("STRONG", "No co-pay."), "budget": ("GOOD", "Mid.")},
            b={"copay": ("STRONG", "No co-pay."), "budget": ("TRADE_OFF", "High.")},
        ),
        [],
    )

    by_factor = {d.factor: d for d in dimensions}
    assert by_factor["copay"].differs is False
    assert by_factor["budget"].differs is True


def test_biggest_differences_lead_with_the_widest_gap() -> None:
    dimensions = build_dimensions(
        _fits(
            a={
                "copay": ("STRONG", "x"),
                "budget": ("GOOD", "x"),
                "coverage": ("STRONG", "x"),
            },
            b={
                "copay": ("NEEDS_ATTENTION", "x"),
                "budget": ("TRADE_OFF", "x"),
                "coverage": ("STRONG", "x"),
            },
        ),
        [],
    )

    ordered = biggest_differences(dimensions)

    assert ordered[0].factor == "copay"
    assert "coverage" not in [d.factor for d in ordered]


def test_a_priority_breaks_a_tie_between_equal_differences() -> None:
    """docs/01_PRODUCT_SPEC.md section 2.7: the user's priorities come second."""
    fits = _fits(
        a={"coverage": ("STRONG", "x"), "sublimits": ("STRONG", "x")},
        b={"coverage": ("GOOD", "x"), "sublimits": ("GOOD", "x")},
    )

    without = biggest_differences(build_dimensions(fits, []))
    with_priority = biggest_differences(build_dimensions(fits, ["fewer_sublimits"]))

    assert without[0].factor == "coverage"
    assert with_priority[0].factor == "sublimits"


def test_the_difference_list_stays_short() -> None:
    """docs/02_UX_UI_SPEC.md section 10: avoid giant feature matrices."""
    factors = list(FACTOR_LABELS)
    fits = _fits(
        a=dict.fromkeys(factors, ("STRONG", "x")),
        b=dict.fromkeys(factors, ("NEEDS_ATTENTION", "x")),
    )

    assert len(biggest_differences(build_dimensions(fits, []))) == MAX_DIFFERENCES


def test_priorities_are_shown_even_when_the_options_agree() -> None:
    """Saying "all three are strong here" answers the reader's question too."""
    dimensions = build_dimensions(
        _fits(a={"copay": ("STRONG", "x")}, b={"copay": ("STRONG", "x")}),
        ["low_copay"],
    )

    shown = priority_dimensions(dimensions)

    assert [d.factor for d in shown] == ["copay"]
    assert shown[0].differs is False


def test_unverified_data_counts_as_a_real_difference() -> None:
    """docs/06_RECOMMENDATION_ENGINE.md section 8: unknown is never average."""
    dimensions = build_dimensions(
        _fits(a={"exclusions": ("GOOD", "x")}, b={"exclusions": ("UNVERIFIED", "x")}),
        [],
    )

    assert biggest_differences(dimensions)[0].factor == "exclusions"


def test_comparison_is_deterministic(db: AsyncSession) -> None:
    fits = _fits(
        a={"coverage": ("STRONG", "x"), "copay": ("GOOD", "x")},
        b={"coverage": ("GOOD", "x"), "copay": ("TRADE_OFF", "x")},
    )

    first = [d.factor for d in biggest_differences(build_dimensions(fits, []))]
    second = [d.factor for d in biggest_differences(build_dimensions(fits, []))]

    assert first == second


# -------------------------------------------------------------- the payload --


async def test_the_response_follows_the_specified_order(db: AsyncSession) -> None:
    user = await make_user(db)
    run_id, refs = await run_with_options(db, user)

    view = ComparisonView.of(
        await service.compare(db, user=user, run_id=run_id, product_references=refs[:3])
    )

    assert view.biggest_differences
    assert view.your_priorities
    assert len(view.all_details) == 8
    assert len(view.options) == 3


async def test_every_compared_option_carries_its_watch_out(db: AsyncSession) -> None:
    user = await make_user(db)
    run_id, refs = await run_with_options(db, user)

    view = ComparisonView.of(
        await service.compare(db, user=user, run_id=run_id, product_references=refs[:2])
    )

    assert all(option.watch_out.strip() for option in view.options)
    assert all(option.source_type == "SYNTHETIC" for option in view.options)


async def test_no_score_or_difference_size_is_exposed(db: AsyncSession) -> None:
    """A difference "size" on screen would be a score by another name."""
    user = await make_user(db)
    run_id, refs = await run_with_options(db, user)

    view = ComparisonView.of(
        await service.compare(db, user=user, run_id=run_id, product_references=refs[:2])
    )
    serialized = view.model_dump_json().lower()

    for forbidden in ("spread", "score", "rank", "rating", "winner", "better"):
        assert forbidden not in serialized


async def test_the_order_the_user_picked_is_preserved(db: AsyncSession) -> None:
    user = await make_user(db)
    run_id, refs = await run_with_options(db, user)
    chosen = [refs[2], refs[0]]

    view = ComparisonView.of(
        await service.compare(db, user=user, run_id=run_id, product_references=chosen)
    )

    assert [option.product_reference for option in view.options] == chosen
