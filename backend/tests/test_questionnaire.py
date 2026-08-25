"""The questionnaire engine (docs/11_BUILD_PLAN.md Phase 4)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.allowlist import grant_access
from app.auth.models import AuthIdentity
from app.questionnaires import service
from app.questionnaires.definitions import Condition
from app.questionnaires.errors import (
    InvalidAnswerError,
    QuestionnaireIncompleteError,
    QuestionnaireSessionNotFoundError,
    QuestionNotApplicableError,
    SessionAlreadyCompletedError,
)
from app.questionnaires.health_beta import HEALTH_BETA
from app.questionnaires.models import (
    STATUS_COMPLETED,
    PriorityItem,
    PriorityProfile,
    QuestionnaireAnswer,
)
from app.questionnaires.validation import validate_answer
from app.users.models import User


async def make_user(db: AsyncSession, email: str = "invited@example.com") -> User:
    await grant_access(db, email)
    await db.commit()
    identity = (
        await db.execute(select(AuthIdentity).where(AuthIdentity.email == email))
    ).scalar_one()
    user = User(auth_identity_id=identity.id)
    db.add(user)
    await db.commit()
    return user


#: Every required question for the simplest possible path.
JUST_ME_ANSWERS = {
    "applicant_age": 34,
    "pincode": "560001",
    "cover_for": "just_me",
    "has_employer_cover": "yes",
    "has_personal_cover": False,
    "desired_cover": "10l_to_25l",
    "room_preference": "shared_is_fine",
    "copay_tolerance": "prefer_none",
    "waiting_period_sensitivity": "as_soon_as_possible",
    "priorities": ["low_copay", "short_waiting_periods"],
}


async def answer_all(
    db: AsyncSession, user: User, session_id: str, answers: dict[str, object]
) -> service.SessionState:
    state = await service.load_state(db, user=user, session_id=session_id)
    for question_id, value in answers.items():
        state = await service.save_answer(
            db, user=user, session_id=session_id, question_id=question_id, value=value
        )
    return state


# ------------------------------------------------------- the seeded question set --


def test_the_health_question_set_is_marked_draft() -> None:
    """docs/13_DECISIONS_AND_OPEN_ITEMS.md open item 6: wording is not decided."""
    assert HEALTH_BETA.status == "DRAFT"
    assert HEALTH_BETA.version == "health-beta-draft-001"


def test_every_question_belongs_to_a_declared_stage() -> None:
    stage_keys = {stage.key for stage in HEALTH_BETA.stages}

    assert all(question.stage in stage_keys for question in HEALTH_BETA.questions)


def test_stages_match_the_specification() -> None:
    """docs/01_PRODUCT_SPEC.md section 2.2."""
    assert [stage.label for stage in HEALTH_BETA.stages] == [
        "About you",
        "Your cover",
        "What matters",
    ]


def test_question_ids_and_data_fields_are_unique() -> None:
    ids = [q.id for q in HEALTH_BETA.questions]
    fields = [q.data_field for q in HEALTH_BETA.questions]

    assert len(ids) == len(set(ids))
    assert len(fields) == len(set(fields))


def test_the_health_condition_question_is_optional_and_flagged_sensitive() -> None:
    """docs/01_PRODUCT_SPEC.md 2.2: no detailed medical history by default."""
    question = HEALTH_BETA.question("broad_health_conditions")

    assert question is not None
    assert question.sensitive is True
    assert question.required is False
    assert {option.value for option in question.options} == {
        "no",
        "yes",
        "prefer_not_to_say",
    }


def test_only_the_health_condition_question_is_sensitive() -> None:
    sensitive = [q.id for q in HEALTH_BETA.questions if q.sensitive]

    assert sensitive == ["broad_health_conditions"]


def test_sensitive_questions_explain_why_they_are_asked() -> None:
    """docs/02_UX_UI_SPEC.md rule 3."""
    for question in HEALTH_BETA.questions:
        if question.sensitive:
            assert question.help_text


def test_priorities_come_from_the_specification_and_cap_at_three() -> None:
    """docs/01_PRODUCT_SPEC.md section 2.3."""
    question = HEALTH_BETA.question("priorities")

    assert question is not None
    assert question.max_selections == 3
    assert {option.value for option in question.options} == {
        "lower_premium",
        "low_copay",
        "short_waiting_periods",
        "hospital_flexibility",
        "broad_coverage",
        "fewer_sublimits",
    }


def test_no_question_states_an_insurance_fact() -> None:
    """CLAUDE.md: never invent insurance facts, premiums or claim outcomes."""
    parts: list[str] = []
    for question in HEALTH_BETA.questions:
        parts.extend(filter(None, [question.title, question.description, question.help_text]))
        for option in question.options:
            parts.extend(filter(None, [option.label, option.description]))
    text = " ".join(parts).lower()

    for forbidden in ("guarantee", "claim approved", "we recommend", "cheapest"):
        assert forbidden not in text

    # "best" may appear only in the negative — docs/02_UX_UI_SPEC.md rule 5
    # wants trade-offs acknowledged, and "there is no single best policy" is
    # the framing the product is built on, not a claim.
    for index in range(len(text)):
        if text.startswith("best", index):
            assert text[max(0, index - 16) : index].endswith("no single ")


# ------------------------------------------------------------------ branching --


def test_conditional_questions_are_hidden_by_default() -> None:
    visible = {q.id for q in HEALTH_BETA.visible_questions({})}

    assert "spouse_age" not in visible
    assert "children_count" not in visible
    assert "oldest_parent_age" not in visible


@pytest.mark.parametrize(
    ("cover_for", "expected"),
    [
        ("just_me", set()),
        ("me_spouse", {"spouse_age"}),
        ("me_family", {"spouse_age", "children_count"}),
        ("my_parents", {"oldest_parent_age"}),
    ],
)
def test_branching_reveals_exactly_the_right_questions(cover_for: str, expected: set[str]) -> None:
    visible = {q.id for q in HEALTH_BETA.visible_questions({"cover_for": cover_for})}
    conditional = {"spouse_age", "children_count", "oldest_parent_age"}

    assert visible & conditional == expected


def test_branching_is_deterministic() -> None:
    """Same answers in, same questions out — every time."""
    answers = {"cover_for": "me_family"}

    first = [q.id for q in HEALTH_BETA.visible_questions(answers)]
    second = [q.id for q in HEALTH_BETA.visible_questions(answers)]

    assert first == second


def test_conditions_compose_with_all_of() -> None:
    condition = Condition(
        all_of=(
            Condition(field="a", operator="EQUALS", value=1),
            Condition(field="b", operator="IN", value=["x", "y"]),
        )
    )

    assert condition.evaluate({"a": 1, "b": "x"}) is True
    assert condition.evaluate({"a": 1, "b": "z"}) is False
    assert condition.evaluate({"a": 2, "b": "x"}) is False


# ----------------------------------------------------------------- validation --


def test_a_choice_outside_the_options_is_rejected() -> None:
    question = HEALTH_BETA.question("cover_for")
    assert question is not None

    with pytest.raises(InvalidAnswerError):
        validate_answer(question, "someone_else")


def test_more_than_three_priorities_are_rejected() -> None:
    question = HEALTH_BETA.question("priorities")
    assert question is not None

    with pytest.raises(InvalidAnswerError, match="Choose up to 3"):
        validate_answer(
            question,
            ["lower_premium", "low_copay", "broad_coverage", "fewer_sublimits"],
        )


def test_duplicate_priorities_are_rejected() -> None:
    question = HEALTH_BETA.question("priorities")
    assert question is not None

    with pytest.raises(InvalidAnswerError):
        validate_answer(question, ["low_copay", "low_copay"])


def test_priority_order_is_preserved() -> None:
    question = HEALTH_BETA.question("priorities")
    assert question is not None

    assert validate_answer(question, ["broad_coverage", "low_copay"]) == [
        "broad_coverage",
        "low_copay",
    ]


@pytest.mark.parametrize("value", ["56001", "5600011", "abcdef", 560001])
def test_a_malformed_pincode_is_rejected(value: object) -> None:
    question = HEALTH_BETA.question("pincode")
    assert question is not None

    with pytest.raises(InvalidAnswerError):
        validate_answer(question, value)


def test_an_age_outside_the_supported_range_is_rejected() -> None:
    question = HEALTH_BETA.question("applicant_age")
    assert question is not None

    with pytest.raises(InvalidAnswerError):
        validate_answer(question, 4)
    with pytest.raises(InvalidAnswerError):
        validate_answer(question, 150)


def test_a_boolean_question_rejects_a_string() -> None:
    question = HEALTH_BETA.question("has_personal_cover")
    assert question is not None

    with pytest.raises(InvalidAnswerError):
        validate_answer(question, "yes")


def test_an_optional_question_accepts_no_answer() -> None:
    question = HEALTH_BETA.question("approximate_budget")
    assert question is not None

    assert validate_answer(question, None) is None


def test_a_required_question_rejects_no_answer() -> None:
    question = HEALTH_BETA.question("applicant_age")
    assert question is not None

    with pytest.raises(InvalidAnswerError):
        validate_answer(question, None)


def test_validation_errors_never_echo_the_submitted_value() -> None:
    """Answers can be sensitive; error messages must not repeat them."""
    question = HEALTH_BETA.question("broad_health_conditions")
    assert question is not None
    secret = "a-private-diagnosis"

    with pytest.raises(InvalidAnswerError) as raised:
        validate_answer(question, secret)

    assert secret not in raised.value.message


# ------------------------------------------------------- sessions and drafts --


async def test_starting_twice_resumes_the_same_draft(db: AsyncSession) -> None:
    user = await make_user(db)

    first = await service.start_or_resume(db, user=user, domain="HEALTH")
    second = await service.start_or_resume(db, user=user, domain="HEALTH")

    assert first.id == second.id


async def test_answers_persist_across_reloads(db: AsyncSession) -> None:
    """docs/03_FRONTEND_ARCHITECTURE.md section 3: persist the draft server-side."""
    user = await make_user(db)
    session = await service.start_or_resume(db, user=user, domain="HEALTH")

    await service.save_answer(
        db, user=user, session_id=session.id, question_id="applicant_age", value=41
    )
    reloaded = await service.load_state(db, user=user, session_id=session.id)

    assert reloaded.answers["applicant_age"] == 41


async def test_re_answering_updates_in_place(db: AsyncSession) -> None:
    user = await make_user(db)
    session = await service.start_or_resume(db, user=user, domain="HEALTH")

    for age in (30, 31, 32):
        await service.save_answer(
            db, user=user, session_id=session.id, question_id="applicant_age", value=age
        )

    rows = (
        (
            await db.execute(
                select(QuestionnaireAnswer).where(
                    QuestionnaireAnswer.session_id == session.id,
                    QuestionnaireAnswer.question_id == "applicant_age",
                )
            )
        )
        .scalars()
        .all()
    )

    assert len(rows) == 1
    assert rows[0].answer_json == {"value": 32}


async def test_a_sensitive_answer_is_flagged_in_storage(db: AsyncSession) -> None:
    """docs/05_DATA_MODEL.md section 2."""
    user = await make_user(db)
    session = await service.start_or_resume(db, user=user, domain="HEALTH")

    await service.save_answer(
        db,
        user=user,
        session_id=session.id,
        question_id="broad_health_conditions",
        value="yes",
    )

    row = (
        await db.execute(
            select(QuestionnaireAnswer).where(
                QuestionnaireAnswer.question_id == "broad_health_conditions"
            )
        )
    ).scalar_one()

    assert row.sensitive is True


async def test_a_hidden_question_cannot_be_answered(db: AsyncSession) -> None:
    """Answering around a branch would bypass the questionnaire's logic."""
    user = await make_user(db)
    session = await service.start_or_resume(db, user=user, domain="HEALTH")

    with pytest.raises(QuestionNotApplicableError):
        await service.save_answer(
            db, user=user, session_id=session.id, question_id="spouse_age", value=33
        )


async def test_changing_a_branch_answer_drops_the_orphaned_answer(
    db: AsyncSession,
) -> None:
    """The answers are the only source of truth: no stale branch survives."""
    user = await make_user(db)
    session = await service.start_or_resume(db, user=user, domain="HEALTH")

    await service.save_answer(
        db, user=user, session_id=session.id, question_id="cover_for", value="me_spouse"
    )
    await service.save_answer(
        db, user=user, session_id=session.id, question_id="spouse_age", value=33
    )
    state = await service.save_answer(
        db, user=user, session_id=session.id, question_id="cover_for", value="just_me"
    )

    assert "spouse_age" not in state.answers
    assert "spouse_age" not in {q.id for q in state.visible}


async def test_the_next_question_is_the_first_unanswered_one(db: AsyncSession) -> None:
    user = await make_user(db)
    session = await service.start_or_resume(db, user=user, domain="HEALTH")

    state = await service.load_state(db, user=user, session_id=session.id)
    assert state.next_question is not None
    assert state.next_question.id == "applicant_age"

    state = await service.save_answer(
        db, user=user, session_id=session.id, question_id="applicant_age", value=30
    )
    assert state.next_question is not None
    assert state.next_question.id == "pincode"


async def test_an_optional_question_does_not_block_progress(db: AsyncSession) -> None:
    user = await make_user(db)
    session = await service.start_or_resume(db, user=user, domain="HEALTH")

    state = await answer_all(db, user, session.id, JUST_ME_ANSWERS)

    # Neither optional question was answered, and the draft is still complete.
    assert "broad_health_conditions" not in state.answers
    assert "approximate_budget" not in state.answers
    assert state.is_complete is True


# ---------------------------------------------------------------- completion --


async def test_completing_requires_every_visible_required_answer(
    db: AsyncSession,
) -> None:
    user = await make_user(db)
    session = await service.start_or_resume(db, user=user, domain="HEALTH")

    with pytest.raises(QuestionnaireIncompleteError):
        await service.complete(db, user=user, session_id=session.id)


async def test_completing_records_the_questionnaire_version(db: AsyncSession) -> None:
    user = await make_user(db)
    session = await service.start_or_resume(db, user=user, domain="HEALTH")
    await answer_all(db, user, session.id, JUST_ME_ANSWERS)

    state = await service.complete(db, user=user, session_id=session.id)

    assert state.session.status == STATUS_COMPLETED
    assert state.session.completed_at is not None
    assert state.session.questionnaire_version == HEALTH_BETA.version


async def test_completing_stores_priorities_in_the_order_chosen(
    db: AsyncSession,
) -> None:
    user = await make_user(db)
    session = await service.start_or_resume(db, user=user, domain="HEALTH")
    await answer_all(
        db,
        user,
        session.id,
        {**JUST_ME_ANSWERS, "priorities": ["broad_coverage", "low_copay"]},
    )

    await service.complete(db, user=user, session_id=session.id)

    profile = (await db.execute(select(PriorityProfile))).scalar_one()
    assert profile.questionnaire_session_id == session.id

    items = (
        (
            await db.execute(
                select(PriorityItem)
                .where(PriorityItem.priority_profile_id == profile.id)
                .order_by(PriorityItem.rank_order)
            )
        )
        .scalars()
        .all()
    )

    assert [item.factor_key for item in items] == ["broad_coverage", "low_copay"]
    assert [item.rank_order for item in items] == [1, 2]


async def test_a_completed_session_cannot_be_changed(db: AsyncSession) -> None:
    """Answers behind a completed run must not shift underneath it."""
    user = await make_user(db)
    session = await service.start_or_resume(db, user=user, domain="HEALTH")
    await answer_all(db, user, session.id, JUST_ME_ANSWERS)
    await service.complete(db, user=user, session_id=session.id)

    with pytest.raises(SessionAlreadyCompletedError):
        await service.save_answer(
            db, user=user, session_id=session.id, question_id="applicant_age", value=99
        )
    with pytest.raises(SessionAlreadyCompletedError):
        await service.complete(db, user=user, session_id=session.id)


async def test_completing_starts_a_fresh_draft_next_time(db: AsyncSession) -> None:
    user = await make_user(db)
    first = await service.start_or_resume(db, user=user, domain="HEALTH")
    await answer_all(db, user, first.id, JUST_ME_ANSWERS)
    await service.complete(db, user=user, session_id=first.id)

    second = await service.start_or_resume(db, user=user, domain="HEALTH")

    assert second.id != first.id


# ------------------------------------------------------------- authorization --


async def test_one_user_cannot_read_another_users_answers(db: AsyncSession) -> None:
    owner = await make_user(db, "owner@example.com")
    intruder = await make_user(db, "intruder@example.com")
    session = await service.start_or_resume(db, user=owner, domain="HEALTH")

    with pytest.raises(QuestionnaireSessionNotFoundError):
        await service.load_state(db, user=intruder, session_id=session.id)


async def test_one_user_cannot_answer_another_users_questionnaire(
    db: AsyncSession,
) -> None:
    owner = await make_user(db, "owner@example.com")
    intruder = await make_user(db, "intruder@example.com")
    session = await service.start_or_resume(db, user=owner, domain="HEALTH")

    with pytest.raises(QuestionnaireSessionNotFoundError):
        await service.save_answer(
            db,
            user=intruder,
            session_id=session.id,
            question_id="applicant_age",
            value=30,
        )


async def test_the_endpoints_require_a_session(api: AsyncClient) -> None:
    assert (await api.get("/api/v1/questionnaire-sessions/qs_x")).status_code == 401
    assert (
        await api.post("/api/v1/questionnaire-sessions", json={"domain": "HEALTH"})
    ).status_code == 401
    assert (await api.post("/api/v1/questionnaire-sessions/qs_x/complete")).status_code == 401
    assert (
        await api.put(
            "/api/v1/questionnaire-sessions/qs_x/answers/applicant_age", json={"value": 30}
        )
    ).status_code == 401
