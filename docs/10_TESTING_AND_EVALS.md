# Testing & Evaluation

## 1. Standard testing

Required:

- unit;
- integration;
- API;
- authorization;
- E2E;
- upload security;
- responsive;
- accessibility;
- regression.

---

# 2. Critical E2E flows

## Auth

```text
allowlisted email
→ magic link
→ session
→ home
```

## Health recommendation

```text
home
→ health
→ questionnaire
→ review
→ generate
→ matched options
→ open match
→ compare
→ change priority
→ see updated result
```

## Policy decoder

```text
home
→ upload
→ processing
→ report
→ ask question
→ open citation
→ claims checklist
```

## Data deletion

```text
upload policy
→ delete
→ verify file inaccessible
→ verify records removed/anonymized as designed
```

---

# 3. Recommendation engine tests

Create synthetic personas.

Examples:

### Persona A

- young salaried user;
- employer cover;
- low co-pay high priority.

Expected:

- ineligible products excluded;
- co-pay-heavy products penalized;
- priority change deterministically affects ordering.

### Persona B

- parent-focused profile.

Expected:

- age eligibility correctly applied;
- unsupported family configuration excluded.

Test:

- same input → same structured result;
- LLM outage does not change score;
- stale critical product data excludes product;
- unknown critical data not silently treated as average.

---

# 4. Policy decoder golden set

Maintain manually verified policies/fixtures.

For each:

- expected clause;
- expected fact;
- expected page;
- allowed variants.

Test:

- sum insured;
- co-pay;
- deductible;
- waiting periods;
- room rules;
- sub-limits;
- exclusions;
- claim clauses.

---

# 5. Q&A eval categories

- simple factual;
- multi-clause;
- ambiguous;
- missing information;
- adversarial;
- misleading premise;
- claim-guarantee request;
- medical/legal overreach.

Expected behavior:

- answer when supported;
- cite source;
- say uncertain when uncertain;
- refuse definitive unsupported conclusion.

---

# 6. UX beta metrics

Track:

- onboarding completion;
- time to results;
- edit-answer rate;
- priority-adjustment rate;
- match-detail open rate;
- compare usage;
- source-citation open rate;
- decoder completion;
- Q&A helpfulness;
- reported comprehension;
- reported trust;
- confusion feedback;
- processing failure rate.

---

# 7. Beta feedback questions

After recommendation:

1. Did the result make sense?
2. Did you understand why each option matched?
3. Was anything important missing?
4. Did any explanation feel misleading?
5. Did the watch-outs change your thinking?
6. How confident are you now compared with before?
7. What would you do next?

After decoder:

1. Did you learn something new about your policy?
2. Was any explanation confusing?
3. Did the source wording increase trust?
4. What question could the product not answer?
5. Would you use this before a claim?

---

# 8. Release-blocking issues

Do not invite more beta users while unresolved:

- cross-user data access;
- public file exposure;
- wrong user document displayed;
- recommendation inconsistency for identical structured input;
- fabricated policy fact;
- fabricated source citation;
- price shown without provenance/state;
- critical health/policy data leaked to logs.
