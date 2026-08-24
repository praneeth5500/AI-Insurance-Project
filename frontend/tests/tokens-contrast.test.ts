import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * docs/02_UX_UI_SPEC.md says "Validate contrast before finalizing".
 *
 * This test is that validation, kept in CI so a future token change cannot
 * quietly drop the palette below WCAG 2.1 AA. It reads the real stylesheet
 * rather than a copy of the values.
 */

const css = readFileSync(join(process.cwd(), "app", "globals.css"), "utf8");

function token(name: string): string {
  const match = new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})\\s*;`).exec(css);
  if (!match?.[1]) throw new Error(`Token --${name} not found in globals.css`);
  return match[1];
}

function channel(value: number): number {
  const c = value / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

function luminance(hex: string): number {
  const n = Number.parseInt(hex.slice(1), 16);
  return (
    0.2126 * channel((n >> 16) & 255) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255)
  );
}

export function contrast(a: string, b: string): number {
  const [lighter, darker] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (lighter + 0.05) / (darker + 0.05);
}

const AA_TEXT = 4.5;
const AA_NON_TEXT = 3;

describe("body and heading text", () => {
  it.each([
    ["text-primary on bg", "text-primary", "bg"],
    ["text-primary on surface", "text-primary", "surface"],
    ["text-secondary on bg", "text-secondary", "bg"],
    ["text-secondary on surface", "text-secondary", "surface"],
  ])("%s meets AA", (_name, fg, bg) => {
    expect(contrast(token(fg), token(bg))).toBeGreaterThanOrEqual(AA_TEXT);
  });
});

describe("text on soft tinted containers", () => {
  // InlineAlert puts --text-primary on every soft background for this reason.
  it.each(["accent-soft", "positive-soft", "attention-soft", "critical-soft"])(
    "text-primary on %s meets AA",
    (soft) => {
      expect(contrast(token("text-primary"), token(soft))).toBeGreaterThanOrEqual(AA_TEXT);
    },
  );
});

describe("interactive colour", () => {
  it("primary button label meets AA (surface on accent)", () => {
    expect(contrast(token("surface"), token("accent"))).toBeGreaterThanOrEqual(AA_TEXT);
  });

  it("accent as a link colour meets AA on both backgrounds", () => {
    expect(contrast(token("accent"), token("surface"))).toBeGreaterThanOrEqual(AA_TEXT);
    expect(contrast(token("accent"), token("bg"))).toBeGreaterThanOrEqual(AA_TEXT);
  });

  it("focus ring meets the 3:1 non-text minimum", () => {
    expect(contrast(token("accent"), token("bg"))).toBeGreaterThanOrEqual(AA_NON_TEXT);
    expect(contrast(token("accent"), token("surface"))).toBeGreaterThanOrEqual(AA_NON_TEXT);
  });

  it("control borders meet the 3:1 non-text minimum", () => {
    // --control-border aliases --text-secondary precisely because --border does
    // not clear 3:1. If that alias is changed, this test must still pass.
    expect(css).toMatch(/--control-border:\s*var\(--text-secondary\)/);
    expect(contrast(token("text-secondary"), token("surface"))).toBeGreaterThanOrEqual(AA_NON_TEXT);
  });
});

describe("status colours as icons and rules", () => {
  it.each([
    ["positive", "positive-soft"],
    ["attention", "attention-soft"],
    ["critical", "critical-soft"],
    ["accent", "accent-soft"],
  ])("%s meets the 3:1 non-text minimum on %s", (tone, soft) => {
    expect(contrast(token(tone), token(soft))).toBeGreaterThanOrEqual(AA_NON_TEXT);
  });
});

describe("known limitations", () => {
  it("attention on attention-soft is below AA for text, which is why it is icon-only", () => {
    const ratio = contrast(token("attention"), token("attention-soft"));
    expect(ratio).toBeLessThan(AA_TEXT);
    expect(ratio).toBeGreaterThanOrEqual(AA_NON_TEXT);
  });

  it("the decorative border is not used as a control boundary", () => {
    // --border is intentionally subtle (1.24:1) and must stay decorative.
    expect(contrast(token("border"), token("surface"))).toBeLessThan(AA_NON_TEXT);
  });
});
