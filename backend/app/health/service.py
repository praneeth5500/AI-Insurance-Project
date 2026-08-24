"""Readiness checks for the API's own dependencies."""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.core.logging import log_fields
from app.db.session import get_engine

logger = logging.getLogger(__name__)


async def check_database() -> bool:
    """Return True when a real round-trip to PostgreSQL succeeds."""
    try:
        engine = get_engine()
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        # The exception detail may contain the connection string; log the code only.
        logger.error(
            "dependency_unavailable",
            extra=log_fields(event="dependency_unavailable", resource_type="database"),
        )
        return False
    return True
