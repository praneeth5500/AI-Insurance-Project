# Phase 13 — Policy Q&A

## What this phase changed

A reader can ask questions about their own uploaded policy and get answers
drawn only from that document, each one showing the wording it came from.

This is the highest-risk surface in the product. It is conversational, so it
reads as authoritative, and it is about money someone may be counting on.
`docs/07_POLICY_DECODER_AI.md` section 9 lists what it must never do, and most
of the design below is about making those prohibitions structural rather than
matters of good behaviour.

## The flow, and where the safety lives

`docs/07_POLICY_DECODER_AI.md` section 7:

```text
question -> retrieve clauses -> check evidence is sufficient
  -> answer from that evidence -> attach citations
```

The **sufficiency check between retrieval and generation** is the load-bearing
step. A model handed weak evidence will still write a confident paragraph, so
the question has to be recognised as unanswerable *before* anything tries to
answer it. A test asserts the model is never even consulted for a question
that failed retrieval.

## Decisions and why

### Retrieval is deterministic term scoring, not embeddings

Three reasons, in order of importance:

1. **The same question must produce the same citations.** A reader who
   re-phrases nothing and asks again should not get different evidence.
2. **It is inspectable.** When retrieval picks the wrong clause you can see
   which words did it. That is not true of a vector, and it matters for a
   system whose errors are about someone's insurance.
3. An embedding service is another undecided vendor.

Scoring is idf-weighted overlap, so terms that appear in every clause of every
policy — "policy", "insured", "cover" — contribute nothing. Without that, the
top result for any question would be whichever clause is longest.

### Without a model, the assistant quotes instead of paraphrasing

No provider is chosen (open item 2). Rather than disabling the feature, the
assistant finds the relevant clauses, shows the wording, cites the pages, and
**says outright that it is quoting rather than explaining**. The reader is told
this before they type, not after they read an answer and wonder why it sounds
like a photocopier.

That is less fluent than a generated answer and completely grounded. When a
provider arrives the same retrieval and the same sufficiency check run first,
and the model only ever sees clauses that passed them — a model handed nothing
but retrieved wording cannot invent a clause.

### Three refusals, not one

* **Insufficient evidence** — the specification's wording verbatim, plus the
  "suggest what to check next" section 7 requires.
* **Too broad** — new, and not in the specification. "What is covered?" is one
  of the most natural questions a reader asks and is genuinely unanswerable by
  retrieval, because every clause of every policy is about what is covered.
  Answering it with the section 7 refusal would *mislead*: it would say the
  policy is silent on something it addresses everywhere. So it says the
  question is broad, names specific things that will work, and points at the
  report, which already answers it section by section.
* **Unavailable** — the model is down or absent. The reader still gets their
  policy's wording; losing the explanation is a degradation, losing the answer
  would not be.

### A conversation cannot leave its policy

`conversations.policy_id` is NOT NULL and every route is scoped to a policy.
`docs/01_PRODUCT_SPEC.md` section 5 keeps Q&A inside policy context; an
endpoint that answered without one would quietly become a general chatbot.

### Prohibitions are enforced by construction

No code path produces a claim outcome, an insurer's behaviour, a premium or a
legal interpretation, because every answer is assembled from clause text plus
fixed framing. The single judgement the assistant makes is *which clauses are
relevant*, and it shows its working by citing them.

## A defect this phase caught

Conversation history came back in the wrong order. Both the question and the
answer are written in one transaction, and `created_at` defaults to `now()` —
which in PostgreSQL is *transaction start time*, identical for both. Ordering
fell through to the random id.

Fixed with an explicit `ordinal` per conversation rather than by nudging
timestamps. Any two rows written in one transaction have this problem;
a timestamp is not a sequence.

## Verification

Backend: 23 new tests (358 total) — retrieval determinism, common words not
deciding relevance, the model never consulted after a failed sufficiency check,
each of the three refusals, an outage still producing wording, citations on
every grounded answer, cross-user refusal, and a policy that is not ready being
unquestionable.

Frontend: 10 new tests (211 total).

Browser: 19 checks against the real stack. A PDF uploaded through the UI,
processed by the worker, then three real questions asked through the assistant —
one answered from the policy with a page citation, one refused as unanswerable,
one told it was too broad — plus the desktop 65/35 split and mobile layout.

## Two harness mistakes worth recording

Both cost time and neither was a product defect:

* I rebuilt the frontend without `NEXT_PUBLIC_API_BASE_URL`, which is inlined
  at build time. The browser then posted to `localhost:8000` while the page
  was on `127.0.0.1:3000`, so the session cookie landed on a different host
  and every sign-in bounced. This is the exact trap recorded in
  `docs/PHASE_2_NOTES.md` — worth re-reading before any manual verification.
* The API process predated the Q&A router, so `/questions` returned 404 and
  the assistant silently did not render. The page degrades to report-only when
  the conversation fails to load, which is correct behaviour and also very
  good at hiding a stale server.

## Open questions

1. **No model provider** (open item 2). Until one is chosen the assistant
   quotes rather than explains. It is useful — it finds the right clause and
   shows it — but it is not the product the specification describes.
2. **Retrieval is single-turn.** "What about for my spouse?" is not understood
   as following the previous question. Multi-turn retrieval needs the model.
3. **The stopword list is domain judgement** and unreviewed. It decides which
   questions are answerable, which is more consequential than it looks.

## Definition of done

| Item | Status |
|---|---|
| Retrieval | ✅ deterministic, inspectable, idf-weighted |
| Grounded answer | ✅ quoted today, generated behind the same interface |
| Citations | ✅ clause, page and wording on every grounded answer |
| Insufficient-evidence response | ✅ the specified wording, plus what to try next |
| AI unavailability handling | ✅ still answers with the policy's wording |
