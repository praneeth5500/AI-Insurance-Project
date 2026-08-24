"""Health endpoint behaviour (Phase 0 definition of done)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.middleware import REQUEST_ID_HEADER


async def test_live_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_live_echoes_a_request_id(client: AsyncClient) -> None:
    response = await client.get("/health/live")

    request_id = response.headers[REQUEST_ID_HEADER]
    assert request_id.startswith("req_")


async def test_request_ids_are_unique_per_request(client: AsyncClient) -> None:
    first = await client.get("/health/live")
    second = await client.get("/health/live")

    assert first.headers[REQUEST_ID_HEADER] != second.headers[REQUEST_ID_HEADER]


async def test_ready_reports_ok_when_database_answers(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def database_available() -> bool:
        return True

    monkeypatch.setattr("app.health.router.check_database", database_available)

    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "dependencies": {"database": "ok"}}


async def test_ready_returns_503_in_the_standard_error_shape_when_database_is_down(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def database_unavailable() -> bool:
        return False

    monkeypatch.setattr("app.health.router.check_database", database_unavailable)

    response = await client.get("/health/ready")

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "SERVICE_UNAVAILABLE"
    assert error["retryable"] is True
    assert error["requestId"] is not None


async def test_ready_is_unavailable_when_the_engine_was_never_initialised(
    client: AsyncClient,
) -> None:
    # No lifespan ran, so get_engine() raises — readiness must degrade, not 500.
    response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
