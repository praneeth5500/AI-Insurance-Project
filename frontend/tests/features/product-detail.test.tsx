import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PolicyFact } from "@/features/product/policy-fact";
import { ProductDetailView } from "@/features/product/product-detail-view";
import { SaveButton } from "@/features/product/save-button";
import type { FitView, ProductDetail, ProductFactView } from "@/lib/api/types";

afterEach(() => vi.unstubAllGlobals());

function mockApi(body: unknown, ok = true, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue({ ok, status, json: async () => body });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function fact(overrides: Partial<ProductFactView> = {}): ProductFactView {
  return {
    key: "copay",
    label: "Co-pay",
    value: "No share of the bill is passed back to you.",
    example: "If a policy has a 10% co-pay and a bill comes to ₹1 lakh, you pay ₹10,000.",
    hasSource: false,
    sourceNote: "This is a demo product, so there is no policy document to quote.",
    ...overrides,
  };
}

function fit(overrides: Partial<FitView> = {}): FitView {
  return { factor: "copay", label: "Co-pay", fit: "STRONG", note: "No co-pay.", ...overrides };
}

function product(overrides: Partial<ProductDetail> = {}): ProductDetail {
  return {
    reference: "sp_1",
    insurerName: "Meridian Mutual (demo)",
    productName: "Core Health",
    sourceType: "SYNTHETIC",
    highlights: [fit(), fit({ factor: "coverage", label: "Coverage", fit: "GOOD" })],
    watchOut: "Room charges are capped.",
    fits: [fit(), fit({ factor: "budget", label: "Budget", fit: "TRADE_OFF" })],
    sections: [{ key: "your-costs", label: "Your Costs", facts: [fact()] }],
    sourceDocuments: [],
    sourceDocumentsNote: "No policy document exists for a demo product.",
    provenance: {
      sourceType: "SYNTHETIC",
      catalogueVersion: "synthetic-health-001",
      verifiedAt: null,
      explanation: "This product is synthetic: it was invented to test this screen.",
    },
    saved: false,
    ...overrides,
  };
}

// -------------------------------------------------------------- the fact ---

describe("PolicyFact", () => {
  it("offers both affordances the specification requires", () => {
    render(<PolicyFact fact={fact()} />);

    expect(screen.getByRole("button", { name: /Explain with example/ })).toBeDefined();
    expect(screen.getByRole("button", { name: /View source wording/ })).toBeDefined();
  });

  it("keeps the example collapsed until asked", async () => {
    const user = userEvent.setup();
    render(<PolicyFact fact={fact()} />);

    const trigger = screen.getByRole("button", { name: /Explain with example/ });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");

    await user.click(trigger);
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText(/10% co-pay/)).toBeDefined();
  });

  it("labels an example as an example every time", async () => {
    const user = userEvent.setup();
    render(<PolicyFact fact={fact()} />);

    await user.click(screen.getByRole("button", { name: /Explain with example/ }));

    // docs/12_BETA_CHECKLIST.md: examples clearly labeled as examples.
    expect(
      screen.getByText(/Example — explains how this works, not this policy's terms/),
    ).toBeDefined();
  });

  it("says plainly that no source wording exists rather than inventing one", async () => {
    const user = userEvent.setup();
    render(<PolicyFact fact={fact()} />);

    await user.click(screen.getByRole("button", { name: /View source wording/ }));

    expect(screen.getByText("No source wording available")).toBeDefined();
    expect(screen.getByText(/no policy document to quote/)).toBeDefined();
  });

  it("still offers the source control when there is nothing to show", () => {
    // Hiding the control would hide the fact that nothing is verified.
    render(<PolicyFact fact={fact({ hasSource: false })} />);

    expect(screen.getByRole("button", { name: /View source wording/ })).toBeDefined();
  });
});

// -------------------------------------------------------------- the save ---

describe("SaveButton", () => {
  it("saves and reflects the server's answer", async () => {
    const user = userEvent.setup();
    const fetchMock = mockApi({ reference: "sp_1", saved: true });
    render(<SaveButton reference="sp_1" initiallySaved={false} />);

    await user.click(screen.getByRole("button", { name: /Save this option/ }));

    await waitFor(() => expect(screen.getByRole("button", { name: /Saved/ })).toBeDefined());
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/v1/products/sp_1/saved");
    expect(init.method).toBe("PUT");
  });

  it("unsaves with a DELETE", async () => {
    const user = userEvent.setup();
    const fetchMock = mockApi({ reference: "sp_1", saved: false });
    render(<SaveButton reference="sp_1" initiallySaved />);

    await user.click(screen.getByRole("button", { name: /Saved/ }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect((fetchMock.mock.calls[0] as [string, RequestInit])[1].method).toBe("DELETE");
  });

  it("does not pretend a failed save worked", async () => {
    const user = userEvent.setup();
    mockApi(
      { error: { code: "X", message: "nope", retryable: true, requestId: null } },
      false,
      500,
    );
    render(<SaveButton reference="sp_1" initiallySaved={false} />);

    await user.click(screen.getByRole("button", { name: /Save this option/ }));

    expect((await screen.findByRole("alert")).textContent).toContain("couldn't update");
    expect(screen.getByRole("button", { name: /Save this option/ })).toBeDefined();
  });
});

// ------------------------------------------------------------ the screen ---

describe("ProductDetailView", () => {
  it("leads with the insurer and product", () => {
    render(<ProductDetailView product={product()} runId="rr_1" />);

    expect(
      screen.getByRole("heading", { level: 1, name: /Meridian Mutual \(demo\) · Core Health/ }),
    ).toBeDefined();
  });

  it("puts the watch-out beside the strengths, not below the fold", () => {
    render(<ProductDetailView product={product()} runId="rr_1" />);

    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings.slice(0, 2)).toEqual(["Why this matches you", "What to watch out for"]);
  });

  it("makes Compare the primary action and offers Save", () => {
    render(<ProductDetailView product={product()} runId="rr_1" />);

    expect(screen.getByRole("link", { name: "Compare this policy" }).getAttribute("href")).toBe(
      "/app/recommendations/rr_1",
    );
    expect(screen.getByRole("button", { name: /Save this option/ })).toBeDefined();
  });

  it("offers no checkout and says so", () => {
    const { container } = render(<ProductDetailView product={product()} runId="rr_1" />);

    // docs/12_BETA_CHECKLIST.md: no fake checkout.
    const text = (container.textContent ?? "").toLowerCase();
    for (const forbidden of ["buy now", "get a quote", "purchase", "checkout", "apply now"]) {
      expect(text).not.toContain(forbidden);
    }
    expect(screen.getByText(/doesn't sell insurance/)).toBeDefined();
  });

  it("labels the product as demo content", () => {
    render(<ProductDetailView product={product()} runId="rr_1" />);

    expect(screen.getAllByRole("status")[0]!.textContent).toContain("synthetic");
  });

  it("shows provenance rather than implying the data is verified", () => {
    render(<ProductDetailView product={product()} runId="rr_1" />);

    expect(screen.getByText("Not verified — demo data")).toBeDefined();
    expect(screen.getByText("synthetic-health-001")).toBeDefined();
  });

  it("keeps a Source Documents section that explains its emptiness", () => {
    render(<ProductDetailView product={product()} runId="rr_1" />);

    const section = screen
      .getByRole("heading", { name: "Source Documents" })
      .closest("section") as HTMLElement;
    expect(within(section).getByText(/No policy document exists/)).toBeDefined();
  });

  it("renders each policy section from the specification", () => {
    render(<ProductDetailView product={product()} runId="rr_1" />);

    expect(screen.getByRole("heading", { name: "Your Costs" })).toBeDefined();
    expect(screen.getByRole("heading", { name: "Policy Details" })).toBeDefined();
  });

  it("shows no overall score", () => {
    const { container } = render(<ProductDetailView product={product()} runId="rr_1" />);

    const text = (container.textContent ?? "").toLowerCase();
    expect(text).not.toContain("score");
    expect(text).not.toMatch(/\d+\s*\/\s*100/);
  });

  it("works as a standalone URL with no run to return to", () => {
    render(<ProductDetailView product={product()} runId={null} />);

    expect(screen.queryByRole("link", { name: "Compare this policy" })).toBeNull();
    expect(screen.getByRole("button", { name: /Save this option/ })).toBeDefined();
  });
});
