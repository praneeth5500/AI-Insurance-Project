"""Shared test fixtures.

Tests never touch a real database or real user data (docs/09_AWS_DEPLOYMENT.md
section 4). Dependency behaviour is substituted per test.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="local",
        log_level="WARNING",
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
    )


@pytest.fixture
def app(settings: Settings) -> Iterator[FastAPI]:
    yield create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """HTTP client that does not run lifespan, so no engine is created."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client
