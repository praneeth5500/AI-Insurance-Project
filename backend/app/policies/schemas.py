"""Policy upload payloads (docs/08_API_CONTRACTS.md section 7).

Nothing here carries document content. A response describes a policy — its
name, its stage, its files' sizes and types — and the bytes themselves are
only ever streamed from the authenticated download route.
"""

from __future__ import annotations

from datetime import datetime

from app.core.schema import ApiModel
from app.policies.models import (
    PROCESSING_STAGES,
    STAGE_LABELS,
    STATUS_FAILED,
    STATUS_READY,
    PolicyDocument,
    UploadedPolicy,
)
from app.policies.service import PolicyWithDocuments
from app.policies.validation import REJECTION_MESSAGES


class DocumentView(ApiModel):
    id: str
    filename: str
    mime_type: str
    size_bytes: int
    page_count: int | None
    created_at: datetime

    @classmethod
    def of(cls, document: PolicyDocument) -> DocumentView:
        return cls(
            id=document.id,
            filename=document.filename,
            mime_type=document.mime_type,
            size_bytes=document.size_bytes,
            page_count=document.page_count,
            created_at=document.created_at,
        )


class StageView(ApiModel):
    """One step of processing.

    docs/02_UX_UI_SPEC.md section 14: no fake percentages, use stages. So the
    UI is given the stage list and which one is current, and cannot invent a
    progress bar from it.
    """

    key: str
    label: str
    state: str  # DONE | CURRENT | PENDING


class PolicyView(ApiModel):
    id: str
    display_name: str
    domain: str | None
    status: str
    status_label: str
    stages: list[StageView]
    is_ready: bool
    is_failed: bool
    #: Present only on failure, in language the reader can act on.
    failure_message: str | None
    documents: list[DocumentView]
    created_at: datetime
    ready_at: datetime | None

    @classmethod
    def of(cls, result: PolicyWithDocuments) -> PolicyView:
        policy = result.policy
        return cls(
            id=policy.id,
            display_name=policy.display_name,
            domain=policy.domain,
            status=policy.status,
            status_label=STAGE_LABELS.get(policy.status, policy.status),
            stages=_stages_for(policy),
            is_ready=policy.status == STATUS_READY,
            is_failed=policy.status == STATUS_FAILED,
            failure_message=_failure_message(policy),
            documents=[DocumentView.of(document) for document in result.documents],
            created_at=policy.created_at,
            ready_at=policy.ready_at,
        )


class PolicySummaryView(ApiModel):
    """A policy in a list, without its documents."""

    id: str
    display_name: str
    status: str
    status_label: str
    is_ready: bool
    is_failed: bool
    created_at: datetime

    @classmethod
    def of(cls, policy: UploadedPolicy) -> PolicySummaryView:
        return cls(
            id=policy.id,
            display_name=policy.display_name,
            status=policy.status,
            status_label=STAGE_LABELS.get(policy.status, policy.status),
            is_ready=policy.status == STATUS_READY,
            is_failed=policy.status == STATUS_FAILED,
            created_at=policy.created_at,
        )


def _stages_for(policy: UploadedPolicy) -> list[StageView]:
    """The stage list, with the current one marked.

    A failed policy keeps the stages it completed and stops there. Showing
    every stage as pending would hide how far it got; showing them all as done
    would be a lie.
    """
    if policy.status == STATUS_FAILED:
        # We do not know which stage failed from the status alone, so nothing
        # after RECEIVED is claimed.
        return [
            StageView(
                key=stage,
                label=STAGE_LABELS[stage],
                state="DONE" if index == 0 else "PENDING",
            )
            for index, stage in enumerate(PROCESSING_STAGES)
        ]

    try:
        current = PROCESSING_STAGES.index(policy.status)
    except ValueError:
        current = 0

    views: list[StageView] = []
    for index, stage in enumerate(PROCESSING_STAGES):
        if index < current:
            state = "DONE"
        elif index == current:
            state = "DONE" if policy.status == STATUS_READY else "CURRENT"
        else:
            state = "PENDING"
        views.append(StageView(key=stage, label=STAGE_LABELS[stage], state=state))
    return views


def _failure_message(policy: UploadedPolicy) -> str | None:
    if policy.status != STATUS_FAILED:
        return None
    if policy.failure_reason and policy.failure_reason in REJECTION_MESSAGES:
        return REJECTION_MESSAGES[policy.failure_reason]
    return (
        "We couldn't finish reading that document. Nothing is wrong with your policy — "
        "this is a limit of our reader. You can try uploading it again, or delete it."
    )


class PolicyListView(ApiModel):
    policies: list[PolicySummaryView]


class DeleteResponse(ApiModel):
    id: str
    deleted: bool
