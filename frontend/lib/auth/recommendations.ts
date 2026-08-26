import type {
  ApiResult,
  AppError,
  ComparisonView,
  ProductDetail,
  RecommendationRun,
} from "@/lib/api/types";
import { fetchAsUser } from "@/lib/auth/session";

const NETWORK_ERROR: AppError = {
  code: "NETWORK_UNAVAILABLE",
  message: "We couldn't load your matched options. Please check your connection and try again.",
  retryable: true,
  requestId: null,
};

const UNEXPECTED_ERROR: AppError = {
  code: "UNEXPECTED_RESPONSE",
  message: "Something went wrong on our side.",
  retryable: true,
  requestId: null,
};

function isAppError(value: unknown): value is AppError {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return typeof candidate.code === "string" && typeof candidate.message === "string";
}

/** Load a match set server-side, so the first paint already has the results. */
export async function getRecommendationRun(runId: string): Promise<ApiResult<RecommendationRun>> {
  const response = await fetchAsUser(`/api/v1/recommendation-runs/${runId}`);
  if (response === null) return { status: "error", error: NETWORK_ERROR };

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return { status: "error", error: UNEXPECTED_ERROR };
  }

  if (!response.ok) {
    const envelope = (body as { error?: unknown }).error;
    return {
      status: "error",
      error: isAppError(envelope)
        ? { ...envelope, requestId: envelope.requestId ?? null }
        : UNEXPECTED_ERROR,
    };
  }

  return { status: "success", data: body as RecommendationRun };
}

/**
 * Build a comparison server-side.
 *
 * `POST` per docs/08_API_CONTRACTS.md section 6. The chosen options travel in
 * the URL so the page can be reloaded, shared and navigated back to, while
 * the comparison itself is still computed by the API — the 2-to-3 limit is
 * enforced there, not by the client.
 */
export async function getComparison(
  runId: string,
  productReferences: string[],
): Promise<ApiResult<ComparisonView>> {
  const response = await fetchAsUser("/api/v1/comparisons", {
    method: "POST",
    body: JSON.stringify({ recommendationRunId: runId, productReferences }),
  });
  if (response === null) return { status: "error", error: NETWORK_ERROR };

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return { status: "error", error: UNEXPECTED_ERROR };
  }

  if (!response.ok) {
    const envelope = (body as { error?: unknown }).error;
    return {
      status: "error",
      error: isAppError(envelope)
        ? { ...envelope, requestId: envelope.requestId ?? null }
        : UNEXPECTED_ERROR,
    };
  }

  return { status: "success", data: body as ComparisonView };
}

/**
 * Load one option in full, server-side.
 *
 * `runId` names the result set the reader came from. Fit is a judgement about
 * a person and only exists inside a run, so with one the page shows exactly
 * what that run recorded, and without one it shows the policy's facts and
 * says why there is no personal assessment.
 */
export async function getProductDetail(
  reference: string,
  runId: string | null,
): Promise<ApiResult<ProductDetail>> {
  const query = runId ? `?run=${encodeURIComponent(runId)}` : "";
  const response = await fetchAsUser(`/api/v1/products/${encodeURIComponent(reference)}${query}`);
  if (response === null) return { status: "error", error: NETWORK_ERROR };

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return { status: "error", error: UNEXPECTED_ERROR };
  }

  if (!response.ok) {
    const envelope = (body as { error?: unknown }).error;
    return {
      status: "error",
      error: isAppError(envelope)
        ? { ...envelope, requestId: envelope.requestId ?? null }
        : UNEXPECTED_ERROR,
    };
  }

  return { status: "success", data: body as ProductDetail };
}
