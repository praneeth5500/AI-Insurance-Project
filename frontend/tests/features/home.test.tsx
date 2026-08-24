import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NewUserHome } from "@/features/home/new-user-home";
import { ReturningHome } from "@/features/home/returning-home";
import { DemoDataNotice } from "@/features/home/demo-data-notice";
import type { FeatureAvailability, HomeSummary } from "@/lib/api/types";

const NOTHING_AVAILABLE: FeatureAvailability = {
  healthRecommendation: "COMING_SOON",
  motorRecommendation: "COMING_SOON",
  policyDecoder: "COMING_SOON",
};

const ALL_AVAILABLE: FeatureAvailability = {
  healthRecommendation: "AVAILABLE",
  motorRecommendation: "AVAILABLE",
  policyDecoder: "AVAILABLE",
};

function summary(overrides: Partial<HomeSummary> = {}): HomeSummary {
  return {
    isNewUser: false,
    dataMode: "REAL",
    features: NOTHING_AVAILABLE,
    continueAction: null,
    recommendations: [],
    policies: [],
    claimsChecklist: null,
    household: null,
    vehicles: null,
    ...overrides,
  };
}

describe("NewUserHome", () => {
  it("leads with the specified hero and supporting copy", () => {
    render(<NewUserHome features={NOTHING_AVAILABLE} />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Insurance should make sense before you need it.",
      }),
    ).toBeDefined();
    expect(screen.getByText(/Tell us what matters to you/)).toBeDefined();
  });

  it("shows the three product cards from the specification", () => {
    render(<NewUserHome features={NOTHING_AVAILABLE} />);

    expect(screen.getByText("Health Insurance")).toBeDefined();
    expect(screen.getByText("Motor Insurance")).toBeDefined();
    expect(screen.getByText("Already have insurance?")).toBeDefined();
  });

  it("offers no link to a destination that is not built", () => {
    render(<NewUserHome features={NOTHING_AVAILABLE} />);

    // docs/12_BETA_CHECKLIST.md: no dead buttons.
    expect(screen.queryAllByRole("link")).toHaveLength(0);
    expect(screen.getAllByText("Coming soon")).toHaveLength(3);
  });

  it("links only the destinations that are available", () => {
    render(<NewUserHome features={{ ...NOTHING_AVAILABLE, healthRecommendation: "AVAILABLE" }} />);

    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(1);
    expect(links[0]?.getAttribute("href")).toBe("/app/recommend/health");
    expect(screen.getAllByText("Coming soon")).toHaveLength(2);
  });

  it("links every card once all flows exist", () => {
    render(<NewUserHome features={ALL_AVAILABLE} />);

    expect(screen.getAllByRole("link")).toHaveLength(3);
    expect(screen.queryByText("Coming soon")).toBeNull();
  });

  it("makes no insurance claim: no premium, insurer or guarantee wording", () => {
    const { container } = render(<NewUserHome features={ALL_AVAILABLE} />);

    const text = container.textContent ?? "";
    for (const forbidden of ["premium", "₹", "best policy", "guarantee", "cheapest"]) {
      expect(text.toLowerCase()).not.toContain(forbidden);
    }
  });
});

describe("ReturningHome", () => {
  it("puts continue where you left off first", () => {
    render(
      <ReturningHome
        summary={summary({
          continueAction: {
            kind: "RESUME_QUESTIONNAIRE",
            label: "Continue your health cover questions",
            href: "/app/recommend/health",
            context: "Stage 2 of 4",
            updatedAt: null,
          },
        })}
      />,
    );

    const headings = screen.getAllByRole("heading");
    expect(headings[0]?.textContent).toBe("Welcome back");
    expect(headings[1]?.textContent).toBe("Continue where you left off");
    expect(screen.getByRole("link", { name: /Continue/ }).getAttribute("href")).toBe(
      "/app/recommend/health",
    );
  });

  it("renders nothing for modules with no content", () => {
    // docs/02_UX_UI_SPEC.md section 6: do not render empty irrelevant modules.
    render(<ReturningHome summary={summary()} />);

    expect(screen.queryByText("Continue where you left off")).toBeNull();
    expect(screen.queryByText("Your matched options")).toBeNull();
    expect(screen.queryByText("Your policies")).toBeNull();
    expect(screen.queryByText("Claims preparation")).toBeNull();
    expect(screen.queryByText("Household")).toBeNull();
    expect(screen.queryByText("Vehicles")).toBeNull();
  });

  it("shows saved recommendation sessions as counts, not rankings", () => {
    render(
      <ReturningHome
        summary={summary({
          recommendations: [
            {
              id: "rr_1",
              domain: "HEALTH",
              matchCount: 10,
              createdAt: "2026-08-01T00:00:00Z",
              href: "/app/recommendations/rr_1",
            },
          ],
        })}
      />,
    );

    // `closest("div")` would stop at the heading row, so scope to the whole card.
    const card = screen.getByText("Your matched options").closest("[class*='rounded-card']")!;
    expect(within(card as HTMLElement).getByText(/10 matched options/)).toBeDefined();
    expect(card.textContent?.toLowerCase()).not.toContain("best");
  });

  it("spells out policy status rather than relying on colour", () => {
    render(
      <ReturningHome
        summary={summary({
          policies: [
            {
              id: "pol_1",
              displayName: "My policy.pdf",
              status: "PROCESSING",
              createdAt: "2026-08-01T00:00:00Z",
              href: "/app/policies/pol_1",
            },
          ],
        })}
      />,
    );

    expect(screen.getByText(/Still being read/)).toBeDefined();
  });

  it("shows claims preparation progress without predicting an outcome", () => {
    render(
      <ReturningHome
        summary={summary({
          claimsChecklist: {
            id: "crs_1",
            policyDisplayName: "My policy.pdf",
            completedItems: 2,
            totalItems: 6,
            href: "/app/policies/pol_1/claims-readiness",
          },
        })}
      />,
    );

    expect(screen.getByText(/2 of 6 steps prepared/)).toBeDefined();
    // docs/07_POLICY_DECODER_AI.md section 9: never promise claim approval.
    expect(screen.getByText(/does not decide whether a claim is accepted/)).toBeDefined();
  });

  it("shows household and vehicles only when present", () => {
    render(
      <ReturningHome
        summary={summary({
          household: { memberCount: 3, href: "/app/profile/household" },
          vehicles: { count: 1, href: "/app/profile/vehicles" },
        })}
      />,
    );

    expect(screen.getByText(/3 people on your profile/)).toBeDefined();
    expect(screen.getByText(/1 vehicle saved/)).toBeDefined();
  });

  it("keeps recent Q&A off the home screen", () => {
    const { container } = render(
      <ReturningHome
        summary={summary({
          policies: [
            {
              id: "pol_1",
              displayName: "My policy.pdf",
              status: "READY",
              createdAt: "2026-08-01T00:00:00Z",
              href: "/app/policies/pol_1",
            },
          ],
        })}
      />,
    );

    // docs/01_PRODUCT_SPEC.md section 5: Q&A stays inside policy context.
    expect(container.textContent?.toLowerCase()).not.toContain("recent question");
    expect(container.textContent?.toLowerCase()).not.toContain("q&a");
  });
});

describe("DemoDataNotice", () => {
  it("says plainly that the content is not the user's own", () => {
    render(<DemoDataNotice />);

    const notice = screen.getByRole("status");
    expect(notice.textContent).toContain("placeholder data");
    expect(notice.textContent).toContain("not your");
    expect(notice.textContent).toContain("none of it describes a real policy");
  });
});
