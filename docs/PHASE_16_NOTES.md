# Phase 16 — Security / Beta Hardening

`docs/11_BUILD_PLAN.md` Phase 16 asks for a review across ten areas. This
document records what was checked, what was changed, and — for the areas that
depend on infrastructure that does not exist yet — exactly what is still owed
before an invite goes out.

Nothing here adds a feature. Every change narrows what a mistake elsewhere
could do.

---

## 1. Authorization

Audited every operation in the OpenAPI schema: **31 operations**, of which
five are unauthenticated by design —

- `POST /api/v1/auth/request-magic-link`
- `POST /api/v1/auth/verify`
- `POST /api/v1/auth/sign-out` (idempotent; signing out without a session is
  not an error)
- `GET /health/live`
- `GET /health/ready`

Every other operation resolves `CurrentUser`, and every resource route
re-checks ownership in the service rather than trusting the path. A policy id
in the URL is never enough: `get_policy` scopes by `user_id`, and the document
download re-derives the storage key from the row it just authorised.

`/docs` and `/openapi.json` were already gated to `APP_ENV=local`. A test now
holds that: it builds an app with `app_env="production-beta"` and asserts both
return 404. Publishing the schema next to private data would hand an attacker
a map.

**No changes required.**

## 2. Object storage access

There is still no object store (open item in `docs/13_DECISIONS_AND_OPEN_ITEMS.md`),
so `docs/09_AWS_DEPLOYMENT.md` section 5 cannot be satisfied yet. What exists
instead:

- `build_file_storage()` **refuses to run outside `APP_ENV=local`** rather than
  falling back to a container filesystem. A deployed environment fails to
  start; it does not quietly accept a beta user's policy document and put it
  somewhere that cannot keep it.
- `LocalFileStorage` resolves every key and re-checks it is inside the storage
  root, writes `0o600`, and defaults to a directory under the developer's home
  — not `/tmp` or `/var/tmp`, which every account on the machine can read.
- `storage_key()` is built only from identifiers we generated. A filename never
  reaches the filesystem; the extension is checked to be alphanumeric before it
  is used.
- There is no route that returns a document without a session and an ownership
  check. There is no public URL, signed or otherwise.

**Owed before deployment:** an S3 adapter with block-public-access, SSE, a
lifecycle policy, and per-environment prefixes.

## 3. Logs

Two changes, one of them a real leak.

`ALLOWED_LOG_FIELDS` already dropped any structured field not on the
allow-list, and a check across the codebase confirms **every** `logger.*` call
goes through `log_fields()`. But `JsonFormatter` wrote `str(exc_value)` into
`exception_message` on any record carrying `exc_info` — and an exception's text
is not ours to publish. A database integrity error quotes the value that
collided; a validation error quotes the input. Both are exactly what
`docs/09_AWS_DEPLOYMENT.md` section 9 forbids in logs, and the unhandled-error
path in `RequestContextMiddleware` uses `logger.exception`.

`JsonFormatter` now takes `include_exception_message`, which `configure_logging`
sets from `settings.is_local`. Deployed logs get the exception *type* and the
request id — enough to find the request — and never the message. Locally the
message is kept (you are debugging with your own data) but truncated to 500
characters.

## 4. Rate limits

New `app/core/rate_limit.py`: a sliding-window limiter, per process.

| Key | Limit | Why |
|---|---|---|
| `magic-link:email:<address>` | 5 / 15 min | A beta user cannot be flooded with sign-in mail sent by us |
| `magic-link:ip:<addr>` | 20 / 15 min | One caller cannot spray many addresses |
| `verify:ip:<addr>` | 30 / 15 min | A token has 32 bytes of entropy, so a search is hopeless; this stops it being free, and stops a stolen link being replayed at speed |
| `upload:<user_id>` | 20 / hour | Uploads cost storage and worker time |
| `question:<user_id>` | 60 / hour | Q&A will cost provider spend once an LLM is configured |

The window slides rather than resetting on a boundary — a fixed bucket lets a
caller send twice the budget across a tick, and there is a test for exactly
that. The address is normalised before it becomes a key, so `A@x.com` and
`a@x.com` are one bucket, not two.

`X-Forwarded-For` is used when present, because behind a load balancer the
socket address is the balancer's. That header is client-controllable when
nothing strips it, which is why it is *only* ever a rate-limit key: forging it
costs the forger their own bucket and buys them nothing.

**Known limit:** the counter lives in the process. Two API instances mean two
budgets. That is honest for a beta of a handful of users on one instance; a
shared store (Redis, or the database) is the fix when there is more than one.
Recorded in `docs/SPEC_ISSUES.md`.

## 5. Upload attacks

`validate_upload()` already rejected empty files, oversized files, unsupported
types (by magic bytes, not by the client's declared content type), encrypted
PDFs and corrupt PDFs. Phase 16 adds one more:

- **`TOO_MANY_PAGES`** — a PDF is a container, and a small file can declare
  thousands of pages that the worker then walks one at a time. Refusing at
  upload is cheaper than discovering it in extraction. `MAX_DOCUMENT_PAGES`
  defaults to 400, far above a real policy booklet.

Also holding from earlier phases: `Content-Disposition: attachment` with a
*generated* filename (the reader's own filename is untrusted text and putting
it in a header invites header injection), plus `X-Content-Type-Options:
nosniff` — together these stop an uploaded file being rendered in the origin's
context.

## 6. Deletion

Verified, unchanged. `delete_policy()` removes the bytes **first**, then marks
the rows deleted, then writes a `PolicyDeletionAudit` carrying
`storage_confirmed`. If storage fails, the audit records that objects may still
exist rather than claiming a clean deletion — a delete path that reports
success it cannot vouch for is worse than one that admits a problem.

## 7. Backups

**Not satisfiable in this phase, and not faked.** `docs/09_AWS_DEPLOYMENT.md`
section 6 requires automated backups on managed PostgreSQL. There is no AWS
account and no database instance (open item in
`docs/13_DECISIONS_AND_OPEN_ITEMS.md`), so there is nothing to configure and
nothing to test. Writing a backup script against an instance that does not
exist would be documentation of a wish.

What Phase 16 *can* do is make the beta refuse to run without the things that
protect the data it holds. `validate_for_environment()` now fails to start a
deployed environment that has not been configured — see below.

**Owed before deployment:** managed PostgreSQL with automated backups,
encrypted storage and restricted network access, plus one tested restore. The
restore is the part people skip; a backup nobody has restored is a hypothesis.

## 8. Error handling

The single error envelope and the `AppError` hierarchy were already in place
and are unchanged. Added `RateLimitedError` (`RATE_LIMITED`, 429, retryable).
The 429 body is the same shape as every other error, so the frontend's existing
error handling covers it without a special case.

New in configuration — a deployed environment now refuses to start when:

- `DATABASE_URL` is still the local default (already present);
- `CORS_ALLOWED_ORIGINS` is empty or still `http://localhost:3000`;
- any CORS origin is `*` — the API sends credentials, so **every listed origin
  can read a signed-in user's data**; a wildcard there is an open door, not a
  misconfiguration;
- any CORS origin is plain http — the session cookie is `Secure`, so such an
  origin cannot work and listing it only misleads;
- `FRONTEND_BASE_URL` is still localhost, which would send sign-in links to a
  machine the reader is not on;
- `HOME_DEMO_DATA` is on outside local/preview (already present).

Local development is untouched: `make dev` still needs no configuration.

## 9. Security headers

New `SecurityHeadersMiddleware`, outermost in the stack so it covers error
responses too — a 401 is the response an attacker sees most often.

```text
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Content-Security-Policy: default-src 'none'; frame-ancestors 'none';
                         base-uri 'none'; form-action 'none'
Referrer-Policy: no-referrer
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
Strict-Transport-Security: max-age=31536000; includeSubDomains   (non-local only)
```

The policy is stricter than a website's because this API renders nothing:
`default-src 'none'` means a response that somehow reached a browser as a
document could load nothing at all. `Referrer-Policy: no-referrer` keeps the
path of a private document out of a `Referer` header. HSTS is withheld locally,
where there is no TLS to insist on and setting it would poison the developer's
browser for `localhost`.

## 10. Accessibility and responsive behaviour

Both are checked per phase as part of the definition of done, in a real browser
rather than by inspection, and each phase's notes record what was driven. The
Phase 16 change with a user-visible surface is the `/design-system` route,
which is now `notFound()` unless `NEXT_PUBLIC_APP_ENV=local`. It is developer
reference: it names routes that are not built and renders every error and empty
state out of context, which is misleading to anyone who is not building the
thing.

---

## What is still owed before an invite goes out

Ordered by what blocks what. None of these are code problems; all of them are
decisions or accounts that do not exist yet.

1. **An email provider.** Nothing can sign in remotely without one. Local
   development writes links to a file; that is not a beta.
2. **A database with backups**, and one tested restore.
3. **An object store** for uploaded documents, or the decoder stays off
   (`FEATURE_POLICY_DECODER=false`) — which is a legitimate way to ship the
   first beta.
4. **A shared rate-limit store** if more than one API instance runs.
5. **An LLM provider** for Q&A and explanation, and an **OCR provider** for
   scanned documents. Both currently refuse rather than fabricate, and the UI
   states plainly that the capability is unavailable — so their absence is
   visible, not silent.

## Checks

```text
ruff format · ruff check · mypy (strict) · pytest       backend
tsc --noEmit · eslint · vitest                          frontend
```

All green — 404 backend tests, 228 frontend. 18 new backend tests across
`tests/test_security_hardening.py`, `tests/test_logging_safety.py` and
`tests/test_config.py`.
