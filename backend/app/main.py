"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, log_fields
from app.core.middleware import RequestContextMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.db import registry as _model_registry  # noqa: F401 - completes the mapper registry
from app.db.session import dispose_engine, init_engine
from app.health.router import router as health_router

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. Tests call this directly with overridden settings."""
    settings = settings or get_settings()
    settings.validate_for_environment()
    configure_logging(settings.log_level, is_local=settings.is_local)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        init_engine(settings)
        logger.info("application_started", extra=log_fields(event="application_started"))
        try:
            yield
        finally:
            await dispose_engine()
            logger.info("application_stopped", extra=log_fields(event="application_stopped"))

    app = FastAPI(
        title="AI Insurance Decision Platform API",
        version="0.1.0",
        lifespan=lifespan,
        # Interactive docs are a local development aid only.
        docs_url="/docs" if settings.is_local else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.is_local else None,
    )

    # Added before the request-context middleware so it runs outermost and
    # its headers are present even on an error response.
    app.add_middleware(SecurityHeadersMiddleware, is_local=settings.is_local)
    app.add_middleware(
        RequestContextMiddleware,
        slow_request_threshold_ms=settings.slow_request_threshold_ms,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_v1_router)

    return app


app = create_app()
