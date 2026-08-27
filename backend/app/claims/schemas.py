"""Claims checklist payloads.

The response groups items by origin rather than returning one flat list.
`docs/07_POLICY_DECODER_AI.md` section 10 says not to blend the three kinds,
and a flat list with a field on each item invites exactly that — one careless
`.map()` in a client and a general suggestion is rendered as a policy
requirement.
"""

from __future__ import annotations

from app.claims.models import ORIGIN_EXPLANATIONS, ORIGIN_LABELS, ORIGINS
from app.claims.service import Checklist, ChecklistItemWithSource
from app.core.schema import ApiModel


class ChecklistSourceView(ApiModel):
    page: int
    clause_title: str | None
    clause_text: str


class ChecklistItemView(ApiModel):
    id: str
    label: str
    description: str
    completed: bool
    user_note: str | None
    #: Present only on policy-specific items, and always present on them.
    source: ChecklistSourceView | None

    @classmethod
    def of(cls, entry: ChecklistItemWithSource) -> ChecklistItemView:
        item = entry.item
        return cls(
            id=item.id,
            label=item.label,
            description=item.description,
            completed=item.completed,
            user_note=item.user_note,
            source=(
                ChecklistSourceView(
                    page=entry.clause.source_page,
                    clause_title=entry.clause.title,
                    clause_text=entry.clause.source_text,
                )
                if entry.clause is not None
                else None
            ),
        )


class ChecklistGroupView(ApiModel):
    origin: str
    label: str
    #: What this group is and, for the general one, what it is *not*.
    explanation: str
    items: list[ChecklistItemView]


class ChecklistView(ApiModel):
    policy_id: str
    display_name: str
    groups: list[ChecklistGroupView]
    completed_count: int
    total_count: int
    #: Stated on the response, not left to the UI to remember.
    #: docs/01_PRODUCT_SPEC.md section 3.6.
    disclaimer: str

    @classmethod
    def of(cls, checklist: Checklist) -> ChecklistView:
        by_origin: dict[str, list[ChecklistItemView]] = {origin: [] for origin in ORIGINS}
        for entry in checklist.items:
            by_origin[entry.item.origin].append(ChecklistItemView.of(entry))

        return cls(
            policy_id=checklist.policy.id,
            display_name=checklist.policy.display_name,
            groups=[
                ChecklistGroupView(
                    origin=origin,
                    label=ORIGIN_LABELS[origin],
                    explanation=ORIGIN_EXPLANATIONS[origin],
                    items=by_origin[origin],
                )
                for origin in ORIGINS
                if by_origin[origin]
            ],
            completed_count=checklist.completed_count,
            total_count=len(checklist.items),
            disclaimer=(
                "Working through this doesn't guarantee a claim will be paid, and nothing "
                "here predicts what your insurer will decide. It is a way to have your "
                "documents and questions ready."
            ),
        )


class UpdateItemRequest(ApiModel):
    completed: bool | None = None
    note: str | None = None
