import { apiBaseUrl } from "@/lib/api/client";
import type { ApiResult, AppError, QuestionnaireSession } from "@/lib/api/types";
import { SESSION_COOKIE_NAME } from "@/lib/auth/session";
import { cookies } from "next/headers";

const NETWORK_ERROR: AppError = {
  code: "NETWORK_UNAVAILABLE",
  message: "We couldn't load your answers. Please check your connection and try again.",
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

/**
 * Start or resume the user's draft, server-side.
 *
 * Done on the server so the first paint already has the questions and the
 * saved answers — the flow never flashes an empty screen while it loads.
 */
export async function startOrResumeServerSide(
  domain = "HEALTH",
): Promise<ApiResult<QuestionnaireSession>> {
  const cookieStore = await cookies();
  const session = cookieStore.get(SESSION_COOKIE_NAME);
  if (!session) return { status: "error", error: NETWORK_ERROR };

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}/api/v1/questionnaire-sessions`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        Cookie: `${SESSION_COOKIE_NAME}=${session.value}`,
      },
      body: JSON.stringify({ domain }),
      cache: "no-store",
    });
  } catch {
    return { status: "error", error: NETWORK_ERROR };
  }

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

  return { status: "success", data: body as QuestionnaireSession };
}
