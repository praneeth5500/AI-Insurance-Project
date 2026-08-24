"""The signed-in home summary (docs/11_BUILD_PLAN.md Phase 3)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.allowlist import grant_access
from app.core.config import AppEnv, Settings
from app.home.service import build_home_summary, feature_availability
from app.users.models import User

INVITED = "invited@example.com"


async def _user(db: AsyncSession) -> User:
    from sqlalchemy import select

    from app.auth.models import AuthIdentity

    await grant_access(db, INVITED)
    await db.commit()
    identity = (
        await db.execute(select(AuthIdentity).where(AuthIdentity.email == INVITED))
    ).scalar_one()
    user = User(auth_identity_id=identity.id)
    db.add(user)
    await db.commit()
    return user


# ------------------------------------------------------------ authorization --


async def test_home_requires_a_session(api: AsyncClient) -> None:
    response = await api.get("/api/v1/home")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


# --------------------------------------------------------------- new user ---


async def test_a_user_with_no_activity_gets_the_new_user_home(
    db: AsyncSession, settings: Settings
) -> None:
    summary = await build_home_summary(settings, user=await _user(db))

    assert summary.is_new_user is True
    assert summary.data_mode == "REAL"


async def test_empty_modules_are_absent_rather_than_empty_shells(
    db: AsyncSession, settings: Settings
) -> None:
    """docs/02_UX_UI_SPEC.md section 6: do not render empty irrelevant modules."""
    summary = await build_home_summary(settings, user=await _user(db))

    assert summary.continue_action is None
    assert summary.recommendations == []
    assert summary.policies == []
    assert summary.claims_checklist is None
    assert summary.household is None
    assert summary.vehicles is None


async def test_no_activity_is_reported_that_does_not_exist(
    db: AsyncSession, settings: Settings
) -> None:
    """Recommendation runs and policies do not exist yet, and the summary says so."""
    summary = await build_home_summary(settings, user=await _user(db))

    assert summary.recommendations == []
    assert summary.policies == []


# ------------------------------------------------------------ availability --


async def test_unbuilt_destinations_are_reported_as_coming_soon(
    settings: Settings,
) -> None:
    """docs/12_BETA_CHECKLIST.md requires no dead buttons."""
    features = feature_availability(settings)

    assert features.health_recommendation == "COMING_SOON"
    assert features.motor_recommendation == "COMING_SOON"
    assert features.policy_decoder == "COMING_SOON"


async def test_a_feature_flag_marks_its_destination_available() -> None:
    features = feature_availability(Settings(app_env="local", feature_health_recommendation=True))

    assert features.health_recommendation == "AVAILABLE"
    # Turning one on must not turn the others on.
    assert features.motor_recommendation == "COMING_SOON"
    assert features.policy_decoder == "COMING_SOON"


async def test_motor_stays_off_by_default() -> None:
    """docs/13_DECISIONS_AND_OPEN_ITEMS.md item 8: not until health and motor
    data are ready."""
    assert Settings(app_env="local").feature_motor_recommendation is False


# -------------------------------------------------------------- demo mode ---


async def test_demo_mode_is_labelled_as_demo(db: AsyncSession) -> None:
    settings = Settings(app_env="local", home_demo_data=True)

    summary = await build_home_summary(settings, user=await _user(db))

    assert summary.data_mode == "DEMO"
    assert summary.is_new_user is False


async def test_demo_mode_populates_every_module_for_layout_review(
    db: AsyncSession,
) -> None:
    settings = Settings(app_env="local", home_demo_data=True)

    summary = await build_home_summary(settings, user=await _user(db))

    assert summary.continue_action is not None
    assert len(summary.recommendations) == 1
    assert len(summary.policies) == 1
    assert summary.claims_checklist is not None
    assert summary.household is not None
    assert summary.vehicles is not None


async def test_demo_data_contains_no_insurance_facts(db: AsyncSession) -> None:
    """CLAUDE.md: never invent insurance facts, premiums or claim outcomes."""
    settings = Settings(app_env="local", home_demo_data=True)

    summary = await build_home_summary(settings, user=await _user(db))
    serialized = summary.model_dump_json().lower()

    for forbidden in ("premium", "₹", "insurer", "sum insured", "claim approved"):
        assert forbidden not in serialized

    # Every demo identifier is obviously a demo identifier.
    assert summary.recommendations[0].id.startswith("rr_demo")
    assert summary.policies[0].id.startswith("pol_demo")


@pytest.mark.parametrize("app_env", ["staging", "production-beta"])
def test_demo_data_is_refused_outside_local_and_preview(app_env: AppEnv) -> None:
    """Synthetic modules must never reach a beta user as though they were real."""
    settings = Settings(
        app_env=app_env,
        database_url="postgresql+asyncpg://x:y@host/db",
        home_demo_data=True,
    )

    with pytest.raises(RuntimeError, match="HOME_DEMO_DATA cannot be enabled"):
        settings.validate_for_environment()


def test_demo_data_is_allowed_in_preview() -> None:
    settings = Settings(
        app_env="preview",
        database_url="postgresql+asyncpg://x:y@host/db",
        home_demo_data=True,
    )

    settings.validate_for_environment()
