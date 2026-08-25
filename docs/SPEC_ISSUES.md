# Specification issues

Technical inconsistencies found while reading the specification. **No
specification file has been edited** — this log exists so the conflicts are
recorded rather than silently resolved in code.

Each item names the phase that has to settle it. Until then, nothing is
invented: the ambiguity stays visible.

---

## 1. `recommendation_runs` has no status column — Phase 9

`docs/05_DATA_MODEL.md` section 6 lists `recommendation_runs` without a status
field, but `docs/08_API_CONTRACTS.md` section 4 returns
`{"runId": "...", "status": "PROCESSING"}` and later `"status": "READY"`.

**Impact:** the API cannot report run status from the model as specified.
**Options:** add `status` to `recommendation_runs`, or derive it from the
presence of candidates. Needs a decision before Phase 9 migrations.

## 2. Extraction confidence is both a number and an enum — Phase 11

`docs/07_POLICY_DECODER_AI.md` section 4 shows `"confidence": 0.96` (numeric);
section 5 defines the states `HIGH | MEDIUM | LOW | NOT_FOUND | CONFLICTING`.
`docs/05_DATA_MODEL.md` section 7 leaves `policy_facts.confidence` untyped.

**Impact:** unclear what is persisted and what the UI reads.
**Likely resolution:** store both — a numeric model score plus a derived state,
since `NOT_FOUND` and `CONFLICTING` are not points on a 0–1 scale. Needs
confirmation.

## 3. Analytics event name mismatch — Phase 15

`docs/03_FRONTEND_ARCHITECTURE.md` section 7 lists `questionnaire_reviewed`.
`docs/12_BETA_CHECKLIST.md` requires `questionnaire_completed`.

**Impact:** the beta checklist cannot be ticked off against the implemented
event.
**Note:** these may be two genuinely different events (reviewing the summary
vs. submitting it). Needs a decision.

## 4. `QuestionDefinition` has no text input type — Phase 4

`docs/01_PRODUCT_SPEC.md` section 2.2 allows "simple numeric/**text** inputs
where required", but the `inputType` union in
`docs/03_FRONTEND_ARCHITECTURE.md` section 3 offers only `SINGLE_CHOICE`,
`MULTI_CHOICE`, `NUMBER`, `MONEY`, `PINCODE`, `BOOLEAN`.

**Impact:** any free-text question is unrepresentable.
**Note:** possibly deliberate — free text is hard to match on deterministically.
Needs confirmation before the question schema is frozen.

## 5. Two routes appear to render the same results view — Phase 5

`docs/03_FRONTEND_ARCHITECTURE.md` section 2 lists both
`/app/recommend/health/results/:runId` and `/app/recommendations/:runId`.

**Impact:** duplicate implementations, or an undocumented redirect.
**Suggested resolution:** treat `/app/recommendations/:runId` as canonical
(it is domain-agnostic and matches the saved-run concept) and redirect the
other. Needs confirmation.

## 6. Upload ordering is ambiguous — Phase 10

`docs/08_API_CONTRACTS.md` section 7 defines `POST /policies/uploads`
("returns presigned/private upload instructions") and `POST /policies`
("create processing record after successful upload"). It is not stated whether
the policy record exists before the file is stored.

**Impact:** affects orphaned-upload cleanup and the storage key layout.
**Note:** the second reading (upload first, then create the record) leaves
uploaded objects with no owning row until step two completes.

## 7. Recommendation runs are async in the contract, synchronous in the engine — Phase 9

`docs/08_API_CONTRACTS.md` section 4 returns `PROCESSING`, implying a job.
`docs/06_RECOMMENDATION_ENGINE.md` describes deterministic matching that
should complete in milliseconds.

**Decision taken in Phase 0:** none — no code depends on this yet. The
async-shaped contract is the safer envelope to keep (it permits a synchronous
implementation that returns `READY` immediately), but this should be confirmed.

## 8. `Toast` is specified as a global component but has no phase — Phase 3+

`docs/03_FRONTEND_ARCHITECTURE.md` section 4 lists `Toast` among the global
components, but the Phase 1 build list in `docs/11_BUILD_PLAN.md` does not
include it (it lists "Alert", which is `InlineAlert`).

**Impact:** none yet. Not built in Phase 1, to avoid widening the phase.
**Suggested resolution:** build it with the first feature that needs a
transient, non-blocking confirmation — most likely saving a match (Phase 5/7).
Confirm whether transient toasts are wanted at all: an in-page `InlineAlert`
is more durable for a product built around trust and re-reading.

## 9. The data model has no storage for the magic-link flow — Phase 2 (implemented)

`docs/05_DATA_MODEL.md` section 1 defines `auth_identities` and `users`, but
the magic-link flow that `docs/04_BACKEND_ARCHITECTURE.md` section 7 requires
also needs somewhere to keep issued links and live sessions. Neither is in the
logical model.

**Resolved by adding two tables**, since Phase 2 cannot exist without them:

- `magic_link_tokens` — token digest, expiry, `consumed_at` (single use);
- `sessions` — token digest, expiry, `revoked_at` (revocation).

Both store only a SHA-256 digest, never the token. Please confirm these belong
in the data model document, or tell me how you would rather they be shaped.

## 10. `POST /api/v1/auth/sign-out` is not in the API contracts — Phase 2 (implemented)

`docs/11_BUILD_PLAN.md` Phase 2 requires sign out, but
`docs/08_API_CONTRACTS.md` section 1 lists only `request-magic-link` and
`verify`. Added `POST /api/v1/auth/sign-out`, which revokes the session row and
clears the cookie, and is idempotent. Flagged so the contracts document can be
updated deliberately rather than drifting.

## 11. Phase 3 has no "Done when" section — Phase 3

Every other phase in `docs/11_BUILD_PLAN.md` ends with acceptance criteria.
Phase 3 lists what to build and stops.

**Impact:** no agreed bar for when the home screen is finished.
**Handled by** holding Phase 3 to `CLAUDE.md`'s own definition of done plus the
two home sections of the specification; the resulting checklist is in
`docs/PHASE_3_NOTES.md`. Please confirm it matches what you intended.

## 12. Analytics events: `CLAUDE.md` and the build plan disagree on timing

`CLAUDE.md`'s definition of done requires "analytics event exists where
specified", and `docs/03_FRONTEND_ARCHITECTURE.md` section 7 specifies
`home_viewed` for this screen. But `docs/11_BUILD_PLAN.md` sequences all
analytics at Phase 15.

**Impact:** every phase from 3 onwards either builds an analytics pipeline
early or ships without the specified event.
**Not resolved.** Phase 3 followed the build plan and did not implement
`home_viewed`. Either the build plan should move analytics earlier, or
`CLAUDE.md`'s definition of done should say "from Phase 15 onwards".

## 13. `GET /api/v1/home` is not in the API contracts — Phase 3 (implemented)

`docs/08_API_CONTRACTS.md` begins at the questionnaire and defines nothing for
the home screen, which `docs/11_BUILD_PLAN.md` Phase 3 requires.

**Resolved by adding** `GET /api/v1/home`, returning feature availability, a
nullable continue action, and the conditional modules from
`docs/01_PRODUCT_SPEC.md` section 5. Flagged so the contracts document can be
updated deliberately.

## 14. `QuestionDefinition` cannot express "choose up to 3" — Phase 4 (implemented)

`docs/01_PRODUCT_SPEC.md` section 2.3 says "Choose up to 3 things that matter
most", but the `QuestionDefinition` schema in
`docs/03_FRONTEND_ARCHITECTURE.md` section 3 has no field for a selection
limit.

**Resolved by adding** `maxSelections` (MULTI_CHOICE only). Also added
`sensitive`, because `docs/05_DATA_MODEL.md` section 2 requires sensitive
fields to be flagged in metadata and the schema has no way to say so. Both are
enforced server-side.

## 15. Phase 4 also has no "Done when" section

Same gap as issue 11. Phase 4 was held to its build list plus `CLAUDE.md`'s
definition of done; the resulting checklist is in `docs/PHASE_4_NOTES.md`.

## 16. Phase 5 has no "Done when" section either

The third phase in a row (see issues 11 and 15). Phase 5 was held to its build
list plus `CLAUDE.md`'s definition of done; the checklist is in
`docs/PHASE_5_NOTES.md`. Worth a single decision covering Phases 3 onwards
rather than one per phase.

## 17. `POST /comparisons` names `productVersionIds`, and has no table

`docs/08_API_CONTRACTS.md` section 6 sends `productVersionIds`, but product
versions are Phase 8; until then the identifiers are synthetic product
references, so the field is named `productReferences` for what it actually
carries. It becomes `productVersionIds` when product versions exist.

`docs/05_DATA_MODEL.md` also defines no `comparisons` table. None was added: a
comparison is derived from a recommendation run plus a selection, both already
stored, and persisting it would create a record that can silently disagree
with the run it came from.

## 18. "Save" has no table, and no home module — Phase 7

`docs/11_BUILD_PLAN.md` Phase 7 asks for "save", but `docs/05_DATA_MODEL.md`
defines no table for saved products, and `docs/01_PRODUCT_SPEC.md` section 5
does not list saved products among the returning-home modules.

**Resolved by adding** a minimal `saved_products` table (user, product
reference, timestamp). **Not resolved:** where a user finds their saved
options again. Raised in `docs/PHASE_7_NOTES.md` — saving that cannot be found
is half a feature.

## 19. `/app/products/:productVersionId` before product versions exist

`docs/03_FRONTEND_ARCHITECTURE.md` section 2 and
`docs/08_API_CONTRACTS.md` section 5 both address products by
`productVersionId`. Product versions arrive in Phase 8, so the route and
endpoint currently carry a synthetic product reference. Same shape as issue 17
for comparisons; both become version ids together.

## 20. `product_versions` has no record of *who* verified it — Phase 8

`docs/05_DATA_MODEL.md` section 4 gives `product_versions` a `verified_at` but
no verifier. "Manually verified" is a claim about a human action, and a claim
nobody's name is attached to is not verification.

**Resolved by adding** a NOT NULL `verified_by`, which the importer requires.
Please confirm you want it, and what it should hold — a name, an email, or an
internal identifier.

---

## Resolved in Phase 0

### Repository shape

`docs/00_README.md` suggests `docs/PRODUCT_SPEC.md` (unnumbered) nested inside
an `insurance-app/` directory. The specification files were moved into `docs/`
**keeping their numbered filenames**, so the prescribed reading order survives,
and the redundant `insurance-app/` wrapper was dropped because the repository
root already is that root. Approved before implementation.

### Worker placement

`docs/00_README.md` puts `worker/` at the top level; `docs/04_BACKEND_ARCHITECTURE.md`
describes a modular monolith whose worker needs the same domain code as the
API. Resolved as a top-level `worker/` package with an editable path
dependency on `backend/`, so there is no duplicated domain layer. Approved
before implementation.

## Resolved in Phase 1

### Palette contrast

`docs/02_UX_UI_SPEC.md` section 2 asks for contrast validation before the
tokens are finalised. Measured; two constrained usages resulted
(`--attention` as icon-only on its own tint, and a derived `--control-border`
for interactive boundaries). Full results and the two decisions left open for
the founder are in `docs/PHASE_1_NOTES.md`. No specification file was edited.

## Resolved in Phase 2

### Session and magic-link lifetimes

Not fixed anywhere in the specification. Implemented as configuration
(`MAGIC_LINK_TTL_MINUTES`, `SESSION_TTL_DAYS`) with documented defaults rather
than hard-coded values, and raised as an open question in
`docs/PHASE_2_NOTES.md`.

### How beta invites are issued

The specification says access is invite-only but not how an invite is created.
Implemented as the smallest mechanism that works — a configured address list
applied by an operator running `make seed-allowlist` — and flagged for a
product decision rather than guessed at.

## Resolved in Phase 3

### Advertising destinations that are not built

`docs/02_UX_UI_SPEC.md` section 5 specifies three product cards on the
new-user home, but none of their flows exist before Phase 4, and
`docs/12_BETA_CHECKLIST.md` requires no dead buttons. Resolved by rendering
every card as specified while showing its action only once the flow works,
driven by per-feature configuration. Motor stays off by default per open
item 8. Details in `docs/PHASE_3_NOTES.md`.

## Resolved in Phase 4

### "Find my matches" before matching exists

`docs/01_PRODUCT_SPEC.md` section 2.4 specifies "Find my matches" as the
review action, but the matching engine is Phase 9. The button reads "Save my
answers" until matching exists; the specified wording is already wired behind
a flag and appears the moment Phase 9 lands. Promising matches the product
cannot produce would be an unsupported UI claim.

### Seeding questions against an open decision

Open item 6 leaves question wording undecided. The seeded set is marked
`DRAFT` and draws every field from the candidate lists the specification
already provides, rather than inventing new ones. It still needs the founder's
wording pass — see `docs/PHASE_4_NOTES.md`.

## Resolved in Phase 5

### A recommendation experience before the recommendation engine

Phase 5 asks for the results UX before the engine that produces real
matches. Handled by making the prototype nature unmissable: fictional insurer
names, no premium at all, a persistent "Demo products" notice, no overall
score, and a run that records `prototype-ordering-001` as what produced it.
Each constraint is enforced by a test. See `docs/PHASE_5_NOTES.md`.

### Showing a price for a synthetic product

`docs/12_BETA_CHECKLIST.md` requires every displayed premium to carry a state,
source and timestamp; `CLAUDE.md` forbids inventing a premium. Resolved by
carrying no price and rendering an explicit "No price available" state that
says why. Raised as an open question — a labelled synthetic price would let
the price UI be tested, but that is the founder's call.

## Resolved in Phase 6

### Ranking differences without producing a score

The comparison must lead with the biggest differences, but any visible
"difference size" would be a score by another name — which
`docs/01_PRODUCT_SPEC.md` section 2.5 rules out. Resolved by using the spread
between fit labels for ordering only and never serialising it. Enforced by a
test.

## Resolved in Phase 7

### Source links for data that has no source

`docs/01_PRODUCT_SPEC.md` section 2.8 requires every technical item to support
"View source wording", but synthetic products have no policy document, and a
fabricated citation is release-blocking. Resolved by keeping the control on
every fact and having it state plainly that no source exists and why. The
control is deliberately not hidden: hiding it would hide the fact that nothing
is verified.

### Examples with figures, on products that carry no figures

Resolved by separating the two: an example is a labelled hypothetical about
policies in general, never a statement about this product. Product facts still
carry no figures. See `docs/PHASE_7_NOTES.md`.

## Resolved in Phase 8

### Requiring a quote method with no partner to quote from

`docs/04_BACKEND_ARCHITECTURE.md` section 3 requires `get_quote` on the
provider interface; open item 5 leaves the partner undecided. Resolved by
having every implementation raise rather than return a placeholder: an
estimate, a range or a stub would be an invented premium, which `CLAUDE.md`
forbids. Failing loudly means a caller cannot ship a fabricated number by
accident.

### Freshness windows

Neither the verification window (how long a verified fact stays usable) nor
the indicative-price window is fixed anywhere in the specification. Both are
configuration with documented defaults — 180 and 30 days — and raised in
`docs/PHASE_8_NOTES.md` as product decisions.
