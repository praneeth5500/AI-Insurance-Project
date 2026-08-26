# Phase 10 — Policy Upload

## What this phase changed

The first thing in this product that genuinely belongs to the user. Every
other piece of data so far is either a catalogue we authored or answers the
reader gave a form; a policy document is *their* file, and most of the design
here is about what must not happen to it.

The flow is: validate the bytes → create the records → store the bytes →
enqueue the job → commit. That order matters. Validation comes first so a file
we will not process is never written anywhere. The commit comes last so a
queued job can never point at a policy row that was rolled back.

## Decisions and why

### The feature is off, and the server enforces that

`FEATURE_POLICY_DECODER` has existed since Phase 3, showing "Coming soon" on
the home card. The whole upload flow is built behind it and the flag is
checked **on the server**, not only in the UI. An upload endpoint that quietly
worked while the product said the feature did not exist would be collecting
private documents it has nothing to do with.

### Storage is an interface, and the local one refuses to deploy

`docs/09_AWS_DEPLOYMENT.md` section 5 sets the requirements — block public
access, encrypt at rest, separate by environment, signed temporary URLs, a
lifecycle policy, a deletion path. No bucket is chosen, so `FileStorage` is a
Protocol with a local implementation that writes to a private directory under
the developer's home (not `/tmp`, which every account on the machine can read)
and **raises outside `APP_ENV=local`**. Losing beta users' policy documents to
a container restart is worse than refusing to start.

### There is no public URL, and no signed link either

A document is only ever streamed back through `GET /policies/{id}/documents/{id}`,
which re-checks ownership on every request. That is stricter than the signed
temporary URL the deployment spec allows, and it is what `CLAUDE.md` rule 7
actually asks for: access cannot outlive the reader's session, because there is
no artefact to outlive it. The response carries `Content-Disposition:
attachment` and `X-Content-Type-Options: nosniff` so an uploaded file cannot be
rendered in the origin's context.

### Nothing the client says about the file is trusted

A `Content-Type` header is a claim and a filename extension is a claim. The
type is determined from the bytes. A storage key is built from identifiers we
generated, never from a filename — a filename can contain path separators and
traversal sequences, and here it is display text only.

### Every rejection says what to do next

"Upload failed" tells someone with a password-protected PDF nothing. So each
refusal has its own message: an encrypted PDF says to save an unlocked copy, a
corrupt one says to download it from the insurer again, an oversized one
suggests exporting a scan at lower resolution.

A **scan is not a failure**. It is a document that needs a different reading
path, and the validator records whether a text layer exists so the worker knows
which path to take.

### The queue carries identifiers only

`docs/09_AWS_DEPLOYMENT.md` section 8. A queue row must never become a second,
unprotected copy of someone's policy. `DatabaseJobQueue` is the local adapter
open item 4 asks for — a real queue with atomic claims
(`FOR UPDATE SKIP LOCKED`), leases so a crashed worker's job is reclaimed
rather than stuck, bounded retries, and a bounded error field so document
content cannot leak into it.

### Deleting means deleting, and says so honestly

The bytes go first, then the rows are marked. If storage cannot confirm the
removal, the audit records `storage_confirmed = false` and says objects may
still exist. A delete path that reports a clean success it cannot vouch for is
worse than one that admits a problem. The audit keeps identifiers and a
timestamp and nothing about the document — a trace that preserved the filename
would defeat the deletion.

## Spec divergence

`docs/08_API_CONTRACTS.md` section 7 describes returning "presigned/private
upload instructions or upload session". Presigning needs an object store and
one is not chosen, so this implements the other half of that sentence: the file
is posted to the API, which validates it before anything is written. The
storage interface is shaped so a presigned flow can be added without changing
callers. Recorded in `docs/SPEC_ISSUES.md`.

## What is deliberately not here

The worker does not consume the queue yet. Extraction is Phase 11, and a
worker that claimed jobs only to fail them would turn every upload into a
visible error. A policy sits at "Reading document" until Phase 11 gives the
worker something to do — which is why the feature stays flagged off.

## Verification

Backend: 35 new tests (284 total) covering validation by content, cross-user
access on read, download and delete, storage-key construction, deletion
auditing including the unconfirmed case, and queue claim/retry/lease
behaviour.

Browser: 18 checks in real Chromium — an executable renamed `.pdf` refused by
its bytes, a real PDF accepted, named stages with no percentage, leaving and
returning, a signed-out request refused with 401, mobile layout and tap
targets, and a delete that actually removes the policy.

## Open questions

1. **The 20 MB limit and the 5-document limit** are mine, not the
   specification's. Both are configuration.
2. **No object-storage vendor is chosen.** The adapter is written to fail
   closed until one is.
3. **No antivirus scan.** The beta checklist does not ask for one, and the
   files are never executed or served back inline, but a real beta accepting
   documents from outside your household should probably have one.

## Definition of done

| Item | Status |
|---|---|
| Private upload | ✅ never publicly readable, no signed URL either |
| File validation | ✅ type from bytes, size, encryption, corruption |
| DB record | ✅ policies, documents, deletion audit |
| Queue job | ✅ local adapter, identifiers only |
| Processing UI | ✅ named stages, leave and return |
| Failure handling | ✅ specific, actionable messages; failure stays visible |
