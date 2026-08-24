import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Input } from "@/components/ui/input";

describe("Input", () => {
  it("associates the visible label with the field", () => {
    render(<Input label="Pincode" />);

    expect(screen.getByLabelText("Pincode")).toBeDefined();
  });

  it("links its description so screen readers read it with the field", () => {
    render(<Input label="Pincode" description="Used to check availability." />);

    const field = screen.getByLabelText("Pincode");
    const describedBy = field.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    expect(document.getElementById(describedBy!)?.textContent).toBe("Used to check availability.");
  });

  it("marks the field invalid and links the error message", () => {
    render(<Input label="Pincode" error="Enter all 6 digits." />);

    const field = screen.getByLabelText("Pincode");
    expect(field.getAttribute("aria-invalid")).toBe("true");

    const describedBy = field.getAttribute("aria-describedby")!;
    expect(document.getElementById(describedBy)?.textContent).toBe("Enter all 6 digits.");
    expect(screen.getByRole("alert").textContent).toBe("Enter all 6 digits.");
  });

  it("links both description and error at once", () => {
    render(<Input label="Pincode" description="Six digits." error="Too short." />);

    const ids = screen.getByLabelText("Pincode").getAttribute("aria-describedby")!.split(" ");
    expect(ids).toHaveLength(2);
    expect(ids.map((id) => document.getElementById(id)?.textContent)).toEqual([
      "Six digits.",
      "Too short.",
    ]);
  });

  it("generates unique ids so two fields never collide", () => {
    render(
      <>
        <Input label="First" />
        <Input label="Second" />
      </>,
    );

    expect(screen.getByLabelText("First").id).not.toBe(screen.getByLabelText("Second").id);
  });

  it("exposes the required state to assistive technology", () => {
    render(<Input label="Pincode" required />);

    expect(screen.getByLabelText(/Pincode/).hasAttribute("required")).toBe(true);
    expect(screen.getByText("(required)")).toBeDefined();
  });

  it("accepts typed input", async () => {
    const user = userEvent.setup();
    render(<Input label="Pincode" />);

    await user.type(screen.getByLabelText("Pincode"), "560001");
    expect((screen.getByLabelText("Pincode") as HTMLInputElement).value).toBe("560001");
  });
});
