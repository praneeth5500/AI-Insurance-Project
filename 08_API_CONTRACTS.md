# API Contracts

These are initial contracts. Use `/api/v1`.

---

# 1. Auth

## POST /api/v1/auth/request-magic-link

Request:

```json
{
  "email": "user@example.com"
}
```

Response should be generic.

Do not reveal allowlist membership unnecessarily.

## POST /api/v1/auth/verify

Implementation may be handled by auth provider depending on chosen adapter.

---

# 2. Me

## GET /api/v1/me

```json
{
  "id": "usr_...",
  "email": "user@example.com",
  "hasProfile": true,
  "betaAccess": true
}
```

---

# 3. Questionnaire

## POST /api/v1/questionnaire-sessions

```json
{
  "domain": "HEALTH"
}
```

## GET /api/v1/questionnaire-sessions/{id}

Returns:

- session;
- current stage;
- answers;
- next visible question.

## PUT /api/v1/questionnaire-sessions/{id}/answers/{questionId}

```json
{
  "value": "..."
}
```

## POST /api/v1/questionnaire-sessions/{id}/complete

Validates required inputs.

---

# 4. Recommendation

## POST /api/v1/recommendation-runs

```json
{
  "questionnaireSessionId": "qs_..."
}
```

Response:

```json
{
  "runId": "rr_...",
  "status": "PROCESSING"
}
```

## GET /api/v1/recommendation-runs/{runId}

Returns:

```json
{
  "id": "rr_...",
  "status": "READY",
  "decisionProfile": {},
  "matches": [],
  "canShowMore": true,
  "presentationMode": "BETA_MATCH_SET"
}
```

## PATCH /api/v1/recommendation-runs/{runId}/priorities

Request:

```json
{
  "priorities": [
    {"factor": "copay", "level": "HIGH"},
    {"factor": "waiting_period", "level": "HIGH"}
  ]
}
```

Return recalculated draft/match set.

---

# 5. Product detail

## GET /api/v1/product-versions/{id}

Return only verified fields.

Include source/provenance metadata.

---

# 6. Comparison

## POST /api/v1/comparisons

```json
{
  "recommendationRunId": "rr_...",
  "productVersionIds": ["pv_1", "pv_2", "pv_3"]
}
```

Reject more than 3 in beta.

---

# 7. Policy upload

## POST /api/v1/policies/uploads

Returns presigned/private upload instructions or upload session.

## POST /api/v1/policies

Create processing record after successful upload.

## GET /api/v1/policies/{policyId}

Returns status and metadata.

## DELETE /api/v1/policies/{policyId}

Delete user-owned policy data according to retention/deletion behavior.

---

# 8. Policy analysis

## GET /api/v1/policies/{policyId}/report

Returns decoder sections with facts and citations.

## GET /api/v1/policies/{policyId}/source/pages/{page}

Authorized source access.

---

# 9. Policy Q&A

## POST /api/v1/policies/{policyId}/questions

```json
{
  "question": "Does this policy have a room-rent limit?"
}
```

Response:

```json
{
  "answer": "...",
  "status": "SUPPORTED",
  "citations": [
    {
      "page": 12,
      "clauseId": "cl_..."
    }
  ],
  "uncertainty": null
}
```

Possible status:

```text
SUPPORTED
PARTIAL
NOT_FOUND
UNSAFE_TO_CONCLUDE
```

---

# 10. Claims readiness

## POST /api/v1/policies/{policyId}/claims-readiness

Create or return checklist.

## PATCH /api/v1/claims-readiness/{sessionId}/items/{itemId}

Mark completed / add note.

---

# 11. Feedback

## POST /api/v1/feedback

```json
{
  "contextType": "RECOMMENDATION",
  "contextId": "rr_...",
  "rating": 4,
  "comment": "..."
}
```

---

# 12. Error shape

Use one error format:

```json
{
  "error": {
    "code": "POLICY_PROCESSING_FAILED",
    "message": "We couldn't read this policy.",
    "retryable": true,
    "requestId": "req_..."
  }
}
```

Do not expose internal stack traces.
