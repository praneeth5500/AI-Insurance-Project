"use client";

import { FileText, HelpCircle, Home, Search, User } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { NavIconName, NavItem } from "@/components/layout/nav-items";
import { cn } from "@/lib/ui/cn";

/** Resolves the serialisable icon name from a NavItem to a component. */
const ICONS: Record<NavIconName, LucideIcon> = {
  home: Home,
  recommend: Search,
  policies: FileText,
  profile: User,
  help: HelpCircle,
};

export type MobileNavigationProps = {
  items: readonly NavItem[];
};

/**
 * Bottom navigation for small screens. Hidden from `md` up.
 *
 * Every target is at least 44px tall and carries an icon plus a text label —
 * the label is never dropped in favour of an icon alone.
 */
export function MobileNavigation({ items }: MobileNavigationProps) {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Primary"
      className={cn(
        "fixed inset-x-0 bottom-0 z-30 border-t border-border bg-surface md:hidden",
        // Keeps the bar clear of the iOS home indicator.
        "pb-[env(safe-area-inset-bottom)]",
      )}
    >
      <ul className="flex items-stretch">
        {items.map(({ href, label, icon }) => {
          const current = pathname === href || pathname.startsWith(`${href}/`);
          const Icon = icon ? ICONS[icon] : null;
          return (
            <li key={href} className="flex-1">
              <Link
                href={href}
                aria-current={current ? "page" : undefined}
                className={cn(
                  "flex min-h-touch flex-col items-center justify-center gap-0.5 px-1 py-2",
                  "text-meta transition-colors duration-fast ease-standard",
                  current ? "font-medium text-accent" : "text-secondary",
                )}
              >
                {Icon ? <Icon className="size-5" aria-hidden="true" /> : null}
                <span>{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
