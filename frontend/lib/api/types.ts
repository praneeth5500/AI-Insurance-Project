/**
 * Shared API types.
 *
 * The error shape is the single envelope defined in
 * `docs/08_API_CONTRACTS.md` section 12. The backend guarantees every failure
 * arrives in this form, so the client never has to guess.
 */

export type AppError = {
  code: string;
  message: string;
  retryable: boolean;
  requestId: string | null;
};

export type ApiErrorBody = {
  error: AppError;
};

/** Outcome of a completed request. */
export type ApiResult<T> = { status: "success"; data: T } | { status: "error"; error: AppError };

/**
 * Explicit request state (`docs/03_FRONTEND_ARCHITECTURE.md` section 5).
 * Every screen renders all four states — never a blank screen while loading.
 */
export type AsyncState<T> = { status: "idle" } | { status: "loading" } | ApiResult<T>;

/** `GET /api/v1/me` and `POST /api/v1/auth/verify` */
export type CurrentUser = {
  id: string;
  email: string;
  hasProfile: boolean;
  betaAccess: boolean;
};

/** `POST /api/v1/auth/request-magic-link` */
export type MagicLinkResponse = {
  status: string;
};

// ---------------------------------------------------------------- home ----

/** Whether a destination actually works, so the UI never offers a dead action. */
export type Availability = "AVAILABLE" | "COMING_SOON";

/** REAL: the user's own data. DEMO: clearly-labelled synthetic layout data. */
export type DataMode = "REAL" | "DEMO";

export type FeatureAvailability = {
  healthRecommendation: Availability;
  motorRecommendation: Availability;
  policyDecoder: Availability;
};

export type ContinueAction = {
  kind: "RESUME_QUESTIONNAIRE" | "VIEW_RECOMMENDATION" | "VIEW_POLICY";
  label: string;
  href: string;
  context: string | null;
  updatedAt: string | null;
};

export type RecommendationSummary = {
  id: string;
  domain: "HEALTH" | "MOTOR";
  matchCount: number;
  createdAt: string;
  href: string;
};

export type PolicySummary = {
  id: string;
  displayName: string;
  status: string;
  createdAt: string;
  href: string;
};

export type ClaimsChecklistSummary = {
  id: string;
  policyDisplayName: string;
  completedItems: number;
  totalItems: number;
  href: string;
};

export type HouseholdSummary = { memberCount: number; href: string };

export type VehicleSummary = { count: number; href: string };

/** `GET /api/v1/home` */
export type HomeSummary = {
  isNewUser: boolean;
  dataMode: DataMode;
  features: FeatureAvailability;
  continueAction: ContinueAction | null;
  recommendations: RecommendationSummary[];
  policies: PolicySummary[];
  claimsChecklist: ClaimsChecklistSummary | null;
  household: HouseholdSummary | null;
  vehicles: VehicleSummary | null;
};

// ------------------------------------------------------- questionnaire ----

export type InputType =
  "SINGLE_CHOICE" | "MULTI_CHOICE" | "NUMBER" | "MONEY" | "PINCODE" | "BOOLEAN";

export type QuestionOption = {
  value: string;
  label: string;
  description: string | null;
};

export type Question = {
  id: string;
  stage: string;
  title: string;
  description: string | null;
  inputType: InputType;
  options: QuestionOption[];
  required: boolean;
  dataField: string;
  /** "Why we're asking this" — docs/02_UX_UI_SPEC.md rule 3. */
  helpText: string | null;
  maxSelections: number | null;
  unit: string | null;
  minValue: number | null;
  maxValue: number | null;
  /** Never send this answer's value to analytics or logs. */
  sensitive: boolean;
};

export type QuestionnaireStage = {
  key: string;
  label: string;
  questionIds: string[];
  complete: boolean;
};

export type QuestionnaireAnswer = {
  questionId: string;
  value: unknown;
};

/** `GET /api/v1/questionnaire-sessions/{id}` */
export type QuestionnaireSession = {
  id: string;
  domain: string;
  questionnaireVersion: string;
  status: "IN_PROGRESS" | "COMPLETED";
  startedAt: string;
  completedAt: string | null;
  /** DRAFT until the founder's wording pass on the question set. */
  definitionStatus: "DRAFT" | "ACTIVE";
  stages: QuestionnaireStage[];
  questions: Question[];
  answers: QuestionnaireAnswer[];
  currentStage: string | null;
  nextQuestionId: string | null;
  isComplete: boolean;
};

// ------------------------------------------------------ recommendations ----

/** docs/01_PRODUCT_SPEC.md section 2.6. Never conveyed by colour alone. */
export type FitLabel = "STRONG" | "GOOD" | "TRADE_OFF" | "NEEDS_ATTENTION" | "UNVERIFIED";

export type FitView = {
  factor: string;
  label: string;
  fit: FitLabel;
  note: string;
};

/** Never a bare number: state, source and reason always travel with it. */
export type PriceView = {
  state: "INDICATIVE" | "QUOTED" | "FINAL" | "UNAVAILABLE";
  amount: number | null;
  currency: string | null;
  sourceType: string;
  generatedAt: string | null;
  explanation: string;
};

export type MatchView = {
  id: string;
  productReference: string;
  insurerName: string;
  productName: string;
  sourceType: string;
  presentationOrder: number;
  eligibilityStatus: string;
  highlights: FitView[];
  watchOut: string;
  fits: FitView[];
  price: PriceView;
};

/** `GET /api/v1/recommendation-runs/{runId}` */
export type RecommendationRun = {
  id: string;
  status: string;
  presentationMode: string;
  sourceType: string;
  questionnaireVersion: string;
  scoringVersion: string;
  catalogueVersion: string;
  createdAt: string;
  decisionProfile: string[];
  priorities: string[];
  matches: MatchView[];
  additionalMatches: MatchView[];
  canShowMore: boolean;
  reordered: string[];
  /**
   * The run this one replaced. Changing a priority produces a new run rather
   * than editing the old one, so results can never be rewritten after the
   * fact (docs/06_RECOMMENDATION_ENGINE.md section 11).
   */
  previousRunId: string | null;
  /**
   * How many options were assessed and not offered, with the rules that ruled
   * them out. A count and reasons — never a list of rejected products.
   */
  excludedCount: number;
  exclusionNotes: string[];
};

// ---------------------------------------------------------- comparison ----

export type DimensionView = {
  factor: string;
  label: string;
  /** Keyed by product reference. */
  values: Record<string, FitLabel>;
  notes: Record<string, string>;
  differs: boolean;
  isPriority: boolean;
};

export type ComparisonOptionView = {
  productReference: string;
  insurerName: string;
  productName: string;
  sourceType: string;
  watchOut: string;
};

/** `POST /api/v1/comparisons` */
export type ComparisonView = {
  runId: string;
  sourceType: string;
  options: ComparisonOptionView[];
  priorities: string[];
  biggestDifferences: DimensionView[];
  yourPriorities: DimensionView[];
  allDetails: DimensionView[];
};

// ----------------------------------------------------- product detail ----

export type ProductFactView = {
  key: string;
  label: string;
  value: string;
  /** "Explain with example" — about the mechanism, never this product. */
  example: string | null;
  /** False for every synthetic product. Never fabricate a citation. */
  hasSource: boolean;
  sourceNote: string | null;
};

export type ProductSectionView = {
  key: string;
  label: string;
  facts: ProductFactView[];
};

export type ProvenanceView = {
  sourceType: string;
  catalogueVersion: string;
  verifiedAt: string | null;
  explanation: string;
};

/** `GET /api/v1/products/{reference}` */
export type ProductDetail = {
  reference: string;
  insurerName: string;
  productName: string;
  sourceType: string;
  highlights: FitView[];
  watchOut: string;
  fits: FitView[];
  /**
   * Set when the page was opened outside a set of matches. Fit is a judgement
   * about a person, so without a run there is nothing to say about it, and
   * the page says that rather than inventing one.
   */
  fitContextNote: string | null;
  sections: ProductSectionView[];
  sourceDocuments: string[];
  sourceDocumentsNote: string;
  provenance: ProvenanceView;
  saved: boolean;
};

/** `GET /health/ready` */
export type ReadinessResponse = {
  status: "ready";
  dependencies: {
    database: "ok" | "unavailable";
  };
};

// ------------------------------------------------------ uploaded policies ----

/**
 * One step of processing (docs/02_UX_UI_SPEC.md section 14).
 *
 * Stages, never a percentage: any percentage here would be invented, and the
 * UX spec rules out fake progress.
 */
export type PolicyStage = {
  key: string;
  label: string;
  state: "DONE" | "CURRENT" | "PENDING";
};

export type PolicyDocumentView = {
  id: string;
  filename: string;
  mimeType: string;
  sizeBytes: number;
  pageCount: number | null;
  createdAt: string;
};

/** `GET /api/v1/policies/{policyId}` */
export type UploadedPolicy = {
  id: string;
  displayName: string;
  domain: string | null;
  status: string;
  statusLabel: string;
  stages: PolicyStage[];
  isReady: boolean;
  isFailed: boolean;
  /** Present only on failure, in language the reader can act on. */
  failureMessage: string | null;
  documents: PolicyDocumentView[];
  createdAt: string;
  readyAt: string | null;
};

export type UploadedPolicySummary = {
  id: string;
  displayName: string;
  status: string;
  statusLabel: string;
  isReady: boolean;
  isFailed: boolean;
  createdAt: string;
};
