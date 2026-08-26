# Phase 11 — Document Extraction

## What this phase changed

The worker stopped being a placeholder. It now claims `PROCESS_POLICY` jobs,
fetches the document from private storage, reads it, cuts it into clauses and
extracts structured facts — each one carrying the page and the sentence it came
from.

The governing sentence for the whole phase is two words from
`docs/07_POLICY_DECODER_AI.md` section 4: **never guess.** Most of the design
below is a consequence of taking that literally.

## The three layers, kept apart

`docs/07_POLICY_DECODER_AI.md` section 3 asks for a source layer, a structured
fact layer and an explanation layer, and says explanation must never become the
source of truth. They are separate tables:

* `policy_pages`, `policy_clauses` — what the document says, verbatim.
* `policy_facts` — normalised values, each pointing at the clause that
  supports it.
* Explanation — **not stored at all.** It is generated for display in Phase 12
  and has nowhere to become authoritative.

`policy_facts.clause_id` is how a value earns the right to be shown. It is
nullable only so a NOT_FOUND fact can exist; every fact with a *value* has a
clause, and a test enforces that.

## Why extraction is deterministic

The specification anticipates a model doing this. No provider is chosen
(open item 2), and the build plan is explicit that AI comes *after* the
structured output is correct.

That is not a workaround for these particular facts. "How many months before
pre-existing conditions are covered" is a number printed in the document. A
pattern that finds it and quotes the sentence it came from cannot hallucinate,
and every value is checkable against the quote shown beside it. A model earns
its place on the harder half — clauses whose meaning is not carried by a
number — and will implement the same `FactExtractor` interface under the same
rule: a value arrives with its clause, or it is NOT_FOUND.

The extraction run records `ai_provider` as null rather than leaving it
ambiguous, so any run can answer "did a model touch this?".

## Decisions and why

### A scan fails loudly instead of producing an empty policy

No OCR provider is chosen (open item 3). `UnavailableOcrProvider` raises, and
the policy shows "reading scans isn't part of this beta yet". The alternative —
returning empty pages — would give the reader a policy whose every section is
blank, which they would reasonably read as *this covers nothing*. That is the
worst failure this system could produce, and it would look like a success.

### OCR is decided per page, not per document

A born-digital wording with a scanned endorsement stapled on the end is a real
shape. Native text is used where it exists; OCR is only consulted for pages
that yielded nothing, which is what section 11's "do not run OCR unnecessarily"
actually requires. When some pages are readable and some are not, the
unreadable ones are stored as empty with method `NONE` rather than dropped — a
missing page number would make every later citation lie.

### Conflicts are reported, not resolved

When two clauses give different answers for the same fact, the result is
`CONFLICTING` with every reading and its page attached. Picking a winner
silently is precisely the failure section 5's conflicting state exists to
prevent. Nothing automated may rely on a fact in that state.

### An implausible reading is discarded

A 600-month waiting period is a misread, not a policy term. Values outside
sane bounds are dropped rather than reported, because a wrong fact shown with
a confident citation is more damaging than no fact at all.

### Confidence is both a number and a state

`docs/SPEC_ISSUES.md` issue 2 recorded that the specification shows it both
ways. Both are stored: the number is what the extractor produced, the state is
what the UI may reason about, and the state is derived from the number plus
which clause the value was found in. A figure inside a clause titled "Waiting
Periods" is worth more than the same figure in a marketing paragraph.

### A permanent failure is not retried

A password-protected PDF will still be password-protected on the third
attempt. Retrying only delays telling the reader something they could act on
now, so `is_permanent()` decides, and the queue honours it.

### Nothing about the document is logged

Not its text, not its filename, not an exception's message. That is why
`ExtractionFailed` carries a named reason rather than a string, and why the
job's error field is bounded (`docs/09_AWS_DEPLOYMENT.md` section 9).

## A defect this phase caught

The end-to-end run initially produced **one** clause and every fact at MEDIUM
confidence. The cause was the test PDF fixture, which drew a whole page as a
single text-showing operator — so the extractor saw one long line, no headings,
and no sections to file facts under. Real PDFs place each line separately.

The fixture now lays out one operator per line, which is how a document is
actually shaped. The same policy then produced 5 correctly classified clauses
and 5 facts at HIGH confidence. Worth recording because the unit tests passed
throughout: they fed `ExtractedPage` objects directly and never exercised the
PDF-to-text boundary where the problem lived.

## Verification

Backend: 26 new tests (310 total) — native-before-OCR, a scan failing clearly,
OCR used when a provider exists, encrypted and corrupt PDFs, hyphenated line
breaks, heading classification and its refusal to guess, facts with citations,
NOT_FOUND, CONFLICTING, years normalised to months, implausible values
discarded, determinism, and a structural check that no model is imported.

End to end against the real database and the real worker: upload → queue →
claim → extract → 5 clauses → 5 facts with quotes → policy READY.

## Open questions

1. **No OCR provider** (open item 3). Until one is chosen, scans and photos
   are refused with an explanation. This is the single biggest gap in the
   decoder for real users — a lot of people only have a scan.
2. **The fact patterns are Indian-market shaped** — lakh and crore, "co-payment",
   "pre-existing diseases". They will need review against real wordings, and a
   golden set (section 12) built from documents you have permission to use.
3. **Six fact keys** is a deliberately small start. Everything the decoder
   sections want — restoration, day-care, network, sub-limits by treatment —
   is either a model's job or needs more patterns and review.

## Definition of done

| Item | Status |
|---|---|
| Native PDF extraction | ✅ per page, preferred over OCR |
| OCR adapter fallback | ✅ interface + honest refusal until a provider exists |
| Page model | ✅ text, method and coverage per page |
| Clause segmentation | ✅ deterministic, verbatim, page-attributed |
| Structured fact extraction | ✅ 6 facts, behind the interface a model will implement |
| Validation | ✅ bounds, confidence states, conflict detection |
| Citations | ✅ page + clause + the exact sentence |
