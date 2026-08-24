"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { NavItem } from "@/components/layout/nav-items";
import { cn } from "@/lib/ui/cn";

export type TopNavigationProps = {
  items: readonly NavItem[];
  /** Right-aligned items, e.g. Profile. */
  endItems?: readonly NavItem[];
};

/** Desktop navigation. Hidden below `md`, where MobileNavigation takes over. */
export function TopNavigation({ items, endItems = [] }: TopNavigationProps) {
  const pathname = usePathname();
  const isCurrent = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  const linkClass = (href: string) =>
    cn(
      "flex min-h-touch items-center rounded-control px-3 text-support",
      "transition-colors duration-fast ease-standard hover:bg-bg",
      isCurrent(href) ? "font-medium text-primary" : "text-secondary hover:text-primary",
    );

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-surface">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center gap-2 px-4 sm:px-6">
        <Link
          href="/"
          className="mr-2 flex min-h-touch items-center rounded-control px-1 text-body font-semibold text-primary"
        >
          Insurance
          <span className="sr-only"> — home</span>
        </Link>

        <nav aria-label="Primary" className="hidden md:block">
          <ul className="flex items-center gap-1">
            {items.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={isCurrent(item.href) ? "page" : undefined}
                  className={linkClass(item.href)}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        {endItems.length > 0 ? (
          <nav aria-label="Account" className="ml-auto hidden md:block">
            <ul className="flex items-center gap-1">
              {endItems.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    aria-current={isCurrent(item.href) ? "page" : undefined}
                    className={linkClass(item.href)}
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ) : null}
      </div>
    </header>
  );
}
