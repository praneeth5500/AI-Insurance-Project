import Link from "next/link";
import { HomeModule } from "@/features/home/home-module";
import type { VehicleSummary as VehicleSummaryData } from "@/lib/api/types";

/**
 * Vehicles, shown only when relevant (docs/02_UX_UI_SPEC.md section 6:
 * "Vehicles if relevant"). The caller passes null when the user has none.
 */
export function VehicleSummary({ vehicles }: { vehicles: VehicleSummaryData }) {
  return (
    <HomeModule title="Vehicles">
      <Link
        href={vehicles.href}
        className="flex min-h-touch items-center rounded-control px-3 py-2 text-support text-secondary transition-colors duration-fast hover:bg-bg"
      >
        {vehicles.count === 1 ? "1 vehicle" : `${vehicles.count} vehicles`} saved
      </Link>
    </HomeModule>
  );
}
