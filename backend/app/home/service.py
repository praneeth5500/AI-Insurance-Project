"""Assembling the home summary."""

from __future__ import annotations

from app.core.config import Settings
from app.home.demo import demo_summary
from app.home.schemas import Availability, FeatureAvailability, HomeSummary
from app.users.models import User


def _availability(enabled: bool) -> Availability:
    return "AVAILABLE" if enabled else "COMING_SOON"


def feature_availability(settings: Settings) -> FeatureAvailability:
    return FeatureAvailability(
        health_recommendation=_availability(settings.feature_health_recommendation),
        motor_recommendation=_availability(settings.feature_motor_recommendation),
        policy_decoder=_availability(settings.feature_policy_decoder),
    )


async def build_home_summary(settings: Settings, *, user: User) -> HomeSummary:
    """What this user can do next.

    Recommendation runs, uploaded policies, claims checklists, households and
    vehicles are built in Phases 5 to 14. Until those tables exist, every
    module is genuinely empty, and the summary says so honestly rather than
    inventing activity. `HOME_DEMO_DATA` substitutes clearly-labelled
    synthetic modules for layout review.
    """
    features = feature_availability(settings)

    if settings.home_demo_data:
        return demo_summary(features)

    # No activity exists yet for any user, so the home renders its new-user
    # form. Each module is populated by the phase that creates its data.
    return HomeSummary(
        is_new_user=not user.has_profile,
        data_mode="REAL",
        features=features,
    )
