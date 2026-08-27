import { apiBaseUrl } from "@/lib/api/client";

/**
 * Client-side event tracking.
 *
 * `docs/03_FRONTEND_ARCHITECTURE.md` section 7 ends with the rule this file
 * exists to respect: never put sensitive answer content into an event.
 *
 * The real enforcement is on the server — only declared events with declared
 * property keys are stored, and a browser cannot widen either. This module's
 * job is narrower: give call sites a typed shape so the temptation to pass an
 * answer never arises, and make tracking impossible to break the page with.
 *
 * Fire-and-forget on purpose. A measurement that can fail a reader's action is
 * worse than no measurement, so nothing here is awaited and every failure is
 * swallowed.
 */

/** The events a browser is allowed to send. Must match the server registry. */
export type ClientEvent =
  | "home_viewed"
  | "question_answered"
  | "question_help_opened"
  | "questionnaire_reviewed"
  | "match_opened"
  | "compare_added"
  | "comparison_viewed"
  | "policy_upload_started"
  | "decoder_section_opened"
  | "citation_opened"
  | "claims_checklist_opened"
  | "error_shown";

/**
 * Only primitives. A structured value is how an answer payload travels, and
 * the type stops one being passed by accident rather than relying on the
 * server to drop it.
 */
export type EventProperties = Record<string, string | number | boolean | null>;

export function track(name: ClientEvent, properties: EventProperties = {}): void {
  void fetch(`${apiBaseUrl()}/api/v1/analytics/events`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, properties }),
    // Lets the request survive a navigation, so an event on a link click is
    // not lost when the page unloads.
    keepalive: true,
  }).catch(() => {
    // Measurement never surfaces to the reader.
  });
}
