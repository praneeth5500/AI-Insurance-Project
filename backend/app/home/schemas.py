"""Home summary payload.

The API reports *state* — what exists, what is available. All user-facing copy
lives in the frontend design layer, so wording changes do not require an API
change.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.core.schema import ApiModel

#: AVAILABLE  — the flow is built and works end to end.
#: COMING_SOON — deliberately advertised but not yet usable.
Availability = Literal["AVAILABLE", "COMING_SOON"]

#: REAL — everything shown belongs to this user.
#: DEMO — clearly-labelled synthetic modules for layout review only.
DataMode = Literal["REAL", "DEMO"]


class FeatureAvailability(ApiModel):
    """Which destinations actually work, so the UI never offers a dead action."""

    health_recommendation: Availability
    motor_recommendation: Availability
    policy_decoder: Availability


class ContinueAction(ApiModel):
    """The single most useful next step, or nothing.

    docs/02_UX_UI_SPEC.md section 6: "Only show an action if relevant."
    """

    kind: Literal["RESUME_QUESTIONNAIRE", "VIEW_RECOMMENDATION", "VIEW_POLICY"]
    label: str
    href: str
    context: str | None = None
    updated_at: datetime | None = None


class RecommendationSummary(ApiModel):
    id: str
    domain: Literal["HEALTH", "MOTOR"]
    match_count: int
    created_at: datetime
    href: str


class PolicySummary(ApiModel):
    id: str
    display_name: str
    status: str
    created_at: datetime
    href: str


class ClaimsChecklistSummary(ApiModel):
    id: str
    policy_display_name: str
    completed_items: int
    total_items: int
    href: str


class HouseholdSummary(ApiModel):
    member_count: int
    href: str


class VehicleSummary(ApiModel):
    count: int
    href: str


class HomeSummary(ApiModel):
    """Everything the home screen needs, in one request.

    A module is `None` when it has nothing to show. The UI renders nothing for
    those: "Do not render empty irrelevant modules"
    (docs/02_UX_UI_SPEC.md section 6).
    """

    is_new_user: bool
    data_mode: DataMode
    features: FeatureAvailability
    continue_action: ContinueAction | None = None
    recommendations: list[RecommendationSummary] = []
    policies: list[PolicySummary] = []
    claims_checklist: ClaimsChecklistSummary | None = None
    household: HouseholdSummary | None = None
    vehicles: VehicleSummary | None = None
