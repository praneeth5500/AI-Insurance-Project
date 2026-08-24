import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { buttonClassName } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { Availability } from "@/lib/api/types";
import { cn } from "@/lib/ui/cn";

/**
 * A primary product entry point on the new-user home
 * (docs/02_UX_UI_SPEC.md section 5).
 *
 * A card whose destination is not built yet renders its action as inert text
 * with a visible "Coming soon" marker, never as a button that goes nowhere:
 * docs/12_BETA_CHECKLIST.md requires no dead buttons, and CLAUDE.md forbids a
 * UI claim the backend cannot support.
 */
export type ProductCardProps = {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel: string;
  href: string;
  availability: Availability;
  /** Shown instead of the action when the destination is not ready. */
  comingSoonNote: string;
};

export function ProductCard({
  icon: Icon,
  title,
  description,
  actionLabel,
  href,
  availability,
  comingSoonNote,
}: ProductCardProps) {
  const available = availability === "AVAILABLE";

  return (
    <Card className="flex h-full flex-col gap-4">
      <span
        className={cn(
          "flex size-10 items-center justify-center rounded-control",
          available ? "bg-accent-soft" : "bg-bg",
        )}
      >
        <Icon
          className={cn("size-5", available ? "text-accent" : "text-secondary")}
          aria-hidden="true"
        />
      </span>

      <div className="flex flex-1 flex-col gap-1.5">
        <h3 className="text-h3 font-medium text-primary">{title}</h3>
        <p className="text-support text-secondary">{description}</p>
      </div>

      {available ? (
        <Link href={href} className={buttonClassName({ variant: "secondary" })}>
          {actionLabel}
        </Link>
      ) : (
        <div className="flex flex-col gap-1">
          {/* Not a button: there is nowhere to go yet, and pretending
              otherwise would be a claim the product cannot support. */}
          <p className="text-support font-medium text-secondary">Coming soon</p>
          <p className="text-meta text-secondary">{comingSoonNote}</p>
        </div>
      )}
    </Card>
  );
}
