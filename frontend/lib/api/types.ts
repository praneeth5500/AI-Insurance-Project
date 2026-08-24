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

/** `GET /health/ready` */
export type ReadinessResponse = {
  status: "ready";
  dependencies: {
    database: "ok" | "unavailable";
  };
};
