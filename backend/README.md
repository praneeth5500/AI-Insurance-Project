# Backend

FastAPI + Pydantic + SQLAlchemy (async) + PostgreSQL, built as a **modular
monolith** (`docs/04_BACKEND_ARCHITECTURE.md`).

## Phase 5 status

Foundation, beta authentication, the home summary, the adaptive questionnaire
engine, and a mock recommendation experience over a synthetic product
catalogue. The real matching engine is Phase 9.

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
app/core/          config, logging, errors, middleware, API model base, tokens
app/db/            async engine/session, declarative base, id/timestamp helpers
app/health/        /health/live and /health/ready
app/api/v1/        the versioned product API router
app/auth/          identities, magic links, sessions, allowlist
app/home/          the signed-in home summary
app/questionnaires/ question definitions, branching, drafts, priorities
app/products/      synthetic catalogue and provenance
app/recommendations/ prototype ordering, decision profile, runs
app/users/         the domain user profile (separate from the auth identity)
app/audit/         audit events
app/integrations/  external provider adapters (email so far)
migrations/        Alembic environment and migrations
```

## Structure that later phases create

Documented rather than scaffolded empty, per `CLAUDE.md` ("avoid premature
abstractions"). Target module list from
`docs/04_BACKEND_ARCHITECTURE.md` section 1:

```text
households/ profiles/                     later
products/ pricing/  (real data)           Phase 8
scoring/                                  Phase 9
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
- **Migrations are mandatory** for schema changes. Add the model, import it in
  `migrations/env.py`, then `make migration m="..."`.
- **Auth relationships are `lazy="raise"`.** Implicit lazy loading under async
  SQLAlchemy fails non-deterministically depending on garbage collection, so
  callers must eager load or carry the object explicitly. See
  `docs/PHASE_2_NOTES.md`.
- **Sign-in tokens are never stored or logged in the clear** — only SHA-256
  digests are persisted.
- **Auth tests need a real database.** `make db-up`, then `make test`.
