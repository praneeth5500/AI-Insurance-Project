import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Button } from "@/components/ui/button";

describe("Button", () => {
  it("defaults to type=button so it cannot submit a form by accident", () => {
    render(<Button>Continue</Button>);

    expect(screen.getByRole("button", { name: "Continue" }).getAttribute("type")).toBe("button");
  });

  it("is reachable and activatable by keyboard", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Continue</Button>);

    await user.tab();
    expect(screen.getByRole("button", { name: "Continue" })).toBe(document.activeElement);

    await user.keyboard("{Enter}");
    await user.keyboard(" ");
    expect(onClick).toHaveBeenCalledTimes(2);
  });

  it("announces the loading state and blocks activation", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Find my matches
      </Button>,
    );

    const button = screen.getByRole("button");
    expect(button.getAttribute("aria-busy")).toBe("true");
    expect((button as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("Loading")).toBeDefined();

    await user.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("does not fire when disabled", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Continue
      </Button>,
    );

    await user.click(screen.getByRole("button"));
    expect(onClick).not.toHaveBeenCalled();
  });
});
