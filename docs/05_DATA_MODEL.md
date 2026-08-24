# Data Model

This is a logical model. Generate migrations only after validating the relationships in implementation.

---

# 1. Auth and user

## auth_identities

```text
id
email
provider
provider_subject
allowlisted
status
created_at
last_login_at
```

## users

```text
id
auth_identity_id
display_name nullable
created_at
updated_at
```

## households

```text
id
owner_user_id
name nullable
created_at
```

## household_members

```text
id
household_id
relationship
display_name
birth_year or age field appropriate to beta
created_at
```

Avoid storing more personal data than needed.

---

# 2. Questionnaire

## questionnaire_definitions

```text
id
domain
version
status
created_at
```

## questionnaire_sessions

```text
id
user_id
domain
questionnaire_version
status
started_at
completed_at
```

## questionnaire_answers

```text
id
session_id
question_id
answer_json
created_at
updated_at
```

Sensitive fields must be flagged in metadata.

---

# 3. User priorities

## priority_profiles

```text
id
questionnaire_session_id
domain
version
created_at
```

## priority_items

```text
id
priority_profile_id
factor_key
priority_level
rank_order nullable
```

Onboarding model:

- top 3 priorities.

Results model:

- optional fine-tuning.

---

# 4. Insurance product catalogue

## insurers

```text
id
name
external_id nullable
active
```

## insurance_products

```text
id
insurer_id
domain
name
external_product_id nullable
```

## product_versions

```text
id
product_id
version_label
uin_or_reference nullable
effective_from nullable
effective_to nullable
active
source_type
source_name
source_reference
verified_at
created_at
```

## product_facts

```text
id
product_version_id
fact_key
value_json
normalized_value_json nullable
critical_for_matching boolean
source_reference nullable
source_page nullable
verified_at
```

Examples of health fact keys:

```text
eligibility_age
sum_insured_options
copay
deductible
ped_waiting_period
room_rent_rule
hospital_network
disease_sublimits
restoration
pre_hospitalization
post_hospitalization
major_exclusion
```

---

# 5. Pricing

## product_prices

```text
id
product_version_id
status                INDICATIVE | QUOTED | FINAL
amount
currency              INR
billing_period
taxes_included nullable
fees_included nullable
source_type
source_name
source_quote_id nullable
generated_at
valid_until nullable
underwriting_required nullable
assumptions_json nullable
request_fingerprint nullable
```

Never display a price record without source/status/timestamp.

---

# 6. Recommendation

## recommendation_runs

```text
id
user_id
questionnaire_session_id
domain
questionnaire_version
scoring_version
presentation_mode
created_at
```

## recommendation_candidates

```text
id
recommendation_run_id
product_version_id
eligibility_status
internal_relevance_value nullable
internal_order nullable
presentation_order nullable
reason_summary_json
```

## fit_components

```text
id
candidate_id
factor_key
normalized_score nullable
label
user_priority_level
hard_requirement boolean
evidence_json
```

Historical runs do not change when new product data arrives.

---

# 7. Uploaded policy

## uploaded_policies

```text
id
user_id
domain nullable
display_name
status
created_at
ready_at nullable
```

## policy_documents

```text
id
policy_id
storage_key
filename
mime_type
size_bytes
sha256
page_count nullable
created_at
deleted_at nullable
```

## policy_pages

```text
id
document_id
page_number
text
extraction_method
confidence nullable
```

Do not index raw page text in ordinary logs.

## policy_clauses

```text
id
policy_id
clause_type
title nullable
source_page
source_text
normalized_text nullable
confidence nullable
```

## policy_facts

```text
id
policy_id
fact_key
value_json
confidence
clause_id nullable
extraction_run_id
```

## extraction_runs

```text
id
policy_id
schema_version
ocr_provider
ai_provider
model
prompt_version
status
started_at
completed_at
```

---

# 8. Q&A

## conversations

```text
id
user_id
policy_id
created_at
```

## messages

```text
id
conversation_id
role
content
created_at
model_metadata_json nullable
```

## citations

```text
id
message_id
policy_clause_id
page_number
quote_start nullable
quote_end nullable
```

---

# 9. Claims readiness

## claims_readiness_sessions

```text
id
user_id
policy_id
status
created_at
updated_at
```

## claims_checklist_items

```text
id
session_id
item_key
label
description
source_clause_id nullable
completed
user_note nullable
```

---

# 10. Audit / feedback

## feedback

```text
id
user_id nullable
context_type
context_id nullable
rating nullable
comment nullable
created_at
```

## audit_events

```text
id
user_id nullable
event_type
resource_type
resource_id nullable
metadata_json
created_at
```

Do not store sensitive source content in audit metadata.
