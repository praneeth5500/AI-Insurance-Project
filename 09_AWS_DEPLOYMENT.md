# AWS / Deployment Specification

## Goal

Keep beta infrastructure simple, private, observable, and replaceable.

Do not over-engineer.

---

# 1. Recommended beta topology

```text
Browser
↓
Next.js frontend
↓
FastAPI API
↓
PostgreSQL

FastAPI
├── S3 private files
├── Queue
├── AI provider
├── OCR provider
└── Email/auth provider

Queue
↓
Python worker
↓
S3 + PostgreSQL + AI/OCR
```

---

# 2. Suggested deployment

A practical implementation:

### Frontend

- Vercel or equivalent managed Next.js hosting

### Backend

- AWS container hosting

### Database

- managed PostgreSQL

### Files

- AWS S3 private bucket

### Queue

- AWS SQS

### Worker

- Python container worker

### Monitoring

- CloudWatch plus application error monitoring if desired

### Email

- provider adapter; AWS SES is compatible with an AWS-centered stack

Exact vendor choice can be changed without domain rewrites.

---

# 3. Region

For the beta, prefer an AWS India region for backend data/storage if practical.

This is a product/security choice for the Indian target market, not a legal conclusion.

---

# 4. Environments

```text
local
preview
staging
production-beta
```

Do not use real customer data in local/preview.

---

# 5. S3

Requirements:

- block public access;
- server-side encryption;
- separate buckets/prefixes by environment;
- signed temporary URLs;
- lifecycle policy;
- deletion path;
- MIME validation before processing.

---

# 6. Database

Use managed PostgreSQL for beta.

Require:

- automated backups;
- encrypted storage;
- restricted network access;
- migrations;
- staging separate from production-beta.

---

# 7. Secrets

Never commit:

- DB URLs;
- API keys;
- JWT secrets;
- email secrets;
- AI provider keys;
- storage credentials.

Use environment/secret manager.

---

# 8. Queue

Document processing is asynchronous.

Message contains identifiers, not raw PDF content.

Example:

```json
{
  "job_type": "PROCESS_POLICY",
  "policy_id": "pol_...",
  "document_id": "doc_..."
}
```

Worker fetches authorized file internally.

---

# 9. Logging

Log:

- request ID;
- user ID where appropriate;
- resource ID;
- status;
- latency;
- error code.

Do not log:

- full policy text;
- detailed health answers;
- raw documents;
- magic-link tokens.

---

# 10. Deployment safety

Before beta deploy:

- run migrations;
- run unit/integration tests;
- run critical E2E;
- verify S3 not public;
- verify env vars;
- verify rollback;
- verify health checks;
- verify delete flow.
