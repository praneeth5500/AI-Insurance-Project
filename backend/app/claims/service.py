"""Building and keeping a claims checklist.

`docs/01_PRODUCT_SPEC.md` section 3.6: explain claims-related clauses and
build a personalised document/action checklist. **It does not predict
guaranteed claim approval.**

The checklist is assembled from three separately-sourced groups
(`docs/07_POLICY_DECODER_AI.md` section 10), and the code path for each is
different on purpose:

* **Policy-specific** items are derived from clauses in the reader's own
  document. Each one carries the clause it came from, so it can be checked.
  If the document has no claims clauses, this group is empty — and saying so
  is more useful than filling it with plausible requirements.
* **General preparation** comes from the approved templates and is identical
  for every reader. It is never presented as something this policy requires.
* **Confirm with insurer** are questions, not answers. The policy does not
  say, so neither do we.

A checklist is created once per policy and then kept: ticking things off is
the point, and regenerating it on every visit would throw that away.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.claims.models import (
    ORIGIN_POLICY_SPECIFIC,
    STATUS_ACTIVE,
    STATUS_COMPLETED,
    ClaimsChecklistItem,
    ClaimsReadinessSession,
)
from app.claims.templates import general_items, insurer_questions
from app.core.logging import log_fields
from app.extraction.clauses import CLAUSE_AT_CLAIM_TIME
from app.extraction.models import PolicyClause
from app.policies.errors import PolicyNotFoundError
from app.policies.models import STATUS_READY, UploadedPolicy
from app.users.models import User

logger = logging.getLogger(__name__)

MAX_NOTE_LENGTH = 500

#: Words that, in a clause filed under "At Claim Time", indicate a concrete
#: thing the reader has to do or produce. Deliberately narrow: a clause that
#: merely mentions claims is not a requirement, and turning one into a
#: checklist item would be inventing an obligation.
_REQUIREMENT_MARKERS: tuple[tuple[str, str, str], ...] = (
    (
        "intimation",
        "Tell your insurer within the time your policy states",
        "Your policy sets out when the insurer must be told about a claim.",
    ),
    (
        "notify",
        "Tell your insurer within the time your policy states",
        "Your policy sets out when the insurer must be told about a claim.",
    ),
    (
        "documents",
        "Provide the documents your policy lists",
        "Your policy names the documents it expects with a claim.",
    ),
    (
        "original",
        "Keep the original documents",
        "Your policy refers to originals, so photocopies may not be enough.",
    ),
    (
        "pre-authorisation",
        "Arrange pre-authorisation before planned treatment",
        "Your policy refers to approval being arranged before treatment.",
    ),
    (
        "pre-authorization",
        "Arrange pre-authorisation before planned treatment",
        "Your policy refers to approval being arranged before treatment.",
    ),
    (
        "cashless",
        "Follow your policy's cashless process",
        "Your policy describes how cashless treatment is arranged.",
    ),
)


@dataclass(frozen=True)
class ChecklistItemWithSource:
    item: ClaimsChecklistItem
    clause: PolicyClause | None


@dataclass(frozen=True)
class Checklist:
    session: ClaimsReadinessSession
    items: list[ChecklistItemWithSource]
    policy: UploadedPolicy

    @property
    def completed_count(self) -> int:
        return sum(1 for entry in self.items if entry.item.completed)


class ChecklistItemNotFoundError(PolicyNotFoundError):
    code = "CHECKLIST_ITEM_NOT_FOUND"
    message = "We couldn't find that checklist item."


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


def _policy_specific_items(clauses: list[PolicyClause]) -> list[tuple[str, str, str, PolicyClause]]:
    """Requirements read from the reader's own claims clauses.

    Only clauses already filed under "At Claim Time" are considered, and only
    a narrow set of markers counts. Both limits exist for the same reason: an
    item in this group is a claim about what the document says, so a false
    positive here is an invented policy term.
    """
    found: dict[str, tuple[str, str, str, PolicyClause]] = {}

    for clause in clauses:
        if clause.clause_type != CLAUSE_AT_CLAIM_TIME:
            continue
        haystack = (clause.normalized_text or clause.source_text).lower()
        for marker, label, description in _REQUIREMENT_MARKERS:
            if marker not in haystack:
                continue
            key = label.lower().replace(" ", "_")[:60]
            # First clause wins, so the citation points at where the reader
            # should start reading rather than the last mention.
            found.setdefault(key, (key, label, description, clause))

    return list(found.values())


async def get_or_create(db: AsyncSession, *, user: User, policy_id: str) -> Checklist:
    """The checklist for one policy, built once and then kept."""
    policy = await _policy_for(db, user=user, policy_id=policy_id)

    session = (
        await db.execute(
            select(ClaimsReadinessSession).where(
                ClaimsReadinessSession.user_id == user.id,
                ClaimsReadinessSession.policy_id == policy_id,
            )
        )
    ).scalar_one_or_none()

    if session is None:
        session = ClaimsReadinessSession(user_id=user.id, policy_id=policy_id, status=STATUS_ACTIVE)
        db.add(session)
        await db.flush()
        await _build_items(db, session=session, policy=policy)
        await db.commit()

    return await _load(db, session=session, policy=policy)


async def _build_items(
    db: AsyncSession, *, session: ClaimsReadinessSession, policy: UploadedPolicy
) -> None:
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

    ordinal = 0
    for key, label, description, clause in _policy_specific_items(clauses):
        db.add(
            ClaimsChecklistItem(
                session_id=session.id,
                item_key=key,
                label=label,
                description=description,
                origin=ORIGIN_POLICY_SPECIFIC,
                source_clause_id=clause.id,
                source_page=clause.source_page,
                ordinal=ordinal,
            )
        )
        ordinal += 1

    for template in (*general_items(), *insurer_questions()):
        db.add(
            ClaimsChecklistItem(
                session_id=session.id,
                item_key=template.key,
                label=template.label,
                description=template.description,
                origin=template.origin,
                # No clause: these are not claims about this document, and a
                # citation would say otherwise.
                source_clause_id=None,
                source_page=None,
                ordinal=ordinal,
            )
        )
        ordinal += 1

    await db.flush()


async def _load(
    db: AsyncSession, *, session: ClaimsReadinessSession, policy: UploadedPolicy
) -> Checklist:
    rows = (
        await db.execute(
            select(ClaimsChecklistItem, PolicyClause)
            .outerjoin(PolicyClause, ClaimsChecklistItem.source_clause_id == PolicyClause.id)
            .where(ClaimsChecklistItem.session_id == session.id)
            .order_by(ClaimsChecklistItem.ordinal)
        )
    ).all()

    return Checklist(
        session=session,
        items=[ChecklistItemWithSource(item=item, clause=clause) for item, clause in rows],
        policy=policy,
    )


async def update_item(
    db: AsyncSession,
    *,
    user: User,
    policy_id: str,
    item_id: str,
    completed: bool | None = None,
    note: str | None = None,
) -> Checklist:
    """Tick an item off, or attach a note to it."""
    policy = await _policy_for(db, user=user, policy_id=policy_id)

    session = (
        await db.execute(
            select(ClaimsReadinessSession).where(
                ClaimsReadinessSession.user_id == user.id,
                ClaimsReadinessSession.policy_id == policy_id,
            )
        )
    ).scalar_one_or_none()
    if session is None:
        raise ChecklistItemNotFoundError

    item = (
        await db.execute(
            select(ClaimsChecklistItem).where(
                ClaimsChecklistItem.id == item_id,
                # Scoped to the session we just proved belongs to this user,
                # so an id from someone else's checklist cannot be updated.
                ClaimsChecklistItem.session_id == session.id,
            )
        )
    ).scalar_one_or_none()
    if item is None:
        raise ChecklistItemNotFoundError

    if completed is not None:
        item.completed = completed
    if note is not None:
        item.user_note = note.strip()[:MAX_NOTE_LENGTH] or None

    checklist = await _load(db, session=session, policy=policy)
    session.status = (
        STATUS_COMPLETED if checklist.completed_count == len(checklist.items) else STATUS_ACTIVE
    )
    await db.commit()

    logger.info(
        "claims_checklist_updated",
        extra=log_fields(
            event="claims_checklist_updated",
            user_id=user.id,
            resource_type="claims_readiness_session",
            resource_id=session.id,
        ),
    )
    return await _load(db, session=session, policy=policy)
