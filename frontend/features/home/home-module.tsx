import type { ReactNode } from "react";
import { Card } from "@/components/ui/card";

/**
 * Shared frame for a returning-home module.
 *
 * A module is only ever rendered when it has something to show — the spec is
 * explicit that empty irrelevant modules must not be drawn
 * (docs/02_UX_UI_SPEC.md section 6), so there is no empty variant here.
 */
export function HomeModule({
  title,
  action,
  children,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-4">
        <h2 className="text-h3 font-medium text-primary">{title}</h2>
        {action}
      </div>
      {children}
    </Card>
  );
}
