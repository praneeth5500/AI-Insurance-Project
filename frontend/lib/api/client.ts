/**
 * Typed API client.
 *
 * Returns a discriminated result instead of throwing, so callers are forced to
 * handle the error branch and cannot accidentally render a blank screen.
 */

import type { ApiErrorBody, ApiResult, AppError, ReadinessResponse } from "@/lib/api/types";

const DEFAULT_BASE_URL = "http://localhost:8000";

export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_BASE_URL;
}

const NETWORK_ERROR: AppError = {
  code: "NETWORK_UNAVAILABLE",
  message: "We could not reach the service. Please check your connection and try again.",
  retryable: true,
  requestId: null,
};

const UNEXPECTED_RESPONSE_ERROR: AppError = {
  code: "UNEXPECTED_RESPONSE",
  message: "Something went wrong on our side.",
  retryable: true,
  requestId: null,
};

function isAppError(value: unknown): value is AppError {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.code === "string" &&
    typeof candidate.message === "string" &&
    typeof candidate.retryable === "boolean"
  );
}

function toAppError(body: unknown): AppError {
  if (typeof body === "object" && body !== null && "error" in body) {
    const { error } = body as ApiErrorBody;
    if (isAppError(error)) {
      return { ...error, requestId: error.requestId ?? null };
    }
  }
  return UNEXPECTED_RESPONSE_ERROR;
}

/** Perform a JSON request and narrow the outcome to success or a typed error. */
export async function requestJson<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      headers: { Accept: "application/json", ...init?.headers },
    });
  } catch {
    // The underlying reason is deliberately dropped: it can name internal hosts.
    return { status: "error", error: NETWORK_ERROR };
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return { status: "error", error: UNEXPECTED_RESPONSE_ERROR };
  }

  if (!response.ok) {
    return { status: "error", error: toAppError(body) };
  }

  return { status: "success", data: body as T };
}

/** Readiness of the API and its dependencies. Used by the Phase 0 status page. */
export async function getReadiness(): Promise<ApiResult<ReadinessResponse>> {
  return requestJson<ReadinessResponse>("/health/ready", { cache: "no-store" });
}
