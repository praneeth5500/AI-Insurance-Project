import { Card } from "@/components/ui/card";

/**
 * "What we learned about you" (docs/01_PRODUCT_SPEC.md section 2.5).
 *
 * A synthesis of what the person told us, one statement per line so each can
 * be checked against what they actually answered. Every line is derived
 * server-side from a stored answer; nothing is inferred, and no AI writes it.
 */
export function DecisionProfileSummary({ lines }: { lines: readonly string[] }) {
  if (lines.length === 0) return null;

  return (
    <Card className="flex flex-col gap-3">
      <h2 className="text-h3 font-medium text-primary">What we learned about you</h2>
      <ul className="flex flex-col gap-2">
        {lines.map((line) => (
          <li key={line} className="text-body text-secondary">
            {line}
          </li>
        ))}
      </ul>
    </Card>
  );
}
