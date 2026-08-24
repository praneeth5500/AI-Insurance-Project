import Link from "next/link";
import { HomeModule } from "@/features/home/home-module";
import type { HouseholdSummary } from "@/lib/api/types";

/** Household profile summary (docs/01_PRODUCT_SPEC.md section 5). */
export function ProfileSummary({ household }: { household: HouseholdSummary }) {
  const { memberCount } = household;

  return (
    <HomeModule title="Household">
      <Link
        href={household.href}
        className="flex min-h-touch items-center rounded-control px-3 py-2 text-support text-secondary transition-colors duration-fast hover:bg-bg"
      >
        {memberCount === 1 ? "1 person" : `${memberCount} people`} on your profile
      </Link>
    </HomeModule>
  );
}
