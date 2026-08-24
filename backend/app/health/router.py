"""Health endpoints.

These sit outside ``/api/v1`` deliberately: they are operational endpoints for
load balancers and deployment checks, not part of the versioned product API.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Response, status

from app.core.errors import error_body
from app.core.schema import ApiModel
from app.health.service import check_database

router = APIRouter(prefix="/health", tags=["health"])


class LivenessResponse(ApiModel):
    status: Literal["ok"] = "ok"


class DependencyStatus(ApiModel):
    database: Literal["ok", "unavailable"]


class ReadinessResponse(ApiModel):
    status: Literal["ready"] = "ready"
    dependencies: DependencyStatus


@router.get("/live", response_model=LivenessResponse, summary="Process is running")
async def live() -> LivenessResponse:
    """Return 200 whenever the process can serve HTTP."""
    return LivenessResponse()


@router.get("/ready", summary="Process and its dependencies are usable")
async def ready(response: Response) -> object:
    """Return 200 only when PostgreSQL answers; 503 in the standard error shape."""
    database_ok = await check_database()
    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return error_body(
            "SERVICE_UNAVAILABLE",
            "The service is temporarily unavailable. Please try again shortly.",
            retryable=True,
        )
    return ReadinessResponse(dependencies=DependencyStatus(database="ok"))
