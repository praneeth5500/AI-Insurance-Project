"""Claims readiness (docs/05_DATA_MODEL.md section 9).

`docs/01_PRODUCT_SPEC.md` section 3.6 sets the boundary: the beta explains
claims-related clauses and builds a personalised checklist. **It does not
predict guaranteed claim approval** — and `docs/07_POLICY_DECODER_AI.md`
section 9 lists promising a claim outcome first among the prohibitions.

`origin` is the column that keeps this honest. Section 10 requires the three
kinds of checklist item to be kept apart:

* a **policy-specific requirement**, read from a clause in this document;
* a **general preparation suggestion**, from an approved template, true of
  claims in general and not of this policy in particular;
* an **unknown**, where the policy does not say and the insurer must be asked.

"Do not blend them." A general suggestion presented as this policy's
requirement is an invented policy term; an unknown presented as a suggestion
hides that we do not know.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import new_id, timestamp_column

STATUS_ACTIVE = "ACTIVE"
STATUS_COMPLETED = "COMPLETED"

#: docs/07_POLICY_DECODER_AI.md section 10.
ORIGIN_POLICY_SPECIFIC = "POLICY_SPECIFIC"
ORIGIN_GENERAL_PREPARATION = "GENERAL_PREPARATION"
ORIGIN_CONFIRM_WITH_INSURER = "CONFIRM_WITH_INSURER"

ORIGINS = (ORIGIN_POLICY_SPECIFIC, ORIGIN_GENERAL_PREPARATION, ORIGIN_CONFIRM_WITH_INSURER)

#: What the reader is told each group is. The wording is part of the safety
#: property, not decoration: a group heading that blurred these would undo the
#: separation the column exists to enforce.
ORIGIN_LABELS: dict[str, str] = {
    ORIGIN_POLICY_SPECIFIC: "Your policy asks for this",
    ORIGIN_GENERAL_PREPARATION: "Generally worth having",
    ORIGIN_CONFIRM_WITH_INSURER: "Ask your insurer",
}

ORIGIN_EXPLANATIONS: dict[str, str] = {
    ORIGIN_POLICY_SPECIFIC: (
        "Read from your own policy document. Each one links to the wording it came from."
    ),
    ORIGIN_GENERAL_PREPARATION: (
        "Not from your policy — these are things insurers commonly ask for. Your policy may "
        "not require them, and it may require things not listed here."
    ),
    ORIGIN_CONFIRM_WITH_INSURER: (
        "Your document doesn't say, and we won't guess. These are worth a phone call before "
        "you need them."
    ),
}


class ClaimsReadinessSession(Base):
    __tablename__ = "claims_readiness_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("crs"))
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    policy_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("uploaded_policies.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_ACTIVE)
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = timestamp_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_claims_sessions_user", "user_id", "policy_id"),)


class ClaimsChecklistItem(Base):
    __tablename__ = "claims_checklist_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("cci"))
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("claims_readiness_sessions.id", ondelete="CASCADE"), nullable=False
    )
    item_key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    #: Which of the three kinds this is. Never blended.
    origin: Mapped[str] = mapped_column(String(32), nullable=False)
    #: Set only on POLICY_SPECIFIC items. An item claiming to come from the
    #: policy without a clause behind it would be exactly the invention this
    #: separation prevents, and a test enforces the pairing.
    source_clause_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("policy_clauses.id", ondelete="SET NULL"), nullable=True
    )
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: The reader's own note — a policy number, who they spoke to. Their data,
    #: treated like every other private field: stored here and nowhere else.
    user_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (Index("ix_claims_items_session", "session_id", "ordinal"),)
