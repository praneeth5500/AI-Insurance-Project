# Backend

FastAPI + Pydantic + SQLAlchemy (async) + PostgreSQL, built as a **modular
monolith** (`docs/04_BACKEND_ARCHITECTURE.md`).

## Phase 0 status

Foundation only: configuration, safe logging, the single error envelope,
request-id middleware, the database engine, health endpoints, and Alembic
scaffolding. **No domain modules and no database tables exist yet.**

## Commands

```bash
uv sync                                   # install
uv run uvicorn app.main:app --reload      # or: make dev-backend
uv run pytest
uv run ruff check . && uv run ruff format .
uv run mypy app tests
uv run alembic upgrade head               # or: make migrate
```

## Structure that Phase 0 created

```text
app/core/       config, logging, errors, middleware, API model base
app/db/         async engine/session, declarative base (no models yet)
app/health/     /health/live and /health/ready
app/api/v1/     the versioned product API router (empty)
migrations/     Alembic environment (zero migrations)
```

## Structure that later phases create

Documented rather than scaffolded empty, per `CLAUDE.md` ("avoid premature
abstractions"). Target module list from
`docs/04_BACKEND_ARCHITECTURE.md` section 1:

```text
auth/ users/ households/ profiles/        Phase 2 onwards
questionnaires/                           Phase 4
recommendations/ scoring/                 Phase 9
products/ pricing/                        Phase 8
policies/ documents/                      Phases 10-11
ai/                                       Phases 9, 11, 13
claims_readiness/                         Phase 14
integrations/                             external provider adapters
analytics/ audit/                         Phase 15
```

Each module follows `router → service → domain → repository/adapter`. Provider
SDK calls stay out of domain logic.

## Conventions

- **mypy strict.** No untyped defs, no implicit `Any`.
- **camelCase on the wire, snake_case internally.** Inherit every request and
  response model from `app.core.schema.ApiModel`.
- **One error shape.** Raise `AppError` subclasses; handlers render
  `{"error": {code, message, retryable, requestId}}`. `message` is shown to a
  user, so it must never contain user input or internal detail.
- **Logging is allow-listed.** `app.core.logging.ALLOWED_LOG_FIELDS` is the
  full set of fields that may be logged. Policy text, health answers and
  tokens are dropped by a filter rather than by reviewer vigilance.
- **Health endpoints live outside `/api/v1`** — they are operational, not
  product API.
- **Migrations are mandatory** for schema changes, but Phase 0 has none:
  `docs/05_DATA_MODEL.md` is a logical model and asks for migrations only once
  relationships are validated in implementation.
