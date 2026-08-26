"""Q&A tables (docs/05_DATA_MODEL.md section 8).

A conversation belongs to one policy. `docs/01_PRODUCT_SPEC.md` section 5 is
explicit that Q&A stays inside policy context and never becomes a general
chat surface — the scoping here is what makes that structural rather than a
convention.

Message content is the reader's own question and our answer about their own
policy. It is treated exactly like page text: stored here, never logged, never
sent to analytics (`docs/09_AWS_DEPLOYMENT.md` section 9).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import new_id, timestamp_column

ROLE_USER = "USER"
ROLE_ASSISTANT = "ASSISTANT"

#: Why an answer turned out the way it did. Stored so a conversation can be
#: audited later without re-running retrieval.
ANSWER_GROUNDED = "GROUNDED"
ANSWER_INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
ANSWER_UNAVAILABLE = "UNAVAILABLE"
ANSWER_TOO_BROAD = "TOO_BROAD"


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("cnv"))
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    #: Not nullable: a conversation with no policy would be a general chatbot,
    #: which this product is deliberately not.
    policy_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("uploaded_policies.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())

    __table_args__ = (Index("ix_conversations_policy", "policy_id", "user_id"),)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("msg"))
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    #: Position in the conversation. Explicit, because `created_at` defaults to
    #: `now()` — which in PostgreSQL is *transaction* start time, so a question
    #: and the answer written in the same transaction share a timestamp and
    #: cannot be ordered by it.
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    #: Set on assistant messages. Which answer path produced this, so an
    #: answer's grounding can be checked without guessing.
    answer_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    #: Which model, which prompt, which retrieval version. Null while no model
    #: participates — recorded rather than left ambiguous.
    model_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())

    __table_args__ = (Index("ix_messages_conversation", "conversation_id", "ordinal"),)


class Citation(Base):
    """What an answer was based on.

    `docs/07_POLICY_DECODER_AI.md` section 8 requires the clause and the
    page on every material answer. A grounded answer with no citation rows is
    a contradiction in terms, and a test enforces it.
    """

    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("cit"))
    message_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    policy_clause_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("policy_clauses.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    #: The span within the clause that was quoted, when a narrower quote was
    #: shown than the whole clause.
    quote_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quote_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: Order shown, so the reader's numbered references stay stable.
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (Index("ix_citations_message", "message_id", "ordinal"),)
