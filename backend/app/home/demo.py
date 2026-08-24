"""Synthetic home modules for layout review.

docs/11_BUILD_PLAN.md Phase 3 says "Use mock data first": the returning-user
home has to be reviewable before recommendation runs and uploaded policies
exist. This module produces that content.

Two rules govern everything here:

* it is served only when `HOME_DEMO_DATA` is on, which configuration refuses
  outside local and preview;
* the response is marked `dataMode: "DEMO"`, and the UI labels it as demo
  data, because prototype data must never look like a real record
  (docs/00_README.md, "Prototype truth rule").

Nothing here is an insurance fact. There are no insurer names, no product
names, no premiums and no claim outcomes — only counts and timestamps that
exercise the layout.
"""

from __future__ import annotations

from datetime import timedelta

from app.db.types import utcnow
from app.home.schemas import (
    ClaimsChecklistSummary,
    ContinueAction,
    FeatureAvailability,
    HomeSummary,
    HouseholdSummary,
    PolicySummary,
    RecommendationSummary,
    VehicleSummary,
)


def demo_summary(features: FeatureAvailability) -> HomeSummary:
    """A returning user with activity in every module."""
    now = utcnow()

    return HomeSummary(
        is_new_user=False,
        data_mode="DEMO",
        features=features,
        continue_action=ContinueAction(
            kind="RESUME_QUESTIONNAIRE",
            label="Continue your health cover questions",
            href="/app/recommend/health",
            context="Demo · stage 2 of 4",
            updated_at=now - timedelta(hours=3),
        ),
        recommendations=[
            RecommendationSummary(
                id="rr_demo_1",
                domain="HEALTH",
                match_count=10,
                created_at=now - timedelta(days=2),
                href="/app/recommendations/rr_demo_1",
            )
        ],
        policies=[
            PolicySummary(
                id="pol_demo_1",
                display_name="Demo policy document",
                status="READY",
                created_at=now - timedelta(days=9),
                href="/app/policies/pol_demo_1",
            )
        ],
        claims_checklist=ClaimsChecklistSummary(
            id="crs_demo_1",
            policy_display_name="Demo policy document",
            completed_items=2,
            total_items=6,
            href="/app/policies/pol_demo_1/claims-readiness",
        ),
        household=HouseholdSummary(member_count=3, href="/app/profile/household"),
        vehicles=VehicleSummary(count=1, href="/app/profile/vehicles"),
    )
