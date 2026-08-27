"""The ``/api/v1`` router.

Domain routers are mounted here by the phases that build them.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.router import router as auth_router
from app.claims.router import router as claims_router
from app.decoder.router import router as decoder_router
from app.home.router import router as home_router
from app.policies.router import router as policy_router
from app.products.router import router as product_router
from app.qa.router import router as qa_router
from app.questionnaires.router import router as questionnaire_router
from app.recommendations.router import comparison_router
from app.recommendations.router import router as recommendation_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(home_router)
api_v1_router.include_router(questionnaire_router)
api_v1_router.include_router(recommendation_router)
api_v1_router.include_router(comparison_router)
api_v1_router.include_router(product_router)
api_v1_router.include_router(policy_router)
api_v1_router.include_router(decoder_router)
api_v1_router.include_router(qa_router)
api_v1_router.include_router(claims_router)
