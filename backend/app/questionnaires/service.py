"""Questionnaire use cases.

Two properties matter most here:

1. **The answers are the only source of truth.** Which questions apply is
   recomputed from them on every read, so changing an earlier answer cannot
   leave a stale branch behind.
2. **Nothing is inferred.** A question the user has not reached is simply
   unanswered; it is never given a default.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log_fields
from app.db.types import utcnow
from app.questionnaires import repository as repo
from app.questionnaires.definitions import QuestionDefinition, QuestionnaireDefinition
from app.questionnaires.errors import (
    QuestionnaireIncompleteError,
    QuestionnaireSessionNotFoundError,
    QuestionNotApplicableError,
    QuestionNotFoundError,
    SessionAlreadyCompletedError,
)
from app.questionnaires.health_beta import HEALTH_BETA, PRIORITY_QUESTION_ID
from app.questionnaires.models import (
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    PriorityItem,
    PriorityProfile,
    QuestionnaireAnswer,
    QuestionnaireSession,
)
from app.questionnaires.validation import validate_answer
from app.users.models import User

logger = logging.getLogger(__name__)

#: Only health is seeded. Motor is architecturally supported but has no
#: question set (docs/13_DECISIONS_AND_OPEN_ITEMS.md open item 8).
DEFINITIONS: dict[str, QuestionnaireDefinition] = {HEALTH_BETA.domain: HEALTH_BETA}


def get_definition(domain: str) -> QuestionnaireDefinition:
    definition = DEFINITIONS.get(domain)
    if definition is None:
        raise QuestionnaireSessionNotFoundError("That questionnaire isn't available yet.")
    return definition


@dataclass(frozen=True)
class SessionState:
    """Everything needed to render the flow, computed fresh on every read."""

    session: QuestionnaireSession
    definition: QuestionnaireDefinition
    answers: dict[str, Any]
    visible: list[QuestionDefinition]

    @property
    def unanswered_required(self) -> list[QuestionDefinition]:
        return [
            question
            for question in self.visible
            if question.required and self.answers.get(question.data_field) is None
        ]

    @property
    def next_question(self) -> QuestionDefinition | None:
        """The first visible question still needing an answer."""
        return next(iter(self.unanswered_required), None)

    @property
    def is_complete(self) -> bool:
        return not self.unanswered_required


async def start_or_resume(db: AsyncSession, *, user: User, domain: str) -> QuestionnaireSession:
    """Return the user's in-progress draft, creating one if there is none.

    Resuming rather than starting fresh is what makes "continue where you left
    off" possible (docs/01_PRODUCT_SPEC.md section 5).
    """
    definition = get_definition(domain)

    existing = await repo.get_active_session(
        db, user_id=user.id, domain=domain, version=definition.version
    )
    if existing is not None:
        return existing

    session = QuestionnaireSession(
        user_id=user.id,
        domain=domain,
        questionnaire_version=definition.version,
        status=STATUS_IN_PROGRESS,
    )
    db.add(session)
    await db.commit()
    logger.info(
        "questionnaire_session_started",
        extra=log_fields(
            event="questionnaire_session_started",
            user_id=user.id,
            resource_type="questionnaire_session",
            resource_id=session.id,
        ),
    )
    return session


async def load_state(db: AsyncSession, *, user: User, session_id: str) -> SessionState:
    session = await repo.get_session_for_user(db, session_id=session_id, user_id=user.id)
    if session is None:
        raise QuestionnaireSessionNotFoundError

    definition = get_definition(session.domain)
    stored = await repo.list_answers(db, session_id=session.id)

    answers: dict[str, Any] = {}
    for answer in stored:
        question = definition.question(answer.question_id)
        if question is not None:
            answers[question.data_field] = answer.answer_json.get("value")

    visible = definition.visible_questions(answers)
    visible_fields = {question.data_field for question in visible}

    # An answer to a question that is no longer applicable is kept in the
    # database — the user did give it — but excluded from the working set so
    # it cannot influence branching or completeness.
    applicable = {field: value for field, value in answers.items() if field in visible_fields}

    return SessionState(session=session, definition=definition, answers=applicable, visible=visible)


async def save_answer(
    db: AsyncSession, *, user: User, session_id: str, question_id: str, value: Any
) -> SessionState:
    """Persist one answer. This is the draft checkpoint."""
    state = await load_state(db, user=user, session_id=session_id)

    if state.session.status == STATUS_COMPLETED:
        raise SessionAlreadyCompletedError

    question = state.definition.question(question_id)
    if question is None:
        raise QuestionNotFoundError
    if question not in state.visible:
        # Answering a hidden question would let a caller bypass branching.
        raise QuestionNotApplicableError

    normalized = validate_answer(question, value)

    existing = await repo.get_answer(db, session_id=session_id, question_id=question_id)
    if existing is None:
        db.add(
            QuestionnaireAnswer(
                session_id=session_id,
                question_id=question_id,
                answer_json={"value": normalized},
                sensitive=question.sensitive,
            )
        )
    else:
        existing.answer_json = {"value": normalized}
        existing.sensitive = question.sensitive

    await db.commit()

    # The question id is safe to log; the value never is.
    logger.info(
        "questionnaire_answer_saved",
        extra=log_fields(
            event="questionnaire_answer_saved",
            user_id=user.id,
            resource_type="questionnaire_session",
            resource_id=session_id,
        ),
    )

    return await load_state(db, user=user, session_id=session_id)


async def complete(db: AsyncSession, *, user: User, session_id: str) -> SessionState:
    """Mark the session complete, after checking every required answer exists."""
    state = await load_state(db, user=user, session_id=session_id)

    if state.session.status == STATUS_COMPLETED:
        raise SessionAlreadyCompletedError
    if not state.is_complete:
        raise QuestionnaireIncompleteError

    state.session.status = STATUS_COMPLETED
    state.session.completed_at = utcnow()

    await _persist_priorities(db, state)
    await db.commit()

    logger.info(
        "questionnaire_completed",
        extra=log_fields(
            event="questionnaire_completed",
            user_id=user.id,
            resource_type="questionnaire_session",
            resource_id=session_id,
        ),
    )
    return await load_state(db, user=user, session_id=session_id)


async def _persist_priorities(db: AsyncSession, state: SessionState) -> None:
    """Turn the chosen priorities into structured rows.

    The engine reads these, not the raw answer. Weighting is not decided here:
    it lives in versioned scoring configuration
    (docs/06_RECOMMENDATION_ENGINE.md section 6).
    """
    question = state.definition.question(PRIORITY_QUESTION_ID)
    if question is None:
        return

    chosen = state.answers.get(question.data_field)
    if not isinstance(chosen, list) or not chosen:
        return

    profile = PriorityProfile(
        questionnaire_session_id=state.session.id,
        domain=state.session.domain,
        version=state.session.questionnaire_version,
    )
    db.add(profile)
    await db.flush()

    for rank, factor_key in enumerate(chosen, start=1):
        db.add(
            PriorityItem(
                priority_profile_id=profile.id,
                factor_key=factor_key,
                # Everything chosen here is a top-3 pick; finer levels come
                # from the results-page editor in a later phase.
                priority_level="HIGH",
                rank_order=rank,
            )
        )


__all__ = [
    "STATUS_COMPLETED",
    "STATUS_IN_PROGRESS",
    "SessionState",
    "complete",
    "get_definition",
    "load_state",
    "save_answer",
    "start_or_resume",
]
