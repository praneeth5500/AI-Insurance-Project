import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AppShell, MAIN_CONTENT_ID } from "@/components/layout/app-shell";
import type { NavItem } from "@/components/layout/nav-items";

vi.mock("next/navigation", () => ({
  usePathname: () => "/app/recommend",
}));

const desktopItems = [
  { href: "/app/recommend", label: "Find Insurance" },
  { href: "/app/policies", label: "My Policies" },
] as const;

const mobileItems = [
  { href: "/app/home", label: "Home", icon: "home" },
  { href: "/app/recommend", label: "Recommend", icon: "recommend" },
] as const satisfies readonly NavItem[];

function renderShell() {
  return render(
    <AppShell desktopItems={desktopItems} mobileItems={mobileItems}>
      <p>Page content</p>
    </AppShell>,
  );
}

describe("AppShell", () => {
  it("renders a single main landmark that the skip link targets", () => {
    renderShell();

    const main = screen.getByRole("main");
    expect(main.id).toBe(MAIN_CONTENT_ID);
    expect(screen.getByRole("link", { name: "Skip to main content" }).getAttribute("href")).toBe(
      `#${MAIN_CONTENT_ID}`,
    );
  });

  it("puts the skip link first in the tab order", async () => {
    const user = userEvent.setup();
    renderShell();

    await user.tab();
    expect(document.activeElement).toBe(screen.getByRole("link", { name: "Skip to main content" }));
  });

  it("marks the active destination with aria-current in both navigations", () => {
    renderShell();

    const current = screen.getAllByRole("link", { current: "page" });
    expect(current.map((link) => link.getAttribute("href"))).toEqual([
      "/app/recommend",
      "/app/recommend",
    ]);
  });

  it("labels both navigations so they are distinguishable", () => {
    renderShell();

    // Desktop and mobile navigation are both present in the DOM; CSS decides
    // which is visible, so both must carry a name.
    expect(screen.getAllByRole("navigation", { name: "Primary" })).toHaveLength(2);
  });

  it("keeps a text label on every mobile destination, never an icon alone", () => {
    renderShell();

    expect(screen.getByRole("link", { name: "Home" })).toBeDefined();
    expect(screen.getByRole("link", { name: "Recommend" })).toBeDefined();
  });
});
