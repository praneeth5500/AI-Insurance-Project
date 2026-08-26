import type {
  ApiResult,
  AppError,
  DecodedPolicy,
  UploadedPolicy,
  UploadedPolicySummary,
} from "@/lib/api/types";
import { fetchAsUser } from "@/lib/auth/session";

/**
 * Server-side reads for uploaded policies.
 *
 * There is deliberately no helper that returns a document URL. A policy
 * document is only ever streamed through an authenticated endpoint that
 * re-checks ownership on every request, so nothing here can hand the browser
 * a link that outlives the reader's session.
 */

const NETWORK_ERROR: AppError = {
  code: "NETWORK_UNAVAILABLE",
  message: "We couldn't load your policy. Please check your connection and try again.",
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

async function parse<T>(response: Response | null): Promise<ApiResult<T>> {
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

  return { status: "success", data: body as T };
}

export async function getPolicy(policyId: string): Promise<ApiResult<UploadedPolicy>> {
  return parse<UploadedPolicy>(
    await fetchAsUser(`/api/v1/policies/${encodeURIComponent(policyId)}`),
  );
}

export async function listPolicies(): Promise<ApiResult<{ policies: UploadedPolicySummary[] }>> {
  return parse<{ policies: UploadedPolicySummary[] }>(await fetchAsUser("/api/v1/policies"));
}

/** Load the decoder report server-side, so the first paint is the report. */
export async function getDecodedPolicy(policyId: string): Promise<ApiResult<DecodedPolicy>> {
  return parse<DecodedPolicy>(
    await fetchAsUser(`/api/v1/policies/${encodeURIComponent(policyId)}/decoded`),
  );
}
