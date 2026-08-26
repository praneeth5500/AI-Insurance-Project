"""Q&A payloads.

Every assistant message carries its `answerState` and its citations. There is
no shape here that can express an answer without saying what kind of answer it
is — a grounded one, a quoted one, or a refusal.
"""

from __future__ import annotations

from datetime import datetime

from app.core.schema import ApiModel
from app.extraction.models import PolicyClause
from app.qa.models import Citation, Message
from app.qa.service import AnswerResult


class CitationView(ApiModel):
    ordinal: int
    page: int
    clause_title: str | None
    #: The wording itself, so a citation can be read without another request.
    clause_text: str


class MessageView(ApiModel):
    id: str
    role: str
    content: str
    #: Null on the reader's own messages.
    answer_state: str | None
    citations: list[CitationView]
    created_at: datetime

    @classmethod
    def of(cls, message: Message, citations: list[tuple[Citation, PolicyClause]]) -> MessageView:
        return cls(
            id=message.id,
            role=message.role,
            content=message.content,
            answer_state=message.answer_state,
            citations=[
                CitationView(
                    ordinal=citation.ordinal,
                    page=citation.page_number,
                    clause_title=clause.title,
                    clause_text=clause.source_text,
                )
                for citation, clause in citations
            ],
            created_at=message.created_at,
        )


class AskRequest(ApiModel):
    question: str


class ConversationView(ApiModel):
    policy_id: str
    messages: list[MessageView]
    #: Whether plain-language explanation is available. The UI says so up
    #: front rather than letting the reader discover it in an answer.
    explanation_available: bool


class AnswerView(ApiModel):
    message: MessageView
    #: True when the assistant quoted the policy instead of explaining it.
    quoted_not_explained: bool

    @classmethod
    def of(cls, result: AnswerResult) -> AnswerView:
        return cls(
            message=MessageView.of(result.message, result.citations),
            quoted_not_explained=result.quoted_not_explained,
        )
