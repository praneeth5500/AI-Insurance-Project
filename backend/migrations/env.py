"""Alembic environment.

No domain migrations exist yet — docs/05_DATA_MODEL.md is a logical model and
migrations are generated once relationships are validated in implementation.
This file exists so that ``make migrate`` and autogeneration work the moment
the first model lands.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model modules are imported for their side effect of registering tables on
# Base.metadata, which is what autogenerate compares against.
from app.audit import models as audit_models  # noqa: E402,F401
from app.auth import models as auth_models  # noqa: E402,F401
from app.extraction import models as extraction_models  # noqa: E402,F401
from app.jobs import models as job_models  # noqa: E402,F401
from app.policies import models as policy_models  # noqa: E402,F401
from app.pricing import models as pricing_models  # noqa: E402,F401
from app.products import models as product_models  # noqa: E402,F401
from app.questionnaires import models as questionnaire_models  # noqa: E402,F401
from app.recommendations import models as recommendation_models  # noqa: E402,F401
from app.users import models as user_models  # noqa: E402,F401

target_metadata = Base.metadata

config.set_main_option("sqlalchemy.url", get_settings().database_url)


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
