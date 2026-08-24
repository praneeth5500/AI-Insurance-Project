import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { ChoiceCard, ChoiceCardGroup } from "@/components/ui/choice-card";

function RadioGroupFixture({ onSelect }: { onSelect?: (value: string) => void }) {
  const [value, setValue] = useState("just-me");
  const options = [
    { value: "just-me", label: "Just me" },
    { value: "me-spouse", label: "Me + spouse" },
    { value: "me-family", label: "Me + family" },
  ];

  return (
    <ChoiceCardGroup legend="Who are you looking to protect?">
      {options.map((option) => (
        <ChoiceCard
          key={option.value}
          name="who"
          value={option.value}
          label={option.label}
          checked={value === option.value}
          onChange={() => {
            setValue(option.value);
            onSelect?.(option.value);
          }}
        />
      ))}
    </ChoiceCardGroup>
  );
}

describe("ChoiceCard", () => {
  it("renders real radios inside a labelled group", () => {
    render(<RadioGroupFixture />);

    expect(screen.getByRole("group", { name: "Who are you looking to protect?" })).toBeDefined();
    expect(screen.getAllByRole("radio")).toHaveLength(3);
    expect(screen.getByRole("radio", { name: "Just me" })).toBeDefined();
  });

  it("moves selection with arrow keys, as native radios do", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<RadioGroupFixture onSelect={onSelect} />);

    await user.tab();
    expect(screen.getByRole("radio", { name: "Just me" })).toBe(document.activeElement);

    await user.keyboard("{ArrowDown}");
    expect(onSelect).toHaveBeenCalledWith("me-spouse");
    expect((screen.getByRole("radio", { name: "Me + spouse" }) as HTMLInputElement).checked).toBe(
      true,
    );
  });

  it("puts the whole card in the label, so clicking anywhere selects it", async () => {
    const user = userEvent.setup();
    render(
      <ChoiceCardGroup legend="Priorities">
        <ChoiceCard
          type="checkbox"
          name="priority"
          value="copay"
          label="Low co-pay"
          description="Pay less of each claim yourself"
        />
      </ChoiceCardGroup>,
    );

    await user.click(screen.getByText("Pay less of each claim yourself"));
    expect((screen.getByRole("checkbox") as HTMLInputElement).checked).toBe(true);
  });

  it("supports multi-select via checkboxes", () => {
    render(
      <ChoiceCardGroup legend="Priorities">
        <ChoiceCard type="checkbox" name="p" value="a" label="A" />
        <ChoiceCard type="checkbox" name="p" value="b" label="B" />
      </ChoiceCardGroup>,
    );

    expect(screen.getAllByRole("checkbox")).toHaveLength(2);
  });

  it("does not select a disabled option", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ChoiceCardGroup legend="Priorities">
        <ChoiceCard name="p" value="a" label="Unavailable" disabled onChange={onChange} />
      </ChoiceCardGroup>,
    );

    await user.click(screen.getByText("Unavailable"));
    expect(onChange).not.toHaveBeenCalled();
  });

  it("keeps the legend available to screen readers when visually hidden", () => {
    render(
      <ChoiceCardGroup legend="Hidden question" hideLegend>
        <ChoiceCard name="p" value="a" label="A" />
      </ChoiceCardGroup>,
    );

    expect(screen.getByRole("group", { name: "Hidden question" })).toBeDefined();
  });

  it("announces a group-level error", () => {
    render(
      <ChoiceCardGroup legend="Priorities" error="Choose up to 3.">
        <ChoiceCard name="p" value="a" label="A" />
      </ChoiceCardGroup>,
    );

    expect(screen.getByRole("alert").textContent).toBe("Choose up to 3.");
  });
});
