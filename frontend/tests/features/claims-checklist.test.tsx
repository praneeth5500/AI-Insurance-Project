import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ClaimsChecklistView } from "@/features/policy/claims-checklist";
import type { ClaimsChecklist } from "@/lib/api/types";

afterEach(() => vi.unstubAllGlobals());

function checklist(overrides: Partial<ClaimsChecklist> = {}): ClaimsChecklist {
  return {
    policyId: "pol_1",
    displayName: "My Health Policy",
    groups: [
      {
        origin: "POLICY_SPECIFIC",
        label: "Your policy asks for this",
        explanation:
          "Read from your own policy document. Each one links to the wording it came from.",
        items: [
          {
            id: "cci_1",
            label: "Tell your insurer within the time your policy states",
            description: "Your policy sets out when the insurer must be told about a claim.",
            completed: false,
            userNote: null,
            source: {
              page: 21,
              clauseTitle: "CLAIM PROCEDURE",
              clauseText: "The insurer must receive intimation within 24 hours of admission.",
            },
          },
        ],
      },
      {
        origin: "GENERAL_PREPARATION",
        label: "Generally worth having",
        explanation:
          "Not from your policy — these are things insurers commonly ask for. Your policy may not require them, and it may require things not listed here.",
        items: [
          {
            id: "cci_2",
            label: "Photo ID for everyone on the policy",
            description: "Insurers generally ask for identification matching the names.",
            completed: false,
            userNote: null,
            source: null,
          },
        ],
      },
      {
        origin: "CONFIRM_WITH_INSURER",
        label: "Ask your insurer",
        explanation: "Your document doesn't say, and we won't guess.",
        items: [
          {
            id: "cci_3",
            label: "How soon you must tell them about a claim",
            description: "Ask for the notification window in writing.",
            completed: false,
            userNote: null,
            source: null,
          },
        ],
      },
    ],
    completedCount: 0,
    totalCount: 3,
    disclaimer:
      "Working through this doesn't guarantee a claim will be paid, and nothing here predicts what your insurer will decide.",
    ...overrides,
  };
}

describe("ClaimsChecklistView", () => {
  it("renders the three kinds of item as separate sections", () => {
    // docs/07_POLICY_DECODER_AI.md section 10: do not blend them. A single
    // list with small labels is blending with extra steps.
    render(<ClaimsChecklistView initial={checklist()} />);

    expect(screen.getByRole("heading", { name: "Your policy asks for this" })).toBeDefined();
    expect(screen.getByRole("heading", { name: "Generally worth having" })).toBeDefined();
    expect(screen.getByRole("heading", { name: "Ask your insurer" })).toBeDefined();
  });

  it("says of the general group that it is not from the policy", () => {
    render(<ClaimsChecklistView initial={checklist()} />);

    expect(screen.getByText(/Not from your policy/)).toBeDefined();
    expect(screen.getByText(/may not require them/)).toBeDefined();
  });

  it("offers source wording only on items read from the policy", async () => {
    const user = userEvent.setup();
    render(<ClaimsChecklistView initial={checklist()} />);

    const sourceButtons = screen.getAllByRole("button", { name: /View source wording/ });
    expect(sourceButtons).toHaveLength(1);

    await user.click(sourceButtons[0]!);
    expect(
      screen.getByText("The insurer must receive intimation within 24 hours of admission."),
    ).toBeDefined();
  });

  it("states that it does not predict a claim outcome", () => {
    render(<ClaimsChecklistView initial={checklist()} />);

    const notice = screen.getByRole("status");
    expect(notice.textContent).toContain("doesn't guarantee a claim will be paid");
    expect(notice.textContent).toContain("nothing here predicts");
  });

  it("promises no outcome anywhere on the page", () => {
    render(<ClaimsChecklistView initial={checklist()} />);

    const text = (document.body.textContent ?? "").toLowerCase();
    expect(text).not.toContain("will be approved");
    expect(text).not.toContain("you will be paid");
  });

  it("ticks an item off and reflects the server's new count", async () => {
    const updated = checklist({ completedCount: 1 });
    updated.groups[0]!.items[0]!.completed = true;
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => updated });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<ClaimsChecklistView initial={checklist()} />);

    await user.click(screen.getAllByRole("checkbox")[0]!);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toContain("/claims-checklist/cci_1");
    expect(JSON.parse(init.body as string)).toEqual({ completed: true });
    await waitFor(() => expect(screen.getByText(/1 of 3 done/)).toBeDefined());
  });

  it("saves a note when the field loses focus, not on every keystroke", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => checklist() });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<ClaimsChecklistView initial={checklist()} />);

    const note = screen.getAllByLabelText("Your note")[0]!;
    await user.type(note, "policy 12345");
    expect(fetchMock).not.toHaveBeenCalled();

    await user.tab();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(JSON.parse(fetchMock.mock.calls[0]![1].body as string)).toEqual({
      note: "policy 12345",
    });
  });

  it("ticks immediately rather than waiting for the server", async () => {
    // Someone working through this at an admission desk is not on a good
    // connection; a checkbox that waits for a round trip feels broken.
    let resolve: (value: unknown) => void = () => {};
    const pending = new Promise((r) => {
      resolve = r;
    });
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(pending));
    const user = userEvent.setup();
    render(<ClaimsChecklistView initial={checklist()} />);

    const box = screen.getAllByRole("checkbox")[0]!;
    await user.click(box);

    expect((box as HTMLInputElement).checked).toBe(true);
    expect(screen.getByText(/1 of 3 done/)).toBeDefined();
    resolve({ ok: true, status: 200, json: async () => checklist({ completedCount: 1 }) });
  });

  it("undoes the tick and says so when saving fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    const user = userEvent.setup();
    render(<ClaimsChecklistView initial={checklist()} />);

    const box = screen.getAllByRole("checkbox")[0]!;
    await user.click(box);

    await waitFor(() => expect(screen.getByRole("alert")).toBeDefined());
    expect(screen.getByRole("alert").textContent).toContain("has been undone");
    expect((box as HTMLInputElement).checked).toBe(false);
    expect(screen.getByText(/0 of 3 done/)).toBeDefined();
  });
});
