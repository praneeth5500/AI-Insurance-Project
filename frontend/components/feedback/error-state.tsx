import { AlertOctagon } from "lucide-react";
import type { ReactNode } from "react";
import { TrackView } from "@/lib/analytics/track-view";
import { cn } from "@/lib/ui/cn";

/**
 * Shown when something failed.
 *
 * Says what went wrong and what the user can do about it
 * (docs/02_UX_UI_SPEC.md section 14). The error code and request id are
 * displayed when available so a beta user can quote them in feedback — they
 * are the two identifiers the API returns in its error envelope.
 *
 * This component is presentational: callers map an API error onto these props
 * rather than the component importing the API layer.
 *
 * It does emit one thing — the error telemetry Phase 15 asks for. Doing it
 * here rather than at each call site means an error screen cannot be added
 * without being counted, which is the only way the number stays true. The
 * code is recorded; the description, which can carry specifics, is not.
 */
export type ErrorStateProps = {
  title: string;
  description: string;
  /** Machine-readable code from the API error envelope. */
  code?: string;
  /** Request id from the API error envelope. */
  requestId?: string;
  /** Retry affordance. Only pass one when retrying can actually help. */
  action?: ReactNode;
  className?: string;
};

export function ErrorState({
  title,
  description,
  code,
  requestId,
  action,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center gap-3 rounded-card border border-border",
        "bg-surface px-6 py-10 text-center",
        className,
      )}
    >
      <TrackView event="error_shown" properties={{ error_code: code ?? "UNKNOWN" }} />
      <span className="flex size-11 items-center justify-center rounded-full bg-critical-soft">
        <AlertOctagon className="size-5 text-critical" aria-hidden="true" />
      </span>
      <div className="flex flex-col gap-1">
        <p className="text-h3 font-medium text-primary">{title}</p>
        <p className="mx-auto max-w-prose text-support text-secondary">{description}</p>
      </div>
      {action ? <div className="mt-1">{action}</div> : null}
      {code || requestId ? (
        <p className="text-meta text-secondary">
          {code ? <span>Error code: {code}</span> : null}
          {code && requestId ? <span aria-hidden="true"> · </span> : null}
          {requestId ? <span>Reference: {requestId}</span> : null}
        </p>
      ) : null}
    </div>
  );
}
