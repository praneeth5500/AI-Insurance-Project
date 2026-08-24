import { InlineAlert } from "@/components/feedback/inline-alert";

/**
 * Marks a screen as showing synthetic content.
 *
 * docs/00_README.md, "Prototype truth rule": prototype data must never look
 * like verified real insurance facts. Whenever the home summary comes back
 * with `dataMode: "DEMO"`, this notice is shown above it.
 */
export function DemoDataNotice() {
  return (
    <InlineAlert tone="attention" title="Demo content">
      The activity below is placeholder data used to review this layout. It is not your information,
      and none of it describes a real policy.
    </InlineAlert>
  );
}
