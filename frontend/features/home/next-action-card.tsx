import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { buttonClassName } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { ContinueAction } from "@/lib/api/types";
import { cn } from "@/lib/ui/cn";

/**
 * "Continue where you left off" — the top priority of the returning-user home
 * (docs/01_PRODUCT_SPEC.md section 5).
 *
 * Rendered only when there is genuinely something to continue: the spec says
 * "Only show an action if relevant" (docs/02_UX_UI_SPEC.md section 6), so the
 * caller passes `null` and nothing is drawn.
 */
export function NextActionCard({ action }: { action: ContinueAction }) {
  return (
    <Card emphasis="raised" className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-h3 font-medium text-primary">Continue where you left off</h2>
        <p className="text-support text-secondary">{action.label}</p>
        {action.context ? <p className="text-meta text-secondary">{action.context}</p> : null}
      </div>
      {/* Full width on mobile where it is the one clear action; hugs its
          content on wider screens rather than spanning the card. */}
      <Link
        href={action.href}
        className={cn(buttonClassName({ size: "lg" }), "w-full sm:w-auto sm:self-start")}
      >
        Continue
        <ArrowRight className="size-4" aria-hidden="true" />
      </Link>
    </Card>
  );
}
