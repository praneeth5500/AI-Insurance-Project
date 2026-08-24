# Phase 0 — Repository Foundation

Implementation notes for `docs/11_BUILD_PLAN.md` Phase 0.

## What Phase 0 delivers

A repository where the frontend runs, the backend runs, the database connects,
the health endpoints work, and one command runs every check — plus the
cross-cutting rules that later phases inherit.

## Definition of done

| Requirement | Status | Evidence |
|---|---|---|
| frontend runs | ✅ | `pnpm build` succeeds; `pnpm start` serves the status page |
| backend runs | ✅ | `uvicorn app.main:app` boots and serves requests |
| DB connects | ✅ | `/health/ready` performs a real `SELECT 1` against PostgreSQL 16 |
| health endpoint works | ✅ | `/health/live` 200; `/health/ready` 200 with DB up, 503 with DB down |
| CI/test command exists | ✅ | `make check`, mirrored by `.github/workflows/ci.yml` |

## Decisions taken

### Tooling

pnpm · Next.js 15 (App Router) · React 19 · TypeScript strict · Tailwind CSS 4 ·
uv · ruff · mypy strict · pytest · vitest. No state-management library, no
component library, no ORM beyond SQLAlchemy — none is needed yet.

### camelCase on the wire, snake_case internally

`docs/08_API_CONTRACTS.md` uses camelCase (`runId`, `questionnaireSessionId`);
Python is snake_case. `app.core.schema.ApiModel` applies the alias generator in
one place. Retrofitting this later would touch every schema, so it is set now.

### One error envelope, installed at the app level

`docs/08_API_CONTRACTS.md` section 12 defines a single error shape. Handlers
for `AppError`, validation errors, HTTP errors and unhandled exceptions are
registered on the application, so no route can return a non-conforming error
and no stack trace can reach a client. Validation detail is deliberately
discarded — FastAPI's default echoes the request body, which will later carry
sensitive questionnaire answers.

### Logging is allow-listed, not review-listed

`docs/09_AWS_DEPLOYMENT.md` section 9 forbids logging policy text, health
answers, raw documents and magic-link tokens. Rather than relying on reviewers
to catch violations, `ALLOWED_LOG_FIELDS` in `app/core/logging.py` names the
only fields that may be emitted, and a logging filter drops everything else.
Tracebacks are reduced to exception type and message for the same reason.

### Configuration fails loudly outside `local`

`Settings.validate_for_environment()` refuses to run `preview`, `staging` or
`production-beta` on the local database default, so a misconfigured deploy
cannot quietly point at the wrong database. It runs in both `create_app()` and
the worker's `run()`, so injecting settings directly does not bypass it.

### Health endpoints sit outside `/api/v1`

They are operational endpoints for load balancers and deploy checks, not part
of the versioned product API. `/health/live` reports only that the process
serves HTTP; `/health/ready` degrades to 503 — in the standard error envelope —
when PostgreSQL is unreachable.

### The API client returns errors instead of throwing

`AsyncState<T>` (`docs/03_FRONTEND_ARCHITECTURE.md` section 5) requires every
screen to handle `idle | loading | success | error`. `requestJson` returns a
discriminated result, so the error branch is a type-level obligation rather
than a convention.

## What Phase 0 deliberately does NOT do

| Not built | Why |
|---|---|
| Design tokens, typography, components | Phase 1. The palette in `docs/02_UX_UI_SPEC.md` still needs contrast validation; freezing unvalidated values now would be wrong. |
| Auth, sessions, allowlist | Phase 2. The auth provider is open item 1. |
| The home screen | Phase 3. `app/page.tsx` is a developer status page and makes no product claim. |
| Database tables and migrations | `docs/05_DATA_MODEL.md` is a *logical* model and asks for migrations only after relationships are validated in implementation. Alembic is wired so the first model can migrate immediately. |
| Provider adapters (LLM, OCR, storage, queue, email) | Open items 1–5. Defining Protocols before there is a caller would be abstraction without a use case; each arrives with its phase. |
| A queue in the worker | Open item 4. The worker starts, validates config, logs and exits. |
| Empty domain folders | `CLAUDE.md` says avoid premature abstraction. The target layout is documented in `backend/README.md` and `frontend/README.md` instead. |
| Playwright / E2E | Phase 2 at the earliest — there is no user flow to test yet. |

## Local verification performed

PostgreSQL 16 was run locally (the sandbox has no Docker daemon, so
`postgres`/`initdb` were used directly instead of `docker compose`; the
compose file is the documented path and is unchanged in intent). Verified:

- `/health/live` → 200 `{"status":"ok"}` with an `X-Request-ID` header;
- `/health/ready` → 200 `{"status":"ready","dependencies":{"database":"ok"}}`;
- database stopped → `/health/ready` → 503 `SERVICE_UNAVAILABLE` while
  `/health/live` stayed 200; database restarted → `/health/ready` → 200 again;
- unknown route → 404 in the error envelope with a request id;
- `alembic upgrade head` runs cleanly against a real database;
- frontend served by `pnpm start` rendered the API's readiness;
- backend stopped → the frontend rendered its `role="alert"` error state with
  `NETWORK_UNAVAILABLE`, not a blank screen or a crash;
- request logs contained only allow-listed operational fields.

## Next phase

Phase 1 — Design System. Tokens, typography, and the component set in
`docs/11_BUILD_PLAN.md` Phase 1, with a showcase route. No domain logic.
