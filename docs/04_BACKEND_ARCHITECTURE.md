# Backend Architecture

## Stack

- Python
- FastAPI
- Pydantic
- SQLAlchemy or equivalent ORM
- PostgreSQL
- S3-compatible private object storage
- Async job queue
- Separate worker process
- Provider adapters for AI, OCR, insurance data, auth/email

---

# 1. Architecture style

Use a **modular monolith**.

```text
backend/app/
├── auth/
├── users/
├── households/
├── profiles/
├── questionnaires/
├── recommendations/
├── scoring/
├── products/
├── pricing/
├── policies/
├── documents/
├── ai/
├── claims_readiness/
├── integrations/
├── analytics/
└── audit/
```

Avoid microservices.

---

# 2. Layering

Each domain should roughly have:

```text
router/API
↓
service/use-case
↓
domain logic
↓
repository/adapters
↓
database/external provider
```

Keep provider SDK calls out of domain logic.

---

# 3. External adapters

Define interfaces:

```python
class InsuranceProductProvider(Protocol):
    async def list_products(...): ...
    async def get_product(...): ...
    async def get_quote(...): ...

class LLMProvider(Protocol):
    async def generate_structured(...): ...
    async def answer_grounded(...): ...

class OCRProvider(Protocol):
    async def extract_pages(...): ...

class FileStorage(Protocol):
    async def put_private(...): ...
    async def get_signed_url(...): ...
    async def delete(...): ...

class EmailProvider(Protocol):
    async def send_magic_link(...): ...
```

Do not couple product logic to one vendor.

---

# 4. Recommendation pipeline

```text
Questionnaire answers
↓
Normalize user profile
↓
Hard eligibility filter
↓
Load verified/current product versions
↓
Compute fit dimensions
↓
Apply user priorities
↓
Internal relevance ordering
↓
Build explanation evidence object
↓
AI creates plain-language explanation
↓
Persist immutable recommendation run
↓
Return presentation-safe result
```

AI must not be inside eligibility or score calculation.

---

# 5. Policy document pipeline

```text
Upload request
↓
Validate file
↓
Store private
↓
Create processing job
↓
Worker reads file
↓
Native text extraction
↓
OCR fallback if needed
↓
Normalize pages
↓
Segment clauses
↓
Structured fact extraction
↓
Validation
↓
Persist facts + citations
↓
Build retrieval index
↓
Mark ready
```

---

# 6. Async processing

Long document processing must not block a normal HTTP request.

Recommended beta architecture:

```text
FastAPI
↓
Queue
↓
Python worker
↓
S3 / PostgreSQL / AI provider
```

Exact queue technology can be selected during implementation.

AWS-aligned option:

- SQS for queue
- worker on ECS/Fargate

Local development can use a simpler queue adapter.

---

# 7. Authentication

Beta requirements:

- allowlisted emails;
- passwordless magic link;
- signed/expiring token;
- one-time use where practical;
- session revocation;
- audit login events.

Keep auth identity separate from user/household profiles.

---

# 8. Data safety

- never expose S3 object paths publicly;
- use signed URLs only when needed;
- authorize every policy file access;
- do not write document text to standard logs;
- redact sensitive request bodies from error reporting;
- use synthetic fixtures in tests;
- implement delete cascade behavior intentionally.

---

# 9. Versioning

Version:

- questionnaire;
- scoring config;
- product version;
- policy extraction schema;
- AI prompt;
- model/provider;
- recommendation run.

Historical recommendation runs are immutable.

---

# 10. Health checks / observability

Endpoints:

```text
/health/live
/health/ready
```

Monitor:

- API errors;
- DB failures;
- queue backlog;
- processing time;
- AI errors;
- OCR errors;
- partner API errors;
- extraction uncertainty;
- token/model cost if available.
