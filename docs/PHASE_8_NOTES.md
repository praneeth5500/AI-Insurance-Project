# Phase 8 — Real Data Domain Layer

Implementation notes for `docs/11_BUILD_PLAN.md` Phase 8.

## Definition of done

Phase 8 has **no "Done when" section** — the sixth in a row. Held to the build
list plus `CLAUDE.md`'s definition of done:

| Requirement | Status | Evidence |
|---|---|---|
| Canonical product model | ✅ | `insurers`, `insurance_products`, `product_versions`, `product_facts` per `docs/05_DATA_MODEL.md` §4 |
| Product versioning | ✅ | Terms are identified by version label; a change is a new version, never an edit |
| Provenance | ✅ | `source_type`, `source_name`, `source_reference`, `verified_at`, `verified_by` — all NOT NULL |
| Price state | ✅ | `product_prices` per §5, plus the rules that decide whether a price may be shown |
| Manual verified-data importer | ✅ | `make import-products`, validated end to end against a real database |
| Partner adapter interface | ✅ | `InsuranceProductProvider` per `docs/04_BACKEND_ARCHITECTURE.md` §3, two implementations |
| Types / tests | ✅ | 208 backend tests (was 172), mypy strict, lint and format clean |

## "Do not scrape random websites into production data"

That sentence is the whole point of the phase, so it is enforced in code
rather than left as guidance. Nothing reaches the canonical catalogue without:

* a `sourceType` of `MANUALLY_VERIFIED` or `PARTNER_API` — **`SYNTHETIC` is
  refused outright**, so a demo product cannot be laundered into the real
  catalogue;
* a **source name** and a **source reference** — *which document, and where in
  it*;
* a `verifiedAt` that is not in the future;
* a **`verifiedBy`** — the person who checked it.

`verifiedBy` is not in `docs/05_DATA_MODEL.md`. I added it because "manually
verified" is a claim about a human action, and a claim nobody's name is
attached to is not verification. Recorded in `docs/SPEC_ISSUES.md`.

Two further guards:

* **Unknown fields are rejected, not ignored.** A typo in `verifiedBy` fails
  the import rather than silently dropping the value and writing a version
  that looks verified.
* **The whole file is validated before anything is written.** One bad record
  means nothing is imported, rather than a half-loaded catalogue.

### The template cannot be imported

`backend/examples/products.template.json` ships full of `REPLACE_ME`, and the
importer refuses any value containing a placeholder marker. So the template
demonstrates the required shape but cannot become a catalogue of placeholders
by being run as-is. A test asserts the shipped template fails validation.

## Decisions taken

### Stale data is excluded, never downgraded

`docs/13_DECISIONS_AND_OPEN_ITEMS.md` decides it and
`docs/06_RECOMMENDATION_ENGINE.md` §4 makes it a *hard* failure: a product with
stale or missing critical data leaves the match set rather than scoring badly.
`freshness.py` returns a reason (`VERIFICATION_STALE`, `CRITICAL_FACT_MISSING`,
`SUPERSEDED`, …) rather than a boolean, so the engine can explain an exclusion
in Phase 9 instead of a product silently vanishing.

A missing critical fact is deliberately **not** a low score — §8 forbids
turning unknown into a neutral value.

### A price is a state, never a number

`docs/05_DATA_MODEL.md` §5 ends with "Never display a price record without
source/status/timestamp". The cheapest way to keep that promise is to make a
row without them impossible: `status`, `source_type`, `source_name` and
`generated_at` are all NOT NULL.

`pricing/service.py` then answers one question — *is this price safe to put on
a screen?* — and returns either a `DisplayablePrice` carrying everything the
checklist requires, or a `SuppressedPrice` with a reason. There is no path
that yields a bare number. Four rules from `docs/12_BETA_CHECKLIST.md` fall out
of that:

* an expired quote is not shown;
* an indicative figure older than the window is not shown (**an old estimate
  is worse than none: it looks current**);
* an unrecognised state is never guessed at;
* an indicative figure is labelled "Indicative premium" with "the amount you
  are actually offered can differ" — never described as final.

Unknown tax and fee status stays `None` and is shown as unknown, rather than
being assumed either way.

### `get_quote` raises in every implementation

`docs/04_BACKEND_ARCHITECTURE.md` §3 requires the method; open item 5 says no
partner is chosen. Both providers raise `QuoteNotAvailableError`.

Returning an estimate, a range or a placeholder would be inventing a price,
which `CLAUDE.md` forbids outright — so the method fails loudly instead. A
caller cannot accidentally ship a fabricated number.

### The synthetic catalogue is behind the same interface, and stays separate

`SyntheticCatalogueProvider` exposes the Phase 5 demo products through
`InsuranceProductProvider`, so the seam is real and Phase 9 reads products
through a provider rather than a fixture. It never writes to the canonical
tables: a demo product and a verified one live in different places, by
construction.

### Amounts are stored in the smallest unit

`product_prices.amount` is paise, so no rounding is introduced by us. The
formatting decision belongs to the screen, not the database.

## Open questions for the founder

1. **The freshness window is 180 days.** Not fixed anywhere in the
   specification, so it is configuration with a documented default. It decides
   when a verified fact stops being usable and a product drops out of
   matching — genuinely a product decision. Insurance terms change; six months
   felt defensible, but it is your call.
2. **The indicative-price window is 30 days**, same reasoning.
3. **`verifiedBy` is an addition** to `docs/05_DATA_MODEL.md` §4. Confirm you
   want it, and confirm what it should hold — a name, an email, an internal id.
4. **Nothing is imported yet.** The tables are empty and the beta still runs on
   synthetic products. Importing real verified data is a deliberate act, and
   whose data, and when, is yours to decide.
5. Still open: saved options on the home screen (Phase 7), labelled synthetic
   prices (Phase 5), question wording (open item 6), session lifetimes, invite
   issuance, the unthrottled magic-link endpoint, `/design-system` being
   public, and analytics timing (issue 12).

## Deliberately not done

| Not built | Why |
|---|---|
| Rewiring the recommendation engine onto the provider | Phase 9 does that, and says explicitly: "Start with synthetic + manually verified fixtures". |
| A real partner adapter | Open item 5. The interface is fixed; the vendor is not. |
| Product data in the beta | The canonical tables ship empty. Real data is a decision, not a default. |
| An admin UI for imports | The CLI is the smallest thing that works and keeps import a deliberate, reviewable act. |

## Verification performed

208 backend tests, plus the importer exercised end to end against a real
database through the actual `make` target:

1. importing the **shipped template** → refused, naming every placeholder;
2. a filled-in file → 1 version, 2 facts written;
3. re-importing the same file → **0 inserted, 1 re-verified**, still 2 facts —
   idempotent, no duplicates;
4. a file with `verifiedBy` removed → refused, nothing written;
5. the database confirms one insurer, one product, one version with
   `MANUALLY_VERIFIED` provenance, a named verifier and two facts.

Front-end tests (177) still pass unchanged: this phase adds a domain layer and
touches no screen.

## Next phase

Phase 9 — Matching Engine: hard eligibility, fit evaluators, priority
weighting, scoring version, immutable recommendation runs and the explanation
evidence object, starting from synthetic and manually verified fixtures. AI
explanation only after the structured output is correct.
