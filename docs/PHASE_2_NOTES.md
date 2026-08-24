# Phase 2 — Beta Auth

Implementation notes for `docs/11_BUILD_PLAN.md` Phase 2.

## Definition of done

| Requirement | Status | Evidence |
|---|---|---|
| Allowlisted user can sign in | ✅ | Full flow verified in Chromium: email → link → session → protected home |
| Non-allowlisted user cannot access app | ✅ | No link is issued; the response is identical to an invited address; `/app/*` redirects to sign-in |
| Expired token handled | ✅ | Expired, already-used and unknown links all return `SIGN_IN_LINK_INVALID` with a "request a new link" action |
| Session protected | ✅ | `/api/v1/me` 401s without a valid session; expired, revoked and de-allowlisted sessions all fail |

## The flow

```text
/sign-in            email entry, one field, no password
   |
   |  POST /api/v1/auth/request-magic-link      always the same response
   v
email               link to /auth/verify?token=...   single use, expiring
   |
   |  POST /api/v1/auth/verify                  sets an httpOnly session cookie
   v
/app/home           protected: middleware fast path + requireUser() on every request
   |
   |  POST /api/v1/auth/sign-out                revokes the session row
   v
/sign-in
```

## Decisions taken

### Opaque random tokens, not signed tokens

`docs/04_BACKEND_ARCHITECTURE.md` section 7 asks for a "signed/expiring token"
with "one-time use where practical" and "session revocation". Both magic-link
and session tokens are 32 bytes of `secrets.token_urlsafe`, stored **only as a
SHA-256 digest**.

This is a deliberate reading of the requirement rather than a literal one: a
self-contained signed token cannot be revoked before it expires, and one-time
use needs server state anyway. A random token checked against a row gives
single use, revocation and immediate de-allowlisting — and there is no signing
secret to leak. A stolen database still cannot be replayed against the API.

### The response never reveals allowlist membership

`docs/08_API_CONTRACTS.md` section 1 says the response should be generic.
Requesting a link returns `{"status": "SENT_IF_ELIGIBLE"}` whether or not the
address is invited, and the UI wording matches: *"If you@example.com is on the
beta invite list, a sign-in link is on its way."* It never claims an email was
sent. Both properties are covered by tests.

Similarly, unknown, expired, already-used and revoked links return one
identical error. Distinguishing them would tell an attacker which tokens exist,
and the user's next action ("request a new link") is the same in every case.

### Auth identity and user profile are separate rows

`docs/01_PRODUCT_SPEC.md` section 6 requires it. `auth_identities` holds email,
allowlist status and sign-in history; `users` is the domain profile that
households, vehicles and policies will hang off. First sign-in creates the
`users` row; the identity never becomes the profile.

`hasProfile` is honestly `false` until a profile exists — it is not a
placeholder `true`.

### Two layers of protection on `/app/*`

Next.js middleware checks only that a session cookie *exists* — a fast path
that saves an anonymous visitor a round trip. The real gate is `requireUser()`
in the protected layout, which asks the API on every request. A cookie's
presence is never treated as proof of a session, and the code says so.

If the API is unreachable, `getCurrentUser()` returns null, so a protected page
**fails closed** rather than rendering as though the user were signed in.

### Revocation takes effect immediately

`resolve_session` re-checks `allowlisted` and `status` on every request, so
withdrawing access ends live sessions on the next request rather than at
session expiry. Covered by a test.

### Email delivery is behind an adapter and fails closed

The vendor is open item 1 in `docs/13_DECISIONS_AND_OPEN_ITEMS.md`, so only
the `EmailProvider` Protocol is fixed. Local development writes links to
`backend/.dev-magic-links.log` (gitignored) rather than the application log,
because `docs/09_AWS_DEPLOYMENT.md` section 9 forbids magic-link tokens in
logs and that rule should not bend for convenience. The dev adapter refuses to
construct outside `APP_ENV=local`, and `build_email_provider` raises in
deployed environments until a real adapter is configured — so a deployment
cannot silently swallow invites.

### Audit metadata is allow-listed

`docs/05_DATA_MODEL.md` section 10 forbids sensitive content in audit metadata.
`ALLOWED_METADATA_KEYS` drops anything not on the list, so an email address or
token cannot reach the audit table by accident. A test asserts the invited
address never appears in any audit row.

### `lazy="raise"` on the auth relationships

See "Defects found" below. Implicit lazy loading under async SQLAlchemy either
raises `MissingGreenlet` or silently succeeds from the weak identity map,
depending on garbage collection. Both auth relationships are declared
`lazy="raise"` so an accidental traversal fails deterministically, in tests as
well as in production.

## Defects found while building

### 1. Sign-in 500'd on a real server while every test passed

Building the verify response from `issued.user.auth_identity.email` traverses a
lazily loaded relationship after the commit. Under async SQLAlchemy that
attempts IO outside the greenlet context and raises `MissingGreenlet` — but
only when the identity has been evicted from SQLAlchemy's **weak** identity
map. Whether it fails depends on garbage collection, which is why:

- the unit tests passed (the fixture kept the identity referenced);
- a per-request-session integration test still passed;
- the live server failed on the first sign-in of a fresh identity;
- and after an unrelated refactor the live server stopped failing.

A flaky auth bug that only appears for some users is exactly the kind of thing
that must not reach a beta. The fix is structural rather than defensive: the
response carries the identity explicitly, and `lazy="raise"` now makes any
accidental traversal fail loudly and deterministically. Reintroducing the old
line now fails two tests immediately — verified.

### 2. `NEXT_PUBLIC_API_BASE_URL` is inlined at build time

Setting it only at `pnpm start` left the browser calling `localhost:8000`
while the page was served from `127.0.0.1:3000`. The session cookie was set on
a different host and never sent back, so sign-in appeared to succeed and then
bounced straight back to `/sign-in`.

This was a harness mistake, but it is also a real deployment trap, so it is
written down here: **the variable must be set at build time**, and the API and
the app must be same-site for the cookie to be sent. `SESSION_COOKIE_DOMAIN`
exists for the deployed case where they are different subdomains of one site.

## Open questions for the founder

1. **Token and session lifetimes.** The specification does not fix either.
   Defaults are 15 minutes for a magic link and 14 days for a session, both
   configurable. Please confirm or change — 14 days on a beta that will hold
   health answers may be longer than you want.
2. **How invites are issued.** Currently `BETA_ALLOWLIST_EMAILS` plus
   `make seed-allowlist`, run by an operator. That is deliberately the smallest
   thing that works; an admin screen is a product decision I did not want to
   invent.
3. **Rate limiting.** `POST /auth/request-magic-link` is currently unthrottled,
   so a third party could repeatedly trigger emails to an invited address.
   Rate limits are listed under Phase 16, so this is flagged rather than built
   — say the word if you would rather it were done sooner.
4. **`/design-system` is still public.** Raised in Phase 1 and still true. It
   holds no data, but it should move behind auth or be disabled outside
   `local`.

## What Phase 2 deliberately does NOT do

| Not built | Why |
|---|---|
| The real home screen | Phase 3. `/app/home` is a placeholder that makes no product claim and offers no feature that does not exist. |
| Households, profiles, vehicles | Later phases. Only `auth_identities` and `users` exist. |
| Analytics events | Phase 15. |
| Rate limiting | Phase 16 (see open question 3). |
| A production email adapter | Vendor undecided; the interface is fixed and deployment fails closed without one. |

## Next phase

Phase 3 — Home: the new-user and returning-user home screens from
`docs/02_UX_UI_SPEC.md` sections 5 and 6, with mock data first.
