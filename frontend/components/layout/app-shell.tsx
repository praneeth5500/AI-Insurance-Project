import type { ReactNode } from "react";
import { MobileNavigation } from "@/components/layout/mobile-navigation";
import type { NavItem } from "@/components/layout/nav-items";
import { TopNavigation } from "@/components/layout/top-navigation";

/**
 * The responsive application frame: top navigation on desktop, bottom
 * navigation on mobile, and a single `main` landmark between them.
 *
 * The shell owns no routing decisions — the navigation item sets are passed
 * in by the route group that uses it.
 */
export type AppShellProps = {
  desktopItems: readonly NavItem[];
  desktopEndItems?: readonly NavItem[];
  mobileItems: readonly NavItem[];
  children: ReactNode;
};

export const MAIN_CONTENT_ID = "main-content";

export function AppShell({
  desktopItems,
  desktopEndItems = [],
  mobileItems,
  children,
}: AppShellProps) {
  return (
    <div className="flex min-h-dvh flex-col bg-bg">
      {/* First tab stop: lets keyboard users skip the navigation. */}
      <a
        href={`#${MAIN_CONTENT_ID}`}
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-control focus:bg-surface focus:px-4 focus:py-3 focus:text-support focus:font-medium focus:text-primary focus:shadow-raised"
      >
        Skip to main content
      </a>

      <TopNavigation items={desktopItems} endItems={desktopEndItems} />

      <main
        id={MAIN_CONTENT_ID}
        // Bottom padding clears the fixed mobile navigation bar.
        className="flex-1 pb-24 md:pb-0"
      >
        {children}
      </main>

      <MobileNavigation items={mobileItems} />
    </div>
  );
}
