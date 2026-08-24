import Link from "next/link";
import { HomeModule } from "@/features/home/home-module";
import type { ClaimsChecklistSummary } from "@/lib/api/types";

/**
 * An in-progress claims checklist, shown only when one exists
 * (docs/02_UX_UI_SPEC.md section 6: "Active Claims Checklist if present").
 *
 * Reports preparation progress only. It never suggests a claim will be
 * approved — the product does not predict claim outcomes
 * (docs/07_POLICY_DECODER_AI.md section 9).
 */
export function ConditionalClaimsCard({ checklist }: { checklist: ClaimsChecklistSummary }) {
  const { completedItems, totalItems } = checklist;

  return (
    <HomeModule title="Claims preparation">
      <Link
        href={checklist.href}
        className="flex min-h-touch flex-col justify-center rounded-control px-3 py-2 transition-colors duration-fast hover:bg-bg"
      >
        <span className="text-support font-medium text-primary">{checklist.policyDisplayName}</span>
        <span className="text-meta text-secondary">
          {completedItems} of {totalItems} steps prepared
        </span>
      </Link>
      <p className="text-meta text-secondary">
        A checklist helps you prepare. It does not decide whether a claim is accepted.
      </p>
    </HomeModule>
  );
}
