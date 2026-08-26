import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProcessingStatus } from "@/features/policy/processing-status";
import { UploadZone } from "@/features/policy/upload-zone";
import type { UploadedPolicy } from "@/lib/api/types";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh: vi.fn(), replace: vi.fn() }),
}));

afterEach(() => {
  vi.unstubAllGlobals();
  push.mockClear();
});

function policy(overrides: Partial<UploadedPolicy> = {}): UploadedPolicy {
  return {
    id: "pol_1",
    displayName: "My Health Policy",
    domain: null,
    status: "READING",
    statusLabel: "Reading document",
    stages: [
      { key: "RECEIVED", label: "Uploaded", state: "DONE" },
      { key: "READING", label: "Reading document", state: "CURRENT" },
      { key: "FINDING_CLAUSES", label: "Finding important clauses", state: "PENDING" },
      { key: "BUILDING_SUMMARY", label: "Building summary", state: "PENDING" },
      { key: "PREPARING_QA", label: "Preparing Q&A", state: "PENDING" },
      { key: "READY", label: "Ready", state: "PENDING" },
    ],
    isReady: false,
    isFailed: false,
    failureMessage: null,
    documents: [
      {
        id: "doc_1",
        filename: "policy.pdf",
        mimeType: "application/pdf",
        sizeBytes: 120_000,
        pageCount: 12,
        createdAt: "2026-08-01T00:00:00Z",
      },
    ],
    createdAt: "2026-08-01T00:00:00Z",
    readyAt: null,
    ...overrides,
  };
}

// ------------------------------------------------------------ upload zone ---

describe("UploadZone", () => {
  it("names the supported types and the size limit before anything is chosen", () => {
    render(<UploadZone />);

    expect(screen.getByText(/PDF, or a clear photo or scan in PNG or JPEG/)).toBeDefined();
    expect(screen.getByText(/20 MB/)).toBeDefined();
  });

  it("keeps a real file input, so the control stays keyboard-operable", () => {
    const { container } = render(<UploadZone />);

    const input = container.querySelector('input[type="file"]');
    expect(input).not.toBeNull();
    expect(input?.getAttribute("accept")).toContain("application/pdf");
  });

  it("makes the privacy claim only in terms the backend actually supports", () => {
    render(<UploadZone />);

    // docs/02_UX_UI_SPEC.md section 13 allows this copy "only if
    // implementation supports it": private storage, and a delete path.
    const line = screen.getByText(/stored privately/);
    expect(line.textContent).toContain("delete it at any time");
  });
});

// ------------------------------------------------------ processing status ---

describe("ProcessingStatus", () => {
  it("shows named stages and never a percentage", () => {
    render(<ProcessingStatus policy={policy()} />);

    // Twice on purpose: once in the stage list, once in the live region that
    // announces the change to a screen reader.
    expect(screen.getAllByText("Reading document")).toHaveLength(2);
    expect(screen.getByText("Preparing Q&A")).toBeDefined();
    expect(document.body.textContent).not.toMatch(/\d+\s*%/);
  });

  it("tells the reader they can leave and come back", () => {
    render(<ProcessingStatus policy={policy()} />);

    expect(screen.getByText(/close this page and come back/)).toBeDefined();
  });

  it("states what failed and what the reader can do about it", () => {
    render(
      <ProcessingStatus
        policy={policy({
          status: "FAILED",
          isFailed: true,
          failureMessage:
            "That PDF is password-protected, so we can't open it. Please save an unlocked copy and upload that instead.",
        })}
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert.textContent).toContain("password-protected");
    expect(alert.textContent).toContain("upload that instead");
  });

  it("carries each stage's state in text, not by icon alone", () => {
    // docs/02_UX_UI_SPEC.md section 16: never rely on colour or shape alone.
    render(<ProcessingStatus policy={policy()} />);

    expect(screen.getAllByText("done").length).toBeGreaterThan(0);
    expect(screen.getByText("in progress")).toBeDefined();
    expect(screen.getAllByText("not started").length).toBeGreaterThan(0);
  });

  it("offers a delete path and says what deleting actually does", () => {
    render(<ProcessingStatus policy={policy()} />);

    expect(screen.getByRole("button", { name: "Delete this policy" })).toBeDefined();
    expect(screen.getByText(/nothing about what the document said/)).toBeDefined();
  });
});
