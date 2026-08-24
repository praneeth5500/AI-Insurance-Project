# Decisions & Open Items

## Approved decisions

### Product

- Two modules: recommendation + existing-policy intelligence
- Invite-only beta
- Health + Motor product direction
- Health first as full recommendation flow
- Existing policy decoder on home
- Policy Q&A
- Claims-readiness explanation + checklist

### Recommendation UX

- Adaptive questionnaire
- Hybrid structured flow + optional AI help
- Cards/buttons as primary input
- No fixed question count
- Stage name + subtle progress
- Short review before matching
- What we learned about you before results
- 5 primary matched options
- See 5 more
- Up to 3 in comparison
- No visible overall numeric fit score
- Category-level fit
- User chooses Top 3 priorities
- Fine-tuning after results
- AI does not calculate ranking
- User priority changes trigger deterministic recalculation
- Historical recommendation runs immutable

### Decoder UX

- PDF + scans
- Short upload introduction
- Visible processing stages
- User can leave/return
- Desktop report left + assistant right
- Claims-readiness checklist
- Source-linked Q&A

### Visual

- Premium minimal + human warmth
- Warm off-white surfaces
- Deep graphite text
- Restrained indigo/cobalt accent
- Modern neutral sans typography
- Limited abstract/product visuals
- No stock insurance imagery
- Dark mode deferred
- Voice deferred

### Engineering

- Next.js + React + TypeScript
- FastAPI + Python
- PostgreSQL
- Private S3
- Async worker
- Provider adapters
- Modular monolith
- Email allowlist + passwordless magic link

### Truth/safety

- Critical stale product data excluded
- Cached fallback only inside freshness window
- Price states: indicative / quoted / final
- Never invent a premium range
- Never guarantee a claim
- Never silently guess missing policy facts

---

# Open items

These are intentionally **not decided** yet.

## 1. Exact auth provider

Required behavior is decided.
Vendor is not.

## 2. Exact LLM provider/model

Architecture must remain replaceable.

## 3. Exact OCR provider

Native PDF first.
OCR fallback required.

## 4. Exact queue implementation

AWS SQS is a good production-beta direction.
Local adapter still needed.

## 5. Insurance partner / aggregator API

Not chosen.

Until ready:

- synthetic data for UI;
- manually verified data for controlled real-product testing.

## 6. Final health questionnaire questions

The structure is decided.
Exact question wording/data fields still need a dedicated pass.

## 7. Exact health evaluator rules

The dimensions are decided.
The product-specific normalization rules require implementation + review.

## 8. Motor recommendation timing

Architecture supports it.
Do not enable until health engine and motor data are ready.

## 9. Public monetization

Not part of this beta.

## 10. Public purchase flow

Not part of the current build requirement.

---

# Do-not-invent list for Claude

If the project lacks a decision for any of these, stop and flag it:

- insurer API credentials;
- actual insurer/product data;
- actual premium;
- final quote;
- medical underwriting outcome;
- hospital network completeness;
- claim approval;
- legal interpretation;
- exact product eligibility when no source exists;
- production retention period;
- public monetization behavior.

Use mocks/interfaces instead of guessing.
