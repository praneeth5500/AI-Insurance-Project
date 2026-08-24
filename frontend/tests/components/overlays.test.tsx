import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Sheet } from "@/components/ui/sheet";

function SheetFixture() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)}>Open sheet</Button>
      <Sheet
        open={open}
        onOpenChange={setOpen}
        title="Why we're asking this"
        description="Contextual help."
      >
        <p>Body content</p>
      </Sheet>
    </>
  );
}

function ModalFixture() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)}>Open modal</Button>
      <Modal
        open={open}
        onOpenChange={setOpen}
        title="Discard your answers?"
        footer={<Button onClick={() => setOpen(false)}>Discard</Button>}
      />
    </>
  );
}

describe("Sheet", () => {
  it("exposes an accessible name and description", async () => {
    const user = userEvent.setup();
    render(<SheetFixture />);

    await user.click(screen.getByRole("button", { name: "Open sheet" }));

    const dialog = await screen.findByRole("dialog", { name: "Why we're asking this" });
    const describedBy = dialog.getAttribute("aria-describedby")!;
    expect(document.getElementById(describedBy)?.textContent).toBe("Contextual help.");
  });

  it("moves focus into the sheet and traps it", async () => {
    const user = userEvent.setup();
    render(<SheetFixture />);

    await user.click(screen.getByRole("button", { name: "Open sheet" }));
    const dialog = await screen.findByRole("dialog");

    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));

    // Tabbing repeatedly must never escape the dialog.
    for (let i = 0; i < 6; i += 1) {
      await user.tab();
      expect(dialog.contains(document.activeElement)).toBe(true);
    }
  });

  it("closes on Escape and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    render(<SheetFixture />);

    const trigger = screen.getByRole("button", { name: "Open sheet" });
    await user.click(trigger);
    await screen.findByRole("dialog");

    await user.keyboard("{Escape}");

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(document.activeElement).toBe(trigger));
  });

  it("closes with the labelled close control", async () => {
    const user = userEvent.setup();
    render(<SheetFixture />);

    await user.click(screen.getByRole("button", { name: "Open sheet" }));
    await screen.findByRole("dialog");

    await user.click(screen.getByRole("button", { name: "Close" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });
});

describe("Modal", () => {
  it("is a dialog with an accessible name that receives focus", async () => {
    const user = userEvent.setup();
    render(<ModalFixture />);

    await user.click(screen.getByRole("button", { name: "Open modal" }));

    const dialog = await screen.findByRole("dialog", { name: "Discard your answers?" });
    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));
  });

  it("returns focus to the trigger when it closes", async () => {
    const user = userEvent.setup();
    render(<ModalFixture />);

    const trigger = screen.getByRole("button", { name: "Open modal" });
    await user.click(trigger);
    await screen.findByRole("dialog");

    await user.keyboard("{Escape}");
    await waitFor(() => expect(document.activeElement).toBe(trigger));
  });

  it("closes on Escape", async () => {
    const user = userEvent.setup();
    render(<ModalFixture />);

    await user.click(screen.getByRole("button", { name: "Open modal" }));
    await screen.findByRole("dialog");

    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("renders footer actions", async () => {
    const user = userEvent.setup();
    render(<ModalFixture />);

    await user.click(screen.getByRole("button", { name: "Open modal" }));
    expect(await screen.findByRole("button", { name: "Discard" })).toBeDefined();
  });
});
