# UX / UI Specification

## 1. Design direction

**Premium minimal + human warmth**

The product should communicate:

- quiet confidence;
- clarity;
- transparency;
- intelligence;
- safety;
- control.

It should not look like a traditional insurance marketplace.

---

# 2. Visual system

## Colors

Starting tokens:

```css
--bg: #F7F7F4;
--surface: #FFFFFF;
--text-primary: #171717;
--text-secondary: #676767;
--border: #E7E7E2;

--accent: #4856D6;
--accent-soft: #EEF0FF;

--positive: #17795D;
--positive-soft: #EAF7F2;

--attention: #A56500;
--attention-soft: #FFF5DD;

--critical: #B42318;
--critical-soft: #FDEDEC;
```

Validate contrast before finalizing.

## Typography

Use a neutral modern sans.

Preferred character:

- high legibility;
- excellent numerals;
- restrained;
- modern.

Suggested class:

- Geist / Inter-like.

Do not introduce multiple decorative fonts.

## Type scale

Approximate:

```text
Hero desktop        48–64
Hero mobile         36–44
H1                  36–44
H2                  28–32
H3                  20–24
Body                16–18
Support             14
Metadata            12–13
```

## Shape

- card radius: ~12–16px;
- subtle border;
- restrained shadows;
- avoid pill-shaped everything.

## Motion

Purposeful only:

- 160–240ms;
- question transition;
- expand/collapse;
- result reordering;
- processing status.

No decorative motion loops.

---

# 3. UX rules

## Rule 1 — Simple answer first

Information hierarchy:

```text
Human answer
↓
Why it matters to this person
↓
Example
↓
Technical detail
↓
Source wording
```

## Rule 2 — One primary question per onboarding screen

Do not create form walls.

## Rule 3 — Explain sensitive questions

Every sensitive field can expose:

> Why we're asking this

## Rule 4 — Show weaknesses

Every policy detail needs:

> What to watch out for

Trust requires discussing disadvantages.

## Rule 5 — No fake certainty

Use:

- "matches this priority"
- "needs verification"
- "not found in the source"

rather than pretending all facts are equally certain.

---

# 4. Navigation

Desktop:

```text
Logo
Find Insurance
My Recommendations
My Policies
Help
Profile
```

Mobile:

```text
Home
Recommend
Policies
Profile
```

---

# 5. New-user home

Hero:

> **Insurance should make sense before you need it.**

Supporting copy:

> Tell us what matters to you and understand which options fit — or upload the cover you already have and see what it really means.

Primary product cards:

### Health Insurance

> Find health insurance based on what matters to you.

### Motor Insurance

> Find cover based on your vehicle, use, and priorities.

Existing-policy card:

> Already have insurance? Understand your existing policy.

---

# 6. Returning home

Top:

### Continue where you left off

Only show an action if relevant.

Then:

- Recommendations
- Uploaded Policies
- Active Claims Checklist if present
- Household Profile
- Vehicles if relevant

Do not render empty irrelevant modules.

---

# 7. Onboarding

Use:

- subtle top progress bar;
- stage name.

Stages:

```text
About you
Your cover
What matters
Review
```

Example screen:

```text
[Progress]

Your cover

Who are you looking to protect?

[ Just me ]
[ Me + spouse ]
[ Me + family ]
[ My parents ]

Why we're asking this
Ask a question

Back                         Continue
```

---

# 8. Results

Top:

> What we learned about you

Then:

> Matched options

Primary view: 5.

Action:

> See 5 more matches

Card density: medium.

Card content:

```text
Insurer + Product
3 strongest fit areas
1 watch-out
price state if reliable
Why this matches
Compare
View details
```

---

# 9. Priority editor

During onboarding:

choose top 3.

Results page:

fine-tune.

Do not expose raw weights.

Use understandable controls such as:

```text
Less important
Normal
More important
Must have
```

or a compact priority-order editor.

Any changed priority should visibly explain why results changed.

---

# 10. Comparison

Max 3.

First show:

> Biggest differences

Then:

> Your priorities

Then:

> All details

Avoid giant feature matrices.

---

# 11. Policy detail

Above fold:

```text
Insurer + product
short personalized fit statement
3 fit highlights
1 trade-off
Compare
Save
```

While user is evaluating:

Primary CTA:

> Compare this policy

When user explicitly indicates decision readiness:

Primary CTA may become:

> Continue to official insurer / partner

---

# 12. Decoder

Desktop:

```text
65% report / 35% assistant
```

Left:

- decoder sections;
- source links.

Right:

- policy Q&A;
- citations.

Mobile:

- full-width report;
- Ask about this policy opens a sheet/full screen.

---

# 13. Upload

Short intro.

Large but restrained upload zone.

Show:

- supported file type;
- filename;
- size;
- remove;
- analyze.

Privacy line:

> Your policy is stored privately and is only used to generate your analysis.

Only use this copy if implementation supports it.

---

# 14. Processing

No fake percentages.

Use stages.

Allow leave/return.

If extraction fails:

say clearly what failed and what the user can do.

---

# 15. Responsive rules

- mobile-first questionnaire;
- minimum touch targets ~44px;
- no horizontal comparison tables on phone;
- one clear sticky action where useful;
- preserve context when opening AI help;
- source clauses must remain readable on mobile;
- use sheets for secondary controls.

---

# 16. Accessibility

Required:

- semantic HTML;
- keyboard navigation;
- form labels;
- visible focus;
- sufficient contrast;
- status not communicated only by color;
- screen-reader-friendly loading/status messages;
- reduced-motion respect;
- clear error association.
