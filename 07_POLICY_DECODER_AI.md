# Policy Decoder & AI Specification

## 1. Goal

Turn an uploaded insurance policy into:

- structured facts;
- plain-language explanations;
- source-linked evidence;
- grounded Q&A;
- claims-readiness checklist.

The AI must remain anchored to the uploaded policy.

---

# 2. Processing pipeline

```text
Upload
↓
File validation
↓
Private storage
↓
Native PDF extraction
↓
OCR fallback for scan/image
↓
Page normalization
↓
Clause segmentation
↓
Structured extraction
↓
Validation
↓
Policy facts
↓
Retrieval index
↓
Decoder + Q&A
```

---

# 3. Three-layer truth model

Keep separate:

## Source layer

Original PDF/pages/clauses.

## Structured fact layer

Extracted normalized facts.

## Explanation layer

AI-generated plain-language explanations.

Never let explanation text become the source of truth.

---

# 4. Extraction contract

Use schema-constrained output.

Example:

```json
{
  "fact_key": "ped_waiting_period",
  "value": {
    "months": 36
  },
  "source": {
    "page": 14,
    "clause_title": "Waiting Periods",
    "text": "..."
  },
  "confidence": 0.96
}
```

If a fact is not found:

```json
{
  "fact_key": "ped_waiting_period",
  "value": null,
  "status": "NOT_FOUND"
}
```

Never guess.

---

# 5. Extraction confidence

Suggested states:

```text
HIGH
MEDIUM
LOW
NOT_FOUND
CONFLICTING
```

Critical facts with low/conflicting confidence should be highlighted for manual review or excluded from automated conclusions.

---

# 6. Decoder writing style

Explain technical language without hiding the technical term.

Pattern:

```text
Plain language title

What it means:
...

Example:
...

Important conditions:
...

Technical term:
...

Source:
Page X · Clause Y
```

---

# 7. Q&A retrieval

Question flow:

```text
User question
↓
Classify intent
↓
Retrieve relevant policy clauses/facts
↓
Check evidence sufficiency
↓
Generate answer from evidence
↓
Attach citations
```

If evidence is insufficient:

> I couldn't determine that from the policy you uploaded.

Then suggest what to check next.

---

# 8. Answer contract

Every material policy answer should contain:

1. concise answer;
2. why;
3. relevant clause;
4. page/section;
5. conditions/exceptions;
6. uncertainty;
7. safe next step if needed.

---

# 9. Prohibited AI behavior

Do not:

- promise claim approval;
- invent insurer behavior;
- invent medical eligibility;
- invent a missing clause;
- produce a premium from policy text unless it is explicitly present and current;
- give definitive legal interpretation;
- tell the user to ignore policy wording.

---

# 10. Claims readiness

Generate checklist items only from:

- relevant source clauses;
- approved general process templates;
- clearly labeled assumptions.

Separate:

```text
Policy-specific requirement
General preparation suggestion
Unknown / confirm with insurer
```

Do not blend them.

---

# 11. OCR

Support:

- native-text PDF first;
- OCR fallback for scanned pages.

OCR provider should be replaceable.

For AWS-first infrastructure, an AWS OCR adapter can be implemented later.

Do not run OCR unnecessarily on already extractable pages.

---

# 12. Evaluation

Maintain a golden set of test policies.

Manually verify facts.

Test:

- clause extraction;
- page citation;
- missing fact handling;
- conflicting clauses;
- low-quality scans;
- Q&A grounding;
- refusal/uncertainty behavior.
