import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CompareTray } from "@/features/recommendations/compare-tray";
import { DecisionProfileSummary } from "@/features/recommendations/decision-profile-summary";
import { MatchCard } from "@/features/recommendations/match-card";
import { PriceDisplay } from "@/features/recommendations/price-display";
import { PriorityEditor } from "@/features/recommendations/priority-editor";
import { ResultsClient } from "@/features/recommendations/results-client";
import type { FitView, MatchView, RecommendationRun } from "@/lib/api/types";

afterEach(() => vi.unstubAllGlobals());

function fit(overrides: Partial<FitView> = {}): FitView {
  return { factor: "copay", label: "Co-pay", fit: "STRONG", note: "No co-pay.", ...overrides };
}

function match(index: number, overrides: Partial<MatchView> = {}): MatchView {
  return {
    id: `rc_${index}`,
    productReference: `sp_${index}`,
    insurerName: `Insurer ${index} (demo)`,
    productName: `Plan ${index}`,
    sourceType: "SYNTHETIC",
    presentationOrder: index,
    eligibilityStatus: "NOT_ASSESSED",
    highlights: [fit(), fit({ factor: "coverage", label: "Coverage", fit: "GOOD" })],
    watchOut: "Room charges are capped.",
    fits: [fit(), fit({ factor: "budget", label: "Budget", fit: "TRADE_OFF" })],
    price: {
      state: "UNAVAILABLE",
      amount: null,
      currency: null,
      sourceType: "SYNTHETIC",
      generatedAt: null,
      explanation: "These are demo products, so there is no price to show.",
    },
    ...overrides,
  };
}

function run(overrides: Partial<RecommendationRun> = {}): RecommendationRun {
  return {
    id: "rr_1",
    status: "READY",
    presentationMode: "BETA_MATCH_SET",
    sourceType: "SYNTHETIC",
    questionnaireVersion: "health-beta-draft-001",
    scoringVersion: "prototype-ordering-001",
    catalogueVersion: "synthetic-health-001",
    createdAt: "2026-08-01T00:00:00Z",
    decisionProfile: ["You're looking for cover for yourself, and you're 34."],
    priorities: ["low_copay"],
    matches: [match(1), match(2), match(3), match(4), match(5)],
    additionalMatches: [match(6), match(7), match(8), match(9), match(10)],
    canShowMore: true,
    reordered: [],
    ...overrides,
  };
}

function mockApi(body: unknown, ok = true, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue({ ok, status, json: async () => body });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

// --------------------------------------------------------------- the card --

describe("MatchCard", () => {
  const props = {
    match: match(1),
    position: 1,
    selected: false,
    onToggleCompare: vi.fn(),
    compareDisabled: false,
    moved: false,
    detailHref: "/app/products/sp_1?from=rr_1",
  };

  it("names the insurer and product and marks it as demo content", () => {
    render(<MatchCard {...props} />);

    expect(screen.getByText(/Insurer 1 \(demo\) · Plan 1/)).toBeDefined();
    expect(screen.getByText("Demo product")).toBeDefined();
  });

  it("shows the strengths and exactly one watch-out", () => {
    render(<MatchCard {...props} />);

    expect(screen.getByText("Watch out for")).toBeDefined();
    expect(screen.getByText("Room charges are capped.")).toBeDefined();
  });

  it("shows no overall score", () => {
    const { container } = render(<MatchCard {...props} />);

    const text = (container.textContent ?? "").toLowerCase();
    expect(text).not.toMatch(/\d+\s*\/\s*100/);
    expect(text).not.toContain("score");
  });

  it("keeps the full category fit behind 'Why this matches'", async () => {
    const user = userEvent.setup();
    render(<MatchCard {...props} />);

    const trigger = screen.getByRole("button", { name: /Why this matches/ });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByText("Budget")).toBeNull();

    await user.click(trigger);
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText("Budget")).toBeDefined();
  });

  it("states fit in words, not colour alone", async () => {
    const user = userEvent.setup();
    render(<MatchCard {...props} />);

    await user.click(screen.getByRole("button", { name: /Why this matches/ }));
    expect(screen.getAllByText("Strong").length).toBeGreaterThan(0);
    expect(screen.getByText("Trade-off")).toBeDefined();
  });

  it("links to the detail screen", () => {
    render(<MatchCard {...props} />);

    const link = screen.getByRole("link", { name: /View details/ });
    expect(link.getAttribute("href")).toBe("/app/products/sp_1?from=rr_1");
  });

  it("disables compare once the limit is reached", () => {
    render(<MatchCard {...props} compareDisabled />);

    expect((screen.getByRole("checkbox") as HTMLInputElement).disabled).toBe(true);
  });
});

// -------------------------------------------------------------- the price --

describe("PriceDisplay", () => {
  it("says plainly when there is no price rather than inventing one", () => {
    render(<PriceDisplay price={match(1).price} />);

    expect(screen.getByText("No price available")).toBeDefined();
    expect(screen.getByText(/no price to show/)).toBeDefined();
  });

  it("never shows an amount without its state", () => {
    render(
      <PriceDisplay
        price={{
          state: "INDICATIVE",
          amount: 12000,
          currency: "INR",
          sourceType: "PARTNER_API",
          generatedAt: "2026-08-01T00:00:00Z",
          explanation: "Before underwriting.",
        }}
      />,
    );

    expect(screen.getByText("Indicative premium")).toBeDefined();
    expect(screen.getByText("₹12,000")).toBeDefined();
    expect(screen.getByText("Before underwriting.")).toBeDefined();
  });
});

// ------------------------------------------------------------ the results --

describe("ResultsClient", () => {
  it("leads with what we learned, then the matched options", () => {
    render(<ResultsClient initialRun={run()} />);

    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings[0]).toBe("What we learned about you");
    expect(headings[1]).toBe("Matched options");
  });

  it("shows 5 options and reveals 5 more on request", async () => {
    const user = userEvent.setup();
    render(<ResultsClient initialRun={run()} />);

    expect(screen.getAllByRole("checkbox", { name: /Compare/ })).toHaveLength(5);

    await user.click(screen.getByRole("button", { name: "See 5 more matches" }));
    expect(screen.getAllByRole("checkbox", { name: /Compare/ })).toHaveLength(10);
    expect(screen.queryByRole("button", { name: /See 5 more/ })).toBeNull();
  });

  it("labels the whole screen as demo content", () => {
    render(<ResultsClient initialRun={run()} />);

    const notice = screen.getAllByRole("status")[0]!;
    expect(notice.textContent).toContain("invented for testing");
    expect(notice.textContent).toContain("nothing here is a recommendation to buy");
  });

  it("says there is no single best option", () => {
    render(<ResultsClient initialRun={run()} />);

    expect(screen.getByText(/no single best option/)).toBeDefined();
  });

  it("caps comparison at three", async () => {
    const user = userEvent.setup();
    render(<ResultsClient initialRun={run()} />);

    const boxes = screen.getAllByRole("checkbox", { name: /Compare/ });
    for (const box of boxes.slice(0, 3)) await user.click(box);

    expect(screen.getByText("3 of 3 selected to compare")).toBeDefined();
    expect((boxes[3] as HTMLInputElement).disabled).toBe(true);
  });

  it("lets a selection be removed from the tray", async () => {
    const user = userEvent.setup();
    render(<ResultsClient initialRun={run()} />);

    await user.click(screen.getAllByRole("checkbox", { name: /Compare/ })[0]!);
    expect(screen.getByText("1 of 3 selected to compare")).toBeDefined();

    await user.click(screen.getByRole("button", { name: /Remove Insurer 1/ }));
    expect(screen.queryByText(/selected to compare/)).toBeNull();
  });

  it("needs two options before comparison is offered", async () => {
    const user = userEvent.setup();
    render(<ResultsClient initialRun={run()} />);

    const boxes = screen.getAllByRole("checkbox", { name: /Compare/ });
    await user.click(boxes[0]!);
    expect(screen.queryByRole("link", { name: "Compare side by side" })).toBeNull();
    expect(screen.getByText("Pick one more option to compare.")).toBeDefined();

    await user.click(boxes[1]!);
    const link = screen.getByRole("link", { name: "Compare side by side" });
    expect(link.getAttribute("href")).toBe("/app/recommendations/rr_1/compare?options=sp_1,sp_2");
  });

  it("sends changed priorities to the server and explains what moved", async () => {
    const user = userEvent.setup();
    const reordered = run({
      priorities: ["lower_premium"],
      reordered: ["sp_3"],
    });
    const fetchMock = mockApi(reordered);

    render(<ResultsClient initialRun={run()} />);

    await user.click(screen.getByRole("checkbox", { name: /Lower premium/ }));
    await user.click(screen.getByRole("button", { name: "Update my matches" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/recommendation-runs/rr_1/priorities");
    expect(init.method).toBe("PATCH");

    // docs/02_UX_UI_SPEC.md section 9: explain why the results changed.
    const notice = await screen.findByText(/1 option moved/);
    expect(notice).toBeDefined();
  });

  it("says so when a priority change does not move anything", async () => {
    const user = userEvent.setup();
    mockApi(run({ priorities: ["broad_coverage"], reordered: [] }));

    render(<ResultsClient initialRun={run()} />);

    await user.click(screen.getByRole("checkbox", { name: /Broad coverage/ }));
    await user.click(screen.getByRole("button", { name: "Update my matches" }));

    expect(await screen.findByText(/The order didn't change/)).toBeDefined();
  });

  it("surfaces a failure to reorder without losing the results", async () => {
    const user = userEvent.setup();
    mockApi(
      {
        error: {
          code: "SERVICE_UNAVAILABLE",
          message: "The service is temporarily unavailable.",
          retryable: true,
          requestId: "req_1",
        },
      },
      false,
      503,
    );

    render(<ResultsClient initialRun={run()} />);

    await user.click(screen.getByRole("checkbox", { name: /Lower premium/ }));
    await user.click(screen.getByRole("button", { name: "Update my matches" }));

    expect((await screen.findByRole("alert")).textContent).toContain("temporarily unavailable");
    expect(screen.getAllByRole("checkbox", { name: /Compare/ })).toHaveLength(5);
  });
});

// ----------------------------------------------------- the priority editor --

describe("PriorityEditor", () => {
  it("does not expose raw weights", () => {
    const { container } = render(
      <PriorityEditor priorities={["low_copay"]} onApply={vi.fn()} saving={false} />,
    );

    const text = (container.textContent ?? "").toLowerCase();
    expect(text).not.toContain("weight");
    expect(text).not.toContain("multiplier");
    expect(text).not.toMatch(/\d\.\d/);
  });

  it("caps the choice at three", async () => {
    const user = userEvent.setup();
    render(<PriorityEditor priorities={[]} onApply={vi.fn()} saving={false} />);

    for (const label of ["Lower premium", "Low co-pay", "Short waiting periods"]) {
      await user.click(screen.getByRole("checkbox", { name: label }));
    }

    expect(
      (screen.getByRole("checkbox", { name: "Broad coverage" }) as HTMLInputElement).disabled,
    ).toBe(true);
  });

  it("stays disabled until something actually changes", async () => {
    const user = userEvent.setup();
    render(<PriorityEditor priorities={["low_copay"]} onApply={vi.fn()} saving={false} />);

    const apply = screen.getByRole("button", { name: "Update my matches" });
    expect((apply as HTMLButtonElement).disabled).toBe(true);

    await user.click(screen.getByRole("checkbox", { name: "Broad coverage" }));
    expect((apply as HTMLButtonElement).disabled).toBe(false);
  });
});

describe("DecisionProfileSummary", () => {
  it("renders nothing when there is nothing to say", () => {
    const { container } = render(<DecisionProfileSummary lines={[]} />);

    expect(container.firstChild).toBeNull();
  });

  it("lists each statement so it can be checked", () => {
    render(<DecisionProfileSummary lines={["You're 34.", "You'd rather not pay a co-pay."]} />);

    const list = screen.getByRole("list");
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);
  });
});

describe("CompareTray", () => {
  it("renders nothing when nothing is selected", () => {
    const { container } = render(
      <CompareTray selected={[]} onRemove={vi.fn()} onClear={vi.fn()} runId="rr_1" />,
    );

    expect(container.firstChild).toBeNull();
  });
});
