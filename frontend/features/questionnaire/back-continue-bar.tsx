"use client";

import { Button } from "@/components/ui/button";

/**
 * Back / Continue, matching the example screen in
 * docs/02_UX_UI_SPEC.md section 7.
 *
 * On mobile the primary action comes first in the visual order but stays last
 * in the DOM, so tab order still runs Back → Continue.
 */
export function BackContinueBar({
  onBack,
  onContinue,
  backDisabled,
  continueDisabled,
  continueLabel = "Continue",
  saving = false,
}: {
  onBack: () => void;
  onContinue: () => void;
  backDisabled: boolean;
  continueDisabled: boolean;
  continueLabel?: string;
  saving?: boolean;
}) {
  return (
    <div className="flex flex-col-reverse gap-3 border-t border-border pt-6 sm:flex-row sm:justify-between">
      <Button variant="secondary" onClick={onBack} disabled={backDisabled}>
        Back
      </Button>
      <Button size="lg" onClick={onContinue} disabled={continueDisabled} loading={saving}>
        {continueLabel}
      </Button>
    </div>
  );
}
