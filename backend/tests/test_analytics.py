"""Analytics and feedback (docs/11_BUILD_PLAN.md Phase 15).

The build plan attaches one instruction to this phase: **do not send sensitive
answer values to analytics.** `docs/03_FRONTEND_ARCHITECTURE.md` section 7 and
`docs/12_BETA_CHECKLIST.md` say the same. So most of these tests try to get
sensitive data into an event and assert that it does not arrive.

The rest check that the funnel the beta checklist names actually fires, since
an event that exists in a registry but is never emitted measures nothing.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import service as analytics
from app.analytics.events import (
    BETA_CHECKLIST_EVENTS,
    EVENTS,
    POLICY_PROCESSING_COMPLETED,
    POLICY_QUESTION_ASKED,
    POLICY_UPLOAD_COMPLETED,
    PRIORITY_CHANGED,
    QUESTION_ANSWERED,
    QUESTIONNAIRE_COMPLETED,
    RECOMMENDATION_GENERATED,
    RECOMMENDATION_STARTED,
    UnknownEventError,
)
from app.analytics.models import AnalyticsEvent
from app.core.config import Settings
from app.extraction.pipeline import process_document
from app.feedback import service as feedback_service
from app.feedback.models import Feedback
from app.jobs.queue import DatabaseJobQueue
from app.policies import service as policy_service
from app.policies.storage import LocalFileStorage
from app.qa import service as qa_service
from app.questionnaires import service as questionnaire_service
from app.questionnaires.models import STATUS_COMPLETED
from app.recommendations import service as recommendation_service
from tests.test_extraction import POLICY_TEXT
from tests.test_policy_upload import pdf_bytes
from tests.test_questionnaire import JUST_ME_ANSWERS, answer_all, make_user


@pytest.fixture
def storage(tmp_path: Path) -> LocalFileStorage:
    return LocalFileStorage(Settings(app_env="local"), root=tmp_path / "uploads")


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="local", feature_policy_decoder=True)


async def events_named(db: AsyncSession, name: str) -> list[AnalyticsEvent]:
    return list(
        (await db.execute(select(AnalyticsEvent).where(AnalyticsEvent.name == name)))
        .scalars()
        .all()
    )


# ------------------------------------------------ nothing sensitive leaks ---


def test_an_undeclared_property_is_dropped() -> None:
    """The failure mode of a careless call site is a missing property, never
    a leaked answer."""
    clean = analytics.sanitize(
        QUESTION_ANSWERED,
        {"question_id": "applicant_age", "stage": "about-you", "value": 34},
    )

    assert clean == {"question_id": "applicant_age", "stage": "about-you"}
    assert "value" not in clean


def test_a_questionnaire_answer_cannot_be_recorded_under_any_key() -> None:
    """Every field the health questionnaire collects, offered to the event
    that is closest to being allowed to carry it."""
    sensitive = {
        "applicant_age": 34,
        "pincode": "560001",
        "broad_health_conditions": "yes",
        "spouse_age": 33,
        "approximate_budget": 20000,
        "answer": "yes",
        "answers": {"broad_health_conditions": "yes"},
        "value": "yes",
        "priorities": ["low_copay"],
    }

    clean = analytics.sanitize(QUESTION_ANSWERED, sensitive)

    assert clean == {}


def test_structured_values_are_dropped_even_on_a_declared_key() -> None:
    """A dict is how an answer payload travels. No event needs one."""
    clean = analytics.sanitize(QUESTION_ANSWERED, {"question_id": {"nested": "yes"}})

    assert clean == {}


def test_string_properties_are_bounded() -> None:
    """A property must not become a smuggling channel for free text."""
    clean = analytics.sanitize(QUESTION_ANSWERED, {"question_id": "x" * 5000})

    assert len(clean["question_id"]) <= analytics.MAX_VALUE_LENGTH


def test_an_undeclared_event_is_refused() -> None:
    with pytest.raises(UnknownEventError):
        analytics.sanitize("something_someone_invented", {})


def test_no_event_declares_a_property_that_could_hold_an_answer() -> None:
    """A static check on the registry itself.

    This is the test that would have to be edited to introduce the leak, which
    is exactly the point: adding such a property becomes a deliberate act with
    a visible diff.
    """
    forbidden = {
        "value",
        "values",
        "answer",
        "answers",
        "comment",
        "text",
        "content",
        "note",
        "email",
        "filename",
        "question_text",
        "priorities",
        "pincode",
        "age",
    }

    for definition in EVENTS.values():
        overlap = definition.allowed_properties & forbidden
        assert overlap == set(), f"{definition.name} declares {overlap}"


async def test_a_recorded_event_stores_only_the_clean_properties(db: AsyncSession) -> None:
    user = await make_user(db)

    await analytics.record(
        db,
        name=QUESTION_ANSWERED,
        user=user,
        properties={"question_id": "pincode", "stage": "about-you", "value": "560001"},
    )
    await db.commit()

    event = (await db.execute(select(AnalyticsEvent))).scalar_one()
    assert event.properties_json == {"question_id": "pincode", "stage": "about-you"}
    assert "560001" not in str(event.properties_json)


async def test_recording_never_breaks_the_thing_it_measures(db: AsyncSession) -> None:
    """A questionnaire submission must not fail because an event could not be
    written."""
    await analytics.record_safely(db, name="not_a_real_event", properties={"x": 1})

    assert await events_named(db, "not_a_real_event") == []


# ------------------------------------------------------------ the funnel ---


def test_every_event_the_beta_checklist_names_is_declared() -> None:
    for name in BETA_CHECKLIST_EVENTS:
        assert name in EVENTS, name


async def test_starting_and_completing_the_questionnaire_are_recorded(
    db: AsyncSession,
) -> None:
    user = await make_user(db)
    session = await questionnaire_service.start_or_resume(db, user=user, domain="HEALTH")
    await answer_all(db, user, session.id, JUST_ME_ANSWERS)
    state = await questionnaire_service.complete(db, user=user, session_id=session.id)

    assert state.session.status == STATUS_COMPLETED
    assert await events_named(db, RECOMMENDATION_STARTED)
    assert await events_named(db, QUESTIONNAIRE_COMPLETED)


async def test_generating_a_match_set_records_its_shape_not_its_content(
    db: AsyncSession,
) -> None:
    user = await make_user(db)
    session = await questionnaire_service.start_or_resume(db, user=user, domain="HEALTH")
    await answer_all(db, user, session.id, JUST_ME_ANSWERS)
    await questionnaire_service.complete(db, user=user, session_id=session.id)
    await recommendation_service.create_run(db, user=user, questionnaire_session_id=session.id)

    event = (await events_named(db, RECOMMENDATION_GENERATED))[0]
    assert event.properties_json["match_count"] > 0
    assert event.properties_json["excluded_count"] >= 0
    assert event.properties_json["scoring_version"]


async def test_changing_priorities_records_how_many_not_which(db: AsyncSession) -> None:
    """A priority is something the reader told us about themselves."""
    user = await make_user(db)
    session = await questionnaire_service.start_or_resume(db, user=user, domain="HEALTH")
    await answer_all(db, user, session.id, JUST_ME_ANSWERS)
    await questionnaire_service.complete(db, user=user, session_id=session.id)
    run = await recommendation_service.create_run(
        db, user=user, questionnaire_session_id=session.id
    )

    await recommendation_service.update_priorities(
        db, user=user, run_id=run.run.id, priorities=["broad_coverage", "low_copay"]
    )

    event = (await events_named(db, PRIORITY_CHANGED))[0]
    assert event.properties_json["priority_count"] == 2
    assert "broad_coverage" not in str(event.properties_json)


async def test_uploading_and_processing_a_policy_are_recorded(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user = await make_user(db)
    uploaded = await policy_service.create_policy_from_upload(
        db,
        user=user,
        storage=storage,
        queue=DatabaseJobQueue(db),
        settings=settings,
        filename="Sensitive Policy Name.pdf",
        data=pdf_bytes(text=POLICY_TEXT.strip()),
    )
    await process_document(
        db, policy_id=uploaded.policy.id, document_id=uploaded.documents[0].id, storage=storage
    )

    upload_event = (await events_named(db, POLICY_UPLOAD_COMPLETED))[0]
    assert upload_event.properties_json["page_count"] >= 1
    # The filename is the reader's, and identifies the document.
    assert "Sensitive" not in str(upload_event.properties_json)

    processed = (await events_named(db, POLICY_PROCESSING_COMPLETED))[0]
    assert processed.properties_json["outcome"] == "READY"
    assert processed.properties_json["facts_found"] >= 1


async def test_asking_a_question_records_the_answer_kind_not_the_question(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user = await make_user(db)
    uploaded = await policy_service.create_policy_from_upload(
        db,
        user=user,
        storage=storage,
        queue=DatabaseJobQueue(db),
        settings=settings,
        filename="wording.pdf",
        data=pdf_bytes(text=POLICY_TEXT.strip()),
    )
    await process_document(
        db, policy_id=uploaded.policy.id, document_id=uploaded.documents[0].id, storage=storage
    )

    await qa_service.ask(
        db,
        user=user,
        policy_id=uploaded.policy.id,
        question="Does this cover my diabetes treatment?",
    )

    event = (await events_named(db, POLICY_QUESTION_ASKED))[0]
    assert event.properties_json["answer_state"]
    # A question can contain a health condition. It must not reach analytics.
    assert "diabetes" not in str(event.properties_json)


# ----------------------------------------------------------- the feedback ---


async def test_feedback_records_a_rating_and_a_comment(db: AsyncSession) -> None:
    user = await make_user(db)

    await feedback_service.submit(
        db,
        user=user,
        context_type="DECODER",
        context_id="pol_1",
        rating=1,
        comment="The waiting period explanation finally made sense.",
    )

    entry = (await db.execute(select(Feedback))).scalar_one()
    assert entry.rating == 1
    assert entry.comment is not None and "waiting period" in entry.comment


async def test_the_feedback_comment_never_reaches_analytics(db: AsyncSession) -> None:
    """Free text has one home, and it is not the funnel."""
    user = await make_user(db)

    await feedback_service.submit(
        db,
        user=user,
        context_type="DECODER",
        rating=-1,
        comment="My policy number is 12345 and I am being treated for a heart condition.",
    )

    event = (await events_named(db, "feedback_submitted"))[0]
    serialised = str(event.properties_json)
    assert "12345" not in serialised
    assert "heart" not in serialised
    assert event.properties_json == {"context_type": "DECODER", "rating": -1}


async def test_a_comment_is_bounded(db: AsyncSession) -> None:
    """Long enough for a real complaint, short enough not to become a place
    people paste a policy document."""
    user = await make_user(db)

    await feedback_service.submit(db, user=user, context_type="GENERAL", comment="x" * 10_000)

    entry = (await db.execute(select(Feedback))).scalar_one()
    assert entry.comment is not None
    assert len(entry.comment) <= feedback_service.MAX_COMMENT_LENGTH


async def test_empty_feedback_is_refused(db: AsyncSession) -> None:
    user = await make_user(db)

    with pytest.raises(feedback_service.FeedbackRejectedError):
        await feedback_service.submit(db, user=user, context_type="GENERAL")


async def test_an_unknown_context_is_refused(db: AsyncSession) -> None:
    user = await make_user(db)

    with pytest.raises(feedback_service.FeedbackRejectedError):
        await feedback_service.submit(db, user=user, context_type="SOMETHING_ELSE", rating=1)


async def test_an_invalid_rating_is_refused(db: AsyncSession) -> None:
    user = await make_user(db)

    with pytest.raises(feedback_service.FeedbackRejectedError):
        await feedback_service.submit(db, user=user, context_type="GENERAL", rating=5)


async def test_the_comment_is_not_echoed_back_to_the_client(db: AsyncSession) -> None:
    """It is written for a human to read, not for the client to re-render."""
    from app.feedback.schemas import FeedbackView

    user = await make_user(db)
    entry = await feedback_service.submit(
        db, user=user, context_type="GENERAL", comment="something private"
    )

    assert "something private" not in FeedbackView.of(entry).model_dump_json()
