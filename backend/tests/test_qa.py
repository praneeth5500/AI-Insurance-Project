"""Policy Q&A (docs/11_BUILD_PLAN.md Phase 13).

An assistant answering questions about someone's insurance is the highest-risk
surface in this product: it is conversational, so it reads as authoritative,
and it is about money the reader may be counting on. `docs/07_POLICY_DECODER_AI.md`
section 9 lists what it must never do.

These tests are mostly about the refusals — the question the policy does not
answer, the model that is not available — because those are the paths where a
plausible-sounding wrong answer would come from.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.extraction.models import PolicyClause
from app.extraction.pipeline import process_document
from app.jobs.queue import DatabaseJobQueue
from app.policies import service as policy_service
from app.policies.errors import PolicyNotFoundError
from app.policies.storage import LocalFileStorage
from app.qa import service
from app.qa.llm import GroundedAnswer, LlmUnavailableError, UnavailableLlmProvider
from app.qa.models import (
    ANSWER_INSUFFICIENT_EVIDENCE,
    ANSWER_UNAVAILABLE,
    ROLE_ASSISTANT,
    ROLE_USER,
    Message,
)
from app.qa.retrieval import MIN_RELEVANCE, retrieve, sufficient
from app.qa.schemas import AnswerView
from app.users.models import User
from tests.test_extraction import POLICY_TEXT
from tests.test_policy_upload import pdf_bytes
from tests.test_questionnaire import make_user


@pytest.fixture
def storage(tmp_path: Path) -> LocalFileStorage:
    return LocalFileStorage(Settings(app_env="local"), root=tmp_path / "uploads")


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="local", feature_policy_decoder=True)


async def ready_policy(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings, *, email: str = "r@example.com"
) -> tuple[User, str]:
    user = await make_user(db, email)
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
    return user, uploaded.policy.id


async def clauses_for(db: AsyncSession, policy_id: str) -> list[PolicyClause]:
    return list(
        (
            await db.execute(
                select(PolicyClause)
                .where(PolicyClause.policy_id == policy_id)
                .order_by(PolicyClause.ordinal)
            )
        )
        .scalars()
        .all()
    )


# -------------------------------------------------------------- retrieval ---


async def test_a_question_finds_the_clause_that_answers_it(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    _, policy_id = await ready_policy(db, storage, settings)
    clauses = await clauses_for(db, policy_id)

    found = sufficient(retrieve("How long until my pre-existing condition is covered?", clauses))

    assert found
    assert found[0].clause.title == "WAITING PERIODS"


async def test_retrieval_is_deterministic(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """A reader who asks the same words twice must get the same citations."""
    _, policy_id = await ready_policy(db, storage, settings)
    clauses = await clauses_for(db, policy_id)

    first = retrieve("what is the co-payment", clauses)
    second = retrieve("what is the co-payment", clauses)

    assert [(item.clause.id, item.score) for item in first] == [
        (item.clause.id, item.score) for item in second
    ]


async def test_words_common_to_every_clause_do_not_decide_relevance(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """ "policy", "insured" and "cover" are in every clause of every policy.

    If they scored, the top result would be whichever clause is longest.
    """
    _, policy_id = await ready_policy(db, storage, settings)
    clauses = await clauses_for(db, policy_id)

    found = sufficient(retrieve("policy insured cover", clauses))

    assert found == []


async def test_a_question_the_policy_does_not_address_retrieves_nothing(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    _, policy_id = await ready_policy(db, storage, settings)
    clauses = await clauses_for(db, policy_id)

    assert sufficient(retrieve("Which dentist should I register with?", clauses)) == []


async def test_at_most_three_clauses_are_used(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """Few enough that the reader can check them all."""
    _, policy_id = await ready_policy(db, storage, settings)
    clauses = await clauses_for(db, policy_id)

    assert len(sufficient(retrieve("waiting period cover claim room exclusion", clauses))) <= 3


def test_the_relevance_floor_is_not_zero() -> None:
    """One coincidental word in common is not evidence."""
    assert MIN_RELEVANCE > 0


# ----------------------------------------------------------- the answers ---


async def test_an_answer_quotes_the_policy_and_says_that_is_what_it_is_doing(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """No model is configured (open item 2).

    The assistant shows the wording rather than paraphrasing it, and tells the
    reader which of the two it is doing — wording dressed as an answer is what
    makes an ungrounded assistant dangerous.
    """
    user, policy_id = await ready_policy(db, storage, settings)

    result = await service.ask(
        db, user=user, policy_id=policy_id, question="How long is the waiting period?"
    )

    assert result.answer_state == ANSWER_UNAVAILABLE
    assert result.quoted_not_explained is True
    assert "can't explain this in my own words yet" in result.message.content
    assert "36 months" in result.message.content


async def test_every_grounded_answer_carries_its_citations(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """docs/07_POLICY_DECODER_AI.md section 8: the clause and the page."""
    user, policy_id = await ready_policy(db, storage, settings)

    result = await service.ask(
        db, user=user, policy_id=policy_id, question="What is the co-payment on a claim?"
    )

    assert result.citations
    for citation, clause in result.citations:
        assert citation.page_number >= 1
        assert citation.policy_clause_id == clause.id
        assert clause.source_text


async def test_a_question_the_policy_cannot_answer_gets_the_specified_refusal(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """docs/07_POLICY_DECODER_AI.md section 7, including "suggest what to
    check next"."""
    user, policy_id = await ready_policy(db, storage, settings)

    result = await service.ask(
        db,
        user=user,
        policy_id=policy_id,
        question="Which dentist should I register with in Bangalore?",
    )

    assert result.answer_state == ANSWER_INSUFFICIENT_EVIDENCE
    assert result.message.content.startswith(
        "I couldn't determine that from the policy you uploaded."
    )
    assert "ask your insurer directly" in result.message.content
    # A refusal cites nothing: there is nothing it was based on.
    assert result.citations == []


async def test_a_refusal_never_dresses_itself_up_as_an_answer(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user, policy_id = await ready_policy(db, storage, settings)

    result = await service.ask(
        db, user=user, policy_id=policy_id, question="Will my claim be approved?"
    )

    lowered = result.message.content.lower()
    for forbidden in ("yes", "will be approved", "guaranteed", "you are covered for"):
        assert forbidden not in lowered


async def test_no_answer_promises_a_claim_outcome_or_a_premium(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """docs/07_POLICY_DECODER_AI.md section 9."""
    user, policy_id = await ready_policy(db, storage, settings)

    for question in (
        "Will my hospital bill be paid in full?",
        "How much will this policy cost me next year?",
        "Should I ignore the waiting period clause?",
    ):
        result = await service.ask(db, user=user, policy_id=policy_id, question=question)
        lowered = result.message.content.lower()
        assert "will be paid" not in lowered
        assert "premium will be" not in lowered
        assert "you can ignore" not in lowered


async def test_a_model_answer_is_used_when_a_provider_exists(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """The generated path is real code, not a branch that has never run."""

    class StubLlm:
        name = "stub"
        model = "stub-1"
        prompt_version = "v1"

        async def answer(self, *, question: str, evidence: list[str]) -> GroundedAnswer:
            # A model only ever sees the retrieved clauses.
            assert evidence
            return GroundedAnswer(text="Your policy waits 36 months.", used_evidence=(0,))

    user, policy_id = await ready_policy(db, storage, settings)

    result = await service.ask(
        db,
        user=user,
        policy_id=policy_id,
        question="How long is the pre-existing waiting period?",
        llm=StubLlm(),
    )

    assert result.answer_state == "GROUNDED"
    assert result.quoted_not_explained is False
    assert result.message.content == "Your policy waits 36 months."
    assert result.message.model_metadata_json is not None
    assert result.message.model_metadata_json["model"] == "stub-1"
    assert result.citations


async def test_the_model_is_never_asked_about_a_question_that_failed_retrieval(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """The sufficiency check runs first.

    A model handed weak evidence still writes a confident paragraph, which is
    exactly the failure section 7's check exists to prevent.
    """
    asked = False

    class SpyLlm(UnavailableLlmProvider):
        async def answer(self, *, question: str, evidence: list[str]) -> GroundedAnswer:
            nonlocal asked
            asked = True
            raise LlmUnavailableError("should not be reached")

    user, policy_id = await ready_policy(db, storage, settings)

    await service.ask(
        db,
        user=user,
        policy_id=policy_id,
        question="Which dentist should I register with in Bangalore?",
        llm=SpyLlm(),
    )

    assert asked is False


async def test_an_outage_produces_the_quoted_answer_not_an_error(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """docs/12_BETA_CHECKLIST.md: AI outage handled.

    The reader still gets their policy's wording. Losing the explanation is a
    degradation; losing the answer entirely would not be.
    """

    class BrokenLlm(UnavailableLlmProvider):
        async def answer(self, *, question: str, evidence: list[str]) -> GroundedAnswer:
            raise LlmUnavailableError("provider down")

    user, policy_id = await ready_policy(db, storage, settings)

    result = await service.ask(
        db,
        user=user,
        policy_id=policy_id,
        question="What is the room rent limit?",
        llm=BrokenLlm(),
    )

    assert result.answer_state == ANSWER_UNAVAILABLE
    assert result.citations
    assert "1%" in result.message.content


# ------------------------------------------------------------ conversation ---


async def test_a_conversation_belongs_to_one_policy(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """docs/01_PRODUCT_SPEC.md section 5: Q&A stays inside policy context."""
    user, policy_id = await ready_policy(db, storage, settings)

    first = await service.get_or_create_conversation(db, user=user, policy_id=policy_id)
    second = await service.get_or_create_conversation(db, user=user, policy_id=policy_id)

    assert first.id == second.id
    assert first.policy_id == policy_id


async def test_history_returns_the_exchange_in_order(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user, policy_id = await ready_policy(db, storage, settings)
    await service.ask(db, user=user, policy_id=policy_id, question="What is the co-payment?")

    messages = await service.history(db, user=user, policy_id=policy_id)

    assert [message.role for message, _ in messages] == [ROLE_USER, ROLE_ASSISTANT]


async def test_a_question_that_is_too_long_is_refused(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user, policy_id = await ready_policy(db, storage, settings)

    with pytest.raises(service.QuestionTooLongError):
        await service.ask(db, user=user, policy_id=policy_id, question="a" * 5000)


async def test_one_user_cannot_ask_about_another_users_policy(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    _, policy_id = await ready_policy(db, storage, settings, email="owner@example.com")
    intruder = await make_user(db, "intruder@example.com")

    with pytest.raises(PolicyNotFoundError):
        await service.ask(
            db, user=intruder, policy_id=policy_id, question="What is the co-payment?"
        )


async def test_a_policy_that_is_not_ready_cannot_be_questioned(
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

    with pytest.raises(PolicyNotFoundError):
        await service.ask(db, user=user, policy_id=uploaded.policy.id, question="What is covered?")


async def test_the_response_says_whether_explanation_is_available(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """The reader is told up front, not left to discover it in an answer."""
    user, policy_id = await ready_policy(db, storage, settings)
    result = await service.ask(
        db, user=user, policy_id=policy_id, question="What is the room rent limit?"
    )

    view = AnswerView.of(result)

    assert view.quoted_not_explained is True


async def test_the_stored_exchange_records_how_it_was_produced(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user, policy_id = await ready_policy(db, storage, settings)
    await service.ask(db, user=user, policy_id=policy_id, question="What is the co-payment?")

    message = (
        (await db.execute(select(Message).where(Message.role == ROLE_ASSISTANT))).scalars().first()
    )

    assert message is not None
    assert message.model_metadata_json is not None
    assert message.model_metadata_json["retrievalVersion"]
    # No model was involved, and that is recorded rather than left ambiguous.
    assert message.model_metadata_json.get("model") is None


async def test_deleting_a_policy_takes_its_conversation_with_it(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """A question about a deleted policy is still data about that policy."""
    user, policy_id = await ready_policy(db, storage, settings)
    await service.ask(db, user=user, policy_id=policy_id, question="What is the co-payment?")

    await policy_service.delete_policy(db, user=user, policy_id=policy_id, storage=storage)
    # The policy row is soft-deleted, so cascade has not fired; what matters
    # is that the conversation is no longer reachable.
    with pytest.raises(PolicyNotFoundError):
        await service.history(db, user=user, policy_id=policy_id)


async def test_a_question_too_broad_to_search_is_told_what_would_work_instead(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """ "What is covered?" is natural, and genuinely unanswerable by retrieval:
    every clause of every policy is about what is covered.

    Answering it with the section 7 refusal would mislead — the policy does
    address it, just not in a way one search can point at.
    """
    user, policy_id = await ready_policy(db, storage, settings)

    result = await service.ask(db, user=user, policy_id=policy_id, question="What is covered?")

    assert result.answer_state == "TOO_BROAD"
    assert "broad question" in result.message.content
    assert "waiting period" in result.message.content
    assert result.citations == []
    # It must not claim the policy is silent on it.
    assert "couldn't determine that from the policy" not in result.message.content
