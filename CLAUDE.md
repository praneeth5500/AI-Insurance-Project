# CLAUDE.md — Instructions for Claude Code

You are helping build an invite-only beta of an AI-assisted insurance decision platform.

## Product intent

This product should help users **understand before they choose**.

It must not feel like:

- an aggressive insurance marketplace;
- a generic AI chatbot;
- a legacy insurance portal;
- a dashboard full of unexplained numbers.

It should feel:

- calm;
- premium;
- simple;
- transparent;
- evidence-driven;
- human;
- trustworthy.

## Non-negotiable behavior

1. Never invent insurance facts.
2. Never invent a premium.
3. Never invent a claim outcome.
4. Never let the LLM generate the recommendation ranking.
5. Never let the LLM silently overwrite structured policy facts.
6. Never log raw policy documents or sensitive user answers unnecessarily.
7. Never expose uploaded files publicly.
8. Never make a UI claim that the backend cannot support.
9. Never silently use stale critical insurance data.
10. Never rewrite historical recommendation results after the fact.

## Product terminology

Prefer:

- "Matched options"
- "Strong match for this priority"
- "Why this matches you"
- "What to watch out for"
- "Indicative premium"
- "Quoted premium"
- "View source wording"

Avoid:

- "Best policy"
- "Guaranteed best"
- "You should buy this"
- "Claim guaranteed"
- "Final premium" unless actually confirmed
- fake rankings or fake insurer ratings

## Engineering principles

- TypeScript strict mode.
- Python type hints.
- Pydantic schemas at boundaries.
- Small feature-oriented modules.
- Modular monolith.
- Avoid premature abstractions.
- Avoid microservices.
- External services must sit behind adapters/interfaces.
- Database migrations are mandatory for schema changes.
- Critical domain rules require tests.
- AI structured output must be schema-validated.
- File processing must be asynchronous.
- A failed extraction must remain visibly failed/uncertain.

## Frontend principles

- Next.js + React + TypeScript.
- Mobile-first for questionnaire/recommendation.
- No giant comparison spreadsheets on mobile.
- One primary decision per onboarding screen.
- Progressive disclosure.
- Category fit over one overall score.
- Up to 3 policies in active comparison.
- Top 5 primary matched options; 5 more available.
- Accessibility is part of done.
- Loading, empty, error, and unavailable states are required.

## AI principles

Use AI for:

- explanation;
- policy language simplification;
- contextual help;
- document classification;
- structured extraction with validation;
- retrieval-grounded Q&A.

Use deterministic logic for:

- hard eligibility;
- preference weighting;
- ranking;
- stale-data rules;
- pricing state;
- policy version selection.

## Data provenance

Every product/policy fact used in the app should ideally know:

```text
source_type
source_name
source_reference
version
effective_date
verified_at
```

Allowed prototype provenance:

```text
SYNTHETIC
MANUALLY_VERIFIED
PARTNER_API
UPLOADED_POLICY
```

## Before implementing a feature

Read its relevant spec.

Then state internally:

- user problem;
- required data;
- happy path;
- error states;
- API contract;
- analytics event;
- tests.

Do not create undocumented behavior.

## Definition of done

A feature is done when:

- it satisfies the spec;
- types pass;
- tests pass;
- mobile works;
- keyboard/accessibility basics work;
- loading/empty/error states exist;
- analytics event exists where specified;
- no sensitive-data logging was introduced;
- documentation is updated.
