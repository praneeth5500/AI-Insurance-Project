"""Uploaded policies and their documents (docs/05_DATA_MODEL.md section 7).

Phase 10 creates the two tables the upload flow needs. The extraction tables
— pages, clauses, facts, runs — arrive in Phase 11 with the worker that fills
them, rather than standing empty in the meantime.

Two things about this data are different from everything else in the build,
and shape the columns:

* **It is the user's own document**, not catalogue data. It is private, it is
  deletable, and it must never be logged
  (`docs/09_AWS_DEPLOYMENT.md` section 9, `CLAUDE.md` rules 6 and 7). The
  bytes live in object storage; this table holds only a key pointing at them.
* **A failed extraction stays visibly failed.** `CLAUDE.md`: a failed
  extraction must remain visibly failed or uncertain. So status is explicit,
  a failure reason is stored, and nothing collapses a failure into an empty
  success.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import new_id, timestamp_column

#: The stages from docs/01_PRODUCT_SPEC.md section 3.3, in order. They are
#: named stages rather than a percentage because
#: docs/02_UX_UI_SPEC.md section 14 says no fake percentages — and any
#: percentage here would be invented.
STATUS_RECEIVED = "RECEIVED"
STATUS_READING = "READING"
STATUS_FINDING_CLAUSES = "FINDING_CLAUSES"
STATUS_BUILDING_SUMMARY = "BUILDING_SUMMARY"
STATUS_PREPARING_QA = "PREPARING_QA"
STATUS_READY = "READY"
STATUS_FAILED = "FAILED"

#: Ordered, so the UI can show a stage list with the current one marked and
#: the reader can see both where they are and what is still to come.
PROCESSING_STAGES: tuple[str, ...] = (
    STATUS_RECEIVED,
    STATUS_READING,
    STATUS_FINDING_CLAUSES,
    STATUS_BUILDING_SUMMARY,
    STATUS_PREPARING_QA,
    STATUS_READY,
)

STAGE_LABELS: dict[str, str] = {
    STATUS_RECEIVED: "Uploaded",
    STATUS_READING: "Reading document",
    STATUS_FINDING_CLAUSES: "Finding important clauses",
    STATUS_BUILDING_SUMMARY: "Building summary",
    STATUS_PREPARING_QA: "Preparing Q&A",
    STATUS_READY: "Ready",
    STATUS_FAILED: "Couldn't be read",
}


class UploadedPolicy(Base):
    __tablename__ = "uploaded_policies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("pol"))
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    #: HEALTH, MOTOR, or null when the reader has not said and we have not
    #: read the document yet. Never guessed from a filename.
    domain: Mapped[str | None] = mapped_column(String(16), nullable=True)
    #: What the reader calls this policy. Defaults to the filename they chose,
    #: which is theirs to change.
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=STATUS_RECEIVED)

    #: Why processing failed, in language a reader can act on. Written by us
    #: from a known set of causes — never a raw exception, which could carry
    #: document content into a place it does not belong.
    failure_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())
    ready_at: Mapped[datetime | None] = timestamp_column(nullable=True)
    #: Set when the reader deletes the policy. The row survives briefly so a
    #: deletion can be audited; the documents themselves go immediately.
    deleted_at: Mapped[datetime | None] = timestamp_column(nullable=True)

    __table_args__ = (Index("ix_uploaded_policies_user", "user_id", "created_at"),)

    @property
    def is_failed(self) -> bool:
        return self.status == STATUS_FAILED


class PolicyDocument(Base):
    """One file belonging to an uploaded policy."""

    __tablename__ = "policy_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("doc"))
    policy_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("uploaded_policies.id", ondelete="CASCADE"), nullable=False
    )
    #: The object-storage key. Derived from identifiers, never from the
    #: filename the client sent (`app.policies.storage`).
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    #: The reader's own filename, kept so the UI can show what they uploaded.
    #: Treated as untrusted display text and never used to build a path.
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    #: The type we *determined*, not the one the client claimed.
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    #: Lets a re-upload of the same file be recognised, and gives a stored
    #: document an integrity check that does not require reading it.
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: Set when a PDF is encrypted. Recorded rather than inferred later,
    #: because it is the difference between "we could not read this" and
    #: "this file needs a password" — and the reader can act on the second.
    is_encrypted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: Anything the validator learned and the worker will want, e.g. whether
    #: the PDF carries an extractable text layer.
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())
    #: Set when the bytes are removed from storage. The row stays so a
    #: deletion is provable.
    deleted_at: Mapped[datetime | None] = timestamp_column(nullable=True)

    __table_args__ = (Index("ix_policy_documents_policy", "policy_id"),)


class PolicyDeletionAudit(Base):
    """Proof that a deletion happened, holding nothing about the document.

    `docs/12_BETA_CHECKLIST.md` requires a working delete path. A delete that
    leaves no trace cannot be shown to work, and a trace that keeps the
    filename or the text would defeat the deletion — so this records only
    identifiers and a timestamp.
    """

    __tablename__ = "policy_deletion_audits"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("pda"))
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    documents_removed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    #: Whether every object was confirmed gone from storage. False means the
    #: bytes may still exist somewhere and someone needs to look.
    storage_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())

    __table_args__ = (Index("ix_policy_deletion_audits_user", "user_id"),)
