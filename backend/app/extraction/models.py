"""Extraction tables (docs/05_DATA_MODEL.md section 7).

`docs/07_POLICY_DECODER_AI.md` section 3 defines a three-layer truth model,
and these tables keep the layers physically apart:

* **Source layer** — `policy_pages` and `policy_clauses`: what the document
  actually says, verbatim, with page numbers.
* **Structured fact layer** — `policy_facts`: normalised values, each one
  pointing back at the clause it came from.
* **Explanation layer** — not stored here at all. Plain-language explanation
  is generated for display and is never allowed to become the source of
  truth.

The direction of that dependency is the point. A fact without a clause is a
guess, so `policy_facts.clause_id` is how a value earns the right to be shown;
`docs/07_POLICY_DECODER_AI.md` section 4 is blunt about the alternative:
never guess.

`docs/09_AWS_DEPLOYMENT.md` section 9 adds one operational rule that shapes
these columns: *do not index raw page text in ordinary logs.* Page text lives
in this table and nowhere else — not in the queue payload, not in an error
message, not in an audit row.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import new_id, timestamp_column

#: How a page's text was obtained. Recorded per page, because one document can
#: legitimately mix both — a born-digital wording with a scanned endorsement
#: stapled on the end.
METHOD_NATIVE = "NATIVE_PDF"
METHOD_OCR = "OCR"
METHOD_NONE = "NONE"

#: docs/07_POLICY_DECODER_AI.md section 5.
CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"
CONFIDENCE_NOT_FOUND = "NOT_FOUND"
CONFIDENCE_CONFLICTING = "CONFLICTING"

#: States that must never drive an automated conclusion (section 5). A fact in
#: one of these is shown to the reader as uncertain and excluded from
#: anything the product asserts.
UNRELIABLE_CONFIDENCE = frozenset({CONFIDENCE_LOW, CONFIDENCE_NOT_FOUND, CONFIDENCE_CONFLICTING})

RUN_RUNNING = "RUNNING"
RUN_SUCCEEDED = "SUCCEEDED"
RUN_FAILED = "FAILED"


class ExtractionRun(Base):
    """One attempt at reading a policy.

    Every input that could change the output is recorded — the schema version,
    which OCR provider ran, which model, which prompt version. A run months
    old should be explainable without guessing which pipeline produced it,
    exactly as a recommendation run is.
    """

    __tablename__ = "extraction_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("exr"))
    policy_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("uploaded_policies.id", ondelete="CASCADE"), nullable=False
    )
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    #: Null when no OCR was needed — running OCR on already-extractable pages
    #: is explicitly discouraged (section 11).
    ocr_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    #: Null while extraction is deterministic. Set when a model participates,
    #: so a run can always answer "did an AI touch this?".
    ai_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=RUN_RUNNING)
    #: A named cause, never a raw exception — an exception's text can carry
    #: document content.
    failure_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = timestamp_column(nullable=True)

    __table_args__ = (Index("ix_extraction_runs_policy", "policy_id"),)


class PolicyPage(Base):
    """One page of the source document, as text."""

    __tablename__ = "policy_pages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("pg"))
    document_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("policy_documents.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    #: The page's text. This is the reader's own document — it is never
    #: logged, never put in a queue payload and never sent to analytics.
    text: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(16), nullable=False)
    #: How much text was recovered relative to what a page usually holds.
    #: Null for a page that was never attempted.
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (Index("ix_policy_pages_document", "document_id", "page_number", unique=True),)


class PolicyClause(Base):
    """A segment of the document with a heading, kept verbatim.

    Verbatim matters: `docs/07_POLICY_DECODER_AI.md` section 6 requires every
    explanation to link to source wording, and a paraphrase stored here would
    quietly become the thing the reader is shown as "the policy says".
    """

    __tablename__ = "policy_clauses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("cls"))
    policy_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("uploaded_policies.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("policy_documents.id", ondelete="CASCADE"), nullable=False
    )
    #: Which decoder section this clause belongs under, when we can tell.
    clause_type: Mapped[str] = mapped_column(String(32), nullable=False)
    #: The heading as printed. Null when the segment had none.
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_page: Mapped[int] = mapped_column(Integer, nullable=False)
    #: Exactly what the document says.
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    #: Whitespace-normalised, for matching. Never shown as the source.
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    #: Order within the document, so clauses can be presented as they appear.
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (Index("ix_policy_clauses_policy", "policy_id", "ordinal"),)


class PolicyFact(Base):
    """One normalised fact, with the clause that supports it.

    `clause_id` is nullable only so a NOT_FOUND fact can be recorded — saying
    "we looked for this and it is not there" is itself useful, and far better
    than silence. Every fact with a *value* has a clause.
    """

    __tablename__ = "policy_facts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("pf"))
    policy_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("uploaded_policies.id", ondelete="CASCADE"), nullable=False
    )
    extraction_run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("extraction_runs.id", ondelete="CASCADE"), nullable=False
    )
    fact_key: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Null when the fact was looked for and not found (section 4).
    value_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    #: docs/SPEC_ISSUES.md issue 2: the specification shows confidence both as
    #: a number and as an enum. Both are kept — the number is what the
    #: extractor produced, the state is what the UI is allowed to reason
    #: about — and the state is derived from the number, never set apart
    #: from it.
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_state: Mapped[str] = mapped_column(String(16), nullable=False)
    clause_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("policy_clauses.id", ondelete="SET NULL"), nullable=True
    )
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: The exact sentence the value came from, so a citation can quote it.
    source_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Every candidate found, when they disagree. A CONFLICTING fact has to be
    #: able to show the reader *what* disagrees.
    alternatives_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_policy_facts_policy", "policy_id", "fact_key"),
        Index("ix_policy_facts_run", "extraction_run_id"),
    )

    @property
    def is_reliable(self) -> bool:
        return self.confidence_state not in UNRELIABLE_CONFIDENCE
