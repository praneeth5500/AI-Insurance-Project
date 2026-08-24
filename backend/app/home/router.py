"""Home endpoint.

Not in docs/08_API_CONTRACTS.md, which starts at the questionnaire. Recorded
in docs/SPEC_ISSUES.md so the contracts document can be updated deliberately.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import AppSettings, CurrentUser
from app.home.schemas import HomeSummary
from app.home.service import build_home_summary

router = APIRouter(tags=["home"])


@router.get("/home", response_model=HomeSummary, summary="What this user can do next")
async def home(user: CurrentUser, settings: AppSettings) -> HomeSummary:
    return await build_home_summary(settings, user=user)
