# Phase 17 — Friends & Family Beta

`docs/11_BUILD_PLAN.md` Phase 17 is not a feature. It is an activity the
founder performs: invite three to five people, watch where they get confused,
fix that, then invite ten to twenty more. "Do not optimize growth before the
product is understandable and reliable."

Two things belong to engineering here.

1. **The operator surface the activity needs.** You cannot run a beta you
   cannot see or take back.
2. **A verification pass over `docs/12_BETA_CHECKLIST.md`** — an honest one,
   where an unticked box stays unticked.

---

## 1. Operator surface

Invites already existed (`make seed-allowlist`). Two things were missing:
there was no way to withdraw access, and no way to see the state of the beta.
Both are now command-line tools, matching the existing idiom. An admin UI is
still deliberately not built — `docs/PHASE_2_NOTES.md` records that as a
product decision, and guessing at it is exactly what CLAUDE.md forbids.

```bash
make seed-allowlist                                  # invite (existing)
make revoke-access EMAILS=a@example.com,b@example.com # withdraw
make beta-status                                     # who holds an invite, who used it
```

**Revocation ends live sessions, not just the allowlist flag.** `resolve_session`
already re-checks `can_sign_in` on every request, so a revoked person is refused
on their next request regardless — but the database should say what is true, and
a later change to that check must not be able to quietly reopen access.
Reinstating someone does *not* resurrect the sessions that were ended: access
comes back, the old cookie does not.

`make beta-status` exists for one number in particular — how many invited
people have **never signed in**. That is the number that tells you the mail is
not arriving, and it is invisible from inside the application. Verified against
the local database: three seeded invites, three "never", then one revocation
that ended 14 live sessions, then a reinstatement that restored access without
restoring the sessions.

Invited addresses print to the operator's terminal and never reach the
application log — the log gets counts and identity ids only.

## 2. Beta checklist verification

Verified against `docs/12_BETA_CHECKLIST.md`. Where a box could be checked
mechanically it was; where it needs the founder personally, it says so.

### Passing

- **Product scope** — health is the only enabled recommendation domain
  (`FEATURE_MOTOR_RECOMMENDATION=false`); claims readiness is explanation plus
  checklist with no filing path; there is no checkout anywhere.
- **Access** — allowlist enforced, magic link works, sessions expire and
  revoke, non-allowlisted addresses blocked without revealing that they are
  not invited (`tests/test_auth_flow.py`).
- **Recommendation** — deterministic ranking with no LLM in the path, hard
  eligibility exclusions, top 5 plus 5 more, comparison capped at 3, category
  fit labels with no overall numeric score anywhere in the UI, why + watch-out
  on every match, unknown critical data shown as `UNVERIFIED` rather than
  averaged away, and runs immutable after the fact
  (`tests/test_matching.py`, `tests/test_recommendations.py`).
- **Product data** — all 10 catalogue products are `SYNTHETIC` and labelled as
  demo products on screen; catalogue version `synthetic-health-002`.
- **Premium** — price is a *state*, never a bare number; there is no invented
  range and no personalised "from" price.
- **Upload** — PDF works; a scanned PDF fails clearly rather than silently
  producing blank pages; file size, page count, type and password-protection
  are all enforced; storage is private and a cross-user access test passes
  (`tests/test_policy_upload.py`).
- **Decoder / Q&A** — facts carry citations, not-found and conflicting states
  are visible, and an unavailable LLM produces a refusal rather than a guess
  (`tests/test_decoder.py`, `tests/test_qa.py`).
- **Privacy/security** — no public storage, no raw documents or health answers
  in logs or analytics, deletion works and is audited, sign-out works, no
  secrets in the repository. See `docs/PHASE_16_NOTES.md`.
- **Analytics** — all 11 events the checklist names are defined *and* emitted.
  Checked by locating each event's emit site, not by reading the definitions.
- **UX** — mobile questionnaire, mobile comparison, decoder split and mobile
  layouts, keyboard basics, readable errors, and loading/empty states were each
  driven in a real browser in their own phase; the per-phase notes record what
  was tested.

### Not passing, and cannot pass here

- **`Production-beta DB separate from local/staging`** — there is no deployed
  database at all. Blocked on infrastructure.
- **`I have personally tested the full flow on mobile`** — founder review.
- **`I have asked at least a few users to complete it without my help`** —
  founder review, and the whole point of the phase.

The last two are the checklist working as intended. They are not for me to
tick.

## 3. What has to happen before the first invite goes out

In order. Nothing below is a code problem.

1. **An email provider.** Without one, no invited person can sign in remotely.
   The provider sits behind `EmailProvider`; local development writes links to
   `backend/.dev-magic-links.log`, which is not a beta. **Hard blocker.**
2. **A database with automated backups**, and one restore actually tested.
3. **A deployment**, with `APP_ENV`, `DATABASE_URL`, `CORS_ALLOWED_ORIGINS` and
   `FRONTEND_BASE_URL` set. The API now refuses to start without them, so this
   will surface immediately rather than as a subtle failure.
4. **Decide whether the decoder is in the first beta.** `FEATURE_POLICY_DECODER`
   is off by default, and shipping the first beta without it is legitimate: the
   decoder needs an object store, and Q&A needs an LLM provider. The
   recommendation flow stands on its own.
5. **Confirm the open questions** in `docs/SPEC_ISSUES.md` — the weighting
   multipliers, the fit thresholds, the upload limits and the rate-limit
   numbers are all chosen by me and marked as needing your confirmation.

Suggested first invite list, per the build plan: **three to five people you can
sit next to.** The point is watching where they hesitate, which no analytics
event will tell you.

## Checks

```text
ruff format · ruff check · mypy (strict) · pytest       backend
tsc --noEmit · eslint · vitest                          frontend
```

All green. 10 new backend tests in `tests/test_beta_operations.py`, plus the
operator scripts exercised end-to-end against the local database.
