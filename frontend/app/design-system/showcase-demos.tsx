"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ChoiceCard, ChoiceCardGroup } from "@/components/ui/choice-card";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Sheet } from "@/components/ui/sheet";
import { ProgressStage } from "@/components/feedback/progress-stage";

/** Onboarding stages from docs/02_UX_UI_SPEC.md section 7. */
const STAGES = ["About you", "Your cover", "What matters", "Review"] as const;

export function ProgressStageDemo() {
  const [index, setIndex] = useState(1);

  return (
    <div className="flex flex-col gap-4">
      <ProgressStage stages={STAGES} currentIndex={index} />
      <div className="flex gap-2">
        <Button variant="secondary" onClick={() => setIndex((i) => Math.max(0, i - 1))}>
          Back
        </Button>
        <Button onClick={() => setIndex((i) => Math.min(STAGES.length - 1, i + 1))}>
          Continue
        </Button>
      </div>
    </div>
  );
}

export function ChoiceCardDemo() {
  const [who, setWho] = useState("just-me");
  const [priorities, setPriorities] = useState<string[]>(["copay"]);

  const togglePriority = (value: string) => {
    setPriorities((current) =>
      current.includes(value) ? current.filter((v) => v !== value) : [...current, value],
    );
  };

  return (
    <div className="flex flex-col gap-8">
      <ChoiceCardGroup
        legend="Who are you looking to protect?"
        description="Single select. Arrow keys move between options."
        columns={2}
      >
        {[
          { value: "just-me", label: "Just me" },
          { value: "me-spouse", label: "Me + spouse" },
          { value: "me-family", label: "Me + family" },
          { value: "my-parents", label: "My parents" },
        ].map((option) => (
          <ChoiceCard
            key={option.value}
            name="showcase-who"
            value={option.value}
            label={option.label}
            checked={who === option.value}
            onChange={() => setWho(option.value)}
          />
        ))}
      </ChoiceCardGroup>

      <ChoiceCardGroup
        legend="Multi-select variant"
        description="Each option is an independent checkbox."
        columns={2}
      >
        {[
          { value: "copay", label: "Low co-pay", description: "Pay less of each claim yourself" },
          { value: "waiting", label: "Short waiting periods" },
          { value: "hospitals", label: "Hospital flexibility" },
          { value: "disabled", label: "Unavailable option", description: "Disabled state" },
        ].map((option) => (
          <ChoiceCard
            key={option.value}
            type="checkbox"
            name="showcase-priority"
            value={option.value}
            label={option.label}
            {...(option.description ? { description: option.description } : {})}
            disabled={option.value === "disabled"}
            checked={priorities.includes(option.value)}
            onChange={() => togglePriority(option.value)}
          />
        ))}
      </ChoiceCardGroup>
    </div>
  );
}

export function InputDemo() {
  const [value, setValue] = useState("");
  const showError = value.length > 0 && value.length < 6;

  return (
    <div className="flex max-w-md flex-col gap-6">
      <Input
        label="Pincode"
        description="Used to check which options are available in your area."
        placeholder="560001"
        inputMode="numeric"
        required
        value={value}
        onChange={(event) => setValue(event.target.value)}
        {...(showError ? { error: "Enter all 6 digits of your pincode." } : {})}
      />
      <Input label="Approximate annual budget" prefix="₹" inputMode="numeric" />
      <Input label="Disabled field" disabled placeholder="Not editable" />
    </div>
  );
}

export function OverlayDemo() {
  const [sheetOpen, setSheetOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div className="flex flex-wrap gap-3">
      <Button variant="secondary" onClick={() => setSheetOpen(true)}>
        Open sheet
      </Button>
      <Button variant="secondary" onClick={() => setModalOpen(true)}>
        Open modal
      </Button>

      <Sheet
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        title="Why we're asking this"
        description="Bottom sheet on mobile, side panel from md up."
        footer={
          <Button fullWidth onClick={() => setSheetOpen(false)}>
            Got it
          </Button>
        }
      >
        <p className="text-body text-secondary">
          Secondary controls and contextual help open here so the user keeps their place in the
          flow. Focus is trapped while it is open, Escape closes it, and focus returns to the button
          that opened it.
        </p>
      </Sheet>

      <Modal
        open={modalOpen}
        onOpenChange={setModalOpen}
        title="Discard your answers?"
        description="A modal interrupts, so it is reserved for a decision that blocks progress."
        footer={
          <>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Keep editing
            </Button>
            <Button onClick={() => setModalOpen(false)}>Discard</Button>
          </>
        }
      />
    </div>
  );
}
