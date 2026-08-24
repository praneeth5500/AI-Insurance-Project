"""Every error leaves the API in the single shape from
docs/08_API_CONTRACTS.md section 12."""

from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.errors import AppError, ServiceUnavailableError

EXPECTED_KEYS = {"code", "message", "retryable", "requestId"}


async def test_unknown_route_uses_the_error_envelope(client: AsyncClient) -> None:
    response = await client.get("/does-not-exist")

    assert response.status_code == 404
    error = response.json()["error"]
    assert set(error) == EXPECTED_KEYS
    assert error["code"] == "NOT_FOUND"
    assert error["retryable"] is False


async def test_app_error_is_rendered_with_its_code_and_retryability(app: FastAPI) -> None:
    @app.get("/boom-known")
    async def boom_known() -> None:
        raise ServiceUnavailableError()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/boom-known")

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "SERVICE_UNAVAILABLE"
    assert error["retryable"] is True


async def test_unexpected_exception_does_not_leak_internal_detail(app: FastAPI) -> None:
    secret = "connection to postgres://user:password@host failed"

    @app.get("/boom-unknown")
    async def boom_unknown() -> None:
        raise RuntimeError(secret)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/boom-unknown")

    assert response.status_code == 500
    body = response.text
    assert secret not in body
    assert "Traceback" not in body
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"


async def test_validation_failure_does_not_echo_the_request_body(app: FastAPI) -> None:
    from app.core.schema import ApiModel

    class Payload(ApiModel):
        member_age: int

    @app.post("/echo")
    async def echo(payload: Payload) -> None:
        return None

    sensitive = "diagnosed-with-something-private"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/echo", json={"memberAge": sensitive})

    assert response.status_code == 422
    assert sensitive not in response.text
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_app_error_defaults_are_safe_to_show_a_user() -> None:
    error = AppError()

    assert error.code == "INTERNAL_ERROR"
    assert error.retryable is False
    assert "went wrong" in error.message
