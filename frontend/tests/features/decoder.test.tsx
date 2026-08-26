import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { DecoderView } from "@/features/policy/decoder-view";
import { FactCard } from "@/features/policy/fact-card";
import type { DecodedPolicy, FactCard as FactCardData } from "@/lib/api/types";

function fact(overrides: Partial<FactCardData> = {}): FactCardData {
  return {
    factKey: "ped_waiting_period_months",
    title: "How long before existing conditions are covered",
    technicalTerm: "Pre-existing disease waiting period",
    statement: "You would wait 3 years (36 months) from the start of the policy.",
    example:
      "If a policy waits 36 months before covering an existing condition, a claim for that condition in year 2 would not be paid.",
    conditions:
      "This usually requires continuous cover — a lapse can restart the clock. What counts as pre-existing is defined in the policy.",
    confidenceState: "HIGH",
    reliable: true,
    citation: {
      page: 14,
      clauseTitle: "WAITING PERIODS",
      quote: "Pre-existing diseases are covered after a waiting period of 36 months.",
      clauseText:
        "Pre-existing diseases are covered after a waiting period of 36 months of continuous coverage under this policy.",
    },
    alternatives: [],
    ...overrides,
  };
}

function decoded(overrides: Partial<DecodedPolicy> = {}): DecodedPolicy {
  return {
    policyId: "pol_1",
    displayName: "My Health Policy",
    sections: [{ key: "before-cover-starts", label: "Before Cover Starts", facts: [fact()] }],
    unknownCount: 0,
    conflictingCount: 0,
    unreadClauseCount: 0,
    schemaVersion: "policy-extraction-001",
    aiProvider: null,
    ...overrides,
  };
}

// ------------------------------------------------------------- fact card ---

describe("FactCard", () => {
  it("carries every part of the card the specification fixes", async () => {
    // docs/07_POLICY_DECODER_AI.md section 6: title, what it means, example,
    // important conditions, technical term, source.
    const user = userEvent.setup();
    render(<FactCard fact={fact()} />);

    expect(screen.getByRole("heading", { name: /How long before existing/ })).toBeDefined();
    expect(screen.getByText(/You would wait 3 years/)).toBeDefined();
    expect(screen.getByText(/Worth checking/)).toBeDefined();
    expect(screen.getByText(/Pre-existing disease waiting period/)).toBeDefined();
    expect(screen.getByRole("button", { name: /View source wording · Page 14/ })).toBeDefined();

    await user.click(screen.getByRole("button", { name: /Explain with an example/ }));
    expect(screen.getByText(/this explains how it works, not your policy/)).toBeDefined();
  });

  it("shows the wording verbatim when the source is opened", async () => {
    const user = userEvent.setup();
    render(<FactCard fact={fact()} />);

    await user.click(screen.getByRole("button", { name: /View source wording/ }));

    expect(
      screen.getByText("Pre-existing diseases are covered after a waiting period of 36 months."),
    ).toBeDefined();
  });

  it("keeps the technical term rather than replacing it", () => {
    // A reader who learns "co-payment" can use it on their insurer's site.
    render(<FactCard fact={fact()} />);

    expect(screen.getByText(/Technical term:/)).toBeDefined();
    expect(screen.getByText("Pre-existing disease waiting period")).toBeDefined();
  });

  it("says plainly when it could not find something, and why that matters", () => {
    render(
      <FactCard
        fact={fact({
          statement: null,
          confidenceState: "NOT_FOUND",
          reliable: false,
          citation: null,
        })}
      />,
    );

    expect(screen.getByText(/couldn't find this in the document/)).toBeDefined();
    expect(screen.getByText(/doesn't mean it isn't there/)).toBeDefined();
    // The card still explains what the thing is, so an unknown is informative.
    expect(screen.getByRole("button", { name: /Explain with an example/ })).toBeDefined();
    expect(screen.getByText(/No source to show/)).toBeDefined();
  });

  it("shows both readings when the policy contradicts itself, and picks neither", () => {
    render(
      <FactCard
        fact={fact({
          statement: null,
          confidenceState: "CONFLICTING",
          reliable: false,
          alternatives: [
            { page: 14, clauseTitle: null, quote: "…after 36 months…", clauseText: null },
            { page: 22, clauseTitle: null, quote: "…after 48 months…", clauseText: null },
          ],
        })}
      />,
    );

    expect(screen.getByText(/don't agree/)).toBeDefined();
    expect(screen.getByText(/We haven't picked one/)).toBeDefined();
    expect(screen.getByText("Page 14")).toBeDefined();
    expect(screen.getByText("Page 22")).toBeDefined();
  });

  it("conveys confidence in words, not colour alone", () => {
    render(<FactCard fact={fact({ confidenceState: "CONFLICTING", statement: null })} />);

    expect(screen.getByText("Your policy says two different things")).toBeDefined();
  });

  it("does not badge an ordinary reading as high confidence", () => {
    // Labelling the normal case would make genuine uncertainty harder to spot.
    render(<FactCard fact={fact()} />);

    expect(document.body.textContent).not.toContain("High confidence");
  });
});

// ----------------------------------------------------------- the report ----

describe("DecoderView", () => {
  it("leads with what it could not determine", () => {
    render(
      <DecoderView
        decoded={decoded({ unknownCount: 2, conflictingCount: 1, unreadClauseCount: 4 })}
        conversation={null}
      />,
    );

    const alerts = screen.getAllByRole("status").map((node) => node.textContent ?? "");
    const gaps = alerts.find((text) => text.includes("couldn't determine"));
    expect(gaps).toBeDefined();
    expect(gaps).toContain("2 things");
    expect(gaps).toContain("1 point is stated more than once");
    expect(gaps).toContain("4 other sections");
  });

  it("says this is a reading of the document, not advice", () => {
    render(<DecoderView decoded={decoded()} conversation={null} />);

    const notice = screen
      .getAllByRole("status")
      .find((node) => node.textContent?.includes("not advice"));
    expect(notice).toBeDefined();
    expect(notice?.textContent).toContain("check with your insurer");
  });

  it("states whether an AI model was involved", () => {
    render(<DecoderView decoded={decoded()} conversation={null} />);

    expect(screen.getByText("no AI model")).toBeDefined();
    expect(screen.getByText(/no AI model was involved/)).toBeDefined();
  });

  it("promises no claim outcome anywhere", () => {
    // docs/07_POLICY_DECODER_AI.md section 9.
    render(<DecoderView decoded={decoded({ unknownCount: 1 })} conversation={null} />);

    const text = (document.body.textContent ?? "").toLowerCase();
    for (const forbidden of ["will be approved", "guaranteed", "you will be paid"]) {
      expect(text).not.toContain(forbidden);
    }
  });

  it("renders the sections the report actually has", () => {
    render(<DecoderView decoded={decoded()} conversation={null} />);

    expect(screen.getByRole("heading", { name: "Before Cover Starts" })).toBeDefined();
  });
});
