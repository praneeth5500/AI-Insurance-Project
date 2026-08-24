import Link from "next/link";
import { HomeModule } from "@/features/home/home-module";
import { formatDate } from "@/features/home/format";
import type { RecommendationSummary } from "@/lib/api/types";

const DOMAIN_LABEL: Record<RecommendationSummary["domain"], string> = {
  HEALTH: "Health cover",
  MOTOR: "Motor cover",
};

/** Saved recommendation sessions (docs/01_PRODUCT_SPEC.md section 5). */
export function RecommendationHistoryCard({
  recommendations,
}: {
  recommendations: readonly RecommendationSummary[];
}) {
  return (
    <HomeModule title="Your matched options">
      <ul className="flex flex-col gap-2">
        {recommendations.map((run) => (
          <li key={run.id}>
            <Link
              href={run.href}
              className="flex min-h-touch flex-col justify-center rounded-control px-3 py-2 transition-colors duration-fast hover:bg-bg"
            >
              <span className="text-support font-medium text-primary">
                {DOMAIN_LABEL[run.domain]}
              </span>
              {/* A count of options, never a ranking or a recommendation. */}
              <span className="text-meta text-secondary">
                {run.matchCount} matched options · {formatDate(run.createdAt)}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </HomeModule>
  );
}
