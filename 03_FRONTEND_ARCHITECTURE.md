# Frontend Architecture

## Stack

- Next.js
- React
- TypeScript strict mode
- Tailwind CSS
- Accessible headless primitives
- One icon library
- Typed API client
- Form/state tooling only when justified

Do not add a large state-management library before it is necessary.

---

# 1. App structure

Suggested:

```text
frontend/
├── app/
│   ├── (public)/
│   ├── (auth)/
│   └── (app)/
├── components/
│   ├── ui/
│   ├── layout/
│   └── feedback/
├── features/
│   ├── auth/
│   ├── home/
│   ├── questionnaire/
│   ├── recommendations/
│   ├── comparison/
│   ├── product-detail/
│   ├── policy-upload/
│   ├── policy-decoder/
│   ├── policy-chat/
│   └── account/
├── lib/
│   ├── api/
│   ├── analytics/
│   ├── auth/
│   ├── formatting/
│   └── validation/
├── styles/
└── tests/
```

---

# 2. Routes

```text
/
├── /sign-in
├── /auth/verify
├── /privacy
├── /terms
├── /help
│
├── /app/home
│
├── /app/recommend
│   ├── /health
│   │   ├── /about-you
│   │   ├── /current-cover
│   │   ├── /priorities
│   │   ├── /review
│   │   └── /results/:runId
│   └── /motor
│
├── /app/recommendations/:runId
├── /app/recommendations/:runId/compare
├── /app/products/:productVersionId
│
├── /app/policies
│   ├── /upload
│   ├── /:policyId/processing
│   ├── /:policyId
│   ├── /:policyId/ask
│   ├── /:policyId/source
│   └── /:policyId/claims-readiness
│
├── /app/profile
│   ├── /household
│   └── /vehicles
│
└── /app/settings
    ├── /account
    ├── /privacy
    └── /data
```

---

# 3. Questionnaire rendering

Do not hard-code every question as a separate unique component.

Use a question definition:

```ts
type QuestionDefinition = {
  id: string;
  version: string;
  domain: "HEALTH" | "MOTOR";
  stage: string;
  title: string;
  description?: string;
  inputType:
    | "SINGLE_CHOICE"
    | "MULTI_CHOICE"
    | "NUMBER"
    | "MONEY"
    | "PINCODE"
    | "BOOLEAN";
  options?: Array<{
    value: string;
    label: string;
    description?: string;
  }>;
  required: boolean;
  showIf?: ConditionDefinition;
  dataField: string;
  helpKey?: string;
  analyticsKey: string;
};
```

Questionnaire state:

```text
current question
answers
visible question graph
stage
completion state
draft session ID
```

Persist draft server-side after meaningful checkpoints.

---

# 4. Primary components

Global:

```text
AppShell
TopNavigation
MobileNavigation
PageContainer
PageHeader
Button
Card
Sheet
Modal
Toast
InlineAlert
Skeleton
EmptyState
ErrorState
ProgressStage
```

Questionnaire:

```text
QuestionnaireShell
StageProgress
QuestionHeader
OptionCard
OptionGrid
ChoiceGroup
HelpDisclosure
AIHelpSheet
BackContinueBar
ReviewSection
```

Recommendations:

```text
DecisionProfileSummary
PriorityEditor
MatchList
MatchCard
FitDimension
WatchOut
CompareSelector
CompareTray
PriceDisplay
```

Product detail:

```text
ProductHero
FitHighlights
WhyItMatches
TradeoffPanel
PolicySectionNav
PolicyFact
ExampleExplainer
SourceLink
DecisionActionBar
```

Decoder:

```text
UploadDropzone
ProcessingStages
PolicyReport
PolicySection
PolicyFactCard
SourceClauseViewer
PolicyAssistant
Citation
ClaimsChecklist
```

Dashboard:

```text
NextActionCard
RecommendationHistoryCard
PolicyLibraryCard
ProfileSummary
VehicleSummary
ConditionalClaimsCard
```

---

# 5. API state

Use explicit states:

```ts
type AsyncState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: AppError };
```

Do not render blank screens while loading.

---

# 6. Error UX

Must support:

- expired invite;
- expired magic link;
- API unavailable;
- partner unavailable;
- no matched products;
- incomplete product data;
- stale price;
- upload too large;
- corrupt PDF;
- unsupported file;
- password-protected PDF;
- unreadable scan;
- AI unavailable;
- missing source;
- processing failure.

---

# 7. Analytics events

Examples:

```text
home_viewed
recommendation_started
question_answered
question_help_opened
questionnaire_reviewed
recommendation_generated
match_opened
priority_changed
compare_added
comparison_viewed
policy_upload_started
policy_upload_completed
policy_processing_completed
decoder_section_opened
policy_question_asked
citation_opened
claims_checklist_opened
feedback_submitted
```

Never put sensitive medical answer content directly into analytics event properties.
