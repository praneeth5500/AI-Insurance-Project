import Link from "next/link";
import { HomeModule } from "@/features/home/home-module";
import { formatDate } from "@/features/home/format";
import type { PolicySummary } from "@/lib/api/types";

const STATUS_LABEL: Record<string, string> = {
  READY: "Ready to read",
  PROCESSING: "Still being read",
  FAILED: "Could not be read",
};

/** Uploaded policies (docs/01_PRODUCT_SPEC.md section 5). */
export function PolicyLibraryCard({ policies }: { policies: readonly PolicySummary[] }) {
  return (
    <HomeModule title="Your policies">
      <ul className="flex flex-col gap-2">
        {policies.map((policy) => (
          <li key={policy.id}>
            <Link
              href={policy.href}
              className="flex min-h-touch flex-col justify-center rounded-control px-3 py-2 transition-colors duration-fast hover:bg-bg"
            >
              <span className="text-support font-medium text-primary">{policy.displayName}</span>
              <span className="text-meta text-secondary">
                {/* Status is spelled out, never conveyed by colour alone. */}
                {STATUS_LABEL[policy.status] ?? policy.status} · {formatDate(policy.createdAt)}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </HomeModule>
  );
}
