"""Shared test fixtures.

Tests never use real user data (docs/09_AWS_DEPLOYMENT.md section 4). Auth is
security-critical, so its tests run against a real PostgreSQL database with
the real migrations applied — an in-memory substitute would not exercise the
constraints that enforce single-use tokens and unique emails.

Set TEST_DATABASE_URL to point at a throwaway database; it defaults to
`insurance_test` on the local development server.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Importing the model modules registers their tables on Base.metadata.
from app.audit import models as _audit_models  # noqa: F401
from app.auth import models as _auth_models  # noqa: F401
from app.core.config import Settings
from app.db.base import Base
from app.db.session import dispose_engine, get_session, init_engine
from app.main import create_app
from app.users import models as _user_models  # noqa: F401

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://insurance:insurance@127.0.0.1:5432/insurance_test",
)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="local",
        log_level="WARNING",
        database_url=TEST_DATABASE_URL,
        frontend_base_url="http://localhost:3000",
        magic_link_ttl_minutes=15,
        session_ttl_days=14,
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


@pytest.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    """A session-wide engine against the test database."""
    test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=None)
    async with test_engine.begin() as connection:
        # Rebuild from the models each session so a stale test database cannot
        # mask a schema change. Deployed environments always use migrations.
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """A clean database per test."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()
        yield session


@pytest.fixture
async def live_api(
    app: FastAPI, settings: Settings, db: AsyncSession
) -> AsyncIterator[AsyncClient]:
    """Client using the application's own per-request sessions.

    The `api` fixture pins every request to one shared session, which keeps
    assertions simple but also keeps objects warm in a single identity map.
    That hides bugs that only appear when each request starts with an empty
    session — lazy relationship loads, in particular. This fixture wires the
    real engine to the test database so the production path is exercised.

    `db` is depended upon only for its per-test truncation.
    """
    init_engine(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client
    await dispose_engine()


@pytest.fixture
async def api(app: FastAPI, db: AsyncSession) -> AsyncIterator[AsyncClient]:
    """HTTP client wired to the per-test database session."""

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield db

    app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client
    app.dependency_overrides.clear()
