import type { ApiResult, AppError, RecommendationRun } from "@/lib/api/types";
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
