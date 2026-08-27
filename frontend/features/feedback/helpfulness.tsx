"use client";

import { ThumbsDown, ThumbsUp } from "lucide-react";
import { useState } from "react";
import { apiBaseUrl } from "@/lib/api/client";

/**
 * "Was this helpful?" — the beta checklist's helpfulness signal.
 *
 * Placed on the screens where being wrong actually costs the reader
 * something: the match set, the decoded report, an answer. Two decisions
 * worth stating:
 *
 * * **A rating alone is enough.** Requiring a comment gets far fewer
 *   responses, and the count is the signal that generalises.
 * * **"No" opens a comment box, "yes" does not.** What went wrong is worth
 *   the extra step; what went right rarely says anything actionable.
 */
export function Helpfulness({
  contextType,
  contextId = null,
  question = "Was this helpful?",
}: {
  contextType: string;
  contextId?: string | null;
  question?: string;
}) {
  const [rating, setRating] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [done, setDone] = useState(false);

  function send(value: number, text?: string) {
    void fetch(`${apiBaseUrl()}/api/v1/feedback`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contextType,
        contextId,
        rating: value,
        ...(text ? { comment: text } : {}),
      }),
      keepalive: true,
    }).catch(() => {
      // Feedback failing must not become the reader's problem.
    });
  }

  if (done) {
    return (
      <p role="status" className="text-support text-secondary">
        Thanks — that helps.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3 rounded-card border border-control-border bg-surface p-4">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-support font-medium text-primary">{question}</p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => {
              send(1);
              setDone(true);
            }}
            className="inline-flex min-h-touch items-center gap-1 rounded-control border border-control-border px-3 text-support text-primary"
          >
            <ThumbsUp className="size-4" aria-hidden="true" />
            Yes
          </button>
          <button
            type="button"
            onClick={() => setRating(-1)}
            aria-expanded={rating === -1}
            className="inline-flex min-h-touch items-center gap-1 rounded-control border border-control-border px-3 text-support text-primary"
          >
            <ThumbsDown className="size-4" aria-hidden="true" />
            No
          </button>
        </div>
      </div>

      {rating === -1 ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            send(-1, comment);
            setDone(true);
          }}
          className="flex flex-col gap-2"
        >
          <label htmlFor="feedback-comment" className="text-support text-secondary">
            What was missing or wrong? (optional)
          </label>
          <textarea
            id="feedback-comment"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            maxLength={2000}
            rows={3}
            className="rounded-control border border-control-border bg-surface p-3 text-support text-primary"
          />
          <p className="text-meta text-secondary">
            Please don&apos;t include anything you wouldn&apos;t want us to read — this goes to a
            person.
          </p>
          <button
            type="submit"
            className="inline-flex min-h-touch items-center justify-center self-start rounded-control bg-accent px-6 text-body font-medium text-surface"
          >
            Send
          </button>
        </form>
      ) : null}
    </div>
  );
}
