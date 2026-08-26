"use client";

import { AlertTriangle, Check, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { InlineAlert } from "@/components/feedback/inline-alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { apiBaseUrl } from "@/lib/api/client";
import type { UploadedPolicy } from "@/lib/api/types";

/**
 * The processing screen (docs/02_UX_UI_SPEC.md section 14).
 *
 * Three rules from the spec shape it:
 *
 * * **No fake percentages.** Named stages come from the server, which knows
 *   which one it has actually reached. Nothing here interpolates progress.
 * * **The reader may leave and return.** The state lives on the server, so
 *   this page is a view of it rather than the only place it exists. Closing
 *   the tab loses nothing.
 * * **If extraction fails, say clearly what failed and what they can do.**
 *   The failure message is written server-side from a known set of causes,
 *   so it can be specific without echoing anything from the document.
 */

//: Slow enough not to hammer the API, quick enough that a short document
//: does not sit on a stale screen.
const POLL_MS = 4000;

export function ProcessingStatus({ policy }: { policy: UploadedPolicy }) {
  const router = useRouter();
  const settled = policy.isReady || policy.isFailed;

  useEffect(() => {
    if (settled) return;
    const timer = setInterval(() => router.refresh(), POLL_MS);
    return () => clearInterval(timer);
  }, [settled, router]);

  async function remove() {
    await fetch(`${apiBaseUrl()}/api/v1/policies/${policy.id}`, {
      method: "DELETE",
      credentials: "include",
    });
    router.push("/app/home");
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-h2 font-semibold text-primary sm:text-h1">{policy.displayName}</h1>
        <p className="text-support text-secondary">
          {policy.documents.length === 1 ? "1 document" : `${policy.documents.length} documents`} ·
          uploaded privately
        </p>
      </div>

      {policy.isFailed ? (
        <InlineAlert tone="critical" title="We couldn't read that document">
          {policy.failureMessage}
        </InlineAlert>
      ) : null}

      {!settled ? (
        <p aria-live="polite" className="sr-only">
          {policy.statusLabel}
        </p>
      ) : null}

      <Card className="flex flex-col gap-3">
        <h2 className="text-h3 font-medium text-primary">Progress</h2>
        <ol className="flex flex-col gap-3">
          {policy.stages.map((stage) => (
            <li key={stage.key} className="flex items-center gap-3">
              <span aria-hidden="true" className="flex size-5 items-center justify-center">
                {stage.state === "DONE" ? (
                  <Check className="size-4 text-positive" />
                ) : stage.state === "CURRENT" ? (
                  <Loader2 className="size-4 animate-spin text-accent" />
                ) : policy.isFailed ? (
                  <AlertTriangle className="size-4 text-secondary" />
                ) : (
                  <span className="size-2 rounded-full bg-control-border" />
                )}
              </span>
              <span
                className={
                  stage.state === "PENDING"
                    ? "text-support text-secondary"
                    : "text-support font-medium text-primary"
                }
              >
                {stage.label}
              </span>
              {/* The state is carried in text, not by the icon alone. */}
              <span className="sr-only">
                {stage.state === "DONE"
                  ? "done"
                  : stage.state === "CURRENT"
                    ? "in progress"
                    : "not started"}
              </span>
            </li>
          ))}
        </ol>

        {!settled ? (
          <p className="text-meta text-secondary">
            This can take a few minutes. You can close this page and come back — we&apos;ll keep
            going.
          </p>
        ) : null}
      </Card>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Button variant="secondary" onClick={remove}>
          Delete this policy
        </Button>
      </div>

      <p className="text-meta text-secondary">
        Deleting removes the document from our storage. We keep a record that the deletion happened,
        and nothing about what the document said.
      </p>
    </div>
  );
}
