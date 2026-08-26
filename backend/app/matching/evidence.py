"""What a fit judgement was based on.

docs/06_RECOMMENDATION_ENGINE.md section 7 puts `explanationEvidence` on every
evaluator result, and docs/05_DATA_MODEL.md persists it as `evidence_json` on
each fit component. The point is accountability: months after a run, it should
be possible to say exactly which product fact and which of the reader's own
answers produced "Trade-off", and where that fact came from.

It is also what makes the AI explanation safe when it arrives. An LLM asked to
phrase an explanation gets these objects, not the product; it cannot introduce
a fact that is not here, and anything it says can be checked against them.
CLAUDE.md: the model never generates the ranking, and never silently
overwrites structured policy facts.
"""

from __future__ import annotations

from typing import Any, Literal

from app.core.schema import ApiModel

#: PRODUCT_FACT — a recorded fact about the policy.
#: USER_ANSWER  — something the reader told us.
#: RULE         — the threshold that turned those into a label.
#: DATA_GAP     — a fact we do not have. Never treated as a neutral value.
EvidenceKind = Literal["PRODUCT_FACT", "USER_ANSWER", "RULE", "DATA_GAP"]


class Evidence(ApiModel):
    """One traceable input to a fit judgement."""

    kind: EvidenceKind
    #: The fact key, question data field, or rule name.
    key: str
    #: The value used. Kept as a primitive so the record stays readable.
    value: str | int | float | bool | None = None
    #: Plain-language statement of what this contributed.
    detail: str
    #: Provenance, for PRODUCT_FACT evidence.
    source_type: str | None = None
    source_reference: str | None = None

    def as_json(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)


def product_fact(
    key: str,
    value: str | int | float | bool | None,
    detail: str,
    *,
    source_type: str | None = None,
    source_reference: str | None = None,
) -> Evidence:
    return Evidence(
        kind="PRODUCT_FACT",
        key=key,
        value=value,
        detail=detail,
        source_type=source_type,
        source_reference=source_reference,
    )


def user_answer(key: str, value: str | int | float | bool | None, detail: str) -> Evidence:
    return Evidence(kind="USER_ANSWER", key=key, value=value, detail=detail)


def rule(key: str, detail: str) -> Evidence:
    return Evidence(kind="RULE", key=key, detail=detail)


def data_gap(key: str, detail: str) -> Evidence:
    """A fact we do not have.

    Recorded explicitly so a missing fact leaves a trace instead of quietly
    becoming an average score.
    """
    return Evidence(kind="DATA_GAP", key=key, detail=detail)
