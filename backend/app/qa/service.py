"""Answering a question about the reader's own policy.

`docs/07_POLICY_DECODER_AI.md` section 7 fixes the flow:

    question -> retrieve clauses -> check evidence is sufficient
      -> answer from that evidence -> attach citations

and section 8 fixes what a material answer must contain: the answer, why, the
clause, the page, conditions, uncertainty, and a safe next step.

## What happens without a model

No provider is configured (open item 2). Rather than refusing the feature, the
assistant **quotes the policy** instead of paraphrasing it: it says which
sections address the question, shows the wording, cites the pages, and says
outright that it is quoting rather than explaining. That is less fluent than a
generated answer and completely grounded — and the reader is told which of the
two they are getting.

When a provider arrives, the same retrieval and the same sufficiency check run
first, and the model only ever sees clauses that passed them. A model that is
handed nothing but the retrieved wording cannot invent a clause.

## What is never said

Section 9's prohibitions are enforced by construction, not by asking nicely: no
code path here produces a claim outcome, an insurer's behaviour, a premium, or
a legal interpretation, because every answer is assembled from clause text plus
fixed framing. The one judgement the assistant makes is *which clauses are
relevant*, and it shows its working by citing them.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import service as analytics
from app.analytics.events import POLICY_QUESTION_ASKED
from app.core.logging import log_fields
from app.extraction.models import PolicyClause
from app.policies.errors import PolicyNotFoundError
from app.policies.models import STATUS_READY, UploadedPolicy
from app.qa.llm import GroundedAnswer, LlmProvider, LlmUnavailableError, build_llm_provider
from app.qa.models import (
    ANSWER_GROUNDED,
    ANSWER_INSUFFICIENT_EVIDENCE,
    ANSWER_TOO_BROAD,
    ANSWER_UNAVAILABLE,
    ROLE_ASSISTANT,
    ROLE_USER,
    Citation,
    Conversation,
    Message,
)
from app.qa.retrieval import RETRIEVAL_VERSION, Retrieved, retrieve, sufficient, tokenize
from app.users.models import User

logger = logging.getLogger(__name__)

MAX_QUESTION_LENGTH = 500

#: The refusal wording from docs/07_POLICY_DECODER_AI.md section 7, plus the
#: "suggest what to check next" the section requires immediately after it.
INSUFFICIENT_EVIDENCE_ANSWER = (
    "I couldn't determine that from the policy you uploaded.\n\n"
    "That may be because it is worded differently from what I searched for, or because it "
    "is in a part of the document I couldn't read. Two things worth trying: search the "
    "document itself for the term your insurer would use, or ask your insurer directly and "
    "ask them to point you at the clause."
)

#: Shown when a question carries no term specific enough to search on.
#:
#: "What is covered?" is one of the most natural things a reader asks, and it
#: is genuinely unanswerable by retrieval: every clause of every policy is
#: about what is covered. Answering it with the section 7 refusal would be
#: misleading — the policy *does* address it, just not in a way one search can
#: point at. So this says what the question needs instead, and sends the
#: reader to the report, which already answers it in structured form.
TOO_BROAD_ANSWER = (
    "That's a broad question, and your policy answers it in a lot of places at once — so "
    "I can't point you at one part of it.\n\n"
    "Two things that will work better: ask about something specific, like the waiting "
    "period, the co-payment, the room rent limit or what's excluded. Or read the summary "
    "above, which sets out what we could determine section by section."
)


@dataclass(frozen=True)
class AnswerResult:
    message: Message
    answer_state: str
    citations: list[tuple[Citation, PolicyClause]]
    #: True when the answer quotes the policy rather than explaining it.
    quoted_not_explained: bool


class QuestionTooLongError(ValueError):
    """The question is longer than we will accept."""


async def _policy_for(db: AsyncSession, *, user: User, policy_id: str) -> UploadedPolicy:
    policy = (
        await db.execute(
            select(UploadedPolicy).where(
                UploadedPolicy.id == policy_id,
                UploadedPolicy.user_id == user.id,
                UploadedPolicy.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if policy is None or policy.status != STATUS_READY:
        raise PolicyNotFoundError
    return policy


async def get_or_create_conversation(
    db: AsyncSession, *, user: User, policy_id: str
) -> Conversation:
    """One conversation per policy per reader.

    docs/01_PRODUCT_SPEC.md section 5: Q&A stays inside policy context. A
    conversation that could move between policies would be the general chat
    surface this product deliberately isn't.
    """
    await _policy_for(db, user=user, policy_id=policy_id)

    existing = (
        await db.execute(
            select(Conversation).where(
                Conversation.user_id == user.id, Conversation.policy_id == policy_id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    conversation = Conversation(user_id=user.id, policy_id=policy_id)
    db.add(conversation)
    await db.flush()
    return conversation


async def history(
    db: AsyncSession, *, user: User, policy_id: str
) -> list[tuple[Message, list[tuple[Citation, PolicyClause]]]]:
    conversation = await get_or_create_conversation(db, user=user, policy_id=policy_id)
    messages = list(
        (
            await db.execute(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.ordinal)
            )
        )
        .scalars()
        .all()
    )
    return [(message, await _citations_for(db, message)) for message in messages]


async def _next_ordinal(db: AsyncSession, conversation_id: str) -> int:
    """The next position in this conversation.

    Read inside the request's transaction, so a question and its answer get
    consecutive positions even though they share a `now()` timestamp.
    """
    current = (
        await db.execute(
            select(func.max(Message.ordinal)).where(Message.conversation_id == conversation_id)
        )
    ).scalar_one_or_none()
    return 0 if current is None else current + 1


async def _citations_for(db: AsyncSession, message: Message) -> list[tuple[Citation, PolicyClause]]:
    rows = (
        await db.execute(
            select(Citation, PolicyClause)
            .join(PolicyClause, Citation.policy_clause_id == PolicyClause.id)
            .where(Citation.message_id == message.id)
            .order_by(Citation.ordinal)
        )
    ).all()
    return [(citation, clause) for citation, clause in rows]


async def ask(
    db: AsyncSession,
    *,
    user: User,
    policy_id: str,
    question: str,
    llm: LlmProvider | None = None,
) -> AnswerResult:
    """Answer one question about one policy."""
    cleaned = question.strip()
    if not cleaned:
        raise QuestionTooLongError("A question is required.")
    if len(cleaned) > MAX_QUESTION_LENGTH:
        raise QuestionTooLongError("That question is longer than we can handle.")

    llm = llm or build_llm_provider()
    policy = await _policy_for(db, user=user, policy_id=policy_id)
    conversation = await get_or_create_conversation(db, user=user, policy_id=policy_id)

    next_ordinal = await _next_ordinal(db, conversation.id)
    db.add(
        Message(
            conversation_id=conversation.id,
            role=ROLE_USER,
            ordinal=next_ordinal,
            content=cleaned,
        )
    )
    await db.flush()

    clauses = list(
        (
            await db.execute(
                select(PolicyClause)
                .where(PolicyClause.policy_id == policy.id)
                .order_by(PolicyClause.ordinal)
            )
        )
        .scalars()
        .all()
    )

    retrieved = retrieve(cleaned, clauses)
    evidence = sufficient(retrieved)

    if not tokenize(cleaned):
        # Nothing in the question is specific enough to search on.
        result = await _record(
            db,
            conversation=conversation,
            text=TOO_BROAD_ANSWER,
            state=ANSWER_TOO_BROAD,
            evidence=[],
            metadata={"retrievalVersion": RETRIEVAL_VERSION},
            quoted_not_explained=False,
        )
        await _record_asked(db, user, result.answer_state)
        _log(user, policy.id)
        return result

    if not evidence:
        result = await _record(
            db,
            conversation=conversation,
            text=INSUFFICIENT_EVIDENCE_ANSWER,
            state=ANSWER_INSUFFICIENT_EVIDENCE,
            evidence=[],
            metadata={"retrievalVersion": RETRIEVAL_VERSION},
            quoted_not_explained=False,
        )
        await _record_asked(db, user, result.answer_state)
        _log(user, policy.id)
        return result

    generated: GroundedAnswer | None = None
    try:
        generated = await llm.answer(
            question=cleaned, evidence=[item.clause.source_text for item in evidence]
        )
    except LlmUnavailableError:
        generated = None

    if generated is None:
        # No model. Quote the policy rather than paraphrase it, and say so.
        result = await _record(
            db,
            conversation=conversation,
            text=_quoted_answer(evidence),
            state=ANSWER_UNAVAILABLE,
            evidence=evidence,
            metadata={"retrievalVersion": RETRIEVAL_VERSION, "model": None},
            quoted_not_explained=True,
        )
    else:
        used = [evidence[index] for index in generated.used_evidence if index < len(evidence)]
        result = await _record(
            db,
            conversation=conversation,
            text=generated.text,
            state=ANSWER_GROUNDED,
            evidence=used or evidence,
            metadata={
                "retrievalVersion": RETRIEVAL_VERSION,
                "provider": llm.name,
                "model": llm.model,
                "promptVersion": llm.prompt_version,
            },
            quoted_not_explained=False,
        )

    await _record_asked(db, user, result.answer_state)
    _log(user, policy.id)
    return result


def _quoted_answer(evidence: list[Retrieved]) -> str:
    """An answer made of the policy's own words.

    Deliberately says what it is doing. A reader who is shown wording and told
    it is wording knows to read it; one shown wording dressed as an answer
    might not.
    """
    lines = [
        "I can't explain this in my own words yet — that part of the assistant isn't "
        "switched on. What I can do is show you the parts of your policy that address it, "
        "so you can read the actual wording:",
        "",
    ]
    for index, item in enumerate(evidence, start=1):
        heading = item.clause.title or "Untitled section"
        lines.append(f"{index}. {heading} — page {item.clause.source_page}")
        lines.append(f"   “{_shorten(item.clause.source_text)}”")
        lines.append("")

    lines.append(
        "If this doesn't answer your question, the wording above is the part to take to "
        "your insurer — quoting the page number usually gets a faster answer."
    )
    return "\n".join(lines).strip()


def _shorten(text: str, limit: int = 600) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit].rsplit(" ", 1)[0] + "…"


async def _record(
    db: AsyncSession,
    *,
    conversation: Conversation,
    text: str,
    state: str,
    evidence: list[Retrieved],
    metadata: dict[str, object],
    quoted_not_explained: bool,
) -> AnswerResult:
    message = Message(
        conversation_id=conversation.id,
        role=ROLE_ASSISTANT,
        ordinal=await _next_ordinal(db, conversation.id),
        content=text,
        answer_state=state,
        model_metadata_json=metadata,
    )
    db.add(message)
    await db.flush()

    citations: list[tuple[Citation, PolicyClause]] = []
    for ordinal, item in enumerate(evidence):
        citation = Citation(
            message_id=message.id,
            policy_clause_id=item.clause.id,
            page_number=item.clause.source_page,
            ordinal=ordinal,
        )
        db.add(citation)
        citations.append((citation, item.clause))
    await db.flush()

    return AnswerResult(
        message=message,
        answer_state=state,
        citations=citations,
        quoted_not_explained=quoted_not_explained,
    )


async def _record_asked(db: AsyncSession, user: User, answer_state: str) -> None:
    """Count the question and what kind of answer it got — never its text."""
    await analytics.record_safely(
        db, name=POLICY_QUESTION_ASKED, user=user, properties={"answer_state": answer_state}
    )
    await db.commit()


def _log(user: User, policy_id: str) -> None:
    logger.info(
        "policy_question_asked",
        extra=log_fields(
            event="policy_question_asked",
            user_id=user.id,
            resource_type="uploaded_policy",
            resource_id=policy_id,
        ),
    )
