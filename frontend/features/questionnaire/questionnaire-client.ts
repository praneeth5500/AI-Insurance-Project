"use client";

import { postJson, requestJson } from "@/lib/api/client";
import type { ApiResult, QuestionnaireSession, RecommendationRun } from "@/lib/api/types";

const BASE = "/api/v1/questionnaire-sessions";

export async function startOrResume(domain = "HEALTH"): Promise<ApiResult<QuestionnaireSession>> {
  return postJson<QuestionnaireSession>(BASE, { domain });
}

/**
 * Save one answer. This is the draft checkpoint
 * (docs/03_FRONTEND_ARCHITECTURE.md section 3) — the server returns the
 * recomputed session, so branching stays server-side and the client never has
 * to reason about which questions apply.
 */
export async function saveAnswer(
  sessionId: string,
  questionId: string,
  value: unknown,
): Promise<ApiResult<QuestionnaireSession>> {
  return requestJson<QuestionnaireSession>(`${BASE}/${sessionId}/answers/${questionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ value }),
  });
}

export async function completeSession(sessionId: string): Promise<ApiResult<QuestionnaireSession>> {
  return postJson<QuestionnaireSession>(`${BASE}/${sessionId}/complete`, {});
}

/** Turn a completed questionnaire into a match set. */
export async function createRecommendationRun(
  questionnaireSessionId: string,
): Promise<ApiResult<RecommendationRun>> {
  return postJson<RecommendationRun>("/api/v1/recommendation-runs", {
    questionnaireSessionId,
  });
}
