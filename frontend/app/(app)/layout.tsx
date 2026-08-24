import { AppShell } from "@/components/layout/app-shell";
import type { NavItem } from "@/components/layout/nav-items";
import { requireUser } from "@/lib/auth/session";

/**
 * The authenticated area.
 *
 * `requireUser()` runs on every request to a route under this layout and asks
 * the API whether the session is still valid, unexpired, unrevoked and still
 * allowlisted. The middleware cookie check is only a fast path — this is the
 * actual gate.
 */

// Navigation labels from docs/02_UX_UI_SPEC.md section 4. Destinations that
// have not been built yet are not listed: an invited beta user should never
// meet a dead link.
const DESKTOP_ITEMS: readonly NavItem[] = [{ href: "/app/home", label: "Home" }];
const MOBILE_ITEMS: readonly NavItem[] = [{ href: "/app/home", label: "Home", icon: "home" }];

export const dynamic = "force-dynamic";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  await requireUser();

  return (
    <AppShell desktopItems={DESKTOP_ITEMS} mobileItems={MOBILE_ITEMS}>
      {children}
    </AppShell>
  );
}
