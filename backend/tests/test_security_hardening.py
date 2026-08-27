"""Phase 16: the protections that only exist to bound a mistake.

None of these tests describe a feature a user would name. They describe the
things that must stay true while the beta is reachable from the internet:
responses that a browser cannot be tricked by, endpoints that cannot be
hammered, and documentation that is not published alongside private data.
"""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.rate_limit import MAGIC_LINK_PER_EMAIL, Limit, RateLimiter, client_ip
from app.main import create_app


def _deployed(settings: Settings, app_env: str) -> Settings:
    """The local test settings, reconfigured as a real deployment would be."""
    return settings.model_copy(
        update={
            "app_env": app_env,
            "database_url": "postgresql+asyncpg://u:p@db.internal:5432/insurance",
            "cors_allowed_origins": "https://app.example.com",
            "frontend_base_url": "https://app.example.com",
        }
    )


async def test_every_response_carries_the_security_headers(client: AsyncClient) -> None:
    response = await client.get("/health/live")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


async def test_error_responses_carry_them_too(api: AsyncClient) -> None:
    """A 401 is exactly the response an attacker sees most often."""
    response = await api.get("/api/v1/me")

    assert response.status_code == 401
    assert response.headers["x-content-type-options"] == "nosniff"


async def test_hsts_is_absent_locally_and_present_when_deployed(
    settings: Settings, client: AsyncClient
) -> None:
    """Sending HSTS for localhost would poison the developer's browser."""
    local = await client.get("/health/live")
    assert "strict-transport-security" not in local.headers

    deployed = create_app(_deployed(settings, "staging"))
    transport_client = AsyncClient(
        transport=ASGITransport(app=deployed), base_url="http://testserver"
    )
    async with transport_client as http:
        response = await http.get("/health/live")
    assert response.headers["strict-transport-security"].startswith("max-age=")


async def test_api_documentation_is_not_served_outside_local(settings: Settings) -> None:
    """OpenAPI names every private endpoint and its shape. Local only."""
    deployed = create_app(_deployed(settings, "production-beta"))
    transport_client = AsyncClient(
        transport=ASGITransport(app=deployed), base_url="http://testserver"
    )
    async with transport_client as http:
        assert (await http.get("/docs")).status_code == 404
        assert (await http.get("/openapi.json")).status_code == 404


def test_the_window_slides_rather_than_resetting_on_a_boundary() -> None:
    """A fixed bucket would let a caller send twice the budget across a tick."""
    isolated = RateLimiter()
    limit = Limit(times=2, seconds=10)

    assert isolated.check("k", limit, now=0.0)
    assert isolated.check("k", limit, now=1.0)
    assert not isolated.check("k", limit, now=2.0)

    # The first hit ages out at t=10, and only then is one slot free again.
    assert not isolated.check("k", limit, now=9.9)
    assert isolated.check("k", limit, now=10.1)


def test_limits_are_kept_per_key() -> None:
    isolated = RateLimiter()
    limit = Limit(times=1, seconds=10)

    assert isolated.check("a", limit, now=0.0)
    assert not isolated.check("a", limit, now=0.0)
    assert isolated.check("b", limit, now=0.0)


def test_client_ip_prefers_the_forwarded_address_and_bounds_it() -> None:
    class _Req:
        headers = {"x-forwarded-for": "203.0.113.7, 10.0.0.1"}
        client = None

    assert client_ip(_Req()) == "203.0.113.7"

    class _Long:
        headers = {"x-forwarded-for": "x" * 500}
        client = None

    assert len(client_ip(_Long())) == 64

    class _Socket:
        headers: dict[str, str] = {}

        class client:  # noqa: N801 - mimicking Starlette's attribute shape
            host = "198.51.100.4"

    assert client_ip(_Socket()) == "198.51.100.4"


async def test_magic_link_requests_are_limited_per_address(api: AsyncClient) -> None:
    """One address cannot be used to send unlimited mail to a beta user.

    The address is not on the allowlist, so nothing is ever sent; the point is
    that the limit is reached before the allowlist is even consulted.
    """
    payload = {"email": "flood@example.com"}
    for _ in range(MAGIC_LINK_PER_EMAIL.times):
        assert (await api.post("/api/v1/auth/request-magic-link", json=payload)).status_code == 200

    blocked = await api.post("/api/v1/auth/request-magic-link", json=payload)
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"


async def test_the_limit_is_per_address_not_global(api: AsyncClient) -> None:
    """Exhausting one address must not lock every other beta user out."""
    for _ in range(MAGIC_LINK_PER_EMAIL.times):
        await api.post("/api/v1/auth/request-magic-link", json={"email": "one@example.com"})

    other = await api.post("/api/v1/auth/request-magic-link", json={"email": "two@example.com"})
    assert other.status_code == 200


async def test_case_differences_do_not_buy_a_fresh_budget(api: AsyncClient) -> None:
    """`A@x.com` and `a@x.com` are one inbox, so they are one bucket."""
    for index in range(MAGIC_LINK_PER_EMAIL.times):
        address = "MiXeD@example.com" if index % 2 else "mixed@example.com"
        assert (
            await api.post("/api/v1/auth/request-magic-link", json={"email": address})
        ).status_code == 200

    blocked = await api.post("/api/v1/auth/request-magic-link", json={"email": "MIXED@EXAMPLE.COM"})
    assert blocked.status_code == 429
