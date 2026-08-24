# Product Specification

## 1. Product goal

Build an invite-only web application that helps users understand insurance decisions and existing policies.

### Core promise

> **Understand first. Choose confidently.**

### Beta learning goal

The beta is primarily about product learning, not maximizing sales.

We want to learn whether users:

- understand the questions;
- trust the matching logic;
- understand category-level fit;
- find policy explanations useful;
- discover information they did not previously understand;
- use comparison;
- adjust priorities;
- trust source-linked answers;
- return to saved recommendations/policies.

---

# 2. Module 1 — Guided Insurance Matching

## 2.1 Entry

Home presents separate cards:

- Health Insurance
- Motor Insurance

Health is the first full recommendation domain.

Motor is supported architecturally and may be enabled after health beta stability.

## 2.2 Health onboarding

Adaptive, structured flow.

Stages:

```text
About you
Your cover
What matters
Review
```

Question types primarily:

- choice cards;
- buttons;
- segmented controls;
- simple numeric/text inputs where required.

AI help is contextual and optional.

### Candidate inputs

Only collect fields that change eligibility, match, or explanation.

Possible health fields:

- who is being protected;
- member ages;
- city/pincode;
- existing employer coverage;
- existing personal coverage;
- desired/baseline cover;
- approximate budget;
- broad health conditions only when necessary;
- room/hospital preference;
- co-pay tolerance;
- waiting-period sensitivity;
- user-selected priorities.

Do not collect detailed medical history by default.

## 2.3 Priority capture

During onboarding:

> Choose up to 3 things that matter most.

Candidate priorities:

- lower premium;
- low co-pay;
- short waiting periods;
- hospital flexibility;
- broad coverage;
- fewer sub-limits.

After results, users can fine-tune priorities.

## 2.4 Review

Before matching, show a short review.

User can edit each section.

Then:

> Find my matches

## 2.5 Results

First show:

### What we learned about you

A synthesis, not a raw form dump.

Then:

### 5 primary matched options

Each card:

- insurer/product;
- 3 strongest fit areas;
- 1 watch-out;
- premium state if reliable;
- Why this matches;
- Compare;
- View details.

Then:

> See 5 more matches

Total beta result set target: up to 10 matched options.

Do not show an overall 0–100 consumer score.

## 2.6 Category fit

Possible visible health fit categories:

- coverage;
- co-pay;
- waiting periods;
- hospital flexibility;
- network usefulness;
- sub-limits;
- exclusions/conditions;
- budget;
- user priorities.

Use labels such as:

- Strong
- Good
- Trade-off
- Needs attention
- Not enough verified data

Never rely on color alone.

## 2.7 Comparison

User can compare up to 3 policies.

Comparison prioritizes:

1. biggest meaningful differences;
2. user's top priorities;
3. all details afterward.

Mobile uses stacked differences, not a wide horizontal table.

## 2.8 Policy detail

Sections:

```text
Why this matches you
What to watch out for
Your Cover
Your Costs
Waiting Periods
Important Limits
Not Covered
Claims
Policy Details
Source Documents
```

Every technical item should support:

- Explain with example
- View source wording

## 2.9 Outbound continuation

For the early beta, this can remain disabled or use a controlled official/partner link when available.

The main product learning loop should not depend on checkout.

---

# 3. Module 2 — Existing Policy Intelligence

## 3.1 Entry

Home CTA:

> Understand my existing policy

## 3.2 Input

Support:

- PDF
- scanned PDF
- supported images/scans

Later:

- email import

## 3.3 Processing

Show stages:

```text
Uploading
Reading document
Finding important clauses
Building summary
Preparing Q&A
Ready
```

User may leave and return.

## 3.4 Decoder sections

```text
Your Cover
Your Costs
Before Cover Starts
Important Limits
Not Covered
At Claim Time
Policy Details
```

Each extracted fact includes source reference where possible.

## 3.5 Q&A

Desktop:

- report left;
- AI assistant right.

Mobile:

- report primary;
- AI opens full-screen/sheet.

Answer format:

```text
Answer
Why
Relevant clause
Page/section
Conditions/exceptions
What is uncertain
Safe next action
```

## 3.6 Claims readiness

Beta supports:

- explain claims-related clauses;
- build a personalized document/action checklist.

It does not predict guaranteed claim approval.

---

# 4. Users

Initial beta includes friends/family and selected invited users.

Health flows should eventually accommodate:

- first-time individual buyer;
- salaried employee with employer cover;
- family cover;
- parents.

Use one adaptive flow rather than four independent products.

---

# 5. Returning-user home

Top priority:

> Continue where you left off

Then conditionally show:

- saved recommendation sessions;
- uploaded policies;
- active claims checklist;
- household/profile summary;
- vehicles when relevant;
- privacy/settings.

Do not place isolated recent Q&A on the home screen.

Q&A stays inside policy context.

Full activity history is deferred.

---

# 6. Account

Beta:

- email allowlist;
- passwordless magic link;
- no password;
- no username.

Domain profile must be separate from auth identity.

One authenticated user may later manage:

- self;
- spouse;
- children;
- parents;
- multiple vehicles;
- multiple policies.

---

# 7. Pricing truth states

Never use one generic premium field.

Supported states:

```text
INDICATIVE
QUOTED
FINAL
```

### Indicative

Price returned before final underwriting/acceptance.

### Quoted

Formal quote with quote reference/validity.

### Final

Confirmed amount for issuance, only when genuinely available.

Do not invent price ranges.
Avoid misleading "from ₹X" on personalized results.
