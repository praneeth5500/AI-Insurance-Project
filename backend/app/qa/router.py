"""Policy Q&A endpoints.

Scoped to the policy and its owner by the service. There is no endpoint that
answers a question without a policy — `docs/01_PRODUCT_SPEC.md` section 5
keeps Q&A inside policy context, and a general endpoint would quietly become
a chatbot.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser, DbSession
from app.core.errors import AppError
from app.policies.dependencies import DecoderEnabled
from app.qa import service
from app.qa.llm import build_llm_provider
from app.qa.models import ROLE_ASSISTANT
from app.qa.schemas import AnswerView, AskRequest, ConversationView, MessageView

router = APIRouter(prefix="/policies", tags=["qa"], dependencies=[DecoderEnabled])


class QuestionRejectedError(AppError):
    code = "QUESTION_REJECTED"
    http_status = 422
    message = "We couldn't use that question."


def _explanation_available() -> bool:
    return build_llm_provider().name != "none"


@router.get(
    "/{policy_id}/questions",
    response_model=ConversationView,
    summary="Your questions about this policy",
)
async def conversation(policy_id: str, user: CurrentUser, db: DbSession) -> ConversationView:
    messages = await service.history(db, user=user, policy_id=policy_id)
    return ConversationView(
        policy_id=policy_id,
        messages=[MessageView.of(message, citations) for message, citations in messages],
        explanation_available=_explanation_available(),
    )


@router.post(
    "/{policy_id}/questions",
    response_model=AnswerView,
    summary="Ask about this policy",
)
async def ask(policy_id: str, payload: AskRequest, user: CurrentUser, db: DbSession) -> AnswerView:
    try:
        result = await service.ask(db, user=user, policy_id=policy_id, question=payload.question)
    except service.QuestionTooLongError as exc:
        raise QuestionRejectedError(str(exc)) from exc
    assert result.message.role == ROLE_ASSISTANT
    return AnswerView.of(result)
