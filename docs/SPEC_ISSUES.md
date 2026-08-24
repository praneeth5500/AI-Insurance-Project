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
