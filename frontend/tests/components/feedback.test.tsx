import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { InlineAlert } from "@/components/feedback/inline-alert";
import { ProgressStage } from "@/components/feedback/progress-stage";
import { Skeleton, SkeletonBlock } from "@/components/feedback/skeleton";

describe("InlineAlert", () => {
  it("interrupts for critical messages and stays polite otherwise", () => {
    const { rerender } = render(<InlineAlert tone="critical">Problem</InlineAlert>);
    expect(screen.getByRole("alert")).toBeDefined();

    rerender(<InlineAlert tone="info">Information</InlineAlert>);
    expect(screen.getByRole("status")).toBeDefined();
  });

  it("carries tone in wording, not colour alone", () => {
    render(<InlineAlert tone="attention">Some details are unverified.</InlineAlert>);

    // A default wording label is present even when no title is supplied.
    expect(screen.getByText("Worth checking")).toBeDefined();
  });

  it("lets a caller override the wording label", () => {
    render(<InlineAlert tone="positive" title="Saved" />);

    expect(screen.getByText("Saved")).toBeDefined();
  });
});

describe("Skeleton", () => {
  it("hides decorative placeholders from assistive technology", () => {
    const { container } = render(<Skeleton className="h-4 w-full" />);

    expect(container.firstElementChild?.getAttribute("aria-hidden")).toBe("true");
  });

  it("announces a loading message instead of silence", () => {
    render(<SkeletonBlock label="Loading your matched options" />);

    const status = screen.getByRole("status");
    expect(status.getAttribute("aria-live")).toBe("polite");
    expect(status.textContent).toContain("Loading your matched options");
  });
});

describe("EmptyState", () => {
  it("shows what would fill it and the action that does so", () => {
    render(
      <EmptyState
        title="No saved policies yet"
        description="Uploaded policies appear here."
        action={<button type="button">Upload a policy</button>}
      />,
    );

    expect(screen.getByText("No saved policies yet")).toBeDefined();
    expect(screen.getByRole("button", { name: "Upload a policy" })).toBeDefined();
  });
});

describe("ErrorState", () => {
  it("announces itself and shows the error reference", () => {
    render(
      <ErrorState
        title="We couldn't load this"
        description="Please try again."
        code="SERVICE_UNAVAILABLE"
        requestId="req_abc123"
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert.textContent).toContain("We couldn't load this");
    expect(alert.textContent).toContain("SERVICE_UNAVAILABLE");
    expect(alert.textContent).toContain("req_abc123");
  });

  it("omits the reference line when there is nothing to reference", () => {
    render(<ErrorState title="Failed" description="Try again." />);

    expect(screen.getByRole("alert").textContent).not.toContain("Error code");
  });
});

describe("ProgressStage", () => {
  const stages = ["About you", "Your cover", "What matters", "Review"] as const;

  it("announces the stage and its position as one sentence", () => {
    const { container } = render(<ProgressStage stages={stages} currentIndex={1} />);

    expect(screen.getByText("Step 2 of 4. Current stage: Your cover.")).toBeDefined();
    // The same information is also visible.
    expect(container.textContent).toContain("Your cover");
  });

  it("shows no percentage, because the flow has no fixed question count", () => {
    const { container } = render(<ProgressStage stages={stages} currentIndex={1} />);

    expect(container.textContent).not.toMatch(/%/);
  });

  it("clamps an out-of-range index rather than rendering nothing", () => {
    render(<ProgressStage stages={stages} currentIndex={99} />);

    expect(screen.getByText("Step 4 of 4. Current stage: Review.")).toBeDefined();
  });
});
