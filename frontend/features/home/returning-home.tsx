import { ConditionalClaimsCard } from "@/features/home/conditional-claims-card";
import { NextActionCard } from "@/features/home/next-action-card";
import { PolicyLibraryCard } from "@/features/home/policy-library-card";
import { ProfileSummary } from "@/features/home/profile-summary";
import { RecommendationHistoryCard } from "@/features/home/recommendation-history-card";
import { VehicleSummary } from "@/features/home/vehicle-summary";
import type { HomeSummary } from "@/lib/api/types";

/**
 * The returning-user home (docs/01_PRODUCT_SPEC.md section 5,
 * docs/02_UX_UI_SPEC.md section 6).
 *
 * Order is the specification's: continue first, then recommendations,
 * policies, claims checklist, household, vehicles. Every module below the
 * first is conditional — when there is nothing to show, nothing is rendered,
 * rather than an empty shell.
 *
 * Recent Q&A is deliberately absent: it stays inside policy context
 * (docs/01_PRODUCT_SPEC.md section 5).
 */
export function ReturningHome({ summary }: { summary: HomeSummary }) {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-h2 font-semibold text-primary sm:text-h1">Welcome back</h1>

      {summary.continueAction ? <NextActionCard action={summary.continueAction} /> : null}

      {summary.recommendations.length > 0 ? (
        <RecommendationHistoryCard recommendations={summary.recommendations} />
      ) : null}

      {summary.policies.length > 0 ? <PolicyLibraryCard policies={summary.policies} /> : null}

      {summary.claimsChecklist ? (
        <ConditionalClaimsCard checklist={summary.claimsChecklist} />
      ) : null}

      {summary.household ? <ProfileSummary household={summary.household} /> : null}

      {summary.vehicles ? <VehicleSummary vehicles={summary.vehicles} /> : null}
    </div>
  );
}
