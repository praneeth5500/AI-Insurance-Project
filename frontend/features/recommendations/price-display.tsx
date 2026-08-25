import type { PriceView } from "@/lib/api/types";

/**
 * A price, or an honest statement that there isn't one.
 *
 * docs/12_BETA_CHECKLIST.md requires every displayed premium to carry a
 * state, a source and a timestamp, and docs/01_PRODUCT_SPEC.md section 7
 * forbids describing an indicative figure as final. This component therefore
 * cannot render a bare number: it renders a state.
 *
 * For synthetic products the state is UNAVAILABLE and it says why, because
 * CLAUDE.md forbids inventing a premium.
 */
const STATE_LABEL: Record<PriceView["state"], string> = {
  INDICATIVE: "Indicative premium",
  QUOTED: "Quoted premium",
  FINAL: "Confirmed premium",
  UNAVAILABLE: "No price available",
};

export function PriceDisplay({ price }: { price: PriceView }) {
  return (
    <div className="flex flex-col gap-0.5">
      <p className="text-meta font-medium text-secondary">{STATE_LABEL[price.state]}</p>
      {price.state !== "UNAVAILABLE" && price.amount !== null ? (
        <p className="text-h3 font-semibold text-primary">
          {price.currency === "INR" ? "₹" : ""}
          {price.amount.toLocaleString("en-IN")}
        </p>
      ) : null}
      <p className="text-meta text-secondary">{price.explanation}</p>
    </div>
  );
}
