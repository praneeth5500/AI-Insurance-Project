"""Decoder payloads.

Every card carries its own uncertainty. `docs/12_BETA_CHECKLIST.md` requires a
visible not-found state and a visible conflicting state, so the schema has no
way to express a value without also expressing how much it can be trusted —
`confidenceState` is required on every fact.
"""

from __future__ import annotations

from app.core.schema import ApiModel
from app.decoder.service import Citation, DecodedFact, DecodedPolicy, DecodedSection


class CitationView(ApiModel):
    page: int
    clause_title: str | None
    #: The sentence the value came from.
    quote: str
    #: The whole clause, for "view source wording". Null when the clause was
    #: not stored — never a placeholder, and never invented.
    clause_text: str | None


class FactCardView(ApiModel):
    """docs/07_POLICY_DECODER_AI.md section 6."""

    fact_key: str
    title: str
    #: Kept, not replaced: explaining a term without hiding it is the rule.
    technical_term: str
    #: Null when the value is unknown or disputed. The UI shows its unknown
    #: state instead of a sentence built around a blank.
    statement: str | None
    #: A labelled hypothetical about policies in general, never this policy.
    example: str
    conditions: str
    confidence_state: str
    reliable: bool
    citation: CitationView | None
    #: Populated for a conflicting fact: every reading, and where each came
    #: from, so the reader can see what disagrees.
    alternatives: list[CitationView]

    @classmethod
    def of(cls, fact: DecodedFact) -> FactCardView:
        return cls(
            fact_key=fact.fact_key,
            title=fact.title,
            technical_term=fact.technical_term,
            statement=fact.statement,
            example=fact.example,
            conditions=fact.conditions,
            confidence_state=fact.confidence_state,
            reliable=fact.reliable,
            citation=_citation(fact.citation),
            alternatives=[view for view in (_citation(item) for item in fact.alternatives) if view],
        )


def _citation(citation: Citation | None) -> CitationView | None:
    if citation is None:
        return None
    return CitationView(
        page=citation.page,
        clause_title=citation.clause_title,
        quote=citation.quote,
        clause_text=citation.clause_text,
    )


class SectionView(ApiModel):
    key: str
    label: str
    facts: list[FactCardView]

    @classmethod
    def of(cls, section: DecodedSection) -> SectionView:
        return cls(
            key=section.key,
            label=section.label,
            facts=[FactCardView.of(fact) for fact in section.facts],
        )


class DecoderView(ApiModel):
    policy_id: str
    display_name: str
    sections: list[SectionView]
    #: How much we could not determine. Surfaced rather than buried: a report
    #: that looks complete when it is not is the failure this whole phase is
    #: written to avoid.
    unknown_count: int
    conflicting_count: int
    #: Clauses in the document we did not extract a fact from. The reader is
    #: told this so the report is never mistaken for the whole policy.
    unread_clause_count: int
    #: Which pipeline produced this, so a report can be explained later.
    schema_version: str | None
    #: Null while extraction is deterministic. Present so a reader can always
    #: be told whether a model was involved in what they are reading.
    ai_provider: str | None

    @classmethod
    def of(cls, decoded: DecodedPolicy) -> DecoderView:
        return cls(
            policy_id=decoded.policy.id,
            display_name=decoded.policy.display_name,
            sections=[SectionView.of(section) for section in decoded.sections],
            unknown_count=decoded.unknown_count,
            conflicting_count=decoded.conflicting_count,
            unread_clause_count=decoded.unmatched_clause_count,
            schema_version=decoded.extraction_run.schema_version
            if decoded.extraction_run
            else None,
            ai_provider=decoded.extraction_run.ai_provider if decoded.extraction_run else None,
        )
