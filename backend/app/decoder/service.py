"""Assembling the decoder report.

Reads what extraction stored — facts, their clauses, their pages — and
arranges it into the sections `docs/01_PRODUCT_SPEC.md` section 3.4 names.
Nothing is computed about the policy here; the report is a *view*.

Two rules decide most of the shape:

* **An unknown is shown, not hidden.** `docs/12_BETA_CHECKLIST.md` requires a
  visible not-found state and a visible conflicting state. A section that
  quietly omitted the facts we could not find would tell the reader their
  policy has no waiting period, which is the opposite of true.
* **Every stated value links to its source.** Section 6 ends every card with
  "Source: Page X · Clause Y", and the clause text travels with the card so
  the reader can check the wording themselves without leaving the page.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.decoder.content import CONTENT, SECTION_ORDER, describe_value
from app.extraction.models import (
    CONFIDENCE_CONFLICTING,
    CONFIDENCE_NOT_FOUND,
    UNRELIABLE_CONFIDENCE,
    ExtractionRun,
    PolicyClause,
    PolicyFact,
)
from app.policies.errors import PolicyNotFoundError
from app.policies.models import STATUS_READY, UploadedPolicy
from app.users.models import User


@dataclass(frozen=True)
class Citation:
    page: int
    clause_title: str | None
    quote: str
    #: The full clause, so "view source wording" shows the wording in context
    #: rather than the one sentence a pattern happened to match.
    clause_text: str | None


@dataclass(frozen=True)
class DecodedFact:
    fact_key: str
    title: str
    technical_term: str
    #: None when the value is unknown or disputed.
    statement: str | None
    example: str
    conditions: str
    confidence_state: str
    reliable: bool
    citation: Citation | None
    #: Populated for a CONFLICTING fact: what disagrees, and where.
    alternatives: list[Citation]


@dataclass(frozen=True)
class DecodedSection:
    key: str
    label: str
    facts: list[DecodedFact]


@dataclass(frozen=True)
class DecodedPolicy:
    policy: UploadedPolicy
    sections: list[DecodedSection]
    #: Clauses we filed under a section but had no fact for, so the reader can
    #: still read what the document says about it.
    unmatched_clause_count: int
    extraction_run: ExtractionRun | None

    @property
    def unknown_count(self) -> int:
        return sum(
            1
            for section in self.sections
            for fact in section.facts
            if fact.confidence_state == CONFIDENCE_NOT_FOUND
        )

    @property
    def conflicting_count(self) -> int:
        return sum(
            1
            for section in self.sections
            for fact in section.facts
            if fact.confidence_state == CONFIDENCE_CONFLICTING
        )


class PolicyNotReadyError(PolicyNotFoundError):
    """The policy exists but has not finished processing."""

    code = "POLICY_NOT_READY"
    message = "That policy is still being read."


async def decode(db: AsyncSession, *, user: User, policy_id: str) -> DecodedPolicy:
    """Build the report for one policy, scoped to its owner."""
    policy = (
        await db.execute(
            select(UploadedPolicy).where(
                UploadedPolicy.id == policy_id,
                UploadedPolicy.user_id == user.id,
                UploadedPolicy.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if policy is None:
        raise PolicyNotFoundError
    if policy.status != STATUS_READY:
        raise PolicyNotReadyError

    run = (
        await db.execute(
            select(ExtractionRun)
            .where(ExtractionRun.policy_id == policy.id)
            .order_by(ExtractionRun.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    facts = list(
        (
            await db.execute(
                select(PolicyFact).where(
                    PolicyFact.policy_id == policy.id,
                    PolicyFact.extraction_run_id == (run.id if run else ""),
                )
            )
        )
        .scalars()
        .all()
    )
    clauses = {
        clause.id: clause
        for clause in (
            await db.execute(select(PolicyClause).where(PolicyClause.policy_id == policy.id))
        )
        .scalars()
        .all()
    }

    decoded: dict[str, list[DecodedFact]] = {key: [] for key, _ in SECTION_ORDER}
    for fact in facts:
        content = CONTENT.get(fact.fact_key)
        if content is None:
            # A fact the decoder has no authored explanation for is not shown.
            # Rendering a raw key and a number would be worse than omitting it.
            continue
        decoded[content.section].append(_to_decoded(fact, clauses))

    used_clause_ids = {fact.clause_id for fact in facts if fact.clause_id}

    return DecodedPolicy(
        policy=policy,
        sections=[
            DecodedSection(key=key, label=label, facts=decoded[key])
            for key, label in SECTION_ORDER
            if decoded[key]
        ],
        unmatched_clause_count=len(set(clauses) - used_clause_ids),
        extraction_run=run,
    )


def _to_decoded(fact: PolicyFact, clauses: dict[str, PolicyClause]) -> DecodedFact:
    content = CONTENT[fact.fact_key]
    clause = clauses.get(fact.clause_id) if fact.clause_id else None

    citation = None
    if fact.source_page is not None and fact.source_quote:
        citation = Citation(
            page=fact.source_page,
            clause_title=clause.title if clause else None,
            quote=fact.source_quote,
            clause_text=clause.source_text if clause else None,
        )

    return DecodedFact(
        fact_key=fact.fact_key,
        title=content.title,
        technical_term=content.technical_term,
        # A disputed value has no statement: saying one of two numbers as
        # though it were the answer is exactly what CONFLICTING prevents.
        statement=describe_value(fact.fact_key, fact.value_json),
        example=content.example,
        conditions=content.conditions,
        confidence_state=fact.confidence_state,
        reliable=fact.confidence_state not in UNRELIABLE_CONFIDENCE,
        citation=citation,
        alternatives=[
            Citation(
                page=int(alternative.get("page", 0)),
                clause_title=None,
                quote=str(alternative.get("quote", "")),
                clause_text=None,
            )
            for alternative in fact.alternatives_json
        ],
    )
