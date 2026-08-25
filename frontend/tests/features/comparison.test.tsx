import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ComparisonRow } from "@/features/recommendations/comparison-row";
import { ComparisonView } from "@/features/recommendations/comparison-view";
import type {
  ComparisonOptionView,
  ComparisonView as Comparison,
  DimensionView,
} from "@/lib/api/types";

function option(n: number): ComparisonOptionView {
  return {
    productReference: `sp_${n}`,
    insurerName: `Insurer ${n} (demo)`,
    productName: `Plan ${n}`,
    sourceType: "SYNTHETIC",
    watchOut: `Watch-out ${n}.`,
  };
}

function dimension(overrides: Partial<DimensionView> = {}): DimensionView {
  return {
    factor: "copay",
    label: "Co-pay",
    values: { sp_1: "STRONG", sp_2: "NEEDS_ATTENTION" },
    notes: { sp_1: "No co-pay.", sp_2: "A share of every claim." },
    differs: true,
    isPriority: false,
    ...overrides,
  };
}

function comparison(overrides: Partial<Comparison> = {}): Comparison {
  return {
    runId: "rr_1",
    sourceType: "SYNTHETIC",
    options: [option(1), option(2)],
    priorities: ["low_copay"],
    biggestDifferences: [dimension()],
    yourPriorities: [dimension({ isPriority: true })],
    allDetails: [dimension(), dimension({ factor: "budget", label: "Budget", differs: false })],
    ...overrides,
  };
}

describe("ComparisonRow", () => {
  it("repeats each option's name so no column has to be remembered", () => {
    render(<ComparisonRow dimension={dimension()} options={[option(1), option(2)]} />);

    expect(screen.getByText(/Insurer 1 \(demo\) · Plan 1/)).toBeDefined();
    expect(screen.getByText(/Insurer 2 \(demo\) · Plan 2/)).toBeDefined();
  });

  it("states each fit in words as well as colour", () => {
    render(<ComparisonRow dimension={dimension()} options={[option(1), option(2)]} />);

    expect(screen.getByText("Strong")).toBeDefined();
    expect(screen.getByText("Needs attention")).toBeDefined();
  });

  it("marks a dimension the user said mattered", () => {
    render(
      <ComparisonRow
        dimension={dimension({ isPriority: true })}
        options={[option(1), option(2)]}
      />,
    );

    expect(screen.getByText("Your priority")).toBeDefined();
  });

  it("says so when the options do not differ", () => {
    render(
      <ComparisonRow dimension={dimension({ differs: false })} options={[option(1), option(2)]} />,
    );

    expect(screen.getByText("These options are the same here")).toBeDefined();
  });

  it("stacks on mobile and only becomes columns from sm", () => {
    const { container } = render(
      <ComparisonRow dimension={dimension()} options={[option(1), option(2)]} />,
    );

    // docs/01_PRODUCT_SPEC.md section 2.7: no wide horizontal table on a phone.
    const grid = container.querySelector("[class*='grid']") as HTMLElement;
    expect(grid.className).toContain("sm:grid-cols-2");
    expect(grid.className).not.toMatch(/(^|\s)grid-cols-2/);
  });

  it("uses three columns from sm when three options are compared", () => {
    const { container } = render(
      <ComparisonRow
        dimension={dimension({ values: { sp_1: "STRONG", sp_2: "GOOD", sp_3: "TRADE_OFF" } })}
        options={[option(1), option(2), option(3)]}
      />,
    );

    const grid = container.querySelector("[class*='grid']") as HTMLElement;
    expect(grid.className).toContain("sm:grid-cols-3");
  });
});

describe("ComparisonView", () => {
  it("follows the specified section order", () => {
    render(<ComparisonView comparison={comparison()} />);

    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings).toEqual([
      "Comparing",
      "Biggest differences",
      "Your priorities",
      "What to watch out for",
      "All details",
    ]);
  });

  it("labels the screen as demo content", () => {
    render(<ComparisonView comparison={comparison()} />);

    expect(screen.getByRole("status").textContent).toContain("invented for testing");
  });

  it("keeps all details behind a disclosure to avoid a feature matrix", async () => {
    const user = userEvent.setup();
    render(<ComparisonView comparison={comparison()} />);

    expect(screen.queryByText("Budget")).toBeNull();

    await user.click(screen.getByRole("button", { name: /Show all 2 details/ }));
    expect(screen.getByText("Budget")).toBeDefined();
  });

  it("shows every option's watch-out", () => {
    render(<ComparisonView comparison={comparison()} />);

    const section = screen
      .getByRole("heading", { name: "What to watch out for" })
      .closest("section") as HTMLElement;
    expect(within(section).getByText("Watch-out 1.")).toBeDefined();
    expect(within(section).getByText("Watch-out 2.")).toBeDefined();
  });

  it("declares no winner", () => {
    const { container } = render(<ComparisonView comparison={comparison()} />);

    const text = (container.textContent ?? "").toLowerCase();
    for (const forbidden of ["winner", "best option", "we recommend", "you should choose"]) {
      expect(text).not.toContain(forbidden);
    }
  });

  it("shows no overall score or total", () => {
    const { container } = render(<ComparisonView comparison={comparison()} />);

    const text = (container.textContent ?? "").toLowerCase();
    expect(text).not.toContain("score");
    expect(text).not.toMatch(/\d+\s*\/\s*100/);
  });

  it("handles options that are alike on everything", () => {
    render(<ComparisonView comparison={comparison({ biggestDifferences: [] })} />);

    expect(screen.getByText(/alike on every dimension we hold/)).toBeDefined();
  });

  it("omits the priorities section when none were chosen", () => {
    render(<ComparisonView comparison={comparison({ yourPriorities: [], priorities: [] })} />);

    expect(screen.queryByRole("heading", { name: "Your priorities" })).toBeNull();
  });

  it("offers a way back to the matched options", () => {
    render(<ComparisonView comparison={comparison()} />);

    expect(
      screen.getByRole("link", { name: /Back to your matched options/ }).getAttribute("href"),
    ).toBe("/app/recommendations/rr_1");
  });
});
