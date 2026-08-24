"""The ``/api/v1`` router.

Empty in Phase 0. Domain routers (auth, questionnaires, recommendations,
policies) are mounted here by the phases that build them.
"""

from __future__ import annotations

from fastapi import APIRouter

api_v1_router = APIRouter(prefix="/api/v1")
